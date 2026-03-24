"""Tests for the RPD Binary Parser (Phase 44).

Covers:
- RPDBinaryHeader model and validation
- RPDBinaryObject, RPDBinarySection, RPDParseResult models
- RPDBinaryParser — full parse, header, sections, objects, properties
- LargeFileStreamingParser — streaming iteration
- RPDBinaryToXMLConverter — binary → XML conversion
- build_test_rpd_binary — test data generator
"""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import pytest

from src.core.rpd_binary_parser import (
    LargeFileStreamingParser,
    OBJ_COLUMN,
    OBJ_TABLE,
    RPD_MAGIC,
    RPD_VERSION_12,
    RPDBinaryHeader,
    RPDBinaryObject,
    RPDBinaryParser,
    RPDBinarySection,
    RPDBinaryToXMLConverter,
    RPDLayer,
    RPDParseResult,
    SECTION_PHYSICAL,
    build_test_rpd_binary,
)


# ===================================================================
# Test data helper
# ===================================================================

def _test_binary() -> bytes:
    """Build a small synthetic RPD binary for testing."""
    return build_test_rpd_binary(
        rpd_name="TestRPD",
        version=RPD_VERSION_12,
        tables=["DIM_CUSTOMER", "FACT_SALES"],
        columns={
            "DIM_CUSTOMER": ["CUSTOMER_ID", "NAME", "REGION"],
            "FACT_SALES": ["SALE_ID", "CUSTOMER_ID", "AMOUNT", "SALE_DATE"],
        },
    )


# ===================================================================
# RPDBinaryHeader
# ===================================================================


class TestRPDBinaryHeader:
    def test_valid_header(self):
        h = RPDBinaryHeader(magic=RPD_MAGIC, version=12)
        assert h.is_valid

    def test_invalid_magic(self):
        h = RPDBinaryHeader(magic=b"XXXX", version=12)
        assert not h.is_valid

    def test_invalid_version(self):
        h = RPDBinaryHeader(magic=RPD_MAGIC, version=99)
        assert not h.is_valid

    def test_version_label(self):
        h = RPDBinaryHeader(magic=RPD_MAGIC, version=12)
        assert h.version_label == "OBIEE 12c/OAC"

    def test_version_label_10(self):
        h = RPDBinaryHeader(magic=RPD_MAGIC, version=10)
        assert h.version_label == "OBIEE 10g"


# ===================================================================
# RPDBinaryObject
# ===================================================================


class TestRPDBinaryObject:
    def test_type_label_table(self):
        o = RPDBinaryObject(object_type=OBJ_TABLE, name="Sales")
        assert o.type_label == "Table"

    def test_type_label_column(self):
        o = RPDBinaryObject(object_type=OBJ_COLUMN, name="ID")
        assert o.type_label == "Column"

    def test_type_label_unknown(self):
        o = RPDBinaryObject(object_type=0xFF)
        assert "Unknown" in o.type_label


# ===================================================================
# RPDBinarySection
# ===================================================================


class TestRPDBinarySection:
    def test_name(self):
        s = RPDBinarySection(section_type=SECTION_PHYSICAL)
        assert s.name == "Physical Layer"

    def test_unknown_type(self):
        s = RPDBinarySection(section_type=0xFF)
        assert "Section" in s.name


# ===================================================================
# RPDParseResult
# ===================================================================


class TestRPDParseResult:
    def test_empty_result(self):
        r = RPDParseResult()
        assert r.total_objects == 0
        assert not r.is_valid  # header not valid by default

    def test_valid_result(self):
        r = RPDParseResult(header=RPDBinaryHeader(magic=RPD_MAGIC, version=12))
        assert r.is_valid

    def test_result_with_errors(self):
        r = RPDParseResult(
            header=RPDBinaryHeader(magic=RPD_MAGIC, version=12),
            errors=["Something went wrong"],
        )
        assert not r.is_valid

    def test_layer_summary(self):
        r = RPDParseResult(
            header=RPDBinaryHeader(magic=RPD_MAGIC, version=12),
            sections=[
                RPDBinarySection(section_type=SECTION_PHYSICAL, object_count=5),
            ],
        )
        summary = r.layer_summary
        assert summary["Physical Layer"] == 5

    def test_objects_by_layer(self):
        objs = [RPDBinaryObject(object_type=OBJ_TABLE, name="T1")]
        r = RPDParseResult(
            header=RPDBinaryHeader(magic=RPD_MAGIC, version=12),
            sections=[RPDBinarySection(layer=RPDLayer.PHYSICAL, objects=objs, object_count=1)],
        )
        assert len(r.objects_by_layer(RPDLayer.PHYSICAL)) == 1

    def test_tables(self):
        r = RPDParseResult(sections=[
            RPDBinarySection(objects=[
                RPDBinaryObject(object_type=OBJ_TABLE, name="A"),
                RPDBinaryObject(object_type=OBJ_COLUMN, name="c1"),
            ]),
        ])
        assert len(r.tables()) == 1
        assert len(r.columns()) == 1


# ===================================================================
# RPDBinaryParser
# ===================================================================


