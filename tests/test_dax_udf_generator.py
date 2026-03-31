"""Tests for dax_udf_generator — complex expressions → DAX UDFs."""

from __future__ import annotations

import unittest

from src.agents.semantic.dax_udf_generator import (
    DAXParameter,
    DAXUserDefinedFunction,
    UDFGenerationResult,
    generate_udfs,
)


class TestDAXUserDefinedFunction(unittest.TestCase):

    def test_to_dax(self):
        udf = DAXUserDefinedFunction(
            name="CalcMargin",
            parameters=[
                DAXParameter(name="Revenue", type_hint="Scalar"),
                DAXParameter(name="Cost", type_hint="Scalar"),
            ],
            body="DIVIDE(Revenue - Cost, Revenue)",
            description="Calculate profit margin",
        )
        dax = udf.to_dax()
        self.assertIn("DEFINE FUNCTION", dax)
        self.assertIn("CalcMargin", dax)
        self.assertIn("Revenue", dax)
        self.assertIn("DIVIDE", dax)

    def test_to_tmdl(self):
        udf = DAXUserDefinedFunction(
            name="MyFunc",
            parameters=[],
            body="42",
        )
        tmdl = udf.to_tmdl()
        self.assertIn("MyFunc", tmdl)


class TestGenerateUDFs(unittest.TestCase):

    def test_detects_complex_measures(self):
        measures = [
            {
                "name": "ComplexCalc",
                "expression": """
                    CALCULATE(
                        SUMX(
                            FILTER(Sales, Sales[Status] = "Active"),
                            Sales[Amount] * Sales[Qty]
                        ),
                        USERELATIONSHIP(Sales[OrderDate], Date[Date])
                    )
                """,
                "confidence": 0.5,
            },
        ]
        result = generate_udfs(measures, confidence_threshold=0.7)
        self.assertIsInstance(result, UDFGenerationResult)

    def test_high_confidence_not_extracted(self):
        measures = [
            {
                "name": "Simple",
                "expression": "SUM(Sales[Amount])",
                "confidence": 0.99,
            },
        ]
        result = generate_udfs(measures, confidence_threshold=0.7)
        self.assertEqual(len(result.udfs), 0)

    def test_empty_measures(self):
        result = generate_udfs([])
        self.assertEqual(len(result.udfs), 0)

    def test_nested_calculate_pattern(self):
        measures = [
            {
                "name": "NestedCalc",
                "expression": "CALCULATE(CALCULATE(SUM(T[X]), T[A] = 1), T[B] = 2)",
                "confidence": 0.6,
            },
        ]
        result = generate_udfs(measures, confidence_threshold=0.7)
        # Should detect nested CALCULATE
        self.assertIsInstance(result, UDFGenerationResult)


if __name__ == "__main__":
    unittest.main()
