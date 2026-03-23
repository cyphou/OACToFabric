"""Tests for Phase 19 — Fabric/PBI deployment validation.

Covers:
- Coordination DDL generation & deployment
- PBIR report deployment
- OLS (Object-Level Security) configuration
- End-to-end dry-run migration
- Performance baseline capture
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.dry_run import (
    AgentTiming,
    DryRunMigration,
    DryRunResult,
    PerformanceBaseline,
)
from src.core.models import MigrationScope, ValidationReport
from src.deployers.coordination_ddl import (
    CoordinationDeployment,
    coordination_table_names,
    deploy_coordination_tables,
    generate_coordination_ddl,
    generate_drop_ddl,
)
from src.deployers.pbi_deployer import PBIDeployer, PBIDeploymentResult


# =========================================================================
# Coordination DDL
# =========================================================================


class TestCoordinationDDL:
    """Test coordination table DDL generation."""

    def test_table_names_returns_five(self):
        names = coordination_table_names()
        assert len(names) == 5
        assert "agent_tasks" in names
        assert "migration_inventory" in names
        assert "mapping_rules" in names
        assert "validation_results" in names
        assert "agent_logs" in names

    def test_generate_ddl_default_schema(self):
        stmts = generate_coordination_ddl()
        assert len(stmts) == 5
        for stmt in stmts:
            assert "dbo." in stmt
            assert "CREATE TABLE IF NOT EXISTS" in stmt

    def test_generate_ddl_custom_schema(self):
        stmts = generate_coordination_ddl(schema="migration")
        for stmt in stmts:
            assert "migration." in stmt

    def test_ddl_contains_expected_columns(self):
        stmts = generate_coordination_ddl()
        # agent_tasks should have agent_id, status, etc.
        tasks_ddl = [s for s in stmts if "agent_tasks" in s][0]
        assert "agent_id" in tasks_ddl
        assert "status" in tasks_ddl
        assert "duration_ms" in tasks_ddl
        # migration_inventory
        inv_ddl = [s for s in stmts if "migration_inventory" in s][0]
        assert "asset_type" in inv_ddl
        assert "complexity_score" in inv_ddl

    def test_generate_drop_ddl(self):
        stmts = generate_drop_ddl()
        assert len(stmts) == 5
        for stmt in stmts:
            assert stmt.startswith("DROP TABLE IF EXISTS")

    def test_drop_ddl_reverse_order(self):
        create_names = coordination_table_names()
        drop_stmts = generate_drop_ddl()
        # Drop order should be reversed from creation order
        drop_names = [s.split(".")[-1] for s in drop_stmts]
        assert drop_names == list(reversed(create_names))


class TestCoordinationDeployment:
    """Test the deploy_coordination_tables async function."""

    @pytest.mark.asyncio
    async def test_deploy_all_success(self):
        mock_client = AsyncMock()
        mock_client.execute_sql = AsyncMock(return_value={"status": "ok"})

        result = await deploy_coordination_tables(
            mock_client, "test.sql.endpoint"
        )

        assert isinstance(result, CoordinationDeployment)
        assert result.success
        assert len(result.tables_created) == 5
        assert result.total == 5
        assert mock_client.execute_sql.call_count == 5

    @pytest.mark.asyncio
    async def test_deploy_partial_failure(self):
        call_count = 0

        async def _sql(endpoint, query, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise RuntimeError("Connection lost")
            return {"status": "ok"}

        mock_client = AsyncMock()
        mock_client.execute_sql = _sql

        result = await deploy_coordination_tables(
            mock_client, "test.sql.endpoint"
        )

        assert not result.success
        assert len(result.tables_created) == 4
        assert len(result.tables_failed) == 1
        assert "Connection lost" in result.tables_failed[0][1]

    @pytest.mark.asyncio
    async def test_deploy_custom_schema(self):
        mock_client = AsyncMock()
        mock_client.execute_sql = AsyncMock(return_value={"status": "ok"})

        await deploy_coordination_tables(
            mock_client, "ep", schema="oac_migration"
        )

        for call in mock_client.execute_sql.call_args_list:
            query = call.args[1]
            assert "oac_migration." in query


# =========================================================================
# PBIR Report Deployment
# =========================================================================


class TestPBIRDeploy:
    """Test PBIR report deployment."""

    def _make_deployer(self, *, dry_run: bool = False) -> PBIDeployer:
        mock_client = AsyncMock()
        mock_client.group_id = "test-group"
        mock_client._request = AsyncMock(return_value={"id": "new-report-123"})
        mock_client.deploy_tmdl = AsyncMock(
            return_value={"status": "ok", "method": "rest_api"}
        )
        mock_client.import_pbix = AsyncMock(return_value={"id": "import-456"})
        mock_client.get_dataset_roles = AsyncMock(return_value=[])
        mock_client.add_workspace_user = AsyncMock(return_value={})
        return PBIDeployer(pbi_client=mock_client, dry_run=dry_run)

    @pytest.mark.asyncio
    async def test_deploy_pbir_report(self):
        deployer = self._make_deployer()
        pbir_files = {
            "report.json": '{"config": {}}',
            "pages/page1.json": '{"visuals": []}',
        }

        result = await deployer.deploy_pbir_report("TestReport", pbir_files, "ds-1")

        assert result.success
        assert result.artifact_type == "pbir_report"
        assert result.artifact_name == "TestReport"
        assert result.artifact_id == "new-report-123"

    @pytest.mark.asyncio
    async def test_deploy_pbir_dry_run(self):
        deployer = self._make_deployer(dry_run=True)
        pbir_files = {"report.json": '{}'}

        result = await deployer.deploy_pbir_report("DryReport", pbir_files)

        assert result.success
        assert result.details.get("dry_run") is True
        assert "report.json" in result.details["files"]

    @pytest.mark.asyncio
    async def test_deploy_pbir_failure(self):
        deployer = self._make_deployer()
        deployer.pbi_client._request = AsyncMock(
            side_effect=RuntimeError("API error")
        )

        result = await deployer.deploy_pbir_report("FailReport", {"x.json": "{}"})

        assert not result.success
        assert "API error" in result.error


# =========================================================================
# OLS Configuration
# =========================================================================


class TestOLSDeploy:
    """Test Object-Level Security deployment."""

    def _make_deployer(self, *, dry_run: bool = False) -> PBIDeployer:
        mock_client = AsyncMock()
        mock_client.group_id = "test-group"
        mock_client.get_dataset_roles = AsyncMock(
            return_value=[
                {
                    "name": "RestrictedRole",
                    "tablePermissions": [
                        {
                            "name": "Sales",
                            "columnPermissions": [
                                {"name": "Salary", "metadataPermission": "None"},
                                {"name": "SSN", "metadataPermission": "None"},
                            ],
                        }
                    ],
                }
            ]
        )
        return PBIDeployer(pbi_client=mock_client, dry_run=dry_run)

    @pytest.mark.asyncio
    async def test_configure_ols(self):
        deployer = self._make_deployer()
        rules = [
            {"role_name": "RestrictedRole", "table_name": "Sales", "column_name": "Salary", "permission": "None"},
            {"role_name": "RestrictedRole", "table_name": "Sales", "column_name": "SSN", "permission": "None"},
        ]

        result = await deployer.configure_ols("ds-1", rules)

        assert result.success
        assert result.artifact_type == "ols"
        assert result.details["ols_columns_found"] == 2

    @pytest.mark.asyncio
    async def test_configure_ols_dry_run(self):
        deployer = self._make_deployer(dry_run=True)

        result = await deployer.configure_ols("ds-1", [{"col": "x"}])

        assert result.success
        assert result.details["dry_run"] is True
        assert result.details["rule_count"] == 1


# =========================================================================
# Dry-Run Migration
# =========================================================================


class TestDryRunMigration:
    """Test end-to-end dry-run migration."""

    @pytest.mark.asyncio
    async def test_dry_run_all_agents_succeed(self):
        async def _runner(agent_id: str, scope: MigrationScope) -> ValidationReport:
            await asyncio.sleep(0.001)
            return ValidationReport(
                agent_id=agent_id, total_checks=3, passed=3
            )

        dry_run = DryRunMigration(_runner, agent_ids=["discovery", "schema"])
        scope = MigrationScope()

        result = await dry_run.execute(scope)

        assert isinstance(result, DryRunResult)
        assert result.success
        assert result.agents_run == ["discovery", "schema"]
        assert len(result.errors) == 0
        assert result.baseline.total_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_dry_run_agent_failure(self):
        async def _runner(agent_id: str, scope: MigrationScope) -> ValidationReport:
            if agent_id == "etl":
                raise RuntimeError("ETL blew up")
            return ValidationReport(agent_id=agent_id)

        dry_run = DryRunMigration(_runner, agent_ids=["discovery", "etl", "semantic_model"])
        result = await dry_run.execute(MigrationScope())

        assert not result.success
        assert len(result.errors) == 1
        assert "etl" in result.errors[0]
        # All 3 agents should still be attempted
        assert len(result.agents_run) == 3

    @pytest.mark.asyncio
    async def test_dry_run_captures_timing(self):
        async def _runner(agent_id: str, scope: MigrationScope) -> ValidationReport:
            await asyncio.sleep(0.01)
            return ValidationReport(agent_id=agent_id)

        dry_run = DryRunMigration(_runner, agent_ids=["discovery"])
        result = await dry_run.execute(MigrationScope())

        assert len(result.baseline.agent_timings) == 1
        assert result.baseline.agent_timings[0].agent_id == "discovery"
        assert result.baseline.agent_timings[0].duration_ms >= 5

    @pytest.mark.asyncio
    async def test_dry_run_default_agent_order(self):
        dry_run = DryRunMigration(AsyncMock())
        assert len(dry_run._agent_ids) == 7
        assert dry_run._agent_ids[0] == "discovery"
        assert dry_run._agent_ids[-1] == "validation"


# =========================================================================
# Performance Baseline
# =========================================================================


class TestPerformanceBaseline:
    """Test PerformanceBaseline data structure."""

    def test_add_timing(self):
        baseline = PerformanceBaseline()
        t = AgentTiming(agent_id="test", started_at=100.0)
        t.finish(items=10)

        baseline.add_timing(t)

        assert len(baseline.agent_timings) == 1
        assert baseline.total_items_processed == 10

    def test_to_dict(self):
        baseline = PerformanceBaseline(total_duration_ms=5000)
        t = AgentTiming(agent_id="discovery", started_at=100.0)
        t.finish(items=25)
        baseline.add_timing(t)

        d = baseline.to_dict()

        assert d["total_duration_ms"] == 5000
        assert len(d["agents"]) == 1
        assert d["agents"][0]["agent_id"] == "discovery"
        assert d["agents"][0]["items_processed"] == 25

    def test_summary_output(self):
        baseline = PerformanceBaseline(total_duration_ms=1234)
        t = AgentTiming(agent_id="schema", started_at=100.0)
        t.finish(items=5)
        baseline.add_timing(t)

        text = baseline.summary()

        assert "1234ms" in text
        assert "schema" in text


# =========================================================================
# deploy_all with new PBIR/OLS
# =========================================================================


class TestDeployAllExtended:
    """Test PBIDeployer.deploy_all with PBIR and OLS additions."""

    @pytest.mark.asyncio
    async def test_deploy_all_includes_pbir_and_ols(self):
        mock_client = AsyncMock()
        mock_client.group_id = "g1"
        mock_client._request = AsyncMock(return_value={"id": "r1"})
        mock_client.deploy_tmdl = AsyncMock(return_value={"status": "ok"})
        mock_client.get_dataset_roles = AsyncMock(return_value=[])
        mock_client.add_workspace_user = AsyncMock(return_value={})

        deployer = PBIDeployer(pbi_client=mock_client, dry_run=True)

        results = await deployer.deploy_all(
            semantic_models=[("model1", {"model.tmdl": "x"})],
            pbir_reports=[("report1", {"report.json": "{}"}, "ds-1")],
            ols_configs=[("ds-1", [{"col": "salary"}])],
        )

        types = [r.artifact_type for r in results]
        assert "semantic_model" in types
        assert "pbir_report" in types
        assert "ols" in types
        assert all(r.success for r in results)
