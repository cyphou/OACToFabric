"""PBI bookmark generation from OAC story points and saved filter states.

Ported from T2P — generates PBI bookmark JSON structures that capture
page state + filter state + visual visibility for guided navigation.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bookmark model
# ---------------------------------------------------------------------------


@dataclass
class BookmarkFilter:
    """A filter applied within a bookmark."""

    table: str
    column: str
    operator: str = "In"        # In, NotIn, GreaterThan, etc.
    values: list[Any] = field(default_factory=list)


@dataclass
class PBIBookmark:
    """A Power BI bookmark definition."""

    name: str
    display_name: str
    page_name: str = ""
    filters: list[BookmarkFilter] = field(default_factory=list)
    hidden_visuals: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Generate the PBI bookmark JSON structure."""
        bookmark_id = str(uuid.uuid4()).replace("-", "")[:16]

        filter_json = []
        for f in self.filters:
            filter_json.append({
                "type": "Categorical",
                "column": {
                    "Expression": {
                        "SourceRef": {"Entity": f.table},
                    },
                    "Property": f.column,
                },
                "filterType": 1 if f.operator == "In" else 2,
                "values": [{"Literal": {"Value": f"'{v}'"}} for v in f.values] if f.values else [],
            })

        return {
            "name": bookmark_id,
            "displayName": self.display_name,
            "explorationState": {
                "activeSection": self.page_name,
                "filters": json.dumps(filter_json) if filter_json else "",
            },
            "options": {
                "targetVisuals": None,
                "hiddenVisuals": self.hidden_visuals if self.hidden_visuals else None,
            },
        }


# ---------------------------------------------------------------------------
# Conversion from OAC story points / saved states
# ---------------------------------------------------------------------------


def convert_oac_story_points(
    story_points: list[dict[str, Any]],
    page_mapping: dict[str, str] | None = None,
) -> list[PBIBookmark]:
    """Convert OAC story/narrative points to PBI bookmarks.

    Parameters
    ----------
    story_points
        List of OAC story point dicts with keys:
        - name: story point name
        - page: OAC page/tab
        - filters: list of filter dicts
        - hidden_views: list of hidden view names
    page_mapping
        Maps OAC page names to PBI page IDs.
    """
    pmap = page_mapping or {}
    bookmarks: list[PBIBookmark] = []

    for i, sp in enumerate(story_points):
        name = sp.get("name", f"Bookmark {i + 1}")
        oac_page = sp.get("page", "")
        pbi_page = pmap.get(oac_page, oac_page)

        filters: list[BookmarkFilter] = []
        for flt in sp.get("filters", []):
            if isinstance(flt, dict):
                filters.append(BookmarkFilter(
                    table=flt.get("table", ""),
                    column=flt.get("column", ""),
                    operator=flt.get("operator", "In"),
                    values=flt.get("values", []),
                ))

        bookmarks.append(PBIBookmark(
            name=name,
            display_name=name,
            page_name=pbi_page,
            filters=filters,
            hidden_visuals=sp.get("hidden_views", []),
            description=sp.get("description", ""),
        ))

    logger.info("Generated %d bookmarks from OAC story points", len(bookmarks))
    return bookmarks


def convert_saved_filter_states(
    saved_states: list[dict[str, Any]],
) -> list[PBIBookmark]:
    """Convert OAC saved filter selections to PBI bookmarks.

    Parameters
    ----------
    saved_states
        List of saved state dicts with keys:
        - name: saved state name
        - prompt_values: dict of prompt_name → list of selected values
        - page: optional page reference
    """
    bookmarks: list[PBIBookmark] = []

    for state in saved_states:
        name = state.get("name", "Saved State")
        filters: list[BookmarkFilter] = []

        for prompt_name, values in state.get("prompt_values", {}).items():
            # Map OAC prompt to table.column reference
            # Convention: prompt names follow "TableName.ColumnName" or just "ColumnName"
            parts = prompt_name.split(".", 1)
            table = parts[0] if len(parts) > 1 else ""
            column = parts[-1]

            filters.append(BookmarkFilter(
                table=table,
                column=column,
                values=values if isinstance(values, list) else [values],
            ))

        bookmarks.append(PBIBookmark(
            name=name,
            display_name=name,
            page_name=state.get("page", ""),
            filters=filters,
        ))

    logger.info("Generated %d bookmarks from saved filter states", len(bookmarks))
    return bookmarks


def generate_bookmarks_json(bookmarks: list[PBIBookmark]) -> str:
    """Generate the PBI bookmarks JSON array for report.json config."""
    return json.dumps([b.to_dict() for b in bookmarks], indent=2)
