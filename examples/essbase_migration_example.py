#!/usr/bin/env python3
"""Essbase → Fabric & Power BI migration example.

Demonstrates end-to-end migration of all three Essbase sample cubes
through the full pipeline:

  1. Parse outline XML (EssbaseOutlineParser)
  2. Convert to SemanticModelIR (EssbaseToSemanticModelConverter)
  3. Translate calc scripts → DAX (EssbaseCalcTranslator)
  4. Generate TMDL semantic model (generate_tmdl)
  5. Generate DDL for dimension tables (generate_create_table)
  6. Map security filters → RLS roles
  7. Map substitution vars → What-if parameters
  8. Produce HTML + Markdown migration reports

Usage::

    py -3 examples/essbase_migration_example.py
    py -3 examples/essbase_migration_example.py -o output/essbase_report
    py -3 examples/essbase_migration_example.py --cube medium_finance.xml
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.connectors.essbase_connector import (
    EssbaseCalcScript,
    EssbaseCalcTranslator,
    EssbaseFilter,
    EssbaseMdxTranslator,
    EssbaseOutlineParser,
    EssbaseSubstitutionVar,
    ParsedOutline,
)
from src.connectors.essbase_semantic_bridge import (
    EssbaseConversionResult,
    EssbaseToSemanticModelConverter,
)
from src.agents.schema.ddl_generator import generate_create_table
from src.agents.schema.type_mapper import TargetPlatform
from src.agents.semantic.tmdl_generator import generate_tmdl

logger = logging.getLogger(__name__)

ESSBASE_SAMPLES_DIR = _PROJECT_ROOT / "examples" / "essbase_samples"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "output" / "essbase_migration"


# ═════════════════════════════════════════════════════════════════════
# Result container
# ═════════════════════════════════════════════════════════════════════


@dataclass
class EssbaseMigrationResult:
    """Aggregated result of an Essbase → Fabric migration."""

    cubes_processed: int = 0
    cube_results: list[dict[str, Any]] = field(default_factory=list)

    # Totals
    total_dimensions: int = 0
    total_members: int = 0
    total_dynamic_calcs: int = 0
    total_tables: int = 0
    total_measures: int = 0
    total_relationships: int = 0
    total_hierarchies: int = 0
    total_tmdl_files: int = 0
    total_ddl_tables: int = 0
    total_calc_translations: int = 0
    total_rls_roles: int = 0
    total_whatif_params: int = 0

    # Translation quality
    high_confidence_count: int = 0  # ≥ 0.7
    medium_confidence_count: int = 0  # 0.5–0.7
    low_confidence_count: int = 0  # < 0.5

    warnings: list[str] = field(default_factory=list)
    review_items: list[str] = field(default_factory=list)

    elapsed_seconds: float = 0.0
    output_dir: str = ""

    def summary(self) -> str:
        lines = [
            f"Essbase → Fabric migration complete in {self.elapsed_seconds:.1f}s",
            f"  Cubes processed:      {self.cubes_processed}",
            f"  Dimensions:           {self.total_dimensions}",
            f"  Members:              {self.total_members}",
            f"  Dynamic calcs:        {self.total_dynamic_calcs}",
            f"  Semantic tables:      {self.total_tables}",
            f"  DAX measures:         {self.total_measures}",
            f"  Relationships:        {self.total_relationships}",
            f"  Hierarchies:          {self.total_hierarchies}",
            f"  TMDL files:           {self.total_tmdl_files}",
            f"  DDL tables:           {self.total_ddl_tables}",
            f"  Calc translations:    {self.total_calc_translations}",
            f"    High confidence:    {self.high_confidence_count}",
            f"    Medium confidence:  {self.medium_confidence_count}",
            f"    Low confidence:     {self.low_confidence_count}",
            f"  RLS roles:            {self.total_rls_roles}",
            f"  What-if params:       {self.total_whatif_params}",
            f"  Warnings:             {len(self.warnings)}",
            f"  Review items:         {len(self.review_items)}",
            f"  Output:               {self.output_dir}",
        ]
        return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════
# Synthetic data: calc scripts, filters, substitution vars
# ═════════════════════════════════════════════════════════════════════

# Calc scripts that exercise different translation complexity levels
SAMPLE_CALC_SCRIPTS: dict[str, list[EssbaseCalcScript]] = {
    "simple_budget": [
        EssbaseCalcScript(
            name="CalcGrossProfit",
            content="Revenue - COGS",
            application="SimpleBudget",
            database="Budget",
        ),
    ],
    "medium_finance": [
        EssbaseCalcScript(
            name="CalcGrossProfit",
            content="Revenue - COGS",
            application="FinanceCorp",
            database="Finance",
        ),
        EssbaseCalcScript(
            name="CalcOperatingIncome",
            content="Gross Profit - Operating Expenses",
            application="FinanceCorp",
            database="Finance",
        ),
        EssbaseCalcScript(
            name="CalcGrossMarginPct",
            content="@ROUND(Gross Profit % Revenue, 4)",
            application="FinanceCorp",
            database="Finance",
        ),
        EssbaseCalcScript(
            name="CalcVariance",
            content="Actual - Budget",
            application="FinanceCorp",
            database="Finance",
        ),
        EssbaseCalcScript(
            name="CalcVariancePct",
            content="@ROUND((Actual - Budget) % Budget, 4)",
            application="FinanceCorp",
            database="Finance",
        ),
        EssbaseCalcScript(
            name="CalcYTD",
            content="@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))",
            application="FinanceCorp",
            database="Finance",
        ),
    ],
    "complex_planning": [
        EssbaseCalcScript(
            name="CalcGrossProfit",
            content="Revenue + COGS",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcEBITDA",
            content="Gross Profit + OpEx",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcEBIT",
            content="EBITDA + Depreciation",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcGrossMarginPct",
            content="@ROUND(Gross Profit % Revenue, 4)",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcEBITDAMarginPct",
            content="@ROUND(EBITDA % Revenue, 4)",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcRevPerFTE",
            content="@ROUND(Revenue / (Headcount SM + Headcount RD + Headcount GA), 0)",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcBudVariance",
            content="Actual - Budget",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcBudVariancePct",
            content="@ROUND((Actual - Budget) % Budget, 4)",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcYTD",
            content="@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcPriorYear",
            content="@PRIOR(Time, 12, @LEVMBRS(Time, 3))",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcYoYGrowth",
            content="@ROUND((Actual - @PRIOR(Actual, 1, @LEVMBRS(Scenario, 0))) % @PRIOR(Actual, 1, @LEVMBRS(Scenario, 0)), 4)",
            application="PlanCorp",
            database="Planning",
        ),
        EssbaseCalcScript(
            name="CalcCurrencyConvert",
            content="@CALCMBR(Local, @XREF(ExchangeRates, Rate))",
            application="PlanCorp",
            database="Planning",
            description="Currency conversion — unsupported pattern",
        ),
    ],
}

SAMPLE_FILTERS: dict[str, list[EssbaseFilter]] = {
    "simple_budget": [],
    "medium_finance": [
        EssbaseFilter(
            name="RegionalAccess",
            rows=[
                {"member": "North America", "access": "read"},
                {"member": "EMEA", "access": "read"},
                {"member": "APAC", "access": "none"},
            ],
        ),
    ],
    "complex_planning": [
        EssbaseFilter(
            name="RegionalManager",
            rows=[
                {"member": "Americas", "access": "write"},
                {"member": "EMEA", "access": "read"},
                {"member": "APAC", "access": "none"},
            ],
        ),
        EssbaseFilter(
            name="FinanceAnalyst",
            rows=[
                {"member": "Actual", "access": "read"},
                {"member": "Budget", "access": "read"},
                {"member": "Forecast", "access": "none"},
            ],
        ),
        EssbaseFilter(
            name="PlanningAdmin",
            rows=[
                {"member": "Worldwide", "access": "write"},
                {"member": "Actual", "access": "write"},
                {"member": "Budget", "access": "write"},
                {"member": "Forecast", "access": "write"},
            ],
        ),
    ],
}

SAMPLE_SUBST_VARS: dict[str, list[EssbaseSubstitutionVar]] = {
    "simple_budget": [],
    "medium_finance": [
        EssbaseSubstitutionVar("CurMonth", "Jun", "application"),
        EssbaseSubstitutionVar("CurYear", "FY2024", "application"),
    ],
    "complex_planning": [
        EssbaseSubstitutionVar("CurMonth", "Mar-24", "application"),
        EssbaseSubstitutionVar("CurYear", "FY2024", "application"),
        EssbaseSubstitutionVar("BudYear", "FY2024", "database"),
        EssbaseSubstitutionVar("FcstStart", "Apr-24", "database"),
        EssbaseSubstitutionVar("BaseCurrency", "USD", "server"),
    ],
}


# ═════════════════════════════════════════════════════════════════════
# Pipeline steps
# ═════════════════════════════════════════════════════════════════════


def parse_outline(xml_path: Path) -> ParsedOutline:
    """Step 1 — Parse Essbase outline XML."""
    parser = EssbaseOutlineParser()
    text = xml_path.read_text(encoding="utf-8")
    app_name = xml_path.stem.replace("_", " ").title().replace(" ", "")
    outline = parser.parse_xml(text, app=app_name, db=xml_path.stem)
    return outline


def convert_to_semantic_model(
    outline: ParsedOutline,
    cube_key: str,
) -> EssbaseConversionResult:
    """Step 2 — Convert outline → SemanticModelIR via the bridge."""
    converter = EssbaseToSemanticModelConverter()
    return converter.convert(
        outline,
        model_name=f"Essbase_{cube_key}",
        calc_scripts=SAMPLE_CALC_SCRIPTS.get(cube_key, []),
        filters=SAMPLE_FILTERS.get(cube_key, []),
        substitution_vars=SAMPLE_SUBST_VARS.get(cube_key, []),
    )


def generate_tmdl_output(
    conversion: EssbaseConversionResult,
    cube_dir: Path,
) -> dict[str, str]:
    """Step 3 — Generate TMDL files from SemanticModelIR."""
    tmdl_result = generate_tmdl(
        conversion.ir,
        lakehouse_name="EssbaseLakehouse",
    )

    # Write TMDL files to disk
    tmdl_dir = cube_dir / "SemanticModel"
    tmdl_dir.mkdir(parents=True, exist_ok=True)
    for fname, content in tmdl_result.files.items():
        fpath = tmdl_dir / fname
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")

    return tmdl_result.files


def generate_ddl_output(
    conversion: EssbaseConversionResult,
    cube_dir: Path,
) -> list[dict[str, str]]:
    """Step 4 — Generate DDL for dimension tables."""
    ddl_results = []
    for table in conversion.ir.tables:
        cols = [
            {"name": c.name, "data_type": c.data_type}
            for c in table.columns
            if c.kind.value in ("key", "direct", "column")
        ]
        if not cols:
            continue
        ddl = generate_create_table(
            table_name=table.name,
            columns=cols,
            platform=TargetPlatform.LAKEHOUSE,
        )
        ddl_results.append({"table": table.name, "ddl": ddl})

    if ddl_results:
        ddl_text = "\n\n".join(d["ddl"] for d in ddl_results)
        (cube_dir / "generated_ddl.sql").write_text(ddl_text, encoding="utf-8")

    return ddl_results


def translate_additional_calcs(
    cube_key: str,
) -> list[dict[str, Any]]:
    """Step 5 — Translate additional calc script formulas."""
    translator = EssbaseCalcTranslator()
    mdx_translator = EssbaseMdxTranslator()
    results = []

    for script in SAMPLE_CALC_SCRIPTS.get(cube_key, []):
        tr = translator.translate(script)
        results.append({
            "name": tr.source_name,
            "source": tr.source_formula,
            "dax": tr.dax_expression,
            "confidence": tr.confidence,
            "method": tr.method,
            "warnings": tr.warnings,
        })

    # Example MDX translations for complex cubes
    if cube_key == "complex_planning":
        mdx_samples = [
            ("YTD Revenue", "SELECT {[Measures].[Revenue]} ON COLUMNS, YTD([Time].CurrentMember) ON ROWS FROM Planning"),
            ("Top 5 Products", "SELECT TopCount([Product].Children, 5, [Measures].[Revenue]) ON ROWS FROM Planning"),
            ("Variance Filter", "SELECT Filter([Entity].Children, IIF([Measures].[Bud Variance] > 0, True, False)) ON ROWS FROM Planning"),
        ]
        for name, mdx in mdx_samples:
            tr = mdx_translator.translate(mdx, source_name=name)
            results.append({
                "name": tr.source_name,
                "source": tr.source_formula,
                "dax": tr.dax_expression,
                "confidence": tr.confidence,
                "method": "mdx_rules",
                "warnings": tr.warnings,
            })

    return results


def build_migration_report_md(
    result: EssbaseMigrationResult,
) -> str:
    """Step 6 — Build a Markdown migration report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Essbase → Fabric Migration Report",
        "",
        f"> **Generated:** {now}  ",
        f"> **Cubes:** {result.cubes_processed} | **Elapsed:** {result.elapsed_seconds:.1f}s  ",
        f"> **Output:** `{result.output_dir}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Cubes processed | **{result.cubes_processed}** |",
        f"| Dimensions | {result.total_dimensions} |",
        f"| Members | {result.total_members} |",
        f"| Dynamic calcs | {result.total_dynamic_calcs} |",
        f"| Semantic tables | {result.total_tables} |",
        f"| DAX measures | {result.total_measures} |",
        f"| Relationships | {result.total_relationships} |",
        f"| Hierarchies | {result.total_hierarchies} |",
        f"| TMDL files | {result.total_tmdl_files} |",
        f"| DDL tables | {result.total_ddl_tables} |",
        f"| Calc translations | {result.total_calc_translations} |",
        f"| RLS roles | {result.total_rls_roles} |",
        f"| What-if params | {result.total_whatif_params} |",
        "",
        "## Translation Confidence",
        "",
        "| Level | Count |",
        "|-------|-------|",
        f"| High (≥0.7) | {result.high_confidence_count} |",
        f"| Medium (0.5–0.7) | {result.medium_confidence_count} |",
        f"| Low (<0.5) | {result.low_confidence_count} |",
        "",
    ]

    # Per-cube details
    for cube in result.cube_results:
        lines.extend([
            f"## Cube: {cube['name']}",
            "",
            f"- **Dimensions:** {cube['dimensions']}",
            f"- **Members:** {cube['members']}",
            f"- **Dynamic calcs:** {cube['dynamic_calcs']}",
            f"- **Tables generated:** {cube['tables']}",
            f"- **Measures:** {cube['measures']}",
            f"- **Relationships:** {cube['relationships']}",
            f"- **TMDL files:** {cube['tmdl_files']}",
            f"- **DDL tables:** {cube['ddl_tables']}",
            "",
        ])

        if cube.get("calc_translations"):
            lines.extend([
                "### Calc Script Translations",
                "",
                "| Script | Source | DAX | Confidence |",
                "|--------|--------|-----|------------|",
            ])
            for ct in cube["calc_translations"]:
                src = ct["source"][:40].replace("|", "\\|")
                dax = ct["dax"][:50].replace("|", "\\|")
                lines.append(f"| {ct['name']} | `{src}` | `{dax}` | {ct['confidence']:.0%} |")
            lines.append("")

        if cube.get("rls_roles"):
            lines.extend([
                "### RLS Roles",
                "",
                "| Role | Filter |",
                "|------|--------|",
            ])
            for role in cube["rls_roles"]:
                lines.append(f"| {role['name']} | `{role['filter'][:60]}` |")
            lines.append("")

        if cube.get("whatif_params"):
            lines.extend([
                "### What-If Parameters",
                "",
                "| Parameter | Value | DAX Variable |",
                "|-----------|-------|-------------|",
            ])
            for p in cube["whatif_params"]:
                lines.append(f"| {p['name']} | {p['value']} | `{p['dax']}` |")
            lines.append("")

    # Warnings
    if result.warnings:
        lines.extend(["## Warnings", ""])
        for w in result.warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Review items
    if result.review_items:
        lines.extend(["## Items Requiring Manual Review", ""])
        for r in result.review_items:
            lines.append(f"- {r}")
        lines.append("")

    # Mapping reference
    lines.extend([
        "## Essbase → Fabric Mapping Reference",
        "",
        "| Essbase Concept | Fabric / Power BI Equivalent |",
        "|----------------|------------------------------|",
        "| Cube | Semantic Model |",
        "| Dimension (Accounts) | DAX Measures + Calculated Columns |",
        "| Dimension (Time) | Date Table (mark as date table) |",
        "| Dimension (Regular, Sparse) | Dimension Table with hierarchy |",
        "| Dense Dimension | Columns in fact table |",
        "| Dynamic Calc Member | DAX Measure |",
        "| Calc Script | DAX Measures / Calculated Tables |",
        "| Essbase Filter | RLS Role (DAX filter) |",
        "| Substitution Variable | What-if Parameter |",
        "| UDA | Boolean column on dimension table |",
        "| Shared Member | Alternate hierarchy |",
        "",
        "---",
        f"*Generated by OAC-to-Fabric Migration Accelerator — {now}*",
    ])
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════
# Main pipeline
# ═════════════════════════════════════════════════════════════════════


