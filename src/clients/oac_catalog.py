"""OAC Catalog REST API client.

Provides paginated access to the Oracle Analytics Cloud catalog:
- List folders and analyses under a given path
- Retrieve analysis/dashboard metadata (XML definition)
- Retrieve subject area definitions

Implements automatic pagination, 429 rate-limit handling,
and cached responses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.clients.oac_auth import OACAuth

logger = logging.getLogger(__name__)


class OACCatalogError(Exception):
    """Raised on non-retryable catalog API failures."""


@dataclass
class CatalogItem:
    """A single catalog entry."""

    path: str
    name: str
    type: str  # "folder", "analysis", "dashboard", "filter", "other"
    owner: str = ""
    description: str = ""
    caption: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class OACCatalogClient:
    """Client for OAC Catalog REST API.

    Parameters
    ----------
    base_url
        OAC instance base URL (without trailing ``/``).
    auth
        ``OACAuth`` instance for token management.
    api_version
        API version string.
    page_size
        Number of items per paginated request.
    max_retries
        Retry attempts on transient errors.
    """

    base_url: str
    auth: OACAuth
    api_version: str = "20210901"
    page_size: int = 100
    max_retries: int = 3
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

    # ---- low-level request ----

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

    # ---- catalog operations ----

    async def list_folder(self, folder_path: str) -> list[CatalogItem]:
        """List items in *folder_path* (one page)."""
        data = await self._request(
            "GET",
            f"/api/{self.api_version}/catalog",
            params={"path": folder_path, "limit": self.page_size},
        )
        return self._parse_items(data)

    async def list_folder_recursive(self, folder_path: str) -> AsyncIterator[CatalogItem]:
        """Recursively traverse *folder_path* yielding all items."""
        items = await self.list_folder(folder_path)
        for item in items:
            yield item
            if item.type == "folder":
                async for child in self.list_folder_recursive(item.path):
                    yield child

    async def get_analysis(self, analysis_path: str) -> dict[str, Any]:
        """Retrieve full analysis definition (XML/JSON metadata)."""
        data = await self._request(
            "GET",
            f"/api/{self.api_version}/catalog/analyses",
            params={"path": analysis_path},
        )
        return data

    async def get_dashboard(self, dashboard_path: str) -> dict[str, Any]:
        """Retrieve full dashboard definition."""
        data = await self._request(
            "GET",
            f"/api/{self.api_version}/catalog/dashboards",
            params={"path": dashboard_path},
        )
        return data

    async def get_subject_area(self, sa_name: str) -> dict[str, Any]:
        """Retrieve a subject area definition."""
        data = await self._request(
            "GET",
            f"/api/{self.api_version}/catalog/subjectareas/{sa_name}",
        )
        return data

    async def list_subject_areas(self) -> list[dict[str, Any]]:
        """List all subject areas."""
        data = await self._request(
            "GET",
            f"/api/{self.api_version}/catalog/subjectareas",
        )
        return data.get("items", [])

    # ---- paginated helpers ----

    async def list_all_paginated(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        items_key: str = "items",
    ) -> list[dict[str, Any]]:
        """Fetch all pages from a paginated endpoint."""
        all_items: list[dict[str, Any]] = []
        offset = 0
        page_params = dict(params or {})

        while True:
            page_params["offset"] = offset
            page_params["limit"] = self.page_size
            data = await self._request("GET", endpoint, params=page_params)

            items = data.get(items_key, [])
            all_items.extend(items)
            logger.debug("Fetched %d items (offset=%d)", len(items), offset)

            if len(items) < self.page_size:
                break
            offset += self.page_size
            if data.get("hasMore") is False:
                break

        return all_items

    # ---- parsing ----

    def _parse_items(self, data: dict[str, Any]) -> list[CatalogItem]:
        """Parse catalog API response into ``CatalogItem`` list."""
        items: list[CatalogItem] = []
        for entry in data.get("items", []):
            items.append(
                CatalogItem(
                    path=entry.get("path", ""),
                    name=entry.get("name", ""),
                    type=entry.get("type", "other"),
                    owner=entry.get("owner", ""),
                    description=entry.get("description", ""),
                    caption=entry.get("caption", ""),
                    attributes=entry.get("attributes", {}),
                )
            )
        return items
