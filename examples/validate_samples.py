#!/usr/bin/env python3
"""Validate that all example sample files parse successfully.

Runs each sample through its respective connector/parser and reports
pass/fail status.  Returns exit-code 0 only when every sample passes.

Usage::

    python examples/validate_samples.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

EXAMPLES_DIR = Path(__file__).resolve().parent

# ── colour helpers (ANSI, graceful no-colour on redirect) ──────────────
_ISATTY = sys.stdout.isatty()

def _green(text: str) -> str:
    return f"\033[92m{text}\033[0m" if _ISATTY else text

def _red(text: str) -> str:
    return f"\033[91m{text}\033[0m" if _ISATTY else text

def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m" if _ISATTY else text


# ── validators ─────────────────────────────────────────────────────────

def validate_xml(path: Path, root_tag: str | None = None) -> str | None:
    """Parse XML and optionally check root tag.  Returns error or None."""
    try:
        tree = ET.parse(path)  # noqa: S314 — trusted local test data
        root = tree.getroot()
        if root_tag and root.tag.lower() != root_tag.lower():
            return f"expected root <{root_tag}>, got <{root.tag}>"
        return None
    except ET.ParseError as exc:
        return f"XML parse error: {exc}"


def validate_json(path: Path) -> str | None:
    """Parse JSON.  Returns error or None."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return f"expected JSON object, got {type(data).__name__}"
        return None
    except json.JSONDecodeError as exc:
        return f"JSON parse error: {exc}"


def validate_qlik_script(path: Path) -> str | None:
    """Basic structural check for Qlik load scripts."""
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return "file is empty"
        # Must contain at least one LOAD or SQL SELECT
        upper = text.upper()
        if "LOAD" not in upper and "SQL SELECT" not in upper:
            return "no LOAD or SQL SELECT statement found"
        return None
    except Exception as exc:
        return str(exc)


# ── sample registry ────────────────────────────────────────────────────

SAMPLES: list[tuple[Path, str, object]] = [
    # OAC RPD XML
    (EXAMPLES_DIR / "oac_samples" / "simple_sales.xml", "OAC RPD", lambda p: validate_xml(p, "Repository")),
    (EXAMPLES_DIR / "oac_samples" / "medium_hr.xml", "OAC RPD", lambda p: validate_xml(p, "Repository")),
    (EXAMPLES_DIR / "oac_samples" / "complex_enterprise.xml", "OAC RPD", lambda p: validate_xml(p, "Repository")),
    (EXAMPLES_DIR / "oac_samples" / "advanced_analytics.xml", "OAC RPD", lambda p: validate_xml(p, "Repository")),
    (EXAMPLES_DIR / "oac_samples" / "financial_functions.xml", "OAC RPD", lambda p: validate_xml(p, "Repository")),
    (EXAMPLES_DIR / "oac_samples" / "full_catalog_enterprise.xml", "OAC RPD", lambda p: validate_xml(p, "Repository")),
    # OAC REST API JSON
    (EXAMPLES_DIR / "oac_samples" / "catalog_api_response.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "analysis_sales_overview.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "analysis_financial_report.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "dashboard_executive.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "dashboard_operational.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "dataflow_etl_pipeline.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "dataflow_customer_360.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "data_model_star_schema.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "prompt_definitions.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "filter_definitions.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "agent_alert_definitions.json", "OAC API JSON", validate_json),
    (EXAMPLES_DIR / "oac_samples" / "connections.json", "OAC API JSON", validate_json),
    # Essbase
    (EXAMPLES_DIR / "essbase_samples" / "simple_budget.xml", "Essbase XML", lambda p: validate_xml(p, "outline")),
    (EXAMPLES_DIR / "essbase_samples" / "simple_budget.json", "Essbase JSON", validate_json),
    (EXAMPLES_DIR / "essbase_samples" / "medium_finance.xml", "Essbase XML", lambda p: validate_xml(p, "outline")),
    (EXAMPLES_DIR / "essbase_samples" / "complex_planning.xml", "Essbase XML", lambda p: validate_xml(p, "outline")),
    # Cognos
    (EXAMPLES_DIR / "cognos_samples" / "simple_list_report.xml", "Cognos", lambda p: validate_xml(p, "report")),
    (EXAMPLES_DIR / "cognos_samples" / "medium_crosstab.xml", "Cognos", lambda p: validate_xml(p, "report")),
    (EXAMPLES_DIR / "cognos_samples" / "complex_dashboard.xml", "Cognos", lambda p: validate_xml(p, "report")),
    # Qlik
    (EXAMPLES_DIR / "qlik_samples" / "simple_load.qvs", "Qlik Script", validate_qlik_script),
    (EXAMPLES_DIR / "qlik_samples" / "medium_etl.qvs", "Qlik Script", validate_qlik_script),
    (EXAMPLES_DIR / "qlik_samples" / "complex_pipeline.qvs", "Qlik Script", validate_qlik_script),
    # Tableau
    (EXAMPLES_DIR / "tableau_samples" / "simple_chart.twb", "Tableau TWB", lambda p: validate_xml(p, "workbook")),
    (EXAMPLES_DIR / "tableau_samples" / "medium_dashboard.twb", "Tableau TWB", lambda p: validate_xml(p, "workbook")),
    (EXAMPLES_DIR / "tableau_samples" / "complex_enterprise.twb", "Tableau TWB", lambda p: validate_xml(p, "workbook")),
]


# ── main ───────────────────────────────────────────────────────────────

def main() -> int:
    print(_bold("Validating example samples\n"))
    passed = 0
    failed = 0

    for path, connector, validator in SAMPLES:
        rel = path.relative_to(EXAMPLES_DIR)
        error = validator(path)
        if error is None:
            print(f"  {_green('PASS')}  [{connector:14s}]  {rel}")
            passed += 1
        else:
            print(f"  {_red('FAIL')}  [{connector:14s}]  {rel}  — {error}")
            failed += 1

    print()
    summary = f"{passed} passed, {failed} failed out of {passed + failed} samples"
    if failed:
        print(_red(f"FAILED: {summary}"))
        return 1
    print(_green(f"ALL PASSED: {summary}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
