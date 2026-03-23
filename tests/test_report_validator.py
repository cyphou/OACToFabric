"""Tests for report validator — visual counts, types, screenshots, slicers."""

from __future__ import annotations

import pytest

from src.agents.validation.report_validator import (
    ReportCheckResult,
    ReportCheckStatus,
    ReportCheckType,
    ReportTestCase,
    ReportValidationReport,
    evaluate_screenshot_diff,
    evaluate_visual_count,
    evaluate_visual_type,
    generate_drillthrough_tests,
    generate_slicer_tests,
    generate_visual_count_tests,
    generate_visual_type_tests,
    render_report_validation_report,
)


# ---------------------------------------------------------------------------
# Visual count tests
# ---------------------------------------------------------------------------


class TestGenerateVisualCountTests:
    def test_generates_per_page(self):
        oac = [
            {
                "name": "SalesReport",
                "pages": [
                    {"name": "Overview", "visual_count": 5},
                    {"name": "Detail", "visual_count": 3},
                ],
            },
        ]
        pbi = [
            {
                "name": "SalesReport",
                "pages": [
                    {"name": "Overview", "visual_count": 5},
                    {"name": "Detail", "visual_count": 3},
                ],
            },
        ]
        tests = generate_visual_count_tests(oac, pbi)
        assert len(tests) == 2

    def test_missing_pbi_report(self):
        oac = [{"name": "R1", "pages": [{"name": "P1", "visual_count": 4}]}]
        tests = generate_visual_count_tests(oac, [])
        assert len(tests) == 1
        assert tests[0].expected_value == 4

    def test_empty(self):
        assert generate_visual_count_tests([], []) == []


# ---------------------------------------------------------------------------
# Visual type tests
# ---------------------------------------------------------------------------


class TestGenerateVisualTypeTests:
    def test_generates(self):
        oac = [{"id": "v1", "report": "R", "page": "P", "type": "bar"}]
        pbi = [{"id": "v1", "report": "R", "page": "P", "type": "clusteredBarChart"}]
        mapping = {"bar": "clusteredBarChart"}
        tests = generate_visual_type_tests(oac, pbi, mapping)
        assert len(tests) == 1
        assert tests[0].expected_value == "clusteredBarChart"

    def test_no_mapping(self):
        oac = [{"id": "v1", "report": "R", "page": "P", "type": "line"}]
        tests = generate_visual_type_tests(oac, [])
        assert len(tests) == 1
        assert tests[0].expected_value == "line"

    def test_empty(self):
        assert generate_visual_type_tests([], []) == []


# ---------------------------------------------------------------------------
# Slicer tests
# ---------------------------------------------------------------------------


class TestGenerateSlicerTests:
    def test_generates(self):
        slicers = [
            {
                "report": "R",
                "page": "P",
                "slicer_type": "dropdown",
                "bound_column": "Region",
                "values": ["East", "West"],
            },
        ]
        tests = generate_slicer_tests(slicers)
        assert len(tests) == 1
        assert tests[0].check_type == ReportCheckType.SLICER_BEHAVIOUR

    def test_empty(self):
        assert generate_slicer_tests([]) == []


# ---------------------------------------------------------------------------
# Drillthrough tests
# ---------------------------------------------------------------------------


class TestGenerateDrillthroughTests:
    def test_generates(self):
        dts = [
            {
                "report": "R",
                "source_page": "Overview",
                "target_page": "Detail",
                "context_columns": ["ProductId"],
            },
        ]
        tests = generate_drillthrough_tests(dts)
        assert len(tests) == 1
        assert tests[0].expected_value == "Detail"

    def test_empty(self):
        assert generate_drillthrough_tests([]) == []


# ---------------------------------------------------------------------------
# Result evaluation
# ---------------------------------------------------------------------------


class TestEvaluateVisualCount:
    def test_pass(self):
        tc = ReportTestCase(
            check_type=ReportCheckType.VISUAL_COUNT,
            report_name="R", page_name="P", expected_value=5,
        )
        r = evaluate_visual_count(tc, 5)
        assert r.status == ReportCheckStatus.PASS

    def test_fail(self):
        tc = ReportTestCase(
            check_type=ReportCheckType.VISUAL_COUNT,
            report_name="R", page_name="P", expected_value=5,
        )
        r = evaluate_visual_count(tc, 4)
        assert r.status == ReportCheckStatus.FAIL


class TestEvaluateVisualType:
    def test_pass_case_insensitive(self):
        tc = ReportTestCase(
            check_type=ReportCheckType.VISUAL_TYPE,
            report_name="R", expected_value="clusteredBarChart",
        )
        r = evaluate_visual_type(tc, "ClusteredBarChart")
        assert r.status == ReportCheckStatus.PASS

    def test_fail(self):
        tc = ReportTestCase(
            check_type=ReportCheckType.VISUAL_TYPE,
            report_name="R", expected_value="bar",
        )
        r = evaluate_visual_type(tc, "line")
        assert r.status == ReportCheckStatus.FAIL


class TestEvaluateScreenshotDiff:
    def test_high_similarity_pass(self):
        r = evaluate_screenshot_diff("R", "P", 0.95)
        assert r.status == ReportCheckStatus.PASS

    def test_low_similarity_review(self):
        r = evaluate_screenshot_diff("R", "P", 0.70)
        assert r.status == ReportCheckStatus.MANUAL_REVIEW

    def test_very_low_fail(self):
        r = evaluate_screenshot_diff("R", "P", 0.50)
        assert r.status == ReportCheckStatus.FAIL

    def test_threshold(self):
        r = evaluate_screenshot_diff("R", "P", 0.85, threshold=0.85)
        assert r.status == ReportCheckStatus.PASS


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


class TestReportValidationReport:
    def test_add_and_counts(self):
        rpt = ReportValidationReport()
        rpt.add(ReportCheckResult(
            check_type=ReportCheckType.VISUAL_COUNT, report_name="R",
            status=ReportCheckStatus.PASS,
        ))
        rpt.add(ReportCheckResult(
            check_type=ReportCheckType.VISUAL_COUNT, report_name="R",
            status=ReportCheckStatus.FAIL,
        ))
        rpt.add(ReportCheckResult(
            check_type=ReportCheckType.SCREENSHOT_DIFF, report_name="R",
            status=ReportCheckStatus.MANUAL_REVIEW,
        ))
        assert rpt.total_checks == 3
        assert rpt.passed == 1
        assert rpt.failed == 1
        assert rpt.manual_review == 1

    def test_render(self):
        rpt = ReportValidationReport()
        rpt.add(ReportCheckResult(
            check_type=ReportCheckType.VISUAL_COUNT, report_name="Sales",
            page_name="Overview", expected_value=5, actual_value=4,
            status=ReportCheckStatus.FAIL,
        ))
        md = render_report_validation_report(rpt)
        assert "Report Validation Report" in md
        assert "Sales" in md
