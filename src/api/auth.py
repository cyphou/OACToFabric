"""Authentication and role-based access control.

Provides:
- ``PlatformRole`` — admin / operator / viewer roles.
- ``TokenClaims`` — decoded JWT claims.
- ``AuthConfig`` — authentication configuration.
- ``JWTValidator`` — validate JWTs against Azure AD / Entra ID.
- ``RBACEnforcer`` — role-based permission checks.
- ``APIKeyStore`` — API key authentication for programmatic access.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Roles and permissions
# ---------------------------------------------------------------------------


class PlatformRole(str, Enum):
    """Platform-level roles."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


# Permission matrix
ROLE_PERMISSIONS: dict[PlatformRole, frozenset[str]] = {
    PlatformRole.ADMIN: frozenset({
        "migration:create", "migration:read", "migration:cancel", "migration:delete",
        "migration:rollback",
        "tenant:create", "tenant:read", "tenant:update", "tenant:delete",
        "plugin:install", "plugin:remove", "plugin:list",
        "user:manage", "settings:manage",
    }),
    PlatformRole.OPERATOR: frozenset({
        "migration:create", "migration:read", "migration:cancel",
        "migration:rollback",
        "tenant:read",
        "plugin:list",
    }),
    PlatformRole.VIEWER: frozenset({
        "migration:read",
        "tenant:read",
        "plugin:list",
    }),
}


# ---------------------------------------------------------------------------
# Token claims
# ---------------------------------------------------------------------------


@dataclass
class TokenClaims:
    """Decoded JWT claims."""

    sub: str  # subject (user / service principal)
    tenant_id: str = ""
    roles: list[PlatformRole] = field(default_factory=list)
    email: str = ""
    name: str = ""
    issued_at: float = 0.0
    expires_at: float = 0.0

    @property
    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at

    @property
    def highest_role(self) -> PlatformRole:
        """Return the most privileged role."""
        priority = {PlatformRole.ADMIN: 0, PlatformRole.OPERATOR: 1, PlatformRole.VIEWER: 2}
        if not self.roles:
            return PlatformRole.VIEWER
        return min(self.roles, key=lambda r: priority.get(r, 99))

    @property
    def permissions(self) -> frozenset[str]:
        """Union of all permissions across roles."""
        perms: set[str] = set()
        for role in self.roles:
            perms |= ROLE_PERMISSIONS.get(role, frozenset())
        return frozenset(perms)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


# ---------------------------------------------------------------------------
# Auth config
# ---------------------------------------------------------------------------


@dataclass
class AuthConfig:
    """Authentication configuration."""

    enabled: bool = True
    issuer: str = ""  # e.g. "https://login.microsoftonline.com/{tenant}/v2.0"
    audience: str = ""  # e.g. "api://oac2fabric"
    tenant_id: str = ""  # Azure AD tenant
    client_id: str = ""
    require_https: bool = True
    token_expiry_seconds: int = 3600

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.enabled and not self.issuer:
            errors.append("issuer is required when auth is enabled")
        if self.enabled and not self.audience:
            errors.append("audience is required when auth is enabled")
        return errors


# ---------------------------------------------------------------------------
# JWT validator (mock-friendly)
# ---------------------------------------------------------------------------


class JWTValidator:
    """Validate JWT tokens.

    In production, this validates against Azure AD / Entra ID JWKS.
    For testing, a mock mode is provided that accepts any well-formed
    dict as claims.
    """

    def __init__(self, config: AuthConfig, *, mock_mode: bool = False) -> None:
        self._config = config
        self._mock_mode = mock_mode
        self._mock_claims: dict[str, TokenClaims] = {}

    def register_mock_token(self, token: str, claims: TokenClaims) -> None:
        """Register a mock token for testing."""
        if not self._mock_mode:
            raise RuntimeError("register_mock_token() requires mock_mode=True")
        self._mock_claims[token] = claims

    def validate(self, token: str) -> TokenClaims | None:
        """Validate a JWT token and return claims, or None if invalid."""
        if not self._config.enabled:
            # Auth disabled — return admin claims
            return TokenClaims(sub="anonymous", roles=[PlatformRole.ADMIN])

        if self._mock_mode:
            claims = self._mock_claims.get(token)
            if claims and not claims.is_expired:
                return claims
            return None

        # Real validation would use MSAL / PyJWT with JWKS
        logger.warning("Real JWT validation not implemented — rejecting token")
        return None


# ---------------------------------------------------------------------------
# RBAC enforcer
# ---------------------------------------------------------------------------


class RBACEnforcer:
    """Check role-based permissions."""

    def check(self, claims: TokenClaims, permission: str) -> bool:
        """Return True if the user has the required permission."""
        return claims.has_permission(permission)

    def require(self, claims: TokenClaims, permission: str) -> None:
        """Raise if the user lacks the required permission."""
        if not self.check(claims, permission):
            raise PermissionError(
                f"User '{claims.sub}' lacks permission '{permission}'. "
                f"Roles: {[r.value for r in claims.roles]}"
            )


# ---------------------------------------------------------------------------
# API key store
# ---------------------------------------------------------------------------


@dataclass
class APIKey:
    """A stored API key."""

    key_id: str
    key_hash: str  # SHA-256 of the actual key
    tenant_id: str
    name: str
    roles: list[PlatformRole] = field(default_factory=lambda: [PlatformRole.OPERATOR])
    created_at: float = field(default_factory=time.time)
    enabled: bool = True


class APIKeyStore:
    """API key management for programmatic access."""

    def __init__(self) -> None:
        self._keys: dict[str, APIKey] = {}  # key_id → APIKey

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def create_key(
        self,
        tenant_id: str,
        name: str,
        roles: list[PlatformRole] | None = None,
    ) -> tuple[str, APIKey]:
        """Create a new API key. Returns (raw_key, api_key_record).

        The raw key is returned only once — store it securely.
        """
        key_id = secrets.token_hex(8)
        raw_key = f"oac2f_{secrets.token_hex(24)}"
        api_key = APIKey(
            key_id=key_id,
            key_hash=self._hash_key(raw_key),
            tenant_id=tenant_id,
            name=name,
            roles=roles or [PlatformRole.OPERATOR],
        )
        self._keys[key_id] = api_key
        logger.info("API key created: %s (%s) for tenant %s", name, key_id, tenant_id)
        return raw_key, api_key

    def validate_key(self, raw_key: str) -> TokenClaims | None:
        """Validate a raw API key and return claims."""
        key_hash = self._hash_key(raw_key)
        for api_key in self._keys.values():
            if hmac.compare_digest(api_key.key_hash, key_hash) and api_key.enabled:
                return TokenClaims(
                    sub=f"apikey:{api_key.key_id}",
                    tenant_id=api_key.tenant_id,
                    roles=api_key.roles,
                    name=api_key.name,
                )
        return None

    def revoke(self, key_id: str) -> bool:
        api_key = self._keys.get(key_id)
        if api_key:
            api_key.enabled = False
            return True
        return False

    def delete(self, key_id: str) -> bool:
        return self._keys.pop(key_id, None) is not None

    def list_keys(self, tenant_id: str | None = None) -> list[APIKey]:
        keys = list(self._keys.values())
        if tenant_id:
            keys = [k for k in keys if k.tenant_id == tenant_id]
        return keys

    @property
    def count(self) -> int:
        return len(self._keys)
