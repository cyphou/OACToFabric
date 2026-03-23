"""Tests for data reconciliation — query generation, comparison, reporting."""

from __future__ import annotations

import pytest

from src.agents.validation.data_reconciliation import (
    CheckStatus,
    CheckType,
    ReconciliationQuery,
    ReconciliationReport,
    ReconciliationResult,
    compare_values,
    evaluate_result,
    generate_data_type_checks,
    generate_reconciliation_queries,
    render_reconciliation_report,
)


# ---------------------------------------------------------------------------
# Query generation
# ---------------------------------------------------------------------------


class TestGenerateReconciliationQueries:
    def _sample_inventory(self) -> list:
        return [
            {
                "source_name": "SALES",
                "target_name": "dbo.Sales",
                "columns": [
                    {"name": "Amount", "type": "number"},
                    {"name": "Region", "type": "varchar"},
                ],
            },
        ]

    def test_generates_row_count(self):
        queries = generate_reconciliation_queries(self._sample_inventory())
        row_counts = [q for q in queries if q.check_type == CheckType.ROW_COUNT]
        assert len(row_counts) == 1
        assert "COUNT(*)" in row_counts[0].oracle_sql
        assert "COUNT(*)" in row_counts[0].fabric_sql

    def test_generates_null_counts(self):
        queries = generate_reconciliation_queries(self._sample_inventory())
        nulls = [q for q in queries if q.check_type == CheckType.NULL_COUNT]
        assert len(nulls) == 2  # one per column

    def test_generates_distinct_counts(self):
        queries = generate_reconciliation_queries(self._sample_inventory())
        distincts = [q for q in queries if q.check_type == CheckType.DISTINCT_COUNT]
        assert len(distincts) == 2

    def test_generates_numeric_aggregates(self):
        queries = generate_reconciliation_queries(self._sample_inventory())
        sums = [q for q in queries if q.check_type == CheckType.AGGREGATE_SUM]
        assert len(sums) == 1  # only Amount is numeric
        avgs = [q for q in queries if q.check_type == CheckType.AGGREGATE_AVG]
        assert len(avgs) == 1

    def test_generates_min_max_for_numeric(self):
        queries = generate_reconciliation_queries(self._sample_inventory())
        mins = [q for q in queries if q.check_type == CheckType.MIN_VALUE]
        maxs = [q for q in queries if q.check_type == CheckType.MAX_VALUE]
        assert len(mins) == 1
        assert len(maxs) == 1

    def test_generates_sample_rows(self):
        queries = generate_reconciliation_queries(
            self._sample_inventory(), include_sample=True
        )
        samples = [q for q in queries if q.check_type == CheckType.SAMPLE_ROWS]
        assert len(samples) == 1

    def test_no_sample_when_disabled(self):
        queries = generate_reconciliation_queries(
            self._sample_inventory(), include_sample=False
        )
        samples = [q for q in queries if q.check_type == CheckType.SAMPLE_ROWS]
        assert len(samples) == 0

    def test_non_numeric_no_min_max(self):
        inv = [
            {
                "source_name": "T",
                "target_name": "T",
                "columns": [{"name": "Name", "type": "varchar"}],
            },
        ]
        queries = generate_reconciliation_queries(inv, include_sample=False)
        mins = [q for q in queries if q.check_type == CheckType.MIN_VALUE]
        assert len(mins) == 0

    def test_multiple_tables(self):
        inv = [
            {"source_name": "A", "target_name": "A", "columns": []},
            {"source_name": "B", "target_name": "B", "columns": []},
        ]
        queries = generate_reconciliation_queries(inv, include_sample=False)
        row_counts = [q for q in queries if q.check_type == CheckType.ROW_COUNT]
        assert len(row_counts) == 2

    def test_empty_inventory(self):
        assert generate_reconciliation_queries([]) == []


# ---------------------------------------------------------------------------
# Value comparison
# ---------------------------------------------------------------------------


class TestCompareValues:
    def test_both_none(self):
        status, v, pct = compare_values(None, None)
        assert status == CheckStatus.PASS

    def test_source_none(self):
        status, _, _ = compare_values(None, 42)
        assert status == CheckStatus.FAIL

    def test_target_none(self):
        status, _, _ = compare_values(42, None)
        assert status == CheckStatus.FAIL

    def test_exact_match(self):
        status, v, pct = compare_values(100, 100)
        assert status == CheckStatus.PASS
        assert v == 0

    def test_within_tolerance(self):
        status, v, pct = compare_values(100, 100.005, tolerance=0.01)
        assert status == CheckStatus.PASS

    def test_exceeds_tolerance(self):
        status, v, pct = compare_values(100, 200, tolerance=0.01)
        assert status == CheckStatus.FAIL

    def test_string_match(self):
        status, _, _ = compare_values("hello", "hello")
        assert status == CheckStatus.PASS

    def test_string_mismatch(self):
        status, _, _ = compare_values("hello", "world")
        assert status == CheckStatus.FAIL

    def test_zero_values(self):
        status, _, _ = compare_values(0, 0)
        assert status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# Result evaluation
# ---------------------------------------------------------------------------


class TestEvaluateResult:
    def test_pass(self):
        q = ReconciliationQuery(
            check_type=CheckType.ROW_COUNT,
            asset_name="Sales",
            tolerance=0,
        )
        r = evaluate_result(q, 1000, 1000, duration_ms=50)
        assert r.status == CheckStatus.PASS
        assert r.duration_ms == 50

    def test_fail(self):
        q = ReconciliationQuery(
            check_type=CheckType.ROW_COUNT,
            asset_name="Sales",
            tolerance=0,
        )
        r = evaluate_result(q, 1000, 999)
        assert r.status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# Data type checks
# ---------------------------------------------------------------------------


class TestDataTypeChecks:
    def test_generates(self):
        inv = [
            {
                "source_name": "T",
                "target_name": "T",
                "columns": [
                    {"name": "C1", "type": "NUMBER"},
                    {"name": "C2", "type": "VARCHAR2"},
                ],
            },
        ]
        checks = generate_data_type_checks(
            inv, {"NUMBER": "DECIMAL", "VARCHAR2": "VARCHAR"}
        )
        assert len(checks) == 2
        assert checks[0].check_type == CheckType.DATA_TYPE

    def test_empty(self):
        assert generate_data_type_checks([]) == []


# ---------------------------------------------------------------------------
# Reconciliation report
# ---------------------------------------------------------------------------


class TestReconciliationReport:
    def test_add_and_counts(self):
        rpt = ReconciliationReport()
        rpt.add(ReconciliationResult(
            check_type=CheckType.ROW_COUNT, asset_name="A",
            status=CheckStatus.PASS,
        ))
        rpt.add(ReconciliationResult(
            check_type=CheckType.ROW_COUNT, asset_name="B",
            status=CheckStatus.FAIL,
        ))
        assert rpt.total_checks == 2
        assert rpt.passed == 1
        assert rpt.failed == 1
        assert rpt.pass_rate == 50.0

    def test_empty_pass_rate(self):
        assert ReconciliationReport().pass_rate == 0.0


class TestRenderReport:
    def test_renders_markdown(self):
        rpt = ReconciliationReport()
        rpt.add(ReconciliationResult(
            check_type=CheckType.ROW_COUNT, asset_name="Sales",
            source_value=1000, target_value=999,
            status=CheckStatus.FAIL, variance_percent=0.1,
        ))
        md = render_reconciliation_report(rpt)
        assert "Data Reconciliation Report" in md
        assert "Sales" in md
        assert "FAIL" in md or "Failed" in md
