"""Tests for AI-Assisted Schema Optimization (Phase 45).

Covers:
- ColumnProfile, TableProfile, SchemaProfile models
- WorkloadPattern, OptimizationRecommendation, OptimizationReport models
- PartitionKeyRecommender — candidate ranking, HPK recommendations
- StorageModeAdvisor — Import / Direct Lake / Dual mode
- CapacitySizer — SKU recommendations
- SchemaOptimizer — end-to-end analysis
"""

from __future__ import annotations

import pytest

from src.core.schema_optimizer import (
    CapacitySizer,
    ColumnProfile,
    FabricSKU,
    OptimizationReport,
    OptimizationRecommendation,
    PartitionKeyRecommender,
    RecommendationType,
    SchemaOptimizer,
    SchemaProfile,
    Severity,
    StorageMode,
    StorageModeAdvisor,
    TableProfile,
    WorkloadPattern,
)


# ===================================================================
# Helpers
# ===================================================================


def _small_profile() -> SchemaProfile:
    """Small schema (< 0.5 GB)."""
    return SchemaProfile(
        tables=[
            TableProfile(
                name="Orders",
                row_count=10_000,
                size_bytes=50 * 1024 * 1024,  # 50 MB
                column_count=8,
                is_fact=True,
                columns=[
                    ColumnProfile(name="OrderID", cardinality=10000, is_key=True),
                    ColumnProfile(name="CustomerID", cardinality=500),
                    ColumnProfile(name="Region", data_type="string", cardinality=5),
                    ColumnProfile(name="Amount", cardinality=8000),
                ],
            ),
            TableProfile(
                name="Customers",
                row_count=500,
                size_bytes=5 * 1024 * 1024,  # 5 MB
                column_count=4,
                is_dimension=True,
                columns=[
                    ColumnProfile(name="CustomerID", cardinality=500, is_key=True),
                    ColumnProfile(name="Name", data_type="string", cardinality=500),
                ],
            ),
        ],
        total_size_bytes=55 * 1024 * 1024,
    )


def _large_profile() -> SchemaProfile:
    """Large schema (> 10 GB) with wide tables."""
    return SchemaProfile(
        tables=[
            TableProfile(
                name="FactSales",
                row_count=100_000_000,
                size_bytes=50 * (1024 ** 3),  # 50 GB
                column_count=120,
                is_fact=True,
                columns=[
                    ColumnProfile(name="SaleID", cardinality=100_000_000, is_key=True),
                    ColumnProfile(name="TenantID", cardinality=200),
                    ColumnProfile(name="ProductID", cardinality=50_000),
                    ColumnProfile(name="RegionID", cardinality=50),
                    ColumnProfile(name="Status", data_type="string", cardinality=5),
                ],
            ),
            TableProfile(
                name="DimProduct",
                row_count=50_000,
                size_bytes=1 * (1024 ** 3),  # 1 GB
                column_count=15,
                is_dimension=True,
                columns=[
                    ColumnProfile(name="ProductID", cardinality=50_000, is_key=True),
                ],
            ),
        ],
        total_size_bytes=51 * (1024 ** 3),
    )


# ===================================================================
# Data models
# ===================================================================


class TestColumnProfile:
    def test_defaults(self):
        c = ColumnProfile(name="Col1")
        assert c.cardinality == 0
        assert not c.is_key


class TestTableProfile:
    def test_size_mb(self):
        t = TableProfile(name="T", size_bytes=10 * 1024 * 1024)
        assert t.size_mb == 10.0

    def test_size_gb(self):
        t = TableProfile(name="T", size_bytes=2 * (1024 ** 3))
        assert t.size_gb == 2.0


class TestSchemaProfile:
    def test_table_count(self):
        p = _small_profile()
        assert p.table_count == 2

    def test_total_rows(self):
        p = _small_profile()
        assert p.total_rows == 10500

    def test_fact_dim(self):
        p = _small_profile()
        assert len(p.fact_tables) == 1
        assert len(p.dim_tables) == 1


class TestWorkloadPattern:
    def test_defaults(self):
        w = WorkloadPattern(pattern_type="aggregation", frequency=100)
        assert w.frequency == 100


class TestOptimizationReport:
    def test_empty(self):
        r = OptimizationReport()
        assert r.recommendation_count == 0
        assert r.critical_count == 0

    def test_by_type(self):
        r = OptimizationReport(recommendations=[
            OptimizationRecommendation(rec_type=RecommendationType.PARTITION_KEY, severity=Severity.INFO, title="A"),
            OptimizationRecommendation(rec_type=RecommendationType.PARTITION_KEY, severity=Severity.INFO, title="B"),
            OptimizationRecommendation(rec_type=RecommendationType.STORAGE_MODE, severity=Severity.INFO, title="C"),
        ])
        grouped = r.by_type
        assert len(grouped["partition_key"]) == 2
        assert len(grouped["storage_mode"]) == 1


# ===================================================================
# PartitionKeyRecommender
# ===================================================================


