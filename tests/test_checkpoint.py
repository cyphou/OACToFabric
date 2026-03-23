"""Tests for the checkpoint manager — persist and resume migration progress."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.core.checkpoint import Checkpoint, CheckpointManager


# ---------------------------------------------------------------------------
# Checkpoint data class
# ---------------------------------------------------------------------------


class TestCheckpoint:
    def test_defaults(self):
        cp = Checkpoint()
        assert cp.run_id == ""
        assert cp.status == "not_started"
        assert cp.completed_waves == []
        assert cp.completed_agents == {}

    def test_is_wave_complete(self):
        cp = Checkpoint(completed_waves=[1, 2])
        assert cp.is_wave_complete(1)
        assert cp.is_wave_complete(2)
        assert not cp.is_wave_complete(3)

    def test_is_agent_complete(self):
        cp = Checkpoint(completed_agents={"1": ["01-discovery", "02-schema"]})
        assert cp.is_agent_complete(1, "01-discovery")
        assert cp.is_agent_complete(1, "02-schema")
        assert not cp.is_agent_complete(1, "03-etl")
        assert not cp.is_agent_complete(2, "01-discovery")

    def test_pending_agents(self):
        cp = Checkpoint(completed_agents={"1": ["01-discovery"]})
        pending = cp.pending_agents(1, ["01-discovery", "02-schema", "03-etl"])
        assert pending == ["02-schema", "03-etl"]

    def test_pending_agents_empty_wave(self):
        cp = Checkpoint()
        pending = cp.pending_agents(1, ["01-discovery"])
        assert pending == ["01-discovery"]


# ---------------------------------------------------------------------------
# CheckpointManager lifecycle
# ---------------------------------------------------------------------------


class TestCheckpointManager:
    def test_start_creates_file(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        cp = mgr.start("run-001")
        assert cp.run_id == "run-001"
        assert cp.status == "in_progress"
        assert mgr.path.exists()

    def test_start_writes_valid_json(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-002")
        raw = json.loads(mgr.path.read_text(encoding="utf-8"))
        assert raw["run_id"] == "run-002"
        assert raw["status"] == "in_progress"

    def test_load_returns_none_when_no_file(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        assert mgr.load() is None

    def test_load_restores_checkpoint(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-003")
        mgr.mark_agent_complete(1, "01-discovery")
        mgr.mark_wave_complete(1)

        # New manager, same dir
        mgr2 = CheckpointManager(output_dir=tmp_path)
        cp = mgr2.load()
        assert cp is not None
        assert cp.run_id == "run-003"
        assert cp.is_wave_complete(1)
        assert cp.is_agent_complete(1, "01-discovery")


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------


class TestCheckpointProgress:
    def test_mark_agent_complete(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-004")
        mgr.mark_agent_complete(1, "01-discovery")
        mgr.mark_agent_complete(1, "02-schema")

        cp = mgr.checkpoint
        assert cp.is_agent_complete(1, "01-discovery")
        assert cp.is_agent_complete(1, "02-schema")

    def test_mark_agent_complete_idempotent(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-005")
        mgr.mark_agent_complete(1, "01-discovery")
        mgr.mark_agent_complete(1, "01-discovery")  # duplicate
        assert len(mgr.checkpoint.completed_agents["1"]) == 1

    def test_mark_wave_complete(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-006")
        mgr.mark_wave_complete(1)
        mgr.mark_wave_complete(2)
        assert mgr.checkpoint.completed_waves == [1, 2]

    def test_mark_wave_complete_idempotent(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-007")
        mgr.mark_wave_complete(1)
        mgr.mark_wave_complete(1)  # duplicate
        assert mgr.checkpoint.completed_waves == [1]

    def test_mark_finished(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-008")
        mgr.mark_finished("succeeded")
        assert mgr.checkpoint.status == "succeeded"

    def test_mark_failed(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-009")
        mgr.mark_failed("Connection timeout")
        assert mgr.checkpoint.status == "failed"
        assert mgr.checkpoint.metadata["last_error"] == "Connection timeout"

    def test_mark_agent_without_start_raises(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        with pytest.raises(RuntimeError, match="not started"):
            mgr.mark_agent_complete(1, "01-discovery")


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


class TestCheckpointResume:
    def test_can_resume_when_in_progress(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-010")
        assert mgr.can_resume()

    def test_cannot_resume_when_no_checkpoint(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        assert not mgr.can_resume()

    def test_cannot_resume_when_succeeded(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-011")
        mgr.mark_finished("succeeded")
        # Need to reload to test can_resume
        mgr2 = CheckpointManager(output_dir=tmp_path)
        assert not mgr2.can_resume()

    def test_resume_wave_after_completion(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-012")
        mgr.mark_wave_complete(1)
        mgr.mark_wave_complete(2)
        assert mgr.resume_wave() == 3

    def test_resume_wave_from_scratch(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-013")
        assert mgr.resume_wave() == 1


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestCheckpointDelete:
    def test_delete_removes_file(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-014")
        assert mgr.path.exists()
        mgr.delete()
        assert not mgr.path.exists()

    def test_delete_is_safe_when_no_file(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.delete()  # Should not raise


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestCheckpointEdgeCases:
    def test_load_corrupt_json(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.path.parent.mkdir(parents=True, exist_ok=True)
        mgr.path.write_text("not valid json", encoding="utf-8")
        assert mgr.load() is None

    def test_creates_directories(self, tmp_path: Path):
        deep_path = tmp_path / "a" / "b" / "c"
        mgr = CheckpointManager(output_dir=deep_path)
        mgr.start("run-015")
        assert mgr.path.exists()

    def test_multiple_waves_ordering(self, tmp_path: Path):
        mgr = CheckpointManager(output_dir=tmp_path)
        mgr.start("run-016")
        mgr.mark_wave_complete(3)
        mgr.mark_wave_complete(1)
        # Should be sorted
        assert mgr.checkpoint.completed_waves == [1, 3]
