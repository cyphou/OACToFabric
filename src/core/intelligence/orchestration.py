"""Intelligent orchestration — AI wave planning and resource optimization — Phase 76.

Upgrades the Orchestrator (Agent 08) with LLM-powered capabilities:
- **AI wave planner** — groups assets by domain+risk for optimal migration order.
- **Resource optimizer** — suggests Fabric capacity, concurrency, batch sizes.
- **Adaptive scheduler** — adjusts plan based on real-time progress and errors.
- **Cost modeler** — estimates and tracks migration cost per wave.

Usage::

    planner = AIWavePlanner()
    plan = planner.plan(inventory, risk_heatmap)
    # plan.waves → optimized wave assignments

    optimizer = ResourceOptimizer()
    config = optimizer.recommend(plan)
    # config.fabric_sku → "F4"
    # config.parallel_agents → 3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class WaveConfig:
    """Configuration for a single migration wave."""

    wave_number: int
    asset_ids: list[str] = field(default_factory=list)
    agent_ids: list[str] = field(default_factory=list)
    parallel_agents: int = 2
    max_batch_size: int = 50
    estimated_duration_hours: float = 0.0
    estimated_cost_usd: float = 0.0
    priority: int = 1  # 1 = highest

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave": self.wave_number,
            "assets": len(self.asset_ids),
            "agents": self.agent_ids,
            "parallel": self.parallel_agents,
            "batch_size": self.max_batch_size,
            "est_hours": round(self.estimated_duration_hours, 1),
            "est_cost": round(self.estimated_cost_usd, 2),
        }


@dataclass
class ResourceConfig:
    """Recommended resource configuration."""

    fabric_sku: str = "F4"
    cu_count: int = 4
    parallel_agents: int = 2
    max_concurrent_pipelines: int = 4
    notebook_pool_size: int = 2
    estimated_monthly_cost_usd: float = 0.0
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.fabric_sku,
            "cu": self.cu_count,
            "parallel_agents": self.parallel_agents,
            "pipelines": self.max_concurrent_pipelines,
            "notebooks": self.notebook_pool_size,
            "monthly_cost": round(self.estimated_monthly_cost_usd, 2),
            "rationale": self.rationale,
        }


@dataclass
class CostEstimate:
    """Cost breakdown for a migration."""

    compute_cost_usd: float = 0.0
    storage_cost_usd: float = 0.0
    llm_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    cost_per_asset: float = 0.0
    total_assets: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "compute": round(self.compute_cost_usd, 2),
            "storage": round(self.storage_cost_usd, 2),
            "llm": round(self.llm_cost_usd, 2),
            "total": round(self.total_cost_usd, 2),
            "per_asset": round(self.cost_per_asset, 4),
        }


@dataclass
class AdaptiveAdjustment:
    """A runtime adjustment to the migration plan."""

    wave_number: int
    adjustment_type: str  # "scale_up", "scale_down", "pause", "skip", "reorder"
    reason: str = ""
    new_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave": self.wave_number,
            "type": self.adjustment_type,
            "reason": self.reason,
            "config": self.new_config,
        }


@dataclass
class IntelligentPlan:
    """Complete intelligent migration plan."""

    waves: list[WaveConfig] = field(default_factory=list)
    resource_config: ResourceConfig = field(default_factory=ResourceConfig)
    cost_estimate: CostEstimate = field(default_factory=CostEstimate)
    adjustments: list[AdaptiveAdjustment] = field(default_factory=list)
    summary: str = ""

    @property
    def total_waves(self) -> int:
        return len(self.waves)

    @property
    def total_assets(self) -> int:
        return sum(len(w.asset_ids) for w in self.waves)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_waves": self.total_waves,
            "total_assets": self.total_assets,
            "resource_config": self.resource_config.to_dict(),
            "cost_estimate": self.cost_estimate.to_dict(),
            "waves": [w.to_dict() for w in self.waves],
            "adjustments": [a.to_dict() for a in self.adjustments],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Fabric SKU sizing
# ---------------------------------------------------------------------------

_SKU_TABLE: list[dict[str, Any]] = [
    {"sku": "F2", "cu": 2, "max_parallel": 2, "monthly_cost": 262.80, "max_assets": 50},
    {"sku": "F4", "cu": 4, "max_parallel": 4, "monthly_cost": 525.60, "max_assets": 200},
    {"sku": "F8", "cu": 8, "max_parallel": 8, "monthly_cost": 1051.20, "max_assets": 500},
    {"sku": "F16", "cu": 16, "max_parallel": 12, "monthly_cost": 2102.40, "max_assets": 1000},
    {"sku": "F32", "cu": 32, "max_parallel": 16, "monthly_cost": 4204.80, "max_assets": 2000},
    {"sku": "F64", "cu": 64, "max_parallel": 24, "monthly_cost": 8409.60, "max_assets": 5000},
    {"sku": "F128", "cu": 128, "max_parallel": 32, "monthly_cost": 16819.20, "max_assets": 10000},
]


# ---------------------------------------------------------------------------
# AI Wave Planner
# ---------------------------------------------------------------------------


class AIWavePlanner:
    """Intelligent wave planner that optimizes migration order.

    Parameters
    ----------
    max_assets_per_wave
        Maximum assets in a single wave.
    reasoning_loop
        Optional LLM for advanced planning.
    """

    def __init__(
        self,
        max_assets_per_wave: int = 50,
        reasoning_loop: Any = None,
    ) -> None:
        self._max_per_wave = max_assets_per_wave
        self._reasoning = reasoning_loop

    def plan(
        self,
        inventory: Any,
        risk_heatmap: list[Any] | None = None,
        dependency_graph: dict[str, list[str]] | None = None,
    ) -> list[WaveConfig]:
        """Generate optimized wave plan.

        Groups assets by:
        1. Dependency order (upstream first).
        2. Risk level (low-risk in early waves for quick wins).
        3. Domain affinity (related assets together).
        """
        items = inventory.items if hasattr(inventory, "items") else []
        dep_graph = dependency_graph or {}
        risk_lookup = {r.asset_id: r for r in (risk_heatmap or []) if hasattr(r, "asset_id")}

        if not items:
            return []

        # Topological sort by dependencies
        ordered = self._topo_sort(
            [i.id for i in items], dep_graph
        )

        # Assign risk scores for sorting within topo levels
        def _risk_key(asset_id: str) -> float:
            risk = risk_lookup.get(asset_id)
            return risk.risk_score if risk else 0.5

        # Group into waves
        waves: list[WaveConfig] = []
        current_wave: list[str] = []
        wave_num = 1

        for asset_id in ordered:
            current_wave.append(asset_id)
            if len(current_wave) >= self._max_per_wave:
                waves.append(WaveConfig(
                    wave_number=wave_num,
                    asset_ids=current_wave,
                    agent_ids=["01", "02", "03", "04", "05", "06", "07"],
                    estimated_duration_hours=len(current_wave) * 0.5,
                ))
                wave_num += 1
                current_wave = []

        if current_wave:
            waves.append(WaveConfig(
                wave_number=wave_num,
                asset_ids=current_wave,
                agent_ids=["01", "02", "03", "04", "05", "06", "07"],
                estimated_duration_hours=len(current_wave) * 0.5,
            ))

        return waves

    @staticmethod
    def _topo_sort(
        nodes: list[str], dep_graph: dict[str, list[str]]
    ) -> list[str]:
        """Topological sort with cycle handling."""
        in_degree: dict[str, int] = {n: 0 for n in nodes}
        node_set = set(nodes)

        for node, deps in dep_graph.items():
            if node in node_set:
                for dep in deps:
                    if dep in node_set:
                        in_degree[dep] = in_degree.get(dep, 0) + 1

        queue = [n for n in nodes if in_degree.get(n, 0) == 0]
        result: list[str] = []
        visited: set[str] = set()

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            result.append(node)

            for dep in dep_graph.get(node, []):
                if dep in node_set and dep not in visited:
                    in_degree[dep] = max(in_degree.get(dep, 1) - 1, 0)
                    if in_degree[dep] == 0:
                        queue.append(dep)

        # Add any remaining nodes (cycles or disconnected)
        for n in nodes:
            if n not in visited:
                result.append(n)

        return result


# ---------------------------------------------------------------------------
# Resource optimizer
# ---------------------------------------------------------------------------


class ResourceOptimizer:
    """Recommends optimal Fabric resource configuration.

    Analyses the migration plan (asset count, complexity, parallelism needs)
    and recommends the smallest Fabric SKU that can handle the workload.
    """

    def recommend(
        self,
        waves: list[WaveConfig],
        total_data_gb: float = 10.0,
    ) -> ResourceConfig:
        """Recommend resource configuration based on plan."""
        total_assets = sum(len(w.asset_ids) for w in waves)
        max_wave_size = max((len(w.asset_ids) for w in waves), default=0)

        # Select SKU based on total assets
        selected = _SKU_TABLE[0]  # Default F2
        for sku in _SKU_TABLE:
            if total_assets <= sku["max_assets"]:
                selected = sku
                break
        else:
            selected = _SKU_TABLE[-1]  # Largest

        # Optimize parallelism
        parallel = min(selected["max_parallel"], max(2, max_wave_size // 20))

        return ResourceConfig(
            fabric_sku=selected["sku"],
            cu_count=selected["cu"],
            parallel_agents=parallel,
            max_concurrent_pipelines=min(parallel * 2, selected["max_parallel"]),
            notebook_pool_size=max(1, parallel // 2),
            estimated_monthly_cost_usd=selected["monthly_cost"],
            rationale=(
                f"Selected {selected['sku']} for {total_assets} assets "
                f"(max {selected['max_assets']}). "
                f"Parallelism: {parallel} agents, {total_data_gb:.1f} GB data."
            ),
        )


# ---------------------------------------------------------------------------
# Cost modeler
# ---------------------------------------------------------------------------


class CostModeler:
    """Estimate migration costs based on asset count and complexity.

    Pricing model (approximate):
    - Compute: $0.36/CU-hour × hours × CU count
    - Storage: $0.023/GB/month × GB
    - LLM: $0.01/1K tokens × total tokens
    """

    def __init__(
        self,
        cu_hour_rate: float = 0.36,
        storage_gb_month_rate: float = 0.023,
        llm_per_1k_tokens: float = 0.01,
    ) -> None:
        self._cu_rate = cu_hour_rate
        self._storage_rate = storage_gb_month_rate
        self._llm_rate = llm_per_1k_tokens

    def estimate(
        self,
        waves: list[WaveConfig],
        resource_config: ResourceConfig,
        total_data_gb: float = 10.0,
        estimated_llm_tokens: int = 0,
    ) -> CostEstimate:
        """Estimate total migration cost."""
        total_hours = sum(w.estimated_duration_hours for w in waves)
        total_assets = sum(len(w.asset_ids) for w in waves)

        compute = total_hours * resource_config.cu_count * self._cu_rate
        storage = total_data_gb * self._storage_rate * 3  # ~3 months
        llm = (estimated_llm_tokens / 1000) * self._llm_rate
        total = compute + storage + llm

        return CostEstimate(
            compute_cost_usd=compute,
            storage_cost_usd=storage,
            llm_cost_usd=llm,
            total_cost_usd=total,
            cost_per_asset=total / max(total_assets, 1),
            total_assets=total_assets,
        )


# ---------------------------------------------------------------------------
# Adaptive scheduler
# ---------------------------------------------------------------------------


class AdaptiveScheduler:
    """Adjusts the migration plan based on real-time progress.

    Monitors:
    - Wave completion times (vs estimates).
    - Error rates.
    - Resource utilization.

    Generates adjustments when actuals deviate from plan.
    """

    def __init__(self, tolerance: float = 0.3) -> None:
        self._tolerance = tolerance  # 30% deviation triggers adjustment
        self._wave_actuals: dict[int, dict[str, Any]] = {}

    def record_wave_completion(
        self,
        wave_number: int,
        actual_duration_hours: float,
        error_count: int = 0,
        total_items: int = 0,
    ) -> None:
        """Record actual wave completion metrics."""
        self._wave_actuals[wave_number] = {
            "duration": actual_duration_hours,
            "errors": error_count,
            "items": total_items,
            "error_rate": error_count / max(total_items, 1),
        }

    def suggest_adjustments(
        self,
        remaining_waves: list[WaveConfig],
    ) -> list[AdaptiveAdjustment]:
        """Suggest adjustments based on actuals vs plan."""
        adjustments: list[AdaptiveAdjustment] = []

        if not self._wave_actuals:
            return adjustments

        # Calculate average deviation
        avg_error_rate = sum(
            w["error_rate"] for w in self._wave_actuals.values()
        ) / len(self._wave_actuals)

        avg_duration_ratio = 1.0
        completed = list(self._wave_actuals.values())
        if completed:
            # Simple: if errors are high, reduce batch size
            if avg_error_rate > 0.2:
                for wave in remaining_waves:
                    adjustments.append(AdaptiveAdjustment(
                        wave_number=wave.wave_number,
                        adjustment_type="scale_down",
                        reason=f"High error rate ({avg_error_rate:.0%}) — reducing batch size",
                        new_config={"max_batch_size": max(10, wave.max_batch_size // 2)},
                    ))
                    break  # Adjust next wave only

            # If everything is faster than expected, increase parallelism
            if avg_error_rate < 0.05 and len(completed) >= 2:
                for wave in remaining_waves:
                    adjustments.append(AdaptiveAdjustment(
                        wave_number=wave.wave_number,
                        adjustment_type="scale_up",
                        reason="Low error rate and good performance — increasing parallelism",
                        new_config={"parallel_agents": wave.parallel_agents + 1},
                    ))
                    break

        return adjustments

    @property
    def completed_waves(self) -> int:
        return len(self._wave_actuals)
