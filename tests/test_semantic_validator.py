"""Tests for semantic model validator — measure, relationship, hierarchy checks."""

from __future__ import annotations

import pytest

from src.agents.validation.semantic_validator import (
    SemanticCheckResult,
    SemanticCheckStatus,
    SemanticCheckType,
    SemanticTestCase,
    SemanticValidationReport,
    evaluate_semantic_result,
    generate_filter_context_tests,
    generate_hierarchy_tests,
    generate_measure_tests,
    generate_relationship_tests,
    render_semantic_report,
)


# ---------------------------------------------------------------------------
# Measure tests
# ---------------------------------------------------------------------------


class TestGenerateMeasureTests:
    def test_generates(self):
        measures = [
            {
                "name": "TotalSales",
                "table": "Sales",
                "dax_expression": "SUM(Sales[Amount])",
                "oac_expression": "SUM(Revenue)",
            },
        ]
        tests = generate_measure_tests(measures)
        assert len(tests) == 1
        assert tests[0].check_type == SemanticCheckType.MEASURE_RESULT
        assert "TotalSales" in tests[0].name
        assert "EVALUATE" in tests[0].dax_query

    def test_empty(self):
        assert generate_measure_tests([]) == []

    def test_multiple(self):
        measures = [
            {"name": "M1", "table": "T1", "dax_expression": "SUM(T1[A])"},
            {"name": "M2", "table": "T2", "dax_expression": "COUNT(T2[B])"},
        ]
        tests = generate_measure_tests(measures)
        assert len(tests) == 2


# ---------------------------------------------------------------------------
# Relationship tests
# ---------------------------------------------------------------------------


class TestGenerateRelationshipTests:
    def test_generates_join_and_orphan(self):
        rels = [
            {
                "from_table": "Sales",
                "from_column": "ProductId",
                "to_table": "Products",
                "to_column": "Id",
                "type": "M:1",
            },
        ]
        tests = generate_relationship_tests(rels)
        # 2 tests per relationship: join count + orphan check
        assert len(tests) == 2
        assert tests[0].check_type == SemanticCheckType.RELATIONSHIP

    def test_empty(self):
        assert generate_relationship_tests([]) == []


# ---------------------------------------------------------------------------
# Hierarchy tests
# ---------------------------------------------------------------------------


class TestGenerateHierarchyTests:
    def test_generates_per_level(self):
        hierarchies = [
            {
                "name": "Geography",
                "table": "Dim_Geography",
                "levels": ["Country", "Region", "City"],
                "measure": "COUNT(*)",
            },
        ]
        tests = generate_hierarchy_tests(hierarchies)
        assert len(tests) == 3  # one per level
        assert all(
            t.check_type == SemanticCheckType.HIERARCHY_DRILL for t in tests
        )
        assert "Level 1" in tests[0].name
        assert "Level 3" in tests[2].name

    def test_empty(self):
        assert generate_hierarchy_tests([]) == []


# ---------------------------------------------------------------------------
# Filter context tests
# ---------------------------------------------------------------------------


class TestGenerateFilterContextTests:
    def test_generates(self):
        filters = [
            {
                "table": "Sales",
                "column": "Region",
                "value": "East",
                "measure": "TotalSales",
            },
        ]
        tests = generate_filter_context_tests(filters)
        assert len(tests) == 1
        assert tests[0].check_type == SemanticCheckType.FILTER_CONTEXT
        assert "East" in tests[0].dax_query

    def test_empty(self):
        assert generate_filter_context_tests([]) == []


# ---------------------------------------------------------------------------
# Result evaluation
# ---------------------------------------------------------------------------


class TestEvaluateSemanticResult:
    def test_exact_match(self):
        tc = SemanticTestCase(
            check_type=SemanticCheckType.MEASURE_RESULT,
            name="Test",
            expected_tolerance=0.0001,
        )
        r = evaluate_semantic_result(tc, 100, 100)
        assert r.status == SemanticCheckStatus.PASS

    def test_within_tolerance(self):
        tc = SemanticTestCase(
            check_type=SemanticCheckType.MEASURE_RESULT,
            name="Test",
            expected_tolerance=0.01,
        )
        r = evaluate_semantic_result(tc, 100, 100.5)
        assert r.status == SemanticCheckStatus.PASS

    def test_exceeds_tolerance(self):
        tc = SemanticTestCase(
            check_type=SemanticCheckType.MEASURE_RESULT,
            name="Test",
            expected_tolerance=0.0001,
        )
        r = evaluate_semantic_result(tc, 100, 200)
        assert r.status == SemanticCheckStatus.FAIL

    def test_both_none_pass(self):
        tc = SemanticTestCase(
            check_type=SemanticCheckType.MEASURE_RESULT, name="Test"
        )
        r = evaluate_semantic_result(tc, None, None)
        assert r.status == SemanticCheckStatus.PASS

    def test_one_none_fail(self):
        tc = SemanticTestCase(
            check_type=SemanticCheckType.MEASURE_RESULT, name="Test"
        )
        r = evaluate_semantic_result(tc, 100, None)
        assert r.status == SemanticCheckStatus.FAIL

    def test_string_match(self):
        tc = SemanticTestCase(
            check_type=SemanticCheckType.MEASURE_RESULT, name="Test"
        )
        r = evaluate_semantic_result(tc, "hello", "hello")
        assert r.status == SemanticCheckStatus.PASS

    def test_string_mismatch(self):
        tc = SemanticTestCase(
            check_type=SemanticCheckType.MEASURE_RESULT, name="Test"
        )
        r = evaluate_semantic_result(tc, "hello", "world")
        assert r.status == SemanticCheckStatus.FAIL


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


class TestSemanticReport:
    def test_add_and_counts(self):
        rpt = SemanticValidationReport()
        rpt.add(SemanticCheckResult(
            check_type=SemanticCheckType.MEASURE_RESULT, name="M1",
            status=SemanticCheckStatus.PASS,
        ))
        rpt.add(SemanticCheckResult(
            check_type=SemanticCheckType.MEASURE_RESULT, name="M2",
            status=SemanticCheckStatus.FAIL,
        ))
        assert rpt.total_checks == 2
        assert rpt.passed == 1
        assert rpt.failed == 1
        assert rpt.pass_rate == 50.0

    def test_render(self):
        rpt = SemanticValidationReport()
        rpt.add(SemanticCheckResult(
            check_type=SemanticCheckType.MEASURE_RESULT, name="M1",
            oac_value=100, pbi_value=99, status=SemanticCheckStatus.FAIL,
        ))
        md = render_semantic_report(rpt)
        assert "Semantic Model Validation Report" in md
        assert "M1" in md
