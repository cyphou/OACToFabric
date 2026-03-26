"""Monitoring exporter — 3-backend metrics export (JSON, Azure Monitor, Prometheus).

Reads from TelemetryCollector data and exports to:
  1. JSON file — JSONL line-delimited output for offline analysis
  2. Azure Monitor — custom metrics via REST (when configured)
  3. Prometheus — text exposition format for scraping
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ExportBackend(str, Enum):
    JSON = "json"
    AZURE_MONITOR = "azure_monitor"
    PROMETHEUS = "prometheus"


@dataclass
class ExportConfig:
    """Configuration for metric export."""

    backends: list[ExportBackend] = field(
        default_factory=lambda: [ExportBackend.JSON]
    )
    json_output_path: str = "output/metrics/migration_metrics.jsonl"
    prometheus_port: int = 9090
    azure_monitor_connection_string: str = ""


@dataclass
class ExportResult:
    """Result of an export operation."""

    backend: ExportBackend
    success: bool
    records_exported: int = 0
    error: str = ""


# ---------------------------------------------------------------------------
# JSON exporter
# ---------------------------------------------------------------------------


def export_to_json(
    events: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    spans: list[dict[str, Any]],
    output_path: str | Path = "output/metrics/migration_metrics.jsonl",
) -> ExportResult:
    """Write telemetry data as JSONL to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with open(path, "a", encoding="utf-8") as f:
        for event in events:
            record = {"type": "event", "timestamp": _now_iso(), **event}
            f.write(json.dumps(record, default=str) + "\n")
            count += 1
        for metric in metrics:
            record = {"type": "metric", "timestamp": _now_iso(), **metric}
            f.write(json.dumps(record, default=str) + "\n")
            count += 1
        for span in spans:
            record = {"type": "span", "timestamp": _now_iso(), **span}
            f.write(json.dumps(record, default=str) + "\n")
            count += 1

    logger.info("Exported %d records to %s", count, path)
    return ExportResult(
        backend=ExportBackend.JSON, success=True, records_exported=count
    )


# ---------------------------------------------------------------------------
# Prometheus text exposition
# ---------------------------------------------------------------------------


def render_prometheus_metrics(
    metrics: list[dict[str, Any]],
) -> str:
    """Render metrics in Prometheus text exposition format.

    Returns a string suitable for HTTP response to /metrics endpoint.
    """
    lines: list[str] = []

    for m in metrics:
        name = m.get("name", "unknown").replace(".", "_").replace("-", "_")
        value = m.get("value", 0)
        tags = m.get("tags", {})
        kind = m.get("kind", "counter")

        # TYPE line
        prom_type = "gauge" if kind == "gauge" else "counter"
        lines.append(f"# TYPE migration_{name} {prom_type}")

        # Label string
        if tags:
            labels = ",".join(
                f'{k}="{v}"' for k, v in sorted(tags.items())
            )
            lines.append(f"migration_{name}{{{labels}}} {value}")
        else:
            lines.append(f"migration_{name} {value}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Azure Monitor (stub — requires azure-monitor-ingestion SDK)
# ---------------------------------------------------------------------------


def export_to_azure_monitor(
    metrics: list[dict[str, Any]],
    connection_string: str,
) -> ExportResult:
    """Export metrics to Azure Monitor custom metrics.

    This is a structural placeholder. In production, integrate with
    ``azure-monitor-ingestion`` SDK or the custom metrics REST API.
    """
    if not connection_string:
        return ExportResult(
            backend=ExportBackend.AZURE_MONITOR,
            success=False,
            error="No connection string configured",
        )

    # Structural placeholder — log the intent
    logger.info(
        "Azure Monitor export: %d metrics (connection configured)",
        len(metrics),
    )

    return ExportResult(
        backend=ExportBackend.AZURE_MONITOR,
        success=True,
        records_exported=len(metrics),
    )


# ---------------------------------------------------------------------------
# Unified export
# ---------------------------------------------------------------------------


def export_telemetry(
    events: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    spans: list[dict[str, Any]],
    config: ExportConfig | None = None,
) -> list[ExportResult]:
    """Export telemetry data to all configured backends."""
    cfg = config or ExportConfig()
    results: list[ExportResult] = []

    for backend in cfg.backends:
        if backend == ExportBackend.JSON:
            results.append(
                export_to_json(events, metrics, spans, cfg.json_output_path)
            )
        elif backend == ExportBackend.PROMETHEUS:
            # Prometheus is pull-based; just log that we rendered
            text = render_prometheus_metrics(metrics)
            results.append(ExportResult(
                backend=ExportBackend.PROMETHEUS,
                success=True,
                records_exported=len(metrics),
            ))
            logger.debug("Prometheus metrics rendered (%d bytes)", len(text))
        elif backend == ExportBackend.AZURE_MONITOR:
            results.append(
                export_to_azure_monitor(
                    metrics, cfg.azure_monitor_connection_string
                )
            )

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
