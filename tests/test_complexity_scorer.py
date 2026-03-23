"""Tests for complexity scorer."""

from __future__ import annotations

import pytest

from src.agents.discovery.complexity_scorer import score_all, score_item
from src.core.models import AssetType, ComplexityCategory, InventoryItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(
    asset_type: AssetType = AssetType.ANALYSIS,
    metadata: dict | None = None,
) -> InventoryItem:
    return InventoryItem(
        id=f"test__{asset_type.value}",
        asset_type=asset_type,
        source_path=f"/test/{asset_type.value}",
        name=f"Test {asset_type.value}",
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestScoreItem:
    def test_minimal_item_is_low(self):
        item = _make_item()
        score, cat = score_item(item)
        assert score >= 1.0
        assert cat == ComplexityCategory.LOW

    def test_many_columns_increases_score(self):
        item_few = _make_item(metadata={"columns": ["a", "b"]})
        item_many = _make_item(metadata={"columns": [f"col_{i}" for i in range(50)]})
        score_few, _ = score_item(item_few)
        score_many, _ = score_item(item_many)
        assert score_many > score_few

    def test_custom_calcs_increase_score(self):
        item = _make_item(
            asset_type=AssetType.LOGICAL_TABLE,
            metadata={"custom_calc_count": 20},
        )
        score, cat = score_item(item)
        assert score > 3.0  # should be Medium+

    def test_rls_increases_score(self):
        item = _make_item(
            asset_type=AssetType.INIT_BLOCK,
            metadata={"variables": ["VAR1", "VAR2", "VAR3", "VAR4", "VAR5"]},
        )
        score, cat = score_item(item)
        assert score > 1.5  # Higher than baseline

    def test_dashboard_with_many_pages(self):
        item = _make_item(
            asset_type=AssetType.DASHBOARD,
            metadata={"pages": [f"Page {i}" for i in range(10)]},
        )
        score, cat = score_item(item)
        assert score > 1.0

    def test_high_complexity_category(self):
        item = _make_item(
            asset_type=AssetType.LOGICAL_TABLE,
            metadata={
                "custom_calc_count": 30,
                "columns": [f"col_{i}" for i in range(100)],
            },
        )
        score, cat = score_item(item)
        assert cat in (ComplexityCategory.MEDIUM, ComplexityCategory.HIGH)


class TestScoreAll:
    def test_scores_all_items(self):
        items = [
            _make_item(metadata={"columns": ["a"]}),
            _make_item(
                asset_type=AssetType.LOGICAL_TABLE,
                metadata={"custom_calc_count": 15},
            ),
        ]
        # Need unique IDs
        items[0].id = "item_1"
        items[1].id = "item_2"

        scored = score_all(items)
        assert len(scored) == 2
        for item in scored:
            assert item.complexity_score > 0
            assert item.complexity_category in ComplexityCategory

    def test_returns_same_list(self):
        items = [_make_item()]
        result = score_all(items)
        assert result is items  # In-place mutation
