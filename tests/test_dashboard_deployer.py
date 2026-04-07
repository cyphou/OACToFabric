"""Tests for Phase 80 — Dashboard Deployer."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest

from src.tools.dashboard_deployer import (
    DashboardDeployer,
    DashboardPage,
    DashboardTemplate,
    DashboardTile,
    TileType,
    build_default_template,
)


class TestDashboardTile(unittest.TestCase):
    def test_to_dict(self) -> None:
        tile = DashboardTile(tile_id="t1", title="Test", tile_type=TileType.STAT, kql_query="count")
        d = tile.to_dict()
        self.assertEqual(d["tile_id"], "t1")
        self.assertEqual(d["tile_type"], "stat")


class TestDashboardTemplate(unittest.TestCase):
    def test_to_json(self) -> None:
        tpl = DashboardTemplate(
            name="Test Dashboard",
            pages=[DashboardPage(page_id="p1", title="Page 1")],
        )
        j = tpl.to_json()
        data = json.loads(j)
        self.assertEqual(data["name"], "Test Dashboard")
        self.assertEqual(len(data["pages"]), 1)


class TestBuildDefaultTemplate(unittest.TestCase):
    def test_default_has_three_pages(self) -> None:
        tpl = build_default_template()
        self.assertEqual(len(tpl.pages), 3)

    def test_overview_page_tiles(self) -> None:
        tpl = build_default_template()
        overview = tpl.pages[0]
        self.assertEqual(overview.page_id, "overview")
        self.assertTrue(len(overview.tiles) >= 3)

    def test_custom_database(self) -> None:
        tpl = build_default_template(database="CustomDB")
        self.assertEqual(tpl.database, "CustomDB")
        # KQL queries should reference the custom DB
        for page in tpl.pages:
            for tile in page.tiles:
                if tile.kql_query:
                    self.assertIn("CustomDB", tile.kql_query)


class TestDashboardDeployer(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def test_deploy_dry_run(self) -> None:
        deployer = DashboardDeployer(workspace_id="ws-1", dry_run=True)
        tpl = build_default_template()
        result = self._run(deployer.deploy(tpl))
        self.assertTrue(result.success)
        self.assertEqual(result.dashboard_id, "dry-run")

    def test_deploy_default(self) -> None:
        deployer = DashboardDeployer(workspace_id="ws-1")
        result = self._run(deployer.deploy_default())
        self.assertTrue(result.success)

    def test_export_template(self) -> None:
        deployer = DashboardDeployer()
        tpl = build_default_template()
        with tempfile.TemporaryDirectory() as td:
            path = deployer.export_template(tpl, f"{td}/dashboard.json")
            self.assertTrue(path.endswith("dashboard.json"))
            data = json.loads(open(path).read())
            self.assertEqual(data["name"], "OAC Migration Observability")


if __name__ == "__main__":
    unittest.main()
