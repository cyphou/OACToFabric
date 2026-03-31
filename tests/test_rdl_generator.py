"""Tests for rdl_generator — RDL XML generation for Paginated Reports."""

from __future__ import annotations

import unittest

from src.agents.report.bip_parser import (
    BIPDataSet,
    BIPLayoutRegion,
    BIPParameter,
    BIPReportDefinition,
)
from src.agents.report.rdl_generator import (
    RDLGenerationResult,
    generate_rdl,
)


class TestGenerateRDL(unittest.TestCase):

    def _make_report(self, **kwargs) -> BIPReportDefinition:
        defaults = {
            "name": "Test",
            "data_sets": [BIPDataSet(name="DS1", sql_query="SELECT 1", data_source="Src")],
            "parameters": [],
            "layout_regions": [BIPLayoutRegion(region_type="detail", fields=["col1"])],
        }
        defaults.update(kwargs)
        return BIPReportDefinition(**defaults)

    def test_basic_rdl_generation(self):
        report = self._make_report()
        result = generate_rdl(report)
        self.assertEqual(result.report_name, "Test")
        self.assertIn("<Report", result.rdl_xml)
        self.assertIn("DS1", result.rdl_xml)
        self.assertEqual(result.data_source_count, 1)
        self.assertEqual(result.data_set_count, 1)

    def test_parameters_rendered(self):
        report = self._make_report(
            parameters=[BIPParameter(name="Region", data_type="string", prompt="Select Region")]
        )
        result = generate_rdl(report)
        self.assertEqual(result.parameter_count, 1)
        self.assertIn("Region", result.rdl_xml)

    def test_group_region(self):
        report = self._make_report(
            layout_regions=[BIPLayoutRegion(
                region_type="group", fields=["Sales", "Region"], group_by="Region"
            )]
        )
        result = generate_rdl(report)
        self.assertIn("Group_Region", result.rdl_xml)

    def test_sort_region(self):
        report = self._make_report(
            layout_regions=[BIPLayoutRegion(
                region_type="detail", fields=["Amount"], sort_by="Amount"
            )]
        )
        result = generate_rdl(report)
        self.assertIn("SortExpression", result.rdl_xml)

    def test_chart_region(self):
        report = self._make_report(
            layout_regions=[BIPLayoutRegion(region_type="chart", fields=["Revenue"])]
        )
        result = generate_rdl(report)
        self.assertIn("Chart", result.rdl_xml)

    def test_empty_datasets(self):
        report = self._make_report(data_sets=[])
        result = generate_rdl(report)
        self.assertEqual(result.data_set_count, 0)

    def test_page_settings(self):
        report = self._make_report(page_width="11in", page_height="8.5in")
        result = generate_rdl(report)
        self.assertIn("11in", result.rdl_xml)
        self.assertIn("8.5in", result.rdl_xml)

    def test_duplicate_params_deduplicated(self):
        params = [
            BIPParameter(name="P1"),
            BIPParameter(name="P1"),
            BIPParameter(name="P2"),
        ]
        report = self._make_report(parameters=params)
        result = generate_rdl(report)
        self.assertEqual(result.parameter_count, 2)

    def test_data_type_mapping(self):
        report = self._make_report(
            parameters=[BIPParameter(name="Dt", data_type="date")]
        )
        result = generate_rdl(report)
        self.assertIn("DateTime", result.rdl_xml)


if __name__ == "__main__":
    unittest.main()
