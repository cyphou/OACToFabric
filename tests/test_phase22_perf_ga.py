"""Phase 22 — Performance, Load Testing & GA Readiness.

Tests cover:
- BenchmarkResult properties and summary
- BenchmarkSuite aggregation
- Benchmarker context manager (timing, memory, errors)
- ThroughputTracker lifecycle
- Synthetic inventory generator
- Large RPD XML generator
- MigrationLock concurrency semantics
- CHANGELOG & MIGRATION_PLAYBOOK existence
"""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET

import pytest

from src.core.benchmarking import (
    BenchmarkResult,
    BenchmarkSuite,
    Benchmarker,
    MigrationLock,
    ThroughputTracker,
    generate_large_rpd_xml,
    generate_synthetic_inventory,
)


# ===================================================================
# BenchmarkResult
# ===================================================================


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    def test_items_per_second_basic(self):
        r = BenchmarkResult(name="test", duration_seconds=2.0, items_processed=100)
        assert r.items_per_second == pytest.approx(50.0)

    def test_items_per_second_zero_duration(self):
        r = BenchmarkResult(name="test", duration_seconds=0.0, items_processed=100)
        assert r.items_per_second == 0.0

    def test_success_no_errors(self):
        r = BenchmarkResult(name="test")
        assert r.success is True

    def test_success_with_errors(self):
        r = BenchmarkResult(name="test", errors=["boom"])
        assert r.success is False

    def test_summary_contains_name(self):
        r = BenchmarkResult(name="rpd_parse", duration_seconds=1.5, items_processed=10)
        s = r.summary()
        assert "rpd_parse" in s
        assert "1.50s" in s
        assert "10 items" in s

    def test_default_values(self):
        r = BenchmarkResult(name="x")
        assert r.duration_seconds == 0.0
        assert r.peak_memory_mb == 0.0
        assert r.items_processed == 0
        assert r.errors == []
        assert r.metadata == {}

    def test_metadata_stored(self):
        r = BenchmarkResult(name="x", metadata={"wave": 1})
        assert r.metadata["wave"] == 1


# ===================================================================
# BenchmarkSuite
# ===================================================================


class TestBenchmarkSuite:
    """Tests for BenchmarkSuite aggregation."""

    def test_add_and_count(self):
        suite = BenchmarkSuite()
        suite.add(BenchmarkResult(name="a", duration_seconds=1.0))
        suite.add(BenchmarkResult(name="b", duration_seconds=2.0))
        assert len(suite.results) == 2

    def test_total_duration(self):
        suite = BenchmarkSuite()
        suite.add(BenchmarkResult(name="a", duration_seconds=1.0))
        suite.add(BenchmarkResult(name="b", duration_seconds=2.5))
        assert suite.total_duration == pytest.approx(3.5)

    def test_all_passed_true(self):
        suite = BenchmarkSuite()
        suite.add(BenchmarkResult(name="a"))
        suite.add(BenchmarkResult(name="b"))
        assert suite.all_passed is True

    def test_all_passed_false_if_any_error(self):
        suite = BenchmarkSuite()
        suite.add(BenchmarkResult(name="a"))
        suite.add(BenchmarkResult(name="b", errors=["fail"]))
        assert suite.all_passed is False

    def test_summary_format(self):
        suite = BenchmarkSuite()
        suite.add(BenchmarkResult(name="a", duration_seconds=1.0))
        s = suite.summary()
        assert "Benchmark Suite Results" in s
        assert "PASS" in s
        assert "1 benchmarks" in s

    def test_empty_suite(self):
        suite = BenchmarkSuite()
        assert suite.total_duration == 0.0
        assert suite.all_passed is True


# ===================================================================
# Benchmarker context manager
# ===================================================================


