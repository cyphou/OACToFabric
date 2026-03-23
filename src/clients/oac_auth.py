"""OAuth2 / IDCS authentication for Oracle Analytics Cloud.

Handles:
- Client-credentials grant via Oracle IDCS token endpoint.
- Token caching with automatic refresh before expiry.
- Retry on transient HTTP errors (429, 5xx).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class OACAuthError(Exception):
    """Raised when authentication with OAC / IDCS fails."""


@dataclass
class TokenInfo:
    """Cached access token."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: float = 0.0  # epoch seconds

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at - 30  # 30‑s safety margin


@dataclass
class OACAuth:
    """Manage OAuth2 client-credentials tokens for OAC.

    Parameters
    ----------
    token_url
        IDCS token endpoint, e.g.
        ``https://idcs-xxx.identity.oraclecloud.com/oauth2/v1/token``
    client_id
        OAuth2 client ID registered in IDCS.
    client_secret
        OAuth2 client secret.
    scope
        Token scope.  Defaults to the common OAC scope.
    max_retries
        Number of retry attempts on transient failures.
    """

    token_url: str
    client_id: str
    client_secret: str
    scope: str = "urn:opc:resource:consumer::all"
    max_retries: int = 3
    _token: TokenInfo | None = field(default=None, init=False, repr=False)
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    # ----- lifecycle -----

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ----- token management -----

    async def get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._token is None or self._token.is_expired:
            self._token = await self._request_token()
        return self._token.access_token

    async def get_headers(self) -> dict[str, str]:
        """Return HTTP headers with Authorization bearer token."""
        token = await self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request_token(self) -> TokenInfo:
        """Exchange client credentials for an access token."""
        client = await self._get_client()
        payload = {
            "grant_type": "client_credentials",
            "scope": self.scope,
        }
        logger.debug("Requesting token from %s", self.token_url)

        resp = await client.post(
            self.token_url,
            data=payload,
            auth=(self.client_id, self.client_secret),
        )
        resp.raise_for_status()

        body = resp.json()
        if "access_token" not in body:
            raise OACAuthError(f"Token response missing 'access_token': {body}")

        expires_in = body.get("expires_in", 3600)
        token = TokenInfo(
            access_token=body["access_token"],
            token_type=body.get("token_type", "Bearer"),
            expires_at=time.time() + expires_in,
        )
        logger.info("Obtained token (expires in %ds)", expires_in)
        return token

    def invalidate(self) -> None:
        """Force re-authentication on next call."""
        self._token = None
