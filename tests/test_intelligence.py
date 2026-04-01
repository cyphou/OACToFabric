"""Tests for src/core/intelligence — Phase 70 Agent Intelligence Framework.

Covers: ToolRegistry, CostController, SemanticCache, AgentMemory,
PromptBuilder, ReasoningLoop, and IntelligentMixin.
"""

from __future__ import annotations

import asyncio
import json
import time
import unittest
from dataclasses import dataclass
from typing import Any

from src.core.intelligence.tool_registry import (
    ToolDefinition,
    ToolParameter,
    ToolRegistry,
    ToolResult,
)
from src.core.intelligence.cost_controller import (
    AgentBudget,
    CostController,
    SemanticCache,
)
from src.core.intelligence.agent_memory import (
    AgentMemory,
    MemoryEntry,
)
from src.core.intelligence.prompt_builder import (
    AGENT_ROLES,
    FewShotExample,
    PromptBuilder,
)
from src.core.intelligence.reasoning_loop import (
    ReasoningLoop,
    ReasoningResult,
    ReasoningStep,
    StepType,
)
from src.core.base_agent import IntelligentMixin, MigrationAgent
from src.core.models import (
    Inventory,
    MigrationPlan,
    MigrationResult,
    MigrationScope,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _sync_handler(x: str) -> str:
    return f"echo:{x}"


async def _async_handler(x: str) -> str:
    return f"async:{x}"


async def _failing_handler(x: str) -> str:
    raise ValueError("boom")


# ---------------------------------------------------------------------------
# ToolRegistry tests
# ---------------------------------------------------------------------------


class TestToolParameter(unittest.TestCase):

    def test_defaults(self):
        p = ToolParameter()
        self.assertEqual(p.type, "string")
        self.assertTrue(p.required)
        self.assertIsNone(p.enum)


class TestToolDefinition(unittest.TestCase):

    def test_to_llm_schema(self):
        tool = ToolDefinition(
            name="translate",
            description="Translate expression",
            parameters={"expr": ToolParameter(type="string", description="OAC expr")},
        )
        schema = tool.to_llm_schema()
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "translate")
        self.assertIn("expr", schema["function"]["parameters"]["properties"])
        self.assertIn("expr", schema["function"]["parameters"]["required"])

    def test_optional_param_not_in_required(self):
        tool = ToolDefinition(
            name="t",
            description="d",
            parameters={"a": ToolParameter(required=False)},
        )
        schema = tool.to_llm_schema()
        self.assertEqual(schema["function"]["parameters"]["required"], [])

    def test_enum_in_schema(self):
        tool = ToolDefinition(
            name="t",
            description="d",
            parameters={"mode": ToolParameter(enum=["fast", "slow"])},
        )
        schema = tool.to_llm_schema()
        self.assertEqual(
            schema["function"]["parameters"]["properties"]["mode"]["enum"],
            ["fast", "slow"],
        )


