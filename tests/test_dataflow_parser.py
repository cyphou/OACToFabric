"""Tests for OAC data flow parser."""

from __future__ import annotations

import pytest

from src.agents.etl.dataflow_parser import (
    DataFlow,
    DataFlowStep,
    StepType,
    parse_dataflow_json,
    parse_multiple_dataflows,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_FLOW_JSON = {
    "id": "flow_001",
    "name": "Customer Load",
    "description": "Load customers from Oracle to Lakehouse",
    "steps": [
        {
            "id": "s1",
            "name": "Read Customers",
            "type": "DATABASE_SOURCE",
            "table": "CUSTOMERS",
            "connection": "OracleDB",
            "columns": [
                {"name": "CUST_ID", "dataType": "NUMBER(10,0)"},
                {"name": "CUST_NAME", "dataType": "VARCHAR2(255)"},
            ],
            "upstreamSteps": [],
            "downstreamSteps": ["s2"],
        },
        {
            "id": "s2",
            "name": "Filter Active",
            "type": "FILTER",
            "filterExpression": "STATUS = 'ACTIVE'",
            "upstreamSteps": ["s1"],
            "downstreamSteps": ["s3"],
        },
        {
            "id": "s3",
            "name": "Write Customers",
            "type": "DATABASE_TARGET",
            "targetTable": "customers_lakehouse",
            "upstreamSteps": ["s2"],
            "downstreamSteps": [],
        },
    ],
    "schedule": {"repeat_interval": "FREQ=DAILY; BYHOUR=2"},
    "parameters": {"env": "prod"},
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseDataFlowJSON:
    def test_basic_parse(self):
        flow = parse_dataflow_json(SAMPLE_FLOW_JSON)
        assert flow.id == "flow_001"
        assert flow.name == "Customer Load"
        assert len(flow.steps) == 3

    def test_step_types(self):
        flow = parse_dataflow_json(SAMPLE_FLOW_JSON)
        assert flow.steps[0].step_type == StepType.SOURCE_DB
        assert flow.steps[1].step_type == StepType.FILTER
        assert flow.steps[2].step_type == StepType.TARGET_DB

    def test_columns_parsed(self):
        flow = parse_dataflow_json(SAMPLE_FLOW_JSON)
        cols = flow.steps[0].columns
        assert len(cols) == 2
        assert cols[0].name == "CUST_ID"
        assert cols[0].data_type == "NUMBER(10,0)"

    def test_upstream_downstream(self):
        flow = parse_dataflow_json(SAMPLE_FLOW_JSON)
        assert flow.steps[1].upstream_step_ids == ["s1"]
        assert flow.steps[1].downstream_step_ids == ["s3"]

    def test_filter_expression(self):
        flow = parse_dataflow_json(SAMPLE_FLOW_JSON)
        assert flow.steps[1].filter_expression == "STATUS = 'ACTIVE'"

    def test_schedule_and_params(self):
        flow = parse_dataflow_json(SAMPLE_FLOW_JSON)
        assert flow.schedule["repeat_interval"] == "FREQ=DAILY; BYHOUR=2"
        assert flow.parameters["env"] == "prod"

    def test_source_target_properties(self):
        flow = parse_dataflow_json(SAMPLE_FLOW_JSON)
        assert len(flow.source_steps) == 1
        assert len(flow.target_steps) == 1
        assert len(flow.transform_steps) == 1

    def test_topological_order(self):
        flow = parse_dataflow_json(SAMPLE_FLOW_JSON)
        ordered = flow.topological_order()
        ids = [s.id for s in ordered]
        assert ids.index("s1") < ids.index("s2") < ids.index("s3")


class TestStepTypeNormalisation:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("DATABASE_SOURCE", StepType.SOURCE_DB),
            ("SOURCE", StepType.SOURCE_DB),
            ("FILTER", StepType.FILTER),
            ("JOIN", StepType.JOIN),
            ("AGGREGATE", StepType.AGGREGATE),
            ("DERIVED_COLUMN", StepType.ADD_COLUMN),
            ("SELECT", StepType.RENAME_COLUMN),
            ("CAST", StepType.DATA_TYPE_CONVERSION),
            ("TARGET", StepType.TARGET_DB),
            ("PROCEDURE_CALL", StepType.STORED_PROCEDURE),
            ("FOREACH", StepType.LOOP),
            ("UNKNOWN_TYPE", StepType.CUSTOM),
        ],
    )
    def test_normalise(self, raw: str, expected: StepType):
        from src.agents.etl.dataflow_parser import _normalise_step_type
        assert _normalise_step_type(raw) == expected


class TestParseMultiple:
    def test_parses_list(self):
        flows = parse_multiple_dataflows([SAMPLE_FLOW_JSON, SAMPLE_FLOW_JSON])
        assert len(flows) == 2


class TestEmptyFlow:
    def test_empty_steps(self):
        flow = parse_dataflow_json({"id": "empty", "name": "Empty"})
        assert flow.id == "empty"
        assert len(flow.steps) == 0
        assert flow.topological_order() == []
