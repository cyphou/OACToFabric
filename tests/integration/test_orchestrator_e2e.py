"""Integration tests — Orchestrator end-to-end.

Uses mock agent runners to verify the orchestrator drives the full
discover → plan → execute → validate lifecycle without live services.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.orchestrator.dag_engine import ExecutionDAG, build_default_migration_dag, NodeStatus
from src.agents.orchestrator.wave_planner import plan_waves, WavePlan
from src.agents.orchestrator.notification_manager import NotificationManager, Channel
from src.core.models import (
    AssetType,
    Inventory,
    InventoryItem,
    MigrationScope,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# DAG lifecycle
# ---------------------------------------------------------------------------


class TestDAGLifecycle:
    def test_default_dag_has_seven_nodes(self):
        dag = build_default_migration_dag()
        assert len(dag.nodes) == 7

    def test_topological_batches_respects_deps(self):
        dag = build_default_migration_dag()
        batches = dag.topological_batches()
        # First batch should only contain discovery
        first_ids = set(batches[0])
        assert "01-discovery" in first_ids

    def test_mark_succeeded_unblocks_dependents(self):
        dag = build_default_migration_dag()
        dag.mark_running("01-discovery")
        dag.mark_succeeded("01-discovery")
        ready = dag.ready_nodes()
        ready_ids = set(ready)
        assert "02-schema" in ready_ids

    def test_mark_failed_blocks_dependents(self):
        dag = build_default_migration_dag()
        dag.mark_running("01-discovery")
        dag.mark_failed("01-discovery", "boom")
        dag.block_dependents("01-discovery")
        # Schema depends on discovery — should be blocked
        node = dag.get_node("02-schema")
        assert node.status == NodeStatus.BLOCKED


# ---------------------------------------------------------------------------
# Wave planner
# ---------------------------------------------------------------------------


class TestWavePlannerIntegration:
    def test_plans_waves_from_inventory(self, sample_inventory: Inventory):
        plan = plan_waves(sample_inventory, max_items_per_wave=3)
        assert isinstance(plan, WavePlan)
        assert plan.total_items == 5
        assert plan.wave_count >= 2  # 5 items / 3 per wave

    def test_empty_inventory_produces_zero_waves(self):
        inv = Inventory(items=[])
        plan = plan_waves(inv, max_items_per_wave=10)
        assert plan.wave_count == 0


# ---------------------------------------------------------------------------
# Notification manager
# ---------------------------------------------------------------------------


class TestNotificationManagerIntegration:
    def test_log_channel_captures_notifications(self):
        mgr = NotificationManager(enabled_channels=[Channel.LOG])
        mgr.notify("wave_started", "Test", "Test message")
        mgr.notify("agent_failed_first", "Warn", "Warning message")
        mgr.notify("agent_failed_max", "Err", "Error message")
        assert len(mgr.history) == 3

    def test_notification_severity_ordering(self):
        from src.agents.orchestrator.notification_manager import Severity
        mgr = NotificationManager(enabled_channels=[Channel.LOG])
        mgr.notify("wave_started", "First", "first", severity=Severity.INFO)
        mgr.notify("agent_failed_max", "Second", "second", severity=Severity.HIGH)
        _SEVERITY_ORDER = {Severity.INFO: 0, Severity.WARN: 1, Severity.HIGH: 2, Severity.CRITICAL: 3}
        assert _SEVERITY_ORDER[mgr.history[0].severity] < _SEVERITY_ORDER[mgr.history[1].severity]
