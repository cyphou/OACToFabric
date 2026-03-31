"""Phase 52 — Automated Regression Testing tests.

Covers:
* DataBaseline serialization (to_json / from_json)
* VisualBaseline creation (hash computation)
* RegressionBaseline full capture
* RegressionFinding / VisualRegressionFinding data classes
* RegressionReport: add_result, to_dict, generate_markdown, counters
* RegressionSchedule defaults & custom values
* RegressionTester:
    - capture_data_baseline
    - capture_visual_baseline
    - capture_full_baseline
    - run_data_regression (row count drift, new/missing tables, checksums)
    - run_schema_regression (drift detection integration)
    - run_visual_regression (hash & SSIM paths)
    - run_full_regression (combined suite, selective types)
    - notification integration (critical/warning)
* Convenience wrappers: capture_baseline, run_regression
"""

from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from src.agents.orchestrator.notification_manager import (
    Channel,
    Notification,
    NotificationManager,
    Severity,
)
from src.agents.validation.schema_drift import (
    ColumnSnapshot,
    DriftItem,
    DriftReport,
    SchemaSnapshot,
    TableSnapshot,
    compare_snapshots,
)
from src.core.regression_tester import (
    DataBaseline,
    RegressionBaseline,
    RegressionFinding,
    RegressionReport,
    RegressionSchedule,
    RegressionSeverity,
    RegressionTester,
    RegressionTestResult,
    RegressionType,
    ScheduleFrequency,
    VisualBaseline,
    VisualRegressionFinding,
    capture_baseline,
    run_regression,
)


# ============================================================================
# Helpers
# ============================================================================


def _schema_snapshot(
    sid: str, tables: list[tuple[str, list[tuple[str, str]]]] | None = None
) -> SchemaSnapshot:
    """Build a SchemaSnapshot from ``[(table, [(col, type)])]``."""
    snap = SchemaSnapshot(snapshot_id=sid, captured_at="2025-01-01T00:00:00Z")
    for tname, cols in tables or []:
        ts = TableSnapshot(table_name=tname)
        for cname, dtype in cols:
            ts.columns.append(ColumnSnapshot(name=cname, data_type=dtype))
        snap.tables.append(ts)
    return snap


# ============================================================================
# DataBaseline
# ============================================================================


class TestDataBaseline(unittest.TestCase):
    """DataBaseline construction and serialization."""

    def test_basic_creation(self):
        bl = DataBaseline(
            baseline_id="bl-1",
            captured_at="2025-01-01",
            table_row_counts={"t1": 100, "t2": 200},
        )
        self.assertEqual(bl.baseline_id, "bl-1")
        self.assertEqual(bl.table_row_counts["t1"], 100)

    def test_to_json_roundtrip(self):
        bl = DataBaseline(
            baseline_id="bl-rt",
            captured_at="2025-06-01",
            table_row_counts={"orders": 500},
            table_checksums={"orders": "abc123"},
        )
        j = bl.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["baselineId"], "bl-rt")
        self.assertIn("orders", parsed["tableRowCounts"])
        self.assertEqual(parsed["tableChecksums"]["orders"], "abc123")

    def test_from_json_roundtrip(self):
        original = DataBaseline(
            baseline_id="bl-round",
            captured_at="2025-06-01",
            table_row_counts={"a": 10, "b": 20},
            table_checksums={"a": "h1"},
        )
        restored = DataBaseline.from_json(original.to_json())
        self.assertEqual(restored.baseline_id, original.baseline_id)
        self.assertEqual(restored.table_row_counts, original.table_row_counts)
        self.assertEqual(restored.table_checksums, original.table_checksums)

    def test_from_json_empty_checksums(self):
        bl = DataBaseline(baseline_id="e", captured_at="", table_row_counts={"x": 1})
        restored = DataBaseline.from_json(bl.to_json())
        self.assertEqual(restored.table_checksums, {})


# ============================================================================
# VisualBaseline
# ============================================================================


