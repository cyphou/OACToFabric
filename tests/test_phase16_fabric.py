"""Phase 16 tests — FabricClient.execute_sql() with pyodbc implementation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clients.fabric_client import FabricClient


class TestFabricClientExecuteSQL:
    """Tests for the real execute_sql implementation."""

    def _make_client(self) -> FabricClient:
        return FabricClient(workspace_id="ws-123", access_token="tok-abc")

    @pytest.mark.asyncio
    async def test_execute_sql_rest_fallback(self):
        """When pyodbc is not available, should fall back to REST."""
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=MagicMock(return_value={"results": [{"status": "ok"}]}),
                raise_for_status=MagicMock(),
            )
        )
        client._client = mock_http

        # Patch pyodbc as unavailable
        with patch.dict("sys.modules", {"pyodbc": None}):
            result = await client.execute_sql(
                "test.datawarehouse.fabric.microsoft.com",
                "CREATE TABLE test (id INT)",
            )
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_sql_accepts_endpoint(self):
        """execute_sql should accept sql_endpoint parameter."""
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=MagicMock(return_value={"results": []}),
                raise_for_status=MagicMock(),
            )
        )
        client._client = mock_http
        result = await client.execute_sql(
            "myendpoint.datawarehouse.fabric.microsoft.com",
            "SELECT 1",
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_create_pipeline(self):
        """Test create_pipeline API call."""
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=MagicMock(
                status_code=201,
                json=MagicMock(return_value={"id": "pipe-1", "status": "created"}),
                raise_for_status=MagicMock(),
            )
        )
        client._client = mock_http
        result = await client.create_pipeline("test_pipeline", {"activities": []})
        assert result["id"] == "pipe-1"

    @pytest.mark.asyncio
    async def test_create_notebook(self):
        """Test create_notebook API call."""
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=MagicMock(
                status_code=201,
                json=MagicMock(return_value={"id": "nb-1"}),
                raise_for_status=MagicMock(),
            )
        )
        client._client = mock_http
        result = await client.create_notebook("test_notebook", "print('hello')")
        assert result["id"] == "nb-1"


class TestFabricClientInit:
    """Test FabricClient initialization."""

    def test_default_init(self):
        client = FabricClient(workspace_id="ws-1", access_token="tok")
        assert client.workspace_id == "ws-1"

    def test_custom_api_base(self):
        client = FabricClient(
            workspace_id="ws-1",
            access_token="tok",
            api_base="https://custom.api.com/v2",
        )
        assert "custom.api.com" in client.api_base
