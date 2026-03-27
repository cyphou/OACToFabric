"""Post-migration schema drift detection.

Captures schema snapshots (table structures) and compares
them over time to detect drift: new columns, type changes,
missing tables, renamed columns, etc.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ColumnSnapshot:
    """Snapshot of a single column."""

    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False


@dataclass
class TableSnapshot:
    """Snapshot of a single table's schema."""

    table_name: str
    columns: list[ColumnSnapshot] = field(default_factory=list)
    row_count: int | None = None

    @property
    def column_names(self) -> set[str]:
        return {c.name for c in self.columns}

    @property
    def column_map(self) -> dict[str, ColumnSnapshot]:
        return {c.name: c for c in self.columns}


@dataclass
class SchemaSnapshot:
    """Full schema snapshot (all tables at a point in time)."""

    snapshot_id: str = ""
    captured_at: str = ""
    tables: list[TableSnapshot] = field(default_factory=list)

    @property
    def table_names(self) -> set[str]:
        return {t.table_name for t in self.tables}

    @property
    def table_map(self) -> dict[str, TableSnapshot]:
        return {t.table_name: t for t in self.tables}

    def to_json(self) -> str:
        """Serialize snapshot to JSON."""
        data = {
            "snapshotId": self.snapshot_id,
            "capturedAt": self.captured_at,
            "tables": [
                {
                    "tableName": t.table_name,
                    "rowCount": t.row_count,
                    "columns": [
                        {
                            "name": c.name,
                            "dataType": c.data_type,
                            "isNullable": c.is_nullable,
                            "isPrimaryKey": c.is_primary_key,
                        }
                        for c in t.columns
                    ],
                }
                for t in self.tables
            ],
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SchemaSnapshot":
        """Deserialize snapshot from JSON."""
        data = json.loads(json_str)
        snap = cls(
            snapshot_id=data.get("snapshotId", ""),
            captured_at=data.get("capturedAt", ""),
        )
        for t in data.get("tables", []):
            ts = TableSnapshot(
                table_name=t["tableName"],
                row_count=t.get("rowCount"),
            )
            for c in t.get("columns", []):
                ts.columns.append(
                    ColumnSnapshot(
                        name=c["name"],
                        data_type=c["dataType"],
                        is_nullable=c.get("isNullable", True),
                        is_primary_key=c.get("isPrimaryKey", False),
                    )
                )
            snap.tables.append(ts)
        return snap


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


@dataclass
class DriftItem:
    """Single schema drift finding."""

    drift_type: str  # added_table, dropped_table, added_column, dropped_column, type_change, row_count_change
    table_name: str
    column_name: str = ""
    old_value: str = ""
    new_value: str = ""
    severity: str = "info"  # info, warning, critical


@dataclass
class DriftReport:
    """Schema drift comparison report."""

    baseline_id: str
    current_id: str
    compared_at: str = ""
    drifts: list[DriftItem] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.drifts)

    @property
    def has_critical(self) -> bool:
        return any(d.severity == "critical" for d in self.drifts)

    @property
    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for d in self.drifts:
            counts[d.drift_type] = counts.get(d.drift_type, 0) + 1
        return counts

    def to_json(self) -> str:
        return json.dumps(
            {
                "baselineId": self.baseline_id,
                "currentId": self.current_id,
                "comparedAt": self.compared_at,
                "driftCount": self.count,
                "hasCritical": self.has_critical,
                "summary": self.summary,
                "drifts": [
                    {
                        "type": d.drift_type,
                        "table": d.table_name,
                        "column": d.column_name,
                        "oldValue": d.old_value,
                        "newValue": d.new_value,
                        "severity": d.severity,
                    }
                    for d in self.drifts
                ],
            },
            indent=2,
        )


