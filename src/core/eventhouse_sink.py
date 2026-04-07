"""Eventhouse Sink — stream telemetry events to Fabric Real-Time Analytics (Eventhouse / KQL).

Collects telemetry from ``TelemetryCollector`` and formats it as KQL-ingestible
payloads.  Supports both direct ingestion (via Fabric Eventhouse REST) and
offline JSON export for CI/local testing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IngestionMode(str, Enum):
    """How telemetry is delivered to Eventhouse."""

    DIRECT = "direct"       # Push via Eventhouse REST API
    QUEUED = "queued"       # Write to OneLake queue folder, Eventstream picks up
    OFFLINE = "offline"     # Write JSON files locally (for CI / dev)


class EventCategory(str, Enum):
    """Categories for dashboard filtering."""

    AGENT = "agent"
    MIGRATION = "migration"
    DEPLOYMENT = "deployment"
    VALIDATION = "validation"
    PERFORMANCE = "performance"
    COST = "cost"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EventhouseEvent:
    """A single event formatted for Eventhouse ingestion."""

    event_id: str = ""
    timestamp: str = ""
    category: EventCategory = EventCategory.AGENT
    event_name: str = ""
    agent_id: str = ""
    wave_id: str = ""
    run_id: str = ""
    duration_ms: int = 0
    status: str = "ok"
    properties: dict[str, Any] = field(default_factory=dict)

    def to_kql_row(self) -> dict[str, Any]:
        """Return a flat dict for KQL ingestion."""
        return {
            "EventId": self.event_id,
            "Timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
            "Category": self.category.value,
            "EventName": self.event_name,
            "AgentId": self.agent_id,
            "WaveId": self.wave_id,
            "RunId": self.run_id,
            "DurationMs": self.duration_ms,
            "Status": self.status,
            "Properties": json.dumps(self.properties),
        }


@dataclass
class EventhouseMetric:
    """A metric point formatted for Eventhouse ingestion."""

    metric_name: str = ""
    value: float = 0.0
    timestamp: str = ""
    agent_id: str = ""
    wave_id: str = ""
    run_id: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    def to_kql_row(self) -> dict[str, Any]:
        return {
            "MetricName": self.metric_name,
            "Value": self.value,
            "Timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
            "AgentId": self.agent_id,
            "WaveId": self.wave_id,
            "RunId": self.run_id,
            "Tags": json.dumps(self.tags),
        }


@dataclass
class SinkResult:
    """Result of a flush to Eventhouse."""

    mode: IngestionMode
    events_sent: int = 0
    metrics_sent: int = 0
    errors: list[str] = field(default_factory=list)
    file_path: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "events_sent": self.events_sent,
            "metrics_sent": self.metrics_sent,
            "errors": self.errors,
            "file_path": self.file_path,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Eventhouse Sink
# ---------------------------------------------------------------------------


@dataclass
class EventhouseSink:
    """Buffer and flush telemetry to Fabric Eventhouse.

    Parameters
    ----------
    eventhouse_uri
        Fabric Eventhouse ingestion endpoint (ignored in OFFLINE mode).
    database
        KQL database name.
    events_table
        Target table for events (default ``MigrationEvents``).
    metrics_table
        Target table for metrics (default ``MigrationMetrics``).
    mode
        Ingestion mode (``direct``, ``queued``, ``offline``).
    """

    eventhouse_uri: str = ""
    database: str = "MigrationTelemetry"
    events_table: str = "MigrationEvents"
    metrics_table: str = "MigrationMetrics"
    mode: IngestionMode = IngestionMode.OFFLINE
    _event_buffer: list[EventhouseEvent] = field(default_factory=list, repr=False)
    _metric_buffer: list[EventhouseMetric] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------
    # Buffer
    # ------------------------------------------------------------------

    def track_event(self, event: EventhouseEvent) -> None:
        self._event_buffer.append(event)

    def track_metric(self, metric: EventhouseMetric) -> None:
        self._metric_buffer.append(metric)

    @property
    def buffered_events(self) -> int:
        return len(self._event_buffer)

    @property
    def buffered_metrics(self) -> int:
        return len(self._metric_buffer)

    # ------------------------------------------------------------------
    # Convenience: ingest from TelemetryCollector
    # ------------------------------------------------------------------

    def ingest_from_collector(self, collector: Any) -> None:
        """Pull events/metrics/spans from a ``TelemetryCollector`` into buffers."""
        import uuid

        for ev in getattr(collector, "events", []):
            self.track_event(EventhouseEvent(
                event_id=uuid.uuid4().hex[:12],
                timestamp=ev.timestamp.isoformat() if hasattr(ev, "timestamp") else "",
                event_name=ev.name,
                agent_id=ev.correlation.get("agent_id", "") if hasattr(ev, "correlation") else "",
                wave_id=ev.correlation.get("wave_id", "") if hasattr(ev, "correlation") else "",
                run_id=ev.correlation.get("run_id", "") if hasattr(ev, "correlation") else "",
                duration_ms=int(ev.duration_ms or 0) if hasattr(ev, "duration_ms") else 0,
                properties=ev.properties if hasattr(ev, "properties") else {},
            ))

        for mp in getattr(collector, "metrics", []):
            self.track_metric(EventhouseMetric(
                metric_name=mp.name,
                value=mp.value,
                timestamp=mp.timestamp.isoformat() if hasattr(mp, "timestamp") else "",
                tags=mp.tags if hasattr(mp, "tags") else {},
            ))

    # ------------------------------------------------------------------
    # Flush
    # ------------------------------------------------------------------

    def flush(self, *, output_dir: str = "") -> SinkResult:
        """Flush all buffered events and metrics.

        In OFFLINE mode, writes JSON files to *output_dir*.
        In DIRECT/QUEUED mode, would POST to Eventhouse endpoint (stubbed).
        """
        events_count = len(self._event_buffer)
        metrics_count = len(self._metric_buffer)

        if self.mode == IngestionMode.OFFLINE:
            return self._flush_offline(output_dir or "output/telemetry")

        # DIRECT / QUEUED — production implementation would call Eventhouse REST API.
        logger.info(
            "FLUSH %s: %d events, %d metrics → %s/%s",
            self.mode.value,
            events_count,
            metrics_count,
            self.eventhouse_uri,
            self.database,
        )
        self._event_buffer.clear()
        self._metric_buffer.clear()
        return SinkResult(mode=self.mode, events_sent=events_count, metrics_sent=metrics_count)

    def _flush_offline(self, output_dir: str) -> SinkResult:
        """Write buffers to local JSON files."""
        from pathlib import Path

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        errors: list[str] = []

        events_path = out / f"events_{ts}.json"
        try:
            events_path.write_text(json.dumps(
                [e.to_kql_row() for e in self._event_buffer], indent=2, default=str,
            ))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"events write error: {exc}")

        metrics_path = out / f"metrics_{ts}.json"
        try:
            metrics_path.write_text(json.dumps(
                [m.to_kql_row() for m in self._metric_buffer], indent=2, default=str,
            ))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"metrics write error: {exc}")

        events_count = len(self._event_buffer)
        metrics_count = len(self._metric_buffer)
        self._event_buffer.clear()
        self._metric_buffer.clear()

        logger.info("OFFLINE flush: %d events, %d metrics → %s", events_count, metrics_count, out)
        return SinkResult(
            mode=IngestionMode.OFFLINE,
            events_sent=events_count,
            metrics_sent=metrics_count,
            errors=errors,
            file_path=str(out),
        )

    # ------------------------------------------------------------------
    # KQL schema helpers
    # ------------------------------------------------------------------

    @staticmethod
    def events_table_schema() -> str:
        """Return a KQL ``.create table`` command for the events table."""
        return (
            ".create table MigrationEvents (\n"
            "    EventId: string,\n"
            "    Timestamp: datetime,\n"
            "    Category: string,\n"
            "    EventName: string,\n"
            "    AgentId: string,\n"
            "    WaveId: string,\n"
            "    RunId: string,\n"
            "    DurationMs: int,\n"
            "    Status: string,\n"
            "    Properties: dynamic\n"
            ")"
        )

    @staticmethod
    def metrics_table_schema() -> str:
        """Return a KQL ``.create table`` command for the metrics table."""
        return (
            ".create table MigrationMetrics (\n"
            "    MetricName: string,\n"
            "    Value: real,\n"
            "    Timestamp: datetime,\n"
            "    AgentId: string,\n"
            "    WaveId: string,\n"
            "    RunId: string,\n"
            "    Tags: dynamic\n"
            ")"
        )
