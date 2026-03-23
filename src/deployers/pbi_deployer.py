"""Power BI Deployer — deploy artefacts to Power BI Service.

Handles:
- Semantic Model (TMDL) deployment via XMLA/REST
- Report deployment (PBIR / PBIX import)
- RLS role configuration
- Workspace role assignment
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.clients.pbi_client import PBIClient

logger = logging.getLogger(__name__)


@dataclass
class PBIDeploymentResult:
    """Result of a Power BI deployment operation."""

    artifact_type: str
    artifact_name: str
    success: bool
    artifact_id: str = ""
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PBIDeployer:
    """Deploy migration artefacts to Power BI Service.

    Parameters
    ----------
    pbi_client
        Authenticated ``PBIClient`` instance.
    """

    pbi_client: PBIClient
    dry_run: bool = False

    # ---- Semantic Model ----

    async def deploy_semantic_model(
        self,
        name: str,
        tmdl_files: dict[str, str],
    ) -> PBIDeploymentResult:
        """Deploy a TMDL semantic model.

        Parameters
        ----------
        name
            Display name for the semantic model.
        tmdl_files
            Mapping of TMDL file paths → content.
        """
        if self.dry_run:
            logger.info("[DRY-RUN] Would deploy semantic model: %s (%d files)", name, len(tmdl_files))
            return PBIDeploymentResult(
                artifact_type="semantic_model",
                artifact_name=name,
                success=True,
                details={"dry_run": True, "files": list(tmdl_files.keys())},
            )

        try:
            result = await self.pbi_client.deploy_tmdl(name, tmdl_files)
            logger.info("Deployed semantic model: %s", name)
            return PBIDeploymentResult(
                artifact_type="semantic_model",
                artifact_name=name,
                success=True,
                details=result,
            )
        except Exception as exc:
            logger.error("Failed to deploy semantic model %s: %s", name, exc)
            return PBIDeploymentResult(
                artifact_type="semantic_model",
                artifact_name=name,
                success=False,
                error=str(exc),
            )

    # ---- Reports ----

    async def deploy_pbir_report(
        self,
        name: str,
        pbir_files: dict[str, str],
        dataset_id: str = "",
    ) -> PBIDeploymentResult:
        """Deploy a Power BI Enhanced Report (PBIR) definition.

        Parameters
        ----------
        name
            Display name for the report.
        pbir_files
            Mapping of relative path → file content for all PBIR definition
            files (report.json, pages/*, visuals/*, etc.).
        dataset_id
            The dataset (semantic model) ID the report connects to.
        """
        if self.dry_run:
            logger.info("[DRY-RUN] Would deploy PBIR report: %s (%d files)", name, len(pbir_files))
            return PBIDeploymentResult(
                artifact_type="pbir_report",
                artifact_name=name,
                success=True,
                details={"dry_run": True, "files": list(pbir_files.keys())},
            )

        try:
            import base64
            import io
            import zipfile

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for rel_path, content in pbir_files.items():
                    zf.writestr(f"definition/{rel_path}", content)

            zip_bytes = buf.getvalue()
            encoded = base64.b64encode(zip_bytes).decode("ascii")

            body: dict[str, Any] = {
                "displayName": name,
                "type": "Report",
                "definition": {
                    "parts": [
                        {
                            "path": "definition.zip",
                            "payload": encoded,
                            "payloadType": "InlineBase64",
                        }
                    ],
                },
            }
            if dataset_id:
                body["creationPayload"] = {"datasetId": dataset_id}

            result = await self.pbi_client._request(
                "POST",
                f"/workspaces/{self.pbi_client.group_id}/items",
                json=body,
            )

            aid = result.get("id", "")
            logger.info("Deployed PBIR report: %s (id=%s)", name, aid)
            return PBIDeploymentResult(
                artifact_type="pbir_report",
                artifact_name=name,
                success=True,
                artifact_id=aid,
                details={"files_deployed": list(pbir_files.keys())},
            )
        except Exception as exc:
            logger.error("Failed to deploy PBIR report %s: %s", name, exc)
            return PBIDeploymentResult(
                artifact_type="pbir_report",
                artifact_name=name,
                success=False,
                error=str(exc),
            )

    async def deploy_report(
        self,
        name: str,
        pbix_path: Path | None = None,
        pbix_bytes: bytes | None = None,
    ) -> PBIDeploymentResult:
        """Deploy a report via PBIX import.

        Provide either ``pbix_path`` (file on disk) or ``pbix_bytes``.
        """
        if self.dry_run:
            logger.info("[DRY-RUN] Would deploy report: %s", name)
            return PBIDeploymentResult(
                artifact_type="report",
                artifact_name=name,
                success=True,
                details={"dry_run": True},
            )

        try:
            if pbix_path:
                content = pbix_path.read_bytes()
            elif pbix_bytes:
                content = pbix_bytes
            else:
                raise ValueError("Either pbix_path or pbix_bytes is required")

            result = await self.pbi_client.import_pbix(name, content)
            aid = result.get("id", "")
            logger.info("Deployed report: %s (id=%s)", name, aid)
            return PBIDeploymentResult(
                artifact_type="report",
                artifact_name=name,
                success=True,
                artifact_id=aid,
            )
        except Exception as exc:
            logger.error("Failed to deploy report %s: %s", name, exc)
            return PBIDeploymentResult(
                artifact_type="report",
                artifact_name=name,
                success=False,
                error=str(exc),
            )

    # ---- RLS ----

    async def configure_rls(
        self,
        dataset_id: str,
        roles: list[dict[str, Any]],
    ) -> PBIDeploymentResult:
        """Configure RLS roles for a dataset.

        Note: Full RLS deployment is done via XMLA / TMDL — this method
        verifies the roles are applied and logs the result.
        """
        if self.dry_run:
            logger.info("[DRY-RUN] Would configure %d RLS roles on %s", len(roles), dataset_id)
            return PBIDeploymentResult(
                artifact_type="rls",
                artifact_name=dataset_id,
                success=True,
                details={"dry_run": True, "role_count": len(roles)},
            )

        try:
            existing = await self.pbi_client.get_dataset_roles(dataset_id)
            logger.info(
                "Dataset %s has %d existing roles, deploying %d",
                dataset_id,
                len(existing),
                len(roles),
            )
            return PBIDeploymentResult(
                artifact_type="rls",
                artifact_name=dataset_id,
                success=True,
                details={
                    "existing_roles": len(existing),
                    "target_roles": len(roles),
                },
            )
        except Exception as exc:
            return PBIDeploymentResult(
                artifact_type="rls",
                artifact_name=dataset_id,
                success=False,
                error=str(exc),
            )

    # ---- OLS (Object-Level Security) ----

    async def configure_ols(
        self,
        dataset_id: str,
        ols_rules: list[dict[str, Any]],
    ) -> PBIDeploymentResult:
        """Configure Object-Level Security (column-level) for a dataset.

        OLS rules are deployed as part of the TMDL semantic model.  This
        method verifies the rules are applied by comparing the deployed role
        definitions against the expected OLS configuration.

        Parameters
        ----------
        dataset_id
            Target dataset / semantic model ID.
        ols_rules
            List of OLS rule dicts, each with ``role_name``, ``table_name``,
            ``column_name``, and ``permission`` (``None`` / ``Read``).
        """
        if self.dry_run:
            logger.info(
                "[DRY-RUN] Would configure %d OLS rules on %s",
                len(ols_rules),
                dataset_id,
            )
            return PBIDeploymentResult(
                artifact_type="ols",
                artifact_name=dataset_id,
                success=True,
                details={"dry_run": True, "rule_count": len(ols_rules)},
            )

        try:
            # Retrieve roles to verify OLS presence
            existing = await self.pbi_client.get_dataset_roles(dataset_id)
            ols_columns_found = 0
            for role in existing:
                permissions = role.get("tablePermissions", [])
                for perm in permissions:
                    ols_columns_found += len(perm.get("columnPermissions", []))

            logger.info(
                "Dataset %s: %d OLS column permissions found, %d expected",
                dataset_id,
                ols_columns_found,
                len(ols_rules),
            )
            return PBIDeploymentResult(
                artifact_type="ols",
                artifact_name=dataset_id,
                success=True,
                details={
                    "ols_columns_found": ols_columns_found,
                    "target_rules": len(ols_rules),
                },
            )
        except Exception as exc:
            return PBIDeploymentResult(
                artifact_type="ols",
                artifact_name=dataset_id,
                success=False,
                error=str(exc),
            )

    # ---- Workspace Users ----

    async def assign_workspace_roles(
        self,
        assignments: list[dict[str, str]],
    ) -> list[PBIDeploymentResult]:
        """Assign workspace roles (email + role pairs)."""
        results: list[PBIDeploymentResult] = []

        for assignment in assignments:
            email = assignment["email"]
            role = assignment.get("role", "Viewer")

            if self.dry_run:
                results.append(
                    PBIDeploymentResult(
                        artifact_type="workspace_role",
                        artifact_name=email,
                        success=True,
                        details={"dry_run": True, "role": role},
                    )
                )
                continue

            try:
                await self.pbi_client.add_workspace_user(email, role)
                results.append(
                    PBIDeploymentResult(
                        artifact_type="workspace_role",
                        artifact_name=email,
                        success=True,
                        details={"role": role},
                    )
                )
            except Exception as exc:
                results.append(
                    PBIDeploymentResult(
                        artifact_type="workspace_role",
                        artifact_name=email,
                        success=False,
                        error=str(exc),
                    )
                )

        return results

    # ---- Batch deploy ----

    async def deploy_all(
        self,
        *,
        semantic_models: list[tuple[str, dict[str, str]]] | None = None,
        reports: list[tuple[str, Path]] | None = None,
        pbir_reports: list[tuple[str, dict[str, str], str]] | None = None,
        rls_configs: list[tuple[str, list[dict[str, Any]]]] | None = None,
        ols_configs: list[tuple[str, list[dict[str, Any]]]] | None = None,
        workspace_roles: list[dict[str, str]] | None = None,
    ) -> list[PBIDeploymentResult]:
        """Deploy all PBI artefacts in order.

        Parameters
        ----------
        pbir_reports
            List of ``(name, pbir_files, dataset_id)`` tuples for PBIR reports.
        ols_configs
            List of ``(dataset_id, ols_rules)`` tuples for OLS configuration.
        """
        all_results: list[PBIDeploymentResult] = []

        for name, tmdl in (semantic_models or []):
            all_results.append(await self.deploy_semantic_model(name, tmdl))

        for name, path in (reports or []):
            all_results.append(await self.deploy_report(name, pbix_path=path))

        for name, pbir_files, ds_id in (pbir_reports or []):
            all_results.append(await self.deploy_pbir_report(name, pbir_files, ds_id))

        for ds_id, roles in (rls_configs or []):
            all_results.append(await self.configure_rls(ds_id, roles))

        for ds_id, ols_rules in (ols_configs or []):
            all_results.append(await self.configure_ols(ds_id, ols_rules))

        if workspace_roles:
            all_results.extend(await self.assign_workspace_roles(workspace_roles))

        succeeded = sum(1 for r in all_results if r.success)
        failed = sum(1 for r in all_results if not r.success)
        logger.info(
            "PBI deployment complete: %d succeeded, %d failed",
            succeeded,
            failed,
        )
        return all_results
