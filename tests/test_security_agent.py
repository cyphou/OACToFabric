"""Tests for Security Migration Agent (Agent 06) — end-to-end lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agents.security.security_agent import SecurityMigrationAgent
from src.core.models import (
    AssetType,
    Inventory,
    InventoryItem,
    MigrationScope,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "security_output"
    d.mkdir()
    return d


def _make_inventory() -> Inventory:
    """Create a test inventory with security roles and init blocks."""
    return Inventory(items=[
        InventoryItem(
            id="role__sales_viewer",
            asset_type=AssetType.SECURITY_ROLE,
            source_path="/security/SalesViewer",
            name="SalesViewer",
            metadata={
                "name": "SalesViewer",
                "permission_level": "viewer",
                "users": ["alice@corp.com", "bob@corp.com"],
                "groups": ["SalesTeam"],
                "rls_filters": [
                    {
                        "table": "Sales",
                        "expression": "Region = 'East'",
                    },
                ],
                "object_permissions": [
                    {"type": "hideColumn", "table": "Sales", "column": "Margin"},
                    {"type": "hideColumn", "table": "Sales", "column": "Cost"},
                ],
                "session_variables": [],
            },
        ),
        InventoryItem(
            id="role__regional_sales",
            asset_type=AssetType.SECURITY_ROLE,
            source_path="/security/RegionalSales",
            name="RegionalSales",
            metadata={
                "name": "RegionalSales",
                "permission_level": "viewer",
                "users": ["charlie@corp.com"],
                "rls_filters": [],
                "object_permissions": [],
                "session_variables": [
                    {"variable": "REGION", "table": "Sales", "column": "Region"},
                ],
            },
        ),
        InventoryItem(
            id="role__admin",
            asset_type=AssetType.SECURITY_ROLE,
            source_path="/security/Admin",
            name="Admin",
            metadata={
                "name": "Admin",
                "permission_level": "admin",
                "users": ["admin@corp.com"],
                "rls_filters": [],
                "object_permissions": [],
                "session_variables": [],
            },
        ),
        InventoryItem(
            id="init__set_region",
            asset_type=AssetType.INIT_BLOCK,
            source_path="/security/init/set_region",
            name="set_region",
            metadata={
                "name": "set_region",
                "sql": "SELECT region FROM user_regions WHERE email = :user",
                "variables": ["REGION"],
            },
        ),
    ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSecurityMigrationAgentLifecycle:
    @pytest.mark.asyncio
    async def test_discover_from_scope(self, output_dir: Path):
        scope = MigrationScope(include_paths=["/security/SalesViewer"])
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = await agent.discover(scope)
        assert inventory.count == 1

    @pytest.mark.asyncio
    async def test_plan(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        assert len(plan.items) == 4
        assert plan.estimated_duration_minutes >= 1

    @pytest.mark.asyncio
    async def test_execute_writes_roles_tmdl(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        result = await agent.execute(plan)

        assert result.succeeded == 4
        assert result.failed == 0

        roles_file = output_dir / "roles.tmdl"
        assert roles_file.exists()
        content = roles_file.read_text(encoding="utf-8")
        assert "role 'SalesViewer'" in content
        assert "role 'RegionalSales'" in content

    @pytest.mark.asyncio
    async def test_execute_writes_ols_tmdl(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        ols_file = output_dir / "ols.tmdl"
        assert ols_file.exists()
        content = ols_file.read_text(encoding="utf-8")
        assert "SalesViewer" in content
        assert "Margin" in content
        assert "metadataPermission: none" in content

    @pytest.mark.asyncio
    async def test_execute_writes_lookup_ddl(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        ddl_file = output_dir / "Security_UserAccess.sql"
        assert ddl_file.exists()
        content = ddl_file.read_text(encoding="utf-8")
        assert "CREATE TABLE Security_UserAccess" in content
        assert "UserEmail" in content
        assert "REGION" in content

    @pytest.mark.asyncio
    async def test_execute_writes_assignment_script(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        script_file = output_dir / "workspace_role_assignments.ps1"
        assert script_file.exists()
        content = script_file.read_text(encoding="utf-8")
        assert "SalesViewer" in content
        assert "Invoke-FabricRestMethod" in content

    @pytest.mark.asyncio
    async def test_execute_writes_test_plan(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        test_plan_file = output_dir / "rls_test_plan.md"
        assert test_plan_file.exists()
        content = test_plan_file.read_text(encoding="utf-8")
        assert "RLS Validation Test Plan" in content

    @pytest.mark.asyncio
    async def test_execute_writes_security_matrix(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        matrix_file = output_dir / "security_matrix.md"
        assert matrix_file.exists()
        content = matrix_file.read_text(encoding="utf-8")
        assert "Object-Level Security Matrix" in content

    @pytest.mark.asyncio
    async def test_execute_writes_summary(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        summary = output_dir / "security_migration_summary.md"
        assert summary.exists()
        content = summary.read_text(encoding="utf-8")
        assert "# Security Migration Summary" in content
        assert "OAC roles processed" in content
        assert "RLS roles generated" in content

    @pytest.mark.asyncio
    async def test_validate_passes(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        result = await agent.execute(plan)
        report = await agent.validate(result)

        assert report.failed == 0
        assert report.passed >= 4

    @pytest.mark.asyncio
    async def test_summary_report_content(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        report = agent.generate_summary_report()
        assert "## Overview" in report
        assert "Workspace role assignments" in report
        assert "RLS roles generated" in report
        assert "OLS roles generated" in report

    @pytest.mark.asyncio
    async def test_workspace_roles_correct(self, output_dir: Path):
        agent = SecurityMigrationAgent(output_dir=output_dir)
        inventory = _make_inventory()
        plan = await agent.plan(inventory)
        await agent.execute(plan)

        # Admin role should map to Admin workspace role
        report = agent.generate_summary_report()
        assert "Admin" in report
