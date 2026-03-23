"""Tests for layout engine — OAC grid → PBI pixel layout."""

from __future__ import annotations

import pytest

from src.agents.report.layout_engine import (
    DEFAULT_CANVAS_HEIGHT,
    DEFAULT_CANVAS_WIDTH,
    MAX_VISUALS_PER_PAGE,
    MIN_VISUAL_HEIGHT,
    MIN_VISUAL_WIDTH,
    VISUAL_PADDING,
    OACPageLayout,
    OACSection,
    PBIPage,
    VisualPosition,
    compute_page_layouts,
    paginate,
    translate_flat_views,
    translate_sections,
)


# ---------------------------------------------------------------------------
# Section-based layout
# ---------------------------------------------------------------------------


class TestTranslateSections:
    def test_single_full_section(self):
        sections = [
            OACSection(
                name="Main",
                relative_x=0.0, relative_y=0.0,
                relative_width=1.0, relative_height=1.0,
            ),
        ]
        positions = translate_sections(sections)
        assert len(positions) == 1
        p = positions[0]
        assert p.x == VISUAL_PADDING
        assert p.y == VISUAL_PADDING
        assert p.width == DEFAULT_CANVAS_WIDTH - 2 * VISUAL_PADDING
        assert p.height == DEFAULT_CANVAS_HEIGHT - 2 * VISUAL_PADDING

    def test_two_column_layout(self):
        sections = [
            OACSection(
                name="Left",
                relative_x=0.0, relative_y=0.0,
                relative_width=0.5, relative_height=1.0,
            ),
            OACSection(
                name="Right",
                relative_x=0.5, relative_y=0.0,
                relative_width=0.5, relative_height=1.0,
            ),
        ]
        positions = translate_sections(sections)
        assert len(positions) == 2
        assert positions[0].x < positions[1].x  # left before right
        assert positions[0].width == positions[1].width

    def test_section_with_views(self):
        sections = [
            OACSection(
                name="Main",
                relative_x=0.0, relative_y=0.0,
                relative_width=1.0, relative_height=1.0,
                views=[
                    {"name": "chart1", "type": "line"},
                    {"name": "chart2", "type": "table"},
                ],
            ),
        ]
        positions = translate_sections(sections)
        assert len(positions) == 2
        assert positions[0].visual_name == "chart1"
        assert positions[1].visual_name == "chart2"
        # Stacked vertically
        assert positions[1].y > positions[0].y

    def test_minimum_dimensions(self):
        sections = [
            OACSection(
                name="Tiny",
                relative_x=0.0, relative_y=0.0,
                relative_width=0.01, relative_height=0.01,
            ),
        ]
        positions = translate_sections(sections)
        assert positions[0].width >= MIN_VISUAL_WIDTH
        assert positions[0].height >= MIN_VISUAL_HEIGHT


# ---------------------------------------------------------------------------
# Flat view layout
# ---------------------------------------------------------------------------


class TestTranslateFlatViews:
    def test_empty(self):
        assert translate_flat_views([]) == []

    def test_single_view(self):
        views = [{"name": "v1"}]
        positions = translate_flat_views(views)
        assert len(positions) == 1
        assert positions[0].visual_name == "v1"

    def test_grid_layout_3_columns(self):
        views = [{"name": f"v{i}"} for i in range(6)]
        positions = translate_flat_views(views)
        assert len(positions) == 6
        # 3 columns × 2 rows
        # First row: same y
        assert positions[0].y == positions[1].y == positions[2].y
        # Second row: different y
        assert positions[3].y == positions[4].y == positions[5].y
        assert positions[3].y > positions[0].y

    def test_two_views_use_two_columns(self):
        views = [{"name": "a"}, {"name": "b"}]
        positions = translate_flat_views(views)
        assert positions[0].y == positions[1].y  # same row
        assert positions[1].x > positions[0].x   # side by side

    def test_within_canvas(self):
        views = [{"name": f"v{i}"} for i in range(9)]
        positions = translate_flat_views(views)
        for p in positions:
            assert p.x >= 0
            assert p.y >= 0
            assert p.x + p.width <= DEFAULT_CANVAS_WIDTH + 10  # small tolerance
            assert p.y + p.height <= DEFAULT_CANVAS_HEIGHT + 10


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestPaginate:
    def test_no_pagination_needed(self):
        positions = [
            VisualPosition(x=0, y=0, width=400, height=300, visual_name="v1"),
        ]
        result = paginate(positions)
        assert all(p.page_index == 0 for p in result)

    def test_overflow_y(self):
        positions = [
            VisualPosition(x=0, y=0, width=400, height=300, visual_name="v1"),
            VisualPosition(x=0, y=500, width=400, height=300, visual_name="v2"),
        ]
        result = paginate(positions, canvas_height=720)
        # v2 at y=500 + h=300 = 800 > 720 → new page
        assert result[1].page_index == 1

    def test_max_per_page(self):
        positions = [
            VisualPosition(x=0, y=i * 10, width=50, height=50, visual_name=f"v{i}")
            for i in range(5)
        ]
        result = paginate(positions, max_per_page=3, canvas_height=10000)
        assert result[0].page_index == 0
        assert result[2].page_index == 0
        assert result[3].page_index == 1

    def test_empty(self):
        assert paginate([]) == []


# ---------------------------------------------------------------------------
# Full page layout computation
# ---------------------------------------------------------------------------


class TestComputePageLayouts:
    def test_with_sections(self):
        oac_page = OACPageLayout(
            page_name="Dashboard",
            sections=[
                OACSection(
                    name="Top",
                    relative_x=0.0, relative_y=0.0,
                    relative_width=1.0, relative_height=0.5,
                    views=[{"name": "chart1"}],
                ),
                OACSection(
                    name="Bottom",
                    relative_x=0.0, relative_y=0.5,
                    relative_width=1.0, relative_height=0.5,
                    views=[{"name": "chart2"}],
                ),
            ],
        )
        pages = compute_page_layouts(oac_page)
        assert len(pages) >= 1
        assert len(pages[0].visuals) == 2

    def test_flat_views_fallback(self):
        oac_page = OACPageLayout(
            page_name="Simple",
            views=[{"name": "v1"}, {"name": "v2"}],
        )
        pages = compute_page_layouts(oac_page)
        assert len(pages) >= 1
        assert len(pages[0].visuals) >= 2

    def test_auto_pagination(self):
        oac_page = OACPageLayout(
            page_name="Dense",
            views=[{"name": f"v{i}"} for i in range(25)],
        )
        pages = compute_page_layouts(oac_page)
        assert len(pages) >= 2  # 25 visuals should overflow

    def test_page_naming(self):
        oac_page = OACPageLayout(
            page_name="Overview",
            views=[{"name": "v1"}],
        )
        pages = compute_page_layouts(oac_page)
        assert "Overview" in pages[0].display_name
