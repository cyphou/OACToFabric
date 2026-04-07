"""Tests for Phase 79 — Blue/Green Manager."""

from __future__ import annotations

import asyncio
import unittest

from src.deployers.blue_green import (
    BlueGreenManager,
    SlotInfo,
    SlotLabel,
    SwapOutcome,
    ValidationGate,
)


class TestSlotInfo(unittest.TestCase):
    def test_to_dict(self) -> None:
        info = SlotInfo(slot=SlotLabel.LIVE, artifact_id="a1", artifact_name="model_v1", version=1)
        d = info.to_dict()
        self.assertEqual(d["slot"], "live")
        self.assertEqual(d["version"], 1)


class TestBlueGreenManager(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def _manager_with_slots(self) -> BlueGreenManager:
        mgr = BlueGreenManager(workspace_id="ws-1")
        mgr.set_slot(SlotInfo(slot=SlotLabel.LIVE, artifact_id="a1", artifact_name="model_v1", version=1))
        mgr.set_slot(SlotInfo(slot=SlotLabel.STAGING, artifact_id="a2", artifact_name="model_v2", version=2))
        return mgr

    def test_set_and_get_slots(self) -> None:
        mgr = self._manager_with_slots()
        self.assertIsNotNone(mgr.live)
        self.assertEqual(mgr.live.artifact_name, "model_v1")
        self.assertIsNotNone(mgr.staging)
        self.assertEqual(mgr.staging.version, 2)

    def test_swap_success(self) -> None:
        mgr = self._manager_with_slots()
        result = self._run(mgr.swap())
        self.assertEqual(result.outcome, SwapOutcome.SWAPPED)
        self.assertTrue(result.success)
        self.assertEqual(mgr.live.artifact_name, "model_v2")
        self.assertEqual(mgr.staging.artifact_name, "model_v1")

    def test_swap_no_staging(self) -> None:
        mgr = BlueGreenManager(workspace_id="ws-1")
        mgr.set_slot(SlotInfo(slot=SlotLabel.LIVE, artifact_id="a1", artifact_name="model_v1"))
        result = self._run(mgr.swap())
        self.assertEqual(result.outcome, SwapOutcome.FAILED)
        self.assertIn("No staging", result.error)

    def test_swap_dry_run(self) -> None:
        mgr = BlueGreenManager(workspace_id="ws-1", dry_run=True)
        mgr.set_slot(SlotInfo(slot=SlotLabel.LIVE, artifact_id="a1", artifact_name="v1", version=1))
        mgr.set_slot(SlotInfo(slot=SlotLabel.STAGING, artifact_id="a2", artifact_name="v2", version=2))
        result = self._run(mgr.swap())
        self.assertEqual(result.outcome, SwapOutcome.DRY_RUN)

    def test_swap_validation_failure(self) -> None:
        mgr = self._manager_with_slots()

        # Override validation to fail
        async def fail_gates(staging, *, gates=None):
            return [ValidationGate(name="schema_match", passed=False, message="mismatch")]

        mgr.run_validation_gates = fail_gates
        result = self._run(mgr.swap())
        self.assertEqual(result.outcome, SwapOutcome.VALIDATION_FAILED)
        self.assertFalse(result.all_gates_passed)

    def test_rollback(self) -> None:
        mgr = self._manager_with_slots()
        self._run(mgr.swap())
        # Now live=v2, staging=v1
        result = self._run(mgr.rollback())
        self.assertEqual(result.outcome, SwapOutcome.ROLLED_BACK)
        self.assertEqual(mgr.live.artifact_name, "model_v1")

    def test_swap_count(self) -> None:
        mgr = self._manager_with_slots()
        self.assertEqual(mgr.swap_count, 0)
        self._run(mgr.swap())
        self.assertEqual(mgr.swap_count, 1)

    def test_swap_result_summary(self) -> None:
        mgr = self._manager_with_slots()
        result = self._run(mgr.swap())
        self.assertIn("swapped", result.summary())


if __name__ == "__main__":
    unittest.main()
