"""Data reconciliation — generate and evaluate data-layer validation checks.

Compares Oracle source data with Fabric target data across multiple dimensions:
  - Row counts
  - Checksums (aggregate hash)
  - Null counts per column
  - Distinct counts per column
  - Min / Max per numeric / date columns
  - Aggregate totals (SUM, AVG) for numeric columns
  - Data-type verification against the mapping rules
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


class CheckType(str, Enum):
    """Categories of data reconciliation checks."""

    ROW_COUNT = "row_count"
    CHECKSUM = "checksum"
    NULL_COUNT = "null_count"
    DISTINCT_COUNT = "distinct_count"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    AGGREGATE_SUM = "aggregate_sum"
    AGGREGATE_AVG = "aggregate_avg"
    SAMPLE_ROWS = "sample_rows"
    DATA_TYPE = "data_type"


class CheckStatus(str, Enum):
    """Outcome of a single validation check."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class ReconciliationQuery:
    """A paired query to run against source (Oracle) and target (Fabric)."""

    check_type: CheckType
    asset_name: str
    column_name: str = ""
    oracle_sql: str = ""
    fabric_sql: str = ""
    tolerance: float = 0.0
    description: str = ""


@dataclass
class ReconciliationResult:
    """Result of a single reconciliation check."""

    check_type: CheckType
    asset_name: str
    column_name: str = ""
    source_value: Any = None
    target_value: Any = None
    variance: float = 0.0
    variance_percent: float = 0.0
    status: CheckStatus = CheckStatus.PASS
    tolerance: float = 0.0
    description: str = ""
    error: str = ""
    duration_ms: int = 0


@dataclass
class ReconciliationReport:
    """Aggregated reconciliation results for a migration wave."""

    results: list[ReconciliationResult] = field(default_factory=list)
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    skipped: int = 0
    errors: int = 0

    def add(self, result: ReconciliationResult) -> None:
        self.results.append(result)
        self.total_checks += 1
        if result.status == CheckStatus.PASS:
            self.passed += 1
        elif result.status == CheckStatus.FAIL:
            self.failed += 1
        elif result.status == CheckStatus.WARN:
            self.warnings += 1
        elif result.status == CheckStatus.SKIP:
            self.skipped += 1
        elif result.status == CheckStatus.ERROR:
            self.errors += 1

    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.passed / self.total_checks * 100


# ---------------------------------------------------------------------------
# Query generation
# ---------------------------------------------------------------------------


_NUMERIC_TYPES = frozenset({
    "number", "decimal", "int", "integer", "float", "double",
    "bigint", "smallint", "tinyint", "numeric", "real", "money",
})


def _is_numeric(col_type: str) -> bool:
    """Check if a column type is numeric."""
    return col_type.strip().lower().split("(")[0] in _NUMERIC_TYPES


