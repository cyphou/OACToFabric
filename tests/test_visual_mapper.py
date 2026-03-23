"""Tests for visual type mapper — OAC chart types → PBI visuals."""

from __future__ import annotations

import pytest

from src.agents.report.visual_mapper import (
    ConditionalFormatRule,
    OACChartType,
    PBIVisualType,
    SortConfig,
    VisualFieldMapping,
    get_data_roles,
    map_oac_columns_to_roles,
    map_visual_type,
    translate_conditional_format,
    translate_format_string,
    translate_sort,
)


# ---------------------------------------------------------------------------
# Visual type mapping
# ---------------------------------------------------------------------------


class TestMapVisualType:
    def test_table(self):
        vt, w = map_visual_type("table")
        assert vt == PBIVisualType.TABLE_EX
        assert not w

    def test_pivot_table(self):
        vt, _ = map_visual_type("pivotTable")
        assert vt == PBIVisualType.MATRIX

    def test_vertical_bar(self):
        vt, _ = map_visual_type("verticalBar")
        assert vt == PBIVisualType.CLUSTERED_COLUMN

    def test_horizontal_bar(self):
        vt, _ = map_visual_type("horizontalBar")
        assert vt == PBIVisualType.CLUSTERED_BAR

    def test_line(self):
        vt, _ = map_visual_type("line")
        assert vt == PBIVisualType.LINE

    def test_pie(self):
        vt, _ = map_visual_type("pie")
        assert vt == PBIVisualType.PIE

    def test_donut(self):
        vt, _ = map_visual_type("donut")
        assert vt == PBIVisualType.DONUT

    def test_scatter(self):
        vt, _ = map_visual_type("scatter")
        assert vt == PBIVisualType.SCATTER

    def test_bubble_warns(self):
        vt, w = map_visual_type("bubble")
        assert vt == PBIVisualType.SCATTER
        assert any("size field" in x.lower() for x in w)

    def test_gauge(self):
        vt, _ = map_visual_type("gauge")
        assert vt == PBIVisualType.GAUGE

    def test_kpi(self):
        vt, _ = map_visual_type("kpi")
        assert vt == PBIVisualType.CARD

    def test_funnel(self):
        vt, _ = map_visual_type("funnel")
        assert vt == PBIVisualType.FUNNEL

    def test_treemap(self):
        vt, _ = map_visual_type("treemap")
        assert vt == PBIVisualType.TREEMAP

    def test_waterfall(self):
        vt, _ = map_visual_type("waterfall")
        assert vt == PBIVisualType.WATERFALL

    def test_combo(self):
        vt, _ = map_visual_type("combo")
        assert vt == PBIVisualType.COMBO

    def test_area(self):
        vt, _ = map_visual_type("area")
        assert vt == PBIVisualType.AREA

    def test_narrative(self):
        vt, _ = map_visual_type("narrative")
        assert vt == PBIVisualType.TEXTBOX

    def test_image(self):
        vt, _ = map_visual_type("image")
        assert vt == PBIVisualType.IMAGE

    def test_heatmap_warns(self):
        vt, w = map_visual_type("heatmap")
        assert vt == PBIVisualType.MATRIX
        assert any("conditional" in x.lower() for x in w)

    def test_trellis_warns(self):
        vt, w = map_visual_type("trellis")
        assert any("small multiples" in x.lower() for x in w)

    def test_unknown_defaults_to_table(self):
        vt, w = map_visual_type("some_unknown_type")
        assert vt == PBIVisualType.TABLE_EX
        assert len(w) == 1

    def test_normalised_variant(self):
        vt, _ = map_visual_type("line chart")
        assert vt == PBIVisualType.LINE

    def test_crosstab_to_matrix(self):
        vt, _ = map_visual_type("crosstab")
        assert vt == PBIVisualType.MATRIX


# ---------------------------------------------------------------------------
# Data roles
# ---------------------------------------------------------------------------


class TestDataRoles:
    def test_table_roles(self):
        roles = get_data_roles(PBIVisualType.TABLE_EX)
        assert "Values" in roles

    def test_bar_has_category(self):
        roles = get_data_roles(PBIVisualType.CLUSTERED_BAR)
        assert "Category" in roles
        assert "Y" in roles

    def test_scatter_roles(self):
        roles = get_data_roles(PBIVisualType.SCATTER)
        assert "X" in roles
        assert "Y" in roles
        assert "Size" in roles

    def test_unknown_type_defaults(self):
        roles = get_data_roles(PBIVisualType.SLICER)
        assert "Values" in roles


# ---------------------------------------------------------------------------
# Column-to-role mapping
# ---------------------------------------------------------------------------


class TestColumnToRoleMapping:
    def test_categories_and_measures(self):
        cols = [
            {"name": "Region", "table": "Sales"},
            {"name": "Revenue", "table": "Sales", "is_measure": True, "aggregation": "SUM"},
        ]
        mappings = map_oac_columns_to_roles(cols, PBIVisualType.CLUSTERED_COLUMN)
        assert len(mappings) == 2
        assert mappings[0].role == "Category"
        assert mappings[0].is_measure is False
        assert mappings[1].role == "Y"
        assert mappings[1].is_measure is True

    def test_table_mapping_applied(self):
        cols = [{"name": "Col1", "table": "OldTable"}]
        mappings = map_oac_columns_to_roles(
            cols, PBIVisualType.TABLE_EX, table_mapping={"OldTable": "NewTable"}
        )
        assert mappings[0].table_name == "NewTable"


# ---------------------------------------------------------------------------
# Conditional formatting
# ---------------------------------------------------------------------------


class TestConditionalFormat:
    def test_stoplight(self):
        oac = {
            "column": "Revenue",
            "type": "stoplight",
            "thresholds": [
                {"value": 100, "color": "green"},
                {"value": 50, "color": "yellow"},
                {"value": 0, "color": "red"},
            ],
        }
        rule = translate_conditional_format(oac)
        assert rule is not None
        assert rule.column_name == "Revenue"
        assert rule.rule_type == "icon"
        assert len(rule.conditions) == 3
        assert rule.conditions[0]["color"] == "#00B050"  # green

    def test_color_format(self):
        rule = translate_conditional_format({
            "column": "Status",
            "type": "color",
            "thresholds": [{"value": 1, "color": "#FF0000"}],
        })
        assert rule.rule_type == "color"

    def test_databar(self):
        rule = translate_conditional_format({
            "column": "Sales",
            "type": "databar",
            "thresholds": [],
        })
        assert rule.rule_type == "dataBar"

    def test_missing_column_returns_none(self):
        assert translate_conditional_format({"type": "color"}) is None


# ---------------------------------------------------------------------------
# Format string
# ---------------------------------------------------------------------------


class TestFormatString:
    def test_known_format(self):
        assert translate_format_string("#,##0.00") == "#,0.00"

    def test_percent(self):
        assert translate_format_string("0.00%") == "0.00%"

    def test_unknown_passthrough(self):
        assert translate_format_string("custom_fmt") == "custom_fmt"

    def test_empty(self):
        assert translate_format_string("") == ""


# ---------------------------------------------------------------------------
# Sort
# ---------------------------------------------------------------------------


class TestSort:
    def test_basic_sort(self):
        sc = translate_sort({"column": "Revenue", "direction": "descending"})
        assert sc is not None
        assert sc.column_name == "Revenue"
        assert sc.direction == "descending"

    def test_missing_column(self):
        assert translate_sort({}) is None

    def test_invalid_direction_defaults(self):
        sc = translate_sort({"column": "X", "direction": "random"})
        assert sc.direction == "ascending"
