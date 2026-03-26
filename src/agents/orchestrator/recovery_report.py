"""Recovery report — tracks self-healing actions and recovery outcomes.

Records every auto-repair, retry, and fallback that occurred during
migration execution. Generates a structured report for post-migration
review.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RecoveryActionType(str, Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    SELF_HEAL = "self_heal"
    SKIP = "skip"
    MANUAL_REQUIRED = "manual_required"


class RecoveryOutcome(str, Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


@dataclass
class RecoveryAction:
    """A single recovery action taken during migration."""

    agent_id: str
    asset_id: str
    action_type: RecoveryActionType
    description: str
    outcome: RecoveryOutcome = RecoveryOutcome.RESOLVED
    original_error: str = ""
    resolution: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempt: int = 1


@dataclass
class RecoveryReport:
    """Aggregated recovery report."""

    actions: list[RecoveryAction] = field(default_factory=list)

    @property
    def total_actions(self) -> int:
        return len(self.actions)

    @property
    def resolved_count(self) -> int:
        return sum(1 for a in self.actions if a.outcome == RecoveryOutcome.RESOLVED)

    @property
    def unresolved_count(self) -> int:
        return sum(1 for a in self.actions if a.outcome == RecoveryOutcome.UNRESOLVED)

    @property
    def by_agent(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self.actions:
            counts[a.agent_id] = counts.get(a.agent_id, 0) + 1
        return counts

    @property
    def by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self.actions:
            counts[a.action_type.value] = counts.get(a.action_type.value, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


class RecoveryTracker:
    """Accumulates recovery actions during a migration run."""

    def __init__(self) -> None:
        self._actions: list[RecoveryAction] = []

    def record(
        self,
        agent_id: str,
        asset_id: str,
        action_type: RecoveryActionType,
        description: str,
        *,
        outcome: RecoveryOutcome = RecoveryOutcome.RESOLVED,
        original_error: str = "",
        resolution: str = "",
        attempt: int = 1,
    ) -> RecoveryAction:
        """Record a recovery action."""
        action = RecoveryAction(
            agent_id=agent_id,
            asset_id=asset_id,
            action_type=action_type,
            description=description,
            outcome=outcome,
            original_error=original_error,
            resolution=resolution,
            attempt=attempt,
        )
        self._actions.append(action)
        logger.info(
            "Recovery [%s] %s/%s: %s → %s",
            action_type.value, agent_id, asset_id, description, outcome.value,
        )
        return action

    def record_retry(
        self,
        agent_id: str,
        asset_id: str,
        error: str,
        attempt: int,
        resolved: bool = True,
    ) -> RecoveryAction:
        """Convenience: record a retry action."""
        return self.record(
            agent_id=agent_id,
            asset_id=asset_id,
            action_type=RecoveryActionType.RETRY,
            description=f"Retry attempt {attempt}",
            outcome=RecoveryOutcome.RESOLVED if resolved else RecoveryOutcome.UNRESOLVED,
            original_error=error,
            resolution="Succeeded on retry" if resolved else "Max retries exhausted",
            attempt=attempt,
        )

    def record_self_heal(
        self,
        agent_id: str,
        asset_id: str,
        description: str,
        resolution: str,
    ) -> RecoveryAction:
        """Convenience: record a self-healing action."""
        return self.record(
            agent_id=agent_id,
            asset_id=asset_id,
            action_type=RecoveryActionType.SELF_HEAL,
            description=description,
            resolution=resolution,
        )

    def build_report(self) -> RecoveryReport:
        """Build an aggregated recovery report."""
        report = RecoveryReport(actions=list(self._actions))
        logger.info(
            "Recovery report: %d actions (%d resolved, %d unresolved)",
            report.total_actions,
            report.resolved_count,
            report.unresolved_count,
        )
        return report


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_recovery_report(report: RecoveryReport) -> dict[str, Any]:
    """Render recovery report as a JSON-serialisable dict."""
    return {
        "total_actions": report.total_actions,
        "resolved": report.resolved_count,
        "unresolved": report.unresolved_count,
        "by_agent": report.by_agent,
        "by_type": report.by_type,
        "actions": [
            {
                "agent_id": a.agent_id,
                "asset_id": a.asset_id,
                "type": a.action_type.value,
                "description": a.description,
                "outcome": a.outcome.value,
                "original_error": a.original_error,
                "resolution": a.resolution,
                "attempt": a.attempt,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in report.actions
        ],
    }


def save_recovery_report(
    report: RecoveryReport,
    output_path: str | Path = "output/recovery_report.json",
) -> Path:
    """Save the recovery report to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = render_recovery_report(report)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Recovery report saved to %s", path)
    return path
