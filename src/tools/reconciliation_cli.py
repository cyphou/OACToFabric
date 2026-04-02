"""Data reconciliation CLI — compare source Oracle data vs Fabric targets.

Provides:

1. **ReconciliationRunner** — executes paired queries against Oracle + Fabric
   SQL endpoints and produces a comparison report.
2. **OfflineReconciler** — compares two JSON/CSV snapshots without live
   database connections (useful for CI and testing).
3. **Report generators** — Markdown and JSON output.

Design:
- Connection-agnostic: callers provide a ``QueryExecutor`` callback
- Supports tolerance thresholds (absolute and percentage)
- Generates actionable diff reports

Usage::

    from src.tools.reconciliation_cli import (
        OfflineReconciler,
        ReconciliationRunner,
        generate_markdown_report,
    )

    # Offline mode (CI-friendly)
    reconciler = OfflineReconciler()
    report = reconciler.compare_snapshots(source_snap, target_snap)
    print(generate_markdown_report(report))

    # Live mode (with actual DB connections)
    runner = ReconciliationRunner(
        source_executor=oracle_exec,
        target_executor=fabric_exec,
    )
    report = await runner.run(table_inventory)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class CheckType(str, Enum):
    ROW_COUNT = "row_count"
    CHECKSUM = "checksum"
    NULL_COUNT = "null_count"
    DISTINCT_COUNT = "distinct_count"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    SUM_VALUE = "sum_value"
    AVG_VALUE = "avg_value"
    SAMPLE_MATCH = "sample_match"
    SCHEMA_MATCH = "schema_match"


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class CheckResult:
    """A single reconciliation check result."""

    check_type: CheckType
    table: str
    column: str = ""
    source_value: Any = None
    target_value: Any = None
    variance: float = 0.0
    variance_pct: float = 0.0
    status: Status = Status.PASS
    tolerance: float = 0.0
    message: str = ""
    duration_ms: int = 0


@dataclass
class ReconReport:
    """Aggregated reconciliation report."""

    checks: list[CheckResult] = field(default_factory=list)
    tables_checked: int = 0
    columns_checked: int = 0
    timestamp: str = ""
    source_label: str = "Oracle"
    target_label: str = "Fabric"

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == Status.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == Status.FAIL)

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.status == Status.WARN)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total else 0.0


# ---------------------------------------------------------------------------
# Value comparison
# ---------------------------------------------------------------------------


def compare_values(
    source: Any,
    target: Any,
    tolerance: float = 0.0,
) -> tuple[Status, float, float]:
    """Compare two values with tolerance. Returns (status, variance, variance_pct)."""
    if source is None and target is None:
        return Status.PASS, 0.0, 0.0
    if source is None or target is None:
        return Status.FAIL, 0.0, 100.0

    try:
        s = float(source)
        t = float(target)
    except (ValueError, TypeError):
        return (Status.PASS, 0.0, 0.0) if str(source) == str(target) else (Status.FAIL, 0.0, 100.0)

    if s == 0.0 and t == 0.0:
        return Status.PASS, 0.0, 0.0

    variance = abs(t - s)
    denom = abs(s) if s != 0 else abs(t)
    pct = (variance / denom * 100) if denom else 0.0

    if tolerance > 0:
        if variance <= tolerance or pct <= tolerance * 100:
            return Status.PASS, variance, pct
    elif variance == 0.0:
        return Status.PASS, 0.0, 0.0

    return Status.FAIL, variance, pct


# ---------------------------------------------------------------------------
# Offline reconciliation (snapshot-based)
# ---------------------------------------------------------------------------


@dataclass
class TableSnapshot:
    """Snapshot of a single table's statistics."""

    table_name: str
    row_count: int = 0
    columns: dict[str, ColumnSnapshot] = field(default_factory=dict)


@dataclass
class ColumnSnapshot:
    """Per-column statistics."""

    name: str
    null_count: int = 0
    distinct_count: int = 0
    min_value: Any = None
    max_value: Any = None
    sum_value: float | None = None
    avg_value: float | None = None
    data_type: str = ""


