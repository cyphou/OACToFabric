"""Orchestrator Agent — Agent 08.

Central coordinator that drives the full OAC → Fabric migration by:
  1. Discovering all assets (delegates to Agent 01).
  2. Planning migration waves based on inventory & dependency analysis.
  3. Executing waves in DAG-order, running agents in parallel where safe.
  4. Validating each wave (delegates to Agent 07).
  5. Handling failures (retries, escalation, blocking).
  6. Generating a final migration summary.

The orchestrator does **not** subclass ``MigrationAgent`` — it *owns*
agent instances and drives their lifecycle instead.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Awaitable

from src.core.models import (
    AgentState,
    Inventory,
    MigrationScope,
    TaskStatus,
    ValidationReport,
)

from .dag_engine import (
    DAGNode,
    ExecutionDAG,
    NodeStatus,
    build_default_migration_dag,
)
from .notification_manager import (
    Channel,
    NotificationManager,
    Severity,
    render_notification_log,
)
from .wave_planner import (
    MigrationWave,
    WavePlan,
    plan_waves,
    render_wave_plan,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class OrchestratorConfig:
    """Runtime configuration for the orchestrator."""

    max_retries: int = 3
    retry_backoff_seconds: list[int] = field(
        default_factory=lambda: [60, 300, 900]
    )
    heartbeat_interval_seconds: int = 60
    validate_after_each_wave: bool = True
    auto_advance_waves: bool = False
    parallel_agents_per_wave: int = 3
    max_items_per_wave: int = 50
    notification_channels: list[Channel] = field(
        default_factory=lambda: [Channel.LOG]
    )
    output_dir: str = "output/orchestrator"


# ---------------------------------------------------------------------------
# Agent execution result
# ---------------------------------------------------------------------------


@dataclass
class AgentExecutionResult:
    """Outcome of running a single agent within a wave."""

    agent_id: str
    status: NodeStatus
    validation: ValidationReport | None = None
    error: str = ""
    duration_seconds: float = 0.0
    retry_count: int = 0


@dataclass
class WaveExecutionResult:
    """Outcome of executing all agents in a wave."""

    wave_id: int
    wave_name: str
    agent_results: list[AgentExecutionResult] = field(default_factory=list)
    validation_passed: bool = False
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None

    @property
    def succeeded(self) -> int:
        return sum(
            1 for r in self.agent_results if r.status == NodeStatus.SUCCEEDED
        )

    @property
    def failed(self) -> int:
        return sum(
            1 for r in self.agent_results if r.status == NodeStatus.FAILED
        )


@dataclass
class MigrationSummary:
    """End-to-end migration summary."""

    wave_results: list[WaveExecutionResult] = field(default_factory=list)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None
    overall_status: str = "pending"
    total_agents_run: int = 0
    total_succeeded: int = 0
    total_failed: int = 0

    @property
    def all_passed(self) -> bool:
        return self.total_failed == 0 and self.total_agents_run > 0


# ---------------------------------------------------------------------------
# Agent runner protocol
# ---------------------------------------------------------------------------

# An *agent runner* is a callable that runs an agent's full lifecycle and
# returns a ValidationReport.  The orchestrator uses this abstraction so
# that tests can inject stubs without instantiating real agents.

AgentRunner = Callable[[str, MigrationScope], Awaitable[ValidationReport]]


async def _default_agent_runner(
    agent_id: str, scope: MigrationScope
) -> ValidationReport:
    """Placeholder runner — logs a warning and returns an empty report."""
    logger.warning("Default agent runner invoked for %s (no-op)", agent_id)
    return ValidationReport(agent_id=agent_id, total_checks=1, passed=1)


# ---------------------------------------------------------------------------
# Orchestrator Agent
# ---------------------------------------------------------------------------


class OrchestratorAgent:
    """Agent 08 — Migration Orchestrator."""

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        agent_runner: AgentRunner | None = None,
        lakehouse_client: Any | None = None,
    ) -> None:
        self.config = config or OrchestratorConfig()
        self._runner = agent_runner or _default_agent_runner
        self._lakehouse = lakehouse_client
        self._notifier = NotificationManager(
            enabled_channels=self.config.notification_channels,
        )
        self._output_dir = Path(self.config.output_dir)
        self._dag: ExecutionDAG | None = None
        self._wave_plan: WavePlan | None = None
        self._summary = MigrationSummary()

    # ------------------------------------------------------------------
    # Full migration lifecycle
    # ------------------------------------------------------------------

    async def run_migration(self, scope: MigrationScope) -> MigrationSummary:
        """Execute the complete OAC → Fabric migration.

        Steps:
        1. Build DAG & discover.
        2. Plan waves.
        3. For each wave: execute agents ➜ validate ➜ notify.
        4. Generate final reports.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._summary = MigrationSummary()

        # --- 1. Build DAG ---
        self._dag = build_default_migration_dag()

        # --- 2. Discovery (always first) ---
        self._notifier.notify(
            "wave_started",
            "Migration started",
            f"Scope: {len(scope.include_paths)} paths, "
            f"wave={scope.wave}",
        )

        discovery_result = await self._execute_agent(
            "01-discovery", scope
        )

        if discovery_result.status == NodeStatus.FAILED:
            self._summary.overall_status = "failed"
            self._notifier.notify(
                "migration_halted",
                "Migration halted",
                f"Discovery failed: {discovery_result.error}",
                severity=Severity.CRITICAL,
            )
            return self._finalize()

        # --- 3. Plan waves from inventory ---
        inventory = await self._load_inventory(scope)
        self._wave_plan = plan_waves(
            inventory, max_items_per_wave=self.config.max_items_per_wave
        )

        # Write wave plan
        self._write_report(
            "wave_plan.md", render_wave_plan(self._wave_plan)
        )

        # --- 4. Execute each wave ---
        for wave in self._wave_plan.waves:
            wave_result = await self.execute_wave(wave, scope)
            self._summary.wave_results.append(wave_result)

            if wave_result.failed > 0 and not self.config.auto_advance_waves:
                self._notifier.notify(
                    "migration_halted",
                    f"Wave {wave.id} failures — migration paused",
                    f"{wave_result.failed} agent(s) failed in {wave.name}",
                    severity=Severity.HIGH,
                    wave_id=str(wave.id),
                )
                break

        # --- 5. Final summary ---
        return self._finalize()

    # ------------------------------------------------------------------
    # Wave execution
    # ------------------------------------------------------------------

    async def execute_wave(
        self,
        wave: MigrationWave,
        scope: MigrationScope,
    ) -> WaveExecutionResult:
        """Execute all agents assigned to a wave.

        Agents within the wave run in DAG-order; independent agents
        within the same batch run in parallel.
        """
        result = WaveExecutionResult(
            wave_id=wave.id, wave_name=wave.name
        )

        self._notifier.notify(
            "wave_started",
            f"{wave.name} started",
            f"{wave.count} items, agents: {wave.agent_ids}",
            wave_id=str(wave.id),
        )

        # Build a sub-DAG for the agents in this wave
        sub_dag = self._build_wave_dag(wave.agent_ids)
        batches = sub_dag.topological_batches()

        for batch in batches:
            # Limit parallelism
            sem = asyncio.Semaphore(self.config.parallel_agents_per_wave)

            async def _run_with_sem(agent_id: str) -> AgentExecutionResult:
                async with sem:
                    return await self._execute_agent_with_retry(
                        agent_id, scope
                    )

            tasks = [_run_with_sem(aid) for aid in batch]
            batch_results = await asyncio.gather(*tasks)

            for ar in batch_results:
                result.agent_results.append(ar)
                self._summary.total_agents_run += 1
                if ar.status == NodeStatus.SUCCEEDED:
                    self._summary.total_succeeded += 1
                else:
                    self._summary.total_failed += 1

        # Wave validation
        if self.config.validate_after_each_wave:
            val_result = await self._execute_agent("07-validation", scope)
            result.validation_passed = (
                val_result.status == NodeStatus.SUCCEEDED
            )

        result.completed_at = datetime.now(timezone.utc)

        self._notifier.notify(
            "wave_completed",
            f"{wave.name} completed",
            f"{result.succeeded}/{len(result.agent_results)} agents succeeded",
            wave_id=str(wave.id),
        )

        return result

    # ------------------------------------------------------------------
    # Agent execution
    # ------------------------------------------------------------------

    async def _execute_agent(
        self,
        agent_id: str,
        scope: MigrationScope,
    ) -> AgentExecutionResult:
        """Execute a single agent's full lifecycle."""
        start = datetime.now(timezone.utc)
        try:
            report = await self._runner(agent_id, scope)
            duration = (datetime.now(timezone.utc) - start).total_seconds()

            status = (
                NodeStatus.SUCCEEDED
                if report.failed == 0
                else NodeStatus.FAILED
            )

            if self._dag:
                if status == NodeStatus.SUCCEEDED:
                    self._dag.mark_succeeded(agent_id)
                else:
                    self._dag.mark_failed(agent_id)

            self._notifier.notify(
                "agent_completed",
                f"Agent {agent_id} finished",
                f"Status: {status.value}, checks: {report.passed}/{report.total_checks}",
                agent_id=agent_id,
            )

            return AgentExecutionResult(
                agent_id=agent_id,
                status=status,
                validation=report,
                duration_seconds=duration,
            )

        except Exception as exc:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            if self._dag:
                self._dag.mark_failed(agent_id, str(exc))

            return AgentExecutionResult(
                agent_id=agent_id,
                status=NodeStatus.FAILED,
                error=str(exc),
                duration_seconds=duration,
            )

    async def _execute_agent_with_retry(
        self,
        agent_id: str,
        scope: MigrationScope,
    ) -> AgentExecutionResult:
        """Execute an agent with retry logic."""
        max_retries = self.config.max_retries
        backoffs = self.config.retry_backoff_seconds

        for attempt in range(max_retries + 1):
            result = await self._execute_agent(agent_id, scope)

            if result.status == NodeStatus.SUCCEEDED:
                result.retry_count = attempt
                return result

            if attempt < max_retries:
                delay = backoffs[min(attempt, len(backoffs) - 1)]
                self._notifier.notify(
                    "agent_failed_first",
                    f"Agent {agent_id} failed (attempt {attempt + 1})",
                    f"Retrying in {delay}s — {result.error}",
                    agent_id=agent_id,
                    severity=Severity.WARN,
                )
                await asyncio.sleep(delay)
            else:
                self._notifier.notify(
                    "agent_failed_max",
                    f"Agent {agent_id} failed after {max_retries + 1} attempts",
                    f"Error: {result.error}",
                    agent_id=agent_id,
                    severity=Severity.HIGH,
                )
                # Block dependents
                if self._dag:
                    blocked = self._dag.block_dependents(agent_id)
                    if blocked:
                        logger.warning(
                            "Blocked dependents of %s: %s", agent_id, blocked
                        )

        result.retry_count = max_retries
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_inventory(self, scope: MigrationScope) -> Inventory:
        """Load inventory from Lakehouse or build a minimal one from scope."""
        from src.core.models import AssetType, InventoryItem

        if self._lakehouse is not None:
            rows = self._lakehouse.read_inventory()
            items = [
                InventoryItem(
                    id=r["id"],
                    asset_type=AssetType(r["asset_type"]),
                    source_path=r.get("source_path", ""),
                    name=r.get("name", ""),
                    metadata=r.get("metadata", {}),
                )
                for r in rows
            ]
            return Inventory(items=items)

        # Fallback: build from scope
        items = [
            InventoryItem(
                id=f"scope__{i}",
                asset_type=AssetType.PHYSICAL_TABLE,
                source_path=p,
                name=p.strip("/").split("/")[-1],
            )
            for i, p in enumerate(scope.include_paths)
        ]
        return Inventory(items=items)

    def _build_wave_dag(self, agent_ids: list[str]) -> ExecutionDAG:
        """Build a sub-DAG containing only the specified agents."""
        if not self._dag:
            return ExecutionDAG()

        sub = ExecutionDAG()
        agent_set = set(agent_ids)
        for aid in agent_ids:
            node = self._dag.get_node(aid)
            if node:
                sub.add_node(aid, node.label)

        # Add edges that exist in the full DAG between these agents
        for edge in self._dag.edges:
            if edge.source in agent_set and edge.target in agent_set:
                sub.add_edge(edge.source, edge.target)

        return sub

    def _finalize(self) -> MigrationSummary:
        """Finalize the migration summary and write reports."""
        self._summary.completed_at = datetime.now(timezone.utc)
        self._summary.overall_status = (
            "succeeded" if self._summary.all_passed else "failed"
        )

        # Write summary report
        self._write_report(
            "migration_summary.md",
            self.generate_summary_report(),
        )

        # Write notification log
        self._write_report(
            "notification_log.md",
            render_notification_log(self._notifier.history),
        )

        self._notifier.notify(
            "migration_complete",
            "Migration completed",
            f"Status: {self._summary.overall_status} — "
            f"{self._summary.total_succeeded}/{self._summary.total_agents_run} "
            f"agents succeeded",
        )

        return self._summary

    def _write_report(self, filename: str, content: str) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        (self._output_dir / filename).write_text(content, encoding="utf-8")
        logger.info("Wrote %s", filename)

    # ------------------------------------------------------------------
    # Summary report
    # ------------------------------------------------------------------

    def generate_summary_report(self) -> str:
        """Generate a Markdown migration summary."""
        s = self._summary
        lines = [
            "# Migration Summary",
            "",
            f"**Status:** {s.overall_status}",
            f"**Started:** {s.started_at.isoformat()}",
            f"**Completed:** {s.completed_at.isoformat() if s.completed_at else '—'}",
            f"**Agents run:** {s.total_agents_run}",
            f"**Succeeded:** {s.total_succeeded}",
            f"**Failed:** {s.total_failed}",
            "",
        ]

        if s.wave_results:
            lines.extend([
                "## Wave Results",
                "",
                "| Wave | Agents Run | Succeeded | Failed | Validation |",
                "|---|---|---|---|---|",
            ])
            for wr in s.wave_results:
                val = "PASS" if wr.validation_passed else "FAIL"
                lines.append(
                    f"| {wr.wave_name} | {len(wr.agent_results)} | "
                    f"{wr.succeeded} | {wr.failed} | {val} |"
                )
            lines.append("")

        # Per-agent detail
        lines.extend([
            "## Agent Detail",
            "",
            "| Agent | Status | Duration (s) | Retries | Error |",
            "|---|---|---|---|---|",
        ])
        for wr in s.wave_results:
            for ar in wr.agent_results:
                lines.append(
                    f"| {ar.agent_id} | {ar.status.value} | "
                    f"{ar.duration_seconds:.1f} | {ar.retry_count} | "
                    f"{ar.error[:80] if ar.error else '—'} |"
                )
        lines.append("")

        # DAG status
        if self._dag:
            lines.extend([
                "## DAG Status",
                "",
                "| Node | Status |",
                "|---|---|",
            ])
            for node in self._dag.nodes:
                lines.append(f"| {node.id} | {node.status.value} |")
            lines.append("")

        return "\n".join(lines)
