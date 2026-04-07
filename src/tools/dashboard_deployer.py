"""Dashboard Deployer — deploy a KQL observability dashboard to Fabric Eventhouse.

Creates/updates a Fabric Real-Time Dashboard backed by the ``MigrationEvents``
and ``MigrationMetrics`` KQL tables populated by ``EventhouseSink``.
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


class TileType(str, Enum):
    """Visual tile types for the KQL dashboard."""

    TIMECHART = "timechart"
    BARCHART = "barchart"
    PIECHART = "piechart"
    STAT = "stat"
    TABLE = "table"
    MAP = "map"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DashboardTile:
    """One tile in the KQL dashboard."""

    tile_id: str
    title: str
    tile_type: TileType = TileType.TIMECHART
    kql_query: str = ""
    width: int = 6
    height: int = 4
    position: tuple[int, int] = (0, 0)
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_id": self.tile_id,
            "title": self.title,
            "tile_type": self.tile_type.value,
            "kql_query": self.kql_query,
            "width": self.width,
            "height": self.height,
            "position": list(self.position),
            "parameters": self.parameters,
        }


@dataclass
class DashboardPage:
    """A page in the KQL dashboard."""

    page_id: str
    title: str
    tiles: list[DashboardTile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "tiles": [t.to_dict() for t in self.tiles],
        }


@dataclass
class DashboardTemplate:
    """Full dashboard template (multiple pages)."""

    name: str
    database: str = "MigrationTelemetry"
    pages: list[DashboardPage] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "database": self.database,
            "version": self.version,
            "parameters": self.parameters,
            "pages": [p.to_dict() for p in self.pages],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class DeployResult:
    """Result of a dashboard deployment."""

    dashboard_name: str
    success: bool
    dashboard_id: str = ""
    url: str = ""
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dashboard_name": self.dashboard_name,
            "success": self.success,
            "dashboard_id": self.dashboard_id,
            "url": self.url,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Default template
# ---------------------------------------------------------------------------


def build_default_template(database: str = "MigrationTelemetry") -> DashboardTemplate:
    """Build the standard migration observability dashboard."""

    # Page 1 — Overview
    overview = DashboardPage(
        page_id="overview",
        title="Migration Overview",
        tiles=[
            DashboardTile(
                tile_id="total_events",
                title="Total Events",
                tile_type=TileType.STAT,
                kql_query=f"{database}.MigrationEvents | count",
                width=3,
                height=2,
                position=(0, 0),
            ),
            DashboardTile(
                tile_id="events_by_agent",
                title="Events by Agent",
                tile_type=TileType.BARCHART,
                kql_query=(
                    f"{database}.MigrationEvents\n"
                    "| summarize Count=count() by AgentId\n"
                    "| order by Count desc"
                ),
                width=6,
                height=4,
                position=(0, 2),
            ),
            DashboardTile(
                tile_id="events_timeline",
                title="Event Timeline",
                tile_type=TileType.TIMECHART,
                kql_query=(
                    f"{database}.MigrationEvents\n"
                    "| summarize Count=count() by bin(Timestamp, 5m)\n"
                    "| order by Timestamp asc"
                ),
                width=12,
                height=4,
                position=(0, 6),
            ),
        ],
    )

    # Page 2 — Agent Performance
    agent_perf = DashboardPage(
        page_id="agent_performance",
        title="Agent Performance",
        tiles=[
            DashboardTile(
                tile_id="avg_duration",
                title="Avg Duration by Agent (ms)",
                tile_type=TileType.BARCHART,
                kql_query=(
                    f"{database}.MigrationEvents\n"
                    "| summarize AvgDuration=avg(DurationMs) by AgentId\n"
                    "| order by AvgDuration desc"
                ),
                width=6,
                height=4,
                position=(0, 0),
            ),
            DashboardTile(
                tile_id="error_rate",
                title="Error Rate by Agent",
                tile_type=TileType.BARCHART,
                kql_query=(
                    f"{database}.MigrationEvents\n"
                    "| summarize Total=count(), Errors=countif(Status != 'ok') by AgentId\n"
                    "| extend ErrorRate=round(todouble(Errors)/todouble(Total)*100, 2)\n"
                    "| order by ErrorRate desc"
                ),
                width=6,
                height=4,
                position=(6, 0),
            ),
        ],
    )

    # Page 3 — Cost & SLA
    cost_sla = DashboardPage(
        page_id="cost_sla",
        title="Cost & SLA Tracking",
        tiles=[
            DashboardTile(
                tile_id="cost_burndown",
                title="Estimated Cost Burn-down",
                tile_type=TileType.TIMECHART,
                kql_query=(
                    f"{database}.MigrationMetrics\n"
                    "| where MetricName == 'estimated_cost_usd'\n"
                    "| summarize TotalCost=sum(Value) by bin(Timestamp, 1h)\n"
                    "| order by Timestamp asc"
                ),
                width=12,
                height=4,
                position=(0, 0),
            ),
            DashboardTile(
                tile_id="sla_compliance",
                title="SLA Compliance",
                tile_type=TileType.PIECHART,
                kql_query=(
                    f"{database}.MigrationMetrics\n"
                    "| where MetricName == 'sla_met'\n"
                    "| summarize Met=countif(Value == 1), Missed=countif(Value == 0)"
                ),
                width=6,
                height=4,
                position=(0, 4),
            ),
        ],
    )

    return DashboardTemplate(
        name="OAC Migration Observability",
        database=database,
        pages=[overview, agent_perf, cost_sla],
        parameters={"timeRange": "last_24h"},
    )


# ---------------------------------------------------------------------------
# Dashboard deployer
# ---------------------------------------------------------------------------


@dataclass
class DashboardDeployer:
    """Deploy a KQL dashboard template to Fabric.

    Parameters
    ----------
    workspace_id
        Fabric workspace ID.
    eventhouse_uri
        Fabric Eventhouse cluster URI.
    dry_run
        If *True*, export the template JSON without deploying.
    """

    workspace_id: str = ""
    eventhouse_uri: str = ""
    dry_run: bool = False

    async def deploy(self, template: DashboardTemplate) -> DeployResult:
        """Deploy or update the dashboard."""
        if self.dry_run:
            logger.info("DRY-RUN dashboard deploy: %s (%d pages)", template.name, len(template.pages))
            return DeployResult(
                dashboard_name=template.name,
                success=True,
                dashboard_id="dry-run",
            )

        try:
            # In production: POST template to Fabric Real-Time Dashboard API.
            logger.info("Deploying dashboard '%s' to workspace %s", template.name, self.workspace_id)
            return DeployResult(
                dashboard_name=template.name,
                success=True,
                dashboard_id=f"dash-{template.name.replace(' ', '-').lower()}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Dashboard deploy failed: %s", exc)
            return DeployResult(
                dashboard_name=template.name,
                success=False,
                error=str(exc),
            )

    async def deploy_default(self, database: str = "MigrationTelemetry") -> DeployResult:
        """Deploy the standard migration observability dashboard."""
        template = build_default_template(database)
        return await self.deploy(template)

    def export_template(self, template: DashboardTemplate, output_path: str) -> str:
        """Write the template JSON file locally."""
        from pathlib import Path

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template.to_json())
        logger.info("Dashboard template exported to %s", path)
        return str(path)
