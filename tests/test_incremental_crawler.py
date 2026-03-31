"""Tests for incremental_crawler — change detection between inventory snapshots."""

from __future__ import annotations

import json
import unittest

from src.agents.discovery.incremental_crawler import (
    AssetFingerprint,
    ChangeRecord,
    IncrementalResult,
    compute_fingerprint,
    detect_changes,
    fingerprints_from_json,
    fingerprints_to_json,
)


class TestComputeFingerprint(unittest.TestCase):

    def test_string_content(self):
        fp = compute_fingerprint("a1", "table", "Sales", "CREATE TABLE Sales (id INT)")
        self.assertEqual(fp.asset_id, "a1")
        self.assertEqual(fp.asset_type, "table")
        self.assertIsInstance(fp.hash, str)
        self.assertEqual(len(fp.hash), 64)  # SHA-256

    def test_dict_content(self):
        fp = compute_fingerprint("a2", "analysis", "Report1", {"cols": ["a", "b"]})
        self.assertEqual(len(fp.hash), 64)

    def test_deterministic_hash(self):
        fp1 = compute_fingerprint("a", "t", "N", "content")
        fp2 = compute_fingerprint("a", "t", "N", "content")
        self.assertEqual(fp1.hash, fp2.hash)

    def test_different_content_different_hash(self):
        fp1 = compute_fingerprint("a", "t", "N", "v1")
        fp2 = compute_fingerprint("a", "t", "N", "v2")
        self.assertNotEqual(fp1.hash, fp2.hash)


class TestDetectChanges(unittest.TestCase):

    def test_no_changes(self):
        fps = [AssetFingerprint(asset_id="a", asset_type="t", name="N", hash="h1")]
        result = detect_changes(fps, fps)
        self.assertFalse(result.has_changes)
        self.assertEqual(result.unchanged_count, 1)

    def test_added(self):
        prev = []
        curr = [AssetFingerprint(asset_id="a", asset_type="t", name="N", hash="h1")]
        result = detect_changes(prev, curr)
        self.assertEqual(len(result.added), 1)
        self.assertEqual(result.added[0].change_type, "added")

    def test_modified(self):
        prev = [AssetFingerprint(asset_id="a", asset_type="t", name="N", hash="h1")]
        curr = [AssetFingerprint(asset_id="a", asset_type="t", name="N", hash="h2")]
        result = detect_changes(prev, curr)
        self.assertEqual(len(result.modified), 1)
        self.assertEqual(result.modified[0].old_hash, "h1")
        self.assertEqual(result.modified[0].new_hash, "h2")

    def test_removed(self):
        prev = [AssetFingerprint(asset_id="a", asset_type="t", name="N", hash="h1")]
        curr = []
        result = detect_changes(prev, curr)
        self.assertEqual(len(result.removed), 1)
        self.assertEqual(result.removed[0].change_type, "removed")

    def test_mixed_changes(self):
        prev = [
            AssetFingerprint(asset_id="a", asset_type="t", name="A", hash="h1"),
            AssetFingerprint(asset_id="b", asset_type="t", name="B", hash="h2"),
            AssetFingerprint(asset_id="c", asset_type="t", name="C", hash="h3"),
        ]
        curr = [
            AssetFingerprint(asset_id="a", asset_type="t", name="A", hash="h1"),   # unchanged
            AssetFingerprint(asset_id="b", asset_type="t", name="B", hash="h2x"),  # modified
            AssetFingerprint(asset_id="d", asset_type="t", name="D", hash="h4"),   # added
        ]
        result = detect_changes(prev, curr)
        self.assertEqual(result.unchanged_count, 1)
        self.assertEqual(len(result.modified), 1)
        self.assertEqual(len(result.removed), 1)
        self.assertEqual(len(result.added), 1)
        self.assertEqual(result.total_changes, 3)


class TestIncrementalResult(unittest.TestCase):

    def test_affected_asset_ids(self):
        result = IncrementalResult(
            added=[ChangeRecord(asset_id="a1", asset_type="t", name="A", change_type="added")],
            modified=[ChangeRecord(asset_id="a2", asset_type="t", name="B", change_type="modified")],
        )
        ids = result.affected_asset_ids()
        self.assertIn("a1", ids)
        self.assertIn("a2", ids)

    def test_affected_types(self):
        result = IncrementalResult(
            added=[ChangeRecord(asset_id="a1", asset_type="table", name="A", change_type="added")],
            modified=[ChangeRecord(asset_id="a2", asset_type="analysis", name="B", change_type="modified")],
        )
        types = result.affected_types()
        self.assertIn("table", types)
        self.assertIn("analysis", types)

    def test_summary(self):
        result = IncrementalResult(
            added=[ChangeRecord(asset_id="a", asset_type="t", name="A", change_type="added")],
        )
        self.assertIn("1 added", result.summary())


class TestFingerprintSerialization(unittest.TestCase):

    def test_roundtrip(self):
        fps = [
            AssetFingerprint(asset_id="a1", asset_type="table", name="Sales", hash="abc123"),
            AssetFingerprint(asset_id="a2", asset_type="analysis", name="Report", hash="def456"),
        ]
        json_text = fingerprints_to_json(fps)
        restored = fingerprints_from_json(json_text)
        self.assertEqual(len(restored), 2)
        self.assertEqual(restored[0].asset_id, "a1")
        self.assertEqual(restored[1].hash, "def456")


if __name__ == "__main__":
    unittest.main()
