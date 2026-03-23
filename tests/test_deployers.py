"""Tests for Fabric and PBI deployers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.clients.fabric_client import FabricClient
from src.clients.pbi_client import PBIClient
from src.deployers.fabric_deployer import DeploymentResult, FabricDeployer
from src.deployers.pbi_deployer import PBIDeployer, PBIDeploymentResult


# ---------------------------------------------------------------------------
# FabricDeployer
# ---------------------------------------------------------------------------


class TestFabricDeployer:
    def _make_deployer(self, dry_run: bool = False) -> FabricDeployer:
        mock_fc = AsyncMock(spec=FabricClient)
        mock_fc.execute_sql = AsyncMock(return_value={"status": "ok"})
        mock_fc.create_pipeline = AsyncMock(return_value={"id": "pipe-1"})
        mock_fc.create_notebook = AsyncMock(return_value={"id": "nb-1"})
        return FabricDeployer(
            fabric_client=mock_fc,
            lakehouse_id="lh-1",
            dry_run=dry_run,
        )

    @pytest.mark.asyncio
    async def test_deploy_ddl(self):
        deployer = self._make_deployer()
        stmts = [
            "CREATE TABLE sales (id INT, amount DECIMAL)",
            "CREATE TABLE products (id INT, name STRING)",
        ]
        results = await deployer.deploy_ddl(stmts, "sql-endpoint")
        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].artifact_name == "sales"

    @pytest.mark.asyncio
    async def test_deploy_ddl_dry_run(self):
        deployer = self._make_deployer(dry_run=True)
        results = await deployer.deploy_ddl(["CREATE TABLE t (id INT)"], "ep")
        assert results[0].success
        assert results[0].details["dry_run"] is True

    @pytest.mark.asyncio
    async def test_deploy_pipeline(self):
        deployer = self._make_deployer()
        result = await deployer.deploy_pipeline("load_sales", {"activities": []})
        assert result.success
        assert result.artifact_id == "pipe-1"

    @pytest.mark.asyncio
    async def test_deploy_notebook(self):
        deployer = self._make_deployer()
        result = await deployer.deploy_notebook("transform_nb", "print('hello')")
        assert result.success
        assert result.artifact_id == "nb-1"

    @pytest.mark.asyncio
    async def test_deploy_all(self):
        deployer = self._make_deployer()
        results = await deployer.deploy_all(
            ddl_statements=["CREATE TABLE t (id INT)"],
            sql_endpoint="ep",
            pipelines=[("pipe", {"activities": []})],
            notebooks=[("nb", "code")],
        )
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_deploy_ddl_failure(self):
        deployer = self._make_deployer()
        deployer.fabric_client.execute_sql = AsyncMock(side_effect=Exception("boom"))
        results = await deployer.deploy_ddl(["CREATE TABLE t (id INT)"], "ep")
        assert not results[0].success
        assert "boom" in results[0].error

    def test_extract_table_name(self):
        assert FabricDeployer._extract_table_name("CREATE TABLE sales (id INT)") == "sales"
        assert FabricDeployer._extract_table_name("CREATE TABLE IF NOT EXISTS db.orders (id INT)") == "db.orders"
        assert FabricDeployer._extract_table_name("SELECT 1") == "unknown_table"


# ---------------------------------------------------------------------------
# PBIDeployer
# ---------------------------------------------------------------------------


class TestPBIDeployer:
    def _make_deployer(self, dry_run: bool = False) -> PBIDeployer:
        mock_pbi = AsyncMock(spec=PBIClient)
        mock_pbi.deploy_tmdl = AsyncMock(
            return_value={"status": "ok", "files_deployed": []}
        )
        mock_pbi.import_pbix = AsyncMock(return_value={"id": "import-1"})
        mock_pbi.get_dataset_roles = AsyncMock(return_value=[])
        mock_pbi.add_workspace_user = AsyncMock(return_value={})
        return PBIDeployer(pbi_client=mock_pbi, dry_run=dry_run)

    @pytest.mark.asyncio
    async def test_deploy_semantic_model(self):
        deployer = self._make_deployer()
        result = await deployer.deploy_semantic_model(
            "Sales Model", {"model.tmdl": "content"}
        )
        assert result.success
        assert result.artifact_type == "semantic_model"

    @pytest.mark.asyncio
    async def test_deploy_semantic_model_dry_run(self):
        deployer = self._make_deployer(dry_run=True)
        result = await deployer.deploy_semantic_model("Model", {"m.tmdl": "c"})
        assert result.success
        assert result.details["dry_run"] is True

    @pytest.mark.asyncio
    async def test_deploy_report_bytes(self):
        deployer = self._make_deployer()
        result = await deployer.deploy_report("Report", pbix_bytes=b"\x00")
        assert result.success
        assert result.artifact_id == "import-1"

    @pytest.mark.asyncio
    async def test_deploy_report_no_input(self):
        deployer = self._make_deployer()
        result = await deployer.deploy_report("Report")
        assert not result.success
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_configure_rls(self):
        deployer = self._make_deployer()
        result = await deployer.configure_rls(
            "ds-1", [{"name": "SalesRole", "filter": "[Region] = 'US'"}]
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_assign_workspace_roles(self):
        deployer = self._make_deployer()
        results = await deployer.assign_workspace_roles(
            [{"email": "user@test.com", "role": "Viewer"}]
        )
        assert len(results) == 1
        assert results[0].success

    @pytest.mark.asyncio
    async def test_deploy_all(self):
        deployer = self._make_deployer()
        results = await deployer.deploy_all(
            semantic_models=[("Model", {"m.tmdl": "c"})],
            workspace_roles=[{"email": "a@b.com", "role": "Member"}],
        )
        assert len(results) == 2
        assert all(r.success for r in results)
