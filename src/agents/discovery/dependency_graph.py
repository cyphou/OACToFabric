"""Dependency graph builder — build and query a directed graph of asset dependencies.

Uses networkx to represent:
  Analysis → SubjectArea → LogicalTable → PhysicalTable
  Dashboard → Analysis
  DataFlow → Source/Target tables
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx

from src.core.models import Dependency, InventoryItem

logger = logging.getLogger(__name__)


class DependencyGraph:
    """Directed acyclic graph of asset dependencies."""

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, items: list[InventoryItem]) -> None:
        """Build the graph from a list of inventory items."""
        # Add every item as a node
        for item in items:
            self._graph.add_node(
                item.id,
                asset_type=item.asset_type.value,
                name=item.name,
                source_path=item.source_path,
            )

        # Add dependency edges
        edge_count = 0
        for item in items:
            for dep in item.dependencies:
                self._graph.add_edge(
                    dep.source_id,
                    dep.target_id,
                    dependency_type=dep.dependency_type,
                )
                edge_count += 1

        logger.info(
            "Dependency graph: %d nodes, %d edges",
            self._graph.number_of_nodes(),
            edge_count,
        )

    def add_dependency(self, dep: Dependency) -> None:
        """Add a single dependency edge."""
        self._graph.add_edge(
            dep.source_id, dep.target_id, dependency_type=dep.dependency_type
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def upstream(self, asset_id: str) -> list[str]:
        """Assets that this asset depends on (successors — things it points to)."""
        if asset_id not in self._graph:
            return []
        return list(nx.descendants(self._graph, asset_id))

    def downstream(self, asset_id: str) -> list[str]:
        """Assets that depend on this asset (predecessors — things that point to it)."""
        if asset_id not in self._graph:
            return []
        return list(nx.ancestors(self._graph, asset_id))

    def direct_dependencies(self, asset_id: str) -> list[str]:
        """Direct successors only."""
        if asset_id not in self._graph:
            return []
        return list(self._graph.successors(asset_id))

    def direct_dependents(self, asset_id: str) -> list[str]:
        """Direct predecessors only."""
        if asset_id not in self._graph:
            return []
        return list(self._graph.predecessors(asset_id))

    def roots(self) -> list[str]:
        """Nodes with no incoming edges (top-level assets like dashboards)."""
        return [n for n in self._graph.nodes() if self._graph.in_degree(n) == 0]

    def leaves(self) -> list[str]:
        """Nodes with no outgoing edges (leaf assets like physical tables)."""
        return [n for n in self._graph.nodes() if self._graph.out_degree(n) == 0]

    def has_cycles(self) -> bool:
        return not nx.is_directed_acyclic_graph(self._graph)

    def topological_order(self) -> list[str]:
        """Return nodes in topological order (leaves first)."""
        if self.has_cycles():
            logger.warning("Dependency graph has cycles — returning best-effort order")
            return list(nx.topological_sort(nx.DiGraph(self._graph)))  # copy to break cycles
        return list(reversed(list(nx.topological_sort(self._graph))))

    def connected_components(self) -> list[set[str]]:
        """Return weakly connected components."""
        return [set(c) for c in nx.weakly_connected_components(self._graph)]

    def subgraph(self, asset_ids: set[str]) -> "DependencyGraph":
        """Return a new DependencyGraph containing only the given nodes and their edges."""
        g = DependencyGraph()
        g._graph = self._graph.subgraph(asset_ids).copy()
        return g

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_adjacency_list(self) -> dict[str, list[dict[str, str]]]:
        """Export as adjacency list: {source_id: [{target_id, dependency_type}]}."""
        result: dict[str, list[dict[str, str]]] = {}
        for src, tgt, data in self._graph.edges(data=True):
            result.setdefault(src, []).append(
                {"target_id": tgt, "dependency_type": data.get("dependency_type", "")}
            )
        return result

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of the graph."""
        type_counts: dict[str, int] = {}
        for _, data in self._graph.nodes(data=True):
            t = data.get("asset_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "has_cycles": self.has_cycles(),
            "connected_components": len(self.connected_components()),
            "root_count": len(self.roots()),
            "leaf_count": len(self.leaves()),
            "asset_type_counts": type_counts,
        }
