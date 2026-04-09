"""Comprehensive verification of all generated .pbip project files.

Checks TMDL semantic model, PBIR report, project structure, M expressions,
DAX syntax, JSON schemas, indentation, and cross-references.

Usage:
    python scripts/verify_all.py [--output-dir DIR]
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT = "output/migration_report/MigrationReport"

# Expected JSON schema prefixes
EXPECTED_SCHEMAS = {
    ".pbip": "pbipProperties",
    "definition.pbism": "semanticModel/definitionProperties",
    "definition.pbir": "report/definitionProperties",
    "report.json": "report/definition/report",
    "version.json": "versionMetadata",
    ".platform": "platformProperties",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class CheckResult:
    """Accumulates check results."""

    def __init__(self) -> None:
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self._section = ""

    def section(self, name: str) -> None:
        self._section = name

    def ok(self, msg: str) -> None:
        self.passed.append(f"[{self._section}] {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(f"[{self._section}] {msg}")

    def error(self, msg: str) -> None:
        self.errors.append(f"[{self._section}] {msg}")

    def summary(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  VERIFICATION REPORT")
        lines.append("=" * 70)
        lines.append(f"  Passed:   {len(self.passed)}")
        lines.append(f"  Warnings: {len(self.warnings)}")
        lines.append(f"  Errors:   {len(self.errors)}")
        lines.append("=" * 70)
        if self.errors:
            lines.append("")
            lines.append("ERRORS:")
            for e in self.errors:
                lines.append(f"  ✗ {e}")
        if self.warnings:
            lines.append("")
            lines.append("WARNINGS:")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        if not self.errors and not self.warnings:
            lines.append("")
            lines.append("  ALL CHECKS PASSED!")
        lines.append("")
        return "\n".join(lines)


def _read(path: str) -> str:
    return open(path, encoding="utf-8").read()


def _read_json(path: str) -> dict:
    return json.loads(_read(path))


def _quote_name(name: str) -> str:
    return f"'{name}'" if " " in name or not name.isalnum() else name


# ---------------------------------------------------------------------------
# 1. Project structure checks
# ---------------------------------------------------------------------------

def check_project_structure(out: str, r: CheckResult) -> None:
    r.section("Structure")

    # .pbip file
    pbip_files = list(Path(out).glob("*.pbip"))
    if not pbip_files:
        r.error("No .pbip file found")
        return
    r.ok(f".pbip file: {pbip_files[0].name}")

    # SemanticModel folder
    sm_dirs = [d for d in Path(out).iterdir() if d.is_dir() and "SemanticModel" in d.name]
    if not sm_dirs:
        r.error("No SemanticModel folder found")
        return
    sm = sm_dirs[0]
    r.ok(f"SemanticModel folder: {sm.name}")

    # Report folder
    rpt_dirs = [d for d in Path(out).iterdir() if d.is_dir() and "Report" in d.name]
    if not rpt_dirs:
        r.error("No Report folder found")
        return
    rpt = rpt_dirs[0]
    r.ok(f"Report folder: {rpt.name}")

    # Required files
    required_sm = ["definition.pbism", "definition/model.tmdl", "definition/database.tmdl"]
    for f in required_sm:
        if (sm / f).exists():
            r.ok(f"SM: {f}")
        else:
            r.error(f"SM: missing {f}")

    required_rpt = ["definition.pbir", "definition/report.json", "definition/version.json"]
    for f in required_rpt:
        if (rpt / f).exists():
            r.ok(f"Report: {f}")
        else:
            r.error(f"Report: missing {f}")

    # .platform files
    for folder in [sm, rpt]:
        plat = folder / ".platform"
        if plat.exists():
            r.ok(f"{folder.name}/.platform present")
        else:
            r.warn(f"{folder.name}/.platform missing (optional for local)")

    # Tables folder
    tables = sm / "definition" / "tables"
    if tables.exists():
        count = len(list(tables.glob("*.tmdl")))
        if count > 0:
            r.ok(f"Tables: {count} .tmdl files")
        else:
            r.error("Tables folder is empty")
    else:
        r.error("No tables/ folder in SemanticModel definition")

    # Pages folder
    pages = rpt / "definition" / "pages"
    if pages.exists():
        page_count = len([d for d in pages.iterdir() if d.is_dir()])
        if page_count > 0:
            r.ok(f"Pages: {page_count} page folders")
        else:
            r.warn("Pages folder has no page subdirectories")
    else:
        r.warn("No pages/ folder in Report definition")


# ---------------------------------------------------------------------------
# 2. JSON schema validation
# ---------------------------------------------------------------------------

def check_json_files(out: str, r: CheckResult) -> None:
    r.section("JSON")
    out_path = Path(out)

    # Find all .json and .pbip/.pbism/.pbir files
    json_files = list(out_path.rglob("*.json")) + list(out_path.rglob("*.pbip"))
    json_files += list(out_path.rglob("*.pbism")) + list(out_path.rglob("*.pbir"))
    json_files += list(out_path.rglob(".platform"))

    for jf in json_files:
        try:
            data = _read_json(str(jf))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            r.error(f"{jf.name}: invalid JSON — {exc}")
            continue

        # Check $schema present
        schema = data.get("$schema", "")
        rel = jf.relative_to(out_path)
        if rel.suffix in (".json", ".pbip", ".pbism", ".pbir") or rel.name == ".platform":
            if schema:
                r.ok(f"{rel}: valid JSON with $schema")
            elif rel.name not in ("page.json",):
                # page.json may not have $schema in older versions
                pass

        # Validate specific schema URLs
        for key, expected_fragment in EXPECTED_SCHEMAS.items():
            if str(rel).endswith(key) or rel.name == key:
                if expected_fragment not in schema:
                    r.warn(f"{rel}: $schema doesn't contain '{expected_fragment}'")
                break


# ---------------------------------------------------------------------------
# 3. PBIP project references
# ---------------------------------------------------------------------------

def check_pbip_references(out: str, r: CheckResult) -> None:
    r.section("PBIP Refs")
    out_path = Path(out)

    # .pbip → report path
    pbip_files = list(out_path.glob("*.pbip"))
    if not pbip_files:
        return
    pbip = _read_json(str(pbip_files[0]))
    artifacts = pbip.get("artifacts", [])
    if not artifacts:
        r.error(".pbip: no artifacts defined")
        return
    report_path = artifacts[0].get("report", {}).get("path", "")
    if report_path and (out_path / report_path).is_dir():
        r.ok(f".pbip → report path '{report_path}' exists")
    else:
        r.error(f".pbip → report path '{report_path}' not found")

    # definition.pbir → SM path
    rpt_dirs = [d for d in out_path.iterdir() if d.is_dir() and "Report" in d.name]
    if rpt_dirs:
        pbir_path = rpt_dirs[0] / "definition.pbir"
        if pbir_path.exists():
            pbir = _read_json(str(pbir_path))
            sm_path = pbir.get("datasetReference", {}).get("byPath", {}).get("path", "")
            if sm_path:
                resolved = (rpt_dirs[0] / sm_path).resolve()
                if resolved.exists():
                    r.ok(f"definition.pbir → SM path resolves correctly")
                else:
                    r.error(f"definition.pbir → SM path '{sm_path}' doesn't resolve")
            else:
                r.error("definition.pbir: no byPath SM reference")


# ---------------------------------------------------------------------------
# 4. TMDL model.tmdl cross-references
# ---------------------------------------------------------------------------

def check_model_refs(out: str, r: CheckResult) -> None:
    r.section("Model Refs")
    sm_def = _find_sm_def(out)
    if not sm_def:
        r.error("Cannot find SemanticModel definition folder")
        return

    tables_dir = os.path.join(sm_def, "tables")
    if not os.path.isdir(tables_dir):
        r.error("No tables/ directory")
        return

    # Parse all table files
    table_names: set[str] = set()
    table_cols: dict[str, set[str]] = {}
    table_measures: dict[str, set[str]] = {}
    table_hiers: dict[str, set[str]] = {}

    for fname in os.listdir(tables_dir):
        if not fname.endswith(".tmdl"):
            continue
        content = _read(os.path.join(tables_dir, fname))
        tm = re.match(r"^table\s+(?:'([^']+)'|(\w+))", content)
        if not tm:
            r.error(f"{fname}: cannot parse table name")
            continue
        tname = tm.group(1) or tm.group(2)
        table_names.add(tname)
        cols, measures, hiers = set(), set(), set()
        for m in re.finditer(r"^\tcolumn\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
            cols.add(m.group(1) or m.group(2))
        for m in re.finditer(r"^\tmeasure\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
            measures.add(m.group(1) or m.group(2))
        for m in re.finditer(r"^\thierarchy\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
            hiers.add(m.group(1) or m.group(2))
        table_cols[tname] = cols
        table_measures[tname] = measures
        table_hiers[tname] = hiers

    r.ok(f"{len(table_names)} tables parsed")

    # model.tmdl
    model_path = os.path.join(sm_def, "model.tmdl")
    model = _read(model_path)

    # ref table vs actual tables
    ref_tables = re.findall(r"^ref table\s+(?:'([^']+)'|(\w+))", model, re.MULTILINE)
    ref_names = [g[0] or g[1] for g in ref_tables]
    for ref in ref_names:
        if ref not in table_names:
            r.error(f"model.tmdl: ref table {_quote_name(ref)} has no .tmdl file")
    for t in table_names:
        if t not in ref_names:
            r.warn(f"Table {_quote_name(t)} not referenced in model.tmdl")

    # Duplicate ref table
    dupes = {k: v for k, v in Counter(ref_names).items() if v > 1}
    if dupes:
        r.error(f"model.tmdl: duplicate ref table entries: {dupes}")
    else:
        r.ok("No duplicate ref table entries")

    # Empty tables
    empty = [t for t in table_names if not table_cols.get(t) and not table_measures.get(t)]
    if empty:
        for t in empty:
            r.error(f"Empty table (no columns/measures): {_quote_name(t)}")
    else:
        r.ok("No empty tables")

    # Relationships
    rel_path = os.path.join(sm_def, "relationships.tmdl")
    if os.path.exists(rel_path):
        rel = _read(rel_path)
        rel_issues = 0
        for m in re.finditer(
            r"(fromColumn|toColumn):\s+(?:'([^']+)'|(\w+))\.(?:'([^']+)'|(\w+))", rel
        ):
            kind = m.group(1)
            tbl = m.group(2) or m.group(3)
            col = m.group(4) or m.group(5)
            if tbl not in table_names:
                r.error(f"relationships.tmdl: {kind} references unknown table {_quote_name(tbl)}")
                rel_issues += 1
            elif col not in table_cols.get(tbl, set()):
                r.error(f"relationships.tmdl: {kind} {tbl}.{col} column not found")
                rel_issues += 1
        if rel_issues == 0:
            r.ok("All relationship columns valid")

    # Perspectives
    persp_path = os.path.join(sm_def, "perspectives.tmdl")
    if os.path.exists(persp_path):
        persp = _read(persp_path)
        actual_persps = set()
        for m in re.finditer(r"^perspective\s+(?:'([^']+)'|(\w+))", persp, re.MULTILINE):
            actual_persps.add(m.group(1) or m.group(2))
        model_persps = set()
        for m in re.finditer(r"^ref perspective\s+(?:'([^']+)'|(\w+))", model, re.MULTILINE):
            model_persps.add(m.group(1) or m.group(2))
        for p in model_persps - actual_persps:
            r.error(f"model.tmdl: ref perspective {_quote_name(p)} not in perspectives.tmdl")
        for p in actual_persps - model_persps:
            r.error(f"perspectives.tmdl: {_quote_name(p)} missing ref in model.tmdl")
        if not (model_persps - actual_persps) and not (actual_persps - model_persps):
            r.ok(f"All {len(actual_persps)} perspectives cross-referenced correctly")

        # perspectiveColumn/perspectiveMeasure accuracy
        current_table = None
        persp_issues = 0
        for line in persp.split("\n"):
            tm = re.match(r"^\tperspectiveTable\s+(?:'([^']+)'|(\w+))", line)
            if tm:
                current_table = tm.group(1) or tm.group(2)
                if current_table not in table_names:
                    r.error(f"perspectives: table {_quote_name(current_table)} not found")
                    persp_issues += 1
                continue
            cm = re.match(r"^\t\tperspectiveColumn\s+(?:'([^']+)'|(\w+))", line)
            if cm and current_table:
                col = cm.group(1) or cm.group(2)
                if current_table in table_cols and col not in table_cols[current_table]:
                    r.error(f"perspectives: {current_table}.{col} is not a column")
                    persp_issues += 1
            mm = re.match(r"^\t\tperspectiveMeasure\s+(?:'([^']+)'|(\w+))", line)
            if mm and current_table:
                meas = mm.group(1) or mm.group(2)
                if current_table in table_measures and meas not in table_measures[current_table]:
                    r.error(f"perspectives: {current_table}.{meas} is not a measure")
                    persp_issues += 1
        if persp_issues == 0:
            r.ok("All perspective columns/measures valid")

    # Hierarchy levels
    hier_issues = 0
    for fname in os.listdir(tables_dir):
        if not fname.endswith(".tmdl"):
            continue
        content = _read(os.path.join(tables_dir, fname))
        tm = re.match(r"^table\s+(?:'([^']+)'|(\w+))", content)
        if not tm:
            continue
        tname = tm.group(1) or tm.group(2)
        cols = table_cols.get(tname, set())
        for hm in re.finditer(r"^\thierarchy\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
            hier_name = hm.group(1) or hm.group(2)
            hier_start = hm.end()
            for lm in re.finditer(r"^\t\tlevel\s+(?:'([^']+)'|(\w+))", content[hier_start:], re.MULTILINE):
                level_end = lm.end() + hier_start
                col_match = re.search(r"^\t\t\tcolumn:\s+(?:'([^']+)'|(\w+))", content[level_end:], re.MULTILINE)
                if col_match:
                    col_ref = col_match.group(1) or col_match.group(2)
                    if col_ref not in cols:
                        r.error(f"{fname}: hierarchy {hier_name} level → missing column {col_ref}")
                        hier_issues += 1
    if hier_issues == 0:
        r.ok("All hierarchy level columns valid")


# ---------------------------------------------------------------------------
# 5. Partition M expression syntax
# ---------------------------------------------------------------------------

def check_partitions(out: str, r: CheckResult) -> None:
    r.section("Partitions")
    sm_def = _find_sm_def(out)
    if not sm_def:
        return
    tables_dir = os.path.join(sm_def, "tables")
    if not os.path.isdir(tables_dir):
        return

    for fname in sorted(os.listdir(tables_dir)):
        if not fname.endswith(".tmdl"):
            continue
        lines = _read(os.path.join(tables_dir, fname)).split("\n")
        in_source = False
        source_line = 0
        has_partition = False

        for i, line in enumerate(lines):
            # Partition declaration
            if re.match(r"^\tpartition\s+", line):
                has_partition = True

            # source = block
            if re.match(r"^\t\tsource\s*=\s*$", line):
                in_source = True
                source_line = i + 1
                continue

            if in_source:
                stripped = line.strip()
                if not stripped:
                    continue
                tabs = len(line) - len(line.lstrip("\t"))

                # let/in should be at 4 tabs
                if stripped.lower() == "let" and tabs != 4:
                    r.error(f"{fname}:{i+1}: 'let' at {tabs} tabs (expected 4)")
                elif stripped.lower() in ("in",) and tabs != 4:
                    r.error(f"{fname}:{i+1}: 'in' at {tabs} tabs (expected 4)")
                # Content inside let should be at 4 tabs
                elif in_source and stripped.lower() not in ("let", "in") and tabs > 0:
                    if tabs < 3:
                        in_source = False  # Exited source block

                # Check for content on same line as source =
                if i == source_line and stripped:
                    if not re.match(r"^\t\tsource\s*=\s*.+", lines[i-1] if i > 0 else ""):
                        pass  # ok, content on next line

                # End of source block
                if tabs <= 2:
                    in_source = False

                # M variable name check: no &, +, -, * in identifiers
                if in_source and stripped and not stripped.startswith("//"):
                    vm = re.match(r"^([A-Za-z_]\S*)\s*=\s", stripped)
                    if vm:
                        var = vm.group(1)
                        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", var) and var != "Source":
                            r.error(f"{fname}:{i+1}: M variable '{var}' has invalid chars")

    r.ok("Partition indentation checked")


# ---------------------------------------------------------------------------
# 6. DAX expression validity
# ---------------------------------------------------------------------------

def check_dax_expressions(out: str, r: CheckResult) -> None:
    r.section("DAX")
    sm_def = _find_sm_def(out)
    if not sm_def:
        return
    tables_dir = os.path.join(sm_def, "tables")
    if not os.path.isdir(tables_dir):
        return

    bad_patterns = [
        (re.compile(r"\bTHEN\b", re.IGNORECASE), "IF/THEN/ELSE (VB/SQL syntax, not DAX)"),
        (re.compile(r"\bELSEIF\b", re.IGNORECASE), "ELSEIF (not valid DAX)"),
        (re.compile(r"@\w+\s*\("), "Essbase @function (untranslated)"),
        (re.compile(r"\[\["), "Double brackets [[col]]"),
        (re.compile(r"\{tbl\}"), "{tbl} placeholder leaked"),
        (re.compile(r"\bEND\b(?!\s*IF)", re.IGNORECASE), "Stray END keyword"),
    ]

    issues = 0
    for fname in sorted(os.listdir(tables_dir)):
        if not fname.endswith(".tmdl"):
            continue
        content = _read(os.path.join(tables_dir, fname))
        for line_num, line in enumerate(content.split("\n"), 1):
            # Only check calculated column / measure expressions
            m = re.match(r"^\t(column|measure)\s+(?:'[^']+'\s*=\s*|[^\s=]+\s*=\s*)(.+)", line)
            if not m:
                continue
            kind = m.group(1)
            expr = m.group(2)

            # Skip triple-backtick openers
            if expr.strip() == "```":
                continue

            # Skip FIND('@', ...) which is valid DAX
            expr_check = re.sub(r"FIND\s*\([^)]*@[^)]*\)", "", expr)

            for pat, desc in bad_patterns:
                if pat.search(expr_check):
                    r.error(f"{fname}:{line_num}: {kind} has {desc}: {expr[:80]}")
                    issues += 1
                    break

            # Unbalanced parentheses
            opens = expr.count("(")
            closes = expr.count(")")
            if opens != closes:
                r.error(f"{fname}:{line_num}: unbalanced parens ({opens} open, {closes} close)")
                issues += 1

    if issues == 0:
        r.ok("All DAX expressions valid")
    else:
        r.error(f"{issues} invalid DAX expressions found")


# ---------------------------------------------------------------------------
# 7. TMDL syntax checks (orphaned ///, description:, tabs vs spaces)
# ---------------------------------------------------------------------------

def check_tmdl_syntax(out: str, r: CheckResult) -> None:
    r.section("TMDL Syntax")
    sm_def = _find_sm_def(out)
    if not sm_def:
        return

    issues = 0
    for root, dirs, files in os.walk(sm_def):
        for fname in files:
            if not fname.endswith(".tmdl"):
                continue
            path = os.path.join(root, fname)
            content = _read(path)
            rel = os.path.relpath(path, sm_def)

            # Orphaned ///
            for i, line in enumerate(content.split("\n"), 1):
                stripped = line.strip()
                if stripped.startswith("///") and not stripped.startswith("/// <"):
                    r.error(f"{rel}:{i}: orphaned /// comment")
                    issues += 1

            # Invalid description: property
            if re.search(r"^\t+description:", content, re.MULTILINE):
                r.error(f"{rel}: invalid 'description:' property (not valid TMDL)")
                issues += 1

            # Mixed tabs and spaces in indentation
            # (skip lines inside source = blocks and triple-backtick expression blocks
            # — M code and multi-line DAX use spaces legitimately)
            in_source_block = False
            in_backtick_block = False
            for i, line in enumerate(content.split("\n"), 1):
                stripped = line.strip()
                if re.match(r"^\t\tsource\s*=\s*$", line):
                    in_source_block = True
                    continue
                if in_source_block:
                    tabs = len(line) - len(line.lstrip("\t"))
                    if tabs <= 1 and stripped:
                        in_source_block = False
                    else:
                        continue  # skip M expression content
                # Track triple-backtick blocks (multi-line DAX expressions)
                if stripped == "```" or stripped.endswith("= ```"):
                    in_backtick_block = not in_backtick_block
                    continue
                if in_backtick_block:
                    continue  # skip DAX expression content
                if line and line[0] == "\t":
                    indent = line[:len(line) - len(line.lstrip())]
                    if " " in indent:
                        r.error(f"{rel}:{i}: mixed tabs and spaces")
                        issues += 1
                        break

            # Ensure file ends with newline
            if content and not content.endswith("\n"):
                r.warn(f"{rel}: file doesn't end with newline")

    if issues == 0:
        r.ok("TMDL syntax clean (no orphaned ///, no description:, no mixed indent)")


# ---------------------------------------------------------------------------
# 8. Expressions.tmdl validation
# ---------------------------------------------------------------------------

def check_expressions(out: str, r: CheckResult) -> None:
    r.section("Expressions")
    sm_def = _find_sm_def(out)
    if not sm_def:
        return

    expr_path = os.path.join(sm_def, "expressions.tmdl")
    if not os.path.exists(expr_path):
        r.warn("No expressions.tmdl (optional)")
        return

    content = _read(expr_path)
    lines = content.strip().split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        # Each expression line should start with "expression"
        if not stripped.startswith("expression "):
            r.error(f"expressions.tmdl:{i}: line doesn't start with 'expression'")
            continue

        # Check for meta [...] tag
        if "meta [" not in stripped:
            r.warn(f"expressions.tmdl:{i}: missing meta tag")

        # Check for IsParameterQuery
        if "IsParameterQuery=true" not in stripped and "IsParameterQuery = true" not in stripped:
            r.warn(f"expressions.tmdl:{i}: missing IsParameterQuery=true")

    r.ok(f"expressions.tmdl: {len(lines)} expressions checked")


# ---------------------------------------------------------------------------
# 9. Database.tmdl validation
# ---------------------------------------------------------------------------

def check_database(out: str, r: CheckResult) -> None:
    r.section("Database")
    sm_def = _find_sm_def(out)
    if not sm_def:
        return

    db_path = os.path.join(sm_def, "database.tmdl")
    if not os.path.exists(db_path):
        r.error("database.tmdl missing")
        return

    content = _read(db_path)
    if not content.startswith("database"):
        r.error("database.tmdl: doesn't start with 'database'")

    m = re.search(r"compatibilityLevel:\s*(\d+)", content)
    if m:
        level = int(m.group(1))
        if level >= 1550:
            r.ok(f"compatibilityLevel: {level}")
        else:
            r.warn(f"compatibilityLevel {level} is very old (expected ≥ 1550)")
    else:
        r.error("database.tmdl: missing compatibilityLevel")


# ---------------------------------------------------------------------------
# 10. Model.tmdl header validation
# ---------------------------------------------------------------------------

def check_model_header(out: str, r: CheckResult) -> None:
    r.section("Model Header")
    sm_def = _find_sm_def(out)
    if not sm_def:
        return

    model_path = os.path.join(sm_def, "model.tmdl")
    content = _read(model_path)

    if not content.startswith("model "):
        r.error("model.tmdl: doesn't start with 'model'")

    if "culture:" not in content:
        r.error("model.tmdl: missing culture:")
    else:
        r.ok("model.tmdl: culture present")

    if "defaultPowerBIDataSourceVersion:" not in content:
        r.warn("model.tmdl: missing defaultPowerBIDataSourceVersion")
    else:
        r.ok("model.tmdl: defaultPowerBIDataSourceVersion present")

    # Check for lineageTag at model level (invalid)
    first_ref = content.find("ref ")
    if first_ref > 0:
        header = content[:first_ref]
        if "lineageTag:" in header:
            r.error("model.tmdl: lineageTag at model level (invalid)")
        else:
            r.ok("No invalid lineageTag at model level")


# ---------------------------------------------------------------------------
# 11. Report.json content check
# ---------------------------------------------------------------------------

def check_report_json(out: str, r: CheckResult) -> None:
    r.section("Report JSON")
    rpt_dirs = [d for d in Path(out).iterdir() if d.is_dir() and "Report" in d.name]
    if not rpt_dirs:
        return

    rpt_json = rpt_dirs[0] / "definition" / "report.json"
    if not rpt_json.exists():
        r.error("report.json missing")
        return

    data = _read_json(str(rpt_json))

    # $schema
    schema = data.get("$schema", "")
    if "report/definition/report" in schema:
        r.ok(f"report.json $schema OK")
    else:
        r.error(f"report.json: unexpected $schema: {schema}")

    # themeCollection
    theme = data.get("themeCollection", {})
    base_theme = theme.get("baseTheme", {})
    if base_theme.get("name"):
        r.ok(f"report.json: theme = {base_theme['name']}")
    else:
        r.warn("report.json: no base theme name")

    if "reportVersionAtImport" in base_theme:
        r.ok(f"report.json: reportVersionAtImport = {base_theme['reportVersionAtImport']}")
    else:
        r.warn("report.json: missing reportVersionAtImport")


# ---------------------------------------------------------------------------
# 12. Page files check
# ---------------------------------------------------------------------------

def check_pages(out: str, r: CheckResult) -> None:
    r.section("Pages")
    rpt_dirs = [d for d in Path(out).iterdir() if d.is_dir() and "Report" in d.name]
    if not rpt_dirs:
        return

    pages_dir = rpt_dirs[0] / "definition" / "pages"
    if not pages_dir.exists():
        r.warn("No pages/ folder")
        return

    page_folders = [d for d in pages_dir.iterdir() if d.is_dir()]
    valid = 0
    for pf in page_folders:
        page_json = pf / "page.json"
        if page_json.exists():
            try:
                data = _read_json(str(page_json))
                display_name = data.get("displayName", "Untitled")
                valid += 1
            except (json.JSONDecodeError, UnicodeDecodeError):
                r.error(f"Page {pf.name}/page.json: invalid JSON")
        else:
            r.error(f"Page {pf.name}: missing page.json")

        # Check for visuals
        visuals_dir = pf / "visuals"
        if visuals_dir.exists():
            vis_count = len([v for v in visuals_dir.iterdir() if v.is_dir()])
            if vis_count == 0:
                r.warn(f"Page {pf.name}: no visuals")

    if valid > 0:
        r.ok(f"{valid} valid pages with page.json")


# ---------------------------------------------------------------------------
# 13. Triple backtick block validation
# ---------------------------------------------------------------------------

def check_backtick_blocks(out: str, r: CheckResult) -> None:
    r.section("Backticks")
    sm_def = _find_sm_def(out)
    if not sm_def:
        return

    issues = 0
    for root, dirs, files_list in os.walk(sm_def):
        for fname in files_list:
            if not fname.endswith(".tmdl"):
                continue
            path = os.path.join(root, fname)
            content = _read(path)
            rel = os.path.relpath(path, sm_def)

            # Count backtick openers and closers
            backtick_positions = [i for i, c in enumerate(content) if content[i:i+3] == "```"]
            if len(backtick_positions) % 2 != 0:
                r.error(f"{rel}: unmatched triple backticks ({len(backtick_positions)} found)")
                issues += 1

    if issues == 0:
        r.ok("All triple backtick blocks properly paired")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _find_sm_def(out: str) -> str | None:
    """Find the SemanticModel/definition folder."""
    for d in Path(out).iterdir():
        if d.is_dir() and "SemanticModel" in d.name:
            defn = d / "definition"
            if defn.exists():
                return str(defn)
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Verify all generated .pbip project files")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, help="Migration output directory")
    args = parser.parse_args()

    out = args.output_dir
    if not os.path.isdir(out):
        print(f"ERROR: Output directory not found: {out}")
        return 1

    r = CheckResult()

    check_project_structure(out, r)
    check_json_files(out, r)
    check_pbip_references(out, r)
    check_model_refs(out, r)
    check_partitions(out, r)
    check_dax_expressions(out, r)
    check_tmdl_syntax(out, r)
    check_expressions(out, r)
    check_database(out, r)
    check_model_header(out, r)
    check_report_json(out, r)
    check_pages(out, r)
    check_backtick_blocks(out, r)

    print(r.summary())
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
