"""TMDL Incremental — delta-based TMDL updates.

Instead of regenerating the entire TMDL semantic model from scratch,
this module computes the minimal set of TMDL file changes required
when only specific assets have been modified.

Integrates with ``incremental_crawler.detect_changes()`` to determine
which tables, measures, and relationships need updating.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Delta operation types
# ---------------------------------------------------------------------------


@dataclass
class TMDLFileOp:
    """A single TMDL file operation."""

    operation: str        # create, update, delete
    file_path: str        # relative path within TMDL folder
    content: str = ""     # new/updated content (empty for delete)
    reason: str = ""      # human-readable reason


@dataclass
class TMDLDeltaPlan:
    """A plan of incremental TMDL changes."""

    operations: list[TMDLFileOp] = field(default_factory=list)
    affected_tables: list[str] = field(default_factory=list)
    affected_measures: list[str] = field(default_factory=list)
    affected_relationships: list[str] = field(default_factory=list)
    requires_full_rebuild: bool = False
    rebuild_reason: str = ""

    @property
    def total_operations(self) -> int:
        return len(self.operations)

    def summary(self) -> str:
        if self.requires_full_rebuild:
            return f"Full rebuild required: {self.rebuild_reason}"
        creates = sum(1 for o in self.operations if o.operation == "create")
        updates = sum(1 for o in self.operations if o.operation == "update")
        deletes = sum(1 for o in self.operations if o.operation == "delete")
        return (
            f"TMDL delta: {creates} create, {updates} update, {deletes} delete "
            f"({len(self.affected_tables)} tables, {len(self.affected_measures)} measures)"
        )


# ---------------------------------------------------------------------------
# Table TMDL snippet generator
# ---------------------------------------------------------------------------


def _generate_table_tmdl(
    table_name: str,
    columns: list[dict[str, str]],
    source_expression: str = "",
) -> str:
    """Generate a single table TMDL file content.

    Parameters
    ----------
    table_name : str
        Table display name.
    columns : list[dict[str, str]]
        Column definitions (name, dataType, sourceColumn).
    source_expression : str
        M expression for the table source.

    Returns
    -------
    str
        TMDL content for the table file.
    """
    lines = [f"table '{table_name}'"]

    if source_expression:
        lines.append(f"\tpartition '{table_name}' = entity")
        lines.append(f"\t\tentityName = '{table_name}'")
        lines.append(f"\t\tschemaCheck = warn")
    else:
        lines.append(f"\tpartition '{table_name}' = entity")
        lines.append(f"\t\tentityName = '{table_name}'")

    for col in columns:
        name = col.get("name", "")
        dtype = col.get("dataType", "String")
        source = col.get("sourceColumn", name)
        lines.append(f"")
        lines.append(f"\tcolumn '{name}'")
        lines.append(f"\t\tdataType = {dtype}")
        lines.append(f"\t\tsourceColumn = '{source}'")

    return "\n".join(lines)


def _generate_measure_tmdl(
    table_name: str,
    measures: list[dict[str, str]],
) -> str:
    """Generate measure TMDL additions for a table.

    Parameters
    ----------
    table_name : str
        Table the measures belong to.
    measures : list[dict[str, str]]
        Measure definitions (name, expression, formatString).

    Returns
    -------
    str
        TMDL measure snippet.
    """
    lines: list[str] = []
    for m in measures:
        name = m.get("name", "")
        expr = m.get("expression", "")
        fmt = m.get("formatString", "")
        lines.append(f"\tmeasure '{name}' = {expr}")
        if fmt:
            lines.append(f"\t\tformatString = {fmt}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------


def compute_tmdl_delta(
    changes: list[dict[str, Any]],
    tmdl_base_path: str = "definition/tables",
) -> TMDLDeltaPlan:
    """Compute incremental TMDL changes from asset change records.

    Parameters
    ----------
    changes : list[dict[str, Any]]
        Change records from ``incremental_crawler.detect_changes()``.
        Each dict must have: ``asset_id``, ``asset_type``, ``change_type``, ``name``.
        Optional: ``columns``, ``measures``, ``relationships``.
    tmdl_base_path : str
        Base path for TMDL table files.

    Returns
    -------
    TMDLDeltaPlan
        Plan of TMDL file operations.
    """
    plan = TMDLDeltaPlan()

    # Check if changes affect model-level structures
    model_level_changes = [
        c for c in changes
        if c.get("asset_type") in ("model", "database", "connection")
    ]
    if model_level_changes:
        plan.requires_full_rebuild = True
        plan.rebuild_reason = (
            f"Model-level changes detected: "
            f"{', '.join(c.get('name', '') for c in model_level_changes)}"
        )
        return plan

    for change in changes:
        asset_type = change.get("asset_type", "")
        change_type = change.get("change_type", "")
        name = change.get("name", "")

        if asset_type == "table":
            file_path = f"{tmdl_base_path}/{name}.tmdl"

            if change_type == "added":
                columns = change.get("columns", [])
                content = _generate_table_tmdl(name, columns)
                plan.operations.append(TMDLFileOp(
                    operation="create",
                    file_path=file_path,
                    content=content,
                    reason=f"New table '{name}' discovered",
                ))
                plan.affected_tables.append(name)

            elif change_type == "modified":
                columns = change.get("columns", [])
                content = _generate_table_tmdl(name, columns)
                plan.operations.append(TMDLFileOp(
                    operation="update",
                    file_path=file_path,
                    content=content,
                    reason=f"Table '{name}' modified",
                ))
                plan.affected_tables.append(name)

            elif change_type == "removed":
                plan.operations.append(TMDLFileOp(
                    operation="delete",
                    file_path=file_path,
                    reason=f"Table '{name}' removed from source",
                ))
                plan.affected_tables.append(name)

        elif asset_type == "measure":
            table = change.get("table", "")
            file_path = f"{tmdl_base_path}/{table}.tmdl"
            plan.affected_measures.append(name)

            if change_type in ("added", "modified"):
                measures = change.get("measures", [{"name": name, "expression": change.get("expression", "")}])
                content = _generate_measure_tmdl(table, measures)
                plan.operations.append(TMDLFileOp(
                    operation="update",
                    file_path=file_path,
                    content=content,
                    reason=f"Measure '{name}' {change_type}",
                ))

        elif asset_type == "relationship":
            plan.affected_relationships.append(name)
            plan.operations.append(TMDLFileOp(
                operation="update",
                file_path="definition/relationships.tmdl",
                reason=f"Relationship '{name}' {change_type}",
            ))

    logger.info(plan.summary())
    return plan


# ---------------------------------------------------------------------------
# Apply delta
# ---------------------------------------------------------------------------


def apply_tmdl_delta(
    plan: TMDLDeltaPlan,
    output_dir: str,
    dry_run: bool = False,
) -> list[str]:
    """Apply TMDL delta operations to disk.

    Parameters
    ----------
    plan : TMDLDeltaPlan
        Delta plan to apply.
    output_dir : str
        Base output directory.
    dry_run : bool
        If True, log operations without writing files.

    Returns
    -------
    list[str]
        List of file paths affected.
    """
    affected: list[str] = []
    base = Path(output_dir)

    for op in plan.operations:
        full_path = base / op.file_path
        affected.append(str(full_path))

        if dry_run:
            logger.info("[DRY RUN] %s: %s — %s", op.operation, op.file_path, op.reason)
            continue

        if op.operation == "create":
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(op.content, encoding="utf-8")
            logger.info("Created: %s", op.file_path)

        elif op.operation == "update":
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(op.content, encoding="utf-8")
            logger.info("Updated: %s", op.file_path)

        elif op.operation == "delete":
            if full_path.exists():
                full_path.unlink()
                logger.info("Deleted: %s", op.file_path)
            else:
                logger.warning("Delete target not found: %s", op.file_path)

    return affected
