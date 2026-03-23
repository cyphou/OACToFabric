"""Tests for Oracle → Fabric data type mapping engine."""

from __future__ import annotations

import pytest

from src.agents.schema.type_mapper import (
    TargetPlatform,
    TypeMapping,
    map_all_columns,
    map_oracle_type,
)


# ---------------------------------------------------------------------------
# Lakehouse (Spark/Delta) mappings
# ---------------------------------------------------------------------------

class TestLakehouseMapping:
    """Test Oracle → Fabric Lakehouse (Spark SQL) type mapping."""

    @pytest.mark.parametrize(
        "oracle, expected",
        [
            ("NUMBER(5,0)", "INT"),
            ("NUMBER(9,0)", "INT"),
            ("NUMBER(10,0)", "BIGINT"),
            ("NUMBER(18,0)", "BIGINT"),
            ("NUMBER(19,0)", "DECIMAL(19,0)"),
            ("NUMBER(10,2)", "DECIMAL(10,2)"),
            ("NUMBER(38,10)", "DECIMAL(38,10)"),
            ("NUMBER", "DOUBLE"),
            ("VARCHAR2(100)", "STRING"),
            ("VARCHAR2(4000 BYTE)", "STRING"),
            ("NVARCHAR2(255)", "STRING"),
            ("CHAR(10)", "STRING"),
            ("NCHAR(5)", "STRING"),
            ("CLOB", "STRING"),
            ("NCLOB", "STRING"),
            ("DATE", "TIMESTAMP"),
            ("TIMESTAMP", "TIMESTAMP"),
            ("TIMESTAMP(6)", "TIMESTAMP"),
            ("TIMESTAMP WITH TIME ZONE", "TIMESTAMP"),
            ("TIMESTAMP(3) WITH LOCAL TIME ZONE", "TIMESTAMP"),
            ("BLOB", "BINARY"),
            ("RAW(16)", "BINARY"),
            ("FLOAT", "DOUBLE"),
            ("FLOAT(126)", "DOUBLE"),
            ("XMLTYPE", "STRING"),
            ("INTERVAL YEAR TO MONTH", "STRING"),
            ("INTERVAL DAY TO SECOND", "STRING"),
            ("BOOLEAN", "BOOLEAN"),
            ("INTEGER", "INT"),
            ("BINARY_FLOAT", "FLOAT"),
            ("BINARY_DOUBLE", "DOUBLE"),
            ("LONG", "STRING"),
            ("LONG RAW", "BINARY"),
        ],
    )
    def test_mapping(self, oracle: str, expected: str):
        result = map_oracle_type(oracle, TargetPlatform.LAKEHOUSE)
        assert result.fabric_type == expected

    def test_unknown_type_fallback(self):
        result = map_oracle_type("SDO_GEOMETRY", TargetPlatform.LAKEHOUSE)
        assert result.fabric_type == "STRING"
        assert result.is_fallback is True

    def test_case_insensitivity(self):
        r1 = map_oracle_type("number(5,0)", TargetPlatform.LAKEHOUSE)
        r2 = map_oracle_type("NUMBER(5,0)", TargetPlatform.LAKEHOUSE)
        assert r1.fabric_type == r2.fabric_type


# ---------------------------------------------------------------------------
# Warehouse (T-SQL) mappings
# ---------------------------------------------------------------------------

class TestWarehouseMapping:
    @pytest.mark.parametrize(
        "oracle, expected",
        [
            ("NUMBER(5,0)", "INT"),
            ("NUMBER(18,0)", "BIGINT"),
            ("NUMBER(10,2)", "DECIMAL(10,2)"),
            ("VARCHAR2(100)", "VARCHAR(100)"),
            ("CLOB", "VARCHAR(MAX)"),
            ("DATE", "DATETIME2"),
            ("TIMESTAMP", "DATETIME2(7)"),
            ("TIMESTAMP WITH TIME ZONE", "DATETIME2(7)"),
            ("BLOB", "VARBINARY(MAX)"),
            ("RAW(32)", "VARBINARY(MAX)"),
        ],
    )
    def test_mapping(self, oracle: str, expected: str):
        result = map_oracle_type(oracle, TargetPlatform.WAREHOUSE)
        assert result.fabric_type == expected

    def test_unknown_type_fallback(self):
        result = map_oracle_type("BFILE", TargetPlatform.WAREHOUSE)
        assert result.fabric_type == "VARCHAR(MAX)"
        assert result.is_fallback is True


# ---------------------------------------------------------------------------
# map_all_columns
# ---------------------------------------------------------------------------

class TestMapAllColumns:
    def test_maps_columns(self):
        columns = [
            {"name": "ID", "data_type": "NUMBER(10,0)"},
            {"name": "NAME", "data_type": "VARCHAR2(255)"},
            {"name": "CREATED", "data_type": "DATE"},
        ]
        result = map_all_columns(columns, TargetPlatform.LAKEHOUSE)
        assert len(result) == 3
        assert result[0]["fabric_type"] == "BIGINT"
        assert result[1]["fabric_type"] == "STRING"
        assert result[2]["fabric_type"] == "TIMESTAMP"

    def test_preserves_original_fields(self):
        columns = [{"name": "ID", "data_type": "NUMBER(5,0)", "nullable": False}]
        result = map_all_columns(columns)
        assert result[0]["name"] == "ID"
        assert result[0]["nullable"] is False