def compare_snapshots(
    baseline: SchemaSnapshot,
    current: SchemaSnapshot,
) -> DriftReport:
    """Compare two schema snapshots and report drift.

    Args:
        baseline: Reference snapshot (captured at migration time)
        current: Current snapshot (captured during validation)

    Returns:
        DriftReport with all detected drifts
    """
    report = DriftReport(
        baseline_id=baseline.snapshot_id,
        current_id=current.snapshot_id,
        compared_at=datetime.now(timezone.utc).isoformat(),
    )

    baseline_tables = baseline.table_names
    current_tables = current.table_names

    # Dropped tables
    for tbl in sorted(baseline_tables - current_tables):
        report.drifts.append(
            DriftItem(
                drift_type="dropped_table",
                table_name=tbl,
                old_value=tbl,
                severity="critical",
            )
        )

    # Added tables
    for tbl in sorted(current_tables - baseline_tables):
        report.drifts.append(
            DriftItem(
                drift_type="added_table",
                table_name=tbl,
                new_value=tbl,
                severity="info",
            )
        )

    # Compare common tables
    bmap = baseline.table_map
    cmap = current.table_map

    for tbl in sorted(baseline_tables & current_tables):
        bt = bmap[tbl]
        ct = cmap[tbl]

        # Dropped columns
        for col in sorted(bt.column_names - ct.column_names):
            report.drifts.append(
                DriftItem(
                    drift_type="dropped_column",
                    table_name=tbl,
                    column_name=col,
                    old_value=bt.column_map[col].data_type,
                    severity="critical",
                )
            )

        # Added columns
        for col in sorted(ct.column_names - bt.column_names):
            report.drifts.append(
                DriftItem(
                    drift_type="added_column",
                    table_name=tbl,
                    column_name=col,
                    new_value=ct.column_map[col].data_type,
                    severity="warning",
                )
            )

        # Type changes
        for col in sorted(bt.column_names & ct.column_names):
            old_type = bt.column_map[col].data_type.lower()
            new_type = ct.column_map[col].data_type.lower()
            if old_type != new_type:
                report.drifts.append(
                    DriftItem(
                        drift_type="type_change",
                        table_name=tbl,
                        column_name=col,
                        old_value=old_type,
                        new_value=new_type,
                        severity="warning",
                    )
                )

        # Row count change (if available)
        if bt.row_count is not None and ct.row_count is not None:
            if bt.row_count > 0:
                pct_change = abs(ct.row_count - bt.row_count) / bt.row_count * 100
                if pct_change > 50:
                    report.drifts.append(
                        DriftItem(
                            drift_type="row_count_change",
                            table_name=tbl,
                            old_value=str(bt.row_count),
                            new_value=str(ct.row_count),
                            severity="warning" if pct_change < 90 else "critical",
                        )
                    )

    logger.info(
        "Drift report: %d findings (%d critical)",
        report.count,
        sum(1 for d in report.drifts if d.severity == "critical"),
    )
    return report


# ---------------------------------------------------------------------------
# Snapshot capture from inventory
# ---------------------------------------------------------------------------


def capture_snapshot(
    table_inventory: list[dict],
    snapshot_id: str = "",
) -> SchemaSnapshot:
    """Capture a schema snapshot from table inventory.

    Args:
        table_inventory: List of table dicts (name, columns[name, data_type, ...], row_count)
        snapshot_id: Optional identifier for this snapshot

    Returns:
        SchemaSnapshot ready for serialization/comparison
    """
    snap = SchemaSnapshot(
        snapshot_id=snapshot_id or f"snap-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        captured_at=datetime.now(timezone.utc).isoformat(),
    )

    for tbl in table_inventory:
        ts = TableSnapshot(
            table_name=tbl.get("name", ""),
            row_count=tbl.get("row_count"),
        )
        for col in tbl.get("columns", []):
            ts.columns.append(
                ColumnSnapshot(
                    name=col.get("name", ""),
                    data_type=col.get("data_type", "string"),
                    is_nullable=col.get("is_nullable", True),
                    is_primary_key=col.get("is_primary_key", False),
                )
            )
        snap.tables.append(ts)

    logger.info(
        "Captured snapshot '%s': %d tables",
        snap.snapshot_id, len(snap.tables),
    )
    return snap
