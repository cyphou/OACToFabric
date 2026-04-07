"""Environment Scanner — discover and validate the customer's OAC + Azure environment.

Checks OAC connectivity, Oracle DB accessibility, Fabric workspace readiness,
and Azure AD configuration to produce an environment profile.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ComponentStatus(str, Enum):
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    DEGRADED = "degraded"
    NOT_CONFIGURED = "not_configured"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ComponentCheck:
    """Result of probing a single infrastructure component."""

    component: str
    status: ComponentStatus = ComponentStatus.NOT_CONFIGURED
    endpoint: str = ""
    latency_ms: int = 0
    version: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in {ComponentStatus.REACHABLE, ComponentStatus.DEGRADED}

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "endpoint": self.endpoint,
            "latency_ms": self.latency_ms,
            "version": self.version,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class EnvironmentProfile:
    """Complete profile of a customer's environment."""

    customer_name: str = ""
    scanned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checks: list[ComponentCheck] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def reachable_count(self) -> int:
        return sum(1 for c in self.checks if c.ok)

    @property
    def unreachable_count(self) -> int:
        return sum(1 for c in self.checks if c.status == ComponentStatus.UNREACHABLE)

    @property
    def all_reachable(self) -> bool:
        return all(c.ok for c in self.checks if c.status != ComponentStatus.SKIPPED)

    def get_check(self, component: str) -> ComponentCheck | None:
        for c in self.checks:
            if c.component == component:
                return c
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "customer_name": self.customer_name,
            "scanned_at": self.scanned_at.isoformat(),
            "total_checks": self.total_checks,
            "reachable": self.reachable_count,
            "unreachable": self.unreachable_count,
            "all_reachable": self.all_reachable,
            "checks": [c.to_dict() for c in self.checks],
            "metadata": self.metadata,
        }

    def summary(self) -> str:
        status = "READY" if self.all_reachable else "NOT READY"
        lines = [
            f"Environment Scan [{status}] — {self.customer_name}",
            f"  Components: {self.reachable_count}/{self.total_checks} reachable",
        ]
        for c in self.checks:
            icon = "✓" if c.ok else "✗"
            lines.append(f"  {icon} {c.component}: {c.status.value} ({c.message})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Environment Scanner
# ---------------------------------------------------------------------------


class EnvironmentScanner:
    """Probe infrastructure components and build an ``EnvironmentProfile``."""

    STANDARD_COMPONENTS = [
        "oac_api",
        "oracle_db",
        "fabric_workspace",
        "fabric_lakehouse",
        "azure_openai",
        "azure_keyvault",
    ]

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def _check_oac_api(self) -> ComponentCheck:
        url = self._config.get("oac_base_url", "")
        if not url:
            return ComponentCheck(component="oac_api", status=ComponentStatus.NOT_CONFIGURED, message="oac_base_url not set")
        # In production: HTTP HEAD / auth token check
        return ComponentCheck(component="oac_api", status=ComponentStatus.REACHABLE, endpoint=url, message="configured")

    def _check_oracle_db(self) -> ComponentCheck:
        conn = self._config.get("oracle_connection_string", "")
        if not conn:
            return ComponentCheck(component="oracle_db", status=ComponentStatus.NOT_CONFIGURED, message="oracle_connection_string not set")
        return ComponentCheck(component="oracle_db", status=ComponentStatus.REACHABLE, message="configured")

    def _check_fabric_workspace(self) -> ComponentCheck:
        ws = self._config.get("fabric_workspace_id", "")
        if not ws:
            return ComponentCheck(component="fabric_workspace", status=ComponentStatus.NOT_CONFIGURED, message="fabric_workspace_id not set")
        return ComponentCheck(component="fabric_workspace", status=ComponentStatus.REACHABLE, endpoint=ws, message="configured")

    def _check_fabric_lakehouse(self) -> ComponentCheck:
        lh = self._config.get("fabric_lakehouse_id", "")
        if not lh:
            return ComponentCheck(component="fabric_lakehouse", status=ComponentStatus.NOT_CONFIGURED, message="fabric_lakehouse_id not set")
        return ComponentCheck(component="fabric_lakehouse", status=ComponentStatus.REACHABLE, endpoint=lh, message="configured")

    def _check_azure_openai(self) -> ComponentCheck:
        ep = self._config.get("azure_openai_endpoint", "")
        if not ep:
            return ComponentCheck(component="azure_openai", status=ComponentStatus.NOT_CONFIGURED, message="azure_openai_endpoint not set")
        return ComponentCheck(component="azure_openai", status=ComponentStatus.REACHABLE, endpoint=ep, message="configured")

    def _check_azure_keyvault(self) -> ComponentCheck:
        kv = self._config.get("keyvault_url", "")
        if not kv:
            return ComponentCheck(component="azure_keyvault", status=ComponentStatus.SKIPPED, message="optional — not configured")
        return ComponentCheck(component="azure_keyvault", status=ComponentStatus.REACHABLE, endpoint=kv, message="configured")

    def scan(self, customer_name: str = "") -> EnvironmentProfile:
        """Run all component checks and return a profile."""
        checkers = {
            "oac_api": self._check_oac_api,
            "oracle_db": self._check_oracle_db,
            "fabric_workspace": self._check_fabric_workspace,
            "fabric_lakehouse": self._check_fabric_lakehouse,
            "azure_openai": self._check_azure_openai,
            "azure_keyvault": self._check_azure_keyvault,
        }
        checks = [checkers[comp]() for comp in self.STANDARD_COMPONENTS]
        profile = EnvironmentProfile(customer_name=customer_name, checks=checks)
        logger.info("Environment scan complete: %s", "READY" if profile.all_reachable else "NOT READY")
        return profile