class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        self.reg = ToolRegistry()

    def test_register_and_get(self):
        tool = ToolDefinition(name="t1", description="d1")
        self.reg.register(tool)
        self.assertEqual(self.reg.get("t1").description, "d1")

    def test_get_missing_raises(self):
        with self.assertRaises(KeyError):
            self.reg.get("nonexistent")

    def test_has_and_contains(self):
        self.reg.register(ToolDefinition(name="x", description=""))
        self.assertTrue(self.reg.has("x"))
        self.assertIn("x", self.reg)
        self.assertNotIn("y", self.reg)

    def test_len(self):
        self.assertEqual(len(self.reg), 0)
        self.reg.register(ToolDefinition(name="a", description=""))
        self.assertEqual(len(self.reg), 1)

    def test_register_function_auto_params(self):
        def my_func(name: str, count: int = 5) -> str:
            """Do something."""
            return f"{name}:{count}"

        tool = self.reg.register_function("my_func", my_func)
        self.assertEqual(tool.name, "my_func")
        self.assertIn("name", tool.parameters)
        self.assertEqual(tool.parameters["name"].type, "string")
        self.assertTrue(tool.parameters["name"].required)
        self.assertEqual(tool.parameters["count"].type, "integer")
        self.assertFalse(tool.parameters["count"].required)

    def test_list_tools_all(self):
        self.reg.register(ToolDefinition(name="a", description=""))
        self.reg.register(ToolDefinition(name="b", description=""))
        self.assertEqual(len(self.reg.list_tools()), 2)

    def test_list_tools_agent_scope(self):
        self.reg.register(ToolDefinition(name="a", description="", agent_scope=["04-semantic"]))
        self.reg.register(ToolDefinition(name="b", description="", agent_scope=["05-report"]))
        self.reg.register(ToolDefinition(name="c", description=""))  # no scope = all
        result = self.reg.list_tools(agent_id="04-semantic")
        names = {t.name for t in result}
        self.assertIn("a", names)
        self.assertIn("c", names)
        self.assertNotIn("b", names)

    def test_to_llm_tools(self):
        self.reg.register(ToolDefinition(name="t", description="d"))
        schemas = self.reg.to_llm_tools()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["function"]["name"], "t")

    def test_invoke_sync_handler(self):
        self.reg.register(ToolDefinition(
            name="echo", description="", handler=_sync_handler,
            parameters={"x": ToolParameter()},
        ))
        result = _run(self.reg.invoke("echo", {"x": "hello"}))
        self.assertTrue(result.success)
        self.assertEqual(result.output, "echo:hello")

    def test_invoke_async_handler(self):
        self.reg.register(ToolDefinition(
            name="aecho", description="", handler=_async_handler,
            parameters={"x": ToolParameter()},
        ))
        result = _run(self.reg.invoke("aecho", {"x": "hi"}))
        self.assertTrue(result.success)
        self.assertEqual(result.output, "async:hi")

    def test_invoke_missing_tool(self):
        result = _run(self.reg.invoke("nope", {}))
        self.assertFalse(result.success)
        self.assertIn("not found", result.error)

    def test_invoke_no_handler(self):
        self.reg.register(ToolDefinition(name="nohandler", description=""))
        result = _run(self.reg.invoke("nohandler", {}))
        self.assertFalse(result.success)
        self.assertIn("no handler", result.error)

    def test_invoke_missing_required_param(self):
        self.reg.register(ToolDefinition(
            name="need_x", description="",
            handler=_sync_handler,
            parameters={"x": ToolParameter(required=True)},
        ))
        result = _run(self.reg.invoke("need_x", {}))
        self.assertFalse(result.success)
        self.assertIn("Missing required", result.error)

    def test_invoke_handler_exception(self):
        self.reg.register(ToolDefinition(
            name="fail", description="", handler=_failing_handler,
            parameters={"x": ToolParameter()},
        ))
        result = _run(self.reg.invoke("fail", {"x": "a"}))
        self.assertFalse(result.success)
        self.assertIn("boom", result.error)


# ---------------------------------------------------------------------------
# SemanticCache tests
# ---------------------------------------------------------------------------


class TestSemanticCache(unittest.TestCase):

    def test_put_and_get(self):
        cache = SemanticCache()
        cache.put("sys", "usr", "result")
        self.assertEqual(cache.get("sys", "usr"), "result")

    def test_miss(self):
        cache = SemanticCache()
        self.assertIsNone(cache.get("a", "b"))

    def test_hit_rate(self):
        cache = SemanticCache()
        cache.put("s", "u", "v")
        cache.get("s", "u")  # hit
        cache.get("x", "y")  # miss
        self.assertAlmostEqual(cache.hit_rate, 0.5)

    def test_eviction(self):
        cache = SemanticCache(max_size=2)
        cache.put("s1", "u1", "v1")
        cache.put("s2", "u2", "v2")
        cache.put("s3", "u3", "v3")  # evicts s1/u1
        self.assertIsNone(cache.get("s1", "u1"))
        self.assertEqual(cache.get("s3", "u3"), "v3")

    def test_clear(self):
        cache = SemanticCache()
        cache.put("a", "b", "c")
        cache.clear()
        self.assertEqual(cache.size, 0)
        self.assertAlmostEqual(cache.hit_rate, 0.0)


# ---------------------------------------------------------------------------
# CostController tests
# ---------------------------------------------------------------------------


class TestAgentBudget(unittest.TestCase):

    def test_remaining(self):
        b = AgentBudget(agent_id="a", budget=1000, used=300)
        self.assertEqual(b.remaining, 700)

    def test_exhausted(self):
        b = AgentBudget(agent_id="a", budget=100, used=100)
        self.assertTrue(b.exhausted)
        b2 = AgentBudget(agent_id="a", budget=100, used=50)
        self.assertFalse(b2.exhausted)

    def test_utilization(self):
        b = AgentBudget(agent_id="a", budget=1000, used=500)
        self.assertAlmostEqual(b.utilization, 0.5)


