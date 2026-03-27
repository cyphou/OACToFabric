"""Lineage map generator — produces JSON dependency/lineage graphs.

Generates a portable JSON representation of the full asset lineage from
the discovery inventory, suitable for visualization, impact analysis,
and migration planning.

Output schema:
{
  "version": "1.0",
  "generated_at": "ISO-8601",
  "summary": { "nodes": N, "edges": M, "layers": [...] },
  "nodes": [ { "id", "name", "asset_type", "layer", "metadata" } ],
  "edges": [ { "source", "target", "type" } ],
  "layers": { "physical": [...], "logical": [...], "presentation": [...] }
}
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Layer classification
# ---------------------------------------------------------------------------

_ASSET_TYPE_LAYER: dict[str, str] = {
    "physical_table": "physical",
    "physical_column": "physical",
    "connection_pool": "physical",
    "logical_table": "logical",
    "logical_column": "logical",
    "logical_join": "logical",
    "presentation_table": "presentation",
    "presentation_column": "presentation",
    "subject_area": "presentation",
    "analysis": "consumption",
    "dashboard": "consumption",
    "dashboard_page": "consumption",
    "prompt": "consumption",
    "agent_alert": "consumption",
    "data_flow": "etl",
    "stored_procedure": "etl",
    "schedule": "etl",
    "security_role": "security",
    "session_variable": "security",
    "initialization_block": "security",
}


@dataclass
class LineageNode:
    """A single node in the lineage graph."""

    id: str
    name: str
    asset_type: str
    layer: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type,
            "layer": self.layer,
            "metadata": self.metadata,
        }


@dataclass
class LineageEdge:
    """A directed edge in the lineage graph."""

    source: str
    target: str
    dependency_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.dependency_type,
        }


@dataclass
class LineageMap:
    """Complete lineage map with nodes, edges, and layer groupings."""

    nodes: list[LineageNode] = field(default_factory=list)
    edges: list[LineageEdge] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def layers(self) -> dict[str, list[str]]:
        """Group node IDs by layer."""
        result: dict[str, list[str]] = {}
        for node in self.nodes:
            result.setdefault(node.layer, []).append(node.id)
        return result

    def to_dict(self) -> dict[str, Any]:
        layers = self.layers
        return {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "nodes": self.node_count,
                "edges": self.edge_count,
                "layers": sorted(layers.keys()),
            },
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "layers": {k: sorted(v) for k, v in sorted(layers.items())},
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialise the lineage map to JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def impact_analysis(self, asset_id: str) -> dict[str, list[str]]:
        """Find all assets upstream and downstream of a given asset.

        Returns dict with 'upstream' (assets this depends on) and
        'downstream' (assets that depend on this).
        """
        # Build adjacency lists
        forward: dict[str, list[str]] = {}  # source → [targets]
        reverse: dict[str, list[str]] = {}  # target → [sources]
        for edge in self.edges:
            forward.setdefault(edge.source, []).append(edge.target)
            reverse.setdefault(edge.target, []).append(edge.source)

        def _bfs(start: str, adj: dict[str, list[str]]) -> list[str]:
            visited: set[str] = set()
            queue = [start]
            while queue:
                current = queue.pop(0)
                for neighbor in adj.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            return sorted(visited)

        return {
            "upstream": _bfs(asset_id, forward),
            "downstream": _bfs(asset_id, reverse),
        }


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_lineage_map(
    items: list[dict[str, Any]],
    dependencies: list[dict[str, Any]] | None = None,
) -> LineageMap:
    """Build a lineage map from inventory items and dependencies.

    Parameters
    ----------
    items
        List of inventory item dicts with at least 'id', 'name', 'asset_type'.
        May include 'metadata' and 'dependencies'.
    dependencies
        Optional separate dependency list with 'source_id', 'target_id',
        'dependency_type'. If None, dependencies are extracted from items.

    Returns
    -------
    LineageMap
        The complete lineage map ready for serialisation.
    """
    lmap = LineageMap()

    # Build nodes
    for item in items:
        asset_type = item.get("asset_type", "unknown")
        if hasattr(asset_type, "value"):
            asset_type = asset_type.value
        layer = _ASSET_TYPE_LAYER.get(str(asset_type).lower(), "other")
        lmap.nodes.append(LineageNode(
            id=item["id"],
            name=item.get("name", item["id"]),
            asset_type=str(asset_type),
            layer=layer,
            metadata=item.get("metadata", {}),
        ))

    # Build edges from explicit dependencies
    if dependencies:
        for dep in dependencies:
            lmap.edges.append(LineageEdge(
                source=dep["source_id"],
                target=dep["target_id"],
                dependency_type=dep.get("dependency_type", "depends_on"),
            ))
    else:
        # Extract from items
        for item in items:
            for dep in item.get("dependencies", []):
                src = dep.get("source_id", item["id"])
                tgt = dep.get("target_id", dep.get("id", ""))
                if src and tgt:
                    lmap.edges.append(LineageEdge(
                        source=src,
                        target=tgt,
                        dependency_type=dep.get("dependency_type", "depends_on"),
                    ))

    logger.info(
        "Lineage map built: %d nodes, %d edges, %d layers",
        lmap.node_count,
        lmap.edge_count,
        len(lmap.layers),
    )
    return lmap
