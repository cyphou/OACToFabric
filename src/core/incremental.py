"""Incremental & delta migration — change detection, sync journal, scheduling.

Provides:
- ``ChangeType`` — enumeration (added, modified, deleted, unchanged).
- ``ChangeRecord`` — single asset change.
- ``ChangeSet`` — collection of changes between two inventory snapshots.
- ``ChangeDetector`` — compare two inventories to produce a ``ChangeSet``.
- ``SyncJournal`` — audit trail for incremental syncs.
- ``SyncScheduler`` — schedule periodic sync runs.
- ``ConflictPolicy`` — resolution strategy for concurrent changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Change types
# ---------------------------------------------------------------------------


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


class ConflictPolicy(str, Enum):
    """Strategy for resolving conflicts in incremental sync."""
    LATEST_WINS = "latest_wins"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Change record
# ---------------------------------------------------------------------------


@dataclass
class ChangeRecord:
    """A single detected change between source snapshots."""

    asset_id: str
    asset_type: str
    name: str
    change_type: ChangeType
    source_path: str = ""
    old_hash: str = ""
    new_hash: str = ""
    changed_fields: list[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Change set
# ---------------------------------------------------------------------------


@dataclass
class ChangeSet:
    """Collection of changes between two inventory snapshots."""

    changes: list[ChangeRecord] = field(default_factory=list)
    base_snapshot_id: str = ""
    current_snapshot_id: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def added(self) -> list[ChangeRecord]:
        return [c for c in self.changes if c.change_type == ChangeType.ADDED]

    @property
    def modified(self) -> list[ChangeRecord]:
        return [c for c in self.changes if c.change_type == ChangeType.MODIFIED]

    @property
    def deleted(self) -> list[ChangeRecord]:
        return [c for c in self.changes if c.change_type == ChangeType.DELETED]

    @property
    def unchanged(self) -> list[ChangeRecord]:
        return [c for c in self.changes if c.change_type == ChangeType.UNCHANGED]

    @property
    def has_changes(self) -> bool:
        return any(c.change_type != ChangeType.UNCHANGED for c in self.changes)

    @property
    def change_count(self) -> int:
        return len(self.added) + len(self.modified) + len(self.deleted)

    def summary(self) -> str:
        return (
            f"ChangeSet: {len(self.added)} added, "
            f"{len(self.modified)} modified, "
            f"{len(self.deleted)} deleted, "
            f"{len(self.unchanged)} unchanged"
        )


# ---------------------------------------------------------------------------
# Change detector
# ---------------------------------------------------------------------------


def _hash_item(item: dict[str, Any]) -> str:
    """Compute a content hash for an inventory item dict."""
    # Use a deterministic subset of fields for comparison
    fields_to_hash = {
        k: v for k, v in sorted(item.items())
        if k not in ("discovered_at", "migration_status", "migration_wave", "incomplete")
    }
    blob = json.dumps(fields_to_hash, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


class ChangeDetector:
    """Compare two inventory snapshots and produce a ChangeSet.

    Each snapshot is a ``list[dict]`` where each dict has at least
    an ``asset_id`` key.
    """

    def detect(
        self,
        baseline: list[dict[str, Any]],
        current: list[dict[str, Any]],
        *,
        baseline_id: str = "baseline",
        current_id: str = "current",
    ) -> ChangeSet:
        """Compare *baseline* and *current* inventories.

        Returns a ``ChangeSet`` with all changes classified.
        """
        base_map = {item["asset_id"]: item for item in baseline}
        curr_map = {item["asset_id"]: item for item in current}

        changes: list[ChangeRecord] = []

        # Check current items against baseline
        for asset_id, curr_item in curr_map.items():
            if asset_id not in base_map:
                changes.append(ChangeRecord(
                    asset_id=asset_id,
                    asset_type=curr_item.get("asset_type", ""),
                    name=curr_item.get("name", ""),
                    change_type=ChangeType.ADDED,
                    source_path=curr_item.get("source_path", ""),
                    new_hash=_hash_item(curr_item),
                ))
            else:
                base_item = base_map[asset_id]
                old_h = _hash_item(base_item)
                new_h = _hash_item(curr_item)

                if old_h != new_h:
                    changed_fields = [
                        k for k in set(base_item.keys()) | set(curr_item.keys())
                        if base_item.get(k) != curr_item.get(k)
                        and k not in ("discovered_at", "migration_status", "migration_wave")
                    ]
                    changes.append(ChangeRecord(
                        asset_id=asset_id,
                        asset_type=curr_item.get("asset_type", ""),
                        name=curr_item.get("name", ""),
                        change_type=ChangeType.MODIFIED,
                        source_path=curr_item.get("source_path", ""),
                        old_hash=old_h,
                        new_hash=new_h,
                        changed_fields=changed_fields,
                    ))
                else:
                    changes.append(ChangeRecord(
                        asset_id=asset_id,
                        asset_type=curr_item.get("asset_type", ""),
                        name=curr_item.get("name", ""),
                        change_type=ChangeType.UNCHANGED,
                        source_path=curr_item.get("source_path", ""),
                        old_hash=old_h,
                        new_hash=new_h,
                    ))

        # Check for deletions
        for asset_id, base_item in base_map.items():
            if asset_id not in curr_map:
                changes.append(ChangeRecord(
                    asset_id=asset_id,
                    asset_type=base_item.get("asset_type", ""),
                    name=base_item.get("name", ""),
                    change_type=ChangeType.DELETED,
                    source_path=base_item.get("source_path", ""),
                    old_hash=_hash_item(base_item),
                ))

        cs = ChangeSet(
            changes=changes,
            base_snapshot_id=baseline_id,
            current_snapshot_id=current_id,
        )
        logger.info("Change detection: %s", cs.summary())
        return cs


# ---------------------------------------------------------------------------
# Sync journal
# ---------------------------------------------------------------------------


@dataclass
class SyncEntry:
    """A single sync journal entry."""

    sync_id: str
    migration_id: str
    change_set_summary: str
    added: int = 0
    modified: int = 0
    deleted: int = 0
    status: str = "completed"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error: str = ""


class SyncJournal:
    """Audit trail for incremental sync operations."""

    def __init__(self) -> None:
        self._entries: list[SyncEntry] = []

    def record(
        self,
        sync_id: str,
        migration_id: str,
        change_set: ChangeSet,
        *,
        status: str = "completed",
        error: str = "",
    ) -> SyncEntry:
        entry = SyncEntry(
            sync_id=sync_id,
            migration_id=migration_id,
            change_set_summary=change_set.summary(),
            added=len(change_set.added),
            modified=len(change_set.modified),
            deleted=len(change_set.deleted),
            status=status,
            completed_at=datetime.now(timezone.utc),
            error=error,
        )
        self._entries.append(entry)
        logger.info("Sync recorded: %s — %s", sync_id, change_set.summary())
        return entry

    @property
    def entries(self) -> list[SyncEntry]:
        return list(self._entries)

    def get_by_migration(self, migration_id: str) -> list[SyncEntry]:
        return [e for e in self._entries if e.migration_id == migration_id]

    @property
    def total_syncs(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# Sync scheduler
# ---------------------------------------------------------------------------


@dataclass
class SyncSchedule:
    """Schedule configuration for periodic sync."""

    migration_id: str
    interval_minutes: int = 60
    enabled: bool = True
    conflict_policy: ConflictPolicy = ConflictPolicy.LATEST_WINS
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class SyncScheduler:
    """Manage scheduled sync operations.

    In production, this would integrate with APScheduler or Fabric
    triggers. For now, provides the scheduling data model.
    """

    def __init__(self) -> None:
        self._schedules: dict[str, SyncSchedule] = {}

    def add_schedule(
        self,
        migration_id: str,
        *,
        interval_minutes: int = 60,
        conflict_policy: ConflictPolicy = ConflictPolicy.LATEST_WINS,
    ) -> SyncSchedule:
        schedule = SyncSchedule(
            migration_id=migration_id,
            interval_minutes=interval_minutes,
            conflict_policy=conflict_policy,
        )
        self._schedules[migration_id] = schedule
        logger.info("Schedule added: %s every %d min", migration_id, interval_minutes)
        return schedule

    def remove_schedule(self, migration_id: str) -> bool:
        if migration_id in self._schedules:
            del self._schedules[migration_id]
            return True
        return False

    def get_schedule(self, migration_id: str) -> SyncSchedule | None:
        return self._schedules.get(migration_id)

    def list_schedules(self) -> list[SyncSchedule]:
        return list(self._schedules.values())

    def pause(self, migration_id: str) -> bool:
        sched = self._schedules.get(migration_id)
        if sched:
            sched.enabled = False
            return True
        return False

    def resume(self, migration_id: str) -> bool:
        sched = self._schedules.get(migration_id)
        if sched:
            sched.enabled = True
            return True
        return False

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._schedules.values() if s.enabled)