class OfflineReconciler:
    """Compare pre-captured snapshots without live connections."""

    def __init__(
        self,
        *,
        tolerance: float = 0.0,
        source_label: str = "Oracle",
        target_label: str = "Fabric",
    ) -> None:
        self.tolerance = tolerance
        self.source_label = source_label
        self.target_label = target_label

    def compare_snapshots(
        self,
        source: list[TableSnapshot],
        target: list[TableSnapshot],
    ) -> ReconReport:
        """Compare source and target table snapshots."""
        report = ReconReport(
            source_label=self.source_label,
            target_label=self.target_label,
        )

        target_map = {t.table_name: t for t in target}

        for src_table in source:
            tgt_table = target_map.get(src_table.table_name)
            if tgt_table is None:
                report.checks.append(CheckResult(
                    check_type=CheckType.SCHEMA_MATCH,
                    table=src_table.table_name,
                    status=Status.FAIL,
                    message=f"Table '{src_table.table_name}' missing in target",
                ))
                continue

            report.tables_checked += 1

            # Row count
            status, var, pct = compare_values(
                src_table.row_count, tgt_table.row_count, self.tolerance
            )
            report.checks.append(CheckResult(
                check_type=CheckType.ROW_COUNT,
                table=src_table.table_name,
                source_value=src_table.row_count,
                target_value=tgt_table.row_count,
                variance=var,
                variance_pct=pct,
                status=status,
                tolerance=self.tolerance,
            ))

            # Column-level checks
            for col_name, src_col in src_table.columns.items():
                tgt_col = tgt_table.columns.get(col_name)
                if tgt_col is None:
                    report.checks.append(CheckResult(
                        check_type=CheckType.SCHEMA_MATCH,
                        table=src_table.table_name,
                        column=col_name,
                        status=Status.FAIL,
                        message=f"Column '{col_name}' missing in target",
                    ))
                    continue

                report.columns_checked += 1

                # Null count
                status, var, pct = compare_values(
                    src_col.null_count, tgt_col.null_count, self.tolerance
                )
                report.checks.append(CheckResult(
                    check_type=CheckType.NULL_COUNT,
                    table=src_table.table_name,
                    column=col_name,
                    source_value=src_col.null_count,
                    target_value=tgt_col.null_count,
                    variance=var,
                    variance_pct=pct,
                    status=status,
                ))

                # Distinct count
                status, var, pct = compare_values(
                    src_col.distinct_count, tgt_col.distinct_count, self.tolerance
                )
                report.checks.append(CheckResult(
                    check_type=CheckType.DISTINCT_COUNT,
                    table=src_table.table_name,
                    column=col_name,
                    source_value=src_col.distinct_count,
                    target_value=tgt_col.distinct_count,
                    variance=var,
                    variance_pct=pct,
                    status=status,
                ))

                # Numeric aggregates
                if src_col.sum_value is not None:
                    status, var, pct = compare_values(
                        src_col.sum_value, tgt_col.sum_value, self.tolerance
                    )
                    report.checks.append(CheckResult(
                        check_type=CheckType.SUM_VALUE,
                        table=src_table.table_name,
                        column=col_name,
                        source_value=src_col.sum_value,
                        target_value=tgt_col.sum_value,
                        variance=var,
                        variance_pct=pct,
                        status=status,
                        tolerance=self.tolerance,
                    ))

                if src_col.avg_value is not None:
                    status, var, pct = compare_values(
                        src_col.avg_value, tgt_col.avg_value, self.tolerance
                    )
                    report.checks.append(CheckResult(
                        check_type=CheckType.AVG_VALUE,
                        table=src_table.table_name,
                        column=col_name,
                        source_value=src_col.avg_value,
                        target_value=tgt_col.avg_value,
                        variance=var,
                        variance_pct=pct,
                        status=status,
                        tolerance=self.tolerance,
                    ))

        return report

    def compare_json_files(
        self,
        source_path: str,
        target_path: str,
    ) -> ReconReport:
        """Compare two JSON snapshot files.

        Expected JSON format::

            [
              {
                "table_name": "Sales",
                "row_count": 1000,
                "columns": {
                  "Amount": {"null_count": 0, "distinct_count": 500, "sum_value": 12345.67}
                }
              }
            ]
        """
        source_data = json.loads(Path(source_path).read_text(encoding="utf-8"))
        target_data = json.loads(Path(target_path).read_text(encoding="utf-8"))

        source_snaps = [_dict_to_snapshot(d) for d in source_data]
        target_snaps = [_dict_to_snapshot(d) for d in target_data]

        return self.compare_snapshots(source_snaps, target_snaps)


