"""Tests for the Discovery Agent (Agent 01) — end-to-end with mocks."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.discovery.discovery_agent import DiscoveryAgent
from src.core.models import (
    AssetType,
    ComplexityCategory,
    Inventory,
    InventoryItem,
    MigrationScope,
)


# ---------------------------------------------------------------------------
# Sample RPD XML (minimal)
# ---------------------------------------------------------------------------

MINI_RPD = """\
<?xml version="1.0"?>
<Repository>
  <PhysicalTable name="ORDERS">
    <PhysicalColumn name="ORDER_ID" dataType="NUMBER"/>
  </PhysicalTable>
  <LogicalTable name="Orders">
    <LogicalColumn name="Order ID"/>
    <LogicalTableSource physicalTable="ORDERS"/>
  </LogicalTable>
  <SubjectArea name="Order Tracking">
    <PresentationTable name="Orders" logicalTable="Orders">
      <PresentationColumn name="Order ID"/>
    </PresentationTable>
  </SubjectArea>
</Repository>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_oac_client(catalog_items: list[InventoryItem] | None = None, connections: list[InventoryItem] | None = None):
    """Return an OACClient mock."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.discover_catalog_assets = AsyncMock(return_value=catalog_items or [])
    client.discover_connections = AsyncMock(return_value=connections or [])
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDiscoveryAgentDiscover:
    @pytest.mark.asyncio
    async def test_discover_api_only(self):
        """Discover from OAC API only (no RPD)."""
        mock_items = [
            InventoryItem(
                id="analysis__report1",
                asset_type=AssetType.ANALYSIS,
                source_path="/shared/Report1",
                name="Report1",
                metadata={"columns": ["A", "B"]},
            ),
        ]
        oac = _mock_oac_client(catalog_items=mock_items)
        agent = DiscoveryAgent(oac_client=oac, rpd_xml_path="")

        scope = MigrationScope(include_paths=["/shared"])
        inventory = await agent.discover(scope)

        assert inventory.count == 1
        assert inventory.items[0].name == "Report1"
        assert inventory.items[0].complexity_score > 0

    @pytest.mark.asyncio
    async def test_discover_with_rpd(self, tmp_path: Path):
        """Discover from OAC API + RPD XML."""
        rpd_file = tmp_path / "test.xml"
        rpd_file.write_text(MINI_RPD, encoding="utf-8")

        oac = _mock_oac_client()
        agent = DiscoveryAgent(oac_client=oac, rpd_xml_path=str(rpd_file))

        scope = MigrationScope()
        inventory = await agent.discover(scope)

        # Should have physical table, logical table, subject area, presentation table
        assert inventory.count >= 3
        types = {i.asset_type for i in inventory.items}
        assert AssetType.PHYSICAL_TABLE in types
        assert AssetType.LOGICAL_TABLE in types
        assert AssetType.SUBJECT_AREA in types

    @pytest.mark.asyncio
    async def test_discover_deduplicates(self, tmp_path: Path):
        """Items from API and RPD with same ID get merged."""
        rpd_file = tmp_path / "test.xml"
        rpd_file.write_text(MINI_RPD, encoding="utf-8")

        # API returns item with same ID as RPD physical table
        api_item = InventoryItem(
            id="physicaltable__orders",
            asset_type=AssetType.PHYSICAL_TABLE,
            source_path="/physical/ORDERS",
            name="ORDERS",
            metadata={"extra_info": "from_api"},
        )
        oac = _mock_oac_client(catalog_items=[api_item])
        agent = DiscoveryAgent(oac_client=oac, rpd_xml_path=str(rpd_file))

        scope = MigrationScope()
        inventory = await agent.discover(scope)

        # Should not have duplicates
        ids = [i.id for i in inventory.items]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_discover_applies_exclude(self):
        """Excluded paths are filtered out."""
        mock_items = [
            InventoryItem(id="a1", asset_type=AssetType.ANALYSIS, source_path="/shared/include/A", name="A"),
            InventoryItem(id="a2", asset_type=AssetType.ANALYSIS, source_path="/shared/exclude/B", name="B"),
        ]
        oac = _mock_oac_client(catalog_items=mock_items)
        agent = DiscoveryAgent(oac_client=oac, rpd_xml_path="")

        scope = MigrationScope(exclude_paths=["/shared/exclude"])
        inventory = await agent.discover(scope)

        assert inventory.count == 1
        assert inventory.items[0].name == "A"

    @pytest.mark.asyncio
    async def test_dependency_graph_built(self, tmp_path: Path):
        """Dependency graph is populated after discover."""
        rpd_file = tmp_path / "test.xml"
        rpd_file.write_text(MINI_RPD, encoding="utf-8")

        oac = _mock_oac_client()
        agent = DiscoveryAgent(oac_client=oac, rpd_xml_path=str(rpd_file))

        scope = MigrationScope()
        await agent.discover(scope)

        assert agent.dependency_graph.node_count > 0


class TestDiscoveryAgentPlanExecuteValidate:
    @pytest.mark.asyncio
    async def test_dry_run(self):
        """Full lifecycle without Lakehouse (dry-run)."""
        mock_items = [
            InventoryItem(
                id="analysis__test",
                asset_type=AssetType.ANALYSIS,
                source_path="/shared/test",
                name="Test",
            ),
        ]
        oac = _mock_oac_client(catalog_items=mock_items)
        agent = DiscoveryAgent(oac_client=oac, rpd_xml_path="")

        scope = MigrationScope()
        inventory = await agent.discover(scope)
        plan = await agent.plan(inventory)
        result = await agent.execute(plan)
        report = await agent.validate(result)

        assert result.succeeded == 1
        assert report.passed >= 1


class TestSummaryReport:
    @pytest.mark.asyncio
    async def test_generates_markdown(self):
        mock_items = [
            InventoryItem(
                id="a1", asset_type=AssetType.ANALYSIS,
                source_path="/shared/A", name="A",
            ),
            InventoryItem(
                id="d1", asset_type=AssetType.DASHBOARD,
                source_path="/shared/D", name="D",
            ),
        ]
        oac = _mock_oac_client(catalog_items=mock_items)
        agent = DiscoveryAgent(oac_client=oac, rpd_xml_path="")

        scope = MigrationScope()
        inventory = await agent.discover(scope)
        report = agent.generate_summary_report(inventory)

        assert "# Discovery Summary Report" in report
        assert "analysis" in report
        assert "dashboard" in report
