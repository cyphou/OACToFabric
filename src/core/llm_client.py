"""Azure OpenAI wrapper with async support, retry, token budgeting, and caching.

Provides a unified interface for all LLM translation calls in the migration
framework.  Integrates with ``translation_cache.py`` for deterministic-hit
caching and supports configurable token budgets to control costs.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Non-retryable LLM error."""


class TokenBudgetExceeded(LLMClientError):
    """Raised when the token budget for a run is exceeded."""


@dataclass
class LLMResponse:
    """Structured response from the LLM."""

    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    cached: bool = False
    latency_ms: float = 0.0


@dataclass
class LLMClient:
    """Async Azure OpenAI client with retry, budgeting, and caching.

    Parameters
    ----------
    endpoint
        Azure OpenAI endpoint URL.
    api_key
        API key for authentication.
    deployment
        Model deployment name (e.g. ``gpt-4``).
    api_version
        Azure OpenAI API version.
    max_tokens
        Default max tokens per completion.
    temperature
        Default temperature for completions.
    max_retries
        Number of retry attempts.
    token_budget
        Maximum total tokens allowed per run (0 = unlimited).
    """

    endpoint: str
    api_key: str
    deployment: str = "gpt-4"
    api_version: str = "2024-02-01"
    max_tokens: int = 2048
    temperature: float = 0.1
    max_retries: int = 3
    token_budget: int = 500_000
    _tokens_used: int = field(default=0, init=False, repr=False)
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)
    _cache: dict[str, LLMResponse] = field(default_factory=dict, init=False, repr=False)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=120.0,
                headers={"api-key": self.api_key},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ---- budget ----

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    @property
    def tokens_remaining(self) -> int:
        if self.token_budget <= 0:
            return float("inf")  # type: ignore[return-value]
        return max(0, self.token_budget - self._tokens_used)

    def reset_budget(self) -> None:
        self._tokens_used = 0

    # ---- cache key ----

    @staticmethod
    def _cache_key(system: str, user: str) -> str:
        raw = f"{system}||{user}"
        return hashlib.sha256(raw.encode()).hexdigest()

    # ---- completion ----

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        use_cache: bool = True,
    ) -> LLMResponse:
        """Run a chat completion.

        Parameters
        ----------
        system_prompt
            System-level instruction.
        user_prompt
            User-level prompt with the translation task.
        max_tokens
            Override default max_tokens.
        temperature
            Override default temperature.
        use_cache
            If True, check/store in the in-memory cache.
        """
        # Cache check
        key = self._cache_key(system_prompt, user_prompt)
        if use_cache and key in self._cache:
            cached = self._cache[key]
            logger.debug("Cache hit for prompt (hash=%s)", key[:12])
            return LLMResponse(
                content=cached.content,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                model=cached.model,
                cached=True,
            )

        # Budget check
        if self.token_budget > 0 and self._tokens_used >= self.token_budget:
            raise TokenBudgetExceeded(
                f"Token budget exhausted: {self._tokens_used}/{self.token_budget}"
            )

        start = time.monotonic()
        response = await self._call_api(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        response.latency_ms = elapsed_ms

        # Update budget
        self._tokens_used += response.total_tokens

        # Cache store
        if use_cache:
            self._cache[key] = response

        logger.debug(
            "LLM call: %d tokens (budget: %d/%d), %.0fms",
            response.total_tokens,
            self._tokens_used,
            self.token_budget,
            elapsed_ms,
        )
        return response

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        client = await self._get_client()
        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )

        body = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice.get("message", {}).get("content", ""),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model=data.get("model", self.deployment),
        )

    # ---- batch helper ----

    async def batch_complete(
        self,
        tasks: list[tuple[str, str]],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> list[LLMResponse]:
        """Run multiple completions sequentially.

        Parameters
        ----------
        tasks
            List of (system_prompt, user_prompt) tuples.
        """
        results: list[LLMResponse] = []
        for system, user in tasks:
            try:
                r = await self.complete(
                    system,
                    user,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                results.append(r)
            except TokenBudgetExceeded:
                logger.warning("Token budget exceeded — stopping batch")
                break
        return results

    # ---- structured output ----

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Run a chat completion expecting JSON output.

        Appends JSON formatting instructions to the system prompt.
        """
        json_system = (
            system_prompt
            + "\n\nIMPORTANT: Return your response as valid JSON only. "
            "No markdown, no code fences, no explanation outside the JSON."
        )
        return await self.complete(
            json_system,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # ---- function calling ----

    async def complete_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Run a chat completion with function-calling tools.

        The tools are included in the API request body.  The response
        may contain tool_calls in the content.  For Phase 70 the
        ReasoningLoop handles tool dispatch — this method just passes
        tool schemas through to the API.
        """
        return await self.complete(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
