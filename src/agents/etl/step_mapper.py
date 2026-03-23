"""Step Mapper — translate OAC data flow steps to Fabric equivalents.

Maps each ``DataFlowStep`` to one or more Fabric artefacts:
  - Data Factory pipeline activities (Copy, Filter, ForEach, etc.)
  - PySpark DataFrame operations (for Notebook-based ETL)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .dataflow_parser import DataFlow, DataFlowStep, StepType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapped output types
# ---------------------------------------------------------------------------


class FabricTargetType:
    """Constants for Fabric artefact types."""

    COPY_ACTIVITY = "CopyActivity"
    FILTER_ACTIVITY = "FilterActivity"
    LOOKUP_ACTIVITY = "LookupActivity"
    FOREACH_ACTIVITY = "ForEachActivity"
    IF_CONDITION = "IfConditionActivity"
    SWITCH_ACTIVITY = "SwitchActivity"
    DATAFLOW_GEN2 = "DataflowGen2"
    NOTEBOOK = "Notebook"
    STORED_PROCEDURE = "StoredProcedureActivity"
    DERIVED_COLUMN = "DerivedColumn"
    SELECT_COLUMN = "SelectColumn"
    JOIN = "JoinTransformation"
    AGGREGATE = "AggregateTransformation"
    UNION = "UnionTransformation"
    SORT = "SortTransformation"
    UNKNOWN = "Unknown"


@dataclass
class MappedStep:
    """A single OAC step mapped to its Fabric equivalent(s)."""

    original_step: DataFlowStep
    fabric_type: str
    fabric_activity_json: dict[str, Any] = field(default_factory=dict)
    pyspark_code: str = ""
    notes: str = ""
    requires_review: bool = False
    review_reason: str = ""


@dataclass
class MappedDataFlow:
    """Complete mapping result for one data flow."""

    flow_id: str
    flow_name: str
    mapped_steps: list[MappedStep] = field(default_factory=list)
    pipeline_json: dict[str, Any] = field(default_factory=dict)
    notebook_code: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def review_required(self) -> list[MappedStep]:
        return [s for s in self.mapped_steps if s.requires_review]


# ---------------------------------------------------------------------------
# Step-level mapping
# ---------------------------------------------------------------------------


def map_step(step: DataFlowStep, oracle_schema: str = "OACS") -> MappedStep:
    """Map a single OAC DataFlowStep to its Fabric equivalent."""
    mapper = _STEP_MAPPERS.get(step.step_type, _map_custom)
    return mapper(step, oracle_schema)


def _map_source_db(step: DataFlowStep, schema: str) -> MappedStep:
    """SOURCE_DB → Copy Activity (source side)."""
    table = step.source_table or step.name
    activity = {
        "name": f"Read_{table}",
        "type": "Copy",
        "typeProperties": {
            "source": {
                "type": "OracleSource",
                "oracleReaderQuery": f"SELECT * FROM {schema}.{table}",
            },
            "sink": {
                "type": "LakehouseTableSink",
                "tableActionOption": "Overwrite",
            },
        },
    }
    pyspark = (
        f'df_{_safe_var(table)} = spark.read.format("jdbc") \\\n'
        f'    .option("url", oracle_jdbc_url) \\\n'
        f'    .option("dbtable", "{schema}.{table}") \\\n'
        f'    .option("driver", "oracle.jdbc.OracleDriver") \\\n'
        f"    .load()\n"
    )
    return MappedStep(
        original_step=step,
        fabric_type=FabricTargetType.COPY_ACTIVITY,
        fabric_activity_json=activity,
        pyspark_code=pyspark,
    )


def _map_source_file(step: DataFlowStep, schema: str) -> MappedStep:
    """SOURCE_FILE → Copy Activity (file source)."""
    path = step.source_table or step.name
    activity = {
        "name": f"ReadFile_{step.name}",
        "type": "Copy",
        "typeProperties": {
            "source": {
                "type": "DelimitedTextSource",
                "storeSettings": {"type": "AzureBlobFSReadSettings", "recursive": True},
            },
            "sink": {"type": "LakehouseTableSink"},
        },
    }
    pyspark = (
        f'df_{_safe_var(step.name)} = spark.read.format("csv") \\\n'
        f'    .option("header", "true") \\\n'
        f'    .option("inferSchema", "true") \\\n'
        f'    .load("Files/{path}")\n'
    )
    return MappedStep(
        original_step=step,
        fabric_type=FabricTargetType.COPY_ACTIVITY,
        fabric_activity_json=activity,
        pyspark_code=pyspark,
    )


def _map_filter(step: DataFlowStep, schema: str) -> MappedStep:
    """FILTER → Dataflow Filter / Spark .filter()."""
    expr = step.filter_expression or "true"
    activity = {
        "name": f"Filter_{step.name}",
        "type": "Filter",
        "typeProperties": {
            "condition": {"value": f"@equals(item().status, '{expr}')"},
        },
    }
    pyspark = f'df = df.filter("{expr}")\n'
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.FILTER_ACTIVITY,
        fabric_activity_json=activity, pyspark_code=pyspark,
    )


def _map_join(step: DataFlowStep, schema: str) -> MappedStep:
    """JOIN → Data Flow Join / Spark .join()."""
    jtype = (step.join_type or "INNER").upper()
    spark_jtype = {"INNER": "inner", "LEFT": "left", "RIGHT": "right",
                   "FULL": "outer", "CROSS": "cross"}.get(jtype, "inner")
    condition = step.join_condition or "1=1"

    activity = {
        "name": f"Join_{step.name}",
        "type": "DataflowJoin",
        "typeProperties": {
            "joinType": jtype,
            "condition": condition,
        },
    }
    left_var = _safe_var(step.upstream_step_ids[0]) if step.upstream_step_ids else "df_left"
    right_var = _safe_var(step.upstream_step_ids[1]) if len(step.upstream_step_ids) > 1 else "df_right"
    pyspark = f'df = {left_var}.join({right_var}, on={repr(condition)}, how="{spark_jtype}")\n'
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.JOIN,
        fabric_activity_json=activity, pyspark_code=pyspark,
    )


def _map_aggregate(step: DataFlowStep, schema: str) -> MappedStep:
    """AGGREGATE → Spark .groupBy().agg()."""
    group_cols = step.group_by_columns or ["all"]
    agg_exprs = step.aggregate_expressions

    agg_parts = []
    for ae in agg_exprs:
        agg_parts.append(ae.get("expression", "count(*)"))

    group_str = ", ".join(f'"{c}"' for c in group_cols)
    agg_str = ", ".join(agg_parts)

    activity = {
        "name": f"Agg_{step.name}",
        "type": "DataflowAggregate",
        "typeProperties": {
            "groupBy": group_cols,
            "aggregations": agg_exprs,
        },
    }
    pyspark = f"df = df.groupBy({group_str}).agg({agg_str})\n"
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.AGGREGATE,
        fabric_activity_json=activity, pyspark_code=pyspark,
    )


def _map_lookup(step: DataFlowStep, schema: str) -> MappedStep:
    """LOOKUP → Lookup Activity / broadcast join."""
    table = step.source_table or step.name
    activity = {
        "name": f"Lookup_{step.name}",
        "type": "Lookup",
        "typeProperties": {
            "source": {
                "type": "OracleSource",
                "oracleReaderQuery": f"SELECT * FROM {schema}.{table}",
            },
            "firstRowOnly": False,
        },
    }
    pyspark = (
        f"from pyspark.sql.functions import broadcast\n"
        f'df_lookup = spark.table("{table}")\n'
        f"df = df.join(broadcast(df_lookup), on=..., how=\"left\")\n"
    )
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.LOOKUP_ACTIVITY,
        fabric_activity_json=activity, pyspark_code=pyspark,
        notes="Review join keys for broadcast join",
    )


def _map_union(step: DataFlowStep, schema: str) -> MappedStep:
    """UNION → Spark .union()."""
    activity = {
        "name": f"Union_{step.name}",
        "type": "DataflowUnion",
    }
    upstreams = " .union(".join(_safe_var(u) for u in step.upstream_step_ids) if step.upstream_step_ids else "df_a.union(df_b)"
    pyspark = f"df = {upstreams})\n" if step.upstream_step_ids else "df = df_a.union(df_b)\n"
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.UNION,
        fabric_activity_json=activity, pyspark_code=pyspark,
    )


def _map_sort(step: DataFlowStep, schema: str) -> MappedStep:
    """SORT → Spark .orderBy()."""
    cols = step.sort_columns
    order_parts = []
    for sc in cols:
        col = sc.get("column", "id")
        order = sc.get("order", "ASC")
        if order.upper() == "DESC":
            order_parts.append(f'F.col("{col}").desc()')
        else:
            order_parts.append(f'F.col("{col}").asc()')

    order_str = ", ".join(order_parts) if order_parts else '"id"'
    pyspark = f"from pyspark.sql import functions as F\ndf = df.orderBy({order_str})\n"
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.SORT,
        fabric_activity_json={"name": f"Sort_{step.name}", "type": "DataflowSort"},
        pyspark_code=pyspark,
    )


def _map_add_column(step: DataFlowStep, schema: str) -> MappedStep:
    """ADD_COLUMN / DERIVED_COLUMN → Spark .withColumn()."""
    parts = []
    for col in step.columns:
        expr = col.expression or f"lit(None)"
        alias = col.alias or col.name
        parts.append(f'df = df.withColumn("{alias}", F.expr("{expr}"))')

    pyspark = "from pyspark.sql import functions as F\n" + "\n".join(parts) + "\n"
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.DERIVED_COLUMN,
        fabric_activity_json={"name": f"DerivedCol_{step.name}", "type": "DerivedColumn"},
        pyspark_code=pyspark,
    )


def _map_rename_column(step: DataFlowStep, schema: str) -> MappedStep:
    """RENAME_COLUMN / SELECT → Spark .withColumnRenamed()."""
    parts = []
    for col in step.columns:
        if col.alias and col.alias != col.name:
            parts.append(f'df = df.withColumnRenamed("{col.name}", "{col.alias}")')

    pyspark = "\n".join(parts) + "\n" if parts else "# No renames\n"
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.SELECT_COLUMN,
        fabric_activity_json={"name": f"Select_{step.name}", "type": "Select"},
        pyspark_code=pyspark,
    )


def _map_data_type_conversion(step: DataFlowStep, schema: str) -> MappedStep:
    """DATA_TYPE_CONVERSION → Spark .cast()."""
    parts = []
    for col in step.columns:
        dtype = col.data_type or "string"
        parts.append(f'df = df.withColumn("{col.name}", F.col("{col.name}").cast("{dtype}"))')

    pyspark = "from pyspark.sql import functions as F\n" + "\n".join(parts) + "\n"
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.DERIVED_COLUMN,
        fabric_activity_json={"name": f"Cast_{step.name}", "type": "DerivedColumn"},
        pyspark_code=pyspark,
    )


def _map_target_db(step: DataFlowStep, schema: str) -> MappedStep:
    """TARGET_DB → Copy Activity sink / Spark saveAsTable."""
    table = step.target_table or step.source_table or step.name
    activity = {
        "name": f"Write_{table}",
        "type": "Copy",
        "typeProperties": {
            "sink": {
                "type": "LakehouseTableSink",
                "tableActionOption": "Overwrite",
            },
        },
    }
    pyspark = f'df.write.mode("overwrite").format("delta").saveAsTable("{table}")\n'
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.COPY_ACTIVITY,
        fabric_activity_json=activity, pyspark_code=pyspark,
    )


def _map_target_file(step: DataFlowStep, schema: str) -> MappedStep:
    """TARGET_FILE → write to OneLake."""
    path = step.target_table or step.name
    pyspark = f'df.write.mode("overwrite").parquet("Files/{path}")\n'
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.COPY_ACTIVITY,
        fabric_activity_json={"name": f"WriteFile_{step.name}", "type": "Copy"},
        pyspark_code=pyspark,
    )


def _map_branch(step: DataFlowStep, schema: str) -> MappedStep:
    """BRANCH / CONDITIONAL → If Condition Activity."""
    activity = {
        "name": f"Branch_{step.name}",
        "type": "IfCondition",
        "typeProperties": {
            "expression": {"value": step.filter_expression or "@true"},
            "ifTrueActivities": [],
            "ifFalseActivities": [],
        },
    }
    pyspark = f'# Branch: {step.name}\nif condition:\n    pass  # true path\nelse:\n    pass  # false path\n'
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.IF_CONDITION,
        fabric_activity_json=activity, pyspark_code=pyspark,
        requires_review=True, review_reason="Branch logic needs manual routing of downstream activities",
    )


def _map_loop(step: DataFlowStep, schema: str) -> MappedStep:
    """LOOP / FOREACH → ForEach Activity."""
    activity = {
        "name": f"ForEach_{step.name}",
        "type": "ForEach",
        "typeProperties": {
            "isSequential": False,
            "items": {"value": "@pipeline().parameters.items"},
            "activities": [],
        },
    }
    pyspark = f"for item in items:\n    pass  # loop body from {step.name}\n"
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.FOREACH_ACTIVITY,
        fabric_activity_json=activity, pyspark_code=pyspark,
        requires_review=True, review_reason="Loop body needs to be populated with inner activities",
    )


def _map_stored_procedure(step: DataFlowStep, schema: str) -> MappedStep:
    """STORED_PROCEDURE → Notebook Activity (PySpark translation needed)."""
    proc = step.procedure_name or step.name
    activity = {
        "name": f"Notebook_{proc}",
        "type": "SparkNotebook",
        "typeProperties": {
            "notebook": {"referenceName": f"nb_{_safe_var(proc)}"},
            "parameters": step.parameters,
        },
    }
    pyspark = (
        f"# TODO: Translate PL/SQL procedure '{proc}' to PySpark\n"
        f"# Original body:\n"
    )
    if step.procedure_body:
        for line in step.procedure_body.split("\n"):
            pyspark += f"# {line}\n"
    else:
        pyspark += f"# (body not available — retrieve from Oracle and translate)\n"

    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.NOTEBOOK,
        fabric_activity_json=activity, pyspark_code=pyspark,
        requires_review=True,
        review_reason=f"PL/SQL procedure '{proc}' requires translation to PySpark",
    )


def _map_custom(step: DataFlowStep, schema: str) -> MappedStep:
    """Fallback for unknown step types."""
    return MappedStep(
        original_step=step, fabric_type=FabricTargetType.UNKNOWN,
        notes=f"Unknown step type: {step.step_type.value}",
        requires_review=True,
        review_reason=f"Unmapped OAC step type '{step.step_type.value}' — manual conversion required",
    )


# Dispatcher
_STEP_MAPPERS: dict[StepType, Any] = {
    StepType.SOURCE_DB: _map_source_db,
    StepType.SOURCE_FILE: _map_source_file,
    StepType.FILTER: _map_filter,
    StepType.JOIN: _map_join,
    StepType.AGGREGATE: _map_aggregate,
    StepType.LOOKUP: _map_lookup,
    StepType.UNION: _map_union,
    StepType.SORT: _map_sort,
    StepType.ADD_COLUMN: _map_add_column,
    StepType.RENAME_COLUMN: _map_rename_column,
    StepType.DATA_TYPE_CONVERSION: _map_data_type_conversion,
    StepType.TARGET_DB: _map_target_db,
    StepType.TARGET_FILE: _map_target_file,
    StepType.BRANCH: _map_branch,
    StepType.LOOP: _map_loop,
    StepType.STORED_PROCEDURE: _map_stored_procedure,
    StepType.CUSTOM: _map_custom,
}


# ---------------------------------------------------------------------------
# Flow-level mapping
# ---------------------------------------------------------------------------


def map_dataflow(flow: DataFlow, oracle_schema: str = "OACS") -> MappedDataFlow:
    """Map an entire OAC DataFlow to Fabric artefacts.

    Returns a ``MappedDataFlow`` containing:
    - per-step mapping with activity JSON and PySpark code
    - a combined pipeline JSON
    - a combined notebook script
    """
    mapped_steps: list[MappedStep] = []
    warnings: list[str] = []

    for step in flow.topological_order():
        ms = map_step(step, oracle_schema)
        mapped_steps.append(ms)
        if ms.requires_review:
            warnings.append(f"Step '{step.name}' ({step.step_type.value}): {ms.review_reason}")

    # Assemble pipeline JSON
    activities = [ms.fabric_activity_json for ms in mapped_steps if ms.fabric_activity_json]
    pipeline_json = {
        "name": f"Pipeline_{_safe_var(flow.name)}",
        "properties": {
            "description": f"Migrated from OAC data flow: {flow.name}",
            "activities": activities,
            "parameters": {k: {"type": "String", "defaultValue": v} for k, v in flow.parameters.items()},
            "annotations": ["auto-generated", "etl-migration", "agent-03"],
        },
    }

    # Assemble notebook code
    nb_lines = [
        f"# Notebook: {flow.name}",
        f"# Migrated from OAC Data Flow '{flow.id}'",
        f"# Auto-generated by Agent 03 — ETL Migration Agent",
        "",
        "from pyspark.sql import functions as F",
        "",
    ]
    for ms in mapped_steps:
        if ms.pyspark_code:
            nb_lines.append(f"# --- Step: {ms.original_step.name} ({ms.original_step.step_type.value}) ---")
            nb_lines.append(ms.pyspark_code)

    mf = MappedDataFlow(
        flow_id=flow.id,
        flow_name=flow.name,
        mapped_steps=mapped_steps,
        pipeline_json=pipeline_json,
        notebook_code="\n".join(nb_lines),
        warnings=warnings,
    )
    logger.info(
        "Mapped data flow '%s': %d steps, %d warnings",
        flow.name, len(mapped_steps), len(warnings),
    )
    return mf


def map_multiple_dataflows(
    flows: list[DataFlow], oracle_schema: str = "OACS"
) -> list[MappedDataFlow]:
    """Map a list of data flows."""
    return [map_dataflow(f, oracle_schema) for f in flows]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_var(name: str) -> str:
    """Sanitise a name for use as a Python variable / activity name."""
    import re
    return re.sub(r"[^\w]", "_", name.strip()).lower()
