"""Strategy recommender — migration approach per asset group — Phase 71.

Works with ``AIAssessor`` to recommend specific migration strategies based on
complexity, dependency depth, business domain analysis, and pattern matching
from prior migrations stored in agent memory.

Three core strategies:
- **Lift-and-shift**: Direct rule-based mapping exists; fully automated.
- **Refactor**: Partial mapping + manual tuning; semi-automated.
- **Rebuild**: No mapping available; manual redesign required.
- **Defer**: Low priority or blocked; schedule for later wave.

Usage::

    recommender = StrategyRecommender()
    recommendations = recommender.recommend(inventory, risk_heatmap)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.core.models import (
    AssetType,
    ComplexityCategory,
    Inventory,
    InventoryItem,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain classification patterns
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "finance": ["revenue", "cost", "profit", "budget", "forecast", "gl", "ledger", "journal", "ar", "ap"],
    "sales": ["sales", "order", "customer", "deal", "pipeline", "quota", "opportunity"],
    "hr": ["employee", "headcount", "salary", "payroll", "benefit", "leave", "attendance"],
    "supply_chain": ["inventory", "warehouse", "shipping", "logistics", "procurement", "supplier"],
    "marketing": ["campaign", "lead", "conversion", "impression", "click", "channel"],
}


# ---------------------------------------------------------------------------
# Wave grouping strategies
# ---------------------------------------------------------------------------


@dataclass
class DomainCluster:
    """A cluster of assets belonging to the same business domain."""

    domain: str
    asset_ids: list[str] = field(default_factory=list)
    avg_complexity: float = 0.0
    total_assets: int = 0
    recommended_wave: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "asset_count": self.total_assets,
            "avg_complexity": round(self.avg_complexity, 2),
            "wave": self.recommended_wave,
        }


@dataclass
class WaveAssignment:
    """Assignment of assets to migration waves."""

    wave_number: int
    domain: str
    strategy: str
    asset_ids: list[str] = field(default_factory=list)
    estimated_hours: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave": self.wave_number,
            "domain": self.domain,
            "strategy": self.strategy,
            "asset_count": len(self.asset_ids),
            "estimated_hours": self.estimated_hours,
        }


@dataclass
class StrategyPlan:
    """Complete strategy plan with wave assignments."""

    waves: list[WaveAssignment] = field(default_factory=list)
    domain_clusters: list[DomainCluster] = field(default_factory=list)
    total_waves: int = 0
    total_estimated_hours: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_waves": self.total_waves,
            "total_estimated_hours": round(self.total_estimated_hours, 1),
            "waves": [w.to_dict() for w in self.waves],
            "domains": [d.to_dict() for d in self.domain_clusters],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Domain classifier
# ---------------------------------------------------------------------------


def classify_domain(item: InventoryItem) -> str:
    """Classify an asset into a business domain based on name and metadata."""
    searchable = (item.name + " " + item.metadata.get("description", "")).lower()

    best_domain = "general"
    best_score = 0

    for domain, keywords in _DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in searchable)
        if score > best_score:
            best_score = score
            best_domain = domain

    return best_domain


def _complexity_to_numeric(cat: ComplexityCategory) -> float:
    """Map complexity category to a numeric value."""
    return {"Low": 1.0, "Medium": 2.0, "High": 3.0}.get(cat.value, 2.0)


# ---------------------------------------------------------------------------
# Strategy recommender
# ---------------------------------------------------------------------------


class StrategyRecommender:
    """Recommends migration strategies and wave assignments.

    Parameters
    ----------
    max_assets_per_wave
        Maximum number of assets per migration wave.
    agent_memory
        Optional agent memory for pattern matching from prior migrations.
    """

    def __init__(
        self,
        max_assets_per_wave: int = 50,
        agent_memory: Any = None,
    ) -> None:
        self._max_per_wave = max_assets_per_wave
        self._memory = agent_memory

    def recommend(
        self,
        inventory: Inventory,
        risk_heatmap: list[Any] | None = None,
    ) -> StrategyPlan:
        """Generate a migration strategy plan.

        Parameters
        ----------
        inventory
            Full source inventory.
        risk_heatmap
            Risk assessments from ``AIAssessor`` (optional).
        """
        items = inventory.items
        if not items:
            return StrategyPlan(summary="No assets to plan.")

        # 1. Classify domains
        domain_map: dict[str, list[InventoryItem]] = {}
        for item in items:
            domain = classify_domain(item)
            domain_map.setdefault(domain, []).append(item)

        # 2. Build risk lookup
        risk_lookup: dict[str, Any] = {}
        if risk_heatmap:
            for r in risk_heatmap:
                risk_lookup[r.asset_id] = r

        # 3. Build domain clusters
        clusters: list[DomainCluster] = []
        for domain, domain_items in sorted(domain_map.items()):
            complexities = []
            for item in domain_items:
                cat = item.metadata.get("complexity", "Medium")
                try:
                    complexities.append(_complexity_to_numeric(ComplexityCategory(cat)))
                except ValueError:
                    complexities.append(2.0)

            avg_c = sum(complexities) / len(complexities) if complexities else 2.0
            cluster = DomainCluster(
                domain=domain,
                asset_ids=[i.id for i in domain_items],
                avg_complexity=avg_c,
                total_assets=len(domain_items),
            )
            clusters.append(cluster)

        # 4. Assign waves (simpler domains first, complex later)
        clusters.sort(key=lambda c: c.avg_complexity)
        wave_assignments: list[WaveAssignment] = []
        wave_num = 1

        for cluster in clusters:
            # Split large clusters into multiple waves
            chunk_start = 0
            while chunk_start < len(cluster.asset_ids):
                chunk = cluster.asset_ids[chunk_start : chunk_start + self._max_per_wave]

                # Determine dominant strategy
                strategies = {"lift_and_shift": 0, "refactor": 0, "rebuild": 0}
                for aid in chunk:
                    risk = risk_lookup.get(aid)
                    if risk:
                        strategies[risk.suggested_strategy.value] = (
                            strategies.get(risk.suggested_strategy.value, 0) + 1
                        )
                    else:
                        strategies["lift_and_shift"] += 1

                dominant = max(strategies, key=lambda k: strategies[k])

                effort_map = {"lift_and_shift": 0.5, "refactor": 2.0, "rebuild": 8.0}
                estimated = len(chunk) * effort_map.get(dominant, 1.0)

                wave_assignments.append(WaveAssignment(
                    wave_number=wave_num,
                    domain=cluster.domain,
                    strategy=dominant,
                    asset_ids=chunk,
                    estimated_hours=estimated,
                ))
                cluster.recommended_wave = wave_num
                wave_num += 1
                chunk_start += self._max_per_wave

        total_hours = sum(w.estimated_hours for w in wave_assignments)

        plan = StrategyPlan(
            waves=wave_assignments,
            domain_clusters=clusters,
            total_waves=len(wave_assignments),
            total_estimated_hours=total_hours,
            summary=(
                f"Plan: {len(wave_assignments)} waves across {len(clusters)} domains, "
                f"~{total_hours:.0f} hours estimated for {len(items)} assets."
            ),
        )

        logger.info(
            "Strategy plan: %d waves, %d domains, %.0f hours",
            plan.total_waves, len(clusters), total_hours,
        )
        return plan
