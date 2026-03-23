"""Fabric Deployer — deploy artefacts to Microsoft Fabric.

Handles:
- Lakehouse table creation (DDL via SQL endpoint)
- Data pipeline deployment
- Notebook deployment
- Delta table data loading
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.clients.fabric_client import FabricClient

logger = logging.getLogger(__name__)


@dataclass
class DeploymentResult:
    """Result of a single deployment operation."""

    artifact_type: str
    artifact_name: str
    success: bool
    artifact_id: str = ""
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricDeployer:
    """Deploy migration artefacts to Microsoft Fabric.

    Parameters
    ----------
    fabric_client
        Authenticated ``FabricClient`` instance.
    lakehouse_id
        Target Lakehouse ID for DDL/table operations.
    """

    fabric_client: FabricClient
    lakehouse_id: str
    dry_run: bool = False

    # ---- DDL / Table Creation ----

    async def deploy_ddl(
        self,
        ddl_statements: list[str],
        sql_endpoint: str,
    ) -> list[DeploymentResult]:
        """Execute DDL statements against the Lakehouse SQL endpoint."""
        results: list[DeploymentResult] = []

        for stmt in ddl_statements:
            name = self._extract_table_name(stmt)
            if self.dry_run:
                logger.info("[DRY-RUN] Would execute DDL: %s", stmt[:80])
                results.append(
                    DeploymentResult(
                        artifact_type="table",
                        artifact_name=name,
                        success=True,
                        details={"dry_run": True},
                    )
                )
                continue

            try:
                await self.fabric_client.execute_sql(sql_endpoint, stmt)
                results.append(
                    DeploymentResult(
                        artifact_type="table",
                        artifact_name=name,
                        success=True,
                    )
                )
                logger.info("Deployed table: %s", name)
            except Exception as exc:
                results.append(
                    DeploymentResult(
                        artifact_type="table",
                        artifact_name=name,
                        success=False,
                        error=str(exc),
                    )
                )
                logger.error("Failed to deploy table %s: %s", name, exc)

        return results

    # ---- Data Pipelines ----

    async def deploy_pipeline(
        self,
        name: str,
        definition: dict[str, Any],
    ) -> DeploymentResult:
        """Deploy a data pipeline to the Fabric workspace."""
        if self.dry_run:
            logger.info("[DRY-RUN] Would deploy pipeline: %s", name)
            return DeploymentResult(
                artifact_type="pipeline",
                artifact_name=name,
                success=True,
                details={"dry_run": True},
            )

        try:
            result = await self.fabric_client.create_pipeline(name, definition)
            aid = result.get("id", "")
            logger.info("Deployed pipeline: %s (id=%s)", name, aid)
            return DeploymentResult(
                artifact_type="pipeline",
                artifact_name=name,
                success=True,
                artifact_id=aid,
            )
        except Exception as exc:
            logger.error("Failed to deploy pipeline %s: %s", name, exc)
            return DeploymentResult(
                artifact_type="pipeline",
                artifact_name=name,
                success=False,
                error=str(exc),
            )

    # ---- Notebooks ----

    async def deploy_notebook(
        self,
        name: str,
        content: str,
    ) -> DeploymentResult:
        """Deploy a Fabric notebook."""
        if self.dry_run:
            logger.info("[DRY-RUN] Would deploy notebook: %s", name)
            return DeploymentResult(
                artifact_type="notebook",
                artifact_name=name,
                success=True,
                details={"dry_run": True},
            )

        try:
            result = await self.fabric_client.create_notebook(name, content)
            aid = result.get("id", "")
            logger.info("Deployed notebook: %s (id=%s)", name, aid)
            return DeploymentResult(
                artifact_type="notebook",
                artifact_name=name,
                success=True,
                artifact_id=aid,
            )
        except Exception as exc:
            logger.error("Failed to deploy notebook %s: %s", name, exc)
            return DeploymentResult(
                artifact_type="notebook",
                artifact_name=name,
                success=False,
                error=str(exc),
            )

    # ---- Batch deploy ----

    async def deploy_all(
        self,
        *,
        ddl_statements: list[str] | None = None,
        sql_endpoint: str = "",
        pipelines: list[tuple[str, dict[str, Any]]] | None = None,
        notebooks: list[tuple[str, str]] | None = None,
    ) -> list[DeploymentResult]:
        """Deploy all artefacts in order: DDL → Pipelines → Notebooks."""
        all_results: list[DeploymentResult] = []

        if ddl_statements and sql_endpoint:
            all_results.extend(await self.deploy_ddl(ddl_statements, sql_endpoint))

        for name, defn in (pipelines or []):
            all_results.append(await self.deploy_pipeline(name, defn))

        for name, content in (notebooks or []):
            all_results.append(await self.deploy_notebook(name, content))

        succeeded = sum(1 for r in all_results if r.success)
        failed = sum(1 for r in all_results if not r.success)
        logger.info(
            "Deployment complete: %d succeeded, %d failed", succeeded, failed
        )
        return all_results

    # ---- helpers ----

    @staticmethod
    def _extract_table_name(ddl: str) -> str:
        """Best-effort extraction of table name from a CREATE TABLE statement."""
        upper = ddl.upper()
        for keyword in ("CREATE TABLE IF NOT EXISTS", "CREATE TABLE", "CREATE OR REPLACE TABLE"):
            if keyword in upper:
                rest = ddl[upper.index(keyword) + len(keyword) :].strip()
                name = rest.split("(")[0].split()[0].strip().strip("`\"'[]")
                return name
        return "unknown_table"
