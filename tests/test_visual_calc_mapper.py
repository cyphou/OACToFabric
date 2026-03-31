"""Tests for visual_calc_mapper — visual calculations and Fluent 2 themes."""

from __future__ import annotations

import unittest

from src.agents.report.visual_calc_mapper import (
    OACVisualCalc,
    PBIVisualCalc,
    VisualCalcResult,
    generate_fluent2_theme,
    map_all_visual_calcs,
    map_visual_calc,
)


class TestMapVisualCalc(unittest.TestCase):

    def test_running_sum(self):
        calc = OACVisualCalc(name="RunTotal", expression="RSUM(Sales)")
        result = map_visual_calc(calc)
        self.assertIn("RUNNINGSUM", result.expression)
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_running_avg(self):
        calc = OACVisualCalc(name="RunAvg", expression="RUNNING_AVG(Revenue)")
        result = map_visual_calc(calc)
        self.assertIn("MOVINGAVERAGE", result.expression)

    def test_rank(self):
        calc = OACVisualCalc(name="Ranking", expression="RANK(Sales)")
        result = map_visual_calc(calc)
        self.assertIn("RANK", result.expression)
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_pct_of_total(self):
        calc = OACVisualCalc(name="Pct", expression="PCT_OF_TOTAL(Revenue)")
        result = map_visual_calc(calc)
        self.assertIn("DIVIDE", result.expression)
        self.assertIn("COLLAPSE", result.expression)

    def test_moving_average(self):
        calc = OACVisualCalc(name="MA", expression="MAVG(Sales, 3)")
        result = map_visual_calc(calc)
        self.assertIn("MOVINGAVERAGE", result.expression)
        self.assertIn("3", result.expression)

    def test_unknown_expression_low_confidence(self):
        calc = OACVisualCalc(name="Custom", expression="SPECIAL_FUNC(X)")
        result = map_visual_calc(calc)
        self.assertLess(result.confidence, 0.8)
        if result.warning:
            self.assertIn("low confidence", result.warning.lower())

    def test_data_type_mapping(self):
        calc = OACVisualCalc(name="D", expression="RSUM(X)", data_type="integer")
        result = map_visual_calc(calc)
        self.assertEqual(result.data_type, "Int64")

    def test_to_visual_json(self):
        pbi = PBIVisualCalc(name="V1", expression="RUNNINGSUM(Sales)", data_type="Double")
        j = pbi.to_visual_json()
        self.assertEqual(j["name"], "V1")
        self.assertEqual(j["expression"], "RUNNINGSUM(Sales)")


class TestMapAllVisualCalcs(unittest.TestCase):

    def test_multiple_calcs(self):
        calcs = [
            OACVisualCalc(name="RC", expression="RCOUNT(Id)"),
            OACVisualCalc(name="RS", expression="RSUM(Amount)"),
            OACVisualCalc(name="UK", expression="UNKNOWN(X)"),
        ]
        result = map_all_visual_calcs(calcs)
        self.assertEqual(len(result.calculations), 3)
        self.assertGreater(result.high_confidence_count, 0)

    def test_empty(self):
        result = map_all_visual_calcs([])
        self.assertEqual(len(result.calculations), 0)


class TestFluent2Theme(unittest.TestCase):

    def test_theme_structure(self):
        theme = generate_fluent2_theme()
        self.assertEqual(theme["name"], "Fluent2Modern")
        self.assertIn("dataColors", theme)
        self.assertEqual(len(theme["dataColors"]), 10)
        self.assertIn("visualStyles", theme)
        self.assertIn("textClasses", theme)

    def test_theme_colors_are_hex(self):
        theme = generate_fluent2_theme()
        for color in theme["dataColors"]:
            self.assertTrue(color.startswith("#"))


if __name__ == "__main__":
    unittest.main()
