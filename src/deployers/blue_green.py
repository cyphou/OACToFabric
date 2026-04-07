"""Blue/Green semantic-model swap for zero-downtime deployment.

Strategy
--------
1. Deploy the new semantic model to a *staging* slot (green).
2. Run validation (row counts, DAX checks, TMDL validation).
3. If validation passes, swap green → live and demote the old live → staging.
4. If validation fails, roll back by keeping the original live in place.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SlotLabel(str, Enum):
    LIVE = "live"
    STAGING = "staging"


class SwapOutcome(str, Enum):
    SWAPPED = "swapped"
    ROLLED_BACK = "rolled_back"
    VALIDATION_FAILED = "validation_failed"
    FAILED = "failed"
    DRY_RUN = "dry_run"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SlotInfo:
    """Metadata for one deployment slot."""

    slot: SlotLabel
    artifact_id: str = ""
    artifact_name: str = ""
    version: int = 0
    deployed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    healthy: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot.value,
            "artifact_id": self.artifact_id,
            "artifact_name": self.artifact_name,
            "version": self.version,
            "deployed_at": self.deployed_at.isoformat(),
            "healthy": self.healthy,
            "metadata": self.metadata,
        }


@dataclass
class ValidationGate:
    """A single validation check that must pass before swap."""

    name: str
    passed: bool = False
    message: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "duration_ms": self.duration_ms,
        }


@dataclass
class SwapResult:
    """Outcome of a blue/green swap attempt."""

    outcome: SwapOutcome
    live_before: SlotInfo | None = None
    live_after: SlotInfo | None = None
    validation_gates: list[ValidationGate] = field(default_factory=list)
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        return self.outcome == SwapOutcome.SWAPPED

    @property
    def all_gates_passed(self) -> bool:
        return all(g.passed for g in self.validation_gates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "live_before": self.live_before.to_dict() if self.live_before else None,
            "live_after": self.live_after.to_dict() if self.live_after else None,
            "validation_gates": [g.to_dict() for g in self.validation_gates],
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }

    def summary(self) -> str:
        gates_str = ", ".join(
            f"{g.name}={'PASS' if g.passed else 'FAIL'}" for g in self.validation_gates
        )
        return (
            f"Swap {self.outcome.value}: "
            f"gates=[{gates_str}], "
            f"live_before={self.live_before.artifact_name if self.live_before else '—'}, "
            f"live_after={self.live_after.artifact_name if self.live_after else '—'}"
        )


# ---------------------------------------------------------------------------
# Blue/Green Manager
# ---------------------------------------------------------------------------


@dataclass
class BlueGreenManager:
    """Manage blue/green deployment slots for semantic models.

    Parameters
    ----------
    workspace_id
        Fabric workspace ID.
    dry_run
        If *True*, do not execute real swaps.
    """

    workspace_id: str
    dry_run: bool = False
    _slots: dict[SlotLabel, SlotInfo] = field(default_factory=dict, repr=False)
    _history: list[SwapResult] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------
    # Slot management
    # ------------------------------------------------------------------

    def set_slot(self, info: SlotInfo) -> None:
        self._slots[info.slot] = info

    def get_slot(self, label: SlotLabel) -> SlotInfo | None:
        return self._slots.get(label)

    @property
    def live(self) -> SlotInfo | None:
        return self._slots.get(SlotLabel.LIVE)

    @property
    def staging(self) -> SlotInfo | None:
        return self._slots.get(SlotLabel.STAGING)

    @property
    def swap_count(self) -> int:
        return len(self._history)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def run_validation_gates(
        self,
        staging: SlotInfo,
        *,
        gates: list[str] | None = None,
    ) -> list[ValidationGate]:
        """Run standard validation gates against the staging slot.

        Override or extend for custom checks.  Returns a list of
        ``ValidationGate`` results.
        """
        gate_names = gates or ["schema_match", "row_count", "dax_syntax", "tmdl_structure"]
        results: list[ValidationGate] = []
        for name in gate_names:
            # In production, dispatch to real validators.
            # Here we produce a passing stub:
            results.append(ValidationGate(name=name, passed=True, message="Stub — OK"))
        return results

    # ------------------------------------------------------------------
    # Swap
    # ------------------------------------------------------------------

    async def swap(
        self,
        staging: SlotInfo | None = None,
        *,
        gates: list[str] | None = None,
    ) -> SwapResult:
        """Attempt to promote staging → live.

        Steps
        -----
        1. Validate the staging artifact.
        2. If all gates pass, swap slots.
        3. If any gate fails, keep the current live.
        """
        staging = staging or self.staging
        if staging is None:
            return SwapResult(outcome=SwapOutcome.FAILED, error="No staging artifact to promote")

        live_before = self.live

        # Run validation gates
        validation_gates = await self.run_validation_gates(staging, gates=gates)
        all_passed = all(g.passed for g in validation_gates)

        if not all_passed:
            logger.warning("Validation failed for staging %s — aborting swap", staging.artifact_name)
            result = SwapResult(
                outcome=SwapOutcome.VALIDATION_FAILED,
                live_before=live_before,
                live_after=live_before,  # unchanged
                validation_gates=validation_gates,
            )
            self._history.append(result)
            return result

        if self.dry_run:
            logger.info("DRY-RUN swap: %s → live", staging.artifact_name)
            result = SwapResult(
                outcome=SwapOutcome.DRY_RUN,
                live_before=live_before,
                live_after=staging,
                validation_gates=validation_gates,
            )
            self._history.append(result)
            return result

        # Perform the swap
        try:
            new_live = SlotInfo(
                slot=SlotLabel.LIVE,
                artifact_id=staging.artifact_id,
                artifact_name=staging.artifact_name,
                version=staging.version,
                metadata=staging.metadata,
            )
            old_staging = None
            if live_before:
                old_staging = SlotInfo(
                    slot=SlotLabel.STAGING,
                    artifact_id=live_before.artifact_id,
                    artifact_name=live_before.artifact_name,
                    version=live_before.version,
                    healthy=live_before.healthy,
                    metadata=live_before.metadata,
                )
                self._slots[SlotLabel.STAGING] = old_staging

            self._slots[SlotLabel.LIVE] = new_live

            logger.info(
                "SWAPPED: %s (v%d) → live, %s (v%d) → staging",
                new_live.artifact_name,
                new_live.version,
                old_staging.artifact_name if old_staging else "—",
                old_staging.version if old_staging else 0,
            )

            result = SwapResult(
                outcome=SwapOutcome.SWAPPED,
                live_before=live_before,
                live_after=new_live,
                validation_gates=validation_gates,
            )
            self._history.append(result)
            return result

        except Exception as exc:  # noqa: BLE001
            logger.error("Swap failed: %s", exc)
            result = SwapResult(
                outcome=SwapOutcome.FAILED,
                live_before=live_before,
                validation_gates=validation_gates,
                error=str(exc),
            )
            self._history.append(result)
            return result

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    async def rollback(self) -> SwapResult:
        """Revert the last swap by promoting the current staging back to live."""
        staging = self.staging
        if staging is None:
            return SwapResult(outcome=SwapOutcome.FAILED, error="No staging slot to rollback to")

        live_before = self.live
        new_live = SlotInfo(
            slot=SlotLabel.LIVE,
            artifact_id=staging.artifact_id,
            artifact_name=staging.artifact_name,
            version=staging.version,
            metadata=staging.metadata,
        )
        self._slots[SlotLabel.LIVE] = new_live

        if live_before:
            self._slots[SlotLabel.STAGING] = SlotInfo(
                slot=SlotLabel.STAGING,
                artifact_id=live_before.artifact_id,
                artifact_name=live_before.artifact_name,
                version=live_before.version,
                metadata=live_before.metadata,
            )

        logger.info("ROLLBACK: %s (v%d) restored to live", new_live.artifact_name, new_live.version)
        result = SwapResult(
            outcome=SwapOutcome.ROLLED_BACK,
            live_before=live_before,
            live_after=new_live,
        )
        self._history.append(result)
        return result
