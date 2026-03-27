"""OAC KPI/Scorecard → Power BI Goals/Scorecard JSON generator.

Converts OAC KPI definitions into PBI Goals/Scorecard JSON format
for import into the Power BI Goals feature.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class OACKpi:
    """Parsed OAC KPI definition."""

    id: str
    name: str
    description: str = ""
    actual_expression: str = ""
    target_expression: str = ""
    target_value: float | None = None
    status_thresholds: dict = field(default_factory=dict)
    owner: str = ""
    trend_direction: str = "up"  # "up" = higher is better
    format_string: str = "#,##0"
    unit: str = ""
    time_dimension: str = ""


@dataclass
class PBIGoal:
    """Power BI Goal definition."""

    name: str
    description: str = ""
    current_value: float | None = None
    target_value: float | None = None
    start_date: str = ""
    due_date: str = ""
    owner: str = ""
    status: str = "notStarted"  # notStarted, onTrack, atRisk, behind
    notes: list[str] = field(default_factory=list)
    connected_measure: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class PBIScorecard:
    """Power BI Scorecard containing goals."""

    name: str
    description: str = ""
    goals: list[PBIGoal] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to PBI Scorecard JSON."""
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> dict:
        goals_list = []
        for g in self.goals:
            goal_dict = {
                "name": g.name,
                "description": g.description,
                "owner": g.owner,
                "status": g.status,
                "notes": g.notes,
            }
            if g.current_value is not None:
                goal_dict["currentValue"] = g.current_value
            if g.target_value is not None:
                goal_dict["targetValue"] = g.target_value
            if g.start_date:
                goal_dict["startDate"] = g.start_date
            if g.due_date:
                goal_dict["dueDate"] = g.due_date
            if g.connected_measure:
                goal_dict["connectedMeasure"] = g.connected_measure
            goals_list.append(goal_dict)

        return {
            "name": self.name,
            "description": self.description,
            "goals": goals_list,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

    @property
    def count(self) -> int:
        return len(self.goals)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_oac_kpi(kpi_meta: dict) -> OACKpi:
    """Parse a single OAC KPI definition.

    Args:
        kpi_meta: Dict from OAC catalog/RPD KPI definition.

    Returns:
        Parsed OACKpi instance.
    """
    return OACKpi(
        id=str(kpi_meta.get("id", kpi_meta.get("name", ""))),
        name=kpi_meta.get("name", kpi_meta.get("title", "Unknown KPI")),
        description=kpi_meta.get("description", ""),
        actual_expression=kpi_meta.get("actualExpression", kpi_meta.get("actual", "")),
        target_expression=kpi_meta.get("targetExpression", kpi_meta.get("target", "")),
        target_value=kpi_meta.get("targetValue"),
        status_thresholds=kpi_meta.get("thresholds", {}),
        owner=kpi_meta.get("owner", ""),
        trend_direction=kpi_meta.get("trendDirection", "up"),
        format_string=kpi_meta.get("formatString", "#,##0"),
        unit=kpi_meta.get("unit", ""),
        time_dimension=kpi_meta.get("timeDimension", ""),
    )


def _map_status(thresholds: dict, trend: str = "up") -> str:
    """Map OAC status thresholds to PBI goal status."""
    if not thresholds:
        return "notStarted"
    # If we have percentage thresholds, translate to PBI status
    critical = thresholds.get("critical", thresholds.get("red"))
    warning = thresholds.get("warning", thresholds.get("yellow"))
    if critical is not None or warning is not None:
        return "onTrack"  # Default to onTrack; actual status is computed at runtime
    return "notStarted"


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def convert_kpi_to_goal(kpi: OACKpi) -> PBIGoal:
    """Convert a single OAC KPI to a PBI Goal.

    Args:
        kpi: Parsed OAC KPI

    Returns:
        PBI Goal definition
    """
    goal = PBIGoal(
        name=kpi.name,
        description=kpi.description or f"Migrated from OAC KPI: {kpi.id}",
        target_value=kpi.target_value,
        owner=kpi.owner,
        status=_map_status(kpi.status_thresholds, kpi.trend_direction),
    )

    # Connect to measure if actual expression looks like a measure reference
    if kpi.actual_expression:
        expr = kpi.actual_expression.strip()
        if expr.startswith("[") and expr.endswith("]"):
            goal.connected_measure = expr[1:-1]
        else:
            goal.notes.append(f"OAC actual expression: {expr}")

    if kpi.target_expression:
        goal.notes.append(f"OAC target expression: {kpi.target_expression}")

    if kpi.unit:
        goal.notes.append(f"Unit: {kpi.unit}")

    if kpi.format_string and kpi.format_string != "#,##0":
        goal.notes.append(f"Format: {kpi.format_string}")

    if kpi.status_thresholds:
        goal.notes.append(
            f"Thresholds: {json.dumps(kpi.status_thresholds)}"
        )
        goal.warnings.append(
            "OAC threshold-based status coloring requires manual "
            "configuration in PBI Goals"
        )

    return goal


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def generate_scorecard(
    kpi_list: list[dict],
    scorecard_name: str = "Migrated Scorecard",
    description: str = "",
) -> PBIScorecard:
    """Generate a PBI Scorecard from a list of OAC KPI definitions.

    Args:
        kpi_list: List of OAC KPI metadata dicts
        scorecard_name: Name for the generated scorecard
        description: Scorecard description

    Returns:
        PBIScorecard with converted goals
    """
    scorecard = PBIScorecard(
        name=scorecard_name,
        description=description or f"Migrated from {len(kpi_list)} OAC KPIs",
    )

    for kpi_meta in kpi_list:
        kpi = parse_oac_kpi(kpi_meta)
        goal = convert_kpi_to_goal(kpi)
        scorecard.goals.append(goal)
        if goal.warnings:
            scorecard.warnings.extend(goal.warnings)

    logger.info(
        "Generated scorecard '%s' with %d goals",
        scorecard.name, scorecard.count,
    )
    return scorecard
