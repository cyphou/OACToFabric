"""Prompt builder — domain-specific prompt construction with context management.

Builds LLM prompts that include:
- Agent role and file-ownership constraints (from AGENTS.md)
- Task-specific instructions
- Few-shot examples from the translation catalog
- Relevant agent memory entries
- Context window management (priority-based truncation)

Usage::

    builder = PromptBuilder(agent_id="04-semantic", agent_role="Semantic Model Agent")
    system, user = builder.build(
        task="translate_expression",
        source="@SUM(Sales)",
        context={"target_format": "DAX"},
        few_shots=[("@AVG(Profit)", "AVERAGE(Fact[Profit])")],
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Approximate tokens per character (conservative for English + code)
_CHARS_PER_TOKEN = 4

# Default context window (GPT-4.1 supports 128K; we leave headroom)
DEFAULT_MAX_CONTEXT_TOKENS = 60_000


# ---------------------------------------------------------------------------
# Agent role definitions
# ---------------------------------------------------------------------------

AGENT_ROLES: dict[str, str] = {
    "01-discovery": (
        "You are the Discovery Agent. You crawl OAC environments, parse RPD XML, "
        "build inventory, and assess migration complexity. You produce only inventory "
        "and dependency metadata. Do NOT modify schema DDL, ETL pipelines, semantic "
        "models, or reports."
    ),
    "02-schema": (
        "You are the Schema Migration Agent. You convert Oracle DDL to Fabric "
        "Lakehouse/Warehouse tables. You produce Fabric table DDL, data type mappings, "
        "and data copy pipelines. Do NOT modify report visuals or semantic models."
    ),
    "03-etl": (
        "You are the ETL Migration Agent. You convert OAC Data Flows and PL/SQL to "
        "Fabric pipelines and PySpark notebooks. Do NOT modify schema DDL or semantic "
        "model logic."
    ),
    "04-semantic": (
        "You are the Semantic Model Agent. You convert RPD logical models to TMDL "
        "semantic models and translate OAC expressions to DAX. Do NOT modify report "
        "visuals, security roles, or schema DDL."
    ),
    "05-report": (
        "You are the Report Migration Agent. You convert OAC Analyses and Dashboards "
        "to PBIR reports. Do NOT modify semantic model TMDL or schema DDL."
    ),
    "06-security": (
        "You are the Security Agent. You migrate OAC roles, RLS, and OLS to Fabric "
        "and Power BI security. Do NOT modify TMDL tables/measures or report visuals."
    ),
    "07-validation": (
        "You are the Validation Agent. You verify migration correctness across all "
        "layers. You read all source files for verification but write only to "
        "validation outputs and tests."
    ),
    "08-orchestrator": (
        "You are the Orchestrator Agent. You coordinate all agents, manage "
        "dependencies, and monitor progress. You delegate all domain work to the "
        "appropriate agent."
    ),
}


# ---------------------------------------------------------------------------
# Few-shot example
# ---------------------------------------------------------------------------


@dataclass
class FewShotExample:
    """A single few-shot example for prompt building."""

    source: str
    target: str
    explanation: str = ""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


@dataclass
class PromptBuilder:
    """Builds structured prompts for an agent's LLM reasoning loop.

    Parameters
    ----------
    agent_id
        Agent identifier (e.g. ``"04-semantic"``).
    agent_role
        Override the default role description for the agent.
    max_context_tokens
        Maximum tokens for the full prompt (system + user).
    """

    agent_id: str
    agent_role: str = ""
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS
    _negative_examples: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.agent_role:
            self.agent_role = AGENT_ROLES.get(self.agent_id, "You are a migration agent.")

    def add_negative_example(self, example: str) -> None:
        """Add a negative example (from rejected human reviews)."""
        self._negative_examples.append(example)

    def build(
        self,
        task: str,
        source: str,
        *,
        context: dict[str, Any] | None = None,
        few_shots: list[FewShotExample] | None = None,
        memory_entries: list[dict[str, Any]] | None = None,
        constraints: list[str] | None = None,
    ) -> tuple[str, str]:
        """Build (system_prompt, user_prompt) for an LLM call.

        Parameters
        ----------
        task
            Task type (e.g. ``"translate_expression"``, ``"diagnose_error"``).
        source
            The source content to process.
        context
            Additional key-value context (e.g. target format, table mapping).
        few_shots
            Examples for few-shot learning.
        memory_entries
            Relevant agent memory entries (dicts with key/value/confidence).
        constraints
            Additional constraints to append to the system prompt.
        """
        system = self._build_system(task, constraints)
        user = self._build_user(task, source, context, few_shots, memory_entries)

        # Truncate if too long
        total_chars = len(system) + len(user)
        max_chars = self.max_context_tokens * _CHARS_PER_TOKEN
        if total_chars > max_chars:
            user = self._truncate(user, max_chars - len(system))

        return system, user

    def _build_system(self, task: str, constraints: list[str] | None) -> str:
        parts = [self.agent_role]

        if task:
            parts.append(f"\nCurrent task: {task}")

        parts.append("\nRules:")
        parts.append("- Return ONLY the requested output, no explanation unless asked.")
        parts.append("- If uncertain, express your confidence level (0.0–1.0).")
        parts.append("- Preserve business logic exactly.")

        if constraints:
            for c in constraints:
                parts.append(f"- {c}")

        if self._negative_examples:
            parts.append("\nKnown incorrect outputs (DO NOT repeat these):")
            for neg in self._negative_examples[-5:]:  # last 5
                parts.append(f"  ✗ {neg}")

        return "\n".join(parts)

    def _build_user(
        self,
        task: str,
        source: str,
        context: dict[str, Any] | None,
        few_shots: list[FewShotExample] | None,
        memory_entries: list[dict[str, Any]] | None,
    ) -> str:
        parts: list[str] = []

        # Few-shot examples (highest priority)
        if few_shots:
            parts.append("## Examples")
            for ex in few_shots:
                parts.append(f"Source: {ex.source}")
                parts.append(f"Target: {ex.target}")
                if ex.explanation:
                    parts.append(f"Note: {ex.explanation}")
                parts.append("")

        # Memory (prior decisions)
        if memory_entries:
            parts.append("## Prior Decisions (from memory)")
            for m in memory_entries[:10]:  # cap at 10
                parts.append(f"- {m.get('key', '?')} → {m.get('value', '?')} "
                             f"(confidence: {m.get('confidence', '?')})")
            parts.append("")

        # Context
        if context:
            parts.append("## Context")
            for k, v in context.items():
                parts.append(f"- {k}: {v}")
            parts.append("")

        # Source (the actual task input)
        parts.append("## Input")
        parts.append(source)

        return "\n".join(parts)

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Truncate text to fit within max_chars, keeping start and end."""
        if len(text) <= max_chars:
            return text
        half = max_chars // 2
        return text[:half] + "\n\n... [truncated] ...\n\n" + text[-half:]

    def estimate_tokens(self, system: str, user: str) -> int:
        """Rough token estimate for budgeting."""
        return (len(system) + len(user)) // _CHARS_PER_TOKEN
