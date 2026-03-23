"""Coordination DDL generator — DDL for migration coordination tables.

Generates CREATE TABLE statements for the five coordination Delta tables
used by the multi-agent orchestrator:

- ``agent_tasks``       — Task queue per agent
- ``migration_inventory`` — Full inventory of discovered OAC assets
- ``mapping_rules``      — Translation rules (OAC → Fabric/PBI)
- ``validation_results`` — Test results, reconciliation outcomes
- ``agent_logs``         — Structured logs, diagnostics, timing

These tables are deployed to a Fabric Lakehouse via the SQL endpoint
(``FabricClient.execute_sql``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL templates — Fabric Lakehouse T-SQL (Delta format)
# ---------------------------------------------------------------------------

_DDL_AGENT_TASKS = """\
CREATE TABLE IF NOT EXISTS {schema}.agent_tasks (
    id                  VARCHAR(64)     NOT NULL,
    agent_id            VARCHAR(32)     NOT NULL,
    wave_id             VARCHAR(64),
    task_type           VARCHAR(32)     NOT NULL,
    status              VARCHAR(16)     NOT NULL,
    asset_type          VARCHAR(32),
    asset_source_name   VARCHAR(256),
    asset_target_name   VARCHAR(256),
    started_at          TIMESTAMP,
    completed_at        TIMESTAMP,
    duration_ms         INT,
    retry_count         INT             DEFAULT 0,
    result              VARCHAR(MAX),
    assigned_by         VARCHAR(64),
    last_updated        TIMESTAMP
)
"""

_DDL_MIGRATION_INVENTORY = """\
CREATE TABLE IF NOT EXISTS {schema}.migration_inventory (
    id                  VARCHAR(64)     NOT NULL,
    asset_type          VARCHAR(32)     NOT NULL,
    source_path         VARCHAR(512)    NOT NULL,
    name                VARCHAR(256)    NOT NULL,
    owner               VARCHAR(128),
    last_modified       TIMESTAMP,
    metadata            VARCHAR(MAX),
    dependencies        VARCHAR(MAX),
    complexity_score    FLOAT,
    complexity_category VARCHAR(16),
    migration_status    VARCHAR(32),
    migration_wave      INT,
    incomplete          BIT,
    discovered_at       TIMESTAMP,
    source              VARCHAR(64)
)
"""

_DDL_MAPPING_RULES = """\
CREATE TABLE IF NOT EXISTS {schema}.mapping_rules (
    id                  VARCHAR(64)     NOT NULL,
    source_type         VARCHAR(32)     NOT NULL,
    source_name         VARCHAR(256)    NOT NULL,
    target_type         VARCHAR(32)     NOT NULL,
    target_name         VARCHAR(256)    NOT NULL,
    rule_category       VARCHAR(32),
    rule_details        VARCHAR(MAX),
    confidence          FLOAT,
    created_by          VARCHAR(32),
    created_at          TIMESTAMP
)
"""

_DDL_VALIDATION_RESULTS = """\
CREATE TABLE IF NOT EXISTS {schema}.validation_results (
    id                  VARCHAR(64)     NOT NULL,
    migration_id        VARCHAR(64)     NOT NULL,
    agent_id            VARCHAR(32)     NOT NULL,
    check_type          VARCHAR(32)     NOT NULL,
    check_name          VARCHAR(256)    NOT NULL,
    status              VARCHAR(16)     NOT NULL,
    expected_value      VARCHAR(MAX),
    actual_value        VARCHAR(MAX),
    details             VARCHAR(MAX),
    executed_at         TIMESTAMP
)
"""

_DDL_AGENT_LOGS = """\
CREATE TABLE IF NOT EXISTS {schema}.agent_logs (
    agent_id            VARCHAR(32)     NOT NULL,
    level               VARCHAR(8)      NOT NULL,
    message             VARCHAR(MAX)    NOT NULL,
    extra               VARCHAR(MAX),
    timestamp           TIMESTAMP       NOT NULL
)
"""

# Ordered so that tables referenced by foreign-key-like dependencies come first.
_ALL_DDL: list[tuple[str, str]] = [
    ("migration_inventory", _DDL_MIGRATION_INVENTORY),
    ("agent_tasks", _DDL_AGENT_TASKS),
    ("mapping_rules", _DDL_MAPPING_RULES),
    ("validation_results", _DDL_VALIDATION_RESULTS),
    ("agent_logs", _DDL_AGENT_LOGS),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def coordination_table_names() -> list[str]:
    """Return the names of all coordination tables in deployment order."""
    return [name for name, _ in _ALL_DDL]


def generate_coordination_ddl(schema: str = "dbo") -> list[str]:
    """Generate DDL statements for all coordination tables.

    Parameters
    ----------
    schema
        Target schema within the Lakehouse (default ``dbo``).

    Returns
    -------
    list[str]
        List of CREATE TABLE statements, one per table.
    """
    return [tmpl.format(schema=schema).strip() for _, tmpl in _ALL_DDL]


def generate_drop_ddl(schema: str = "dbo") -> list[str]:
    """Generate DROP TABLE IF EXISTS statements for all coordination tables.

    Useful for test teardown and re-deployment scenarios.
    """
    return [
        f"DROP TABLE IF EXISTS {schema}.{name}"
        for name, _ in reversed(_ALL_DDL)
    ]


@dataclass
class CoordinationDeployment:
    """Result of a coordination table deployment."""

    tables_created: list[str]
    tables_failed: list[tuple[str, str]]  # (name, error)

    @property
    def success(self) -> bool:
        return len(self.tables_failed) == 0

    @property
    def total(self) -> int:
        return len(self.tables_created) + len(self.tables_failed)


async def deploy_coordination_tables(
    fabric_client: Any,
    sql_endpoint: str,
    *,
    schema: str = "dbo",
) -> CoordinationDeployment:
    """Deploy all coordination tables to a Fabric Lakehouse.

    Parameters
    ----------
    fabric_client
        An instance of ``FabricClient`` (or any object with ``execute_sql``).
    sql_endpoint
        Lakehouse SQL endpoint hostname.
    schema
        Target schema.

    Returns
    -------
    CoordinationDeployment
        Deployment result with lists of created / failed tables.
    """
    created: list[str] = []
    failed: list[tuple[str, str]] = []

    ddl_stmts = generate_coordination_ddl(schema=schema)
    names = coordination_table_names()

    for name, stmt in zip(names, ddl_stmts):
        try:
            await fabric_client.execute_sql(sql_endpoint, stmt)
            created.append(name)
            logger.info("Created coordination table: %s.%s", schema, name)
        except Exception as exc:
            failed.append((name, str(exc)))
            logger.error("Failed to create %s.%s: %s", schema, name, exc)

    result = CoordinationDeployment(tables_created=created, tables_failed=failed)
    if result.success:
        logger.info(
            "All %d coordination tables deployed successfully", result.total
        )
    else:
        logger.warning(
            "Coordination deployment: %d created, %d failed",
            len(created), len(failed),
        )
    return result
