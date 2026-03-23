"""Artifact versioning — content-addressable snapshots.

Provides:
- ``ArtifactType`` — categories of generated artifacts.
- ``ArtifactSnapshot`` — immutable versioned snapshot.
- ``ArtifactDiff`` — diff between two snapshots.
- ``ArtifactVersioner`` — version control for generated TMDL/PBIR/DDL.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Artifact types
# ---------------------------------------------------------------------------


class ArtifactType(str, Enum):
    """Categories of generated artifacts."""

    TMDL = "tmdl"
    PBIR = "pbir"
    DDL = "ddl"
    DAX_MEASURE = "dax_measure"
    PIPELINE_JSON = "pipeline_json"
    RLS_DEFINITION = "rls_definition"
    NOTEBOOK = "notebook"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@dataclass
class ArtifactSnapshot:
    """An immutable versioned snapshot of a generated artifact."""

    snapshot_id: str
    artifact_id: str
    artifact_type: ArtifactType
    name: str
    content: str
    content_hash: str
    version: int
    migration_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "name": self.name,
            "content_hash": self.content_hash,
            "version": self.version,
            "migration_id": self.migration_id,
            "created_at": self.created_at.isoformat(),
            "content_length": len(self.content),
        }


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


@dataclass
class ArtifactDiff:
    """Diff between two snapshots."""

    artifact_id: str
    from_version: int
    to_version: int
    added_lines: int = 0
    removed_lines: int = 0
    diff_text: str = ""
    is_identical: bool = False

    @property
    def changed_lines(self) -> int:
        return self.added_lines + self.removed_lines

    def summary(self) -> str:
        if self.is_identical:
            return f"v{self.from_version} → v{self.to_version}: identical"
        return (
            f"v{self.from_version} → v{self.to_version}: "
            f"+{self.added_lines} / -{self.removed_lines} lines"
        )


# ---------------------------------------------------------------------------
# Versioner
# ---------------------------------------------------------------------------


class ArtifactVersioner:
    """Version control for generated artifacts.

    Each ``save()`` creates an immutable snapshot with a content hash.
    If the content hasn't changed, no new version is created.
    """

    def __init__(self) -> None:
        # artifact_id → list of snapshots (ordered by version)
        self._store: dict[str, list[ArtifactSnapshot]] = {}

    def save(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        name: str,
        content: str,
        migration_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactSnapshot:
        """Save a new version. Returns the snapshot (existing if unchanged)."""
        content_hash = ArtifactSnapshot.compute_hash(content)
        history = self._store.get(artifact_id, [])

        # Skip if content unchanged
        if history and history[-1].content_hash == content_hash:
            logger.debug("Artifact %s unchanged — skipping", artifact_id)
            return history[-1]

        version = len(history) + 1
        snapshot = ArtifactSnapshot(
            snapshot_id=uuid.uuid4().hex[:12],
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            name=name,
            content=content,
            content_hash=content_hash,
            version=version,
            migration_id=migration_id,
            metadata=metadata or {},
        )

        if artifact_id not in self._store:
            self._store[artifact_id] = []
        self._store[artifact_id].append(snapshot)

        logger.info("Artifact %s saved: v%d (%s)", artifact_id, version, content_hash[:8])
        return snapshot

    def get_latest(self, artifact_id: str) -> ArtifactSnapshot | None:
        history = self._store.get(artifact_id, [])
        return history[-1] if history else None

    def get_version(self, artifact_id: str, version: int) -> ArtifactSnapshot | None:
        history = self._store.get(artifact_id, [])
        if 1 <= version <= len(history):
            return history[version - 1]
        return None

    def get_history(self, artifact_id: str) -> list[ArtifactSnapshot]:
        return list(self._store.get(artifact_id, []))

    def diff(self, artifact_id: str, from_version: int, to_version: int) -> ArtifactDiff | None:
        """Compare two versions of an artifact."""
        snap_from = self.get_version(artifact_id, from_version)
        snap_to = self.get_version(artifact_id, to_version)
        if not snap_from or not snap_to:
            return None

        if snap_from.content_hash == snap_to.content_hash:
            return ArtifactDiff(
                artifact_id=artifact_id,
                from_version=from_version,
                to_version=to_version,
                is_identical=True,
            )

        from_lines = snap_from.content.splitlines(keepends=True)
        to_lines = snap_to.content.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            from_lines, to_lines,
            fromfile=f"v{from_version}", tofile=f"v{to_version}",
        ))

        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        return ArtifactDiff(
            artifact_id=artifact_id,
            from_version=from_version,
            to_version=to_version,
            added_lines=added,
            removed_lines=removed,
            diff_text="".join(diff_lines),
        )

    def list_artifacts(self) -> list[str]:
        return list(self._store.keys())

    @property
    def artifact_count(self) -> int:
        return len(self._store)

    @property
    def total_versions(self) -> int:
        return sum(len(h) for h in self._store.values())
