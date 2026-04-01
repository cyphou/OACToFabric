"""Intelligence layer — LLM reasoning, agent memory, tool use, and cost control.

Phase 70 of the OAC-to-Fabric migration platform.  Provides the shared
infrastructure that upgrades deterministic agents into LLM-powered
autonomous agents while keeping the existing rule engines as the fast path.

Modules
-------
- ``tool_registry``   — Typed tool definitions exposed to the LLM.
- ``cost_controller``  — Per-agent token budgets, caching, cost logging.
- ``agent_memory``     — Persistent per-agent memory (decisions, patterns).
- ``prompt_builder``   — Domain-specific prompt construction with context management.
- ``reasoning_loop``   — ReAct (Reason + Act) loop wrapping agent tasks.
"""

from src.core.intelligence.agent_memory import AgentMemory, MemoryEntry
from src.core.intelligence.cost_controller import CostController, CostSummary, SemanticCache
from src.core.intelligence.prompt_builder import FewShotExample, PromptBuilder
from src.core.intelligence.reasoning_loop import ReasoningLoop, ReasoningResult, ReasoningStep
from src.core.intelligence.tool_registry import ToolDefinition, ToolParameter, ToolRegistry, ToolResult

__all__ = [
    "AgentMemory",
    "CostController",
    "CostSummary",
    "FewShotExample",
    "MemoryEntry",
    "PromptBuilder",
    "ReasoningLoop",
    "ReasoningResult",
    "ReasoningStep",
    "SemanticCache",
    "ToolDefinition",
    "ToolParameter",
    "ToolRegistry",
    "ToolResult",
]
