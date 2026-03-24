#!/usr/bin/env python3
"""Run a full migration test against example sample files and generate a report.

Executes the complete migration pipeline:
  1. Discovery  — parse all example RPD/Essbase/Cognos/Qlik/Tableau files
  2. Schema     — generate Fabric DDL from discovered physical tables
  3. Semantic   — build SemanticModelIR and generate TMDL
  4. Report     — visual mapping, prompt→slicer conversion, PBIR generation
  5. Security   — role mapping (OAC→Fabric), RLS/OLS conversion
  6. ETL        — data flow step mapping to Fabric pipeline activities
  7. Validation — run Agent 07 validation suite with test-case generation
  8. Report     — produce HTML + Markdown migration reports

Usage::

    python scripts/run_migration_test.py
    python scripts/run_migration_test.py --output-dir output/migration_report
    python scripts/run_migration_test.py --samples examples/oac_samples/complex_enterprise.xml
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.discovery.rpd_parser import RPDParser
from src.agents.etl.dataflow_parser import DataFlow, DataFlowStep, StepType
from src.agents.etl.step_mapper import map_step
from src.agents.report.layout_engine import PBIPage, VisualPosition
from src.agents.report.pbir_generator import (
    PBIRGenerationResult,
    VisualSpec,
    generate_pbir,
    write_pbir_to_disk,
)
from src.agents.report.prompt_converter import (
    SlicerConfig,
    convert_all_prompts,
)
from src.agents.report.visual_mapper import map_visual_type
from src.agents.schema.ddl_generator import generate_create_table
from src.agents.schema.type_mapper import TargetPlatform
from src.agents.security.rls_converter import render_roles_tmdl
from src.agents.security.role_mapper import (
    map_roles,
    parse_oac_role,
)
from src.agents.semantic.rpd_model_parser import parse_inventory_to_ir
from src.agents.semantic.tmdl_generator import generate_tmdl
from src.agents.validation.validation_agent import ValidationAgent
from src.core.models import (
    AssetType,
    Inventory,
    InventoryItem,
    MigrationScope,
)

from html_report_generator import (
    ETLMappingEntry,
    PromptMappingEntry,
    ReportData,
    SecurityMappingEntry,
    VisualMappingEntry,
    generate_html_report,
)

logger = logging.getLogger("migration_test")


# ---------------------------------------------------------------------------
# Connector parsers (lightweight wrappers)
# ---------------------------------------------------------------------------

def discover_oac_sample(xml_path: Path) -> list[InventoryItem]:
    """Parse an OAC RPD XML sample and return inventory items."""
    parser = RPDParser(xml_path)
    return parser.parse()


def discover_essbase_sample(xml_path: Path) -> list[InventoryItem]:
    """Parse an Essbase outline XML and return inventory items."""
    from xml.etree import ElementTree as ET

    tree = ET.parse(xml_path)  # noqa: S314
    root = tree.getroot()
    items: list[InventoryItem] = []

    for dim in root.findall(".//dimension"):
        dim_name = dim.get("name", "unknown")
        dim_type = dim.get("type", "regular")
        storage = dim.get("storageType", "sparse")

        members = []
        for member in dim.iter("member"):
            m_name = member.get("name", "")
            m_formula = member.get("formula", "")
            m_storage = member.get("storageType", "store")
            members.append({
                "name": m_name,
                "formula": m_formula,
                "storageType": m_storage,
                "consolidation": member.get("consolidation", "+"),
            })

        items.append(
            InventoryItem(
                id=f"essbase_dim__{dim_name.lower()}",
                asset_type=AssetType.LOGICAL_TABLE,
                source_path=f"/essbase/{xml_path.stem}/{dim_name}",
                name=dim_name,
                metadata={
                    "dimension_type": dim_type,
                    "storage_type": storage,
                    "members": members,
                    "member_count": len(members),
                    "columns": [{"name": m["name"], "expression": m["formula"]} for m in members if m["formula"]],
                    "hierarchies": [{"name": f"{dim_name}Hierarchy", "levels": [m["name"] for m in members[:5]]}],
                },
                source="essbase",
            )
        )
    return items


def discover_cognos_sample(xml_path: Path) -> list[InventoryItem]:
    """Parse a Cognos report spec XML and return inventory items."""
    from xml.etree import ElementTree as ET

    tree = ET.parse(xml_path)  # noqa: S314
    root = tree.getroot()
    items: list[InventoryItem] = []
    report_name = root.get("name", xml_path.stem)

    for query in root.findall(".//query"):
        q_name = query.get("name", "unnamed")
        data_items = []
        for di in query.findall(".//dataItem"):
            data_items.append({
                "name": di.get("name", ""),
                "label": di.get("label", ""),
                "aggregate": di.get("aggregate", "none"),
                "expression": (di.find("expression").text if di.find("expression") is not None else ""),
            })
        items.append(
            InventoryItem(
                id=f"cognos_query__{q_name.lower()}",
                asset_type=AssetType.DATA_MODEL,
                source_path=f"/cognos/{report_name}/{q_name}",
                name=q_name,
                metadata={
                    "data_items": data_items,
                    "measures": [
                        {"name": d["name"], "expression": d["expression"], "aggregation": d["aggregate"]}
                        for d in data_items if d["aggregate"] not in ("none", "")
                    ],
                },
                source="cognos",
            )
        )

    for page in root.findall(".//page"):
        p_name = page.get("name", "unnamed")
        visuals = []
        for vis_tag in ("list", "crosstab", "chart", "repeater", "map"):
            for vis in page.findall(f".//{vis_tag}"):
                visuals.append({
                    "type": vis_tag,
                    "name": vis.get("name", ""),
                    "refQuery": vis.get("refQuery", ""),
                })
        items.append(
            InventoryItem(
                id=f"cognos_page__{p_name.lower().replace(' ', '_')}",
                asset_type=AssetType.ANALYSIS,
                source_path=f"/cognos/{report_name}/{p_name}",
                name=f"{report_name} — {p_name}",
                metadata={"name": f"{report_name} — {p_name}", "visuals": visuals, "visual_count": len(visuals)},
                source="cognos",
            )
        )

    for prompt_tag in ("selectValue", "datePrompt", "textBoxPrompt", "treePrompt"):
        for prompt in root.findall(f".//{prompt_tag}"):
            items.append(
                InventoryItem(
                    id=f"cognos_prompt__{prompt.get('paramName', 'p').lower()}",
                    asset_type=AssetType.PROMPT,
                    source_path=f"/cognos/{report_name}/prompts/{prompt.get('paramName', '')}",
                    name=prompt.get("caption", prompt.get("name", "")),
                    metadata={
                        "type": prompt_tag,
                        "paramName": prompt.get("paramName", ""),
                        "required": prompt.get("required", "false"),
                    },
                    source="cognos",
                )
            )
    return items


def discover_qlik_sample(script_path: Path) -> list[InventoryItem]:
    """Parse a Qlik load script and return inventory items."""
    import re

    text = script_path.read_text(encoding="utf-8")
    items: list[InventoryItem] = []

    # Variables
    for match in re.finditer(r"(?:LET|SET)\s+(\w+)\s*=\s*(.+?);", text, re.IGNORECASE):
        items.append(
            InventoryItem(
                id=f"qlik_var__{match.group(1).lower()}",
                asset_type=AssetType.FILTER,
                source_path=f"/qlik/{script_path.stem}/variables/{match.group(1)}",
                name=match.group(1),
                metadata={"value": match.group(2).strip()},
                source="qlik",
            )
        )

    # LOAD statements — find table alias
    load_pattern = re.compile(
        r"(?:(\w+):)?\s*(?:NOCONCATENATE\s+)?LOAD\s+(.+?)\s+"
        r"(?:FROM|RESIDENT|INLINE)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in load_pattern.finditer(text):
        alias = match.group(1) or "unnamed_load"
        field_text = match.group(2)
        fields = [f.strip().split(" AS ")[-1].strip() for f in field_text.split(",") if f.strip()]
        items.append(
            InventoryItem(
                id=f"qlik_table__{alias.lower()}",
                asset_type=AssetType.PHYSICAL_TABLE,
                source_path=f"/qlik/{script_path.stem}/{alias}",
                name=alias,
                metadata={
                    "columns": [{"name": f, "data_type": "VARCHAR"} for f in fields[:20]],
                    "field_count": len(fields),
                },
                source="qlik",
            )
        )

    # SQL SELECT
    sql_pattern = re.compile(
        r"SQL\s+SELECT\s+(.+?)\s+FROM\s+(\S+)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in sql_pattern.finditer(text):
        table_name = match.group(2).split(".")[-1]
        field_text = match.group(1)
        fields = [f.strip().split(".")[-1] for f in field_text.split(",") if f.strip()]
        items.append(
            InventoryItem(
                id=f"qlik_sql__{table_name.lower()}",
                asset_type=AssetType.PHYSICAL_TABLE,
                source_path=f"/qlik/{script_path.stem}/{table_name}",
                name=table_name,
                metadata={
                    "columns": [{"name": f, "data_type": "VARCHAR"} for f in fields[:20]],
                    "source": "sql",
                },
                source="qlik",
            )
        )
    return items


def discover_tableau_sample(twb_path: Path) -> list[InventoryItem]:
    """Parse a Tableau TWB XML and return inventory items."""
    from xml.etree import ElementTree as ET

    tree = ET.parse(twb_path)  # noqa: S314
    root = tree.getroot()
    items: list[InventoryItem] = []

    for ds in root.findall(".//datasource"):
        ds_name = ds.get("name", "")
        if ds_name == "Parameters":
            # Parameters datasource
            for col in ds.findall(".//column"):
                calc = col.find("calculation")
                items.append(
                    InventoryItem(
                        id=f"tableau_param__{col.get('name', '').lower()}",
                        asset_type=AssetType.PROMPT,
                        source_path=f"/tableau/{twb_path.stem}/parameters/{col.get('name', '')}",
                        name=col.get("caption", col.get("name", "")),
                        metadata={
                            "datatype": col.get("datatype", ""),
                            "formula": calc.get("formula", "") if calc is not None else "",
                        },
                        source="tableau",
                    )
                )
            continue

        caption = ds.get("caption", ds_name)
        columns = []
        calc_fields = []
        for col in ds.findall(".//column"):
            col_data = {
                "name": col.get("name", ""),
                "caption": col.get("caption", ""),
                "datatype": col.get("datatype", ""),
                "role": col.get("role", ""),
            }
            calc = col.find("calculation")
            if calc is not None:
                col_data["formula"] = calc.get("formula", "")
                calc_fields.append(col_data)
            columns.append(col_data)

        connections = []
        for conn in ds.findall(".//connection"):
            connections.append({
                "class": conn.get("class", ""),
                "server": conn.get("server", ""),
                "dbname": conn.get("dbname", ""),
            })

        items.append(
            InventoryItem(
                id=f"tableau_ds__{ds_name.lower().replace(' ', '_')}",
                asset_type=AssetType.LOGICAL_TABLE,
                source_path=f"/tableau/{twb_path.stem}/{ds_name}",
                name=caption,
                metadata={
                    "columns": [
                        {"name": c["name"], "data_type": c.get("datatype", ""), "expression": c.get("formula", "")}
                        for c in columns
                    ],
                    "calculated_fields": calc_fields,
                    "connections": connections,
                    "hierarchies": [],
                },
                source="tableau",
            )
        )

    for ws in root.findall(".//worksheet"):
        ws_name = ws.get("name", "")
        mark = ws.find(".//mark")
        items.append(
            InventoryItem(
                id=f"tableau_ws__{ws_name.lower().replace(' ', '_')}",
                asset_type=AssetType.ANALYSIS,
                source_path=f"/tableau/{twb_path.stem}/worksheets/{ws_name}",
                name=ws_name,
                metadata={
                    "name": ws_name,
                    "mark_type": mark.get("class", "") if mark is not None else "",
                },
                source="tableau",
            )
        )

    for dash in root.findall(".//dashboard"):
        dash_name = dash.get("name", "")
        zones = [z.get("name", "") for z in dash.findall(".//zone")]
        items.append(
            InventoryItem(
                id=f"tableau_dash__{dash_name.lower().replace(' ', '_')}",
                asset_type=AssetType.DASHBOARD,
                source_path=f"/tableau/{twb_path.stem}/dashboards/{dash_name}",
                name=dash_name,
                metadata={"name": dash_name, "zones": zones, "zone_count": len(zones)},
                source="tableau",
            )
        )
    return items


# ---------------------------------------------------------------------------
# Schema migration (DDL generation)
# ---------------------------------------------------------------------------

def generate_ddl_for_items(items: list[InventoryItem], platform: TargetPlatform) -> list[dict[str, str]]:
    """Generate CREATE TABLE DDL for physical table items."""
    results = []
    for item in items:
        if item.asset_type != AssetType.PHYSICAL_TABLE:
            continue
        columns = item.metadata.get("columns", [])
        if not columns:
            continue
        ddl = generate_create_table(
            table_name=item.name,
            columns=columns,
            platform=platform,
        )
        results.append({"table": item.name, "ddl": ddl, "source": item.source})
    return results


# ---------------------------------------------------------------------------
# Report / Visual migration (Agent 05)
# ---------------------------------------------------------------------------

def run_visual_mapping(items: list[InventoryItem]) -> tuple[list[VisualMappingEntry], list[dict]]:
    """Map OAC/Cognos/Tableau visual types to Power BI visuals."""
    mappings: list[VisualMappingEntry] = []
    type_counts: dict[str, VisualMappingEntry] = {}
    visual_specs: list[dict] = []

    for item in items:
        if item.asset_type not in (AssetType.ANALYSIS, AssetType.DASHBOARD):
            continue
        meta = dict(item.metadata)

        # determine source chart types
        chart_types: list[str] = []
        if "mark_type" in meta and meta["mark_type"]:
            chart_types.append(meta["mark_type"])
        for vis in meta.get("visuals", []):
            vtype = vis.get("type", "")
            if vtype:
                chart_types.append(vtype)
        if meta.get("zones"):
            chart_types.append("dashboard")
        if not chart_types:
            chart_types.append("table")

        for ct in chart_types:
            pbi_type, warnings = map_visual_type(ct)
            key = f"{ct}→{pbi_type.value}"
            if key in type_counts:
                type_counts[key].count += 1
            else:
                entry = VisualMappingEntry(
                    source_type=ct,
                    pbi_type=pbi_type.value,
                    count=1,
                    warnings=warnings,
                )
                type_counts[key] = entry
            visual_specs.append({
                "name": item.name,
                "source_type": ct,
                "pbi_type": pbi_type.value,
                "source": item.source,
            })

    mappings = list(type_counts.values())
    return mappings, visual_specs


def run_prompt_conversion(items: list[InventoryItem]) -> tuple[list[PromptMappingEntry], list[SlicerConfig]]:
    """Convert prompts to PBI slicers."""
    prompt_metas: list[dict] = []
    for item in items:
        if item.asset_type != AssetType.PROMPT:
            continue
        meta = dict(item.metadata)
        meta.setdefault("name", item.name)
        prompt_metas.append(meta)

    slicers_raw = convert_all_prompts(prompt_metas)
    entries: list[PromptMappingEntry] = []
    slicers: list[SlicerConfig] = []

    for pm, raw_result in zip(prompt_metas, slicers_raw):
        if isinstance(raw_result, SlicerConfig):
            slicers.append(raw_result)
            entries.append(PromptMappingEntry(
                name=pm.get("name", ""),
                source_type=pm.get("type", "unknown"),
                pbi_type=f"Slicer ({raw_result.slicer_style.value})",
                source=pm.get("source", ""),
            ))
        else:
            entries.append(PromptMappingEntry(
                name=pm.get("name", ""),
                source_type=pm.get("type", "unknown"),
                pbi_type="What-If Parameter",
                source=pm.get("source", ""),
            ))

    return entries, slicers


def run_pbir_generation(
    items: list[InventoryItem],
    visual_specs_data: list[dict],
    slicers: list[SlicerConfig],
) -> PBIRGenerationResult | None:
    """Generate PBIR report structure."""
    analyses = [i for i in items if i.asset_type in (AssetType.ANALYSIS, AssetType.DASHBOARD)]
    if not analyses:
        return None

    # Build pages from analysis items
    pages: list[PBIPage] = []
    specs: dict[str, VisualSpec] = {}

    for idx, item in enumerate(analyses):
        positions: list[VisualPosition] = []
        meta = dict(item.metadata)
        visuals_meta = meta.get("visuals", [])

        for vi, vis_data in enumerate(visuals_meta):
            vname = f"{item.name}_{vi}"
            vtype = vis_data.get("type", "table")
            pbi_type, _ = map_visual_type(vtype)
            col = vi % 3
            row = vi // 3
            positions.append(VisualPosition(
                x=col * 420 + 10,
                y=row * 260 + 10,
                width=400,
                height=240,
                page_index=idx,
                visual_name=vname,
                visual_type=pbi_type.value,
            ))
            specs[vname] = VisualSpec(
                name=vname,
                title=vis_data.get("name", vname),
                visual_type=pbi_type,
                position=positions[-1],
            )

        if not positions and meta.get("mark_type"):
            vname = f"{item.name}_main"
            pbi_type, _ = map_visual_type(meta["mark_type"])
            positions.append(VisualPosition(
                x=10, y=10, width=1260, height=700,
                page_index=idx, visual_name=vname, visual_type=pbi_type.value,
            ))
            specs[vname] = VisualSpec(name=vname, title=item.name, visual_type=pbi_type, position=positions[-1])

        page = PBIPage(
            name=f"Page_{idx + 1}",
            display_name=item.name[:40],
            page_index=idx,
            visuals=positions,
        )
        pages.append(page)

    if not pages:
        return None

    return generate_pbir(
        report_name="MigrationReport",
        pages=pages,
        visual_specs=specs,
        slicers=slicers,
    )


# ---------------------------------------------------------------------------
# Security migration (Agent 06)
# ---------------------------------------------------------------------------

def run_security_mapping(items: list[InventoryItem]) -> tuple[list[SecurityMappingEntry], str]:
    """Map security roles and generate RLS TMDL."""
    role_items = [i for i in items if i.asset_type == AssetType.SECURITY_ROLE]
    if not role_items:
        return [], ""

    oac_roles = [parse_oac_role(dict(item.metadata) | {"name": item.name}) for item in role_items]
    result = map_roles(oac_roles)

    entries: list[SecurityMappingEntry] = []
    for ws_assign in result.workspace_assignments:
        matching_rls = [r for r in result.rls_roles if r.role_name == ws_assign.role_name]
        rls_count = sum(len(r.table_permissions) for r in matching_rls)
        entries.append(SecurityMappingEntry(
            oac_role=ws_assign.role_name,
            fabric_role=ws_assign.workspace_role.value,
            rls_filters=rls_count,
            ols_columns=0,
            aad_group=ws_assign.aad_group,
        ))

    # generate RLS TMDL
    rls_tmdl = render_roles_tmdl(result.rls_roles) if result.rls_roles else ""

    return entries, rls_tmdl


# ---------------------------------------------------------------------------
# ETL migration (Agent 03)
# ---------------------------------------------------------------------------

def build_synthetic_dataflows(items: list[InventoryItem]) -> list[DataFlow]:
    """Build synthetic data flow definitions from discovered physical tables.

    Since the sample files don't include OAC Data Flow XML, we create
    representative data flows showing what the migration would produce.
    """
    flows: list[DataFlow] = []

    # group physical tables by source
    by_source: dict[str, list[InventoryItem]] = {}
    for item in items:
        if item.asset_type == AssetType.PHYSICAL_TABLE:
            by_source.setdefault(item.source, []).append(item)

    for source, tables in by_source.items():
        steps: list[DataFlowStep] = []
        for idx, table_item in enumerate(tables):
            # Source step
            steps.append(DataFlowStep(
                id=f"{source}_{table_item.name}_src",
                name=f"Read_{table_item.name}",
                step_type=StepType.SOURCE_DB,
                order=idx * 3,
                source_table=table_item.name,
            ))
            # Filter step (if table has many columns)
            cols = table_item.metadata.get("columns", [])
            if len(cols) > 5:
                steps.append(DataFlowStep(
                    id=f"{source}_{table_item.name}_filter",
                    name=f"Filter_{table_item.name}",
                    step_type=StepType.FILTER,
                    order=idx * 3 + 1,
                    filter_expression=f"WHERE {cols[0].get('name', 'id')} IS NOT NULL",
                ))
            # Target step
            steps.append(DataFlowStep(
                id=f"{source}_{table_item.name}_tgt",
                name=f"Write_{table_item.name}",
                step_type=StepType.TARGET_DB,
                order=idx * 3 + 2,
                target_table=table_item.name,
            ))

        flows.append(DataFlow(
            id=f"flow_{source}",
            name=f"{source.upper()} Data Load",
            description=f"Load {len(tables)} tables from {source}",
            steps=steps,
        ))

    return flows


def run_etl_mapping(items: list[InventoryItem]) -> list[ETLMappingEntry]:
    """Map ETL data flow steps to Fabric pipeline activities."""
    flows = build_synthetic_dataflows(items)
    entries: list[ETLMappingEntry] = []

    for flow in flows:
        for step in flow.steps:
            mapped = map_step(step)
            entries.append(ETLMappingEntry(
                step_name=step.name,
                source_type=step.step_type.value,
                fabric_target=mapped.fabric_type,
                warnings=[mapped.review_reason] if mapped.requires_review else [],
            ))

    return entries


# ---------------------------------------------------------------------------
# Report generator (Markdown — kept for backward compatibility)
# ---------------------------------------------------------------------------

def generate_migration_report(
    *,
    all_items: list[InventoryItem],
    ddl_results: list[dict[str, str]],
    tmdl_result: dict | None,
    validation_result: dict | None,
    elapsed_seconds: float,
    output_dir: Path,
) -> str:
    """Generate a comprehensive Markdown migration report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # --- Asset breakdown ---
    by_type: dict[str, list[InventoryItem]] = {}
    by_source: dict[str, list[InventoryItem]] = {}
    for item in all_items:
        by_type.setdefault(item.asset_type.value, []).append(item)
        by_source.setdefault(item.source, []).append(item)

    lines = [
        "# Migration Report",
        "",
        f"> **Generated:** {now}  ",
        f"> **Total assets discovered:** {len(all_items)}  ",
        f"> **Elapsed time:** {elapsed_seconds:.1f}s  ",
        f"> **Output directory:** `{output_dir}`",
        "",
        "---",
        "",
        "## 1. Discovery Summary",
        "",
        "### Assets by Source Platform",
        "",
        "| Source | Assets | Types |",
        "|--------|--------|-------|",
    ]
    for source, items in sorted(by_source.items()):
        types = sorted({i.asset_type.value for i in items})
        lines.append(f"| **{source}** | {len(items)} | {', '.join(types)} |")

    lines.extend([
        "",
        "### Assets by Type",
        "",
        "| Asset Type | Count | Sources |",
        "|------------|-------|---------|",
    ])
    for atype, items in sorted(by_type.items()):
        sources = sorted({i.source for i in items})
        lines.append(f"| {atype} | {len(items)} | {', '.join(sources)} |")

    # --- Detailed inventory ---
    lines.extend([
        "",
        "### Full Inventory",
        "",
        "<details>",
        "<summary>Click to expand — all discovered assets</summary>",
        "",
        "| # | Name | Type | Source | Path |",
        "|---|------|------|--------|------|",
    ])
    for i, item in enumerate(all_items, 1):
        lines.append(f"| {i} | {item.name} | {item.asset_type.value} | {item.source} | `{item.source_path}` |")
    lines.extend(["", "</details>", ""])

    # --- Schema migration ---
    lines.extend([
        "---",
        "",
        "## 2. Schema Migration (DDL)",
        "",
        f"**Tables generated:** {len(ddl_results)}",
        "",
    ])
    if ddl_results:
        lines.extend([
            "| # | Table | Source | Platform |",
            "|---|-------|--------|----------|",
        ])
        for i, d in enumerate(ddl_results, 1):
            lines.append(f"| {i} | `{d['table']}` | {d['source']} | Lakehouse (Delta) |")

        lines.extend([
            "",
            "<details>",
            "<summary>Generated DDL statements</summary>",
            "",
        ])
        for d in ddl_results:
            lines.extend([
                f"#### `{d['table']}`",
                "",
                "```sql",
                d["ddl"].strip(),
                "```",
                "",
            ])
        lines.extend(["</details>", ""])

    # --- Semantic model ---
    lines.extend([
        "---",
        "",
        "## 3. Semantic Model (TMDL)",
        "",
    ])
    if tmdl_result:
        files = tmdl_result.get("files", {})
        translations = tmdl_result.get("translation_log", [])
        warnings = tmdl_result.get("warnings", [])
        review = tmdl_result.get("review_items", [])

        lines.extend([
            f"**TMDL files generated:** {len(files)}  ",
            f"**Expressions translated:** {len(translations)}  ",
            f"**Warnings:** {len(warnings)}  ",
            f"**Items requiring review:** {len(review)}",
            "",
        ])

        if files:
            lines.extend([
                "### Generated Files",
                "",
                "| File | Size (chars) |",
                "|------|-------------|",
            ])
            for fname, content in sorted(files.items()):
                lines.append(f"| `{fname}` | {len(content):,} |")

        if translations:
            lines.extend([
                "",
                "### Expression Translations",
                "",
                "| # | Source Expression | DAX Output | Confidence |",
                "|---|-----------------|------------|------------|",
            ])
            for i, tx in enumerate(translations, 1):
                src = tx.original_expression[:60] + ("…" if len(tx.original_expression) > 60 else "")
                dax = tx.dax_expression[:60] + ("…" if len(tx.dax_expression) > 60 else "")
                conf = f"{tx.confidence:.0%}"
                lines.append(f"| {i} | `{src}` | `{dax}` | {conf} |")

        if review:
            lines.extend([
                "",
                "### Items Requiring Review",
                "",
                "| Type | Table | Column/Hierarchy | Reason |",
                "|------|-------|------------------|--------|",
            ])
            for r in review:
                lines.append(
                    f"| {r.get('type', '')} | {r.get('table', '')} | "
                    f"{r.get('column', r.get('hierarchy', ''))} | {r.get('reason', '')} |"
                )

        lines.extend([
            "",
            "<details>",
            "<summary>TMDL file contents</summary>",
            "",
        ])
        for fname, content in sorted(files.items()):
            lines.extend([
                f"#### `{fname}`",
                "",
                "```",
                content.strip(),
                "```",
                "",
            ])
        lines.extend(["</details>", ""])
    else:
        lines.append("_No logical tables found — TMDL generation skipped._\n")

    # --- Validation ---
    lines.extend([
        "---",
        "",
        "## 4. Validation",
        "",
    ])
    if validation_result:
        lines.extend([
            f"**Layers validated:** {validation_result.get('succeeded', 0)}/4  ",
            f"**Errors:** {len(validation_result.get('errors', []))}",
            "",
            "Detailed reports written to:",
            "",
            "- `data_reconciliation_report.md`",
            "- `semantic_validation_report.md`",
            "- `report_validation_report.md`",
            "- `security_validation_report.md`",
            "- `validation_summary.md`",
            "- `reconciliation_queries.sql`",
            "",
        ])
    else:
        lines.append("_Validation not run._\n")

    # --- Summary ---
    physical = len(by_type.get("physicalTable", []))
    logical = len(by_type.get("logicalTable", []))
    analyses = len(by_type.get("analysis", []))
    dashboards = len(by_type.get("dashboard", []))
    security = len(by_type.get("securityRole", []))
    prompts = len(by_type.get("prompt", []))

    lines.extend([
        "---",
        "",
        "## 5. Migration Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total assets discovered | **{len(all_items)}** |",
        f"| Physical tables | {physical} |",
        f"| Logical tables / dimensions | {logical} |",
        f"| Analyses / worksheets | {analyses} |",
        f"| Dashboards | {dashboards} |",
        f"| Security roles | {security} |",
        f"| Prompts / parameters | {prompts} |",
        f"| DDL statements generated | {len(ddl_results)} |",
        f"| TMDL files generated | {len(tmdl_result.get('files', {})) if tmdl_result else 0} |",
        f"| Expressions translated | {len(tmdl_result.get('translation_log', [])) if tmdl_result else 0} |",
        f"| Elapsed time | {elapsed_seconds:.1f}s |",
        "",
        "---",
        "",
        "*Report generated by OAC-to-Fabric Migration Accelerator*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_migration(
    samples_dir: Path,
    output_dir: Path,
    specific_files: list[Path] | None = None,
) -> None:
    """Run the full migration pipeline against sample files."""
    start = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print("  OAC-to-Fabric Migration Test")
    print(f"{'='*70}\n")

    # ── Step 1: Discovery ──────────────────────────────────────────────
    print("[1/8] Discovery — parsing sample files...")
    all_items: list[InventoryItem] = []

    if specific_files:
        file_list = specific_files
    else:
        file_list = sorted(samples_dir.rglob("*"))

    for fpath in file_list:
        if not fpath.is_file():
            continue
        try:
            if fpath.suffix == ".xml" and "oac_samples" in str(fpath):
                items = discover_oac_sample(fpath)
                print(f"  ✓ OAC RPD:  {fpath.name} → {len(items)} items")
                all_items.extend(items)
            elif fpath.suffix == ".xml" and "essbase_samples" in str(fpath):
                items = discover_essbase_sample(fpath)
                print(f"  ✓ Essbase:  {fpath.name} → {len(items)} items")
                all_items.extend(items)
            elif fpath.suffix == ".xml" and "cognos_samples" in str(fpath):
                items = discover_cognos_sample(fpath)
                print(f"  ✓ Cognos:   {fpath.name} → {len(items)} items")
                all_items.extend(items)
            elif fpath.suffix == ".qvs":
                items = discover_qlik_sample(fpath)
                print(f"  ✓ Qlik:     {fpath.name} → {len(items)} items")
                all_items.extend(items)
            elif fpath.suffix == ".twb":
                items = discover_tableau_sample(fpath)
                print(f"  ✓ Tableau:  {fpath.name} → {len(items)} items")
                all_items.extend(items)
        except Exception as exc:
            print(f"  ✗ {fpath.name}: {exc}")

    print(f"\n  Total discovered: {len(all_items)} assets\n")

    # ── Step 2: Schema migration ───────────────────────────────────────
    print("[2/8] Schema — generating DDL...")
    ddl_results = generate_ddl_for_items(all_items, TargetPlatform.LAKEHOUSE)
    print(f"  Generated {len(ddl_results)} CREATE TABLE statements\n")

    if ddl_results:
        ddl_content = "\n\n".join(d["ddl"] for d in ddl_results)
        (output_dir / "generated_ddl.sql").write_text(ddl_content, encoding="utf-8")

    # ── Step 3: Semantic model ─────────────────────────────────────────
    print("[3/8] Semantic — building TMDL model...")
    tmdl_result_dict: dict | None = None
    inventory = Inventory(items=all_items)
    try:
        ir = parse_inventory_to_ir(inventory)
        if ir.tables:
            result = generate_tmdl(ir, lakehouse_name="MigrationLakehouse")
            tmdl_result_dict = {
                "files": result.files,
                "translation_log": result.translation_log,
                "warnings": result.warnings,
                "review_items": result.review_items,
            }
            print(f"  Generated {len(result.files)} TMDL files")
            print(f"  Translated {len(result.translation_log)} expressions")
            if result.review_items:
                print(f"  ⚠ {len(result.review_items)} items need review")

            # Write TMDL files
            tmdl_dir = output_dir / "SemanticModel"
            tmdl_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in result.files.items():
                fpath = tmdl_dir / fname
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(content, encoding="utf-8")
        else:
            print("  No logical tables found — skipping TMDL generation")
    except Exception as exc:
        print(f"  ✗ TMDL generation error: {exc}")
    print()

    # ── Step 4: Report / Visual migration ──────────────────────────────
    print("[4/8] Report — visual mapping & PBIR generation...")
    visual_mappings, visual_specs_data = run_visual_mapping(all_items)
    prompt_entries, slicers = run_prompt_conversion(all_items)
    pbir_result: PBIRGenerationResult | None = None
    try:
        pbir_result = run_pbir_generation(all_items, visual_specs_data, slicers)
        if pbir_result:
            print(f"  Mapped {len(visual_mappings)} visual types")
            print(f"  Converted {len(prompt_entries)} prompts → slicers")
            print(f"  Generated {pbir_result.page_count} PBIR pages, {pbir_result.visual_count} visuals")
            # Write PBIR files
            pbir_dir = output_dir / "PBIR"
            write_pbir_to_disk(pbir_result, pbir_dir)
        else:
            print("  No analyses/dashboards found — skipping PBIR generation")
    except Exception as exc:
        print(f"  ✗ PBIR generation error: {exc}")
    print()

    # ── Step 5: Security migration ─────────────────────────────────────
    print("[5/8] Security — role mapping & RLS conversion...")
    security_entries, rls_tmdl = run_security_mapping(all_items)
    if security_entries:
        print(f"  Mapped {len(security_entries)} security roles")
        if rls_tmdl:
            (output_dir / "rls_roles.tmdl").write_text(rls_tmdl, encoding="utf-8")
            print(f"  Generated RLS TMDL ({len(rls_tmdl)} chars)")
    else:
        print("  No security roles found")
    print()

    # ── Step 6: ETL migration ──────────────────────────────────────────
    print("[6/8] ETL — data flow step mapping...")
    etl_entries = run_etl_mapping(all_items)
    if etl_entries:
        print(f"  Mapped {len(etl_entries)} ETL steps to Fabric activities")
        notebooks = sum(1 for e in etl_entries if "notebook" in e.fabric_target.lower())
        copies = sum(1 for e in etl_entries if "copy" in e.fabric_target.lower())
        print(f"  → {copies} Copy Activities, {notebooks} Notebooks")
    else:
        print("  No physical tables for ETL mapping")
    print()

    # ── Step 7: Validation ─────────────────────────────────────────────
    print("[7/8] Validation — running Agent 07...")
    validation_result_dict: dict | None = None
    try:
        val_dir = output_dir / "validation"
        agent = ValidationAgent(output_dir=val_dir)
        scope = MigrationScope(include_paths=["/"])
        val_inventory = await agent.discover(scope)

        val_inventory = Inventory(items=all_items)
        plan = await agent.plan(val_inventory)
        result = await agent.execute(plan)
        validation_result_dict = {
            "succeeded": result.succeeded,
            "failed": result.failed,
            "errors": result.errors,
        }
        print(f"  Validation layers: {result.succeeded}/4 succeeded")
        if result.errors:
            for err in result.errors:
                print(f"  ⚠ {err}")
    except Exception as exc:
        print(f"  ✗ Validation error: {exc}")
    print()

    # ── Step 8: Generate reports ───────────────────────────────────────
    elapsed = time.perf_counter() - start
    print("[8/8] Report — generating migration reports...")

    # -- Build report data for HTML --
    by_type: dict[str, int] = {}
    by_source: dict[str, int] = {}
    items_dicts: list[dict] = []
    for item in all_items:
        by_type[item.asset_type.value] = by_type.get(item.asset_type.value, 0) + 1
        by_source[item.source] = by_source.get(item.source, 0) + 1
        items_dicts.append({
            "name": item.name,
            "asset_type": item.asset_type.value,
            "source": item.source,
            "source_path": item.source_path,
        })

    translations_dicts: list[dict] = []
    if tmdl_result_dict:
        for tx in tmdl_result_dict.get("translation_log", []):
            translations_dicts.append({
                "original": tx.original_expression,
                "dax": tx.dax_expression,
                "confidence": tx.confidence,
                "method": tx.method,
            })

    rd = ReportData(
        items=items_dicts,
        by_source=by_source,
        by_type=by_type,
        ddl_results=ddl_results,
        tmdl_files=tmdl_result_dict.get("files", {}) if tmdl_result_dict else {},
        translations=translations_dicts,
        review_items=tmdl_result_dict.get("review_items", []) if tmdl_result_dict else [],
        visual_mappings=visual_mappings,
        prompt_mappings=prompt_entries,
        pbir_pages=pbir_result.page_count if pbir_result else 0,
        pbir_visuals=pbir_result.visual_count if pbir_result else 0,
        security_mappings=security_entries,
        rls_rules_tmdl=rls_tmdl,
        etl_mappings=etl_entries,
        validation_layers=validation_result_dict.get("succeeded", 0) if validation_result_dict else 0,
        validation_total=4,
        validation_errors=validation_result_dict.get("errors", []) if validation_result_dict else [],
        elapsed_seconds=elapsed,
        output_dir=str(output_dir),
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    # HTML report
    html_content = generate_html_report(rd)
    html_path = output_dir / "migration_report.html"
    html_path.write_text(html_content, encoding="utf-8")

    # Markdown report (backward compat)
    md_content = generate_migration_report(
        all_items=all_items,
        ddl_results=ddl_results,
        tmdl_result=tmdl_result_dict,
        validation_result=validation_result_dict,
        elapsed_seconds=elapsed,
        output_dir=output_dir,
    )
    md_path = output_dir / "migration_report.md"
    md_path.write_text(md_content, encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"  Migration test complete!")
    print(f"{'='*70}")
    print(f"\n  HTML Report: {html_path}")
    print(f"  MD Report:   {md_path}")
    print(f"  Output dir:  {output_dir}")
    print(f"  Elapsed:     {elapsed:.1f}s")
    print(f"  Assets:      {len(all_items)} discovered")
    print(f"  DDL:         {len(ddl_results)} tables")
    if tmdl_result_dict:
        print(f"  TMDL:        {len(tmdl_result_dict['files'])} files")
        print(f"  Translated:  {len(tmdl_result_dict['translation_log'])} expressions")
    print(f"  Visuals:     {len(visual_mappings)} types mapped")
    print(f"  Prompts:     {len(prompt_entries)} → slicers")
    print(f"  Security:    {len(security_entries)} roles")
    print(f"  ETL steps:   {len(etl_entries)} mapped")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run migration test against example sample files",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("output/migration_report"),
        help="Output directory (default: output/migration_report)",
    )
    parser.add_argument(
        "--samples",
        type=Path,
        nargs="*",
        help="Specific sample files to process (default: all examples/)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    samples_dir = PROJECT_ROOT / "examples"
    specific = [Path(s) for s in args.samples] if args.samples else None

    asyncio.run(run_migration(samples_dir, args.output_dir, specific))


if __name__ == "__main__":
    main()
