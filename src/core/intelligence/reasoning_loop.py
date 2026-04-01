"""Reasoning loop — ReAct (Reason + Act) loop for agent LLM reasoning.

Wraps the agent lifecycle with LLM reasoning that decides:
1. Whether rules suffice or LLM reasoning is needed.
2. Which tool to call and with what parameters.
3. How to interpret tool results and decide next steps.
4. When to stop (task complete or max iterations reached).

The loop is **additive** — it enhances agents, not replaces them.  Existing
rule-based logic stays as the fast path; the reasoning loop handles the
long tail that rules don't cover.

Usage::

    loop = ReasoningLoop(
        llm_client=llm,
        tool_registry=tools,
        prompt_builder=builder,
        agent_memory=memory,
        cost_controller=costs,
    )
    result = await loop.run(task="translate_expression", source="@SUM(Sales)")
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class StepType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL = "final"


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""

    step_type: StepType
    content: str
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_result: Any = None
    tokens_used: int = 0
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.step_type.value,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "tool_result": str(self.tool_result)[:500] if self.tool_result else None,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
        }


@dataclass
class ReasoningResult:
    """Result of a full reasoning loop execution."""

    output: Any = None
    success: bool = False
    confidence: float = 0.0
    steps: list[ReasoningStep] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    iterations: int = 0
    error: str = ""

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": str(self.output)[:1000] if self.output else None,
            "success": self.success,
            "confidence": self.confidence,
            "iterations": self.iterations,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "steps": [s.to_dict() for s in self.steps],
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# ReAct prompt fragments
# ---------------------------------------------------------------------------

_REACT_SUFFIX = """

You have access to the following tools:
{tool_list}

Use the following format:

Thought: reason about what to do
Action: tool_name
Action Input: {{"param1": "value1"}}
Observation: [tool result will appear here]
... (repeat Thought/Action/Observation as needed)
Thought: I have the answer
Final Answer: [your final output]
Confidence: [0.0-1.0]

