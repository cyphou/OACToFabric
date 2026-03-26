"""Tests for fabric_pipeline_generator and incremental_merger modules."""

from __future__ import annotations

import json

import pytest

from src.agents.etl.fabric_pipeline_generator import (
    FabricPipeline,
    PipelineActivity,
    build_3_stage_pipeline,
    generate_notebook_cell,
    get_spark_read_template,
    list_supported_connectors,
)
from src.agents.etl.incremental_merger import (
    MergeResult,
    USER_EDITABLE_KEYS,
    USER_OWNED_FILES,
    merge_artifacts,
)


# ---------------------------------------------------------------------------
# Pipeline generator
# ---------------------------------------------------------------------------

class TestPipelineActivity:
    def test_to_dict_basic(self):
        act = PipelineActivity(name="Test", activity_type="RefreshDataflow")
        d = act.to_dict()
        assert d["name"] == "Test"
        assert d["type"] == "RefreshDataflow"
        assert d["policy"]["retry"] == 2

    def test_depends_on(self):
        act = PipelineActivity(
            name="Stage2", activity_type="TridentNotebook",
            depends_on=["Stage1A", "Stage1B"],
        )
        d = act.to_dict()
        assert len(d["dependsOn"]) == 2
        assert d["dependsOn"][0]["activity"] == "Stage1A"


class TestBuild3StagePipeline:
    def test_full_pipeline(self):
        pipeline = build_3_stage_pipeline(
            pipeline_name="MigrationPipeline",
            dataflow_ids=[
                {"name": "Customers", "id": "df-001"},
                {"name": "Orders", "id": "df-002"},
            ],
            notebook_id="nb-001",
            notebook_name="ETL_Notebook",
            semantic_model_id="sm-001",
            workspace_id="ws-001",
        )
        assert pipeline.name == "MigrationPipeline"
        # 2 dataflows + 1 notebook + 1 refresh = 4 activities
        assert len(pipeline.activities) == 4

        # Stage 1: two parallel dataflow refreshes (no dependencies)
        assert pipeline.activities[0].depends_on == []
        assert pipeline.activities[1].depends_on == []

        # Stage 2: notebook depends on both dataflows
        assert set(pipeline.activities[2].depends_on) == {"Refresh_Customers", "Refresh_Orders"}

        # Stage 3: refresh depends on notebook
        assert pipeline.activities[3].depends_on == ["Run_ETL_Notebook"]

    def test_pipeline_without_notebook(self):
        pipeline = build_3_stage_pipeline(
            pipeline_name="Simple",
            dataflow_ids=[{"name": "DF1", "id": "df-1"}],
            semantic_model_id="sm-1",
        )
        # 1 dataflow + 0 notebook + 1 refresh = 2 activities
        assert len(pipeline.activities) == 2
        # Refresh depends on dataflow directly
        assert pipeline.activities[1].depends_on == ["Refresh_DF1"]

    def test_to_json(self):
        pipeline = build_3_stage_pipeline(
            pipeline_name="JSONTest",
            dataflow_ids=[{"name": "D1", "id": "1"}],
        )
        parsed = json.loads(pipeline.to_json())
        assert parsed["name"] == "JSONTest"
        assert "activities" in parsed["properties"]


class TestSparkConnectors:
    def test_supported_connectors(self):
        connectors = list_supported_connectors()
        assert "oracle" in connectors
        assert "postgresql" in connectors
        assert "snowflake" in connectors
        assert len(connectors) == 9

    def test_get_template(self):
        template = get_spark_read_template("oracle")
        assert template is not None
        assert "jdbc:oracle:thin" in template

    def test_unknown_returns_none(self):
        assert get_spark_read_template("unknown") is None

    def test_generate_cell(self):
        cell = generate_notebook_cell("csv", {"file_path": "/data/file.csv", "table_var": "data"})
        assert "csv" in cell
        assert "/data/file.csv" in cell

    def test_unsupported_cell(self):
        cell = generate_notebook_cell("unknown_db", {})
        assert "Unsupported" in cell


# ---------------------------------------------------------------------------
# Incremental merger
# ---------------------------------------------------------------------------

class TestMergeArtifacts:
    def test_added_files(self):
        existing = {}
        incoming = {"new_file.json": '{"a": 1}'}
        merged, result = merge_artifacts(existing, incoming)
        assert "new_file.json" in merged
        assert result.added == 1

    def test_unchanged_files(self):
        content = '{"key": "value"}'
        existing = {"file.json": content}
        incoming = {"file.json": content}
        merged, result = merge_artifacts(existing, incoming)
        assert result.unchanged == 1
        assert merged["file.json"] == content

    def test_user_owned_kept(self):
        existing = {"custom_measures": "my stuff"}
        incoming = {}
        merged, result = merge_artifacts(existing, incoming)
        assert "custom_measures" in merged
        assert result.kept == 1

    def test_non_user_owned_deleted(self):
        existing = {"generated.json": "old"}
        incoming = {}
        merged, result = merge_artifacts(existing, incoming)
        assert "generated.json" not in merged
        assert result.deleted == 1

    def test_json_preserves_user_editable_keys(self):
        existing = json.dumps({"displayName": "My Custom Name", "data": "old"})
        incoming = json.dumps({"displayName": "Auto Name", "data": "new"})
        existing_files = {"report.json": existing}
        incoming_files = {"report.json": incoming}
        merged, result = merge_artifacts(existing_files, incoming_files)
        parsed = json.loads(merged["report.json"])
        assert parsed["displayName"] == "My Custom Name"  # preserved
        assert parsed["data"] == "new"  # updated

    def test_non_json_modified(self):
        existing = {"file.tmdl": "old content"}
        incoming = {"file.tmdl": "new content"}
        merged, result = merge_artifacts(existing, incoming)
        assert merged["file.tmdl"] == "new content"
        assert result.modified == 1

    def test_total_count(self):
        existing = {"a.json": "1", "b.json": "2", "custom_measures": "x"}
        incoming = {"a.json": "1", "c.json": "3"}
        merged, result = merge_artifacts(existing, incoming)
        assert result.total == 4  # unchanged + deleted + kept + added
