#!/usr/bin/env python3
"""Prepare BSO writeback package for Smart View and Longview.

This script orchestrates existing migration generators to produce a complete
backend writeback package for BSO planning workloads:

1. Warehouse DDL and stored procedures
2. Writeback calculation notebook and pipeline JSON
3. Longview Phase A artifacts (dimension DDL, data migration, UAT, cutover)
4. TDS connection config for Longview
5. Smart View + Longview operator summary

Usage:
    py -3 scripts/prepare_bso_writeback.py \
        --outline examples/essbase_samples/longview_budget_writeback.xml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.agents.etl.longview_migration import generate_phase_a_artifacts
from src.agents.etl.writeback_generator import config_from_essbase_outline
from src.connectors.essbase_connector import EssbaseOutlineParser


def _build_outline_dict_from_xml(xml_path: Path) -> dict[str, Any]:
    parser = EssbaseOutlineParser()
    parsed = parser.parse_xml(xml_path.read_text(encoding="utf-8"))
    if not parsed.is_valid:
        raise ValueError(f"Invalid Essbase outline: {parsed.errors}")

    dims: list[dict[str, Any]] = []
    for dim in parsed.dimensions:
        dims.append(
            {
                "name": dim.name,
                "type": "dense" if dim.storage_type == "dense" else "sparse",
                "dimension_type": dim.dimension_type,
                "members": dim.members,
            }
        )

    return {
        "application": parsed.application or xml_path.stem,
        "database": parsed.database or xml_path.stem,
        "dimensions": dims,
    }


def _load_outline(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix == ".xml":
        return _build_outline_dict_from_xml(path)
    raise ValueError(f"Unsupported outline format: {suffix} (expected .xml or .json)")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_summary(
    output_dir: Path,
    app: str,
    db: str,
    workspace: str,
    warehouse: str,
    assessment: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# BSO Writeback Preparation Summary",
            "",
            f"- Application: {app}",
            f"- Database: {db}",
            f"- Workspace: {workspace}",
            f"- Warehouse: {warehouse}",
            f"- Complexity: {assessment.get('complexity', 'N/A')}",
            f"- Estimated weeks: {assessment.get('estimated_weeks', 'N/A')}",
            "",
            "## Generated Artifacts",
            "",
            "- warehouse_ddl.sql",
            "- stored_procedures.sql",
            "- calc_notebook.py",
            "- pipeline.json",
            "- model_hints.json",
            "- dimension_ddl.sql",
            "- data_migration_notebook.py",
            "- uat_notebook.py",
            "- cutover_checklist.md",
            "- tds_connection.json",
            "- assessment.json",
            "- warnings.txt",
            "",
            "## Smart View + Longview Readiness",
            "",
            "1. Longview should point writeback to Fabric TDS endpoint and use dbo.usp_WriteBudget.",
            "2. Smart View users can move to Excel + semantic model grids while writeback stays on Warehouse.",
            "3. Run data_migration_notebook.py then uat_notebook.py before production cutover.",
            "4. Execute cutover_checklist.md in order (includes rollback plan).",
            "",
            f"Output folder: {output_dir}",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare BSO writeback package")
    parser.add_argument(
        "--outline",
        type=Path,
        default=Path("examples/essbase_samples/longview_budget_writeback.xml"),
        help="Path to Essbase outline (.xml or .json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/etl/bso_writeback_prep"),
        help="Output directory for generated artifacts",
    )
    parser.add_argument("--workspace-name", default="BudgetWorkspace")
    parser.add_argument("--warehouse-name", default="BudgetWarehouse")
    parser.add_argument("--application", default="")
    parser.add_argument("--database", default="")
    parser.add_argument("--enable-allocation", action="store_true")
    parser.add_argument("--enable-currency", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    outline = _load_outline(args.outline)
    cfg = config_from_essbase_outline(
        outline,
        enable_allocation=args.enable_allocation,
        enable_currency=args.enable_currency,
    )

    if args.application:
        cfg.application_name = args.application
    if args.database:
        cfg.database_name = args.database

    phase_a = generate_phase_a_artifacts(
        cfg,
        workspace_name=args.workspace_name,
        warehouse_name=args.warehouse_name,
    )

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    _write(out / "warehouse_ddl.sql", phase_a.writeback.warehouse_ddl)
    _write(out / "stored_procedures.sql", phase_a.writeback.stored_procedures)
    _write(out / "calc_notebook.py", phase_a.writeback.calc_notebook)
    _write(out / "pipeline.json", phase_a.writeback.pipeline_json)
    _write_json(out / "model_hints.json", phase_a.writeback.model_hints)

    _write(out / "dimension_ddl.sql", phase_a.dimension_ddl)
    _write(out / "data_migration_notebook.py", phase_a.data_migration_notebook)
    _write(out / "uat_notebook.py", phase_a.uat_notebook)
    _write(out / "cutover_checklist.md", phase_a.cutover_checklist)
    _write_json(out / "tds_connection.json", phase_a.tds_connection_config)
    _write_json(out / "assessment.json", phase_a.assessment)

    warnings = phase_a.warnings or []
    _write(out / "warnings.txt", "\n".join(warnings) if warnings else "No warnings")

    summary = _build_summary(
        out,
        cfg.application_name,
        cfg.database_name,
        args.workspace_name,
        args.warehouse_name,
        phase_a.assessment,
    )
    _write(out / "PREP_SUMMARY.md", summary)

    print(f"Prepared BSO writeback package in: {out}")
    print(f"Application/DB: {cfg.application_name}/{cfg.database_name}")
    print(f"Complexity: {phase_a.assessment.get('complexity', 'N/A')}")
    print(f"Estimated weeks: {phase_a.assessment.get('estimated_weeks', 'N/A')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