class TestVisualBaseline(unittest.TestCase):
    """VisualBaseline data class."""

    def test_fields(self):
        vb = VisualBaseline(
            report_name="Sales",
            page_name="Overview",
            screenshot_hash="abc",
            captured_at="2025-01-01",
            width=1920,
            height=1080,
        )
        self.assertEqual(vb.report_name, "Sales")
        self.assertEqual(vb.width, 1920)

    def test_defaults(self):
        vb = VisualBaseline(
            report_name="R", page_name="P", screenshot_hash="h", captured_at="t"
        )
        self.assertEqual(vb.width, 0)
        self.assertEqual(vb.height, 0)


# ============================================================================
# RegressionBaseline
# ============================================================================


class TestRegressionBaseline(unittest.TestCase):
    """RegressionBaseline composite dataclass."""

    def test_creation(self):
        bl = RegressionBaseline(
            baseline_id="rb-1",
            captured_at="2025-01-01",
            data_baseline=DataBaseline(
                baseline_id="d1", captured_at="", table_row_counts={"t": 5}
            ),
        )
        self.assertIsNotNone(bl.data_baseline)
        self.assertIsNone(bl.schema_baseline)
        self.assertEqual(bl.visual_baselines, [])

    def test_to_json(self):
        bl = RegressionBaseline(
            baseline_id="rb-j",
            captured_at="2025-01-01",
            data_baseline=DataBaseline(
                baseline_id="d2", captured_at="", table_row_counts={"x": 1}
            ),
        )
        j = bl.to_json()
        data = json.loads(j)
        self.assertEqual(data["baselineId"], "rb-j")


# ============================================================================
# RegressionFinding / VisualRegressionFinding
# ============================================================================


class TestRegressionFinding(unittest.TestCase):
    def test_finding_defaults(self):
        f = RegressionFinding(
            finding_id="f1",
            regression_type=RegressionType.DATA,
            severity=RegressionSeverity.WARNING,
            table_name="t",
            description="desc",
        )
        self.assertIsNone(f.baseline_value)
        self.assertIsNone(f.current_value)
        self.assertEqual(f.details, {})
        self.assertAlmostEqual(f.variance, 0.0)

    def test_visual_finding(self):
        vf = VisualRegressionFinding(
            finding_id="vf1",
            severity=RegressionSeverity.CRITICAL,
            report_name="R",
            page_name="P",
            description="visual drift",
            ssim_score=0.75,
            threshold=0.95,
        )
        self.assertEqual(vf.regression_type, RegressionType.VISUAL)
        self.assertAlmostEqual(vf.ssim_score, 0.75)


# ============================================================================
# RegressionTestResult
# ============================================================================


class TestRegressionTestResult(unittest.TestCase):
    def test_defaults(self):
        r = RegressionTestResult(
            test_id="t1",
            regression_type=RegressionType.DATA,
            executed_at="now",
        )
        self.assertTrue(r.passed)
        self.assertEqual(r.findings, [])

    def test_with_findings(self):
        r = RegressionTestResult(
            test_id="t2",
            regression_type=RegressionType.SCHEMA,
            executed_at="now",
            passed=False,
            findings=[
                RegressionFinding(
                    finding_id="x",
                    regression_type=RegressionType.SCHEMA,
                    severity=RegressionSeverity.CRITICAL,
                    table_name="t",
                    description="drop",
                )
            ],
        )
        self.assertFalse(r.passed)
        self.assertEqual(len(r.findings), 1)


# ============================================================================
# RegressionReport
# ============================================================================


