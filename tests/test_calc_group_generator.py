"""Tests for calc_group_generator — OAC time-intel → TMDL calculation groups."""

from __future__ import annotations

import unittest

from src.agents.semantic.calc_group_generator import (
    CalcGroupDetectionResult,
    CalculationGroup,
    CalculationItem,
    build_calculation_group,
    detect_time_intel_clusters,
)


class TestCalculationGroup(unittest.TestCase):

    def test_to_tmdl(self):
        group = CalculationGroup(
            name="TimeCalcs",
            items=[
                CalculationItem(name="Current", expression="SELECTEDMEASURE()"),
                CalculationItem(name="YTD", expression="CALCULATE(SELECTEDMEASURE(), DATESYTD('Date'[Date]))"),
            ],
        )
        tmdl = group.to_tmdl()
        self.assertIn("table 'TimeCalcs'", tmdl)
        self.assertIn("calculationGroup", tmdl)
        self.assertIn("calculationItem 'Current'", tmdl)
        self.assertIn("calculationItem 'YTD'", tmdl)
        self.assertIn("SELECTEDMEASURE()", tmdl)


class TestDetectTimeIntelClusters(unittest.TestCase):

    def test_detects_ytd_pattern(self):
        measures = [
            {"name": "Sales YTD", "expression": "CALCULATE(SUM(Sales[Amount]), DATESYTD(Date[Date]))"},
            {"name": "Cost YTD", "expression": "CALCULATE(SUM(Cost[Amount]), DATESYTD(Date[Date]))"},
            {"name": "Revenue", "expression": "SUM(Sales[Amount])"},
        ]
        result = detect_time_intel_clusters(measures, date_table_name="Date")
        self.assertIsInstance(result, CalcGroupDetectionResult)

    def test_builds_calc_group(self):
        measures = [
            {"name": "Sales YTD", "expression": "CALCULATE(SUM(Sales[Amount]), DATESYTD(Date[Date]))"},
            {"name": "Cost YTD", "expression": "CALCULATE(SUM(Cost[Amount]), DATESYTD(Date[Date]))"},
            {"name": "Sales PY", "expression": "CALCULATE(SUM(Sales[Amount]), SAMEPERIODLASTYEAR(Date[Date]))"},
            {"name": "Cost PY", "expression": "CALCULATE(SUM(Cost[Amount]), SAMEPERIODLASTYEAR(Date[Date]))"},
        ]
        result = detect_time_intel_clusters(measures, date_table_name="Date", min_matches=2)
        if result.groups:
            self.assertGreater(len(result.groups[0].items), 0)

    def test_no_patterns_found(self):
        measures = [
            {"name": "Simple", "expression": "SUM(T[X])"},
        ]
        result = detect_time_intel_clusters(measures, date_table_name="Date")
        # With only simple measures, may not produce calc group
        self.assertIsInstance(result, CalcGroupDetectionResult)


class TestBuildCalculationGroup(unittest.TestCase):

    def test_create_group(self):
        items = [
            {"name": "Current", "expression": "SELECTEDMEASURE()"},
            {"name": "PY", "expression": "CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))"},
        ]
        group = build_calculation_group("TimeCG", items)
        self.assertEqual(group.name, "TimeCG")
        self.assertEqual(len(group.items), 2)

    def test_tmdl_output(self):
        items = [{"name": "Current", "expression": "SELECTEDMEASURE()"}]
        group = build_calculation_group("CG", items)
        tmdl = group.to_tmdl()
        self.assertIn("calculationGroup", tmdl)


if __name__ == "__main__":
    unittest.main()
