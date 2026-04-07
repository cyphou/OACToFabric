"""Accuracy Scorer — compare translation output against golden corpus entries.

Supports exact match, normalised match (whitespace/case-insensitive), and
fuzzy match (token-level Jaccard similarity).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MatchLevel(str, Enum):
    """Granularity of match between actual and expected."""

    EXACT = "exact"
    NORMALISED = "normalised"
    FUZZY = "fuzzy"
    MISMATCH = "mismatch"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EntryScore:
    """Score for a single corpus entry."""

    entry_id: str
    category: str = ""
    difficulty: str = ""
    match_level: MatchLevel = MatchLevel.MISMATCH
    similarity: float = 0.0
    expected: str = ""
    actual: str = ""
    error: str = ""

    @property
    def passed(self) -> bool:
        return self.match_level != MatchLevel.MISMATCH

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "category": self.category,
            "difficulty": self.difficulty,
            "match_level": self.match_level.value,
            "similarity": round(self.similarity, 4),
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "error": self.error,
        }


@dataclass
class AccuracyReport:
    """Aggregated accuracy report across a corpus."""

    scores: list[EntryScore] = field(default_factory=list)
    fuzzy_threshold: float = 0.8

    @property
    def total(self) -> int:
        return len(self.scores)

    @property
    def exact_matches(self) -> int:
        return sum(1 for s in self.scores if s.match_level == MatchLevel.EXACT)

    @property
    def normalised_matches(self) -> int:
        return sum(1 for s in self.scores if s.match_level == MatchLevel.NORMALISED)

    @property
    def fuzzy_matches(self) -> int:
        return sum(1 for s in self.scores if s.match_level == MatchLevel.FUZZY)

    @property
    def mismatches(self) -> int:
        return sum(1 for s in self.scores if s.match_level == MatchLevel.MISMATCH)

    @property
    def errors(self) -> int:
        return sum(1 for s in self.scores if s.error)

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.total - self.mismatches) / self.total

    @property
    def exact_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.exact_matches / self.total

    def by_category(self) -> dict[str, dict[str, Any]]:
        cats: dict[str, list[EntryScore]] = {}
        for s in self.scores:
            cats.setdefault(s.category, []).append(s)
        result: dict[str, dict[str, Any]] = {}
        for cat, entries in cats.items():
            total = len(entries)
            passed = sum(1 for e in entries if e.passed)
            result[cat] = {"total": total, "passed": passed, "rate": passed / total if total else 0.0}
        return result

    def by_difficulty(self) -> dict[str, dict[str, Any]]:
        diffs: dict[str, list[EntryScore]] = {}
        for s in self.scores:
            diffs.setdefault(s.difficulty, []).append(s)
        result: dict[str, dict[str, Any]] = {}
        for diff, entries in diffs.items():
            total = len(entries)
            passed = sum(1 for e in entries if e.passed)
            result[diff] = {"total": total, "passed": passed, "rate": passed / total if total else 0.0}
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "exact_matches": self.exact_matches,
            "normalised_matches": self.normalised_matches,
            "fuzzy_matches": self.fuzzy_matches,
            "mismatches": self.mismatches,
            "errors": self.errors,
            "pass_rate": round(self.pass_rate, 4),
            "exact_rate": round(self.exact_rate, 4),
            "by_category": self.by_category(),
            "by_difficulty": self.by_difficulty(),
        }

    def summary(self) -> str:
        lines = [
            f"Accuracy: {self.pass_rate:.1%} pass rate ({self.total} entries)",
            f"  Exact:      {self.exact_matches}",
            f"  Normalised: {self.normalised_matches}",
            f"  Fuzzy:      {self.fuzzy_matches}",
            f"  Mismatch:   {self.mismatches}",
            f"  Errors:     {self.errors}",
        ]
        for cat, stats in self.by_category().items():
            lines.append(f"  [{cat}] {stats['passed']}/{stats['total']} ({stats['rate']:.0%})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokenise(text: str) -> set[str]:
    """Split on non-alphanumeric boundaries."""
    return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    intersection = a & b
    union = a | b
    return len(intersection) / len(union) if union else 0.0


class AccuracyScorer:
    """Score translations against a golden corpus.

    Parameters
    ----------
    fuzzy_threshold
        Minimum Jaccard similarity for a fuzzy match (default 0.8).
    """

    def __init__(self, fuzzy_threshold: float = 0.8) -> None:
        self.fuzzy_threshold = fuzzy_threshold

    def score_entry(
        self,
        entry_id: str,
        expected: str,
        actual: str,
        *,
        category: str = "",
        difficulty: str = "",
    ) -> EntryScore:
        """Score a single translation."""
        if not actual:
            return EntryScore(
                entry_id=entry_id,
                category=category,
                difficulty=difficulty,
                match_level=MatchLevel.MISMATCH,
                expected=expected,
                actual=actual,
                error="empty translation",
            )

        # Exact match
        if actual.strip() == expected.strip():
            return EntryScore(
                entry_id=entry_id,
                category=category,
                difficulty=difficulty,
                match_level=MatchLevel.EXACT,
                similarity=1.0,
                expected=expected,
                actual=actual,
            )

        # Normalised match
        if _normalise(actual) == _normalise(expected):
            return EntryScore(
                entry_id=entry_id,
                category=category,
                difficulty=difficulty,
                match_level=MatchLevel.NORMALISED,
                similarity=1.0,
                expected=expected,
                actual=actual,
            )

        # Fuzzy match
        sim = _jaccard(_tokenise(expected), _tokenise(actual))
        if sim >= self.fuzzy_threshold:
            return EntryScore(
                entry_id=entry_id,
                category=category,
                difficulty=difficulty,
                match_level=MatchLevel.FUZZY,
                similarity=sim,
                expected=expected,
                actual=actual,
            )

        return EntryScore(
            entry_id=entry_id,
            category=category,
            difficulty=difficulty,
            match_level=MatchLevel.MISMATCH,
            similarity=sim,
            expected=expected,
            actual=actual,
        )

    def score_corpus(
        self,
        entries: list[dict[str, Any]],
        translator: Any,
        *,
        field_key: str = "expected_dax",
    ) -> AccuracyReport:
        """Score an entire corpus using a translator callable.

        Parameters
        ----------
        entries
            List of corpus dicts with ``source``, ``expected_dax`` (or *field_key*),
            ``id``, ``category``, ``difficulty``.
        translator
            A callable ``(source: str) -> str`` that returns the translation.
        field_key
            Key in each entry for the expected output.
        """
        report = AccuracyReport(fuzzy_threshold=self.fuzzy_threshold)
        for entry in entries:
            entry_id = entry.get("id", "")
            source = entry.get("source", "")
            expected = entry.get(field_key, "")
            if not expected:
                continue

            try:
                actual = translator(source)
            except Exception as exc:  # noqa: BLE001
                report.scores.append(EntryScore(
                    entry_id=entry_id,
                    category=entry.get("category", ""),
                    difficulty=entry.get("difficulty", ""),
                    match_level=MatchLevel.MISMATCH,
                    expected=expected,
                    error=str(exc),
                ))
                continue

            score = self.score_entry(
                entry_id,
                expected,
                actual,
                category=entry.get("category", ""),
                difficulty=entry.get("difficulty", ""),
            )
            report.scores.append(score)

        return report
