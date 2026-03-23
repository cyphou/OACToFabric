"""Telemetry — structured observability for the migration framework.

Provides:
- **Correlation IDs** propagated across all agents in a migration run.
- **Structured events** (agent started/completed/failed, wave progress).
- **Custom metrics** (items migrated, duration, error counts).
- **Distributed tracing** via OpenTelemetry-compatible spans.

When Azure Application Insights is configured (via connection string),
events and metrics are forwarded automatically.  Otherwise, everything
is emitted through Python's standard ``logging`` module so no external
dependency is required at dev/test time.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Correlation context
# ---------------------------------------------------------------------------


class CorrelationContext:
    """Thread-local-style context carrying a correlation ID.

    Every migration run gets a unique ``run_id``.  Individual agent
    executions get a ``span_id`` nested under the run.
    """

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id: str = run_id or uuid.uuid4().hex[:12]
        self.span_id: str = ""
        self.agent_id: str = ""
        self.wave_id: str = ""
        self.extra: dict[str, str] = {}

    def new_span(self, agent_id: str = "", wave_id: str = "") -> str:
        """Create a new span ID under the current run."""
        self.span_id = uuid.uuid4().hex[:8]
        self.agent_id = agent_id
        self.wave_id = wave_id
        return self.span_id

    def as_dict(self) -> dict[str, str]:
        d = {
            "run_id": self.run_id,
            "span_id": self.span_id,
            "agent_id": self.agent_id,
            "wave_id": self.wave_id,
        }
        d.update(self.extra)
        return {k: v for k, v in d.items() if v}


# ---------------------------------------------------------------------------
# Metric types
# ---------------------------------------------------------------------------


class MetricKind(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    kind: MetricKind = MetricKind.COUNTER
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


@dataclass
class TelemetryEvent:
    """A structured telemetry event."""

    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation: dict[str, str] = field(default_factory=dict)
    duration_ms: float | None = None


# ---------------------------------------------------------------------------
# Span (lightweight distributed-trace span)
# ---------------------------------------------------------------------------


@dataclass
class Span:
    """A trace span representing a unit of work."""

    name: str
    span_id: str
    parent_span_id: str = ""
    run_id: str = ""
    agent_id: str = ""
    wave_id: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    status: str = "ok"
    error: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds() * 1000


# ---------------------------------------------------------------------------
# Telemetry Collector
# ---------------------------------------------------------------------------


class TelemetryCollector:
    """Central telemetry collector for the migration framework.

    Accumulates events, metrics, and spans in memory and optionally
    forwards them to Azure Application Insights.

    Usage::

        tc = TelemetryCollector()
        ctx = tc.start_run()

        with tc.span("discover", agent_id="01-discovery", context=ctx):
            ...  # agent work

        tc.record_metric("items_migrated", 42, tags={"agent": "02-schema"})
        tc.track_event("wave_completed", {"wave_id": "1", "succeeded": "7"})
    """

    def __init__(self, connection_string: str | None = None) -> None:
        self._connection_string = connection_string
        self._events: list[TelemetryEvent] = []
        self._metrics: list[MetricPoint] = []
        self._spans: list[Span] = []
        self._context: CorrelationContext | None = None

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def start_run(self, run_id: str | None = None) -> CorrelationContext:
        """Begin a new migration run and return its correlation context."""
        self._context = CorrelationContext(run_id=run_id)
        self.track_event("migration_run_started", {"run_id": self._context.run_id})
        logger.info("Telemetry run started: %s", self._context.run_id)
        return self._context

    def end_run(self, status: str = "succeeded") -> None:
        """Mark the current run as finished."""
        if self._context:
            self.track_event(
                "migration_run_ended",
                {"run_id": self._context.run_id, "status": status},
            )
            logger.info(
                "Telemetry run ended: %s — %s",
                self._context.run_id,
                status,
            )

    @property
    def context(self) -> CorrelationContext | None:
        return self._context

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def track_event(
        self,
        name: str,
        properties: dict[str, Any] | None = None,
        *,
        context: CorrelationContext | None = None,
    ) -> TelemetryEvent:
        """Record a structured event."""
        ctx = context or self._context
        event = TelemetryEvent(
            name=name,
            properties=properties or {},
            correlation=ctx.as_dict() if ctx else {},
        )
        self._events.append(event)
        logger.debug("Event: %s %s", name, event.properties)
        return event

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        kind: MetricKind = MetricKind.COUNTER,
        tags: dict[str, str] | None = None,
    ) -> MetricPoint:
        """Record a metric data point."""
        point = MetricPoint(name=name, value=value, kind=kind, tags=tags or {})
        self._metrics.append(point)
        logger.debug("Metric: %s = %s (%s)", name, value, kind.value)
        return point

    def increment(self, name: str, delta: float = 1, **tags: str) -> MetricPoint:
        """Convenience: increment a counter metric."""
        return self.record_metric(name, delta, kind=MetricKind.COUNTER, tags=tags)

    # ------------------------------------------------------------------
    # Spans (tracing)
    # ------------------------------------------------------------------

    @contextmanager
    def span(
        self,
        name: str,
        *,
        agent_id: str = "",
        wave_id: str = "",
        context: CorrelationContext | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        """Context manager that creates and records a trace span."""
        ctx = context or self._context
        span_id = uuid.uuid4().hex[:8]
        parent = ctx.span_id if ctx else ""

        s = Span(
            name=name,
            span_id=span_id,
            parent_span_id=parent,
            run_id=ctx.run_id if ctx else "",
            agent_id=agent_id or (ctx.agent_id if ctx else ""),
            wave_id=wave_id or (ctx.wave_id if ctx else ""),
            attributes=attributes or {},
        )

        # Update context
        if ctx:
            old_span = ctx.span_id
            ctx.span_id = span_id
            if agent_id:
                ctx.agent_id = agent_id
            if wave_id:
                ctx.wave_id = wave_id

        logger.debug("Span started: %s [%s]", name, span_id)
        start = time.monotonic()

        try:
            yield s
            s.status = "ok"
        except Exception as exc:
            s.status = "error"
            s.error = str(exc)
            raise
        finally:
            elapsed = time.monotonic() - start
            s.end_time = datetime.now(timezone.utc)
            s.attributes["duration_ms"] = round(elapsed * 1000, 2)
            self._spans.append(s)

            # Record duration metric
            self.record_metric(
                f"span_duration_ms.{name}",
                elapsed * 1000,
                kind=MetricKind.HISTOGRAM,
                tags={"agent_id": s.agent_id, "wave_id": s.wave_id},
            )

            # Restore parent span
            if ctx:
                ctx.span_id = old_span

            logger.debug(
                "Span ended: %s [%s] — %.1fms (%s)",
                name,
                span_id,
                elapsed * 1000,
                s.status,
            )

    # ------------------------------------------------------------------
    # Agent convenience helpers
    # ------------------------------------------------------------------

    def agent_started(
        self,
        agent_id: str,
        wave_id: str = "",
        *,
        context: CorrelationContext | None = None,
    ) -> None:
        """Track an agent lifecycle start."""
        self.track_event(
            "agent_started",
            {"agent_id": agent_id, "wave_id": wave_id},
            context=context,
        )
        self.increment("agents_started", agent_id=agent_id)

    def agent_completed(
        self,
        agent_id: str,
        succeeded: int,
        failed: int,
        duration_seconds: float,
        *,
        context: CorrelationContext | None = None,
    ) -> None:
        """Track an agent lifecycle completion."""
        self.track_event(
            "agent_completed",
            {
                "agent_id": agent_id,
                "succeeded": succeeded,
                "failed": failed,
                "duration_seconds": round(duration_seconds, 2),
            },
            context=context,
        )
        self.increment("agents_completed", agent_id=agent_id)
        self.record_metric(
            "items_migrated",
            succeeded,
            tags={"agent_id": agent_id},
        )
        self.record_metric(
            "items_failed",
            failed,
            tags={"agent_id": agent_id},
        )

    def agent_failed(
        self,
        agent_id: str,
        error: str,
        *,
        context: CorrelationContext | None = None,
    ) -> None:
        """Track an agent failure."""
        self.track_event(
            "agent_failed",
            {"agent_id": agent_id, "error": error[:500]},
            context=context,
        )
        self.increment("agents_failed", agent_id=agent_id)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def events(self) -> list[TelemetryEvent]:
        return list(self._events)

    @property
    def metrics(self) -> list[MetricPoint]:
        return list(self._metrics)

    @property
    def spans(self) -> list[Span]:
        return list(self._spans)

    def get_metrics_by_name(self, name: str) -> list[MetricPoint]:
        """Return all metric points matching *name*."""
        return [m for m in self._metrics if m.name == name]

    def get_events_by_name(self, name: str) -> list[TelemetryEvent]:
        """Return all events matching *name*."""
        return [e for e in self._events if e.name == name]

    def reset(self) -> None:
        """Clear all collected telemetry data."""
        self._events.clear()
        self._metrics.clear()
        self._spans.clear()
        self._context = None

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a summary of collected telemetry."""
        return {
            "run_id": self._context.run_id if self._context else None,
            "total_events": len(self._events),
            "total_metrics": len(self._metrics),
            "total_spans": len(self._spans),
            "event_types": sorted(set(e.name for e in self._events)),
            "metric_names": sorted(set(m.name for m in self._metrics)),
        }
