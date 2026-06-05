"""Tests for ETL Agent (Agent 03) — end-to-end lifecycle with mocks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agents.etl.etl_agent import ETLAgent
from src.core.models import AssetType, Inventory, InventoryItem, MigrationScope


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "etl_output"
    d.mkdir()
    return d


SAMPLE_FLOW_DEF = {
    "id": "flow_test",
    "name": "Test Flow",
    "steps": [
        {"id": "s1", "name": "ReadOrders", "type": "DATABASE_SOURCE", "table": "ORDERS",
         "upstreamSteps": [], "downstreamSteps": ["s2"]},
        {"id": "s2", "name": "FilterRecent", "type": "FILTER",
         "filterExpression": "order_date > '2024-01-01'",
         "upstreamSteps": ["s1"], "downstreamSteps": ["s3"]},
        {"id": "s3", "name": "WriteOrders", "type": "DATABASE_TARGET",
         "targetTable": "orders_target",
         "upstreamSteps": ["s2"], "downstreamSteps": []},
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestETLAgentLifecycle:
    @pytest.mark.asyncio
    async def test_discover_from_scope(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/dataflows/customer_load", "/dataflows/order_sync"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        assert inventory.count == 2

    @pytest.mark.asyncio
    async def test_plan_with_data_flow(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/dataflows/test_flow"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)

        # Attach flow definition
        inventory.items[0].metadata = {"definition": SAMPLE_FLOW_DEF}

        plan = await agent.plan(inventory)
        assert len(plan.items) == 1
        assert len(agent.mapped_flows) == 1
        assert len(agent.mapped_flows[0].mapped_steps) == 3

    @pytest.mark.asyncio
    async def test_plan_with_plsql(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/dataflows/plsql_flow"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)

        inventory.items[0].metadata = {
            "procedure_body": "BEGIN INSERT INTO target SELECT * FROM source; END;",
        }

        plan = await agent.plan(inventory)
        assert len(agent.plsql_translations) == 1
        assert "saveAsTable" in agent.plsql_translations[0].pyspark_code or "INSERT INTO" in agent.plsql_translations[0].pyspark_code

    @pytest.mark.asyncio
    async def test_plan_with_schedule(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/dataflows/scheduled_flow"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)

        inventory.items[0].metadata = {
            "definition": SAMPLE_FLOW_DEF,
            "schedule": {
                "repeat_interval": "FREQ=DAILY; BYHOUR=2",
                "enabled": "TRUE",
                "comments": "Daily load",
            },
        }

        plan = await agent.plan(inventory)
        assert len(agent.triggers) == 1
        assert agent.triggers[0].recurrence["frequency"] == "Day"

    @pytest.mark.asyncio
    async def test_execute_writes_files(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/dataflows/test_flow"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {"definition": SAMPLE_FLOW_DEF}

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)

        assert result.succeeded == 1
        assert result.failed == 0

        # Pipeline JSON
        pipeline_files = list((output_dir / "pipelines").glob("*.json"))
        assert len(pipeline_files) == 1
        data = json.loads(pipeline_files[0].read_text())
        assert "name" in data

        # Notebook
        nb_files = list((output_dir / "notebooks").glob("*.py"))
        assert len(nb_files) == 1

        # Summary report
        assert (output_dir / "etl_migration_summary.md").exists()

    @pytest.mark.asyncio
    async def test_execute_writes_triggers(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/dataflows/with_schedule"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {
            "definition": SAMPLE_FLOW_DEF,
            "schedule": {"repeat_interval": "FREQ=HOURLY; INTERVAL=2"},
        }

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)

        trigger_files = list((output_dir / "triggers").glob("*.json"))
        assert len(trigger_files) == 1

    @pytest.mark.asyncio
    async def test_validate_passes(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/dataflows/test_flow"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {"definition": SAMPLE_FLOW_DEF}

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)
        report = await agent.validate(result)

        assert report.failed == 0
        assert report.passed >= 4  # execution + pipeline + notebook + json validity

    @pytest.mark.asyncio
    async def test_review_queue(self, output_dir: Path):
        """Steps requiring review generate a review queue file."""
        flow_with_branch = {
            "id": "flow_review",
            "name": "Review Flow",
            "steps": [
                {"id": "s1", "name": "Source", "type": "DATABASE_SOURCE", "table": "T",
                 "upstreamSteps": [], "downstreamSteps": ["s2"]},
                {"id": "s2", "name": "BranchLogic", "type": "CONDITIONAL",
                 "upstreamSteps": ["s1"], "downstreamSteps": []},
            ],
        }
        scope = MigrationScope(include_paths=["/dataflows/review_flow"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {"definition": flow_with_branch}

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)

        review_path = output_dir / "review_queue.json"
        assert review_path.exists()
        review_items = json.loads(review_path.read_text())
        assert len(review_items) >= 1

    @pytest.mark.asyncio
    async def test_summary_report_content(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/dataflows/summary_test"])
        agent = ETLAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        inventory.items[0].metadata = {"definition": SAMPLE_FLOW_DEF}

        plan = await agent.plan(inventory)
        report = agent.generate_summary_report()

        assert "# ETL Migration Summary Report" in report
        assert "Test Flow" in report
        assert "Data Flows" in report

    @pytest.mark.asyncio
    async def test_discover_hydrates_essbase_cube_outline_from_lakehouse(self, output_dir: Path):
        class _MockLakehouse:
            def read_inventory(self, asset_type=None):
                if asset_type == "dataflow":
                    return []
                if asset_type == "cube":
                    return [{
                        "id": "Sample.Basic",
                        "source_path": "/Sample/Basic",
                        "name": "Basic",
                        "metadata": {
                            "application": "Sample",
                            "database": "Basic",
                            "cube_type": "BSO",
                        },
                    }]
                if asset_type == "dimension":
                    return [
                        {
                            "id": "Sample.Basic.Year",
                            "name": "Year",
                            "dependencies": ["Sample.Basic"],
                            "metadata": {
                                "dimension_type": "time",
                                "storage_type": "dense",
                            },
                        },
                        {
                            "id": "Sample.Basic.Product",
                            "name": "Product",
                            "dependencies": ["Sample.Basic"],
                            "metadata": {
                                "dimension_type": "regular",
                                "storage_type": "sparse",
                            },
                        },
                    ]
                if asset_type == "calcScript":
                    return [{
                        "id": "Sample.Basic.calc.CalcAll",
                        "name": "CalcAll",
                        "dependencies": ["Sample.Basic"],
                        "metadata": {"content": "AGG(Year);"},
                    }]
                return []

        agent = ETLAgent(output_dir=output_dir, lakehouse_client=_MockLakehouse())
        inv = await agent.discover(MigrationScope())

        cubes = [i for i in inv.items if i.asset_type == AssetType.DATA_MODEL]
        assert len(cubes) == 1
        cube = cubes[0]
        assert cube.metadata["cube_type"] == "BSO"
        assert "outline" in cube.metadata
        assert cube.metadata["outline"]["application"] == "Sample"
        assert len(cube.metadata["outline"]["dimensions"]) == 2

    @pytest.mark.asyncio
    async def test_aso_cube_skips_writeback_generation(self, output_dir: Path):
        agent = ETLAgent(output_dir=output_dir)
        inv = Inventory(items=[
            InventoryItem(
                id="aso_cube_1",
                asset_type=AssetType.DATA_MODEL,
                source_path="/essbase/App/ASOCube",
                name="ASOCube",
                metadata={
                    "cube_type": "ASO",
                    "outline": {
                        "application": "App",
                        "database": "ASOCube",
                        "dimensions": [],
                    },
                },
            ),
        ])

        await agent.plan(inv)
        assert agent.writeback_results == []

    @pytest.mark.asyncio
    async def test_bso_cube_generates_writeback_artifacts(self, output_dir: Path):
        agent = ETLAgent(output_dir=output_dir)
        inv = Inventory(items=[
            InventoryItem(
                id="bso_cube_1",
                asset_type=AssetType.DATA_MODEL,
                source_path="/essbase/FinPlan/Budget",
                name="Budget",
                metadata={
                    "cube_type": "BSO",
                    "outline": {
                        "cube_type": "BSO",
                        "application": "FinPlan",
                        "database": "Budget",
                        "dimensions": [
                            {
                                "name": "Account",
                                "type": "dense",
                                "dimension_type": "accounts",
                                "members": ["Revenue", "COGS", "Gross_Margin"],
                            },
                            {
                                "name": "Entity",
                                "type": "sparse",
                                "members": ["Corporate", "EMEA"],
                            },
                            {
                                "name": "Period",
                                "type": "dense",
                                "dimension_type": "time",
                                "members": ["Jan", "Feb", "Mar"],
                            },
                        ],
                    },
                },
            ),
        ])

        plan = await agent.plan(inv)
        assert len(agent.writeback_results) == 1

        result = await agent.execute(plan)
        assert result.failed == 0
        assert (output_dir / "writeback" / "warehouse_ddl_0.sql").exists()
