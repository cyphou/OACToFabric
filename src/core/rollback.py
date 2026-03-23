"""Migration rollback engine.

Provides:
- ``ActionType`` — types of recorded migration actions.
- ``RecordedAction`` — a single reversible migration action.
- ``ActionLog`` — append-only log of all actions in a migration.
- ``RollbackPlan`` — plan listing actions to reverse.
- ``RollbackResult`` — outcome of a rollback execution.
- ``RollbackEngine`` — reverse agent actions using the action log.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action types
# ---------------------------------------------------------------------------


class ActionType(str, Enum):
    """Types of reversible migration actions."""

    SCHEMA_CREATE_TABLE = "schema_create_table"
    SCHEMA_ALTER_TABLE = "schema_alter_table"
    SCHEMA_DROP_TABLE = "schema_drop_table"
    SEMANTIC_DEPLOY_MODEL = "semantic_deploy_model"
    SEMANTIC_UPDATE_MODEL = "semantic_update_model"
    REPORT_DEPLOY = "report_deploy"
    REPORT_UPDATE = "report_update"
    SECURITY_SET_RLS = "security_set_rls"
    SECURITY_SET_OLS = "security_set_ols"
    PIPELINE_CREATE = "pipeline_create"
    PIPELINE_UPDATE = "pipeline_update"
    DATA_LOAD = "data_load"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Recorded action
# ---------------------------------------------------------------------------


@dataclass
class RecordedAction:
    """A single reversible migration action."""

    action_id: str
    action_type: ActionType
    agent_id: str
    migration_id: str
    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    forward_payload: dict[str, Any] = field(default_factory=dict)
    reverse_payload: dict[str, Any] = field(default_factory=dict)
    artifact_version: int = 0  # version before this action was applied
    is_reversed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "agent_id": self.agent_id,
            "migration_id": self.migration_id,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "artifact_version": self.artifact_version,
            "is_reversed": self.is_reversed,
        }


# ---------------------------------------------------------------------------
# Action log
# ---------------------------------------------------------------------------


class ActionLog:
    """Append-only log of all actions in a migration."""

    def __init__(self, migration_id: str) -> None:
        self.migration_id = migration_id
        self._actions: list[RecordedAction] = []

    def record(
        self,
        action_type: ActionType,
        agent_id: str,
        description: str,
        forward_payload: dict[str, Any] | None = None,
        reverse_payload: dict[str, Any] | None = None,
        artifact_version: int = 0,
    ) -> RecordedAction:
        action = RecordedAction(
            action_id=uuid.uuid4().hex[:12],
            action_type=action_type,
            agent_id=agent_id,
            migration_id=self.migration_id,
            description=description,
            forward_payload=forward_payload or {},
            reverse_payload=reverse_payload or {},
            artifact_version=artifact_version,
        )
        self._actions.append(action)
        logger.info("Action recorded: %s — %s", action.action_type.value, description)
        return action

    @property
    def actions(self) -> list[RecordedAction]:
        return list(self._actions)

    @property
    def count(self) -> int:
        return len(self._actions)

    def get_by_agent(self, agent_id: str) -> list[RecordedAction]:
        return [a for a in self._actions if a.agent_id == agent_id]

    def get_reversible(self) -> list[RecordedAction]:
        """Return actions that haven't been reversed, in reverse order."""
        return [a for a in reversed(self._actions) if not a.is_reversed]

    def get_actions_after(self, action_id: str) -> list[RecordedAction]:
        """Return all actions after the given action_id (inclusive), reversed."""
        found = False
        result = []
        for a in self._actions:
            if a.action_id == action_id:
                found = True
            if found and not a.is_reversed:
                result.append(a)
        return list(reversed(result))


# ---------------------------------------------------------------------------
# Rollback plan
# ---------------------------------------------------------------------------


@dataclass
class RollbackPlan:
    """A plan listing actions to reverse."""

    migration_id: str
    actions_to_reverse: list[RecordedAction] = field(default_factory=list)
    target_version: int | None = None  # rollback to this artifact version
    description: str = ""
    dry_run: bool = False

    @property
    def action_count(self) -> int:
        return len(self.actions_to_reverse)

    def summary(self) -> str:
        types = [a.action_type.value for a in self.actions_to_reverse]
        return (
            f"Rollback plan for migration {self.migration_id}: "
            f"{self.action_count} actions to reverse — {types}"
        )


