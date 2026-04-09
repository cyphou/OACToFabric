"""RPD logical/presentation model parser — structured semantic layer extraction.

Reads RPD inventory items (produced by Agent 01) and builds a rich
in-memory model suitable for TMDL generation.  This is **not** an XML
parser — it works on the normalised ``InventoryItem`` objects already
stored in the Fabric Lakehouse ``migration_inventory`` Delta table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.models import AssetType, Inventory, InventoryItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ColumnKind(str, Enum):
    """Categorisation of a logical column for TMDL generation."""

    DIRECT = "direct"               # Direct mapping to a physical column
    CALCULATED = "calculated"       # Derived expression → DAX calculated column
    MEASURE = "measure"             # Aggregate expression → DAX measure
    KEY = "key"                     # Table key column


class JoinCardinality(str, Enum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "M:N"


class CrossFilterBehaviour(str, Enum):
    SINGLE = "singleDirection"
    BOTH = "bothDirections"
    AUTOMATIC = "automatic"


# ---------------------------------------------------------------------------
# Data classes — semantic model intermediate representation
# ---------------------------------------------------------------------------


@dataclass
class LogicalColumn:
    """A single column from an RPD logical table."""

    name: str
    data_type: str = ""
    expression: str = ""
    kind: ColumnKind = ColumnKind.DIRECT
    source_table: str = ""
    source_column: str = ""
    display_folder: str = ""
    format_string: str = ""
    description: str = ""
    aggregation: str = ""           # SUM, COUNT, AVG, etc.
    is_hidden: bool = False
    sort_by_column: str = ""        # Column to sort this column by


@dataclass
class HierarchyLevel:
    """A single level within a hierarchy."""

    name: str
    column_name: str
    ordinal: int = 0


@dataclass
class Hierarchy:
    """An RPD hierarchy mapped from the logical layer."""

    name: str
    table_name: str
    levels: list[HierarchyLevel] = field(default_factory=list)
    description: str = ""


@dataclass
class LogicalJoin:
    """A join between two RPD logical tables."""

    from_table: str
    to_table: str
    from_column: str
    to_column: str
    join_type: str = "inner"        # inner | left | right | full
    cardinality: JoinCardinality = JoinCardinality.ONE_TO_MANY
    expression: str = ""            # Complex join expression if any
    is_active: bool = True


@dataclass
class CalculationItem:
    """A single calculation item within a calculation group."""
    name: str
    expression: str = "CALCULATE(SELECTEDMEASURE())"
    ordinal: int | None = None


@dataclass
class CalculationGroup:
    """A calculation group for measure switching."""
    precedence: int = 0
    items: list[CalculationItem] = field(default_factory=list)


@dataclass
class RefreshPolicy:
    """Incremental refresh policy for a table."""
    incremental_granularity: str = "Day"       # Day | Month | Quarter | Year
    incremental_periods: int = 3
    rolling_window_granularity: str = "Month"   # Day | Month | Quarter | Year
    rolling_window_periods: int = 12
    polling_expression: str = ""
    source_expression: str = ""


@dataclass
class LogicalTable:
    """A fully parsed RPD logical table with columns, hierarchies, and metadata."""

    name: str
    columns: list[LogicalColumn] = field(default_factory=list)
    hierarchies: list[Hierarchy] = field(default_factory=list)
    physical_sources: list[str] = field(default_factory=list)
    partition_sql: str = ""         # SQL query for TMDL partition expression
    description: str = ""
    display_folder: str = ""
    is_date_table: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    calculation_group: CalculationGroup | None = None   # Calculation group (measure switching)
    refresh_policy: RefreshPolicy | None = None         # Incremental refresh policy

    @property
    def measures(self) -> list[LogicalColumn]:
        return [c for c in self.columns if c.kind == ColumnKind.MEASURE]

    @property
    def calculated_columns(self) -> list[LogicalColumn]:
        return [c for c in self.columns if c.kind == ColumnKind.CALCULATED]

    @property
    def direct_columns(self) -> list[LogicalColumn]:
        return [c for c in self.columns if c.kind == ColumnKind.DIRECT]


@dataclass
class SubjectArea:
    """An OAC subject area / presentation catalog → maps to a TMDL perspective."""

    name: str
    tables: list[str] = field(default_factory=list)          # Logical table names
    columns: dict[str, list[str]] = field(default_factory=dict)  # table → visible columns
    description: str = ""


@dataclass
class SemanticModelIR:
    """Intermediate Representation of the full OAC semantic layer.

    This is the output of the RPD model parser and the input to the
    TMDL generator.
    """

    tables: list[LogicalTable] = field(default_factory=list)
    joins: list[LogicalJoin] = field(default_factory=list)
    subject_areas: list[SubjectArea] = field(default_factory=list)
    model_name: str = "SemanticModel"
    description: str = ""
    culture: str = "en-US"                                   # Model locale
    cultures: list[str] = field(default_factory=list)        # Additional locale codes

    def table_by_name(self, name: str) -> LogicalTable | None:
        for t in self.tables:
            if t.name == name:
                return t
        return None


# ---------------------------------------------------------------------------
# Column classification heuristics
# ---------------------------------------------------------------------------

# Aggregate functions that indicate a MEASURE
_AGGREGATE_FUNCTIONS = {
    "SUM", "COUNT", "COUNTDISTINCT", "AVG", "MIN", "MAX",
    "AVERAGE", "STDEV", "STDEVP", "VAR", "VARP",
    "FIRST", "LAST",
}

# Time-intelligence functions that indicate a MEASURE
_TIME_INTEL_FUNCTIONS = {
    "AGO", "TODATE", "PERIODROLLING", "RSUM", "MAVG", "MSUM",
}


def _classify_column(col_meta: dict[str, Any]) -> ColumnKind:
    """Determine whether an RPD logical column is DIRECT, CALCULATED, or MEASURE."""
    import re as _re
    expr = (col_meta.get("expression") or "").strip()
    if not expr:
        return ColumnKind.DIRECT

    # Simple physical column reference: "TABLE"."COLUMN" → DIRECT
    if _re.fullmatch(r'"[^"]+"\."[^"]+"', expr):
        return ColumnKind.DIRECT

    expr_upper = expr.upper()

    # Check for aggregate functions → MEASURE
    for fn in _AGGREGATE_FUNCTIONS | _TIME_INTEL_FUNCTIONS:
        if f"{fn}(" in expr_upper:
            return ColumnKind.MEASURE

    # Any non-trivial expression → CALCULATED
    return ColumnKind.CALCULATED


def _detect_aggregation(expression: str) -> str:
    """Extract the aggregate function name from an OAC expression."""
    expr_upper = expression.upper().strip()
    for fn in _AGGREGATE_FUNCTIONS:
        if expr_upper.startswith(f"{fn}("):
            return fn
    return ""


def _is_date_table(table_name: str, columns: list[dict[str, Any]]) -> bool:
    """Heuristic: table is a date/time dimension."""
    name_lower = table_name.lower()
    if any(kw in name_lower for kw in ("date", "time", "calendar", "period")):
        return True
    col_names = {c.get("name", "").lower() for c in columns}
    date_cols = {"year", "month", "quarter", "day", "week"}
    return len(col_names & date_cols) >= 3


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_inventory_to_ir(inventory: Inventory) -> SemanticModelIR:
    """Build a ``SemanticModelIR`` from an Agent 01 Inventory.

    Extracts logical tables, joins, hierarchies, and subject areas from
    the ``InventoryItem`` metadata populated by the RPD parser.
    """
    ir = SemanticModelIR()

    logical_items = inventory.by_type(AssetType.LOGICAL_TABLE)
    subject_area_items = inventory.by_type(AssetType.SUBJECT_AREA)

    # --- Logical tables ---
    for item in logical_items:
        table = _parse_logical_table(item)
        ir.tables.append(table)

    # --- Joins (from dependencies) ---
    for item in logical_items:
        for dep in item.dependencies:
            if dep.dependency_type in ("joins_to", "logical_join"):
                join = _parse_join(item.name, dep)
                ir.joins.append(join)

    # --- Subject areas → perspectives ---
    for item in subject_area_items:
        sa = _parse_subject_area(item)
        ir.subject_areas.append(sa)

    logger.info(
        "Parsed RPD model: %d tables, %d joins, %d subject areas",
        len(ir.tables), len(ir.joins), len(ir.subject_areas),
    )
    return ir


def _parse_logical_table(item: InventoryItem) -> LogicalTable:
    """Convert an InventoryItem (LogicalTable) to a LogicalTable IR object."""
    meta = item.metadata
    raw_cols: list[dict[str, Any]] = meta.get("columns", [])
    raw_hierarchies: list[dict[str, Any]] = meta.get("hierarchies", [])

    columns: list[LogicalColumn] = []
    for c in raw_cols:
        name = c.get("name", "")
        expression = c.get("expression", "")
        kind = _classify_column(c)
        aggregation = _detect_aggregation(expression) if kind == ColumnKind.MEASURE else ""

        # For DIRECT columns with "TABLE"."COL" expression, extract physical column name
        source_col = c.get("source_column", name)
        if kind == ColumnKind.DIRECT and expression:
            import re as _re_src
            m = _re_src.fullmatch(r'"[^"]+"\."([^"]+)"', expression.strip())
            if m:
                source_col = m.group(1)

        columns.append(
            LogicalColumn(
                name=name,
                data_type=c.get("data_type", c.get("dataType", "")),
                expression=expression if kind != ColumnKind.DIRECT else "",
                kind=kind,
                source_table=c.get("source_table", ""),
                source_column=source_col,
                aggregation=aggregation,
                description=c.get("description", ""),
            )
        )

    hierarchies: list[Hierarchy] = []
    for h in raw_hierarchies:
        h_levels = [
            HierarchyLevel(name=lv, column_name=lv, ordinal=i)
            for i, lv in enumerate(h.get("levels", []))
        ]
        hierarchies.append(
            Hierarchy(name=h.get("name", ""), table_name=item.name, levels=h_levels)
        )

    # Physical sources (for partition SQL generation)
    physical_sources = [
        d.target_id for d in item.dependencies if d.dependency_type == "maps_to_physical"
    ]

    return LogicalTable(
        name=item.name,
        columns=columns,
        hierarchies=hierarchies,
        physical_sources=physical_sources,
        is_date_table=_is_date_table(item.name, raw_cols),
        description=meta.get("description", ""),
        metadata=meta,
    )


def _parse_join(from_table: str, dep: Any) -> LogicalJoin:
    """Build a LogicalJoin from a dependency entry."""
    meta = dep.__dict__ if hasattr(dep, "__dict__") else {}
    to_table = dep.target_id
    # Legacy format: "logicalTable__some_name" → "some name"
    if to_table.startswith("logicalTable__"):
        to_table = to_table.replace("logicalTable__", "").replace("_", " ")
    return LogicalJoin(
        from_table=from_table,
        to_table=to_table,
        from_column=meta.get("from_column", ""),
        to_column=meta.get("to_column", ""),
        join_type=meta.get("join_type", "inner"),
        expression=meta.get("expression", ""),
    )


def _parse_subject_area(item: InventoryItem) -> SubjectArea:
    """Build a SubjectArea from an InventoryItem."""
    meta = item.metadata
    tables_meta = meta.get("tables", [])
    table_names = [t.get("name", "") for t in tables_meta if t.get("name")]
    columns_map = {
        t.get("name", ""): t.get("columns", []) for t in tables_meta if t.get("name")
    }
    return SubjectArea(
        name=item.name,
        tables=table_names,
        columns=columns_map,
        description=meta.get("description", ""),
    )
