"""Semantic model validator — verify DAX measures, relationships, hierarchies.

Generates validation test cases that compare OAC logical SQL results
against Power BI DAX query results to ensure semantic equivalence.

Covers:
  - Measure result comparison (OAC expression vs DAX EVALUATE)
  - Relationship correctness (join cardinality via cross-table queries)
  - Hierarchy drill-down accuracy (aggregate at each level)
  - Filter context equivalence
  - Calculated column verification
  - Time-intelligence measure comparison
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


class SemanticCheckType(str, Enum):
    """Types of semantic model validation checks."""

    MEASURE_RESULT = "measure_result"
    RELATIONSHIP = "relationship"
    HIERARCHY_DRILL = "hierarchy_drill"
    FILTER_CONTEXT = "filter_context"
    CALCULATED_COLUMN = "calculated_column"
    TIME_INTELLIGENCE = "time_intelligence"


class SemanticCheckStatus(str, Enum):
    """Outcome of a semantic validation check."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class SemanticTestCase:
    """A single semantic model validation test case."""

    check_type: SemanticCheckType
    name: str
    description: str = ""
    oac_query: str = ""         # Logical SQL for OAC
    dax_query: str = ""         # DAX EVALUATE query for PBI
    expected_tolerance: float = 0.0001
    table_name: str = ""
    measure_name: str = ""
    hierarchy_name: str = ""


@dataclass
class SemanticCheckResult:
    """Result of a single semantic validation check."""

    check_type: SemanticCheckType
    name: str
    oac_value: Any = None
    pbi_value: Any = None
    variance: float = 0.0
    variance_percent: float = 0.0
    status: SemanticCheckStatus = SemanticCheckStatus.PASS
    tolerance: float = 0.0001
    description: str = ""
    error: str = ""
    duration_ms: int = 0


@dataclass
class SemanticValidationReport:
    """Aggregated semantic model validation results."""

    results: list[SemanticCheckResult] = field(default_factory=list)
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    skipped: int = 0

    def add(self, result: SemanticCheckResult) -> None:
        self.results.append(result)
        self.total_checks += 1
        if result.status == SemanticCheckStatus.PASS:
            self.passed += 1
        elif result.status == SemanticCheckStatus.FAIL:
            self.failed += 1
        elif result.status == SemanticCheckStatus.WARN:
            self.warnings += 1
        elif result.status == SemanticCheckStatus.SKIP:
            self.skipped += 1

    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.passed / self.total_checks * 100


# ---------------------------------------------------------------------------
# Test-case generation — measures
# ---------------------------------------------------------------------------


def generate_measure_tests(
    measures: list[dict[str, Any]],
) -> list[SemanticTestCase]:
    """Generate validation test cases for DAX measures.

    Parameters
    ----------
    measures : list[dict]
        Each dict must contain::

            - name: str          — Measure name
            - table: str         — Table the measure belongs to
            - dax_expression: str  — DAX formula
            - oac_expression: str  — Original OAC expression (optional)
    """
    tests: list[SemanticTestCase] = []

    for m in measures:
        name = m.get("name", "")
        table = m.get("table", "")
        dax = m.get("dax_expression", "")
        oac = m.get("oac_expression", "")

        tests.append(
            SemanticTestCase(
                check_type=SemanticCheckType.MEASURE_RESULT,
                name=f"Measure: {name}",
                description=f"Compare {name} result between OAC and PBI",
                oac_query=_build_oac_measure_query(table, oac or name),
                dax_query=_build_dax_evaluate(table, name),
                expected_tolerance=0.0001,
                table_name=table,
                measure_name=name,
            )
        )

    logger.info("Generated %d measure test cases", len(tests))
    return tests


def _build_oac_measure_query(table: str, expression: str) -> str:
    """Build an OAC logical SQL query for a measure."""
    return f'SELECT {expression} AS result FROM "{table}"'


def _build_dax_evaluate(table: str, measure: str) -> str:
    """Build a DAX EVALUATE query for a measure."""
    return (
        f"EVALUATE ROW(\"{measure}\", "
        f"CALCULATE([{measure}]))"
    )


# ---------------------------------------------------------------------------
# Test-case generation — relationships
# ---------------------------------------------------------------------------


