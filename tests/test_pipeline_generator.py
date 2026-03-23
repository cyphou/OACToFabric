"""Tests for Fabric Data Factory pipeline generator."""

from __future__ import annotations

import json

import pytest

from src.agents.schema.pipeline_generator import (
    generate_all_pipelines,
    generate_full_load_pipeline,
    generate_incremental_pipeline,
    serialize_pipeline,
)


class TestFullLoadPipeline:
    def test_basic_pipeline(self):
        p = generate_full_load_pipeline(
            table_name="CUSTOMERS",
            oracle_schema="SALES",
            oracle_connection_name="OracleDB",
            lakehouse_name="migrate_lh",
        )
        assert p["name"] == "FullLoad_CUSTOMERS"
        assert len(p["properties"]["activities"]) == 1
        activity = p["properties"]["activities"][0]
        assert activity["type"] == "Copy"
        assert "SALES.CUSTOMERS" in activity["typeProperties"]["source"]["oracleReaderQuery"]

    def test_with_partition(self):
        p = generate_full_load_pipeline(
            table_name="ORDERS",
            oracle_schema="SALES",
            oracle_connection_name="OracleDB",
            lakehouse_name="lh",
            partition_column="ORDER_ID",
            partition_count=8,
        )
        source = p["properties"]["activities"][0]["typeProperties"]["source"]
        assert source["partitionOption"] == "DynamicRange"
        assert source["partitionSettings"]["partitionCount"] == 8

    def test_annotations_present(self):
        p = generate_full_load_pipeline("T", "S", "C", "L")
        assert "full-load" in p["properties"]["annotations"]
        assert "agent-02" in p["properties"]["annotations"]


class TestIncrementalPipeline:
    def test_basic_pipeline(self):
        p = generate_incremental_pipeline(
            table_name="ORDERS",
            oracle_schema="SALES",
            oracle_connection_name="OracleDB",
            lakehouse_name="lh",
            watermark_column="LAST_UPDATED",
        )
        assert p["name"] == "IncrLoad_ORDERS"
        assert len(p["properties"]["activities"]) == 4
        activity_names = [a["name"] for a in p["properties"]["activities"]]
        assert "GetLastWatermark" in activity_names
        assert "GetCurrentWatermark" in activity_names
        assert "CopyDelta_ORDERS" in activity_names
        assert "UpdateWatermark" in activity_names

    def test_watermark_column_in_query(self):
        p = generate_incremental_pipeline("T", "S", "C", "L", watermark_column="MODIFIED_AT")
        copy = next(a for a in p["properties"]["activities"] if a["name"].startswith("CopyDelta"))
        assert "MODIFIED_AT" in copy["typeProperties"]["source"]["oracleReaderQuery"]


class TestBatchGeneration:
    def test_full_mode(self):
        tables = [
            {"name": "T1"},
            {"name": "T2"},
        ]
        pipelines = generate_all_pipelines(tables, "SCH", "CONN", "LH", mode="full")
        assert len(pipelines) == 2
        assert all(p["name"].startswith("FullLoad") for p in pipelines)

    def test_incremental_mode(self):
        tables = [{"name": "T1"}]
        pipelines = generate_all_pipelines(tables, "SCH", "CONN", "LH", mode="incremental")
        assert len(pipelines) == 1
        assert pipelines[0]["name"].startswith("IncrLoad")

    def test_both_mode(self):
        tables = [{"name": "T1", "watermark_column": "UPD_DATE"}]
        pipelines = generate_all_pipelines(tables, "SCH", "CONN", "LH", mode="both")
        # Should get both full load and incremental
        assert len(pipelines) == 2
        names = [p["name"] for p in pipelines]
        assert any("FullLoad" in n for n in names)
        assert any("IncrLoad" in n for n in names)

    def test_auto_partition_large_table(self):
        tables = [{"name": "BIG_TABLE", "row_count": 500_000_000, "partition_column": "ID"}]
        pipelines = generate_all_pipelines(tables, "SCH", "CONN", "LH", mode="full")
        source = pipelines[0]["properties"]["activities"][0]["typeProperties"]["source"]
        assert source["partitionSettings"]["partitionCount"] == 16


class TestSerialize:
    def test_serialize_pretty(self):
        p = generate_full_load_pipeline("T", "S", "C", "L")
        s = serialize_pipeline(p, pretty=True)
        parsed = json.loads(s)
        assert parsed["name"] == "FullLoad_T"

    def test_serialize_compact(self):
        p = generate_full_load_pipeline("T", "S", "C", "L")
        s = serialize_pipeline(p, pretty=False)
        assert "\n" not in s
