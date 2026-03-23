"""Phase 30 — Rollback, Versioning & Release v2.0.

Tests cover:
- ArtifactType enum
- ArtifactSnapshot hash computation and to_dict
- ArtifactDiff properties (changed_lines, summary, is_identical)
- ArtifactVersioner save/get_latest/get_version/get_history/diff
- ArtifactVersioner deduplication (skip if unchanged)
- ActionType enum values
- RecordedAction construction and to_dict
- ActionLog record/count/get_by_agent/get_reversible/get_actions_after
- RollbackPlan summary
- RollbackEngine plan_full_rollback and plan_rollback_to
- RollbackEngine execute (mock mode)
- RollbackEngine dry-run
- RollbackResult properties (all_succeeded, summary)
"""

from __future__ import annotations

import pytest

from src.core.artifact_versioner import (
    ArtifactDiff,
    ArtifactSnapshot,
    ArtifactType,
    ArtifactVersioner,
)
from src.core.rollback import (
    ActionLog,
    ActionType,
    RecordedAction,
    RollbackEngine,
    RollbackPlan,
    RollbackResult,
    RollbackStepResult,
)


# ===================================================================
# ArtifactType
# ===================================================================


class TestArtifactType:
    def test_artifact_types(self):
        assert ArtifactType.TMDL.value == "tmdl"
        assert ArtifactType.PBIR.value == "pbir"
        assert ArtifactType.DDL.value == "ddl"
        assert len(ArtifactType) == 8


# ===================================================================
# ArtifactSnapshot
# ===================================================================


class TestArtifactSnapshot:
    def test_compute_hash(self):
        h = ArtifactSnapshot.compute_hash("hello")
        assert len(h) == 64
        assert h == ArtifactSnapshot.compute_hash("hello")

    def test_different_content_different_hash(self):
        assert ArtifactSnapshot.compute_hash("a") != ArtifactSnapshot.compute_hash("b")

    def test_to_dict(self):
        snap = ArtifactSnapshot(
            snapshot_id="s1",
            artifact_id="a1",
            artifact_type=ArtifactType.TMDL,
            name="model.tmdl",
            content="CREATE TABLE ...",
            content_hash="abc123",
            version=1,
            migration_id="m1",
        )
        d = snap.to_dict()
        assert d["snapshot_id"] == "s1"
        assert d["artifact_type"] == "tmdl"
        assert d["version"] == 1
        assert "content_length" in d


# ===================================================================
# ArtifactDiff
# ===================================================================


class TestArtifactDiff:
    def test_identical_diff(self):
        d = ArtifactDiff(artifact_id="a1", from_version=1, to_version=2, is_identical=True)
        assert d.changed_lines == 0
        assert "identical" in d.summary()

    def test_changed_diff(self):
        d = ArtifactDiff(
            artifact_id="a1",
            from_version=1,
            to_version=2,
            added_lines=5,
            removed_lines=3,
        )
        assert d.changed_lines == 8
        assert "+5" in d.summary()
        assert "-3" in d.summary()


# ===================================================================
# ArtifactVersioner
# ===================================================================