class TestRPDBinaryParser:
    def test_parse_synthetic(self):
        parser = RPDBinaryParser()
        result = parser.parse_bytes(_test_binary())
        assert result.is_valid
        assert result.header.rpd_name == "TestRPD"
        assert result.header.version == 12

    def test_section_count(self):
        parser = RPDBinaryParser()
        result = parser.parse_bytes(_test_binary())
        assert len(result.sections) == 1  # one physical layer section

    def test_object_count(self):
        parser = RPDBinaryParser()
        result = parser.parse_bytes(_test_binary())
        # 2 tables + 7 columns = 9 objects
        assert result.total_objects == 9

    def test_tables_found(self):
        parser = RPDBinaryParser()
        result = parser.parse_bytes(_test_binary())
        tables = result.tables()
        names = [t.name for t in tables]
        assert "DIM_CUSTOMER" in names
        assert "FACT_SALES" in names

    def test_columns_found(self):
        parser = RPDBinaryParser()
        result = parser.parse_bytes(_test_binary())
        cols = result.columns()
        names = [c.name for c in cols]
        assert "CUSTOMER_ID" in names
        assert "AMOUNT" in names

    def test_column_properties(self):
        parser = RPDBinaryParser()
        result = parser.parse_bytes(_test_binary())
        cols = result.columns()
        # Columns should have table property
        cust_id = [c for c in cols if c.name == "CUSTOMER_ID"]
        assert len(cust_id) >= 1
        assert cust_id[0].properties.get("table") in ("DIM_CUSTOMER", "FACT_SALES")

    def test_empty_data(self):
        parser = RPDBinaryParser()
        result = parser.parse_bytes(b"")
        assert not result.is_valid
        assert len(result.errors) >= 1

    def test_invalid_magic(self):
        data = bytearray(_test_binary())
        data[0:4] = b"XXXX"
        parser = RPDBinaryParser()
        result = parser.parse_bytes(bytes(data))
        assert not result.is_valid

    def test_parse_file(self):
        with tempfile.NamedTemporaryFile(suffix=".rpd", delete=False) as f:
            f.write(_test_binary())
            f.flush()
            parser = RPDBinaryParser()
            result = parser.parse_file(f.name)
            assert result.is_valid

    def test_parse_file_not_found(self):
        parser = RPDBinaryParser()
        result = parser.parse_file("/nonexistent/file.rpd")
        assert not result.is_valid

    def test_last_result(self):
        parser = RPDBinaryParser()
        assert parser.last_result is None
        parser.parse_bytes(_test_binary())
        assert parser.last_result is not None


# ===================================================================
# LargeFileStreamingParser
# ===================================================================


class TestLargeFileStreamingParser:
    def test_stream_objects(self):
        with tempfile.NamedTemporaryFile(suffix=".rpd", delete=False) as f:
            f.write(_test_binary())
            f.flush()
            parser = LargeFileStreamingParser(chunk_size=1024)
            objects = list(parser.iter_objects(f.name))
            assert len(objects) == 9
            assert parser.objects_parsed == 9

    def test_stream_missing_file(self):
        parser = LargeFileStreamingParser()
        objects = list(parser.iter_objects("/nonexistent.rpd"))
        assert len(objects) == 0
        assert len(parser.errors) >= 1

    def test_small_chunk_size(self):
        with tempfile.NamedTemporaryFile(suffix=".rpd", delete=False) as f:
            f.write(_test_binary())
            f.flush()
            parser = LargeFileStreamingParser(chunk_size=64)
            objects = list(parser.iter_objects(f.name))
            assert len(objects) == 9


# ===================================================================
# RPDBinaryToXMLConverter
# ===================================================================


class TestRPDBinaryToXMLConverter:
    def test_convert_to_xml(self):
        parser = RPDBinaryParser()
        result = parser.parse_bytes(_test_binary())
        converter = RPDBinaryToXMLConverter()
        xml = converter.convert(result)
        assert '<?xml version="1.0"' in xml
        assert "Repository" in xml
        assert "PhysicalLayer" in xml
        assert "DIM_CUSTOMER" in xml

    def test_convert_empty(self):
        result = RPDParseResult(header=RPDBinaryHeader(rpd_name="Empty", version=12))
        converter = RPDBinaryToXMLConverter()
        xml = converter.convert(result)
        assert "Empty" in xml
        assert "</Repository>" in xml

    def test_convert_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            parser = RPDBinaryParser()
            result = parser.parse_bytes(_test_binary())
            converter = RPDBinaryToXMLConverter()
            path = converter.convert_to_file(result, Path(tmpdir) / "output.xml")
            assert path.exists()
            content = path.read_text()
            assert "DIM_CUSTOMER" in content

    def test_xml_escaping(self):
        data = build_test_rpd_binary(tables=["Table<With>&Special"])
        parser = RPDBinaryParser()
        result = parser.parse_bytes(data)
        converter = RPDBinaryToXMLConverter()
        xml = converter.convert(result)
        assert "&lt;" in xml
        assert "&amp;" in xml


# ===================================================================
# build_test_rpd_binary
# ===================================================================


class TestBuildTestRPDBinary:
    def test_default(self):
        data = build_test_rpd_binary()
        assert data[:4] == RPD_MAGIC

    def test_custom_name(self):
        data = build_test_rpd_binary(rpd_name="MyRPD")
        parser = RPDBinaryParser()
        result = parser.parse_bytes(data)
        assert result.header.rpd_name == "MyRPD"

    def test_custom_tables(self):
        data = build_test_rpd_binary(tables=["A", "B", "C"])
        parser = RPDBinaryParser()
        result = parser.parse_bytes(data)
        tables = result.tables()
        assert len(tables) == 3

    def test_round_trip(self):
        data = build_test_rpd_binary(
            tables=["T1", "T2"],
            columns={"T1": ["C1", "C2"], "T2": ["C3"]},
        )
        parser = RPDBinaryParser()
        result = parser.parse_bytes(data)
        assert len(result.tables()) == 2
        assert len(result.columns()) == 3
