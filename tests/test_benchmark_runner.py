"""Tests for Phase 81 — Benchmark Runner."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.benchmarks.benchmark_runner import BenchmarkConfig, BenchmarkRunner

_CORPUS = Path(__file__).resolve().parent / "benchmarks" / "golden_corpus.json"


class TestBenchmarkConfig(unittest.TestCase):
    def test_defaults(self) -> None:
        cfg = BenchmarkConfig()
        self.assertEqual(cfg.min_pass_rate, 0.70)
        self.assertEqual(cfg.fuzzy_threshold, 0.80)

    def test_corpus_exists(self) -> None:
        self.assertTrue(_CORPUS.exists(), f"Golden corpus not found at {_CORPUS}")


class TestBenchmarkRunner(unittest.TestCase):
    def test_run_with_identity(self) -> None:
        """Identity translator — low pass rate expected (echoes source, no conversion)."""
        runner = BenchmarkRunner(BenchmarkConfig(min_pass_rate=0.0))
        result = runner.run(lambda src: src)
        self.assertGreater(result.total_entries, 0)
        self.assertGreaterEqual(result.pass_rate, 0.0)

    def test_run_with_perfect_translator(self) -> None:
        """Load corpus and supply exact expected values."""
        corpus = json.loads(_CORPUS.read_text(encoding="utf-8"))
        lookup = {e["source"]: e.get("expected_dax", "") for e in corpus["entries"]}

        def perfect(src: str) -> str:
            return lookup.get(src, "")

        runner = BenchmarkRunner(BenchmarkConfig(min_pass_rate=0.0, corpus_path=str(_CORPUS)))
        result = runner.run(perfect)
        # DAX entries should match exactly; pyspark entries return "" → mismatch
        self.assertGreater(result.pass_rate, 0.5)

    def test_ci_gate_fail(self) -> None:
        """Gate should fail when pass rate < threshold."""
        runner = BenchmarkRunner(BenchmarkConfig(min_pass_rate=1.0))
        result = runner.run(lambda src: "wrong")
        self.assertFalse(result.passed_ci_gate)

    def test_category_filter(self) -> None:
        runner = BenchmarkRunner(BenchmarkConfig(categories=["arithmetic"], min_pass_rate=0.0))
        result = runner.run(lambda src: src)
        self.assertGreater(result.total_entries, 0)
        self.assertLessEqual(result.total_entries, 10)  # only arithmetic entries

    def test_result_to_dict(self) -> None:
        runner = BenchmarkRunner(BenchmarkConfig(min_pass_rate=0.0))
        result = runner.run(lambda src: src)
        d = result.to_dict()
        self.assertIn("pass_rate", d)
        self.assertIn("duration_seconds", d)


if __name__ == "__main__":
    unittest.main()
