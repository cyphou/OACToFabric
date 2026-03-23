"""Hierarchy mapper — RPD hierarchies → TMDL hierarchy definitions.

Converts OAC/RPD logical hierarchies (with levels) to Power BI
Tabular Model Definition Language (TMDL) hierarchy structures.

Also handles:
  - Level ordering (ordinal assignment)
  - Column validation against the parent table
  - Multi-level hierarchy flattening hints
  - Date dimension auto-hierarchy detection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .rpd_model_parser import Hierarchy, HierarchyLevel, LogicalTable, SemanticModelIR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TMDL hierarchy types
# ---------------------------------------------------------------------------


@dataclass
class TMDLLevel:
    """A single level within a TMDL hierarchy."""

    name: str
    column_name: str            # Must match a column in the parent table
    ordinal: int = 0
    lineage_tag: str = ""


@dataclass
class TMDLHierarchy:
    """A TMDL hierarchy definition."""

    name: str
    table_name: str
    levels: list[TMDLLevel] = field(default_factory=list)
    lineage_tag: str = ""
    display_folder: str = ""
    description: str = ""
    is_auto_generated: bool = False
    warnings: list[str] = field(default_factory=list)
    requires_review: bool = False
    review_reason: str = ""


# ---------------------------------------------------------------------------
# Date hierarchy auto-detection
# ---------------------------------------------------------------------------

# Common date dimension column patterns (in preferred hierarchy order)
_DATE_LEVEL_ORDER: list[tuple[str, list[str]]] = [
    ("Year", ["year", "yr", "calendar_year", "fiscal_year"]),
    ("Quarter", ["quarter", "qtr", "cal_quarter", "fiscal_quarter"]),
    ("Month", ["month", "mon", "calendar_month", "fiscal_month"]),
    ("Week", ["week", "wk", "week_number"]),
    ("Day", ["day", "date", "day_of_month", "cal_date"]),
]


def _detect_date_hierarchy(table: LogicalTable) -> TMDLHierarchy | None:
    """Attempt to auto-generate a date hierarchy from column names."""
    col_map = {c.name.lower(): c.name for c in table.columns}
    levels: list[TMDLLevel] = []

    for ordinal, (level_name, patterns) in enumerate(_DATE_LEVEL_ORDER):
        for pattern in patterns:
            if pattern in col_map:
                levels.append(
                    TMDLLevel(
                        name=level_name,
                        column_name=col_map[pattern],
                        ordinal=ordinal,
                    )
                )
                break

    # Need at least Year + one more level for a meaningful hierarchy
    if len(levels) >= 2:
        return TMDLHierarchy(
            name="Date",
            table_name=table.name,
            levels=levels,
            display_folder="Hierarchies",
            description="Auto-generated date hierarchy",
            is_auto_generated=True,
        )
    return None


# ---------------------------------------------------------------------------
# Core mapping
# ---------------------------------------------------------------------------


def map_hierarchy(
    hierarchy: Hierarchy,
    table: LogicalTable | None = None,
) -> TMDLHierarchy:
    """Map an RPD Hierarchy to a TMDL hierarchy definition.

    Parameters
    ----------
    hierarchy : Hierarchy
        The RPD hierarchy from the model IR.
    table : LogicalTable | None
        Parent table (used for column validation).
    """
    warnings: list[str] = []
    requires_review = False
    review_reason = ""

    # Validate that level columns exist in the parent table
    table_col_names: set[str] = set()
    if table:
        table_col_names = {c.name for c in table.columns}

    levels: list[TMDLLevel] = []
    for hl in hierarchy.levels:
        col_name = hl.column_name or hl.name
        if table_col_names and col_name not in table_col_names:
            # Try case-insensitive match
            match = next((c for c in table_col_names if c.lower() == col_name.lower()), None)
            if match:
                col_name = match
            else:
                warnings.append(
                    f"Level '{hl.name}' references column '{col_name}' "
                    f"not found in table '{hierarchy.table_name}'"
                )
                requires_review = True
                review_reason = "Missing column references"

        levels.append(
            TMDLLevel(
                name=hl.name,
                column_name=col_name,
                ordinal=hl.ordinal,
            )
        )

    # Ensure ordinals are sequential
    levels.sort(key=lambda lv: lv.ordinal)
    for i, lv in enumerate(levels):
        lv.ordinal = i

    # Flag hierarchies with a single level (unusual)
    if len(levels) <= 1:
        warnings.append("Single-level hierarchy — may not be useful in Power BI")

    return TMDLHierarchy(
        name=hierarchy.name,
        table_name=hierarchy.table_name,
        levels=levels,
        display_folder="Hierarchies",
        description=hierarchy.description,
        warnings=warnings,
        requires_review=requires_review,
        review_reason=review_reason,
    )


def map_all_hierarchies(ir: SemanticModelIR) -> list[TMDLHierarchy]:
    """Map all hierarchies from the semantic model IR.

    Also auto-generates date hierarchies for date tables that don't
    already have one.
    """
    result: list[TMDLHierarchy] = []

    # Map explicit hierarchies
    for table in ir.tables:
        for h in table.hierarchies:
            tmdl_h = map_hierarchy(h, table)
            result.append(tmdl_h)

    # Auto-generate date hierarchies for date tables without one
    tables_with_hierarchies = {h.table_name for h in result}
    for table in ir.tables:
        if table.is_date_table and table.name not in tables_with_hierarchies:
            auto_h = _detect_date_hierarchy(table)
            if auto_h:
                result.append(auto_h)
                logger.info(
                    "Auto-generated date hierarchy for table '%s' with %d levels",
                    table.name, len(auto_h.levels),
                )

    logger.info("Mapped %d hierarchies total", len(result))
    return result


def hierarchy_to_tmdl(hierarchy: TMDLHierarchy) -> str:
    """Render a TMDL hierarchy as a TMDL text fragment.

    Example output::

        hierarchy Geography
            level Country
                column: Country
            level Region
                column: Region
            level City
                column: City
    """
    lines = [f"    hierarchy {hierarchy.name}"]
    if hierarchy.lineage_tag:
        lines.append(f"        lineageTag: {hierarchy.lineage_tag}")
    for level in hierarchy.levels:
        lines.append(f"        level {level.name}")
        lines.append(f"            column: {level.column_name}")
        if level.lineage_tag:
            lines.append(f"            lineageTag: {level.lineage_tag}")
    return "\n".join(lines)
