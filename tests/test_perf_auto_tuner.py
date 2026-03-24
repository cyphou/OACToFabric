"""Tests for Performance Auto-Tuning (Phase 46).

Covers:
- QueryProfile model (categories, SE ratio, scan efficiency)
- DAXMeasureProfile model (complexity detection)
- PerformanceAnalyzer — query analysis
- DAXOptimizer — pattern detection and optimization suggestions
- AggregationAdvisor — aggregation table recommendations
- CompositeModelAdvisor — composite model patterns
- PerformanceAutoTuner — end-to-end tuning
"""

from __future__ import annotations

import pytest

from src.core.perf_auto_tuner import (
    AggregationAdvisor,
    AggregationTableSpec,
    CompositeModelAdvisor,
    CompositeModelPattern,
    DAXMeasureProfile,
    DAXOptimization,
    DAXOptimizer,
    OptimizationAction,
    PerformanceAnalyzer,
    PerformanceAutoTuner,
    PerformanceTuningReport,
    QueryCategory,
    QueryProfile,
)


# ===================================================================
# Helpers
# ===================================================================


def _sample_queries() -> list[QueryProfile]:
    return [
        QueryProfile(query_id="q1", duration_ms=200, storage_engine_ms=180, formula_engine_ms=20, rows_scanned=1000, rows_returned=100, table_names=["Sales"]),
        QueryProfile(query_id="q2", duration_ms=3000, storage_engine_ms=2500, formula_engine_ms=500, rows_scanned=500000, rows_returned=1000, table_names=["Sales", "Products"]),
        QueryProfile(query_id="q3", duration_ms=8000, storage_engine_ms=3000, formula_engine_ms=5000, rows_scanned=2000000, rows_returned=50, table_names=["FactSales"]),
        QueryProfile(query_id="q4", duration_ms=45000, storage_engine_ms=10000, formula_engine_ms=35000, rows_scanned=10000000, rows_returned=10, table_names=["FactSales", "DimDate"]),
    ]


def _sample_measures() -> list[DAXMeasureProfile]:
    return [
        DAXMeasureProfile(
            name="TotalSales",
            expression="SUM(Sales[Amount])",
            avg_duration_ms=100,
        ),
        DAXMeasureProfile(
            name="SlowIterator",
            expression="SUMX(Sales, Sales[Amount])",
            avg_duration_ms=3000,
            uses_iterator=True,
        ),
        DAXMeasureProfile(
            name="DeepNested",
            expression="CALCULATE(COUNTROWS(Orders))",
            avg_duration_ms=5000,
            nested_depth=5,
            uses_calculate=True,
        ),
        DAXMeasureProfile(
            name="BidirMeasure",
            expression="CALCULATE(SUM(Sales[Amount]))",
            avg_duration_ms=2000,
            uses_bidir=True,
        ),
    ]


# ===================================================================
# QueryProfile
# ===================================================================


class TestQueryProfile:
    def test_fast(self):
        q = QueryProfile(duration_ms=500)
        assert q.category == QueryCategory.FAST

    def test_normal(self):
        q = QueryProfile(duration_ms=3000)
        assert q.category == QueryCategory.NORMAL

    def test_slow(self):
        q = QueryProfile(duration_ms=15000)
        assert q.category == QueryCategory.SLOW

    def test_critical(self):
        q = QueryProfile(duration_ms=60000)
        assert q.category == QueryCategory.CRITICAL

    def test_se_ratio(self):
        q = QueryProfile(storage_engine_ms=800, formula_engine_ms=200)
        assert q.se_ratio == 0.8

    def test_se_ratio_zero(self):
        q = QueryProfile()
        assert q.se_ratio == 0.0

    def test_scan_efficiency(self):
        q = QueryProfile(rows_scanned=1000, rows_returned=100)
        assert q.scan_efficiency == 0.1

    def test_scan_efficiency_zero(self):
        q = QueryProfile(rows_scanned=0)
        assert q.scan_efficiency == 1.0


# ===================================================================
# DAXMeasureProfile
# ===================================================================


