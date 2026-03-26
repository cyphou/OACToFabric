"""Visual fallback cascade — 3-tier degradation for unmappable visuals.

Ported from T2P — when a complex visual type cannot be faithfully
represented, degrade through a cascade of simpler alternatives:
  Tier 1: Map to closest simpler PBI visual
  Tier 2: Fall back to basic chart (clusteredBarChart)
  Tier 3: Fall back to table (tableEx) or card

Also includes the approximation map documenting why each fallback was
chosen and what the user should verify.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .visual_mapper import PBIVisualType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 3-tier fallback cascade
# ---------------------------------------------------------------------------

_FALLBACK_CASCADE: dict[str, list[PBIVisualType]] = {
    # Tier 1: closest simpler visual → Tier 2: basic chart → Tier 3: table/card
    "scatter":              [PBIVisualType.SCATTER, PBIVisualType.TABLE_EX],
    "bubble":               [PBIVisualType.SCATTER, PBIVisualType.TABLE_EX],
    "boxAndWhisker":        [PBIVisualType.BOX_WHISKER, PBIVisualType.CLUSTERED_COLUMN, PBIVisualType.TABLE_EX],
    "histogram":            [PBIVisualType.HISTOGRAM, PBIVisualType.CLUSTERED_COLUMN, PBIVisualType.TABLE_EX],
    "sankey":               [PBIVisualType.SANKEY, PBIVisualType.STACKED_BAR, PBIVisualType.TABLE_EX],
    "chord":                [PBIVisualType.CHORD, PBIVisualType.MATRIX, PBIVisualType.TABLE_EX],
    "wordCloud":            [PBIVisualType.WORD_CLOUD, PBIVisualType.TABLE_EX],
    "networkDiagram":       [PBIVisualType.NETWORK_NAVIGATOR, PBIVisualType.TABLE_EX],
    "gantt":                [PBIVisualType.GANTT, PBIVisualType.TABLE_EX],
    "parallelCoordinates":  [PBIVisualType.LINE, PBIVisualType.TABLE_EX],
    "radarChart":           [PBIVisualType.RADAR, PBIVisualType.LINE, PBIVisualType.TABLE_EX],
    "sunburst":             [PBIVisualType.SUNBURST, PBIVisualType.TREEMAP, PBIVisualType.TABLE_EX],
    "gauge":                [PBIVisualType.GAUGE, PBIVisualType.CARD],
    "kpi":                  [PBIVisualType.CARD, PBIVisualType.MULTI_ROW_CARD],
    "trellis":              [PBIVisualType.CLUSTERED_COLUMN, PBIVisualType.TABLE_EX],
    "tagCloud":             [PBIVisualType.WORD_CLOUD, PBIVisualType.TABLE_EX],
    "mapview":              [PBIVisualType.MAP, PBIVisualType.FILLED_MAP, PBIVisualType.TABLE_EX],
    "heatmap":              [PBIVisualType.MATRIX, PBIVisualType.TABLE_EX],
    "combo":                [PBIVisualType.COMBO, PBIVisualType.CLUSTERED_BAR, PBIVisualType.TABLE_EX],
    # Ultimate fallback for anything unknown
    "__unknown__":          [PBIVisualType.TABLE_EX, PBIVisualType.CARD],
}


# ---------------------------------------------------------------------------
# Approximation map (documentation for each fallback)
# ---------------------------------------------------------------------------

_APPROXIMATION_MAP: dict[str, dict[str, str]] = {
    "boxAndWhisker": {
        "nearest": "BoxAndWhiskerByMAQSoftware custom visual",
        "fallback": "clusteredColumnChart",
        "notes": "Requires AppSource visual install. Without it, shows grouped column chart with min/max/median as separate series.",
    },
    "sankey": {
        "nearest": "ChicagoITSankey custom visual",
        "fallback": "stackedBarChart",
        "notes": "Requires AppSource visual. Fallback shows source/destination as stacked categories.",
    },
    "chord": {
        "nearest": "ChicagoITChord custom visual",
        "fallback": "matrix with conditional formatting",
        "notes": "Matrix can show same N×N relationship data as a heatmap.",
    },
    "histogram": {
        "nearest": "HistogramChart custom visual or binned column chart",
        "fallback": "clusteredColumnChart with calculated bins",
        "notes": "Create a bin column using GROUP BY + COUNTROWS for histogram effect.",
    },
    "networkDiagram": {
        "nearest": "NetworkNavigatorChart custom visual",
        "fallback": "tableEx",
        "notes": "No native PBI equivalent — table shows source→target edges.",
    },
    "gantt": {
        "nearest": "GanttByMAQSoftware custom visual",
        "fallback": "tableEx",
        "notes": "Table with conditional formatting (data bars) as timeline approximation.",
    },
    "parallelCoordinates": {
        "nearest": "line chart with series",
        "fallback": "lineChart",
        "notes": "Each dimension becomes a point on the X axis, each row a series.",
    },
    "sunburst": {
        "nearest": "Built-in sunburst (PBI native)",
        "fallback": "treemap",
        "notes": "Sunburst is natively supported in PBI. Treemap fallback if issues arise.",
    },
    "trellis": {
        "nearest": "Small multiples on clusteredColumnChart",
        "fallback": "clusteredColumnChart",
        "notes": "Enable Small Multiples feature in visual formatting. OAC trellis maps to this.",
    },
}


# ---------------------------------------------------------------------------
# Fallback resolution
# ---------------------------------------------------------------------------


@dataclass
class FallbackResult:
    """Result of visual fallback resolution."""

    original_type: str
    resolved_type: PBIVisualType
    tier: int               # 1 = exact custom visual, 2 = simpler native, 3 = table/card
    approximation_notes: str = ""
    warnings: list[str] | None = None


def resolve_visual_fallback(oac_type: str) -> FallbackResult:
    """Resolve an OAC visual type through the 3-tier fallback cascade.

    Returns the best available PBI visual type with approximation notes.
    """
    normalized = oac_type.strip().lower().replace(" ", "").replace("-", "").replace("_", "")

    # Check direct cascade
    cascade = _FALLBACK_CASCADE.get(normalized)
    if not cascade:
        # Try original type string
        cascade = _FALLBACK_CASCADE.get(oac_type, _FALLBACK_CASCADE["__unknown__"])

    resolved = cascade[0]
    tier = 1

    # Determine tier based on position in cascade
    if len(cascade) > 1 and resolved != cascade[0]:
        tier = 2
    if resolved in (PBIVisualType.TABLE_EX, PBIVisualType.CARD):
        tier = 3

    # Get approximation notes
    approx = _APPROXIMATION_MAP.get(normalized, _APPROXIMATION_MAP.get(oac_type, {}))
    notes = approx.get("notes", "")

    warnings = []
    if tier >= 2:
        warnings.append(f"Visual type '{oac_type}' degraded to tier {tier}: {resolved.value}")
    if tier == 3:
        warnings.append(f"No close PBI equivalent for '{oac_type}' — using {resolved.value}")

    return FallbackResult(
        original_type=oac_type,
        resolved_type=resolved,
        tier=tier,
        approximation_notes=notes,
        warnings=warnings,
    )
