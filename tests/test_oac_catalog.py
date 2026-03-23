"""Tests for OAC Catalog REST API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clients.oac_auth import OACAuth, TokenInfo
from src.clients.oac_catalog import CatalogItem, OACCatalogClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_auth() -> OACAuth:
    auth = OACAuth(
        token_url="https://idcs.example.com/oauth2/v1/token",
        client_id="id",
        client_secret="secret",
    )
    import time
    auth._token = TokenInfo(access_token="test", expires_at=time.time() + 3600)
    return auth


def _mock_response(body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# CatalogItem
# ---------------------------------------------------------------------------


class TestCatalogItem:
    def test_basic_fields(self):
        item = CatalogItem(
            path="/shared/sales/report1",
            name="report1",
            type="analysis",
            owner="admin",
        )
        assert item.path == "/shared/sales/report1"
        assert item.type == "analysis"


# ---------------------------------------------------------------------------
# OACCatalogClient
# ---------------------------------------------------------------------------


class TestOACCatalogClient:
    def _make_client(self) -> OACCatalogClient:
        return OACCatalogClient(
            base_url="https://oac.example.com",
            auth=_mock_auth(),
            page_size=10,
        )

    @pytest.mark.asyncio
    async def test_list_folder(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({
                "items": [
                    {"path": "/shared/a", "name": "a", "type": "folder"},
                    {"path": "/shared/b", "name": "b", "type": "analysis"},
                ]
            })
        )
        client._client = mock_http

        items = await client.list_folder("/shared")
        assert len(items) == 2
        assert items[0].type == "folder"
        assert items[1].type == "analysis"

    @pytest.mark.asyncio
    async def test_get_analysis(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"name": "Sales Report", "columns": []})
        )
        client._client = mock_http

        data = await client.get_analysis("/shared/sales/report1")
        assert data["name"] == "Sales Report"

    @pytest.mark.asyncio
    async def test_list_all_paginated_single_page(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({
                "items": [{"id": "1"}, {"id": "2"}],
                "hasMore": False,
            })
        )
        client._client = mock_http

        results = await client.list_all_paginated("/api/20210901/test")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_all_paginated_multiple_pages(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False

        page1 = _mock_response({"items": [{"id": str(i)} for i in range(10)]})
        page2 = _mock_response({"items": [{"id": "10"}], "hasMore": False})
        mock_http.request = AsyncMock(side_effect=[page1, page2])
        client._client = mock_http

        results = await client.list_all_paginated("/api/20210901/test")
        assert len(results) == 11

    @pytest.mark.asyncio
    async def test_parse_items_empty(self):
        client = self._make_client()
        items = client._parse_items({"items": []})
        assert items == []

    @pytest.mark.asyncio
    async def test_close(self):
        client = self._make_client()
        mock_http = AsyncMock()
        mock_http.is_closed = False
        client._client = mock_http
        await client.close()
        mock_http.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_subject_areas(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"items": [{"name": "Sales"}, {"name": "HR"}]})
        )
        client._client = mock_http
        result = await client.list_subject_areas()
        assert len(result) == 2