def run_essbase_migration(
    *,
    samples_dir: Path = ESSBASE_SAMPLES_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    specific_cube: str | None = None,
    verbose: bool = False,
) -> EssbaseMigrationResult:
    """Execute the Essbase → Fabric migration pipeline."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s")

    start = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = EssbaseMigrationResult(output_dir=str(output_dir))

    # Discover XML outlines
    if specific_cube:
        xml_files = [samples_dir / specific_cube]
    else:
        xml_files = sorted(samples_dir.glob("*.xml"))

    for xml_path in xml_files:
        if not xml_path.exists():
            result.warnings.append(f"File not found: {xml_path}")
            continue

        cube_key = xml_path.stem
        cube_dir = output_dir / cube_key
        cube_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  Processing: {xml_path.name}")
        print(f"{'='*60}")

        # 1. Parse outline
        outline = parse_outline(xml_path)
        if not outline.is_valid:
            result.warnings.append(f"Invalid outline: {xml_path.name} — {outline.errors}")
            continue

        print(f"  Dimensions:    {len(outline.dimensions)}")
        print(f"  Members:       {outline.total_members}")
        print(f"  Dynamic calcs: {outline.total_dynamic_calcs}")

        # 2. Convert to semantic model
        conversion = convert_to_semantic_model(outline, cube_key)
        print(f"  Tables:        {conversion.table_count}")
        print(f"  Measures:      {conversion.measure_count}")
        print(f"  Relationships: {conversion.relationship_count}")
        print(f"  RLS roles:     {len(conversion.rls_roles)}")
        print(f"  What-if:       {len(conversion.whatif_parameters)}")

        # 3. Generate TMDL
        tmdl_files = generate_tmdl_output(conversion, cube_dir)
        print(f"  TMDL files:    {len(tmdl_files)}")

        # 4. Generate DDL
        ddl_results = generate_ddl_output(conversion, cube_dir)
        print(f"  DDL tables:    {len(ddl_results)}")

        # 5. Translate calc scripts + MDX
        calc_translations = translate_additional_calcs(cube_key)
        print(f"  Translations:  {len(calc_translations)}")

        # Count confidence levels
        for ct in calc_translations:
            if ct["confidence"] >= 0.7:
                result.high_confidence_count += 1
            elif ct["confidence"] >= 0.5:
                result.medium_confidence_count += 1
            else:
                result.low_confidence_count += 1

        # Count hierarchies
        hierarchy_count = sum(len(t.hierarchies) for t in conversion.ir.tables)

        # Build cube result
        cube_result = {
            "name": cube_key,
            "file": xml_path.name,
            "dimensions": len(outline.dimensions),
            "members": outline.total_members,
            "dynamic_calcs": outline.total_dynamic_calcs,
            "tables": conversion.table_count,
            "measures": conversion.measure_count,
            "relationships": conversion.relationship_count,
            "hierarchies": hierarchy_count,
            "tmdl_files": len(tmdl_files),
            "ddl_tables": len(ddl_results),
            "calc_translations": calc_translations,
            "rls_roles": [
                {"name": r.name, "filter": r.filter_expression}
                for r in conversion.rls_roles
            ],
            "whatif_params": [
                {"name": p.name, "value": p.current_value, "dax": p.dax_variable}
                for p in conversion.whatif_parameters
            ],
        }
        result.cube_results.append(cube_result)

        # Accumulate totals
        result.cubes_processed += 1
        result.total_dimensions += len(outline.dimensions)
        result.total_members += outline.total_members
        result.total_dynamic_calcs += outline.total_dynamic_calcs
        result.total_tables += conversion.table_count
        result.total_measures += conversion.measure_count
        result.total_relationships += conversion.relationship_count
        result.total_hierarchies += hierarchy_count
        result.total_tmdl_files += len(tmdl_files)
        result.total_ddl_tables += len(ddl_results)
        result.total_calc_translations += len(calc_translations)
        result.total_rls_roles += len(conversion.rls_roles)
        result.total_whatif_params += len(conversion.whatif_parameters)
        result.warnings.extend(conversion.warnings)
        result.review_items.extend(conversion.review_items)

    # 6. Generate reports
    result.elapsed_seconds = time.perf_counter() - start

    md_report = build_migration_report_md(result)
    md_path = output_dir / "essbase_migration_report.md"
    md_path.write_text(md_report, encoding="utf-8")

    print(f"\n{'='*60}")
    print(result.summary())
    print(f"\n  Report: {md_path}")

    return result


# ═════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Essbase → Fabric & Power BI migration example",
    )
    parser.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cube", type=str, help="Specific XML file name (e.g. medium_finance.xml)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    run_essbase_migration(
        output_dir=args.output_dir,
        specific_cube=args.cube,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
