"""Complexity scorer — weighted scoring per asset for migration prioritization.

Weights from Agent 01 SPEC:
  Custom calculations:      0.3  (1–10)
  RLS complexity:           0.2  (1–10)
  Custom viz / plugins:     0.2  (1–10)
  Column / measure count:   0.1  (1–10)
  Prompt / filter count:    0.1  (1–10)
  Dashboard page count:     0.1  (1–10)

Total = Σ(weight × score)  → Low (1–3), Medium (4–6), High (7–10)
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.models import AssetType, ComplexityCategory, InventoryItem

logger = logging.getLogger(__name__)

# Weight configuration (sum = 1.0)
WEIGHTS = {
    "custom_calcs": 0.3,
    "rls": 0.2,
    "custom_viz": 0.2,
    "columns": 0.1,
    "prompts": 0.1,
    "pages": 0.1,
}


def _clamp(value: float, lo: float = 1.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def _scale(count: int, thresholds: tuple[int, ...] = (2, 5, 10, 20, 40)) -> float:
    """Map a count onto a 1–10 scale using the given thresholds."""
    for i, t in enumerate(thresholds):
        if count <= t:
            return _clamp(1.0 + (i * 2))
    return 10.0


# ---------------------------------------------------------------------------
# Factor extractors
# ---------------------------------------------------------------------------

def _custom_calc_score(meta: dict[str, Any], asset_type: AssetType) -> float:
    """Score based on custom OAC expressions / calculated columns."""
    if asset_type in (AssetType.LOGICAL_TABLE, AssetType.DATA_MODEL):
        return _scale(meta.get("custom_calc_count", 0), (1, 3, 7, 15, 30))
    # For analyses, count filters with expressions
    filters = meta.get("filters", [])
    return _scale(len(filters), (1, 3, 6, 10, 20))


def _rls_score(meta: dict[str, Any], asset_type: AssetType) -> float:
    """Score based on row-level security complexity."""
    if asset_type == AssetType.INIT_BLOCK:
        variables = meta.get("variables", [])
        return _scale(len(variables), (1, 2, 4, 7, 10))
    if asset_type == AssetType.SECURITY_ROLE:
        perms = meta.get("permissions", [])
        return _scale(len(perms), (2, 5, 10, 20, 40))
    # Non-security items get baseline
    return 1.0


def _custom_viz_score(meta: dict[str, Any], asset_type: AssetType) -> float:
    """Score for custom viz / plugins — analyses & dashboards."""
    if asset_type not in (AssetType.ANALYSIS, AssetType.DASHBOARD):
        return 1.0
    # Heuristic: presence of custom visualization markers in metadata
    if meta.get("custom_visualizations"):
        return _scale(len(meta["custom_visualizations"]), (1, 2, 4, 6, 10))
    return 1.0


def _columns_score(meta: dict[str, Any]) -> float:
    columns = meta.get("columns", [])
    return _scale(len(columns) if isinstance(columns, list) else 0, (5, 15, 30, 60, 100))


def _prompts_score(meta: dict[str, Any]) -> float:
    prompts = meta.get("prompts", [])
    return _scale(len(prompts) if isinstance(prompts, list) else 0, (1, 3, 5, 8, 12))


def _pages_score(meta: dict[str, Any]) -> float:
    pages = meta.get("pages", [])
    count = len(pages) if isinstance(pages, list) else 0
    return _scale(count, (1, 3, 5, 8, 12))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_item(item: InventoryItem) -> tuple[float, ComplexityCategory]:
    """Compute weighted complexity score and category for a single item."""
    meta = item.metadata
    at = item.asset_type

    total = (
        WEIGHTS["custom_calcs"] * _custom_calc_score(meta, at)
        + WEIGHTS["rls"] * _rls_score(meta, at)
        + WEIGHTS["custom_viz"] * _custom_viz_score(meta, at)
        + WEIGHTS["columns"] * _columns_score(meta)
        + WEIGHTS["prompts"] * _prompts_score(meta)
        + WEIGHTS["pages"] * _pages_score(meta)
    )

    total = round(total, 2)

    if total <= 3.0:
        category = ComplexityCategory.LOW
    elif total <= 6.0:
        category = ComplexityCategory.MEDIUM
    else:
        category = ComplexityCategory.HIGH

    return total, category


def score_all(items: list[InventoryItem]) -> list[InventoryItem]:
    """Score every item in-place and return the list."""
    for item in items:
        score, category = score_item(item)
        item.complexity_score = score
        item.complexity_category = category

    low = sum(1 for i in items if i.complexity_category == ComplexityCategory.LOW)
    med = sum(1 for i in items if i.complexity_category == ComplexityCategory.MEDIUM)
    high = sum(1 for i in items if i.complexity_category == ComplexityCategory.HIGH)
    logger.info("Complexity scoring: %d Low, %d Medium, %d High", low, med, high)

    return items
