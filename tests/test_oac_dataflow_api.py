"""Tests for OAC Data Flow REST API client."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.clients.oac_auth import OACAuth, TokenInfo
from src.clients.oac_dataflow_api import (
    DataFlowDefinition,
    OACDataFlowClient,
    OACDataFlowError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_auth() -> OACAuth:
    auth = OACAuth(
        token_url="https://idcs.example.com/oauth2/v1/token",
        client_id="id",
        client_secret="secret",
    )
    auth._token = TokenInfo(access_token="test", expires_at=time.time() + 3600)
    return auth


def _mock_response(body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# DataFlowDefinition
# ---------------------------------------------------------------------------


class TestDataFlowDefinition:
    def test_basic_fields(self):
        defn = DataFlowDefinition(
            id="df-1",
            name="Load Sales",
            path="/shared/etl/load_sales",
            steps=[{"type": "sql_transform"}],
        )
        assert defn.id == "df-1"
        assert defn.name == "Load Sales"
        assert len(defn.steps) == 1


# ---------------------------------------------------------------------------
# OACDataFlowClient
# ---------------------------------------------------------------------------


class TestOACDataFlowClient:
    def _make_client(self) -> OACDataFlowClient:
        return OACDataFlowClient(
            base_url="https://oac.example.com",
            auth=_mock_auth(),
            page_size=10,
        )

    @pytest.mark.asyncio
    async def test_list_dataflows_single_page(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({
                "items": [
                    {"id": "df-1", "name": "Flow1"},
                    {"id": "df-2", "name": "Flow2"},
                ],
                "hasMore": False,
            })
        )
        client._client = mock_http

        flows = await client.list_dataflows()
        assert len(flows) == 2

    @pytest.mark.asyncio
    async def test_list_dataflows_multiple_pages(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False

        page1 = _mock_response({"items": [{"id": f"df-{i}"} for i in range(10)]})
        page2 = _mock_response({"items": [{"id": "df-10"}], "hasMore": False})
        mock_http.request = AsyncMock(side_effect=[page1, page2])
        client._client = mock_http

        flows = await client.list_dataflows()
        assert len(flows) == 11

    @pytest.mark.asyncio
    async def test_get_dataflow(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({
                "id": "df-1",
                "name": "Load Sales",
                "path": "/etl/load",
                "steps": [{"type": "sql"}],
                "parameters": [{"name": "date"}],
            })
        )
        client._client = mock_http

        defn = await client.get_dataflow("df-1")
        assert isinstance(defn, DataFlowDefinition)
        assert defn.name == "Load Sales"
        assert len(defn.steps) == 1

    @pytest.mark.asyncio
    async def test_get_dataflow_by_path_not_found(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"items": []})
        )
        client._client = mock_http

        with pytest.raises(OACDataFlowError, match="not found"):
            await client.get_dataflow_by_path("/missing/flow")

    @pytest.mark.asyncio
    async def test_get_execution_history(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({
                "items": [
                    {"id": "exec-1", "status": "completed"},
                    {"id": "exec-2", "status": "failed"},
                ]
            })
        )
        client._client = mock_http

        history = await client.get_execution_history("df-1")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_export_all_definitions(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False

        # First call: list_dataflows
        list_resp = _mock_response({
            "items": [{"id": "df-1", "name": "F1"}, {"id": "df-2", "name": "F2"}],
            "hasMore": False,
        })
        # Next calls: get_dataflow for each
        get_resp1 = _mock_response({"id": "df-1", "name": "F1", "path": "/a"})
        get_resp2 = _mock_response({"id": "df-2", "name": "F2", "path": "/b"})
        mock_http.request = AsyncMock(side_effect=[list_resp, get_resp1, get_resp2])
        client._client = mock_http

        definitions = await client.export_all_definitions()
        assert len(definitions) == 2

    @pytest.mark.asyncio
    async def test_close(self):
        client = self._make_client()
        mock_http = AsyncMock()
        mock_http.is_closed = False
        client._client = mock_http
        await client.close()
        mock_http.aclose.assert_called_once()