class TestCostController(unittest.TestCase):

    def setUp(self):
        self.cc = CostController(default_budget=10_000, cost_per_1k_tokens=0.01)

    def test_set_and_get_budget(self):
        self.cc.set_budget("agent1", 5000)
        b = self.cc.get_budget("agent1")
        self.assertEqual(b.budget, 5000)

    def test_lazy_create_budget(self):
        b = self.cc.get_budget("new_agent")
        self.assertEqual(b.budget, 10_000)

    def test_can_spend(self):
        self.cc.set_budget("a", 1000)
        self.assertTrue(self.cc.can_spend("a", 500))
        self.assertFalse(self.cc.can_spend("a", 2000))

    def test_can_spend_unlimited(self):
        self.cc.set_budget("a", 0)  # unlimited
        self.assertTrue(self.cc.can_spend("a", 999_999))

    def test_record_tokens(self):
        self.cc.record("agent1", 500)
        b = self.cc.get_budget("agent1")
        self.assertEqual(b.used, 500)

    def test_record_multiple(self):
        self.cc.record("a", 100)
        self.cc.record("a", 200)
        b = self.cc.get_budget("a")
        self.assertEqual(b.used, 300)

    def test_summary(self):
        self.cc.record("a", 100, cost_usd=0.01)
        self.cc.record("b", 200, cost_usd=0.02)
        s = self.cc.summary()
        self.assertEqual(s.total_tokens, 300)
        self.assertAlmostEqual(s.total_cost_usd, 0.03)
        self.assertEqual(s.total_calls, 2)
        self.assertIn("a", s.by_agent)
        self.assertIn("b", s.by_agent)

    def test_reset_specific(self):
        self.cc.record("a", 100)
        self.cc.reset("a")
        self.assertEqual(self.cc.get_budget("a").used, 0)

    def test_reset_all(self):
        self.cc.record("a", 100)
        self.cc.record("b", 200)
        self.cc.reset()
        self.assertEqual(self.cc.get_budget("a").used, 0)
        self.assertEqual(self.cc.get_budget("b").used, 0)

    def test_cache_integration(self):
        self.cc.cache.put("s", "u", "cached_val")
        self.assertEqual(self.cc.cache.get("s", "u"), "cached_val")


# ---------------------------------------------------------------------------
# AgentMemory tests
# ---------------------------------------------------------------------------


class TestMemoryEntry(unittest.TestCase):

    def test_not_expired_by_default(self):
        e = MemoryEntry(entry_type="decision", key="k", value="v")
        self.assertFalse(e.expired)

    def test_expired_with_ttl(self):
        e = MemoryEntry(
            entry_type="decision", key="k", value="v",
            ttl_seconds=0.01, created_at=time.time() - 1,
        )
        self.assertTrue(e.expired)

    def test_to_dict(self):
        e = MemoryEntry(entry_type="pattern", key="k", value="v")
        d = e.to_dict()
        self.assertEqual(d["entry_type"], "pattern")
        self.assertEqual(d["key"], "k")


