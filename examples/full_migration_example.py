#!/usr/bin/env python3
"""Full migration example — OAC → Fabric & Power BI with HTML report.

Demonstrates the complete 8-step migration pipeline using the built-in
sample files.  Produces a self-contained HTML report, Markdown report,
TMDL semantic model, PBIR report structure, DDL scripts, and validation
results — all from static example files with **no live connections**.

Usage::

    # Run with defaults (all samples → output/migration_report)
    python examples/full_migration_example.py

    # Specify output directory
    python examples/full_migration_example.py -o output/my_report

    # Single source file
    python examples/full_migration_example.py --samples examples/oac_samples/complex_enterprise.xml

    # Programmatic usage
    from examples.full_migration_example import run_full_migration
    result = await run_full_migration()
    print(result.summary())
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is importable regardless of execution context
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Agent imports ──────────────────────────────────────────────────────
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
from src.agents.report.prompt_converter import SlicerConfig, convert_all_prompts
from src.agents.report.visual_mapper import map_visual_type
from src.agents.schema.ddl_generator import generate_create_table
from src.agents.schema.type_mapper import TargetPlatform
from src.agents.security.rls_converter import render_roles_tmdl
from src.agents.security.role_mapper import map_roles, parse_oac_role
from src.agents.semantic.rpd_model_parser import parse_inventory_to_ir
from src.agents.semantic.tmdl_generator import generate_tmdl
from src.agents.validation.validation_agent import ValidationAgent
from src.core.models import AssetType, Inventory, InventoryItem, MigrationScope

logger = logging.getLogger(__name__)

# Default directories
EXAMPLES_DIR = _PROJECT_ROOT / "examples"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "output" / "migration_report"


# ═══════════════════════════════════════════════════════════════════════
# Result container
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class MigrationResult:
    """Aggregated result of a full migration run."""

    # Discovery
    items: list[InventoryItem] = field(default_factory=list)
    by_source: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)

    # Schema
    ddl_results: list[dict[str, str]] = field(default_factory=list)

    # Semantic
    tmdl_files: dict[str, str] = field(default_factory=dict)
    translations: list[dict[str, Any]] = field(default_factory=list)
    review_items: list[dict[str, Any]] = field(default_factory=list)

    # Report
    visual_mappings: list[dict[str, Any]] = field(default_factory=list)
    prompt_mappings: list[dict[str, Any]] = field(default_factory=list)
    pbir_pages: int = 0
    pbir_visuals: int = 0

    # Security
    security_mappings: list[dict[str, Any]] = field(default_factory=list)
    rls_tmdl: str = ""

    # ETL
    etl_mappings: list[dict[str, Any]] = field(default_factory=list)

    # Validation
    validation_passed: int = 0
    validation_total: int = 4
    validation_errors: list[str] = field(default_factory=list)

    # Meta
    elapsed_seconds: float = 0.0
    output_dir: str = ""
    html_report_path: str = ""
    md_report_path: str = ""

    def summary(self) -> str:
        """Return a concise multi-line summary string."""
        lines = [
            f"Migration complete in {self.elapsed_seconds:.1f}s",
            f"  Assets discovered:  {len(self.items)}",
            f"  Source platforms:    {len(self.by_source)} ({', '.join(sorted(self.by_source))})",
            f"  DDL tables:         {len(self.ddl_results)}",
            f"  TMDL files:         {len(self.tmdl_files)}",
            f"  Expressions:        {len(self.translations)}",
            f"  Visual types:       {len(self.visual_mappings)}",
            f"  Prompts -> slicers: {len(self.prompt_mappings)}",
            f"  PBIR pages/visuals: {self.pbir_pages}/{self.pbir_visuals}",
            f"  Security roles:     {len(self.security_mappings)}",
            f"  ETL steps:          {len(self.etl_mappings)}",
            f"  Validation:         {self.validation_passed}/{self.validation_total}",
            f"  HTML report:        {self.html_report_path}",
        ]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# Source parsers (per connector)
# ═══════════════════════════════════════════════════════════════════════


def _parse_oac(xml_path: Path) -> list[InventoryItem]:
    parser = RPDParser(xml_path)
    return parser.parse()


def _parse_essbase(xml_path: Path) -> list[InventoryItem]:
    from xml.etree import ElementTree as ET

    tree = ET.parse(xml_path)  # noqa: S314 — trusted local samples
    root = tree.getroot()
    items: list[InventoryItem] = []
    for dim in root.findall(".//dimension"):
        dim_name = dim.get("name", "unknown")
        members = []
        for member in dim.iter("member"):
            members.append({
                "name": member.get("name", ""),
                "formula": member.get("formula", ""),
                "storageType": member.get("storageType", "store"),
                "consolidation": member.get("consolidation", "+"),
            })
        items.append(InventoryItem(
            id=f"essbase_dim__{dim_name.lower()}",
            asset_type=AssetType.LOGICAL_TABLE,
            source_path=f"/essbase/{xml_path.stem}/{dim_name}",
            name=dim_name,
            metadata={
                "dimension_type": dim.get("type", "regular"),
                "storage_type": dim.get("storageType", "sparse"),
                "members": members,
                "member_count": len(members),
                "columns": [
                    {"name": m["name"], "expression": m["formula"]}
                    for m in members
                    if m["formula"]
                ],
                "hierarchies": [
                    {"name": f"{dim_name}Hierarchy", "levels": [m["name"] for m in members[:5]]}
                ],
            },
            source="essbase",
        ))
    return items


def _parse_cognos(xml_path: Path) -> list[InventoryItem]:
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
        items.append(InventoryItem(
            id=f"cognos_query__{q_name.lower()}",
            asset_type=AssetType.DATA_MODEL,
            source_path=f"/cognos/{report_name}/{q_name}",
            name=q_name,
            metadata={
                "data_items": data_items,
                "measures": [
                    {"name": d["name"], "expression": d["expression"], "aggregation": d["aggregate"]}
                    for d in data_items
                    if d["aggregate"] not in ("none", "")
                ],
            },
            source="cognos",
        ))

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
        items.append(InventoryItem(
            id=f"cognos_page__{p_name.lower().replace(' ', '_')}",
            asset_type=AssetType.ANALYSIS,
            source_path=f"/cognos/{report_name}/{p_name}",
            name=f"{report_name} — {p_name}",
            metadata={"name": f"{report_name} — {p_name}", "visuals": visuals, "visual_count": len(visuals)},
            source="cognos",
        ))

    for prompt_tag in ("selectValue", "datePrompt", "textBoxPrompt", "treePrompt"):
        for prompt in root.findall(f".//{prompt_tag}"):
            items.append(InventoryItem(
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
            ))
    return items


def _parse_qlik(script_path: Path) -> list[InventoryItem]:
    import re

    text = script_path.read_text(encoding="utf-8")
    items: list[InventoryItem] = []

    for match in re.finditer(r"(?:LET|SET)\s+(\w+)\s*=\s*(.+?);", text, re.IGNORECASE):
        items.append(InventoryItem(
            id=f"qlik_var__{match.group(1).lower()}",
            asset_type=AssetType.FILTER,
            source_path=f"/qlik/{script_path.stem}/variables/{match.group(1)}",
            name=match.group(1),
            metadata={"value": match.group(2).strip()},
            source="qlik",
        ))

    load_pattern = re.compile(
        r"(?:(\w+):)?\s*(?:NOCONCATENATE\s+)?LOAD\s+(.+?)\s+(?:FROM|RESIDENT|INLINE)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in load_pattern.finditer(text):
        alias = match.group(1) or "unnamed_load"
        field_text = match.group(2)
        fields = [f.strip().split(" AS ")[-1].strip() for f in field_text.split(",") if f.strip()]
        items.append(InventoryItem(
            id=f"qlik_table__{alias.lower()}",
            asset_type=AssetType.PHYSICAL_TABLE,
            source_path=f"/qlik/{script_path.stem}/{alias}",
            name=alias,
            metadata={
                "columns": [{"name": f, "data_type": "VARCHAR"} for f in fields[:20]],
                "field_count": len(fields),
            },
            source="qlik",
        ))

    sql_pattern = re.compile(
        r"SQL\s+SELECT\s+(.+?)\s+FROM\s+(\S+)", re.IGNORECASE | re.DOTALL
    )
    for match in sql_pattern.finditer(text):
        table_name = match.group(2).split(".")[-1]
        field_text = match.group(1)
        fields = [f.strip().split(".")[-1] for f in field_text.split(",") if f.strip()]
        items.append(InventoryItem(
            id=f"qlik_sql__{table_name.lower()}",
            asset_type=AssetType.PHYSICAL_TABLE,
            source_path=f"/qlik/{script_path.stem}/{table_name}",
            name=table_name,
            metadata={
                "columns": [{"name": f, "data_type": "VARCHAR"} for f in fields[:20]],
                "source": "sql",
            },
            source="qlik",
        ))
    return items


def _parse_oac_json(json_path: Path) -> list[InventoryItem]:
    """Parse an OAC REST API JSON sample and return inventory items."""
    import json as _json

    with open(json_path, encoding="utf-8") as fh:
        data = _json.load(fh)

    items: list[InventoryItem] = []
    fname = json_path.stem

    # Catalog response — list of mixed asset types
    if "items" in data and isinstance(data["items"], list):
        for raw in data["items"]:
            asset_type_str = raw.get("type", "")
            type_map = {
                "analysis": AssetType.ANALYSIS,
                "dashboard": AssetType.DASHBOARD,
                "dataModel": AssetType.DATA_MODEL,
                "prompt": AssetType.PROMPT,
                "filter": AssetType.FILTER,
                "agent": AssetType.AGENT_ALERT,
                "dataflow": AssetType.DATA_FLOW,
            }
            atype = type_map.get(asset_type_str)
            if not atype:
                continue
            path = raw.get("path", f"/{asset_type_str}/{raw.get('name', '')}")
            items.append(InventoryItem(
                id=f"oac_{asset_type_str}__{path.replace('/', '__').lower()}",
                asset_type=atype,
                source_path=path,
                name=raw.get("name", ""),
                owner=raw.get("owner", ""),
                metadata={
                    k: raw[k]
                    for k in ("columns", "filters", "prompts", "pages", "steps",
                              "subjectAreas", "embeddedContent", "caption")
                    if k in raw
                },
                source="oac_api",
            ))
        return items

    # Single analysis definition
    if data.get("type") == "analysis" or "criteria" in data:
        vis_list = data.get("visualizations", [])
        items.append(InventoryItem(
            id=f"oac_analysis__{fname.lower()}",
            asset_type=AssetType.ANALYSIS,
            source_path=data.get("path", f"/oac/{fname}"),
            name=data.get("name", fname),
            owner=data.get("owner", ""),
            metadata={
                "name": data.get("name", fname),
                "visuals": [
                    {"type": v.get("type", "table"), "name": v.get("title", v.get("id", ""))}
                    for v in vis_list
                ],
                "visual_count": len(vis_list),
                "criteria": data.get("criteria", []),
                "columns": [
                    {"name": c.get("name", ""), "expression": c.get("expression", ""),
                     "data_type": c.get("dataType", "VARCHAR")}
                    for criteria in data.get("criteria", [])
                    for c in criteria.get("columns", [])
                ],
                "filters": data.get("criteria", [{}])[0].get("filters", []) if data.get("criteria") else [],
                "actionLinks": data.get("actionLinks", []),
            },
            source="oac_api",
        ))
        return items

    # Dashboard definition
    if data.get("type") == "dashboard" or "embeddedContent" in data:
        pages = data.get("pages", [])
        embedded = data.get("embeddedContent", [])
        items.append(InventoryItem(
            id=f"oac_dashboard__{fname.lower()}",
            asset_type=AssetType.DASHBOARD,
            source_path=data.get("path", f"/oac/{fname}"),
            name=data.get("name", fname),
            owner=data.get("owner", ""),
            metadata={
                "name": data.get("name", fname),
                "pages": pages,
                "zones": [p.get("name", "") for p in pages],
                "zone_count": len(pages),
                "embeddedContent": embedded,
                "embedded_analyses": [e.get("path", "") for e in embedded],
            },
            source="oac_api",
        ))
        return items

    # Data flow definitions
    if "steps" in data and data.get("id", "").startswith("df-"):
        items.append(InventoryItem(
            id=f"oac_dataflow__{fname.lower()}",
            asset_type=AssetType.DATA_FLOW,
            source_path=data.get("path", f"/oac/{fname}"),
            name=data.get("name", fname),
            metadata={
                "steps": data.get("steps", []),
                "parameters": data.get("parameters", []),
                "schedule": data.get("schedule", {}),
            },
            source="oac_api",
        ))
        return items

    # Data model definition
    if "tables" in data and "joins" in data:
        for tbl in data.get("tables", []):
            tbl_name = tbl.get("name", "")
            is_fact = tbl.get("type") == "fact"
            cols = tbl.get("columns", [])
            items.append(InventoryItem(
                id=f"oac_table__{tbl_name.lower().replace(' ', '_')}",
                asset_type=AssetType.PHYSICAL_TABLE if is_fact else AssetType.LOGICAL_TABLE,
                source_path=f"/oac/{fname}/{tbl_name}",
                name=tbl_name,
                metadata={
                    "columns": [
                        {"name": c.get("name", ""), "data_type": c.get("dataType", "VARCHAR"),
                         "expression": c.get("expression", "")}
                        for c in cols
                    ],
                    "hierarchies": tbl.get("hierarchies", []),
                    "table_type": tbl.get("type", "dimension"),
                },
                source="oac_api",
            ))
        return items

    # Agent/alert definitions
    if "agents" in data:
        for agent in data.get("agents", []):
            items.append(InventoryItem(
                id=f"oac_agent__{agent.get('name', '').lower().replace(' ', '_')}",
                asset_type=AssetType.AGENT_ALERT,
                source_path=agent.get("path", f"/oac/agents/{agent.get('name', '')}"),
                name=agent.get("name", ""),
                metadata={
                    "condition": agent.get("condition", {}),
                    "schedule": agent.get("schedule", {}),
                    "actions": agent.get("actions", []),
                    "priority": agent.get("priority", "medium"),
                },
                source="oac_api",
            ))
        return items

    # Prompt definitions
    if "prompts" in data:
        for prompt in data.get("prompts", []):
            items.append(InventoryItem(
                id=f"oac_prompt__{prompt.get('name', '').lower().replace(' ', '_')}",
                asset_type=AssetType.PROMPT,
                source_path=prompt.get("path", f"/oac/prompts/{prompt.get('name', '')}"),
                name=prompt.get("name", ""),
                metadata={
                    "type": prompt.get("promptType", "columnValue"),
                    "column": prompt.get("column", ""),
                    "multiSelect": prompt.get("multiSelect", False),
                    "required": prompt.get("required", False),
                    "dataType": prompt.get("dataType", "varchar"),
                },
                source="oac_api",
            ))
        return items

    # Filter definitions
    if "filters" in data:
        for filt in data.get("filters", []):
            items.append(InventoryItem(
                id=f"oac_filter__{filt.get('name', '').lower().replace(' ', '_')}",
                asset_type=AssetType.FILTER,
                source_path=filt.get("path", f"/oac/filters/{filt.get('name', '')}"),
                name=filt.get("name", ""),
                metadata={
                    "conditions": filt.get("conditions", []),
                    "scope": filt.get("scope", "shared"),
                },
                source="oac_api",
            ))
        return items

    # Connections
    if "items" not in data and any("host" in item for item in data.get("items", data.get("connections", []))):
        pass  # handled by catalog above

    # Fallback: try items list with host field (connections)
    conn_items = data if isinstance(data, list) else data.get("items", [])
    if isinstance(conn_items, list) and conn_items and "host" in conn_items[0]:
        for conn in conn_items:
            items.append(InventoryItem(
                id=f"oac_connection__{conn.get('name', '').lower().replace(' ', '_')}",
                asset_type=AssetType.CONNECTION,
                source_path=f"/connections/{conn.get('name', '')}",
                name=conn.get("name", ""),
                metadata={
                    "type": conn.get("type", ""),
                    "host": conn.get("host", ""),
                    "port": conn.get("port"),
                    "database": conn.get("database", ""),
                },
                source="oac_api",
            ))
        return items

    return items


def _parse_tableau(twb_path: Path) -> list[InventoryItem]:
    from xml.etree import ElementTree as ET

    tree = ET.parse(twb_path)  # noqa: S314
    root = tree.getroot()
    items: list[InventoryItem] = []

    for ds in root.findall(".//datasource"):
        ds_name = ds.get("name", "")
        if ds_name == "Parameters":
            for col in ds.findall(".//column"):
                calc = col.find("calculation")
                items.append(InventoryItem(
                    id=f"tableau_param__{col.get('name', '').lower()}",
                    asset_type=AssetType.PROMPT,
                    source_path=f"/tableau/{twb_path.stem}/parameters/{col.get('name', '')}",
                    name=col.get("caption", col.get("name", "")),
                    metadata={
                        "datatype": col.get("datatype", ""),
                        "formula": calc.get("formula", "") if calc is not None else "",
                    },
                    source="tableau",
                ))
            continue

        caption = ds.get("caption", ds_name)
        columns, calc_fields, connections = [], [], []
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
        for conn in ds.findall(".//connection"):
            connections.append({
                "class": conn.get("class", ""),
                "server": conn.get("server", ""),
                "dbname": conn.get("dbname", ""),
            })
        items.append(InventoryItem(
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
        ))

    for ws in root.findall(".//worksheet"):
        ws_name = ws.get("name", "")
        mark = ws.find(".//mark")
        items.append(InventoryItem(
            id=f"tableau_ws__{ws_name.lower().replace(' ', '_')}",
            asset_type=AssetType.ANALYSIS,
            source_path=f"/tableau/{twb_path.stem}/worksheets/{ws_name}",
            name=ws_name,
            metadata={
                "name": ws_name,
                "mark_type": mark.get("class", "") if mark is not None else "",
            },
            source="tableau",
        ))

    for dash in root.findall(".//dashboard"):
        dash_name = dash.get("name", "")
        zones = [z.get("name", "") for z in dash.findall(".//zone")]
        items.append(InventoryItem(
            id=f"tableau_dash__{dash_name.lower().replace(' ', '_')}",
            asset_type=AssetType.DASHBOARD,
            source_path=f"/tableau/{twb_path.stem}/dashboards/{dash_name}",
            name=dash_name,
            metadata={"name": dash_name, "zones": zones, "zone_count": len(zones)},
            source="tableau",
        ))
    return items


# ═══════════════════════════════════════════════════════════════════════
# Pipeline steps
# ═══════════════════════════════════════════════════════════════════════

_PARSER_MAP: dict[str, tuple[str, object]] = {
    # (parent_dir_fragment, parser_function)
}


def discover_all(
    samples_dir: Path,
    specific_files: list[Path] | None = None,
) -> list[InventoryItem]:
    """Step 1 — Discover and parse all sample source files."""
    all_items: list[InventoryItem] = []
    file_list = specific_files or sorted(samples_dir.rglob("*"))

    for fpath in file_list:
        if not fpath.is_file():
            continue
        try:
            if fpath.suffix == ".xml" and "oac_samples" in str(fpath):
                all_items.extend(_parse_oac(fpath))
            elif fpath.suffix == ".json" and "oac_samples" in str(fpath):
                all_items.extend(_parse_oac_json(fpath))
            elif fpath.suffix == ".xml" and "essbase_samples" in str(fpath):
                all_items.extend(_parse_essbase(fpath))
            elif fpath.suffix == ".xml" and "cognos_samples" in str(fpath):
                all_items.extend(_parse_cognos(fpath))
            elif fpath.suffix == ".qvs":
                all_items.extend(_parse_qlik(fpath))
            elif fpath.suffix == ".twb":
                all_items.extend(_parse_tableau(fpath))
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", fpath.name, exc)

    return all_items


def generate_schema(
    items: list[InventoryItem],
    platform: TargetPlatform = TargetPlatform.LAKEHOUSE,
) -> list[dict[str, str]]:
    """Step 2 — Generate DDL for all physical tables."""
    results = []
    for item in items:
        if item.asset_type != AssetType.PHYSICAL_TABLE:
            continue
        columns = item.metadata.get("columns", [])
        if not columns:
            continue
        ddl = generate_create_table(table_name=item.name, columns=columns, platform=platform)
        results.append({"table": item.name, "ddl": ddl, "source": item.source})
    return results


def build_semantic_model(
    items: list[InventoryItem],
) -> dict[str, Any] | None:
    """Step 3 — Parse inventory → SemanticModelIR → TMDL."""
    inventory = Inventory(items=items)
    ir = parse_inventory_to_ir(inventory)
    if not ir.tables:
        return None
    result = generate_tmdl(ir, lakehouse_name="MigrationLakehouse")
    return {
        "files": result.files,
        "translation_log": result.translation_log,
        "warnings": result.warnings,
        "review_items": result.review_items,
    }


def map_visuals(
    items: list[InventoryItem],
) -> tuple[list[dict[str, Any]], list[dict]]:
    """Step 4a — Map source visual types → Power BI visuals."""
    type_counts: dict[str, dict] = {}
    specs: list[dict] = []

    for item in items:
        if item.asset_type not in (AssetType.ANALYSIS, AssetType.DASHBOARD):
            continue
        meta = dict(item.metadata)
        chart_types: list[str] = []
        if meta.get("mark_type"):
            chart_types.append(meta["mark_type"])
        for vis in meta.get("visuals", []):
            if vis.get("type"):
                chart_types.append(vis["type"])
        if meta.get("zones"):
            chart_types.append("dashboard")
        if not chart_types:
            chart_types.append("table")

        for ct in chart_types:
            pbi_type, warnings = map_visual_type(ct)
            key = f"{ct}→{pbi_type.value}"
            if key in type_counts:
                type_counts[key]["count"] += 1
            else:
                type_counts[key] = {
                    "source_type": ct,
                    "pbi_type": pbi_type.value,
                    "count": 1,
                    "warnings": warnings,
                }
            specs.append({"name": item.name, "source_type": ct, "pbi_type": pbi_type.value, "source": item.source})

    return list(type_counts.values()), specs


def convert_prompts(
    items: list[InventoryItem],
) -> tuple[list[dict[str, Any]], list[SlicerConfig]]:
    """Step 4b — Convert prompts/parameters → PBI slicers."""
    prompt_metas = []
    for item in items:
        if item.asset_type != AssetType.PROMPT:
            continue
        meta = dict(item.metadata)
        meta.setdefault("name", item.name)
        prompt_metas.append(meta)

    slicers_raw = convert_all_prompts(prompt_metas)
    entries, slicers = [], []
    for pm, raw in zip(prompt_metas, slicers_raw):
        if isinstance(raw, SlicerConfig):
            slicers.append(raw)
            entries.append({
                "name": pm.get("name", ""),
                "source_type": pm.get("type", "unknown"),
                "pbi_type": f"Slicer ({raw.slicer_style.value})",
                "source": pm.get("source", ""),
            })
        else:
            entries.append({
                "name": pm.get("name", ""),
                "source_type": pm.get("type", "unknown"),
                "pbi_type": "What-If Parameter",
                "source": pm.get("source", ""),
            })
    return entries, slicers


def generate_report(
    items: list[InventoryItem],
    slicers: list[SlicerConfig],
) -> PBIRGenerationResult | None:
    """Step 4c — Generate PBIR report pages and visuals."""
    analyses = [i for i in items if i.asset_type in (AssetType.ANALYSIS, AssetType.DASHBOARD)]
    if not analyses:
        return None

    pages: list[PBIPage] = []
    specs: dict[str, VisualSpec] = {}

    for idx, item in enumerate(analyses):
        positions: list[VisualPosition] = []
        meta = dict(item.metadata)

        for vi, vis_data in enumerate(meta.get("visuals", [])):
            vname = f"{item.name}_{vi}"
            vtype = vis_data.get("type", "table")
            pbi_type, _ = map_visual_type(vtype)
            col, row = vi % 3, vi // 3
            pos = VisualPosition(
                x=col * 420 + 10, y=row * 260 + 10,
                width=400, height=240,
                page_index=idx, visual_name=vname, visual_type=pbi_type.value,
            )
            positions.append(pos)
            specs[vname] = VisualSpec(name=vname, title=vis_data.get("name", vname), visual_type=pbi_type, position=pos)

        if not positions and meta.get("mark_type"):
            vname = f"{item.name}_main"
            pbi_type, _ = map_visual_type(meta["mark_type"])
            pos = VisualPosition(x=10, y=10, width=1260, height=700, page_index=idx, visual_name=vname, visual_type=pbi_type.value)
            positions.append(pos)
            specs[vname] = VisualSpec(name=vname, title=item.name, visual_type=pbi_type, position=pos)

        pages.append(PBIPage(name=f"Page_{idx + 1}", display_name=item.name[:40], page_index=idx, visuals=positions))

    if not pages:
        return None
    return generate_pbir(report_name="MigrationReport", pages=pages, visual_specs=specs, slicers=slicers)


def map_security(items: list[InventoryItem]) -> tuple[list[dict[str, Any]], str]:
    """Step 5 — Map OAC security roles → Fabric/PBI roles + RLS TMDL."""
    role_items = [i for i in items if i.asset_type == AssetType.SECURITY_ROLE]
    if not role_items:
        return [], ""
    oac_roles = [parse_oac_role(dict(item.metadata) | {"name": item.name}) for item in role_items]
    result = map_roles(oac_roles)
    entries = []
    for ws in result.workspace_assignments:
        matching_rls = [r for r in result.rls_roles if r.role_name == ws.role_name]
        entries.append({
            "oac_role": ws.role_name,
            "fabric_role": ws.workspace_role.value,
            "rls_filters": sum(len(r.table_permissions) for r in matching_rls),
            "ols_columns": 0,
            "aad_group": ws.aad_group,
        })
    rls_tmdl = render_roles_tmdl(result.rls_roles) if result.rls_roles else ""
    return entries, rls_tmdl


def map_etl(items: list[InventoryItem]) -> list[dict[str, Any]]:
    """Step 6 — Map data flow steps → Fabric pipeline activities."""
    flows: list[DataFlow] = []
    by_source: dict[str, list[InventoryItem]] = {}
    for item in items:
        if item.asset_type == AssetType.PHYSICAL_TABLE:
            by_source.setdefault(item.source, []).append(item)

    for source, tables in by_source.items():
        steps: list[DataFlowStep] = []
        for idx, t in enumerate(tables):
            steps.append(DataFlowStep(
                id=f"{source}_{t.name}_src", name=f"Read_{t.name}",
                step_type=StepType.SOURCE_DB, order=idx * 3, source_table=t.name,
            ))
            cols = t.metadata.get("columns", [])
            if len(cols) > 5:
                steps.append(DataFlowStep(
                    id=f"{source}_{t.name}_filter", name=f"Filter_{t.name}",
                    step_type=StepType.FILTER, order=idx * 3 + 1,
                    filter_expression=f"WHERE {cols[0].get('name', 'id')} IS NOT NULL",
                ))
            steps.append(DataFlowStep(
                id=f"{source}_{t.name}_tgt", name=f"Write_{t.name}",
                step_type=StepType.TARGET_DB, order=idx * 3 + 2, target_table=t.name,
            ))
        flows.append(DataFlow(
            id=f"flow_{source}", name=f"{source.upper()} Data Load",
            description=f"Load {len(tables)} tables from {source}", steps=steps,
        ))

    entries = []
    for flow in flows:
        for step in flow.steps:
            mapped = map_step(step)
            entries.append({
                "step_name": step.name,
                "source_type": step.step_type.value,
                "fabric_target": mapped.fabric_type,
                "warnings": [mapped.review_reason] if mapped.requires_review else [],
            })
    return entries


async def run_validation(
    items: list[InventoryItem],
    output_dir: Path,
) -> dict[str, Any]:
    """Step 7 — Agent 07 cross-layer validation."""
    val_dir = output_dir / "validation"
    agent = ValidationAgent(output_dir=val_dir)
    scope = MigrationScope(include_paths=["/"])
    await agent.discover(scope)
    inventory = Inventory(items=items)
    plan = await agent.plan(inventory)
    result = await agent.execute(plan)
    return {
        "succeeded": result.succeeded,
        "failed": result.failed,
        "errors": result.errors,
    }


# ═══════════════════════════════════════════════════════════════════════
# HTML report builder (inline — no external dependency on scripts/)
# ═══════════════════════════════════════════════════════════════════════


def _build_html_report(result: MigrationResult) -> str:
    """Delegate to the project's HTML report generator."""
    # Import here to avoid circular imports and keep the example self-contained
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))
    from html_report_generator import (
        ETLMappingEntry,
        PromptMappingEntry,
        ReportData,
        SecurityMappingEntry,
        VisualMappingEntry,
        generate_html_report,
    )

    rd = ReportData(
        items=[
            {"name": i.name, "asset_type": i.asset_type.value, "source": i.source, "source_path": i.source_path}
            for i in result.items
        ],
        by_source=result.by_source,
        by_type=result.by_type,
        ddl_results=result.ddl_results,
        tmdl_files=result.tmdl_files,
        translations=result.translations,
        review_items=result.review_items,
        visual_mappings=[
            VisualMappingEntry(
                source_type=vm["source_type"],
                pbi_type=vm["pbi_type"],
                count=vm["count"],
                warnings=vm.get("warnings", []),
            )
            for vm in result.visual_mappings
        ],
        prompt_mappings=[
            PromptMappingEntry(
                name=pm["name"],
                source_type=pm["source_type"],
                pbi_type=pm["pbi_type"],
                source=pm.get("source", ""),
            )
            for pm in result.prompt_mappings
        ],
        pbir_pages=result.pbir_pages,
        pbir_visuals=result.pbir_visuals,
        security_mappings=[
            SecurityMappingEntry(
                oac_role=sm["oac_role"],
                fabric_role=sm["fabric_role"],
                rls_filters=sm["rls_filters"],
                ols_columns=sm["ols_columns"],
                aad_group=sm.get("aad_group", ""),
            )
            for sm in result.security_mappings
        ],
        rls_rules_tmdl=result.rls_tmdl,
        etl_mappings=[
            ETLMappingEntry(
                step_name=em["step_name"],
                source_type=em["source_type"],
                fabric_target=em["fabric_target"],
                warnings=em.get("warnings", []),
            )
            for em in result.etl_mappings
        ],
        validation_layers=result.validation_passed,
        validation_total=result.validation_total,
        validation_errors=result.validation_errors,
        elapsed_seconds=result.elapsed_seconds,
        output_dir=result.output_dir,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )
    return generate_html_report(rd)


