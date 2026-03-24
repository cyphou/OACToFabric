"""Tests for the Migration Analytics Dashboard (Phase 43).

Covers:
- AgentMetrics, WaveMetrics, CostMetrics, MigrationMetrics models
- MetricsCollector — snapshot creation, wave/agent updates
- DashboardDataExporter — JSON/CSV export
- PBITTemplateGenerator — manifest generation
- ExecutiveSummary computation
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.plugins.analytics_dashboard import (
    AgentMetrics,
    CostMetrics,
    DashboardDataExporter,
    ExecutiveSummary,
    MetricsCollector,
    MigrationMetrics,
    PBITTemplateGenerator,
    WaveMetrics,
)


# ===================================================================
# AgentMetrics
# ===================================================================


class TestAgentMetrics:
    def test_defaults(self):
        m = AgentMetrics(agent_id="01")
        assert m.status == "pending"
        assert m.progress_pct == 0.0

    def test_progress_pct(self):
        m = AgentMetrics(agent_id="01", items_total=100, items_completed=75)
        assert m.progress_pct == 75.0

    def test_success_rate(self):
        m = AgentMetrics(agent_id="01", items_completed=8, items_failed=2)
        assert m.success_rate == 80.0

    def test_zero_total(self):
        m = AgentMetrics(agent_id="01")
        assert m.progress_pct == 0.0
        assert m.success_rate == 0.0


# ===================================================================
# WaveMetrics
# ===================================================================


class TestWaveMetrics:
    def test_defaults(self):
        w = WaveMetrics(wave_number=1)
        assert w.total_items == 0
        assert w.progress_pct == 0.0

    def test_aggregation(self):
        w = WaveMetrics(
            wave_number=1,
            agents=[
                AgentMetrics(agent_id="01", items_total=50, items_completed=30),
                AgentMetrics(agent_id="02", items_total=30, items_completed=20),
            ],
        )
        assert w.total_items == 80
        assert w.completed_items == 50
        assert w.progress_pct == 62.5


# ===================================================================
# CostMetrics
# ===================================================================


class TestCostMetrics:
    def test_defaults(self):
        c = CostMetrics()
        assert c.budget_remaining_pct == 100.0

    def test_budget_usage(self):
        c = CostMetrics(estimated_cost_usd=800, budget_usd=1000)
        assert c.budget_remaining_pct == 20.0

    def test_zero_budget(self):
        c = CostMetrics(budget_usd=0)
        assert c.budget_remaining_pct == 100.0


# ===================================================================
# MigrationMetrics
# ===================================================================


class TestMigrationMetrics:
    def test_defaults(self):
        m = MigrationMetrics()
        assert m.overall_progress_pct == 0.0
        assert m.wave_count == 0

    def test_progress(self):
        m = MigrationMetrics(total_assets=200, assets_migrated=150)
        assert m.overall_progress_pct == 75.0

    def test_wave_count(self):
        m = MigrationMetrics(waves=[WaveMetrics(wave_number=1), WaveMetrics(wave_number=2)])
        assert m.wave_count == 2

    def test_completed_wave_count(self):
        m = MigrationMetrics(waves=[
            WaveMetrics(wave_number=1, status="completed"),
            WaveMetrics(wave_number=2, status="running"),
        ])
        assert m.completed_wave_count == 1

    def test_to_dict(self):
        m = MigrationMetrics(migration_id="m1", total_assets=10)
        d = m.to_dict()
        assert d["migration_id"] == "m1"
        assert d["total_assets"] == 10


# ===================================================================
# MetricsCollector
# ===================================================================


class TestMetricsCollector:
    def test_create_snapshot(self):
        c = MetricsCollector()
        m = c.create_snapshot("run-1", total_assets=100)
        assert m.migration_id == "run-1"
        assert m.total_assets == 100
        assert c.snapshot_count == 1

    def test_latest(self):
        c = MetricsCollector()
        c.create_snapshot("a")
        m = c.create_snapshot("b")
        assert c.latest.migration_id == "b"

    def test_latest_empty(self):
        c = MetricsCollector()
        assert c.latest is None

    def test_add_wave(self):
        c = MetricsCollector()
        m = c.create_snapshot("run-1")
        agents = [AgentMetrics(agent_id="01", items_total=50)]
        wave = c.add_wave(m, 1, agents)
        assert wave.wave_number == 1
        assert m.wave_count == 1

    def test_update_agent(self):
        c = MetricsCollector()
        m = c.create_snapshot("run-1")
        c.add_wave(m, 1, [AgentMetrics(agent_id="01", items_total=50)])
        result = c.update_agent(m, "01", status="completed", items_completed=48, items_failed=2)
        assert result is not None
        assert result.status == "completed"
        assert result.items_completed == 48

    def test_update_agent_missing(self):
        c = MetricsCollector()
        m = c.create_snapshot("run-1")
        assert c.update_agent(m, "99", status="x") is None

    def test_compute_totals(self):
        c = MetricsCollector()
        m = c.create_snapshot("run-1", total_assets=100)
        c.add_wave(m, 1, [
            AgentMetrics(agent_id="01", items_completed=30, items_failed=2),
            AgentMetrics(agent_id="02", items_completed=20, items_failed=1),
        ])
        c.compute_totals(m)
        assert m.assets_migrated == 50
        assert m.assets_failed == 3


# ===================================================================
# DashboardDataExporter
# ===================================================================


class TestDashboardDataExporter:
    def _sample_metrics(self) -> MigrationMetrics:
        return MigrationMetrics(
            migration_id="test-export",
            total_assets=100,
            assets_migrated=75,
            waves=[WaveMetrics(
                wave_number=1,
                status="completed",
                agents=[
                    AgentMetrics(agent_id="01", agent_name="Discovery", items_total=50, items_completed=50, duration_seconds=120),
                    AgentMetrics(agent_id="02", agent_name="Schema", items_total=30, items_completed=25, items_failed=5, duration_seconds=300),
                ],
            )],
        )

    def test_export_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = DashboardDataExporter(tmpdir)
            path = exporter.export_json(self._sample_metrics())
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["migration_id"] == "test-export"

    def test_export_agent_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = DashboardDataExporter(tmpdir)
            path = exporter.export_agent_csv(self._sample_metrics())
            assert path.exists()
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 3  # header + 2 agents
            assert "Discovery" in lines[1]

    def test_export_wave_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = DashboardDataExporter(tmpdir)
            path = exporter.export_wave_csv(self._sample_metrics())
            assert path.exists()
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 2  # header + 1 wave

    def test_export_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = DashboardDataExporter(tmpdir)
            paths = exporter.export_all(self._sample_metrics())
            assert len(paths) == 3
            assert all(p.exists() for p in paths)


# ===================================================================
# PBITTemplateGenerator
# ===================================================================


class TestPBITTemplateGenerator:
    def test_generate_manifest(self):
        gen = PBITTemplateGenerator()
        manifest = gen.generate_manifest()
        assert manifest["name"] == "OAC Migration Analytics"
        assert len(manifest["data_sources"]) == 3
        assert len(manifest["pages"]) == 5

    def test_page_names(self):
        gen = PBITTemplateGenerator()
        manifest = gen.generate_manifest()
        names = [p["name"] for p in manifest["pages"]]
        assert "Executive Summary" in names
        assert "Wave Progress" in names
        assert "Agent Details" in names
        assert "Cost Analysis" in names
        assert "Validation" in names

    def test_save_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = PBITTemplateGenerator()
            path = gen.save_manifest(tmpdir)
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["template_version"] == "1.0.0"


# ===================================================================
# ExecutiveSummary
# ===================================================================


class TestExecutiveSummary:
    def test_from_healthy_metrics(self):
        m = MigrationMetrics(
            migration_id="m1",
            total_assets=100,
            assets_migrated=90,
            assets_failed=0,
            waves=[WaveMetrics(wave_number=1, status="completed")],
            validation_pass_rate=99.5,
            cost=CostMetrics(estimated_cost_usd=500, budget_usd=1000),
        )
        s = ExecutiveSummary.from_metrics(m)
        assert s.overall_progress == 90.0
        assert s.timeline_status == "on_track"
        assert len(s.top_risks) == 0

    def test_from_risky_metrics(self):
        m = MigrationMetrics(
            migration_id="m2",
            total_assets=100,
            assets_migrated=50,
            assets_failed=15,
            overall_status="in_progress",
            waves=[WaveMetrics(wave_number=1, status="completed")],
            critical_issues=3,
            cost=CostMetrics(estimated_cost_usd=900, budget_usd=1000),
        )
        s = ExecutiveSummary.from_metrics(m)
        assert s.timeline_status == "at_risk"
        assert len(s.top_risks) >= 2  # failed assets + critical issues + budget

    def test_defaults(self):
        s = ExecutiveSummary()
        assert s.timeline_status == "on_track"
        assert s.top_risks == []
