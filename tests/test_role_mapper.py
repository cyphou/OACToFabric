"""Tests for role mapper — OAC roles → Fabric workspace & PBI RLS roles."""

from __future__ import annotations

import pytest

from src.agents.security.role_mapper import (
    FabricRoleAssignment,
    FabricWorkspaceRole,
    OACPermissionLevel,
    OACRole,
    RLSRoleDefinition,
    RLSTablePermission,
    RoleMappingResult,
    generate_role_assignment_script,
    map_roles,
    map_workspace_role,
    parse_oac_role,
    translate_rls_expression,
    _parse_permission_level,
    _safe_role_name,
    _session_variable_to_dax,
    _suggest_aad_group,
)


# ---------------------------------------------------------------------------
# Permission level parsing
# ---------------------------------------------------------------------------


class TestParsePermissionLevel:
    def test_admin(self):
        assert _parse_permission_level("admin") == OACPermissionLevel.ADMIN

    def test_administrator(self):
        assert _parse_permission_level("Administrator") == OACPermissionLevel.ADMIN

    def test_developer(self):
        assert _parse_permission_level("developer") == OACPermissionLevel.DEVELOPER

    def test_bi_developer(self):
        assert _parse_permission_level("BI Developer") == OACPermissionLevel.DEVELOPER

    def test_viewer(self):
        assert _parse_permission_level("viewer") == OACPermissionLevel.VIEWER

    def test_consumer(self):
        assert _parse_permission_level("consumer") == OACPermissionLevel.VIEWER

    def test_readonly(self):
        assert _parse_permission_level("read-only") == OACPermissionLevel.VIEWER

    def test_content_creator(self):
        assert _parse_permission_level("contentCreator") == OACPermissionLevel.CONTENT_CREATOR

    def test_unknown(self):
        assert _parse_permission_level("some_weird_level") == OACPermissionLevel.UNKNOWN


# ---------------------------------------------------------------------------
# Workspace role mapping
# ---------------------------------------------------------------------------


class TestMapWorkspaceRole:
    def test_admin(self):
        assert map_workspace_role(OACPermissionLevel.ADMIN) == FabricWorkspaceRole.ADMIN

    def test_developer(self):
        assert map_workspace_role(OACPermissionLevel.DEVELOPER) == FabricWorkspaceRole.CONTRIBUTOR

    def test_content_creator(self):
        assert map_workspace_role(OACPermissionLevel.CONTENT_CREATOR) == FabricWorkspaceRole.CONTRIBUTOR

    def test_viewer_edit(self):
        assert map_workspace_role(OACPermissionLevel.VIEWER_EDIT) == FabricWorkspaceRole.MEMBER

    def test_viewer(self):
        assert map_workspace_role(OACPermissionLevel.VIEWER) == FabricWorkspaceRole.VIEWER

    def test_unknown_defaults_viewer(self):
        assert map_workspace_role(OACPermissionLevel.UNKNOWN) == FabricWorkspaceRole.VIEWER


# ---------------------------------------------------------------------------
# OAC role parsing
# ---------------------------------------------------------------------------


class TestParseOACRole:
    def test_basic(self):
        meta = {
            "name": "SalesManager",
            "permission_level": "admin",
            "users": ["user1@corp.com", "user2@corp.com"],
            "groups": ["SalesTeam"],
            "rls_filters": [{"table": "Sales", "expression": "Region = 'East'"}],
        }
        role = parse_oac_role(meta)
        assert role.name == "SalesManager"
        assert role.permission_level == OACPermissionLevel.ADMIN
        assert len(role.users) == 2
        assert len(role.rls_filters) == 1

    def test_defaults(self):
        role = parse_oac_role({})
        assert role.name == "UnknownRole"
        assert role.permission_level == OACPermissionLevel.UNKNOWN


# ---------------------------------------------------------------------------
# RLS expression translation
# ---------------------------------------------------------------------------


class TestTranslateRLSExpression:
    def test_empty_returns_true(self):
        assert translate_rls_expression("") == "TRUE()"

    def test_session_user(self):
        result = translate_rls_expression("VALUEOF(NQ_SESSION.USER)")
        assert "USERPRINCIPALNAME()" in result

    def test_session_variable_lookup(self):
        result = translate_rls_expression("VALUEOF(NQ_SESSION.REGION)")
        assert "Security_UserAccess" in result
        assert "REGION" in result
        assert "REVIEW" in result

    def test_simple_equality(self):
        result = translate_rls_expression("Status = 'Active'")
        assert '[Status] = "Active"' == result

    def test_complex_fallback(self):
        result = translate_rls_expression("CASE WHEN x THEN y END")
        assert "REVIEW" in result


