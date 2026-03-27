"""DAG engine — resolve agent execution order via topological sort.

Provides a lightweight directed-acyclic-graph implementation that determines
which agents can run in parallel and which must wait for predecessors.

Key concepts
------------
- **Node**: An agent ID (e.g. ``"01-discovery"``).
- **Edge**: A dependency from one agent to another
  (``A → B`` means *B depends on A* — A must finish before B starts.)
- **Topological batches**: Groups of nodes that can execute in parallel;
  within a batch every node's predecessors have already completed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class NodeStatus(str, Enum):
    """Execution status of a DAG node."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class DAGNode:
    """A single node in the execution DAG."""

    id: str
    label: str = ""
    status: NodeStatus = NodeStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    error: str = ""


@dataclass
class DAGEdge:
    """A directed edge: *source* must complete before *target*."""

    source: str
    target: str


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------


class ExecutionDAG:
    """Directed acyclic graph with topological batch execution."""

    def __init__(self) -> None:
        self._nodes: dict[str, DAGNode] = {}
        self._edges: list[DAGEdge] = []
        # Adjacency lists (forward & reverse)
        self._successors: dict[str, set[str]] = {}
        self._predecessors: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def add_node(self, node_id: str, label: str = "", **meta: Any) -> DAGNode:
        """Add a node (agent) to the DAG."""
        if node_id in self._nodes:
            return self._nodes[node_id]
        node = DAGNode(id=node_id, label=label or node_id, metadata=meta)
        self._nodes[node_id] = node
        self._successors.setdefault(node_id, set())
        self._predecessors.setdefault(node_id, set())
        return node

    def add_edge(self, source: str, target: str) -> None:
        """Add a dependency edge: *source* must finish before *target*.

        Both nodes are auto-created if they don't already exist.

        Raises
        ------
        ValueError
            If the edge would create a cycle.
        """
        self.add_node(source)
        self.add_node(target)

        if source == target:
            raise ValueError(f"Self-loop not allowed: {source}")

        # Check for cycle before adding
        if self._would_create_cycle(source, target):
            raise ValueError(
                f"Adding edge {source} → {target} would create a cycle"
            )

        edge = DAGEdge(source=source, target=target)
        self._edges.append(edge)
        self._successors[source].add(target)
        self._predecessors[target].add(source)

    def _would_create_cycle(self, source: str, target: str) -> bool:
        """Return True if adding target → ... → source path exists."""
        # If we add source→target, there's a cycle iff there is already
        # a path from target back to source.
        visited: set[str] = set()
        stack = [target]
        while stack:
            node = stack.pop()
            if node == source:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(self._successors.get(node, set()))
        # Also need to check the reverse path: is source reachable from target
        # already? Yes - that's what we just checked.
        return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def nodes(self) -> list[DAGNode]:
        return list(self._nodes.values())

    @property
    def node_ids(self) -> list[str]:
        return list(self._nodes.keys())

    @property
    def edges(self) -> list[DAGEdge]:
        return list(self._edges)

    def get_node(self, node_id: str) -> DAGNode | None:
        return self._nodes.get(node_id)

    def predecessors(self, node_id: str) -> set[str]:
        return set(self._predecessors.get(node_id, set()))

    def successors(self, node_id: str) -> set[str]:
        return set(self._successors.get(node_id, set()))

    # ------------------------------------------------------------------
    # Topological sort — Kahn's algorithm producing batches
    # ------------------------------------------------------------------

    def topological_batches(self) -> list[list[str]]:
        """Return nodes grouped into execution batches.

        Within each batch, all nodes are independent and can run in
        parallel.  Batches are returned in dependency order — every node
        in batch *n+1* depends only on nodes from batches ≤ *n*.

        Raises
        ------
        ValueError
            If the graph contains a cycle.
        """
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] += 1

        # Start with zero-in-degree nodes
        ready = [nid for nid, deg in in_degree.items() if deg == 0]
        batches: list[list[str]] = []
        processed = 0

        while ready:
            batches.append(sorted(ready))
            next_ready: list[str] = []
            for nid in ready:
                processed += 1
                for succ in self._successors.get(nid, set()):
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        next_ready.append(succ)
            ready = next_ready

        if processed != len(self._nodes):
            raise ValueError(
                "Cycle detected — cannot produce topological order"
            )

        return batches

    def topological_sort(self) -> list[str]:
        """Return a flat topological ordering (batch order preserved)."""
        result: list[str] = []
        for batch in self.topological_batches():
            result.extend(batch)
        return result

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def ready_nodes(self) -> list[str]:
        """Return nodes whose predecessors have all succeeded."""
        ready: list[str] = []
        for nid, node in self._nodes.items():
            if node.status != NodeStatus.PENDING:
                continue
            preds = self._predecessors.get(nid, set())
            if all(
                self._nodes[p].status == NodeStatus.SUCCEEDED for p in preds
            ):
                ready.append(nid)
        return sorted(ready)

    def mark_succeeded(self, node_id: str) -> None:
        node = self._nodes[node_id]
        node.status = NodeStatus.SUCCEEDED

    def mark_failed(self, node_id: str, error: str = "") -> None:
        node = self._nodes[node_id]
        node.status = NodeStatus.FAILED
        node.error = error

    def mark_running(self, node_id: str) -> None:
        self._nodes[node_id].status = NodeStatus.RUNNING

    def mark_skipped(self, node_id: str) -> None:
        self._nodes[node_id].status = NodeStatus.SKIPPED

    def mark_blocked(self, node_id: str) -> None:
        self._nodes[node_id].status = NodeStatus.BLOCKED

    def block_dependents(self, node_id: str) -> list[str]:
        """Mark all transitive successors of *node_id* as BLOCKED.

        Returns the list of blocked node IDs.
        """
        blocked: list[str] = []
        stack = list(self._successors.get(node_id, set()))
        visited: set[str] = set()
        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            if self._nodes[nid].status == NodeStatus.PENDING:
                self._nodes[nid].status = NodeStatus.BLOCKED
                blocked.append(nid)
            stack.extend(self._successors.get(nid, set()))
        return sorted(blocked)

    def is_complete(self) -> bool:
        """True if every node has a terminal status."""
        terminal = {
            NodeStatus.SUCCEEDED,
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
            NodeStatus.BLOCKED,
        }
        return all(n.status in terminal for n in self._nodes.values())

    def summary(self) -> dict[str, int]:
        """Count nodes by status."""
        counts: dict[str, int] = {}
        for node in self._nodes.values():
            counts[node.status.value] = counts.get(node.status.value, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Default migration DAG — standard 7-agent dependency graph
# ---------------------------------------------------------------------------


def build_default_migration_dag() -> ExecutionDAG:
    """Build the standard OAC → Fabric migration DAG.

    Encodes the dependency rules from the AGENTS.md architecture::

        01-discovery → 02-schema, 04-semantic
        02-schema    → 03-etl
        01-discovery → 04-semantic
        04-semantic  → 05-reports, 06-security
        01,02,03,04,05,06 → 07-validation
    """
    dag = ExecutionDAG()

    # Add all agent nodes
    dag.add_node("01-discovery", "Discovery & Inventory Agent")
    dag.add_node("02-schema", "Schema & Data Model Migration Agent")
    dag.add_node("03-etl", "ETL/Data Pipeline Migration Agent")
    dag.add_node("04-semantic", "Semantic Model Migration Agent")
    dag.add_node("05-reports", "Report & Dashboard Migration Agent")
    dag.add_node("06-security", "Security & Governance Migration Agent")
    dag.add_node("07-validation", "Validation & Testing Agent")

    # Dependency edges
    dag.add_edge("01-discovery", "02-schema")
    dag.add_edge("01-discovery", "04-semantic")
    dag.add_edge("02-schema", "03-etl")
    dag.add_edge("04-semantic", "05-reports")
    dag.add_edge("04-semantic", "06-security")

    # Validation depends on everything
    for agent in ["01-discovery", "02-schema", "03-etl",
                  "04-semantic", "05-reports", "06-security"]:
        dag.add_edge(agent, "07-validation")

    return dag


# ---------------------------------------------------------------------------
# Dead letter queue (Phase 49)
# ---------------------------------------------------------------------------


@dataclass
class DeadLetterEntry:
    """A permanently failed task moved to the dead letter queue."""

    node_id: str
    error: str
    retry_count: int
    blocked_dependents: list[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "error": self.error,
            "retry_count": self.retry_count,
            "blocked_dependents": self.blocked_dependents,
            "timestamp": self.timestamp,
        }


class DeadLetterQueue:
    """Dead letter queue for permanently failed DAG nodes.

    After a node exhausts retries, it is moved to the DLQ.
    Dependents are blocked and recorded.
    """

    def __init__(self) -> None:
        self._entries: list[DeadLetterEntry] = []

    @property
    def entries(self) -> list[DeadLetterEntry]:
        return list(self._entries)

    @property
    def count(self) -> int:
        return len(self._entries)

    def add(
        self,
        dag: ExecutionDAG,
        node_id: str,
        error: str = "",
    ) -> DeadLetterEntry:
        """Move a failed node to the DLQ and block its dependents.

        Args:
            dag: The execution DAG
            node_id: Node that permanently failed
            error: Error description

        Returns:
            DeadLetterEntry with blocked dependents
        """
        node = dag.get_node(node_id)
        retry_count = node.retry_count if node else 0

        # Mark failed and block dependents
        dag.mark_failed(node_id, error)
        blocked = dag.block_dependents(node_id)

        import datetime
        entry = DeadLetterEntry(
            node_id=node_id,
            error=error,
            retry_count=retry_count,
            blocked_dependents=blocked,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        self._entries.append(entry)
        logger.warning(
            "DLQ: Node '%s' failed permanently (retries=%d, blocked=%d dependents)",
            node_id, retry_count, len(blocked),
        )
        return entry

    def to_json(self) -> str:
        """Serialize the DLQ to JSON."""
        import json
        return json.dumps(
            {"dead_letter_queue": [e.to_dict() for e in self._entries]},
            indent=2,
        )

    def summary(self) -> str:
        """Return a human-readable summary."""
        if not self._entries:
            return "DLQ: empty — all tasks succeeded or are in-progress."
        lines = [f"Dead Letter Queue: {self.count} entries"]
        for e in self._entries:
            lines.append(
                f"  - {e.node_id}: {e.error} "
                f"(retries={e.retry_count}, blocked={len(e.blocked_dependents)})"
            )
        return "\n".join(lines)
