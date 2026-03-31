"""Tests for direct_lake_generator — Direct Lake TMDL generation."""

from __future__ import annotations

import unittest

from src.agents.semantic.direct_lake_generator import (
    DirectLakeConfig,
    DirectLakeColumnMap,
    DirectLakeResult,
    DirectLakeTableConfig,
    generate_direct_lake_config,
    generate_direct_lake_tmdl,
)


class TestDirectLakeConfig(unittest.TestCase):

    def test_model_section_tmdl(self):
        config = DirectLakeConfig(
            model_name="TestModel",
            lakehouse_name="LH1",
            fallback_mode="DirectQuery",
        )
        tmdl = config.to_tmdl_model_section()
        self.assertIn("model Model", tmdl)
        self.assertIn("DirectLakeFallback", tmdl)
        self.assertIn("DirectQuery", tmdl)


class TestGenerateDirectLakeConfig(unittest.TestCase):

    def test_basic_config(self):
        tables = [
            {
                "name": "Sales",
                "entity_name": "sales_delta",
                "columns": [
                    {"name": "Id", "data_type": "Int64", "is_key": True},
                    {"name": "Amount", "data_type": "Double"},
                ],
            },
        ]
        config = generate_direct_lake_config(
            model_name="Model1",
            tables=tables,
            lakehouse_name="LH1",
        )
        self.assertEqual(config.model_name, "Model1")
        self.assertEqual(len(config.tables), 1)
        self.assertEqual(config.tables[0].entity_name, "sales_delta")
        self.assertEqual(len(config.tables[0].columns), 2)
        self.assertTrue(config.tables[0].columns[0].is_key)

    def test_fallback_mode(self):
        config = generate_direct_lake_config(
            model_name="M", tables=[], lakehouse_name="L",
            fallback_mode="Import",
        )
        self.assertEqual(config.fallback_mode, "Import")


class TestGenerateDirectLakeTMDL(unittest.TestCase):

    def test_tmdl_generation(self):
        config = DirectLakeConfig(
            model_name="Model1",
            lakehouse_name="MyLH",
            lakehouse_id="abc-123",
            tables=[
                DirectLakeTableConfig(
                    table_name="Customers",
                    entity_name="customers",
                    columns=[
                        DirectLakeColumnMap(model_column="CustId", delta_column="customer_id", data_type="Int64", is_key=True),
                        DirectLakeColumnMap(model_column="Name", delta_column="customer_name", data_type="String"),
                    ],
                ),
            ],
        )
        result = generate_direct_lake_tmdl(config)
        self.assertEqual(result.table_count, 1)
        self.assertIn("Customers", result.table_tmdl_snippets)
        tmdl = result.table_tmdl_snippets["Customers"]
        self.assertIn("table 'Customers'", tmdl)
        self.assertIn("entityName = 'customers'", tmdl)
        self.assertIn("isKey = true", tmdl)

    def test_expression_tmdl(self):
        config = DirectLakeConfig(
            model_name="M",
            lakehouse_name="LH",
            lakehouse_id="id-1",
            tables=[],
        )
        result = generate_direct_lake_tmdl(config)
        self.assertIn("DatabaseQuery", result.expression_tmdl)
        self.assertIn("LH", result.expression_tmdl)
        self.assertIn("id-1", result.expression_tmdl)

    def test_model_tmdl(self):
        config = DirectLakeConfig(model_name="M", lakehouse_name="LH", fallback_mode="Automatic")
        result = generate_direct_lake_tmdl(config)
        self.assertIn("model Model", result.model_tmdl)

    def test_empty_tables(self):
        config = DirectLakeConfig(model_name="M", lakehouse_name="LH")
        result = generate_direct_lake_tmdl(config)
        self.assertEqual(result.table_count, 0)
        self.assertEqual(len(result.table_tmdl_snippets), 0)


if __name__ == "__main__":
    unittest.main()
