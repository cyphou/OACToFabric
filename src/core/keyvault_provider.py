"""Azure Key Vault integration for secret management.

Provides:
- ``KeyVaultSecretProvider`` — retrieves secrets from Azure Key Vault,
  with optional caching and fallback to environment variables.
- ``ManagedIdentityAuth`` — helper for authenticating to Azure services
  using managed identity (zero-secret deployment).

When Key Vault is not available (e.g. local development), the provider
falls back to environment variables or a plain config dict.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Secret result
# ---------------------------------------------------------------------------


@dataclass
class SecretValue:
    """A retrieved secret with metadata."""

    name: str
    value: str
    source: str = "keyvault"  # "keyvault" | "env" | "config" | "cache"
    retrieved_at: float = field(default_factory=time.time)
    expires_at: float | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def __repr__(self) -> str:
        return f"SecretValue(name={self.name!r}, source={self.source!r}, redacted=True)"


# ---------------------------------------------------------------------------
# Key Vault Secret Provider
# ---------------------------------------------------------------------------


class KeyVaultSecretProvider:
    """Retrieve secrets from Azure Key Vault with caching and fallback.

    Parameters
    ----------
    vault_url : str
        The Key Vault URL, e.g. ``https://my-vault.vault.azure.net/``.
    cache_ttl_seconds : float
        How long to cache secrets in memory (default: 300 = 5 min).
    fallback_to_env : bool
        If ``True``, fall back to environment variables when Key Vault
        is unavailable.
    config_fallback : dict
        Optional dict of name → value pairs for local dev (lowest priority).
    credential
        Azure credential object (``DefaultAzureCredential``, etc.).
        If ``None``, will attempt to use ``DefaultAzureCredential``.
    """

    def __init__(
        self,
        vault_url: str = "",
        *,
        cache_ttl_seconds: float = 300.0,
        fallback_to_env: bool = True,
        config_fallback: dict[str, str] | None = None,
        credential: Any = None,
    ) -> None:
        self._vault_url = vault_url.rstrip("/")
        self._cache_ttl = cache_ttl_seconds
        self._fallback_to_env = fallback_to_env
        self._config_fallback = config_fallback or {}
        self._credential = credential
        self._cache: dict[str, SecretValue] = {}
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-init the Key Vault SecretClient."""
        if self._client is not None:
            return self._client
        try:
            from azure.keyvault.secrets import SecretClient

            if self._credential is None:
                from azure.identity import DefaultAzureCredential

                self._credential = DefaultAzureCredential()

            self._client = SecretClient(
                vault_url=self._vault_url,
                credential=self._credential,
            )
            return self._client
        except ImportError:
            logger.warning(
                "azure-keyvault-secrets or azure-identity not installed — "
                "Key Vault integration unavailable"
            )
            return None
        except Exception as exc:
            logger.warning("Failed to initialize Key Vault client: %s", exc)
            return None

    def get_secret(self, name: str) -> SecretValue:
        """Retrieve a secret by name.

        Resolution order:
        1. In-memory cache (if not expired)
        2. Azure Key Vault
        3. Environment variable (``name`` uppercased, hyphens → underscores)
        4. Config fallback dict

        Raises
        ------
        KeyError
            If the secret is not found in any source.
        """
        # 1. Cache check
        cached = self._cache.get(name)
        if cached and not cached.is_expired:
            logger.debug("Secret %r served from cache", name)
            return SecretValue(
                name=name,
                value=cached.value,
                source="cache",
                retrieved_at=cached.retrieved_at,
                expires_at=cached.expires_at,
            )

        # 2. Key Vault
        if self._vault_url:
            client = self._get_client()
            if client is not None:
                try:
                    kv_secret = client.get_secret(name)
                    secret = SecretValue(
                        name=name,
                        value=kv_secret.value,
                        source="keyvault",
                        expires_at=time.time() + self._cache_ttl,
                    )
                    self._cache[name] = secret
                    logger.info("Secret %r retrieved from Key Vault", name)
                    return secret
                except Exception as exc:
                    logger.warning(
                        "Key Vault lookup failed for %r: %s — trying fallbacks",
                        name,
                        exc,
                    )

        # 3. Environment variable
        if self._fallback_to_env:
            env_key = name.upper().replace("-", "_")
            env_val = os.environ.get(env_key)
            if env_val is not None:
                secret = SecretValue(
                    name=name,
                    value=env_val,
                    source="env",
                    expires_at=time.time() + self._cache_ttl,
                )
                self._cache[name] = secret
                logger.info("Secret %r retrieved from environment variable", name)
                return secret

        # 4. Config fallback
        if name in self._config_fallback:
            secret = SecretValue(
                name=name,
                value=self._config_fallback[name],
                source="config",
                expires_at=time.time() + self._cache_ttl,
            )
            self._cache[name] = secret
            logger.info("Secret %r retrieved from config fallback", name)
            return secret

        raise KeyError(f"Secret {name!r} not found in Key Vault, env, or config")

    def get_secret_value(self, name: str, default: str = "") -> str:
        """Convenience: return just the string value, with a default."""
        try:
            return self.get_secret(name).value
        except KeyError:
            return default

    def clear_cache(self) -> None:
        """Remove all cached secrets."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    @property
    def vault_url(self) -> str:
        return self._vault_url


# ---------------------------------------------------------------------------
# Managed Identity Auth helper
# ---------------------------------------------------------------------------


class ManagedIdentityAuth:
    """Helper for managed identity authentication to Azure services.

    Wraps ``DefaultAzureCredential`` with scoped token acquisition
    and caching.

    Parameters
    ----------
    client_id : str
        Optional user-assigned managed identity client ID.
        If empty, uses system-assigned identity.
    """

    def __init__(self, client_id: str = "") -> None:
        self._client_id = client_id
        self._credential: Any = None
        self._token_cache: dict[str, tuple[str, float]] = {}

    def _get_credential(self) -> Any:
        """Lazy-init the Azure credential."""
        if self._credential is not None:
            return self._credential
        try:
            from azure.identity import (
                DefaultAzureCredential,
                ManagedIdentityCredential,
            )

            if self._client_id:
                self._credential = ManagedIdentityCredential(
                    client_id=self._client_id
                )
            else:
                self._credential = DefaultAzureCredential()
            return self._credential
        except ImportError:
            raise ImportError(
                "azure-identity is required for managed identity authentication"
            )

    def get_token(self, scope: str) -> str:
        """Acquire a token for the given scope.

        Returns a cached token if it hasn't expired.
        """
        cached = self._token_cache.get(scope)
        if cached:
            token, expires_at = cached
            if time.time() < expires_at - 60:  # 60s buffer before expiry
                return token

        cred = self._get_credential()
        result = cred.get_token(scope)
        self._token_cache[scope] = (result.token, result.expires_on)
        return result.token

    def clear_cache(self) -> None:
        """Clear cached tokens."""
        self._token_cache.clear()