# ---------------------------------------------------------------------------
# Rollback result
# ---------------------------------------------------------------------------


@dataclass
class RollbackStepResult:
    """Result of rolling back a single action."""

    action_id: str
    action_type: ActionType
    success: bool
    error: str = ""


@dataclass
class RollbackResult:
    """Outcome of a rollback execution."""

    migration_id: str
    steps: list[RollbackStepResult] = field(default_factory=list)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def succeeded(self) -> int:
        return sum(1 for s in self.steps if s.success)

    @property
    def failed(self) -> int:
        return sum(1 for s in self.steps if not s.success)

    @property
    def all_succeeded(self) -> bool:
        return all(s.success for s in self.steps) and self.total > 0

    def summary(self) -> str:
        return (
            f"Rollback {self.migration_id}: "
            f"{self.succeeded}/{self.total} succeeded, {self.failed} failed"
        )


# ---------------------------------------------------------------------------
# Rollback engine
# ---------------------------------------------------------------------------


class RollbackEngine:
    """Reverse agent actions using the action log.

    Each action type has a corresponding reverse handler. In the real
    system, handlers call Fabric/PBI APIs. This implementation provides
    the framework and a mock mode for testing.
    """

    def __init__(self, *, mock_mode: bool = True) -> None:
        self._mock_mode = mock_mode

    def plan_full_rollback(self, action_log: ActionLog) -> RollbackPlan:
        """Plan reversal of all reversible actions."""
        return RollbackPlan(
            migration_id=action_log.migration_id,
            actions_to_reverse=action_log.get_reversible(),
            description="Full rollback of all reversible actions",
        )

    def plan_rollback_to(self, action_log: ActionLog, action_id: str) -> RollbackPlan:
        """Plan reversal of all actions after (and including) the given action."""
        actions = action_log.get_actions_after(action_id)
        return RollbackPlan(
            migration_id=action_log.migration_id,
            actions_to_reverse=actions,
            description=f"Rollback to action {action_id}",
        )

    async def execute(self, plan: RollbackPlan, action_log: ActionLog) -> RollbackResult:
        """Execute a rollback plan."""
        result = RollbackResult(migration_id=plan.migration_id)

        if plan.dry_run:
            for action in plan.actions_to_reverse:
                result.steps.append(RollbackStepResult(
                    action_id=action.action_id,
                    action_type=action.action_type,
                    success=True,
                    error="dry-run — no changes made",
                ))
            return result

        for action in plan.actions_to_reverse:
            step_result = await self._reverse_action(action)
            result.steps.append(step_result)

            if step_result.success:
                action.is_reversed = True
            else:
                logger.error(
                    "Rollback step failed: %s — %s",
                    action.action_id,
                    step_result.error,
                )
                # Continue with remaining actions (best effort)

        logger.info(result.summary())
        return result

    async def _reverse_action(self, action: RecordedAction) -> RollbackStepResult:
        """Reverse a single action."""
        if self._mock_mode:
            return RollbackStepResult(
                action_id=action.action_id,
                action_type=action.action_type,
                success=True,
            )

        # Real implementation would dispatch to appropriate handler
        handler = self._get_handler(action.action_type)
        if handler is None:
            return RollbackStepResult(
                action_id=action.action_id,
                action_type=action.action_type,
                success=False,
                error=f"No handler for action type: {action.action_type.value}",
            )

        try:
            await handler(action)
            return RollbackStepResult(
                action_id=action.action_id,
                action_type=action.action_type,
                success=True,
            )
        except Exception as exc:
            return RollbackStepResult(
                action_id=action.action_id,
                action_type=action.action_type,
                success=False,
                error=str(exc),
            )

    def _get_handler(self, action_type: ActionType) -> Any:
        """Get the reverse handler for an action type.

        Returns None for unimplemented types.
        """
        # Real handlers would be registered here
        return None
