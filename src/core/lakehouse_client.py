"""Lakehouse client — read/write Delta tables in the coordination Lakehouse.

This module provides a thin wrapper around PySpark + Delta Lake for
storing and retrieving agent coordination data (inventory, tasks, mappings,
validation results, logs).

When running locally (dev/test), it uses a local SparkSession with Delta.
When running on Fabric, it relies on the pre-configured Fabric SparkSession.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from src.core.models import AgentTask, InventoryItem, TaskStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Delta table schemas
# ---------------------------------------------------------------------------

INVENTORY_SCHEMA = StructType(
    [
        StructField("id", StringType(), False),
        StructField("asset_type", StringType(), False),
        StructField("source_path", StringType(), False),
        StructField("name", StringType(), False),
        StructField("owner", StringType(), True),
        StructField("last_modified", TimestampType(), True),
        StructField("metadata", StringType(), True),  # JSON string
        StructField("dependencies", StringType(), True),  # JSON string
        StructField("complexity_score", DoubleType(), True),
        StructField("complexity_category", StringType(), True),
        StructField("migration_status", StringType(), True),
        StructField("migration_wave", IntegerType(), True),
        StructField("incomplete", BooleanType(), True),
        StructField("discovered_at", TimestampType(), True),
        StructField("source", StringType(), True),
    ]
)

AGENT_TASKS_SCHEMA = StructType(
    [
        StructField("id", StringType(), False),
        StructField("agent_id", StringType(), False),
        StructField("wave_id", StringType(), True),
        StructField("task_type", StringType(), False),
        StructField("status", StringType(), False),
        StructField("asset_type", StringType(), True),
        StructField("asset_source_name", StringType(), True),
        StructField("asset_target_name", StringType(), True),
        StructField("started_at", TimestampType(), True),
        StructField("completed_at", TimestampType(), True),
        StructField("duration_ms", IntegerType(), True),
        StructField("retry_count", IntegerType(), True),
        StructField("result", StringType(), True),  # JSON string
        StructField("assigned_by", StringType(), True),
        StructField("last_updated", TimestampType(), True),
    ]
)


# ---------------------------------------------------------------------------
# Lakehouse client
# ---------------------------------------------------------------------------


class LakehouseClient:
    """Manages Delta table operations for the coordination Lakehouse."""

    def __init__(self, spark: SparkSession | None = None, database: str = "oac_migration") -> None:
        self._spark = spark or self._create_local_spark()
        self._database = database
        self._ensure_database()

    # ------------------------------------------------------------------
    # Spark session
    # ------------------------------------------------------------------

    @staticmethod
    def _create_local_spark() -> SparkSession:
        """Create a local SparkSession with Delta Lake support (dev/test)."""
        return (
            SparkSession.builder.appName("oac-migration")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .config("spark.sql.warehouse.dir", "/tmp/oac_migration_warehouse")
            .master("local[*]")
            .getOrCreate()
        )

    def _ensure_database(self) -> None:
        self._spark.sql(f"CREATE DATABASE IF NOT EXISTS {self._database}")
        self._spark.sql(f"USE {self._database}")

    @property
    def spark(self) -> SparkSession:
        return self._spark

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def _table_exists(self, table_name: str) -> bool:
        return self._spark.catalog.tableExists(f"{self._database}.{table_name}")

    def _full_table_name(self, table_name: str) -> str:
        return f"{self._database}.{table_name}"

    # ------------------------------------------------------------------
    # migration_inventory
    # ------------------------------------------------------------------

    def write_inventory(self, items: list[InventoryItem]) -> int:
        """Write (MERGE/upsert) inventory items into the migration_inventory Delta table."""
        if not items:
            return 0

        rows = [item.to_flat_dict() for item in items]
        df = self._spark.createDataFrame(rows, schema=INVENTORY_SCHEMA)  # type: ignore[arg-type]

        table = self._full_table_name("migration_inventory")

        if not self._table_exists("migration_inventory"):
            df.write.format("delta").saveAsTable(table)
            logger.info("Created migration_inventory table with %d rows", len(rows))
        else:
            # MERGE (upsert) by id
            df.createOrReplaceTempView("_inv_updates")
            self._spark.sql(f"""
                MERGE INTO {table} AS target
                USING _inv_updates AS source
                ON target.id = source.id
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
            """)
            logger.info("Merged %d rows into migration_inventory", len(rows))

        return len(rows)

    def read_inventory(
        self,
        asset_type: str | None = None,
        migration_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read inventory items, optionally filtered."""
        if not self._table_exists("migration_inventory"):
            return []

        df: DataFrame = self._spark.table(self._full_table_name("migration_inventory"))

        if asset_type:
            df = df.filter(F.col("asset_type") == asset_type)
        if migration_status:
            df = df.filter(F.col("migration_status") == migration_status)

        rows = df.collect()
        result = []
        for row in rows:
            d = row.asDict()
            d["metadata"] = json.loads(d["metadata"]) if d.get("metadata") else {}
            d["dependencies"] = json.loads(d["dependencies"]) if d.get("dependencies") else []
            result.append(d)
        return result

    def count_inventory(self, asset_type: str | None = None) -> int:
        if not self._table_exists("migration_inventory"):
            return 0
        df = self._spark.table(self._full_table_name("migration_inventory"))
        if asset_type:
            df = df.filter(F.col("asset_type") == asset_type)
        return df.count()

    # ------------------------------------------------------------------
    # agent_tasks
    # ------------------------------------------------------------------

    def write_task(self, task: AgentTask) -> None:
        """Upsert a single agent task."""
        d = task.model_dump(mode="json")
        d["result"] = json.dumps(d["result"])
        df = self._spark.createDataFrame([d], schema=AGENT_TASKS_SCHEMA)  # type: ignore[arg-type]

        table = self._full_table_name("agent_tasks")

        if not self._table_exists("agent_tasks"):
            df.write.format("delta").saveAsTable(table)
        else:
            df.createOrReplaceTempView("_task_update")
            self._spark.sql(f"""
                MERGE INTO {table} AS target
                USING _task_update AS source
                ON target.id = source.id
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
            """)

    def read_tasks(self, agent_id: str | None = None, status: TaskStatus | None = None) -> list[dict[str, Any]]:
        """Read tasks, optionally filtered by agent and/or status."""
        if not self._table_exists("agent_tasks"):
            return []
        df = self._spark.table(self._full_table_name("agent_tasks"))
        if agent_id:
            df = df.filter(F.col("agent_id") == agent_id)
        if status:
            df = df.filter(F.col("status") == status.value)
        return [row.asDict() for row in df.collect()]

    # ------------------------------------------------------------------
    # agent_logs
    # ------------------------------------------------------------------

    def write_log(
        self,
        agent_id: str,
        level: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Append a log entry to the agent_logs table."""
        row = {
            "agent_id": agent_id,
            "level": level,
            "message": message,
            "extra": json.dumps(extra or {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        df = self._spark.createDataFrame([row])

        table = self._full_table_name("agent_logs")
        if not self._table_exists("agent_logs"):
            df.write.format("delta").saveAsTable(table)
        else:
            df.write.format("delta").mode("append").saveAsTable(table)

    # ------------------------------------------------------------------
    # Cleanup (for tests)
    # ------------------------------------------------------------------

    def drop_all_tables(self) -> None:
        """Drop all coordination tables — use only in tests."""
        for t in ("migration_inventory", "agent_tasks", "agent_logs", "mapping_rules", "validation_results"):
            if self._table_exists(t):
                self._spark.sql(f"DROP TABLE {self._full_table_name(t)}")
        logger.info("Dropped all coordination tables")
