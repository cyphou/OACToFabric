"""OAC Data Flow REST API client.

Provides access to Oracle Analytics Cloud Data Flow endpoints:
- List data flows
- Export data flow definition (JSON)
- Export data flow execution history

Supports pagination and rate-limit retry.
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

from src.clients.oac_auth import OACAuth

logger = logging.getLogger(__name__)


class OACDataFlowError(Exception):
    """Non-retryable data-flow API error."""


@dataclass
class DataFlowDefinition:
    """Parsed data flow definition."""

    id: str
    name: str
    path: str
    description: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    schedule: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OACDataFlowClient:
    """Client for OAC Data Flow REST API.

    Parameters
    ----------
    base_url
        OAC instance base URL.
    auth
        ``OACAuth`` for token management.
    api_version
        API version string.
    page_size
        Items per page.
    """

    base_url: str
    auth: OACAuth
    api_version: str = "20210901"
    page_size: int = 100
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=60.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        headers = await self.auth.get_headers()
        resp = await client.request(method, path, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()

    # ---- Data Flow operations ----

    async def list_dataflows(self) -> list[dict[str, Any]]:
        """List all data flows (all pages)."""
        all_flows: list[dict[str, Any]] = []
        offset = 0

        while True:
            data = await self._request(
                "GET",
                f"/api/{self.api_version}/dataflows",
                params={"offset": offset, "limit": self.page_size},
            )
            items = data.get("items", [])
            all_flows.extend(items)
            if len(items) < self.page_size or data.get("hasMore") is False:
                break
            offset += self.page_size

        logger.info("Listed %d data flows", len(all_flows))
        return all_flows

    async def get_dataflow(self, dataflow_id: str) -> DataFlowDefinition:
        """Retrieve a single data flow definition."""
        data = await self._request(
            "GET",
            f"/api/{self.api_version}/dataflows/{dataflow_id}",
        )
        return self._parse_dataflow(data, dataflow_id)

    async def get_dataflow_by_path(self, path: str) -> DataFlowDefinition:
        """Retrieve a data flow by catalog path."""
        data = await self._request(
            "GET",
            f"/api/{self.api_version}/dataflows",
            params={"path": path},
        )
        items = data.get("items", [])
        if not items:
            raise OACDataFlowError(f"Data flow not found at path: {path}")
        return self._parse_dataflow(items[0], items[0].get("id", ""))

    async def get_execution_history(
        self,
        dataflow_id: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve execution history for a data flow."""
        data = await self._request(
            "GET",
            f"/api/{self.api_version}/dataflows/{dataflow_id}/executions",
            params={"limit": limit},
        )
        return data.get("items", [])

    async def export_all_definitions(self) -> list[DataFlowDefinition]:
        """Export all data flow definitions."""
        flows = await self.list_dataflows()
        definitions: list[DataFlowDefinition] = []

        for flow_meta in flows:
            flow_id = flow_meta.get("id", "")
            if flow_id:
                try:
                    defn = await self.get_dataflow(flow_id)
                    definitions.append(defn)
                except Exception as exc:
                    logger.warning("Failed to export dataflow %s: %s", flow_id, exc)

        logger.info("Exported %d data flow definitions", len(definitions))
        return definitions

    # ---- parsing ----

    def _parse_dataflow(self, data: dict[str, Any], dataflow_id: str) -> DataFlowDefinition:
        return DataFlowDefinition(
            id=dataflow_id or data.get("id", ""),
            name=data.get("name", ""),
            path=data.get("path", ""),
            description=data.get("description", ""),
            steps=data.get("steps", []),
            parameters=data.get("parameters", []),
            schedule=data.get("schedule"),
            raw=data,
        )
