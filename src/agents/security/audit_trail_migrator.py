"""Audit Trail Migrator — OAC audit logs → Fabric Unified Audit integration.

Generates audit trail migration configuration to capture OAC usage data
and feed it into Fabric's unified audit logging, preserving historical
access patterns for compliance and governance.

Handles:
  - OAC usage tracking logs → Lakehouse Delta table schema
  - Access history migration (report views, query execution, data exports)
  - Compliance event mapping (login, permission change, data access)
  - Retention policy configuration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAC audit event types
# ---------------------------------------------------------------------------


@dataclass
class OACAuditEvent:
    """An OAC audit log event."""

    event_type: str         # login, query, view_report, export, permission_change
    timestamp: str = ""     # ISO 8601
    user: str = ""
    subject_area: str = ""
    resource_path: str = ""
    action: str = ""
    details: str = ""
    ip_address: str = ""
    session_id: str = ""


# ---------------------------------------------------------------------------
# Fabric audit types
# ---------------------------------------------------------------------------


@dataclass
class AuditTableSchema:
    """Schema for audit trail Delta table in Fabric Lakehouse."""

    table_name: str = "migration_audit_trail"
    columns: list[tuple[str, str]] = field(default_factory=lambda: [
        ("event_id", "STRING"),
        ("event_type", "STRING"),
        ("event_timestamp", "TIMESTAMP"),
        ("user_principal", "STRING"),
        ("source_system", "STRING"),
        ("source_resource", "STRING"),
        ("target_resource", "STRING"),
        ("action", "STRING"),
        ("details", "STRING"),
        ("ip_address", "STRING"),
        ("session_id", "STRING"),
        ("migration_wave", "STRING"),
        ("ingested_at", "TIMESTAMP"),
    ])

    def to_ddl(self) -> str:
        """Generate CREATE TABLE DDL for the audit trail table."""
        col_defs = ",\n    ".join(
            f"{name} {dtype}" for name, dtype in self.columns
        )
        return (
            f"CREATE TABLE IF NOT EXISTS {self.table_name} (\n"
            f"    {col_defs}\n"
            f") USING DELTA\n"
            f"PARTITIONED BY (event_type)\n"
            f"TBLPROPERTIES (\n"
            f"    'delta.autoOptimize.optimizeWrite' = 'true',\n"
            f"    'delta.autoOptimize.autoCompact' = 'true'\n"
            f")"
        )


@dataclass
class RetentionPolicy:
    """Data retention policy for audit logs."""

    retention_days: int = 365
    archive_after_days: int = 90
    archive_format: str = "parquet"
    purge_enabled: bool = False


@dataclass
class AuditPipelineConfig:
    """Configuration for ongoing audit log ingestion pipeline."""

    source_type: str = "OAC_API"       # OAC_API, log_file, database
    batch_size: int = 10000
    schedule: str = "PT1H"             # ISO 8601 duration
    error_handling: str = "continue"   # continue, stop, quarantine

    def to_pipeline_json(self) -> dict[str, Any]:
        """Generate Fabric pipeline activity for audit ingestion."""
        return {
            "name": "IngestAuditTrail",
            "type": "TridentNotebook",
            "typeProperties": {
                "notebookId": "AuditTrailIngestion",
                "parameters": {
                    "batch_size": str(self.batch_size),
                    "source_type": self.source_type,
                    "error_handling": self.error_handling,
                },
            },
            "policy": {
                "timeout": "0.01:00:00",
                "retry": 2,
                "retryIntervalInSeconds": 60,
            },
        }


@dataclass
class AuditMigrationResult:
    """Result of audit trail migration setup."""

    table_ddl: str = ""
    pyspark_ingestion: str = ""
    pipeline_json: dict[str, Any] = field(default_factory=dict)
    retention_policy: RetentionPolicy = field(default_factory=RetentionPolicy)
    event_count: int = 0
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Event type mapping
# ---------------------------------------------------------------------------

_OAC_TO_FABRIC_EVENT: dict[str, str] = {
    "login": "UserLogin",
    "logout": "UserLogout",
    "query": "QueryExecution",
    "view_report": "ReportView",
    "export": "DataExport",
    "permission_change": "PermissionChange",
    "create_analysis": "ArtifactCreated",
    "modify_analysis": "ArtifactModified",
    "delete_analysis": "ArtifactDeleted",
    "schedule_change": "ScheduleModified",
    "data_upload": "DataIngestion",
    "error": "SystemError",
}


# ---------------------------------------------------------------------------
# PySpark ingestion code generation
# ---------------------------------------------------------------------------


def _generate_ingestion_code(
    table_name: str = "migration_audit_trail",
    source_type: str = "OAC_API",
) -> str:
    """Generate PySpark notebook code for audit log ingestion."""
    return f'''# Audit Trail Ingestion — {source_type}
from pyspark.sql import functions as F
from datetime import datetime

# Read raw audit events (from parameter or staging table)
raw_events = spark.read.format("delta").table("staging_audit_events")

# Map OAC event types to Fabric-compatible types
event_mapping = {{
    "login": "UserLogin",
    "query": "QueryExecution",
    "view_report": "ReportView",
    "export": "DataExport",
    "permission_change": "PermissionChange",
}}

mapping_expr = F.create_map([F.lit(x) for pair in event_mapping.items() for x in pair])

audit_df = raw_events.withColumn(
    "event_type",
    F.coalesce(mapping_expr[F.col("event_type")], F.col("event_type"))
).withColumn(
    "source_system", F.lit("OAC")
).withColumn(
    "ingested_at", F.current_timestamp()
)

# Write to audit trail table
audit_df.write.mode("append").format("delta").saveAsTable("{table_name}")

print(f"Ingested {{audit_df.count()}} audit events into {table_name}")
'''


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_audit_migration(
    retention_days: int = 365,
    table_name: str = "migration_audit_trail",
    source_type: str = "OAC_API",
) -> AuditMigrationResult:
    """Generate audit trail migration artifacts.

    Parameters
    ----------
    retention_days : int
        Number of days to retain audit logs.
    table_name : str
        Name of the audit trail Delta table.
    source_type : str
        Source type for audit log ingestion.

    Returns
    -------
    AuditMigrationResult
        Complete audit migration configuration.
    """
    schema = AuditTableSchema(table_name=table_name)
    retention = RetentionPolicy(retention_days=retention_days)
    pipeline_config = AuditPipelineConfig(source_type=source_type)

    result = AuditMigrationResult(
        table_ddl=schema.to_ddl(),
        pyspark_ingestion=_generate_ingestion_code(table_name, source_type),
        pipeline_json=pipeline_config.to_pipeline_json(),
        retention_policy=retention,
    )

    logger.info(
        "Generated audit migration: table='%s', retention=%d days, source='%s'",
        table_name,
        retention_days,
        source_type,
    )
    return result


def map_audit_event(oac_event: OACAuditEvent) -> dict[str, str]:
    """Map a single OAC audit event to Fabric event format.

    Parameters
    ----------
    oac_event : OACAuditEvent
        OAC audit event.

    Returns
    -------
    dict[str, str]
        Fabric-compatible audit event record.
    """
    fabric_type = _OAC_TO_FABRIC_EVENT.get(
        oac_event.event_type.lower(), oac_event.event_type
    )
    return {
        "event_type": fabric_type,
        "event_timestamp": oac_event.timestamp,
        "user_principal": oac_event.user,
        "source_system": "OAC",
        "source_resource": oac_event.resource_path,
        "action": oac_event.action or oac_event.event_type,
        "details": oac_event.details,
        "ip_address": oac_event.ip_address,
        "session_id": oac_event.session_id,
    }
