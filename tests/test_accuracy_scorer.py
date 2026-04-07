"""Tests for Phase 81 — Accuracy Scorer."""

from __future__ import annotations

import unittest

from tests.benchmarks.accuracy_scorer import (
    AccuracyReport,
    AccuracyScorer,
    EntryScore,
    MatchLevel,
)


class TestEntryScore(unittest.TestCase):
    def test_passed_exact(self) -> None:
        s = EntryScore(entry_id="1", match_level=MatchLevel.EXACT, similarity=1.0)
        self.assertTrue(s.passed)

    def test_not_passed_mismatch(self) -> None:
        s = EntryScore(entry_id="1", match_level=MatchLevel.MISMATCH, similarity=0.3)
        self.assertFalse(s.passed)

    def test_to_dict(self) -> None:
        s = EntryScore(entry_id="1", category="lod", difficulty="high", match_level=MatchLevel.FUZZY, similarity=0.85)
        d = s.to_dict()
        self.assertEqual(d["category"], "lod")
        self.assertTrue(d["passed"])


class TestAccuracyScorer(unittest.TestCase):
    def test_exact_match(self) -> None:
        scorer = AccuracyScorer()
        s = scorer.score_entry("e1", "SUM([Revenue])", "SUM([Revenue])")
        self.assertEqual(s.match_level, MatchLevel.EXACT)

    def test_normalised_match(self) -> None:
        scorer = AccuracyScorer()
        s = scorer.score_entry("e1", "SUM( [Revenue] )", "sum( [revenue] )")
        self.assertEqual(s.match_level, MatchLevel.NORMALISED)

    def test_fuzzy_match(self) -> None:
        scorer = AccuracyScorer(fuzzy_threshold=0.6)
        s = scorer.score_entry("e1", "CALCULATE(SUM([Revenue]), ALL(Table))", "CALCULATE(SUM([Revenue]), ALLEXCEPT(Table, Table[Col]))")
        self.assertIn(s.match_level, {MatchLevel.FUZZY, MatchLevel.MISMATCH})

    def test_mismatch(self) -> None:
        scorer = AccuracyScorer()
        s = scorer.score_entry("e1", "SUM([Revenue])", "COMPLETELY_DIFFERENT_OUTPUT()")
        self.assertEqual(s.match_level, MatchLevel.MISMATCH)

    def test_empty_actual(self) -> None:
        scorer = AccuracyScorer()
        s = scorer.score_entry("e1", "SUM([Revenue])", "")
        self.assertEqual(s.match_level, MatchLevel.MISMATCH)
        self.assertEqual(s.error, "empty translation")

    def test_score_corpus(self) -> None:
        scorer = AccuracyScorer()
        entries = [
            {"id": "e1", "source": "SUM(Revenue)", "expected_dax": "SUM([Revenue])", "category": "agg", "difficulty": "low"},
            {"id": "e2", "source": "AVG(Amount)", "expected_dax": "AVERAGE([Amount])", "category": "agg", "difficulty": "low"},
        ]
        # Identity translator — only e1 has a chance of matching
        report = scorer.score_corpus(entries, lambda s: s)
        self.assertEqual(report.total, 2)

    def test_score_corpus_with_exception(self) -> None:
        scorer = AccuracyScorer()
        entries = [{"id": "e1", "source": "bad", "expected_dax": "good", "category": "x", "difficulty": "low"}]

        def fail_translator(src: str) -> str:
            raise ValueError("boom")

        report = scorer.score_corpus(entries, fail_translator)
        self.assertEqual(report.errors, 1)


class TestAccuracyReport(unittest.TestCase):
    def test_pass_rate(self) -> None:
        report = AccuracyReport(scores=[
            EntryScore(entry_id="1", match_level=MatchLevel.EXACT),
            EntryScore(entry_id="2", match_level=MatchLevel.NORMALISED),
            EntryScore(entry_id="3", match_level=MatchLevel.MISMATCH),
        ])
        self.assertAlmostEqual(report.pass_rate, 2 / 3, places=4)

    def test_by_category(self) -> None:
        report = AccuracyReport(scores=[
            EntryScore(entry_id="1", category="agg", match_level=MatchLevel.EXACT),
            EntryScore(entry_id="2", category="agg", match_level=MatchLevel.MISMATCH),
            EntryScore(entry_id="3", category="lod", match_level=MatchLevel.EXACT),
        ])
        cats = report.by_category()
        self.assertEqual(cats["agg"]["total"], 2)
        self.assertEqual(cats["agg"]["passed"], 1)
        self.assertEqual(cats["lod"]["passed"], 1)

    def test_summary(self) -> None:
        report = AccuracyReport(scores=[
            EntryScore(entry_id="1", category="agg", match_level=MatchLevel.EXACT),
        ])
        s = report.summary()
        self.assertIn("100.0%", s)

    def test_empty_report(self) -> None:
        report = AccuracyReport()
        self.assertEqual(report.pass_rate, 0.0)
        self.assertEqual(report.exact_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
