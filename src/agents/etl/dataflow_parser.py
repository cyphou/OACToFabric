"""OAC Data Flow parser — extract structured step graph from data flow definitions.

Parses OAC Data Flow JSON/XML definitions into a normalised list
of ``DataFlowStep`` objects representing the ETL DAG.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step types supported by OAC Data Flows
# ---------------------------------------------------------------------------


class StepType(str, Enum):
    """Canonical OAC data flow step types."""

    SOURCE_DB = "source_database"
    SOURCE_FILE = "source_file"
    FILTER = "filter"
    JOIN = "join"
    AGGREGATE = "aggregate"
    LOOKUP = "lookup"
    UNION = "union"
    SORT = "sort"
    ADD_COLUMN = "add_column"
    RENAME_COLUMN = "rename_column"
    DATA_TYPE_CONVERSION = "data_type_conversion"
    TARGET_DB = "target_database"
    TARGET_FILE = "target_file"
    BRANCH = "branch"
    LOOP = "loop"
    STORED_PROCEDURE = "stored_procedure"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DataFlowColumn:
    """A column reference within a data flow step."""

    name: str
    data_type: str = ""
    expression: str = ""
    alias: str = ""


@dataclass
class DataFlowStep:
    """A single step in an OAC data flow DAG."""

    id: str
    name: str
    step_type: StepType
    order: int = 0
    source_table: str = ""
    target_table: str = ""
    connection_name: str = ""
    columns: list[DataFlowColumn] = field(default_factory=list)
    filter_expression: str = ""
    join_type: str = ""  # INNER, LEFT, RIGHT, FULL, CROSS
    join_condition: str = ""
    group_by_columns: list[str] = field(default_factory=list)
    aggregate_expressions: list[dict[str, str]] = field(default_factory=list)
    sort_columns: list[dict[str, str]] = field(default_factory=list)  # {"column": ..., "order": "ASC"|"DESC"}
    procedure_name: str = ""
    procedure_body: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    upstream_step_ids: list[str] = field(default_factory=list)
    downstream_step_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataFlow:
    """A complete OAC data flow containing an ordered list of steps."""

    id: str
    name: str
    description: str = ""
    steps: list[DataFlowStep] = field(default_factory=list)
    schedule: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def source_steps(self) -> list[DataFlowStep]:
        return [s for s in self.steps if s.step_type in (StepType.SOURCE_DB, StepType.SOURCE_FILE)]

    @property
    def target_steps(self) -> list[DataFlowStep]:
        return [s for s in self.steps if s.step_type in (StepType.TARGET_DB, StepType.TARGET_FILE)]

    @property
    def transform_steps(self) -> list[DataFlowStep]:
        src_tgt = {StepType.SOURCE_DB, StepType.SOURCE_FILE, StepType.TARGET_DB, StepType.TARGET_FILE}
        return [s for s in self.steps if s.step_type not in src_tgt]

    def topological_order(self) -> list[DataFlowStep]:
        """Return steps in execution order (topological sort by upstream deps)."""
        visited: set[str] = set()
        ordered: list[DataFlowStep] = []
        step_map = {s.id: s for s in self.steps}

        def _visit(step_id: str) -> None:
            if step_id in visited:
                return
            visited.add(step_id)
            step = step_map.get(step_id)
            if step is None:
                return
            for up in step.upstream_step_ids:
                _visit(up)
            ordered.append(step)

        for s in self.steps:
            _visit(s.id)

        return ordered


# ---------------------------------------------------------------------------
# OAC type normalisation
# ---------------------------------------------------------------------------

_OAC_TYPE_MAP: dict[str, StepType] = {
    "DATABASE_SOURCE": StepType.SOURCE_DB,
    "FILE_SOURCE": StepType.SOURCE_FILE,
    "SOURCE": StepType.SOURCE_DB,
    "FILTER": StepType.FILTER,
    "JOIN": StepType.JOIN,
    "AGGREGATE": StepType.AGGREGATE,
    "LOOKUP": StepType.LOOKUP,
    "UNION": StepType.UNION,
    "SORT": StepType.SORT,
    "ADD_COLUMN": StepType.ADD_COLUMN,
    "DERIVED_COLUMN": StepType.ADD_COLUMN,
    "RENAME_COLUMN": StepType.RENAME_COLUMN,
    "SELECT": StepType.RENAME_COLUMN,
    "DATA_TYPE_CONVERSION": StepType.DATA_TYPE_CONVERSION,
    "CAST": StepType.DATA_TYPE_CONVERSION,
    "DATABASE_TARGET": StepType.TARGET_DB,
    "TARGET": StepType.TARGET_DB,
    "FILE_TARGET": StepType.TARGET_FILE,
    "BRANCH": StepType.BRANCH,
    "CONDITIONAL": StepType.BRANCH,
    "LOOP": StepType.LOOP,
    "FOREACH": StepType.LOOP,
    "STORED_PROCEDURE": StepType.STORED_PROCEDURE,
    "PROCEDURE_CALL": StepType.STORED_PROCEDURE,
}


def _normalise_step_type(raw: str) -> StepType:
    """Map an OAC step type string to our canonical StepType."""
    normalised = raw.strip().upper().replace(" ", "_")
    return _OAC_TYPE_MAP.get(normalised, StepType.CUSTOM)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_dataflow_json(definition: dict[str, Any]) -> DataFlow:
    """Parse an OAC Data Flow JSON definition into a ``DataFlow`` object.

    Expected JSON structure (as returned by OAC API)::

        {
            "id": "...",
            "name": "...",
            "description": "...",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Read Customers",
                    "type": "DATABASE_SOURCE",
                    "table": "CUSTOMERS",
                    "connection": "OracleDB",
                    "columns": [...],
                    "upstreamSteps": [],
                    "downstreamSteps": ["step_2"]
                },
                ...
            ],
            "schedule": { ... },
            "parameters": { ... }
        }
    """
    flow_id = definition.get("id", "unknown")
    flow_name = definition.get("name", "Unnamed Data Flow")

    steps: list[DataFlowStep] = []
    for idx, raw_step in enumerate(definition.get("steps", [])):
        step = _parse_step(raw_step, idx)
        steps.append(step)

    flow = DataFlow(
        id=flow_id,
        name=flow_name,
        description=definition.get("description", ""),
        steps=steps,
        schedule=definition.get("schedule", {}),
        parameters=definition.get("parameters", {}),
        metadata=definition.get("metadata", {}),
    )
    logger.info("Parsed data flow '%s' with %d steps", flow_name, len(steps))
    return flow


def _parse_step(raw: dict[str, Any], order: int) -> DataFlowStep:
    """Parse a single step dict into a DataFlowStep."""
    step_type = _normalise_step_type(raw.get("type", "CUSTOM"))

    columns = [
        DataFlowColumn(
            name=c.get("name", ""),
            data_type=c.get("dataType", c.get("data_type", "")),
            expression=c.get("expression", ""),
            alias=c.get("alias", ""),
        )
        for c in raw.get("columns", [])
    ]

    sort_cols = []
    for sc in raw.get("sortColumns", raw.get("sort_columns", [])):
        if isinstance(sc, str):
            sort_cols.append({"column": sc, "order": "ASC"})
        else:
            sort_cols.append({"column": sc.get("column", ""), "order": sc.get("order", "ASC")})

    agg_exprs = []
    for ae in raw.get("aggregateExpressions", raw.get("aggregate_expressions", [])):
        if isinstance(ae, str):
            agg_exprs.append({"expression": ae, "alias": ""})
        else:
            agg_exprs.append({"expression": ae.get("expression", ""), "alias": ae.get("alias", "")})

    return DataFlowStep(
        id=raw.get("id", f"step_{order}"),
        name=raw.get("name", f"Step {order}"),
        step_type=step_type,
        order=order,
        source_table=raw.get("table", raw.get("source_table", "")),
        target_table=raw.get("targetTable", raw.get("target_table", "")),
        connection_name=raw.get("connection", raw.get("connection_name", "")),
        columns=columns,
        filter_expression=raw.get("filterExpression", raw.get("filter_expression", "")),
        join_type=raw.get("joinType", raw.get("join_type", "")),
        join_condition=raw.get("joinCondition", raw.get("join_condition", "")),
        group_by_columns=raw.get("groupByColumns", raw.get("group_by_columns", [])),
        aggregate_expressions=agg_exprs,
        sort_columns=sort_cols,
        procedure_name=raw.get("procedureName", raw.get("procedure_name", "")),
        procedure_body=raw.get("procedureBody", raw.get("procedure_body", "")),
        parameters=raw.get("parameters", {}),
        upstream_step_ids=raw.get("upstreamSteps", raw.get("upstream_step_ids", [])),
        downstream_step_ids=raw.get("downstreamSteps", raw.get("downstream_step_ids", [])),
        metadata=raw.get("metadata", {}),
    )


def parse_multiple_dataflows(definitions: list[dict[str, Any]]) -> list[DataFlow]:
    """Parse a list of OAC Data Flow definitions."""
    return [parse_dataflow_json(d) for d in definitions]