class TestRegressionReport(unittest.TestCase):
    """RegressionReport — add_result, counters, to_dict, markdown."""

    def _make_report(self) -> RegressionReport:
        rpt = RegressionReport(
            report_id="rpt-1", baseline_id="bl-1", executed_at="2025-01-01"
        )
        passing = RegressionTestResult(
            test_id="pass1",
            regression_type=RegressionType.DATA,
            executed_at="now",
            passed=True,
        )
        failing = RegressionTestResult(
            test_id="fail1",
            regression_type=RegressionType.SCHEMA,
            executed_at="now",
            passed=False,
            findings=[
                RegressionFinding(
                    finding_id="c1",
                    regression_type=RegressionType.SCHEMA,
                    severity=RegressionSeverity.CRITICAL,
                    table_name="t",
                    description="col dropped",
                ),
                RegressionFinding(
                    finding_id="w1",
                    regression_type=RegressionType.SCHEMA,
                    severity=RegressionSeverity.WARNING,
                    table_name="t2",
                    description="type change",
                ),
            ],
        )
        rpt.add_result(passing)
        rpt.add_result(failing)
        return rpt

    def test_counters(self):
        rpt = self._make_report()
        self.assertEqual(rpt.total_tests, 2)
        self.assertEqual(rpt.passed, 1)
        self.assertEqual(rpt.failed, 1)
        self.assertEqual(rpt.finding_count, 2)
        self.assertEqual(rpt.critical_count, 1)
        self.assertEqual(rpt.warning_count, 1)

    def test_to_dict(self):
        rpt = self._make_report()
        d = rpt.to_dict()
        self.assertEqual(d["reportId"], "rpt-1")
        self.assertEqual(d["totalTests"], 2)
        self.assertIn("findings", d)

    def test_generate_markdown(self):
        rpt = self._make_report()
        md = rpt.generate_markdown()
        self.assertIn("# Regression Test Report", md)
        self.assertIn("rpt-1", md)
        self.assertIn("critical", md)
        self.assertIn("col dropped", md)

    def test_empty_report(self):
        rpt = RegressionReport(
            report_id="empty", baseline_id="bl", executed_at="now"
        )
        self.assertEqual(rpt.total_tests, 0)
        self.assertEqual(rpt.finding_count, 0)
        md = rpt.generate_markdown()
        self.assertIn("Regression Test Report", md)


# ============================================================================
# RegressionSchedule
# ============================================================================


class TestRegressionSchedule(unittest.TestCase):
    def test_defaults(self):
        s = RegressionSchedule(schedule_id="s1")
        self.assertEqual(s.frequency, ScheduleFrequency.DAILY)
        self.assertAlmostEqual(s.row_count_tolerance, 0.01)
        self.assertAlmostEqual(s.ssim_threshold, 0.95)
        self.assertTrue(s.enabled)

    def test_custom(self):
        s = RegressionSchedule(
            schedule_id="s2",
            frequency=ScheduleFrequency.HOURLY,
            row_count_tolerance=0.05,
            ssim_threshold=0.80,
            test_types=[RegressionType.DATA],
            enabled=False,
        )
        self.assertEqual(s.frequency, ScheduleFrequency.HOURLY)
        self.assertEqual(s.test_types, [RegressionType.DATA])
        self.assertFalse(s.enabled)


# ============================================================================
# RegressionTester — Baseline Capture
# ============================================================================


