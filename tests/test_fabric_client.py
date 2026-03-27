"""Tests for Fabric REST API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.clients.fabric_client import FabricClient


def _mock_response(body: dict | list, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = b'{"ok": true}'
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


class TestFabricClient:
    def _make_client(self) -> FabricClient:
        return FabricClient(
            workspace_id="ws-123",
            access_token="tok-abc",
        )

    @pytest.mark.asyncio
    async def test_get_workspace(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"id": "ws-123", "displayName": "Test"})
        )
        client._client = mock_http

        ws = await client.get_workspace()
        assert ws["id"] == "ws-123"

    @pytest.mark.asyncio
    async def test_list_items(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"value": [{"id": "i1"}, {"id": "i2"}]})
        )
        client._client = mock_http

        items = await client.list_items()
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_list_lakehouses(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"value": [{"id": "lh-1"}]})
        )
        client._client = mock_http

        lhs = await client.list_lakehouses()
        assert len(lhs) == 1

    @pytest.mark.asyncio
    async def test_create_pipeline(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"id": "pipe-1", "displayName": "test-pipe"})
        )
        client._client = mock_http

        result = await client.create_pipeline("test-pipe", {"activities": []})
        assert result["id"] == "pipe-1"

    @pytest.mark.asyncio
    async def test_create_notebook(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"id": "nb-1"})
        )
        client._client = mock_http

        result = await client.create_notebook("test-nb", "print('hello')")
        assert result["id"] == "nb-1"

    @pytest.mark.asyncio
    async def test_execute_sql_placeholder(self):
        from unittest.mock import patch
        client = self._make_client()
        with patch.dict("sys.modules", {"pyodbc": None}):
            result = await client.execute_sql("endpoint", "CREATE TABLE t (id INT)")
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_close(self):
        client = self._make_client()
        mock_http = AsyncMock()
        mock_http.is_closed = False
        client._client = mock_http
        await client.close()
        mock_http.aclose.assert_called_once()


class TestFabricClientListTables:
    @pytest.mark.asyncio
    async def test_list_tables(self):
        client = FabricClient(workspace_id="ws-123", access_token="tok")
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"value": [{"name": "t1"}, {"name": "t2"}]})
        )
        client._client = mock_http

        tables = await client.list_tables("lh-1")
        assert len(tables) == 2
