"""Runner factory — builds ``AgentRunner`` callables from the registry.

The factory knows how to instantiate each agent with the correct
dependencies (clients, config, output dirs) and returns an async
callable matching the ``AgentRunner`` protocol expected by the
``OrchestratorAgent``.

Usage::

    registry = build_default_registry()
    factory  = RunnerFactory(registry, config=settings, lakehouse_client=lh)
    runner   = factory.create_runner()
    orch     = OrchestratorAgent(config=orch_cfg, agent_runner=runner)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.agent_registry import AgentRegistry
from src.core.models import MigrationScope, ValidationReport
from src.core.state_coordinator import StateCoordinator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dependency container
# ---------------------------------------------------------------------------


@dataclass
class AgentDependencies:
    """Holds shared dependencies injected into agents.

    All fields are optional — agents that do not need a particular
    dependency will simply ignore it.
    """

    oac_client: Any | None = None
    lakehouse_client: Any | None = None
    llm_client: Any | None = None
    fabric_client: Any | None = None
    pbi_client: Any | None = None

    # RPD / Oracle config
    rpd_xml_path: str = ""
    oracle_schema: str = "OACS"
    oracle_connection_name: str = "OracleDB_Prod"
    lakehouse_name: str = "oac_migration"
    workspace_id: str = ""

    # Table mapping produced by Agent 02, consumed by 05 & 06
    table_mapping: dict[str, str] = field(default_factory=dict)

    # Semantic model info produced by Agent 04, consumed by 05
    semantic_model_id: str = ""
    semantic_model_name: str = "SemanticModel"

    # Base output directory — each agent appends its own sub-dir
    output_base: str = "output"


# ---------------------------------------------------------------------------
# Per-agent constructor argument mapping
# ---------------------------------------------------------------------------

# Maps agent IDs to a function that extracts the right kwargs
# for each agent's ``__init__`` from the dependencies container.

def _discovery_kwargs(deps: AgentDependencies) -> dict[str, Any]:
    kw: dict[str, Any] = {}
    if deps.oac_client is not None:
        kw["oac_client"] = deps.oac_client
    if deps.rpd_xml_path:
        kw["rpd_xml_path"] = deps.rpd_xml_path
    if deps.lakehouse_client is not None:
        kw["lakehouse_client"] = deps.lakehouse_client
    return kw


def _schema_kwargs(deps: AgentDependencies) -> dict[str, Any]:
    return {
        "lakehouse_client": deps.lakehouse_client,
        "oracle_schema": deps.oracle_schema,
        "oracle_connection_name": deps.oracle_connection_name,
        "lakehouse_name": deps.lakehouse_name,
        "output_dir": str(Path(deps.output_base) / "schema"),
    }


def _etl_kwargs(deps: AgentDependencies) -> dict[str, Any]:
    return {
        "lakehouse_client": deps.lakehouse_client,
        "llm_client": deps.llm_client,
        "oracle_schema": deps.oracle_schema,
        "output_dir": str(Path(deps.output_base) / "etl"),
    }


def _semantic_kwargs(deps: AgentDependencies) -> dict[str, Any]:
    return {
        "lakehouse_client": deps.lakehouse_client,
        "llm_client": deps.llm_client,
        "lakehouse_name": deps.lakehouse_name,
        "output_dir": str(Path(deps.output_base) / "semantic_model"),
    }


def _report_kwargs(deps: AgentDependencies) -> dict[str, Any]:
    return {
        "lakehouse_client": deps.lakehouse_client,
        "semantic_model_id": deps.semantic_model_id,
        "semantic_model_name": deps.semantic_model_name,
        "table_mapping": deps.table_mapping,
        "output_dir": str(Path(deps.output_base) / "reports"),
    }


def _security_kwargs(deps: AgentDependencies) -> dict[str, Any]:
    return {
        "lakehouse_client": deps.lakehouse_client,
        "table_mapping": deps.table_mapping,
        "workspace_id": deps.workspace_id,
        "output_dir": str(Path(deps.output_base) / "security"),
    }


def _validation_kwargs(deps: AgentDependencies) -> dict[str, Any]:
    return {
        "lakehouse_client": deps.lakehouse_client,
        "output_dir": str(Path(deps.output_base) / "validation"),
    }


_KWARGS_MAP: dict[str, Any] = {
    "01-discovery": _discovery_kwargs,
    "02-schema": _schema_kwargs,
    "03-etl": _etl_kwargs,
    "04-semantic": _semantic_kwargs,
    "05-report": _report_kwargs,
    "06-security": _security_kwargs,
    "07-validation": _validation_kwargs,
}


# ---------------------------------------------------------------------------
# Runner factory
# ---------------------------------------------------------------------------


class RunnerFactory:
    """Builds an ``AgentRunner`` that instantiates agents from the registry.

    Parameters
    ----------
    registry:
        Agent registry mapping IDs to classes.
    deps:
        Shared dependency container.  If *None*, a default
        ``AgentDependencies()`` is used (all stubs/None).
    """

    def __init__(
        self,
        registry: AgentRegistry,
        deps: AgentDependencies | None = None,
        state_coordinator: StateCoordinator | None = None,
    ) -> None:
        self._registry = registry
        self._deps = deps or AgentDependencies()
        self._state = state_coordinator

    # ---- public API ----

    def create_runner(self):
        """Return an async callable matching ``AgentRunner``.

        The callable:
        1. Looks up the agent class in the registry.
        2. Instantiates it with the correct dependencies.
        3. Calls ``agent.run(scope)`` and returns the validation report.
        """

        async def _runner(
            agent_id: str, scope: MigrationScope
        ) -> ValidationReport:
            return await self._run_agent(agent_id, scope)

        return _runner

    # ---- internal ----

    async def _run_agent(
        self, agent_id: str, scope: MigrationScope
    ) -> ValidationReport:
        """Instantiate and run a single agent, with state tracking."""
        # 0. State: assigned
        if self._state:
            self._state.on_agent_assigned(agent_id, scope)

        # 1. Resolve class
        agent_cls = self._registry.get(agent_id)  # raises KeyError

        # 2. Build constructor kwargs
        kwargs_fn = _KWARGS_MAP.get(agent_id)
        kwargs = kwargs_fn(self._deps) if kwargs_fn else {}

        # 3. Instantiate
        logger.info(
            "Instantiating %s (agent_id=%s) with kwargs: %s",
            agent_cls.__name__,
            agent_id,
            list(kwargs.keys()),
        )
        agent = agent_cls(**kwargs)

        # 4. State: in-progress
        if self._state:
            self._state.on_agent_start(agent_id)

        # 5. Run full lifecycle
        t0 = time.monotonic()
        try:
            report = await agent.run(scope)
            elapsed = time.monotonic() - t0
            logger.info(
                "Agent %s completed in %.1fs — %d/%d checks passed",
                agent_id,
                elapsed,
                report.passed,
                report.total_checks,
            )

            # 6. State: complete
            if self._state:
                self._state.on_agent_complete(
                    agent_id, report, duration_ms=int(elapsed * 1000)
                )

            return report
        except Exception:
            elapsed = time.monotonic() - t0
            logger.exception(
                "Agent %s failed after %.1fs", agent_id, elapsed
            )

            # State: failed
            if self._state:
                import traceback
                self._state.on_agent_failed(
                    agent_id,
                    traceback.format_exc(),
                    duration_ms=int(elapsed * 1000),
                )

            raise

    def update_table_mapping(self, mapping: dict[str, str]) -> None:
        """Update table mapping (produced by Agent 02, consumed by 05/06)."""
        self._deps.table_mapping.update(mapping)

    def update_semantic_model(self, model_id: str, model_name: str) -> None:
        """Update semantic model info (produced by Agent 04, consumed by 05)."""
        self._deps.semantic_model_id = model_id
        self._deps.semantic_model_name = model_name
