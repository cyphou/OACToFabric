"""Phase 25 — Incremental & Delta Migration.

Tests cover:
- ChangeType and ConflictPolicy enums
- ChangeRecord fields and change_type classification
- ChangeSet properties (added, modified, deleted, unchanged, summary)
- _hash_item deterministic hashing
- ChangeDetector.detect with various scenarios
- SyncEntry creation and fields
- SyncJournal record, get_by_migration, total_syncs
- SyncSchedule defaults and custom values
- SyncScheduler add/remove/pause/resume/active_count
"""

from __future__ import annotations

import pytest

from src.core.incremental import (
    ChangeDetector,
    ChangeRecord,
    ChangeSet,
    ChangeType,
    ConflictPolicy,
    SyncEntry,
    SyncJournal,
    SyncSchedule,
    SyncScheduler,
    _hash_item,
)


# ===================================================================
# Enums
# ===================================================================


class TestEnums:
    """Tests for enums."""

    def test_change_types(self):
        assert ChangeType.ADDED.value == "added"
        assert ChangeType.MODIFIED.value == "modified"
        assert ChangeType.DELETED.value == "deleted"
        assert ChangeType.UNCHANGED.value == "unchanged"

    def test_conflict_policies(self):
        assert ConflictPolicy.LATEST_WINS.value == "latest_wins"
        assert ConflictPolicy.MANUAL.value == "manual"


# ===================================================================
# ChangeRecord
# ===================================================================


class TestChangeRecord:
    """Tests for change record."""

    def test_added_record(self):
        cr = ChangeRecord(
            asset_id="a1",
            asset_type="analysis",
            name="report1",
            change_type=ChangeType.ADDED,
        )
        assert cr.change_type == ChangeType.ADDED
        assert cr.old_hash == ""

    def test_modified_record(self):
        cr = ChangeRecord(
            asset_id="a1",
            asset_type="dashboard",
            name="dash1",
            change_type=ChangeType.MODIFIED,
            old_hash="aaa",
            new_hash="bbb",
            changed_fields=["title", "columns"],
        )
        assert len(cr.changed_fields) == 2


# ===================================================================
# _hash_item
# ===================================================================


class TestHashItem:
    """Tests for deterministic hashing."""

    def test_consistent_hash(self):
        item = {"asset_id": "a1", "name": "report", "type": "analysis"}
        h1 = _hash_item(item)
        h2 = _hash_item(item)
        assert h1 == h2

    def test_different_items_different_hash(self):
        item1 = {"asset_id": "a1", "name": "report1"}
        item2 = {"asset_id": "a1", "name": "report2"}
        assert _hash_item(item1) != _hash_item(item2)

    def test_key_order_independent(self):
        item1 = {"name": "report", "asset_id": "a1"}
        item2 = {"asset_id": "a1", "name": "report"}
        assert _hash_item(item1) == _hash_item(item2)

    def test_excludes_transient_fields(self):
        item1 = {"asset_id": "a1", "name": "r", "discovered_at": "2024-01-01"}
        item2 = {"asset_id": "a1", "name": "r", "discovered_at": "2024-06-01"}
        assert _hash_item(item1) == _hash_item(item2)

    def test_hash_is_truncated_sha256(self):
        h = _hash_item({"asset_id": "x"})
        assert len(h) == 16  # SHA-256 hex digest truncated to 16 chars


# ===================================================================
# ChangeSet
# ===================================================================


class TestChangeSet:
    """Tests for change set."""

    def test_empty_changeset(self):
        cs = ChangeSet(changes=[])
        assert cs.has_changes is False
        assert cs.change_count == 0

    def test_changeset_properties(self):
        changes = [
            ChangeRecord("a1", "analysis", "r1", ChangeType.ADDED),
            ChangeRecord("a2", "dashboard", "d1", ChangeType.MODIFIED),
            ChangeRecord("a3", "analysis", "r2", ChangeType.DELETED),
            ChangeRecord("a4", "analysis", "r3", ChangeType.UNCHANGED),
        ]
        cs = ChangeSet(changes=changes)
        assert len(cs.added) == 1
        assert len(cs.modified) == 1
        assert len(cs.deleted) == 1
        assert len(cs.unchanged) == 1
        assert cs.has_changes is True
        assert cs.change_count == 3  # added + modified + deleted

    def test_changeset_summary(self):
        changes = [
            ChangeRecord("a1", "analysis", "r1", ChangeType.ADDED),
            ChangeRecord("a2", "analysis", "r2", ChangeType.ADDED),
        ]
        cs = ChangeSet(changes=changes)
        s = cs.summary()
        assert "2 added" in s


# ===================================================================
# ChangeDetector
# ===================================================================


