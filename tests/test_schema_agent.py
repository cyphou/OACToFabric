"""Tests for Schema Agent (Agent 02) — end-to-end with mocks."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.agents.schema.schema_agent import SchemaAgent
from src.agents.schema.type_mapper import TargetPlatform
from src.core.models import MigrationScope


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "schema_output"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSchemaAgentLifecycle:
    @pytest.mark.asyncio
    async def test_discover_from_scope(self, output_dir: Path):
        """Discovery using scope paths (no Lakehouse)."""
        scope = MigrationScope(include_paths=["/physical/CUSTOMERS", "/physical/ORDERS"])
        agent = SchemaAgent(output_dir=output_dir)

        inventory = await agent.discover(scope)
        assert inventory.count == 2
        names = {i.name for i in inventory.items}
        assert "CUSTOMERS" in names
        assert "ORDERS" in names

    @pytest.mark.asyncio
    async def test_plan_generates_mapping(self, output_dir: Path):
        """Plan generates type mappings and DDL."""
        scope = MigrationScope(include_paths=["/physical/CUSTOMERS"])
        agent = SchemaAgent(output_dir=output_dir)

        # Add column metadata so mapping has something to work with
        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {
            "columns": [
                {"name": "ID", "data_type": "NUMBER(10,0)"},
                {"name": "NAME", "data_type": "VARCHAR2(255)"},
                {"name": "CREATED", "data_type": "DATE"},
            ]
        }

        plan = await agent.plan(inventory)
        assert len(plan.items) == 1
        assert len(agent.mapping_log) == 3

        # Verify type mappings
        fabric_types = {m["column"]: m["fabric_type"] for m in agent.mapping_log}
        assert fabric_types["ID"] == "BIGINT"
        assert fabric_types["NAME"] == "STRING"
        assert fabric_types["CREATED"] == "TIMESTAMP"

    @pytest.mark.asyncio
    async def test_execute_writes_files(self, output_dir: Path):
        """Execute writes DDL and pipeline files to disk."""
        scope = MigrationScope(include_paths=["/physical/USERS"])
        agent = SchemaAgent(output_dir=output_dir)

        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {
            "columns": [
                {"name": "USER_ID", "data_type": "NUMBER(9,0)"},
                {"name": "EMAIL", "data_type": "VARCHAR2(320)"},
            ]
        }

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)

        assert result.succeeded == 1
        assert result.failed == 0

        # Check files exist
        assert (output_dir / "ddl_lakehouse.sql").exists()
        assert (output_dir / "type_mapping_log.json").exists()
        assert (output_dir / "pipelines").exists()
        pipeline_files = list((output_dir / "pipelines").glob("*.json"))
        assert len(pipeline_files) >= 1

    @pytest.mark.asyncio
    async def test_validate_passes(self, output_dir: Path):
        """Full lifecycle validation."""
        scope = MigrationScope(include_paths=["/physical/PRODUCTS"])
        agent = SchemaAgent(output_dir=output_dir)

        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {
            "columns": [
                {"name": "PROD_ID", "data_type": "NUMBER(5,0)"},
                {"name": "PROD_NAME", "data_type": "VARCHAR2(200)"},
            ]
        }

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)
        report = await agent.validate(result)

        assert report.failed == 0
        assert report.passed >= 3

    @pytest.mark.asyncio
    async def test_warehouse_target(self, output_dir: Path):
        """Test with Warehouse (T-SQL) target."""
        scope = MigrationScope(include_paths=["/physical/ITEMS"])
        agent = SchemaAgent(output_dir=output_dir, target_platform=TargetPlatform.WAREHOUSE)

        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {
            "columns": [
                {"name": "ITEM_ID", "data_type": "NUMBER(10,0)"},
                {"name": "DESCRIPTION", "data_type": "CLOB"},
            ]
        }

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)

        assert result.succeeded == 1
        assert (output_dir / "ddl_warehouse.sql").exists()
        ddl = (output_dir / "ddl_warehouse.sql").read_text()
        assert "BIGINT" in ddl
        assert "VARCHAR(MAX)" in ddl

    @pytest.mark.asyncio
    async def test_fallback_type_warning(self, output_dir: Path):
        """Fallback types produce a validation warning."""
        scope = MigrationScope(include_paths=["/physical/SPATIAL"])
        agent = SchemaAgent(output_dir=output_dir)

        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {
            "columns": [
                {"name": "GEOM", "data_type": "SDO_GEOMETRY"},
            ]
        }

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)
        report = await agent.validate(result)

        assert report.warnings >= 1
        warn_detail = next(d for d in report.details if d.get("check") == "no_fallback_types")
        assert warn_detail["fallback_count"] == 1

    @pytest.mark.asyncio
    async def test_summary_report(self, output_dir: Path):
        """Summary report generated correctly."""
        scope = MigrationScope(include_paths=["/physical/T"])
        agent = SchemaAgent(output_dir=output_dir)

        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {
            "columns": [
                {"name": "A", "data_type": "NUMBER(5,0)"},
                {"name": "B", "data_type": "VARCHAR2(100)"},
            ]
        }

        await agent.plan(inventory)
        report = agent.generate_summary_report()

        assert "# Schema Migration Summary Report" in report
        assert "NUMBER" in report
        assert "VARCHAR2" in report
