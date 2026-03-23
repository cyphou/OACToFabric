"""Tests for Azure OpenAI LLM client."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.core.llm_client import LLMClient, LLMResponse, TokenBudgetExceeded


def _mock_response(body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


class TestLLMResponse:
    def test_basic_fields(self):
        r = LLMResponse(content="SUM(x)", prompt_tokens=10, completion_tokens=5, total_tokens=15)
        assert r.content == "SUM(x)"
        assert r.total_tokens == 15
        assert r.cached is False


class TestLLMClient:
    def _make_client(self, budget: int = 100_000) -> LLMClient:
        return LLMClient(
            endpoint="https://test.openai.azure.com",
            api_key="key-123",
            deployment="gpt-4",
            token_budget=budget,
        )

    def test_cache_key_deterministic(self):
        k1 = LLMClient._cache_key("sys", "user")
        k2 = LLMClient._cache_key("sys", "user")
        assert k1 == k2

    def test_cache_key_differs(self):
        k1 = LLMClient._cache_key("sys", "user1")
        k2 = LLMClient._cache_key("sys", "user2")
        assert k1 != k2

    def test_tokens_remaining_unlimited(self):
        client = self._make_client(budget=0)
        assert client.tokens_remaining == float("inf")

    def test_tokens_remaining_with_budget(self):
        client = self._make_client(budget=1000)
        assert client.tokens_remaining == 1000

    def test_reset_budget(self):
        client = self._make_client(budget=1000)
        client._tokens_used = 500
        client.reset_budget()
        assert client.tokens_used == 0

    @pytest.mark.asyncio
    async def test_complete_calls_api(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.post = AsyncMock(
            return_value=_mock_response({
                "choices": [{"message": {"content": "SUM(Sales[Amount])"}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
                "model": "gpt-4",
            })
        )
        client._client = mock_http

        result = await client.complete("system", "translate SUM(revenue)")
        assert result.content == "SUM(Sales[Amount])"
        assert result.total_tokens == 60
        assert client.tokens_used == 60

    @pytest.mark.asyncio
    async def test_complete_uses_cache(self):
        client = self._make_client()
        # Pre-fill cache
        key = client._cache_key("sys", "user")
        client._cache[key] = LLMResponse(content="cached_result", model="gpt-4")

        result = await client.complete("sys", "user")
        assert result.content == "cached_result"
        assert result.cached is True
        assert result.total_tokens == 0  # No API call

    @pytest.mark.asyncio
    async def test_budget_exceeded_raises(self):
        client = self._make_client(budget=100)
        client._tokens_used = 100

        with pytest.raises(TokenBudgetExceeded):
            await client.complete("sys", "user", use_cache=False)

    @pytest.mark.asyncio
    async def test_batch_complete(self):
        client = self._make_client()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.post = AsyncMock(
            return_value=_mock_response({
                "choices": [{"message": {"content": "result"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                "model": "gpt-4",
            })
        )
        client._client = mock_http

        results = await client.batch_complete([("sys", "u1"), ("sys", "u2")])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_batch_stops_on_budget(self):
        client = self._make_client(budget=20)
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        mock_http.post = AsyncMock(
            return_value=_mock_response({
                "choices": [{"message": {"content": "r"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                "model": "gpt-4",
            })
        )
        client._client = mock_http

        results = await client.batch_complete([("sys", f"u{i}") for i in range(5)])
        # Should stop after budget exhausted
        assert len(results) < 5

    @pytest.mark.asyncio
    async def test_close(self):
        client = self._make_client()
        mock_http = AsyncMock()
        mock_http.is_closed = False
        client._client = mock_http
        await client.close()
        mock_http.aclose.assert_called_once()
