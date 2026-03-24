"""AI-Assisted Schema Optimization — intelligent recommendations for Fabric targets.

Provides:
- ``SchemaProfile`` — statistics and metadata for a table/column set.
- ``OptimizationRecommendation`` — a single actionable recommendation.
- ``WorkloadPattern`` — detected query workload pattern.
- ``SchemaOptimizer`` — rule-based + LLM-assisted schema optimization engine.
- ``PartitionKeyRecommender`` — hierarchical partition key recommendations.
- ``StorageModeAdvisor`` — Direct Lake vs. Import mode recommendations.
- ``CapacitySizer`` — Fabric capacity sizing estimates.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RecommendationType(str, Enum):
    PARTITION_KEY = "partition_key"
    STORAGE_MODE = "storage_mode"
    DATA_TYPE = "data_type"
    INDEX = "index"
    DENORMALIZATION = "denormalization"
    AGGREGATION_TABLE = "aggregation_table"
    COLUMN_PRUNING = "column_pruning"
    CAPACITY_SKU = "capacity_sku"


class Severity(str, Enum):
    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    CRITICAL = "critical"


class StorageMode(str, Enum):
    DIRECT_LAKE = "direct_lake"
    IMPORT = "import"
    DUAL = "dual"
    LIVE = "live"


class FabricSKU(str, Enum):
    F2 = "F2"
    F4 = "F4"
    F8 = "F8"
    F16 = "F16"
    F32 = "F32"
    F64 = "F64"
    F128 = "F128"
    F256 = "F256"
    F512 = "F512"
    F1024 = "F1024"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ColumnProfile:
    """Statistics for a single column."""

    name: str
    data_type: str = ""
    cardinality: int = 0
    null_pct: float = 0.0
    avg_length: float = 0.0
    is_key: bool = False
    is_partition_candidate: bool = False
    sample_values: list[str] = field(default_factory=list)


@dataclass
class TableProfile:
    """Statistics for a single table."""

    name: str
    row_count: int = 0
    size_bytes: int = 0
    column_count: int = 0
    columns: list[ColumnProfile] = field(default_factory=list)
    access_frequency: float = 0.0  # queries per hour
    read_write_ratio: float = 0.95  # 0.95 = mostly reads
    is_fact: bool = False
    is_dimension: bool = False

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)

    @property
    def size_gb(self) -> float:
        return round(self.size_bytes / (1024 ** 3), 4)


@dataclass
class SchemaProfile:
    """Aggregate profile for an entire schema."""

    tables: list[TableProfile] = field(default_factory=list)
    total_size_bytes: int = 0
    query_patterns: list[str] = field(default_factory=list)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def total_rows(self) -> int:
        return sum(t.row_count for t in self.tables)

    @property
    def total_size_gb(self) -> float:
        return round(self.total_size_bytes / (1024 ** 3), 2)

    @property
    def fact_tables(self) -> list[TableProfile]:
        return [t for t in self.tables if t.is_fact]

    @property
    def dim_tables(self) -> list[TableProfile]:
        return [t for t in self.tables if t.is_dimension]


@dataclass
class WorkloadPattern:
    """A detected query workload pattern."""

    pattern_type: str = ""  # point_lookup, range_scan, aggregation, join_heavy
    frequency: float = 0.0  # queries per hour
    tables_involved: list[str] = field(default_factory=list)
    filter_columns: list[str] = field(default_factory=list)
    group_by_columns: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class OptimizationRecommendation:
    """A single actionable recommendation."""

    rec_type: RecommendationType
    severity: Severity
    table: str = ""
    column: str = ""
    title: str = ""
    description: str = ""
    impact: str = ""
    action: str = ""
    confidence: float = 0.8
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationReport:
    """Full optimization report."""

    recommendations: list[OptimizationRecommendation] = field(default_factory=list)
    schema_profile: SchemaProfile | None = None
    workload_patterns: list[WorkloadPattern] = field(default_factory=list)
    storage_mode: StorageMode = StorageMode.DIRECT_LAKE
    recommended_sku: FabricSKU = FabricSKU.F8
    estimated_cost_monthly_usd: float = 0.0

    @property
    def recommendation_count(self) -> int:
        return len(self.recommendations)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.recommendations if r.severity == Severity.CRITICAL)

    @property
    def by_type(self) -> dict[str, list[OptimizationRecommendation]]:
        grouped: dict[str, list[OptimizationRecommendation]] = {}
        for r in self.recommendations:
            grouped.setdefault(r.rec_type.value, []).append(r)
        return grouped


# ---------------------------------------------------------------------------
# Partition Key Recommender
# ---------------------------------------------------------------------------


class PartitionKeyRecommender:
    """Recommend hierarchical partition keys for Fabric Lakehouse tables.

    Rules:
    - High cardinality columns preferred (> 100 unique values)
    - Filter columns from workload patterns strongly preferred
    - Avoid low-cardinality columns (< 10 unique values)
    - Prefer columns already used as partition keys in source
    - 20 GB per logical partition limit → recommend HPK if data > 20 GB
    """

    HPK_THRESHOLD_GB = 20.0

    def recommend(
        self,
        table: TableProfile,
        workload: list[WorkloadPattern] | None = None,
    ) -> list[OptimizationRecommendation]:
        recs: list[OptimizationRecommendation] = []

        # Identify candidate columns
        candidates = self._rank_candidates(table, workload or [])

        if not candidates:
            recs.append(OptimizationRecommendation(
                rec_type=RecommendationType.PARTITION_KEY,
                severity=Severity.INFO,
                table=table.name,
                title="No strong partition key candidate",
                description="Consider adding a high-cardinality column for partitioning.",
            ))
            return recs

        best = candidates[0]
        recs.append(OptimizationRecommendation(
            rec_type=RecommendationType.PARTITION_KEY,
            severity=Severity.SUGGESTION,
            table=table.name,
            column=best["name"],
            title=f"Recommended partition key: {best['name']}",
            description=f"Cardinality: {best['cardinality']}, Score: {best['score']:.2f}",
            action=f"Use '{best['name']}' as the partition key for '{table.name}'",
            confidence=min(best["score"], 1.0),
            metadata={"candidates": candidates},
        ))

        # HPK recommendation for large tables
        if table.size_gb > self.HPK_THRESHOLD_GB and len(candidates) >= 2:
            second = candidates[1]
            recs.append(OptimizationRecommendation(
                rec_type=RecommendationType.PARTITION_KEY,
                severity=Severity.WARNING,
                table=table.name,
                title="Hierarchical Partition Key recommended",
                description=(
                    f"Table '{table.name}' is {table.size_gb:.1f} GB — exceeds 20 GB single-partition limit. "
                    f"Use HPK with levels: [{best['name']}, {second['name']}]."
                ),
                action=f"Configure HPK: /{best['name']}/{second['name']}",
                confidence=0.85,
                metadata={"hpk_levels": [best["name"], second["name"]]},
            ))

        return recs

    def _rank_candidates(self, table: TableProfile, workload: list[WorkloadPattern]) -> list[dict[str, Any]]:
        """Score and rank columns as partition key candidates."""
        # Gather filter columns from workload patterns
        filter_cols = set()
        for w in workload:
            if table.name in w.tables_involved:
                filter_cols.update(w.filter_columns)

        candidates: list[dict[str, Any]] = []
        for col in table.columns:
            if col.cardinality < 2:
                continue

            score = 0.0
            # Cardinality score (log scale, normalized)
            if col.cardinality > 0:
                score += min(math.log10(max(col.cardinality, 1)) / 6, 1.0) * 0.5

            # Filter frequency bonus
            if col.name in filter_cols:
                score += 0.3

            # Key column bonus
            if col.is_key:
                score += 0.1

            # Penalty for low cardinality
            if col.cardinality < 10:
                score -= 0.2

            # Penalty for high null percentage
            if col.null_pct > 0.1:
                score -= 0.1

            if score > 0:
                candidates.append({
                    "name": col.name,
                    "cardinality": col.cardinality,
                    "score": round(score, 3),
                    "is_filter": col.name in filter_cols,
                })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates


# ---------------------------------------------------------------------------
# Storage Mode Advisor
# ---------------------------------------------------------------------------


class StorageModeAdvisor:
    """Recommend Direct Lake vs. Import mode for Fabric semantic models.

    Heuristics:
    - Direct Lake: large data (> 1 GB), mostly reads, Lakehouse source
    - Import: small data, complex transformations, real-time requirements
    - Dual: some tables need real-time, others can use Direct Lake
    """

    DIRECT_LAKE_MIN_GB = 0.5
    IMPORT_MAX_GB = 100.0

    def recommend(self, profile: SchemaProfile) -> OptimizationRecommendation:
        total_gb = profile.total_size_gb
        fact_count = len(profile.fact_tables)

        # Rule: small data → Import
        if total_gb < self.DIRECT_LAKE_MIN_GB:
            return OptimizationRecommendation(
                rec_type=RecommendationType.STORAGE_MODE,
                severity=Severity.SUGGESTION,
                title="Import mode recommended",
                description=f"Total data size ({total_gb:.2f} GB) is small. Import mode provides fastest queries.",
                action="Set semantic model storage mode to Import.",
                confidence=0.9,
                metadata={"mode": StorageMode.IMPORT.value, "total_gb": total_gb},
            )

        # Rule: very large data → Direct Lake
        if total_gb > 10:
            return OptimizationRecommendation(
                rec_type=RecommendationType.STORAGE_MODE,
                severity=Severity.SUGGESTION,
                title="Direct Lake mode recommended",
                description=(
                    f"Total data size ({total_gb:.2f} GB) is large. "
                    "Direct Lake avoids data duplication and provides near-real-time refresh."
                ),
                action="Set semantic model storage mode to DirectLake with Lakehouse source.",
                confidence=0.95,
                metadata={"mode": StorageMode.DIRECT_LAKE.value, "total_gb": total_gb},
            )

        # Rule: mixed → Dual or Direct Lake
        if fact_count > 0 and any(t.read_write_ratio < 0.8 for t in profile.tables):
            return OptimizationRecommendation(
                rec_type=RecommendationType.STORAGE_MODE,
                severity=Severity.SUGGESTION,
                title="Dual mode recommended",
                description="Mix of read-heavy and write-heavy tables detected.",
                action="Use Dual mode: Direct Lake for facts, Import for frequently written dimensions.",
                confidence=0.7,
                metadata={"mode": StorageMode.DUAL.value},
            )

        # Default: Direct Lake for mid-size
        return OptimizationRecommendation(
            rec_type=RecommendationType.STORAGE_MODE,
            severity=Severity.SUGGESTION,
            title="Direct Lake mode recommended",
            description=f"Total data size ({total_gb:.2f} GB) suits Direct Lake.",
            action="Set semantic model storage mode to DirectLake.",
            confidence=0.85,
            metadata={"mode": StorageMode.DIRECT_LAKE.value},
        )


# ---------------------------------------------------------------------------
# Capacity Sizer
# ---------------------------------------------------------------------------

# Fabric SKU specs (approximate CU and cost)
_SKU_SPECS: dict[FabricSKU, dict[str, Any]] = {
    FabricSKU.F2: {"cu": 2, "max_data_gb": 10, "cost_usd": 263},
    FabricSKU.F4: {"cu": 4, "max_data_gb": 25, "cost_usd": 526},
    FabricSKU.F8: {"cu": 8, "max_data_gb": 50, "cost_usd": 1051},
    FabricSKU.F16: {"cu": 16, "max_data_gb": 100, "cost_usd": 2102},
    FabricSKU.F32: {"cu": 32, "max_data_gb": 200, "cost_usd": 4205},
    FabricSKU.F64: {"cu": 64, "max_data_gb": 400, "cost_usd": 8409},
    FabricSKU.F128: {"cu": 128, "max_data_gb": 800, "cost_usd": 16819},
    FabricSKU.F256: {"cu": 256, "max_data_gb": 1600, "cost_usd": 33638},
    FabricSKU.F512: {"cu": 512, "max_data_gb": 3200, "cost_usd": 67275},
    FabricSKU.F1024: {"cu": 1024, "max_data_gb": 6400, "cost_usd": 134550},
}


class CapacitySizer:
    """Estimate the right Fabric capacity SKU based on data size and workload.

    Factors:
    - Total data volume (GB)
    - Query concurrency
    - Refresh frequency
    - Number of semantic models
    """

    def recommend(
        self,
        total_data_gb: float,
        concurrent_users: int = 10,
        refresh_frequency_per_day: int = 4,
        semantic_model_count: int = 1,
    ) -> OptimizationRecommendation:
        # Simple sizing: data volume is primary driver, with headroom
        required_gb = total_data_gb * 1.5  # 50% headroom
        # Workload adjustment: more users need more capacity
        workload_factor = 1.0 + (concurrent_users / 100) + (refresh_frequency_per_day / 48)

        effective_gb = required_gb * workload_factor

        # Find smallest SKU that fits
        selected = FabricSKU.F1024  # fallback
        selected_cost = _SKU_SPECS[FabricSKU.F1024]["cost_usd"]

        for sku in FabricSKU:
            specs = _SKU_SPECS[sku]
            if specs["max_data_gb"] >= effective_gb:
                selected = sku
                selected_cost = specs["cost_usd"]
                break

        return OptimizationRecommendation(
            rec_type=RecommendationType.CAPACITY_SKU,
            severity=Severity.SUGGESTION,
            title=f"Recommended SKU: {selected.value}",
            description=(
                f"For {total_data_gb:.1f} GB data, {concurrent_users} concurrent users, "
                f"{refresh_frequency_per_day} refreshes/day. "
                f"Effective capacity need: {effective_gb:.1f} GB."
            ),
            action=f"Provision a Fabric {selected.value} capacity.",
            confidence=0.75,
            metadata={
                "sku": selected.value,
                "monthly_cost_usd": selected_cost,
                "effective_gb": round(effective_gb, 1),
                "data_gb": total_data_gb,
                "headroom_factor": workload_factor,
            },
        )


# ---------------------------------------------------------------------------
# Schema Optimizer — orchestrates all recommendations
# ---------------------------------------------------------------------------


class SchemaOptimizer:
    """Top-level optimizer that combines all recommendation engines.

    Usage::

        optimizer = SchemaOptimizer()
        report = optimizer.analyze(schema_profile, workload_patterns)
        for rec in report.recommendations:
            print(rec.title)
    """

    def __init__(self) -> None:
        self._partition_rec = PartitionKeyRecommender()
        self._storage_advisor = StorageModeAdvisor()
        self._capacity_sizer = CapacitySizer()

    def analyze(
        self,
        profile: SchemaProfile,
        workload: list[WorkloadPattern] | None = None,
        concurrent_users: int = 10,
        refresh_frequency_per_day: int = 4,
    ) -> OptimizationReport:
        recs: list[OptimizationRecommendation] = []

        workload = workload or []

        # 1. Partition key recommendations per fact table
        for table in profile.tables:
            if table.is_fact or table.row_count > 1_000_000:
                recs.extend(self._partition_rec.recommend(table, workload))

        # 2. Storage mode
        storage_rec = self._storage_advisor.recommend(profile)
        recs.append(storage_rec)
        mode = StorageMode(storage_rec.metadata.get("mode", "direct_lake"))

        # 3. Capacity sizing
        cap_rec = self._capacity_sizer.recommend(
            total_data_gb=profile.total_size_gb,
            concurrent_users=concurrent_users,
            refresh_frequency_per_day=refresh_frequency_per_day,
            semantic_model_count=max(1, len(profile.fact_tables)),
        )
        recs.append(cap_rec)
        sku = FabricSKU(cap_rec.metadata.get("sku", "F8"))

        # 4. Column pruning: flag wide tables
        for table in profile.tables:
            if table.column_count > 100:
                recs.append(OptimizationRecommendation(
                    rec_type=RecommendationType.COLUMN_PRUNING,
                    severity=Severity.WARNING,
                    table=table.name,
                    title=f"Wide table: {table.column_count} columns",
                    description="Tables with >100 columns may degrade Direct Lake performance.",
                    action=f"Review '{table.name}' for unused columns.",
                ))

        # 5. Data type optimization
        for table in profile.tables:
            for col in table.columns:
                if col.data_type == "string" and col.cardinality < 50 and col.cardinality > 0:
                    recs.append(OptimizationRecommendation(
                        rec_type=RecommendationType.DATA_TYPE,
                        severity=Severity.INFO,
                        table=table.name,
                        column=col.name,
                        title=f"Low-cardinality string: {col.name}",
                        description=(
                            f"Column has only {col.cardinality} unique values. "
                            "Dictionary encoding will handle this well in Direct Lake."
                        ),
                    ))

        return OptimizationReport(
            recommendations=recs,
            schema_profile=profile,
            workload_patterns=workload,
            storage_mode=mode,
            recommended_sku=sku,
            estimated_cost_monthly_usd=cap_rec.metadata.get("monthly_cost_usd", 0),
        )
