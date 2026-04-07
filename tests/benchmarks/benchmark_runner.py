"""Benchmark Runner — load the golden corpus, invoke the translator, and report accuracy.

Can be run as a pytest test (CI gate) or standalone script.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Resolve corpus path relative to this file
_CORPUS_PATH = Path(__file__).parent / "golden_corpus.json"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    corpus_path: str = str(_CORPUS_PATH)
    min_pass_rate: float = 0.70
    fuzzy_threshold: float = 0.80
    field_key: str = "expected_dax"
    categories: list[str] = field(default_factory=list)  # empty = all


@dataclass
class BenchmarkResult:
    """Result of a full benchmark run."""

    pass_rate: float = 0.0
    exact_rate: float = 0.0
    total_entries: int = 0
    duration_seconds: float = 0.0
    passed_ci_gate: bool = False
    min_pass_rate: float = 0.70
    report_dict: dict[str, Any] = field(default_factory=dict)
    summary_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_rate": round(self.pass_rate, 4),
            "exact_rate": round(self.exact_rate, 4),
            "total_entries": self.total_entries,
            "duration_seconds": round(self.duration_seconds, 3),
            "passed_ci_gate": self.passed_ci_gate,
            "min_pass_rate": self.min_pass_rate,
        }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class BenchmarkRunner:
    """Run the translation accuracy benchmark."""

    def __init__(self, config: BenchmarkConfig | None = None) -> None:
        self.config = config or BenchmarkConfig()

    def _load_corpus(self) -> list[dict[str, Any]]:
        path = Path(self.config.corpus_path)
        if not path.exists():
            raise FileNotFoundError(f"Golden corpus not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        entries: list[dict[str, Any]] = data.get("entries", [])
        if self.config.categories:
            entries = [e for e in entries if e.get("category") in self.config.categories]
        return entries

    def run(self, translator: Any) -> BenchmarkResult:
        """Execute the benchmark."""
        from tests.benchmarks.accuracy_scorer import AccuracyScorer

        entries = self._load_corpus()
        scorer = AccuracyScorer(fuzzy_threshold=self.config.fuzzy_threshold)

        t0 = time.monotonic()
        report = scorer.score_corpus(entries, translator, field_key=self.config.field_key)
        elapsed = time.monotonic() - t0

        passed_gate = report.pass_rate >= self.config.min_pass_rate

        result = BenchmarkResult(
            pass_rate=report.pass_rate,
            exact_rate=report.exact_rate,
            total_entries=report.total,
            duration_seconds=elapsed,
            passed_ci_gate=passed_gate,
            min_pass_rate=self.config.min_pass_rate,
            report_dict=report.to_dict(),
            summary_text=report.summary(),
        )

        logger.info(
            "Benchmark done: %d entries, %.1f%% pass rate (%s gate at %.0f%%)",
            result.total_entries,
            result.pass_rate * 100,
            "PASSED" if passed_gate else "FAILED",
            self.config.min_pass_rate * 100,
        )
        return result


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------


def _identity_translator(source: str) -> str:
    """Stub translator that echoes input — for self-test only."""
    return source


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    runner = BenchmarkRunner()
    result = runner.run(_identity_translator)
    print(result.summary_text)
    sys.exit(0 if result.passed_ci_gate else 1)


if __name__ == "__main__":
    main()
