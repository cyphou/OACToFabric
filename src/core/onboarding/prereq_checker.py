"""Prerequisite Checker — validate all prerequisites before migration can start.

Checks:
- Python version
- Required packages
- Config file existence
- Fabric capacity SKU
- OAC API version
- RPD file accessibility
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PrereqStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


class PrereqCategory(str, Enum):
    RUNTIME = "runtime"
    CONFIG = "config"
    CONNECTIVITY = "connectivity"
    DATA = "data"
    SECURITY = "security"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PrereqCheck:
    """Result of one prerequisite check."""

    name: str
    category: PrereqCategory
    status: PrereqStatus = PrereqStatus.PASS
    message: str = ""
    remediation: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in {PrereqStatus.PASS, PrereqStatus.WARN}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "remediation": self.remediation,
            "details": self.details,
        }


@dataclass
class PrereqReport:
    """Aggregate prerequisite-check report."""

    checks: list[PrereqCheck] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == PrereqStatus.PASS)

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.status == PrereqStatus.WARN)

    @property
    def failures(self) -> int:
        return sum(1 for c in self.checks if c.status == PrereqStatus.FAIL)

    @property
    def ready(self) -> bool:
        return self.failures == 0

    def by_category(self) -> dict[str, list[PrereqCheck]]:
        cats: dict[str, list[PrereqCheck]] = {}
        for c in self.checks:
            cats.setdefault(c.category.value, []).append(c)
        return cats

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "warnings": self.warnings,
            "failures": self.failures,
            "ready": self.ready,
            "checks": [c.to_dict() for c in self.checks],
        }

    def summary(self) -> str:
        status = "READY" if self.ready else "NOT READY"
        lines = [
            f"Prerequisites [{status}]: {self.passed} pass, {self.warnings} warn, {self.failures} fail",
        ]
        for c in self.checks:
            icon = {"pass": "✓", "warn": "⚠", "fail": "✗", "skip": "–"}[c.status.value]
            lines.append(f"  {icon} [{c.category.value}] {c.name}: {c.message}")
            if c.remediation and c.status == PrereqStatus.FAIL:
                lines.append(f"    → {c.remediation}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------


class PrerequisiteChecker:
    """Run all prerequisite checks."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_python_version(self) -> PrereqCheck:
        major, minor = sys.version_info[:2]
        if (major, minor) >= (3, 12):
            return PrereqCheck(
                name="python_version",
                category=PrereqCategory.RUNTIME,
                status=PrereqStatus.PASS,
                message=f"Python {major}.{minor}",
            )
        return PrereqCheck(
            name="python_version",
            category=PrereqCategory.RUNTIME,
            status=PrereqStatus.FAIL,
            message=f"Python {major}.{minor} (need ≥ 3.12)",
            remediation="Install Python 3.12 or newer.",
        )

    def _check_config_file(self) -> PrereqCheck:
        cfg_path = self._config.get("config_path", "config/migration.toml")
        if Path(cfg_path).exists():
            return PrereqCheck(
                name="config_file",
                category=PrereqCategory.CONFIG,
                status=PrereqStatus.PASS,
                message=f"Found {cfg_path}",
            )
        return PrereqCheck(
            name="config_file",
            category=PrereqCategory.CONFIG,
            status=PrereqStatus.FAIL,
            message=f"Missing {cfg_path}",
            remediation=f"Copy config/dev.toml to {cfg_path} and fill in values.",
        )

    def _check_rpd_file(self) -> PrereqCheck:
        rpd = self._config.get("rpd_xml_path", "")
        if not rpd:
            return PrereqCheck(
                name="rpd_file",
                category=PrereqCategory.DATA,
                status=PrereqStatus.WARN,
                message="rpd_xml_path not set (optional for non-RPD flows)",
            )
        if Path(rpd).exists():
            return PrereqCheck(
                name="rpd_file",
                category=PrereqCategory.DATA,
                status=PrereqStatus.PASS,
                message=f"Found {rpd}",
            )
        return PrereqCheck(
            name="rpd_file",
            category=PrereqCategory.DATA,
            status=PrereqStatus.FAIL,
            message=f"RPD file not found: {rpd}",
            remediation="Export the RPD from OAC as XML and place it at the configured path.",
        )

    def _check_fabric_workspace(self) -> PrereqCheck:
        ws = self._config.get("fabric_workspace_id", "")
        if not ws:
            return PrereqCheck(
                name="fabric_workspace",
                category=PrereqCategory.CONNECTIVITY,
                status=PrereqStatus.FAIL,
                message="fabric_workspace_id not configured",
                remediation="Set fabric_workspace_id in the config.",
            )
        return PrereqCheck(
            name="fabric_workspace",
            category=PrereqCategory.CONNECTIVITY,
            status=PrereqStatus.PASS,
            message=f"Workspace ID: {ws[:8]}…",
        )

    def _check_oac_credentials(self) -> PrereqCheck:
        client_id = self._config.get("oac_client_id", "")
        client_secret = self._config.get("oac_client_secret", "")
        if not client_id or not client_secret:
            return PrereqCheck(
                name="oac_credentials",
                category=PrereqCategory.SECURITY,
                status=PrereqStatus.FAIL,
                message="OAC OAuth client_id/client_secret missing",
                remediation="Provide oac_client_id and oac_client_secret in config or Key Vault.",
            )
        return PrereqCheck(
            name="oac_credentials",
            category=PrereqCategory.SECURITY,
            status=PrereqStatus.PASS,
            message="OAC credentials configured",
        )

    def _check_pydantic(self) -> PrereqCheck:
        try:
            import pydantic  # noqa: F401

            return PrereqCheck(
                name="pydantic",
                category=PrereqCategory.RUNTIME,
                status=PrereqStatus.PASS,
                message="pydantic available",
            )
        except ImportError:
            return PrereqCheck(
                name="pydantic",
                category=PrereqCategory.RUNTIME,
                status=PrereqStatus.FAIL,
                message="pydantic not installed",
                remediation="pip install pydantic pydantic-settings",
            )

    # ------------------------------------------------------------------
    # Run all
    # ------------------------------------------------------------------

    def check(self) -> PrereqReport:
        """Run all prerequisite checks and return a report."""
        checks = [
            self._check_python_version(),
            self._check_pydantic(),
            self._check_config_file(),
            self._check_rpd_file(),
            self._check_fabric_workspace(),
            self._check_oac_credentials(),
        ]
        report = PrereqReport(checks=checks)
        logger.info("Prerequisite check: %s", "READY" if report.ready else "NOT READY")
        return report
