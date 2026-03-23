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
