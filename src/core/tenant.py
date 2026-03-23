"""Multi-tenant context and isolation.

Provides:
- ``Tenant`` — tenant identity model.
- ``TenantContext`` — async context variable for current tenant.
- ``TenantStore`` — in-memory tenant registry with CRUD.
- ``TenantScoped`` — mixin that tags objects with a tenant ID.
"""

from __future__ import annotations

import contextvars
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tenant model
# ---------------------------------------------------------------------------


class TenantTier(str, Enum):
    """Service tier for a tenant."""

    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class Tenant:
    """A tenant in the multi-tenant platform."""

    tenant_id: str
    name: str
    tier: TenantTier = TenantTier.STANDARD
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    workspace_id: str = ""  # Fabric workspace assigned to this tenant
    max_concurrent_migrations: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "tier": self.tier.value,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "workspace_id": self.workspace_id,
            "max_concurrent_migrations": self.max_concurrent_migrations,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Tenant context — async context variable
# ---------------------------------------------------------------------------

_current_tenant: contextvars.ContextVar[Optional[Tenant]] = contextvars.ContextVar(
    "current_tenant", default=None,
)


class TenantContext:
    """Manage the current tenant for the async context.

    Usage::

        TenantContext.set(tenant)
        current = TenantContext.get()
        TenantContext.clear()

    Or as a context manager::

        with TenantContext.scope(tenant):
            ...  # tenant active here
    """

    @staticmethod
    def set(tenant: Tenant) -> contextvars.Token:
        return _current_tenant.set(tenant)

    @staticmethod
    def get() -> Tenant | None:
        return _current_tenant.get()

    @staticmethod
    def require() -> Tenant:
        """Get the current tenant or raise."""
        t = _current_tenant.get()
        if t is None:
            raise RuntimeError("No tenant set in context")
        return t

    @staticmethod
    def clear() -> None:
        _current_tenant.set(None)

    class scope:
        """Context manager that sets and then clears the tenant."""

        def __init__(self, tenant: Tenant) -> None:
            self._tenant = tenant
            self._token: contextvars.Token | None = None

        def __enter__(self) -> Tenant:
            self._token = _current_tenant.set(self._tenant)
            return self._tenant

        def __exit__(self, *args: Any) -> None:
            if self._token is not None:
                _current_tenant.reset(self._token)


# ---------------------------------------------------------------------------
# Tenant store — in-memory registry
# ---------------------------------------------------------------------------


class TenantStore:
    """In-memory tenant registry with CRUD operations."""

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}

    def create(
        self,
        name: str,
        tier: TenantTier = TenantTier.STANDARD,
        workspace_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        tenant_id = uuid.uuid4().hex[:12]
        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            tier=tier,
            workspace_id=workspace_id,
            metadata=metadata or {},
        )
        self._tenants[tenant_id] = tenant
        logger.info("Tenant created: %s (%s)", name, tenant_id)
        return tenant

    def get(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def get_by_name(self, name: str) -> Tenant | None:
        for t in self._tenants.values():
            if t.name == name:
                return t
        return None

    def list_all(self) -> list[Tenant]:
        return list(self._tenants.values())

    def update(self, tenant_id: str, **fields: Any) -> Tenant | None:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        for k, v in fields.items():
            if hasattr(tenant, k):
                setattr(tenant, k, v)
        return tenant

    def delete(self, tenant_id: str) -> bool:
        return self._tenants.pop(tenant_id, None) is not None

    def disable(self, tenant_id: str) -> bool:
        t = self._tenants.get(tenant_id)
        if t:
            t.enabled = False
            return True
        return False

    def enable(self, tenant_id: str) -> bool:
        t = self._tenants.get(tenant_id)
        if t:
            t.enabled = True
            return True
        return False

    @property
    def count(self) -> int:
        return len(self._tenants)

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._tenants.values() if t.enabled)


# ---------------------------------------------------------------------------
# Tenant-scoped mixin
# ---------------------------------------------------------------------------


class TenantScoped:
    """Mixin that tags an object with a tenant ID.

    Can be used as a base for tenant-scoped domain objects.
    """

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def belongs_to(self, tenant: Tenant) -> bool:
        return self._tenant_id == tenant.tenant_id
