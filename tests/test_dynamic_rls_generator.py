"""Tests for dynamic_rls_generator — advanced dynamic row-level security."""

from __future__ import annotations

import unittest

from src.agents.security.dynamic_rls_generator import (
    DynamicRLSResult,
    DynamicRLSRule,
    OACSessionFilter,
    generate_dynamic_rls,
)


class TestGenerateDynamicRLS(unittest.TestCase):

    def test_simple_equals_filter(self):
        filters = [
            OACSessionFilter(
                variable_name="NQ_SESSION.REGION",
                target_table="Sales",
                target_column="Region",
                filter_type="equals",
            )
        ]
        result = generate_dynamic_rls(filters)
        self.assertEqual(len(result.roles), 1)
        self.assertIn("LOOKUPVALUE", result.roles[0].dax_filter)
        self.assertIn("USERPRINCIPALNAME", result.roles[0].dax_filter)
        self.assertEqual(result.roles[0].confidence, 1.0)

    def test_in_list_filter(self):
        filters = [
            OACSessionFilter(
                variable_name="NQ_SESSION.DEPARTMENTS",
                target_table="HR",
                target_column="DeptCode",
                filter_type="in_list",
            )
        ]
        result = generate_dynamic_rls(filters)
        self.assertIn("PATHCONTAINS", result.roles[0].dax_filter)
        self.assertGreaterEqual(result.roles[0].confidence, 0.9)

    def test_hierarchy_filter(self):
        filters = [
            OACSessionFilter(
                variable_name="NQ_SESSION.ORG",
                target_table="Employees",
                target_column="EmpId",
                filter_type="hierarchy",
                hierarchy_column="OrgPath",
            )
        ]
        result = generate_dynamic_rls(filters)
        self.assertIn("PATHCONTAINS", result.roles[0].dax_filter)
        self.assertGreaterEqual(result.roles[0].confidence, 0.8)

    def test_hierarchy_missing_column_fallback(self):
        filters = [
            OACSessionFilter(
                variable_name="NQ_SESSION.ORG",
                target_table="T",
                target_column="C",
                filter_type="hierarchy",
            )
        ]
        result = generate_dynamic_rls(filters)
        self.assertLess(result.roles[0].confidence, 0.8)
        self.assertGreater(len(result.warnings), 0)

    def test_time_range_filter(self):
        filters = [
            OACSessionFilter(
                variable_name="NQ_SESSION.ACCESS_PERIOD",
                target_table="Data",
                target_column="Date",
                filter_type="time_range",
                time_start_column="AccessStart",
                time_end_column="AccessEnd",
            )
        ]
        result = generate_dynamic_rls(filters)
        self.assertIn("TODAY()", result.roles[0].dax_filter)
        self.assertGreaterEqual(result.roles[0].confidence, 0.9)

    def test_time_range_missing_columns(self):
        filters = [
            OACSessionFilter(
                variable_name="NQ_SESSION.PERIOD",
                target_table="T",
                target_column="D",
                filter_type="time_range",
            )
        ]
        result = generate_dynamic_rls(filters)
        self.assertLess(result.roles[0].confidence, 0.7)

    def test_lookup_table_generated(self):
        filters = [
            OACSessionFilter(
                variable_name="NQ_SESSION.REGION",
                target_table="Sales",
                target_column="Region",
            )
        ]
        result = generate_dynamic_rls(filters)
        self.assertIn("SecurityAccess", result.lookup_table_tmdl)
        self.assertIn("UserPrincipal", result.lookup_table_tmdl)
        self.assertIn("REGION", result.lookup_table_tmdl)
        self.assertIn("CREATE TABLE", result.lookup_table_ddl)

    def test_roles_tmdl(self):
        filters = [
            OACSessionFilter(
                variable_name="NQ_SESSION.REGION",
                target_table="Sales",
                target_column="Region",
            )
        ]
        result = generate_dynamic_rls(filters, role_name="RegionalAccess")
        self.assertIn("role 'RegionalAccess'", result.tmdl_roles_section)
        self.assertIn("tablePermission 'Sales'", result.tmdl_roles_section)

    def test_multiple_filters(self):
        filters = [
            OACSessionFilter(variable_name="NQ_SESSION.REGION", target_table="Sales", target_column="Region"),
            OACSessionFilter(variable_name="NQ_SESSION.DEPT", target_table="HR", target_column="Dept"),
        ]
        result = generate_dynamic_rls(filters)
        self.assertEqual(len(result.roles), 2)

    def test_variable_deduplication(self):
        filters = [
            OACSessionFilter(variable_name="NQ_SESSION.REGION", target_table="Sales", target_column="Region"),
            OACSessionFilter(variable_name="NQ_SESSION.REGION", target_table="Returns", target_column="Region"),
        ]
        result = generate_dynamic_rls(filters)
        # REGION should appear only once in lookup table
        self.assertEqual(result.lookup_table_tmdl.count("column 'REGION'"), 1)

    def test_empty_filters(self):
        result = generate_dynamic_rls([])
        self.assertEqual(len(result.roles), 0)
        self.assertEqual(result.lookup_table_tmdl, "")


if __name__ == "__main__":
    unittest.main()
