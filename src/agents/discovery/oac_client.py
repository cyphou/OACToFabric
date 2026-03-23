"""OAC REST API client — OAuth2, pagination, retry, catalog extraction."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.core.config import settings
from src.core.models import AssetType, Dependency, InventoryItem, MigrationStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping from OAC catalog type strings to our AssetType enum
# ---------------------------------------------------------------------------
_CATALOG_TYPE_MAP: dict[str, AssetType] = {
    "analysis": AssetType.ANALYSIS,
    "dashboard": AssetType.DASHBOARD,
    "dataModel": AssetType.DATA_MODEL,
    "prompt": AssetType.PROMPT,
    "filter": AssetType.FILTER,
    "agent": AssetType.AGENT_ALERT,
    "dataflow": AssetType.DATA_FLOW,
}


def _make_id(asset_type: str, path: str) -> str:
    """Create a deterministic ID from type + path."""
    slug = path.strip("/").replace("/", "__").replace(" ", "_").lower()
    return f"{asset_type}__{slug}"


# ---------------------------------------------------------------------------
# Retry decorator for OAC API calls
# ---------------------------------------------------------------------------
_retry_oac = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential_jitter(
        initial=settings.retry_backoff_seconds,
        max=30,
        jitter=2,
    ),
    before_sleep=lambda rs: logger.warning(
        "OAC API retry #%d after %s", rs.attempt_number, rs.outcome.exception()
    ),
)


class OACClient:
    """Async Oracle Analytics Cloud REST API client."""

    def __init__(
        self,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        token_url: str | None = None,
        api_version: str | None = None,
        page_size: int | None = None,
    ) -> None:
        self._base_url = (base_url or settings.oac_base_url).rstrip("/")
        self._client_id = client_id or settings.oac_client_id
        self._client_secret = client_secret or settings.oac_client_secret
        self._token_url = token_url or settings.oac_token_url
        self._api_version = api_version or settings.oac_api_version
        self._page_size = page_size or settings.page_size

        self._access_token: str | None = None
        self._token_expires: datetime | None = None
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # HTTP lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "OACClient":
        self._http = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # OAuth2 authentication
    # ------------------------------------------------------------------

    async def _ensure_token(self) -> str:
        """Obtain or refresh the OAuth2 bearer token."""
        now = datetime.now(timezone.utc)
        if self._access_token and self._token_expires and now < self._token_expires:
            return self._access_token

        assert self._http is not None, "Client not opened — use `async with OACClient() as c:`"
        resp = await self._http.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "urn:opc:resource:consumer::all",
            },
        )
        resp.raise_for_status()
        body = resp.json()
        self._access_token = body["access_token"]
        expires_in = int(body.get("expires_in", 3600))
        from datetime import timedelta

        self._token_expires = now + timedelta(seconds=expires_in - 60)
        logger.info("OAC token obtained (expires in %ds)", expires_in)
        return self._access_token  # type: ignore[return-value]

    async def _auth_headers(self) -> dict[str, str]:
        token = await self._ensure_token()
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # ------------------------------------------------------------------
    # Low-level request
    # ------------------------------------------------------------------

    @_retry_oac
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        assert self._http is not None
        headers = await self._auth_headers()
        resp = await self._http.get(f"{self._base_url}{path}", headers=headers, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            import asyncio

            logger.warning("OAC 429 — sleeping %ds", retry_after)
            await asyncio.sleep(retry_after)
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Catalog crawling with pagination
    # ------------------------------------------------------------------

    async def _paginate_catalog(
        self, asset_type: str, path: str = "/shared"
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield all catalog items of a given type via pagination."""
        offset = 0
        while True:
            data = await self._get(
                f"/api/{self._api_version}/catalog",
                params={
                    "type": asset_type,
                    "path": path,
                    "offset": offset,
                    "limit": self._page_size,
                },
            )
            items: list[dict[str, Any]] = data.get("items", [])
            if not items:
                break
            for item in items:
                yield item
            offset += len(items)
            if len(items) < self._page_size:
                break

    # ------------------------------------------------------------------
    # Public discovery methods
    # ------------------------------------------------------------------

    async def discover_catalog_assets(self, path: str = "/shared") -> list[InventoryItem]:
        """Discover all catalog assets (analyses, dashboards, etc.)."""
        results: list[InventoryItem] = []

        for oac_type, asset_type in _CATALOG_TYPE_MAP.items():
            logger.info("Discovering %s assets under %s …", oac_type, path)
            count = 0
            async for raw in self._paginate_catalog(oac_type, path):
                item = self._parse_catalog_item(raw, asset_type)
                results.append(item)
                count += 1
            logger.info("  → found %d %s items", count, oac_type)

        return results

    async def discover_connections(self) -> list[InventoryItem]:
        """Discover OAC connections."""
        data = await self._get(f"/api/{self._api_version}/connections")
        items: list[dict[str, Any]] = data.get("items", [])
        results: list[InventoryItem] = []
        for raw in items:
            results.append(
                InventoryItem(
                    id=_make_id("connection", raw.get("name", "")),
                    asset_type=AssetType.CONNECTION,
                    source_path=f"/connections/{raw.get('name', '')}",
                    name=raw.get("name", ""),
                    owner=raw.get("owner", ""),
                    last_modified=_parse_dt(raw.get("lastModified")),
                    metadata={
                        "type": raw.get("type", ""),
                        "host": raw.get("host", ""),
                        "port": raw.get("port"),
                        "database": raw.get("database", ""),
                    },
                    source="api",
                )
            )
        logger.info("Discovered %d connections", len(results))
        return results

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_catalog_item(raw: dict[str, Any], asset_type: AssetType) -> InventoryItem:
        path = raw.get("path", f"/unknown/{raw.get('name', 'unnamed')}")
        name = raw.get("name", "")
        item_id = _make_id(asset_type.value, path)

        # Build dependencies from referenced subject areas / prompts
        deps: list[Dependency] = []
        for sa in raw.get("subjectAreas", []):
            deps.append(
                Dependency(
                    source_id=item_id,
                    target_id=_make_id("subjectArea", sa),
                    dependency_type="uses_subject_area",
                )
            )
        for p in raw.get("prompts", []):
            deps.append(
                Dependency(
                    source_id=item_id,
                    target_id=_make_id("prompt", p),
                    dependency_type="uses_prompt",
                )
            )

        # Extract metadata
        meta: dict[str, Any] = {}
        for key in ("columns", "filters", "prompts", "pages", "subjectAreas", "steps"):
            if key in raw:
                meta[key] = raw[key]

        # Count embedded analyses (dashboards)
        if "embeddedContent" in raw:
            embedded = raw["embeddedContent"]
            meta["embedded_analyses"] = [e.get("path") for e in embedded] if isinstance(embedded, list) else []
            for e in meta.get("embedded_analyses", []):
                deps.append(
                    Dependency(
                        source_id=item_id,
                        target_id=_make_id("analysis", e),
                        dependency_type="embeds_analysis",
                    )
                )

        return InventoryItem(
            id=item_id,
            asset_type=asset_type,
            source_path=path,
            name=name,
            owner=raw.get("owner", ""),
            last_modified=_parse_dt(raw.get("lastModified")),
            metadata=meta,
            dependencies=deps,
            source="api",
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
