"""Tests for wave planner — partitioning inventory into migration waves."""

from __future__ import annotations

import pytest

from src.agents.orchestrator.wave_planner import (
    MigrationWave,
    WavePlan,
    plan_waves,
    render_wave_plan,
)
from src.core.models import AssetType, Inventory, InventoryItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _item(name: str, asset_type: AssetType, score: float = 0.0) -> InventoryItem:
    return InventoryItem(
        id=f"item__{name.lower()}",
        asset_type=asset_type,
        source_path=f"/{name}",
        name=name,
        complexity_score=score,
    )


def _make_inventory(items: list[InventoryItem]) -> Inventory:
    return Inventory(items=items)


# ---------------------------------------------------------------------------
# Wave planning
# ---------------------------------------------------------------------------


class TestPlanWaves:
    def test_empty_inventory(self):
        plan = plan_waves(_make_inventory([]))
        assert plan.wave_count == 0
        assert plan.total_items == 0

    def test_single_table(self):
        inv = _make_inventory([_item("Sales", AssetType.PHYSICAL_TABLE)])
        plan = plan_waves(inv)
        assert plan.wave_count == 1
        assert plan.waves[0].count == 1

    def test_tables_before_reports(self):
        inv = _make_inventory([
            _item("Dashboard", AssetType.DASHBOARD),
            _item("Sales", AssetType.PHYSICAL_TABLE),
        ])
        plan = plan_waves(inv)
        assert plan.wave_count == 2
        # First wave should be the table
        assert plan.waves[0].items[0].asset_type == AssetType.PHYSICAL_TABLE
        # Second wave should be the dashboard
        assert plan.waves[1].items[0].asset_type == AssetType.DASHBOARD

    def test_max_items_per_wave(self):
        items = [
            _item(f"T{i}", AssetType.PHYSICAL_TABLE) for i in range(10)
        ]
        plan = plan_waves(_make_inventory(items), max_items_per_wave=3)
        # 10 items / 3 = 4 waves (3+3+3+1)
        table_waves = [w for w in plan.waves if w.items[0].asset_type == AssetType.PHYSICAL_TABLE]
        assert len(table_waves) == 4
        assert table_waves[0].count == 3
        assert table_waves[3].count == 1

    def test_complexity_ordering(self):
        inv = _make_inventory([
            _item("Complex", AssetType.PHYSICAL_TABLE, score=10.0),
            _item("Simple", AssetType.PHYSICAL_TABLE, score=1.0),
        ])
        plan = plan_waves(inv)
        # Lowest complexity first
        assert plan.waves[0].items[0].name == "Simple"
        assert plan.waves[0].items[1].name == "Complex"

    def test_agent_ids_assigned(self):
        inv = _make_inventory([
            _item("T1", AssetType.PHYSICAL_TABLE),
            _item("DM", AssetType.DATA_MODEL),
            _item("R1", AssetType.ANALYSIS),
        ])
        plan = plan_waves(inv)
        assert len(plan.waves) == 3
        # Wave 1 (tables) → discovery + schema agents
        assert "01-discovery" in plan.waves[0].agent_ids
        # Wave 2 (data model) → etl + semantic + security agents
        assert "04-semantic" in plan.waves[1].agent_ids
        # Wave 3 (reports) → reports + validation agents
        assert "05-reports" in plan.waves[2].agent_ids

    def test_security_roles_wave_2(self):
        inv = _make_inventory([
            _item("Role1", AssetType.SECURITY_ROLE),
        ])
        plan = plan_waves(inv)
        assert plan.waves[0].agent_ids == ["03-etl", "04-semantic", "06-security"]

    def test_mixed_types(self):
        inv = _make_inventory([
            _item("T1", AssetType.PHYSICAL_TABLE),
            _item("T2", AssetType.LOGICAL_TABLE),
            _item("DF1", AssetType.DATA_FLOW),
            _item("R1", AssetType.ANALYSIS),
            _item("D1", AssetType.DASHBOARD),
        ])
        plan = plan_waves(inv)
        # 2 tables (wave 1) + 1 dataflow (wave 2) + 2 reports (wave 3)
        assert plan.total_items == 5
        assert plan.wave_count == 3

    def test_estimated_duration(self):
        inv = _make_inventory([
            _item("T1", AssetType.PHYSICAL_TABLE, score=5.0),
            _item("T2", AssetType.PHYSICAL_TABLE, score=3.0),
        ])
        plan = plan_waves(inv)
        assert plan.waves[0].estimated_duration_minutes >= 5


# ---------------------------------------------------------------------------
# Wave data class
# ---------------------------------------------------------------------------


class TestMigrationWave:
    def test_add(self):
        wave = MigrationWave(id=1, name="W1")
        wave.add(_item("X", AssetType.PHYSICAL_TABLE))
        assert wave.count == 1


class TestWavePlan:
    def test_total_items(self):
        plan = WavePlan(
            waves=[
                MigrationWave(
                    id=1, name="W1",
                    items=[_item("A", AssetType.PHYSICAL_TABLE)],
                )
            ],
            unassigned=[_item("B", AssetType.DASHBOARD)],
        )
        assert plan.total_items == 2
        assert plan.wave_count == 1


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class TestRenderWavePlan:
    def test_renders_markdown(self):
        inv = _make_inventory([
            _item("Sales", AssetType.PHYSICAL_TABLE),
            _item("Report", AssetType.ANALYSIS),
        ])
        plan = plan_waves(inv)
        md = render_wave_plan(plan)
        assert "Migration Wave Plan" in md
        assert "Sales" in md
        assert "Report" in md
        assert "Wave 1" in md

    def test_empty(self):
        md = render_wave_plan(WavePlan())
        assert "Migration Wave Plan" in md
