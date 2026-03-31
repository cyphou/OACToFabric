"""Tests for bip_parser — BI Publisher report definition parser."""

from __future__ import annotations

import unittest

from src.agents.report.bip_parser import (
    BIPDataSet,
    BIPLayoutRegion,
    BIPParameter,
    BIPReportDefinition,
    parse_bip_data_model,
    parse_bip_report,
    parse_bip_rtf_template,
)


class TestParseBIPDataModel(unittest.TestCase):

    def test_empty_xml(self):
        result = parse_bip_data_model("<root/>")
        self.assertEqual(result, [])

    def test_dataset_with_sql(self):
        xml = """
        <dataModel>
            <dataSet name="Sales">
                <sqlQuery>SELECT * FROM orders WHERE region = :REGION</sqlQuery>
            </dataSet>
        </dataModel>
        """
        result = parse_bip_data_model(xml)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Sales")
        self.assertIn("SELECT * FROM orders", result[0].sql_query)
        self.assertEqual(len(result[0].parameters), 1)
        self.assertEqual(result[0].parameters[0].name, "REGION")

    def test_dataset_with_explicit_params(self):
        xml = """
        <dataModel>
            <dataSet name="Report1">
                <sql>SELECT 1</sql>
                <parameter name="p1" dataType="integer" defaultValue="10" />
            </dataSet>
        </dataModel>
        """
        result = parse_bip_data_model(xml)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].parameters), 1)
        self.assertEqual(result[0].parameters[0].name, "p1")
        self.assertEqual(result[0].parameters[0].data_type, "integer")

    def test_invalid_xml_returns_empty(self):
        result = parse_bip_data_model("not xml at all")
        self.assertEqual(result, [])

    def test_no_sql_dataset_skipped(self):
        xml = "<dataModel><dataSet name='Empty'></dataSet></dataModel>"
        result = parse_bip_data_model(xml)
        self.assertEqual(result, [])


class TestParseBIPRTFTemplate(unittest.TestCase):

    def test_fields_extracted(self):
        rtf = "Report {OrderID} {CustomerName} {Total}"
        regions = parse_bip_rtf_template(rtf)
        self.assertEqual(len(regions), 1)
        self.assertIn("OrderID", regions[0].fields)
        self.assertIn("CustomerName", regions[0].fields)
        self.assertEqual(regions[0].region_type, "detail")

    def test_group_detected(self):
        rtf = "<?for-each: Region?>{Sales}{Region}<?end for-each?>"
        regions = parse_bip_rtf_template(rtf)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].region_type, "group")
        self.assertEqual(regions[0].group_by, "Region")

    def test_sort_detected(self):
        rtf = "<?sort: Amount?>{Amount}{Name}"
        regions = parse_bip_rtf_template(rtf)
        self.assertEqual(regions[0].sort_by, "Amount")

    def test_no_fields_returns_placeholder(self):
        rtf = "Just some plain text"
        regions = parse_bip_rtf_template(rtf)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].fields, ["(no fields detected)"])


class TestParseBIPReport(unittest.TestCase):

    def test_full_report_parsing(self):
        xml = """<dataModel><dataSet name="D1"><sql>SELECT id FROM t</sql></dataSet></dataModel>"""
        rtf = "{id} {name}"
        report = parse_bip_report("TestReport", data_model_xml=xml, rtf_template=rtf)
        self.assertEqual(report.name, "TestReport")
        self.assertGreater(len(report.data_sets), 0)
        self.assertGreater(len(report.layout_regions), 0)

    def test_no_data_model_warning(self):
        report = parse_bip_report("Empty", rtf_template="{x}")
        self.assertTrue(any("No data model" in w for w in report.warnings))

    def test_no_template_warning(self):
        report = parse_bip_report("NoTemplate", data_model_xml="<root/>")
        self.assertTrue(any("No RTF template" in w for w in report.warnings))

    def test_both_missing(self):
        report = parse_bip_report("Bare")
        self.assertEqual(len(report.warnings), 2)


if __name__ == "__main__":
    unittest.main()
