"""Tests for the streaming RPD XML parser — memory-efficient parsing."""

from __future__ import annotations

import pytest
from pathlib import Path
from lxml import etree

from src.core.models import AssetType
from src.core.streaming_parser import StreamingRPDParser


# ---------------------------------------------------------------------------
# Fixtures — generate sample RPD XML files
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_rpd_xml(tmp_path: Path) -> Path:
    """Create a simple RPD XML with various asset types."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Repository>
  <PhysicalLayer>
    <PhysicalTable name="DIM_PRODUCT">
      <Description>Product dimension table</Description>
      <Schema>SH</Schema>
    </PhysicalTable>
    <PhysicalTable name="FACT_SALES">
      <Description>Sales fact table</Description>
      <Schema>SH</Schema>
    </PhysicalTable>
  </PhysicalLayer>
  <LogicalLayer>
    <LogicalTable name="Product">
      <Description>Logical product entity</Description>
      <TableRef name="DIM_PRODUCT"/>
    </LogicalTable>
  </LogicalLayer>
  <PresentationLayer>
    <SubjectArea name="Sales Analysis">
      <Description>Sales subject area</Description>
    </SubjectArea>
    <PresentationTable name="Products">
      <Description>Product presentation table</Description>
    </PresentationTable>
  </PresentationLayer>
  <Security>
    <SecurityRole name="Admin">
      <Description>Administrator role</Description>
    </SecurityRole>
    <InitBlock name="SetRegion">
      <Description>Initialize region variable</Description>
    </InitBlock>
  </Security>
</Repository>"""
    path = tmp_path / "sample_rpd.xml"
    path.write_text(xml, encoding="utf-8")
    return path


@pytest.fixture
def large_rpd_xml(tmp_path: Path) -> Path:
    """Create an RPD XML with many elements to test streaming."""
    root = etree.Element("Repository")
    physical = etree.SubElement(root, "PhysicalLayer")
    for i in range(200):
        table = etree.SubElement(physical, "PhysicalTable", name=f"TABLE_{i:04d}")
        desc = etree.SubElement(table, "Description")
        desc.text = f"Table number {i}"
    
    tree = etree.ElementTree(root)
    path = tmp_path / "large_rpd.xml"
    tree.write(str(path), xml_declaration=True, encoding="UTF-8", pretty_print=True)
    return path


@pytest.fixture
def empty_rpd_xml(tmp_path: Path) -> Path:
    """Create an RPD XML with no tracked elements."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Repository>
  <CustomSection>
    <CustomElement name="something"/>
  </CustomSection>
</Repository>"""
    path = tmp_path / "empty_rpd.xml"
    path.write_text(xml, encoding="utf-8")
    return path


@pytest.fixture
def rpd_with_refs(tmp_path: Path) -> Path:
    """Create an RPD XML with dependency references."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Repository>
  <LogicalLayer>
    <LogicalTable name="OrderFacts">
      <TableRef name="FACT_ORDERS"/>
      <ColumnRef name="ProductKey"/>
    </LogicalTable>
  </LogicalLayer>
</Repository>"""
    path = tmp_path / "refs_rpd.xml"
    path.write_text(xml, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------


class TestStreamingParserBasic:
    def test_parses_physical_tables(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        physical = [i for i in items if i.asset_type == AssetType.PHYSICAL_TABLE]
        assert len(physical) == 2
        names = {i.name for i in physical}
        assert "DIM_PRODUCT" in names
        assert "FACT_SALES" in names

    def test_parses_logical_tables(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        logical = [i for i in items if i.asset_type == AssetType.LOGICAL_TABLE]
        assert len(logical) == 1
        assert logical[0].name == "Product"

    def test_parses_subject_areas(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        sas = [i for i in items if i.asset_type == AssetType.SUBJECT_AREA]
        assert len(sas) == 1
        assert sas[0].name == "Sales Analysis"

    def test_parses_presentation_tables(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        pts = [i for i in items if i.asset_type == AssetType.PRESENTATION_TABLE]
        assert len(pts) == 1

    def test_parses_security_roles(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        roles = [i for i in items if i.asset_type == AssetType.SECURITY_ROLE]
        assert len(roles) == 1
        assert roles[0].name == "Admin"

    def test_parses_init_blocks(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        blocks = [i for i in items if i.asset_type == AssetType.INIT_BLOCK]
        assert len(blocks) == 1

    def test_total_items(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        # 2 physical + 1 logical + 1 subject area + 1 presentation + 1 role + 1 init
        assert len(items) == 7

    def test_source_is_rpd_streaming(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        assert all(i.source == "rpd_streaming" for i in items)


# ---------------------------------------------------------------------------
# Streaming features
# ---------------------------------------------------------------------------


class TestStreamingFeatures:
    def test_max_items_limit(self, large_rpd_xml: Path):
        parser = StreamingRPDParser(large_rpd_xml)
        items = parser.parse(max_items=10)
        assert len(items) == 10

    def test_items_yielded_counter(self, large_rpd_xml: Path):
        parser = StreamingRPDParser(large_rpd_xml)
        items = parser.parse(max_items=25)
        assert parser.items_yielded == 25

    def test_full_parse_200_items(self, large_rpd_xml: Path):
        parser = StreamingRPDParser(large_rpd_xml)
        items = parser.parse()
        assert len(items) == 200

    def test_asset_type_filter(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse(asset_types=[AssetType.PHYSICAL_TABLE])
        assert len(items) == 2
        assert all(i.asset_type == AssetType.PHYSICAL_TABLE for i in items)

    def test_iter_items_generator(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        count = 0
        for item in parser.iter_items():
            count += 1
            assert item.name  # every item should have a name
        assert count > 0

    def test_empty_xml_yields_nothing(self, empty_rpd_xml: Path):
        parser = StreamingRPDParser(empty_rpd_xml)
        items = parser.parse()
        assert len(items) == 0


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


class TestStreamingDependencies:
    def test_extracts_references(self, rpd_with_refs: Path):
        parser = StreamingRPDParser(rpd_with_refs)
        items = parser.parse()
        assert len(items) == 1
        item = items[0]
        assert item.name == "OrderFacts"
        # Should have extracted Ref elements as dependencies
        assert len(item.dependencies) > 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestStreamingErrors:
    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            StreamingRPDParser(tmp_path / "nonexistent.xml")

    def test_invalid_xml(self, tmp_path: Path):
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("<broken><unclosed>", encoding="utf-8")
        parser = StreamingRPDParser(bad_xml)
        with pytest.raises(etree.XMLSyntaxError):
            parser.parse()


# ---------------------------------------------------------------------------
# Item structure
# ---------------------------------------------------------------------------


class TestStreamingItemStructure:
    def test_item_id_format(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        for item in items:
            assert "__" in item.id  # format: assetType__name_slug

    def test_item_source_path(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        for item in items:
            assert item.source_path.startswith("/")

    def test_item_metadata(self, simple_rpd_xml: Path):
        parser = StreamingRPDParser(simple_rpd_xml)
        items = parser.parse()
        # Physical tables should have Description in metadata
        physical = [i for i in items if i.asset_type == AssetType.PHYSICAL_TABLE]
        assert any("Description" in i.metadata for i in physical)