class TestRegressionTesterCapture(unittest.TestCase):
    """Tests for baseline capture methods."""

    def test_capture_data_baseline(self):
        t = RegressionTester()
        bl = t.capture_data_baseline(
            table_row_counts={"a": 10, "b": 20},
            table_checksums={"a": "h1"},
        )
        self.assertEqual(bl.table_row_counts["a"], 10)
        self.assertEqual(bl.table_checksums["a"], "h1")
        self.assertTrue(bl.baseline_id)  # auto-generated
        self.assertTrue(bl.captured_at)

    def test_capture_data_baseline_custom_id(self):
        t = RegressionTester()
        bl = t.capture_data_baseline(
            table_row_counts={"x": 1}, baseline_id="my-bl"
        )
        self.assertEqual(bl.baseline_id, "my-bl")

    def test_capture_visual_baseline(self):
        t = RegressionTester()
        data = b"fake screenshot bytes"
        vb = t.capture_visual_baseline(
            report_name="Sales",
            page_name="Overview",
            screenshot_bytes=data,
            width=1920,
            height=1080,
        )
        expected_hash = hashlib.sha256(data).hexdigest()
        self.assertEqual(vb.screenshot_hash, expected_hash)
        self.assertEqual(vb.report_name, "Sales")
        self.assertEqual(vb.width, 1920)

    def test_capture_full_baseline_data_only(self):
        t = RegressionTester()
        bl = t.capture_full_baseline(table_row_counts={"t1": 100})
        self.assertIsNotNone(bl.data_baseline)
        self.assertIsNone(bl.schema_baseline)
        self.assertEqual(bl.visual_baselines, [])

    def test_capture_full_baseline_all_types(self):
        t = RegressionTester()
        schema = _schema_snapshot("s1", [("t1", [("id", "int")])])
        vb = t.capture_visual_baseline("R", "P", b"img")
        bl = t.capture_full_baseline(
            table_row_counts={"t1": 50},
            schema_snapshot=schema,
            visual_baselines=[vb],
            table_checksums={"t1": "ck"},
            baseline_id="full-bl",
        )
        self.assertEqual(bl.baseline_id, "full-bl")
        self.assertIsNotNone(bl.schema_baseline)
        self.assertEqual(len(bl.visual_baselines), 1)
        self.assertEqual(bl.data_baseline.table_checksums["t1"], "ck")


# ============================================================================
# RegressionTester — Data Regression
# ============================================================================


class TestRunDataRegression(unittest.TestCase):
    """Tests for run_data_regression."""

    def test_no_drift(self):
        t = RegressionTester(row_count_tolerance=0.01)
        bl = DataBaseline(
            baseline_id="b", captured_at="", table_row_counts={"t1": 1000}
        )
        result = t.run_data_regression(bl, {"t1": 1000})
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_within_tolerance(self):
        t = RegressionTester(row_count_tolerance=0.05)
        bl = DataBaseline(
            baseline_id="b", captured_at="", table_row_counts={"t1": 1000}
        )
        # 3% drift — within 5% tolerance
        result = t.run_data_regression(bl, {"t1": 1030})
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_warning_drift(self):
        t = RegressionTester(row_count_tolerance=0.01)
        bl = DataBaseline(
            baseline_id="b", captured_at="", table_row_counts={"t1": 1000}
        )
        # 5% drift → WARNING (> tolerance but ≤ 10%)
        result = t.run_data_regression(bl, {"t1": 1050})
        self.assertTrue(result.passed)  # warnings don't fail
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].severity, RegressionSeverity.WARNING)

    def test_critical_drift(self):
        t = RegressionTester(row_count_tolerance=0.01)
        bl = DataBaseline(
            baseline_id="b", captured_at="", table_row_counts={"t1": 1000}
        )
        # 50% drift → CRITICAL (> 10%)
        result = t.run_data_regression(bl, {"t1": 1500})
        self.assertFalse(result.passed)
        self.assertEqual(result.findings[0].severity, RegressionSeverity.CRITICAL)

    def test_new_table_detected(self):
        t = RegressionTester()
        bl = DataBaseline(
            baseline_id="b", captured_at="", table_row_counts={"t1": 100}
        )
        result = t.run_data_regression(bl, {"t1": 100, "t2": 50})
        # New table is a warning, test still passes
        self.assertTrue(result.passed)
        new_findings = [f for f in result.findings if "New table" in f.description]
        self.assertEqual(len(new_findings), 1)

    def test_missing_table_critical(self):
        t = RegressionTester()
        bl = DataBaseline(
            baseline_id="b",
            captured_at="",
            table_row_counts={"t1": 100, "t2": 200},
        )
        # t2 missing in current
        result = t.run_data_regression(bl, {"t1": 100})
        self.assertFalse(result.passed)
        missing = [f for f in result.findings if "missing" in f.description.lower()]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].severity, RegressionSeverity.CRITICAL)

    def test_checksum_drift(self):
        t = RegressionTester()
        bl = DataBaseline(
            baseline_id="b",
            captured_at="",
            table_row_counts={"t1": 100},
            table_checksums={"t1": "hash_original"},
        )
        result = t.run_data_regression(
            bl, {"t1": 100}, current_checksums={"t1": "hash_changed"}
        )
        # Checksum change is a WARNING
        ck_findings = [f for f in result.findings if "Checksum" in f.description]
        self.assertEqual(len(ck_findings), 1)
        self.assertEqual(ck_findings[0].severity, RegressionSeverity.WARNING)

    def test_checksum_no_drift(self):
        t = RegressionTester()
        bl = DataBaseline(
            baseline_id="b",
            captured_at="",
            table_row_counts={"t1": 100},
            table_checksums={"t1": "same_hash"},
        )
        result = t.run_data_regression(
            bl, {"t1": 100}, current_checksums={"t1": "same_hash"}
        )
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_zero_baseline_rows(self):
        """Baseline with 0 rows → any current > 0 is 100% variance."""
        t = RegressionTester(row_count_tolerance=0.01)
        bl = DataBaseline(
            baseline_id="b", captured_at="", table_row_counts={"t1": 0}
        )
        result = t.run_data_regression(bl, {"t1": 10})
        self.assertFalse(result.passed)
        self.assertEqual(len(result.findings), 1)

    def test_regression_type_is_data(self):
        t = RegressionTester()
        bl = DataBaseline(
            baseline_id="b", captured_at="", table_row_counts={"t1": 100}
        )
        result = t.run_data_regression(bl, {"t1": 100})
        self.assertEqual(result.regression_type, RegressionType.DATA)


