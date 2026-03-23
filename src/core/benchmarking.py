"""Performance benchmarking utilities for the migration framework.

Provides:
- ``BenchmarkResult`` — structured result of a benchmark run.
- ``Benchmarker`` — context-manager based benchmarking with memory tracking.
- ``RPDBenchmark`` — benchmark RPD parsing at various file sizes.
- ``DAGBenchmark`` — benchmark DAG orchestration throughput.
- ``ThroughputTracker`` — items/sec tracking for any pipeline stage.
"""

from __future__ import annotations

import logging
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Benchmark result
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    name: str
    duration_seconds: float = 0.0
    peak_memory_mb: float = 0.0
    items_processed: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def items_per_second(self) -> float:
        if self.duration_seconds <= 0:
            return 0.0
        return self.items_processed / self.duration_seconds

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        return (
            f"Benchmark '{self.name}': "
            f"{self.duration_seconds:.2f}s, "
            f"{self.peak_memory_mb:.1f} MB peak, "
            f"{self.items_processed} items "
            f"({self.items_per_second:.1f} items/sec)"
        )


@dataclass
class BenchmarkSuite:
    """A collection of benchmark results."""

    results: list[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult) -> None:
        self.results.append(result)

    @property
    def total_duration(self) -> float:
        return sum(r.duration_seconds for r in self.results)

    @property
    def all_passed(self) -> bool:
        return all(r.success for r in self.results)

    def summary(self) -> str:
        lines = ["=== Benchmark Suite Results ==="]
        for r in self.results:
            status = "PASS" if r.success else "FAIL"
            lines.append(f"  [{status}] {r.summary()}")
        lines.append(
            f"Total: {len(self.results)} benchmarks, {self.total_duration:.2f}s"
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Benchmarker context manager
# ---------------------------------------------------------------------------


class Benchmarker:
    """Context-manager based benchmarking with optional memory tracking.

    Usage::

        bm = Benchmarker()
        with bm.run("parse_rpd") as ctx:
            parse(data)
            ctx.items_processed = 5000

        result = ctx.result
    """

    @dataclass
    class Context:
        name: str
        items_processed: int = 0
        metadata: dict[str, Any] = field(default_factory=dict)
        result: BenchmarkResult | None = None

    @contextmanager
    def run(
        self,
        name: str,
        *,
        track_memory: bool = True,
    ) -> Generator[Context, None, None]:
        """Run a benchmark, capturing timing and optional memory usage."""
        ctx = self.Context(name=name)

        if track_memory:
            tracemalloc.start()

        start = time.monotonic()

        try:
            yield ctx
        except Exception as exc:
            ctx.result = BenchmarkResult(
                name=name,
                duration_seconds=time.monotonic() - start,
                items_processed=ctx.items_processed,
                errors=[str(exc)],
                metadata=ctx.metadata,
            )
            raise
        finally:
            elapsed = time.monotonic() - start
            peak_mb = 0.0
            if track_memory:
                _, peak = tracemalloc.get_traced_memory()
                peak_mb = peak / (1024 * 1024)
                tracemalloc.stop()

            if ctx.result is None:
                ctx.result = BenchmarkResult(
                    name=name,
                    duration_seconds=elapsed,
                    peak_memory_mb=peak_mb,
                    items_processed=ctx.items_processed,
                    metadata=ctx.metadata,
                )

            logger.info("Benchmark %s: %s", name, ctx.result.summary())


# ---------------------------------------------------------------------------
# Throughput tracker
# ---------------------------------------------------------------------------


class ThroughputTracker:
    """Track items/sec throughput over a processing pipeline.

    Usage::

        tracker = ThroughputTracker("rpd_elements")
        tracker.start()
        for element in elements:
            process(element)
            tracker.tick()
        tracker.stop()
        print(tracker.items_per_second)
    """

    def __init__(self, name: str = "throughput") -> None:
        self.name = name
        self._start: float = 0.0
        self._end: float = 0.0
        self._count: int = 0

    def start(self) -> None:
        self._start = time.monotonic()
        self._count = 0

    def tick(self, n: int = 1) -> None:
        self._count += n

    def stop(self) -> None:
        self._end = time.monotonic()

    @property
    def elapsed_seconds(self) -> float:
        end = self._end or time.monotonic()
        return end - self._start if self._start else 0.0

    @property
    def items_per_second(self) -> float:
        elapsed = self.elapsed_seconds
        return self._count / elapsed if elapsed > 0 else 0.0

    @property
    def count(self) -> int:
        return self._count

    def summary(self) -> str:
        return (
            f"{self.name}: {self._count} items in "
            f"{self.elapsed_seconds:.2f}s "
            f"({self.items_per_second:.1f} items/sec)"
        )


# ---------------------------------------------------------------------------
# Synthetic data generators for load testing
# ---------------------------------------------------------------------------


def generate_synthetic_inventory(
    n_tables: int = 100,
    n_analyses: int = 50,
    n_dashboards: int = 20,
    n_dataflows: int = 30,
) -> list[dict[str, Any]]:
    """Generate a synthetic OAC inventory for load testing.

    Returns a list of inventory item dicts with realistic field names.
    """
    items: list[dict[str, Any]] = []

    for i in range(n_tables):
        items.append(
            {
                "asset_id": f"tbl_{i:05d}",
                "asset_type": "physicalTable",
                "name": f"FACT_TABLE_{i}",
                "schema": "DW",
                "column_count": 10 + (i % 30),
                "row_estimate": 1000 * (i + 1),
                "complexity": "low" if i % 3 == 0 else "medium",
            }
        )

    for i in range(n_analyses):
        items.append(
            {
                "asset_id": f"ana_{i:05d}",
                "asset_type": "analysis",
                "name": f"Sales_Analysis_{i}",
                "subject_area": f"SA_{i % 5}",
                "visual_count": 3 + (i % 8),
                "complexity": "medium" if i % 2 == 0 else "high",
            }
        )

    for i in range(n_dashboards):
        items.append(
            {
                "asset_id": f"dash_{i:05d}",
                "asset_type": "dashboard",
                "name": f"Executive_Dashboard_{i}",
                "page_count": 1 + (i % 5),
                "complexity": "high",
            }
        )

    for i in range(n_dataflows):
        items.append(
            {
                "asset_id": f"df_{i:05d}",
                "asset_type": "dataflow",
                "name": f"ETL_Flow_{i}",
                "step_count": 5 + (i % 10),
                "complexity": "medium",
            }
        )

    return items


def generate_large_rpd_xml(n_elements: int = 1000) -> str:
    """Generate a synthetic RPD XML string for parsing benchmarks.

    The XML follows the OAC RPD structure with logical and physical
    columns, tables, and subject areas.
    """
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<Repository>"]

    for i in range(n_elements):
        lines.append(f'  <LogicalTable name="Table_{i}" id="lt_{i:05d}">')
        for j in range(5):
            lines.append(
                f'    <LogicalColumn name="Col_{j}" '
                f'dataType="VARCHAR" length="100" '
                f'id="lc_{i:05d}_{j:02d}" />'
            )
        lines.append("  </LogicalTable>")

    lines.append("</Repository>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Migration lock for concurrent migration testing
# ---------------------------------------------------------------------------


class MigrationLock:
    """In-memory migration lock for concurrent migration testing.

    In production this would use Fabric Lakehouse row-level locking
    or Azure Blob lease. For testing, an in-memory implementation.
    """

    def __init__(self) -> None:
        self._locks: dict[str, str] = {}  # workspace_id → run_id

    def acquire(self, workspace_id: str, run_id: str) -> bool:
        """Attempt to acquire a migration lock for a workspace.

        Returns True if the lock was acquired, False if already held.
        """
        if workspace_id in self._locks:
            return False
        self._locks[workspace_id] = run_id
        return True

    def release(self, workspace_id: str, run_id: str) -> bool:
        """Release a migration lock.

        Returns True if released, False if held by a different run.
        """
        if self._locks.get(workspace_id) != run_id:
            return False
        del self._locks[workspace_id]
        return True

    def is_locked(self, workspace_id: str) -> bool:
        return workspace_id in self._locks

    def holder(self, workspace_id: str) -> str | None:
        return self._locks.get(workspace_id)

    def clear(self) -> None:
        self._locks.clear()
