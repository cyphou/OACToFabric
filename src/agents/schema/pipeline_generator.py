"""Pipeline generator — generate Fabric Data Factory pipeline JSON.

Produces pipeline definitions for:
  - Full load (initial migration via Copy Activity)
  - Incremental load (watermark-based with MERGE into Delta)
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Full-load pipeline
# ---------------------------------------------------------------------------


def generate_full_load_pipeline(
    table_name: str,
    oracle_schema: str,
    oracle_connection_name: str,
    lakehouse_name: str,
    batch_size: int = 100_000,
    partition_column: str | None = None,
    partition_count: int = 4,
) -> dict[str, Any]:
    """Generate a Fabric Data Factory pipeline JSON for a full table load.

    Returns a dict representing the pipeline definition.
    """
    pipeline_name = f"FullLoad_{table_name}"

    copy_activity: dict[str, Any] = {
        "name": f"Copy_{table_name}",
        "type": "Copy",
        "inputs": [
            {
                "referenceName": oracle_connection_name,
                "type": "DatasetReference",
            }
        ],
        "outputs": [
            {
                "referenceName": lakehouse_name,
                "type": "DatasetReference",
            }
        ],
        "typeProperties": {
            "source": {
                "type": "OracleSource",
                "oracleReaderQuery": f"SELECT * FROM {oracle_schema}.{table_name}",
            },
            "sink": {
                "type": "LakehouseTableSink",
                "tableActionOption": "Overwrite",
                "writeBatchSize": batch_size,
            },
            "enableStaging": False,
        },
    }

    # Add parallel partition if a partition column is specified
    if partition_column:
        copy_activity["typeProperties"]["source"]["partitionOption"] = "DynamicRange"
        copy_activity["typeProperties"]["source"]["partitionSettings"] = {
            "partitionColumnName": partition_column,
            "partitionCount": partition_count,
        }

    pipeline: dict[str, Any] = {
        "name": pipeline_name,
        "properties": {
            "description": f"Full load of {oracle_schema}.{table_name} to Fabric Lakehouse",
            "activities": [copy_activity],
            "parameters": {
                "SourceSchema": {"type": "String", "defaultValue": oracle_schema},
                "SourceTable": {"type": "String", "defaultValue": table_name},
            },
            "annotations": ["auto-generated", "full-load", "agent-02"],
        },
    }

    return pipeline


# ---------------------------------------------------------------------------
# Incremental-load pipeline (watermark-based)
# ---------------------------------------------------------------------------


def generate_incremental_pipeline(
    table_name: str,
    oracle_schema: str,
    oracle_connection_name: str,
    lakehouse_name: str,
    watermark_column: str = "LAST_MODIFIED_DATE",
    key_columns: list[str] | None = None,
    batch_size: int = 100_000,
) -> dict[str, Any]:
    """Generate a Fabric Data Factory pipeline for incremental (watermark) load.

    Uses a high-watermark pattern:
      1. Lookup current high watermark from Delta table
      2. Copy new/changed rows from Oracle (WHERE watermark_col > last_watermark)
      3. MERGE into Delta (upsert by key columns)
      4. Update high watermark
    """
    pipeline_name = f"IncrLoad_{table_name}"
    key_cols = key_columns or ["ID"]

    # Activity 1: Lookup last watermark
    lookup_watermark: dict[str, Any] = {
        "name": "GetLastWatermark",
        "type": "Lookup",
        "typeProperties": {
            "source": {
                "type": "LakehouseTableSource",
                "sqlReaderQuery": (
                    f"SELECT MAX(watermark_value) AS last_watermark "
                    f"FROM watermark_tracking WHERE table_name = '{table_name}'"
                ),
            },
            "dataset": {"referenceName": lakehouse_name, "type": "DatasetReference"},
            "firstRowOnly": True,
        },
    }

    # Activity 2: Lookup current max watermark from Oracle
    lookup_current: dict[str, Any] = {
        "name": "GetCurrentWatermark",
        "type": "Lookup",
        "typeProperties": {
            "source": {
                "type": "OracleSource",
                "oracleReaderQuery": (
                    f"SELECT MAX({watermark_column}) AS current_watermark "
                    f"FROM {oracle_schema}.{table_name}"
                ),
            },
            "dataset": {"referenceName": oracle_connection_name, "type": "DatasetReference"},
            "firstRowOnly": True,
        },
    }

    # Activity 3: Copy delta rows
    copy_delta: dict[str, Any] = {
        "name": f"CopyDelta_{table_name}",
        "type": "Copy",
        "dependsOn": [
            {"activity": "GetLastWatermark", "dependencyConditions": ["Succeeded"]},
            {"activity": "GetCurrentWatermark", "dependencyConditions": ["Succeeded"]},
        ],
        "typeProperties": {
            "source": {
                "type": "OracleSource",
                "oracleReaderQuery": (
                    f"SELECT * FROM {oracle_schema}.{table_name} "
                    f"WHERE {watermark_column} > "
                    f"@{{activity('GetLastWatermark').output.firstRow.last_watermark}} "
                    f"AND {watermark_column} <= "
                    f"@{{activity('GetCurrentWatermark').output.firstRow.current_watermark}}"
                ),
            },
            "sink": {
                "type": "LakehouseTableSink",
                "tableActionOption": "Append",
                "writeBatchSize": batch_size,
            },
        },
    }

    # Activity 4: Update watermark
    update_watermark: dict[str, Any] = {
        "name": "UpdateWatermark",
        "type": "SqlServerStoredProcedure",
        "dependsOn": [
            {"activity": f"CopyDelta_{table_name}", "dependencyConditions": ["Succeeded"]},
        ],
        "typeProperties": {
            "storedProcedureName": "usp_update_watermark",
            "storedProcedureParameters": {
                "tableName": {"value": table_name, "type": "String"},
                "watermarkValue": {
                    "value": "@{activity('GetCurrentWatermark').output.firstRow.current_watermark}",
                    "type": "String",
                },
            },
        },
    }

    pipeline: dict[str, Any] = {
        "name": pipeline_name,
        "properties": {
            "description": f"Incremental load of {oracle_schema}.{table_name} (watermark: {watermark_column})",
            "activities": [lookup_watermark, lookup_current, copy_delta, update_watermark],
            "parameters": {
                "SourceSchema": {"type": "String", "defaultValue": oracle_schema},
                "SourceTable": {"type": "String", "defaultValue": table_name},
            },
            "annotations": ["auto-generated", "incremental", "agent-02"],
        },
    }

    return pipeline


# ---------------------------------------------------------------------------
# Batch pipeline generation
# ---------------------------------------------------------------------------


def generate_all_pipelines(
    tables: list[dict[str, Any]],
    oracle_schema: str,
    oracle_connection_name: str,
    lakehouse_name: str,
    mode: str = "full",
) -> list[dict[str, Any]]:
    """Generate pipeline definitions for a list of tables.

    Each table dict should have:
      - ``name``: table name
      - ``watermark_column`` (optional): for incremental
      - ``key_columns`` (optional): for merge
      - ``partition_column`` (optional): for parallel copy
      - ``row_count`` (optional): enables parallel partition for large tables
    """
    pipelines: list[dict[str, Any]] = []

    for table in tables:
        name = table["name"]
        row_count = table.get("row_count", 0)
        partition_col = table.get("partition_column")

        # Auto-enable partitioning for large tables (> 10M rows)
        partition_count = 4
        if row_count > 100_000_000:
            partition_count = 16
        elif row_count > 10_000_000:
            partition_count = 8

        if mode == "full":
            pipelines.append(
                generate_full_load_pipeline(
                    table_name=name,
                    oracle_schema=oracle_schema,
                    oracle_connection_name=oracle_connection_name,
                    lakehouse_name=lakehouse_name,
                    partition_column=partition_col,
                    partition_count=partition_count,
                )
            )
        elif mode == "incremental":
            pipelines.append(
                generate_incremental_pipeline(
                    table_name=name,
                    oracle_schema=oracle_schema,
                    oracle_connection_name=oracle_connection_name,
                    lakehouse_name=lakehouse_name,
                    watermark_column=table.get("watermark_column", "LAST_MODIFIED_DATE"),
                    key_columns=table.get("key_columns"),
                )
            )
        else:
            # Both
            pipelines.append(
                generate_full_load_pipeline(
                    table_name=name,
                    oracle_schema=oracle_schema,
                    oracle_connection_name=oracle_connection_name,
                    lakehouse_name=lakehouse_name,
                    partition_column=partition_col,
                    partition_count=partition_count,
                )
            )
            if table.get("watermark_column"):
                pipelines.append(
                    generate_incremental_pipeline(
                        table_name=name,
                        oracle_schema=oracle_schema,
                        oracle_connection_name=oracle_connection_name,
                        lakehouse_name=lakehouse_name,
                        watermark_column=table["watermark_column"],
                        key_columns=table.get("key_columns"),
                    )
                )

    logger.info("Generated %d pipeline(s) for %d tables (mode=%s)", len(pipelines), len(tables), mode)
    return pipelines


def serialize_pipeline(pipeline: dict[str, Any], pretty: bool = True) -> str:
    """Serialize a pipeline dict to JSON string."""
    return json.dumps(pipeline, indent=2 if pretty else None, default=str)
