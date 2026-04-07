"""Deployment Manifest — dependency-ordered artifact manifest for Fabric deployment.

Extends the existing ``DeploymentManifest`` from ``fabric_dry_run.py`` with
dependency resolution, topological ordering, and deployment-plan serialization.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ManifestArtifactType(str, Enum):
    LAKEHOUSE_TABLE = "lakehouse_table"
    SEMANTIC_MODEL = "semantic_model"
    REPORT = "report"
    PIPELINE = "pipeline"
    NOTEBOOK = "notebook"
    DATAFLOW = "dataflow"
    RLS_ROLE = "rls_role"
    OLS_RULE = "ols_rule"


class ManifestAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SKIP = "SKIP"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ManifestEntry:
    """One artifact in the deployment manifest."""

    artifact_type: ManifestArtifactType
    artifact_name: str
    action: ManifestAction = ManifestAction.CREATE
    source_path: str = ""
    dependencies: list[str] = field(default_factory=list)
    checksum: str = ""
    estimated_size_kb: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.artifact_type.value}::{self.artifact_name}"

    @property
    def valid(self) -> bool:
        return len(self.validation_errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": self.artifact_type.value,
            "artifact_name": self.artifact_name,
            "action": self.action.value,
            "source_path": self.source_path,
            "dependencies": self.dependencies,
            "checksum": self.checksum,
            "estimated_size_kb": self.estimated_size_kb,
            "metadata": self.metadata,
            "validation_errors": self.validation_errors,
            "valid": self.valid,
        }


@dataclass
class DeploymentPlan:
    """A fully resolved, ordered plan derived from a manifest."""

    workspace_id: str = ""
    entries: list[ManifestEntry] = field(default_factory=list)
    deployment_order: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def artifact_count(self) -> int:
        return len(self.entries)

    @property
    def valid_count(self) -> int:
        return sum(1 for e in self.entries if e.valid)

    @property
    def invalid_count(self) -> int:
        return self.artifact_count - self.valid_count

    @property
    def has_blockers(self) -> bool:
        return len(self.blockers) > 0

    @property
    def deployable(self) -> bool:
        return not self.has_blockers and self.invalid_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "artifact_count": self.artifact_count,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "deployment_order": self.deployment_order,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "entries": [e.to_dict() for e in self.entries],
            "generated_at": self.generated_at.isoformat(),
        }

    def summary(self) -> str:
        status = "READY" if self.deployable else "BLOCKED"
        lines = [
            f"Deployment Plan [{status}]",
            f"  Artifacts: {self.artifact_count} ({self.valid_count} valid, {self.invalid_count} invalid)",
            f"  Blockers:  {len(self.blockers)}",
            f"  Warnings:  {len(self.warnings)}",
        ]
        if self.deployment_order:
            lines.append(f"  Order: {' → '.join(self.deployment_order[:10])}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------


class ManifestBuilder:
    """Build and resolve a ``DeploymentPlan`` from individual entries."""

    def __init__(self, workspace_id: str = "") -> None:
        self._workspace_id = workspace_id
        self._entries: dict[str, ManifestEntry] = {}

    # ------------------------------------------------------------------
    # Add entries
    # ------------------------------------------------------------------

    def add(self, entry: ManifestEntry) -> ManifestBuilder:
        self._entries[entry.key] = entry
        return self

    def add_table(self, name: str, **kwargs: Any) -> ManifestBuilder:
        return self.add(ManifestEntry(
            artifact_type=ManifestArtifactType.LAKEHOUSE_TABLE,
            artifact_name=name,
            **kwargs,
        ))

    def add_semantic_model(self, name: str, **kwargs: Any) -> ManifestBuilder:
        return self.add(ManifestEntry(
            artifact_type=ManifestArtifactType.SEMANTIC_MODEL,
            artifact_name=name,
            **kwargs,
        ))

    def add_report(self, name: str, **kwargs: Any) -> ManifestBuilder:
        return self.add(ManifestEntry(
            artifact_type=ManifestArtifactType.REPORT,
            artifact_name=name,
            **kwargs,
        ))

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Topological sort
    # ------------------------------------------------------------------

    def _topological_order(self) -> tuple[list[str], list[str]]:
        """Return (ordered keys, cycle warnings)."""
        in_degree: dict[str, int] = defaultdict(int)
        graph: dict[str, list[str]] = defaultdict(list)
        all_keys = set(self._entries.keys())

        for key, entry in self._entries.items():
            in_degree.setdefault(key, 0)
            for dep in entry.dependencies:
                if dep in all_keys:
                    graph[dep].append(key)
                    in_degree[key] += 1

        queue: deque[str] = deque(k for k in all_keys if in_degree[k] == 0)
        ordered: list[str] = []
        while queue:
            node = queue.popleft()
            ordered.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        cycles: list[str] = []
        if len(ordered) < len(all_keys):
            remaining = all_keys - set(ordered)
            cycles.append(f"Circular dependency among: {', '.join(sorted(remaining))}")

        return ordered, cycles

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> DeploymentPlan:
        """Resolve dependencies and produce a ``DeploymentPlan``."""
        warnings: list[str] = []
        blockers: list[str] = []

        # Validate dependency references
        all_keys = set(self._entries.keys())
        for key, entry in self._entries.items():
            for dep in entry.dependencies:
                if dep not in all_keys:
                    warnings.append(f"{key} depends on unknown artifact '{dep}'")

        ordered, cycles = self._topological_order()
        blockers.extend(cycles)

        plan = DeploymentPlan(
            workspace_id=self._workspace_id,
            entries=list(self._entries.values()),
            deployment_order=ordered,
            blockers=blockers,
            warnings=warnings,
        )
        logger.info("Manifest built: %d artifacts, %d blockers", plan.artifact_count, len(blockers))
        return plan

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        plan = self.build()
        return json.dumps(plan.to_dict(), indent=2, default=str)
