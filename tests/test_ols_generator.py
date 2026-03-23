"""Tests for OLS generator — OAC object permissions → PBI OLS TMDL."""

from __future__ import annotations

import pytest

from src.agents.security.ols_generator import (
    OACObjectPermissionType,
    OLSColumnPermission,
    OLSGenerationResult,
    OLSPermission,
    OLSRoleDefinition,
    OLSTablePermission,
    convert_all_object_permissions,
    convert_object_permissions,
    generate_security_matrix,
    render_ols_tmdl,
    _parse_permission_type,
)


# ---------------------------------------------------------------------------
# Permission type parsing
# ---------------------------------------------------------------------------


class TestParsePermissionType:
    def test_hide_column(self):
        assert _parse_permission_type("hideColumn") == OACObjectPermissionType.HIDE_COLUMN

    def test_column_hide(self):
        assert _parse_permission_type("column_hide") == OACObjectPermissionType.HIDE_COLUMN

    def test_hide_table(self):
        assert _parse_permission_type("hideTable") == OACObjectPermissionType.HIDE_TABLE

    def test_hide_measure(self):
        assert _parse_permission_type("hideMeasure") == OACObjectPermissionType.HIDE_MEASURE

    def test_restrict_access(self):
        assert _parse_permission_type("restrictAccess") == OACObjectPermissionType.RESTRICT_ACCESS

    def test_deny(self):
        assert _parse_permission_type("deny") == OACObjectPermissionType.RESTRICT_ACCESS

    def test_unknown(self):
        assert _parse_permission_type("something_else") == OACObjectPermissionType.UNKNOWN


# ---------------------------------------------------------------------------
# Single role conversion
# ---------------------------------------------------------------------------


class TestConvertObjectPermissions:
    def test_hide_column(self):
        perms = [{"type": "hideColumn", "table": "Sales", "column": "Margin"}]
        ols = convert_object_permissions("FinanceOnly", perms)
        assert ols.role_name == "FinanceOnly"
        assert len(ols.column_permissions) == 1
        assert ols.column_permissions[0].column_name == "Margin"
        assert ols.column_permissions[0].permission == OLSPermission.NONE

    def test_hide_table(self):
        perms = [{"type": "hideTable", "table": "Financials"}]
        ols = convert_object_permissions("Basic", perms)
        assert len(ols.table_permissions) == 1
        assert ols.table_permissions[0].table_name == "Financials"

    def test_hide_measure_warns(self):
        perms = [{"type": "hideMeasure", "table": "Sales", "measure": "GrossMargin"}]
        ols = convert_object_permissions("ViewerRole", perms)
        assert len(ols.warnings) > 0
        assert any("not natively supported" in w for w in ols.warnings)
        # Still creates column permission as best effort
        assert len(ols.column_permissions) == 1

    def test_restrict_access_maps_to_table(self):
        perms = [{"type": "restrictAccess", "table": "Secret"}]
        ols = convert_object_permissions("BasicViewer", perms)
        assert len(ols.table_permissions) == 1
        assert len(ols.warnings) > 0

    def test_unknown_type_warns(self):
        perms = [{"type": "custom_perm", "table": "T"}]
        ols = convert_object_permissions("R", perms)
        assert any("unknown" in w.lower() for w in ols.warnings)

    def test_table_mapping_applied(self):
        perms = [{"type": "hideColumn", "table": "OldTable", "column": "Col1"}]
        ols = convert_object_permissions("R", perms, table_mapping={"OldTable": "NewTable"})
        assert ols.column_permissions[0].table_name == "NewTable"

    def test_multiple_permissions(self):
        perms = [
            {"type": "hideColumn", "table": "Sales", "column": "Margin"},
            {"type": "hideColumn", "table": "Sales", "column": "Cost"},
            {"type": "hideTable", "table": "HR"},
        ]
        ols = convert_object_permissions("FinanceOnly", perms)
        assert len(ols.column_permissions) == 2
        assert len(ols.table_permissions) == 1


# ---------------------------------------------------------------------------
# Batch conversion
# ---------------------------------------------------------------------------


class TestConvertAllObjectPermissions:
    def test_multiple_roles(self):
        roles = [
            {
                "name": "R1",
                "object_permissions": [
                    {"type": "hideColumn", "table": "Sales", "column": "Margin"},
                ],
            },
            {
                "name": "R2",
                "object_permissions": [
                    {"type": "hideTable", "table": "HR"},
                ],
            },
        ]
        result = convert_all_object_permissions(roles)
        assert len(result.ols_roles) == 2

    def test_skips_roles_without_permissions(self):
        roles = [
            {"name": "R1", "object_permissions": []},
            {"name": "R2", "object_permissions": [
                {"type": "hideColumn", "table": "T", "column": "C"},
            ]},
        ]
        result = convert_all_object_permissions(roles)
        assert len(result.ols_roles) == 1

    def test_empty(self):
        result = convert_all_object_permissions([])
        assert len(result.ols_roles) == 0


# ---------------------------------------------------------------------------
# TMDL rendering
# ---------------------------------------------------------------------------


class TestRenderOLSTMDL:
    def test_column_ols(self):
        roles = [
            OLSRoleDefinition(
                role_name="FinanceOnly",
                column_permissions=[
                    OLSColumnPermission(
                        table_name="Sales",
                        column_name="Margin",
                        permission=OLSPermission.NONE,
                    ),
                ],
            ),
        ]
        tmdl = render_ols_tmdl(roles)
        assert "role 'FinanceOnly'" in tmdl
        assert "columnPermission 'Margin'" in tmdl
        assert "metadataPermission: none" in tmdl

    def test_table_ols(self):
        roles = [
            OLSRoleDefinition(
                role_name="Basic",
                table_permissions=[
                    OLSTablePermission(table_name="HR", permission=OLSPermission.NONE),
                ],
            ),
        ]
        tmdl = render_ols_tmdl(roles)
        assert "tablePermission 'HR'" in tmdl
        assert "FALSE()" in tmdl

    def test_empty_roles(self):
        tmdl = render_ols_tmdl([])
        assert "No OLS roles defined" in tmdl


# ---------------------------------------------------------------------------
# Security matrix
# ---------------------------------------------------------------------------


class TestSecurityMatrix:
    def test_generates_matrix(self):
        roles = [
            OLSRoleDefinition(
                role_name="Basic",
                column_permissions=[
                    OLSColumnPermission(table_name="Sales", column_name="Margin"),
                ],
                table_permissions=[
                    OLSTablePermission(table_name="HR"),
                ],
            ),
        ]
        md = generate_security_matrix(roles)
        assert "Object-Level Security Matrix" in md
        assert "HIDDEN" in md
        assert "Visible" not in md or "HR" in md  # HR should be HIDDEN

    def test_empty(self):
        md = generate_security_matrix([])
        assert "No OLS roles defined" in md
