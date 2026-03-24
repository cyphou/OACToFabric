"""Performance Auto-Tuning — post-migration query and DAX optimization.

Provides:
- ``QueryProfile`` — captured query execution metrics.
- ``DAXMeasureProfile`` — profiled DAX measure with cost indicators.
- ``AggregationTableSpec`` — specification for a recommended aggregation table.
- ``CompositeModelPattern`` — composite model configuration recommendation.
- ``PerformanceAnalyzer`` — analyze query execution profiles.
- ``DAXOptimizer`` — DAX measure optimization via pattern matching.
- ``AggregationAdvisor`` — aggregation table suggestions.
- ``CompositeModelAdvisor`` — composite model pattern recommendations.
- ``PerformanceAutoTuner`` — orchestrates all auto-tuning.
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


class QueryCategory(str, Enum):
    FAST = "fast"          # < 1 second
    NORMAL = "normal"      # 1-5 seconds
    SLOW = "slow"          # 5-30 seconds
    CRITICAL = "critical"  # > 30 seconds


class OptimizationAction(str, Enum):
    REWRITE_DAX = "rewrite_dax"
    ADD_AGGREGATION = "add_aggregation"
    ADD_INDEX = "add_index"
    COMPOSITE_MODEL = "composite_model"
    REDUCE_CARDINALITY = "reduce_cardinality"
    REMOVE_BIDIR = "remove_bidir"
    BATCH_MEASURES = "batch_measures"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class QueryProfile:
    """Captured query execution metrics."""

    query_id: str = ""
    query_text: str = ""
    duration_ms: float = 0.0
    storage_engine_ms: float = 0.0
    formula_engine_ms: float = 0.0
    rows_scanned: int = 0
    rows_returned: int = 0
    memory_kb: int = 0
    table_names: list[str] = field(default_factory=list)
    user_id: str = ""

    @property
    def category(self) -> QueryCategory:
        if self.duration_ms < 1000:
            return QueryCategory.FAST
        if self.duration_ms < 5000:
            return QueryCategory.NORMAL
        if self.duration_ms < 30000:
            return QueryCategory.SLOW
        return QueryCategory.CRITICAL

    @property
    def se_ratio(self) -> float:
        """Storage Engine ratio (lower = more formula engine bound)."""
        total = self.storage_engine_ms + self.formula_engine_ms
        if total == 0:
            return 0.0
        return round(self.storage_engine_ms / total, 3)

    @property
    def scan_efficiency(self) -> float:
        """Ratio of returned vs scanned rows (higher = more efficient)."""
        if self.rows_scanned == 0:
            return 1.0
        return round(self.rows_returned / self.rows_scanned, 4)


@dataclass
class DAXMeasureProfile:
    """Profiled DAX measure with optimization hints."""

    name: str
    expression: str = ""
    avg_duration_ms: float = 0.0
    call_count: int = 0
    uses_calculate: bool = False
    uses_iterator: bool = False
    uses_bidir: bool = False
    nested_depth: int = 0
    table_references: list[str] = field(default_factory=list)

    @property
    def is_complex(self) -> bool:
        return (
            self.nested_depth > 3
            or self.uses_iterator
            or self.uses_bidir
            or self.avg_duration_ms > 2000
        )


@dataclass
class DAXOptimization:
    """A suggested DAX optimization."""

    measure_name: str
    original: str
    optimized: str
    action: OptimizationAction
    reason: str
    estimated_improvement_pct: float = 0.0
    confidence: float = 0.8


@dataclass
class AggregationTableSpec:
    """Specification for a recommended aggregation table."""

    name: str
    source_table: str
    group_by_columns: list[str] = field(default_factory=list)
    aggregations: dict[str, str] = field(default_factory=dict)  # column → agg_function
    estimated_row_count: int = 0
    estimated_size_mb: float = 0.0
    reason: str = ""
    priority: int = 1

    @property
    def column_count(self) -> int:
        return len(self.group_by_columns) + len(self.aggregations)


@dataclass
class CompositeModelPattern:
    """Composite model configuration recommendation."""

    name: str
    direct_lake_tables: list[str] = field(default_factory=list)
    import_tables: list[str] = field(default_factory=list)
    dual_tables: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def table_count(self) -> int:
        return len(self.direct_lake_tables) + len(self.import_tables) + len(self.dual_tables)


@dataclass
class PerformanceTuningReport:
    """Full performance tuning report."""

    query_analysis: dict[str, Any] = field(default_factory=dict)
    dax_optimizations: list[DAXOptimization] = field(default_factory=list)
    aggregation_tables: list[AggregationTableSpec] = field(default_factory=list)
    composite_model: CompositeModelPattern | None = None
    total_queries_analyzed: int = 0
    slow_query_count: int = 0
    estimated_improvement_pct: float = 0.0

    @property
    def optimization_count(self) -> int:
        return len(self.dax_optimizations)

    @property
    def has_aggregation_suggestions(self) -> bool:
        return len(self.aggregation_tables) > 0


# ---------------------------------------------------------------------------
# Performance Analyzer
# ---------------------------------------------------------------------------


class PerformanceAnalyzer:
    """Analyze query execution profiles to identify bottlenecks."""

    def analyze_queries(self, queries: list[QueryProfile]) -> dict[str, Any]:
        if not queries:
            return {"total": 0, "categories": {}}

        categories: dict[str, int] = {c.value: 0 for c in QueryCategory}
        total_duration = 0.0
        se_bound = 0
        fe_bound = 0
        table_frequency: dict[str, int] = {}

        for q in queries:
            categories[q.category.value] += 1
            total_duration += q.duration_ms

            if q.se_ratio > 0.7:
                se_bound += 1
            else:
                fe_bound += 1

            for t in q.table_names:
                table_frequency[t] = table_frequency.get(t, 0) + 1

        return {
            "total": len(queries),
            "categories": categories,
            "avg_duration_ms": round(total_duration / len(queries), 1),
            "p95_duration_ms": round(sorted(q.duration_ms for q in queries)[int(len(queries) * 0.95)], 1),
            "se_bound_pct": round(se_bound / len(queries) * 100, 1),
            "fe_bound_pct": round(fe_bound / len(queries) * 100, 1),
            "hot_tables": sorted(table_frequency.items(), key=lambda x: x[1], reverse=True)[:10],
            "slow_queries": [q.query_id for q in queries if q.category in (QueryCategory.SLOW, QueryCategory.CRITICAL)],
        }


# ---------------------------------------------------------------------------
# DAX Optimizer
# ---------------------------------------------------------------------------

# Common anti-patterns and their optimizations
_DAX_PATTERNS: list[tuple[str, str, str, float]] = [
    # (pattern_re, replacement_hint, reason, improvement_pct)
    (
        r"CALCULATE\s*\(\s*COUNTROWS\s*\(\s*(\w+)\s*\)\s*\)",
        r"COUNTROWS(FILTER(\1, ...))",
        "CALCULATE(COUNTROWS()) can often be replaced with COUNTROWS(FILTER()) for better performance",
        10.0,
    ),
    (
        r"SUMX\s*\(\s*(\w+)\s*,\s*\1\[(\w+)\]\s*\)",
        r"SUM(\1[\2])",
        "SUMX with simple column reference should use SUM for better storage engine optimization",
        25.0,
    ),
    (
        r"AVERAGEX\s*\(\s*(\w+)\s*,\s*\1\[(\w+)\]\s*\)",
        r"AVERAGE(\1[\2])",
        "AVERAGEX with simple column reference should use AVERAGE",
        20.0,
    ),
    (
        r"COUNTROWS\s*\(\s*FILTER\s*\(\s*ALL\s*\(\s*(\w+)\s*\)\s*,",
        "CALCULATE(COUNTROWS(), ALL(), ...)",
        "FILTER(ALL()) pattern may be less efficient than CALCULATE with ALL modifier",
        15.0,
    ),
    (
        r"IF\s*\(\s*ISBLANK\s*\(",
        "COALESCE(...)",
        "IF(ISBLANK()) can often be simplified to COALESCE() (DAX 2021+)",
        5.0,
    ),
    (
        r"RELATED\s*\(\s*(\w+)\[(\w+)\]\s*\).*RELATED\s*\(\s*\1\[",
        "Use expanded table or denormalization",
        "Multiple RELATED() calls to same table can benefit from denormalization",
        15.0,
    ),
]


class DAXOptimizer:
    """Optimize DAX measures using pattern matching and heuristics."""

    def analyze_measure(self, measure: DAXMeasureProfile) -> list[DAXOptimization]:
        optimizations: list[DAXOptimization] = []

        expr = measure.expression

        for pattern_re, replacement, reason, improvement in _DAX_PATTERNS:
            if re.search(pattern_re, expr, re.IGNORECASE | re.DOTALL):
                optimizations.append(DAXOptimization(
                    measure_name=measure.name,
                    original=expr,
                    optimized=f"// Suggested: {replacement}",
                    action=OptimizationAction.REWRITE_DAX,
                    reason=reason,
                    estimated_improvement_pct=improvement,
                ))

        # Check nesting depth
        if measure.nested_depth > 3:
            optimizations.append(DAXOptimization(
                measure_name=measure.name,
                original=expr,
                optimized="// Break into intermediate measures to reduce nesting",
                action=OptimizationAction.BATCH_MEASURES,
                reason=f"Nesting depth {measure.nested_depth} — decompose into helper measures",
                estimated_improvement_pct=10.0,
                confidence=0.6,
            ))

        # Bidirectional relationship warning
        if measure.uses_bidir:
            optimizations.append(DAXOptimization(
                measure_name=measure.name,
                original=expr,
                optimized="// Consider single-direction relationship with CROSSFILTER()",
                action=OptimizationAction.REMOVE_BIDIR,
                reason="Bidirectional relationships can cause performance issues",
                estimated_improvement_pct=20.0,
                confidence=0.7,
            ))

        return optimizations

    def analyze_all(self, measures: list[DAXMeasureProfile]) -> list[DAXOptimization]:
        result: list[DAXOptimization] = []
        for m in measures:
            result.extend(self.analyze_measure(m))
        return result


# ---------------------------------------------------------------------------
# Aggregation Advisor
# ---------------------------------------------------------------------------


class AggregationAdvisor:
    """Recommend aggregation tables based on query patterns."""

    SCAN_THRESHOLD = 1_000_000
    SLOW_THRESHOLD_MS = 5000

    def recommend(
        self,
        queries: list[QueryProfile],
        table_sizes: dict[str, int] | None = None,
    ) -> list[AggregationTableSpec]:
        table_sizes = table_sizes or {}
        suggestions: dict[str, AggregationTableSpec] = {}

        # Find tables that are frequently scanned with high row counts
        for q in queries:
            if q.duration_ms < self.SLOW_THRESHOLD_MS and q.rows_scanned < self.SCAN_THRESHOLD:
                continue

            for table in q.table_names:
                if table in suggestions:
                    suggestions[table].priority += 1
                    continue

                row_count = table_sizes.get(table, q.rows_scanned)
                if row_count > self.SCAN_THRESHOLD:
                    suggestions[table] = AggregationTableSpec(
                        name=f"Agg_{table}",
                        source_table=table,
                        group_by_columns=[],  # would need workload to fill
                        estimated_row_count=max(1, row_count // 100),
                        estimated_size_mb=round(row_count / 100 * 0.001, 2),
                        reason=f"Table '{table}' scanned {row_count:,} rows in slow queries",
                        priority=1,
                    )

        result = sorted(suggestions.values(), key=lambda s: s.priority, reverse=True)
        return result


# ---------------------------------------------------------------------------
# Composite Model Advisor
# ---------------------------------------------------------------------------


class CompositeModelAdvisor:
    """Recommend composite model patterns (DirectLake + Import mix)."""

    LARGE_TABLE_ROWS = 10_000_000
    HOT_QUERY_THRESHOLD = 50  # queries per hour

    def recommend(
        self,
        table_stats: list[dict[str, Any]],
    ) -> CompositeModelPattern:
        direct_lake: list[str] = []
        import_tables: list[str] = []
        dual_tables: list[str] = []

        for stat in table_stats:
            name = stat.get("name", "")
            rows = stat.get("row_count", 0)
            queries_per_hour = stat.get("queries_per_hour", 0)
            is_writeback = stat.get("is_writeback", False)

            if is_writeback:
                import_tables.append(name)
            elif rows > self.LARGE_TABLE_ROWS:
                direct_lake.append(name)
            elif queries_per_hour > self.HOT_QUERY_THRESHOLD:
                dual_tables.append(name)
            else:
                direct_lake.append(name)

        reason_parts: list[str] = []
        if direct_lake:
            reason_parts.append(f"{len(direct_lake)} tables → Direct Lake (large/standard)")
        if import_tables:
            reason_parts.append(f"{len(import_tables)} tables → Import (writeback)")
        if dual_tables:
            reason_parts.append(f"{len(dual_tables)} tables → Dual (hot queries)")

        return CompositeModelPattern(
            name="Auto-tuned composite model",
            direct_lake_tables=direct_lake,
            import_tables=import_tables,
            dual_tables=dual_tables,
            reason="; ".join(reason_parts) if reason_parts else "No tables provided",
        )


# ---------------------------------------------------------------------------
# Performance Auto-Tuner — orchestrates all
# ---------------------------------------------------------------------------


class PerformanceAutoTuner:
    """Top-level auto-tuner that combines all performance recommendations.

    Usage::

        tuner = PerformanceAutoTuner()
        report = tuner.tune(queries, measures, table_stats)
    """

    def __init__(self) -> None:
        self._analyzer = PerformanceAnalyzer()
        self._dax_optimizer = DAXOptimizer()
        self._agg_advisor = AggregationAdvisor()
        self._composite_advisor = CompositeModelAdvisor()

    def tune(
        self,
        queries: list[QueryProfile] | None = None,
        measures: list[DAXMeasureProfile] | None = None,
        table_stats: list[dict[str, Any]] | None = None,
        table_sizes: dict[str, int] | None = None,
    ) -> PerformanceTuningReport:
        queries = queries or []
        measures = measures or []
        table_stats = table_stats or []

        # 1. Query analysis
        analysis = self._analyzer.analyze_queries(queries)

        # 2. DAX optimization
        dax_opts = self._dax_optimizer.analyze_all(measures)

        # 3. Aggregation suggestions
        agg_tables = self._agg_advisor.recommend(queries, table_sizes)

        # 4. Composite model
        composite = self._composite_advisor.recommend(table_stats) if table_stats else None

        # Estimate overall improvement
        slow_count = len(analysis.get("slow_queries", []))
        total_improvement = 0.0
        if dax_opts:
            total_improvement = sum(o.estimated_improvement_pct for o in dax_opts) / len(dax_opts)

        return PerformanceTuningReport(
            query_analysis=analysis,
            dax_optimizations=dax_opts,
            aggregation_tables=agg_tables,
            composite_model=composite,
            total_queries_analyzed=len(queries),
            slow_query_count=slow_count,
            estimated_improvement_pct=round(total_improvement, 1),
        )
