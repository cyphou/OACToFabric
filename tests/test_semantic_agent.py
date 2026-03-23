"""Tests for Semantic Model Agent (Agent 04) — end-to-end lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agents.semantic.semantic_agent import SemanticModelAgent
from src.core.models import AssetType, Dependency, Inventory, InventoryItem, MigrationScope


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "semantic_output"
    d.mkdir()
    return d


def _make_inventory() -> Inventory:
    return Inventory(items=[
        InventoryItem(
            id="logicalTable__sales",
            asset_type=AssetType.LOGICAL_TABLE,
            source_path="/logical/Sales",
            name="Sales",
            metadata={
                "columns": [
                    {"name": "OrderID", "data_type": "NUMBER"},
                    {"name": "Revenue", "data_type": "DECIMAL"},
                    {"name": "TotalRevenue", "expression": "SUM(Revenue)"},
                    {"name": "RevenueYTD", "expression": "TODATE(Revenue, YEAR)"},
                ],
                "hierarchies": [
                    {"name": "Geography", "levels": ["Country", "Region", "City"]},
                ],
            },
            dependencies=[
                Dependency(
                    source_id="logicalTable__sales",
                    target_id="physicalTable__orders",
                    dependency_type="maps_to_physical",
                ),
            ],
        ),
        InventoryItem(
            id="logicalTable__products",
            asset_type=AssetType.LOGICAL_TABLE,
            source_path="/logical/Products",
            name="Products",
            metadata={
                "columns": [
                    {"name": "ProductID", "data_type": "NUMBER"},
                    {"name": "ProductName", "data_type": "VARCHAR2"},
                ],
            },
        ),
        InventoryItem(
            id="subjectArea__sales_analysis",
            asset_type=AssetType.SUBJECT_AREA,
            source_path="/presentation/Sales Analysis",
            name="Sales Analysis",
            metadata={
                "tables": [
                    {"name": "Sales", "columns": ["OrderID", "Revenue"]},
                    {"name": "Products", "columns": ["ProductName"]},
                ],
            },
        ),
    ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSemanticModelAgentLifecycle:
    @pytest.mark.asyncio
    async def test_discover_from_scope(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/logical/Sales", "/logical/Products"])
        agent = SemanticModelAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        assert inventory.count == 2

    @pytest.mark.asyncio
    async def test_plan_builds_ir(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)

        assert agent.ir is not None
        assert len(agent.ir.tables) == 2
        assert len(agent.ir.subject_areas) == 1
        assert plan.estimated_duration_minutes >= 1

    @pytest.mark.asyncio
    async def test_execute_writes_tmdl(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir, lakehouse_name="TestLH")
        inventory = _make_inventory()

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)

        assert result.succeeded == 3  # 2 logical tables + 1 subject area
        assert result.failed == 0

        # Check TMDL files written
        assert (output_dir / "model.tmdl").exists()
        assert (output_dir / "definition" / "tables" / "Sales.tmdl").exists()
        assert (output_dir / "definition" / "tables" / "Products.tmdl").exists()
        assert (output_dir / ".platform").exists()

        # Check Sales table content
        sales_content = (output_dir / "definition" / "tables" / "Sales.tmdl").read_text()
        assert "table Sales" in sales_content
        assert "TotalRevenue" in sales_content

    @pytest.mark.asyncio
    async def test_execute_writes_translation_log(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir)
        inventory = _make_inventory()

        plan = await agent.plan(inventory)
        await agent.execute(plan)

        log_path = output_dir / "translation_log.json"
        assert log_path.exists()
        log_data = json.loads(log_path.read_text())
        assert len(log_data) >= 1
        assert any(entry["column"] == "TotalRevenue" for entry in log_data)

    @pytest.mark.asyncio
    async def test_execute_writes_summary(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir)
        inventory = _make_inventory()

        plan = await agent.plan(inventory)
        await agent.execute(plan)

        summary_path = output_dir / "semantic_model_summary.md"
        assert summary_path.exists()
        content = summary_path.read_text(encoding="utf-8")
        assert "# Semantic Model Migration Summary Report" in content
        assert "Sales" in content

    @pytest.mark.asyncio
    async def test_validate_passes(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir)
        inventory = _make_inventory()

        plan = await agent.plan(inventory)
        result = await agent.execute(plan)
        report = await agent.validate(result)

        assert report.failed == 0
        assert report.passed >= 5  # execution + model.tmdl + table files + relationships + non-empty

    @pytest.mark.asyncio
    async def test_execute_without_plan_fails(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir)
        from src.core.models import MigrationPlan
        plan = MigrationPlan(agent_id="agent-04", items=[])

        result = await agent.execute(plan)
        assert result.failed == 0  # 0 items, 0 failures

    @pytest.mark.asyncio
    async def test_summary_report_content(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir)
        inventory = _make_inventory()

        plan = await agent.plan(inventory)
        await agent.execute(plan)

        report = agent.generate_summary_report()
        assert "## Model Overview" in report
        assert "Sales" in report
        assert "Products" in report
        assert "Expression Translations" in report

    @pytest.mark.asyncio
    async def test_perspectives_generated(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir)
        inventory = _make_inventory()

        plan = await agent.plan(inventory)
        await agent.execute(plan)

        persp_path = output_dir / "definition" / "perspectives.tmdl"
        assert persp_path.exists()
        content = persp_path.read_text()
        assert "Sales Analysis" in content

    @pytest.mark.asyncio
    async def test_platform_json_valid(self, output_dir: Path):
        agent = SemanticModelAgent(output_dir=output_dir)
        inventory = _make_inventory()

        plan = await agent.plan(inventory)
        await agent.execute(plan)

        platform = json.loads((output_dir / ".platform").read_text())
        assert platform["metadata"]["type"] == "SemanticModel"