class TestArtifactVersioner:
    def test_save_first_version(self):
        v = ArtifactVersioner()
        snap = v.save("a1", ArtifactType.TMDL, "model.tmdl", "content v1")
        assert snap.version == 1
        assert v.artifact_count == 1
        assert v.total_versions == 1

    def test_save_new_version(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.TMDL, "model.tmdl", "content v1")
        snap = v.save("a1", ArtifactType.TMDL, "model.tmdl", "content v2")
        assert snap.version == 2
        assert v.total_versions == 2

    def test_save_unchanged_skips(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.TMDL, "model.tmdl", "same content")
        snap = v.save("a1", ArtifactType.TMDL, "model.tmdl", "same content")
        assert snap.version == 1  # no new version
        assert v.total_versions == 1

    def test_get_latest(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.DDL, "schema.sql", "v1")
        v.save("a1", ArtifactType.DDL, "schema.sql", "v2")
        latest = v.get_latest("a1")
        assert latest is not None
        assert latest.version == 2

    def test_get_latest_nonexistent(self):
        v = ArtifactVersioner()
        assert v.get_latest("nope") is None

    def test_get_version(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.DDL, "schema.sql", "v1")
        v.save("a1", ArtifactType.DDL, "schema.sql", "v2")
        snap = v.get_version("a1", 1)
        assert snap is not None
        assert snap.content == "v1"

    def test_get_version_out_of_range(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.DDL, "x", "y")
        assert v.get_version("a1", 0) is None
        assert v.get_version("a1", 99) is None

    def test_get_history(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.TMDL, "m", "v1")
        v.save("a1", ArtifactType.TMDL, "m", "v2")
        v.save("a1", ArtifactType.TMDL, "m", "v3")
        history = v.get_history("a1")
        assert len(history) == 3
        assert [h.version for h in history] == [1, 2, 3]

    def test_diff_identical(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.TMDL, "m", "same")
        v.save("a1", ArtifactType.TMDL, "m", "different")
        # Force save same content with a workaround
        v._store["a1"].append(v._store["a1"][0])  # copy v1 as v3
        diff = v.diff("a1", 1, 3)
        assert diff is not None
        assert diff.is_identical is True

    def test_diff_changed(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.DDL, "x", "line1\nline2\n")
        v.save("a1", ArtifactType.DDL, "x", "line1\nline2\nline3\n")
        diff = v.diff("a1", 1, 2)
        assert diff is not None
        assert diff.added_lines > 0

    def test_diff_nonexistent(self):
        v = ArtifactVersioner()
        assert v.diff("a1", 1, 2) is None

    def test_list_artifacts(self):
        v = ArtifactVersioner()
        v.save("a1", ArtifactType.TMDL, "m1", "c1")
        v.save("a2", ArtifactType.DDL, "m2", "c2")
        assert set(v.list_artifacts()) == {"a1", "a2"}

    def test_save_with_metadata(self):
        v = ArtifactVersioner()
        snap = v.save("a1", ArtifactType.TMDL, "m", "c", metadata={"agent": "04"})
        assert snap.metadata["agent"] == "04"


# ===================================================================
# ActionType
# ===================================================================


class TestActionType:
    def test_action_types(self):
        assert ActionType.SCHEMA_CREATE_TABLE.value == "schema_create_table"
        assert ActionType.REPORT_DEPLOY.value == "report_deploy"
        assert ActionType.CUSTOM.value == "custom"
        assert len(ActionType) == 13


# ===================================================================
# RecordedAction
# ===================================================================


class TestRecordedAction:
    def test_construction(self):
        a = RecordedAction(
            action_id="act1",
            action_type=ActionType.SCHEMA_CREATE_TABLE,
            agent_id="02",
            migration_id="m1",
            description="Create table Sales",
        )
        assert a.action_id == "act1"
        assert a.is_reversed is False

    def test_to_dict(self):
        a = RecordedAction(
            action_id="act1",
            action_type=ActionType.REPORT_DEPLOY,
            agent_id="05",
            migration_id="m1",
            description="Deploy report",
        )
        d = a.to_dict()
        assert d["action_type"] == "report_deploy"
        assert d["is_reversed"] is False


# ===================================================================
# ActionLog
# ===================================================================


class TestActionLog:
    def test_record(self):
        log = ActionLog("m1")
        a = log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "Create table")
        assert a.migration_id == "m1"
        assert log.count == 1

    def test_actions_list(self):
        log = ActionLog("m1")
        log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "Create T1")
        log.record(ActionType.REPORT_DEPLOY, "05", "Deploy R1")
        assert len(log.actions) == 2

    def test_get_by_agent(self):
        log = ActionLog("m1")
        log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "A")
        log.record(ActionType.REPORT_DEPLOY, "05", "B")
        log.record(ActionType.SCHEMA_ALTER_TABLE, "02", "C")
        assert len(log.get_by_agent("02")) == 2
        assert len(log.get_by_agent("05")) == 1

    def test_get_reversible(self):
        log = ActionLog("m1")
        a1 = log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "A")
        a2 = log.record(ActionType.REPORT_DEPLOY, "05", "B")
        a1.is_reversed = True
        reversible = log.get_reversible()
        assert len(reversible) == 1
        assert reversible[0].action_id == a2.action_id

    def test_get_actions_after(self):
        log = ActionLog("m1")
        a1 = log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "A")
        a2 = log.record(ActionType.REPORT_DEPLOY, "05", "B")
        a3 = log.record(ActionType.SECURITY_SET_RLS, "06", "C")
        after = log.get_actions_after(a2.action_id)
        # should include a2 and a3, in reverse order
        assert len(after) == 2
        assert after[0].action_id == a3.action_id
        assert after[1].action_id == a2.action_id


