"""Agent registry — maps agent IDs to concrete MigrationAgent classes.

Provides a central lookup from string agent IDs (e.g. ``"01-discovery"``)
to their implementing classes.  The registry is used by the
``RunnerFactory`` to instantiate agents with the correct dependencies.
"""

from __future__ import annotations

import logging
from typing import Any, Type

from src.core.base_agent import MigrationAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry mapping agent IDs to their implementing classes.

    Usage::

        registry = AgentRegistry()
        registry.register("01-discovery", DiscoveryAgent)
        cls = registry.get("01-discovery")
    """

    def __init__(self) -> None:
        self._agents: dict[str, Type[MigrationAgent]] = {}

    def register(self, agent_id: str, cls: Type[MigrationAgent]) -> None:
        """Register an agent class under the given ID."""
        if agent_id in self._agents:
            logger.warning("Overwriting agent registration for '%s'", agent_id)
        self._agents[agent_id] = cls
        logger.debug("Registered agent '%s' → %s", agent_id, cls.__name__)

    def get(self, agent_id: str) -> Type[MigrationAgent]:
        """Look up an agent class by ID.  Raises KeyError if not found."""
        if agent_id not in self._agents:
            raise KeyError(
                f"Agent '{agent_id}' not registered.  "
                f"Available: {', '.join(sorted(self._agents))}"
            )
        return self._agents[agent_id]

    def list(self) -> list[str]:
        """Return sorted list of registered agent IDs."""
        return sorted(self._agents.keys())

    def has(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def __len__(self) -> int:
        return len(self._agents)


# ---------------------------------------------------------------------------
# Default registry with all 8 agents
# ---------------------------------------------------------------------------


def build_default_registry() -> AgentRegistry:
    """Build the standard registry with all 8 migration agents.

    Imports are deferred to avoid circular dependencies and allow
    the registry to be constructed even when optional dependencies
    are missing.
    """
    registry = AgentRegistry()

    try:
        from src.agents.discovery.discovery_agent import DiscoveryAgent
        registry.register("01-discovery", DiscoveryAgent)
    except ImportError:
        logger.warning("DiscoveryAgent not available — skipping registration")

    try:
        from src.agents.schema.schema_agent import SchemaAgent
        registry.register("02-schema", SchemaAgent)
    except ImportError:
        logger.warning("SchemaAgent not available — skipping registration")

    try:
        from src.agents.etl.etl_agent import ETLAgent
        registry.register("03-etl", ETLAgent)
    except ImportError:
        logger.warning("ETLAgent not available — skipping registration")

    try:
        from src.agents.semantic.semantic_agent import SemanticModelAgent
        registry.register("04-semantic", SemanticModelAgent)
    except ImportError:
        logger.warning("SemanticModelAgent not available — skipping registration")

    try:
        from src.agents.report.report_agent import ReportMigrationAgent
        registry.register("05-report", ReportMigrationAgent)
    except ImportError:
        logger.warning("ReportMigrationAgent not available — skipping registration")

    try:
        from src.agents.security.security_agent import SecurityMigrationAgent
        registry.register("06-security", SecurityMigrationAgent)
    except ImportError:
        logger.warning("SecurityMigrationAgent not available — skipping registration")

    try:
        from src.agents.validation.validation_agent import ValidationAgent
        registry.register("07-validation", ValidationAgent)
    except ImportError:
        logger.warning("ValidationAgent not available — skipping registration")

    logger.info("Agent registry built with %d agents: %s", len(registry), registry.list())
    return registry
