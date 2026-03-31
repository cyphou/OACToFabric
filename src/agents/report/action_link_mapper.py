"""Action Link Mapper — OAC navigation actions → PBI drillthrough / bookmarks.

Maps OAC analysis-level action links to Power BI equivalents:
  - Navigate → Drillthrough page + cross-report filters
  - Drill Down → Hierarchy expansion / drillthrough
  - URL → Button visual with URL action
  - Invoke Agent → Data Activator trigger (delegated to alert_migrator)

This module produces PBIR-compatible JSON for embedding in visual configs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapped action types
# ---------------------------------------------------------------------------


@dataclass
class PBIDrillthrough:
    """A Power BI drillthrough page configuration."""

    target_page: str
    filter_columns: list[str] = field(default_factory=list)
    keep_all_filters: bool = True
    cross_report: bool = False
    target_report_id: str = ""

    def to_visual_json(self) -> dict[str, Any]:
        """Generate drillthrough JSON for PBIR visual config."""
        config: dict[str, Any] = {
            "drillthrough": {
                "targetPage": self.target_page,
                "filterColumns": self.filter_columns,
                "keepAllFilters": self.keep_all_filters,
            }
        }
        if self.cross_report:
            config["drillthrough"]["crossReport"] = {
                "enabled": True,
                "targetReportId": self.target_report_id,
            }
        return config


@dataclass
class PBIBookmarkAction:
    """A Power BI bookmark navigation action."""

    bookmark_name: str
    display_name: str = ""

    def to_visual_json(self) -> dict[str, Any]:
        return {
            "action": {
                "type": "Bookmark",
                "bookmark": self.bookmark_name,
                "displayName": self.display_name or self.bookmark_name,
            }
        }


@dataclass
class PBIURLAction:
    """A Power BI URL action (button visual)."""

    url: str
    display_text: str = "Open Link"
    tooltip: str = ""

    def to_visual_json(self) -> dict[str, Any]:
        return {
            "action": {
                "type": "WebUrl",
                "url": self.url,
                "displayText": self.display_text,
                "tooltip": self.tooltip or self.display_text,
            }
        }


@dataclass
class PBIPageNavigationAction:
    """A Power BI page navigation action."""

    target_page: str
    display_text: str = ""

    def to_visual_json(self) -> dict[str, Any]:
        return {
            "action": {
                "type": "PageNavigation",
                "destination": self.target_page,
                "displayText": self.display_text or self.target_page,
            }
        }


@dataclass
class ActionMappingResult:
    """Result of mapping OAC actions to PBI equivalents."""

    drillthroughs: list[PBIDrillthrough] = field(default_factory=list)
    bookmarks: list[PBIBookmarkAction] = field(default_factory=list)
    url_actions: list[PBIURLAction] = field(default_factory=list)
    page_navigations: list[PBIPageNavigationAction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Mapping logic
# ---------------------------------------------------------------------------


def map_oac_action_link(
    action_type: str,
    target: str,
    parameters: dict[str, str] | None = None,
    source_column: str = "",
) -> PBIDrillthrough | PBIBookmarkAction | PBIURLAction | PBIPageNavigationAction | None:
    """Map a single OAC action link to a PBI action.

    Parameters
    ----------
    action_type : str
        OAC action type (navigate, drillDown, drillThrough, url).
    target : str
        Target path or URL.
    parameters : dict[str, str] | None
        Action parameters (column mappings, filters).
    source_column : str
        Source column triggering the action.

    Returns
    -------
    PBIDrillthrough | PBIBookmarkAction | PBIURLAction | PBIPageNavigationAction | None
        Mapped PBI action, or None if unmappable.
    """
    params = parameters or {}
    norm_type = action_type.lower().replace("_", "").replace("-", "")

    if norm_type in ("navigate", "executereport"):
        filter_cols = [source_column] if source_column else list(params.keys())
        return PBIDrillthrough(
            target_page=target,
            filter_columns=filter_cols,
            cross_report="/" in target,
            target_report_id=params.get("reportId", ""),
        )

    if norm_type in ("drilldown", "drillthrough"):
        filter_cols = [source_column] if source_column else list(params.keys())
        return PBIDrillthrough(
            target_page=target,
            filter_columns=filter_cols,
        )

    if norm_type == "url":
        return PBIURLAction(
            url=target,
            display_text=params.get("label", "Open Link"),
            tooltip=params.get("tooltip", ""),
        )

    if norm_type in ("bookmark", "togglevisibility"):
        return PBIBookmarkAction(
            bookmark_name=target,
            display_name=params.get("label", target),
        )

    if norm_type in ("page", "pagenavigation", "gotosection"):
        return PBIPageNavigationAction(
            target_page=target,
            display_text=params.get("label", target),
        )

    logger.warning("Unmapped OAC action type: %s", action_type)
    return None


def map_all_action_links(
    actions: list[dict[str, Any]],
) -> ActionMappingResult:
    """Map a list of OAC action link definitions to PBI actions.

    Parameters
    ----------
    actions : list[dict[str, Any]]
        OAC action link definitions.
        Each dict must have: ``action_type``, ``target``.
        Optional: ``parameters``, ``source_column``.

    Returns
    -------
    ActionMappingResult
        All mapped PBI actions.
    """
    result = ActionMappingResult()

    for act in actions:
        mapped = map_oac_action_link(
            action_type=act.get("action_type", ""),
            target=act.get("target", ""),
            parameters=act.get("parameters"),
            source_column=act.get("source_column", ""),
        )

        if mapped is None:
            result.warnings.append(
                f"Unmapped action: type={act.get('action_type')}, target={act.get('target')}"
            )
            continue

        if isinstance(mapped, PBIDrillthrough):
            result.drillthroughs.append(mapped)
        elif isinstance(mapped, PBIBookmarkAction):
            result.bookmarks.append(mapped)
        elif isinstance(mapped, PBIURLAction):
            result.url_actions.append(mapped)
        elif isinstance(mapped, PBIPageNavigationAction):
            result.page_navigations.append(mapped)

    logger.info(
        "Mapped %d OAC actions: %d drillthroughs, %d bookmarks, %d URLs, %d navigations",
        len(actions),
        len(result.drillthroughs),
        len(result.bookmarks),
        len(result.url_actions),
        len(result.page_navigations),
    )
    return result
