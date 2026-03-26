# Agent 05: Report & Dashboard Migration Agent — Technical Specification

## 1. Purpose

Convert OAC **Analyses** and **Dashboards** into **Power BI Reports** in **PBIR (Power BI Report)** format, preserving layouts, visuals, filters, prompts, and interactivity.

## 1.1 File Ownership

| File | Purpose |
|------|--------|
| `src/agents/report/report_agent.py` | ReportMigrationAgent class — Analyses → PBI Reports |
| `src/agents/report/prompt_converter.py` | OAC prompts → PBI slicers/parameters |
| `src/agents/report/visual_mapper.py` | OAC viz types → PBI visuals |
| `src/agents/report/layout_engine.py` | Reconstruct page layouts; positioning, grid alignment |
| `src/agents/report/pbir_generator.py` | Generate PBIR (Power BI Report) JSON files |
| `src/agents/report/visual_fallback.py` | 3-tier visual fallback cascade (complex→simpler→table→card) (Phase 47) |
| `src/agents/report/bookmark_generator.py` | PBI bookmark JSON from OAC story points and saved filter states (Phase 47) |

## 1.2 Constraints

- Do NOT modify semantic model TMDL, security roles, or schema DDL
- Do NOT modify discovery or extraction logic
- Only produces PBIR report JSON, visual configs, and slicer definitions
- Semantic model binding comes from Agent 04 — do not duplicate measure generation
- Layout engine uses 1280×720 canvas; do NOT hard-code pixel positions outside layout_engine.py

## 1.3 Delegation Guide

| If you encounter… | Delegate to |
|--------------------|-------------|
| Missing measure or column in model | **Semantic Model (04)** — TMDL gap |
| Data source not migrated | **Schema (02)** |
| Security filter on a visual | **Security (06)** |
| Prompt references unknown subject area | **Discovery (01)** |

---

## 2. Inputs

| Input | Source | Format |
|---|---|---|
| OAC analysis/dashboard definitions | Fabric Lakehouse `migration_inventory` | Delta table (from Agent 01) |
| OAC analysis XML (detailed layout) | OAC catalog export | XML |
| Semantic model reference | Fabric Lakehouse `mapping_rules` | Delta table (from Agent 04) |
| Visual type mapping rules | Config | JSON |

## 3. Outputs

| Output | Destination | Format |
|---|---|---|
| Power BI Report definitions | Git repo | PBIR folder structure |
| Report visual configurations | Git repo | JSON (visual configs) |
| Migration mapping log | Fabric Lakehouse `mapping_rules` | Delta table |
| Visual QA comparison screenshots | Blob Storage | PNG |

## 4. PBIR Structure Generated

```
ReportName.Report/
├── definition.pbir                 # Report metadata, semantic model binding
├── report.json                     # Full report definition
├── StaticResources/
│   └── SharedResources/
│       └── BaseThemes/
│           └── CY24SU06.json       # Theme file
├── pages/
│   ├── page1/
│   │   └── visuals/
│   │       ├── visual1.json
│   │       ├── visual2.json
│   │       └── visual3.json
│   └── page2/
│       └── visuals/
│           └── ...
└── .platform
```

## 5. Visual Type Mapping

### 5.1 OAC Analysis View → Power BI Visual Type

| OAC View / Chart Type | Power BI Visual Type | Notes |
|---|---|---|
| **Table** | `tableEx` | Direct column mapping |
| **Pivot Table** | `pivotTable` (Matrix) | Row/Col/Value mapping |
| **Vertical Bar** | `clusteredBarChart` | Category + Value |
| **Horizontal Bar** | `clusteredColumnChart` | Category + Value |
| **Stacked Bar** | `stackedBarChart` | Category + Series + Value |
| **Line Chart** | `lineChart` | Axis + Values + Legend |
| **Area Chart** | `areaChart` | Axis + Values |
| **Combo Chart (Bar+Line)** | `lineClusteredColumnComboChart` | Dual axis |
| **Pie Chart** | `pieChart` | Category + Values |
| **Donut Chart** | `donutChart` | Category + Values |
| **Scatter Plot** | `scatterChart` | X + Y + Size + Color |
| **Bubble Chart** | `scatterChart` (with size) | X + Y + Size |
| **Map (filled)** | `filledMap` | Location + Value |
| **Map (bubble)** | `map` | Lat/Long + Size |
| **Gauge** | `gauge` | Value + Min + Max + Target |
| **KPI / Metric** | `card` or `multiRowCard` | Single value display |
| **Funnel** | `funnel` | Category + Values |
| **Treemap** | `treemap` | Group + Values |
| **Heatmap** | `matrix` with conditional formatting | Row + Col + Value with color |
| **Waterfall** | `waterfallChart` | Category + Values |
| **Narrative / Text** | `textbox` | Rich text |
| **Image** | `image` | Static image |
| **Trellis / Small Multiples** | Visual with Small Multiples field | Field-based repetition |

