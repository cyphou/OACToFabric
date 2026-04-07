"""Pilot Report — generate a structured report after a live OAC pilot run.

Collects per-agent results, timing, errors, and produces a summary
suitable for stakeholder review and defect triage.
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


class PilotOutcome(str, Enum):
    """High-level result of a pilot run."""

    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"
    ABORTED = "aborted"


class AgentVerdict(str, Enum):
    """Per-agent outcome in a pilot."""

    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PilotAgentResult:
    """Result from a single agent during the pilot."""

    agent_id: str
    agent_name: str = ""
    verdict: AgentVerdict = AgentVerdict.OK
    items_processed: int = 0
    items_failed: int = 0
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.items_processed + self.items_failed
        if total == 0:
            return 1.0
        return self.items_processed / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "verdict": self.verdict.value,
            "items_processed": self.items_processed,
            "items_failed": self.items_failed,
            "duration_ms": self.duration_ms,
            "success_rate": round(self.success_rate, 4),
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class PilotDefect:
    """A defect discovered during pilot execution."""

    defect_id: str
    agent_id: str
    severity: str = "medium"  # low, medium, high, critical
    title: str = ""
    description: str = ""
    asset_name: str = ""
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "defect_id": self.defect_id,
            "agent_id": self.agent_id,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "asset_name": self.asset_name,
            "recommended_action": self.recommended_action,
        }


@dataclass
class PerformanceProfile:
    """Performance metrics captured during the pilot."""

    total_duration_ms: int = 0
    peak_memory_mb: float = 0.0
    api_calls: int = 0
    api_latency_avg_ms: float = 0.0
    api_latency_p99_ms: float = 0.0
    throughput_items_per_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_duration_ms": self.total_duration_ms,
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "api_calls": self.api_calls,
            "api_latency_avg_ms": round(self.api_latency_avg_ms, 2),
            "api_latency_p99_ms": round(self.api_latency_p99_ms, 2),
            "throughput_items_per_sec": round(self.throughput_items_per_sec, 2),
        }


@dataclass
class PilotReport:
    """Full pilot report aggregating all agent results."""

    pilot_id: str = ""
    scope_description: str = ""
    outcome: PilotOutcome = PilotOutcome.PASSED
    agent_results: list[PilotAgentResult] = field(default_factory=list)
    defects: list[PilotDefect] = field(default_factory=list)
    performance: PerformanceProfile = field(default_factory=PerformanceProfile)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    recommendations: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def total_items_processed(self) -> int:
        return sum(r.items_processed for r in self.agent_results)

    @property
    def total_items_failed(self) -> int:
        return sum(r.items_failed for r in self.agent_results)

    @property
    def agents_passed(self) -> int:
        return sum(1 for r in self.agent_results if r.verdict == AgentVerdict.OK)

    @property
    def agents_failed(self) -> int:
        return sum(1 for r in self.agent_results if r.verdict == AgentVerdict.FAILED)

    @property
    def critical_defects(self) -> list[PilotDefect]:
        return [d for d in self.defects if d.severity == "critical"]

    @property
    def high_defects(self) -> list[PilotDefect]:
        return [d for d in self.defects if d.severity == "high"]

    # ------------------------------------------------------------------
    # Outcome computation
    # ------------------------------------------------------------------

    def compute_outcome(self) -> PilotOutcome:
        """Determine overall outcome based on agent results and defects."""
        if any(r.verdict == AgentVerdict.FAILED for r in self.agent_results):
            return PilotOutcome.FAILED
        if self.critical_defects:
            return PilotOutcome.FAILED
        if self.high_defects or any(r.verdict == AgentVerdict.DEGRADED for r in self.agent_results):
            return PilotOutcome.PASSED_WITH_WARNINGS
        return PilotOutcome.PASSED

    def finalize(self) -> None:
        """Set completed_at and compute final outcome."""
        self.completed_at = datetime.now(timezone.utc)
        self.outcome = self.compute_outcome()
        logger.info(
            "Pilot %s finalized — outcome=%s, processed=%d, failed=%d, defects=%d",
            self.pilot_id,
            self.outcome.value,
            self.total_items_processed,
            self.total_items_failed,
            len(self.defects),
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "pilot_id": self.pilot_id,
            "scope_description": self.scope_description,
            "outcome": self.outcome.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_items_processed": self.total_items_processed,
            "total_items_failed": self.total_items_failed,
            "agents_passed": self.agents_passed,
            "agents_failed": self.agents_failed,
            "agent_results": [r.to_dict() for r in self.agent_results],
            "defects": [d.to_dict() for d in self.defects],
            "performance": self.performance.to_dict(),
            "recommendations": self.recommendations,
        }

    def summary(self) -> str:
        """One-paragraph summary for stakeholder emails / dashboards."""
        lines = [
            f"Pilot {self.pilot_id}: {self.outcome.value.upper()}",
            f"  Agents: {self.agents_passed} passed, {self.agents_failed} failed",
            f"  Items:  {self.total_items_processed} processed, {self.total_items_failed} failed",
            f"  Defects: {len(self.defects)} total ({len(self.critical_defects)} critical, {len(self.high_defects)} high)",
        ]
        if self.performance.total_duration_ms:
            lines.append(f"  Duration: {self.performance.total_duration_ms}ms")
        if self.recommendations:
            lines.append(f"  Recommendations: {len(self.recommendations)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pilot report builder (convenience)
# ---------------------------------------------------------------------------


class PilotReportBuilder:
    """Fluent builder for assembling a ``PilotReport``."""

    def __init__(self, pilot_id: str, scope_description: str = "") -> None:
        self._report = PilotReport(pilot_id=pilot_id, scope_description=scope_description)

    def add_agent_result(self, result: PilotAgentResult) -> PilotReportBuilder:
        self._report.agent_results.append(result)
        return self

    def add_defect(self, defect: PilotDefect) -> PilotReportBuilder:
        self._report.defects.append(defect)
        return self

    def set_performance(self, profile: PerformanceProfile) -> PilotReportBuilder:
        self._report.performance = profile
        return self

    def add_recommendation(self, text: str) -> PilotReportBuilder:
        self._report.recommendations.append(text)
        return self

    def build(self) -> PilotReport:
        self._report.finalize()
        return self._report
