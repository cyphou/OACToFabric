"""Security validator — RLS, OLS, and cross-role validation.

Verifies that migrated Power BI security (RLS / OLS) is functionally
equivalent to the OAC security model by generating multi-user test cases
and evaluating row-count, data-content, and visibility outcomes.

Covers:
  - RLS row-count comparison (same user, same query → compare counts)
  - RLS data-content comparison (verify actual filtered data)
  - OLS visibility (hidden columns / tables not accessible)
  - Cross-role testing (different roles see different data)
  - Negative testing (restricted data not visible)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------


class SecurityCheckType(str, Enum):
    """Types of security validation checks."""

    RLS_ROW_COUNT = "rls_row_count"
    RLS_DATA_CONTENT = "rls_data_content"
    OLS_VISIBILITY = "ols_visibility"
    CROSS_ROLE = "cross_role"
    NEGATIVE_TEST = "negative_test"


class SecurityCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class SecurityTestCase:
    """A single security validation test case."""

    check_type: SecurityCheckType
    role_name: str
    test_user: str
    description: str = ""
    table_name: str = ""
    column_name: str = ""
    expected_row_count: int | None = None
    expected_visible: bool | None = None
    oac_query: str = ""
    dax_query: str = ""


@dataclass
class SecurityCheckResult:
    """Result of a single security validation check."""

    check_type: SecurityCheckType
    role_name: str
    test_user: str
    table_name: str = ""
    column_name: str = ""
    expected_value: Any = None
    actual_value: Any = None
    status: SecurityCheckStatus = SecurityCheckStatus.PASS
    description: str = ""
    error: str = ""


@dataclass
class SecurityValidationReport:
    """Aggregated security validation results."""

    results: list[SecurityCheckResult] = field(default_factory=list)
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0

    def add(self, result: SecurityCheckResult) -> None:
        self.results.append(result)
        self.total_checks += 1
        if result.status == SecurityCheckStatus.PASS:
            self.passed += 1
        elif result.status == SecurityCheckStatus.FAIL:
            self.failed += 1
        elif result.status == SecurityCheckStatus.WARN:
            self.warnings += 1

    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.passed / self.total_checks * 100


# ---------------------------------------------------------------------------
# RLS test-case generation
# ---------------------------------------------------------------------------


def generate_rls_row_count_tests(
    rls_roles: list[dict[str, Any]],
) -> list[SecurityTestCase]:
    """Generate RLS row-count validation tests.

    Parameters
    ----------
    rls_roles : list[dict]
        Each dict::

            - role_name: str
            - test_user: str
            - table_permissions: list[dict]
                — table_name, filter_expression, expected_row_count (optional)
    """
    tests: list[SecurityTestCase] = []

    for role in rls_roles:
        role_name = role.get("role_name", "")
        test_user = role.get("test_user", f"test_{role_name.lower()}")

        for tp in role.get("table_permissions", []):
            table = tp.get("table_name", "")
            expected = tp.get("expected_row_count")

            tests.append(
                SecurityTestCase(
                    check_type=SecurityCheckType.RLS_ROW_COUNT,
                    role_name=role_name,
                    test_user=test_user,
                    table_name=table,
                    expected_row_count=expected,
                    description=(
                        f"RLS row count: {role_name} on {table} "
                        f"(user: {test_user})"
                    ),
                    dax_query=(
                        f"EVALUATE ROW(\"RowCount\", "
                        f"COUNTROWS('{table}'))"
                    ),
                )
            )

    logger.info("Generated %d RLS row count test cases", len(tests))
    return tests


def generate_rls_data_content_tests(
    rls_roles: list[dict[str, Any]],
    sample_size: int = 10,
) -> list[SecurityTestCase]:
    """Generate RLS data-content validation tests.

    Verifies actual row data matches expected filter.
    """
    tests: list[SecurityTestCase] = []

    for role in rls_roles:
        role_name = role.get("role_name", "")
        test_user = role.get("test_user", f"test_{role_name.lower()}")

        for tp in role.get("table_permissions", []):
            table = tp.get("table_name", "")
            filter_expr = tp.get("filter_expression", "")

            tests.append(
                SecurityTestCase(
                    check_type=SecurityCheckType.RLS_DATA_CONTENT,
                    role_name=role_name,
                    test_user=test_user,
                    table_name=table,
                    description=(
                        f"RLS data content: {role_name} on {table} — "
                        f"verify filter '{filter_expr[:50]}' applied"
                    ),
                    dax_query=(
                        f"EVALUATE TOPN({sample_size}, '{table}')"
                    ),
                )
            )

    logger.info("Generated %d RLS data content test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# OLS test-case generation
# ---------------------------------------------------------------------------


def generate_ols_visibility_tests(
    ols_roles: list[dict[str, Any]],
) -> list[SecurityTestCase]:
    """Generate OLS visibility validation tests.

    Parameters
    ----------
    ols_roles : list[dict]
        Each dict::

            - role_name: str
            - test_user: str
            - hidden_columns: list[dict] — table_name, column_name
            - hidden_tables: list[str]
    """
    tests: list[SecurityTestCase] = []

    for role in ols_roles:
        role_name = role.get("role_name", "")
        test_user = role.get("test_user", f"test_{role_name.lower()}")

        # Hidden columns
        for hc in role.get("hidden_columns", []):
            table = hc.get("table_name", "")
            column = hc.get("column_name", "")
            tests.append(
                SecurityTestCase(
                    check_type=SecurityCheckType.OLS_VISIBILITY,
                    role_name=role_name,
                    test_user=test_user,
                    table_name=table,
                    column_name=column,
                    expected_visible=False,
                    description=(
                        f"OLS: column {table}.{column} should be HIDDEN "
                        f"for role {role_name}"
                    ),
                )
            )

        # Hidden tables
        for table in role.get("hidden_tables", []):
            tests.append(
                SecurityTestCase(
                    check_type=SecurityCheckType.OLS_VISIBILITY,
                    role_name=role_name,
                    test_user=test_user,
                    table_name=table,
                    expected_visible=False,
                    description=(
                        f"OLS: table {table} should be HIDDEN "
                        f"for role {role_name}"
                    ),
                )
            )

    logger.info("Generated %d OLS visibility test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Cross-role & negative tests
# ---------------------------------------------------------------------------


def generate_cross_role_tests(
    roles: list[dict[str, Any]],
) -> list[SecurityTestCase]:
    """Generate cross-role tests verifying different roles see different data.

    Compares row counts between roles on the same table — if RLS filters
    differ, counts must differ (unless data coincidentally matches).
    """
    tests: list[SecurityTestCase] = []

    # Build (table, role) pairs
    role_tables: dict[str, list[dict[str, Any]]] = {}
    for role in roles:
        for tp in role.get("table_permissions", []):
            table = tp.get("table_name", "")
            role_tables.setdefault(table, []).append(role)

    for table, table_roles in role_tables.items():
        if len(table_roles) < 2:
            continue

        for i in range(len(table_roles)):
            for j in range(i + 1, len(table_roles)):
                r1 = table_roles[i]
                r2 = table_roles[j]
                tests.append(
                    SecurityTestCase(
                        check_type=SecurityCheckType.CROSS_ROLE,
                        role_name=f"{r1['role_name']} vs {r2['role_name']}",
                        test_user=r1.get("test_user", ""),
                        table_name=table,
                        description=(
                            f"Cross-role: compare {r1['role_name']} and "
                            f"{r2['role_name']} on {table} — "
                            f"different filters should produce different results"
                        ),
                    )
                )

    logger.info("Generated %d cross-role test cases", len(tests))
    return tests


def generate_negative_tests(
    rls_roles: list[dict[str, Any]],
) -> list[SecurityTestCase]:
    """Generate negative tests — verify restricted data is NOT visible.

    For each role, pick a table where the filter excludes data and verify
    excluded rows are indeed absent.
    """
    tests: list[SecurityTestCase] = []

    for role in rls_roles:
        role_name = role.get("role_name", "")
        test_user = role.get("test_user", f"test_{role_name.lower()}")

        for tp in role.get("table_permissions", []):
            table = tp.get("table_name", "")
            filter_expr = tp.get("filter_expression", "")
            if not filter_expr:
                continue

            tests.append(
                SecurityTestCase(
                    check_type=SecurityCheckType.NEGATIVE_TEST,
                    role_name=role_name,
                    test_user=test_user,
                    table_name=table,
                    description=(
                        f"Negative: {role_name} on {table} — "
                        f"rows outside filter '{filter_expr[:50]}' "
                        f"must NOT be visible"
                    ),
                    dax_query=(
                        f"EVALUATE FILTER('{table}', "
                        f"NOT({filter_expr}))"
                    ),
                    expected_row_count=0,
                )
            )

    logger.info("Generated %d negative test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Result evaluation
# ---------------------------------------------------------------------------


def evaluate_rls_row_count(
    test_case: SecurityTestCase,
    oac_count: int,
    pbi_count: int,
) -> SecurityCheckResult:
    """Evaluate an RLS row-count test."""
    status = (
        SecurityCheckStatus.PASS
        if oac_count == pbi_count
        else SecurityCheckStatus.FAIL
    )
    return SecurityCheckResult(
        check_type=test_case.check_type,
        role_name=test_case.role_name,
        test_user=test_case.test_user,
        table_name=test_case.table_name,
        expected_value=oac_count,
        actual_value=pbi_count,
        status=status,
        description=test_case.description,
    )


def evaluate_ols_visibility(
    test_case: SecurityTestCase,
    is_visible: bool,
) -> SecurityCheckResult:
    """Evaluate an OLS visibility test."""
    expected_visible = test_case.expected_visible
    if expected_visible is None:
        expected_visible = True

    status = (
        SecurityCheckStatus.PASS
        if is_visible == expected_visible
        else SecurityCheckStatus.FAIL
    )
    return SecurityCheckResult(
        check_type=test_case.check_type,
        role_name=test_case.role_name,
        test_user=test_case.test_user,
        table_name=test_case.table_name,
        column_name=test_case.column_name,
        expected_value="hidden" if not expected_visible else "visible",
        actual_value="visible" if is_visible else "hidden",
        status=status,
        description=test_case.description,
    )


def evaluate_negative_test(
    test_case: SecurityTestCase,
    row_count: int,
) -> SecurityCheckResult:
    """Evaluate a negative test — row count should be 0."""
    status = (
        SecurityCheckStatus.PASS
        if row_count == 0
        else SecurityCheckStatus.FAIL
    )
    return SecurityCheckResult(
        check_type=test_case.check_type,
        role_name=test_case.role_name,
        test_user=test_case.test_user,
        table_name=test_case.table_name,
        expected_value=0,
        actual_value=row_count,
        status=status,
        description=test_case.description,
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_security_validation_report(report: SecurityValidationReport) -> str:
    """Render a Markdown security validation report."""
    lines = [
        "# Security Validation Report",
        "",
        f"- **Total checks:** {report.total_checks}",
        f"- **Passed:** {report.passed}",
        f"- **Failed:** {report.failed}",
        f"- **Warnings:** {report.warnings}",
        f"- **Pass rate:** {report.pass_rate:.1f}%",
        "",
    ]

    # Group by check type
    by_type: dict[str, list[SecurityCheckResult]] = {}
    for r in report.results:
        by_type.setdefault(r.check_type.value, []).append(r)

    for ct, results in sorted(by_type.items()):
        passed = sum(1 for r in results if r.status == SecurityCheckStatus.PASS)
        lines.extend([
            f"## {ct.replace('_', ' ').title()} ({passed}/{len(results)} passed)",
            "",
            "| Role | User | Table | Column | Expected | Actual | Status |",
            "|---|---|---|---|---|---|---|",
        ])
        for r in results:
            lines.append(
                f"| {r.role_name} | {r.test_user} | {r.table_name or '-'} | "
                f"{r.column_name or '-'} | {r.expected_value} | "
                f"{r.actual_value} | {r.status.value} |"
            )
        lines.append("")

    return "\n".join(lines)