# ============================================================================
# RegressionTester — Schema Regression
# ============================================================================


class TestRunSchemaRegression(unittest.TestCase):
    """Tests for run_schema_regression."""

    def test_no_drift(self):
        t = RegressionTester()
        base = _schema_snapshot("s1", [("t1", [("id", "int"), ("name", "varchar")])])
        curr = _schema_snapshot("s2", [("t1", [("id", "int"), ("name", "varchar")])])
        result = t.run_schema_regression(base, curr)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_added_table(self):
        t = RegressionTester()
        base = _schema_snapshot("s1", [("t1", [("id", "int")])])
        curr = _schema_snapshot(
            "s2", [("t1", [("id", "int")]), ("t2", [("id", "int")])]
        )
        result = t.run_schema_regression(base, curr)
        self.assertEqual(result.regression_type, RegressionType.SCHEMA)
        added = [f for f in result.findings if "added" in f.finding_id.lower() or "added" in f.description.lower()]
        self.assertGreater(len(added), 0)

    def test_dropped_table_critical(self):
        t = RegressionTester()
        base = _schema_snapshot(
            "s1", [("t1", [("id", "int")]), ("t2", [("col", "varchar")])]
        )
        curr = _schema_snapshot("s2", [("t1", [("id", "int")])])
        result = t.run_schema_regression(base, curr)
        # Dropped table should appear as a finding
        self.assertGreater(len(result.findings), 0)

    def test_column_type_change(self):
        t = RegressionTester()
        base = _schema_snapshot("s1", [("t1", [("id", "int"), ("val", "varchar")])])
        curr = _schema_snapshot("s2", [("t1", [("id", "int"), ("val", "text")])])
        result = t.run_schema_regression(base, curr)
        type_findings = [
            f for f in result.findings if "type" in f.description.lower()
        ]
        self.assertGreater(len(type_findings), 0)


# ============================================================================
# RegressionTester — Visual Regression
# ============================================================================


