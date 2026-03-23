"""State coordinator — bridges agent lifecycle with Lakehouse persistence.

Wraps the ``LakehouseClient`` to provide high-level helpers that the
``RunnerFactory`` and ``OrchestratorAgent`` call at key lifecycle points:

- **Before** running an agent → write ``ASSIGNED`` task row.
- Agent starts  → update to ``IN_PROGRESS``.
- Agent finishes → update to ``DONE`` / ``FAILED`` with result.
- Validation results → written to ``validation_results`` Delta table.
- Mapping rules → accumulated from Agents 02/03/04 and shared downstream.

Usage::

    coord = StateCoordinator(lakehouse_client)
    await coord.on_agent_start("01-discovery", scope)
    ...
    await coord.on_agent_complete("01-discovery", report)
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.core.models import (
    AgentTask,
    MigrationScope,
    TaskStatus,
    ValidationReport,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory fallback (when no LakehouseClient is available)
# ---------------------------------------------------------------------------


@dataclass
class _InMemoryStore:
    """Minimal in-memory store mirroring essential Lakehouse operations."""

    tasks: list[dict[str, Any]] = field(default_factory=list)
    mapping_rules: list[dict[str, Any]] = field(default_factory=list)
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# State coordinator
# ---------------------------------------------------------------------------


class StateCoordinator:
    """Manages agent state transitions and cross-agent data sharing.

    Parameters
    ----------
    lakehouse_client:
        A ``LakehouseClient`` instance.  If *None*, an in-memory store
        is used (useful for testing and dry-run mode).
    """

    def __init__(self, lakehouse_client: Any | None = None) -> None:
        self._lh = lakehouse_client
        self._mem = _InMemoryStore() if lakehouse_client is None else None

        # In-flight task tracking (agent_id → task_id)
        self._active_tasks: dict[str, str] = {}

        # Accumulated mapping rules (shared cross-agent)
        self._mapping_rules: dict[str, dict[str, str]] = {}

    # ------------------------------------------------------------------
    # Agent lifecycle hooks
    # ------------------------------------------------------------------

    def on_agent_assigned(self, agent_id: str, scope: MigrationScope) -> str:
        """Record that an agent has been assigned a migration task.

        Returns the generated task ID.
        """
        task_id = f"{agent_id}__{uuid.uuid4().hex[:8]}"
        task = AgentTask(
            id=task_id,
            agent_id=agent_id,
            task_type="migration",
            status=TaskStatus.ASSIGNED,
        )
        self._write_task(task)
        self._active_tasks[agent_id] = task_id
        logger.debug("Agent %s assigned → task %s", agent_id, task_id)
        return task_id

    def on_agent_start(self, agent_id: str) -> None:
        """Mark the agent's task as in-progress."""
        task_id = self._active_tasks.get(agent_id)
        if not task_id:
            logger.warning("on_agent_start called for %s with no active task", agent_id)
            return

        task = AgentTask(
            id=task_id,
            agent_id=agent_id,
            task_type="migration",
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
        )
        self._write_task(task)
        self._log(agent_id, "INFO", f"Agent {agent_id} started")

    def on_agent_complete(
        self,
        agent_id: str,
        report: ValidationReport,
        duration_ms: int = 0,
    ) -> None:
        """Mark the agent's task as completed with its validation report."""
        task_id = self._active_tasks.pop(agent_id, None)
        if not task_id:
            logger.warning("on_agent_complete called for %s with no active task", agent_id)
            task_id = f"{agent_id}__orphan"

        task = AgentTask(
            id=task_id,
            agent_id=agent_id,
            task_type="migration",
            status=TaskStatus.COMPLETED,
            started_at=None,
            completed_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            result={
                "total_checks": report.total_checks,
                "passed": report.passed,
                "failed": report.failed,
            },
        )
        self._write_task(task)
        self._write_validation_result(agent_id, report)
        self._log(agent_id, "INFO", f"Agent {agent_id} completed: {report.passed}/{report.total_checks}")

    def on_agent_failed(
        self,
        agent_id: str,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        """Mark the agent's task as failed."""
        task_id = self._active_tasks.pop(agent_id, None)
        if not task_id:
            task_id = f"{agent_id}__orphan"

        task = AgentTask(
            id=task_id,
            agent_id=agent_id,
            task_type="migration",
            status=TaskStatus.FAILED,
            completed_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            result={"error": error},
        )
        self._write_task(task)
        self._log(agent_id, "ERROR", f"Agent {agent_id} failed: {error}")

    # ------------------------------------------------------------------
    # Mapping rules (cross-agent data sharing)
    # ------------------------------------------------------------------

    def write_mapping_rules(
        self,
        source_type: str,
        rules: dict[str, str],
    ) -> None:
        """Write mapping rules (e.g. Oracle→Fabric type map, table renames).

        Parameters
        ----------
        source_type:
            Category key, e.g. ``"data_types"``, ``"table_names"``,
            ``"expressions"``, ``"column_names"``.
        rules:
            Dict of source → target mappings.
        """
        self._mapping_rules[source_type] = {
            **self._mapping_rules.get(source_type, {}),
            **rules,
        }

        row = {
            "id": f"map__{source_type}__{uuid.uuid4().hex[:8]}",
            "source_type": source_type,
            "rules_json": json.dumps(rules),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._lh is not None:
            try:
                self._lh.write_mapping_rule(row)
            except AttributeError:
                # LakehouseClient may not have mapping_rules yet
                logger.debug("LakehouseClient.write_mapping_rule not available — using in-memory")
                if self._mem is None:
                    self._mem = _InMemoryStore()
                self._mem.mapping_rules.append(row)
        elif self._mem is not None:
            self._mem.mapping_rules.append(row)

        logger.debug("Wrote %d mapping rules for source_type=%s", len(rules), source_type)

    def read_mapping_rules(self, source_type: str | None = None) -> dict[str, str]:
        """Read accumulated mapping rules, optionally filtered by source type."""
        if source_type:
            return dict(self._mapping_rules.get(source_type, {}))
        # All rules merged
        merged: dict[str, str] = {}
        for rules in self._mapping_rules.values():
            merged.update(rules)
        return merged

    # ------------------------------------------------------------------
    # Task queries
    # ------------------------------------------------------------------

    def get_agent_status(self, agent_id: str) -> str:
        """Return the latest status for an agent (from memory or Lakehouse)."""
        if agent_id in self._active_tasks:
            return "in_progress"

        if self._lh is not None:
            try:
                tasks = self._lh.read_tasks(agent_id=agent_id)
                if tasks:
                    return tasks[-1].get("status", "unknown")
            except Exception:
                pass

        return "unknown"

    def get_all_task_statuses(self) -> dict[str, str]:
        """Return latest status for all agents."""
        statuses: dict[str, str] = {}
        if self._lh is not None:
            try:
                tasks = self._lh.read_tasks()
                for t in tasks:
                    aid = t.get("agent_id", "")
                    statuses[aid] = t.get("status", "unknown")
            except Exception:
                pass

        if self._mem is not None:
            for t in self._mem.tasks:
                aid = t.get("agent_id", "")
                statuses[aid] = t.get("status", "unknown")

        return statuses

    # ------------------------------------------------------------------
    # Checkpoint / resume support
    # ------------------------------------------------------------------

    def get_completed_agents(self) -> list[str]:
        """Return list of agent IDs that completed successfully."""
        completed: list[str] = []

        if self._lh is not None:
            try:
                tasks = self._lh.read_tasks(status=TaskStatus.COMPLETED)
                completed = list({t["agent_id"] for t in tasks})
            except Exception:
                pass

        if self._mem is not None:
            for t in self._mem.tasks:
                if t.get("status") == TaskStatus.COMPLETED.value:
                    aid = t.get("agent_id", "")
                    if aid not in completed:
                        completed.append(aid)

        return sorted(completed)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_task(self, task: AgentTask) -> None:
        if self._lh is not None:
            try:
                self._lh.write_task(task)
                return
            except Exception:
                logger.debug("LakehouseClient.write_task failed — falling back to memory")

        if self._mem is None:
            self._mem = _InMemoryStore()

        # Upsert in memory
        existing = [i for i, t in enumerate(self._mem.tasks) if t.get("id") == task.id]
        row = task.model_dump(mode="json")
        if existing:
            self._mem.tasks[existing[0]] = row
        else:
            self._mem.tasks.append(row)

    def _write_validation_result(self, agent_id: str, report: ValidationReport) -> None:
        row = {
            "id": f"val__{agent_id}__{uuid.uuid4().hex[:8]}",
            "migration_id": agent_id,
            "agent_id": agent_id,
            "total_checks": report.total_checks,
            "passed": report.passed,
            "failed": report.failed,
            "details_json": json.dumps(report.details) if hasattr(report, "details") else "{}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._lh is not None:
            try:
                self._lh.write_validation_result(row)
                return
            except AttributeError:
                logger.debug("LakehouseClient.write_validation_result not available — using in-memory")

        if self._mem is None:
            self._mem = _InMemoryStore()
        self._mem.validation_results.append(row)

    def _log(self, agent_id: str, level: str, message: str) -> None:
        if self._lh is not None:
            try:
                self._lh.write_log(agent_id, level, message)
                return
            except Exception:
                pass

        if self._mem is None:
            self._mem = _InMemoryStore()
        self._mem.logs.append({
            "agent_id": agent_id,
            "level": level,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
