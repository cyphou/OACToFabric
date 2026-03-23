"""End-to-end migration dry-run runner.

Provides a ``DryRunMigration`` class that exercises the full agent pipeline
without hitting live OAC / Fabric / Power BI services.  Useful for:

- Validating configuration before a real migration
- Capturing a performance baseline (timing per agent, memory)
- Generating a deployment manifest of what *would* be deployed
- CI smoke tests for the full pipeline
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from src.core.models import MigrationScope, ValidationReport

logger = logging.getLogger(__name__)


@dataclass
class AgentTiming:
    """Timing record for a single agent execution."""

    agent_id: str
    started_at: float  # epoch seconds
    finished_at: float = 0.0
    duration_ms: int = 0
    status: str = "pending"
    error: str = ""
    items_processed: int = 0

    def finish(self, status: str = "completed", *, error: str = "", items: int = 0) -> None:
        self.finished_at = time.time()
        self.duration_ms = int((self.finished_at - self.started_at) * 1000)
        self.status = status
        self.error = error
        self.items_processed = items


@dataclass
class PerformanceBaseline:
    """Aggregated performance data from a migration run."""

    total_duration_ms: int = 0
    agent_timings: list[AgentTiming] = field(default_factory=list)
    peak_memory_mb: float = 0.0
    total_items_processed: int = 0
    api_calls: dict[str, int] = field(default_factory=dict)

    def add_timing(self, timing: AgentTiming) -> None:
        self.agent_timings.append(timing)
        self.total_items_processed += timing.items_processed

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_duration_ms": self.total_duration_ms,
            "total_items_processed": self.total_items_processed,
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "api_calls": self.api_calls,
            "agents": [
                {
                    "agent_id": t.agent_id,
                    "duration_ms": t.duration_ms,
                    "status": t.status,
                    "items_processed": t.items_processed,
                    "error": t.error,
                }
                for t in self.agent_timings
            ],
        }

    def summary(self) -> str:
        """Human-readable performance summary."""
        lines = [
            f"=== Performance Baseline ===",
            f"Total duration: {self.total_duration_ms}ms",
            f"Total items processed: {self.total_items_processed}",
            f"Peak memory: {self.peak_memory_mb:.1f} MB",
            "",
        ]
        for t in sorted(self.agent_timings, key=lambda x: x.started_at):
            status_icon = "✓" if t.status == "completed" else "✗"
            lines.append(
                f"  {status_icon} {t.agent_id:20s}  {t.duration_ms:>6d}ms  "
                f"{t.items_processed:>4d} items  [{t.status}]"
            )
        return "\n".join(lines)


@dataclass
class DryRunResult:
    """Result of a full dry-run migration."""

    success: bool
    scope: MigrationScope
    agents_run: list[str]
    agents_skipped: list[str] = field(default_factory=list)
    baseline: PerformanceBaseline = field(default_factory=PerformanceBaseline)
    deployment_manifest: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    validation_report: ValidationReport | None = None


class DryRunMigration:
    """Execute a full migration in dry-run mode.

    Parameters
    ----------
    agent_runner
        Async callable ``(agent_id, scope) -> ValidationReport`` that
        instantiates and runs a single agent.
    agent_ids
        Ordered list of agent IDs to run.  Defaults to the standard 7.
    """

    DEFAULT_AGENT_ORDER = [
        "discovery",
        "schema",
        "etl",
        "semantic_model",
        "report",
        "security",
        "validation",
    ]

    def __init__(
        self,
        agent_runner: Any,
        agent_ids: list[str] | None = None,
    ) -> None:
        self._runner = agent_runner
        self._agent_ids = agent_ids or self.DEFAULT_AGENT_ORDER

    async def execute(self, scope: MigrationScope) -> DryRunResult:
        """Run all agents sequentially, capturing timing and results."""
        baseline = PerformanceBaseline()
        agents_run: list[str] = []
        errors: list[str] = []
        start = time.time()

        # Capture initial memory
        try:
            import tracemalloc
            tracemalloc.start()
        except Exception:
            pass

        last_report: ValidationReport | None = None

        for agent_id in self._agent_ids:
            timing = AgentTiming(agent_id=agent_id, started_at=time.time())

            try:
                logger.info("Dry-run: starting %s", agent_id)
                report = await self._runner(agent_id, scope)
                last_report = report

                items = len(getattr(report, "checks", []))
                timing.finish(status="completed", items=items)
                agents_run.append(agent_id)

            except Exception as exc:
                timing.finish(status="failed", error=str(exc))
                errors.append(f"{agent_id}: {exc}")
                agents_run.append(agent_id)
                logger.error("Dry-run: %s failed: %s", agent_id, exc)

            baseline.add_timing(timing)

        # Capture peak memory
        try:
            import tracemalloc
            if tracemalloc.is_tracing():
                _, peak = tracemalloc.get_traced_memory()
                baseline.peak_memory_mb = peak / (1024 * 1024)
                tracemalloc.stop()
        except Exception:
            pass

        end = time.time()
        baseline.total_duration_ms = int((end - start) * 1000)

        result = DryRunResult(
            success=len(errors) == 0,
            scope=scope,
            agents_run=agents_run,
            baseline=baseline,
            errors=errors,
            validation_report=last_report,
        )

        logger.info(
            "Dry-run complete: %d agents, %d errors, %dms",
            len(agents_run),
            len(errors),
            baseline.total_duration_ms,
        )
        return result