class TestDAXMeasureProfile:
    def test_simple_not_complex(self):
        m = DAXMeasureProfile(name="Simple", expression="SUM(X)")
        assert not m.is_complex

    def test_complex_iterator(self):
        m = DAXMeasureProfile(name="Iter", uses_iterator=True)
        assert m.is_complex

    def test_complex_bidir(self):
        m = DAXMeasureProfile(name="Bidir", uses_bidir=True)
        assert m.is_complex

    def test_complex_nested(self):
        m = DAXMeasureProfile(name="Nested", nested_depth=4)
        assert m.is_complex

    def test_complex_slow(self):
        m = DAXMeasureProfile(name="Slow", avg_duration_ms=3000)
        assert m.is_complex


# ===================================================================
# PerformanceAnalyzer
# ===================================================================


class TestPerformanceAnalyzer:
    def test_empty(self):
        a = PerformanceAnalyzer()
        result = a.analyze_queries([])
        assert result["total"] == 0

    def test_categories(self):
        a = PerformanceAnalyzer()
        result = a.analyze_queries(_sample_queries())
        assert result["total"] == 4
        assert result["categories"]["fast"] == 1
        assert result["categories"]["critical"] == 1

    def test_avg_duration(self):
        a = PerformanceAnalyzer()
        result = a.analyze_queries(_sample_queries())
        assert result["avg_duration_ms"] > 0

    def test_hot_tables(self):
        a = PerformanceAnalyzer()
        result = a.analyze_queries(_sample_queries())
        hot = result["hot_tables"]
        assert len(hot) >= 1
        # FactSales appears in 2 queries
        names = [h[0] for h in hot]
        assert "FactSales" in names

    def test_slow_queries(self):
        a = PerformanceAnalyzer()
        result = a.analyze_queries(_sample_queries())
        assert "q3" in result["slow_queries"]
        assert "q4" in result["slow_queries"]


# ===================================================================
# DAXOptimizer
# ===================================================================


class TestDAXOptimizer:
    def test_sumx_pattern(self):
        opt = DAXOptimizer()
        m = DAXMeasureProfile(name="Rev", expression="SUMX(Sales, Sales[Amount])")
        results = opt.analyze_measure(m)
        assert any("SUM" in r.reason for r in results)

    def test_averagex_pattern(self):
        opt = DAXOptimizer()
        m = DAXMeasureProfile(name="Avg", expression="AVERAGEX(Products, Products[Price])")
        results = opt.analyze_measure(m)
        assert any("AVERAGE" in r.reason for r in results)

    def test_isblank_pattern(self):
        opt = DAXOptimizer()
        m = DAXMeasureProfile(name="Check", expression="IF(ISBLANK(Sales[Amount]), 0, Sales[Amount])")
        results = opt.analyze_measure(m)
        assert any("COALESCE" in r.reason for r in results)

    def test_nesting_depth(self):
        opt = DAXOptimizer()
        m = DAXMeasureProfile(name="Deep", expression="X", nested_depth=5)
        results = opt.analyze_measure(m)
        assert any(r.action == OptimizationAction.BATCH_MEASURES for r in results)

    def test_bidir_warning(self):
        opt = DAXOptimizer()
        m = DAXMeasureProfile(name="Bidir", expression="X", uses_bidir=True)
        results = opt.analyze_measure(m)
        assert any(r.action == OptimizationAction.REMOVE_BIDIR for r in results)

    def test_no_issues(self):
        opt = DAXOptimizer()
        m = DAXMeasureProfile(name="Clean", expression="SUM(Sales[Amount])")
        results = opt.analyze_measure(m)
        assert len(results) == 0

    def test_analyze_all(self):
        opt = DAXOptimizer()
        results = opt.analyze_all(_sample_measures())
        assert len(results) >= 3  # SUMX + nesting + bidir


# ===================================================================
# AggregationAdvisor
# ===================================================================


