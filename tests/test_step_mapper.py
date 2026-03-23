"""Tests for OAC step mapper — data flow steps to Fabric equivalents."""

from __future__ import annotations

import pytest

from src.agents.etl.dataflow_parser import DataFlowStep, DataFlow, StepType, parse_dataflow_json
from src.agents.etl.step_mapper import (
    FabricTargetType,
    MappedDataFlow,
    MappedStep,
    map_dataflow,
    map_step,
)


# ---------------------------------------------------------------------------
# Step-level mapping tests
# ---------------------------------------------------------------------------


class TestMapStep:
    def test_source_db(self):
        step = DataFlowStep(id="s1", name="Read_T", step_type=StepType.SOURCE_DB, source_table="ORDERS")
        ms = map_step(step, oracle_schema="SALES")
        assert ms.fabric_type == FabricTargetType.COPY_ACTIVITY
        assert "SALES.ORDERS" in ms.fabric_activity_json["typeProperties"]["source"]["oracleReaderQuery"]
        assert "df_orders" in ms.pyspark_code.lower()

    def test_source_file(self):
        step = DataFlowStep(id="s1", name="Read_CSV", step_type=StepType.SOURCE_FILE)
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.COPY_ACTIVITY
        assert "csv" in ms.pyspark_code.lower()

    def test_filter(self):
        step = DataFlowStep(id="s1", name="FilterActive", step_type=StepType.FILTER, filter_expression="status=1")
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.FILTER_ACTIVITY
        assert "filter" in ms.pyspark_code.lower()

    def test_join(self):
        step = DataFlowStep(
            id="s1", name="JoinCustOrder", step_type=StepType.JOIN,
            join_type="LEFT", join_condition="a.id = b.id",
            upstream_step_ids=["s_cust", "s_order"],
        )
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.JOIN
        assert "left" in ms.pyspark_code.lower()

    def test_aggregate(self):
        step = DataFlowStep(
            id="s1", name="SumSales", step_type=StepType.AGGREGATE,
            group_by_columns=["REGION"],
            aggregate_expressions=[{"expression": "sum(amount)", "alias": "total"}],
        )
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.AGGREGATE
        assert "groupBy" in ms.pyspark_code

    def test_lookup(self):
        step = DataFlowStep(id="s1", name="LookupCountry", step_type=StepType.LOOKUP, source_table="COUNTRIES")
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.LOOKUP_ACTIVITY
        assert "broadcast" in ms.pyspark_code

    def test_sort(self):
        step = DataFlowStep(
            id="s1", name="SortByDate", step_type=StepType.SORT,
            sort_columns=[{"column": "sale_date", "order": "DESC"}],
        )
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.SORT
        assert "desc" in ms.pyspark_code.lower()

    def test_add_column(self):
        from src.agents.etl.dataflow_parser import DataFlowColumn
        step = DataFlowStep(
            id="s1", name="AddDiscount", step_type=StepType.ADD_COLUMN,
            columns=[DataFlowColumn(name="discount", expression="price * 0.1", alias="discount")],
        )
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.DERIVED_COLUMN
        assert "withColumn" in ms.pyspark_code

    def test_target_db(self):
        step = DataFlowStep(id="s1", name="WriteOrders", step_type=StepType.TARGET_DB, target_table="orders_lh")
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.COPY_ACTIVITY
        assert "saveAsTable" in ms.pyspark_code

    def test_branch_requires_review(self):
        step = DataFlowStep(id="s1", name="CheckStatus", step_type=StepType.BRANCH)
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.IF_CONDITION
        assert ms.requires_review is True

    def test_stored_procedure_requires_review(self):
        step = DataFlowStep(id="s1", name="CalcTotals", step_type=StepType.STORED_PROCEDURE, procedure_name="PKG_CALC.TOTALS")
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.NOTEBOOK
        assert ms.requires_review is True
        assert "PKG_CALC.TOTALS" in ms.pyspark_code

    def test_custom_fallback(self):
        step = DataFlowStep(id="s1", name="Custom", step_type=StepType.CUSTOM)
        ms = map_step(step)
        assert ms.fabric_type == FabricTargetType.UNKNOWN
        assert ms.requires_review is True


# ---------------------------------------------------------------------------
# Flow-level mapping tests
# ---------------------------------------------------------------------------


SAMPLE_FLOW = {
    "id": "flow_001",
    "name": "Customer ETL",
    "steps": [
        {"id": "s1", "name": "ReadCustomers", "type": "DATABASE_SOURCE", "table": "CUSTOMERS",
         "upstreamSteps": [], "downstreamSteps": ["s2"]},
        {"id": "s2", "name": "FilterActive", "type": "FILTER",
         "filterExpression": "active=1", "upstreamSteps": ["s1"], "downstreamSteps": ["s3"]},
        {"id": "s3", "name": "WriteCustomers", "type": "DATABASE_TARGET",
         "targetTable": "customers", "upstreamSteps": ["s2"], "downstreamSteps": []},
    ],
}


class TestMapDataFlow:
    def test_maps_all_steps(self):
        flow = parse_dataflow_json(SAMPLE_FLOW)
        mapped = map_dataflow(flow, oracle_schema="SCH")
        assert len(mapped.mapped_steps) == 3

    def test_pipeline_json_generated(self):
        flow = parse_dataflow_json(SAMPLE_FLOW)
        mapped = map_dataflow(flow)
        assert mapped.pipeline_json["name"] == "Pipeline_customer_etl"
        assert len(mapped.pipeline_json["properties"]["activities"]) == 3

    def test_notebook_code_generated(self):
        flow = parse_dataflow_json(SAMPLE_FLOW)
        mapped = map_dataflow(flow)
        assert "Customer ETL" in mapped.notebook_code
        assert "pyspark" in mapped.notebook_code.lower() or "spark" in mapped.notebook_code.lower()

    def test_warnings_for_review_items(self):
        flow_def = {
            "id": "f2", "name": "Complex",
            "steps": [
                {"id": "s1", "name": "Branch", "type": "CONDITIONAL"},
            ],
        }
        flow = parse_dataflow_json(flow_def)
        mapped = map_dataflow(flow)
        assert len(mapped.warnings) >= 1
        assert len(mapped.review_required) >= 1
