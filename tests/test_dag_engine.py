"""Tests for the DAG engine — graph construction, topological sort, status."""

from __future__ import annotations

import pytest

from src.agents.orchestrator.dag_engine import (
    DAGNode,
    ExecutionDAG,
    NodeStatus,
    build_default_migration_dag,
)


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


class TestGraphConstruction:
    def test_add_node(self):
        dag = ExecutionDAG()
        node = dag.add_node("a", "Agent A")
        assert node.id == "a"
        assert node.label == "Agent A"
        assert len(dag.nodes) == 1

    def test_add_duplicate_node_returns_existing(self):
        dag = ExecutionDAG()
        n1 = dag.add_node("a")
        n2 = dag.add_node("a")
        assert n1 is n2
        assert len(dag.nodes) == 1

    def test_add_edge(self):
        dag = ExecutionDAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        assert len(dag.edges) == 1
        assert "b" in dag.successors("a")
        assert "a" in dag.predecessors("b")

    def test_add_edge_auto_creates_nodes(self):
        dag = ExecutionDAG()
        dag.add_edge("x", "y")
        assert len(dag.nodes) == 2

    def test_self_loop_rejected(self):
        dag = ExecutionDAG()
        with pytest.raises(ValueError, match="Self-loop"):
            dag.add_edge("a", "a")

    def test_cycle_detected(self):
        dag = ExecutionDAG()
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        with pytest.raises(ValueError, match="cycle"):
            dag.add_edge("c", "a")

    def test_no_nodes(self):
        dag = ExecutionDAG()
        assert dag.nodes == []
        assert dag.edges == []
        assert dag.topological_batches() == []


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    def test_linear_chain(self):
        dag = ExecutionDAG()
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        batches = dag.topological_batches()
        assert batches == [["a"], ["b"], ["c"]]

    def test_diamond(self):
        dag = ExecutionDAG()
        dag.add_edge("a", "b")
        dag.add_edge("a", "c")
        dag.add_edge("b", "d")
        dag.add_edge("c", "d")
        batches = dag.topological_batches()
        assert len(batches) == 3
        assert batches[0] == ["a"]
        assert set(batches[1]) == {"b", "c"}
        assert batches[2] == ["d"]

    def test_independent_nodes(self):
        dag = ExecutionDAG()
        dag.add_node("x")
        dag.add_node("y")
        dag.add_node("z")
        batches = dag.topological_batches()
        assert len(batches) == 1
        assert set(batches[0]) == {"x", "y", "z"}

    def test_flat_sort(self):
        dag = ExecutionDAG()
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        assert dag.topological_sort() == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Status management
# ---------------------------------------------------------------------------


class TestStatusManagement:
    def test_mark_succeeded(self):
        dag = ExecutionDAG()
        dag.add_node("a")
        dag.mark_succeeded("a")
        assert dag.get_node("a").status == NodeStatus.SUCCEEDED

    def test_mark_failed(self):
        dag = ExecutionDAG()
        dag.add_node("a")
        dag.mark_failed("a", "boom")
        node = dag.get_node("a")
        assert node.status == NodeStatus.FAILED
        assert node.error == "boom"

    def test_ready_nodes(self):
        dag = ExecutionDAG()
        dag.add_edge("a", "b")
        dag.add_edge("a", "c")
        # Initially only 'a' is ready
        assert dag.ready_nodes() == ["a"]
        dag.mark_succeeded("a")
        # Now b and c are ready
        assert set(dag.ready_nodes()) == {"b", "c"}

    def test_block_dependents(self):
        dag = ExecutionDAG()
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        dag.add_edge("b", "d")
        dag.mark_failed("a")
        blocked = dag.block_dependents("a")
        assert set(blocked) == {"b", "c", "d"}
        assert dag.get_node("b").status == NodeStatus.BLOCKED
        assert dag.get_node("c").status == NodeStatus.BLOCKED

    def test_is_complete(self):
        dag = ExecutionDAG()
        dag.add_node("a")
        dag.add_node("b")
        assert dag.is_complete() is False
        dag.mark_succeeded("a")
        dag.mark_failed("b")
        assert dag.is_complete() is True

    def test_summary(self):
        dag = ExecutionDAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_node("c")
        dag.mark_succeeded("a")
        dag.mark_failed("b")
        s = dag.summary()
        assert s["succeeded"] == 1
        assert s["failed"] == 1
        assert s["pending"] == 1


# ---------------------------------------------------------------------------
# Default migration DAG
# ---------------------------------------------------------------------------


class TestDefaultDAG:
    def test_has_7_nodes(self):
        dag = build_default_migration_dag()
        assert len(dag.nodes) == 7

    def test_discovery_is_root(self):
        dag = build_default_migration_dag()
        assert dag.predecessors("01-discovery") == set()

    def test_validation_depends_on_all(self):
        dag = build_default_migration_dag()
        preds = dag.predecessors("07-validation")
        expected = {
            "01-discovery", "02-schema", "03-etl",
            "04-semantic", "05-reports", "06-security",
        }
        assert preds == expected

    def test_schema_depends_on_discovery(self):
        dag = build_default_migration_dag()
        assert "01-discovery" in dag.predecessors("02-schema")

    def test_etl_depends_on_schema(self):
        dag = build_default_migration_dag()
        assert "02-schema" in dag.predecessors("03-etl")

    def test_reports_depends_on_semantic(self):
        dag = build_default_migration_dag()
        assert "04-semantic" in dag.predecessors("05-reports")

    def test_security_depends_on_semantic(self):
        dag = build_default_migration_dag()
        assert "04-semantic" in dag.predecessors("06-security")

    def test_topological_batches_valid(self):
        dag = build_default_migration_dag()
        batches = dag.topological_batches()
        assert len(batches) >= 3
        # Discovery always first
        assert "01-discovery" in batches[0]
        # Validation always last
        assert "07-validation" in batches[-1]

    def test_parallel_agents(self):
        dag = build_default_migration_dag()
        batches = dag.topological_batches()
        # Batch 2 should contain schema + semantic (parallel)
        assert len(batches[1]) >= 2
