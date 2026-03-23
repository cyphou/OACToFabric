"""Tests for RPD XML parser — parse sample XML fragments."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.agents.discovery.rpd_parser import RPDParser
from src.core.models import AssetType


# ---------------------------------------------------------------------------
# Sample RPD XML fragments
# ---------------------------------------------------------------------------

SAMPLE_RPD_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Repository>
  <!-- Physical Layer -->
  <PhysicalLayer>
    <PhysicalDatabase name="PROD_DB">
      <PhysicalTable name="DIM_CUSTOMER">
        <PhysicalColumn name="CUSTOMER_ID" dataType="NUMBER"/>
        <PhysicalColumn name="CUSTOMER_NAME" dataType="VARCHAR2"/>
        <PhysicalColumn name="REGION" dataType="VARCHAR2"/>
      </PhysicalTable>
      <PhysicalTable name="FACT_SALES">
        <PhysicalColumn name="SALE_ID" dataType="NUMBER"/>
        <PhysicalColumn name="CUSTOMER_ID" dataType="NUMBER"/>
        <PhysicalColumn name="AMOUNT" dataType="NUMBER"/>
        <PhysicalColumn name="SALE_DATE" dataType="DATE"/>
      </PhysicalTable>
    </PhysicalDatabase>
  </PhysicalLayer>

  <!-- Logical Layer -->
  <LogicalLayer>
    <LogicalTable name="Customer">
      <LogicalColumn name="Customer ID"/>
      <LogicalColumn name="Customer Name"/>
      <LogicalColumn name="Region"/>
      <LogicalColumn name="Revenue">
        <Expression>SUM("FACT_SALES"."AMOUNT")</Expression>
      </LogicalColumn>
      <LogicalHierarchy name="Geography">
        <HierarchyLevel name="Region"/>
        <HierarchyLevel name="Customer"/>
      </LogicalHierarchy>
      <LogicalTableSource physicalTable="DIM_CUSTOMER"/>
    </LogicalTable>
    <LogicalTable name="Sales">
      <LogicalColumn name="Sale ID"/>
      <LogicalColumn name="Amount"/>
      <LogicalColumn name="Sale Date"/>
      <LogicalTableSource physicalTable="FACT_SALES"/>
    </LogicalTable>
  </LogicalLayer>

  <!-- Presentation Layer -->
  <PresentationLayer>
    <SubjectArea name="Sales Analysis">
      <PresentationTable name="Customers" logicalTable="Customer">
        <PresentationColumn name="Customer Name"/>
        <PresentationColumn name="Region"/>
      </PresentationTable>
      <PresentationTable name="Sales Data" logicalTable="Sales">
        <PresentationColumn name="Amount"/>
        <PresentationColumn name="Sale Date"/>
      </PresentationTable>
    </SubjectArea>
  </PresentationLayer>

  <!-- Security -->
  <SecurityLayer>
    <ApplicationRole name="SalesAnalyst">
      <Member name="john.doe"/>
      <Member name="jane.smith"/>
      <ObjectPermission object="Sales Analysis"/>
    </ApplicationRole>
    <SessionInitBlock name="SET_REGION">
      <SQL>SELECT REGION FROM USER_REGIONS WHERE USER_NAME = ':USER'</SQL>
      <SessionVariable name="REGION"/>
    </SessionInitBlock>
  </SecurityLayer>
</Repository>
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rpd_xml_file(tmp_path: Path) -> Path:
    p = tmp_path / "test_rpd.xml"
    p.write_text(SAMPLE_RPD_XML, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRPDParser:
    def test_parse_returns_items(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        assert len(items) > 0

    def test_physical_tables_extracted(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        physical = [i for i in items if i.asset_type == AssetType.PHYSICAL_TABLE]
        assert len(physical) == 2
        names = {i.name for i in physical}
        assert "DIM_CUSTOMER" in names
        assert "FACT_SALES" in names

    def test_physical_table_columns(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        dim = next(i for i in items if i.name == "DIM_CUSTOMER")
        cols = dim.metadata.get("columns", [])
        assert len(cols) == 3
        col_names = [c["name"] for c in cols]
        assert "CUSTOMER_ID" in col_names

    def test_logical_tables_extracted(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        logical = [i for i in items if i.asset_type == AssetType.LOGICAL_TABLE]
        assert len(logical) == 2

    def test_logical_table_has_dependencies(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        customer = next(i for i in items if i.name == "Customer" and i.asset_type == AssetType.LOGICAL_TABLE)
        assert len(customer.dependencies) >= 1
        dep_types = [d.dependency_type for d in customer.dependencies]
        assert "maps_to_physical" in dep_types

    def test_logical_table_custom_calc_count(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        customer = next(i for i in items if i.name == "Customer" and i.asset_type == AssetType.LOGICAL_TABLE)
        assert customer.metadata.get("custom_calc_count", 0) >= 1  # Revenue has expression

    def test_subject_areas_extracted(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        sa = [i for i in items if i.asset_type == AssetType.SUBJECT_AREA]
        assert len(sa) == 1
        assert sa[0].name == "Sales Analysis"

    def test_security_roles_extracted(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        roles = [i for i in items if i.asset_type == AssetType.SECURITY_ROLE]
        assert len(roles) == 1
        assert roles[0].name == "SalesAnalyst"
        assert "john.doe" in roles[0].metadata.get("members", [])

    def test_init_blocks_extracted(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        blocks = [i for i in items if i.asset_type == AssetType.INIT_BLOCK]
        assert len(blocks) == 1
        assert blocks[0].name == "SET_REGION"
        assert "REGION" in blocks[0].metadata.get("variables", [])

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            RPDParser(tmp_path / "nonexistent.xml")

    def test_hierarchies(self, rpd_xml_file: Path):
        parser = RPDParser(rpd_xml_file)
        items = parser.parse()
        customer = next(i for i in items if i.name == "Customer" and i.asset_type == AssetType.LOGICAL_TABLE)
        hierarchies = customer.metadata.get("hierarchies", [])
        assert len(hierarchies) == 1
        assert hierarchies[0]["name"] == "Geography"
        assert "Region" in hierarchies[0]["levels"]