class TestBenchmarker:
    """Tests for Benchmarker context-manager."""

    def test_timing(self):
        bm = Benchmarker()
        with bm.run("timer_test", track_memory=False) as ctx:
            time.sleep(0.05)
        assert ctx.result is not None
        assert ctx.result.duration_seconds >= 0.04

    def test_items_processed(self):
        bm = Benchmarker()
        with bm.run("items", track_memory=False) as ctx:
            ctx.items_processed = 42
        assert ctx.result.items_processed == 42
        assert ctx.result.items_per_second > 0

    def test_memory_tracking(self):
        bm = Benchmarker()
        with bm.run("mem_test", track_memory=True) as ctx:
            _ = bytearray(1024 * 1024)  # allocate ~1 MB
            ctx.items_processed = 1
        assert ctx.result.peak_memory_mb > 0

    def test_no_memory_tracking(self):
        bm = Benchmarker()
        with bm.run("no_mem", track_memory=False) as ctx:
            ctx.items_processed = 1
        assert ctx.result.peak_memory_mb == 0.0

    def test_error_in_benchmark(self):
        bm = Benchmarker()
        with pytest.raises(ValueError, match="boom"):
            with bm.run("err_test", track_memory=False) as ctx:
                raise ValueError("boom")
        assert ctx.result is not None
        assert ctx.result.success is False
        assert "boom" in ctx.result.errors[0]

    def test_result_name(self):
        bm = Benchmarker()
        with bm.run("my_benchmark", track_memory=False) as ctx:
            pass
        assert ctx.result.name == "my_benchmark"

    def test_metadata_in_ctx(self):
        bm = Benchmarker()
        with bm.run("meta", track_memory=False) as ctx:
            ctx.metadata["key"] = "val"
        assert ctx.result.metadata["key"] == "val"


# ===================================================================
# ThroughputTracker
# ===================================================================


class TestThroughputTracker:
    """Tests for ThroughputTracker."""

    def test_basic_throughput(self):
        t = ThroughputTracker("test")
        t.start()
        for _ in range(100):
            t.tick()
        t.stop()
        assert t.count == 100
        assert t.items_per_second > 0
        assert t.elapsed_seconds > 0

    def test_tick_n(self):
        t = ThroughputTracker("batch")
        t.start()
        t.tick(50)
        t.tick(50)
        t.stop()
        assert t.count == 100

    def test_summary(self):
        t = ThroughputTracker("xyz")
        t.start()
        t.tick(10)
        t.stop()
        s = t.summary()
        assert "xyz" in s
        assert "10 items" in s

    def test_no_start(self):
        t = ThroughputTracker()
        assert t.elapsed_seconds == 0.0
        assert t.items_per_second == 0.0

    def test_default_name(self):
        t = ThroughputTracker()
        assert t.name == "throughput"


# ===================================================================
# Synthetic inventory generator
# ===================================================================


class TestSyntheticInventory:
    """Tests for generate_synthetic_inventory."""

    def test_default_counts(self):
        inv = generate_synthetic_inventory()
        assert len(inv) == 200  # 100 + 50 + 20 + 30

    def test_custom_counts(self):
        inv = generate_synthetic_inventory(
            n_tables=10, n_analyses=5, n_dashboards=2, n_dataflows=3
        )
        assert len(inv) == 20

    def test_asset_types_present(self):
        inv = generate_synthetic_inventory(
            n_tables=1, n_analyses=1, n_dashboards=1, n_dataflows=1
        )
        types = {item["asset_type"] for item in inv}
        assert types == {"physicalTable", "analysis", "dashboard", "dataflow"}

    def test_table_fields(self):
        inv = generate_synthetic_inventory(
            n_tables=1, n_analyses=0, n_dashboards=0, n_dataflows=0
        )
        t = inv[0]
        assert "asset_id" in t
        assert t["asset_type"] == "physicalTable"
        assert "column_count" in t
        assert "row_estimate" in t

    def test_analysis_fields(self):
        inv = generate_synthetic_inventory(
            n_tables=0, n_analyses=1, n_dashboards=0, n_dataflows=0
        )
        a = inv[0]
        assert a["asset_type"] == "analysis"
        assert "subject_area" in a
        assert "visual_count" in a

    def test_zero_items(self):
        inv = generate_synthetic_inventory(
            n_tables=0, n_analyses=0, n_dashboards=0, n_dataflows=0
        )
        assert inv == []


# ===================================================================
# Large RPD XML generator
# ===================================================================


class TestLargeRPDXml:
    """Tests for generate_large_rpd_xml."""

    def test_valid_xml(self):
        xml_str = generate_large_rpd_xml(n_elements=5)
        root = ET.fromstring(xml_str)
        assert root.tag == "Repository"

    def test_element_count(self):
        xml_str = generate_large_rpd_xml(n_elements=10)
        root = ET.fromstring(xml_str)
        tables = root.findall("LogicalTable")
        assert len(tables) == 10

    def test_columns_per_table(self):
        xml_str = generate_large_rpd_xml(n_elements=1)
        root = ET.fromstring(xml_str)
        table = root.find("LogicalTable")
        cols = table.findall("LogicalColumn")
        assert len(cols) == 5

    def test_large_generation(self):
        xml_str = generate_large_rpd_xml(n_elements=500)
        root = ET.fromstring(xml_str)
        assert len(root.findall("LogicalTable")) == 500

    def test_default_size(self):
        xml_str = generate_large_rpd_xml()
        root = ET.fromstring(xml_str)
        assert len(root.findall("LogicalTable")) == 1000


