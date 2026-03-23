"""Tests for DDL generator."""

from __future__ import annotations

import pytest

from src.agents.schema.ddl_generator import (
    generate_create_table,
    generate_create_view,
    generate_ddl_script,
)
from src.agents.schema.type_mapper import TargetPlatform


# ---------------------------------------------------------------------------
# CREATE TABLE — Lakehouse
# ---------------------------------------------------------------------------

class TestCreateTableLakehouse:
    def test_basic_table(self):
        columns = [
            {"name": "ID", "data_type": "NUMBER(10,0)"},
            {"name": "NAME", "data_type": "VARCHAR2(255)"},
        ]
        ddl = generate_create_table("CUSTOMERS", columns, TargetPlatform.LAKEHOUSE)
        assert "CREATE TABLE IF NOT EXISTS" in ddl
        assert "CUSTOMERS" in ddl
        assert "BIGINT" in ddl
        assert "STRING" in ddl
        assert "USING DELTA" in ddl

    def test_not_null(self):
        columns = [{"name": "ID", "data_type": "NUMBER(5,0)", "nullable": False}]
        ddl = generate_create_table("T", columns, TargetPlatform.LAKEHOUSE)
        assert "NOT NULL" in ddl

    def test_partitioned_by(self):
        columns = [
            {"name": "SALE_DATE", "data_type": "DATE"},
            {"name": "AMOUNT", "data_type": "NUMBER(10,2)"},
        ]
        ddl = generate_create_table("SALES", columns, TargetPlatform.LAKEHOUSE, partition_by=["SALE_DATE"])
        assert "PARTITIONED BY" in ddl
        assert "SALE_DATE" in ddl

    def test_comment(self):
        columns = [{"name": "ID", "data_type": "NUMBER(5,0)"}]
        ddl = generate_create_table("T", columns, TargetPlatform.LAKEHOUSE, comment="Test table")
        assert "COMMENT" in ddl
        assert "Test table" in ddl

    def test_schema_prefix(self):
        columns = [{"name": "ID", "data_type": "NUMBER(5,0)"}]
        ddl = generate_create_table("T", columns, TargetPlatform.LAKEHOUSE, schema="mydb")
        assert "mydb.T" in ddl


# ---------------------------------------------------------------------------
# CREATE TABLE — Warehouse
# ---------------------------------------------------------------------------

class TestCreateTableWarehouse:
    def test_basic_table(self):
        columns = [
            {"name": "ID", "data_type": "NUMBER(10,0)"},
            {"name": "NAME", "data_type": "VARCHAR2(100)"},
        ]
        ddl = generate_create_table("CUSTOMERS", columns, TargetPlatform.WAREHOUSE)
        assert "CREATE TABLE" in ddl
        assert "BIGINT" in ddl
        assert "VARCHAR(100)" in ddl
        assert "USING DELTA" not in ddl

    def test_primary_key(self):
        columns = [{"name": "ID", "data_type": "NUMBER(5,0)", "nullable": False}]
        ddl = generate_create_table("T", columns, TargetPlatform.WAREHOUSE, primary_key=["ID"])
        assert "PRIMARY KEY" in ddl
        assert "NOT ENFORCED" in ddl


# ---------------------------------------------------------------------------
# CREATE VIEW
# ---------------------------------------------------------------------------

class TestCreateView:
    def test_lakehouse_view(self):
        ddl = generate_create_view("V_SALES", "SELECT * FROM SALES", TargetPlatform.LAKEHOUSE)
        assert "CREATE OR REPLACE VIEW" in ddl
        assert "V_SALES" in ddl

    def test_warehouse_view(self):
        ddl = generate_create_view("V_SALES", "SELECT * FROM SALES", TargetPlatform.WAREHOUSE)
        assert "CREATE VIEW" in ddl
        assert "DROP VIEW" in ddl


# ---------------------------------------------------------------------------
# Batch script
# ---------------------------------------------------------------------------

class TestDDLScript:
    def test_generates_multi_table_script(self):
        tables = [
            {"name": "TABLE_A", "columns": [{"name": "ID", "data_type": "NUMBER(5,0)"}]},
            {"name": "TABLE_B", "columns": [{"name": "NAME", "data_type": "VARCHAR2(100)"}]},
        ]
        script = generate_ddl_script(tables, TargetPlatform.LAKEHOUSE)
        assert "TABLE_A" in script
        assert "TABLE_B" in script
        assert script.count("CREATE TABLE") == 2

    def test_empty_list(self):
        script = generate_ddl_script([], TargetPlatform.LAKEHOUSE)
        assert "Tables: 0" in script
