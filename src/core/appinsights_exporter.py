"""Application Insights exporter + optional OTLP compatibility layer.

Provides:
- ``AppInsightsExporter`` that forwards TelemetryCollector data to Azure
  Application Insights via the ``azure-monitor-opentelemetry`` SDK.
- ``OTLPExporter`` that formats telemetry for the OpenTelemetry Protocol
  (OTLP) endpoint, enabling export to Jaeger, Grafana, or any OTLP-
  compatible backend.

Both exporters work entirely through the in-memory data already
collected by :class:`TelemetryCollector` — they never install global
instrumentation hooks, keeping the migration framework decoupled from
whichever backend is chosen at deploy time.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Export result
# ---------------------------------------------------------------------------


@dataclass
class ExportResult:
    """Describes the outcome of an export batch."""

    exporter: str
    events_sent: int = 0
    metrics_sent: int = 0
    spans_sent: int = 0
    errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_items(self) -> int:
        return self.events_sent + self.metrics_sent + self.spans_sent


# ---------------------------------------------------------------------------
# Application Insights exporter
# ---------------------------------------------------------------------------


class AppInsightsExporter:
    """Export TelemetryCollector data to Azure Application Insights.

    Parameters
    ----------
    connection_string : str
        The App Insights connection string (``InstrumentationKey=...``).
    dry_run : bool
        When ``True``, format payloads but do not actually transmit.
    """

    def __init__(self, connection_string: str, *, dry_run: bool = False) -> None:
        self._connection_string = connection_string
        self._dry_run = dry_run
        self._instrumentation_key = self._parse_ikey(connection_string)

    @staticmethod
    def _parse_ikey(conn_str: str) -> str:
        """Extract InstrumentationKey from the connection string."""
        for part in conn_str.split(";"):
            if "=" in part:
                key, _, value = part.partition("=")
                if key.strip().lower() == "instrumentationkey":
                    return value.strip()
        return ""

    # -- Payload builders --------------------------------------------------

    def _build_event_payload(self, event: Any) -> dict[str, Any]:
        return {
            "name": "AppEvents",
            "time": (
                event.timestamp.isoformat()
                if hasattr(event, "timestamp")
                else datetime.now(timezone.utc).isoformat()
            ),
            "iKey": self._instrumentation_key,
            "data": {
                "baseType": "EventData",
                "baseData": {
                    "name": getattr(event, "name", "unknown"),
                    "properties": {
                        **(getattr(event, "properties", {}) or {}),
                        **(getattr(event, "correlation", {}) or {}),
                    },
                },
            },
        }

    def _build_metric_payload(self, metric: Any) -> dict[str, Any]:
        return {
            "name": "AppMetrics",
            "time": (
                metric.timestamp.isoformat()
                if hasattr(metric, "timestamp")
                else datetime.now(timezone.utc).isoformat()
            ),
            "iKey": self._instrumentation_key,
            "data": {
                "baseType": "MetricData",
                "baseData": {
                    "metrics": [
                        {
                            "name": getattr(metric, "name", "unknown"),
                            "value": getattr(metric, "value", 0),
                            "kind": getattr(
                                getattr(metric, "kind", None), "value", "counter"
                            ),
                        }
                    ],
                    "properties": getattr(metric, "tags", {}),
                },
            },
        }

    def _build_span_payload(self, span: Any) -> dict[str, Any]:
        return {
            "name": "AppDependencies",
            "time": (
                span.start_time.isoformat()
                if hasattr(span, "start_time")
                else datetime.now(timezone.utc).isoformat()
            ),
            "iKey": self._instrumentation_key,
            "data": {
                "baseType": "RemoteDependencyData",
                "baseData": {
                    "name": getattr(span, "name", "unknown"),
                    "id": getattr(span, "span_id", ""),
                    "duration": f"{getattr(span, 'duration_ms', 0):.0f}ms",
                    "success": getattr(span, "status", "ok") == "ok",
                    "properties": {
                        "agent_id": getattr(span, "agent_id", ""),
                        "wave_id": getattr(span, "wave_id", ""),
                        "run_id": getattr(span, "run_id", ""),
                        **(getattr(span, "attributes", {}) or {}),
                    },
                },
            },
        }

    # -- Export ------------------------------------------------------------

    def export(self, collector: Any) -> ExportResult:
        """Export all data from a TelemetryCollector instance.

        Parameters
        ----------
        collector
            A ``TelemetryCollector`` (duck-typed — must have ``.events``,
            ``.metrics``, ``.spans`` properties).

        Returns
        -------
        ExportResult
        """
        result = ExportResult(exporter="appinsights")
        payloads: list[dict[str, Any]] = []

        for event in getattr(collector, "events", []):
            payloads.append(self._build_event_payload(event))
            result.events_sent += 1

        for metric in getattr(collector, "metrics", []):
            payloads.append(self._build_metric_payload(metric))
            result.metrics_sent += 1

        for span in getattr(collector, "spans", []):
            payloads.append(self._build_span_payload(span))
            result.spans_sent += 1

        if self._dry_run:
            logger.info(
                "AppInsights dry-run: %d items prepared (not sent)",
                result.total_items,
            )
            return result

        # Real send — POST to Application Insights ingestion endpoint
        try:
            import httpx

            endpoint = self._get_ingestion_endpoint()
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{endpoint}/v2/track",
                    json=payloads,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                resp.raise_for_status()
            logger.info(
                "AppInsights: exported %d items successfully", result.total_items
            )
        except ImportError:
            result.errors.append("httpx not installed — cannot send to App Insights")
            logger.warning("httpx not installed — App Insights export skipped")
        except Exception as exc:
            result.errors.append(str(exc))
            logger.exception("AppInsights export failed")

        return result

    def _get_ingestion_endpoint(self) -> str:
        """Extract IngestionEndpoint from connection string or use default."""
        for part in self._connection_string.split(";"):
            if "=" in part:
                key, _, value = part.partition("=")
                if key.strip().lower() == "ingestionendpoint":
                    return value.strip().rstrip("/")
        return "https://dc.services.visualstudio.com"

    @property
    def instrumentation_key(self) -> str:
        return self._instrumentation_key


# ---------------------------------------------------------------------------
# OTLP exporter (OpenTelemetry Protocol)
# ---------------------------------------------------------------------------


class OTLPExporter:
    """Export TelemetryCollector data in OTLP JSON format.

    This exporter converts the in-memory telemetry into OTLP-compatible
    JSON payloads suitable for sending to any OTLP receiver (Jaeger,
    Grafana Tempo, Collector, etc.).

    Parameters
    ----------
    endpoint : str
        The OTLP HTTP endpoint, e.g. ``http://localhost:4318``.
    service_name : str
        Service name to include in resource attributes.
    dry_run : bool
        If ``True``, build payloads but do not transmit.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:4318",
        service_name: str = "oac-to-fabric-migration",
        *,
        dry_run: bool = False,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._service_name = service_name
        self._dry_run = dry_run

    def _resource_attrs(self) -> list[dict[str, Any]]:
        return [
            {"key": "service.name", "value": {"stringValue": self._service_name}},
            {"key": "telemetry.sdk.name", "value": {"stringValue": "oac-migration"}},
            {"key": "telemetry.sdk.language", "value": {"stringValue": "python"}},
        ]

    def _build_trace_payload(self, spans: list[Any]) -> dict[str, Any]:
        """Build OTLP traces payload from Span objects."""
        otlp_spans = []
        for s in spans:
            otlp_spans.append(
                {
                    "traceId": getattr(s, "run_id", "") or "0" * 32,
                    "spanId": getattr(s, "span_id", ""),
                    "parentSpanId": getattr(s, "parent_span_id", ""),
                    "name": getattr(s, "name", ""),
                    "startTimeUnixNano": (
                        int(s.start_time.timestamp() * 1e9)
                        if hasattr(s, "start_time")
                        else 0
                    ),
                    "endTimeUnixNano": (
                        int(s.end_time.timestamp() * 1e9)
                        if hasattr(s, "end_time") and s.end_time
                        else 0
                    ),
                    "status": {
                        "code": 1 if getattr(s, "status", "ok") == "ok" else 2
                    },
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)}}
                        for k, v in (getattr(s, "attributes", {}) or {}).items()
                    ],
                }
            )
        return {
            "resourceSpans": [
                {
                    "resource": {"attributes": self._resource_attrs()},
                    "scopeSpans": [{"scope": {"name": "migration"}, "spans": otlp_spans}],
                }
            ]
        }

    def _build_metrics_payload(self, metrics: list[Any]) -> dict[str, Any]:
        """Build OTLP metrics payload from MetricPoint objects."""
        otlp_metrics = []
        for m in metrics:
            otlp_metrics.append(
                {
                    "name": getattr(m, "name", ""),
                    "unit": "",
                    "sum": {
                        "dataPoints": [
                            {
                                "asDouble": getattr(m, "value", 0),
                                "timeUnixNano": (
                                    int(m.timestamp.timestamp() * 1e9)
                                    if hasattr(m, "timestamp")
                                    else 0
                                ),
                                "attributes": [
                                    {"key": k, "value": {"stringValue": str(v)}}
                                    for k, v in (getattr(m, "tags", {}) or {}).items()
                                ],
                            }
                        ],
                        "aggregationTemporality": 2,  # cumulative
                        "isMonotonic": True,
                    },
                }
            )
        return {
            "resourceMetrics": [
                {
                    "resource": {"attributes": self._resource_attrs()},
                    "scopeMetrics": [
                        {"scope": {"name": "migration"}, "metrics": otlp_metrics}
                    ],
                }
            ]
        }

    def export(self, collector: Any) -> ExportResult:
        """Export telemetry in OTLP format.

        Parameters
        ----------
        collector
            A ``TelemetryCollector`` instance.

        Returns
        -------
        ExportResult
        """
        result = ExportResult(exporter="otlp")
        spans = list(getattr(collector, "spans", []))
        metrics = list(getattr(collector, "metrics", []))
        events = list(getattr(collector, "events", []))

        result.spans_sent = len(spans)
        result.metrics_sent = len(metrics)
        result.events_sent = len(events)

        if self._dry_run:
            # Build payloads for validation but don't send
            if spans:
                self._build_trace_payload(spans)
            if metrics:
                self._build_metrics_payload(metrics)
            logger.info(
                "OTLP dry-run: %d items prepared (not sent)", result.total_items
            )
            return result

        # Real send
        try:
            import httpx

            with httpx.Client(timeout=30) as client:
                if spans:
                    trace_payload = self._build_trace_payload(spans)
                    resp = client.post(
                        f"{self._endpoint}/v1/traces",
                        json=trace_payload,
                    )
                    resp.raise_for_status()
                if metrics:
                    metric_payload = self._build_metrics_payload(metrics)
                    resp = client.post(
                        f"{self._endpoint}/v1/metrics",
                        json=metric_payload,
                    )
                    resp.raise_for_status()
            logger.info("OTLP: exported %d items successfully", result.total_items)
        except ImportError:
            result.errors.append("httpx not installed — cannot send to OTLP endpoint")
        except Exception as exc:
            result.errors.append(str(exc))
            logger.exception("OTLP export failed")

        return result

    def to_json(self, collector: Any) -> str:
        """Return OTLP JSON representation without sending.

        Useful for debugging or writing to a file.
        """
        spans = list(getattr(collector, "spans", []))
        metrics = list(getattr(collector, "metrics", []))
        data: dict[str, Any] = {}
        if spans:
            data["traces"] = self._build_trace_payload(spans)
        if metrics:
            data["metrics"] = self._build_metrics_payload(metrics)
        return json.dumps(data, indent=2, default=str)
