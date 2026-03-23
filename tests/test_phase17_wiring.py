"""Phase 17 tests — Agent wiring, registry, runner factory, state coordination, CLI.

Tests cover:
- AgentRegistry: register, get, list, has, build_default_registry
- RunnerFactory: create_runner, instantiation, state hooks
- StateCoordinator: lifecycle, mapping rules, checkpoint/resume
- CLI integration: dry-run with real runner, --agents, --resume flags
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.agent_registry import AgentRegistry, build_default_registry
from src.core.base_agent import MigrationAgent
from src.core.models import (
    Inventory,
    MigrationPlan,
    MigrationResult,
    MigrationScope,
    RollbackResult,
    TaskStatus,
    ValidationReport,
)
from src.core.runner_factory import AgentDependencies, RunnerFactory, _KWARGS_MAP
from src.core.state_coordinator import StateCoordinator


# ---------------------------------------------------------------------------
# Helpers: a minimal concrete agent for testing
# ---------------------------------------------------------------------------


class _StubAgent(MigrationAgent):
    """Minimal agent that succeeds instantly."""

    def __init__(self, **kwargs):
        super().__init__(agent_id="stub-agent", agent_name="Stub Agent")
        self.init_kwargs = kwargs
        self.run_called = False

    async def discover(self, scope):
        return Inventory(items=[])

    async def plan(self, inventory):
        return MigrationPlan(agent_id="stub-agent", items=[])

    async def execute(self, plan):
        return MigrationResult(agent_id="stub-agent", succeeded=1, failed=0, skipped=0)

    async def validate(self, result):
        self.run_called = True
        return ValidationReport(agent_id="stub-agent", total_checks=1, passed=1)


class _FailingAgent(MigrationAgent):
    """Agent that always raises."""

    def __init__(self, **kwargs):
        super().__init__(agent_id="fail-agent", agent_name="Failing Agent")

    async def discover(self, scope):
        raise RuntimeError("Discovery boom")

    async def plan(self, inventory):
        return MigrationPlan(agent_id="fail-agent", items=[])

    async def execute(self, plan):
        return MigrationResult(agent_id="fail-agent", succeeded=0, failed=1, skipped=0)

    async def validate(self, result):
        return ValidationReport(agent_id="fail-agent", total_checks=1, passed=0, failed=1)


# ===================================================================
# AgentRegistry tests
# ===================================================================


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def test_register_and_get(self):
        reg = AgentRegistry()
        reg.register("test-agent", _StubAgent)
        assert reg.get("test-agent") is _StubAgent

    def test_get_missing_raises_key_error(self):
        reg = AgentRegistry()
        with pytest.raises(KeyError, match="not-registered"):
            reg.get("not-registered")

    def test_list_returns_sorted(self):
        reg = AgentRegistry()
        reg.register("02-second", _StubAgent)
        reg.register("01-first", _StubAgent)
        assert reg.list() == ["01-first", "02-second"]

    def test_has_and_contains(self):
        reg = AgentRegistry()
        reg.register("x", _StubAgent)
        assert reg.has("x")
        assert "x" in reg
        assert not reg.has("y")
        assert "y" not in reg

    def test_len(self):
        reg = AgentRegistry()
        assert len(reg) == 0
        reg.register("a", _StubAgent)
        assert len(reg) == 1

    def test_overwrite_warns(self):
        reg = AgentRegistry()
        reg.register("a", _StubAgent)
        reg.register("a", _FailingAgent)  # should overwrite
        assert reg.get("a") is _FailingAgent

    def test_build_default_registry_has_seven_agents(self):
        reg = build_default_registry()
        assert len(reg) == 7
        expected = [
            "01-discovery", "02-schema", "03-etl",
            "04-semantic", "05-report", "06-security", "07-validation",
        ]
        assert reg.list() == expected

    def test_default_registry_classes_are_migration_agents(self):
        reg = build_default_registry()
        for agent_id in reg.list():
            cls = reg.get(agent_id)
            assert issubclass(cls, MigrationAgent), f"{agent_id} → {cls} is not a MigrationAgent"


# ===================================================================
# RunnerFactory tests
# ===================================================================


class TestRunnerFactory:
    """Tests for RunnerFactory."""

    def test_create_runner_returns_callable(self):
        reg = AgentRegistry()
        reg.register("stub", _StubAgent)
        factory = RunnerFactory(registry=reg)
        runner = factory.create_runner()
        assert callable(runner)

    @pytest.mark.asyncio
    async def test_runner_instantiates_and_runs_agent(self):
        reg = AgentRegistry()
        reg.register("stub", _StubAgent)
        factory = RunnerFactory(registry=reg)
        runner = factory.create_runner()

        scope = MigrationScope()
        report = await runner("stub", scope)

        assert report.agent_id == "stub-agent"
        assert report.passed == 1
        assert report.total_checks == 1

    @pytest.mark.asyncio
    async def test_runner_raises_for_unknown_agent(self):
        reg = AgentRegistry()
        factory = RunnerFactory(registry=reg)
        runner = factory.create_runner()

        with pytest.raises(KeyError, match="no-such"):
            await runner("no-such", MigrationScope())

    @pytest.mark.asyncio
    async def test_runner_propagates_agent_error(self):
        reg = AgentRegistry()
        reg.register("fail", _FailingAgent)
        factory = RunnerFactory(registry=reg)
        runner = factory.create_runner()

        with pytest.raises(RuntimeError, match="Discovery boom"):
            await runner("fail", MigrationScope())

    @pytest.mark.asyncio
    async def test_runner_with_state_coordinator(self):
        """State coordinator hooks are called on success."""
        reg = AgentRegistry()
        reg.register("stub", _StubAgent)
        coord = StateCoordinator()
        factory = RunnerFactory(registry=reg, state_coordinator=coord)
        runner = factory.create_runner()

        await runner("stub", MigrationScope())

        # Check that state was tracked
        statuses = coord.get_all_task_statuses()
        assert "stub" in statuses
        assert statuses["stub"] == "completed"

    @pytest.mark.asyncio
    async def test_runner_state_on_failure(self):
        """State coordinator records failure on exception."""
        reg = AgentRegistry()
        reg.register("fail", _FailingAgent)
        coord = StateCoordinator()
        factory = RunnerFactory(registry=reg, state_coordinator=coord)
        runner = factory.create_runner()

        with pytest.raises(RuntimeError):
            await runner("fail", MigrationScope())

        statuses = coord.get_all_task_statuses()
        assert "fail" in statuses
        assert statuses["fail"] == "failed"

    def test_update_table_mapping(self):
        reg = AgentRegistry()
        deps = AgentDependencies()
        factory = RunnerFactory(registry=reg, deps=deps)
        factory.update_table_mapping({"ORA_TABLE": "fabric_table"})
        assert deps.table_mapping == {"ORA_TABLE": "fabric_table"}

    def test_update_semantic_model(self):
        reg = AgentRegistry()
        deps = AgentDependencies()
        factory = RunnerFactory(registry=reg, deps=deps)
        factory.update_semantic_model("sm-123", "SalesModel")
        assert deps.semantic_model_id == "sm-123"
        assert deps.semantic_model_name == "SalesModel"


# ===================================================================
# AgentDependencies & kwargs mapping tests
# ===================================================================


class TestAgentDependencies:
    """Tests for dependency container and per-agent kwargs mapping."""

    def test_default_dependencies(self):
        deps = AgentDependencies()
        assert deps.oac_client is None
        assert deps.lakehouse_client is None
        assert deps.llm_client is None
        assert deps.oracle_schema == "OACS"
        assert deps.output_base == "output"

    def test_kwargs_map_has_all_seven_agents(self):
        expected = {
            "01-discovery", "02-schema", "03-etl",
            "04-semantic", "05-report", "06-security", "07-validation",
        }
        assert set(_KWARGS_MAP.keys()) == expected

    def test_discovery_kwargs_with_oac_client(self):
        mock_client = MagicMock()
        deps = AgentDependencies(oac_client=mock_client, rpd_xml_path="/tmp/rpd.xml")
        kw = _KWARGS_MAP["01-discovery"](deps)
        assert kw["oac_client"] is mock_client
        assert kw["rpd_xml_path"] == "/tmp/rpd.xml"

    def test_discovery_kwargs_without_oac_client(self):
        deps = AgentDependencies()
        kw = _KWARGS_MAP["01-discovery"](deps)
        assert "oac_client" not in kw  # None is omitted

    def test_schema_kwargs(self):
        deps = AgentDependencies(oracle_schema="HR", output_base="/out")
        kw = _KWARGS_MAP["02-schema"](deps)
        assert kw["oracle_schema"] == "HR"
        assert "schema" in kw["output_dir"]

    def test_etl_kwargs_includes_llm(self):
        mock_llm = MagicMock()
        deps = AgentDependencies(llm_client=mock_llm)
        kw = _KWARGS_MAP["03-etl"](deps)
        assert kw["llm_client"] is mock_llm

    def test_report_kwargs_includes_semantic_model(self):
        deps = AgentDependencies(semantic_model_id="sm-42", semantic_model_name="Sales")
        kw = _KWARGS_MAP["05-report"](deps)
        assert kw["semantic_model_id"] == "sm-42"
        assert kw["semantic_model_name"] == "Sales"

    def test_security_kwargs_includes_workspace(self):
        deps = AgentDependencies(workspace_id="ws-99")
        kw = _KWARGS_MAP["06-security"](deps)
        assert kw["workspace_id"] == "ws-99"


# ===================================================================
# StateCoordinator tests
# ===================================================================


class TestStateCoordinator:
    """Tests for StateCoordinator lifecycle and data sharing."""

    def test_lifecycle_assigned_start_complete(self):
        coord = StateCoordinator()
        scope = MigrationScope()

        task_id = coord.on_agent_assigned("01-discovery", scope)
        assert task_id.startswith("01-discovery__")

        coord.on_agent_start("01-discovery")

        report = ValidationReport(agent_id="01-discovery", total_checks=5, passed=5)
        coord.on_agent_complete("01-discovery", report, duration_ms=1500)

        # Agent should show as done
        completed = coord.get_completed_agents()
        assert "01-discovery" in completed

    def test_lifecycle_failed(self):
        coord = StateCoordinator()
        scope = MigrationScope()

        coord.on_agent_assigned("02-schema", scope)
        coord.on_agent_start("02-schema")
        coord.on_agent_failed("02-schema", "Connection timeout", duration_ms=500)

        statuses = coord.get_all_task_statuses()
        assert statuses["02-schema"] == "failed"
        assert "02-schema" not in coord.get_completed_agents()

    def test_mapping_rules_write_and_read(self):
        coord = StateCoordinator()
        coord.write_mapping_rules("data_types", {"NUMBER": "DECIMAL", "VARCHAR2": "STRING"})
        coord.write_mapping_rules("table_names", {"ORA_SALES": "fact_sales"})

        dt_rules = coord.read_mapping_rules("data_types")
        assert dt_rules == {"NUMBER": "DECIMAL", "VARCHAR2": "STRING"}

        tn_rules = coord.read_mapping_rules("table_names")
        assert tn_rules == {"ORA_SALES": "fact_sales"}

        all_rules = coord.read_mapping_rules()
        assert "NUMBER" in all_rules
        assert "ORA_SALES" in all_rules

    def test_mapping_rules_merge(self):
        coord = StateCoordinator()
        coord.write_mapping_rules("data_types", {"NUMBER": "DECIMAL"})
        coord.write_mapping_rules("data_types", {"DATE": "TIMESTAMP"})
        rules = coord.read_mapping_rules("data_types")
        assert rules == {"NUMBER": "DECIMAL", "DATE": "TIMESTAMP"}

    def test_get_agent_status_unknown_agent(self):
        coord = StateCoordinator()
        assert coord.get_agent_status("nonexistent") == "unknown"

    def test_get_agent_status_active(self):
        coord = StateCoordinator()
        coord.on_agent_assigned("03-etl", MigrationScope())
        assert coord.get_agent_status("03-etl") == "in_progress"

    def test_checkpoint_resume_flow(self):
        """Simulate a checkpoint/resume scenario."""
        coord = StateCoordinator()
        scope = MigrationScope()

        # First run: Discovery + Schema complete, ETL fails
        for aid in ["01-discovery", "02-schema"]:
            coord.on_agent_assigned(aid, scope)
            coord.on_agent_start(aid)
            coord.on_agent_complete(
                aid, ValidationReport(agent_id=aid, total_checks=1, passed=1)
            )

        coord.on_agent_assigned("03-etl", scope)
        coord.on_agent_start("03-etl")
        coord.on_agent_failed("03-etl", "ORA-12154")

        # Resume: should know which agents completed
        completed = coord.get_completed_agents()
        assert completed == ["01-discovery", "02-schema"]
        assert "03-etl" not in completed

    def test_validation_results_stored(self):
        coord = StateCoordinator()
        coord.on_agent_assigned("07-validation", MigrationScope())
        coord.on_agent_start("07-validation")
        coord.on_agent_complete(
            "07-validation",
            ValidationReport(agent_id="07-validation", total_checks=10, passed=9, failed=1),
        )
        # Validation result should be in memory store
        assert coord._mem is not None
        assert len(coord._mem.validation_results) == 1
        vr = coord._mem.validation_results[0]
        assert vr["total_checks"] == 10
        assert vr["passed"] == 9
        assert vr["failed"] == 1

    def test_on_agent_start_without_assign_warns(self):
        """Calling on_agent_start without assign should not crash."""
        coord = StateCoordinator()
        coord.on_agent_start("ghost-agent")  # should just warn, not raise


# ===================================================================
# CLI integration tests
# ===================================================================


class TestCLIIntegration:
    """Tests for CLI wiring with real registry/runner."""

    def test_build_parser_has_agents_flag(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["migrate", "--agents", "01-discovery,02-schema", "--dry-run"])
        assert args.agents == "01-discovery,02-schema"
        assert args.dry_run is True

    def test_build_parser_has_resume_flag(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["migrate", "--resume", "--dry-run"])
        assert args.resume is True

    @pytest.mark.asyncio
    async def test_cmd_migrate_dry_run_with_real_runner(self, capsys):
        """Dry-run should print scope including agent list and exit 0."""
        from src.cli.main import cmd_migrate
        from src.cli.config_loader import MigrationConfig

        cfg = MigrationConfig()
        args = MagicMock()
        args.wave = None
        args.dry_run = True
        args.output_dir = None
        args.agents = None
        args.resume = False

        result = await cmd_migrate(cfg, args)
        assert result == 0

        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out
        assert "Agents:" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_migrate_dry_run_with_agents_filter(self, capsys):
        """Dry-run with --agents should show filtered list."""
        from src.cli.main import cmd_migrate
        from src.cli.config_loader import MigrationConfig

        cfg = MigrationConfig()
        args = MagicMock()
        args.wave = None
        args.dry_run = True
        args.output_dir = None
        args.agents = "01-discovery,02-schema"
        args.resume = False

        result = await cmd_migrate(cfg, args)
        assert result == 0

        captured = capsys.readouterr()
        assert "01-discovery" in captured.out


# ===================================================================
# Orchestrator + real runner integration test
# ===================================================================


class TestOrchestratorWithRunner:
    """Test OrchestratorAgent with a RunnerFactory-produced runner."""

    @pytest.mark.asyncio
    async def test_orchestrator_uses_injected_runner(self):
        """Orchestrator should call the real runner, not the default no-op."""
        from src.agents.orchestrator.orchestrator_agent import (
            OrchestratorAgent,
            OrchestratorConfig,
        )

        # Build a registry with a single stub agent
        reg = AgentRegistry()
        reg.register("01-discovery", _StubAgent)
        reg.register("07-validation", _StubAgent)

        factory = RunnerFactory(registry=reg)
        runner = factory.create_runner()

        orch = OrchestratorAgent(
            config=OrchestratorConfig(
                validate_after_each_wave=False,
                auto_advance_waves=True,
            ),
            agent_runner=runner,
        )

        # Call _execute_agent directly
        result = await orch._execute_agent("01-discovery", MigrationScope())
        assert result.agent_id == "01-discovery"
        # The stub returns 1/1 passed → SUCCEEDED
        from src.agents.orchestrator.dag_engine import NodeStatus
        assert result.status == NodeStatus.SUCCEEDED
