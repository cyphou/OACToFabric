"""Migration Analytics Dashboard — metrics collection and report generation.

Provides:
- ``MigrationMetrics`` — structured snapshot of migration progress.
- ``MetricsCollector`` — collect and aggregate metrics from Lakehouse state.
- ``DashboardDataExporter`` — export metrics as JSON/CSV for Power BI.
- ``PBITTemplateGenerator`` — generate a .pbit-compatible JSON manifest.
- ``ExecutiveSummary`` — executive summary computation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metric snapshots
# ---------------------------------------------------------------------------


@dataclass
class AgentMetrics:
    """Per-agent progress metrics."""

    agent_id: str
    agent_name: str = ""
    status: str = "pending"  # pending | running | completed | failed
    items_total: int = 0
    items_completed: int = 0
    items_failed: int = 0
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    error_messages: list[str] = field(default_factory=list)

    @property
    def progress_pct(self) -> float:
        if self.items_total == 0:
            return 0.0
        return round(self.items_completed / self.items_total * 100, 1)

    @property
    def success_rate(self) -> float:
        done = self.items_completed + self.items_failed
        if done == 0:
            return 0.0
        return round(self.items_completed / done * 100, 1)


@dataclass
class WaveMetrics:
    """Per-wave progress metrics."""

    wave_number: int
    status: str = "pending"
    agents: list[AgentMetrics] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""

    @property
    def total_items(self) -> int:
        return sum(a.items_total for a in self.agents)

    @property
    def completed_items(self) -> int:
        return sum(a.items_completed for a in self.agents)

    @property
    def progress_pct(self) -> float:
        if self.total_items == 0:
            return 0.0
        return round(self.completed_items / self.total_items * 100, 1)


@dataclass
class CostMetrics:
    """Resource cost tracking."""

    estimated_ru_consumed: float = 0.0
    compute_hours: float = 0.0
    estimated_cost_usd: float = 0.0
    budget_usd: float = 0.0

    @property
    def budget_remaining_pct(self) -> float:
        if self.budget_usd <= 0:
            return 100.0
        used = min(self.estimated_cost_usd, self.budget_usd)
        return round((1 - used / self.budget_usd) * 100, 1)


@dataclass
class MigrationMetrics:
    """Top-level metrics snapshot for a migration run."""

    migration_id: str = ""
    timestamp: str = ""
    overall_status: str = "not_started"  # not_started | in_progress | completed | failed
    waves: list[WaveMetrics] = field(default_factory=list)
    cost: CostMetrics = field(default_factory=CostMetrics)

    # Asset counts
    total_assets: int = 0
    assets_migrated: int = 0
    assets_failed: int = 0
    assets_skipped: int = 0

    # Validation
    validation_pass_rate: float = 0.0
    critical_issues: int = 0

    @property
    def overall_progress_pct(self) -> float:
        if self.total_assets == 0:
            return 0.0
        return round(self.assets_migrated / self.total_assets * 100, 1)

    @property
    def wave_count(self) -> int:
        return len(self.waves)

    @property
    def completed_wave_count(self) -> int:
        return sum(1 for w in self.waves if w.status == "completed")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Metrics collector
# ---------------------------------------------------------------------------


class MetricsCollector:
    """Collect and aggregate migration metrics.

    In production, reads from Lakehouse Delta tables.
    Provides builder methods for constructing metrics programmatically.
    """

    def __init__(self) -> None:
        self._snapshots: list[MigrationMetrics] = []

    def create_snapshot(
        self,
        migration_id: str,
        total_assets: int = 0,
    ) -> MigrationMetrics:
        metrics = MigrationMetrics(
            migration_id=migration_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_assets=total_assets,
        )
        self._snapshots.append(metrics)
        return metrics

    def add_wave(
        self,
        metrics: MigrationMetrics,
        wave_number: int,
        agents: list[AgentMetrics] | None = None,
    ) -> WaveMetrics:
        wave = WaveMetrics(wave_number=wave_number, agents=agents or [])
        metrics.waves.append(wave)
        return wave

    def update_agent(
        self,
        metrics: MigrationMetrics,
        agent_id: str,
        *,
        status: str = "",
        items_completed: int = 0,
        items_failed: int = 0,
    ) -> AgentMetrics | None:
        for wave in metrics.waves:
            for agent in wave.agents:
                if agent.agent_id == agent_id:
                    if status:
                        agent.status = status
                    agent.items_completed = items_completed
                    agent.items_failed = items_failed
                    return agent
        return None

    def compute_totals(self, metrics: MigrationMetrics) -> None:
        """Recompute aggregate totals from wave/agent data."""
        migrated = 0
        failed = 0
        for wave in metrics.waves:
            for agent in wave.agents:
                migrated += agent.items_completed
                failed += agent.items_failed
        metrics.assets_migrated = migrated
        metrics.assets_failed = failed

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)

    @property
    def latest(self) -> MigrationMetrics | None:
        return self._snapshots[-1] if self._snapshots else None


# ---------------------------------------------------------------------------
# Dashboard data exporter
# ---------------------------------------------------------------------------


class DashboardDataExporter:
    """Export metrics as JSON/CSV for Power BI consumption."""

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export_json(self, metrics: MigrationMetrics, filename: str = "metrics.json") -> Path:
        path = self._output_dir / filename
        path.write_text(json.dumps(metrics.to_dict(), indent=2, default=str), encoding="utf-8")
        return path

    def export_agent_csv(self, metrics: MigrationMetrics, filename: str = "agent_metrics.csv") -> Path:
        path = self._output_dir / filename
        lines = ["wave,agent_id,agent_name,status,items_total,items_completed,items_failed,progress_pct,duration_seconds"]
        for wave in metrics.waves:
            for agent in wave.agents:
                lines.append(
                    f"{wave.wave_number},{agent.agent_id},{agent.agent_name},"
                    f"{agent.status},{agent.items_total},{agent.items_completed},"
                    f"{agent.items_failed},{agent.progress_pct},{agent.duration_seconds}"
                )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def export_wave_csv(self, metrics: MigrationMetrics, filename: str = "wave_metrics.csv") -> Path:
        path = self._output_dir / filename
        lines = ["wave_number,status,total_items,completed_items,progress_pct"]
        for wave in metrics.waves:
            lines.append(
                f"{wave.wave_number},{wave.status},{wave.total_items},"
                f"{wave.completed_items},{wave.progress_pct}"
            )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def export_all(self, metrics: MigrationMetrics) -> list[Path]:
        """Export all formats and return file paths."""
        return [
            self.export_json(metrics),
            self.export_agent_csv(metrics),
            self.export_wave_csv(metrics),
        ]


# ---------------------------------------------------------------------------
# Power BI template manifest
# ---------------------------------------------------------------------------


@dataclass
class PBITPage:
    """A page in the Power BI template."""

    name: str
    visuals: list[dict[str, Any]] = field(default_factory=list)


class PBITTemplateGenerator:
    """Generate a Power BI template manifest (JSON) for the analytics dashboard.

    Pages:
    1. Executive Summary — KPI cards, overall progress, timeline
    2. Wave Progress — wave-by-wave drill-down
    3. Agent Details — per-agent metrics
    4. Cost Analysis — budget burn-down
    5. Validation — quality and reconciliation
    """

    def __init__(self, data_source_path: str = "metrics.json") -> None:
        self._data_source = data_source_path

    def generate_manifest(self) -> dict[str, Any]:
        """Generate the full PBIT-compatible manifest."""
        return {
            "template_version": "1.0.0",
            "name": "OAC Migration Analytics",
            "description": "Migration progress dashboard for OAC → Fabric & Power BI",
            "data_sources": [
                {
                    "name": "MigrationMetrics",
                    "type": "json",
                    "path": self._data_source,
                },
                {
                    "name": "AgentMetrics",
                    "type": "csv",
                    "path": "agent_metrics.csv",
                },
                {
                    "name": "WaveMetrics",
                    "type": "csv",
                    "path": "wave_metrics.csv",
                },
            ],
            "pages": [p.__dict__ for p in self._build_pages()],
            "theme": "default",
            "refresh_schedule": "daily",
        }

    def _build_pages(self) -> list[PBITPage]:
        return [
            PBITPage(
                name="Executive Summary",
                visuals=[
                    {"type": "card", "field": "overall_progress_pct", "title": "Overall Progress"},
                    {"type": "card", "field": "assets_migrated", "title": "Assets Migrated"},
                    {"type": "card", "field": "assets_failed", "title": "Assets Failed"},
                    {"type": "card", "field": "validation_pass_rate", "title": "Validation Pass Rate"},
                    {"type": "donut", "field": "status_distribution", "title": "Status Distribution"},
                    {"type": "line", "field": "timeline_progress", "title": "Migration Timeline"},
                ],
            ),
            PBITPage(
                name="Wave Progress",
                visuals=[
                    {"type": "stackedBar", "field": "wave_progress", "title": "Progress by Wave"},
                    {"type": "table", "field": "wave_details", "title": "Wave Details"},
                    {"type": "line", "field": "wave_timeline", "title": "Wave Timeline"},
                ],
            ),
            PBITPage(
                name="Agent Details",
                visuals=[
                    {"type": "matrix", "field": "agent_metrics", "title": "Agent × Wave Matrix"},
                    {"type": "bar", "field": "agent_duration", "title": "Duration by Agent"},
                    {"type": "bar", "field": "agent_items", "title": "Items by Agent"},
                ],
            ),
            PBITPage(
                name="Cost Analysis",
                visuals=[
                    {"type": "card", "field": "estimated_cost_usd", "title": "Estimated Cost"},
                    {"type": "card", "field": "budget_remaining_pct", "title": "Budget Remaining"},
                    {"type": "waterfall", "field": "cost_breakdown", "title": "Cost Breakdown"},
                    {"type": "line", "field": "cost_burndown", "title": "Cost Burn-Down"},
                ],
            ),
            PBITPage(
                name="Validation",
                visuals=[
                    {"type": "card", "field": "validation_pass_rate", "title": "Pass Rate"},
                    {"type": "card", "field": "critical_issues", "title": "Critical Issues"},
                    {"type": "table", "field": "validation_details", "title": "Validation Results"},
                    {"type": "bar", "field": "issues_by_type", "title": "Issues by Type"},
                ],
            ),
        ]

    def save_manifest(self, output_dir: str | Path) -> Path:
        """Save the template manifest to a file."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "migration_dashboard.pbit.json"
        path.write_text(json.dumps(self.generate_manifest(), indent=2), encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------


@dataclass
class ExecutiveSummary:
    """Computed executive summary of a migration."""

    migration_id: str = ""
    overall_progress: float = 0.0
    total_assets: int = 0
    migrated: int = 0
    failed: int = 0
    skipped: int = 0
    waves_total: int = 0
    waves_completed: int = 0
    validation_pass_rate: float = 0.0
    estimated_cost: float = 0.0
    timeline_status: str = "on_track"  # on_track | at_risk | delayed
    top_risks: list[str] = field(default_factory=list)

    @staticmethod
    def from_metrics(metrics: MigrationMetrics) -> "ExecutiveSummary":
        risks: list[str] = []
        if metrics.assets_failed > 0:
            risks.append(f"{metrics.assets_failed} assets failed migration")
        if metrics.critical_issues > 0:
            risks.append(f"{metrics.critical_issues} critical validation issues")
        if metrics.cost.budget_remaining_pct < 20:
            risks.append("Budget near exhaustion")

        # Timeline status heuristic
        completed_waves = metrics.completed_wave_count
        total_waves = metrics.wave_count
        status = "on_track"
        if total_waves > 0 and metrics.assets_failed > metrics.total_assets * 0.1:
            status = "at_risk"
        if total_waves > 0 and completed_waves < total_waves * 0.3 and metrics.overall_status == "in_progress":
            status = "delayed"

        return ExecutiveSummary(
            migration_id=metrics.migration_id,
            overall_progress=metrics.overall_progress_pct,
            total_assets=metrics.total_assets,
            migrated=metrics.assets_migrated,
            failed=metrics.assets_failed,
            skipped=metrics.assets_skipped,
            waves_total=total_waves,
            waves_completed=completed_waves,
            validation_pass_rate=metrics.validation_pass_rate,
            estimated_cost=metrics.cost.estimated_cost_usd,
            timeline_status=status,
            top_risks=risks,
        )