class TestAggregationAdvisor:
    def test_recommend_for_slow_queries(self):
        advisor = AggregationAdvisor()
        queries = [
            QueryProfile(query_id="q1", duration_ms=10000, rows_scanned=5_000_000, table_names=["FactSales"]),
        ]
        results = advisor.recommend(queries)
        assert len(results) >= 1
        assert results[0].source_table == "FactSales"

    def test_no_suggestions_for_fast(self):
        advisor = AggregationAdvisor()
        queries = [
            QueryProfile(query_id="q1", duration_ms=200, rows_scanned=100, table_names=["Small"]),
        ]
        results = advisor.recommend(queries)
        assert len(results) == 0

    def test_priority_increases(self):
        advisor = AggregationAdvisor()
        queries = [
            QueryProfile(query_id="q1", duration_ms=10000, rows_scanned=5_000_000, table_names=["FactSales"]),
            QueryProfile(query_id="q2", duration_ms=8000, rows_scanned=3_000_000, table_names=["FactSales"]),
        ]
        results = advisor.recommend(queries)
        assert results[0].priority >= 2

    def test_spec_properties(self):
        spec = AggregationTableSpec(
            name="Agg_Sales",
            source_table="Sales",
            group_by_columns=["Region", "Year"],
            aggregations={"Amount": "SUM", "Count": "COUNT"},
        )
        assert spec.column_count == 4


# ===================================================================
# CompositeModelAdvisor
# ===================================================================


class TestCompositeModelAdvisor:
    def test_large_tables_direct_lake(self):
        advisor = CompositeModelAdvisor()
        result = advisor.recommend([
            {"name": "FactSales", "row_count": 50_000_000},
            {"name": "DimProduct", "row_count": 5000},
        ])
        assert "FactSales" in result.direct_lake_tables
        assert "DimProduct" in result.direct_lake_tables  # small → defaults to DL

    def test_writeback_import(self):
        advisor = CompositeModelAdvisor()
        result = advisor.recommend([
            {"name": "Budget", "row_count": 100, "is_writeback": True},
        ])
        assert "Budget" in result.import_tables

    def test_hot_tables_dual(self):
        advisor = CompositeModelAdvisor()
        result = advisor.recommend([
            {"name": "DimDate", "row_count": 3650, "queries_per_hour": 200},
        ])
        assert "DimDate" in result.dual_tables

    def test_table_count(self):
        pattern = CompositeModelPattern(
            name="test",
            direct_lake_tables=["A", "B"],
            import_tables=["C"],
        )
        assert pattern.table_count == 3


# ===================================================================
# PerformanceAutoTuner — end-to-end
# ===================================================================


class TestPerformanceAutoTuner:
    def test_tune_empty(self):
        tuner = PerformanceAutoTuner()
        report = tuner.tune()
        assert report.total_queries_analyzed == 0
        assert report.optimization_count == 0

    def test_tune_full(self):
        tuner = PerformanceAutoTuner()
        report = tuner.tune(
            queries=_sample_queries(),
            measures=_sample_measures(),
            table_stats=[
                {"name": "FactSales", "row_count": 50_000_000},
                {"name": "Sales", "row_count": 100_000},
            ],
        )
        assert report.total_queries_analyzed == 4
        assert report.slow_query_count >= 2
        assert report.optimization_count >= 1
        assert report.composite_model is not None

    def test_tune_queries_only(self):
        tuner = PerformanceAutoTuner()
        report = tuner.tune(queries=_sample_queries())
        assert report.total_queries_analyzed == 4
        assert "categories" in report.query_analysis

    def test_tune_measures_only(self):
        tuner = PerformanceAutoTuner()
        report = tuner.tune(measures=_sample_measures())
        assert report.optimization_count >= 1

    def test_aggregation_suggestions(self):
        tuner = PerformanceAutoTuner()
        queries = [
            QueryProfile(query_id="q1", duration_ms=10000, rows_scanned=5_000_000, table_names=["BigTable"]),
        ]
        report = tuner.tune(queries=queries)
        assert report.has_aggregation_suggestions

    def test_report_properties(self):
        report = PerformanceTuningReport(
            dax_optimizations=[
                DAXOptimization(measure_name="M", original="X", optimized="Y", action=OptimizationAction.REWRITE_DAX, reason="test"),
            ],
        )
        assert report.optimization_count == 1
        assert not report.has_aggregation_suggestions
