"""Tests for the resilience module — Unicode, cycles, locking, backoff."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.core.resilience import (
    AdaptiveBackoff,
    MigrationLock,
    break_cycles,
    detect_cycles,
    normalize_name,
    sanitize_identifier,
)


# ---------------------------------------------------------------------------
# Unicode normalization
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_simple_name(self):
        assert normalize_name("Sales_Report") == "Sales_Report"

    def test_spaces_replaced(self):
        assert normalize_name("Sales Report") == "Sales_Report"

    def test_special_chars_replaced(self):
        result = normalize_name("Sales @#$ Report!")
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result

    def test_unicode_transliterated(self):
        result = normalize_name("Ärger über Straße")
        # Should attempt ASCII transliteration
        assert result  # non-empty
        assert all(ord(c) < 128 for c in result)

    def test_accented_chars(self):
        result = normalize_name("café résumé")
        assert "cafe" in result.lower()

    def test_max_length_truncation(self):
        long_name = "A" * 200
        result = normalize_name(long_name, max_length=50)
        assert len(result) <= 50

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_only_special_chars(self):
        result = normalize_name("@#$%^&*()")
        assert result == "unnamed"

    def test_collapses_multiple_underscores(self):
        result = normalize_name("a___b___c")
        assert "___" not in result

    def test_hyphens_preserved(self):
        result = normalize_name("my-report-name")
        assert "-" in result

    def test_dots_preserved(self):
        result = normalize_name("schema.table")
        assert "." in result


class TestSanitizeIdentifier:
    def test_simple_identifier(self):
        assert sanitize_identifier("my_column") == "my_column"

    def test_starts_with_number(self):
        result = sanitize_identifier("123abc")
        assert result[0] == "_" or result[0].isalpha()

    def test_reserved_word(self):
        result = sanitize_identifier("select")
        assert result != "select"  # Should be modified
        assert result.startswith("select")

    def test_special_chars_removed(self):
        result = sanitize_identifier("col@name#1")
        assert "@" not in result
        assert "#" not in result


# ---------------------------------------------------------------------------
# Circular dependency detection
# ---------------------------------------------------------------------------


class TestDetectCycles:
    def test_no_cycle(self):
        edges = [("A", "B"), ("B", "C"), ("A", "C")]
        cycles = detect_cycles(edges)
        assert len(cycles) == 0

    def test_simple_cycle(self):
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        cycles = detect_cycles(edges)
        assert len(cycles) >= 1
        # At least one cycle should contain A, B, C
        all_nodes = set()
        for cycle in cycles:
            all_nodes.update(cycle)
        assert {"A", "B", "C"}.issubset(all_nodes)

    def test_self_loop(self):
        edges = [("A", "A")]
        cycles = detect_cycles(edges)
        assert len(cycles) >= 1

    def test_multiple_cycles(self):
        edges = [
            ("A", "B"), ("B", "A"),  # cycle 1
            ("C", "D"), ("D", "C"),  # cycle 2
        ]
        cycles = detect_cycles(edges)
        assert len(cycles) >= 2

    def test_empty_graph(self):
        assert detect_cycles([]) == []


class TestBreakCycles:
    def test_breaks_simple_cycle(self):
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        kept, removed = break_cycles(edges)
        assert len(removed) >= 1
        # Remaining graph should have no cycles
        assert detect_cycles(kept) == []

    def test_respects_priority(self):
        edges = [("A", "B"), ("B", "A")]
        priority = {"A": 10, "B": 1}  # B is lower priority
        kept, removed = break_cycles(edges, priority=priority)
        assert len(removed) == 1
        # Should remove the edge from B (lower priority source)
        assert removed[0][0] == "B"

    def test_no_cycles_returns_all(self):
        edges = [("A", "B"), ("B", "C")]
        kept, removed = break_cycles(edges)
        assert len(removed) == 0
        assert kept == edges


# ---------------------------------------------------------------------------
# Migration locking
# ---------------------------------------------------------------------------


class TestMigrationLock:
    def test_acquire_and_release(self, tmp_path: Path):
        lock = MigrationLock(tmp_path)
        assert lock.acquire("run-001")
        assert lock.is_locked
        lock.release()
        assert not lock.is_locked

    def test_cannot_acquire_twice(self, tmp_path: Path):
        lock = MigrationLock(tmp_path)
        assert lock.acquire("run-001")
        assert not lock.acquire("run-002")  # Should fail

    def test_force_acquire(self, tmp_path: Path):
        lock = MigrationLock(tmp_path)
        lock.acquire("run-001")
        assert lock.acquire("run-002", force=True)  # Force breaks existing lock

    def test_lock_file_contents(self, tmp_path: Path):
        lock = MigrationLock(tmp_path)
        lock.acquire("run-003")
        lock_file = tmp_path / ".migration.lock"
        data = json.loads(lock_file.read_text(encoding="utf-8"))
        assert data["run_id"] == "run-003"
        assert "acquired_at" in data
        assert "pid" in data

    def test_context_manager(self, tmp_path: Path):
        with MigrationLock(tmp_path) as lock:
            lock.acquire("run-004")
            assert lock.is_locked
        # Auto-released after context
        assert not MigrationLock(tmp_path).is_locked

    def test_release_without_acquire(self, tmp_path: Path):
        lock = MigrationLock(tmp_path)
        lock.release()  # Should not raise


# ---------------------------------------------------------------------------
# Adaptive backoff
# ---------------------------------------------------------------------------


class TestAdaptiveBackoff:
    def test_initial_delay(self):
        backoff = AdaptiveBackoff(base_delay=1.0)
        assert backoff.next_delay() == 1.0

    def test_exponential_increase(self):
        backoff = AdaptiveBackoff(base_delay=1.0, multiplier=2.0)
        backoff.record_failure()  # 1 failure
        assert backoff.next_delay() == 2.0
        backoff.record_failure()  # 2 failures
        assert backoff.next_delay() == 4.0

    def test_max_delay_cap(self):
        backoff = AdaptiveBackoff(base_delay=1.0, max_delay=10.0, multiplier=2.0)
        for _ in range(20):
            backoff.record_failure()
        assert backoff.next_delay() <= 10.0

    def test_success_resets(self):
        backoff = AdaptiveBackoff(base_delay=1.0)
        backoff.record_failure()
        backoff.record_failure()
        assert backoff.consecutive_failures == 2
        backoff.record_success()
        assert backoff.consecutive_failures == 0
        assert backoff.next_delay() == 1.0  # back to base

    def test_total_retries_accumulates(self):
        backoff = AdaptiveBackoff()
        backoff.record_failure()
        backoff.record_failure()
        backoff.record_success()
        backoff.record_failure()
        assert backoff.total_retries == 3

    def test_record_failure_returns_delay(self):
        backoff = AdaptiveBackoff(base_delay=2.0, multiplier=3.0)
        delay = backoff.record_failure()
        assert delay == 6.0  # 2.0 * 3^1

    def test_reset(self):
        backoff = AdaptiveBackoff()
        backoff.record_failure()
        backoff.record_failure()
        backoff.reset()
        assert backoff.consecutive_failures == 0
        assert backoff.total_retries == 0
