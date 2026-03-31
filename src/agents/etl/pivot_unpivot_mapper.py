"""Pivot/Unpivot Mapper — OAC pivot/unpivot steps → Fabric equivalents.

Converts OAC Data Flow pivot and unpivot transformations to:
  - Power Query M ``Table.Pivot`` / ``Table.Unpivot`` expressions
  - PySpark ``pivot()`` / ``stack()`` / ``melt()`` operations
  - Fabric Data Factory Flowlet transformations

Also handles parallel branch mapping for OAC data flows that use
concurrent execution paths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------


@dataclass
class PivotSpec:
    """Specification for a pivot transformation."""

    group_by_columns: list[str]
    pivot_column: str
    value_column: str
    aggregation: str = "sum"       # sum, count, avg, min, max, first, last
    pivot_values: list[str] = field(default_factory=list)  # explicit pivot values


@dataclass
class UnpivotSpec:
    """Specification for an unpivot transformation."""

    id_columns: list[str]           # columns to keep
    unpivot_columns: list[str]      # columns to unpivot
    attribute_column: str = "Attribute"
    value_column: str = "Value"
    only_non_null: bool = True


@dataclass
class ParallelBranchSpec:
    """Specification for parallel execution branches."""

    branch_name: str
    step_names: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


@dataclass
class TransformationOutput:
    """Generated transformation code."""

    m_query: str = ""
    pyspark_code: str = ""
    pipeline_json: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Aggregation mapping
# ---------------------------------------------------------------------------

_AGG_TO_M: dict[str, str] = {
    "sum": "List.Sum",
    "count": "List.Count",
    "avg": "List.Average",
    "min": "List.Min",
    "max": "List.Max",
    "first": "List.First",
    "last": "List.Last",
}

_AGG_TO_PYSPARK: dict[str, str] = {
    "sum": "sum",
    "count": "count",
    "avg": "avg",
    "min": "min",
    "max": "max",
    "first": "first",
    "last": "last",
}


# ---------------------------------------------------------------------------
# Pivot generation
# ---------------------------------------------------------------------------


def generate_pivot(spec: PivotSpec) -> TransformationOutput:
    """Generate pivot transformation in M and PySpark.

    Parameters
    ----------
    spec : PivotSpec
        Pivot transformation specification.

    Returns
    -------
    TransformationOutput
        Generated M query and PySpark code.
    """
    warnings: list[str] = []

    # --- Power Query M ---
    m_agg = _AGG_TO_M.get(spec.aggregation.lower(), "List.Sum")
    m_lines = [
        f'// Pivot: {spec.pivot_column} by {spec.value_column}',
        f'PivotStep = Table.Pivot(',
        f'    Source,',
        f'    List.Distinct(Source[{spec.pivot_column}]),',
        f'    "{spec.pivot_column}",',
        f'    "{spec.value_column}",',
        f'    {m_agg}',
        f')',
    ]
    m_query = "\n".join(m_lines)

    # --- PySpark ---
    py_agg = _AGG_TO_PYSPARK.get(spec.aggregation.lower(), "sum")
    group_cols = ", ".join(f'"{c}"' for c in spec.group_by_columns)
    py_lines = [
        f"# Pivot: {spec.pivot_column} by {spec.value_column}",
        f"df_pivoted = (",
        f"    df.groupBy({group_cols})",
        f'    .pivot("{spec.pivot_column}"',
    ]
    if spec.pivot_values:
        vals = ", ".join(f'"{v}"' for v in spec.pivot_values)
        py_lines.append(f"        , [{vals}])")
    else:
        py_lines.append(f"    )")

    py_lines.extend([
        f'    .agg(F.{py_agg}("{spec.value_column}"))',
        f")",
    ])
    pyspark_code = "\n".join(py_lines)

    # --- Pipeline JSON (Flowlet pivot) ---
    pipeline_json = {
        "type": "Pivot",
        "name": f"Pivot_{spec.pivot_column}",
        "properties": {
            "groupBy": spec.group_by_columns,
            "pivotColumn": spec.pivot_column,
            "valueColumn": spec.value_column,
            "aggregation": spec.aggregation,
            "pivotValues": spec.pivot_values,
        },
    }

    logger.info("Generated pivot for column '%s'", spec.pivot_column)
    return TransformationOutput(
        m_query=m_query,
        pyspark_code=pyspark_code,
        pipeline_json=pipeline_json,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Unpivot generation
# ---------------------------------------------------------------------------


def generate_unpivot(spec: UnpivotSpec) -> TransformationOutput:
    """Generate unpivot transformation in M and PySpark.

    Parameters
    ----------
    spec : UnpivotSpec
        Unpivot transformation specification.

    Returns
    -------
    TransformationOutput
        Generated M query and PySpark code.
    """
    warnings: list[str] = []

    # --- Power Query M ---
    cols = ", ".join(f'"{c}"' for c in spec.unpivot_columns)
    m_func = "Table.Unpivot" if not spec.only_non_null else "Table.UnpivotOtherColumns"

    if spec.only_non_null:
        id_cols = ", ".join(f'"{c}"' for c in spec.id_columns)
        m_lines = [
            f'// Unpivot: {len(spec.unpivot_columns)} columns',
            f'UnpivotStep = Table.UnpivotOtherColumns(',
            f'    Source,',
            f'    {{{id_cols}}},',
            f'    "{spec.attribute_column}",',
            f'    "{spec.value_column}"',
            f')',
        ]
    else:
        m_lines = [
            f'// Unpivot: {len(spec.unpivot_columns)} columns',
            f'UnpivotStep = Table.Unpivot(',
            f'    Source,',
            f'    {{{cols}}},',
            f'    "{spec.attribute_column}",',
            f'    "{spec.value_column}"',
            f')',
        ]
    m_query = "\n".join(m_lines)

    # --- PySpark ---
    n = len(spec.unpivot_columns)
    value_pairs = ", ".join(
        f"'{c}', `{c}`" for c in spec.unpivot_columns
    )
    id_cols = ", ".join(f'"{c}"' for c in spec.id_columns)
    py_lines = [
        f"# Unpivot: {n} columns → '{spec.attribute_column}' / '{spec.value_column}'",
        f"df_unpivoted = df.select(",
        f"    {id_cols},",
        f'    F.expr("stack({n}, {value_pairs}) as ({spec.attribute_column}, {spec.value_column})")',
        f")",
    ]
    if spec.only_non_null:
        py_lines.append(f'df_unpivoted = df_unpivoted.filter(F.col("{spec.value_column}").isNotNull())')
    pyspark_code = "\n".join(py_lines)

    # --- Pipeline JSON ---
    pipeline_json = {
        "type": "Unpivot",
        "name": f"Unpivot_{spec.attribute_column}",
        "properties": {
            "idColumns": spec.id_columns,
            "unpivotColumns": spec.unpivot_columns,
            "attributeColumn": spec.attribute_column,
            "valueColumn": spec.value_column,
            "onlyNonNull": spec.only_non_null,
        },
    }

    logger.info("Generated unpivot: %d columns", n)
    return TransformationOutput(
        m_query=m_query,
        pyspark_code=pyspark_code,
        pipeline_json=pipeline_json,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Parallel branch generation
# ---------------------------------------------------------------------------


def generate_parallel_branches(
    branches: list[ParallelBranchSpec],
) -> dict[str, Any]:
    """Generate Fabric pipeline parallel execution branch configuration.

    Parameters
    ----------
    branches : list[ParallelBranchSpec]
        Parallel branch specifications.

    Returns
    -------
    dict[str, Any]
        Pipeline JSON with parallel ForEach / branch activities.
    """
    activities: list[dict[str, Any]] = []

    for branch in branches:
        deps = [
            {"activity": d, "dependencyConditions": ["Succeeded"]}
            for d in branch.depends_on
        ]
        activity = {
            "name": branch.branch_name,
            "type": "ExecutePipeline",
            "dependsOn": deps,
            "typeProperties": {
                "pipeline": {"referenceName": branch.branch_name},
                "waitOnCompletion": True,
            },
            "policy": {
                "timeout": "0.12:00:00",
                "retry": 2,
                "retryIntervalInSeconds": 30,
            },
        }
        activities.append(activity)

    logger.info("Generated %d parallel branches", len(branches))
    return {
        "type": "Pipeline",
        "properties": {
            "activities": activities,
            "concurrency": len(branches),
        },
    }
