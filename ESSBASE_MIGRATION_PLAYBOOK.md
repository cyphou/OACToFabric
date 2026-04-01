# Essbase to Fabric Migration Playbook

> **Audience**: Migration engineers, Essbase admins, Power BI developers  
> **Prerequisites**: Python 3.12+, `pip install -e ".[dev]"`  
> **Samples**: `examples/essbase_samples/` (simple, medium, complex)

---

## Table of Contents

- [Quick Start (5 minutes)](#quick-start-5-minutes)
- [Step 1 — Parse & Inventory](#step-1--parse--inventory)
- [Step 2 — Assess Complexity](#step-2--assess-complexity)
- [Step 3 — Translate Calc Scripts → DAX](#step-3--translate-calc-scripts--dax)
- [Step 4 — Translate MDX → DAX](#step-4--translate-mdx--dax)
- [Step 5 — Convert Outline → Semantic Model](#step-5--convert-outline--semantic-model)
- [Step 6 — Generate TMDL Artifacts](#step-6--generate-tmdl-artifacts)
- [Step 7 — Migrate Security (Filters → RLS)](#step-7--migrate-security-filters--rls)
- [Step 8 — Migrate Substitution Variables](#step-8--migrate-substitution-variables)
- [Step 9 — Validate](#step-9--validate)
- [Mapping Quick-Reference](#mapping-quick-reference)
- [Worked Examples by Complexity](#worked-examples-by-complexity)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (5 minutes)

```python
from src.connectors.essbase_connector import EssbaseOutlineParser, EssbaseCalcTranslator
from src.connectors.essbase_semantic_bridge import EssbaseToSemanticModelConverter

# 1. Parse outline
parser = EssbaseOutlineParser()
with open("examples/essbase_samples/simple_budget.xml") as f:
    outline = parser.parse_xml(f.read(), app="Budget", db="Plan")

print(f"Dimensions: {outline.dimension_names}")
print(f"Members:    {outline.total_members}")
print(f"Dynamic:    {outline.total_dynamic_calcs}")

# 2. Convert to semantic model
converter = EssbaseToSemanticModelConverter()
result = converter.convert(outline, model_name="BudgetModel")

print(f"Tables:        {result.table_count}")
print(f"Measures:      {result.measure_count}")
print(f"Relationships: {result.relationship_count}")
print(f"Warnings:      {len(result.warnings)}")
```

**Expected output** (simple_budget.xml):
```
Dimensions: ['Time', 'Accounts', 'Product']
Members:    18
Dynamic:    1
Tables:        3   (Fact_BudgetModel, Time, Product)
Measures:      3   (Revenue, COGS, Gross Profit)
Relationships: 2   (Product→Fact, Time→Fact)
Warnings:      0
```

---

## Step 1 — Parse & Inventory

### From XML (outline export / MaxL dump)

```python
from src.connectors.essbase_connector import EssbaseOutlineParser

parser = EssbaseOutlineParser()

# XML string or bytes
with open("examples/essbase_samples/medium_finance.xml") as f:
    outline = parser.parse_xml(f.read(), app="Finance", db="Plan")

assert outline.is_valid
print(f"App/DB:     {outline.application}/{outline.database}")
print(f"Dimensions: {len(outline.dimensions)}")
for dim in outline.dimensions:
    print(f"  {dim.name:20s}  type={dim.dimension_type:10s}  "
          f"storage={dim.storage_type:6s}  members={len(dim.members)}")
```

**Expected output** (medium_finance.xml):
```
App/DB:     Finance/Plan
Dimensions: 5
  Time                  type=time        storage=dense   members=18
  Accounts              type=accounts    storage=dense   members=13
  Entity                type=regular     storage=sparse  members=11
  Product               type=regular     storage=sparse  members=8
  Scenario              type=regular     storage=sparse  members=5
```

### From JSON (Essbase REST API response)

```python
import json
from src.connectors.essbase_connector import EssbaseOutlineParser

parser = EssbaseOutlineParser()

with open("examples/essbase_samples/simple_budget.json") as f:
    data = json.load(f)

outline = parser.parse_json(data, app="Budget", db="Plan")
print(f"Dimensions: {outline.dimension_names}")
# ['Time', 'Accounts', 'Product']
```

### From live Essbase server (REST API)

```python
import asyncio
from src.connectors.essbase_connector import EssbaseConnector

async def discover_live():
    connector = EssbaseConnector()
    connected = await connector.connect({
        "server_url": "https://essbase.example.com:9000",
        "username": "admin",
        "password": "...",        # Use Key Vault in production
        "api_version": "v1",
    })
    if not connected:
        print("Connection failed")
        return

    assets = await connector.discover()
    for asset in assets:
        print(f"  {asset.asset_type:20s}  {asset.asset_id}")

    # Extract detailed metadata (enriches calc scripts with DAX translations)
    result = await connector.extract_metadata()
    for asset in result.assets:
        if asset.asset_type == "calcScript":
            print(f"  Calc: {asset.name}  confidence={asset.metadata.get('translation_confidence', 'N/A')}")

    await connector.disconnect()

asyncio.run(discover_live())
```

---

## Step 2 — Assess Complexity

Use the parsed outline properties to classify cubes into migration waves.

```python
def assess_complexity(outline):
    """Classify cube complexity for wave planning."""
    dim_count = len(outline.dimensions)
    member_count = outline.total_members
    dynamic_count = outline.total_dynamic_calcs
    calc_count = len(outline.calc_scripts)

    # Scoring
    score = 0
    if dim_count <= 3: score += 1
    elif dim_count <= 5: score += 2
    elif dim_count <= 7: score += 3
    else: score += 4

    if member_count <= 20: score += 1
    elif member_count <= 100: score += 2
    elif member_count <= 500: score += 3
    else: score += 4

    if dynamic_count <= 2: score += 0
    elif dynamic_count <= 10: score += 1
    else: score += 2

    score += min(calc_count, 3)

    # Classification
    if score <= 3: return "LOW"
    elif score <= 6: return "MEDIUM"
    elif score <= 9: return "HIGH"
    else: return "EXPERT"

# Example
for sample in ["simple_budget.xml", "medium_finance.xml", "complex_planning.xml"]:
    with open(f"examples/essbase_samples/{sample}") as f:
        outline = parser.parse_xml(f.read())
    complexity = assess_complexity(outline)
    print(f"  {sample:30s}  dims={len(outline.dimensions)}  "
          f"members={outline.total_members:3d}  dynamic={outline.total_dynamic_calcs}  "
          f"→ {complexity}")
```

**Expected output**:
```
  simple_budget.xml               dims=3  members= 18  dynamic=1  → LOW
  medium_finance.xml              dims=5  members= 55  dynamic=5  → MEDIUM
  complex_planning.xml            dims=7  members=115  dynamic=9  → HIGH
```

### Wave Planning Guide

| Complexity | Migration Wave | Approach |
|------------|---------------|----------|
| **LOW** | Wave 1 — automated | Full auto-translate, minimal review |
| **MEDIUM** | Wave 2 — guided | Auto-translate + spot-check calc scripts |
| **HIGH** | Wave 3 — assisted | Auto-translate + manual review of complex calcs |
| **EXPERT** | Wave 4 — supervised | LLM-assisted + SME review, cross-cube refs |

---

## Step 3 — Translate Calc Scripts → DAX

### Single formula

```python
from src.connectors.essbase_connector import EssbaseCalcTranslator

translator = EssbaseCalcTranslator()

# Direct mapping (confidence = 1.0)
r = translator.translate_formula("@SUM(Sales)")
print(f"DAX: {r.dax_expression}  confidence={r.confidence}")
# DAX: SUM(Sales)  confidence=1.0

# Parametric mapping (confidence = 0.7)
r = translator.translate_formula("@PRIOR(Revenue)")
print(f"DAX: {r.dax_expression}  confidence={r.confidence}")
# DAX: CALCULATE( /* @PRIOR */ Revenue)  confidence=0.7

# Complex mapping (confidence = 0.5)
r = translator.translate_formula("@PARENTVAL(Sales)")
print(f"DAX: {r.dax_expression}  confidence={r.confidence}  warnings={r.warnings}")
# DAX: CALCULATE( /* @PARENTVAL */ Sales)  confidence=0.5  warnings=[...]

# Unsupported (confidence = 0.2, needs manual DAX)
r = translator.translate_formula("@ALLOCATE(Cost, Product, Share)")
print(f"DAX: {r.dax_expression}  confidence={r.confidence}  method={r.method}")
# method=unsupported → needs manual DAX pattern
```

### Batch translation from parsed outline

```python
from src.connectors.essbase_connector import EssbaseCalcScript, EssbaseCalcTranslator

translator = EssbaseCalcTranslator()

# Simulate calc scripts extracted from medium_finance.xml formulas
scripts = [
    EssbaseCalcScript(name="GrossProfit", content="Revenue - COGS"),
    EssbaseCalcScript(name="OpIncome", content="Gross Profit - Operating Expenses"),
    EssbaseCalcScript(name="GrossMargin", content="@ROUND(Gross Profit % Revenue, 4)"),
    EssbaseCalcScript(name="YTD", content="@SUMRANGE(Time, @TODATE(Time, @CURRMBR(Time)))"),
]

results = translator.translate_batch(scripts)
for r in results:
    status = "✅" if r.confidence >= 0.7 else "⚠️" if r.confidence >= 0.5 else "❌"
    print(f"  {status} {r.source_name:20s}  conf={r.confidence:.0%}  → {r.dax_expression[:60]}")
```

**Expected output**:
```
  ✅ GrossProfit           conf=100%  → Revenue - COGS
  ✅ OpIncome              conf=100%  → Gross Profit - Operating Expenses
  ✅ GrossMargin           conf=100%  → ROUND(Gross Profit % Revenue, 4)
  ⚠️ YTD                   conf=50%   → CALCULATE(SUM( /* @SUMRANGE */ Time, CALCULATE( /* @TODA
```

### Confidence bands

| Confidence | Colour | Action |
|------------|--------|--------|
| **1.0** | Green | Auto-migrate, no review |
| **0.7** | Yellow | Review parameter bindings |
| **0.5** | Orange | Review DAX structure |
| **0.2** | Red | Manual DAX authoring required |

---

## Step 4 — Translate MDX → DAX

```python
from src.connectors.essbase_connector import EssbaseMdxTranslator

mdx = EssbaseMdxTranslator()

# Time intelligence
r = mdx.translate("YTD([Time].[Q4])")
print(f"DAX: {r.dax_expression}")
# CALCULATE(measure, DATESYTD([Time].[Q4]))

# Set operations
r = mdx.translate("Union(set1, set2)")
print(f"DAX: {r.dax_expression}")
# UNION(set1, set2)

# Conditional
r = mdx.translate("IIF([Measures].[Revenue] > 0, [Measures].[Revenue], 0)")
print(f"DAX: {r.dax_expression}")
# IF([Revenue] > 0, [Revenue], 0)
```

---

## Step 5 — Convert Outline → Semantic Model

### Full conversion (the core migration step)

```python
from src.connectors.essbase_connector import (
    EssbaseCalcScript, EssbaseFilter, EssbaseOutlineParser, EssbaseSubstitutionVar,
)
from src.connectors.essbase_semantic_bridge import EssbaseToSemanticModelConverter

parser = EssbaseOutlineParser()
converter = EssbaseToSemanticModelConverter()

# Parse medium-complexity cube
with open("examples/essbase_samples/medium_finance.xml") as f:
    outline = parser.parse_xml(f.read(), app="Finance", db="Plan")

# Provide extra calc scripts, filters, and substitution variables
calc_scripts = [
    EssbaseCalcScript(name="CalcAll", content="AGG(Entity); AGG(Product);",
                      application="Finance", database="Plan"),
]
filters = [
    EssbaseFilter(name="EMEA_Only", rows=[
        {"member": "EMEA", "access": "read"},
        {"member": "North America", "access": "none"},
        {"member": "APAC", "access": "none"},
    ]),
]
sub_vars = [
    EssbaseSubstitutionVar(name="CurMonth", value="Mar", scope="application"),
    EssbaseSubstitutionVar(name="CurYear", value="FY2024", scope="application"),
]

# Convert
result = converter.convert(
    outline,
    model_name="FinancePlan",
    calc_scripts=calc_scripts,
    filters=filters,
    substitution_vars=sub_vars,
)

# Inspect results
print("=== Semantic Model IR ===")
print(f"Model:          {result.ir.model_name}")
print(f"Tables:         {result.table_count}")
print(f"Measures:       {result.measure_count}")
print(f"Relationships:  {result.relationship_count}")
print()

print("=== Tables ===")
for table in result.ir.tables:
    cols = len(table.columns)
    hiers = len(table.hierarchies)
    date = " [DATE TABLE]" if table.is_date_table else ""
    print(f"  {table.name:30s}  columns={cols:2d}  hierarchies={hiers}{date}")

print()
print("=== Measures (in fact table) ===")
fact = result.ir.tables[0]
for col in fact.columns:
    if hasattr(col, 'kind') and str(col.kind) == "ColumnKind.MEASURE":
        expr = col.expression[:50] if col.expression else "N/A"
        print(f"  {col.name:25s}  → {expr}")

print()
print("=== Relationships ===")
for join in result.ir.joins:
    print(f"  {join.from_table}.{join.from_column} → {join.to_table}.{join.to_column}")

print()
print(f"=== RLS Roles: {len(result.rls_roles)} ===")
for role in result.rls_roles:
    print(f"  {role.name}: {role.filter_expression[:60]}")

print()
print(f"=== What-If Parameters: {len(result.whatif_parameters)} ===")
for p in result.whatif_parameters:
    print(f"  {p.name} = {p.current_value}  → {p.dax_variable}")

print()
print(f"=== Calc Translations: {len(result.calc_translations)} ===")
for t in result.calc_translations:
    print(f"  {t.source_name}: confidence={t.confidence:.0%}")

if result.warnings:
    print(f"\n=== Warnings ({len(result.warnings)}) ===")
    for w in result.warnings:
        print(f"  ⚠️ {w}")

if result.review_items:
    print(f"\n=== Review Items ({len(result.review_items)}) ===")
    for r in result.review_items:
        print(f"  🔍 {r}")
```

### What comes out of conversion

| Input | Output | Notes |
|-------|--------|-------|
| Sparse dimension | Dimension `LogicalTable` with Key, Name, Parent, Level, Gen columns, hierarchy | Star schema join to fact |
| Dense dimension | Columns in fact table | Inlined for performance |
| Time dimension | Date `LogicalTable` with `is_date_table=True` | Auto-hierarchy from generations |
| Accounts dimension | DAX measures on fact table | Dynamic calcs = formulas; stored = `SUM` |
| Attribute dimension | Extra column on parent dimension table | Attached to first regular dim |
| Calc script | DAX measure on fact table | Confidence-gated (≥ 0.5) |
| Filter | `RlsRoleDefinition` | DAX filter expression |
| Substitution variable | `WhatsIfParameter` | `VAR __name = "value"` |

---

## Step 6 — Generate TMDL Artifacts

```python
from src.agents.semantic.tmdl_generator import TmdlGenerator

# Use the SemanticModelIR from Step 5
generator = TmdlGenerator()
tmdl_output = generator.generate(result.ir)

# Write to disk
import os
os.makedirs("output/essbase_tmdl", exist_ok=True)
for filename, content in tmdl_output.files.items():
    path = f"output/essbase_tmdl/{filename}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print(f"Generated {len(tmdl_output.files)} TMDL files")
```

### Expected TMDL output structure

```
output/essbase_tmdl/
├── model.tmdl                    # Semantic model definition
├── tables/
│   ├── Fact_FinancePlan.tmdl     # Fact table (measures + FK columns)
│   ├── Time.tmdl                 # Date table (generations, hierarchy)
│   ├── Entity.tmdl               # Sparse dimension
│   ├── Product.tmdl              # Sparse dimension
│   └── Scenario.tmdl             # Sparse dimension
├── relationships/
│   ├── Entity_to_Fact.tmdl       # Star-schema FK
│   ├── Product_to_Fact.tmdl
│   ├── Scenario_to_Fact.tmdl
│   └── Time_to_Fact.tmdl
└── roles/
    └── EMEA_Only.tmdl            # RLS role from Essbase filter
```

---

## Step 7 — Migrate Security (Filters → RLS)

Essbase filters define member-level read/write/none access. The bridge converts these to Power BI RLS roles with DAX filter expressions.

```python
from src.connectors.essbase_connector import EssbaseFilter
from src.connectors.essbase_semantic_bridge import EssbaseToSemanticModelConverter

converter = EssbaseToSemanticModelConverter()

# Typical Essbase filters
filters = [
    EssbaseFilter(name="EMEA_ReadOnly", rows=[
        {"member": "EMEA", "access": "read"},
        {"member": "North America", "access": "none"},
        {"member": "APAC", "access": "none"},
    ]),
    EssbaseFilter(name="US_Finance", rows=[
        {"member": "US", "access": "read"},
        {"member": "Revenue", "access": "read"},
        {"member": "COGS", "access": "read"},
    ]),
]

# Parse any outline and convert with filters
with open("examples/essbase_samples/medium_finance.xml") as f:
    outline = parser.parse_xml(f.read(), app="Finance", db="Plan")

result = converter.convert(outline, filters=filters)

for role in result.rls_roles:
    print(f"Role: {role.name}")
    print(f"  DAX filter: {role.filter_expression}")
    print(f"  Tables:     {role.tables}")
    print()
```

### Essbase access level → RLS mapping

| Essbase Access | Power BI RLS |
|----------------|-------------|
| `read` | Include in filter (member visible) |
| `write` | Include in filter (Power BI is read-only for RLS) |
| `none` | Exclude from filter (member hidden) |
| `metaread` | Include in filter (metadata only → same as read in PBI) |

---

## Step 8 — Migrate Substitution Variables

Essbase substitution variables (e.g., `&CurMonth`) become Power BI What-If parameters or DAX variables.

```python
from src.connectors.essbase_connector import EssbaseSubstitutionVar

vars = [
    EssbaseSubstitutionVar(name="CurMonth", value="Mar", scope="application"),
    EssbaseSubstitutionVar(name="CurYear", value="FY2024", scope="application"),
    EssbaseSubstitutionVar(name="BudgetVersion", value="V3", scope="database"),
]

# The converter creates WhatsIfParameter objects
result = converter.convert(outline, substitution_vars=vars)
for p in result.whatif_parameters:
    print(f"  {p.name:20s} = {p.current_value:10s}  → {p.dax_variable}")
```

**Expected output**:
```
  CurMonth             = Mar         → VAR __CurMonth = "Mar"
  CurYear              = FY2024      → VAR __CurYear = "FY2024"
  BudgetVersion        = V3          → VAR __BudgetVersion = "V3"
```

### Implementation in Power BI

1. Create a **What-If parameter** table in Power BI Desktop
2. Use `SELECTEDVALUE('Parameter'[Value])` in measures
3. Replace hardcoded substitution variable references in DAX

---

## Step 9 — Validate

### Run all Essbase tests

```bash
py -3 -m pytest tests/test_essbase_connector.py tests/test_essbase_semantic_bridge.py -v
```

### Validate sample files parse correctly

```bash
py -3 examples/validate_samples.py
```

### Run full migration pipeline with Essbase samples

```bash
py -3 examples/full_migration_example.py
```

### Validation checklist

| Check | Command / Method | Expected |
|-------|-----------------|----------|
| Outline parses | `parser.parse_xml(data)` → `outline.is_valid == True` | All dimensions discovered |
| Member count matches | `outline.total_members` | Compare with Essbase EAS |
| Dynamic calcs identified | `outline.total_dynamic_calcs` | Match Essbase calc count |
| Calc confidence ≥ 0.7 | `translator.translate_formula(...)` | ≥ 85% of formulas |
| Semantic model tables | `result.table_count` | 1 fact + N dims |
| Measures generated | `result.measure_count` | Match accounts members |
| Star-schema joins | `result.relationship_count` | 1 per sparse dim + time |
| RLS roles | `len(result.rls_roles)` | Match Essbase filter count |
| TMDL files generated | TMDL output directory | Valid TMDL syntax |
| Tests pass | `pytest tests/test_essbase_*` | 186 passed |

---

## Mapping Quick-Reference

### Essbase Calc → DAX (top 20)

| Essbase | DAX | Confidence |
|---------|-----|-----------|
| `@SUM` | `SUM` | 1.0 |
| `@AVG` | `AVERAGE` | 1.0 |
| `@MIN` / `@MAX` | `MIN` / `MAX` | 1.0 |
| `@ABS` | `ABS` | 1.0 |
| `@ROUND` | `ROUND` | 1.0 |
| `@POWER` | `POWER` | 1.0 |
| `@CONCATENATE` | `CONCATENATE` | 1.0 |
| `#MISSING` | `BLANK()` | 1.0 |
| `@ISMISSING` | `ISBLANK` | 1.0 |
| `@PRIOR` | `CALCULATE(measure, PREVIOUSMONTH)` | 0.7 |
| `@NEXT` | `CALCULATE(measure, NEXTMONTH)` | 0.7 |
| `@SHIFT` | `CALCULATE(measure, DATEADD)` | 0.7 |
| `@ISMBR` | `HASONEVALUE` | 0.7 |
| `@TODATE` | `DATESYTD / DATESMTD` | 0.7 |
| `IF/ELSE/ENDIF` | `IF / SWITCH(TRUE())` | 0.7 |
| `@PARENTVAL` | `CALCULATE(measure, ALLEXCEPT)` | 0.5 |
| `@CHILDREN` | `FILTER + hierarchy` | 0.5 |
| `@DESCENDANTS` | `FILTER + PATH` | 0.5 |
| `@VAR` | Variance CALCULATE pattern | 0.5 |
| `@ALLOCATE` | Manual DAX pattern | 0.2 |

### Essbase Outline → TMDL

| Essbase | TMDL |
|---------|------|
| Cube | Semantic Model |
| Sparse Dimension | Dimension Table + FK join |
| Dense Dimension | Columns in Fact Table |
| Time Dimension | Date Table (`is_date_table=True`) |
| Accounts Dimension | Measures on Fact Table |
| Attribute Dimension | Column on parent dimension table |
| Generation | Hierarchy Level |
| Stored Member | Fact row / dimension row |
| Dynamic Calc Member | DAX Measure |
| Calc Script | DAX Measure |
| Filter | RLS Role |
| Substitution Variable | What-If Parameter |
| UDA | Boolean column on dimension table |
| Alias Table | Display name / translation |
| Shared Member | Alternate hierarchy |
| ASO Cube | Import mode semantic model |
| BSO Cube | Import mode + scheduled refresh |

---

## Worked Examples by Complexity

### Example A: Simple Budget (3 dims, 18 members, 1 dynamic calc)

**Source**: `examples/essbase_samples/simple_budget.xml`

```
Dimensions:
  Time (dense, time)     → Date table with 2-level hierarchy (Quarter→Month)
  Accounts (dense, acct) → 3 measures: Revenue [SUM], COGS [SUM], Gross Profit [DAX: Revenue - COGS]
  Product (sparse, reg)  → Dimension table (Electronics/Furniture → leaf products)

Star Schema:
  Fact_BudgetModel ←── Product (FK: ProductKey)
       ↑
       └── Time (FK: TimeKey, date table)
```

### Example B: Medium Finance (5 dims, 55 members, 5 dynamic calcs)

**Source**: `examples/essbase_samples/medium_finance.xml`

```
Dimensions:
  Time (dense, time)      → Date table, 3-level hierarchy, YTD dynamic calc
  Accounts (dense, acct)  → 12 measures incl. Gross Profit, Op Income, Gross Margin %
  Entity (sparse, reg)    → Dimension table (Global→Region→Country), UDA: Reporting
  Product (sparse, reg)   → Dimension table (All Products→Category→Product)
  Scenario (sparse, reg)  → Dimension table (Actual/Budget/Forecast + Variance calcs)

Star Schema:
  Fact_FinancePlan ←── Entity   (FK: EntityKey)
       ↑            ←── Product  (FK: ProductKey)
       ↑            ←── Scenario (FK: ScenarioKey)
       └── Time (FK: TimeKey, date table)

Dynamic Calc Measures:
  Gross Profit      → Revenue - COGS                              (conf: 1.0)
  Operating Income  → Gross Profit - Operating Expenses           (conf: 1.0)
  Gross Margin Pct  → ROUND(Gross Profit % Revenue, 4)           (conf: 1.0)
  Variance          → Actual - Budget                             (conf: 1.0)
  Variance Pct      → ROUND((Actual - Budget) % Budget, 4)       (conf: 1.0)
```

### Example C: Complex Planning (7 dims, 115 members, 9 dynamic calcs)

**Source**: `examples/essbase_samples/complex_planning.xml`

```
Dimensions:
  Time (dense, time)      → Date table, 4-level hierarchy (Year→Half→Quarter→Month)
                            + YTD and Prior Year dynamic calcs
  Accounts (dense, acct)  → 20+ measures, nested Income Statement + Ratios
                            incl. EBITDA, EBIT, Rev per FTE
  Entity (sparse, reg)    → 4-level hierarchy (Worldwide→Region→Country→SubRegion)
                            + Eliminations, UDAs: Reporting, Operating, Interco
  Product (sparse, reg)   → 3-level hierarchy, UDAs: HighMargin, Recurring
  Channel (sparse, reg)   → 2-level hierarchy (Direct/Indirect→sub-channels)
  Scenario (sparse, reg)  → 5 stored + 4 dynamic calc (Bud Variance, Fcst Variance, YoY Growth)
  Currency (sparse, reg)  → Local + USD/EUR dynamic calcs using @XREF (cross-cube)

Star Schema:
  Fact_PlanningModel ←── Entity   ←── Product  ←── Channel  ←── Scenario  ←── Currency
       └── Time (date table)

Translation Challenges:
  @SUMRANGE + @TODATE    → CALCULATE(SUM, DATESYTD)      conf: 0.5 (complex)
  @PRIOR + @LEVMBRS      → CALCULATE(..., DATEADD)        conf: 0.5 (complex)
  @ROUND(A % B, 4)       → ROUND(DIVIDE(A, B), 4)        conf: 1.0
  @XREF(ExchangeRates)   → LOOKUPVALUE + cross-model ref  conf: 0.2 (manual)
  @CALCMBR + @XREF       → Manual currency conversion      conf: 0.2 (manual)
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `outline.is_valid == False` | XML parse error or no dimensions | Check XML structure, ensure `<outline>` root |
| `total_members == 0` | Members not nested inside `<dimension>` | Verify XML nesting |
| Confidence 0.2 on calc | Uses `@ALLOCATE` or `@XREF` | Write manual DAX measure |
| Missing hierarchy levels | `generation_count == 0` | Add `generation` attributes to XML |
| No measures generated | Accounts dimension missing `member_details` | Ensure members have `storageType` attribute |
| Cross-cube reference | `@XREF` or multi-database formula | Create LOOKUPVALUE to separate model |
| Currency conversion | `@CALCMBR` with exchange rates | Build currency conversion table + DAX |

---

## Related Documentation

- [ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md](ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md) — Architecture & phase roadmap
- [SMART_VIEW_TO_EXCEL_MIGRATION.md](SMART_VIEW_TO_EXCEL_MIGRATION.md) — Smart View → Excel on Semantic Model migration
- [docs/MAPPING_REFERENCE.md](docs/MAPPING_REFERENCE.md) — Full mapping tables (Section 7)
- [examples/essbase_samples/README.md](examples/essbase_samples/README.md) — Sample file index
- [tests/test_essbase_connector.py](tests/test_essbase_connector.py) — 130+ connector tests
- [tests/test_essbase_semantic_bridge.py](tests/test_essbase_semantic_bridge.py) — 56+ bridge tests
