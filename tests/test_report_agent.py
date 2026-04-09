"""Tests for Report Migration Agent (Agent 05) — end-to-end lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agents.report.report_agent import ReportMigrationAgent
from src.core.models import (
    AssetType,
    Inventory,
    InventoryItem,
    MigrationScope,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "report_output"
    d.mkdir()
    return d


def _make_inventory() -> Inventory:
    """Create a test inventory with an analysis and a dashboard."""
    return Inventory(items=[
        InventoryItem(
            id="analysis__sales_overview",
            asset_type=AssetType.ANALYSIS,
            source_path="/analytics/Sales Overview",
            name="Sales Overview",
            metadata={
                "pages": [
                    {
                        "name": "Overview",
                        "views": [
                            {
                                "name": "RevenueChart",
                                "type": "verticalBar",
                                "title": "Revenue by Region",
                                "columns": [
                                    {"name": "Region", "table": "Sales"},
                                    {"name": "Revenue", "table": "Sales", "is_measure": True, "aggregation": "SUM"},
                                ],
                                "sorts": [{"column": "Revenue", "table": "Sales", "direction": "descending"}],
                                "conditionalFormats": [
                                    {
                                        "column": "Revenue",
                                        "type": "color",
                                        "thresholds": [{"value": 1000, "color": "green"}],
                                    },
                                ],
                            },
                            {
                                "name": "SalesTable",
                                "type": "table",
                                "title": "Sales Detail",
                                "columns": [
                                    {"name": "OrderID", "table": "Sales"},
                                    {"name": "Revenue", "table": "Sales", "is_measure": True},
                                ],
                            },
                        ],
                    },
                ],
                "prompts": [
                    {
                        "name": "Region Filter",
                        "type": "dropdown",
                        "table": "Sales",
                        "column": "Region",
                    },
                ],
                "actions": [
                    {
                        "type": "navigate_to_analysis",
                        "source": "RevenueChart",
                        "target": "Details",
                    },
                ],
            },
        ),
        InventoryItem(
            id="analysis__product_report",
            asset_type=AssetType.ANALYSIS,
            source_path="/analytics/Product Report",
            name="Product Report",
            metadata={
                "views": [
                    {
                        "name": "PieChart",
                        "type": "pie",
                        "title": "Sales by Product",
                        "columns": [
                            {"name": "ProductName", "table": "Products"},
                            {"name": "Revenue", "table": "Sales", "is_measure": True},
                        ],
                    },
                ],
            },
        ),
    ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReportMigrationAgentLifecycle:
    @pytest.mark.asyncio
    async def test_discover_from_scope(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/analytics/Sales Overview"])
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        assert inventory.count == 1

    @pytest.mark.asyncio
    async def test_plan(self, output_dir: Path):
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        assert len(plan.items) == 2
        assert plan.estimated_duration_minutes >= 1

    @pytest.mark.asyncio
    async def test_execute_writes_pbir(self, output_dir: Path):
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        result = await agent.execute(plan)

        assert result.succeeded == 2
        assert result.failed == 0

        # Check Sales Overview PBIR
        sales_dir = output_dir / "Sales_Overview"
        assert (sales_dir / "definition.pbir").exists()
        assert (sales_dir / "definition" / "report.json").exists()
        assert (sales_dir / ".platform").exists()

        # Check Product Report PBIR
        product_dir = output_dir / "Product_Report"
        assert (product_dir / "definition.pbir").exists()

    @pytest.mark.asyncio
    async def test_execute_creates_visual_files(self, output_dir: Path):
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        sales_dir = output_dir / "Sales_Overview"
        pages_dir = sales_dir / "definition" / "pages"
        assert pages_dir.exists()
        # Should have at least one page directory with visuals
        page_dirs = [d for d in pages_dir.iterdir() if d.is_dir()]
        assert len(page_dirs) >= 1
        visuals_dir = page_dirs[0] / "visuals"
        assert visuals_dir.exists()
        # PBIR v4.0: each visual in its own subdirectory with visual.json
        visual_dirs = [d for d in visuals_dir.iterdir() if d.is_dir()]
        assert len(visual_dirs) >= 2  # 2 views + 1 slicer = 3

    @pytest.mark.asyncio
    async def test_execute_writes_summary(self, output_dir: Path):
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        summary = output_dir / "report_migration_summary.md"
        assert summary.exists()
        content = summary.read_text(encoding="utf-8")
        assert "# Report Migration Summary" in content
        assert "Sales Overview" in content
        assert "Product Report" in content

    @pytest.mark.asyncio
    async def test_validate_passes(self, output_dir: Path):
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        result = await agent.execute(plan)
        report = await agent.validate(result)

        assert report.failed == 0
        assert report.passed >= 4

    @pytest.mark.asyncio
    async def test_actions_json_written(self, output_dir: Path):
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        actions_file = output_dir / "Sales_Overview" / "actions.json"
        assert actions_file.exists()
        actions = json.loads(actions_file.read_text(encoding="utf-8"))
        assert len(actions) == 1
        assert actions[0]["type"] == "drillthrough"

    @pytest.mark.asyncio
    async def test_platform_json_valid(self, output_dir: Path):
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        pf = json.loads(
            (output_dir / "Sales_Overview" / ".platform").read_text(encoding="utf-8")
        )
        assert pf["metadata"]["type"] == "Report"

    @pytest.mark.asyncio
    async def test_theme_file_written(self, output_dir: Path):
        """Theme info is embedded in report.json resourcePackages (PBIR v4.0)."""
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        report_json_path = (
            output_dir / "Sales_Overview" / "definition" / "report.json"
        )
        assert report_json_path.exists()
        rj = json.loads(report_json_path.read_text(encoding="utf-8"))
        assert "themeCollection" in rj

    @pytest.mark.asyncio
    async def test_summary_report_content(self, output_dir: Path):
        agent = ReportMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        report = agent.generate_summary_report()
        assert "## Overview" in report
        assert "Reports migrated" in report
        assert "Total pages" in report