class TestSessionVariableToDax:
    def test_user_direct(self):
        result = _session_variable_to_dax("USER", "Users", "Email")
        assert "USERPRINCIPALNAME()" in result
        assert "[Email]" in result

    def test_general_variable(self):
        result = _session_variable_to_dax("REGION", "Sales", "Region")
        assert "Security_UserAccess" in result
        assert "REVIEW" in result


# ---------------------------------------------------------------------------
# Full role mapping
# ---------------------------------------------------------------------------


class TestMapRoles:
    def test_maps_workspace_and_rls(self):
        roles = [
            OACRole(
                name="SalesViewer",
                permission_level=OACPermissionLevel.VIEWER,
                users=["user@corp.com"],
                rls_filters=[{"table": "Sales", "expression": "Region = 'East'"}],
            ),
        ]
        result = map_roles(roles)
        assert len(result.workspace_assignments) == 1
        assert result.workspace_assignments[0].workspace_role == FabricWorkspaceRole.VIEWER
        assert len(result.rls_roles) == 1
        assert result.rls_roles[0].role_name == "SalesViewer"

    def test_role_without_rls(self):
        roles = [
            OACRole(
                name="Admin",
                permission_level=OACPermissionLevel.ADMIN,
            ),
        ]
        result = map_roles(roles)
        assert len(result.workspace_assignments) == 1
        assert len(result.rls_roles) == 0

    def test_unknown_permission_warns(self):
        roles = [
            OACRole(name="Mystery", permission_level=OACPermissionLevel.UNKNOWN),
        ]
        result = map_roles(roles)
        assert any("unknown" in w.lower() for w in result.warnings)

    def test_session_variable_rls(self):
        roles = [
            OACRole(
                name="RegionalSales",
                permission_level=OACPermissionLevel.VIEWER,
                session_variables=[
                    {"variable": "REGION", "table": "Sales", "column": "Region"},
                ],
            ),
        ]
        result = map_roles(roles)
        assert len(result.rls_roles) == 1
        assert any(
            "Security_UserAccess" in tp.filter_expression
            for tp in result.rls_roles[0].table_permissions
        )

    def test_multiple_roles(self):
        roles = [
            OACRole(name="R1", permission_level=OACPermissionLevel.ADMIN),
            OACRole(name="R2", permission_level=OACPermissionLevel.VIEWER),
            OACRole(
                name="R3",
                permission_level=OACPermissionLevel.VIEWER,
                rls_filters=[{"table": "T", "expression": ""}],
            ),
        ]
        result = map_roles(roles)
        assert len(result.workspace_assignments) == 3
        assert len(result.rls_roles) == 1  # only R3 has filters


# ---------------------------------------------------------------------------
# AAD group suggestion
# ---------------------------------------------------------------------------


class TestSuggestAADGroup:
    def test_basic(self):
        role = OACRole(name="Sales Managers")
        group = _suggest_aad_group(role)
        assert group.startswith("SG-PBI-")
        assert "Sales" in group

    def test_special_chars(self):
        role = OACRole(name="R&D/Eng")
        group = _suggest_aad_group(role)
        assert "/" not in group
        assert "&" not in group


# ---------------------------------------------------------------------------
# Safe role name
# ---------------------------------------------------------------------------


class TestSafeRoleName:
    def test_passthrough(self):
        assert _safe_role_name("SalesViewer") == "SalesViewer"

    def test_special_chars_removed(self):
        assert _safe_role_name("Sales/Viewer!") == "SalesViewer"

    def test_empty_fallback(self):
        assert _safe_role_name("!!!") == "UnknownRole"


# ---------------------------------------------------------------------------
# Role assignment script
# ---------------------------------------------------------------------------


class TestGenerateRoleAssignmentScript:
    def test_generates_script(self):
        assignments = [
            FabricRoleAssignment(
                role_name="SalesViewer",
                workspace_role=FabricWorkspaceRole.VIEWER,
                aad_group="SG-PBI-SalesViewer",
                source_oac_role="SalesViewer",
            ),
        ]
        script = generate_role_assignment_script(assignments, "ws-123")
        assert "ws-123" in script
        assert "SG-PBI-SalesViewer" in script
        assert "Viewer" in script
        assert "Invoke-FabricRestMethod" in script

    def test_empty_assignments(self):
        script = generate_role_assignment_script([])
        assert "Workspace ID" in script