class TestRunVisualRegression(unittest.TestCase):
    """Tests for run_visual_regression."""

    def _baseline(self, data: bytes = b"screenshot") -> VisualBaseline:
        return VisualBaseline(
            report_name="Sales",
            page_name="Overview",
            screenshot_hash=hashlib.sha256(data).hexdigest(),
            captured_at="2025-01-01",
        )

    def test_identical_screenshots(self):
        t = RegressionTester()
        bl = [self._baseline(b"screenshot")]
        current = {"Sales/Overview": b"screenshot"}
        result = t.run_visual_regression(bl, current)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_hash_mismatch_warning(self):
        t = RegressionTester()
        bl = [self._baseline(b"screenshot_v1")]
        current = {"Sales/Overview": b"screenshot_v2"}
        result = t.run_visual_regression(bl, current)
        # Hash-only comparison → WARNING (not enough info for CRITICAL)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].severity, RegressionSeverity.WARNING)

    def test_missing_screenshot_critical(self):
        t = RegressionTester()
        bl = [self._baseline()]
        result = t.run_visual_regression(bl, {})  # empty screenshots
        self.assertFalse(result.passed)
        self.assertEqual(result.findings[0].severity, RegressionSeverity.CRITICAL)

    def test_ssim_pass(self):
        t = RegressionTester(ssim_threshold=0.95)
        bl = [self._baseline(b"original")]
        current = {"Sales/Overview": b"slightly_different"}
        ssim = {"Sales/Overview": 0.98}  # above threshold
        result = t.run_visual_regression(bl, current, ssim_scores=ssim)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_ssim_warning(self):
        t = RegressionTester(ssim_threshold=0.95)
        bl = [self._baseline(b"original")]
        current = {"Sales/Overview": b"different"}
        ssim = {"Sales/Overview": 0.90}  # below threshold but > 0.8
        result = t.run_visual_regression(bl, current, ssim_scores=ssim)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].severity, RegressionSeverity.WARNING)

    def test_ssim_critical(self):
        t = RegressionTester(ssim_threshold=0.95)
        bl = [self._baseline(b"original")]
        current = {"Sales/Overview": b"very_different"}
        ssim = {"Sales/Overview": 0.50}  # very low
        result = t.run_visual_regression(bl, current, ssim_scores=ssim)
        self.assertFalse(result.passed)
        self.assertEqual(result.findings[0].severity, RegressionSeverity.CRITICAL)
        # VisualRegressionFinding should carry ssim_score
        self.assertIsInstance(result.findings[0], VisualRegressionFinding)
        self.assertAlmostEqual(result.findings[0].ssim_score, 0.50)

    def test_regression_type_is_visual(self):
        t = RegressionTester()
        result = t.run_visual_regression([], {})
        self.assertEqual(result.regression_type, RegressionType.VISUAL)


# ============================================================================
# RegressionTester — Full Regression Suite
# ============================================================================


class TestRunFullRegression(unittest.TestCase):
    """Tests for run_full_regression."""

    def _baseline(self) -> RegressionBaseline:
        schema = _schema_snapshot("s1", [("t1", [("id", "int")])])
        vb = VisualBaseline(
            report_name="R",
            page_name="P",
            screenshot_hash=hashlib.sha256(b"img").hexdigest(),
            captured_at="now",
        )
        return RegressionBaseline(
            baseline_id="full",
            captured_at="2025-01-01",
            data_baseline=DataBaseline(
                baseline_id="d", captured_at="", table_row_counts={"t1": 100}
            ),
            schema_baseline=schema,
            visual_baselines=[vb],
        )

    def test_all_pass(self):
        t = RegressionTester()
        bl = self._baseline()
        curr_schema = _schema_snapshot("s2", [("t1", [("id", "int")])])
        report = t.run_full_regression(
            baseline=bl,
            current_row_counts={"t1": 100},
            current_schema=curr_schema,
            current_screenshots={"R/P": b"img"},
        )
        self.assertEqual(report.total_tests, 3)
        self.assertEqual(report.passed, 3)
        self.assertEqual(report.failed, 0)

    def test_data_only(self):
        t = RegressionTester()
        bl = self._baseline()
        report = t.run_full_regression(
            baseline=bl,
            current_row_counts={"t1": 100},
            test_types=[RegressionType.DATA],
        )
        # Should only run data test
        self.assertEqual(report.total_tests, 1)

    def test_selective_types(self):
        t = RegressionTester()
        bl = self._baseline()
        curr_schema = _schema_snapshot("s2", [("t1", [("id", "int")])])
        report = t.run_full_regression(
            baseline=bl,
            current_row_counts={"t1": 100},
            current_schema=curr_schema,
            test_types=[RegressionType.DATA, RegressionType.SCHEMA],
        )
        self.assertEqual(report.total_tests, 2)

    def test_skip_when_no_current_data(self):
        """If current_row_counts is None, data regression is skipped."""
        t = RegressionTester()
        bl = self._baseline()
        report = t.run_full_regression(baseline=bl)
        self.assertEqual(report.total_tests, 0)

    def test_completed_at_set(self):
        t = RegressionTester()
        bl = self._baseline()
        report = t.run_full_regression(
            baseline=bl, current_row_counts={"t1": 100}
        )
        self.assertIsNotNone(report.completed_at)
        self.assertNotEqual(report.completed_at, "")


