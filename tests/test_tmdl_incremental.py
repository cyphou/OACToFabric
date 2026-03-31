"""Tests for tmdl_incremental — delta-based TMDL updates."""

from __future__ import annotations

import unittest

from src.agents.semantic.tmdl_incremental import (
    TMDLDeltaPlan,
    TMDLFileOp,
    compute_tmdl_delta,
)


class TestTMDLDeltaPlan(unittest.TestCase):

    def test_summary_empty(self):
        plan = TMDLDeltaPlan()
        self.assertIn("0 create", plan.summary())
        self.assertEqual(plan.total_operations, 0)

    def test_summary_with_ops(self):
        plan = TMDLDeltaPlan(
            operations=[
                TMDLFileOp(operation="create", file_path="t.tmdl"),
                TMDLFileOp(operation="update", file_path="u.tmdl"),
            ],
            affected_tables=["T1", "T2"],
        )
        self.assertEqual(plan.total_operations, 2)
        self.assertIn("1 create", plan.summary())
        self.assertIn("1 update", plan.summary())

    def test_full_rebuild_summary(self):
        plan = TMDLDeltaPlan(requires_full_rebuild=True, rebuild_reason="model changed")
        self.assertIn("Full rebuild", plan.summary())


class TestComputeTMDLDelta(unittest.TestCase):

    def test_added_table(self):
        changes = [
            {
                "asset_id": "t1",
                "asset_type": "table",
                "change_type": "added",
                "name": "Sales",
                "columns": [
                    {"name": "Id", "dataType": "Int64"},
                    {"name": "Amount", "dataType": "Double"},
                ],
            }
        ]
        plan = compute_tmdl_delta(changes)
        self.assertFalse(plan.requires_full_rebuild)
        self.assertEqual(len(plan.operations), 1)
        self.assertEqual(plan.operations[0].operation, "create")
        self.assertIn("Sales", plan.operations[0].file_path)
        self.assertIn("table 'Sales'", plan.operations[0].content)

    def test_modified_table(self):
        changes = [
            {
                "asset_id": "t2",
                "asset_type": "table",
                "change_type": "modified",
                "name": "Orders",
                "columns": [{"name": "OrderId", "dataType": "String"}],
            }
        ]
        plan = compute_tmdl_delta(changes)
        self.assertEqual(plan.operations[0].operation, "update")

    def test_removed_table(self):
        changes = [
            {"asset_id": "t3", "asset_type": "table", "change_type": "removed", "name": "OldTable"}
        ]
        plan = compute_tmdl_delta(changes)
        self.assertEqual(plan.operations[0].operation, "delete")

    def test_model_level_forces_rebuild(self):
        changes = [
            {"asset_id": "m1", "asset_type": "model", "change_type": "modified", "name": "MainModel"}
        ]
        plan = compute_tmdl_delta(changes)
        self.assertTrue(plan.requires_full_rebuild)

    def test_measure_change(self):
        changes = [
            {
                "asset_id": "m1",
                "asset_type": "measure",
                "change_type": "added",
                "name": "TotalSales",
                "table": "Sales",
                "expression": "SUM(Sales[Amount])",
            }
        ]
        plan = compute_tmdl_delta(changes)
        self.assertIn("TotalSales", plan.affected_measures)

    def test_relationship_change(self):
        changes = [
            {"asset_id": "r1", "asset_type": "relationship", "change_type": "modified", "name": "Rel1"}
        ]
        plan = compute_tmdl_delta(changes)
        self.assertIn("Rel1", plan.affected_relationships)
        self.assertIn("relationships.tmdl", plan.operations[0].file_path)

    def test_empty_changes(self):
        plan = compute_tmdl_delta([])
        self.assertEqual(plan.total_operations, 0)
        self.assertFalse(plan.requires_full_rebuild)


if __name__ == "__main__":
    unittest.main()