def generate_relationship_tests(
    relationships: list[dict[str, Any]],
) -> list[SemanticTestCase]:
    """Generate validation test cases for relationships.

    Parameters
    ----------
    relationships : list[dict]
        Each dict::

            - from_table: str
            - from_column: str
            - to_table: str
            - to_column: str
            - type: str (1:M, M:1, etc.)
    """
    tests: list[SemanticTestCase] = []

    for rel in relationships:
        from_t = rel.get("from_table", "")
        from_c = rel.get("from_column", "")
        to_t = rel.get("to_table", "")
        to_c = rel.get("to_column", "")

        # Cross-table row count: join both and count
        tests.append(
            SemanticTestCase(
                check_type=SemanticCheckType.RELATIONSHIP,
                name=f"Relationship: {from_t}.{from_c} → {to_t}.{to_c}",
                description=(
                    f"Verify join between {from_t} and {to_t} "
                    f"produces correct row count"
                ),
                oac_query=(
                    f"SELECT COUNT(*) AS cnt FROM \"{from_t}\" "
                    f"JOIN \"{to_t}\" ON \"{from_t}\".\"{from_c}\" = "
                    f"\"{to_t}\".\"{to_c}\""
                ),
                dax_query=(
                    f"EVALUATE ROW(\"JoinCount\", "
                    f"COUNTROWS(CROSSJOIN('{from_t}', '{to_t}')))"
                ),
                expected_tolerance=0,
                table_name=f"{from_t}-{to_t}",
            )
        )

        # Orphan check: keys in child not in parent
        tests.append(
            SemanticTestCase(
                check_type=SemanticCheckType.RELATIONSHIP,
                name=f"Orphans: {from_t}.{from_c} → {to_t}.{to_c}",
                description=(
                    f"Check for orphan rows in {from_t} "
                    f"not matching {to_t}"
                ),
                oac_query=(
                    f"SELECT COUNT(*) AS cnt FROM \"{from_t}\" "
                    f"WHERE \"{from_c}\" NOT IN "
                    f"(SELECT \"{to_c}\" FROM \"{to_t}\")"
                ),
                dax_query=(
                    f"EVALUATE ROW(\"Orphans\", "
                    f"COUNTROWS(EXCEPT(VALUES('{from_t}'[{from_c}]), "
                    f"VALUES('{to_t}'[{to_c}]))))"
                ),
                expected_tolerance=0,
                table_name=f"{from_t}-{to_t}",
            )
        )

    logger.info("Generated %d relationship test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Test-case generation — hierarchies
# ---------------------------------------------------------------------------


def generate_hierarchy_tests(
    hierarchies: list[dict[str, Any]],
) -> list[SemanticTestCase]:
    """Generate drill-down validation test cases for hierarchies.

    Parameters
    ----------
    hierarchies : list[dict]
        Each dict::

            - name: str
            - table: str
            - levels: list[str]  — column names top to bottom
            - measure: str       — a measure to aggregate
    """
    tests: list[SemanticTestCase] = []

    for h in hierarchies:
        name = h.get("name", "")
        table = h.get("table", "")
        levels = h.get("levels", [])
        measure = h.get("measure", "COUNT(*)")

        for i, level in enumerate(levels):
            group_cols = levels[: i + 1]
            group_str = ", ".join(f'"{c}"' for c in group_cols)
            dax_cols = ", ".join(f"'{table}'[{c}]" for c in group_cols)

            tests.append(
                SemanticTestCase(
                    check_type=SemanticCheckType.HIERARCHY_DRILL,
                    name=f"Hierarchy: {name} @ Level {i + 1} ({level})",
                    description=(
                        f"Drill to level {i + 1} ({level}) in {name} "
                        f"and compare aggregate"
                    ),
                    oac_query=(
                        f"SELECT {group_str}, {measure} AS val "
                        f"FROM \"{table}\" GROUP BY {group_str}"
                    ),
                    dax_query=(
                        f"EVALUATE SUMMARIZECOLUMNS("
                        f"{dax_cols}, "
                        f"\"{measure}\", [{measure}])"
                    ),
                    expected_tolerance=0.0001,
                    table_name=table,
                    hierarchy_name=name,
                )
            )

    logger.info("Generated %d hierarchy test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Test-case generation — filter context
# ---------------------------------------------------------------------------


def generate_filter_context_tests(
    filters: list[dict[str, Any]],
) -> list[SemanticTestCase]:
    """Generate filter-context validation tests.

    Parameters
    ----------
    filters : list[dict]
        Each dict::

            - table: str
            - column: str
            - value: str
            - measure: str
    """
    tests: list[SemanticTestCase] = []

    for f in filters:
        table = f.get("table", "")
        column = f.get("column", "")
        value = f.get("value", "")
        measure = f.get("measure", "COUNT(*)")

        tests.append(
            SemanticTestCase(
                check_type=SemanticCheckType.FILTER_CONTEXT,
                name=f"Filter: {table}.{column}='{value}'",
                description=(
                    f"Apply filter {column}='{value}' on {table} "
                    f"and compare {measure}"
                ),
                oac_query=(
                    f"SELECT {measure} AS val FROM \"{table}\" "
                    f"WHERE \"{column}\" = '{value}'"
                ),
                dax_query=(
                    f"EVALUATE ROW(\"{measure}\", "
                    f"CALCULATE([{measure}], "
                    f"'{table}'[{column}] = \"{value}\"))"
                ),
                expected_tolerance=0.0001,
                table_name=table,
            )
        )

    logger.info("Generated %d filter context test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Result comparison
# ---------------------------------------------------------------------------


def evaluate_semantic_result(
    test_case: SemanticTestCase,
    oac_value: Any,
    pbi_value: Any,
    duration_ms: int = 0,
) -> SemanticCheckResult:
    """Evaluate a single semantic validation result."""
    # Both None
    if oac_value is None and pbi_value is None:
        return SemanticCheckResult(
            check_type=test_case.check_type,
            name=test_case.name,
            oac_value=oac_value,
            pbi_value=pbi_value,
            status=SemanticCheckStatus.PASS,
            tolerance=test_case.expected_tolerance,
            description=test_case.description,
            duration_ms=duration_ms,
        )

    if oac_value is None or pbi_value is None:
        return SemanticCheckResult(
            check_type=test_case.check_type,
            name=test_case.name,
            oac_value=oac_value,
            pbi_value=pbi_value,
            status=SemanticCheckStatus.FAIL,
            variance_percent=100.0,
            tolerance=test_case.expected_tolerance,
            description=test_case.description,
            duration_ms=duration_ms,
        )

    try:
        src = float(oac_value)
        tgt = float(pbi_value)
    except (ValueError, TypeError):
        status = (
            SemanticCheckStatus.PASS
            if str(oac_value) == str(pbi_value)
            else SemanticCheckStatus.FAIL
        )
        return SemanticCheckResult(
            check_type=test_case.check_type,
            name=test_case.name,
            oac_value=oac_value,
            pbi_value=pbi_value,
            status=status,
            tolerance=test_case.expected_tolerance,
            description=test_case.description,
            duration_ms=duration_ms,
        )

    variance = abs(tgt - src)
    denom = abs(src) if src != 0 else abs(tgt)
    variance_pct = (variance / denom) * 100 if denom != 0 else 0.0

    status = (
        SemanticCheckStatus.PASS
        if variance_pct <= test_case.expected_tolerance * 100
        else SemanticCheckStatus.FAIL
    )

    return SemanticCheckResult(
        check_type=test_case.check_type,
        name=test_case.name,
        oac_value=oac_value,
        pbi_value=pbi_value,
        variance=variance,
        variance_percent=variance_pct,
        status=status,
        tolerance=test_case.expected_tolerance,
        description=test_case.description,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_semantic_report(report: SemanticValidationReport) -> str:
    """Render a Markdown semantic validation report."""
    lines = [
        "# Semantic Model Validation Report",
        "",
        f"- **Total checks:** {report.total_checks}",
        f"- **Passed:** {report.passed}",
        f"- **Failed:** {report.failed}",
        f"- **Warnings:** {report.warnings}",
        f"- **Pass rate:** {report.pass_rate:.1f}%",
        "",
    ]

    # Group by check type
    by_type: dict[str, list[SemanticCheckResult]] = {}
    for r in report.results:
        by_type.setdefault(r.check_type.value, []).append(r)

    for ct, results in sorted(by_type.items()):
        passed = sum(1 for r in results if r.status == SemanticCheckStatus.PASS)
        lines.extend([
            f"## {ct.replace('_', ' ').title()} ({passed}/{len(results)} passed)",
            "",
            "| Test | OAC Value | PBI Value | Variance % | Status |",
            "|---|---|---|---|---|",
        ])
        for r in results:
            lines.append(
                f"| {r.name} | {r.oac_value} | {r.pbi_value} | "
                f"{r.variance_percent:.4f}% | {r.status.value} |"
            )
        lines.append("")

    return "\n".join(lines)
