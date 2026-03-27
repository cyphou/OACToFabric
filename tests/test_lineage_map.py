"""Tests for lineage map generator (Agent 01 — Discovery)."""

import json
import unittest

from src.agents.discovery.lineage_map import (
    LineageEdge,
    LineageMap,
    LineageNode,
    build_lineage_map,
)


class TestLineageNode(unittest.TestCase):
    def test_to_dict(self):
        node = LineageNode(
            id="t1", name="Sales", asset_type="physical_table", layer="physical"
        )
        d = node.to_dict()
        assert d["id"] == "t1"
        assert d["name"] == "Sales"
        assert d["layer"] == "physical"

    def test_metadata_default_empty(self):
        node = LineageNode(id="x", name="X", asset_type="a", layer="b")
        assert node.metadata == {}


class TestLineageEdge(unittest.TestCase):
    def test_to_dict(self):
        edge = LineageEdge(source="a", target="b", dependency_type="depends_on")
        d = edge.to_dict()
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["type"] == "depends_on"


class TestLineageMap(unittest.TestCase):
    def _make_map(self) -> LineageMap:
        lm = LineageMap()
        lm.nodes = [
            LineageNode("t1", "Sales", "physical_table", "physical"),
            LineageNode("l1", "Sales_Logical", "logical_table", "logical"),
            LineageNode("a1", "Revenue Dashboard", "analysis", "consumption"),
        ]
        lm.edges = [
            LineageEdge("l1", "t1", "depends_on"),
            LineageEdge("a1", "l1", "uses"),
        ]
        return lm

    def test_node_count(self):
        lm = self._make_map()
        assert lm.node_count == 3

    def test_edge_count(self):
        lm = self._make_map()
        assert lm.edge_count == 2

    def test_layers(self):
        lm = self._make_map()
        layers = lm.layers
        assert "physical" in layers
        assert "logical" in layers
        assert "consumption" in layers
        assert "t1" in layers["physical"]

    def test_to_dict_structure(self):
        lm = self._make_map()
        d = lm.to_dict()
        assert d["version"] == "1.0"
        assert "generated_at" in d
        assert d["summary"]["nodes"] == 3
        assert d["summary"]["edges"] == 2
        assert len(d["nodes"]) == 3
        assert len(d["edges"]) == 2

    def test_to_json(self):
        lm = self._make_map()
        j = lm.to_json()
        parsed = json.loads(j)
        assert parsed["version"] == "1.0"
        assert len(parsed["nodes"]) == 3

    def test_impact_analysis_downstream(self):
        lm = self._make_map()
        impact = lm.impact_analysis("t1")
        assert "l1" in impact["downstream"]

    def test_impact_analysis_upstream(self):
        lm = self._make_map()
        impact = lm.impact_analysis("a1")
        assert "l1" in impact["upstream"]

    def test_impact_analysis_unknown_id(self):
        lm = self._make_map()
        impact = lm.impact_analysis("nonexistent")
        assert impact["upstream"] == []
        assert impact["downstream"] == []

    def test_empty_map(self):
        lm = LineageMap()
        assert lm.node_count == 0
        assert lm.edge_count == 0
        d = lm.to_dict()
        assert d["summary"]["nodes"] == 0


class TestBuildLineageMap(unittest.TestCase):
    def test_build_from_items(self):
        items = [
            {"id": "t1", "name": "Sales", "asset_type": "physical_table"},
            {"id": "l1", "name": "Sales_Logical", "asset_type": "logical_table"},
        ]
        deps = [
            {"source_id": "l1", "target_id": "t1", "dependency_type": "depends_on"},
        ]
        lm = build_lineage_map(items, deps)
        assert lm.node_count == 2
        assert lm.edge_count == 1
        assert lm.nodes[0].layer == "physical"
        assert lm.nodes[1].layer == "logical"

    def test_build_extracts_deps_from_items(self):
        items = [
            {
                "id": "a1",
                "name": "Dashboard",
                "asset_type": "analysis",
                "dependencies": [
                    {"source_id": "a1", "target_id": "t1", "dependency_type": "uses"},
                ],
            },
            {"id": "t1", "name": "Table", "asset_type": "physical_table"},
        ]
        lm = build_lineage_map(items)
        assert lm.edge_count == 1

    def test_unknown_asset_type_layer(self):
        items = [{"id": "x", "name": "X", "asset_type": "custom_widget"}]
        lm = build_lineage_map(items)
        assert lm.nodes[0].layer == "other"

    def test_enum_asset_type(self):
        """Asset types with .value attribute (enum-like) handled."""
        class FakeEnum:
            value = "physical_table"
        items = [{"id": "t1", "name": "T", "asset_type": FakeEnum()}]
        lm = build_lineage_map(items)
        assert lm.nodes[0].asset_type == "physical_table"
        assert lm.nodes[0].layer == "physical"

    def test_multiple_layers(self):
        items = [
            {"id": "pt1", "name": "PT", "asset_type": "physical_table"},
            {"id": "lt1", "name": "LT", "asset_type": "logical_table"},
            {"id": "sa1", "name": "SA", "asset_type": "subject_area"},
            {"id": "an1", "name": "AN", "asset_type": "analysis"},
            {"id": "df1", "name": "DF", "asset_type": "data_flow"},
            {"id": "sr1", "name": "SR", "asset_type": "security_role"},
        ]
        lm = build_lineage_map(items)
        assert lm.node_count == 6
        layers = lm.layers
        assert "physical" in layers
        assert "logical" in layers
        assert "presentation" in layers
        assert "consumption" in layers
        assert "etl" in layers
        assert "security" in layers


if __name__ == "__main__":
    unittest.main()
