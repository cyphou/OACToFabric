"""Power BI REST API client.

Provides access to Power BI management APIs:
- Dataset / Semantic Model deployment
- Report deployment  
- RLS role management
- Refresh operations
- Workspace binding

Uses Azure AD (Entra ID) bearer tokens for authentication.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

PBI_API_BASE = "https://api.powerbi.com/v1.0/myorg"


class PBIClientError(Exception):
    """Non-retryable Power BI API error."""


@dataclass
class PBIClient:
    """Async client for Power BI REST APIs.

    Parameters
    ----------
    access_token
        Azure AD bearer token.
    group_id
        Workspace (group) ID for all operations.
    api_base
        PBI API base URL.
    """

    access_token: str
    group_id: str
    api_base: str = PBI_API_BASE
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.api_base,
                timeout=120.0,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        data: bytes | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        kwargs: dict[str, Any] = {}
        if json is not None:
            kwargs["json"] = json
        if params:
            kwargs["params"] = params
        if data is not None:
            kwargs["content"] = data
        if content_type:
            kwargs["headers"] = {"Content-Type": content_type}
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ---- Datasets / Semantic Models ----

    async def list_datasets(self) -> list[dict[str, Any]]:
        """List datasets in the workspace."""
        data = await self._request("GET", f"/groups/{self.group_id}/datasets")
        return data.get("value", [])

    async def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/groups/{self.group_id}/datasets/{dataset_id}"
        )

    async def refresh_dataset(self, dataset_id: str) -> dict[str, Any]:
        """Trigger a dataset refresh."""
        return await self._request(
            "POST",
            f"/groups/{self.group_id}/datasets/{dataset_id}/refreshes",
            json={"notifyOption": "NoNotification"},
        )

    async def get_refresh_history(
        self, dataset_id: str, top: int = 10
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            f"/groups/{self.group_id}/datasets/{dataset_id}/refreshes",
            params={"$top": top},
        )
        return data.get("value", [])

    async def take_over_dataset(self, dataset_id: str) -> dict[str, Any]:
        """Take over a dataset (become the owner)."""
        return await self._request(
            "POST",
            f"/groups/{self.group_id}/datasets/{dataset_id}/Default.TakeOver",
        )

    # ---- RLS ----

    async def get_dataset_roles(self, dataset_id: str) -> list[dict[str, Any]]:
        """Get RLS roles for a dataset (via enhanced metadata)."""
        data = await self._request(
            "GET",
            f"/groups/{self.group_id}/datasets/{dataset_id}",
            params={"$expand": "roles"},
        )
        return data.get("roles", [])

    # ---- Reports ----

    async def list_reports(self) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/groups/{self.group_id}/reports")
        return data.get("value", [])

    async def get_report(self, report_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/groups/{self.group_id}/reports/{report_id}"
        )

    async def clone_report(
        self,
        report_id: str,
        name: str,
        target_dataset_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name}
        if target_dataset_id:
            body["targetModelId"] = target_dataset_id
        return await self._request(
            "POST",
            f"/groups/{self.group_id}/reports/{report_id}/Clone",
            json=body,
        )

    async def delete_report(self, report_id: str) -> dict[str, Any]:
        return await self._request(
            "DELETE", f"/groups/{self.group_id}/reports/{report_id}"
        )

    # ---- Import (PBIX / PBIR) ----

    async def import_pbix(
        self,
        display_name: str,
        pbix_bytes: bytes,
        *,
        name_conflict: str = "CreateOrOverwrite",
    ) -> dict[str, Any]:
        """Import a PBIX file into the workspace.

        Parameters
        ----------
        display_name
            Display name for the imported report/dataset.
        pbix_bytes
            Raw bytes of the .pbix file.
        name_conflict
            Conflict resolution: ``CreateOrOverwrite``, ``Abort``, ``Ignore``.
        """
        return await self._request(
            "POST",
            f"/groups/{self.group_id}/imports",
            params={
                "datasetDisplayName": display_name,
                "nameConflict": name_conflict,
            },
            data=pbix_bytes,
            content_type="application/octet-stream",
        )

    # ---- Workspace ----

    async def get_workspace(self) -> dict[str, Any]:
        return await self._request("GET", f"/groups/{self.group_id}")

    async def list_workspace_users(self) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/groups/{self.group_id}/users")
        return data.get("value", [])

    async def add_workspace_user(
        self,
        email: str,
        role: str = "Viewer",
    ) -> dict[str, Any]:
        """Add a user to the workspace."""
        return await self._request(
            "POST",
            f"/groups/{self.group_id}/users",
            json={
                "emailAddress": email,
                "groupUserAccessRight": role,
            },
        )

    # ---- XMLA endpoint / TMDL deployment ----

    async def deploy_tmdl(
        self,
        dataset_name: str,
        tmdl_content: dict[str, str],
        *,
        conflict_strategy: str = "CreateOrOverwrite",
        xmla_endpoint: str | None = None,
    ) -> dict[str, Any]:
        """Deploy a TMDL semantic model to a Power BI workspace.

        Supports three deployment methods (tried in order):
        1. **Tabular Editor CLI** (``TabularEditor.exe``) — recommended.
        2. **PBI Enhanced Deployment REST** — for supported tenants.
        3. **PBIX import** fallback — packages TMDL as pbix.

        Parameters
        ----------
        dataset_name
            Display name for the semantic model.
        tmdl_content
            Dict of ``relative_path → file_content`` for all TMDL files.
        conflict_strategy
            ``CreateOrOverwrite`` or ``Abort``.
        xmla_endpoint
            Optional XMLA endpoint URL.  If ``None``, uses the default
            workspace XMLA endpoint.
        """
        try:
            return await self._deploy_via_tabular_editor(
                dataset_name, tmdl_content, xmla_endpoint
            )
        except (FileNotFoundError, OSError) as exc:
            logger.info(
                "Tabular Editor not available (%s) — trying REST deploy", exc
            )

        try:
            return await self._deploy_via_rest(
                dataset_name, tmdl_content, conflict_strategy
            )
        except Exception as exc:
            logger.warning("REST deploy failed (%s) — trying PBIX import", exc)

        return await self._deploy_via_pbix_import(dataset_name, tmdl_content)

    async def _deploy_via_tabular_editor(
        self,
        dataset_name: str,
        tmdl_content: dict[str, str],
        xmla_endpoint: str | None,
    ) -> dict[str, Any]:
        """Deploy TMDL using Tabular Editor 2/3 CLI."""
        import asyncio
        import shutil
        import tempfile
        from pathlib import Path

        te_path = shutil.which("TabularEditor") or shutil.which("TabularEditor.exe")
        if not te_path:
            raise FileNotFoundError("TabularEditor CLI not found on PATH")

        # Write TMDL files to a temp directory
        with tempfile.TemporaryDirectory(prefix="tmdl_") as tmpdir:
            for rel_path, content in tmdl_content.items():
                full = Path(tmpdir) / rel_path
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_text(content, encoding="utf-8")

            endpoint = xmla_endpoint or (
                f"powerbi://api.powerbi.com/v1.0/myorg/{self.group_id}"
            )

            cmd = [
                te_path,
                tmpdir,
                "-D", endpoint, dataset_name,
                "-O",  # overwrite
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                raise PBIClientError(
                    f"Tabular Editor deploy failed (rc={proc.returncode}): {error_msg[:500]}"
                )

            logger.info(
                "TMDL deployed via Tabular Editor: %s (%d files)",
                dataset_name,
                len(tmdl_content),
            )
            return {
                "status": "ok",
                "method": "tabular_editor",
                "dataset_name": dataset_name,
                "files_deployed": list(tmdl_content.keys()),
            }

    async def _deploy_via_rest(
        self,
        dataset_name: str,
        tmdl_content: dict[str, str],
        conflict_strategy: str,
    ) -> dict[str, Any]:
        """Deploy TMDL via PBI Enhanced REST API (createReportFromDefinition).

        Uses the Import API with enhanced dataset metadata.
        """
        import base64
        import io
        import zipfile

        # Package TMDL files into a zip
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel_path, content in tmdl_content.items():
                zf.writestr(f"definition/{rel_path}", content)

        zip_bytes = buffer.getvalue()
        encoded = base64.b64encode(zip_bytes).decode("ascii")

        body = {
            "displayName": dataset_name,
            "type": "SemanticModel",
            "definition": {
                "parts": [
                    {
                        "path": "definition.zip",
                        "payload": encoded,
                        "payloadType": "InlineBase64",
                    }
                ]
            },
        }

        result = await self._request(
            "POST",
            f"/workspaces/{self.group_id}/items",
            json=body,
            params={"nameConflict": conflict_strategy},
        )

        logger.info(
            "TMDL deployed via REST API: %s (%d files)",
            dataset_name,
            len(tmdl_content),
        )
        return {
            "status": "ok",
            "method": "rest_api",
            "dataset_name": dataset_name,
            "files_deployed": list(tmdl_content.keys()),
            "response": result,
        }

    async def _deploy_via_pbix_import(
        self,
        dataset_name: str,
        tmdl_content: dict[str, str],
    ) -> dict[str, Any]:
        """Fallback: package TMDL as a minimal PBIX and use the import API."""
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel_path, content in tmdl_content.items():
                zf.writestr(rel_path, content)
            # Minimal DataModelSchema for PBIX import
            zf.writestr(
                "DataModelSchema",
                '{"name": "' + dataset_name + '", "compatibilityLevel": 1567}',
            )

        result = await self.import_pbix(
            display_name=dataset_name,
            pbix_bytes=buffer.getvalue(),
            name_conflict="CreateOrOverwrite",
        )

        logger.info(
            "TMDL deployed via PBIX import fallback: %s (%d files)",
            dataset_name,
            len(tmdl_content),
        )
        return {
            "status": "ok",
            "method": "pbix_import",
            "dataset_name": dataset_name,
            "files_deployed": list(tmdl_content.keys()),
            "response": result,
        }

    async def refresh_and_wait(
        self,
        dataset_id: str,
        *,
        poll_interval_seconds: int = 10,
        timeout_seconds: int = 600,
    ) -> dict[str, Any]:
        """Trigger a dataset refresh and poll until completion.

        Returns the final refresh status.
        """
        import asyncio

        await self.refresh_dataset(dataset_id)
        logger.info("Refresh triggered for dataset %s", dataset_id)

        elapsed = 0
        while elapsed < timeout_seconds:
            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds

            history = await self.get_refresh_history(dataset_id, top=1)
            if history:
                latest = history[0]
                status = latest.get("status", "Unknown")
                if status == "Completed":
                    logger.info("Refresh completed for %s", dataset_id)
                    return latest
                if status == "Failed":
                    raise PBIClientError(
                        f"Refresh failed: {latest.get('serviceExceptionJson', 'unknown error')}"
                    )

        raise PBIClientError(
            f"Refresh timed out after {timeout_seconds}s for dataset {dataset_id}"
        )
