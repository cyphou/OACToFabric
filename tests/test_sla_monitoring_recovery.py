"""Tests for sla_tracker, monitoring, and recovery_report modules."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.agents.orchestrator.sla_tracker import (
    SLAReport,
    SLAResult,
    SLAStatus,
    SLAThresholds,
    build_sla_report,
    evaluate_sla,
    render_sla_summary,
)
from src.agents.orchestrator.monitoring import (
    ExportBackend,
    ExportConfig,
    export_telemetry,
    export_to_json,
    render_prometheus_metrics,
)
from src.agents.orchestrator.recovery_report import (
    RecoveryActionType,
    RecoveryOutcome,
    RecoveryReport,
    RecoveryTracker,
    render_recovery_report,
    save_recovery_report,
)


# ---------------------------------------------------------------------------
# SLA tracker
# ---------------------------------------------------------------------------

class TestEvaluateSLA:
    def test_all_met(self):
        result = evaluate_sla("a1", "Asset1", duration_minutes=10, validation_pass_rate=0.99)
        assert result.overall_status == SLAStatus.MET
        assert result.duration_status == SLAStatus.MET

    def test_duration_breached(self):
        result = evaluate_sla("a2", "Asset2", duration_minutes=120, validation_pass_rate=1.0)
        assert result.duration_status == SLAStatus.BREACHED
        assert result.overall_status == SLAStatus.BREACHED

    def test_duration_at_risk(self):
        result = evaluate_sla("a3", "Asset3", duration_minutes=50, validation_pass_rate=1.0)
        assert result.duration_status == SLAStatus.AT_RISK

    def test_validation_breached(self):
        result = evaluate_sla("a4", "Asset4", duration_minutes=5, validation_pass_rate=0.80)
        assert result.validation_status == SLAStatus.BREACHED

    def test_accuracy_breached(self):
        result = evaluate_sla("a5", "Asset5", duration_minutes=5, validation_pass_rate=1.0, row_count_deviation_pct=0.05)
        assert result.accuracy_status == SLAStatus.BREACHED

    def test_custom_thresholds(self):
        thresholds = SLAThresholds(max_duration_minutes=10)
        result = evaluate_sla("a6", "Asset6", duration_minutes=15, validation_pass_rate=1.0, thresholds=thresholds)
        assert result.duration_status == SLAStatus.BREACHED


class TestSLAReport:
    def test_build_report(self):
        results = [
            evaluate_sla("a1", "A1", 5, 1.0),
            evaluate_sla("a2", "A2", 120, 0.5),
        ]
        report = build_sla_report(results)
        assert report.met_count == 1
        assert report.breached_count == 1
        assert report.compliance_rate == 0.5

    def test_empty_report(self):
        report = build_sla_report([])
        assert report.compliance_rate == 1.0

    def test_render_summary(self):
        results = [evaluate_sla("a1", "A1", 5, 1.0)]
        report = build_sla_report(results)
        summary = render_sla_summary(report)
        assert summary["total_assets"] == 1
        assert summary["met"] == 1
        assert "thresholds" in summary


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------

class TestMonitoring:
    def test_export_to_json(self, tmp_path):
        outpath = tmp_path / "metrics.jsonl"
        events = [{"name": "test_event", "data": "hello"}]
        metrics = [{"name": "items", "value": 42, "tags": {}}]
        spans = [{"name": "discover", "duration_ms": 100}]
        result = export_to_json(events, metrics, spans, outpath)
        assert result.success is True
        assert result.records_exported == 3
        lines = outpath.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_prometheus_format(self):
        metrics = [
            {"name": "items.migrated", "value": 42, "tags": {"agent": "02"}, "kind": "counter"},
            {"name": "duration_ms", "value": 1500, "tags": {}, "kind": "gauge"},
        ]
        text = render_prometheus_metrics(metrics)
        assert "migration_items_migrated" in text
        assert 'agent="02"' in text
        assert "migration_duration_ms" in text
        assert "# TYPE" in text

    def test_export_telemetry_json(self, tmp_path):
        config = ExportConfig(
            backends=[ExportBackend.JSON],
            json_output_path=str(tmp_path / "out.jsonl"),
        )
        results = export_telemetry([], [{"name": "x", "value": 1}], [], config)
        assert len(results) == 1
        assert results[0].success is True


# ---------------------------------------------------------------------------
# Recovery report
# ---------------------------------------------------------------------------

class TestRecoveryTracker:
    def test_record_action(self):
        tracker = RecoveryTracker()
        action = tracker.record(
            agent_id="04-semantic",
            asset_id="sales_model",
            action_type=RecoveryActionType.SELF_HEAL,
            description="Fixed circular relationship",
        )
        assert action.outcome == RecoveryOutcome.RESOLVED
        report = tracker.build_report()
        assert report.total_actions == 1
        assert report.resolved_count == 1

    def test_record_retry(self):
        tracker = RecoveryTracker()
        tracker.record_retry("03-etl", "pipeline_1", "Timeout", attempt=2, resolved=True)
        report = tracker.build_report()
        assert report.by_type.get("retry", 0) == 1

    def test_record_self_heal(self):
        tracker = RecoveryTracker()
        tracker.record_self_heal("04-semantic", "model", "Duplicate table", "Renamed with suffix")
        report = tracker.build_report()
        assert report.by_agent.get("04-semantic", 0) == 1

    def test_unresolved(self):
        tracker = RecoveryTracker()
        tracker.record(
            "01-discovery", "catalog",
            RecoveryActionType.RETRY, "API timeout",
            outcome=RecoveryOutcome.UNRESOLVED,
        )
        report = tracker.build_report()
        assert report.unresolved_count == 1

    def test_render_report(self):
        tracker = RecoveryTracker()
        tracker.record_self_heal("04", "m1", "Fix", "Done")
        report = tracker.build_report()
        rendered = render_recovery_report(report)
        assert rendered["total_actions"] == 1
        assert len(rendered["actions"]) == 1

    def test_save_report(self, tmp_path):
        tracker = RecoveryTracker()
        tracker.record_self_heal("04", "m1", "Fix", "Done")
        report = tracker.build_report()
        path = save_recovery_report(report, tmp_path / "recovery.json")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["total_actions"] == 1