# ============================================================================
# Notification Integration
# ============================================================================


class TestNotificationIntegration(unittest.TestCase):
    """Verify notifications fire on critical / warning findings."""

    def test_critical_notification_sent(self):
        nm = MagicMock(spec=NotificationManager)
        t = RegressionTester(notification_manager=nm)
        bl = RegressionBaseline(
            baseline_id="n1",
            captured_at="",
            data_baseline=DataBaseline(
                baseline_id="d",
                captured_at="",
                table_row_counts={"t1": 100, "t2": 200},
            ),
        )
        # t2 missing → CRITICAL
        report = t.run_full_regression(
            baseline=bl, current_row_counts={"t1": 100}
        )
        nm.notify.assert_called_once()
        call_args = nm.notify.call_args[0][0]
        self.assertEqual(call_args.severity, Severity.CRITICAL)

    def test_warning_notification_sent(self):
        nm = MagicMock(spec=NotificationManager)
        t = RegressionTester(
            notification_manager=nm, row_count_tolerance=0.01
        )
        bl = RegressionBaseline(
            baseline_id="n2",
            captured_at="",
            data_baseline=DataBaseline(
                baseline_id="d",
                captured_at="",
                table_row_counts={"t1": 1000},
            ),
        )
        # 5% drift → WARNING only
        report = t.run_full_regression(
            baseline=bl, current_row_counts={"t1": 1050}
        )
        nm.notify.assert_called_once()
        call_args = nm.notify.call_args[0][0]
        self.assertEqual(call_args.severity, Severity.WARN)

    def test_no_notification_when_clean(self):
        nm = MagicMock(spec=NotificationManager)
        t = RegressionTester(notification_manager=nm)
        bl = RegressionBaseline(
            baseline_id="n3",
            captured_at="",
            data_baseline=DataBaseline(
                baseline_id="d",
                captured_at="",
                table_row_counts={"t1": 100},
            ),
        )
        report = t.run_full_regression(
            baseline=bl, current_row_counts={"t1": 100}
        )
        nm.notify.assert_not_called()

    def test_no_notification_when_manager_absent(self):
        """No crash when notification_manager is None."""
        t = RegressionTester()  # no notification manager
        bl = RegressionBaseline(
            baseline_id="n4",
            captured_at="",
            data_baseline=DataBaseline(
                baseline_id="d",
                captured_at="",
                table_row_counts={"t1": 100, "t2": 200},
            ),
        )
        # Should not raise even with critical findings
        report = t.run_full_regression(
            baseline=bl, current_row_counts={"t1": 100}
        )
        self.assertGreater(report.critical_count, 0)


