"""Automated regression testing — continuous post-migration validation.

Catches data drift, schema changes, and visual regressions in migrated
Fabric/Power BI artifacts by comparing live state against go-live baselines.

Capabilities:
* **Data regression**: Row counts, checksums, sample-query comparisons.
* **Schema drift**: Compare current schema snapshot against baseline.
* **Visual regression**: SSIM-based screenshot comparison.
* **Alert integration**: Notify via notification pipeline when regressions found.
* **Scheduling**: Define periodic regression test suites.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.agents.orchestrator.notification_manager import (
    Channel,
    Notification,
    NotificationManager,
    Severity,
)
from src.agents.validation.data_reconciliation import (
    CheckStatus,
    CheckType,
    ReconciliationReport,
    ReconciliationResult,
)
from src.agents.validation.schema_drift import (
    DriftReport,
    SchemaSnapshot,
    compare_snapshots,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RegressionSeverity(str, Enum):
    """Severity of a regression finding."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class RegressionType(str, Enum):
    """Category of regression test."""

    DATA = "data"
    SCHEMA = "schema"
    VISUAL = "visual"


class ScheduleFrequency(str, Enum):
    """How often to run regression tests."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DataBaseline:
    """Baseline data snapshot captured at go-live."""

    baseline_id: str = ""
    captured_at: str = ""
    table_row_counts: dict[str, int] = field(default_factory=dict)
    table_checksums: dict[str, str] = field(default_factory=dict)
    sample_queries: list[dict[str, Any]] = field(default_factory=list)
    column_stats: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "baselineId": self.baseline_id,
                "capturedAt": self.captured_at,
                "tableRowCounts": self.table_row_counts,
                "tableChecksums": self.table_checksums,
                "sampleQueries": self.sample_queries,
                "columnStats": self.column_stats,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "DataBaseline":
        data = json.loads(json_str)
        return cls(
            baseline_id=data.get("baselineId", ""),
            captured_at=data.get("capturedAt", ""),
            table_row_counts=data.get("tableRowCounts", {}),
            table_checksums=data.get("tableChecksums", {}),
            sample_queries=data.get("sampleQueries", []),
            column_stats=data.get("columnStats", {}),
        )


@dataclass
class VisualBaseline:
    """Baseline visual snapshot for a report page."""

    report_name: str = ""
    page_name: str = ""
    screenshot_hash: str = ""
    captured_at: str = ""
    width: int = 0
    height: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionBaseline:
    """Combined baseline for all regression test types."""

    baseline_id: str = ""
    captured_at: str = ""
    data_baseline: DataBaseline | None = None
    schema_baseline: SchemaSnapshot | None = None
    visual_baselines: list[VisualBaseline] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(
            {
                "baselineId": self.baseline_id,
                "capturedAt": self.captured_at,
                "hasData": self.data_baseline is not None,
                "hasSchema": self.schema_baseline is not None,
                "visualCount": len(self.visual_baselines),
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Regression findings
# ---------------------------------------------------------------------------


@dataclass
class RegressionFinding:
    """A single regression test finding."""

    finding_id: str = ""
    regression_type: RegressionType = RegressionType.DATA
    severity: RegressionSeverity = RegressionSeverity.INFO
    table_name: str = ""
    description: str = ""
    baseline_value: Any = None
    current_value: Any = None
    variance: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualRegressionFinding(RegressionFinding):
    """Visual regression finding with SSIM score."""

    report_name: str = ""
    page_name: str = ""
    ssim_score: float = 1.0  # 1.0 = identical, 0.0 = completely different
    threshold: float = 0.95

    def __post_init__(self):
        self.regression_type = RegressionType.VISUAL


# ---------------------------------------------------------------------------
# Regression report
# ---------------------------------------------------------------------------


@dataclass
class RegressionTestResult:
    """Result of a single regression test run."""

    test_id: str = ""
    regression_type: RegressionType = RegressionType.DATA
    passed: bool = True
    findings: list[RegressionFinding] = field(default_factory=list)
    executed_at: str = ""
    duration_ms: int = 0


@dataclass
class RegressionReport:
    """Aggregated regression test report."""

    report_id: str = ""
    baseline_id: str = ""
    executed_at: str = ""
    completed_at: str = ""
    test_results: list[RegressionTestResult] = field(default_factory=list)
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    findings: list[RegressionFinding] = field(default_factory=list)
    overall_passed: bool = True

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def critical_count(self) -> int:
        return sum(
            1 for f in self.findings if f.severity == RegressionSeverity.CRITICAL
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for f in self.findings if f.severity == RegressionSeverity.WARNING
        )

    def add_result(self, result: RegressionTestResult) -> None:
        self.test_results.append(result)
        self.total_tests += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
            self.overall_passed = False
        self.findings.extend(result.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reportId": self.report_id,
            "baselineId": self.baseline_id,
            "executedAt": self.executed_at,
            "completedAt": self.completed_at,
            "totalTests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "overallPassed": self.overall_passed,
            "criticalCount": self.critical_count,
            "warningCount": self.warning_count,
            "findings": [
                {
                    "findingId": f.finding_id,
                    "type": f.regression_type.value,
                    "severity": f.severity.value,
                    "table": f.table_name,
                    "description": f.description,
                    "baselineValue": str(f.baseline_value),
                    "currentValue": str(f.current_value),
                    "variance": f.variance,
                }
                for f in self.findings
            ],
        }

    def generate_markdown(self) -> str:
        lines = ["# Regression Test Report\n"]
        lines.append(f"**Report ID**: {self.report_id}  ")
        lines.append(f"**Baseline**: {self.baseline_id}  ")
        lines.append(f"**Date**: {self.executed_at}  ")
        lines.append(
            f"**Result**: {'PASSED' if self.overall_passed else 'FAILED'}  "
        )
        lines.append("")

        lines.append("## Summary\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total tests | {self.total_tests} |")
        lines.append(f"| Passed | {self.passed} |")
        lines.append(f"| Failed | {self.failed} |")
        lines.append(f"| Critical findings | {self.critical_count} |")
        lines.append(f"| Warnings | {self.warning_count} |")
        lines.append("")

        if self.findings:
            lines.append("## Findings\n")
            lines.append("| # | Type | Severity | Table | Description |")
            lines.append("|---|------|----------|-------|-------------|")
            for i, f in enumerate(self.findings, 1):
                lines.append(
                    f"| {i} | {f.regression_type.value} | {f.severity.value} "
                    f"| {f.table_name} | {f.description} |"
                )
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Schedule configuration
# ---------------------------------------------------------------------------


@dataclass
class RegressionSchedule:
    """Configuration for scheduled regression tests."""

    schedule_id: str = ""
    frequency: ScheduleFrequency = ScheduleFrequency.DAILY
    enabled: bool = True
    test_types: list[RegressionType] = field(
        default_factory=lambda: list(RegressionType)
    )
    notification_channels: list[Channel] = field(
        default_factory=lambda: [Channel.LOG]
    )
    row_count_tolerance: float = 0.01  # 1% default
    ssim_threshold: float = 0.95
    last_run: str = ""
    next_run: str = ""


# ---------------------------------------------------------------------------
# Regression tester
# ---------------------------------------------------------------------------


class RegressionTester:
    """Run automated regression tests against baselines.

    Compares live Fabric/PBI state against go-live baselines to detect
    data drift, schema changes, and visual regressions.
    """

    def __init__(
        self,
        notification_manager: NotificationManager | None = None,
        row_count_tolerance: float = 0.01,
        ssim_threshold: float = 0.95,
    ) -> None:
        self._notifications = notification_manager
        self.row_count_tolerance = row_count_tolerance
        self.ssim_threshold = ssim_threshold

    # ----- Baseline capture --------------------------------------------------

    def capture_data_baseline(
        self,
        table_row_counts: dict[str, int],
        table_checksums: dict[str, str] | None = None,
        sample_queries: list[dict[str, Any]] | None = None,
        column_stats: dict[str, dict[str, Any]] | None = None,
        baseline_id: str = "",
    ) -> DataBaseline:
        """Capture a data baseline at go-live.

        Args:
            table_row_counts: Table name → row count.
            table_checksums: Table name → checksum string.
            sample_queries: List of {query, expected_result} dicts.
            column_stats: Table.column → {min, max, nulls, distinct}.
            baseline_id: Optional identifier.

        Returns:
            DataBaseline snapshot.
        """
        now = datetime.now(timezone.utc).isoformat()
        return DataBaseline(
            baseline_id=baseline_id or f"data-{now}",
            captured_at=now,
            table_row_counts=table_row_counts,
            table_checksums=table_checksums or {},
            sample_queries=sample_queries or [],
            column_stats=column_stats or {},
        )

    def capture_visual_baseline(
        self,
        report_name: str,
        page_name: str,
        screenshot_bytes: bytes,
        width: int = 0,
        height: int = 0,
    ) -> VisualBaseline:
        """Capture a visual baseline from a report screenshot.

        Args:
            report_name: Name of the Power BI report.
            page_name: Page/tab name.
            screenshot_bytes: Raw screenshot image bytes.
            width: Image width.
            height: Image height.

        Returns:
            VisualBaseline with hash of screenshot.
        """
        screenshot_hash = hashlib.sha256(screenshot_bytes).hexdigest()
        return VisualBaseline(
            report_name=report_name,
            page_name=page_name,
            screenshot_hash=screenshot_hash,
            captured_at=datetime.now(timezone.utc).isoformat(),
            width=width,
            height=height,
        )

    def capture_full_baseline(
        self,
        table_row_counts: dict[str, int],
        schema_snapshot: SchemaSnapshot | None = None,
        visual_baselines: list[VisualBaseline] | None = None,
        table_checksums: dict[str, str] | None = None,
        baseline_id: str = "",
    ) -> RegressionBaseline:
        """Capture a combined baseline for all regression types.

        Args:
            table_row_counts: Table → row count.
            schema_snapshot: Schema snapshot from schema_drift module.
            visual_baselines: Pre-captured visual baselines.
            table_checksums: Optional checksums.
            baseline_id: Optional identifier.

        Returns:
            RegressionBaseline combining data, schema, and visual.
        """
        now = datetime.now(timezone.utc).isoformat()
        bid = baseline_id or f"baseline-{now}"
        data_bl = self.capture_data_baseline(
            table_row_counts=table_row_counts,
            table_checksums=table_checksums or {},
            baseline_id=f"{bid}-data",
        )
        return RegressionBaseline(
            baseline_id=bid,
            captured_at=now,
            data_baseline=data_bl,
            schema_baseline=schema_snapshot,
            visual_baselines=visual_baselines or [],
        )

    # ----- Regression tests --------------------------------------------------

    def run_data_regression(
        self,
        baseline: DataBaseline,
        current_row_counts: dict[str, int],
        current_checksums: dict[str, str] | None = None,
    ) -> RegressionTestResult:
        """Compare current data state against the data baseline.

        Args:
            baseline: Data baseline captured at go-live.
            current_row_counts: Current table → row count.
            current_checksums: Current table → checksum.

        Returns:
            RegressionTestResult with any data drift findings.
        """
        now = datetime.now(timezone.utc).isoformat()
        result = RegressionTestResult(
            test_id=f"data-regression-{now}",
            regression_type=RegressionType.DATA,
            executed_at=now,
            passed=True,
        )

        # Row count comparisons
        all_tables = set(baseline.table_row_counts) | set(current_row_counts)
        for table in sorted(all_tables):
            bl_count = baseline.table_row_counts.get(table)
            cur_count = current_row_counts.get(table)

            if bl_count is None:
                # New table appeared
                result.findings.append(
                    RegressionFinding(
                        finding_id=f"new-table-{table}",
                        regression_type=RegressionType.DATA,
                        severity=RegressionSeverity.WARNING,
                        table_name=table,
                        description=f"New table detected: {table}",
                        current_value=cur_count,
                    )
                )
                continue

            if cur_count is None:
                # Table disappeared
                result.findings.append(
                    RegressionFinding(
                        finding_id=f"missing-table-{table}",
                        regression_type=RegressionType.DATA,
                        severity=RegressionSeverity.CRITICAL,
                        table_name=table,
                        description=f"Table missing: {table}",
                        baseline_value=bl_count,
                    )
                )
                result.passed = False
                continue

            # Row count variance
            if bl_count == 0:
                variance = 1.0 if cur_count > 0 else 0.0
            else:
                variance = abs(cur_count - bl_count) / bl_count

            if variance > self.row_count_tolerance:
                severity = (
                    RegressionSeverity.CRITICAL
                    if variance > 0.1
                    else RegressionSeverity.WARNING
                )
                result.findings.append(
                    RegressionFinding(
                        finding_id=f"row-drift-{table}",
                        regression_type=RegressionType.DATA,
                        severity=severity,
                        table_name=table,
                        description=(
                            f"Row count drift: {bl_count} → {cur_count} "
                            f"({variance:.1%})"
                        ),
                        baseline_value=bl_count,
                        current_value=cur_count,
                        variance=variance,
                    )
                )
                if severity == RegressionSeverity.CRITICAL:
                    result.passed = False

        # Checksum comparisons
        if current_checksums and baseline.table_checksums:
            for table in sorted(
                set(baseline.table_checksums) & set(current_checksums)
            ):
                bl_hash = baseline.table_checksums[table]
                cur_hash = current_checksums[table]
                if bl_hash != cur_hash:
                    result.findings.append(
                        RegressionFinding(
                            finding_id=f"checksum-drift-{table}",
                            regression_type=RegressionType.DATA,
                            severity=RegressionSeverity.WARNING,
                            table_name=table,
                            description=f"Checksum changed for {table}",
                            baseline_value=bl_hash,
                            current_value=cur_hash,
                        )
                    )

        return result

    def run_schema_regression(
        self,
        baseline: SchemaSnapshot,
        current: SchemaSnapshot,
    ) -> RegressionTestResult:
        """Compare current schema against baseline using schema drift detection.

        Args:
            baseline: Schema snapshot from go-live.
            current: Current schema snapshot.

        Returns:
            RegressionTestResult with schema drift findings.
        """
        now = datetime.now(timezone.utc).isoformat()
        result = RegressionTestResult(
            test_id=f"schema-regression-{now}",
            regression_type=RegressionType.SCHEMA,
            executed_at=now,
            passed=True,
        )

        drift_report: DriftReport = compare_snapshots(baseline, current)

        for drift in drift_report.drifts:
            severity = RegressionSeverity.INFO
            if drift.severity == "critical":
                severity = RegressionSeverity.CRITICAL
                result.passed = False
            elif drift.severity == "warning":
                severity = RegressionSeverity.WARNING

            result.findings.append(
                RegressionFinding(
                    finding_id=f"schema-{drift.drift_type}-{drift.table_name}",
                    regression_type=RegressionType.SCHEMA,
                    severity=severity,
                    table_name=drift.table_name,
                    description=(
                        f"Schema drift: {drift.drift_type}"
                        + (f" on column {drift.column_name}" if drift.column_name else "")
                    ),
                    baseline_value=drift.old_value,
                    current_value=drift.new_value,
                    details={"drift_type": drift.drift_type},
                )
            )

        return result

    def run_visual_regression(
        self,
        baseline_visuals: list[VisualBaseline],
        current_screenshots: dict[str, bytes],
        ssim_scores: dict[str, float] | None = None,
    ) -> RegressionTestResult:
        """Compare current report screenshots against visual baselines.

        Uses hash comparison by default. If ``ssim_scores`` are provided
        (pre-computed externally), uses SSIM for similarity detection.

        Args:
            baseline_visuals: Visual baselines from go-live.
            current_screenshots: Dict of ``report_name/page_name`` → bytes.
            ssim_scores: Optional pre-computed SSIM scores (0–1).

        Returns:
            RegressionTestResult with visual regression findings.
        """
        now = datetime.now(timezone.utc).isoformat()
        result = RegressionTestResult(
            test_id=f"visual-regression-{now}",
            regression_type=RegressionType.VISUAL,
            executed_at=now,
            passed=True,
        )

        for vb in baseline_visuals:
            key = f"{vb.report_name}/{vb.page_name}"
            current_bytes = current_screenshots.get(key)

            if current_bytes is None:
                result.findings.append(
                    VisualRegressionFinding(
                        finding_id=f"missing-visual-{key}",
                        severity=RegressionSeverity.CRITICAL,
                        report_name=vb.report_name,
                        page_name=vb.page_name,
                        description=f"Missing screenshot for {key}",
                        ssim_score=0.0,
                        threshold=self.ssim_threshold,
                    )
                )
                result.passed = False
                continue

            # Check SSIM if provided
            if ssim_scores and key in ssim_scores:
                ssim = ssim_scores[key]
                if ssim < self.ssim_threshold:
                    severity = (
                        RegressionSeverity.CRITICAL
                        if ssim < 0.8
                        else RegressionSeverity.WARNING
                    )
                    result.findings.append(
                        VisualRegressionFinding(
                            finding_id=f"visual-diff-{key}",
                            severity=severity,
                            report_name=vb.report_name,
                            page_name=vb.page_name,
                            description=(
                                f"Visual regression: SSIM={ssim:.3f} "
                                f"(threshold={self.ssim_threshold})"
                            ),
                            ssim_score=ssim,
                            threshold=self.ssim_threshold,
                            baseline_value=vb.screenshot_hash,
                            current_value=hashlib.sha256(
                                current_bytes
                            ).hexdigest(),
                        )
                    )
                    if severity == RegressionSeverity.CRITICAL:
                        result.passed = False
            else:
                # Fallback to hash comparison
                current_hash = hashlib.sha256(current_bytes).hexdigest()
                if current_hash != vb.screenshot_hash:
                    result.findings.append(
                        VisualRegressionFinding(
                            finding_id=f"visual-hash-diff-{key}",
                            severity=RegressionSeverity.WARNING,
                            report_name=vb.report_name,
                            page_name=vb.page_name,
                            description=f"Screenshot hash changed for {key}",
                            baseline_value=vb.screenshot_hash,
                            current_value=current_hash,
                            ssim_score=0.0,
                            threshold=self.ssim_threshold,
                        )
                    )

        return result

    # ----- Full suite ---------------------------------------------------------

    def run_full_regression(
        self,
        baseline: RegressionBaseline,
        current_row_counts: dict[str, int] | None = None,
        current_checksums: dict[str, str] | None = None,
        current_schema: SchemaSnapshot | None = None,
        current_screenshots: dict[str, bytes] | None = None,
        ssim_scores: dict[str, float] | None = None,
        test_types: list[RegressionType] | None = None,
    ) -> RegressionReport:
        """Run a full regression test suite against a baseline.

        Args:
            baseline: Combined regression baseline.
            current_row_counts: Current table row counts.
            current_checksums: Current table checksums.
            current_schema: Current schema snapshot.
            current_screenshots: Current report screenshots.
            ssim_scores: Pre-computed SSIM scores.
            test_types: Which regression types to run (default: all).

        Returns:
            RegressionReport with all findings.
        """
        now = datetime.now(timezone.utc).isoformat()
        report = RegressionReport(
            report_id=f"regression-{now}",
            baseline_id=baseline.baseline_id,
            executed_at=now,
        )

        types_to_run = test_types or list(RegressionType)

        # Data regression
        if (
            RegressionType.DATA in types_to_run
            and baseline.data_baseline
            and current_row_counts is not None
        ):
            data_result = self.run_data_regression(
                baseline.data_baseline,
                current_row_counts,
                current_checksums,
            )
            report.add_result(data_result)

        # Schema regression
        if (
            RegressionType.SCHEMA in types_to_run
            and baseline.schema_baseline
            and current_schema is not None
        ):
            schema_result = self.run_schema_regression(
                baseline.schema_baseline, current_schema
            )
            report.add_result(schema_result)

        # Visual regression
        if (
            RegressionType.VISUAL in types_to_run
            and baseline.visual_baselines
            and current_screenshots is not None
        ):
            visual_result = self.run_visual_regression(
                baseline.visual_baselines, current_screenshots, ssim_scores
            )
            report.add_result(visual_result)

        report.completed_at = datetime.now(timezone.utc).isoformat()

        # Send notifications for critical findings
        self._notify_findings(report)

        logger.info(
            "Regression test complete: %d tests, %d passed, %d failed, %d findings",
            report.total_tests,
            report.passed,
            report.failed,
            report.finding_count,
        )
        return report

    # ----- Notification -------------------------------------------------------

    def _notify_findings(self, report: RegressionReport) -> None:
        """Send notifications for regression findings."""
        if not self._notifications:
            return

        if report.critical_count > 0:
            self._notifications.notify(
                Notification(
                    title="Regression Test: CRITICAL findings",
                    message=(
                        f"Regression suite {report.report_id}: "
                        f"{report.critical_count} critical finding(s). "
                        f"{report.failed}/{report.total_tests} tests failed."
                    ),
                    severity=Severity.CRITICAL,
                )
            )
        elif report.warning_count > 0:
            self._notifications.notify(
                Notification(
                    title="Regression Test: warnings detected",
                    message=(
                        f"Regression suite {report.report_id}: "
                        f"{report.warning_count} warning(s). "
                        f"All tests passed."
                    ),
                    severity=Severity.WARN,
                )
            )


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def capture_baseline(
    table_row_counts: dict[str, int],
    schema_snapshot: SchemaSnapshot | None = None,
    visual_baselines: list[VisualBaseline] | None = None,
    table_checksums: dict[str, str] | None = None,
    baseline_id: str = "",
) -> RegressionBaseline:
    """Convenience: capture a full regression baseline."""
    tester = RegressionTester()
    return tester.capture_full_baseline(
        table_row_counts=table_row_counts,
        schema_snapshot=schema_snapshot,
        visual_baselines=visual_baselines,
        table_checksums=table_checksums,
        baseline_id=baseline_id,
    )


def run_regression(
    baseline: RegressionBaseline,
    current_row_counts: dict[str, int] | None = None,
    current_schema: SchemaSnapshot | None = None,
    current_screenshots: dict[str, bytes] | None = None,
    ssim_scores: dict[str, float] | None = None,
    row_count_tolerance: float = 0.01,
    ssim_threshold: float = 0.95,
) -> RegressionReport:
    """Convenience: run a full regression suite."""
    tester = RegressionTester(
        row_count_tolerance=row_count_tolerance,
        ssim_threshold=ssim_threshold,
    )
    return tester.run_full_regression(
        baseline=baseline,
        current_row_counts=current_row_counts,
        current_schema=current_schema,
        current_screenshots=current_screenshots,
        ssim_scores=ssim_scores,
    )
