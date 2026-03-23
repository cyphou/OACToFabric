"""Visual type mapper — OAC chart types → Power BI visual types.

Maps OAC analysis views / chart types to Power BI visual type identifiers
and generates the base visual configuration JSON structures.

Also handles:
  - OAC conditional formatting → PBI formatting rules
  - OAC sorting → PBI sort configuration
  - Number / date format string translation
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OACChartType(str, Enum):
    """Known OAC analysis chart / view types."""

    TABLE = "table"
    PIVOT_TABLE = "pivotTable"
    VERTICAL_BAR = "verticalBar"
    HORIZONTAL_BAR = "horizontalBar"
    STACKED_BAR = "stackedBar"
    STACKED_COLUMN = "stackedColumn"
    LINE = "line"
    AREA = "area"
    COMBO = "combo"
    PIE = "pie"
    DONUT = "donut"
    SCATTER = "scatter"
    BUBBLE = "bubble"
    FILLED_MAP = "filledMap"
    BUBBLE_MAP = "bubbleMap"
    GAUGE = "gauge"
    KPI = "kpi"
    FUNNEL = "funnel"
    TREEMAP = "treemap"
    HEATMAP = "heatmap"
    WATERFALL = "waterfall"
    NARRATIVE = "narrative"
    IMAGE = "image"
    TRELLIS = "trellis"
    UNKNOWN = "unknown"


class PBIVisualType(str, Enum):
    """Power BI visual type identifiers used in PBIR JSON."""

    TABLE_EX = "tableEx"
    MATRIX = "pivotTable"
    CLUSTERED_BAR = "clusteredBarChart"
    CLUSTERED_COLUMN = "clusteredColumnChart"
    STACKED_BAR = "stackedBarChart"
    STACKED_COLUMN = "stackedColumnChart"
    LINE = "lineChart"
    AREA = "areaChart"
    COMBO = "lineClusteredColumnComboChart"
    PIE = "pieChart"
    DONUT = "donutChart"
    SCATTER = "scatterChart"
    FILLED_MAP = "filledMap"
    MAP = "map"
    GAUGE = "gauge"
    CARD = "card"
    MULTI_ROW_CARD = "multiRowCard"
    FUNNEL = "funnel"
    TREEMAP = "treemap"
    WATERFALL = "waterfallChart"
    TEXTBOX = "textbox"
    IMAGE = "image"
    SLICER = "slicer"


# ---------------------------------------------------------------------------
# Mapping table
# ---------------------------------------------------------------------------

_OAC_TO_PBI: dict[OACChartType, PBIVisualType] = {
    OACChartType.TABLE: PBIVisualType.TABLE_EX,
    OACChartType.PIVOT_TABLE: PBIVisualType.MATRIX,
    OACChartType.VERTICAL_BAR: PBIVisualType.CLUSTERED_COLUMN,
    OACChartType.HORIZONTAL_BAR: PBIVisualType.CLUSTERED_BAR,
    OACChartType.STACKED_BAR: PBIVisualType.STACKED_BAR,
    OACChartType.STACKED_COLUMN: PBIVisualType.STACKED_COLUMN,
    OACChartType.LINE: PBIVisualType.LINE,
    OACChartType.AREA: PBIVisualType.AREA,
    OACChartType.COMBO: PBIVisualType.COMBO,
    OACChartType.PIE: PBIVisualType.PIE,
    OACChartType.DONUT: PBIVisualType.DONUT,
    OACChartType.SCATTER: PBIVisualType.SCATTER,
    OACChartType.BUBBLE: PBIVisualType.SCATTER,
    OACChartType.FILLED_MAP: PBIVisualType.FILLED_MAP,
    OACChartType.BUBBLE_MAP: PBIVisualType.MAP,
    OACChartType.GAUGE: PBIVisualType.GAUGE,
    OACChartType.KPI: PBIVisualType.CARD,
    OACChartType.FUNNEL: PBIVisualType.FUNNEL,
    OACChartType.TREEMAP: PBIVisualType.TREEMAP,
    OACChartType.HEATMAP: PBIVisualType.MATRIX,
    OACChartType.WATERFALL: PBIVisualType.WATERFALL,
    OACChartType.NARRATIVE: PBIVisualType.TEXTBOX,
    OACChartType.IMAGE: PBIVisualType.IMAGE,
    OACChartType.TRELLIS: PBIVisualType.CLUSTERED_COLUMN,  # + small multiples
}


def map_visual_type(oac_type: str) -> tuple[PBIVisualType, list[str]]:
    """Map an OAC chart type string to a PBI visual type.

    Returns
    -------
    (pbi_visual_type, warnings)
        The mapped PBI visual type and any warnings.
    """
    warnings: list[str] = []
    try:
        chart = OACChartType(oac_type)
    except ValueError:
        # Attempt normalisation
        normalised = _normalise_chart_type(oac_type)
        try:
            chart = OACChartType(normalised)
        except ValueError:
            warnings.append(f"Unknown OAC chart type '{oac_type}' — defaulting to table")
            return PBIVisualType.TABLE_EX, warnings

    pbi_type = _OAC_TO_PBI.get(chart, PBIVisualType.TABLE_EX)

    if chart == OACChartType.TRELLIS:
        warnings.append("Trellis mapped to clustered column with small multiples — verify layout")
    if chart == OACChartType.HEATMAP:
        warnings.append("Heatmap mapped to matrix with conditional formatting — verify appearance")
    if chart == OACChartType.BUBBLE:
        warnings.append("Bubble chart mapped to scatter — ensure size field is configured")

    return pbi_type, warnings


def _normalise_chart_type(raw: str) -> str:
    """Attempt to normalise varied OAC chart type strings."""
    s = raw.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    mapping: dict[str, str] = {
        "bar": "verticalBar",
        "column": "verticalBar",
        "horizontalbar": "horizontalBar",
        "stackedbar": "stackedBar",
        "stackedcolumn": "stackedColumn",
        "linechart": "line",
        "areachart": "area",
        "combochart": "combo",
        "piechart": "pie",
        "donutchart": "donut",
        "scatterchart": "scatter",
        "bubblechart": "bubble",
        "filledmap": "filledMap",
        "bubblemap": "bubbleMap",
        "gaugechart": "gauge",
        "kpimetric": "kpi",
        "metric": "kpi",
        "funnelchart": "funnel",
        "treemapchart": "treemap",
        "waterfallchart": "waterfall",
        "narrative": "narrative",
        "textbox": "narrative",
        "richtext": "narrative",
        "trellis": "trellis",
        "smallmultiples": "trellis",
        "pivottable": "pivotTable",
        "crosstab": "pivotTable",
        "matrix": "pivotTable",
        "table": "table",
        "image": "image",
    }
    return mapping.get(s, raw)


# ---------------------------------------------------------------------------
# Data field role mapping
# ---------------------------------------------------------------------------

# PBI visual data roles per visual type
_VISUAL_DATA_ROLES: dict[PBIVisualType, list[str]] = {
    PBIVisualType.TABLE_EX: ["Values"],
    PBIVisualType.MATRIX: ["Rows", "Columns", "Values"],
    PBIVisualType.CLUSTERED_BAR: ["Category", "Y"],
    PBIVisualType.CLUSTERED_COLUMN: ["Category", "Y"],
    PBIVisualType.STACKED_BAR: ["Category", "Series", "Y"],
    PBIVisualType.STACKED_COLUMN: ["Category", "Series", "Y"],
    PBIVisualType.LINE: ["Category", "Y", "Series"],
    PBIVisualType.AREA: ["Category", "Y"],
    PBIVisualType.COMBO: ["Category", "ColumnY", "LineY"],
    PBIVisualType.PIE: ["Category", "Y"],
    PBIVisualType.DONUT: ["Category", "Y"],
    PBIVisualType.SCATTER: ["X", "Y", "Size", "Legend"],
    PBIVisualType.FILLED_MAP: ["Location", "Values"],
    PBIVisualType.MAP: ["Latitude", "Longitude", "Size"],
    PBIVisualType.GAUGE: ["Y", "MinValue", "MaxValue", "TargetValue"],
    PBIVisualType.CARD: ["Fields"],
    PBIVisualType.MULTI_ROW_CARD: ["Fields"],
    PBIVisualType.FUNNEL: ["Category", "Y"],
    PBIVisualType.TREEMAP: ["Group", "Values"],
    PBIVisualType.WATERFALL: ["Category", "Y"],
}


def get_data_roles(visual_type: PBIVisualType) -> list[str]:
    """Return the expected data field roles for a visual type."""
    return _VISUAL_DATA_ROLES.get(visual_type, ["Values"])


# ---------------------------------------------------------------------------
# Data class for a mapped visual column
# ---------------------------------------------------------------------------


@dataclass
class VisualFieldMapping:
    """Maps an OAC analysis column to a PBI visual data role."""

    role: str                       # PBI data role (Category, Y, Values, etc.)
    table_name: str                 # Semantic model table
    column_name: str                # Semantic model column / measure
    is_measure: bool = False
    aggregation: str = ""           # SUM, COUNT, etc.
    sort_order: str = ""            # ascending | descending


def map_oac_columns_to_roles(
    oac_columns: list[dict[str, Any]],
    visual_type: PBIVisualType,
    table_mapping: dict[str, str] | None = None,
) -> list[VisualFieldMapping]:
    """Map OAC view columns to PBI visual data roles.

    OAC columns typically have:
    - category columns (dimensions on axis/rows)
    - measure columns (values)
    - series columns (legend/color)

    This function assigns them to the appropriate PBI data roles
    based on the visual type.
    """
    tmap = table_mapping or {}
    roles = get_data_roles(visual_type)
    mappings: list[VisualFieldMapping] = []

    categories = [c for c in oac_columns if not c.get("is_measure", False)]
    measures = [c for c in oac_columns if c.get("is_measure", False)]

    # Assign category columns
    cat_roles = [r for r in roles if r in ("Category", "Rows", "Group", "Location", "X")]
    for i, col in enumerate(categories):
        role = cat_roles[i] if i < len(cat_roles) else "Category"
        tbl = tmap.get(col.get("table", ""), col.get("table", ""))
        mappings.append(
            VisualFieldMapping(
                role=role,
                table_name=tbl,
                column_name=col.get("name", ""),
                is_measure=False,
                sort_order=col.get("sort_order", ""),
            )
        )

    # Assign measure columns
    val_roles = [r for r in roles if r in ("Y", "Values", "ColumnY", "LineY", "Size", "Fields")]
    for i, col in enumerate(measures):
        role = val_roles[i] if i < len(val_roles) else "Y"
        tbl = tmap.get(col.get("table", ""), col.get("table", ""))
        mappings.append(
            VisualFieldMapping(
                role=role,
                table_name=tbl,
                column_name=col.get("name", ""),
                is_measure=True,
                aggregation=col.get("aggregation", "SUM"),
                sort_order=col.get("sort_order", ""),
            )
        )

    return mappings


# ---------------------------------------------------------------------------
# Conditional formatting
# ---------------------------------------------------------------------------


@dataclass
class ConditionalFormatRule:
    """A single conditional formatting rule for a PBI visual."""

    column_name: str
    rule_type: str              # color | dataBar | icon
    conditions: list[dict[str, Any]] = field(default_factory=list)
    # Each condition: {"operator": "greaterThan", "value": 100, "color": "#00FF00"}


def translate_conditional_format(
    oac_format: dict[str, Any],
) -> ConditionalFormatRule | None:
    """Translate an OAC conditional formatting spec to a PBI rule.

    OAC format metadata example::

        {
            "column": "Revenue",
            "type": "stoplight",
            "thresholds": [
                {"value": 100, "color": "green"},
                {"value": 50, "color": "yellow"},
                {"value": 0, "color": "red"}
            ]
        }
    """
    col = oac_format.get("column", "")
    fmt_type = oac_format.get("type", "color").lower()
    thresholds = oac_format.get("thresholds", [])

    if not col:
        return None

    # Determine rule type
    rule_type = "color"
    if fmt_type in ("databar", "databars", "data_bar"):
        rule_type = "dataBar"
    elif fmt_type in ("stoplight", "icon", "iconset", "icon_set"):
        rule_type = "icon"

    # Build conditions
    _COLOR_MAP = {
        "green": "#00B050",
        "yellow": "#FFC000",
        "red": "#FF0000",
        "blue": "#4472C4",
        "orange": "#ED7D31",
        "gray": "#A5A5A5",
        "grey": "#A5A5A5",
    }

    conditions: list[dict[str, Any]] = []
    sorted_thresholds = sorted(thresholds, key=lambda t: t.get("value", 0), reverse=True)
    for i, th in enumerate(sorted_thresholds):
        color = th.get("color", "")
        if color.lower() in _COLOR_MAP:
            color = _COLOR_MAP[color.lower()]
        elif not color.startswith("#"):
            color = "#4472C4"

        conditions.append({
            "operator": "greaterThanOrEqual" if i < len(sorted_thresholds) - 1 else "greaterThanOrEqual",
            "value": th.get("value", 0),
            "color": color,
        })

    return ConditionalFormatRule(
        column_name=col,
        rule_type=rule_type,
        conditions=conditions,
    )


# ---------------------------------------------------------------------------
# Number format translation
# ---------------------------------------------------------------------------

_OAC_FORMAT_MAP: dict[str, str] = {
    "#,##0": "#,0",
    "#,##0.00": "#,0.00",
    "#,##0.0": "#,0.0",
    "0.00%": "0.00%",
    "0%": "0%",
    "$#,##0.00": "$#,0.00",
    "€#,##0.00": "€#,0.00",
    "yyyy-MM-dd": "yyyy-MM-dd",
    "MM/dd/yyyy": "M/d/yyyy",
    "dd/MM/yyyy": "d/M/yyyy",
}


def translate_format_string(oac_format: str) -> str:
    """Translate an OAC number/date format string to PBI equivalent."""
    if not oac_format:
        return ""
    # Direct match
    if oac_format in _OAC_FORMAT_MAP:
        return _OAC_FORMAT_MAP[oac_format]
    # Most OAC formats are close enough to PBI
    return oac_format


# ---------------------------------------------------------------------------
# Sort configuration
# ---------------------------------------------------------------------------


@dataclass
class SortConfig:
    """Sort configuration for a PBI visual."""

    column_name: str
    table_name: str = ""
    direction: str = "ascending"    # ascending | descending


def translate_sort(oac_sort: dict[str, Any]) -> SortConfig | None:
    """Translate an OAC sort spec to a PBI sort config."""
    col = oac_sort.get("column", "")
    if not col:
        return None
    direction = oac_sort.get("direction", "ascending").lower()
    if direction not in ("ascending", "descending"):
        direction = "ascending"
    return SortConfig(
        column_name=col,
        table_name=oac_sort.get("table", ""),
        direction=direction,
    )
