"""DDL Generator — produce CREATE TABLE / CREATE VIEW statements for Fabric.

Supports two targets:
  - Lakehouse: Spark SQL (Delta tables)
  - Warehouse: T-SQL

Uses the type mapper to translate Oracle column types.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .type_mapper import TargetPlatform, map_oracle_type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DDL generation for a single table
# ---------------------------------------------------------------------------


def generate_create_table(
    table_name: str,
    columns: list[dict[str, Any]],
    platform: TargetPlatform = TargetPlatform.LAKEHOUSE,
    schema: str | None = None,
    primary_key: list[str] | None = None,
    partition_by: list[str] | None = None,
    comment: str | None = None,
) -> str:
    """Generate a CREATE TABLE statement.

    Parameters
    ----------
    table_name : str
        Target table name (will be sanitised).
    columns : list[dict]
        Each dict must have ``name`` and ``data_type`` (Oracle type).
        Optional: ``nullable`` (bool, default True).
    platform : TargetPlatform
        Lakehouse (Spark SQL) or Warehouse (T-SQL).
    schema : str | None
        Schema / database prefix.
    primary_key : list[str] | None
        Column names forming the primary key (Warehouse only).
    partition_by : list[str] | None
        Partition columns (Lakehouse only).
    comment : str | None
        Table comment.
    """
    full_name = _qualify(table_name, schema, platform)
    col_defs: list[str] = []

    for col in columns:
        col_name = _safe_name(col["name"], platform)
        mapping = map_oracle_type(col.get("data_type", "VARCHAR2(255)"), platform)
        nullable = col.get("nullable", True)

        if platform == TargetPlatform.LAKEHOUSE:
            col_def = f"    {col_name} {mapping.fabric_type}"
            if not nullable:
                col_def += " NOT NULL"
            if col.get("comment"):
                col_def += f" COMMENT '{_escape_sql(col['comment'])}'"
        else:
            col_def = f"    {col_name} {mapping.fabric_type}"
            if not nullable:
                col_def += " NOT NULL"

        col_defs.append(col_def)

    # Primary key (Warehouse T-SQL only — Lakehouse Delta doesn't enforce PK)
    if primary_key and platform == TargetPlatform.WAREHOUSE:
        pk_cols = ", ".join(_safe_name(c, platform) for c in primary_key)
        col_defs.append(f"    CONSTRAINT PK_{_safe_ident(table_name)} PRIMARY KEY NONCLUSTERED ({pk_cols}) NOT ENFORCED")

    lines: list[str] = []
    if platform == TargetPlatform.LAKEHOUSE:
        lines.append(f"CREATE TABLE IF NOT EXISTS {full_name} (")
    else:
        lines.append(f"IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{_escape_sql(table_name)}')")
        lines.append(f"CREATE TABLE {full_name} (")

    lines.append(",\n".join(col_defs))
    lines.append(")")

    # Delta options
    if platform == TargetPlatform.LAKEHOUSE:
        lines.append("USING DELTA")
        if partition_by:
            parts = ", ".join(_safe_name(c, platform) for c in partition_by)
            lines.append(f"PARTITIONED BY ({parts})")
        if comment:
            lines.append(f"COMMENT '{_escape_sql(comment)}'")

    return "\n".join(lines) + ";\n"


def generate_create_view(
    view_name: str,
    sql_body: str,
    platform: TargetPlatform = TargetPlatform.LAKEHOUSE,
    schema: str | None = None,
) -> str:
    """Generate a CREATE VIEW statement.

    The ``sql_body`` should already be translated to the target dialect
    (use ``sql_translator.translate_sql``).
    """
    full_name = _qualify(view_name, schema, platform)

    if platform == TargetPlatform.LAKEHOUSE:
        return f"CREATE OR REPLACE VIEW {full_name} AS\n{sql_body};\n"
    else:
        return (
            f"IF OBJECT_ID('{_escape_sql(full_name)}', 'V') IS NOT NULL\n"
            f"    DROP VIEW {full_name};\nGO\n"
            f"CREATE VIEW {full_name} AS\n{sql_body};\nGO\n"
        )


# ---------------------------------------------------------------------------
# Batch generation
# ---------------------------------------------------------------------------


def generate_ddl_script(
    tables: list[dict[str, Any]],
    platform: TargetPlatform = TargetPlatform.LAKEHOUSE,
    schema: str | None = None,
) -> str:
    """Generate a full DDL script for a list of tables.

    Each table dict should have:
      - ``name``: table name
      - ``columns``: list of column dicts with ``name``, ``data_type``
      - ``primary_key`` (optional): list of PK column names
      - ``partition_by`` (optional): list of partition column names
      - ``comment`` (optional): table comment
    """
    parts: list[str] = []
    parts.append(f"-- DDL script generated for Fabric {platform.value}")
    parts.append(f"-- Tables: {len(tables)}\n")

    for table in tables:
        ddl = generate_create_table(
            table_name=table["name"],
            columns=table.get("columns", []),
            platform=platform,
            schema=schema,
            primary_key=table.get("primary_key"),
            partition_by=table.get("partition_by"),
            comment=table.get("comment"),
        )
        parts.append(ddl)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------


def _safe_name(name: str, platform: TargetPlatform) -> str:
    """Quote an identifier if needed."""
    ident = _safe_ident(name)
    # Only quote if name has special chars or is reserved
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", ident) and ident.upper() not in _RESERVED:
        return ident
    if platform == TargetPlatform.LAKEHOUSE:
        return f"`{ident}`"
    return f"[{ident}]"


def _safe_ident(name: str) -> str:
    """Sanitise a name for use as an identifier."""
    return re.sub(r"[^\w]", "_", name.strip())


def _qualify(name: str, schema: str | None, platform: TargetPlatform) -> str:
    sn = _safe_name(name, platform)
    if schema:
        return f"{_safe_name(schema, platform)}.{sn}"
    return sn


def _escape_sql(s: str) -> str:
    return s.replace("'", "''")


# A minimal set of reserved words to trigger quoting
_RESERVED = frozenset({
    "SELECT", "FROM", "WHERE", "TABLE", "CREATE", "DROP", "ALTER", "INSERT",
    "UPDATE", "DELETE", "INDEX", "VIEW", "ORDER", "GROUP", "BY", "AS", "ON",
    "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS", "UNION",
    "ALL", "AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN", "LIKE", "IS",
    "NULL", "TRUE", "FALSE", "CASE", "WHEN", "THEN", "ELSE", "END",
    "HAVING", "DISTINCT", "LIMIT", "OFFSET", "VALUES", "SET", "INTO",
    "PRIMARY", "KEY", "CONSTRAINT", "DEFAULT", "CHECK", "UNIQUE", "FOREIGN",
    "REFERENCES", "CASCADE", "GRANT", "REVOKE", "USER", "ROLE", "DATE",
    "TIMESTAMP", "INT", "INTEGER", "FLOAT", "DOUBLE", "STRING", "BINARY",
    "BOOLEAN", "DECIMAL", "BIGINT", "SMALLINT",
})
