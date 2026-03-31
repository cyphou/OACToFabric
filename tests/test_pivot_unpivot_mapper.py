"""Tests for pivot_unpivot_mapper — ETL pivot/unpivot transformations."""

from __future__ import annotations

import unittest

from src.agents.etl.pivot_unpivot_mapper import (
    ParallelBranchSpec,
    PivotSpec,
    TransformationOutput,
    UnpivotSpec,
    generate_parallel_branches,
    generate_pivot,
    generate_unpivot,
)


class TestGeneratePivot(unittest.TestCase):

    def test_basic_pivot(self):
        spec = PivotSpec(
            group_by_columns=["Region", "Year"],
            pivot_column="Quarter",
            value_column="Sales",
            aggregation="sum",
        )
        result = generate_pivot(spec)
        self.assertIn("Table.Pivot", result.m_query)
        self.assertIn(".pivot", result.pyspark_code)
        self.assertEqual(result.pipeline_json["type"], "Pivot")

    def test_pivot_with_explicit_values(self):
        spec = PivotSpec(
            group_by_columns=["Region"],
            pivot_column="Status",
            value_column="Count",
            pivot_values=["Active", "Inactive"],
        )
        result = generate_pivot(spec)
        self.assertIn("Active", result.pyspark_code)
        self.assertIn("Inactive", result.pyspark_code)

    def test_different_aggregations(self):
        for agg in ("sum", "count", "avg", "min", "max"):
            spec = PivotSpec(
                group_by_columns=["A"],
                pivot_column="B",
                value_column="C",
                aggregation=agg,
            )
            result = generate_pivot(spec)
            self.assertIn("Pivot", result.m_query)
            self.assertIn(agg, result.pyspark_code)


class TestGenerateUnpivot(unittest.TestCase):

    def test_basic_unpivot(self):
        spec = UnpivotSpec(
            id_columns=["Region"],
            unpivot_columns=["Q1", "Q2", "Q3", "Q4"],
        )
        result = generate_unpivot(spec)
        self.assertIn("UnpivotOtherColumns", result.m_query)
        self.assertIn("stack(4", result.pyspark_code)
        self.assertEqual(result.pipeline_json["type"], "Unpivot")

    def test_unpivot_include_nulls(self):
        spec = UnpivotSpec(
            id_columns=["ID"],
            unpivot_columns=["A", "B"],
            only_non_null=False,
        )
        result = generate_unpivot(spec)
        self.assertIn("Table.Unpivot(", result.m_query)
        self.assertNotIn("isNotNull", result.pyspark_code)

    def test_custom_column_names(self):
        spec = UnpivotSpec(
            id_columns=["ID"],
            unpivot_columns=["X"],
            attribute_column="Metric",
            value_column="Amount",
        )
        result = generate_unpivot(spec)
        self.assertIn("Metric", result.m_query)
        self.assertIn("Amount", result.pyspark_code)


class TestGenerateParallelBranches(unittest.TestCase):

    def test_basic_branches(self):
        branches = [
            ParallelBranchSpec(branch_name="Branch1", step_names=["S1"]),
            ParallelBranchSpec(branch_name="Branch2", step_names=["S2"]),
        ]
        result = generate_parallel_branches(branches)
        self.assertEqual(len(result["properties"]["activities"]), 2)
        self.assertEqual(result["properties"]["concurrency"], 2)

    def test_branch_dependencies(self):
        branches = [
            ParallelBranchSpec(branch_name="B1"),
            ParallelBranchSpec(branch_name="B2", depends_on=["B1"]),
        ]
        result = generate_parallel_branches(branches)
        b2 = result["properties"]["activities"][1]
        self.assertEqual(len(b2["dependsOn"]), 1)
        self.assertEqual(b2["dependsOn"][0]["activity"], "B1")


if __name__ == "__main__":
    unittest.main()
