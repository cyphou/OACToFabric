"""Base agent class — all migration agents inherit from this."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

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
