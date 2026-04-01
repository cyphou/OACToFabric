# Smart View → Excel on Power BI Semantic Model — Migration Guide

> **Audience**: Essbase admins, Smart View power users, Excel report owners  
> **Scope**: Oracle Smart View for Excel → Excel connected to Power BI semantic models  
> **Related**: [ESSBASE_MIGRATION_PLAYBOOK.md](ESSBASE_MIGRATION_PLAYBOOK.md) (cube → semantic model pipeline)

---

## Executive Summary

Oracle **Smart View** is an Excel add-in that lets users connect to Essbase cubes for ad-hoc analysis, planning grids, and data forms. When migrating Essbase to Fabric, the equivalent user experience is **Excel connected to a Power BI semantic model** via PivotTables, CUBE functions, and (for write-back) Translytical Task Flows.

### Migration Paths at a Glance

| Smart View Feature | Excel + Semantic Model Equivalent | Fidelity |
|--------------------|----------------------------------|----------|
| Ad-hoc grid | PivotTable connected to semantic model | ✅ Full |
| `HsGetValue()` | `CUBEVALUE()` | ✅ Full |
| `HsSetValue()` | Translytical write-back / Power Apps | 🟡 Partial |
| Member selection | PivotTable field list / `CUBESET()` | ✅ Full |
| POV (Point of View) | PivotTable filters / slicers | ✅ Full |
| Zoom In / Zoom Out | PivotTable expand/collapse + drill | ✅ Full |
| Data forms | Power Apps visual / Fabric SQL write-back | 🟡 Partial |
| Suppression (#Missing, zeros) | PivotTable value filters | ✅ Full |
| Smart Lists | Data validation dropdowns | ✅ Full |
| Cell comments / annotations | Excel comments (not in cube) | 🟡 Partial |
| Calc scripts (on-demand) | DAX measures (always live) | ✅ Parity+ |
| Business rules | DAX measures / Power Automate | 🟡 Partial |
| Submit data | Translytical Task Flows / Fabric write-back | 🟡 Preview |
| Cascade prompt → member | Connected slicers | ✅ Full |

---

## 1. Setting Up the Excel Connection

### Option A: Analyze in Excel (recommended for most users)

1. Open the semantic model in **Power BI Service**
2. Click **Analyze in Excel** (ribbon or "..." menu)
3. Excel opens with a pre-connected PivotTable
4. Drag measures and dimensions from the **PivotTable Fields** pane

> Requires: Power BI Pro/PPU license or Fabric capacity

### Option B: Direct XMLA Endpoint (power users / automation)

1. In Excel → **Data** → **Get Data** → **From Analysis Services**
2. Enter the XMLA endpoint:
   ```
   powerbi://api.powerbi.com/v1.0/myorg/<WorkspaceName>
   ```
3. Select the semantic model
4. Build PivotTables or CUBE formulas

> Requires: XMLA read enabled on Fabric capacity (F2+ or P1+)

### Option C: Excel Add-in for Power BI (Office 365)

1. Insert → Add-ins → **Power BI** add-in
2. Browse and pin reports / visuals inside Excel
3. Stays in sync with the published semantic model

---

## 2. Smart View Function → Excel Function Mapping

### 2.1 HsGetValue → CUBEVALUE

**Smart View** retrieves a single cell value from the cube:
```excel
=HsGetValue("EssbaseServer/App/DB", "Jan", "Revenue", "East")
```

**Excel + Semantic Model** equivalent:
```excel
=CUBEVALUE("ThisWorkbookDataModel",
    CUBEMEMBER("ThisWorkbookDataModel", "[Time].[Month].&[Jan]"),
    CUBEMEMBER("ThisWorkbookDataModel", "[Accounts].[Account].&[Revenue]"),
    CUBEMEMBER("ThisWorkbookDataModel", "[Entity].[Region].&[East]"))
```

Or more commonly, reference PivotTable slicers:
```excel
=CUBEVALUE("ThisWorkbookDataModel",
    CUBEMEMBER("ThisWorkbookDataModel", "[Time].[Month].&[Jan]"),
    CUBEMEMBER("ThisWorkbookDataModel", "[Measures].[Revenue]"),
    Slicer_Entity)
```

### 2.2 HsSetValue → Translytical Write-Back

**Smart View** writes a value back to the cube:
```excel
=HsSetValue(1000, "EssbaseServer/App/DB", "Jan", "Revenue", "East")
```

**Fabric equivalent** — Translytical Task Flow via `InvokeUserDataFunction` step:
1. User clicks a **button visual** in a Power BI report
2. Task Flow triggers a **Fabric User Data Function** (UDF)
3. UDF executes parameterized SQL against Lakehouse/Warehouse:
   ```sql
   UPDATE fact_plan SET value = @NewValue
   WHERE time_key = @time_key AND entity_key = @entity_key
   ```
4. Semantic model refreshes (incremental or on-demand)

The write-back infrastructure is implemented in
[src/agents/report/task_flow_generator.py](src/agents/report/task_flow_generator.py) —
use `WriteBackDefinition` + `generate_writeback_task_flow()`:

```python
from src.agents.report.task_flow_generator import (
    WriteBackDefinition, generate_writeback_task_flow,
)

wb = WriteBackDefinition(
    name="budget_update",
    target_table="fact_plan",
    key_columns=["time_key", "entity_key", "account_key"],
    value_column="value",
    lakehouse_name="PlanningLakehouse",
)

# Generate the parameterized SQL for a Fabric UDF
print(wb.to_udf_sql())
# UPDATE fact_plan
# SET value = @NewValue
# WHERE time_key = @time_key AND entity_key = @entity_key AND account_key = @account_key

# Generate a full Task Flow with write-back steps
tf = generate_writeback_task_flow("BudgetSubmit", [wb])
print(tf.to_json())
```

> See Phase 58 in the [DEV_PLAN.md](DEV_PLAN.md) for full Translytical architecture.

**Alternative for planning scenarios:**
- **Power Apps visual** embedded in Power BI report → writes to Dataverse / SQL
- **Excel + Power Automate** → HTTP trigger → Fabric SQL endpoint

### 2.3 HsGetSheetInfo → Workbook metadata

No direct equivalent needed. The PivotTable connection info is visible via:
- **PivotTable** → right-click → **Connection Properties**
- **Data** → **Queries & Connections** panel

### 2.4 Member Selection → CUBESET / CUBEMEMBER

**Smart View** member selector (tree-picker):
```excel
=HsGetValue(..., "IDescendants(Year)")
```

**Excel equivalent:**
```excel
' All descendants of FY2024
=CUBESET("ThisWorkbookDataModel",
    "[Time].[Hierarchy].Members",
    "All Time Members")

' Specific member
=CUBEMEMBER("ThisWorkbookDataModel", "[Time].[Month].&[Jan]")

' Count of a set
=CUBESETCOUNT(CUBESET("ThisWorkbookDataModel", "[Entity].[Region].Members"))
```

### 2.5 Smart View Functions — Full Mapping Table

| Smart View Function | Excel CUBE Function | Notes |
|--------------------|-------------------|-------|
| `HsGetValue(conn, mbr...)` | `CUBEVALUE(conn, mbr...)` | Exact 1:1 mapping |
| `HsSetValue(val, conn, mbr...)` | Translytical UDF / Power Apps | Write-back flow |
| `HsGetSheetInfo(sheet)` | Connection Properties dialog | Manual / VBA |
| `HsCurrency(conn, entity, ...)` | CUBEVALUE with currency measure | DAX handles conversion |
| Member / generation selection | `CUBESET()` + `CUBEMEMBER()` | Set operations |
| `HsAlias(conn, mbr)` | `CUBEMEMBERPROPERTY(conn, mbr, "Caption")` | Display names |
| `HsLabel(conn, mbr)` | `CUBEMEMBERPROPERTY(conn, mbr, "Caption")` | Same as alias |
| `HsDescription(conn, mbr)` | `CUBEMEMBERPROPERTY(conn, mbr, "Description")` | Member metadata |

---

## 3. Smart View Grid → PivotTable Migration

### 3.1 Ad-Hoc Grid Layout

**Smart View** ad-hoc grids have:
- **POV bar** (frozen dimensions at the top)
- **Row dimensions** (sparse dimension members down the left)
- **Column dimensions** (typically Time or Scenario across the top)
- **Data cells** (intersection values)

**PivotTable equivalent:**

| Smart View | PivotTable |
|-----------|-----------|
| POV bar | **Filters** area (drag dims to filter zone) |
| Row dimensions | **Rows** area |
| Column dimensions | **Columns** area |
| Data cells | **Values** area (measures) |
| Zoom In | Expand/collapse (+/-) or drill-down |
| Zoom Out | Collapse levels |
| Keep Only | Right-click → **Filter** → **Keep Only** |
| Remove Only | Right-click → **Filter** → **Hide** |
| Suppress missing | Value filter → "does not equal 0" |

### 3.2 Example: Finance Ad-Hoc Grid

**Smart View layout:**
```
POV:     Entity = [US]    Scenario = [Budget]    Currency = [USD]
         ┌─────────┬─────────┬─────────┬─────────┐
         │  Jan    │  Feb    │  Mar    │  Q1     │
┌────────┼─────────┼─────────┼─────────┼─────────┤
│Revenue │  1,500  │  1,600  │  1,700  │  4,800  │
│COGS    │   (900) │   (950) │  (1000) │  (2850) │
│Gross P │    600  │    650  │    700  │  1,950  │
└────────┴─────────┴─────────┴─────────┴─────────┘
```

**Recreated in Excel PivotTable:**
1. Connect to semantic model (Analyze in Excel)
2. Drag **Entity** and **Scenario** to **Filters** (= POV)
3. Drag **Time** to **Columns**
4. Drag measures (**Revenue**, **COGS**, **Gross Profit**) to **Values**
5. Filter Entity = "US", Scenario = "Budget"
6. Collapse Time to Quarter level → expand Q1 to see months

### 3.3 Example: CUBE Function Grid (replicates Smart View fixed layout)

For users who want exact cell-by-cell control (like Smart View):

```excel
' Row 1: Headers
A1: "Account"    B1: =CUBEMEMBER("Model","[Time].[Month].&[Jan]")
                 C1: =CUBEMEMBER("Model","[Time].[Month].&[Feb]")
                 D1: =CUBEMEMBER("Model","[Time].[Month].&[Mar]")

' Row 2: Revenue
A2: "Revenue"    B2: =CUBEVALUE("Model","[Measures].[Revenue]",B$1,$E$1,$F$1)
                 C2: =CUBEVALUE("Model","[Measures].[Revenue]",C$1,$E$1,$F$1)

' E1/F1: POV cells (like Smart View POV bar)
E1: =CUBEMEMBER("Model","[Entity].[Region].&[US]")
F1: =CUBEMEMBER("Model","[Scenario].[Scenario].&[Budget]")
```

This approach gives Smart View power users the **exact same cell-level control** they're used to.

---

## 4. Advanced Scenarios

### 4.1 Asymmetric Grids (different members per row)

Smart View supports asymmetric layouts where different columns appear for different rows. In Excel:

```excel
' Row 2: Revenue by month
A2: "Revenue"
B2: =CUBEVALUE("Model","[Measures].[Revenue]","[Time].[Month].&[Jan]")
C2: =CUBEVALUE("Model","[Measures].[Revenue]","[Time].[Month].&[Feb]")

' Row 3: Headcount (different measure, different time grain)
A3: "Headcount"
B3: =CUBEVALUE("Model","[Measures].[Headcount]","[Time].[Quarter].&[Q1]")
C3: =CUBEVALUE("Model","[Measures].[Headcount]","[Time].[Quarter].&[Q2]")
```

### 4.2 Substitution Variables → Named Cells

Smart View uses `&CurMonth` in member selections. In Excel:

1. Create a named range: `CurMonth` = `"Jan"`
2. Use in CUBE formulas:
   ```excel
   =CUBEVALUE("Model","[Measures].[Revenue]",
       CUBEMEMBER("Model","[Time].[Month].&[" & CurMonth & "]"))
   ```
3. Or use a **What-If parameter** slicer (from the semantic model)

### 4.3 Cascade POV → Connected Slicers

Smart View cascading prompts (select Entity → Products filtered):

1. Insert **Slicer** connected to PivotTable (or standalone)
2. Create dependent slicers using **relationships** in the semantic model
3. Entity slicer selection auto-filters Product slicer via star schema

### 4.4 Suppression (#Missing / Zeros)

| Smart View Option | PivotTable Equivalent |
|-------------------|----------------------|
| Suppress #Missing | PivotTable → Design → **Show items with no data** (uncheck) |
| Suppress zeros | Value filter → "does not equal 0" |
| Suppress both | Design → uncheck "Show empty" + value filter |
| Suppress rows | Right-click → Filter → **Top 10** or **Value Filters** |

### 4.5 Formatting Preservation

Smart View grids inherit Excel formatting. PivotTables connected to semantic models similarly:
- **Conditional formatting** applies on top of PivotTable values
- **Number formats** set via PivotTable → Value Field Settings → Number Format
- **Report layouts**: Tabular / Outline / Compact (PivotTable Design tab)

---

## 5. Write-Back Migration (Data Forms)

This is the **biggest gap** between Smart View and Excel-on-Semantic-Model.

### 5.1 Current State

| Capability | Smart View | Excel + Fabric |
|-----------|-----------|---------------|
| Read data | ✅ HsGetValue | ✅ CUBEVALUE / PivotTable |
| Write single cell | ✅ HsSetValue → calc on submit | 🟡 Translytical UDF (Preview) |
| Data form (grid write-back) | ✅ Native forms | 🟡 Power Apps visual embed |
| Calculation on submit | ✅ Runs calc script | 🟡 Pipeline trigger after write |
| Approval workflow | 🟡 PBCS planning units | ✅ Power Automate + Dataverse |
| Audit trail | ✅ Essbase audit log | ✅ Fabric SQL auditing |

### 5.2 Recommended Write-Back Architecture

```
Excel User → CUBEVALUE (read)
           → Power Apps / Translytical (write)
                    │
                    ▼
         Fabric SQL Endpoint (INSERT/UPDATE)
                    │
                    ▼
         Lakehouse Delta Table (fact_plan_writeback)
                    │
                    ▼
         Pipeline trigger → Merge into fact_plan
                    │
                    ▼
         Semantic model refresh (incremental)
                    │
                    ▼
         Excel PivotTable auto-refreshes
```

### 5.3 Write-Back Options Comparison

| Option | Complexity | User Experience | Latency |
|--------|-----------|----------------|---------|
| **Translytical Task Flow** (Preview) | Medium | Button in report → UDF → SQL | Seconds |
| **Power Apps visual** | Medium | Embedded form in report | Seconds |
| **Excel + Power Automate** | Low | VBA button → HTTP trigger → SQL | ~30s |
| **Direct SQL endpoint** | High | VBA/ODBC → Fabric SQL | Seconds |
| **Dataverse + model-driven app** | High | Full CRUD app, no Excel needed | Seconds |

### 5.4 Example: Power Automate Write-Back from Excel

```vba
' VBA macro in Excel workbook (replaces HsSetValue)
Sub SubmitBudget()
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP")

    ' Power Automate HTTP trigger URL (from flow)
    Dim url As String
    url = "https://prod-XX.westus.logic.azure.com:443/workflows/..."

    ' Build JSON payload from active cell context
    Dim payload As String
    payload = "{""entity"":""" & Range("E1").Value & """," & _
              """period"":""" & ActiveCell.Offset(0, -ActiveCell.Column + 2).Value & """," & _
              """account"":""" & Range("A" & ActiveCell.Row).Value & """," & _
              """value"":" & ActiveCell.Value & "}"

    http.Open "POST", url, False
    http.setRequestHeader "Content-Type", "application/json"
    http.Send payload

    If http.Status = 200 Then
        MsgBox "Budget submitted"
    Else
        MsgBox "Error: " & http.responseText
    End If
End Sub
```

---

## 6. Migration Playbook — Step by Step

### Phase 1: Inventory Smart View Workbooks

| Task | Action |
|------|--------|
| List all Smart View workbooks | Scan shared drives / SharePoint for `.xlsx` with Smart View connections |
| Identify connection strings | Look for `EssbaseServer/App/DB` references |
| Classify by type | Ad-hoc grid, data form, reporting template, dashboard |
| Count HsGetValue / HsSetValue calls | VBA module scan + formula search |
| Identify calc script triggers | Note which workbooks trigger calcs on submit |

### Phase 2: Map to Target Experience

| Smart View Pattern | Target | Migration Effort |
|-------------------|--------|-----------------|
| Simple ad-hoc grid (read-only) | PivotTable + Analyze in Excel | **Low** — rebuild in minutes |
| Complex CUBE-formula grid | CUBEVALUE/CUBEMEMBER formulas | **Medium** — formula rewrite |
| Data form (write + calc) | Power Apps + Fabric pipeline | **High** — new app required |
| Template with HsGetValue | CUBEVALUE formula replacement | **Medium** — find-replace |
| Dashboard with embedded charts | Power BI report (native) | **Low** — better in PBI |

### Phase 3: Convert Formulas

**Automated approach** (for workbooks with many HsGetValue calls):

```python
import re

def convert_hs_to_cube(formula: str, model_name: str = "ThisWorkbookDataModel") -> str:
    """Convert Smart View HsGetValue formula to Excel CUBEVALUE."""
    # Pattern: =HsGetValue("Server/App/DB", "Mbr1", "Mbr2", ...)
    match = re.match(
        r'=HsGetValue\s*\(\s*"[^"]+"\s*,\s*(.*)\)',
        formula, re.IGNORECASE
    )
    if not match:
        return formula  # Not an HsGetValue formula

    members_str = match.group(1)
    # Split members, handling quoted strings
    members = [m.strip().strip('"') for m in members_str.split(',')]

    # Build CUBEVALUE
    cube_members = []
    for m in members:
        # Determine dimension from member name (requires mapping table)
        cube_members.append(f'CUBEMEMBER("{model_name}","[Dim].[Member].&[{m}]")')

    return f'=CUBEVALUE("{model_name}",{",".join(cube_members)})'

# Example
sv = '=HsGetValue("Essbase/Finance/Plan", "Jan", "Revenue", "US")'
print(convert_hs_to_cube(sv))
```

> **Note**: Dimension mapping is required. The `EssbaseToSemanticModelConverter` output provides the dimension → table mapping needed to produce correct CUBEMEMBER references.

### Phase 4: Deploy & Train

| Task | Detail |
|------|--------|
| Publish semantic model | Deploy TMDL via XMLA endpoint |
| Enable Analyze in Excel | Workspace settings → enable |
| Distribute converted workbooks | SharePoint / OneDrive / Teams |
| Provide training materials | PivotTable basics, CUBE functions, slicer usage |
| Run parallel testing | Smart View vs. PivotTable side-by-side validation |
| Sunset Smart View | Disable after UAT sign-off |

---

## 7. Common Smart View Patterns → Excel Recipes

### Recipe 1: Monthly P&L Report

**Smart View**: Fixed grid with Revenue/COGS/Profit × Jan-Dec, POV = Entity + Scenario

**Excel PivotTable**:
1. Analyze in Excel → connect to semantic model
2. Rows = Accounts hierarchy
3. Columns = Time hierarchy → drill to months
4. Filters = Entity, Scenario
5. Apply conditional formatting (negative = red)

### Recipe 2: Variance Analysis

**Smart View**: Actual vs Budget columns, Variance calc script

**Excel**:
1. PivotTable with **Scenario** in columns (Actual | Budget)
2. Add DAX measure `[Variance] = [Actual] - [Budget]` in semantic model
3. Add `[Variance %] = DIVIDE([Variance], [Budget])` 
4. These appear automatically in the PivotTable field list

### Recipe 3: Rolling Forecast Input

**Smart View**: Data form with HsSetValue for future months

**Fabric**:
1. Power Apps canvas app embedded in Power BI report
2. App reads from semantic model (read) + writes to Lakehouse (write)
3. Fabric pipeline merges writeback table → Lakehouse fact table
4. Semantic model refreshes on schedule

### Recipe 4: Entity-Level Drill Report

**Smart View**: Zoom In on "North America" → shows US, Canada, Mexico

**Excel PivotTable**:
1. Drag **Entity** hierarchy to Rows
2. Click **+** to expand North America
3. Double-click a cell to drill through to detail table

### Recipe 5: Ad-Hoc Investigation (exact Smart View replica)

**Excel CUBE Functions** (for power users who want cell-by-cell control):

```excel
' Connection name (from Analyze in Excel)
' =CUBEVALUE("ThisWorkbookDataModel", member1, member2, ...)

' POV cells
A1: Entity    B1: =CUBEMEMBER("Model","[Entity].[Region].&[US]")
A2: Scenario  B2: =CUBEMEMBER("Model","[Scenario].[Name].&[Budget]")

' Column headers (Time)
C4: =CUBEMEMBER("Model","[Time].[Month].&[Jan]")
D4: =CUBEMEMBER("Model","[Time].[Month].&[Feb]")
E4: =CUBEMEMBER("Model","[Time].[Month].&[Mar]")

' Row headers (Accounts)
B5: =CUBEMEMBER("Model","[Measures].[Revenue]")
B6: =CUBEMEMBER("Model","[Measures].[COGS]")
B7: =CUBEMEMBER("Model","[Measures].[Gross Profit]")

' Data cells (intersections)
C5: =CUBEVALUE("Model",C$4,$B5,$B$1,$B$2)
D5: =CUBEVALUE("Model",D$4,$B5,$B$1,$B$2)
C6: =CUBEVALUE("Model",C$4,$B6,$B$1,$B$2)
' ... fill down / right
```

This replicates the **exact** Smart View grid experience inside Excel — same cell-level precision, same POV pattern, same fill-across behavior.

---

## 8. Key Differences Users Should Know

| Topic | Smart View | Excel + Semantic Model |
|-------|-----------|----------------------|
| **Connection** | Smart View add-in → Essbase server | Native Excel → Power BI XMLA |
| **Authentication** | Essbase credentials | Azure AD / SSO (automatic) |
| **Calc on retrieve** | Essbase calc scripts run server-side | DAX measures evaluate on query |
| **Data freshness** | Real-time (BSO) or calc-time (ASO) | Refresh schedule or DirectQuery |
| **Offline access** | Disconnect mode in Smart View | PivotTable cache + offline mode |
| **Performance** | Depends on Essbase server | Depends on Fabric capacity (F SKU) |
| **Hierarchies** | Gen/Level navigation in Smart View | PivotTable expand/collapse |
| **Multi-cube** | Multiple connections in one sheet | Multiple PivotTables / CUBE funcs |
| **Conditional formatting** | Limited in Smart View | Full Excel conditional formatting |
| **Charts** | Separate from grid | PivotCharts linked to PivotTable |

### What Gets Better

- **SSO authentication** — no separate login
- **Collaboration** — Excel in OneDrive/Teams with co-authoring
- **Refresh** — automatic scheduled refresh vs. manual retrieve
- **Security** — RLS enforced by semantic model (no client bypass)
- **Charting** — PivotCharts, Power BI visuals embedded in Excel
- **Mobile** — Power BI mobile app for on-the-go access
- **Version control** — OneDrive version history

### What Needs Attention

- **Write-back** — not native yet; use Translytical Task Flows or Power Apps
- **Calc scripts** — must be pre-translated to DAX measures
- **Cell-level formatting overrides** — Smart View preserves; PivotTable resets on refresh
- **Multi-grid sheets** — Smart View allows multiple grids; use multiple PivotTables

---

## 9. Automation: Bulk Convert Smart View Workbooks

For large migrations with dozens of Smart View workbooks:

```python
"""Scan Excel workbooks for Smart View formulas and generate migration report."""
import re
from pathlib import Path

SV_PATTERNS = {
    "HsGetValue": re.compile(r"HsGetValue\s*\(", re.IGNORECASE),
    "HsSetValue": re.compile(r"HsSetValue\s*\(", re.IGNORECASE),
    "HsGetSheetInfo": re.compile(r"HsGetSheetInfo", re.IGNORECASE),
    "HsCurrency": re.compile(r"HsCurrency", re.IGNORECASE),
    "Connection": re.compile(r"EssbaseServer|SmartView\.Connection", re.IGNORECASE),
}

def scan_workbook(path: Path) -> dict:
    """Quick scan for Smart View patterns (text-based, works on .xlsx XML)."""
    # For production use, use openpyxl for proper cell scanning
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), data_only=False)
        findings = {k: 0 for k in SV_PATTERNS}
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        for name, pattern in SV_PATTERNS.items():
                            if pattern.search(cell.value):
                                findings[name] += 1
        return {"path": str(path), "findings": findings, "sheets": len(wb.worksheets)}
    except Exception as e:
        return {"path": str(path), "error": str(e)}

# Scan a directory
for xlsx in Path("smart_view_workbooks/").glob("*.xlsx"):
    result = scan_workbook(xlsx)
    print(f"{result['path']}: {result.get('findings', result.get('error'))}")
```

---

## 10. Checklist — Smart View Migration

- [ ] **Inventory** all Smart View workbooks (file paths, owners, frequency of use)
- [ ] **Classify** each workbook: read-only grid / CUBE grid / data form / dashboard
- [ ] **Deploy** semantic model to Fabric workspace with XMLA enabled
- [ ] **Validate** Analyze in Excel produces correct numbers (vs. Smart View)
- [ ] **Convert** HsGetValue formulas to CUBEVALUE (automated or manual)
- [ ] **Recreate** data forms using Power Apps or Translytical Task Flows
- [ ] **Train** users on PivotTable basics + CUBE functions
- [ ] **Parallel run** Smart View alongside Excel/PBI for 2 weeks
- [ ] **Validate** totals match between Smart View and PivotTable
- [ ] **Document** differences and workarounds for each workbook
- [ ] **Sunset** Smart View after UAT sign-off
- [ ] **Monitor** usage adoption (Power BI usage metrics)

---

## 11. Essbase Sample Cubes — Concrete Excel Migration Recipes

The migration pipeline ([examples/essbase_migration_example.py](examples/essbase_migration_example.py)) produces ready-to-deploy semantic models from the 3 sample cubes. Here's how Smart View users reconnect in Excel for each one.

### 11.1 Simple Budget Cube (3 dims: Time, Accounts, Product)

**Essbase Smart View grid** (typical budget analyst sheet):
```
Connection: EssbaseServer/SimpleBudget/Budget
POV:     (none — only 3 dims)
         ┌──────────┬──────────┬──────────┐
         │  Jan     │  Feb     │  Mar     │
┌────────┼──────────┼──────────┼──────────┤
│Revenue │  1,200   │  1,300   │  1,400   │
│COGS    │   (700)  │   (750)  │   (800)  │
│Gross P │    500   │    550   │    600   │
└────────┴──────────┴──────────┴──────────┘
```

**After migration** — TMDL files in `output/essbase_migration/simple_budget/SemanticModel/`:
- `Fact_Essbase_simple_budget.tmdl` — Revenue, COGS, Gross Profit as DAX measures
- `Time.tmdl` — Date table with FY2024 → Q1/Q2 → Jan–Jun hierarchy
- `Product.tmdl` — Electronics (Laptops, Phones), Furniture (Desks, Chairs)

**Excel PivotTable** (Analyze in Excel):
1. Rows = drag **Revenue**, **COGS**, **Gross Profit** measures to Values
2. Columns = drag **Time** hierarchy → expand to months
3. No POV needed (3-dim cube → all dims visible)

**Excel CUBE formula** (exact Smart View replica):
```excel
' Time headers (row 4)
C4: =CUBEMEMBER("Essbase_simple_budget","[Time].[Time].&[Jan]")
D4: =CUBEMEMBER("Essbase_simple_budget","[Time].[Time].&[Feb]")
E4: =CUBEMEMBER("Essbase_simple_budget","[Time].[Time].&[Mar]")

' Measures (column B)
B5: =CUBEMEMBER("Essbase_simple_budget","[Measures].[Revenue]")
B6: =CUBEMEMBER("Essbase_simple_budget","[Measures].[COGS]")
B7: =CUBEMEMBER("Essbase_simple_budget","[Measures].[Gross Profit]")

' Data (fill right + down)
C5: =CUBEVALUE("Essbase_simple_budget",C$4,$B5)
```

### 11.2 Medium Finance Cube (5 dims: Time, Accounts, Entity, Product, Scenario)

**Essbase Smart View** (typical regional finance grid):
```
Connection: EssbaseServer/FinanceCorp/Finance
POV:     Entity = [North America]    Scenario = [Actual]
```

**After migration** — TMDL in `output/essbase_migration/medium_finance/SemanticModel/`:
- Fact table with **19 DAX measures** (Revenue, COGS, Gross Profit, Operating Income, Gross Margin %, Variance, Variance %)
- Entity table (Global → North America/EMEA/APAC → leaf countries)
- Scenario table (Actual, Budget, Forecast, Variance, Variance Pct)
- **1 RLS role**: `RegionalAccess` (North America + EMEA read, APAC denied)
- **2 What-If params**: `CurMonth` = Jun, `CurYear` = FY2024

**Excel PivotTable**:
1. Filters = **Entity** (select "North America"), **Scenario** (select "Actual")
2. Rows = Accounts hierarchy (Revenue → Product Sales, Service Revenue)
3. Columns = Time (Q1–Q4, expand to months)
4. The `Gross Margin Pct` measure (`@ROUND(Gross Profit % Revenue, 4)`) is now a DAX measure — appears in field list automatically

**Substitution variable → Named range**:
```excel
' Define named ranges (replaces &CurMonth / &CurYear)
Name Manager → CurMonth = "Jun"
Name Manager → CurYear  = "FY2024"

' Use in CUBE formula
=CUBEVALUE("Essbase_medium_finance",
    CUBEMEMBER("Essbase_medium_finance","[Time].[Time].&[" & CurMonth & "]"),
    CUBEMEMBER("Essbase_medium_finance","[Measures].[Revenue]"),
    CUBEMEMBER("Essbase_medium_finance","[Entity].[Entity].&[North America]"))
```

### 11.3 Complex Planning Cube (7 dims + write-back + RLS)

**Essbase Smart View** (planning manager grid with write-back):
```
Connection: EssbaseServer/PlanCorp/Planning
POV:     Entity = [US-East]   Scenario = [Budget]   Currency = [USD]   Channel = [Direct]
```

**After migration** — TMDL in `output/essbase_migration/complex_planning/SemanticModel/`:
- **7 tables** (Fact + Time + Entity + Product + Channel + Scenario + Currency)
- **43 DAX measures** including EBITDA, EBIT, Gross Margin %, EBITDA Margin %, Rev per FTE
- **3 RLS roles**: `RegionalManager`, `FinanceAnalyst`, `PlanningAdmin`
- **5 What-If params**: CurMonth, CurYear, BudYear, FcstStart, BaseCurrency
- **6 relationships** (star schema)

**Excel PivotTable** (full planning grid):
1. Filters = Entity, Scenario, Currency, Channel (= 4-dimension POV)
2. Rows = Accounts hierarchy (Income Statement → Revenue/COGS/OpEx → line items)
3. Columns = Time hierarchy (FY2023 → H1/H2 → Q1-Q4 → Jan-Dec)
4. Values = auto-populated from measures

**Write-back** (replacing HsSetValue/Submit Data):

The migration generates write-back UDF stubs via `WriteBackDefinition`:

```python
from src.agents.report.task_flow_generator import (
    WriteBackDefinition, generate_writeback_task_flow,
)

# Budget update write-back for PlanCorp
wb = WriteBackDefinition(
    name="planning_update",
    target_table="Fact_Essbase_complex_planning",
    key_columns=["TimeKey", "EntityKey", "ProductKey", "ChannelKey", "ScenarioKey"],
    value_column="Value",
    lakehouse_name="EssbaseLakehouse",
)

# Generates parameterized SQL:
# UPDATE Fact_Essbase_complex_planning
# SET Value = @NewValue
# WHERE TimeKey = @TimeKey AND EntityKey = @EntityKey
#   AND ProductKey = @ProductKey AND ChannelKey = @ChannelKey
#   AND ScenarioKey = @ScenarioKey
```

Users click a **Submit** button in the Power BI report → Translytical Task Flow → Fabric UDF → delta table update → incremental refresh.

**RLS role mapping** (replacing Essbase filters):

| Essbase Filter | Fabric RLS Role | DAX Filter |
|---------------|----------------|------------|
| `RegionalManager` (Americas=write, EMEA=read, APAC=none) | `RegionalManager` | `[Entity] IN {"Americas","EMEA"}` |
| `FinanceAnalyst` (Actual+Budget=read, Forecast=none) | `FinanceAnalyst` | `[Scenario] IN {"Actual","Budget"}` |
| `PlanningAdmin` (Worldwide=write, all scenarios) | `PlanningAdmin` | No filter (full access) |

### 11.4 Essbase-Specific CUBE Function Patterns

| Essbase Smart View Pattern | Excel CUBE Equivalent |
|---------------------------|----------------------|
| `@CHILDREN(Entity)` | `=CUBESET("Model","[Entity].[Entity].Members")` with level filter |
| `@DESCENDANTS(FY2024)` | `=CUBESET("Model","[Time].[Time].[Month].Members")` |
| `@PARENT(US)` | `=CUBEMEMBERPROPERTY("Model",CUBEMEMBER("Model","[Entity].&[US]"),"ParentUniqueName")` |
| `@ISMBR(Actual)` | `=IF(CUBEMEMBER("Model","[Scenario].&[Actual]")=Slicer_Scenario,...)` |
| `@SUMRANGE(Time,@TODATE)` | DAX `DATESYTD` measure — appears automatically in PivotTable |
| `@PRIOR(Time,12,...)` | DAX `PREVIOUSYEAR` measure — appears automatically |
| `&CurMonth` (subst var) | Named range `CurMonth` in CUBEMEMBER formula |
| `#MISSING` | `BLANK()` in DAX → appears as empty cell in PivotTable |
| Zoom In (expand member) | PivotTable **+** button to expand hierarchy |
| Retrieve (refresh) | PivotTable **Refresh** or `Ctrl+Alt+F5` |
| Submit Data | Translytical Task Flow button or VBA + Power Automate |

---

## Related Documentation

- [ESSBASE_MIGRATION_PLAYBOOK.md](ESSBASE_MIGRATION_PLAYBOOK.md) — Cube → semantic model migration
- [ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md](ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md) — Full architecture
- [examples/essbase_migration_example.py](examples/essbase_migration_example.py) — Run migration on all 3 sample cubes
- [docs/MAPPING_REFERENCE.md](docs/MAPPING_REFERENCE.md) — Essbase calc → DAX mapping
- [DEV_PLAN.md](DEV_PLAN.md) Phase 58 — Translytical Task Flows & write-back
