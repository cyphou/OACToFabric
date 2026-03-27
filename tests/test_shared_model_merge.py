"""Tests for shared semantic model merge engine (Agent 04 — Semantic)."""

import json
import unittest

from src.agents.semantic.shared_model_merge import (
    MergeCandidate,
    MergeResult,
    TableFingerprint,
    extract_table_fingerprint,
    find_merge_candidates,
    generate_merge_manifest,
    jaccard_similarity,
    merge_semantic_models,
)


class TestTableFingerprint(unittest.TestCase):
    def test_fingerprint_hash(self):
        fp = TableFingerprint(
            table_name="Sales",
            source_model="ModelA",
            columns=["id", "amount", "date"],
            column_types={"id": "int64", "amount": "decimal", "date": "dateTime"},
            measures=["Total Sales"],
        )
        assert len(fp.fingerprint) == 16
        assert isinstance(fp.fingerprint, str)

    def test_same_columns_same_fingerprint(self):
        fp1 = TableFingerprint("T", "A", ["a", "b", "c"], {}, [])
        fp2 = TableFingerprint("T2", "B", ["a", "b", "c"], {}, [])
        assert fp1.fingerprint == fp2.fingerprint

    def test_different_columns_different_fingerprint(self):
        fp1 = TableFingerprint("T", "A", ["a", "b"], {}, [])
        fp2 = TableFingerprint("T", "A", ["a", "c"], {}, [])
        assert fp1.fingerprint != fp2.fingerprint


class TestJaccardSimilarity(unittest.TestCase):
    def test_identical_sets(self):
        assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard_similarity({"a"}, {"b"}) == 0.0

    def test_overlap(self):
        score = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert abs(score - 0.5) < 0.01  # 2/4

    def test_empty_sets(self):
        assert jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self):
        assert jaccard_similarity({"a"}, set()) == 0.0


class TestExtractTableFingerprint(unittest.TestCase):
    def test_extract_columns_and_measures(self):
        tmdl = """table 'Sales'
    column 'Id'
        dataType: int64
    column 'Amount'
        dataType: decimal
    measure 'Total Sales' = SUM('Sales'[Amount])
"""
        fp = extract_table_fingerprint("Sales", tmdl, "ModelA")
        assert fp.table_name == "Sales"
        assert "Id" in fp.columns
        assert "Amount" in fp.columns
        assert "Total Sales" in fp.measures
        assert fp.source_model == "ModelA"

    def test_empty_table(self):
        tmdl = "table 'Empty'\n"
        fp = extract_table_fingerprint("Empty", tmdl)
        assert fp.columns == []
        assert fp.measures == []


class TestFindMergeCandidates(unittest.TestCase):
    def test_finds_identical_tables(self):
        fps = [
            TableFingerprint("Sales", "A", ["id", "amount"], {}, []),
            TableFingerprint("Sales", "B", ["id", "amount"], {}, []),
        ]
        candidates = find_merge_candidates(fps, threshold=0.7)
        assert len(candidates) == 1
        assert candidates[0].jaccard_score == 1.0
        assert candidates[0].decision == "merge"

    def test_skips_same_model(self):
        fps = [
            TableFingerprint("T1", "A", ["a", "b"], {}, []),
            TableFingerprint("T2", "A", ["a", "b"], {}, []),
        ]
        candidates = find_merge_candidates(fps, threshold=0.7)
        assert len(candidates) == 0

    def test_below_threshold(self):
        fps = [
            TableFingerprint("T1", "A", ["a", "b", "c", "d"], {}, []),
            TableFingerprint("T2", "B", ["a"], {}, []),
        ]
        candidates = find_merge_candidates(fps, threshold=0.7)
        assert len(candidates) == 0

    def test_partial_overlap_review(self):
        fps = [
            TableFingerprint("T1", "A", ["a", "b", "c"], {}, []),
            TableFingerprint("T2", "B", ["b", "c", "d"], {}, []),
        ]
        # Jaccard = 2/4 = 0.5 — below 0.7 default
        candidates = find_merge_candidates(fps, threshold=0.4)
        assert len(candidates) == 1
        assert candidates[0].decision == "review"


class TestMergeSemanticModels(unittest.TestCase):
    def test_merge_identical_tables(self):
        models = {
            "ModelA": {
                "definition/tables/Sales.tmdl": "table 'Sales'\n    column 'Id'\n    column 'Amount'\n",
            },
            "ModelB": {
                "definition/tables/Sales.tmdl": "table 'Sales'\n    column 'Id'\n    column 'Amount'\n",
            },
        }
        result = merge_semantic_models(models, threshold=0.9)
        assert isinstance(result, MergeResult)
        assert result.merged_count >= 1
        assert len(result.thin_references) == 2

    def test_merge_different_tables_kept(self):
        models = {
            "ModelA": {
                "definition/tables/Sales.tmdl": "table 'Sales'\n    column 'Id'\n",
            },
            "ModelB": {
                "definition/tables/Products.tmdl": "table 'Products'\n    column 'Sku'\n",
            },
        }
        result = merge_semantic_models(models)
        assert len(result.shared_tables) == 2
        assert result.merged_count == 0

    def test_generate_manifest(self):
        result = MergeResult(
            shared_tables=[{"table_name": "Sales", "fingerprint": "abc"}],
            thin_references=[{"report_name": "R1"}],
            merge_decisions=[{"decision": "merge", "kept": "Sales", "merged": "Sales2"}],
        )
        manifest = generate_merge_manifest(result)
        parsed = json.loads(manifest)
        assert parsed["merge_summary"]["merged_count"] == 1
        assert len(parsed["shared_tables"]) == 1


class TestMergeResult(unittest.TestCase):
    def test_merged_count(self):
        r = MergeResult(merge_decisions=[
            {"decision": "merge"}, {"decision": "keep_both"}, {"decision": "merge"},
        ])
        assert r.merged_count == 2

    def test_kept_count(self):
        r = MergeResult(merge_decisions=[
            {"decision": "merge"}, {"decision": "keep_both"}, {"decision": "keep_both"},
        ])
        assert r.kept_count == 2


if __name__ == "__main__":
    unittest.main()