def generate_reconciliation_queries(
    table_inventory: list[dict[str, Any]],
    *,
    include_sample: bool = True,
    sample_size: int = 100,
) -> list[ReconciliationQuery]:
    """Generate paired Oracle / Fabric queries for each table.

    Parameters
    ----------
    table_inventory : list[dict]
        Each dict must contain::

            - source_name: str   — Oracle table
            - target_name: str   — Fabric table
            - columns: list[dict]  — each with ``name`` and ``type``

    Returns
    -------
    list[ReconciliationQuery]
        Queries ready for execution against both systems.
    """
    queries: list[ReconciliationQuery] = []

    for table in table_inventory:
        src = table["source_name"]
        tgt = table["target_name"]
        columns = table.get("columns", [])

        # 1. Row count
        queries.append(
            ReconciliationQuery(
                check_type=CheckType.ROW_COUNT,
                asset_name=src,
                oracle_sql=f"SELECT COUNT(*) AS cnt FROM {src}",
                fabric_sql=f"SELECT COUNT(*) AS cnt FROM {tgt}",
                tolerance=0,
                description=f"Row count for {src}",
            )
        )

        for col in columns:
            col_name = col["name"]
            col_type = col.get("type", "")

            # 2. Null counts
            queries.append(
                ReconciliationQuery(
                    check_type=CheckType.NULL_COUNT,
                    asset_name=src,
                    column_name=col_name,
                    oracle_sql=(
                        f"SELECT COUNT(*) AS cnt FROM {src} "
                        f"WHERE {col_name} IS NULL"
                    ),
                    fabric_sql=(
                        f"SELECT COUNT(*) AS cnt FROM {tgt} "
                        f"WHERE {col_name} IS NULL"
                    ),
                    tolerance=0,
                    description=f"Null count for {src}.{col_name}",
                )
            )

            # 3. Distinct counts
            queries.append(
                ReconciliationQuery(
                    check_type=CheckType.DISTINCT_COUNT,
                    asset_name=src,
                    column_name=col_name,
                    oracle_sql=(
                        f"SELECT COUNT(DISTINCT {col_name}) AS cnt FROM {src}"
                    ),
                    fabric_sql=(
                        f"SELECT COUNT(DISTINCT {col_name}) AS cnt FROM {tgt}"
                    ),
                    tolerance=0,
                    description=f"Distinct count for {src}.{col_name}",
                )
            )

            # 4. Numeric aggregates
            if _is_numeric(col_type):
                # Min
                queries.append(
                    ReconciliationQuery(
                        check_type=CheckType.MIN_VALUE,
                        asset_name=src,
                        column_name=col_name,
                        oracle_sql=f"SELECT MIN({col_name}) AS val FROM {src}",
                        fabric_sql=f"SELECT MIN({col_name}) AS val FROM {tgt}",
                        tolerance=0,
                        description=f"Min value for {src}.{col_name}",
                    )
                )
                # Max
                queries.append(
                    ReconciliationQuery(
                        check_type=CheckType.MAX_VALUE,
                        asset_name=src,
                        column_name=col_name,
                        oracle_sql=f"SELECT MAX({col_name}) AS val FROM {src}",
                        fabric_sql=f"SELECT MAX({col_name}) AS val FROM {tgt}",
                        tolerance=0,
                        description=f"Max value for {src}.{col_name}",
                    )
                )
                # SUM
                queries.append(
                    ReconciliationQuery(
                        check_type=CheckType.AGGREGATE_SUM,
                        asset_name=src,
                        column_name=col_name,
                        oracle_sql=f"SELECT SUM({col_name}) AS val FROM {src}",
                        fabric_sql=f"SELECT SUM({col_name}) AS val FROM {tgt}",
                        tolerance=0.0001,
                        description=f"Sum for {src}.{col_name}",
                    )
                )
                # AVG
                queries.append(
                    ReconciliationQuery(
                        check_type=CheckType.AGGREGATE_AVG,
                        asset_name=src,
                        column_name=col_name,
                        oracle_sql=f"SELECT AVG({col_name}) AS val FROM {src}",
                        fabric_sql=f"SELECT AVG({col_name}) AS val FROM {tgt}",
                        tolerance=0.01,
                        description=f"Average for {src}.{col_name}",
                    )
                )

        # Sample rows
        if include_sample:
            queries.append(
                ReconciliationQuery(
                    check_type=CheckType.SAMPLE_ROWS,
                    asset_name=src,
                    oracle_sql=(
                        f"SELECT * FROM {src} "
                        f"WHERE ROWNUM <= {sample_size} ORDER BY 1"
                    ),
                    fabric_sql=(
                        f"SELECT TOP {sample_size} * FROM {tgt} ORDER BY 1"
                    ),
                    tolerance=0,
                    description=f"Sample {sample_size} rows from {src}",
                )
            )

    logger.info(
        "Generated %d reconciliation queries for %d tables",
        len(queries),
        len(table_inventory),
    )
    return queries


# ---------------------------------------------------------------------------
# Result comparison
# ---------------------------------------------------------------------------