# ============================================================================
# Convenience Functions
# ============================================================================


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for module-level capture_baseline and run_regression wrappers."""

    def test_capture_baseline(self):
        bl = capture_baseline(
            table_row_counts={"t1": 10, "t2": 20},
            baseline_id="conv-bl",
        )
        self.assertEqual(bl.baseline_id, "conv-bl")
        self.assertIsNotNone(bl.data_baseline)

    def test_capture_baseline_with_schema(self):
        schema = _schema_snapshot("s1", [("t1", [("id", "int")])])
        bl = capture_baseline(
            table_row_counts={"t1": 10},
            schema_snapshot=schema,
        )
        self.assertIsNotNone(bl.schema_baseline)

    def test_run_regression_clean(self):
        bl = capture_baseline(table_row_counts={"t1": 100})
        rpt = run_regression(
            baseline=bl, current_row_counts={"t1": 100}
        )
        self.assertEqual(rpt.total_tests, 1)
        self.assertEqual(rpt.passed, 1)

    def test_run_regression_with_drift(self):
        bl = capture_baseline(table_row_counts={"t1": 100})
        rpt = run_regression(
            baseline=bl,
            current_row_counts={"t1": 200},
            row_count_tolerance=0.01,
        )
        self.assertGreater(rpt.finding_count, 0)

    def test_run_regression_custom_thresholds(self):
        bl = capture_baseline(table_row_counts={"t1": 100})
        rpt = run_regression(
            baseline=bl,
            current_row_counts={"t1": 108},
            row_count_tolerance=0.10,  # 10% tolerance
        )
        # 8% drift within 10% tolerance
        self.assertEqual(rpt.finding_count, 0)


# ============================================================================
# Enums
# ============================================================================


class TestEnumValues(unittest.TestCase):
    """Verify enum members and string values."""

    def test_regression_severity(self):
        self.assertEqual(RegressionSeverity.INFO, "info")
        self.assertEqual(RegressionSeverity.WARNING, "warning")
        self.assertEqual(RegressionSeverity.CRITICAL, "critical")

    def test_regression_type(self):
        self.assertEqual(RegressionType.DATA, "data")
        self.assertEqual(RegressionType.SCHEMA, "schema")
        self.assertEqual(RegressionType.VISUAL, "visual")

    def test_schedule_frequency(self):
        self.assertEqual(ScheduleFrequency.HOURLY, "hourly")
        self.assertEqual(ScheduleFrequency.DAILY, "daily")
        self.assertEqual(ScheduleFrequency.WEEKLY, "weekly")
        self.assertEqual(ScheduleFrequency.ON_DEMAND, "on_demand")


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases(unittest.TestCase):
    """Boundary and edge-case scenarios."""

    def test_empty_tables(self):
        """Regression with no tables at all."""
        t = RegressionTester()
        bl = DataBaseline(baseline_id="e", captured_at="", table_row_counts={})
        result = t.run_data_regression(bl, {})
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_large_number_of_tables(self):
        """Regression across many tables."""
        t = RegressionTester(row_count_tolerance=0.01)
        counts = {f"table_{i}": 1000 for i in range(100)}
        bl = DataBaseline(baseline_id="lg", captured_at="", table_row_counts=counts)
        result = t.run_data_regression(bl, counts)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_multiple_visual_baselines(self):
        """Multiple pages with mixed results."""
        t = RegressionTester()
        bl1 = VisualBaseline(
            report_name="R", page_name="P1",
            screenshot_hash=hashlib.sha256(b"p1").hexdigest(),
            captured_at="now",
        )
        bl2 = VisualBaseline(
            report_name="R", page_name="P2",
            screenshot_hash=hashlib.sha256(b"p2").hexdigest(),
            captured_at="now",
        )
        current = {"R/P1": b"p1", "R/P2": b"different_p2"}
        result = t.run_visual_regression([bl1, bl2], current)
        # P1 matches, P2 doesn't
        self.assertEqual(len(result.findings), 1)
        self.assertIn("P2", result.findings[0].page_name)

    def test_data_baseline_from_json_minimal(self):
        """Minimal JSON with no optional fields."""
        j = json.dumps({
            "baselineId": "min",
            "capturedAt": "t",
            "tableRowCounts": {},
        })
        bl = DataBaseline.from_json(j)
        self.assertEqual(bl.baseline_id, "min")
        self.assertEqual(bl.table_row_counts, {})


if __name__ == "__main__":
    unittest.main()
