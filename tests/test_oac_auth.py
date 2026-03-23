"""Tests for OAC OAuth2 authentication client."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from src.clients.oac_auth import OACAuth, OACAuthError, TokenInfo


# ---------------------------------------------------------------------------
# TokenInfo
# ---------------------------------------------------------------------------


class TestTokenInfo:
    def test_not_expired_when_fresh(self):
        info = TokenInfo(access_token="abc", expires_at=time.time() + 600)
        assert info.is_expired is False

    def test_expired_when_past(self):
        info = TokenInfo(access_token="abc", expires_at=time.time() - 10)
        assert info.is_expired is True

    def test_expired_within_safety_margin(self):
        info = TokenInfo(access_token="abc", expires_at=time.time() + 20)
        assert info.is_expired is True  # 30s safety margin


# ---------------------------------------------------------------------------
# OACAuth
# ---------------------------------------------------------------------------


class TestOACAuth:
    def _make_auth(self) -> OACAuth:
        return OACAuth(
            token_url="https://idcs.example.com/oauth2/v1/token",
            client_id="test-id",
            client_secret="test-secret",
        )

    @pytest.mark.asyncio
    async def test_get_token_requests_new(self):
        auth = self._make_auth()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "tok123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.is_closed = False
        mock_client.post = AsyncMock(return_value=mock_resp)
        auth._client = mock_client

        token = await auth.get_token()
        assert token == "tok123"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_uses_cache(self):
        auth = self._make_auth()
        auth._token = TokenInfo(
            access_token="cached",
            expires_at=time.time() + 600,
        )
        token = await auth.get_token()
        assert token == "cached"

    @pytest.mark.asyncio
    async def test_get_headers_includes_bearer(self):
        auth = self._make_auth()
        auth._token = TokenInfo(
            access_token="hdr_token",
            expires_at=time.time() + 600,
        )
        headers = await auth.get_headers()
        assert headers["Authorization"] == "Bearer hdr_token"
        assert "Content-Type" in headers

    def test_invalidate_clears_token(self):
        auth = self._make_auth()
        auth._token = TokenInfo(access_token="old", expires_at=time.time() + 600)
        auth.invalidate()
        assert auth._token is None

    @pytest.mark.asyncio
    async def test_close(self):
        auth = self._make_auth()
        mock_client = AsyncMock()
        mock_client.is_closed = False
        auth._client = mock_client
        await auth.close()
        mock_client.aclose.assert_called_once()
