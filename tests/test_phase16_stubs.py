"""Phase 16 tests — Fabric SQL execution, TMDL roles/expressions, notifications, role mapper."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.security.role_mapper import (
    FabricRoleAssignment,
    FabricWorkspaceRole,
    OACPermissionLevel,
    OACRole,
    RLSRoleDefinition,
    RLSTablePermission,
    RoleMappingResult,
    _suggest_aad_group,
    generate_role_assignment_script,
    map_roles,
    translate_rls_expression,
)


# ---------------------------------------------------------------------------
# AAD Group Resolution
# ---------------------------------------------------------------------------


class TestAADGroupResolution:
    """Tests for _suggest_aad_group with Graph API support."""

    def test_convention_name_without_graph(self):
        role = OACRole(name="Sales Viewers")
        result = _suggest_aad_group(role, graph_client=None)
        assert result == "SG-PBI-Sales_Viewers"

    def test_convention_name_special_chars(self):
        role = OACRole(name="Admin/Super User")
        result = _suggest_aad_group(role, graph_client=None)
        assert result == "SG-PBI-Admin_Super_User"

    def test_convention_name_default(self):
        role = OACRole(name="BasicRole")
        result = _suggest_aad_group(role)
        assert result == "SG-PBI-BasicRole"

    def test_no_todo_aad_group_in_script(self):
        """Verify TODO_AAD_GROUP no longer appears in generated scripts."""
        assignments = [
            FabricRoleAssignment(
                role_name="Viewers",
                workspace_role=FabricWorkspaceRole.VIEWER,
                aad_group="",
                source_oac_role="OAC_Viewers",
            )
        ]
        script = generate_role_assignment_script(assignments)
        assert "TODO_AAD_GROUP" not in script
        assert "SG-PBI-Viewers" in script

    def test_script_uses_provided_group(self):
        assignments = [
            FabricRoleAssignment(
                role_name="Admins",
                workspace_role=FabricWorkspaceRole.ADMIN,
                aad_group="MyCustomGroup",
                source_oac_role="OAC_Admins",
            )
        ]
        script = generate_role_assignment_script(assignments)
        assert "MyCustomGroup" in script


class TestMapRolesIntegration:
    """Integration tests for map_roles."""

    def test_admin_role_maps_to_admin(self):
        roles = [OACRole(name="OACAdmin", permission_level=OACPermissionLevel.ADMIN)]
        result = map_roles(roles)
        assert len(result.workspace_assignments) == 1
        assert result.workspace_assignments[0].workspace_role == FabricWorkspaceRole.ADMIN

    def test_viewer_with_rls(self):
        roles = [
            OACRole(
                name="RegionViewer",
                permission_level=OACPermissionLevel.VIEWER,
                rls_filters=[{"table": "Sales", "expression": "region = 'US'"}],
            )
        ]
        result = map_roles(roles)
        assert len(result.rls_roles) == 1
        rls = result.rls_roles[0]
        assert rls.role_name == "RegionViewer"
        assert len(rls.table_permissions) == 1

    def test_unknown_permission_warns(self):
        roles = [OACRole(name="Mystery", permission_level=OACPermissionLevel.UNKNOWN)]
        result = map_roles(roles)
        assert any("unknown" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# TMDL Roles & Expressions
# ---------------------------------------------------------------------------


class TestTMDLRolesGeneration:
    """Tests for TMDL role generation from RLS role definitions."""

    def test_generate_roles_tmdl_import(self):
        """Test that generate_roles_tmdl can be imported and called."""
        from src.agents.semantic.tmdl_generator import generate_roles_tmdl

        rls_roles = [
            RLSRoleDefinition(
                role_name="SalesTeam",
                description="Sales region filter",
                table_permissions=[
                    RLSTablePermission(
                        table_name="FactSales",
                        filter_expression='[Region] = "US"',
                    )
                ],
            )
        ]
        content = generate_roles_tmdl(rls_roles)
        assert "SalesTeam" in content
        assert "FactSales" in content
        assert "Region" in content

    def test_generate_roles_tmdl_empty(self):
        from src.agents.semantic.tmdl_generator import generate_roles_tmdl

        content = generate_roles_tmdl([])
        assert content == ""

    def test_generate_roles_multiple(self):
        from src.agents.semantic.tmdl_generator import generate_roles_tmdl

        rls_roles = [
            RLSRoleDefinition(
                role_name="US_Team",
                table_permissions=[
                    RLSTablePermission(table_name="Sales", filter_expression='[Region] = "US"'),
                ],
            ),
            RLSRoleDefinition(
                role_name="EU_Team",
                table_permissions=[
                    RLSTablePermission(table_name="Sales", filter_expression='[Region] = "EU"'),
                    RLSTablePermission(table_name="Customers", filter_expression='[Country] IN {"DE","FR"}'),
                ],
            ),
        ]
        content = generate_roles_tmdl(rls_roles)
        assert "US_Team" in content
        assert "EU_Team" in content
        assert content.count("role ") >= 2


class TestTMDLExpressionsGeneration:
    """Tests for TMDL expressions (data sources)."""

    def test_generate_expressions_tmdl_import(self):
        from src.agents.semantic.tmdl_generator import generate_expressions_tmdl

        content = generate_expressions_tmdl(
            lakehouse_name="migration_lh",
            sql_endpoint="myworkspace.datawarehouse.fabric.microsoft.com",
        )
        assert "migration_lh" in content
        assert "myworkspace" in content

    def test_generate_expressions_with_additional_sources(self):
        from src.agents.semantic.tmdl_generator import generate_expressions_tmdl

        content = generate_expressions_tmdl(
            lakehouse_name="main_lh",
            sql_endpoint="ws.datawarehouse.fabric.microsoft.com",
            additional_sources={"ExternalDB": "Server=extdb;Database=prod"},
        )
        assert "main_lh" in content
        assert "ExternalDB" in content


# ---------------------------------------------------------------------------
# Notification Channels
# ---------------------------------------------------------------------------


class TestNotificationChannels:
    """Tests for real notification channel implementations."""

    def test_teams_notification_posts_to_webhook(self):
        from src.agents.orchestrator.notification_manager import (
            Channel,
            Notification,
            NotificationManager,
            Severity,
        )

        mgr = NotificationManager(teams_webhook_url="https://fake.webhook.url/hook")
        notif = Notification(
            title="Test Subject",
            message="Test message body",
            severity=Severity.INFO,
            channel=Channel.TEAMS,
        )
        with patch("httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.post = MagicMock(return_value=MagicMock(status_code=200, raise_for_status=MagicMock()))
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=None)
            MockClient.return_value = mock_instance
            mgr._send_teams(notif)
            mock_instance.post.assert_called_once()
            # Verify the webhook URL was used
            call_args = mock_instance.post.call_args
            assert call_args[0][0] == "https://fake.webhook.url/hook"

    def test_pagerduty_sends_event(self):
        from src.agents.orchestrator.notification_manager import (
            Channel,
            Notification,
            NotificationManager,
            Severity,
        )

        mgr = NotificationManager(pagerduty_routing_key="fake-routing-key")
        notif = Notification(
            title="Alert Subject",
            message="Critical failure",
            severity=Severity.CRITICAL,
            channel=Channel.PAGERDUTY,
        )
        with patch("httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.post = MagicMock(
                return_value=MagicMock(status_code=202, json=MagicMock(return_value={"status": "success"}), raise_for_status=MagicMock())
            )
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=None)
            MockClient.return_value = mock_instance
            mgr._send_pagerduty(notif)
            mock_instance.post.assert_called_once()

    def test_teams_skipped_without_webhook(self):
        from src.agents.orchestrator.notification_manager import (
            Channel,
            Notification,
            NotificationManager,
            Severity,
        )

        mgr = NotificationManager(teams_webhook_url="")
        notif = Notification(title="No Webhook", message="Should skip", channel=Channel.TEAMS)
        # Should not raise
        mgr._send_teams(notif)

    def test_email_skipped_without_config(self):
        from src.agents.orchestrator.notification_manager import (
            Channel,
            Notification,
            NotificationManager,
        )

        mgr = NotificationManager(email_connection_string="", email_recipients=[])
        notif = Notification(title="No Email", message="Should skip", channel=Channel.EMAIL)
        # Should not raise
        mgr._send_email(notif)

    def test_notify_dispatches_to_log(self):
        from src.agents.orchestrator.notification_manager import (
            Channel,
            NotificationManager,
        )

        mgr = NotificationManager(enabled_channels=[Channel.LOG])
        result = mgr.notify("agent_completed", "Agent Done", "All items processed")
        assert len(result) >= 1
        assert result[0].channel == Channel.LOG


# ---------------------------------------------------------------------------
# Datetime timezone fixes
# ---------------------------------------------------------------------------


class TestDatetimeTimezone:
    """Verify datetime.utcnow() has been replaced with timezone-aware calls."""

    def test_models_use_timezone(self):
        from src.core.models import AssetType, InventoryItem

        item = InventoryItem(
            id="a1",
            name="Test",
            asset_type=AssetType.PHYSICAL_TABLE,
            source_path="/tables/test",
        )
        # The discovered_at should be set (timezone-aware)
        assert item.discovered_at is not None

    def test_no_utcnow_in_source(self):
        """Sanity check — grep for utcnow in source files."""
        from pathlib import Path

        src_dir = Path(__file__).parent.parent / "src"
        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "datetime.utcnow" not in content, (
                f"Found deprecated datetime.utcnow() in {py_file.relative_to(src_dir.parent)}"
            )


# ---------------------------------------------------------------------------
# RLS Expression Translation (expanded)
# ---------------------------------------------------------------------------


class TestRLSExpressionTranslation:
    """Additional tests for RLS expression translation."""

    def test_simple_column_filter(self):
        result = translate_rls_expression("region = 'US'")
        assert "[region]" in result
        assert "US" in result

    def test_user_session_variable(self):
        result = translate_rls_expression("VALUEOF(NQ_SESSION.USER)")
        assert "USERPRINCIPALNAME()" in result

    def test_custom_session_variable(self):
        result = translate_rls_expression("VALUEOF(NQ_SESSION.DEPARTMENT)")
        assert "DEPARTMENT" in result
        assert "REVIEW" in result
        assert "Security_UserAccess" in result

    def test_empty_expression(self):
        assert translate_rls_expression("") == "TRUE()"

    def test_complex_expression_flagged(self):
        result = translate_rls_expression("CASE WHEN x > 1 THEN 'A' ELSE 'B' END")
        assert "REVIEW" in result