class TestAgentMemory(unittest.TestCase):

    def setUp(self):
        self.mem = AgentMemory("04-semantic")

    def test_store_and_get(self):
        self.mem.store("decision", "key1", "val1")
        e = self.mem.get("key1")
        self.assertIsNotNone(e)
        self.assertEqual(e.value, "val1")

    def test_get_missing(self):
        self.assertIsNone(self.mem.get("nope"))

    def test_has(self):
        self.mem.store("decision", "k", "v")
        self.assertTrue(self.mem.has("k"))
        self.assertFalse(self.mem.has("x"))

    def test_recall_by_type(self):
        self.mem.store("decision", "d1", "v1")
        self.mem.store("pattern", "p1", "v2")
        decisions = self.mem.recall("decision")
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].key, "d1")

    def test_recall_by_query(self):
        self.mem.store("decision", "sales_sum", "SUM(Sales)")
        self.mem.store("decision", "profit_avg", "AVERAGE(Profit)")
        results = self.mem.recall(query="sales")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].key, "sales_sum")

    def test_recall_min_confidence(self):
        self.mem.store("decision", "k1", "v1", confidence=0.9)
        self.mem.store("decision", "k2", "v2", confidence=0.3)
        results = self.mem.recall(min_confidence=0.5)
        self.assertEqual(len(results), 1)

    def test_recall_limit(self):
        for i in range(20):
            self.mem.store("decision", f"k{i}", f"v{i}")
        results = self.mem.recall(limit=5)
        self.assertEqual(len(results), 5)

    def test_forget(self):
        self.mem.store("decision", "k", "v")
        self.assertTrue(self.mem.forget("k"))
        self.assertFalse(self.mem.has("k"))
        self.assertFalse(self.mem.forget("nope"))

    def test_clear_all(self):
        self.mem.store("decision", "k1", "v1")
        self.mem.store("pattern", "k2", "v2")
        count = self.mem.clear()
        self.assertEqual(count, 2)
        self.assertEqual(self.mem.size, 0)

    def test_clear_by_type(self):
        self.mem.store("decision", "k1", "v1")
        self.mem.store("pattern", "k2", "v2")
        count = self.mem.clear("decision")
        self.assertEqual(count, 1)
        self.assertEqual(self.mem.size, 1)

    def test_prune_expired(self):
        self.mem.store("decision", "k1", "v1", ttl_seconds=0.01)
        self.mem.store("decision", "k2", "v2")  # no expiry
        time.sleep(0.02)
        pruned = self.mem.prune_expired()
        self.assertEqual(pruned, 1)
        self.assertEqual(self.mem.size, 1)

    def test_eviction_at_max_entries(self):
        mem = AgentMemory("a", max_entries=3)
        mem.store("d", "k1", "v1")
        mem.store("d", "k2", "v2")
        mem.store("d", "k3", "v3")
        mem.store("d", "k4", "v4")  # triggers eviction
        self.assertEqual(mem.size, 3)

    def test_export_and_import(self):
        self.mem.store("decision", "k1", "v1", confidence=0.9)
        self.mem.store("pattern", "k2", "v2")
        rows = self.mem.export_all()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("agent_id" in r for r in rows))

        mem2 = AgentMemory("04-semantic")
        count = mem2.import_entries(rows)
        self.assertEqual(count, 2)
        self.assertEqual(mem2.get("k1").value, "v1")

    def test_count_by_type(self):
        self.mem.store("decision", "k1", "v1")
        self.mem.store("decision", "k2", "v2")
        self.mem.store("error", "k3", "v3")
        counts = self.mem.count_by_type()
        self.assertEqual(counts["decision"], 2)
        self.assertEqual(counts["error"], 1)

    def test_access_count_incremented(self):
        self.mem.store("decision", "k", "v")
        self.mem.get("k")
        self.mem.get("k")
        self.assertEqual(self.mem.get("k").access_count, 3)


# ---------------------------------------------------------------------------
# PromptBuilder tests
# ---------------------------------------------------------------------------


