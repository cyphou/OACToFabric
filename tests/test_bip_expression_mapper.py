"""Tests for bip_expression_mapper — BIP XPath → RDL expression mapping."""

from __future__ import annotations

import unittest

from src.agents.report.bip_expression_mapper import (
    ExpressionMappingResult,
    map_all_expressions,
    map_bip_expression,
    map_bip_format,
)


class TestMapBIPExpression(unittest.TestCase):

    def test_empty_expression(self):
        r = map_bip_expression("")
        self.assertEqual(r.rdl_expression, "")
        self.assertEqual(r.confidence, 1.0)

    def test_field_reference(self):
        r = map_bip_expression("{OrderID}")
        self.assertIn("Fields!OrderID.Value", r.rdl_expression)
        self.assertEqual(r.confidence, 1.0)

    def test_nested_field_reference(self):
        r = map_bip_expression("{Order.Total}")
        self.assertIn("Fields!Order_Total.Value", r.rdl_expression)

    def test_sum_aggregate(self):
        r = map_bip_expression("sum(Amount)")
        self.assertIn("Sum(Fields!Amount.Value)", r.rdl_expression)
        self.assertGreaterEqual(r.confidence, 0.9)

    def test_count_aggregate(self):
        r = map_bip_expression("count(OrderID)")
        self.assertIn("Count(Fields!OrderID.Value)", r.rdl_expression)

    def test_avg_aggregate(self):
        r = map_bip_expression("avg(Price)")
        self.assertIn("Avg(Fields!Price.Value)", r.rdl_expression)

    def test_conditional_if_then_else(self):
        r = map_bip_expression("if {Status} then 'Active' else 'Inactive'")
        self.assertIn("IIF", r.rdl_expression)
        self.assertGreaterEqual(r.confidence, 0.5)

    def test_numeric_literal(self):
        r = map_bip_expression("42.5")
        self.assertEqual(r.rdl_expression, "=42.5")

    def test_string_literal(self):
        r = map_bip_expression("'hello'")
        self.assertEqual(r.rdl_expression, "='hello'")


class TestMapBIPFormat(unittest.TestCase):

    def test_number_format(self):
        self.assertEqual(map_bip_format("#,##0.00"), "#,##0.00")

    def test_date_format_mdy(self):
        self.assertEqual(map_bip_format("MM/DD/YYYY"), "MM/dd/yyyy")

    def test_date_format_ymd(self):
        self.assertEqual(map_bip_format("YYYY-MM-DD"), "yyyy-MM-dd")

    def test_empty_format(self):
        self.assertEqual(map_bip_format(""), "")

    def test_unknown_format_passthrough(self):
        self.assertEqual(map_bip_format("CUSTOM_FMT"), "CUSTOM_FMT")

    def test_currency(self):
        self.assertEqual(map_bip_format("$#,##0.00"), "$#,##0.00")


class TestMapAllExpressions(unittest.TestCase):

    def test_batch(self):
        exprs = ["{A}", "sum(B)", ""]
        results = map_all_expressions(exprs)
        self.assertEqual(len(results), 3)

    def test_empty_batch(self):
        results = map_all_expressions([])
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
