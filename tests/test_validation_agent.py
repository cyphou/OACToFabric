"""Tests for Validation Agent (Agent 07) — end-to-end lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.validation.validation_agent import ValidationAgent
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
    d = tmp_path / "validation_output"
    d.mkdir()
    return d


def _make_inventory() -> Inventory:
    """Create a test inventory covering all validation layers."""
    return Inventory(items=[
        # Data layer — physical tables
        InventoryItem(
            id="table__sales",
            asset_type=AssetType.PHYSICAL_TABLE,
            source_path="/tables/Sales",
            name="Sales",
            metadata={
                "source_name": "SALES",
                "target_name": "dbo.Sales",
                "columns": [
                    {"name": "Amount", "type": "number"},
                    {"name": "Region", "type": "varchar"},
                    {"name": "OrderDate", "type": "date"},
                ],
            },
        ),
        InventoryItem(
            id="table__products",
            asset_type=AssetType.PHYSICAL_TABLE,
            source_path="/tables/Products",
            name="Products",
            metadata={
                "source_name": "PRODUCTS",
                "target_name": "dbo.Products",
                "columns": [
                    {"name": "ProductId", "type": "int"},
                    {"name": "Name", "type": "varchar"},
                    {"name": "Price", "type": "decimal"},
                ],
            },
        ),
        # Semantic model
        InventoryItem(
            id="model__sales",
            asset_type=AssetType.DATA_MODEL,
            source_path="/model/Sales",
            name="SalesModel",
            metadata={
                "measures": [
                    {
                        "name": "TotalSales",
                        "table": "Sales",
                        "dax_expression": "SUM(Sales[Amount])",
                        "oac_expression": "SUM(Revenue)",
                    },
                ],
                "relationships": [
                    {
                        "from_table": "Sales",
                        "from_column": "ProductId",
                        "to_table": "Products",
                        "to_column": "ProductId",
                        "type": "M:1",
                    },
                ],
                "hierarchies": [
                    {
                        "name": "Geography",
                        "table": "Sales",
                        "levels": ["Region", "City"],
                        "measure": "TotalSales",
                    },
                ],
                "filters": [
                    {
                        "table": "Sales",
                        "column": "Region",
                        "value": "East",
                        "measure": "TotalSales",
                    },
                ],
            },
        ),
        # Report
        InventoryItem(
            id="report__dash",
            asset_type=AssetType.ANALYSIS,
            source_path="/reports/Dashboard",
            name="Dashboard",
            metadata={
                "name": "Dashboard",
                "pages": [
                    {"name": "Overview", "visual_count": 6},
                    {"name": "Detail", "visual_count": 4},
                ],
            },
        ),
        # Security
        InventoryItem(
            id="role__regional",
            asset_type=AssetType.SECURITY_ROLE,
            source_path="/security/RegionalSales",
            name="RegionalSales",
            metadata={
                "name": "RegionalSales",
                "test_user": "alice@corp.com",
                "rls_filters": [
                    {
                        "table_name": "Sales",
                        "filter_expression": "Region='East'",
                    },
                ],
                "object_permissions": [
                    {"type": "hideColumn", "table": "Sales", "column": "Margin"},
                ],
            },
        ),
    ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidationAgentLifecycle:
    @pytest.mark.asyncio
    async def test_discover(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        scope = MigrationScope(include_paths=["/tables/Sales"])
        inv = await agent.discover(scope)
        assert inv.count == 1

    @pytest.mark.asyncio
    async def test_plan(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        assert len(plan.items) == 5
        assert plan.estimated_duration_minutes >= 5

    @pytest.mark.asyncio
    async def test_execute_succeeds(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        result = await agent.execute(plan)
        assert result.succeeded == 4
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_writes_data_report(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        f = output_dir / "data_reconciliation_report.md"
        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert "Data Reconciliation Report" in content

    @pytest.mark.asyncio
    async def test_writes_reconciliation_queries(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        f = output_dir / "reconciliation_queries.sql"
        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert "COUNT(*)" in content

    @pytest.mark.asyncio
    async def test_writes_semantic_report(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        f = output_dir / "semantic_validation_report.md"
        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert "Semantic Model Validation Report" in content

    @pytest.mark.asyncio
    async def test_writes_report_validation(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        f = output_dir / "report_validation_report.md"
        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert "Report Validation Report" in content

    @pytest.mark.asyncio
    async def test_writes_security_report(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        f = output_dir / "security_validation_report.md"
        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert "Security Validation Report" in content

    @pytest.mark.asyncio
    async def test_writes_summary(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        f = output_dir / "validation_summary.md"
        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert "Validation Summary" in content
        assert "Data Reconciliation" in content
        assert "Semantic Model" in content
        assert "Security" in content

    @pytest.mark.asyncio
    async def test_validate_passes(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        result = await agent.execute(plan)
        report = await agent.validate(result)
        assert report.failed == 0
        assert report.passed >= 5

    @pytest.mark.asyncio
    async def test_summary_report_content(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        report = agent.generate_summary_report()
        assert "## Overview" in report
        assert "Data Reconciliation" in report
        assert "Semantic Model" in report
        assert "Report" in report
        assert "Security" in report
        assert "Generated Artefacts" in report

    @pytest.mark.asyncio
    async def test_data_report_has_checks(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        # Data report should have checks for 2 tables
        assert agent._data_report is not None
        assert agent._data_report.total_checks > 0
        # Each table has: row_count + null_count×cols + distinct×cols + numerics + sample + type
        # Sales: 3 cols (1 numeric) → at least row_count + 3 null + 3 distinct + 4 numeric + sample
        assert agent._data_report.total_checks >= 10

    @pytest.mark.asyncio
    async def test_semantic_report_has_checks(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        assert agent._semantic_report is not None
        # 1 measure + 2 relationship + 2 hierarchy levels + 1 filter = 6
        assert agent._semantic_report.total_checks >= 5

    @pytest.mark.asyncio
    async def test_security_report_has_checks(self, output_dir: Path):
        agent = ValidationAgent(output_dir=output_dir)
        inv = _make_inventory()
        plan = await agent.plan(inv)
        await agent.execute(plan)

        assert agent._security_report is not None
        # RLS row count + data content + OLS visibility + negative = 4+
        assert agent._security_report.total_checks >= 3
