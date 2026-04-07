"""Tests for Phase 80 — Eventhouse Sink."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.core.eventhouse_sink import (
    EventCategory,
    EventhouseEvent,
    EventhouseMetric,
    EventhouseSink,
    IngestionMode,
    SinkResult,
)


class TestEventhouseEvent(unittest.TestCase):
    def test_to_kql_row(self) -> None:
        ev = EventhouseEvent(
            event_id="e1",
            category=EventCategory.AGENT,
            event_name="agent_started",
            agent_id="01",
        )
        row = ev.to_kql_row()
        self.assertEqual(row["EventId"], "e1")
        self.assertEqual(row["Category"], "agent")
        self.assertIn("Timestamp", row)


class TestEventhouseMetric(unittest.TestCase):
    def test_to_kql_row(self) -> None:
        m = EventhouseMetric(metric_name="items_migrated", value=42.0, agent_id="02")
        row = m.to_kql_row()
        self.assertEqual(row["MetricName"], "items_migrated")
        self.assertEqual(row["Value"], 42.0)


class TestEventhouseSink(unittest.TestCase):
    def test_buffer_events(self) -> None:
        sink = EventhouseSink()
        sink.track_event(EventhouseEvent(event_id="e1", event_name="test"))
        sink.track_event(EventhouseEvent(event_id="e2", event_name="test2"))
        self.assertEqual(sink.buffered_events, 2)
        self.assertEqual(sink.buffered_metrics, 0)

    def test_buffer_metrics(self) -> None:
        sink = EventhouseSink()
        sink.track_metric(EventhouseMetric(metric_name="m1", value=1.0))
        self.assertEqual(sink.buffered_metrics, 1)

    def test_flush_offline(self) -> None:
        sink = EventhouseSink(mode=IngestionMode.OFFLINE)
        sink.track_event(EventhouseEvent(event_id="e1", event_name="test"))
        sink.track_metric(EventhouseMetric(metric_name="m1", value=1.0))

        with tempfile.TemporaryDirectory() as td:
            result = sink.flush(output_dir=td)
            self.assertTrue(result.success)
            self.assertEqual(result.events_sent, 1)
            self.assertEqual(result.metrics_sent, 1)
            # Check files were written
            files = list(Path(td).glob("*.json"))
            self.assertEqual(len(files), 2)

    def test_flush_clears_buffers(self) -> None:
        sink = EventhouseSink(mode=IngestionMode.OFFLINE)
        sink.track_event(EventhouseEvent(event_id="e1", event_name="test"))
        with tempfile.TemporaryDirectory() as td:
            sink.flush(output_dir=td)
        self.assertEqual(sink.buffered_events, 0)

    def test_flush_direct_mode(self) -> None:
        sink = EventhouseSink(mode=IngestionMode.DIRECT, eventhouse_uri="https://test.kusto.fabric.microsoft.com")
        sink.track_event(EventhouseEvent(event_id="e1"))
        result = sink.flush()
        self.assertTrue(result.success)
        self.assertEqual(result.events_sent, 1)

    def test_ingest_from_collector_duck_typed(self) -> None:
        """Sink can ingest from any object with .events and .metrics attributes."""
        from types import SimpleNamespace
        from datetime import datetime, timezone

        fake_event = SimpleNamespace(
            name="test_event",
            timestamp=datetime.now(timezone.utc),
            correlation={"agent_id": "01", "run_id": "r1"},
            duration_ms=100,
            properties={"key": "val"},
        )
        fake_metric = SimpleNamespace(
            name="speed",
            value=42.0,
            timestamp=datetime.now(timezone.utc),
            tags={"env": "test"},
        )
        collector = SimpleNamespace(events=[fake_event], metrics=[fake_metric])

        sink = EventhouseSink()
        sink.ingest_from_collector(collector)
        self.assertEqual(sink.buffered_events, 1)
        self.assertEqual(sink.buffered_metrics, 1)

    def test_events_table_schema(self) -> None:
        schema = EventhouseSink.events_table_schema()
        self.assertIn("MigrationEvents", schema)
        self.assertIn("EventId", schema)

    def test_metrics_table_schema(self) -> None:
        schema = EventhouseSink.metrics_table_schema()
        self.assertIn("MigrationMetrics", schema)
        self.assertIn("MetricName", schema)


class TestSinkResult(unittest.TestCase):
    def test_success(self) -> None:
        r = SinkResult(mode=IngestionMode.OFFLINE, events_sent=5)
        self.assertTrue(r.success)

    def test_failure(self) -> None:
        r = SinkResult(mode=IngestionMode.OFFLINE, errors=["disk full"])
        self.assertFalse(r.success)


if __name__ == "__main__":
    unittest.main()