# ═══════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════


async def run_full_migration(
    *,
    samples_dir: Path = EXAMPLES_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    specific_files: list[Path] | None = None,
    verbose: bool = False,
) -> MigrationResult:
    """Execute the complete 8-step migration pipeline.

    Args:
        samples_dir: Root directory containing sample files.
        output_dir: Where to write output artifacts and reports.
        specific_files: If provided, parse only these files.
        verbose: Enable debug logging.

    Returns:
        MigrationResult with all data and the path to the HTML report.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s")

    start = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = MigrationResult(output_dir=str(output_dir))

    # ── 1. Discovery ──────────────────────────────────────────────────
    result.items = discover_all(samples_dir, specific_files)
    for item in result.items:
        result.by_type[item.asset_type.value] = result.by_type.get(item.asset_type.value, 0) + 1
        result.by_source[item.source] = result.by_source.get(item.source, 0) + 1

    # ── 2. Schema (DDL) ──────────────────────────────────────────────
    result.ddl_results = generate_schema(result.items)
    if result.ddl_results:
        ddl_text = "\n\n".join(d["ddl"] for d in result.ddl_results)
        (output_dir / "generated_ddl.sql").write_text(ddl_text, encoding="utf-8")

    # ── 3. Semantic Model (TMDL) ─────────────────────────────────────
    tmdl_dict = build_semantic_model(result.items)
    if tmdl_dict:
        result.tmdl_files = tmdl_dict.get("files", {})
        result.translations = [
            {"original": t.original_expression, "dax": t.dax_expression, "confidence": t.confidence, "method": t.method}
            for t in tmdl_dict.get("translation_log", [])
        ]
        result.review_items = tmdl_dict.get("review_items", [])
        tmdl_dir = output_dir / "SemanticModel"
        tmdl_dir.mkdir(parents=True, exist_ok=True)
        for fname, content in result.tmdl_files.items():
            fpath = tmdl_dir / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")

    # ── 4. Report / Visuals ──────────────────────────────────────────
    result.visual_mappings, visual_specs = map_visuals(result.items)
    result.prompt_mappings, slicers = convert_prompts(result.items)
    pbir = generate_report(result.items, slicers)
    if pbir:
        result.pbir_pages = pbir.page_count
        result.pbir_visuals = pbir.visual_count
        write_pbir_to_disk(pbir, output_dir / "PBIR")

    # ── 5. Security ──────────────────────────────────────────────────
    result.security_mappings, result.rls_tmdl = map_security(result.items)
    if result.rls_tmdl:
        (output_dir / "rls_roles.tmdl").write_text(result.rls_tmdl, encoding="utf-8")

    # ── 6. ETL ───────────────────────────────────────────────────────
    result.etl_mappings = map_etl(result.items)

    # ── 7. Validation ────────────────────────────────────────────────
    try:
        val = await run_validation(result.items, output_dir)
        result.validation_passed = val.get("succeeded", 0)
        result.validation_errors = val.get("errors", [])
    except Exception as exc:
        logger.warning("Validation failed: %s", exc)
        result.validation_errors = [str(exc)]

    # ── 8. Generate Reports ──────────────────────────────────────────
    result.elapsed_seconds = time.perf_counter() - start

    # HTML report
    html = _build_html_report(result)
    html_path = output_dir / "migration_report.html"
    html_path.write_text(html, encoding="utf-8")
    result.html_report_path = str(html_path)

    # Markdown report (compact summary)
    md_lines = _build_markdown_summary(result)
    md_path = output_dir / "migration_report.md"
    md_path.write_text(md_lines, encoding="utf-8")
    result.md_report_path = str(md_path)

    return result


def _build_markdown_summary(r: MigrationResult) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Migration Report",
        "",
        f"> **Generated:** {now}  ",
        f"> **Assets:** {len(r.items)} | **Elapsed:** {r.elapsed_seconds:.1f}s  ",
        f"> **Output:** `{r.output_dir}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Assets discovered | **{len(r.items)}** |",
        f"| Source platforms | {len(r.by_source)} ({', '.join(sorted(r.by_source))}) |",
        f"| DDL tables | {len(r.ddl_results)} |",
        f"| TMDL files | {len(r.tmdl_files)} |",
        f"| Expressions translated | {len(r.translations)} |",
        f"| Visual types mapped | {len(r.visual_mappings)} |",
        f"| Prompts → slicers | {len(r.prompt_mappings)} |",
        f"| PBIR pages / visuals | {r.pbir_pages} / {r.pbir_visuals} |",
        f"| Security roles | {len(r.security_mappings)} |",
        f"| ETL steps | {len(r.etl_mappings)} |",
        f"| Validation | {r.validation_passed}/{r.validation_total} |",
        "",
        "## Assets by Source",
        "",
        "| Source | Count |",
        "|--------|-------|",
    ]
    for src, count in sorted(r.by_source.items()):
        lines.append(f"| {src} | {count} |")
    lines.extend([
        "",
        "## Assets by Type",
        "",
        "| Type | Count |",
        "|------|-------|",
    ])
    for atype, count in sorted(r.by_type.items()):
        lines.append(f"| {atype} | {count} |")
    lines.extend([
        "",
        "---",
        f"*Generated by OAC-to-Fabric Migration Accelerator — {now}*",
    ])
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run full OAC -> Fabric migration with HTML report",
    )
    parser.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--samples", type=Path, nargs="*", help="Specific sample files")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    specific = [Path(s) for s in args.samples] if args.samples else None
    result = asyncio.run(run_full_migration(
        output_dir=args.output_dir,
        specific_files=specific,
        verbose=args.verbose,
    ))

    print(result.summary())
    print(f"\n  Open: {result.html_report_path}")


if __name__ == "__main__":
    main()