# ===================================================================
# MigrationLock
# ===================================================================


class TestMigrationLock:
    """Tests for MigrationLock concurrency semantics."""

    def test_acquire_and_release(self):
        lock = MigrationLock()
        assert lock.acquire("ws1", "run1") is True
        assert lock.is_locked("ws1") is True
        assert lock.release("ws1", "run1") is True
        assert lock.is_locked("ws1") is False

    def test_double_acquire_blocked(self):
        lock = MigrationLock()
        assert lock.acquire("ws1", "run1") is True
        assert lock.acquire("ws1", "run2") is False

    def test_release_by_wrong_holder(self):
        lock = MigrationLock()
        lock.acquire("ws1", "run1")
        assert lock.release("ws1", "wrong") is False
        assert lock.is_locked("ws1") is True

    def test_holder(self):
        lock = MigrationLock()
        lock.acquire("ws1", "run_42")
        assert lock.holder("ws1") == "run_42"

    def test_holder_none_when_unlocked(self):
        lock = MigrationLock()
        assert lock.holder("ws1") is None

    def test_clear(self):
        lock = MigrationLock()
        lock.acquire("ws1", "r1")
        lock.acquire("ws2", "r2")
        lock.clear()
        assert lock.is_locked("ws1") is False
        assert lock.is_locked("ws2") is False

    def test_multiple_workspaces(self):
        lock = MigrationLock()
        assert lock.acquire("ws1", "r1") is True
        assert lock.acquire("ws2", "r2") is True
        assert lock.holder("ws1") == "r1"
        assert lock.holder("ws2") == "r2"

    def test_release_nonexistent(self):
        lock = MigrationLock()
        assert lock.release("ws_x", "r1") is False


# ===================================================================
# GA artifacts existence
# ===================================================================


class TestGAArtifacts:
    """Verify GA deliverables exist on disk."""

    _root = os.path.join(
        os.path.dirname(__file__), os.pardir
    )

    def test_changelog_exists(self):
        path = os.path.join(self._root, "CHANGELOG.md")
        assert os.path.isfile(path), "CHANGELOG.md missing"

    def test_migration_playbook_exists(self):
        path = os.path.join(self._root, "MIGRATION_PLAYBOOK.md")
        assert os.path.isfile(path), "MIGRATION_PLAYBOOK.md missing"

    def test_changelog_has_v1(self):
        path = os.path.join(self._root, "CHANGELOG.md")
        content = open(path, encoding="utf-8").read()
        assert "v1.0.0" in content or "1.0.0" in content

    def test_playbook_has_phases(self):
        path = os.path.join(self._root, "MIGRATION_PLAYBOOK.md")
        content = open(path, encoding="utf-8").read()
        assert "Discovery" in content
        assert "Validation" in content


# ===================================================================
# Integration: Benchmarker + Suite
# ===================================================================


class TestBenchmarkerIntegration:
    """End-to-end: run benchmarks and collect into suite."""

    def test_suite_collects_benchmarks(self):
        bm = Benchmarker()
        suite = BenchmarkSuite()

        with bm.run("fast", track_memory=False) as ctx:
            ctx.items_processed = 100
        suite.add(ctx.result)

        with bm.run("slow", track_memory=False) as ctx:
            time.sleep(0.02)
            ctx.items_processed = 10
        suite.add(ctx.result)

        assert len(suite.results) == 2
        assert suite.all_passed is True
        assert suite.total_duration > 0.01

    def test_inventory_benchmark(self):
        bm = Benchmarker()
        with bm.run("gen_inventory", track_memory=True) as ctx:
            inv = generate_synthetic_inventory(n_tables=500)
            ctx.items_processed = len(inv)
        assert ctx.result.items_processed >= 500
        assert ctx.result.success is True

    def test_rpd_parse_benchmark(self):
        bm = Benchmarker()
        with bm.run("rpd_parse", track_memory=True) as ctx:
            xml_str = generate_large_rpd_xml(n_elements=200)
            root = ET.fromstring(xml_str)
            ctx.items_processed = len(root.findall("LogicalTable"))
        assert ctx.result.items_processed == 200
        assert ctx.result.success is True
