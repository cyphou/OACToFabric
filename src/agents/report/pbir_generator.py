"""PBIR generator — assemble Power BI Report folder structure.

Generates the full PBIR (Power BI Report) folder structure from
translated OAC analyses/dashboards.

Output structure::

    ReportName.Report/
    ├── definition.pbir
    ├── report.json
    ├── StaticResources/
    │   └── SharedResources/
    │       └── BaseThemes/
    │           └── CY24SU06.json
    ├── pages/
    │   ├── page1/
    │   │   └── visuals/
    │   │       ├── visual1.json
    │   │       └── visual2.json
    │   └── page2/
    │       └── visuals/
    │           └── ...
    └── .platform
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .layout_engine import PBIPage, VisualPosition
from .prompt_converter import SlicerConfig, slicer_to_visual_json
from .visual_mapper import (
    PBIVisualType,
    VisualFieldMapping,
    ConditionalFormatRule,
    SortConfig,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Visual JSON generation
# ---------------------------------------------------------------------------


def _visual_id() -> str:
    return str(uuid.uuid4()).replace("-", "")[:16]


@dataclass
class VisualSpec:
    """Full specification of a PBI visual for JSON generation."""

    name: str                                   # unique visual id
    visual_type: PBIVisualType
    position: VisualPosition
    field_mappings: list[VisualFieldMapping] = field(default_factory=list)
    title: str = ""
    conditional_formats: list[ConditionalFormatRule] = field(default_factory=list)
    sort_configs: list[SortConfig] = field(default_factory=list)
    format_overrides: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def generate_visual_json(spec: VisualSpec) -> dict[str, Any]:
    """Generate the PBI visual JSON config for a single visual."""
    # Build prototype query
    selects: list[dict[str, Any]] = []
    for fm in spec.field_mappings:
        column_ref: dict[str, Any]
        if fm.is_measure:
            column_ref = {
                "Measure": {
                    "Expression": {"SourceRef": {"Entity": fm.table_name}},
                    "Property": fm.column_name,
                },
                "Name": f"{fm.table_name}.{fm.column_name}",
            }
        else:
            column_ref = {
                "Column": {
                    "Expression": {"SourceRef": {"Entity": fm.table_name}},
                    "Property": fm.column_name,
                },
                "Name": f"{fm.table_name}.{fm.column_name}",
            }
        selects.append(column_ref)

    # Build data role mappings
    data_roles: dict[str, list[dict[str, Any]]] = {}
    for fm in spec.field_mappings:
        bind = {
            "queryRef": f"{fm.table_name}.{fm.column_name}",
        }
        data_roles.setdefault(fm.role, []).append(bind)

    # Sort configuration
    sorts: list[dict[str, Any]] = []
    for sc in spec.sort_configs:
        sorts.append({
            "Column": {
                "Expression": {"SourceRef": {"Entity": sc.table_name}},
                "Property": sc.column_name,
            },
            "Direction": 1 if sc.direction == "ascending" else 2,
        })

    visual: dict[str, Any] = {
        "name": spec.name,
        "visualType": spec.visual_type.value,
        "position": {
            "x": spec.position.x,
            "y": spec.position.y,
            "width": spec.position.width,
            "height": spec.position.height,
        },
        "config": {
            "singleVisual": {
                "visualType": spec.visual_type.value,
                "projections": data_roles,
                "prototypeQuery": {
                    "Select": selects,
                },
            },
        },
    }

    if spec.title:
        visual["config"]["singleVisual"]["vcObjects"] = {
            "title": [
                {
                    "properties": {
                        "text": {"expr": {"Literal": {"Value": f"'{spec.title}'"}}},
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                    }
                }
            ]
        }

    if sorts:
        visual["config"]["singleVisual"]["sort"] = sorts

    # Conditional formatting
    if spec.conditional_formats:
        rules: list[dict[str, Any]] = []
        for cf in spec.conditional_formats:
            rules.append({
                "column": cf.column_name,
                "ruleType": cf.rule_type,
                "conditions": cf.conditions,
            })
        visual["config"]["singleVisual"]["conditionalFormatting"] = rules

    return visual


# ---------------------------------------------------------------------------
# Page JSON generation
# ---------------------------------------------------------------------------


def generate_page_json(page: PBIPage) -> dict[str, Any]:
    """Generate the PBI page configuration JSON."""
    return {
        "name": page.name,
        "displayName": page.display_name,
        "displayOption": 0,     # FitToPage
        "width": page.width,
        "height": page.height,
    }


# ---------------------------------------------------------------------------
# Report-level JSON
# ---------------------------------------------------------------------------


def generate_report_json(
    report_name: str,
    pages: list[PBIPage],
    theme_name: str = "CY24SU06",
) -> dict[str, Any]:
    """Generate the report.json (report-level definition)."""
    page_configs = [generate_page_json(p) for p in pages]
    return {
        "id": str(uuid.uuid4()),
        "reportId": str(uuid.uuid4()),
        "name": report_name,
        "config": json.dumps({
            "version": "5.55",
            "themeCollection": {
                "baseTheme": {
                    "name": theme_name,
                    "reportVersionAtImport": "5.55",
                    "type": 2,
                }
            },
            "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
        }),
        "sections": page_configs,
        "resourcePackages": [
            {
                "resourcePackage": {
                    "name": "SharedResources",
                    "type": 2,
                    "items": [
                        {
                            "type": 202,
                            "path": f"BaseThemes/{theme_name}.json",
                        }
                    ],
                }
            }
        ],
    }


def generate_definition_pbir(
    report_name: str,
    semantic_model_id: str = "",
    semantic_model_name: str = "SemanticModel",
) -> dict[str, Any]:
    """Generate the definition.pbir metadata file."""
    return {
        "version": "4.0",
        "datasetReference": {
            "byPath": None,
            "byConnection": {
                "connectionString": None,
                "pbiServiceModelId": semantic_model_id or None,
                "pbiModelVirtualServerName": "sobe_wowvirtualserver",
                "pbiModelDatabaseName": semantic_model_id or str(uuid.uuid4()),
                "name": semantic_model_name,
                "connectionType": "pbiServiceXmlaStyleLive",
            },
        },
    }


def generate_platform_json(report_name: str = "Report") -> str:
    """Generate the .platform config file for Git integration."""
    config = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "Report",
            "displayName": report_name,
        },
        "config": {
            "version": "2.0",
            "logicalId": str(uuid.uuid4()),
        },
    }
    return json.dumps(config, indent=2)


def generate_default_theme() -> dict[str, Any]:
    """Generate a minimal PBI theme JSON."""
    return {
        "name": "CY24SU06",
        "dataColors": [
            "#4472C4", "#ED7D31", "#A5A5A5",
            "#FFC000", "#5B9BD5", "#70AD47",
            "#264478", "#9B57A0", "#636363",
        ],
        "background": "#FFFFFF",
        "foreground": "#252423",
        "tableAccent": "#4472C4",
    }


# ---------------------------------------------------------------------------
# OAC action / navigation mapping
# ---------------------------------------------------------------------------


@dataclass
class NavigationAction:
    """A translated OAC dashboard action → PBI interaction."""

    action_type: str                # drillthrough | url | bookmark | crossFilter
    source_visual: str = ""
    target_page: str = ""
    target_url: str = ""
    bookmark_name: str = ""
    context_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def map_oac_action(action_meta: dict[str, Any]) -> NavigationAction:
    """Map an OAC dashboard action to a PBI interaction type."""
    action_type = action_meta.get("type", "").lower()
    warnings: list[str] = []

    if action_type in ("navigate_to_analysis", "navigate_analysis", "drill"):
        return NavigationAction(
            action_type="drillthrough",
            source_visual=action_meta.get("source", ""),
            target_page=action_meta.get("target", ""),
            context_columns=action_meta.get("context_columns", []),
        )

    if action_type in ("navigate_to_url", "url", "link"):
        return NavigationAction(
            action_type="url",
            source_visual=action_meta.get("source", ""),
            target_url=action_meta.get("url", ""),
        )

    if action_type in ("navigate_to_page", "page_navigation", "page"):
        return NavigationAction(
            action_type="bookmark",
            source_visual=action_meta.get("source", ""),
            target_page=action_meta.get("target", ""),
            bookmark_name=action_meta.get("target", ""),
        )

    if action_type in ("filter", "master_detail"):
        return NavigationAction(
            action_type="crossFilter",
            source_visual=action_meta.get("source", ""),
            context_columns=action_meta.get("columns", []),
        )

    warnings.append(f"Unknown action type '{action_type}' — flagged for manual review")
    return NavigationAction(
        action_type="crossFilter",
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Full PBIR generation pipeline
# ---------------------------------------------------------------------------


@dataclass
class PBIRGenerationResult:
    """Result of generating the complete PBIR folder structure."""

    files: dict[str, str]               # relative path → JSON string content
    page_count: int = 0
    visual_count: int = 0
    slicer_count: int = 0
    action_count: int = 0
    warnings: list[str] = field(default_factory=list)
    review_items: list[dict[str, Any]] = field(default_factory=list)


def generate_pbir(
    report_name: str,
    pages: list[PBIPage],
    visual_specs: dict[str, VisualSpec],
    slicers: list[SlicerConfig] | None = None,
    actions: list[NavigationAction] | None = None,
    semantic_model_id: str = "",
    semantic_model_name: str = "SemanticModel",
) -> PBIRGenerationResult:
    """Generate the complete PBIR file set.

    Parameters
    ----------
    report_name : str
        Name for the report.
    pages : list[PBIPage]
        Computed page layouts with visual positions.
    visual_specs : dict[str, VisualSpec]
        visual_name → VisualSpec for chart visuals.
    slicers : list[SlicerConfig]
        Slicer visuals to include.
    actions : list[NavigationAction]
        Translated navigation actions.
    semantic_model_id, semantic_model_name : str
        Semantic model reference.
    """
    files: dict[str, str] = {}
    warnings: list[str] = []
    review_items: list[dict[str, Any]] = []
    visual_count = 0
    slicer_count = 0

    # 1. definition.pbir
    files["definition.pbir"] = json.dumps(
        generate_definition_pbir(report_name, semantic_model_id, semantic_model_name),
        indent=2,
    )

    # 2. .platform
    files[".platform"] = generate_platform_json(report_name)

    # 3. Theme
    files["StaticResources/SharedResources/BaseThemes/CY24SU06.json"] = json.dumps(
        generate_default_theme(), indent=2,
    )

    # 4. Pages and visuals
    for page in pages:
        page_dir = f"pages/{page.name}"

        # Generate visuals for this page
        for vpos in page.visuals:
            spec = visual_specs.get(vpos.visual_name)
            if spec:
                spec.position = vpos
                vj = generate_visual_json(spec)
                files[f"{page_dir}/visuals/{spec.name}.json"] = json.dumps(vj, indent=2)
                visual_count += 1

                for w in spec.warnings:
                    review_items.append({
                        "type": "visual",
                        "page": page.display_name,
                        "visual": spec.title or spec.name,
                        "warning": w,
                    })

    # 5. Slicers (placed on first page)
    if slicers and pages:
        first_page_dir = f"pages/{pages[0].name}"
        for slicer in slicers:
            sj = slicer_to_visual_json(slicer)
            files[f"{first_page_dir}/visuals/{slicer.visual_id}.json"] = json.dumps(sj, indent=2)
            slicer_count += 1

            for w in slicer.warnings:
                review_items.append({
                    "type": "slicer",
                    "page": pages[0].display_name,
                    "slicer": slicer.title,
                    "warning": w,
                })

    # 6. Report.json
    files["report.json"] = json.dumps(
        generate_report_json(report_name, pages),
        indent=2,
    )

    # 7. Actions metadata (for reference / deployment scripts)
    action_list = actions or []
    if action_list:
        action_data = [
            {
                "type": a.action_type,
                "source": a.source_visual,
                "target_page": a.target_page,
                "target_url": a.target_url,
                "bookmark": a.bookmark_name,
                "context": a.context_columns,
            }
            for a in action_list
        ]
        files["actions.json"] = json.dumps(action_data, indent=2)

    result = PBIRGenerationResult(
        files=files,
        page_count=len(pages),
        visual_count=visual_count,
        slicer_count=slicer_count,
        action_count=len(action_list),
        warnings=warnings,
        review_items=review_items,
    )

    logger.info(
        "PBIR generated: %d pages, %d visuals, %d slicers, %d files",
        result.page_count, result.visual_count, result.slicer_count, len(files),
    )
    return result


def write_pbir_to_disk(result: PBIRGenerationResult, output_dir: Path) -> None:
    """Write generated PBIR files to the filesystem."""
    for rel_path, content in result.files.items():
        full_path = output_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
    logger.info("Wrote %d PBIR files to %s", len(result.files), output_dir)


# ---------------------------------------------------------------------------
# Drill-through wiring (Phase 49)
# ---------------------------------------------------------------------------


def wire_drillthrough(
    visual_json: dict[str, Any],
    target_page_name: str,
    context_columns: list[str],
) -> dict[str, Any]:
    """Wire drill-through navigation into a visual's JSON config.

    Adds the drillthrough action to the visual's ``vcObjects`` so that
    clicking the visual navigates to the target page with filter context.

    Args:
        visual_json: Existing visual JSON dict
        target_page_name: Name of the drillthrough target page
        context_columns: Columns that provide filter context

    Returns:
        Updated visual JSON dict with drillthrough config
    """
    drillthrough_config = {
        "drillthrough": [{
            "action": {
                "type": "drillthrough",
                "targetPage": target_page_name,
            },
            "filterColumns": [
                {"column": col} for col in context_columns
            ],
        }]
    }

    config = visual_json.get("config", {})
    if isinstance(config, str):
        config = json.loads(config)
    vc_objects = config.get("singleVisual", {}).get("vcObjects", {})
    vc_objects["drillthrough"] = drillthrough_config["drillthrough"]
    config.setdefault("singleVisual", {})["vcObjects"] = vc_objects
    visual_json["config"] = config
    return visual_json


def generate_drillthrough_page(
    page_name: str,
    display_name: str,
    filter_columns: list[dict[str, str]],
) -> dict[str, Any]:
    """Generate a drillthrough target page configuration.

    Args:
        page_name: Internal page name
        display_name: Display name for the page
        filter_columns: List of dicts with table/column for drillthrough filters

    Returns:
        Page config dict with drillthrough settings
    """
    return {
        "name": page_name,
        "displayName": display_name,
        "displayOption": 1,
        "width": 1280,
        "height": 720,
        "config": json.dumps({
            "isDrillthrough": True,
            "drivethroughFilters": [
                {
                    "table": fc.get("table", ""),
                    "column": fc.get("column", ""),
                }
                for fc in filter_columns
            ],
        }),
    }


# ---------------------------------------------------------------------------
# What-If parameter wiring (Phase 49)
# ---------------------------------------------------------------------------


def generate_whatif_slicer(
    param_name: str,
    min_value: float = 0,
    max_value: float = 100,
    step: float = 1,
    default_value: float = 50,
) -> dict[str, Any]:
    """Generate a What-If parameter slicer visual JSON.

    Creates a numeric range slicer backed by a What-If parameter table.

    Args:
        param_name: Parameter name (also the table name)
        min_value: Minimum slider value
        max_value: Maximum slider value
        step: Step increment
        default_value: Default slider position

    Returns:
        Visual JSON dict for the What-If slicer
    """
    vid = str(uuid.uuid4()).replace("-", "")[:16]
    return {
        "name": vid,
        "visual": {
            "visualType": "slicer",
            "objects": {
                "general": [{"properties": {"orientation": {"expr": {"Literal": {"Value": "0D"}}}}}],
                "data": [{
                    "properties": {
                        "mode": {"expr": {"Literal": {"Value": "'Basic'"}}},
                    }
                }],
                "numericInputStyle": [{
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                    }
                }],
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": "p", "Entity": param_name, "Type": 0}],
                "Select": [{
                    "Column": {"Expression": {"SourceRef": {"Source": "p"}}, "Property": f"{param_name} Value"},
                    "Name": f"{param_name}.{param_name} Value",
                }],
            },
        },
        "position": {"x": 0, "y": 0, "width": 300, "height": 60},
        "metadata": {
            "whatIfParameter": {
                "name": param_name,
                "min": min_value,
                "max": max_value,
                "step": step,
                "default": default_value,
            }
        },
    }


def generate_whatif_tmdl(
    param_name: str,
    min_value: float = 0,
    max_value: float = 100,
    step: float = 1,
    default_value: float = 50,
) -> str:
    """Generate TMDL for a What-If parameter table.

    Args:
        param_name: Clean parameter name
        min_value, max_value, step, default_value: Range parameters

    Returns:
        TMDL table definition string
    """
    import hashlib
    tag = hashlib.md5(param_name.encode()).hexdigest()[:8]  # noqa: S324

    return (
        f"table '{param_name}'\n"
        f"\tlineageTag: {tag}\n\n"
        f"\tcolumn '{param_name} Value'\n"
        f"\t\tdataType: double\n"
        f"\t\tlineageTag: {hashlib.md5(f'{param_name}.val'.encode()).hexdigest()[:8]}\n"  # noqa: S324
        f"\t\tsummarizeBy: none\n"
        f"\t\tisNameInferred: true\n"
        f"\t\tsourceColumn: [{param_name} Value]\n\n"
        f"\tmeasure '{param_name} Value' = SELECTEDVALUE('{param_name}'[{param_name} Value], {default_value})\n"
        f"\t\tformatString: 0.00\n"
        f"\t\tlineageTag: {hashlib.md5(f'{param_name}.measure'.encode()).hexdigest()[:8]}\n\n"  # noqa: S324
        f"\tpartition '{param_name}' = calculated\n"
        f"\t\tmode: import\n"
        f"\t\tsource =\n"
        f"\t\t\tGENERATESERIES({min_value}, {max_value}, {step})\n"
    )


# ---------------------------------------------------------------------------
# Tooltip page generation (Phase 49)
# ---------------------------------------------------------------------------


def generate_tooltip_page(
    page_name: str,
    display_name: str,
    tooltip_visuals: list[dict[str, Any]] | None = None,
    width: int = 320,
    height: int = 240,
) -> dict[str, Any]:
    """Generate a tooltip page configuration.

    Tooltip pages are smaller PBI pages that appear on hover over a visual.

    Args:
        page_name: Internal page name
        display_name: Display name
        tooltip_visuals: Optional list of visual configs to place on the tooltip page
        width: Tooltip page width (default 320px)
        height: Tooltip page height (default 240px)

    Returns:
        Page config dict for a tooltip page
    """
    return {
        "name": page_name,
        "displayName": display_name,
        "displayOption": 1,
        "width": width,
        "height": height,
        "config": json.dumps({
            "visibility": 1,  # hidden from page tab
            "tooltip": {
                "type": "ReportPage",
                "enabled": True,
            },
        }),
        "visuals": tooltip_visuals or [],
    }


def wire_tooltip_to_visual(
    visual_json: dict[str, Any],
    tooltip_page_name: str,
) -> dict[str, Any]:
    """Wire a tooltip page reference into a visual's config.

    Args:
        visual_json: Existing visual JSON
        tooltip_page_name: Name of the tooltip page to show on hover

    Returns:
        Updated visual JSON with tooltip page reference
    """
    config = visual_json.get("config", {})
    if isinstance(config, str):
        config = json.loads(config)
    sv = config.setdefault("singleVisual", {})
    vc = sv.setdefault("vcObjects", {})
    vc["tooltip"] = [{
        "properties": {
            "page": {"expr": {"Literal": {"Value": f"'{tooltip_page_name}'"}}},
            "type": {"expr": {"Literal": {"Value": "'ReportPage'"}}},
        }
    }]
    visual_json["config"] = config
    return visual_json


# ---------------------------------------------------------------------------
# Auto-refresh configuration (Phase 49)
# ---------------------------------------------------------------------------


def set_auto_refresh(
    report_json: dict[str, Any],
    interval_seconds: int = 30,
    enabled: bool = True,
) -> dict[str, Any]:
    """Set automatic page refresh interval in report.json.

    Args:
        report_json: Report configuration dict
        interval_seconds: Refresh interval in seconds (min 1, typically 30+)
        enabled: Whether auto-refresh is enabled

    Returns:
        Updated report_json with auto-refresh setting
    """
    config = report_json.get("config", "{}")
    if isinstance(config, str):
        config = json.loads(config)

    config["autoRefresh"] = {
        "enabled": enabled,
        "intervalMs": max(1000, interval_seconds * 1000),
        "type": "ChangeDetection",
    }

    report_json["config"] = json.dumps(config) if isinstance(report_json.get("config"), str) else config
    return report_json
