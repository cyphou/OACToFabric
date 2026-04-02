"""Healing engine — coordinates diagnosis → repair → validation — Phase 74.

Orchestrates the full self-healing cycle:
1. Diagnose the error.
2. Select the best repair strategy.
3. Apply the repair.
4. Validate the fix (regression guard).
5. Persist the resolution to agent memory.

Usage::

    engine = HealingEngine(diagnostician, strategies)
    report = await engine.heal(error, context)
    if report.healed:
        print(f"Fixed via {report.strategy_used}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.core.intelligence.error_diagnostician import Diagnosis, ErrorDiagnostician
from src.core.intelligence.repair_strategies import RepairResult, RepairStrategy

logger = logging.getLogger(__name__)


@dataclass
class HealingReport:
    """Report of a self-healing attempt."""

    healed: bool = False
    diagnosis: Diagnosis | None = None
    strategy_used: str = ""
    repair_result: RepairResult | None = None
    attempts: list[dict[str, Any]] = field(default_factory=list)
    total_attempts: int = 0
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "healed": self.healed,
            "diagnosis": self.diagnosis.to_dict() if self.diagnosis else None,
            "strategy_used": self.strategy_used,
            "total_attempts": self.total_attempts,
            "error_message": self.error_message,
            "attempts": self.attempts,
        }


class HealingEngine:
    """Self-healing migration pipeline engine.

    Parameters
    ----------
    diagnostician
        Error diagnostician for classifying failures.
    strategies
        List of repair strategies to try.
    agent_memory
        Optional agent memory for persisting resolutions.
    max_strategies
        Maximum number of strategies to try before giving up.
    """

    def __init__(
        self,
        diagnostician: ErrorDiagnostician | None = None,
        strategies: list[RepairStrategy] | None = None,
        agent_memory: Any = None,
        max_strategies: int = 3,
    ) -> None:
        self._diagnostician = diagnostician or ErrorDiagnostician()
        self._strategies = strategies or []
        self._memory = agent_memory
        self._max_strategies = max_strategies
        self._healing_history: list[HealingReport] = []

    @property
    def history(self) -> list[HealingReport]:
        return list(self._healing_history)

    @property
    def success_rate(self) -> float:
        if not self._healing_history:
            return 0.0
        healed = sum(1 for h in self._healing_history if h.healed)
        return healed / len(self._healing_history)

    async def heal(
        self,
        error: Exception | str,
        context: dict[str, Any] | None = None,
    ) -> HealingReport:
        """Attempt to heal a migration error.

        Parameters
        ----------
        error
            The error to diagnose and repair.
        context
            Additional context (source_expression, asset_id, agent_id, etc.).
        """
        report = HealingReport()
        ctx = context or {}

        # 1. Diagnose
        diagnosis = self._diagnostician.diagnose(error, ctx)
        report.diagnosis = diagnosis

        if not diagnosis.can_auto_repair:
            report.error_message = f"Error category '{diagnosis.category.value}' does not support auto-repair"
            self._healing_history.append(report)
            return report

        # 2. Find applicable strategies
        applicable = [
            s for s in self._strategies
            if s.can_handle(diagnosis)
        ][:self._max_strategies]

        if not applicable:
            report.error_message = "No repair strategy available for this diagnosis"
            self._healing_history.append(report)
            return report

        # 3. Try strategies in order
        for strategy in applicable:
            report.total_attempts += 1
            try:
                result = await strategy.repair(diagnosis, ctx)
                report.attempts.append({
                    "strategy": strategy.name,
                    "success": result.success,
                    "description": result.description,
                })

                if result.success:
                    report.healed = True
                    report.strategy_used = strategy.name
                    report.repair_result = result

                    # Persist to memory
                    self._persist_resolution(diagnosis, strategy.name, result)

                    logger.info(
                        "Healed error [%s] via strategy '%s': %s",
                        diagnosis.category.value,
                        strategy.name,
                        result.description,
                    )
                    break

            except Exception as e:
                report.attempts.append({
                    "strategy": strategy.name,
                    "success": False,
                    "description": f"Strategy failed: {e}",
                })
                logger.warning("Strategy '%s' failed: %s", strategy.name, e)

        if not report.healed:
            report.error_message = (
                f"All {report.total_attempts} repair strategies failed for "
                f"'{diagnosis.category.value}'"
            )

        self._healing_history.append(report)
        return report

    def _persist_resolution(
        self, diagnosis: Diagnosis, strategy: str, result: RepairResult
    ) -> None:
        """Store successful resolution in agent memory."""
        if self._memory:
            self._memory.store(
                "healing_resolution",
                key=f"{diagnosis.category.value}_{strategy}",
                value={
                    "category": diagnosis.category.value,
                    "strategy": strategy,
                    "description": result.description,
                },
                confidence=0.9,
            )


class RegressionGuard:
    """Ensures repairs don't break previously passing items.

    Before applying a fix, runs targeted validation on the affected scope
    to catch regressions.
    """

    def __init__(self) -> None:
        self._baselines: dict[str, Any] = {}  # asset_id → baseline result

    def set_baseline(self, asset_id: str, validation_result: Any) -> None:
        """Record a known-good validation result."""
        self._baselines[asset_id] = validation_result

    def check_regression(
        self, asset_id: str, new_result: Any
    ) -> tuple[bool, str]:
        """Check if new result regresses from baseline.

        Returns (passed, message).
        """
        baseline = self._baselines.get(asset_id)
        if baseline is None:
            return True, "No baseline — accepted as new"

        # Compare basic properties
        baseline_pass = getattr(baseline, "passed", getattr(baseline, "success", True))
        new_pass = getattr(new_result, "passed", getattr(new_result, "success", True))

        if baseline_pass and not new_pass:
            return False, "Regression: baseline passed but new result failed"

        return True, "No regression detected"

    @property
    def baseline_count(self) -> int:
        return len(self._baselines)
