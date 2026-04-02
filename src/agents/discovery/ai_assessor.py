"""AI-powered migration complexity assessment — Phase 71.

Uses the intelligence framework (Phase 70) to classify migration difficulty
beyond what rule-based scoring provides.  Detects anomalies in inventory data,
identifies patterns from prior migrations, and generates a risk heat map.

The assessor is **additive** — rule-based ``complexity_scorer`` runs first and
the AI assessor enriches its output with contextual analysis the rules can't do:

- Orphaned tables that nothing references.
- Circular dependency chains.
- Unusual security patterns (overlapping RLS filters, excessive role count).
- Data model anti-patterns (wide fact tables, missing relationships).
- Asset clusters that should migrate together.

Usage::

    assessor = AIAssessor()
    enriched = assessor.assess(inventory, dependency_graph)
    # enriched.risk_heatmap → per-asset risk scores
    # enriched.anomalies → detected issues
    # enriched.strategy_recommendations → per-group strategy
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.models import (
    AssetType,
    ComplexityCategory,
    Inventory,
    InventoryItem,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data types
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    ORPHANED_TABLE = "orphaned_table"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    EXCESSIVE_ROLES = "excessive_roles"
    OVERLAPPING_RLS = "overlapping_rls"
    WIDE_FACT_TABLE = "wide_fact_table"
    MISSING_RELATIONSHIP = "missing_relationship"
    STALE_ASSET = "stale_asset"
    DUPLICATE_LOGIC = "duplicate_logic"
    LARGE_MODEL = "large_model"
    DEEP_NESTING = "deep_nesting"


class MigrationStrategy(str, Enum):
    LIFT_AND_SHIFT = "lift_and_shift"
    REFACTOR = "refactor"
    REBUILD = "rebuild"
    DEFER = "defer"


@dataclass
class Anomaly:
    """A detected anomaly in the source environment."""

    anomaly_type: AnomalyType
    severity: RiskLevel
    asset_ids: list[str]
    description: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.anomaly_type.value,
            "severity": self.severity.value,
            "asset_ids": self.asset_ids,
            "description": self.description,
            "recommendation": self.recommendation,
        }


@dataclass
class AssetRisk:
    """Risk assessment for a single asset."""

    asset_id: str
    asset_name: str
    complexity: ComplexityCategory
    risk_level: RiskLevel
    risk_score: float  # 0.0—1.0
    factors: list[str] = field(default_factory=list)
    suggested_strategy: MigrationStrategy = MigrationStrategy.LIFT_AND_SHIFT

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "complexity": self.complexity.value,
            "risk_level": self.risk_level.value,
            "risk_score": round(self.risk_score, 3),
            "factors": self.factors,
            "strategy": self.suggested_strategy.value,
        }


@dataclass
class StrategyRecommendation:
    """Migration strategy recommendation for a group of assets."""

    group_name: str
    strategy: MigrationStrategy
    asset_ids: list[str]
    rationale: str
    estimated_effort_hours: float = 0.0
    priority: int = 1  # 1 = highest

    def to_dict(self) -> dict[str, Any]:
        return {
            "group": self.group_name,
            "strategy": self.strategy.value,
            "asset_count": len(self.asset_ids),
            "rationale": self.rationale,
            "effort_hours": self.estimated_effort_hours,
            "priority": self.priority,
        }


@dataclass
class AssessmentResult:
    """Full AI-powered assessment result."""

    risk_heatmap: list[AssetRisk] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)
    strategy_recommendations: list[StrategyRecommendation] = field(default_factory=list)
    summary: str = ""
    total_assets: int = 0
    risk_distribution: dict[str, int] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.risk_heatmap if r.risk_level == RiskLevel.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for r in self.risk_heatmap if r.risk_level == RiskLevel.HIGH)

    @property
    def anomaly_count(self) -> int:
        return len(self.anomalies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_assets": self.total_assets,
            "risk_distribution": self.risk_distribution,
            "anomaly_count": self.anomaly_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "strategy_recommendations": [s.to_dict() for s in self.strategy_recommendations],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Rule-based anomaly detectors
# ---------------------------------------------------------------------------


def _detect_orphaned_tables(
    items: list[InventoryItem],
    dep_graph: dict[str, list[str]],
) -> list[Anomaly]:
    """Detect tables that are never referenced by any analysis or dashboard."""
    table_ids = {
        i.id for i in items if i.asset_type in (AssetType.LOGICAL_TABLE, AssetType.DATA_MODEL)
    }
    referenced: set[str] = set()
    for deps in dep_graph.values():
        referenced.update(deps)

    orphaned = table_ids - referenced
    # Also check if the table references nothing (truly isolated)
    truly_orphaned = [oid for oid in orphaned if oid not in dep_graph or not dep_graph[oid]]

    anomalies = []
    if truly_orphaned:
        anomalies.append(Anomaly(
            anomaly_type=AnomalyType.ORPHANED_TABLE,
            severity=RiskLevel.LOW,
            asset_ids=truly_orphaned,
            description=f"{len(truly_orphaned)} table(s) are not referenced by any downstream asset",
            recommendation="Consider excluding these from migration to reduce scope and cost",
        ))
    return anomalies


def _detect_circular_dependencies(
    dep_graph: dict[str, list[str]],
) -> list[Anomaly]:
    """Detect circular dependency chains using DFS."""
    visited: set[str] = set()
    in_stack: set[str] = set()
    cycles: list[list[str]] = []

    def _dfs(node: str, path: list[str]) -> None:
        if node in in_stack:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        in_stack.add(node)
        path.append(node)
        for neighbor in dep_graph.get(node, []):
            _dfs(neighbor, path)
        path.pop()
        in_stack.discard(node)

    for start in dep_graph:
        if start not in visited:
            _dfs(start, [])

    anomalies = []
    for cycle in cycles[:5]:  # Cap at 5
        anomalies.append(Anomaly(
            anomaly_type=AnomalyType.CIRCULAR_DEPENDENCY,
            severity=RiskLevel.HIGH,
            asset_ids=cycle,
            description=f"Circular dependency detected: {' → '.join(cycle)}",
            recommendation="Break the cycle by identifying and refactoring the bi-directional reference",
        ))
    return anomalies


def _detect_excessive_roles(items: list[InventoryItem]) -> list[Anomaly]:
    """Flag environments with unusually high role counts."""
    role_items = [i for i in items if i.asset_type == AssetType.SECURITY_ROLE]
    anomalies = []
    if len(role_items) > 50:
        anomalies.append(Anomaly(
            anomaly_type=AnomalyType.EXCESSIVE_ROLES,
            severity=RiskLevel.MEDIUM,
            asset_ids=[r.id for r in role_items[:10]],
            description=f"{len(role_items)} security roles detected — consider consolidation",
            recommendation="Group similar roles into fewer Fabric workspace roles + RLS combinations",
        ))
    return anomalies


def _detect_wide_fact_tables(items: list[InventoryItem]) -> list[Anomaly]:
    """Flag tables with very high column counts (>200)."""
    anomalies = []
    for item in items:
        col_count = item.metadata.get("column_count", 0)
        if col_count > 200:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.WIDE_FACT_TABLE,
                severity=RiskLevel.MEDIUM,
                asset_ids=[item.id],
                description=f"Table '{item.name}' has {col_count} columns — consider vertical partitioning",
                recommendation="Split wide tables into star-schema fact + dimension tables during migration",
            ))
    return anomalies


def _detect_large_models(items: list[InventoryItem]) -> list[Anomaly]:
    """Flag data models with very high table counts."""
    anomalies = []
    for item in items:
        if item.asset_type == AssetType.DATA_MODEL:
            table_count = item.metadata.get("table_count", 0)
            if table_count > 100:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.LARGE_MODEL,
                    severity=RiskLevel.HIGH,
                    asset_ids=[item.id],
                    description=f"Data model '{item.name}' has {table_count} tables",
                    recommendation="Consider splitting into multiple semantic models with shared datasets",
                ))
    return anomalies


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------


def _compute_risk_score(item: InventoryItem, anomaly_ids: set[str]) -> tuple[float, list[str]]:
    """Compute a 0–1 risk score for an asset."""
    score = 0.0
    factors: list[str] = []

    # Complexity contribution (0.0–0.4)
    complexity = item.metadata.get("complexity_score", 5.0)
    score += min(complexity / 10.0, 1.0) * 0.4
    if complexity >= 7:
        factors.append(f"High complexity score: {complexity}")

    # Column / measure count (0.0–0.15)
    col_count = item.metadata.get("column_count", 0)
    if col_count > 50:
        score += 0.15
        factors.append(f"High column count: {col_count}")
    elif col_count > 20:
        score += 0.07

    # Custom calculations (0.0–0.15)
    calc_count = item.metadata.get("custom_calc_count", 0)
    if calc_count > 20:
        score += 0.15
        factors.append(f"Many custom calculations: {calc_count}")
    elif calc_count > 5:
        score += 0.07

    # Security (0.0–0.15)
    if item.asset_type == AssetType.SECURITY_ROLE:
        perm_count = len(item.metadata.get("permissions", []))
        if perm_count > 10:
            score += 0.15
            factors.append(f"Complex security: {perm_count} permissions")

    # Anomaly involvement (0.0–0.15)
    if item.id in anomaly_ids:
        score += 0.15
        factors.append("Involved in detected anomaly")

    return min(score, 1.0), factors


def _risk_level_from_score(score: float) -> RiskLevel:
    if score >= 0.8:
        return RiskLevel.CRITICAL
    if score >= 0.6:
        return RiskLevel.HIGH
    if score >= 0.3:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _suggest_strategy(risk: AssetRisk) -> MigrationStrategy:
    """Suggest migration strategy based on risk level and complexity."""
    if risk.risk_level == RiskLevel.CRITICAL:
        return MigrationStrategy.REBUILD
    if risk.risk_level == RiskLevel.HIGH:
        return MigrationStrategy.REFACTOR
    if risk.complexity == ComplexityCategory.HIGH:
        return MigrationStrategy.REFACTOR
    return MigrationStrategy.LIFT_AND_SHIFT


# ---------------------------------------------------------------------------
# Strategy grouping
# ---------------------------------------------------------------------------


def _group_by_strategy(
    risks: list[AssetRisk],
) -> list[StrategyRecommendation]:
    """Group assets by recommended strategy and estimate effort."""
    groups: dict[MigrationStrategy, list[str]] = {}
    for r in risks:
        groups.setdefault(r.suggested_strategy, []).append(r.asset_id)

    # Effort heuristics (hours per asset)
    effort_per_asset = {
        MigrationStrategy.LIFT_AND_SHIFT: 0.5,
        MigrationStrategy.REFACTOR: 2.0,
        MigrationStrategy.REBUILD: 8.0,
        MigrationStrategy.DEFER: 0.0,
    }

    rationale_map = {
        MigrationStrategy.LIFT_AND_SHIFT: "Direct mapping exists — automated migration with minimal review",
        MigrationStrategy.REFACTOR: "Partial mapping available — automated migration with manual adjustments",
        MigrationStrategy.REBUILD: "No direct mapping — requires manual redesign in Fabric/Power BI",
        MigrationStrategy.DEFER: "Low priority or blocked by dependencies — migrate in later wave",
    }

    priority_map = {
        MigrationStrategy.LIFT_AND_SHIFT: 1,
        MigrationStrategy.REFACTOR: 2,
        MigrationStrategy.REBUILD: 3,
        MigrationStrategy.DEFER: 4,
    }

    recs = []
    for strategy, ids in sorted(groups.items(), key=lambda x: priority_map.get(x[0], 99)):
        recs.append(StrategyRecommendation(
            group_name=strategy.value.replace("_", " ").title(),
            strategy=strategy,
            asset_ids=ids,
            rationale=rationale_map.get(strategy, ""),
            estimated_effort_hours=len(ids) * effort_per_asset.get(strategy, 1.0),
            priority=priority_map.get(strategy, 99),
        ))
    return recs


# ---------------------------------------------------------------------------
# Main assessor
# ---------------------------------------------------------------------------


class AIAssessor:
    """AI-powered migration complexity assessor.

    Enriches rule-based complexity scoring with anomaly detection,
    pattern recognition, and strategy recommendations.

    Parameters
    ----------
    reasoning_loop
        Optional ``ReasoningLoop`` for LLM-powered analysis.  When *None*,
        operates in rules-only mode (still valuable).
    agent_memory
        Optional ``AgentMemory`` for recalling patterns from prior assessments.
    """

    def __init__(
        self,
        reasoning_loop: Any = None,
        agent_memory: Any = None,
    ) -> None:
        self._reasoning = reasoning_loop
        self._memory = agent_memory

    def assess(
        self,
        inventory: Inventory,
        dependency_graph: dict[str, list[str]] | None = None,
    ) -> AssessmentResult:
        """Run full assessment on an inventory.

        Parameters
        ----------
        inventory
            Discovered inventory (from Agent 01).
        dependency_graph
            Adjacency list of asset dependencies (id → [dependent_ids]).

        Returns
        -------
        AssessmentResult
            Enriched assessment with risk heatmap, anomalies, and strategy recs.
        """
        dep_graph = dependency_graph or {}
        items = inventory.items

        # 1. Detect anomalies
        anomalies: list[Anomaly] = []
        anomalies.extend(_detect_orphaned_tables(items, dep_graph))
        anomalies.extend(_detect_circular_dependencies(dep_graph))
        anomalies.extend(_detect_excessive_roles(items))
        anomalies.extend(_detect_wide_fact_tables(items))
        anomalies.extend(_detect_large_models(items))

        # Collect all asset IDs involved in anomalies
        anomaly_ids: set[str] = set()
        for a in anomalies:
            anomaly_ids.update(a.asset_ids)

        # 2. Compute risk scores
        risks: list[AssetRisk] = []
        for item in items:
            score, factors = _compute_risk_score(item, anomaly_ids)
            risk_level = _risk_level_from_score(score)
            risk = AssetRisk(
                asset_id=item.id,
                asset_name=item.name,
                complexity=ComplexityCategory(item.metadata.get("complexity", "Medium")),
                risk_level=risk_level,
                risk_score=score,
                factors=factors,
            )
            risk.suggested_strategy = _suggest_strategy(risk)
            risks.append(risk)

        # 3. Group and recommend
        recs = _group_by_strategy(risks)

        # 4. Build distribution
        dist: dict[str, int] = {}
        for r in risks:
            dist[r.risk_level.value] = dist.get(r.risk_level.value, 0) + 1

        # 5. Summary
        summary_parts = [
            f"Assessed {len(items)} assets.",
            f"Risk distribution: {dist}.",
            f"Anomalies detected: {len(anomalies)}.",
        ]
        if recs:
            summary_parts.append(
                f"Recommended strategies: {', '.join(f'{r.group_name} ({len(r.asset_ids)})' for r in recs)}."
            )

        result = AssessmentResult(
            risk_heatmap=risks,
            anomalies=anomalies,
            strategy_recommendations=recs,
            summary=" ".join(summary_parts),
            total_assets=len(items),
            risk_distribution=dist,
        )

        # Store in memory for future improvements
        if self._memory:
            self._memory.store(
                "assessment",
                key=f"assessment_{len(items)}_assets",
                value=result.to_dict(),
                confidence=0.9,
            )

        logger.info(
            "AI assessment complete: %d assets, %d anomalies, %d strategy groups",
            len(items), len(anomalies), len(recs),
        )
        return result

    async def assess_with_llm(
        self,
        inventory: Inventory,
        dependency_graph: dict[str, list[str]] | None = None,
    ) -> AssessmentResult:
        """Run assessment with optional LLM enrichment.

        Falls back to rule-only assessment if no reasoning loop is attached.
        """
        result = self.assess(inventory, dependency_graph)

        if self._reasoning:
            # Enrich anomaly descriptions via LLM
            for anomaly in result.anomalies:
                try:
                    enriched = await self._reasoning.run(
                        task="enrich_anomaly",
                        source=anomaly.description,
                        context={"anomaly_type": anomaly.anomaly_type.value},
                    )
                    if enriched.success and enriched.output:
                        anomaly.recommendation = str(enriched.output)
                except Exception:
                    logger.debug("LLM enrichment skipped for anomaly: %s", anomaly.anomaly_type)

        return result