### 5.2 OAC Prompt → Power BI Slicer/Parameter

| OAC Prompt Type | Power BI Equivalent |
|---|---|
| **Dropdown (single select)** | Slicer (dropdown style, single select) |
| **Dropdown (multi select)** | Slicer (dropdown style, multi select) |
| **Search / Type-ahead** | Slicer with search enabled |
| **Slider (range)** | Slicer (between range) |
| **Date Picker** | Slicer (date range, relative date) |
| **Radio Button** | Slicer (tile style, single select) |
| **Checkbox** | Slicer (tile style, multi select) |
| **Text Input** | What-if parameter or text filter |
| **Cascading Prompt** | Multiple slicers with relationship-based filtering |

### 5.3 OAC Formatting → Power BI Formatting

| OAC Formatting | Power BI Equivalent |
|---|---|
| Conditional formatting (color) | Conditional formatting rules (field value rules) |
| Data bars | Data bars in table/matrix |
| Stoplight (icon set) | Icons conditional formatting |
| Number format (#,##0.00) | Format string in visual config |
| Font / size / color | Visual formatting pane settings |
| Borders | Visual border settings |
| Background color | Visual background fill |
| Sorting (column, direction) | Sort settings in visual config |

## 6. Core Logic

### 6.1 Report Generation Flow

```
1. Load OAC analysis/dashboard definitions from Lakehouse
2. Resolve semantic model reference (from Agent 04)
3. For each dashboard page:
   3.1 Create a PBI report page
   3.2 Calculate canvas layout (translate OAC grid → PBI pixel coordinates)
4. For each analysis/view on the page:
   4.1 Map OAC visualization type → PBI visual type
   4.2 Map OAC columns → PBI semantic model columns/measures
   4.3 Map OAC formatting → PBI visual formatting
   4.4 Map OAC prompts → PBI slicers
   4.5 Map OAC actions → PBI drillthrough / bookmarks
   4.6 Generate visual JSON config
5. For each prompt:
   5.1 Create slicer visual or parameter
   5.2 Configure filter connections
6. Assemble PBIR folder structure
7. Commit to Git
8. Deploy to Fabric workspace
```

### 6.2 Layout Translation

OAC uses a **grid/section-based layout** while Power BI uses **pixel-based canvas (1280×720 default)**.

```python
def translate_layout(oac_layout: OACLayout) -> PBILayout:
    """
    Convert OAC grid layout to PBI pixel coordinates.
    
    OAC sections are mapped to horizontal/vertical slices of the PBI canvas.
    Each section's relative size determines the pixel allocation.
    """
    canvas_width = 1280
    canvas_height = 720
    
    # OAC sections: each section has a relative width/height percentage
    for section in oac_layout.sections:
        x = int(section.relative_x * canvas_width)
        y = int(section.relative_y * canvas_height)
        width = int(section.relative_width * canvas_width)
        height = int(section.relative_height * canvas_height)
        
        yield PBIVisualPosition(x=x, y=y, width=width, height=height)
```

## 7. OAC Dashboard Actions → PBI Interactivity

| OAC Action | PBI Equivalent |
|---|---|
| Navigate to analysis | Drillthrough page |
| Navigate to URL | Button with URL action |
| Navigate to dashboard page | Page navigation button / bookmark |
| Filter on click | Cross-filter (default PBI behavior) |
| Master-detail | Drillthrough with context |
| Guided navigation | Bookmarks + buttons |

## 8. Error Handling

| Error | Handling |
|---|---|
| Unknown OAC visual type | Default to table visual, flag for manual review |
| Column not found in semantic model | Log mapping error, create placeholder, flag |
| Complex OAC action type | Create comment in report, flag for manual implementation |
| Layout overflow (too many visuals) | Auto-paginate to additional PBI pages |
| Custom OAC plugin visualization | Flag as unsupported, create placeholder card |

## 9. Testing Strategy

| Test Type | Approach |
|---|---|
| Unit | Visual config generation for each chart type |
| Layout | Verify pixel positions within canvas bounds |
| Integration | Deploy report to dev workspace, open in PBI |
| Visual QA | Screenshot comparison (OAC vs PBI) — manual review |
| Functional | Verify slicers filter correctly, drillthrough works |
