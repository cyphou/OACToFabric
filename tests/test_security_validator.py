"""Tests for security validator — RLS, OLS, cross-role, negative tests."""

from __future__ import annotations

import pytest

from src.agents.validation.security_validator import (
    SecurityCheckResult,
    SecurityCheckStatus,
    SecurityCheckType,
    SecurityTestCase,
    SecurityValidationReport,
    evaluate_negative_test,
    evaluate_ols_visibility,
    evaluate_rls_row_count,
    generate_cross_role_tests,
    generate_negative_tests,
    generate_ols_visibility_tests,
    generate_rls_data_content_tests,
    generate_rls_row_count_tests,
    render_security_validation_report,
)


# ---------------------------------------------------------------------------
# RLS row count tests
# ---------------------------------------------------------------------------


class TestGenerateRLSRowCountTests:
    def test_generates(self):
        roles = [
            {
                "role_name": "RegionalSales",
                "test_user": "alice@corp.com",
                "table_permissions": [
                    {"table_name": "Sales", "filter_expression": "..."},
                    {"table_name": "Inventory", "filter_expression": "..."},
                ],
            },
        ]
        tests = generate_rls_row_count_tests(roles)
        assert len(tests) == 2
        assert all(
            t.check_type == SecurityCheckType.RLS_ROW_COUNT for t in tests
        )

    def test_empty(self):
        assert generate_rls_row_count_tests([]) == []


# ---------------------------------------------------------------------------
# RLS data content tests
# ---------------------------------------------------------------------------


class TestGenerateRLSDataContentTests:
    def test_generates(self):
        roles = [
            {
                "role_name": "R1",
                "test_user": "u1",
                "table_permissions": [
                    {"table_name": "Sales", "filter_expression": "x"},
                ],
            },
        ]
        tests = generate_rls_data_content_tests(roles)
        assert len(tests) == 1
        assert tests[0].check_type == SecurityCheckType.RLS_DATA_CONTENT
        assert "TOPN" in tests[0].dax_query

    def test_empty(self):
        assert generate_rls_data_content_tests([]) == []


# ---------------------------------------------------------------------------
# OLS visibility tests
# ---------------------------------------------------------------------------


class TestGenerateOLSVisibilityTests:
    def test_hidden_columns(self):
        roles = [
            {
                "role_name": "Basic",
                "test_user": "viewer@corp.com",
                "hidden_columns": [
                    {"table_name": "Sales", "column_name": "Margin"},
                ],
                "hidden_tables": [],
            },
        ]
        tests = generate_ols_visibility_tests(roles)
        assert len(tests) == 1
        assert tests[0].expected_visible is False
        assert tests[0].column_name == "Margin"

    def test_hidden_tables(self):
        roles = [
            {
                "role_name": "Basic",
                "test_user": "viewer@corp.com",
                "hidden_columns": [],
                "hidden_tables": ["HR", "Payroll"],
            },
        ]
        tests = generate_ols_visibility_tests(roles)
        assert len(tests) == 2
        assert all(t.expected_visible is False for t in tests)

    def test_combined(self):
        roles = [
            {
                "role_name": "R",
                "test_user": "u",
                "hidden_columns": [
                    {"table_name": "T", "column_name": "C"},
                ],
                "hidden_tables": ["HiddenT"],
            },
        ]
        tests = generate_ols_visibility_tests(roles)
        assert len(tests) == 2

    def test_empty(self):
        assert generate_ols_visibility_tests([]) == []


# ---------------------------------------------------------------------------
# Cross-role tests
# ---------------------------------------------------------------------------


class TestGenerateCrossRoleTests:
    def test_two_roles_same_table(self):
        roles = [
            {
                "role_name": "R1",
                "test_user": "u1",
                "table_permissions": [
                    {"table_name": "Sales", "filter_expression": "x"},
                ],
            },
            {
                "role_name": "R2",
                "test_user": "u2",
                "table_permissions": [
                    {"table_name": "Sales", "filter_expression": "y"},
                ],
            },
        ]
        tests = generate_cross_role_tests(roles)
        assert len(tests) == 1
        assert tests[0].check_type == SecurityCheckType.CROSS_ROLE
        assert "R1 vs R2" in tests[0].role_name

    def test_single_role_no_tests(self):
        roles = [
            {
                "role_name": "R1",
                "table_permissions": [
                    {"table_name": "Sales"},
                ],
            },
        ]
        tests = generate_cross_role_tests(roles)
        assert len(tests) == 0

    def test_empty(self):
        assert generate_cross_role_tests([]) == []


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------


