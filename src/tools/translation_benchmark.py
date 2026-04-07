"""Translation Benchmark CLI — run accuracy benchmarks from the command line.

Usage
-----
::

    python -m src.tools.translation_benchmark --corpus tests/benchmarks/golden_corpus.json \\
        --min-pass-rate 0.75 --output output/benchmark_report.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _build_translator() -> Any:
    """Build the default expression translator for benchmarking."""
    try:
        from src.core.expression_translator import ExpressionTranslator

        t = ExpressionTranslator()
        return t.translate
    except ImportError:
        logger.warning("ExpressionTranslator not available — using identity stub")
        return lambda source: source


def run_benchmark(
    *,
    corpus_path: str = "",
    min_pass_rate: float = 0.70,
    fuzzy_threshold: float = 0.80,
    output_path: str = "",
    categories: list[str] | None = None,
) -> int:
    """Execute the benchmark and optionally write results to JSON."""
    from tests.benchmarks.benchmark_runner import BenchmarkConfig, BenchmarkRunner

    config = BenchmarkConfig(
        min_pass_rate=min_pass_rate,
        fuzzy_threshold=fuzzy_threshold,
        categories=categories or [],
    )
    if corpus_path:
        config.corpus_path = corpus_path

    runner = BenchmarkRunner(config)
    translator = _build_translator()
    result = runner.run(translator)

    print(result.summary_text)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), indent=2))
        logger.info("Report written to %s", out)

    return 0 if result.passed_ci_gate else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run translation accuracy benchmark")
    parser.add_argument("--corpus", default="", help="Path to golden_corpus.json")
    parser.add_argument("--min-pass-rate", type=float, default=0.70, help="CI gate threshold (0.0-1.0)")
    parser.add_argument("--fuzzy-threshold", type=float, default=0.80, help="Jaccard threshold for fuzzy match")
    parser.add_argument("--output", default="", help="Write JSON report to this path")
    parser.add_argument("--categories", nargs="*", default=None, help="Filter corpus by category")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    rc = run_benchmark(
        corpus_path=args.corpus,
        min_pass_rate=args.min_pass_rate,
        fuzzy_threshold=args.fuzzy_threshold,
        output_path=args.output,
        categories=args.categories,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
