"""Tests for materialized_view_generator — Oracle MV → Fabric MV."""

from __future__ import annotations

import unittest

from src.agents.schema.materialized_view_generator import (
    FabricMVResult,
    MaterializedViewDef,
    RefreshMode,
    detect_mv_candidates,
    generate_all_mvs,
    generate_fabric_mv,
    parse_oracle_mv,
)


class TestParseOracleMV(unittest.TestCase):

    def test_basic_mv(self):
        ddl = """
        CREATE MATERIALIZED VIEW sales_summary
        AS SELECT region, SUM(amount) AS total
        FROM sales GROUP BY region
        """
        mv = parse_oracle_mv(ddl)
        self.assertEqual(mv.name, "sales_summary")
        self.assertIn("SELECT", mv.query)

    def test_refresh_fast(self):
        ddl = """
        CREATE MATERIALIZED VIEW mv_fast
        REFRESH FAST ON COMMIT
        AS SELECT id FROM t
        """
        mv = parse_oracle_mv(ddl)
        self.assertEqual(mv.refresh_mode, RefreshMode.FAST)

    def test_refresh_complete(self):
        ddl = """
        CREATE MATERIALIZED VIEW mv_comp
        REFRESH COMPLETE ON DEMAND
        AS SELECT 1 FROM dual
        """
        mv = parse_oracle_mv(ddl)
        self.assertEqual(mv.refresh_mode, RefreshMode.COMPLETE)

    def test_schema_qualified_name(self):
        ddl = "CREATE MATERIALIZED VIEW schema1.mv1 AS SELECT 1 FROM dual"
        mv = parse_oracle_mv(ddl)
        self.assertIn("mv1", mv.name)


class TestGenerateFabricMV(unittest.TestCase):

    def test_basic_generation(self):
        mv = MaterializedViewDef(
            name="sales_mv",
            query="SELECT region, SUM(amount) AS total FROM sales GROUP BY region",
        )
        result = generate_fabric_mv(mv)
        self.assertIn("CREATE MATERIALIZED VIEW", result.ddl)
        self.assertIn("sales_mv", result.ddl)

    def test_target_schema(self):
        mv = MaterializedViewDef(name="mv1", query="SELECT 1")
        result = generate_fabric_mv(mv, target_schema="dbo")
        self.assertIn("dbo", result.ddl)


class TestDetectMVCandidates(unittest.TestCase):

    def test_detects_large_tables(self):
        tables = [
            {"name": "big_table", "estimated_rows": 2_000_000, "is_view": True},
            {"name": "small_table", "estimated_rows": 100, "is_view": True},
        ]
        candidates = detect_mv_candidates(tables, threshold_rows=1_000_000)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0], "big_table")

    def test_empty_tables(self):
        candidates = detect_mv_candidates([])
        self.assertEqual(candidates, [])


class TestGenerateAllMVs(unittest.TestCase):

    def test_multiple_mvs(self):
        ddls = [
            "CREATE MATERIALIZED VIEW mv1 AS SELECT 1 FROM dual",
            "CREATE MATERIALIZED VIEW mv2 AS SELECT 2 FROM dual",
        ]
        results = generate_all_mvs(ddls)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
