"""Prompt / slicer converter — OAC prompts → Power BI slicers & parameters.

Translates OAC analysis/dashboard prompts into Power BI slicer visuals
or what-if parameters, preserving filter type, default values, and
cascading relationships.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAC prompt types
# ---------------------------------------------------------------------------


class OACPromptType(str, Enum):
    """Known OAC prompt/filter types."""

    DROPDOWN_SINGLE = "dropdownSingle"
    DROPDOWN_MULTI = "dropdownMulti"
    SEARCH = "search"
    SLIDER = "slider"
    DATE_PICKER = "datePicker"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    TEXT_INPUT = "textInput"
    CASCADING = "cascading"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# PBI slicer styles
# ---------------------------------------------------------------------------


class PBISlicerStyle(str, Enum):
    """Power BI slicer visual sub-types / styles."""

    DROPDOWN = "Dropdown"
    LIST = "List"
    TILE = "Tile"
    DATE_RANGE = "DateRange"
    RELATIVE_DATE = "RelativeDate"
    BETWEEN = "Between"
    SEARCH = "Dropdown"      # dropdown with search


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SlicerConfig:
    """Configuration for a Power BI slicer visual."""

    visual_id: str = ""
    title: str = ""
    table_name: str = ""
    column_name: str = ""
    slicer_style: PBISlicerStyle = PBISlicerStyle.DROPDOWN
    multi_select: bool = False
    search_enabled: bool = False
    default_values: list[Any] = field(default_factory=list)
    select_all_enabled: bool = True
    is_date_slicer: bool = False
    # Position on canvas (filled by layout engine)
    x: int = 0
    y: int = 0
    width: int = 200
    height: int = 60
    # Cascading / relationship info
    parent_slicer_id: str = ""      # For cascading prompts
    warnings: list[str] = field(default_factory=list)
    requires_review: bool = False

    def __post_init__(self) -> None:
        if not self.visual_id:
            self.visual_id = str(uuid.uuid4()).replace("-", "")[:16]


@dataclass
class ParameterConfig:
    """Configuration for a Power BI What-If parameter."""

    name: str = ""
    data_type: str = "text"         # text | number | date
    default_value: str = ""
    table_name: str = ""
    column_name: str = ""
    warnings: list[str] = field(default_factory=list)
    requires_review: bool = False


# ---------------------------------------------------------------------------
# Prompt type mapping
# ---------------------------------------------------------------------------

_PROMPT_TO_SLICER: dict[OACPromptType, tuple[PBISlicerStyle, bool, bool]] = {
    # (slicer_style, multi_select, search_enabled)
    OACPromptType.DROPDOWN_SINGLE: (PBISlicerStyle.DROPDOWN, False, False),
    OACPromptType.DROPDOWN_MULTI: (PBISlicerStyle.DROPDOWN, True, False),
    OACPromptType.SEARCH: (PBISlicerStyle.DROPDOWN, False, True),
    OACPromptType.SLIDER: (PBISlicerStyle.BETWEEN, False, False),
    OACPromptType.DATE_PICKER: (PBISlicerStyle.DATE_RANGE, False, False),
    OACPromptType.RADIO: (PBISlicerStyle.TILE, False, False),
    OACPromptType.CHECKBOX: (PBISlicerStyle.TILE, True, False),
    OACPromptType.CASCADING: (PBISlicerStyle.DROPDOWN, False, False),
}


def _parse_prompt_type(raw: str) -> OACPromptType:
    """Normalise a raw OAC prompt type string to an enum."""
    s = raw.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    mapping: dict[str, OACPromptType] = {
        "dropdown": OACPromptType.DROPDOWN_SINGLE,
        "dropdownsingle": OACPromptType.DROPDOWN_SINGLE,
        "dropdownsingleselect": OACPromptType.DROPDOWN_SINGLE,
        "dropdownmulti": OACPromptType.DROPDOWN_MULTI,
        "dropdownmultiselect": OACPromptType.DROPDOWN_MULTI,
        "multiselect": OACPromptType.DROPDOWN_MULTI,
        "search": OACPromptType.SEARCH,
        "typeahead": OACPromptType.SEARCH,
        "slider": OACPromptType.SLIDER,
        "range": OACPromptType.SLIDER,
        "datepicker": OACPromptType.DATE_PICKER,
        "daterange": OACPromptType.DATE_PICKER,
        "date": OACPromptType.DATE_PICKER,
        "radio": OACPromptType.RADIO,
        "radiobutton": OACPromptType.RADIO,
        "checkbox": OACPromptType.CHECKBOX,
        "textinput": OACPromptType.TEXT_INPUT,
        "text": OACPromptType.TEXT_INPUT,
        "cascading": OACPromptType.CASCADING,
    }
    return mapping.get(s, OACPromptType.UNKNOWN)


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------


def convert_prompt(
    prompt_meta: dict[str, Any],
    table_mapping: dict[str, str] | None = None,
) -> SlicerConfig | ParameterConfig:
    """Convert an OAC prompt definition to a PBI slicer or parameter.

    Parameters
    ----------
    prompt_meta : dict
        OAC prompt metadata, expected keys::

            - name: str
            - type: str (OAC prompt type)
            - table: str (source table)
            - column: str (source column)
            - default_values: list
            - cascading_parent: str (optional)
            - data_type: str (optional, for text input)

    table_mapping : dict
        OAC table name → PBI semantic model table name.
    """
    tmap = table_mapping or {}
    prompt_type = _parse_prompt_type(prompt_meta.get("type", "dropdown"))
    table = tmap.get(prompt_meta.get("table", ""), prompt_meta.get("table", ""))
    column = prompt_meta.get("column", "")
    name = prompt_meta.get("name", column)
    defaults = prompt_meta.get("default_values", [])
    data_type = prompt_meta.get("data_type", "").lower()

    warnings: list[str] = []

    # Text input → What-If parameter
    if prompt_type == OACPromptType.TEXT_INPUT:
        return ParameterConfig(
            name=name,
            data_type=data_type or "text",
            default_value=str(defaults[0]) if defaults else "",
            table_name=table,
            column_name=column,
            warnings=warnings,
        )

    # Unknown type
    if prompt_type == OACPromptType.UNKNOWN:
        warnings.append(f"Unknown prompt type '{prompt_meta.get('type', '')}' — defaulting to dropdown")
        prompt_type = OACPromptType.DROPDOWN_SINGLE

    # Look up slicer config
    style, multi, search = _PROMPT_TO_SLICER.get(
        prompt_type,
        (PBISlicerStyle.DROPDOWN, False, False),
    )

    # Date detection
    is_date = data_type in ("date", "timestamp", "datetime") or prompt_type == OACPromptType.DATE_PICKER

    # Cascading parent
    parent = prompt_meta.get("cascading_parent", "")
    if parent:
        warnings.append(
            f"Cascading prompt — parent column '{parent}'. "
            "In PBI, cascading is handled via model relationships. Verify slicer interaction."
        )

    return SlicerConfig(
        title=name,
        table_name=table,
        column_name=column,
        slicer_style=style,
        multi_select=multi,
        search_enabled=search,
        default_values=defaults,
        is_date_slicer=is_date,
        parent_slicer_id=parent,
        warnings=warnings,
        requires_review=bool(warnings),
    )


def convert_all_prompts(
    prompts: list[dict[str, Any]],
    table_mapping: dict[str, str] | None = None,
) -> list[SlicerConfig | ParameterConfig]:
    """Convert a list of OAC prompt definitions."""
    return [convert_prompt(p, table_mapping) for p in prompts]


# ---------------------------------------------------------------------------
# Slicer visual JSON generation
# ---------------------------------------------------------------------------


def slicer_to_visual_json(slicer: SlicerConfig) -> dict[str, Any]:
    """Generate the PBI visual JSON config for a slicer.

    Returns a dict suitable for inclusion in a PBIR visual JSON file.
    """
    visual: dict[str, Any] = {
        "name": slicer.visual_id,
        "visualType": "slicer",
        "position": {
            "x": slicer.x,
            "y": slicer.y,
            "width": slicer.width,
            "height": slicer.height,
        },
        "config": {
            "singleVisual": {
                "visualType": "slicer",
                "title": slicer.title,
                "prototypeQuery": {
                    "Select": [
                        {
                            "Column": {
                                "Expression": {"SourceRef": {"Entity": slicer.table_name}},
                                "Property": slicer.column_name,
                            },
                            "Name": f"{slicer.table_name}.{slicer.column_name}",
                        }
                    ],
                },
                "objects": _build_slicer_objects(slicer),
            },
        },
    }
    return visual


def _build_slicer_objects(slicer: SlicerConfig) -> dict[str, Any]:
    """Build slicer formatting objects."""
    objects: dict[str, Any] = {
        "data": [
            {
                "properties": {
                    "mode": {
                        "expr": {"Literal": {"Value": f"'{slicer.slicer_style.value}'"}}
                    },
                },
            }
        ],
        "selection": [
            {
                "properties": {
                    "selectAllCheckbox": {
                        "expr": {"Literal": {"Value": str(slicer.select_all_enabled).lower()}}
                    },
                    "singleSelect": {
                        "expr": {"Literal": {"Value": str(not slicer.multi_select).lower()}}
                    },
                },
            }
        ],
    }
    if slicer.search_enabled:
        objects["general"] = [
            {
                "properties": {
                    "filter": {"expr": {"Literal": {"Value": "true"}}},
                },
            }
        ]
    return objects
