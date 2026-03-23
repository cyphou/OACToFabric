"""Tests for PBIR generator — end-to-end PBIR file generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agents.report.layout_engine import PBIPage, VisualPosition
from src.agents.report.pbir_generator import (
    NavigationAction,
    PBIRGenerationResult,
    VisualSpec,
    generate_definition_pbir,
    generate_default_theme,
    generate_page_json,
    generate_pbir,
    generate_platform_json,
    generate_report_json,
    generate_visual_json,
    map_oac_action,
    write_pbir_to_disk,
)
from src.agents.report.prompt_converter import PBISlicerStyle, SlicerConfig
from src.agents.report.visual_mapper import (
    PBIVisualType,
    VisualFieldMapping,
    ConditionalFormatRule,
    SortConfig,
)


# ---------------------------------------------------------------------------
# Visual JSON generation
# ---------------------------------------------------------------------------


class TestGenerateVisualJSON:
    def test_basic_visual(self):
        spec = VisualSpec(
            name="v001",
            visual_type=PBIVisualType.CLUSTERED_COLUMN,
            position=VisualPosition(x=10, y=20, width=400, height=300),
            field_mappings=[
                VisualFieldMapping(role="Category", table_name="Sales", column_name="Region"),
                VisualFieldMapping(role="Y", table_name="Sales", column_name="Revenue", is_measure=True),
            ],
            title="Revenue by Region",
        )
        vj = generate_visual_json(spec)
        assert vj["name"] == "v001"
        assert vj["visualType"] == "clusteredColumnChart"
        assert vj["position"]["x"] == 10
        assert vj["config"]["singleVisual"]["projections"]["Category"]
        assert vj["config"]["singleVisual"]["projections"]["Y"]
        assert "title" in vj["config"]["singleVisual"].get("vcObjects", {})

    def test_visual_with_sort(self):
        spec = VisualSpec(
            name="v002",
            visual_type=PBIVisualType.TABLE_EX,
            position=VisualPosition(x=0, y=0, width=300, height=200),
            sort_configs=[
                SortConfig(column_name="Revenue", table_name="Sales", direction="descending"),
            ],
        )
        vj = generate_visual_json(spec)
        assert "sort" in vj["config"]["singleVisual"]
        assert vj["config"]["singleVisual"]["sort"][0]["Direction"] == 2  # descending

    def test_visual_with_conditional_format(self):
        spec = VisualSpec(
            name="v003",
            visual_type=PBIVisualType.TABLE_EX,
            position=VisualPosition(x=0, y=0, width=300, height=200),
            conditional_formats=[
                ConditionalFormatRule(
                    column_name="Revenue",
                    rule_type="color",
                    conditions=[{"operator": "greaterThan", "value": 100, "color": "#00FF00"}],
                ),
            ],
        )
        vj = generate_visual_json(spec)
        cf = vj["config"]["singleVisual"]["conditionalFormatting"]
        assert len(cf) == 1
        assert cf[0]["column"] == "Revenue"

    def test_measure_vs_column_refs(self):
        spec = VisualSpec(
            name="v004",
            visual_type=PBIVisualType.CARD,
            position=VisualPosition(x=0, y=0, width=200, height=150),
            field_mappings=[
                VisualFieldMapping(role="Fields", table_name="Sales", column_name="TotalRevenue", is_measure=True),
            ],
        )
        vj = generate_visual_json(spec)
        sel = vj["config"]["singleVisual"]["prototypeQuery"]["Select"]
        assert "Measure" in sel[0]


# ---------------------------------------------------------------------------
# Page JSON
# ---------------------------------------------------------------------------


class TestPageJSON:
    def test_page_config(self):
        page = PBIPage(name="p1", display_name="Overview", width=1280, height=720)
        pj = generate_page_json(page)
        assert pj["name"] == "p1"
        assert pj["displayName"] == "Overview"
        assert pj["width"] == 1280


# ---------------------------------------------------------------------------
# Report JSON
# ---------------------------------------------------------------------------


class TestReportJSON:
    def test_report_structure(self):
        pages = [PBIPage(name="p1", display_name="Page 1")]
        rj = generate_report_json("TestReport", pages)
        assert rj["name"] == "TestReport"
        assert len(rj["sections"]) == 1
        assert "config" in rj


# ---------------------------------------------------------------------------
# Definition PBIR
# ---------------------------------------------------------------------------


class TestDefinitionPBIR:
    def test_definition(self):
        defn = generate_definition_pbir("Report", "model-123", "MyModel")
        assert defn["version"] == "4.0"
        assert defn["datasetReference"]["byConnection"]["name"] == "MyModel"


# ---------------------------------------------------------------------------
# Platform JSON
# ---------------------------------------------------------------------------


class TestPlatformJSON:
    def test_valid_json(self):
        pj = json.loads(generate_platform_json("MyReport"))
        assert pj["metadata"]["type"] == "Report"
        assert pj["metadata"]["displayName"] == "MyReport"


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------


class TestTheme:
    def test_theme_has_colors(self):
        theme = generate_default_theme()
        assert "dataColors" in theme
        assert len(theme["dataColors"]) >= 6


# ---------------------------------------------------------------------------
# Action mapping
# ---------------------------------------------------------------------------


class TestMapOACAction:
    def test_navigate_analysis(self):
        action = map_oac_action({"type": "navigate_to_analysis", "target": "details_page"})
        assert action.action_type == "drillthrough"
        assert action.target_page == "details_page"

    def test_url_action(self):
        action = map_oac_action({"type": "url", "url": "https://example.com"})
        assert action.action_type == "url"
        assert action.target_url == "https://example.com"

    def test_page_navigation(self):
        action = map_oac_action({"type": "page_navigation", "target": "Page2"})
        assert action.action_type == "bookmark"

    def test_filter_action(self):
        action = map_oac_action({"type": "master_detail", "columns": ["Region"]})
        assert action.action_type == "crossFilter"

    def test_unknown_action(self):
        action = map_oac_action({"type": "custom_action"})
        assert len(action.warnings) > 0


# ---------------------------------------------------------------------------
# Full PBIR generation
# ---------------------------------------------------------------------------


class TestGeneratePBIR:
    def test_end_to_end(self):
        pages = [
            PBIPage(
                name="page_0_0",
                display_name="Overview",
                visuals=[
                    VisualPosition(x=10, y=10, width=400, height=300, visual_name="chart1"),
                ],
            ),
        ]
        specs = {
            "chart1": VisualSpec(
                name="v001",
                visual_type=PBIVisualType.CLUSTERED_COLUMN,
                position=VisualPosition(x=10, y=10, width=400, height=300),
                field_mappings=[
                    VisualFieldMapping(role="Category", table_name="Sales", column_name="Region"),
                ],
                title="Revenue by Region",
            ),
        }
        slicers = [
            SlicerConfig(
                title="Region Filter",
                table_name="Sales",
                column_name="Region",
            ),
        ]
        result = generate_pbir(
            report_name="TestReport",
            pages=pages,
            visual_specs=specs,
            slicers=slicers,
        )
        assert isinstance(result, PBIRGenerationResult)
        assert "definition.pbir" in result.files
        assert ".platform" in result.files
        assert "report.json" in result.files
        assert result.page_count == 1
        assert result.visual_count == 1
        assert result.slicer_count == 1

        # Check visual file exists
        visual_files = [k for k in result.files if "visuals/" in k]
        assert len(visual_files) >= 2  # 1 chart + 1 slicer

    def test_no_slicers(self):
        pages = [PBIPage(name="p", display_name="P")]
        result = generate_pbir("R", pages, {})
        assert result.slicer_count == 0

    def test_with_actions(self):
        result = generate_pbir(
            "R",
            [PBIPage(name="p")],
            {},
            actions=[NavigationAction(action_type="drillthrough", target_page="Detail")],
        )
        assert "actions.json" in result.files
        assert result.action_count == 1


class TestWritePBIRToDisk:
    def test_writes_files(self, tmp_path: Path):
        pages = [
            PBIPage(
                name="page_0_0",
                display_name="Main",
                visuals=[VisualPosition(x=0, y=0, width=400, height=300, visual_name="c1")],
            ),
        ]
        specs = {
            "c1": VisualSpec(
                name="v001",
                visual_type=PBIVisualType.CLUSTERED_COLUMN,
                position=VisualPosition(x=0, y=0, width=400, height=300),
            ),
        }
        result = generate_pbir("Report", pages, specs)
        out = tmp_path / "report_output"
        write_pbir_to_disk(result, out)

        assert (out / "definition.pbir").exists()
        assert (out / "report.json").exists()
        assert (out / ".platform").exists()
        assert (out / "StaticResources" / "SharedResources" / "BaseThemes" / "CY24SU06.json").exists()