class TestPartitionKeyRecommender:
    def test_recommend_basic(self):
        rec = PartitionKeyRecommender()
        table = _small_profile().tables[0]  # Orders
        results = rec.recommend(table)
        assert len(results) >= 1
        assert results[0].rec_type == RecommendationType.PARTITION_KEY

    def test_best_candidate_is_key(self):
        rec = PartitionKeyRecommender()
        table = _small_profile().tables[0]
        results = rec.recommend(table)
        # OrderID (10k cardinality + is_key) should rank high
        best = results[0]
        assert best.column in ("OrderID", "Amount", "CustomerID")

    def test_workload_filter_bonus(self):
        rec = PartitionKeyRecommender()
        table = _small_profile().tables[0]
        workload = [WorkloadPattern(
            tables_involved=["Orders"],
            filter_columns=["CustomerID"],
        )]
        results = rec.recommend(table, workload)
        # CustomerID gets filter bonus
        assert any("CustomerID" in r.metadata.get("candidates", [{}])[0].get("name", "") for r in results if r.metadata.get("candidates"))

    def test_hpk_for_large_table(self):
        rec = PartitionKeyRecommender()
        table = _large_profile().tables[0]  # FactSales - 50 GB
        results = rec.recommend(table)
        hpk = [r for r in results if "Hierarchical" in r.title]
        assert len(hpk) >= 1

    def test_no_candidates(self):
        rec = PartitionKeyRecommender()
        table = TableProfile(
            name="Tiny",
            columns=[ColumnProfile(name="ID", cardinality=1)],  # cardinality too low
        )
        results = rec.recommend(table)
        assert any("No strong" in r.title for r in results)


# ===================================================================
# StorageModeAdvisor
# ===================================================================


class TestStorageModeAdvisor:
    def test_small_data_import(self):
        advisor = StorageModeAdvisor()
        rec = advisor.recommend(_small_profile())
        assert rec.metadata["mode"] == "import"

    def test_large_data_direct_lake(self):
        advisor = StorageModeAdvisor()
        rec = advisor.recommend(_large_profile())
        assert rec.metadata["mode"] == "direct_lake"

    def test_mid_size_direct_lake(self):
        profile = SchemaProfile(
            tables=[TableProfile(name="T", size_bytes=3 * (1024 ** 3))],
            total_size_bytes=3 * (1024 ** 3),  # 3 GB
        )
        advisor = StorageModeAdvisor()
        rec = advisor.recommend(profile)
        assert rec.metadata["mode"] == "direct_lake"

    def test_mixed_workload_dual(self):
        profile = SchemaProfile(
            tables=[
                TableProfile(name="Fact", size_bytes=2 * (1024 ** 3), is_fact=True, read_write_ratio=0.95),
                TableProfile(name="Live", size_bytes=1 * (1024 ** 3), read_write_ratio=0.5),
            ],
            total_size_bytes=3 * (1024 ** 3),
        )
        advisor = StorageModeAdvisor()
        rec = advisor.recommend(profile)
        assert rec.metadata["mode"] == "dual"


# ===================================================================
# CapacitySizer
# ===================================================================


class TestCapacitySizer:
    def test_small_data(self):
        sizer = CapacitySizer()
        rec = sizer.recommend(total_data_gb=5, concurrent_users=5)
        assert rec.metadata["sku"] in ("F2", "F4", "F8", "F16")

    def test_large_data(self):
        sizer = CapacitySizer()
        rec = sizer.recommend(total_data_gb=500, concurrent_users=100)
        # Should recommend F256 or higher
        sku = rec.metadata["sku"]
        assert sku in ("F256", "F512", "F1024")

    def test_monthly_cost(self):
        sizer = CapacitySizer()
        rec = sizer.recommend(total_data_gb=10)
        assert rec.metadata["monthly_cost_usd"] > 0

    def test_headroom_factor(self):
        sizer = CapacitySizer()
        rec = sizer.recommend(total_data_gb=10, concurrent_users=50)
        assert rec.metadata["headroom_factor"] > 1.0


# ===================================================================
# SchemaOptimizer — end-to-end
# ===================================================================


class TestSchemaOptimizer:
    def test_analyze_small(self):
        opt = SchemaOptimizer()
        report = opt.analyze(_small_profile())
        assert report.recommendation_count >= 2  # at least storage + capacity
        assert report.storage_mode == StorageMode.IMPORT

    def test_analyze_large(self):
        opt = SchemaOptimizer()
        report = opt.analyze(_large_profile())
        assert report.storage_mode == StorageMode.DIRECT_LAKE
        # Should flag wide table (120 cols)
        pruning = [r for r in report.recommendations if r.rec_type == RecommendationType.COLUMN_PRUNING]
        assert len(pruning) >= 1

    def test_analyze_with_workload(self):
        opt = SchemaOptimizer()
        workload = [WorkloadPattern(
            pattern_type="aggregation",
            tables_involved=["Orders"],
            filter_columns=["CustomerID"],
        )]
        report = opt.analyze(_small_profile(), workload=workload)
        assert report.recommendation_count >= 2

    def test_low_cardinality_data_type(self):
        profile = SchemaProfile(
            tables=[TableProfile(
                name="T",
                row_count=1000,
                size_bytes=100 * 1024 * 1024,
                columns=[ColumnProfile(name="Status", data_type="string", cardinality=4)],
            )],
            total_size_bytes=100 * 1024 * 1024,
        )
        opt = SchemaOptimizer()
        report = opt.analyze(profile)
        dt_recs = [r for r in report.recommendations if r.rec_type == RecommendationType.DATA_TYPE]
        assert len(dt_recs) >= 1

    def test_report_estimated_cost(self):
        opt = SchemaOptimizer()
        report = opt.analyze(_large_profile())
        assert report.estimated_cost_monthly_usd > 0
