"""Tests for Phase 79 — Deployment Manifest."""

from __future__ import annotations

import json
import unittest

from src.deployers.deployment_manifest import (
    DeploymentPlan,
    ManifestAction,
    ManifestArtifactType,
    ManifestBuilder,
    ManifestEntry,
)


class TestManifestEntry(unittest.TestCase):
    def test_key(self) -> None:
        e = ManifestEntry(artifact_type=ManifestArtifactType.LAKEHOUSE_TABLE, artifact_name="t1")
        self.assertEqual(e.key, "lakehouse_table::t1")

    def test_valid_when_no_errors(self) -> None:
        e = ManifestEntry(artifact_type=ManifestArtifactType.REPORT, artifact_name="r1")
        self.assertTrue(e.valid)

    def test_invalid_when_errors(self) -> None:
        e = ManifestEntry(
            artifact_type=ManifestArtifactType.REPORT,
            artifact_name="r1",
            validation_errors=["missing field"],
        )
        self.assertFalse(e.valid)


class TestManifestBuilder(unittest.TestCase):
    def test_add_table(self) -> None:
        builder = ManifestBuilder("ws-1")
        builder.add_table("dim_customer")
        self.assertEqual(builder.entry_count, 1)

    def test_add_semantic_model(self) -> None:
        builder = ManifestBuilder()
        builder.add_semantic_model("Sales Model")
        self.assertEqual(builder.entry_count, 1)

    def test_add_report(self) -> None:
        builder = ManifestBuilder()
        builder.add_report("Sales Dashboard")
        self.assertEqual(builder.entry_count, 1)

    def test_build_simple(self) -> None:
        builder = ManifestBuilder("ws-1")
        builder.add_table("t1")
        builder.add_table("t2")
        plan = builder.build()
        self.assertEqual(plan.artifact_count, 2)
        self.assertTrue(plan.deployable)
        self.assertEqual(len(plan.deployment_order), 2)

    def test_topological_order_respects_dependencies(self) -> None:
        builder = ManifestBuilder()
        builder.add(ManifestEntry(
            artifact_type=ManifestArtifactType.SEMANTIC_MODEL,
            artifact_name="model",
            dependencies=["lakehouse_table::t1"],
        ))
        builder.add(ManifestEntry(
            artifact_type=ManifestArtifactType.LAKEHOUSE_TABLE,
            artifact_name="t1",
        ))
        plan = builder.build()
        order = plan.deployment_order
        t1_idx = order.index("lakehouse_table::t1")
        model_idx = order.index("semantic_model::model")
        self.assertLess(t1_idx, model_idx, "Table should deploy before model")

    def test_circular_dependency_produces_blocker(self) -> None:
        builder = ManifestBuilder()
        builder.add(ManifestEntry(
            artifact_type=ManifestArtifactType.LAKEHOUSE_TABLE,
            artifact_name="a",
            dependencies=["lakehouse_table::b"],
        ))
        builder.add(ManifestEntry(
            artifact_type=ManifestArtifactType.LAKEHOUSE_TABLE,
            artifact_name="b",
            dependencies=["lakehouse_table::a"],
        ))
        plan = builder.build()
        self.assertTrue(plan.has_blockers)
        self.assertFalse(plan.deployable)

    def test_unknown_dependency_warning(self) -> None:
        builder = ManifestBuilder()
        builder.add(ManifestEntry(
            artifact_type=ManifestArtifactType.REPORT,
            artifact_name="r1",
            dependencies=["semantic_model::nonexistent"],
        ))
        plan = builder.build()
        self.assertTrue(len(plan.warnings) > 0)

    def test_to_json(self) -> None:
        builder = ManifestBuilder("ws-1")
        builder.add_table("t1")
        j = builder.to_json()
        data = json.loads(j)
        self.assertEqual(data["artifact_count"], 1)


class TestDeploymentPlan(unittest.TestCase):
    def test_summary(self) -> None:
        plan = DeploymentPlan(
            workspace_id="ws-1",
            entries=[
                ManifestEntry(artifact_type=ManifestArtifactType.LAKEHOUSE_TABLE, artifact_name="t1"),
            ],
            deployment_order=["lakehouse_table::t1"],
        )
        s = plan.summary()
        self.assertIn("READY", s)
        self.assertIn("1", s)

    def test_blocked_summary(self) -> None:
        plan = DeploymentPlan(blockers=["circular dep"])
        self.assertIn("BLOCKED", plan.summary())


if __name__ == "__main__":
    unittest.main()
