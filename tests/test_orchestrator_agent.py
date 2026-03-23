"""Tests for Orchestrator Agent — end-to-end migration coordination."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents.orchestrator.dag_engine import NodeStatus
from src.agents.orchestrator.orchestrator_agent import (
    AgentExecutionResult,
    MigrationSummary,
    OrchestratorAgent,
    OrchestratorConfig,
    WaveExecutionResult,
)
from src.agents.orchestrator.wave_planner import MigrationWave
from src.core.models import (
    AssetType,
    Inventory,
    InventoryItem,
    MigrationScope,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scope() -> MigrationScope:
    return MigrationScope(include_paths=["/tables/Sales", "/tables/Products"])


def _make_runner(fail_agents: set[str] | None = None):
    """Return an agent runner that succeeds unless agent_id is in fail_agents."""
    fail = fail_agents or set()

    async def runner(agent_id: str, scope: MigrationScope) -> ValidationReport:
        if agent_id in fail:
            raise RuntimeError(f"Simulated failure for {agent_id}")
        return ValidationReport(agent_id=agent_id, total_checks=1, passed=1)

    return runner


# ---------------------------------------------------------------------------
# Orchestrator lifecycle
# ---------------------------------------------------------------------------


class TestOrchestratorLifecycle:
    @pytest.mark.asyncio
    async def test_run_migration_succeeds(self, tmp_path: Path):
        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=0,
            retry_backoff_seconds=[0],
        )
        orch = OrchestratorAgent(
            config=config,
            agent_runner=_make_runner(),
        )
        summary = await orch.run_migration(_scope())
        assert summary.overall_status == "succeeded"
        assert summary.total_failed == 0
        assert summary.total_agents_run >= 1

    @pytest.mark.asyncio
    async def test_writes_summary_report(self, tmp_path: Path):
        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=0,
            retry_backoff_seconds=[0],
        )
        orch = OrchestratorAgent(config=config, agent_runner=_make_runner())
        await orch.run_migration(_scope())
        assert (tmp_path / "out" / "migration_summary.md").exists()

    @pytest.mark.asyncio
    async def test_writes_wave_plan(self, tmp_path: Path):
        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=0,
            retry_backoff_seconds=[0],
        )
        orch = OrchestratorAgent(config=config, agent_runner=_make_runner())
        await orch.run_migration(_scope())
        assert (tmp_path / "out" / "wave_plan.md").exists()

    @pytest.mark.asyncio
    async def test_writes_notification_log(self, tmp_path: Path):
        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=0,
            retry_backoff_seconds=[0],
        )
        orch = OrchestratorAgent(config=config, agent_runner=_make_runner())
        await orch.run_migration(_scope())
        assert (tmp_path / "out" / "notification_log.md").exists()

    @pytest.mark.asyncio
    async def test_discovery_failure_halts(self, tmp_path: Path):
        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=0,
            retry_backoff_seconds=[0],
        )
        orch = OrchestratorAgent(
            config=config,
            agent_runner=_make_runner(fail_agents={"01-discovery"}),
        )
        summary = await orch.run_migration(_scope())
        assert summary.overall_status == "failed"

    @pytest.mark.asyncio
    async def test_summary_report_content(self, tmp_path: Path):
        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=0,
            retry_backoff_seconds=[0],
        )
        orch = OrchestratorAgent(config=config, agent_runner=_make_runner())
        await orch.run_migration(_scope())
        md = (tmp_path / "out" / "migration_summary.md").read_text(encoding="utf-8")
        assert "Migration Summary" in md
        assert "Agent Detail" in md
        assert "DAG Status" in md


# ---------------------------------------------------------------------------
# Wave execution
# ---------------------------------------------------------------------------


class TestWaveExecution:
    @pytest.mark.asyncio
    async def test_execute_wave(self, tmp_path: Path):
        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=0,
            retry_backoff_seconds=[0],
            validate_after_each_wave=False,
        )
        orch = OrchestratorAgent(config=config, agent_runner=_make_runner())
        # Set up DAG so the sub-DAG builder works
        from src.agents.orchestrator.dag_engine import build_default_migration_dag
        orch._dag = build_default_migration_dag()

        wave = MigrationWave(
            id=1, name="Wave 1",
            agent_ids=["01-discovery"],
        )
        result = await orch.execute_wave(wave, _scope())
        assert result.succeeded == 1
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_wave_with_failure(self, tmp_path: Path):
        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=0,
            retry_backoff_seconds=[0],
            validate_after_each_wave=False,
        )
        orch = OrchestratorAgent(
            config=config,
            agent_runner=_make_runner(fail_agents={"02-schema"}),
        )
        from src.agents.orchestrator.dag_engine import build_default_migration_dag
        orch._dag = build_default_migration_dag()

        wave = MigrationWave(
            id=1, name="Wave 1",
            agent_ids=["02-schema"],
        )
        result = await orch.execute_wave(wave, _scope())
        assert result.failed == 1


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_failure(self, tmp_path: Path):
        call_count = 0

        async def flaky_runner(
            agent_id: str, scope: MigrationScope
        ) -> ValidationReport:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("transient")
            return ValidationReport(
                agent_id=agent_id, total_checks=1, passed=1
            )

        config = OrchestratorConfig(
            output_dir=str(tmp_path / "out"),
            max_retries=3,
            retry_backoff_seconds=[0, 0, 0],
        )
        orch = OrchestratorAgent(config=config, agent_runner=flaky_runner)
        from src.agents.orchestrator.dag_engine import build_default_migration_dag
        orch._dag = build_default_migration_dag()

        result = await orch._execute_agent_with_retry("01-discovery", _scope())
        assert result.status == NodeStatus.SUCCEEDED
        assert result.retry_count == 2  # succeeded on 3rd attempt
        assert call_count == 3


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class TestDataClasses:
    def test_wave_execution_result(self):
        wr = WaveExecutionResult(wave_id=1, wave_name="W1")
        wr.agent_results.append(
            AgentExecutionResult(
                agent_id="01", status=NodeStatus.SUCCEEDED
            )
        )
        wr.agent_results.append(
            AgentExecutionResult(
                agent_id="02", status=NodeStatus.FAILED, error="err"
            )
        )
        assert wr.succeeded == 1
        assert wr.failed == 1

    def test_migration_summary(self):
        s = MigrationSummary()
        assert s.all_passed is False  # no agents run
        s.total_agents_run = 3
        s.total_succeeded = 3
        s.total_failed = 0
        assert s.all_passed is True

    def test_summary_report_generation(self, tmp_path: Path):
        config = OrchestratorConfig(output_dir=str(tmp_path / "out"))
        orch = OrchestratorAgent(config=config, agent_runner=_make_runner())
        report = orch.generate_summary_report()
        assert "Migration Summary" in report