class TestGenerateNegativeTests:
    def test_generates(self):
        roles = [
            {
                "role_name": "Regional",
                "test_user": "u",
                "table_permissions": [
                    {"table_name": "Sales", "filter_expression": "Region='East'"},
                ],
            },
        ]
        tests = generate_negative_tests(roles)
        assert len(tests) == 1
        assert tests[0].check_type == SecurityCheckType.NEGATIVE_TEST
        assert tests[0].expected_row_count == 0
        assert "NOT" in tests[0].dax_query

    def test_no_filter_skipped(self):
        roles = [
            {
                "role_name": "R",
                "table_permissions": [
                    {"table_name": "T", "filter_expression": ""},
                ],
            },
        ]
        tests = generate_negative_tests(roles)
        assert len(tests) == 0

    def test_empty(self):
        assert generate_negative_tests([]) == []


# ---------------------------------------------------------------------------
# Result evaluation
# ---------------------------------------------------------------------------


class TestEvaluateRLSRowCount:
    def test_pass(self):
        tc = SecurityTestCase(
            check_type=SecurityCheckType.RLS_ROW_COUNT,
            role_name="R", test_user="u", table_name="T",
        )
        r = evaluate_rls_row_count(tc, 100, 100)
        assert r.status == SecurityCheckStatus.PASS

    def test_fail(self):
        tc = SecurityTestCase(
            check_type=SecurityCheckType.RLS_ROW_COUNT,
            role_name="R", test_user="u", table_name="T",
        )
        r = evaluate_rls_row_count(tc, 100, 50)
        assert r.status == SecurityCheckStatus.FAIL


class TestEvaluateOLSVisibility:
    def test_hidden_pass(self):
        tc = SecurityTestCase(
            check_type=SecurityCheckType.OLS_VISIBILITY,
            role_name="R", test_user="u", table_name="T",
            column_name="C", expected_visible=False,
        )
        r = evaluate_ols_visibility(tc, is_visible=False)
        assert r.status == SecurityCheckStatus.PASS

    def test_visible_when_should_be_hidden(self):
        tc = SecurityTestCase(
            check_type=SecurityCheckType.OLS_VISIBILITY,
            role_name="R", test_user="u", table_name="T",
            expected_visible=False,
        )
        r = evaluate_ols_visibility(tc, is_visible=True)
        assert r.status == SecurityCheckStatus.FAIL


class TestEvaluateNegativeTest:
    def test_pass_zero_rows(self):
        tc = SecurityTestCase(
            check_type=SecurityCheckType.NEGATIVE_TEST,
            role_name="R", test_user="u", table_name="T",
        )
        r = evaluate_negative_test(tc, 0)
        assert r.status == SecurityCheckStatus.PASS

    def test_fail_nonzero_rows(self):
        tc = SecurityTestCase(
            check_type=SecurityCheckType.NEGATIVE_TEST,
            role_name="R", test_user="u", table_name="T",
        )
        r = evaluate_negative_test(tc, 5)
        assert r.status == SecurityCheckStatus.FAIL


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


class TestSecurityValidationReport:
    def test_add_counts(self):
        rpt = SecurityValidationReport()
        rpt.add(SecurityCheckResult(
            check_type=SecurityCheckType.RLS_ROW_COUNT,
            role_name="R", test_user="u",
            status=SecurityCheckStatus.PASS,
        ))
        rpt.add(SecurityCheckResult(
            check_type=SecurityCheckType.OLS_VISIBILITY,
            role_name="R", test_user="u",
            status=SecurityCheckStatus.FAIL,
        ))
        assert rpt.total_checks == 2
        assert rpt.passed == 1
        assert rpt.failed == 1

    def test_render(self):
        rpt = SecurityValidationReport()
        rpt.add(SecurityCheckResult(
            check_type=SecurityCheckType.RLS_ROW_COUNT,
            role_name="Regional", test_user="alice",
            expected_value=100, actual_value=50,
            status=SecurityCheckStatus.FAIL,
        ))
        md = render_security_validation_report(rpt)
        assert "Security Validation Report" in md
        assert "Regional" in md