def _dict_to_snapshot(data: dict[str, Any]) -> TableSnapshot:
    """Convert a dict to a TableSnapshot."""
    columns: dict[str, ColumnSnapshot] = {}
    for col_name, col_data in data.get("columns", {}).items():
        if isinstance(col_data, dict):
            columns[col_name] = ColumnSnapshot(
                name=col_name,
                null_count=col_data.get("null_count", 0),
                distinct_count=col_data.get("distinct_count", 0),
                min_value=col_data.get("min_value"),
                max_value=col_data.get("max_value"),
                sum_value=col_data.get("sum_value"),
                avg_value=col_data.get("avg_value"),
                data_type=col_data.get("data_type", ""),
            )

    return TableSnapshot(
        table_name=data.get("table_name", ""),
        row_count=data.get("row_count", 0),
        columns=columns,
    )


# ---------------------------------------------------------------------------
# Live reconciliation runner
# ---------------------------------------------------------------------------

# Type alias for query executor callback
QueryExecutor = Callable[[str], Any]


class ReconciliationRunner:
    """Execute reconciliation queries against live source and target databases.

    Parameters
    ----------
    source_executor
        Callable that takes a SQL query and returns a scalar result.
    target_executor
        Callable that takes a SQL query and returns a scalar result.
    tolerance
        Default tolerance for numeric comparisons.
    """

    def __init__(
        self,
        source_executor: QueryExecutor,
        target_executor: QueryExecutor,
        *,
        tolerance: float = 0.0001,
        source_label: str = "Oracle",
        target_label: str = "Fabric",
    ) -> None:
        self.source_exec = source_executor
        self.target_exec = target_executor
        self.tolerance = tolerance
        self.source_label = source_label
        self.target_label = target_label

    def run(
        self,
        table_inventory: list[dict[str, Any]],
    ) -> ReconReport:
        """Run reconciliation checks against live databases.

        Parameters
        ----------
        table_inventory
            List of dicts with keys: source_name, target_name, columns.
        """
        report = ReconReport(
            source_label=self.source_label,
            target_label=self.target_label,
        )

        for table in table_inventory:
            src_name = table["source_name"]
            tgt_name = table["target_name"]
            columns = table.get("columns", [])
            report.tables_checked += 1

            # Row count
            self._check_scalar(
                report,
                CheckType.ROW_COUNT,
                src_name,
                f"SELECT COUNT(*) FROM {src_name}",
                f"SELECT COUNT(*) FROM {tgt_name}",
            )

            for col in columns:
                col_name = col["name"]
                col_type = col.get("type", "").lower()
                report.columns_checked += 1

                # Null count
                self._check_scalar(
                    report,
                    CheckType.NULL_COUNT,
                    src_name,
                    f"SELECT COUNT(*) FROM {src_name} WHERE {col_name} IS NULL",
                    f"SELECT COUNT(*) FROM {tgt_name} WHERE {col_name} IS NULL",
                    column=col_name,
                )

                # Distinct count
                self._check_scalar(
                    report,
                    CheckType.DISTINCT_COUNT,
                    src_name,
                    f"SELECT COUNT(DISTINCT {col_name}) FROM {src_name}",
                    f"SELECT COUNT(DISTINCT {col_name}) FROM {tgt_name}",
                    column=col_name,
                )

                # Numeric aggregates
                if _is_numeric(col_type):
                    self._check_scalar(
                        report,
                        CheckType.SUM_VALUE,
                        src_name,
                        f"SELECT SUM({col_name}) FROM {src_name}",
                        f"SELECT SUM({col_name}) FROM {tgt_name}",
                        column=col_name,
                        tolerance=self.tolerance,
                    )
                    self._check_scalar(
                        report,
                        CheckType.AVG_VALUE,
                        src_name,
                        f"SELECT AVG({col_name}) FROM {src_name}",
                        f"SELECT AVG({col_name}) FROM {tgt_name}",
                        column=col_name,
                        tolerance=self.tolerance,
                    )

        return report

    def _check_scalar(
        self,
        report: ReconReport,
        check_type: CheckType,
        table: str,
        source_sql: str,
        target_sql: str,
        *,
        column: str = "",
        tolerance: float = 0.0,
    ) -> None:
        """Execute a single paired query and record result."""
        t0 = time.monotonic()
        try:
            src_val = self.source_exec(source_sql)
            tgt_val = self.target_exec(target_sql)
            duration = int((time.monotonic() - t0) * 1000)

            status, var, pct = compare_values(src_val, tgt_val, tolerance)
            report.checks.append(CheckResult(
                check_type=check_type,
                table=table,
                column=column,
                source_value=src_val,
                target_value=tgt_val,
                variance=var,
                variance_pct=pct,
                status=status,
                tolerance=tolerance,
                duration_ms=duration,
            ))
        except Exception as e:
            duration = int((time.monotonic() - t0) * 1000)
            report.checks.append(CheckResult(
                check_type=check_type,
                table=table,
                column=column,
                status=Status.ERROR,
                message=str(e),
                duration_ms=duration,
            ))