Begin!
"""


# ---------------------------------------------------------------------------
# Reasoning loop
# ---------------------------------------------------------------------------


class ReasoningLoop:
    """ReAct reasoning loop wrapping agent tasks.

    Parameters
    ----------
    llm_complete
        Async callable matching ``LLMClient.complete`` signature:
        ``(system_prompt, user_prompt, **kwargs) -> LLMResponse``.
        Accepts any async callable, not just ``LLMClient``, for testability.
    tool_registry
        Tools available to the LLM.
    prompt_builder
        Domain-specific prompt builder.
    agent_memory
        Per-agent memory store (optional).
    cost_controller
        Token budget controller (optional).
    agent_id
        Agent identifier for cost tracking.
    max_iterations
        Maximum reasoning iterations before forced stop.
    """

    def __init__(
        self,
        llm_complete: Any,
        tool_registry: Any,
        prompt_builder: Any,
        agent_memory: Any | None = None,
        cost_controller: Any | None = None,
        agent_id: str = "",
        max_iterations: int = 10,
    ) -> None:
        self._llm = llm_complete
        self._tools = tool_registry
        self._builder = prompt_builder
        self._memory = agent_memory
        self._costs = cost_controller
        self._agent_id = agent_id
        self._max_iterations = max_iterations

    async def run(
        self,
        task: str,
        source: str,
        *,
        context: dict[str, Any] | None = None,
        few_shots: list[Any] | None = None,
    ) -> ReasoningResult:
        """Execute the ReAct reasoning loop.

        Parameters
        ----------
        task
            Task type (e.g. ``"translate_expression"``).
        source
            Source content to process.
        context
            Additional context for the prompt.
        few_shots
            Few-shot examples.

        Returns
        -------
        ReasoningResult
            The result including output, confidence, and full reasoning chain.
        """
        result = ReasoningResult()
        start = time.monotonic()

        # Check cost budget
        if self._costs and not self._costs.can_spend(self._agent_id, estimated_tokens=500):
            result.error = "Token budget exhausted before starting"
            return result

        # Gather memory context
        memory_entries = None
        if self._memory:
            entries = self._memory.recall(query=source[:100], limit=5)
            if entries:
                memory_entries = [e.to_dict() for e in entries]

        # Build prompt
        system, user = self._builder.build(
            task=task,
            source=source,
            context=context,
            few_shots=few_shots,
            memory_entries=memory_entries,
        )

        # Append tool list and ReAct format
        tool_descriptions = self._format_tools()
        user = user + _REACT_SUFFIX.format(tool_list=tool_descriptions)

        conversation = user

        for iteration in range(self._max_iterations):
            result.iterations = iteration + 1

            # Call LLM
            try:
                response = await self._llm(system, conversation)
            except Exception as exc:
                result.error = f"LLM call failed: {exc}"
                break

            tokens = getattr(response, "total_tokens", 0)
            latency = getattr(response, "latency_ms", 0.0)
            content = getattr(response, "content", str(response))
            result.total_tokens += tokens

            if self._costs:
                self._costs.record(self._agent_id, tokens)

            # Parse the response
            parsed = self._parse_response(content)

            for step in parsed:
                step.tokens_used = tokens if step is parsed[0] else 0
                step.latency_ms = latency if step is parsed[0] else 0.0
                result.steps.append(step)

                if step.step_type == StepType.FINAL:
                    result.output = step.content
                    result.success = True
                    result.confidence = self._extract_confidence(content)
                    break

                if step.step_type == StepType.ACTION and step.tool_name:
                    # Execute tool
                    tool_result = await self._execute_tool(step.tool_name, step.tool_args)
                    obs = ReasoningStep(
                        step_type=StepType.OBSERVATION,
                        content=str(tool_result.output if hasattr(tool_result, "output") else tool_result),
                    )
                    result.steps.append(obs)
                    conversation += f"\nObservation: {obs.content}\n"

            if result.success:
                break

            # Add response to conversation for next iteration
            conversation += f"\n{content}\n"

        result.total_latency_ms = (time.monotonic() - start) * 1000

        # Store result in memory
        if self._memory and result.success and result.output:
            self._memory.store(
                "decision",
                key=source[:200],
                value=result.output,
                confidence=result.confidence,
                metadata={"task": task, "iterations": result.iterations},
            )

        return result

    def _format_tools(self) -> str:
        """Format tool descriptions for the ReAct prompt."""
        if not self._tools:
            return "(no tools available)"
        tools = self._tools.list_tools(agent_id=self._agent_id) if hasattr(self._tools, "list_tools") else []
        if not tools:
            return "(no tools available)"
        lines = []
        for t in tools:
            params = ", ".join(f"{k}: {v.type}" for k, v in t.parameters.items())
            lines.append(f"- {t.name}({params}): {t.description}")
        return "\n".join(lines)

    @staticmethod
    def _parse_response(content: str) -> list[ReasoningStep]:
        """Parse a ReAct-formatted LLM response into steps."""
        steps: list[ReasoningStep] = []
        lines = content.strip().split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.lower().startswith("thought:"):
                steps.append(ReasoningStep(
                    step_type=StepType.THOUGHT,
                    content=line[len("thought:"):].strip(),
                ))

            elif line.lower().startswith("action:"):
                tool_name = line[len("action:"):].strip()
                tool_args: dict[str, Any] = {}

                # Look for Action Input on next line
                if i + 1 < len(lines) and lines[i + 1].strip().lower().startswith("action input:"):
                    raw = lines[i + 1].strip()[len("action input:"):].strip()
                    try:
                        tool_args = json.loads(raw)
                    except (json.JSONDecodeError, ValueError):
                        tool_args = {"raw": raw}
                    i += 1

                steps.append(ReasoningStep(
                    step_type=StepType.ACTION,
                    content=f"Call {tool_name}",
                    tool_name=tool_name,
                    tool_args=tool_args,
                ))

            elif line.lower().startswith("final answer:"):
                steps.append(ReasoningStep(
                    step_type=StepType.FINAL,
                    content=line[len("final answer:"):].strip(),
                ))

            elif line.lower().startswith("observation:"):
                steps.append(ReasoningStep(
                    step_type=StepType.OBSERVATION,
                    content=line[len("observation:"):].strip(),
                ))

            i += 1

        # If no structured output was parsed, treat entire content as final
        if not steps:
            steps.append(ReasoningStep(
                step_type=StepType.FINAL,
                content=content.strip(),
            ))

        return steps

    @staticmethod
    def _extract_confidence(content: str) -> float:
        """Extract confidence score from response (if present)."""
        for line in content.split("\n"):
            line = line.strip().lower()
            if line.startswith("confidence:"):
                try:
                    val = float(line[len("confidence:"):].strip())
                    return max(0.0, min(1.0, val))
                except ValueError:
                    pass
        return 0.8  # default confidence if not specified

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Execute a tool and return the result."""
        try:
            if hasattr(self._tools, "invoke"):
                return await self._tools.invoke(name, args)
            return f"Tool '{name}' not available"
        except Exception as exc:
            logger.warning("Tool '%s' execution failed: %s", name, exc)
            return f"Error: {exc}"