class TestChangeDetector:
    """Tests for change detection."""

    def _detect(self, baseline, current):
        return ChangeDetector().detect(baseline, current)

    def test_no_changes(self):
        items = [{"asset_id": "a1", "name": "r1"}]
        cs = self._detect(items, items)
        assert cs.has_changes is False
        assert len(cs.unchanged) == 1

    def test_detect_added(self):
        baseline = [{"asset_id": "a1", "name": "r1"}]
        current = [
            {"asset_id": "a1", "name": "r1"},
            {"asset_id": "a2", "name": "r2"},
        ]
        cs = self._detect(baseline, current)
        assert len(cs.added) == 1
        assert cs.added[0].asset_id == "a2"

    def test_detect_deleted(self):
        baseline = [
            {"asset_id": "a1", "name": "r1"},
            {"asset_id": "a2", "name": "r2"},
        ]
        current = [{"asset_id": "a1", "name": "r1"}]
        cs = self._detect(baseline, current)
        assert len(cs.deleted) == 1
        assert cs.deleted[0].asset_id == "a2"

    def test_detect_modified(self):
        baseline = [{"asset_id": "a1", "name": "r1", "title": "old"}]
        current = [{"asset_id": "a1", "name": "r1", "title": "new"}]
        cs = self._detect(baseline, current)
        assert len(cs.modified) == 1

    def test_detect_mixed(self):
        baseline = [
            {"asset_id": "a1", "name": "r1"},
            {"asset_id": "a2", "name": "r2", "desc": "old"},
            {"asset_id": "a3", "name": "r3"},
        ]
        current = [
            {"asset_id": "a1", "name": "r1"},
            {"asset_id": "a2", "name": "r2", "desc": "new"},
            {"asset_id": "a4", "name": "r4"},
        ]
        cs = self._detect(baseline, current)
        assert len(cs.unchanged) == 1
        assert len(cs.modified) == 1
        assert len(cs.deleted) == 1
        assert len(cs.added) == 1

    def test_empty_baseline(self):
        current = [{"asset_id": "a1", "name": "r1"}]
        cs = self._detect([], current)
        assert len(cs.added) == 1

    def test_empty_current(self):
        baseline = [{"asset_id": "a1", "name": "r1"}]
        cs = self._detect(baseline, [])
        assert len(cs.deleted) == 1

    def test_both_empty(self):
        cs = self._detect([], [])
        assert cs.has_changes is False

    def test_large_inventory(self):
        baseline = [{"asset_id": f"a{i}", "name": f"r{i}"} for i in range(100)]
        current = [{"asset_id": f"a{i}", "name": f"r{i}"} for i in range(50, 150)]
        cs = self._detect(baseline, current)
        assert len(cs.deleted) == 50
        assert len(cs.added) == 50
        assert len(cs.unchanged) == 50


# ===================================================================
# SyncJournal
# ===================================================================


class TestSyncJournal:
    """Tests for sync journal."""

    def test_empty_journal(self):
        journal = SyncJournal()
        assert journal.total_syncs == 0
        assert journal.entries == []

    def test_record_entry(self):
        journal = SyncJournal()
        cs = ChangeSet(changes=[
            ChangeRecord("a1", "analysis", "r1", ChangeType.ADDED),
        ])
        entry = journal.record("sync-1", "mig-1", cs)
        assert entry.migration_id == "mig-1"
        assert entry.added == 1
        assert journal.total_syncs == 1

    def test_get_by_migration(self):
        journal = SyncJournal()
        cs = ChangeSet(changes=[])
        journal.record("s1", "mig-1", cs)
        journal.record("s2", "mig-2", cs)
        journal.record("s3", "mig-1", cs)
        assert len(journal.get_by_migration("mig-1")) == 2
        assert len(journal.get_by_migration("mig-2")) == 1

    def test_multiple_records(self):
        journal = SyncJournal()
        for i in range(5):
            cs = ChangeSet(changes=[
                ChangeRecord(f"a{i}", "analysis", f"r{i}", ChangeType.ADDED),
            ])
            journal.record(f"sync-{i}", "mig-1", cs)
        assert journal.total_syncs == 5


# ===================================================================
# SyncScheduler
# ===================================================================


class TestSyncScheduler:
    """Tests for sync scheduler."""

    def test_add_schedule(self):
        sched = SyncScheduler()
        s = sched.add_schedule("m1", interval_minutes=30)
        assert sched.get_schedule("m1") is not None
        assert sched.active_count == 1
        assert s.interval_minutes == 30

    def test_remove_schedule(self):
        sched = SyncScheduler()
        sched.add_schedule("m1")
        assert sched.remove_schedule("m1") is True
        assert sched.get_schedule("m1") is None

    def test_remove_nonexistent(self):
        sched = SyncScheduler()
        assert sched.remove_schedule("x") is False

    def test_pause_resume(self):
        sched = SyncScheduler()
        sched.add_schedule("m1")
        sched.pause("m1")
        s = sched.get_schedule("m1")
        assert s is not None and s.enabled is False
        assert sched.active_count == 0
        sched.resume("m1")
        s = sched.get_schedule("m1")
        assert s is not None and s.enabled is True
        assert sched.active_count == 1

    def test_list_schedules(self):
        sched = SyncScheduler()
        sched.add_schedule("m1")
        sched.add_schedule("m2")
        assert len(sched.list_schedules()) == 2

    def test_schedule_defaults(self):
        sched = SyncScheduler()
        s = sched.add_schedule("m1")
        assert s.interval_minutes == 60
        assert s.enabled is True
        assert s.conflict_policy == ConflictPolicy.LATEST_WINS

    def test_schedule_custom_policy(self):
        sched = SyncScheduler()
        s = sched.add_schedule(
            "m1",
            interval_minutes=15,
            conflict_policy=ConflictPolicy.MANUAL,
        )
        assert s.conflict_policy == ConflictPolicy.MANUAL
        assert s.interval_minutes == 15