# ===================================================================
# RollbackPlan
# ===================================================================


class TestRollbackPlan:
    def test_plan_summary(self):
        plan = RollbackPlan(
            migration_id="m1",
            actions_to_reverse=[
                RecordedAction("a1", ActionType.SCHEMA_CREATE_TABLE, "02", "m1", "X"),
            ],
        )
        assert plan.action_count == 1
        s = plan.summary()
        assert "m1" in s
        assert "schema_create_table" in s

    def test_empty_plan(self):
        plan = RollbackPlan(migration_id="m1")
        assert plan.action_count == 0


# ===================================================================
# RollbackResult
# ===================================================================


class TestRollbackResult:
    def test_all_succeeded(self):
        result = RollbackResult(
            migration_id="m1",
            steps=[
                RollbackStepResult("a1", ActionType.SCHEMA_CREATE_TABLE, True),
                RollbackStepResult("a2", ActionType.REPORT_DEPLOY, True),
            ],
        )
        assert result.all_succeeded is True
        assert result.succeeded == 2
        assert result.failed == 0

    def test_some_failed(self):
        result = RollbackResult(
            migration_id="m1",
            steps=[
                RollbackStepResult("a1", ActionType.SCHEMA_CREATE_TABLE, True),
                RollbackStepResult("a2", ActionType.REPORT_DEPLOY, False, "API error"),
            ],
        )
        assert result.all_succeeded is False
        assert result.failed == 1

    def test_empty_result(self):
        result = RollbackResult(migration_id="m1")
        assert result.all_succeeded is False
        assert result.total == 0

    def test_summary(self):
        result = RollbackResult(
            migration_id="m1",
            steps=[RollbackStepResult("a1", ActionType.CUSTOM, True)],
        )
        assert "1/1" in result.summary()


# ===================================================================
# RollbackEngine
# ===================================================================


class TestRollbackEngine:
    def test_plan_full_rollback(self):
        engine = RollbackEngine(mock_mode=True)
        log = ActionLog("m1")
        log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "Create T1")
        log.record(ActionType.REPORT_DEPLOY, "05", "Deploy R1")
        plan = engine.plan_full_rollback(log)
        assert plan.action_count == 2

    def test_plan_rollback_to(self):
        engine = RollbackEngine(mock_mode=True)
        log = ActionLog("m1")
        a1 = log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "Create T1")
        a2 = log.record(ActionType.REPORT_DEPLOY, "05", "Deploy R1")
        a3 = log.record(ActionType.SECURITY_SET_RLS, "06", "Set RLS")
        plan = engine.plan_rollback_to(log, a2.action_id)
        assert plan.action_count == 2  # a2 and a3

    @pytest.mark.asyncio
    async def test_execute_mock(self):
        engine = RollbackEngine(mock_mode=True)
        log = ActionLog("m1")
        log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "Create T1")
        log.record(ActionType.REPORT_DEPLOY, "05", "Deploy R1")
        plan = engine.plan_full_rollback(log)
        result = await engine.execute(plan, log)
        assert result.all_succeeded is True
        assert result.succeeded == 2

    @pytest.mark.asyncio
    async def test_execute_dry_run(self):
        engine = RollbackEngine(mock_mode=True)
        log = ActionLog("m1")
        log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "Create T1")
        plan = engine.plan_full_rollback(log)
        plan.dry_run = True
        result = await engine.execute(plan, log)
        assert result.succeeded == 1
        assert "dry-run" in result.steps[0].error

    @pytest.mark.asyncio
    async def test_execute_marks_reversed(self):
        engine = RollbackEngine(mock_mode=True)
        log = ActionLog("m1")
        a1 = log.record(ActionType.SCHEMA_CREATE_TABLE, "02", "Create T1")
        plan = engine.plan_full_rollback(log)
        await engine.execute(plan, log)
        assert a1.is_reversed is True
