"""SLA tracker — per-asset SLA compliance and tracking.

Monitors whether each migrated asset meets defined SLAs for:
  - Migration duration (time from start to completion)
  - Validation pass rate (% of checks passed)
  - Data accuracy (row-count deviation tolerance)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SLA definitions
# ---------------------------------------------------------------------------


class SLAStatus(str, Enum):
    MET = "met"
    AT_RISK = "at_risk"
    BREACHED = "breached"
    PENDING = "pending"


@dataclass(frozen=True)
class SLAThresholds:
    """Configurable SLA thresholds."""

    max_duration_minutes: float = 60.0
    min_validation_pass_rate: float = 0.95       # 95 %
    max_row_count_deviation_pct: float = 0.01    # 1 %
    warn_duration_factor: float = 0.8            # warn at 80 % of max


@dataclass
class SLAResult:
    """SLA evaluation for a single asset."""

    asset_id: str
    asset_name: str
    duration_minutes: float = 0.0
    validation_pass_rate: float = 1.0
    row_count_deviation_pct: float = 0.0
    duration_status: SLAStatus = SLAStatus.PENDING
    validation_status: SLAStatus = SLAStatus.PENDING
    accuracy_status: SLAStatus = SLAStatus.PENDING
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def overall_status(self) -> SLAStatus:
        statuses = [self.duration_status, self.validation_status, self.accuracy_status]
        if SLAStatus.BREACHED in statuses:
            return SLAStatus.BREACHED
        if SLAStatus.AT_RISK in statuses:
            return SLAStatus.AT_RISK
        if SLAStatus.PENDING in statuses:
            return SLAStatus.PENDING
        return SLAStatus.MET


@dataclass
class SLAReport:
    """Aggregated SLA report across all tracked assets."""

    results: list[SLAResult] = field(default_factory=list)
    thresholds: SLAThresholds = field(default_factory=SLAThresholds)

    @property
    def met_count(self) -> int:
        return sum(1 for r in self.results if r.overall_status == SLAStatus.MET)

    @property
    def breached_count(self) -> int:
        return sum(1 for r in self.results if r.overall_status == SLAStatus.BREACHED)

    @property
    def at_risk_count(self) -> int:
        return sum(1 for r in self.results if r.overall_status == SLAStatus.AT_RISK)

    @property
    def compliance_rate(self) -> float:
        if not self.results:
            return 1.0
        return self.met_count / len(self.results)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_sla(
    asset_id: str,
    asset_name: str,
    duration_minutes: float,
    validation_pass_rate: float,
    row_count_deviation_pct: float = 0.0,
    thresholds: SLAThresholds | None = None,
) -> SLAResult:
    """Evaluate SLA compliance for a single asset."""
    t = thresholds or SLAThresholds()
    result = SLAResult(
        asset_id=asset_id,
        asset_name=asset_name,
        duration_minutes=duration_minutes,
        validation_pass_rate=validation_pass_rate,
        row_count_deviation_pct=row_count_deviation_pct,
    )

    # Duration SLA
    if duration_minutes > t.max_duration_minutes:
        result.duration_status = SLAStatus.BREACHED
    elif duration_minutes > t.max_duration_minutes * t.warn_duration_factor:
        result.duration_status = SLAStatus.AT_RISK
    else:
        result.duration_status = SLAStatus.MET

    # Validation pass-rate SLA
    if validation_pass_rate < t.min_validation_pass_rate:
        result.validation_status = SLAStatus.BREACHED
    elif validation_pass_rate < t.min_validation_pass_rate + 0.03:
        result.validation_status = SLAStatus.AT_RISK
    else:
        result.validation_status = SLAStatus.MET

    # Accuracy SLA
    if row_count_deviation_pct > t.max_row_count_deviation_pct:
        result.accuracy_status = SLAStatus.BREACHED
    elif row_count_deviation_pct > t.max_row_count_deviation_pct * 0.5:
        result.accuracy_status = SLAStatus.AT_RISK
    else:
        result.accuracy_status = SLAStatus.MET

    logger.info(
        "SLA %s: duration=%s validation=%s accuracy=%s → %s",
        asset_name,
        result.duration_status.value,
        result.validation_status.value,
        result.accuracy_status.value,
        result.overall_status.value,
    )

    return result


def build_sla_report(
    results: list[SLAResult],
    thresholds: SLAThresholds | None = None,
) -> SLAReport:
    """Build an aggregated SLA report."""
    report = SLAReport(results=results, thresholds=thresholds or SLAThresholds())
    logger.info(
        "SLA report: %d met, %d at-risk, %d breached (%.0f%% compliance)",
        report.met_count,
        report.at_risk_count,
        report.breached_count,
        report.compliance_rate * 100,
    )
    return report


def render_sla_summary(report: SLAReport) -> dict[str, Any]:
    """Render a JSON-serialisable SLA summary."""
    return {
        "total_assets": len(report.results),
        "met": report.met_count,
        "at_risk": report.at_risk_count,
        "breached": report.breached_count,
        "compliance_rate": round(report.compliance_rate, 4),
        "thresholds": {
            "max_duration_minutes": report.thresholds.max_duration_minutes,
            "min_validation_pass_rate": report.thresholds.min_validation_pass_rate,
            "max_row_count_deviation_pct": report.thresholds.max_row_count_deviation_pct,
        },
        "breached_assets": [
            {
                "id": r.asset_id,
                "name": r.asset_name,
                "duration_status": r.duration_status.value,
                "validation_status": r.validation_status.value,
                "accuracy_status": r.accuracy_status.value,
            }
            for r in report.results
            if r.overall_status == SLAStatus.BREACHED
        ],
    }
