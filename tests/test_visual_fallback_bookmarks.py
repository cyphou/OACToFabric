"""Tests for visual_fallback and bookmark_generator modules."""

from __future__ import annotations

import json

import pytest

from src.agents.report.bookmark_generator import (
    BookmarkFilter,
    PBIBookmark,
    convert_oac_story_points,
    convert_saved_filter_states,
    generate_bookmarks_json,
)
from src.agents.report.visual_fallback import (
    FallbackResult,
    resolve_visual_fallback,
)
from src.agents.report.visual_mapper import PBIVisualType


# ---------------------------------------------------------------------------
# Visual fallback
# ---------------------------------------------------------------------------

class TestVisualFallback:
    def test_known_type_resolved(self):
        result = resolve_visual_fallback("sankey")
        assert isinstance(result, FallbackResult)
        assert result.resolved_type == PBIVisualType.SANKEY
        assert result.original_type == "sankey"

    def test_chord_resolved(self):
        result = resolve_visual_fallback("chord")
        assert result.resolved_type == PBIVisualType.CHORD

    def test_gauge_resolved(self):
        result = resolve_visual_fallback("gauge")
        assert result.resolved_type == PBIVisualType.GAUGE
        assert result.tier <= 2

    def test_unknown_falls_to_table(self):
        result = resolve_visual_fallback("completelyfaketype")
        assert result.resolved_type in (PBIVisualType.TABLE_EX, PBIVisualType.CARD)
        assert result.tier == 3

    def test_sunburst(self):
        result = resolve_visual_fallback("sunburst")
        assert result.resolved_type == PBIVisualType.SUNBURST

    def test_approximation_notes(self):
        result = resolve_visual_fallback("boxAndWhisker")
        assert result.approximation_notes != ""

    def test_trellis(self):
        result = resolve_visual_fallback("trellis")
        assert result.resolved_type == PBIVisualType.CLUSTERED_COLUMN

    def test_kpi(self):
        result = resolve_visual_fallback("kpi")
        assert result.resolved_type == PBIVisualType.CARD


# ---------------------------------------------------------------------------
# Bookmark generator
# ---------------------------------------------------------------------------

class TestBookmarkModel:
    def test_bookmark_to_dict(self):
        bm = PBIBookmark(
            name="Test",
            display_name="Test Bookmark",
            page_name="Page1",
            filters=[BookmarkFilter(table="Sales", column="Region", values=["West"])],
        )
        d = bm.to_dict()
        assert d["displayName"] == "Test Bookmark"
        assert d["explorationState"]["activeSection"] == "Page1"
        assert d["explorationState"]["filters"] != ""

    def test_empty_bookmark(self):
        bm = PBIBookmark(name="Empty", display_name="Empty")
        d = bm.to_dict()
        assert d["displayName"] == "Empty"


class TestConvertStoryPoints:
    def test_basic_conversion(self):
        story_points = [
            {
                "name": "Q1 View",
                "page": "Summary",
                "filters": [
                    {"table": "Date", "column": "Quarter", "values": ["Q1"]},
                ],
                "hidden_views": ["chart_3"],
            },
        ]
        bookmarks = convert_oac_story_points(story_points)
        assert len(bookmarks) == 1
        assert bookmarks[0].display_name == "Q1 View"
        assert len(bookmarks[0].filters) == 1
        assert bookmarks[0].hidden_visuals == ["chart_3"]

    def test_page_mapping(self):
        story_points = [{"name": "SP1", "page": "OAC_Page"}]
        bookmarks = convert_oac_story_points(
            story_points, page_mapping={"OAC_Page": "PBI_Page_001"}
        )
        assert bookmarks[0].page_name == "PBI_Page_001"

    def test_empty_story_points(self):
        assert convert_oac_story_points([]) == []

    def test_multiple_story_points(self):
        points = [{"name": f"SP{i}"} for i in range(5)]
        bookmarks = convert_oac_story_points(points)
        assert len(bookmarks) == 5


class TestConvertSavedStates:
    def test_prompt_values(self):
        states = [
            {
                "name": "West Region",
                "prompt_values": {"Sales.Region": ["West", "Northwest"]},
            },
        ]
        bookmarks = convert_saved_filter_states(states)
        assert len(bookmarks) == 1
        assert bookmarks[0].filters[0].table == "Sales"
        assert bookmarks[0].filters[0].column == "Region"
        assert len(bookmarks[0].filters[0].values) == 2

    def test_simple_column_name(self):
        states = [{"name": "S1", "prompt_values": {"Category": ["A"]}}]
        bookmarks = convert_saved_filter_states(states)
        assert bookmarks[0].filters[0].table == ""
        assert bookmarks[0].filters[0].column == "Category"


class TestGenerateBookmarksJSON:
    def test_generates_json_array(self):
        bookmarks = [
            PBIBookmark(name="B1", display_name="Bookmark 1"),
            PBIBookmark(name="B2", display_name="Bookmark 2"),
        ]
        result = json.loads(generate_bookmarks_json(bookmarks))
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["displayName"] == "Bookmark 1"
