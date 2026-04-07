"""Tests for Phase 79 — Idempotent Deployer."""

from __future__ import annotations

import asyncio
import unittest

from src.deployers.idempotent_deployer import (
    ArtifactState,
    DeployAction,
    IdempotentDeployer,
    IdempotentResult,
)


class TestIdempotentResult(unittest.TestCase):
    def test_success_for_created(self) -> None:
        r = IdempotentResult(artifact_type="table", artifact_name="t1", action=DeployAction.CREATED)
        self.assertTrue(r.success)

    def test_success_for_skipped(self) -> None:
        r = IdempotentResult(artifact_type="table", artifact_name="t1", action=DeployAction.SKIPPED)
        self.assertTrue(r.success)

    def test_not_success_for_failed(self) -> None:
        r = IdempotentResult(artifact_type="table", artifact_name="t1", action=DeployAction.FAILED)
        self.assertFalse(r.success)

    def test_to_dict(self) -> None:
        r = IdempotentResult(artifact_type="model", artifact_name="m1", action=DeployAction.UPDATED, new_version=2)
        d = r.to_dict()
        self.assertEqual(d["action"], "updated")
        self.assertEqual(d["new_version"], 2)


class TestIdempotentDeployer(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def test_create_new_artifact(self) -> None:
        deployer = IdempotentDeployer(workspace_id="ws-1")
        result = self._run(deployer.deploy("table", "t1", {"columns": ["id"]}))
        self.assertEqual(result.action, DeployAction.CREATED)
        self.assertEqual(result.new_version, 1)
        self.assertEqual(deployer.registered_count, 1)

    def test_update_existing_artifact(self) -> None:
        deployer = IdempotentDeployer(workspace_id="ws-1")
        self._run(deployer.deploy("table", "t1", {"columns": ["id"]}))
        result = self._run(deployer.deploy("table", "t1", {"columns": ["id", "name"]}))
        self.assertEqual(result.action, DeployAction.UPDATED)
        self.assertEqual(result.new_version, 2)

    def test_skip_identical_checksum(self) -> None:
        deployer = IdempotentDeployer(workspace_id="ws-1")
        self._run(deployer.deploy("table", "t1", {}, checksum="abc123"))
        result = self._run(deployer.deploy("table", "t1", {}, checksum="abc123"))
        self.assertEqual(result.action, DeployAction.SKIPPED)

    def test_force_redeploy(self) -> None:
        deployer = IdempotentDeployer(workspace_id="ws-1")
        self._run(deployer.deploy("table", "t1", {}, checksum="abc123"))
        result = self._run(deployer.deploy("table", "t1", {}, checksum="abc123", force=True))
        self.assertEqual(result.action, DeployAction.UPDATED)

    def test_dry_run(self) -> None:
        deployer = IdempotentDeployer(workspace_id="ws-1", dry_run=True)
        result = self._run(deployer.deploy("table", "t1", {"col": "id"}))
        self.assertEqual(result.action, DeployAction.CREATED)
        self.assertTrue(result.details.get("dry_run"))

    def test_register_and_lookup(self) -> None:
        deployer = IdempotentDeployer(workspace_id="ws-1")
        state = ArtifactState(artifact_id="x", artifact_name="t1", artifact_type="table", version=3)
        deployer.register(state)
        self.assertEqual(deployer.registered_count, 1)
        found = deployer.lookup("table", "t1")
        self.assertIsNotNone(found)
        self.assertEqual(found.version, 3)

    def test_deploy_batch(self) -> None:
        deployer = IdempotentDeployer(workspace_id="ws-1")
        items = [
            {"type": "table", "name": "t1", "definition": {}},
            {"type": "table", "name": "t2", "definition": {}},
        ]
        results = self._run(deployer.deploy_batch(items))
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.success for r in results))

    def test_summary(self) -> None:
        deployer = IdempotentDeployer(workspace_id="ws-1")
        s = deployer.summary()
        self.assertEqual(s["workspace_id"], "ws-1")


if __name__ == "__main__":
    unittest.main()
