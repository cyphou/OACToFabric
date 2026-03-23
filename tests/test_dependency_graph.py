"""Tests for dependency graph builder."""

from __future__ import annotations

import pytest

from src.agents.discovery.dependency_graph import DependencyGraph
from src.core.models import AssetType, Dependency, InventoryItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(id: str, asset_type: AssetType, deps: list[Dependency] | None = None) -> InventoryItem:
    return InventoryItem(
        id=id,
        asset_type=asset_type,
        source_path=f"/test/{id}",
        name=id,
        dependencies=deps or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_build_basic(self):
        items = [
            _item("dashboard_1", AssetType.DASHBOARD, [
                Dependency(source_id="dashboard_1", target_id="analysis_1", dependency_type="embeds_analysis"),
            ]),
            _item("analysis_1", AssetType.ANALYSIS, [
                Dependency(source_id="analysis_1", target_id="sa_1", dependency_type="uses_subject_area"),
            ]),
            _item("sa_1", AssetType.SUBJECT_AREA),
        ]

        graph = DependencyGraph()
        graph.build(items)

        assert graph.node_count == 3
        assert graph.edge_count == 2

    def test_direct_dependencies(self):
        items = [
            _item("d1", AssetType.DASHBOARD, [
                Dependency(source_id="d1", target_id="a1", dependency_type="embeds"),
            ]),
            _item("a1", AssetType.ANALYSIS, [
                Dependency(source_id="a1", target_id="sa1", dependency_type="uses"),
            ]),
            _item("sa1", AssetType.SUBJECT_AREA),
        ]
        graph = DependencyGraph()
        graph.build(items)

        assert graph.direct_dependencies("d1") == ["a1"]
        assert graph.direct_dependencies("a1") == ["sa1"]
        assert graph.direct_dependencies("sa1") == []

    def test_upstream_gives_transitive(self):
        items = [
            _item("d1", AssetType.DASHBOARD, [
                Dependency(source_id="d1", target_id="a1", dependency_type="embeds"),
            ]),
            _item("a1", AssetType.ANALYSIS, [
                Dependency(source_id="a1", target_id="sa1", dependency_type="uses"),
            ]),
            _item("sa1", AssetType.SUBJECT_AREA),
        ]
        graph = DependencyGraph()
        graph.build(items)

        upstream = graph.upstream("d1")
        assert "a1" in upstream
        assert "sa1" in upstream

    def test_roots_and_leaves(self):
        items = [
            _item("d1", AssetType.DASHBOARD, [
                Dependency(source_id="d1", target_id="a1", dependency_type="embeds"),
            ]),
            _item("a1", AssetType.ANALYSIS),
        ]
        graph = DependencyGraph()
        graph.build(items)

        assert "d1" in graph.roots()
        assert "a1" in graph.leaves()

    def test_no_cycles(self):
        items = [
            _item("a", AssetType.ANALYSIS, [
                Dependency(source_id="a", target_id="b", dependency_type="uses"),
            ]),
            _item("b", AssetType.SUBJECT_AREA),
        ]
        graph = DependencyGraph()
        graph.build(items)
        assert not graph.has_cycles()

    def test_connected_components(self):
        items = [
            _item("a", AssetType.ANALYSIS, [
                Dependency(source_id="a", target_id="b", dependency_type="uses"),
            ]),
            _item("b", AssetType.SUBJECT_AREA),
            _item("c", AssetType.DASHBOARD),  # Isolated
        ]
        graph = DependencyGraph()
        graph.build(items)
        components = graph.connected_components()
        assert len(components) == 2

    def test_summary(self):
        items = [
            _item("a", AssetType.ANALYSIS, [
                Dependency(source_id="a", target_id="b", dependency_type="uses"),
            ]),
            _item("b", AssetType.SUBJECT_AREA),
        ]
        graph = DependencyGraph()
        graph.build(items)
        s = graph.summary()
        assert s["total_nodes"] == 2
        assert s["total_edges"] == 1
        assert "analysis" in s["asset_type_counts"]

    def test_to_adjacency_list(self):
        items = [
            _item("a", AssetType.ANALYSIS, [
                Dependency(source_id="a", target_id="b", dependency_type="uses"),
            ]),
            _item("b", AssetType.SUBJECT_AREA),
        ]
        graph = DependencyGraph()
        graph.build(items)
        adj = graph.to_adjacency_list()
        assert "a" in adj
        assert adj["a"][0]["target_id"] == "b"

    def test_empty_graph(self):
        graph = DependencyGraph()
        graph.build([])
        assert graph.node_count == 0
        assert graph.edge_count == 0
        assert graph.roots() == []
        assert graph.leaves() == []

    def test_topological_order(self):
        items = [
            _item("a", AssetType.ANALYSIS, [
                Dependency(source_id="a", target_id="b", dependency_type="uses"),
            ]),
            _item("b", AssetType.SUBJECT_AREA, [
                Dependency(source_id="b", target_id="c", dependency_type="presents"),
            ]),
            _item("c", AssetType.PHYSICAL_TABLE),
        ]
        graph = DependencyGraph()
        graph.build(items)
        order = graph.topological_order()
        # Leaves first: c before b before a
        assert order.index("c") < order.index("b")
        assert order.index("b") < order.index("a")
