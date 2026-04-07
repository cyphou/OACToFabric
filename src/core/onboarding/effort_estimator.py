"""Effort Estimator — estimate migration effort based on inventory profile.

Uses a weighted model based on asset counts, complexity distribution,
and data volume to produce hours/days/cost estimates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Effort multipliers (hours per asset by complexity)
# ---------------------------------------------------------------------------

_EFFORT_PER_ASSET: dict[str, dict[str, float]] = {
    "analysis": {"Low": 0.5, "Medium": 2.0, "High": 6.0},
    "dashboard": {"Low": 0.5, "Medium": 2.0, "High": 5.0},
    "dataModel": {"Low": 1.0, "Medium": 4.0, "High": 12.0},
    "subjectArea": {"Low": 0.5, "Medium": 2.0, "High": 8.0},
    "dataflow": {"Low": 1.0, "Medium": 3.0, "High": 10.0},
    "securityRole": {"Low": 0.25, "Medium": 1.0, "High": 3.0},
    "physicalTable": {"Low": 0.25, "Medium": 0.5, "High": 2.0},
    "connection": {"Low": 0.25, "Medium": 0.5, "High": 1.0},
}

_DEFAULT_EFFORT: dict[str, float] = {"Low": 0.5, "Medium": 2.0, "High": 6.0}

_OVERHEAD_PCT = 0.20  # 20% overhead for testing, remediation, coordination


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class AssetBreakdown:
    """Effort breakdown for one asset type."""

    asset_type: str
    count: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    estimated_hours: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_type": self.asset_type,
            "count": self.count,
            "low": self.low,
            "medium": self.medium,
            "high": self.high,
            "estimated_hours": round(self.estimated_hours, 1),
        }


@dataclass
class EffortEstimate:
    """Full effort estimate for the migration."""

    total_assets: int = 0
    total_hours: float = 0.0
    overhead_hours: float = 0.0
    grand_total_hours: float = 0.0
    estimated_days: float = 0.0
    estimated_weeks: float = 0.0
    team_size: int = 2
    hours_per_day: float = 6.0
    breakdowns: list[AssetBreakdown] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_assets": self.total_assets,
            "total_hours": round(self.total_hours, 1),
            "overhead_hours": round(self.overhead_hours, 1),
            "grand_total_hours": round(self.grand_total_hours, 1),
            "estimated_days": round(self.estimated_days, 1),
            "estimated_weeks": round(self.estimated_weeks, 1),
            "team_size": self.team_size,
            "hours_per_day": self.hours_per_day,
            "breakdowns": [b.to_dict() for b in self.breakdowns],
            "risk_notes": self.risk_notes,
        }

    def summary(self) -> str:
        lines = [
            f"Effort Estimate: {self.total_assets} assets",
            f"  Base hours:     {self.total_hours:.0f}h",
            f"  Overhead (20%): {self.overhead_hours:.0f}h",
            f"  Grand total:    {self.grand_total_hours:.0f}h",
            f"  Calendar:       ~{self.estimated_weeks:.1f} weeks ({self.team_size} people × {self.hours_per_day:.0f}h/day)",
        ]
        if self.breakdowns:
            lines.append("  Breakdown:")
            for b in self.breakdowns:
                lines.append(f"    {b.asset_type}: {b.count} assets → {b.estimated_hours:.0f}h")
        if self.risk_notes:
            lines.append("  Risks:")
            for note in self.risk_notes:
                lines.append(f"    ⚠ {note}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Estimator
# ---------------------------------------------------------------------------


class EffortEstimator:
    """Estimate migration effort from an inventory profile.

    Parameters
    ----------
    team_size
        Number of team members available.
    hours_per_day
        Effective working hours per person per day.
    overhead_pct
        Overhead percentage for testing / coordination.
    """

    def __init__(
        self,
        team_size: int = 2,
        hours_per_day: float = 6.0,
        overhead_pct: float = _OVERHEAD_PCT,
    ) -> None:
        self.team_size = team_size
        self.hours_per_day = hours_per_day
        self.overhead_pct = overhead_pct

    def estimate(self, inventory_profile: list[dict[str, Any]]) -> EffortEstimate:
        """Estimate effort from a list of asset dicts.

        Each dict should have ``asset_type``, ``complexity`` (Low/Medium/High).
        """
        # Group by asset_type
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in inventory_profile:
            at = item.get("asset_type", "unknown")
            groups.setdefault(at, []).append(item)

        breakdowns: list[AssetBreakdown] = []
        total_hours = 0.0
        total_assets = 0
        risk_notes: list[str] = []

        for asset_type, items in sorted(groups.items()):
            multipliers = _EFFORT_PER_ASSET.get(asset_type, _DEFAULT_EFFORT)
            low = medium = high = 0
            hours = 0.0
            for item in items:
                complexity = item.get("complexity", "Medium")
                effort = multipliers.get(complexity, multipliers.get("Medium", 2.0))
                hours += effort
                if complexity == "Low":
                    low += 1
                elif complexity == "High":
                    high += 1
                else:
                    medium += 1

            bd = AssetBreakdown(
                asset_type=asset_type,
                count=len(items),
                low=low,
                medium=medium,
                high=high,
                estimated_hours=hours,
            )
            breakdowns.append(bd)
            total_hours += hours
            total_assets += len(items)

            if high > len(items) * 0.5:
                risk_notes.append(f"{asset_type}: >50% high-complexity assets")

        overhead_hours = total_hours * self.overhead_pct
        grand_total = total_hours + overhead_hours
        capacity = self.team_size * self.hours_per_day
        days = grand_total / capacity if capacity > 0 else 0
        weeks = days / 5

        return EffortEstimate(
            total_assets=total_assets,
            total_hours=total_hours,
            overhead_hours=overhead_hours,
            grand_total_hours=grand_total,
            estimated_days=days,
            estimated_weeks=weeks,
            team_size=self.team_size,
            hours_per_day=self.hours_per_day,
            breakdowns=breakdowns,
            risk_notes=risk_notes,
        )