class TestPromptBuilder(unittest.TestCase):

    def test_default_role(self):
        builder = PromptBuilder(agent_id="04-semantic")
        self.assertIn("Semantic Model Agent", builder.agent_role)

    def test_custom_role(self):
        builder = PromptBuilder(agent_id="04-semantic", agent_role="Custom role")
        self.assertEqual(builder.agent_role, "Custom role")

    def test_build_basic(self):
        builder = PromptBuilder(agent_id="04-semantic")
        system, user = builder.build(task="translate", source="@SUM(Sales)")
        self.assertIn("translate", system)
        self.assertIn("@SUM(Sales)", user)
        self.assertIn("Input", user)

    def test_build_with_context(self):
        builder = PromptBuilder(agent_id="04-semantic")
        _, user = builder.build(
            task="translate",
            source="@SUM(Sales)",
            context={"target": "DAX", "model": "SalesModel"},
        )
        self.assertIn("target: DAX", user)
        self.assertIn("model: SalesModel", user)

    def test_build_with_few_shots(self):
        builder = PromptBuilder(agent_id="04-semantic")
        _, user = builder.build(
            task="translate",
            source="@SUM(Cost)",
            few_shots=[FewShotExample(source="@SUM(Sales)", target="SUM(Fact[Sales])")],
        )
        self.assertIn("Examples", user)
        self.assertIn("@SUM(Sales)", user)
        self.assertIn("SUM(Fact[Sales])", user)

    def test_build_with_memory(self):
        builder = PromptBuilder(agent_id="04-semantic")
        _, user = builder.build(
            task="translate",
            source="@AVG(Profit)",
            memory_entries=[{"key": "@SUM(Revenue)", "value": "SUM(Fact[Revenue])", "confidence": 0.95}],
        )
        self.assertIn("Prior Decisions", user)
        self.assertIn("@SUM(Revenue)", user)

    def test_negative_examples(self):
        builder = PromptBuilder(agent_id="04-semantic")
        builder.add_negative_example("WRONG: SUM([sales])")
        system, _ = builder.build(task="translate", source="@SUM(Sales)")
        self.assertIn("WRONG: SUM([sales])", system)
        self.assertIn("DO NOT repeat", system)

    def test_constraints(self):
        builder = PromptBuilder(agent_id="04-semantic")
        system, _ = builder.build(
            task="translate", source="test",
            constraints=["Use DIVIDE() instead of /"],
        )
        self.assertIn("Use DIVIDE() instead of /", system)

    def test_truncation(self):
        builder = PromptBuilder(agent_id="04-semantic", max_context_tokens=50)
        _, user = builder.build(task="t", source="x" * 10_000)
        # User prompt should be truncated and contain the marker
        self.assertIn("truncated", user)

    def test_estimate_tokens(self):
        builder = PromptBuilder(agent_id="04-semantic")
        tokens = builder.estimate_tokens("system" * 100, "user" * 100)
        self.assertGreater(tokens, 0)

    def test_all_agents_have_roles(self):
        """Every agent ID in AGENT_ROLES maps to a non-empty string."""
        for agent_id, role in AGENT_ROLES.items():
            self.assertIn("-", agent_id)
            self.assertTrue(len(role) > 20, f"Role for {agent_id} is too short")


# ---------------------------------------------------------------------------
# ReasoningLoop tests
# ---------------------------------------------------------------------------


@dataclass
class MockLLMResponse:
    content: str
    total_tokens: int = 50
    latency_ms: float = 10.0


class TestReasoningStep(unittest.TestCase):

    def test_to_dict(self):
        s = ReasoningStep(step_type=StepType.THOUGHT, content="thinking")
        d = s.to_dict()
        self.assertEqual(d["type"], "thought")
        self.assertEqual(d["content"], "thinking")


class TestReasoningResult(unittest.TestCase):

    def test_step_count(self):
        r = ReasoningResult(steps=[
            ReasoningStep(step_type=StepType.THOUGHT, content="a"),
            ReasoningStep(step_type=StepType.FINAL, content="b"),
        ])
        self.assertEqual(r.step_count, 2)

    def test_to_dict(self):
        r = ReasoningResult(output="result", success=True, confidence=0.9)
        d = r.to_dict()
        self.assertTrue(d["success"])
        self.assertAlmostEqual(d["confidence"], 0.9)


class TestReasoningLoopParsing(unittest.TestCase):
    """Test the static _parse_response method."""

    def test_parse_thought_and_final(self):
        content = "Thought: I should translate this\nFinal Answer: SUM(Sales[Amount])\nConfidence: 0.95"
        steps = ReasoningLoop._parse_response(content)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].step_type, StepType.THOUGHT)
        self.assertEqual(steps[1].step_type, StepType.FINAL)
        self.assertEqual(steps[1].content, "SUM(Sales[Amount])")

    def test_parse_action(self):
        content = (
            "Thought: Need to look up the table\n"
            "Action: translate_expression\n"
            'Action Input: {"expression": "@SUM(Sales)"}\n'
        )
        steps = ReasoningLoop._parse_response(content)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[1].step_type, StepType.ACTION)
        self.assertEqual(steps[1].tool_name, "translate_expression")
        self.assertEqual(steps[1].tool_args["expression"], "@SUM(Sales)")

    def test_parse_plain_text_as_final(self):
        """Unstructured response becomes a single FINAL step."""
        steps = ReasoningLoop._parse_response("SUM(Sales[Amount])")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].step_type, StepType.FINAL)

    def test_extract_confidence(self):
        c = ReasoningLoop._extract_confidence("something\nConfidence: 0.85\nend")
        self.assertAlmostEqual(c, 0.85)

    def test_extract_confidence_default(self):
        c = ReasoningLoop._extract_confidence("no confidence here")
        self.assertAlmostEqual(c, 0.8)

    def test_extract_confidence_clamped(self):
        c = ReasoningLoop._extract_confidence("Confidence: 1.5")
        self.assertAlmostEqual(c, 1.0)


