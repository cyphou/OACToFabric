"""Fabric pipeline generator — 3-stage orchestration pattern.

Ported from T2P's PipelineGenerator — generates Fabric Data Factory
pipeline JSON with 3-stage execution:
  Stage 1: RefreshDataflow activities (parallel data ingestion)
  Stage 2: TridentNotebook activity (PySpark ETL + calculated columns)
  Stage 3: TridentDatasetRefresh activity (DirectLake semantic model refresh)
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline components
# ---------------------------------------------------------------------------


@dataclass
class PipelineActivity:
    """A single activity in a Fabric pipeline."""

    name: str
    activity_type: str          # RefreshDataflow, TridentNotebook, TridentDatasetRefresh
    depends_on: list[str] = field(default_factory=list)
    type_properties: dict[str, Any] = field(default_factory=dict)
    timeout: str = "0.12:00:00"
    retry_count: int = 2
    retry_interval: int = 30

    def to_dict(self) -> dict[str, Any]:
        deps = [
            {
                "activity": dep,
                "dependencyConditions": ["Succeeded"],
            }
            for dep in self.depends_on
        ]
        return {
            "name": self.name,
            "type": self.activity_type,
            "dependsOn": deps,
            "policy": {
                "timeout": self.timeout,
                "retry": self.retry_count,
                "retryIntervalInSeconds": self.retry_interval,
                "secureOutput": False,
                "secureInput": False,
            },
            "typeProperties": self.type_properties,
        }


@dataclass
class FabricPipeline:
    """A complete Fabric Data Factory pipeline definition."""

    name: str
    activities: list[PipelineActivity] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "properties": {
                "description": self.description,
                "activities": [a.to_dict() for a in self.activities],
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# 3-stage pipeline builder
# ---------------------------------------------------------------------------


def build_3_stage_pipeline(
    pipeline_name: str,
    dataflow_ids: list[dict[str, str]],
    notebook_id: str = "",
    notebook_name: str = "",
    semantic_model_id: str = "",
    workspace_id: str = "",
    description: str = "",
) -> FabricPipeline:
    """Build a 3-stage Fabric pipeline.

    Stage 1: RefreshDataflow per datasource (parallel)
    Stage 2: TridentNotebook for PySpark ETL
    Stage 3: TridentDatasetRefresh for semantic model

    Parameters
    ----------
    pipeline_name
        Pipeline name.
    dataflow_ids
        List of dicts with 'name' and 'id' keys for each dataflow.
    notebook_id
        Fabric Notebook artifact ID.
    notebook_name
        Notebook name for reference.
    semantic_model_id
        Semantic model artifact ID for refresh.
    workspace_id
        Target workspace ID.
    description
        Pipeline description.
    """
    activities: list[PipelineActivity] = []
    dataflow_activity_names: list[str] = []

    # Stage 1: RefreshDataflow activities (parallel — no dependencies)
    for df in dataflow_ids:
        act_name = f"Refresh_{df.get('name', 'Dataflow')}"
        dataflow_activity_names.append(act_name)
        activities.append(PipelineActivity(
            name=act_name,
            activity_type="RefreshDataflow",
            depends_on=[],
            type_properties={
                "dataflowId": df.get("id", ""),
                "workspaceId": workspace_id,
            },
        ))

    # Stage 2: TridentNotebook (depends on all Stage 1)
    notebook_activity_name = "Run_ETL_Notebook"
    if notebook_id or notebook_name:
        activities.append(PipelineActivity(
            name=notebook_activity_name,
            activity_type="TridentNotebook",
            depends_on=dataflow_activity_names,
            type_properties={
                "notebookId": notebook_id,
                "workspaceId": workspace_id,
            },
        ))

    # Stage 3: TridentDatasetRefresh (depends on Stage 2)
    if semantic_model_id:
        stage2_dep = [notebook_activity_name] if (notebook_id or notebook_name) else dataflow_activity_names
        activities.append(PipelineActivity(
            name="Refresh_SemanticModel",
            activity_type="TridentDatasetRefresh",
            depends_on=stage2_dep,
            type_properties={
                "datasetId": semantic_model_id,
                "workspaceId": workspace_id,
            },
        ))

    return FabricPipeline(
        name=pipeline_name,
        activities=activities,
        description=description or f"3-stage migration pipeline: {pipeline_name}",
    )


# ---------------------------------------------------------------------------
# JDBC connector templates (9 connectors)
# ---------------------------------------------------------------------------

_SPARK_READ_TEMPLATES: dict[str, str] = {
    "oracle": '''# Oracle JDBC read
jdbc_url = "jdbc:oracle:thin:@{server}:{port}/{service}"
df_{table_var} = spark.read.format("jdbc") \\
    .option("url", jdbc_url) \\
    .option("dbtable", "{schema}.{table_name}") \\
    .option("user", dbutils.secrets.get("{secret_scope}", "oracle-user")) \\
    .option("password", dbutils.secrets.get("{secret_scope}", "oracle-password")) \\
    .option("driver", "oracle.jdbc.driver.OracleDriver") \\
    .load()''',

    "postgresql": '''# PostgreSQL JDBC read
jdbc_url = "jdbc:postgresql://{server}:{port}/{database}"
df_{table_var} = spark.read.format("jdbc") \\
    .option("url", jdbc_url) \\
    .option("dbtable", "{schema}.{table_name}") \\
    .option("user", dbutils.secrets.get("{secret_scope}", "pg-user")) \\
    .option("password", dbutils.secrets.get("{secret_scope}", "pg-password")) \\
    .option("driver", "org.postgresql.Driver") \\
    .load()''',

    "sqlserver": '''# SQL Server JDBC read
jdbc_url = "jdbc:sqlserver://{server}:{port};databaseName={database}"
df_{table_var} = spark.read.format("jdbc") \\
    .option("url", jdbc_url) \\
    .option("dbtable", "{schema}.{table_name}") \\
    .option("user", dbutils.secrets.get("{secret_scope}", "sql-user")) \\
    .option("password", dbutils.secrets.get("{secret_scope}", "sql-password")) \\
    .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver") \\
    .load()''',

    "snowflake": '''# Snowflake read
df_{table_var} = spark.read.format("snowflake") \\
    .option("sfURL", "{server}") \\
    .option("sfUser", dbutils.secrets.get("{secret_scope}", "sf-user")) \\
    .option("sfPassword", dbutils.secrets.get("{secret_scope}", "sf-password")) \\
    .option("sfDatabase", "{database}") \\
    .option("sfSchema", "{schema}") \\
    .option("dbtable", "{table_name}") \\
    .load()''',

    "bigquery": '''# BigQuery read
df_{table_var} = spark.read.format("bigquery") \\
    .option("table", "{project}.{dataset}.{table_name}") \\
    .load()''',

    "csv": '''# CSV file read
df_{table_var} = spark.read.format("csv") \\
    .option("header", "true") \\
    .option("inferSchema", "true") \\
    .load("{file_path}")''',

    "excel": '''# Excel file read (requires openpyxl)
import pandas as pd
pdf = pd.read_excel("{file_path}", sheet_name="{sheet_name}")
df_{table_var} = spark.createDataFrame(pdf)''',

    "custom_sql": '''# Custom SQL query read
jdbc_url = "{jdbc_url}"
df_{table_var} = spark.read.format("jdbc") \\
    .option("url", jdbc_url) \\
    .option("query", """{custom_query}""") \\
    .option("user", dbutils.secrets.get("{secret_scope}", "db-user")) \\
    .option("password", dbutils.secrets.get("{secret_scope}", "db-password")) \\
    .load()''',

    "databricks": '''# Databricks Delta read
df_{table_var} = spark.read.format("delta") \\
    .load("{delta_path}")''',
}


def get_spark_read_template(connector_type: str) -> str | None:
    """Get the PySpark read template for a connector type."""
    return _SPARK_READ_TEMPLATES.get(connector_type.lower())


def list_supported_connectors() -> list[str]:
    """List all supported JDBC connector types."""
    return list(_SPARK_READ_TEMPLATES.keys())


def generate_notebook_cell(
    connector_type: str,
    params: dict[str, str],
) -> str:
    """Generate a PySpark notebook cell for reading from a source.

    Parameters
    ----------
    connector_type
        One of the supported connector types (oracle, postgresql, etc.)
    params
        Template parameters to substitute (server, port, database, etc.)
    """
    template = get_spark_read_template(connector_type)
    if not template:
        return f"# Unsupported connector type: {connector_type}"

    try:
        return template.format(**params)
    except KeyError as e:
        return f"# Missing parameter {e} for connector {connector_type}\n{template}"


def generate_delta_write_cell(table_var: str, table_name: str) -> str:
    """Generate a PySpark cell to write a DataFrame to Delta."""
    return f'''# Write to Delta table
df_{table_var}.write.format("delta") \\
    .mode("overwrite") \\
    .option("overwriteSchema", "true") \\
    .saveAsTable("{table_name}")'''
