"""Tests for fabric_naming and lakehouse_generator modules."""

from __future__ import annotations

import json

import pytest

from src.agents.schema.fabric_naming import (
    sanitize_column_name,
    sanitize_schema_name,
    sanitize_table_name,
    to_pascal_case,
    to_snake_case,
)
from src.agents.schema.lakehouse_generator import (
    SPARK_TYPE_MAP,
    LakehouseColumn,
    LakehouseDefinition,
    LakehouseTable,
    build_lakehouse_definition,
    generate_ddl_script,
    generate_lakehouse_definition_json,
    generate_table_metadata_json,
    map_to_spark_type,
)


# ---------------------------------------------------------------------------
# fabric_naming
# ---------------------------------------------------------------------------

class TestSanitizeTableName:
    def test_strips_brackets(self):
        assert sanitize_table_name("[Sales]") == "sales"

    def test_strips_oac_prefix(self):
        assert sanitize_table_name("v_customer_orders") == "customer_orders"
        assert sanitize_table_name("tbl_products") == "products"
        assert sanitize_table_name("f_revenue") == "revenue"
        assert sanitize_table_name("d_date") == "date"

    def test_keeps_prefix_when_disabled(self):
        assert sanitize_table_name("v_sales", strip_oac_prefix=False) == "v_sales"

    def test_replaces_special_chars(self):
        assert sanitize_table_name("Order Details!@#") == "order_details"

    def test_collapses_underscores(self):
        assert sanitize_table_name("sales___data") == "sales_data"

    def test_strips_leading_digits(self):
        assert sanitize_table_name("123_items") == "items"

    def test_empty_returns_table(self):
        assert sanitize_table_name("") == "table"
        assert sanitize_table_name("!!!") == "table"

    def test_lowercase(self):
        assert sanitize_table_name("MyTable") == "mytable"


class TestSanitizeColumnName:
    def test_mixed_case_preserved(self):
        result = sanitize_column_name("OrderDate")
        assert result == "OrderDate"

    def test_strips_brackets(self):
        assert sanitize_column_name("[Amount]") == "Amount"

    def test_empty_returns_column(self):
        assert sanitize_column_name("") == "column"


class TestSanitizeSchemaName:
    def test_basic(self):
        assert sanitize_schema_name("SalesDB") == "salesdb"

    def test_special_chars(self):
        assert sanitize_schema_name("my schema!") == "my_schema"

    def test_empty_returns_dbo(self):
        assert sanitize_schema_name("") == "dbo"


class TestNameConversions:
    def test_pascal_case(self):
        assert to_pascal_case("order_date") == "OrderDate"
        assert to_pascal_case("customer-name") == "CustomerName"

    def test_snake_case(self):
        assert to_snake_case("OrderDate") == "order_date"
        assert to_snake_case("customerID") == "customer_id"


# ---------------------------------------------------------------------------
# lakehouse_generator
# ---------------------------------------------------------------------------

class TestMapToSparkType:
    def test_direct_match(self):
        assert map_to_spark_type("varchar2") == "STRING"
        assert map_to_spark_type("number") == "DECIMAL(19,4)"
        assert map_to_spark_type("date") == "DATE"
        assert map_to_spark_type("boolean") == "BOOLEAN"

    def test_strips_precision(self):
        assert map_to_spark_type("varchar2(100)") == "STRING"
        assert map_to_spark_type("NUMBER(10,2)") == "DECIMAL(19,4)"

    def test_fallback_to_string(self):
        assert map_to_spark_type("xml_type") == "STRING"

    def test_case_insensitive(self):
        assert map_to_spark_type("VARCHAR2") == "STRING"
        assert map_to_spark_type("Date") == "DATE"

    def test_coverage_of_common_types(self):
        for t in ("int", "bigint", "float", "double", "timestamp", "blob"):
            result = map_to_spark_type(t)
            assert result != "STRING" or t in ("blob",)  # blob→BINARY, not STRING


class TestBuildLakehouseDefinition:
    def test_simple_table(self):
        tables = [{
            "name": "v_customers",
            "columns": [
                {"name": "CustomerID", "data_type": "int"},
                {"name": "Name", "data_type": "varchar2"},
            ],
            "estimated_rows": 1000,
        }]
        defn = build_lakehouse_definition(tables)
        assert defn.table_count == 1
        assert defn.total_columns == 2
        assert defn.tables[0].name == "customers"  # v_ prefix stripped
        assert defn.tables[0].columns[0].spark_type == "INT"

    def test_multiple_tables(self):
        tables = [
            {"name": f"table_{i}", "columns": [{"name": "id", "data_type": "int"}]}
            for i in range(5)
        ]
        defn = build_lakehouse_definition(tables)
        assert defn.table_count == 5


class TestGenerateDDL:
    def test_basic_ddl(self):
        table = LakehouseTable(
            name="customers",
            original_name="v_customers",
            columns=[
                LakehouseColumn("id", "ID", "INT", False),
                LakehouseColumn("name", "Name", "STRING"),
            ],
        )
        ddl = generate_ddl_script(table)
        assert "CREATE TABLE IF NOT EXISTS customers" in ddl
        assert "id INT NOT NULL" in ddl
        assert "name STRING" in ddl
        assert "USING DELTA;" in ddl

    def test_partitioned_table(self):
        table = LakehouseTable(
            name="orders",
            original_name="orders",
            columns=[LakehouseColumn("order_date", "order_date", "DATE")],
            partition_columns=["order_date"],
        )
        ddl = generate_ddl_script(table)
        assert "PARTITIONED BY (order_date)" in ddl


class TestGenerateJSON:
    def test_definition_json(self):
        defn = LakehouseDefinition(
            tables=[LakehouseTable(
                name="test",
                original_name="test",
                columns=[LakehouseColumn("id", "id", "INT")],
            )],
            lakehouse_name="TestLH",
        )
        result = json.loads(generate_lakehouse_definition_json(defn))
        assert result["lakehouseName"] == "TestLH"
        assert result["tableCount"] == 1
        assert len(result["tables"]) == 1

    def test_metadata_json(self):
        defn = LakehouseDefinition(
            tables=[LakehouseTable(name="t", original_name="t", columns=[], estimated_rows=500)],
        )
        result = json.loads(generate_table_metadata_json(defn))
        assert result["tableCount"] == 1
        assert result["tables"][0]["estimatedRows"] == 500