class TestReasoningLoopExecution(unittest.TestCase):
    """Test the full ReAct loop with mock LLM."""

    def _make_loop(self, responses: list[str]) -> ReasoningLoop:
        """Create a loop with a mock LLM that returns predefined responses."""
        responses_iter = iter(responses)

        async def mock_llm(system: str, user: str, **kw) -> MockLLMResponse:
            return MockLLMResponse(content=next(responses_iter))

        builder = PromptBuilder(agent_id="04-semantic")
        tools = ToolRegistry()
        tools.register(ToolDefinition(
            name="lookup",
            description="Look up a value",
            parameters={"key": ToolParameter()},
            handler=lambda key: f"found:{key}",
        ))

        return ReasoningLoop(
            llm_complete=mock_llm,
            tool_registry=tools,
            prompt_builder=builder,
            agent_id="04-semantic",
            max_iterations=5,
        )

    def test_single_final_answer(self):
        loop = self._make_loop(["Final Answer: SUM(Sales[Amount])\nConfidence: 0.9"])
        result = _run(loop.run("translate", "@SUM(Sales)"))
        self.assertTrue(result.success)
        self.assertEqual(result.output, "SUM(Sales[Amount])")
        self.assertAlmostEqual(result.confidence, 0.9)
        self.assertEqual(result.iterations, 1)

    def test_unstructured_response(self):
        loop = self._make_loop(["SUM(Sales[Amount])"])
        result = _run(loop.run("translate", "@SUM(Sales)"))
        self.assertTrue(result.success)

    def test_tool_call_then_final(self):
        loop = self._make_loop([
            "Thought: Look up the mapping\nAction: lookup\nAction Input: {\"key\": \"Sales\"}\n",
            "Final Answer: SUM(Sales[Amount])\nConfidence: 0.95",
        ])
        result = _run(loop.run("translate", "@SUM(Sales)"))
        self.assertTrue(result.success)
        self.assertGreater(result.iterations, 1)
        # Should have: thought, action, observation, final
        types = [s.step_type for s in result.steps]
        self.assertIn(StepType.ACTION, types)
        self.assertIn(StepType.OBSERVATION, types)
        self.assertIn(StepType.FINAL, types)

    def test_max_iterations_stops(self):
        # LLM never gives a final answer
        responses = ["Thought: still thinking\n"] * 10

        async def mock_llm(s, u, **kw):
            return MockLLMResponse(content=responses.pop(0) if responses else "done")

        builder = PromptBuilder(agent_id="04-semantic")
        loop = ReasoningLoop(
            llm_complete=mock_llm,
            tool_registry=ToolRegistry(),
            prompt_builder=builder,
            max_iterations=3,
        )
        result = _run(loop.run("translate", "@SUM(Sales)"))
        self.assertLessEqual(result.iterations, 3)

    def test_budget_exhausted(self):
        cc = CostController(default_budget=10)
        cc.record("04-semantic", 10)  # exhaust budget

        async def mock_llm(s, u, **kw):
            return MockLLMResponse(content="Final Answer: x")

        loop = ReasoningLoop(
            llm_complete=mock_llm,
            tool_registry=ToolRegistry(),
            prompt_builder=PromptBuilder(agent_id="04-semantic"),
            cost_controller=cc,
            agent_id="04-semantic",
        )
        result = _run(loop.run("translate", "test"))
        self.assertFalse(result.success)
        self.assertIn("budget", result.error.lower())

    def test_llm_failure(self):
        async def bad_llm(s, u, **kw):
            raise ConnectionError("LLM down")

        loop = ReasoningLoop(
            llm_complete=bad_llm,
            tool_registry=ToolRegistry(),
            prompt_builder=PromptBuilder(agent_id="04-semantic"),
        )
        result = _run(loop.run("translate", "test"))
        self.assertFalse(result.success)
        self.assertIn("LLM", result.error)

    def test_memory_integration(self):
        mem = AgentMemory("04-semantic")
        mem.store("decision", "@SUM(Sales)", "SUM(Sales[Amount])", confidence=0.95)

        loop = self._make_loop(["Final Answer: SUM(Cost[Amount])\nConfidence: 0.9"])
        loop._memory = mem
        result = _run(loop.run("translate", "@SUM(Cost)"))
        self.assertTrue(result.success)
        # The new decision should be stored in memory
        self.assertTrue(mem.has("@SUM(Cost)"))

    def test_tokens_tracked(self):
        loop = self._make_loop(["Final Answer: result"])
        result = _run(loop.run("translate", "test"))
        self.assertGreater(result.total_tokens, 0)


