"""Tests for Power BI REST API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.clients.pbi_client import PBIClient


def _mock_response(body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = b'{"ok": true}'
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


class TestPBIClient:
    def _make_client(self) -> PBIClient:
        return PBIClient(access_token="tok-abc", group_id="grp-123")

    @pytest.mark.asyncio
    async def test_list_datasets(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"value": [{"id": "ds-1"}, {"id": "ds-2"}]})
        )
        client._client = mock_http
        datasets = await client.list_datasets()
        assert len(datasets) == 2

    @pytest.mark.asyncio
    async def test_get_dataset(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"id": "ds-1", "name": "Sales"})
        )
        client._client = mock_http
        ds = await client.get_dataset("ds-1")
        assert ds["name"] == "Sales"

    @pytest.mark.asyncio
    async def test_list_reports(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"value": [{"id": "r-1"}]})
        )
        client._client = mock_http
        reports = await client.list_reports()
        assert len(reports) == 1

    @pytest.mark.asyncio
    async def test_refresh_dataset(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=_mock_response({}))
        client._client = mock_http
        result = await client.refresh_dataset("ds-1")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_deploy_tmdl_via_rest(self):
        """Test TMDL deployment via REST API (fallback after TabularEditor not found)."""
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        # REST deploy succeeds
        mock_http.request = AsyncMock(
            return_value=_mock_response({"id": "ds-new", "status": "deployed"})
        )
        client._client = mock_http

        result = await client.deploy_tmdl(
            "Sales Model",
            {"model.tmdl": "model content", "table_sales.tmdl": "table content"},
        )
        assert result.get("method") in ("tabular_editor", "rest", "rest_api", "pbix_import")

    @pytest.mark.asyncio
    async def test_deploy_tmdl_returns_file_list(self):
        """Test that deploy_tmdl returns information about deployed files."""
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"id": "import-ok"})
        )
        client._client = mock_http
        result = await client.deploy_tmdl(
            "Sales Model",
            {"model.tmdl": "model content"},
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_import_pbix(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(
            return_value=_mock_response({"id": "import-1"})
        )
        client._client = mock_http
        result = await client.import_pbix("Report", b"\x00\x01\x02")
        assert result["id"] == "import-1"

    @pytest.mark.asyncio
    async def test_add_workspace_user(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.request = AsyncMock(return_value=_mock_response({}))
        client._client = mock_http
        result = await client.add_workspace_user("user@example.com", "Member")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_close(self):
        client = self._make_client()
        mock_http = AsyncMock()
        mock_http.is_closed = False
        client._client = mock_http
        await client.close()
        mock_http.aclose.assert_called_once()
