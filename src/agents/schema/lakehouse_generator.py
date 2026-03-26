"""Fabric Lakehouse artifact generator.

Ported from T2P's LakehouseGenerator — produces the 3-artifact set:
  1. lakehouse_definition.json — Table list with metadata
  2. ddl/ folder — CREATE TABLE IF NOT EXISTS per table
  3. table_metadata.json — Summary statistics

Works in concert with schema_agent.py and ddl_generator.py.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .fabric_naming import sanitize_column_name, sanitize_table_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Spark type map (RPD/Oracle semantic types → Spark SQL)
# ---------------------------------------------------------------------------

SPARK_TYPE_MAP: dict[str, str] = {
    # String types
    "string": "STRING",
    "varchar": "STRING",
    "varchar2": "STRING",
    "nvarchar": "STRING",
    "nvarchar2": "STRING",
    "char": "STRING",
    "nchar": "STRING",
    "clob": "STRING",
    "nclob": "STRING",
    "text": "STRING",
    # Numeric types
    "int": "INT",
    "integer": "INT",
    "smallint": "SMALLINT",
    "tinyint": "TINYINT",
    "bigint": "BIGINT",
    "int64": "BIGINT",
    "number": "DECIMAL(19,4)",
    "numeric": "DECIMAL(19,4)",
    "decimal": "DECIMAL(19,4)",
    "float": "DOUBLE",
    "double": "DOUBLE",
    "binary_float": "FLOAT",
    "binary_double": "DOUBLE",
    "real": "DOUBLE",
    "currency": "DECIMAL(19,4)",
    # Date/time types
    "date": "DATE",
    "datetime": "TIMESTAMP",
    "timestamp": "TIMESTAMP",
    "timestamp_tz": "TIMESTAMP",
    # Boolean
    "boolean": "BOOLEAN",
    "bool": "BOOLEAN",
    # Binary
    "blob": "BINARY",
    "raw": "BINARY",
    "long_raw": "BINARY",
}


def map_to_spark_type(oracle_type: str) -> str:
    """Map an Oracle/RPD type to a Spark SQL type.

    Uses a 3-level strategy:
    1. Direct match (exact type name)
    2. Base type (strip parenthesized precision)
    3. Fallback to STRING
    """
    otype = oracle_type.strip().lower()

    # Level 1: Direct match
    if otype in SPARK_TYPE_MAP:
        return SPARK_TYPE_MAP[otype]

    # Level 2: Strip precision/scale
    base = otype.split("(")[0].strip()
    if base in SPARK_TYPE_MAP:
        return SPARK_TYPE_MAP[base]

    # Level 3: Fallback
    logger.warning("Unknown type '%s' — falling back to STRING", oracle_type)
    return "STRING"


# ---------------------------------------------------------------------------
# Lakehouse definition
# ---------------------------------------------------------------------------


@dataclass
class LakehouseColumn:
    """A column in a lakehouse table."""

    name: str
    original_name: str
    spark_type: str
    is_nullable: bool = True
    description: str = ""


@dataclass
class LakehouseTable:
    """A table in the lakehouse definition."""

    name: str
    original_name: str
    columns: list[LakehouseColumn] = field(default_factory=list)
    partition_columns: list[str] = field(default_factory=list)
    estimated_rows: int = 0
    description: str = ""


@dataclass
class LakehouseDefinition:
    """Complete lakehouse artifact set."""

    tables: list[LakehouseTable] = field(default_factory=list)
    lakehouse_name: str = "MigrationLakehouse"

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def total_columns(self) -> int:
        return sum(len(t.columns) for t in self.tables)


# ---------------------------------------------------------------------------
# Generator functions
# ---------------------------------------------------------------------------


def build_lakehouse_definition(
    tables: list[dict[str, Any]],
    lakehouse_name: str = "MigrationLakehouse",
) -> LakehouseDefinition:
    """Build a LakehouseDefinition from inventory table metadata.

    Parameters
    ----------
    tables
        List of table dicts with keys: name, columns, estimated_rows, etc.
    lakehouse_name
        Name for the lakehouse.
    """
    lh_tables: list[LakehouseTable] = []

    for tbl in tables:
        tbl_name = sanitize_table_name(tbl.get("name", "unknown"))
        original_name = tbl.get("name", "")

        columns: list[LakehouseColumn] = []
        for col in tbl.get("columns", []):
            col_name = sanitize_column_name(col.get("name", "unknown"))
            original_col = col.get("name", "")
            spark_type = map_to_spark_type(col.get("data_type", "STRING"))
            columns.append(LakehouseColumn(
                name=col_name,
                original_name=original_col,
                spark_type=spark_type,
                is_nullable=col.get("nullable", True),
                description=col.get("description", ""),
            ))

        lh_tables.append(LakehouseTable(
            name=tbl_name,
            original_name=original_name,
            columns=columns,
            partition_columns=tbl.get("partition_columns", []),
            estimated_rows=tbl.get("estimated_rows", 0),
            description=tbl.get("description", ""),
        ))

    return LakehouseDefinition(tables=lh_tables, lakehouse_name=lakehouse_name)


def generate_lakehouse_definition_json(definition: LakehouseDefinition) -> str:
    """Generate lakehouse_definition.json content."""
    tables_json = []
    for tbl in definition.tables:
        cols_json = [
            {
                "name": col.name,
                "originalName": col.original_name,
                "type": col.spark_type,
                "nullable": col.is_nullable,
                "description": col.description,
            }
            for col in tbl.columns
        ]
        tables_json.append({
            "name": tbl.name,
            "originalName": tbl.original_name,
            "columns": cols_json,
            "partitionColumns": tbl.partition_columns,
            "estimatedRows": tbl.estimated_rows,
            "description": tbl.description,
        })

    result = {
        "lakehouseName": definition.lakehouse_name,
        "tableCount": definition.table_count,
        "totalColumns": definition.total_columns,
        "tables": tables_json,
    }
    return json.dumps(result, indent=2)


def generate_ddl_script(table: LakehouseTable) -> str:
    """Generate a CREATE TABLE IF NOT EXISTS DDL for a single table."""
    col_defs = []
    for col in table.columns:
        nullable = "" if col.is_nullable else " NOT NULL"
        comment = f" COMMENT '{col.description}'" if col.description else ""
        col_defs.append(f"    {col.name} {col.spark_type}{nullable}{comment}")

    cols_str = ",\n".join(col_defs)
    ddl = f"CREATE TABLE IF NOT EXISTS {table.name} (\n{cols_str}\n)"

    if table.partition_columns:
        parts = ", ".join(table.partition_columns)
        ddl += f"\nPARTITIONED BY ({parts})"

    ddl += "\nUSING DELTA;"
    return ddl


def generate_table_metadata_json(definition: LakehouseDefinition) -> str:
    """Generate table_metadata.json — summary statistics."""
    tables_meta = []
    for tbl in definition.tables:
        tables_meta.append({
            "name": tbl.name,
            "originalName": tbl.original_name,
            "columnCount": len(tbl.columns),
            "estimatedRows": tbl.estimated_rows,
            "hasPartitions": bool(tbl.partition_columns),
        })

    result = {
        "lakehouseName": definition.lakehouse_name,
        "tableCount": definition.table_count,
        "totalColumns": definition.total_columns,
        "tables": tables_meta,
    }
    return json.dumps(result, indent=2)


def generate_all_artifacts(
    definition: LakehouseDefinition,
) -> dict[str, str]:
    """Generate the complete 3-artifact set as a dict of path → content.

    Returns dict with keys:
    - lakehouse_definition.json
    - table_metadata.json
    - ddl/{table_name}.sql (one per table)
    """
    files: dict[str, str] = {}

    files["lakehouse_definition.json"] = generate_lakehouse_definition_json(definition)
    files["table_metadata.json"] = generate_table_metadata_json(definition)

    for table in definition.tables:
        files[f"ddl/{table.name}.sql"] = generate_ddl_script(table)

    logger.info(
        "Generated lakehouse artifacts: %d tables, %d files",
        definition.table_count, len(files),
    )
    return files
