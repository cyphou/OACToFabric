"""Tests for the telemetry module — correlation, events, metrics, spans."""

from __future__ import annotations

import pytest
from src.core.telemetry import (
    CorrelationContext,
    MetricKind,
    MetricPoint,
    Span,
    TelemetryCollector,
    TelemetryEvent,
)


# ---------------------------------------------------------------------------
# CorrelationContext
# ---------------------------------------------------------------------------


class TestCorrelationContext:
    def test_auto_generates_run_id(self):
        ctx = CorrelationContext()
        assert ctx.run_id
        assert len(ctx.run_id) == 12

    def test_explicit_run_id(self):
        ctx = CorrelationContext(run_id="my-run-42")
        assert ctx.run_id == "my-run-42"

    def test_new_span_updates_span_id(self):
        ctx = CorrelationContext()
        span_id = ctx.new_span(agent_id="01-discovery", wave_id="w1")
        assert span_id
        assert ctx.span_id == span_id
        assert ctx.agent_id == "01-discovery"
        assert ctx.wave_id == "w1"

    def test_as_dict_omits_empty(self):
        ctx = CorrelationContext(run_id="r1")
        d = ctx.as_dict()
        assert "run_id" in d
        assert "span_id" not in d  # empty string excluded
        assert "agent_id" not in d

    def test_as_dict_includes_extra(self):
        ctx = CorrelationContext(run_id="r1")
        ctx.extra["env"] = "test"
        d = ctx.as_dict()
        assert d["env"] == "test"


# ---------------------------------------------------------------------------
# TelemetryCollector — Run lifecycle
# ---------------------------------------------------------------------------


class TestTelemetryCollectorRun:
    def test_start_run_creates_context(self):
        tc = TelemetryCollector()
        ctx = tc.start_run()
        assert ctx is tc.context
        assert ctx.run_id

    def test_start_run_with_explicit_id(self):
        tc = TelemetryCollector()
        ctx = tc.start_run(run_id="test-run")
        assert ctx.run_id == "test-run"

    def test_start_run_records_event(self):
        tc = TelemetryCollector()
        tc.start_run(run_id="r1")
        events = tc.get_events_by_name("migration_run_started")
        assert len(events) == 1
        assert events[0].properties["run_id"] == "r1"

    def test_end_run_records_event(self):
        tc = TelemetryCollector()
        tc.start_run()
        tc.end_run(status="succeeded")
        events = tc.get_events_by_name("migration_run_ended")
        assert len(events) == 1
        assert events[0].properties["status"] == "succeeded"


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class TestTelemetryEvents:
    def test_track_event(self):
        tc = TelemetryCollector()
        tc.start_run()
        event = tc.track_event("my_event", {"key": "value"})
        assert event.name == "my_event"
        assert event.properties["key"] == "value"
        assert len(tc.events) == 2  # run_started + my_event

    def test_event_includes_correlation(self):
        tc = TelemetryCollector()
        ctx = tc.start_run(run_id="r1")
        event = tc.track_event("test")
        assert event.correlation["run_id"] == "r1"

    def test_events_retrieved_by_name(self):
        tc = TelemetryCollector()
        tc.track_event("a")
        tc.track_event("b")
        tc.track_event("a")
        assert len(tc.get_events_by_name("a")) == 2
        assert len(tc.get_events_by_name("b")) == 1


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestTelemetryMetrics:
    def test_record_metric(self):
        tc = TelemetryCollector()
        m = tc.record_metric("items_migrated", 42, tags={"agent": "02"})
        assert m.name == "items_migrated"
        assert m.value == 42
        assert m.kind == MetricKind.COUNTER

    def test_increment(self):
        tc = TelemetryCollector()
        tc.increment("counter_a")
        tc.increment("counter_a")
        tc.increment("counter_a", delta=5)
        points = tc.get_metrics_by_name("counter_a")
        assert len(points) == 3
        assert sum(p.value for p in points) == 7

    def test_histogram_metric(self):
        tc = TelemetryCollector()
        tc.record_metric("latency_ms", 123.4, kind=MetricKind.HISTOGRAM)
        points = tc.get_metrics_by_name("latency_ms")
        assert points[0].kind == MetricKind.HISTOGRAM


