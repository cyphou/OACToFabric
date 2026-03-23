"""Tests for prompt/slicer converter — OAC prompts → PBI slicers."""

from __future__ import annotations

import pytest

from src.agents.report.prompt_converter import (
    OACPromptType,
    PBISlicerStyle,
    ParameterConfig,
    SlicerConfig,
    convert_all_prompts,
    convert_prompt,
    slicer_to_visual_json,
)


# ---------------------------------------------------------------------------
# Single prompt conversion
# ---------------------------------------------------------------------------


class TestConvertPrompt:
    def test_dropdown_single(self):
        result = convert_prompt({
            "name": "Region Filter",
            "type": "dropdown",
            "table": "Sales",
            "column": "Region",
        })
        assert isinstance(result, SlicerConfig)
        assert result.slicer_style == PBISlicerStyle.DROPDOWN
        assert result.multi_select is False
        assert result.table_name == "Sales"
        assert result.column_name == "Region"

    def test_dropdown_multi(self):
        result = convert_prompt({
            "name": "Products",
            "type": "dropdownMulti",
            "table": "Products",
            "column": "ProductName",
        })
        assert isinstance(result, SlicerConfig)
        assert result.multi_select is True

    def test_search_type(self):
        result = convert_prompt({
            "name": "Search",
            "type": "search",
            "table": "T",
            "column": "C",
        })
        assert isinstance(result, SlicerConfig)
        assert result.search_enabled is True

    def test_slider_range(self):
        result = convert_prompt({
            "name": "Amount Range",
            "type": "slider",
            "table": "T",
            "column": "Amount",
        })
        assert isinstance(result, SlicerConfig)
        assert result.slicer_style == PBISlicerStyle.BETWEEN

    def test_date_picker(self):
        result = convert_prompt({
            "name": "Date",
            "type": "datePicker",
            "table": "Date",
            "column": "OrderDate",
        })
        assert isinstance(result, SlicerConfig)
        assert result.is_date_slicer is True
        assert result.slicer_style == PBISlicerStyle.DATE_RANGE

    def test_radio_button(self):
        result = convert_prompt({
            "name": "Status",
            "type": "radio",
            "table": "T",
            "column": "Status",
        })
        assert isinstance(result, SlicerConfig)
        assert result.slicer_style == PBISlicerStyle.TILE
        assert result.multi_select is False

    def test_checkbox(self):
        result = convert_prompt({
            "name": "Categories",
            "type": "checkbox",
            "table": "T",
            "column": "Category",
        })
        assert isinstance(result, SlicerConfig)
        assert result.slicer_style == PBISlicerStyle.TILE
        assert result.multi_select is True

    def test_text_input_returns_parameter(self):
        result = convert_prompt({
            "name": "Search Text",
            "type": "textInput",
            "table": "T",
            "column": "SearchField",
        })
        assert isinstance(result, ParameterConfig)
        assert result.name == "Search Text"

    def test_cascading_warns(self):
        result = convert_prompt({
            "name": "City",
            "type": "cascading",
            "table": "T",
            "column": "City",
            "cascading_parent": "Region",
        })
        assert isinstance(result, SlicerConfig)
        assert any("cascading" in w.lower() for w in result.warnings)
        assert result.parent_slicer_id == "Region"

    def test_unknown_type_defaults(self):
        result = convert_prompt({
            "name": "Custom",
            "type": "some_weird_type",
            "table": "T",
            "column": "C",
        })
        assert isinstance(result, SlicerConfig)
        assert result.slicer_style == PBISlicerStyle.DROPDOWN
        assert any("unknown" in w.lower() for w in result.warnings)

    def test_table_mapping(self):
        result = convert_prompt(
            {"name": "F", "type": "dropdown", "table": "OldT", "column": "C"},
            table_mapping={"OldT": "NewT"},
        )
        assert isinstance(result, SlicerConfig)
        assert result.table_name == "NewT"

    def test_default_values_preserved(self):
        result = convert_prompt({
            "name": "F",
            "type": "dropdown",
            "table": "T",
            "column": "C",
            "default_values": ["A", "B"],
        })
        assert isinstance(result, SlicerConfig)
        assert result.default_values == ["A", "B"]


# ---------------------------------------------------------------------------
# Batch conversion
# ---------------------------------------------------------------------------


class TestConvertAllPrompts:
    def test_multiple(self):
        prompts = [
            {"name": "A", "type": "dropdown", "table": "T", "column": "C1"},
            {"name": "B", "type": "textInput", "table": "T", "column": "C2"},
        ]
        results = convert_all_prompts(prompts)
        assert len(results) == 2
        assert isinstance(results[0], SlicerConfig)
        assert isinstance(results[1], ParameterConfig)


# ---------------------------------------------------------------------------
# Slicer visual JSON
# ---------------------------------------------------------------------------


class TestSlicerToVisualJSON:
    def test_generates_valid_json(self):
        slicer = SlicerConfig(
            title="Region",
            table_name="Sales",
            column_name="Region",
            slicer_style=PBISlicerStyle.DROPDOWN,
            x=10, y=10, width=200, height=60,
        )
        vj = slicer_to_visual_json(slicer)
        assert vj["visualType"] == "slicer"
        assert vj["position"]["x"] == 10
        assert vj["config"]["singleVisual"]["title"] == "Region"
        assert "prototypeQuery" in vj["config"]["singleVisual"]

    def test_search_enabled(self):
        slicer = SlicerConfig(
            title="Search",
            table_name="T",
            column_name="C",
            search_enabled=True,
        )
        vj = slicer_to_visual_json(slicer)
        objects = vj["config"]["singleVisual"]["objects"]
        assert "general" in objects
