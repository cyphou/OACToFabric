"""Base agent class — all migration agents inherit from this."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from src.core.models import (
    AgentState,
    Inventory,
    MigrationPlan,
    MigrationResult,
    MigrationScope,
    RollbackResult,
    ValidationReport,
)

logger = logging.getLogger(__name__)


class MigrationAgent(ABC):
    """Abstract base for every migration agent."""

    agent_id: str
    agent_name: str

    def __init__(self, agent_id: str, agent_name: str) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self._state = AgentState.IDLE
        self._started_at: datetime | None = None

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    @property
    def state(self) -> AgentState:
        return self._state

    def _set_state(self, state: AgentState) -> None:
        logger.info("[%s] State: %s → %s", self.agent_id, self._state.value, state.value)
        self._state = state

    # ------------------------------------------------------------------
    # Lifecycle — run the full discover → plan → execute → validate cycle
    # ------------------------------------------------------------------

    async def run(self, scope: MigrationScope) -> ValidationReport:
        """Execute the full agent lifecycle."""
        self._started_at = datetime.now(timezone.utc)
        try:
            # Discover
            self._set_state(AgentState.DISCOVERING)
            inventory = await self.discover(scope)
            logger.info("[%s] Discovered %d items", self.agent_id, inventory.count)

            # Plan
            self._set_state(AgentState.PLANNING)
            plan = await self.plan(inventory)
            logger.info("[%s] Plan contains %d items", self.agent_id, len(plan.items))

            # Execute
            self._set_state(AgentState.EXECUTING)
            result = await self.execute(plan)
            logger.info(
                "[%s] Execution: %d succeeded, %d failed, %d skipped",
                self.agent_id,
                result.succeeded,
                result.failed,
                result.skipped,
            )

            # Validate
            self._set_state(AgentState.VALIDATING)
            report = await self.validate(result)
            logger.info(
                "[%s] Validation: %d/%d passed",
                self.agent_id,
                report.passed,
                report.total_checks,
            )

            self._set_state(AgentState.DONE)
            return report

        except Exception:
            self._set_state(AgentState.FAILED)
            logger.exception("[%s] Agent failed", self.agent_id)
            raise

    # ------------------------------------------------------------------
    # Abstract methods — each agent must implement these
    # ------------------------------------------------------------------

    @abstractmethod
    async def discover(self, scope: MigrationScope) -> Inventory:
        """Discover source assets within the given scope."""
        ...

    @abstractmethod
    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """Generate a migration plan from the inventory."""
        ...

    @abstractmethod
    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Execute the migration plan."""
        ...

    @abstractmethod
    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Validate the migration result against the source."""
        ...

    async def rollback(self, result: MigrationResult) -> RollbackResult:
        """Rollback a failed migration (optional override)."""
        logger.warning("[%s] Rollback not implemented", self.agent_id)
        return RollbackResult(agent_id=self.agent_id)


# ---------------------------------------------------------------------------
# Intelligence mixin — Phase 70
# ---------------------------------------------------------------------------


class IntelligentMixin:
    """Mixin that adds LLM reasoning, memory, and tool-use to any agent.

    Injected optionally — agents work without it (rule-only mode).
    When attached, agents can use ``self.reason()`` to invoke the
    ReAct reasoning loop for tasks that rules can't handle.

    Usage::

        class SemanticAgent(IntelligentMixin, MigrationAgent):
            ...
            async def execute(self, plan):
                for item in plan.items:
                    rule_result = self.rules.translate(item)
                    if rule_result.confidence < 0.7:
                        ai_result = await self.reason(
                            task="translate_expression",
                            source=item.expression,
                        )
                        ...
    """

    _reasoning_loop: Any
    _agent_memory: Any
    _cost_controller: Any

    def attach_intelligence(
        self,
        reasoning_loop: Any,
        agent_memory: Any | None = None,
        cost_controller: Any | None = None,
    ) -> None:
        """Attach the intelligence layer to this agent.

        Parameters
        ----------
        reasoning_loop
            A ``ReasoningLoop`` instance.
        agent_memory
            An ``AgentMemory`` instance (optional).
        cost_controller
            A ``CostController`` instance (optional).
        """
        self._reasoning_loop = reasoning_loop
        self._agent_memory = agent_memory
        self._cost_controller = cost_controller

    @property
    def has_intelligence(self) -> bool:
        """Check if the intelligence layer is attached."""
        return hasattr(self, "_reasoning_loop") and self._reasoning_loop is not None

    async def reason(
        self,
        task: str,
        source: str,
        *,
        context: dict[str, Any] | None = None,
        few_shots: list[Any] | None = None,
    ) -> Any:
        """Invoke the LLM reasoning loop for a task.

        Returns the ``ReasoningResult`` from the loop, or *None* if
        intelligence is not attached.
        """
        if not self.has_intelligence:
            return None
        return await self._reasoning_loop.run(
            task=task,
            source=source,
            context=context,
            few_shots=few_shots,
        )

    def remember(
        self,
        entry_type: str,
        key: str,
        value: Any,
        *,
        confidence: float = 1.0,
    ) -> None:
        """Store a memory entry (no-op if memory not attached)."""
        if hasattr(self, "_agent_memory") and self._agent_memory is not None:
            self._agent_memory.store(entry_type, key, value, confidence=confidence)

    def recall_memory(
        self,
        entry_type: str | None = None,
        *,
        query: str = "",
        limit: int = 10,
    ) -> list[Any]:
        """Recall from agent memory (empty list if not attached)."""
        if hasattr(self, "_agent_memory") and self._agent_memory is not None:
            return self._agent_memory.recall(entry_type, query=query, limit=limit)
        return []