_NUMERIC_TYPES = frozenset({
    "number", "decimal", "int", "integer", "float", "double",
    "bigint", "smallint", "tinyint", "numeric", "real", "money",
    "long", "int64",
})


def _is_numeric(col_type: str) -> bool:
    return col_type.strip().split("(")[0] in _NUMERIC_TYPES


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------


def generate_markdown_report(report: ReconReport) -> str:
    """Generate a Markdown reconciliation report."""
    lines = [
        "# Data Reconciliation Report",
        "",
        f"**Source**: {report.source_label}  ",
        f"**Target**: {report.target_label}  ",
        f"**Tables checked**: {report.tables_checked}  ",
        f"**Columns checked**: {report.columns_checked}  ",
        f"**Total checks**: {report.total}  ",
        f"**Passed**: {report.passed} ({report.pass_rate:.1f}%)  ",
        f"**Failed**: {report.failed}  ",
        f"**Warnings**: {report.warnings}  ",
        "",
    ]

    # Group by table
    tables: dict[str, list[CheckResult]] = {}
    for check in report.checks:
        tables.setdefault(check.table, []).append(check)

    for table_name, checks in sorted(tables.items()):
        passed = sum(1 for c in checks if c.status == Status.PASS)
        total = len(checks)
        icon = "✅" if passed == total else "❌"
        lines.append(f"## {icon} {table_name} ({passed}/{total})")
        lines.append("")
        lines.append("| Check | Column | Source | Target | Variance | Status |")
        lines.append("|-------|--------|--------|--------|----------|--------|")

        for c in checks:
            col = c.column or "—"
            src = str(c.source_value) if c.source_value is not None else "—"
            tgt = str(c.target_value) if c.target_value is not None else "—"
            var = f"{c.variance_pct:.2f}%" if c.variance_pct else "0%"
            status_icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "ERROR": "💥"}.get(c.status.value, "—")
            msg = f" {c.message}" if c.message else ""
            lines.append(f"| {c.check_type.value} | {col} | {src} | {tgt} | {var} | {status_icon}{msg} |")

        lines.append("")

    return "\n".join(lines)


def generate_json_report(report: ReconReport) -> str:
    """Generate a JSON reconciliation report."""
    data = {
        "source": report.source_label,
        "target": report.target_label,
        "tables_checked": report.tables_checked,
        "columns_checked": report.columns_checked,
        "total_checks": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "pass_rate": round(report.pass_rate, 2),
        "checks": [
            {
                "type": c.check_type.value,
                "table": c.table,
                "column": c.column,
                "source": c.source_value,
                "target": c.target_value,
                "variance": c.variance,
                "variance_pct": round(c.variance_pct, 4),
                "status": c.status.value,
                "message": c.message,
            }
            for c in report.checks
        ],
    }
    return json.dumps(data, indent=2, default=str)
