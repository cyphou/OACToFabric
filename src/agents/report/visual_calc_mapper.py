"""Visual Calc Mapper — OAC visual-level calculations → PBI visual calculations.

Converts OAC analysis-level computed fields and visual-specific calculations
to Power BI visual calculations (a feature that allows DAX expressions
scoped to a single visual without polluting the semantic model).

Also handles migration to modern Fluent 2 visual defaults.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Visual calculation types
# ---------------------------------------------------------------------------


@dataclass
class OACVisualCalc:
    """An OAC visual-level calculation."""

    name: str
    expression: str            # OAC expression syntax
    visual_id: str = ""
    data_type: str = "number"
    format_string: str = ""


@dataclass
class PBIVisualCalc:
    """A Power BI visual calculation."""

    name: str
    expression: str            # DAX expression
    visual_id: str = ""
    data_type: str = "Double"
    format_string: str = ""
    confidence: float = 1.0
    warning: str = ""

    def to_visual_json(self) -> dict[str, Any]:
        """Generate PBIR visual calculation JSON."""
        return {
            "name": self.name,
            "expression": self.expression,
            "dataType": self.data_type,
            "formatString": self.format_string,
        }


@dataclass
class VisualCalcResult:
    """Result of visual calculation mapping."""

    calculations: list[PBIVisualCalc] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def high_confidence_count(self) -> int:
        return sum(1 for c in self.calculations if c.confidence >= 0.9)


# ---------------------------------------------------------------------------
# OAC expression → DAX conversion (visual-level subset)
# ---------------------------------------------------------------------------

_VISUAL_CALC_PATTERNS: list[tuple[str, str, float]] = [
    # Running totals
    (r"RSUM\((.+?)\)", r"RUNNINGSUM(\1)", 0.95),
    (r"RUNNING_SUM\((.+?)\)", r"RUNNINGSUM(\1)", 0.95),
    # Running averages
    (r"RAVG\((.+?)\)", r"MOVINGAVERAGE(\1, ROWS, UNBOUNDED, 0)", 0.85),
    (r"RUNNING_AVG\((.+?)\)", r"MOVINGAVERAGE(\1, ROWS, UNBOUNDED, 0)", 0.85),
    # Running count
    (r"RCOUNT\((.+?)\)", r"RUNNINGSUM(1)", 0.90),
    # Rank
    (r"RANK\((.+?)\)", r"RANK(DENSE, \1)", 0.90),
    (r"DENSE_RANK\((.+?)\)", r"RANK(DENSE, \1)", 0.95),
    # Percent of total
    (r"PCT_OF_TOTAL\((.+?)\)", r"DIVIDE(\1, COLLAPSE(\1, ROWS))", 0.85),
    (r"PERCENT_OF_TOTAL\((.+?)\)", r"DIVIDE(\1, COLLAPSE(\1, ROWS))", 0.85),
    # Moving average
    (r"MAVG\((.+?),\s*(\d+)\)", r"MOVINGAVERAGE(\1, ROWS, \2, 0)", 0.90),
    # Period over period
    (r"AGO\((.+?),\s*(\d+)\)", r"PREVIOUS(\1, \2)", 0.80),
]

_DATA_TYPE_MAP: dict[str, str] = {
    "number": "Double",
    "integer": "Int64",
    "string": "String",
    "date": "DateTime",
    "boolean": "Boolean",
    "decimal": "Decimal",
    "float": "Double",
    "varchar": "String",
}


def _convert_visual_expression(oac_expr: str) -> tuple[str, float]:
    """Convert OAC visual expression to DAX."""
    for pattern, replacement, confidence in _VISUAL_CALC_PATTERNS:
        m = re.search(pattern, oac_expr, re.IGNORECASE)
        if m:
            result = re.sub(pattern, replacement, oac_expr, flags=re.IGNORECASE)
            return result, confidence

    # Fallback: pass through with low confidence
    return oac_expr, 0.5


# ---------------------------------------------------------------------------
# Visual calculation mapping
# ---------------------------------------------------------------------------


def map_visual_calc(calc: OACVisualCalc) -> PBIVisualCalc:
    """Map a single OAC visual calculation to PBI.

    Parameters
    ----------
    calc : OACVisualCalc
        OAC visual calculation.

    Returns
    -------
    PBIVisualCalc
        Mapped PBI visual calculation.
    """
    dax_expr, confidence = _convert_visual_expression(calc.expression)
    data_type = _DATA_TYPE_MAP.get(calc.data_type.lower(), "Double")

    warning = ""
    if confidence < 0.8:
        warning = f"Low confidence ({confidence:.0%}) translation for '{calc.name}'"

    return PBIVisualCalc(
        name=calc.name,
        expression=dax_expr,
        visual_id=calc.visual_id,
        data_type=data_type,
        format_string=calc.format_string,
        confidence=confidence,
        warning=warning,
    )


def map_all_visual_calcs(calcs: list[OACVisualCalc]) -> VisualCalcResult:
    """Map all OAC visual calculations to PBI.

    Parameters
    ----------
    calcs : list[OACVisualCalc]
        OAC visual calculations.

    Returns
    -------
    VisualCalcResult
        All mapped visual calculations.
    """
    result = VisualCalcResult()

    for calc in calcs:
        pbi_calc = map_visual_calc(calc)
        result.calculations.append(pbi_calc)
        if pbi_calc.warning:
            result.warnings.append(pbi_calc.warning)

    logger.info(
        "Mapped %d visual calculations: %d high-confidence (%.0f%%)",
        len(result.calculations),
        result.high_confidence_count,
        (result.high_confidence_count / len(calcs) * 100) if calcs else 0,
    )
    return result


# ---------------------------------------------------------------------------
# Fluent 2 modern theme defaults
# ---------------------------------------------------------------------------


def generate_fluent2_theme() -> dict[str, Any]:
    """Generate a Fluent 2 visual defaults theme config.

    Returns
    -------
    dict[str, Any]
        PBIR-compatible theme configuration with Fluent 2 defaults.
    """
    return {
        "name": "Fluent2Modern",
        "type": "Advanced",
        "dataColors": [
            "#4C78A8", "#F58518", "#E45756", "#72B7B2",
            "#54A24B", "#EECA3B", "#B279A2", "#FF9DA6",
            "#9D755D", "#BAB0AC",
        ],
        "background": "#FFFFFF",
        "foreground": "#252525",
        "tableAccent": "#4C78A8",
        "visualStyles": {
            "*": {
                "*": {
                    "general": [{
                        "responsive": True,
                        "keepLayerOrder": True,
                    }],
                    "border": [{
                        "show": False,
                        "radius": 8,
                    }],
                    "shadow": [{
                        "show": True,
                        "preset": "bottomRight",
                        "color": {"solid": {"color": "#00000010"}},
                    }],
                    "padding": [{
                        "top": 8,
                        "bottom": 8,
                        "left": 12,
                        "right": 12,
                    }],
                    "title": [{
                        "fontFamily": "Segoe UI Semibold",
                        "fontSize": 12,
                        "fontColor": {"solid": {"color": "#252525"}},
                    }],
                }
            }
        },
        "textClasses": {
            "title": {
                "fontFamily": "Segoe UI Semibold",
                "fontSize": 14,
                "color": "#252525",
            },
            "label": {
                "fontFamily": "Segoe UI",
                "fontSize": 11,
                "color": "#605E5C",
            },
            "callout": {
                "fontFamily": "Segoe UI Semibold",
                "fontSize": 18,
                "color": "#252525",
            },
        },
    }