# ---------------------------------------------------------------------------
# Spans (tracing)
# ---------------------------------------------------------------------------


class TestTelemetrySpans:
    def test_span_records_duration(self):
        tc = TelemetryCollector()
        tc.start_run()
        with tc.span("test_op") as s:
            pass  # immediate
        assert len(tc.spans) == 1
        assert tc.spans[0].name == "test_op"
        assert tc.spans[0].status == "ok"
        assert tc.spans[0].end_time is not None
        assert "duration_ms" in tc.spans[0].attributes

    def test_span_captures_error(self):
        tc = TelemetryCollector()
        tc.start_run()
        with pytest.raises(ValueError, match="boom"):
            with tc.span("failing_op") as s:
                raise ValueError("boom")
        assert tc.spans[0].status == "error"
        assert tc.spans[0].error == "boom"

    def test_span_propagates_context(self):
        tc = TelemetryCollector()
        ctx = tc.start_run(run_id="r1")
        with tc.span("op1", agent_id="01-disc") as s:
            assert s.run_id == "r1"
            assert s.agent_id == "01-disc"

    def test_nested_spans_restore_parent(self):
        tc = TelemetryCollector()
        ctx = tc.start_run(run_id="r1")
        original_span = ctx.span_id

        with tc.span("parent") as parent:
            parent_span_id = ctx.span_id
            with tc.span("child") as child:
                assert child.parent_span_id == parent_span_id
            # After child exits, parent span should be restored
            assert ctx.span_id == parent_span_id

        # After parent exits, original span should be restored
        assert ctx.span_id == original_span

    def test_span_records_duration_metric(self):
        tc = TelemetryCollector()
        tc.start_run()
        with tc.span("my_op"):
            pass
        duration_metrics = [
            m for m in tc.metrics if m.name.startswith("span_duration_ms")
        ]
        assert len(duration_metrics) == 1


# ---------------------------------------------------------------------------
# Agent convenience helpers
# ---------------------------------------------------------------------------


class TestTelemetryAgentHelpers:
    def test_agent_started(self):
        tc = TelemetryCollector()
        tc.start_run()
        tc.agent_started("01-discovery", wave_id="w1")
        events = tc.get_events_by_name("agent_started")
        assert len(events) == 1
        assert events[0].properties["agent_id"] == "01-discovery"
        counters = tc.get_metrics_by_name("agents_started")
        assert len(counters) == 1

    def test_agent_completed(self):
        tc = TelemetryCollector()
        tc.start_run()
        tc.agent_completed("02-schema", succeeded=10, failed=2, duration_seconds=5.5)
        events = tc.get_events_by_name("agent_completed")
        assert len(events) == 1
        assert events[0].properties["succeeded"] == 10
        assert events[0].properties["failed"] == 2
        items = tc.get_metrics_by_name("items_migrated")
        assert items[0].value == 10

    def test_agent_failed(self):
        tc = TelemetryCollector()
        tc.start_run()
        tc.agent_failed("03-etl", error="Connection refused")
        events = tc.get_events_by_name("agent_failed")
        assert events[0].properties["error"] == "Connection refused"


# ---------------------------------------------------------------------------
# Summary & reset
# ---------------------------------------------------------------------------


class TestTelemetrySummary:
    def test_summary_contents(self):
        tc = TelemetryCollector()
        tc.start_run(run_id="r1")
        tc.track_event("e1")
        tc.record_metric("m1", 1)
        s = tc.summary()
        assert s["run_id"] == "r1"
        assert s["total_events"] == 2  # run_started + e1
        assert s["total_metrics"] == 1

    def test_reset_clears_all(self):
        tc = TelemetryCollector()
        tc.start_run()
        tc.track_event("e1")
        tc.record_metric("m1", 1)
        tc.reset()
        assert len(tc.events) == 0
        assert len(tc.metrics) == 0
        assert len(tc.spans) == 0
        assert tc.context is None
