"""Tests for RLS converter — TMDL role generation, init-block analysis, test plans."""

from __future__ import annotations

import pytest

from src.agents.security.rls_converter import (
    LookupColumn,
    RLSTestCase,
    SecurityLookupTable,
    analyse_init_blocks,
    generate_lookup_table_ddl,
    generate_lookup_table_tmdl,
    generate_rls_test_plan,
    render_roles_tmdl,
    render_test_plan_markdown,
)
from src.agents.security.role_mapper import RLSRoleDefinition, RLSTablePermission


# ---------------------------------------------------------------------------
# Init-block analysis
# ---------------------------------------------------------------------------


class TestAnalyseInitBlocks:
    def test_single_init_block(self):
        blocks = [
            {
                "name": "set_region",
                "sql": "SELECT region FROM user_access WHERE user_id = :user",
                "variables": ["REGION"],
            },
        ]
        tables = analyse_init_blocks(blocks)
        assert len(tables) == 1
        t = tables[0]
        assert t.table_name == "Security_UserAccess"
        col_names = [c.name for c in t.columns]
        assert "UserEmail" in col_names
        assert "REGION" in col_names

    def test_multiple_init_blocks_merged(self):
        blocks = [
            {"name": "b1", "sql": "SELECT ...", "variables": ["REGION"]},
            {"name": "b2", "sql": "SELECT ...", "variables": ["DEPARTMENT"]},
        ]
        tables = analyse_init_blocks(blocks)
        assert len(tables) == 1
        col_names = [c.name for c in tables[0].columns]
        assert "REGION" in col_names
        assert "DEPARTMENT" in col_names

    def test_complex_sql_warns(self):
        blocks = [
            {
                "name": "dynamic",
                "sql": "BEGIN EXECUTE IMMEDIATE 'SELECT ...' INTO :var; END;",
                "variables": ["VAR"],
            },
        ]
        tables = analyse_init_blocks(blocks)
        assert len(tables[0].warnings) > 0
        assert any("complex" in w.lower() for w in tables[0].warnings)

    def test_empty_blocks(self):
        assert analyse_init_blocks([]) == []

    def test_duplicate_variables_deduped(self):
        blocks = [
            {"name": "b1", "sql": "", "variables": ["REGION"]},
            {"name": "b2", "sql": "", "variables": ["REGION"]},
        ]
        tables = analyse_init_blocks(blocks)
        # REGION should appear only once (plus UserEmail)
        col_names = [c.name for c in tables[0].columns]
        assert col_names.count("REGION") == 1


# ---------------------------------------------------------------------------
# Lookup table DDL
# ---------------------------------------------------------------------------


class TestGenerateLookupTableDDL:
    def test_basic(self):
        table = SecurityLookupTable(
            table_name="Security_UserAccess",
            columns=[
                LookupColumn(name="UserEmail", data_type="VARCHAR(256)"),
                LookupColumn(name="Region", data_type="VARCHAR(100)"),
            ],
        )
        ddl = generate_lookup_table_ddl(table)
        assert "CREATE TABLE Security_UserAccess" in ddl
        assert "UserEmail" in ddl
        assert "Region" in ddl


# ---------------------------------------------------------------------------
# Lookup table TMDL
# ---------------------------------------------------------------------------


class TestGenerateLookupTableTMDL:
    def test_basic(self):
        table = SecurityLookupTable(
            table_name="Security_UserAccess",
            columns=[
                LookupColumn(name="UserEmail"),
                LookupColumn(name="Region"),
            ],
        )
        tmdl = generate_lookup_table_tmdl(table)
        assert "table 'Security_UserAccess'" in tmdl
        assert "column 'UserEmail'" in tmdl
        assert "column 'Region'" in tmdl
        assert "dataType: string" in tmdl


# ---------------------------------------------------------------------------
# TMDL role rendering
# ---------------------------------------------------------------------------


class TestRenderRolesTMDL:
    def test_single_role(self):
        roles = [
            RLSRoleDefinition(
                role_name="SalesViewer",
                description="View East sales only",
                table_permissions=[
                    RLSTablePermission(
                        table_name="Sales",
                        filter_expression='[Region] = "East"',
                    ),
                ],
            ),
        ]
        tmdl = render_roles_tmdl(roles)
        assert "role 'SalesViewer'" in tmdl
        assert "modelPermission: read" in tmdl
        assert "tablePermission 'Sales'" in tmdl
        assert '[Region] = "East"' in tmdl

    def test_multiple_roles(self):
        roles = [
            RLSRoleDefinition(
                role_name="R1",
                table_permissions=[
                    RLSTablePermission(table_name="T1", filter_expression="TRUE()"),
                ],
            ),
            RLSRoleDefinition(
                role_name="R2",
                table_permissions=[
                    RLSTablePermission(table_name="T2", filter_expression="TRUE()"),
                ],
            ),
        ]
        tmdl = render_roles_tmdl(roles)
        assert "role 'R1'" in tmdl
        assert "role 'R2'" in tmdl

    def test_with_lookup_table(self):
        lookup = SecurityLookupTable(
            table_name="Security_UserAccess",
            columns=[LookupColumn(name="UserEmail"), LookupColumn(name="Region")],
        )
        roles = [
            RLSRoleDefinition(
                role_name="Regional",
                table_permissions=[
                    RLSTablePermission(table_name="Sales", filter_expression="..."),
                ],
            ),
        ]
        tmdl = render_roles_tmdl(roles, lookup_tables=[lookup])
        assert "table 'Security_UserAccess'" in tmdl
        assert "role 'Regional'" in tmdl

    def test_multiline_dax(self):
        roles = [
            RLSRoleDefinition(
                role_name="Complex",
                table_permissions=[
                    RLSTablePermission(
                        table_name="Sales",
                        filter_expression="VAR x = 1\nVAR y = 2\nRETURN x + y",
                    ),
                ],
            ),
        ]
        tmdl = render_roles_tmdl(roles)
        assert "VAR x = 1" in tmdl
        assert "RETURN x + y" in tmdl

    def test_empty_roles(self):
        tmdl = render_roles_tmdl([])
        assert "RLS Roles" in tmdl


# ---------------------------------------------------------------------------
# RLS test plan
# ---------------------------------------------------------------------------


class TestGenerateRLSTestPlan:
    def test_creates_test_cases(self):
        roles = [
            RLSRoleDefinition(
                role_name="Regional",
                table_permissions=[
                    RLSTablePermission(table_name="Sales", filter_expression="..."),
                    RLSTablePermission(table_name="Inventory", filter_expression="..."),
                ],
            ),
        ]
        cases = generate_rls_test_plan(roles)
        # 2 table permissions + 1 admin test
        assert len(cases) == 3
        assert cases[-1].role_name == "Admin (no RLS)"

    def test_empty_roles(self):
        cases = generate_rls_test_plan([])
        assert len(cases) == 1  # admin test only


class TestRenderTestPlanMarkdown:
    def test_renders(self):
        cases = [
            RLSTestCase(
                role_name="R1",
                test_user="user1",
                table_name="Sales",
                expected_filter="region filter",
                description="Test R1 on Sales",
            ),
        ]
        md = render_test_plan_markdown(cases)
        assert "RLS Validation Test Plan" in md
        assert "R1" in md
        assert "user1" in md