def compare_values(
    source_value: Any,
    target_value: Any,
    tolerance: float = 0.0,
) -> tuple[CheckStatus, float, float]:
    """Compare a source value against a target value with tolerance.

    Returns (status, variance, variance_percent).
    """
    # Both None / null
    if source_value is None and target_value is None:
        return CheckStatus.PASS, 0.0, 0.0

    if source_value is None or target_value is None:
        return CheckStatus.FAIL, 0.0, 100.0

    # Numeric comparison
    try:
        src = float(source_value)
        tgt = float(target_value)
    except (ValueError, TypeError):
        # String comparison
        if str(source_value) == str(target_value):
            return CheckStatus.PASS, 0.0, 0.0
        return CheckStatus.FAIL, 0.0, 100.0

    if src == 0 and tgt == 0:
        return CheckStatus.PASS, 0.0, 0.0

    variance = abs(tgt - src)
    denom = abs(src) if src != 0 else abs(tgt)
    variance_pct = (variance / denom) * 100 if denom != 0 else 0.0

    if variance <= tolerance or variance_pct <= tolerance * 100:
        return CheckStatus.PASS, variance, variance_pct

    return CheckStatus.FAIL, variance, variance_pct


def evaluate_result(
    query: ReconciliationQuery,
    source_value: Any,
    target_value: Any,
    duration_ms: int = 0,
) -> ReconciliationResult:
    """Evaluate a single reconciliation check result."""
    status, variance, variance_pct = compare_values(
        source_value, target_value, query.tolerance
    )
    return ReconciliationResult(
        check_type=query.check_type,
        asset_name=query.asset_name,
        column_name=query.column_name,
        source_value=source_value,
        target_value=target_value,
        variance=variance,
        variance_percent=variance_pct,
        status=status,
        tolerance=query.tolerance,
        description=query.description,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Data-type validation
# ---------------------------------------------------------------------------


def generate_data_type_checks(
    table_inventory: list[dict[str, Any]],
    type_mapping: dict[str, str] | None = None,
) -> list[ReconciliationQuery]:
    """Generate data-type verification queries.

    Parameters
    ----------
    type_mapping : dict
        Oracle type → expected Fabric type (e.g. ``{"NUMBER": "DECIMAL"}``).
    """
    mapping = type_mapping or {}
    queries: list[ReconciliationQuery] = []

    for table in table_inventory:
        for col in table.get("columns", []):
            oracle_type = col.get("type", "")
            expected = mapping.get(oracle_type.upper(), oracle_type)
            queries.append(
                ReconciliationQuery(
                    check_type=CheckType.DATA_TYPE,
                    asset_name=table["source_name"],
                    column_name=col["name"],
                    oracle_sql=oracle_type,
                    fabric_sql=expected,
                    tolerance=0,
                    description=(
                        f"Type check {table['source_name']}.{col['name']}: "
                        f"{oracle_type} → {expected}"
                    ),
                )
            )

    return queries


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_reconciliation_report(report: ReconciliationReport) -> str:
    """Render a Markdown reconciliation report."""
    lines = [
        "# Data Reconciliation Report",
        "",
        f"- **Total checks:** {report.total_checks}",
        f"- **Passed:** {report.passed}",
        f"- **Failed:** {report.failed}",
        f"- **Warnings:** {report.warnings}",
        f"- **Skipped:** {report.skipped}",
        f"- **Errors:** {report.errors}",
        f"- **Pass rate:** {report.pass_rate:.1f}%",
        "",
    ]

    # Failed checks detail
    failures = [r for r in report.results if r.status == CheckStatus.FAIL]
    if failures:
        lines.extend([
            "## Failed Checks",
            "",
            "| Check | Asset | Column | Source | Target | Variance % |",
            "|---|---|---|---|---|---|",
        ])
        for f in failures:
            lines.append(
                f"| {f.check_type.value} | {f.asset_name} | "
                f"{f.column_name or '-'} | {f.source_value} | "
                f"{f.target_value} | {f.variance_percent:.4f}% |"
            )
        lines.append("")

    # Summary by table
    tables: dict[str, dict[str, int]] = {}
    for r in report.results:
        t = tables.setdefault(r.asset_name, {"pass": 0, "fail": 0, "total": 0})
        t["total"] += 1
        if r.status == CheckStatus.PASS:
            t["pass"] += 1
        elif r.status == CheckStatus.FAIL:
            t["fail"] += 1

    if tables:
        lines.extend([
            "## Summary by Table",
            "",
            "| Table | Total | Passed | Failed |",
            "|---|---|---|---|",
        ])
        for name, counts in sorted(tables.items()):
            lines.append(
                f"| {name} | {counts['total']} | {counts['pass']} | "
                f"{counts['fail']} |"
            )
        lines.append("")

    return "\n".join(lines)
