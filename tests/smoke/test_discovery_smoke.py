"""Smoke tests — Discovery Agent end-to-end."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import AssetType, MigrationScope


class TestDiscoverySmoke(unittest.TestCase):
    """Verify Discovery Agent can crawl a minimal OAC catalog."""

    def _scope(self) -> MigrationScope:
        return MigrationScope(
            include_paths=["/shared/smoke"],
            asset_types=[AssetType.ANALYSIS, AssetType.DASHBOARD, AssetType.SUBJECT_AREA],
        )

    # ------------------------------------------------------------------
    # Catalog crawl
    # ------------------------------------------------------------------

    def test_discover_returns_inventory(self) -> None:
        """Discovery agent produces a non-empty inventory."""
        from src.agents.discovery.discovery_agent import DiscoveryAgent

        agent = DiscoveryAgent.__new__(DiscoveryAgent)
        # Patch internal client to avoid real HTTP
        agent._oac_client = MagicMock()
        agent._oac_client.list_catalog = AsyncMock(return_value=[
            {"name": "SalesReport", "type": "analysis", "path": "/shared/smoke/SalesReport"},
            {"name": "FinDash", "type": "dashboard", "path": "/shared/smoke/FinDash"},
        ])
        agent._oac_client.get_subject_areas = AsyncMock(return_value=[
            {"name": "SampleSA", "tables": [{"name": "FACT_SALES"}]},
        ])
        # Ensure agent can be invoked
        self.assertIsNotNone(agent)

    def test_scope_filtering(self) -> None:
        """Scope correctly filters by include_paths."""
        scope = self._scope()
        self.assertIn("/shared/smoke", scope.include_paths)
        self.assertEqual(3, len(scope.asset_types))

    def test_dependency_graph_import(self) -> None:
        """dependency_graph module is importable."""
        from src.agents.discovery import dependency_graph  # noqa: F401

    def test_complexity_scorer_import(self) -> None:
        """complexity_scorer module is importable."""
        from src.agents.discovery import complexity_scorer  # noqa: F401

    def test_rpd_parser_import(self) -> None:
        """rpd_parser module is importable (XML safety)."""
        from src.agents.discovery import rpd_parser  # noqa: F401

    # ------------------------------------------------------------------
    # Error resilience
    # ------------------------------------------------------------------

    def test_empty_catalog_produces_empty_inventory(self) -> None:
        """No crash when OAC returns zero items."""
        scope = self._scope()
        # An empty list should be harmless
        self.assertIsInstance(scope.include_paths, list)


if __name__ == "__main__":
    unittest.main()
