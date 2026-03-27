"""Bridge table generator for M:N relationships.

Detects many-to-many joins in RPD logical model and generates:
1. Bridge table DDL (Delta Lake CREATE TABLE)
2. TMDL table + relationship definitions
3. M query partition expression
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ManyToManyJoin:
    """Detected M:N join from RPD model."""

    left_table: str
    left_column: str
    right_table: str
    right_column: str
    join_label: str = ""


@dataclass
class BridgeTableSpec:
    """Generated bridge table specification."""

    table_name: str
    left_table: str
    left_column: str
    right_table: str
    right_column: str
    ddl: str
    tmdl: str
    relationships_tmdl: str
    m_expression: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class BridgeGenerationResult:
    """Result of bridge table generation for all M:N joins."""

    bridge_tables: list[BridgeTableSpec] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.bridge_tables)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tag(name: str) -> str:
    """Deterministic lineage tag from name."""
    return hashlib.md5(name.encode()).hexdigest()[:8]  # noqa: S324


def _safe_name(name: str) -> str:
    """Sanitize identifier for Delta table name."""
    import re

    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return sanitized.strip("_") or "bridge"


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_many_to_many(joins: list[dict]) -> list[ManyToManyJoin]:
    """Detect M:N joins from RPD join definitions.

    Args:
        joins: List of join dicts with keys: left_table, left_column,
               right_table, right_column, cardinality (e.g. 'M:N', 'N:M',
               'many-to-many').

    Returns:
        List of ManyToManyJoin instances for M:N relationships.
    """
    mn_joins: list[ManyToManyJoin] = []
    mn_indicators = {"m:n", "n:m", "many-to-many", "many:many", "*:*"}

    for j in joins:
        card = str(j.get("cardinality", "")).lower().strip()
        if card in mn_indicators:
            mn_joins.append(
                ManyToManyJoin(
                    left_table=j.get("left_table", ""),
                    left_column=j.get("left_column", ""),
                    right_table=j.get("right_table", ""),
                    right_column=j.get("right_column", ""),
                    join_label=j.get("label", ""),
                )
            )
    logger.info("Detected %d M:N joins", len(mn_joins))
    return mn_joins


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def _bridge_table_name(left: str, right: str) -> str:
    """Generate bridge table name from two table names."""
    a, b = sorted([_safe_name(left), _safe_name(right)])
    return f"Bridge_{a}_{b}"


def generate_bridge_ddl(spec: ManyToManyJoin) -> str:
    """Generate Delta Lake CREATE TABLE DDL for a bridge table."""
    table_name = _bridge_table_name(spec.left_table, spec.right_table)
    left_col = _safe_name(spec.left_column)
    right_col = _safe_name(spec.right_column)

    return (
        f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        f"    {left_col} STRING NOT NULL,\n"
        f"    {right_col} STRING NOT NULL\n"
        f") USING DELTA\n"
        f"COMMENT 'Bridge table for M:N relationship between "
        f"{spec.left_table} and {spec.right_table}';\n"
    )


def generate_bridge_tmdl(spec: ManyToManyJoin) -> str:
    """Generate TMDL table definition for a bridge table."""
    table_name = _bridge_table_name(spec.left_table, spec.right_table)
    tag = _tag(table_name)
    left_col = _safe_name(spec.left_column)
    right_col = _safe_name(spec.right_column)

    lines = [
        f"table {table_name}",
        f"\tlineageTag: {tag}",
        "",
        f"\tcolumn {left_col}",
        f"\t\tdataType: string",
        f"\t\tlineageTag: {_tag(f'{table_name}.{left_col}')}",
        f"\t\tsummarizeBy: none",
        f"\t\tsourceColumn: {left_col}",
        "",
        f"\tcolumn {right_col}",
        f"\t\tdataType: string",
        f"\t\tlineageTag: {_tag(f'{table_name}.{right_col}')}",
        f"\t\tsummarizeBy: none",
        f"\t\tsourceColumn: {right_col}",
        "",
        f"\tpartition {table_name} = m",
        f'\t\tmode: import',
        f'\t\tsource =',
        f'\t\t\tlet',
        f'\t\t\t\tSource = Sql.Database(null, null),',
        f'\t\t\t\t{table_name}_Table = Source{{[Schema="dbo",'
        f'Item="{table_name}"]}}[Data]',
        f"\t\t\tin",
        f"\t\t\t\t{table_name}_Table",
        "",
    ]
    return "\n".join(lines)


def generate_bridge_relationships(spec: ManyToManyJoin) -> str:
    """Generate TMDL relationships for bridge table (two 1:N relationships)."""
    table_name = _bridge_table_name(spec.left_table, spec.right_table)
    left_col = _safe_name(spec.left_column)
    right_col = _safe_name(spec.right_column)

    tag_left = _tag(f"rel_{spec.left_table}_{table_name}")
    tag_right = _tag(f"rel_{spec.right_table}_{table_name}")

    lines = [
        f"relationship {tag_left}",
        f"\tfromColumn: {table_name}.{left_col}",
        f"\ttoColumn: {spec.left_table}.{_safe_name(spec.left_column)}",
        f"\tcrossFilteringBehavior: bothDirections",
        "",
        f"relationship {tag_right}",
        f"\tfromColumn: {table_name}.{right_col}",
        f"\ttoColumn: {spec.right_table}.{_safe_name(spec.right_column)}",
        f"\tcrossFilteringBehavior: singleDirection",
        "",
    ]
    return "\n".join(lines)


def generate_bridge_m_expression(spec: ManyToManyJoin) -> str:
    """Generate M query expression for bridge table population."""
    table_name = _bridge_table_name(spec.left_table, spec.right_table)
    left_col = _safe_name(spec.left_column)
    right_col = _safe_name(spec.right_column)

    return (
        f"let\n"
        f'    LeftTable = {spec.left_table},\n'
        f'    RightTable = {spec.right_table},\n'
        f"    Joined = Table.Join(LeftTable, "
        f'"{spec.left_column}", RightTable, "{spec.right_column}"),\n'
        f"    Bridge = Table.SelectColumns(Joined, "
        f'{{"{left_col}", "{right_col}"}}),\n'
        f"    Deduplicated = Table.Distinct(Bridge)\n"
        f"in\n"
        f"    Deduplicated"
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def generate_bridge_tables(joins: list[dict]) -> BridgeGenerationResult:
    """Main entry point: detect M:N joins and generate all bridge table artifacts.

    Args:
        joins: List of join dicts from RPD model parser

    Returns:
        BridgeGenerationResult with all generated bridge table specs
    """
    result = BridgeGenerationResult()
    mn_joins = detect_many_to_many(joins)

    for mn in mn_joins:
        if not mn.left_table or not mn.right_table:
            result.warnings.append(
                f"Skipped M:N join with empty table: {mn.join_label}"
            )
            continue
        if not mn.left_column or not mn.right_column:
            result.warnings.append(
                f"Skipped M:N join with empty column: "
                f"{mn.left_table} <-> {mn.right_table}"
            )
            continue

        table_name = _bridge_table_name(mn.left_table, mn.right_table)

        spec = BridgeTableSpec(
            table_name=table_name,
            left_table=mn.left_table,
            left_column=mn.left_column,
            right_table=mn.right_table,
            right_column=mn.right_column,
            ddl=generate_bridge_ddl(mn),
            tmdl=generate_bridge_tmdl(mn),
            relationships_tmdl=generate_bridge_relationships(mn),
            m_expression=generate_bridge_m_expression(mn),
        )
        result.bridge_tables.append(spec)
        logger.info("Generated bridge table: %s", table_name)

    return result
