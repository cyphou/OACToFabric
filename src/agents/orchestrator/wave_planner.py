"""Wave planner — partition inventory items into migration waves.

A *wave* is a group of assets migrated and validated together.  Waves
are ordered by dependency depth and complexity so that foundational
tables land first and downstream reports follow.

Heuristics
----------
1. **Base tables** (no dependencies) → Wave 1.
2. **Derived tables / ETL** → Wave 2.
3. **Semantic models** that reference only Wave-1 tables → Wave 2.
4. **Reports / dashboards** → Wave 3+.
5. **Security** → Same wave as the semantic model it protects.
6. Items are capped per wave to limit blast radius (default 50).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.core.models import AssetType, Inventory, InventoryItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MigrationWave:
    """A planned migration wave."""

    id: int
    name: str
    items: list[InventoryItem] = field(default_factory=list)
    agent_ids: list[str] = field(default_factory=list)
    estimated_duration_minutes: int = 0

    @property
    def count(self) -> int:
        return len(self.items)

    def add(self, item: InventoryItem) -> None:
        self.items.append(item)


@dataclass
class WavePlan:
    """Full wave plan for a migration."""

    waves: list[MigrationWave] = field(default_factory=list)
    unassigned: list[InventoryItem] = field(default_factory=list)

    @property
    def total_items(self) -> int:
        return sum(w.count for w in self.waves) + len(self.unassigned)

    @property
    def wave_count(self) -> int:
        return len(self.waves)


# ---------------------------------------------------------------------------
# Wave assignment heuristics
# ---------------------------------------------------------------------------

_TYPE_WAVE_PRIORITY: dict[AssetType, int] = {
    AssetType.CONNECTION: 1,
    AssetType.PHYSICAL_TABLE: 1,
    AssetType.LOGICAL_TABLE: 1,
    AssetType.SUBJECT_AREA: 1,
    AssetType.DATA_FLOW: 2,
    AssetType.DATA_MODEL: 2,
    AssetType.PRESENTATION_TABLE: 2,
    AssetType.ANALYSIS: 3,
    AssetType.DASHBOARD: 3,
    AssetType.PROMPT: 3,
    AssetType.FILTER: 3,
    AssetType.AGENT_ALERT: 3,
    AssetType.SECURITY_ROLE: 2,
    AssetType.INIT_BLOCK: 2,
}

_WAVE_AGENT_MAP: dict[int, list[str]] = {
    1: ["01-discovery", "02-schema"],
    2: ["03-etl", "04-semantic", "06-security"],
    3: ["05-reports", "07-validation"],
}


def plan_waves(
    inventory: Inventory,
    *,
    max_items_per_wave: int = 50,
) -> WavePlan:
    """Partition inventory items into ordered migration waves.

    Parameters
    ----------
    inventory : Inventory
        All discovered items.
    max_items_per_wave : int
        Maximum items in a single wave (limits blast radius).

    Returns
    -------
    WavePlan
    """
    # Bucket items by priority
    buckets: dict[int, list[InventoryItem]] = {}
    for item in inventory.items:
        priority = _TYPE_WAVE_PRIORITY.get(item.asset_type, 3)
        buckets.setdefault(priority, []).append(item)

    waves: list[MigrationWave] = []
    wave_counter = 0

    for priority in sorted(buckets.keys()):
        items = buckets[priority]
        # Sort by complexity (lowest first) for predictable ordering
        items.sort(key=lambda i: i.complexity_score)

        # Split into sub-waves if exceeding max
        for chunk_start in range(0, len(items), max_items_per_wave):
            chunk = items[chunk_start : chunk_start + max_items_per_wave]
            wave_counter += 1
            wave = MigrationWave(
                id=wave_counter,
                name=f"Wave {wave_counter}",
                items=chunk,
                agent_ids=list(_WAVE_AGENT_MAP.get(priority, [])),
                estimated_duration_minutes=_estimate_duration(chunk),
            )
            waves.append(wave)

    plan = WavePlan(waves=waves)
    logger.info(
        "Wave plan: %d waves, %d total items",
        plan.wave_count,
        plan.total_items,
    )
    return plan


def _estimate_duration(items: list[InventoryItem]) -> int:
    """Estimate wave duration in minutes based on item count + complexity."""
    if not items:
        return 0
    base = len(items) * 2  # 2 min per item baseline
    complexity_bonus = sum(i.complexity_score for i in items) * 0.5
    return max(5, int(base + complexity_bonus))


# ---------------------------------------------------------------------------
# Summary rendering
# ---------------------------------------------------------------------------


def render_wave_plan(plan: WavePlan) -> str:
    """Render the wave plan as a Markdown document."""
    lines = [
        "# Migration Wave Plan",
        "",
        f"- **Total items:** {plan.total_items}",
        f"- **Waves:** {plan.wave_count}",
        "",
        "## Wave Summary",
        "",
        "| Wave | Items | Agents | Est. Duration |",
        "|---|---|---|---|",
    ]

    for w in plan.waves:
        agents = ", ".join(w.agent_ids) if w.agent_ids else "—"
        lines.append(
            f"| {w.name} | {w.count} | {agents} | {w.estimated_duration_minutes} min |"
        )

    lines.append("")

    # Detail per wave
    for w in plan.waves:
        lines.extend([
            f"## {w.name}",
            "",
            "| Asset | Type | Complexity | Path |",
            "|---|---|---|---|",
        ])
        for item in w.items:
            lines.append(
                f"| {item.name} | {item.asset_type.value} | "
                f"{item.complexity_category.value} | {item.source_path} |"
            )
        lines.append("")

    if plan.unassigned:
        lines.extend([
            "## Unassigned Items",
            "",
            "| Asset | Type | Path |",
            "|---|---|---|",
        ])
        for item in plan.unassigned:
            lines.append(
                f"| {item.name} | {item.asset_type.value} | {item.source_path} |"
            )
        lines.append("")

    return "\n".join(lines)
