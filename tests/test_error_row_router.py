"""Tests for error_row_router — ETL error routing to quarantine."""

from __future__ import annotations

import unittest

from src.agents.etl.error_row_router import (
    ErrorRoutingConfig,
    ErrorRoutingResult,
    ErrorRule,
    QuarantineTableDef,
    generate_default_rules,
    generate_error_routing,
)


class TestQuarantineTableDef(unittest.TestCase):

    def test_ddl_generation(self):
        qt = QuarantineTableDef(table_name="orders_quarantine", source_table="orders")
        ddl = qt.to_ddl()
        self.assertIn("CREATE TABLE", ddl)
        self.assertIn("orders_quarantine", ddl)
        self.assertIn("error_rule", ddl)
        self.assertIn("USING DELTA", ddl)


class TestErrorRoutingConfig(unittest.TestCase):

    def test_auto_quarantine_name(self):
        config = ErrorRoutingConfig(source_table="sales")
        self.assertEqual(config.quarantine_table, "sales_quarantine")

    def test_explicit_quarantine_name(self):
        config = ErrorRoutingConfig(source_table="sales", quarantine_table="my_quarantine")
        self.assertEqual(config.quarantine_table, "my_quarantine")


class TestGenerateErrorRouting(unittest.TestCase):

    def test_basic_routing(self):
        config = ErrorRoutingConfig(
            source_table="orders",
            rules=[
                ErrorRule(rule_name="not_null_id", rule_type="schema", column="order_id"),
                ErrorRule(rule_name="valid_amount", rule_type="transform", column="amount",
                         condition="F.col('amount').cast('double').isNull()"),
            ],
        )
        result = generate_error_routing(config)
        self.assertIn("# Error routing for orders", result.pyspark_code)
        self.assertIn("not_null_id", result.pyspark_code)
        self.assertIn("valid_amount", result.pyspark_code)
        self.assertIn("CREATE TABLE", result.quarantine_ddl)
        self.assertEqual(result.rule_count, 2)
        self.assertEqual(result.pipeline_json["name"], "ErrorRoute_orders")

    def test_no_rules(self):
        config = ErrorRoutingConfig(source_table="empty")
        result = generate_error_routing(config)
        self.assertEqual(result.rule_count, 0)
        self.assertIn("# Error routing for empty", result.pyspark_code)

    def test_continue_on_error_flag(self):
        config = ErrorRoutingConfig(
            source_table="t",
            rules=[ErrorRule(rule_name="r", rule_type="schema", column="c")],
            continue_on_error=False,
            max_error_pct=3.0,
        )
        result = generate_error_routing(config)
        self.assertIn("exceeds threshold", result.pyspark_code)


class TestGenerateDefaultRules(unittest.TestCase):

    def test_not_null_rules(self):
        config = generate_default_rules("orders", not_null_columns=["id", "date"])
        self.assertEqual(len(config.rules), 2)
        self.assertTrue(all(r.rule_type == "schema" for r in config.rules))

    def test_numeric_rules(self):
        config = generate_default_rules("sales", numeric_columns=["amount", "qty"])
        self.assertEqual(len(config.rules), 2)
        self.assertTrue(all(r.rule_type == "transform" for r in config.rules))

    def test_combined_rules(self):
        config = generate_default_rules(
            "t", not_null_columns=["id"], numeric_columns=["val"]
        )
        self.assertEqual(len(config.rules), 2)

    def test_empty_rules(self):
        config = generate_default_rules("t")
        self.assertEqual(len(config.rules), 0)


if __name__ == "__main__":
    unittest.main()
