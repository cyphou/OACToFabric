"""Idempotent Deployer — deploy Fabric/PBI artifacts with create-or-update semantics.

Every ``deploy_*`` method first checks whether the artifact already exists
(by name or ID).  If it does, the method updates; otherwise it creates.
This makes deployments safe to re-run without manual cleanup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data structures
# ---------------------------------------------------------------------------


class DeployAction(str, Enum):
    """Action taken by the idempotent deployer."""

    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class IdempotentResult:
    """Result of a single idempotent deployment operation."""

    artifact_type: str
    artifact_name: str
    action: DeployAction
    artifact_id: str = ""
    previous_version: int = 0
    new_version: int = 0
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        return self.action in {DeployAction.CREATED, DeployAction.UPDATED, DeployAction.SKIPPED}

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": self.artifact_type,
            "artifact_name": self.artifact_name,
            "action": self.action.value,
            "artifact_id": self.artifact_id,
            "previous_version": self.previous_version,
            "new_version": self.new_version,
            "error": self.error,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ArtifactState:
    """Cached state of a deployed artifact for version tracking."""

    artifact_id: str
    artifact_name: str
    artifact_type: str
    version: int = 1
    checksum: str = ""
    last_deployed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Idempotent deployer
# ---------------------------------------------------------------------------


@dataclass
class IdempotentDeployer:
    """Wrap any deployer to provide idempotent create-or-update semantics.

    Parameters
    ----------
    workspace_id
        Fabric workspace to deploy into.
    dry_run
        If *True*, log intended actions without executing.
    """

    workspace_id: str
    dry_run: bool = False
    _registry: dict[str, ArtifactState] = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------
    # Registry helpers
    # ------------------------------------------------------------------

    def _key(self, artifact_type: str, name: str) -> str:
        return f"{artifact_type}::{name}"

    def register(self, state: ArtifactState) -> None:
        """Pre-register an existing artifact (e.g. discovered during startup)."""
        key = self._key(state.artifact_type, state.artifact_name)
        self._registry[key] = state

    def lookup(self, artifact_type: str, name: str) -> ArtifactState | None:
        return self._registry.get(self._key(artifact_type, name))

    @property
    def registered_count(self) -> int:
        return len(self._registry)

    # ------------------------------------------------------------------
    # Core deploy logic
    # ------------------------------------------------------------------

    async def deploy(
        self,
        artifact_type: str,
        artifact_name: str,
        definition: dict[str, Any],
        *,
        checksum: str = "",
        force: bool = False,
    ) -> IdempotentResult:
        """Create or update an artifact.

        If the artifact exists with the same checksum and *force* is False
        the deployment is skipped (no-op).
        """
        key = self._key(artifact_type, artifact_name)
        existing = self._registry.get(key)

        # Skip if identical
        if existing and existing.checksum == checksum and checksum and not force:
            logger.info(
                "SKIP %s/%s — checksum unchanged (v%d)",
                artifact_type,
                artifact_name,
                existing.version,
            )
            return IdempotentResult(
                artifact_type=artifact_type,
                artifact_name=artifact_name,
                action=DeployAction.SKIPPED,
                artifact_id=existing.artifact_id,
                previous_version=existing.version,
                new_version=existing.version,
            )

        action = DeployAction.UPDATED if existing else DeployAction.CREATED
        prev_version = existing.version if existing else 0
        new_version = prev_version + 1

        if self.dry_run:
            logger.info(
                "DRY-RUN %s %s/%s (v%d → v%d)",
                action.value,
                artifact_type,
                artifact_name,
                prev_version,
                new_version,
            )
            return IdempotentResult(
                artifact_type=artifact_type,
                artifact_name=artifact_name,
                action=action,
                previous_version=prev_version,
                new_version=new_version,
                details={"dry_run": True, "definition_keys": list(definition.keys())},
            )

        try:
            # In production, call the appropriate Fabric/PBI REST API here.
            # For now we simulate success and update the registry.
            artifact_id = existing.artifact_id if existing else f"{artifact_type}-{artifact_name}"
            self._registry[key] = ArtifactState(
                artifact_id=artifact_id,
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                version=new_version,
                checksum=checksum,
            )
            logger.info(
                "%s %s/%s → v%d",
                action.value.upper(),
                artifact_type,
                artifact_name,
                new_version,
            )
            return IdempotentResult(
                artifact_type=artifact_type,
                artifact_name=artifact_name,
                action=action,
                artifact_id=artifact_id,
                previous_version=prev_version,
                new_version=new_version,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("FAILED %s %s/%s: %s", action.value, artifact_type, artifact_name, exc)
            return IdempotentResult(
                artifact_type=artifact_type,
                artifact_name=artifact_name,
                action=DeployAction.FAILED,
                previous_version=prev_version,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------

    async def deploy_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[IdempotentResult]:
        """Deploy a list of ``{"type", "name", "definition", "checksum?"}`` dicts."""
        results: list[IdempotentResult] = []
        for item in items:
            r = await self.deploy(
                artifact_type=item["type"],
                artifact_name=item["name"],
                definition=item.get("definition", {}),
                checksum=item.get("checksum", ""),
                force=item.get("force", False),
            )
            results.append(r)
        return results

    def summary(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "dry_run": self.dry_run,
            "registered_artifacts": self.registered_count,
        }