# ---------------------------------------------------------------------------
# IntelligentMixin tests
# ---------------------------------------------------------------------------


class DummyAgent(IntelligentMixin, MigrationAgent):
    """Minimal agent for testing the mixin."""

    async def discover(self, scope: MigrationScope) -> Inventory:
        return Inventory()

    async def plan(self, inventory: Inventory) -> MigrationPlan:
        return MigrationPlan(agent_id=self.agent_id)

    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        return MigrationResult(agent_id=self.agent_id)

    async def validate(self, result: MigrationResult) -> ValidationReport:
        return ValidationReport(agent_id=self.agent_id)


class TestIntelligentMixin(unittest.TestCase):

    def test_has_intelligence_false_by_default(self):
        agent = DummyAgent("04-semantic", "Test Agent")
        self.assertFalse(agent.has_intelligence)

    def test_attach_intelligence(self):
        agent = DummyAgent("04-semantic", "Test Agent")

        async def mock_llm(s, u, **kw):
            return MockLLMResponse(content="Final Answer: done\nConfidence: 0.9")

        builder = PromptBuilder(agent_id="04-semantic")
        tools = ToolRegistry()
        memory = AgentMemory("04-semantic")
        cc = CostController()

        loop = ReasoningLoop(
            llm_complete=mock_llm,
            tool_registry=tools,
            prompt_builder=builder,
            agent_memory=memory,
            cost_controller=cc,
            agent_id="04-semantic",
        )

        agent.attach_intelligence(loop, memory, cc)
        self.assertTrue(agent.has_intelligence)

    def test_reason_without_intelligence(self):
        agent = DummyAgent("04-semantic", "Test Agent")
        result = _run(agent.reason("translate", "@SUM(Sales)"))
        self.assertIsNone(result)

    def test_reason_with_intelligence(self):
        agent = DummyAgent("04-semantic", "Test Agent")

        async def mock_llm(s, u, **kw):
            return MockLLMResponse(content="Final Answer: SUM(Sales[Amount])\nConfidence: 0.85")

        builder = PromptBuilder(agent_id="04-semantic")
        loop = ReasoningLoop(
            llm_complete=mock_llm,
            tool_registry=ToolRegistry(),
            prompt_builder=builder,
        )
        agent.attach_intelligence(loop)
        result = _run(agent.reason("translate", "@SUM(Sales)"))
        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.output, "SUM(Sales[Amount])")

    def test_remember_and_recall(self):
        agent = DummyAgent("04-semantic", "Test Agent")
        mem = AgentMemory("04-semantic")
        agent.attach_intelligence(reasoning_loop=None, agent_memory=mem)

        agent.remember("decision", "key1", "val1", confidence=0.9)
        results = agent.recall_memory("decision", query="key1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].value, "val1")

    def test_recall_without_memory(self):
        agent = DummyAgent("04-semantic", "Test Agent")
        results = agent.recall_memory("decision")
        self.assertEqual(results, [])

    def test_agent_lifecycle_still_works(self):
        """IntelligentMixin does not break the base agent lifecycle."""
        agent = DummyAgent("04-semantic", "Test Agent")
        scope = MigrationScope()
        report = _run(agent.run(scope))
        self.assertIsNotNone(report)


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestIntelligenceConfig(unittest.TestCase):

    def test_defaults(self):
        from src.core.config import Settings
        s = Settings()
        self.assertFalse(s.intelligence_enabled)
        self.assertEqual(s.intelligence_model, "gpt-4.1")
        self.assertEqual(s.intelligence_max_iterations, 10)
        self.assertEqual(s.intelligence_default_token_budget, 500_000)


if __name__ == "__main__":
    unittest.main()
