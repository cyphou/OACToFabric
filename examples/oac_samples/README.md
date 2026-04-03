# OAC Sample Assets

Comprehensive sample files covering **all 16 OAC asset types**. Includes RPD XML exports (repository metadata) and OAC REST API JSON responses (catalog assets).

---

## RPD XML Samples

Repository (RPD) XML exports at multiple complexity levels.

| File | Complexity | Tables | Expressions | Features |
|------|-----------|--------|-------------|----------|
| `simple_sales.xml` | Simple | 2 | 1 | Basic columns, SUM aggregate |
| `medium_hr.xml` | Medium | 4 | 3 | Hierarchies, security roles, init blocks, AVG, `\|\|` concat |
| `complex_enterprise.xml` | Complex | 8 | 7 | Full enterprise RPD, CASE WHEN, multi-fact, data flows |
| `advanced_analytics.xml` | Advanced | 5 | 35 | Time intelligence (AGO, TODATE, PERIODROLLING, RSUM, MAVG), window analytics (RANK, DENSE_RANK, NTILE, RATIO_TO_REPORT), advanced aggregates (COUNTDISTINCT, MEDIAN, STDDEV, PERCENTILE, COUNTIF, SUMIF) |
| `financial_functions.xml` | Advanced | 6 | 50+ | String/date/math/logical functions, DECODE, NVL/NVL2/COALESCE, VALUEOF |
| `full_catalog_enterprise.xml` | Enterprise | 10 | 60+ | **All asset types**: 3 connections, 10 physical tables, 10 logical tables, 3 subject areas, 4 security roles, 3 init blocks, 2 data flows, 5 hierarchies, time intelligence, window functions, CASE WHEN, string/math/date functions, session variables, multi-fact joins |

## OAC REST API JSON Samples

Realistic JSON responses matching the structures consumed by `oac_client.py`, `oac_catalog.py`, and `oac_dataflow_api.py`.

### Catalog

| File | Asset Type | Description |
|------|-----------|-------------|
| `catalog_api_response.json` | Mixed | Paginated catalog listing with 9 items across all asset types (analysis, dashboard, dataModel, prompt, filter, agent, dataflow) |

### Analyses (AssetType.ANALYSIS)

| File | Description |
|------|-------------|
| `analysis_sales_overview.json` | Sales analysis with 2 criteria, 6 visualizations (KPI, bar, line, table), action links, conditional formatting, trend lines |
| `analysis_financial_report.json` | P&L / balance sheet with 3 criteria, pivot table, waterfall, combo chart, compound layout (2 pages), CASE WHEN expressions, AGO/TODATE |

### Dashboards (AssetType.DASHBOARD)

| File | Description |
|------|-------------|
| `dashboard_executive.json` | 3 pages, 10 embedded analyses, guided navigation, master-detail interactions, global filters, tabbed layout |
| `dashboard_operational.json` | Real-time ops dashboard, KPI tiles with refresh interval, warehouse heatmap, inventory alerts, drill-down interactions |

### Data Flows (AssetType.DATA_FLOW)

| File | Description |
|------|-------------|
| `dataflow_etl_pipeline.json` | 9-step daily incremental ETL (3 sources → filter → 2 joins → transform → aggregate → merge target), parameters, schedule, error handling |
| `dataflow_customer_360.json` | Weekly full-load Customer 360 enrichment (CRM + billing + support → join → aggregate → health score → overwrite) |

### Data Models (AssetType.DATA_MODEL)

| File | Description |
|------|-------------|
| `data_model_star_schema.json` | Star schema with 1 fact + 4 dimensions, joins, hierarchies, calculated columns, aggregation rules |

### Prompts (AssetType.PROMPT)

| File | Description |
|------|-------------|
| `prompt_definitions.json` | 5 prompt types: multi-select checkboxes, date range with presets, cascading hierarchy, list box with search, single-select radio |

### Filters (AssetType.FILTER)

| File | Description |
|------|-------------|
| `filter_definitions.json` | 5 saved filters: threshold (>$1M), multi-condition AND, dynamic session variable, top-N ranking, multi-value exclusion |

### Agents & Alerts (AssetType.AGENT_ALERT)

| File | Description |
|------|-------------|
| `agent_alert_definitions.json` | 4 agents: inventory threshold with webhook, revenue drop % with report delivery, ETL failure monitor, new record trigger with personalised delivery |

### Connections (AssetType.CONNECTION)

| File | Description |
|------|-------------|
| `connections.json` | 8 connections: Oracle EBS, Oracle ADW, Oracle ATP, Salesforce REST, ServiceNow REST, analytics DB, HR DB, OCI Object Storage |

---

## Asset Type Coverage

| AssetType | RPD XML | REST API JSON |
|-----------|---------|---------------|
| `PHYSICAL_TABLE` | All XML files | `data_model_star_schema.json` |
| `LOGICAL_TABLE` | All XML files | `data_model_star_schema.json` |
| `PRESENTATION_TABLE` | All XML files | — |
| `SUBJECT_AREA` | All XML files | `catalog_api_response.json` |
| `SECURITY_ROLE` | `medium_hr.xml`, `full_catalog_enterprise.xml` | — |
| `INIT_BLOCK` | `medium_hr.xml`, `full_catalog_enterprise.xml` | — |
| `CONNECTION` | `complex_enterprise.xml`, `full_catalog_enterprise.xml` | `connections.json` |
| `DATA_FLOW` | `complex_enterprise.xml`, `full_catalog_enterprise.xml` | `dataflow_etl_pipeline.json`, `dataflow_customer_360.json` |
| `ANALYSIS` | — | `analysis_sales_overview.json`, `analysis_financial_report.json` |
| `DASHBOARD` | — | `dashboard_executive.json`, `dashboard_operational.json` |
| `DATA_MODEL` | — | `data_model_star_schema.json` |
| `PROMPT` | — | `prompt_definitions.json` |
| `FILTER` | — | `filter_definitions.json` |
| `AGENT_ALERT` | — | `agent_alert_definitions.json` |

---

## XML Structure

The RPD XML uses a `<Repository>` root element with the following top-level tags:

- `<PhysicalTable>` — Physical database tables with `<PhysicalColumn>` children
- `<LogicalTable>` — Business model tables with `<LogicalColumn>`, `<LogicalHierarchy>`, `<LogicalTableSource>`
- `<SubjectArea>` — Presentation layer groupings with `<PresentationTable>` / `<PresentationColumn>`
- `<SecurityRole>` — Application roles with `<Member>` and `<Permission>`
- `<InitBlock>` — Session variable initialisation blocks with `<SQL>` and `<Variable>`
- `<Connection>` — Database connection definitions
- `<DataFlow>` — Data flow definitions

## Usage

```python
# Parse RPD XML
from src.agents.discovery.rpd_parser import RPDParser

parser = RPDParser()
with open("examples/oac_samples/simple_sales.xml") as f:
    inventory = parser.parse(f.read())

for table in inventory.get("physical_tables", []):
    print(table["name"])
```

```python
# Load catalog API response
import json

with open("examples/oac_samples/catalog_api_response.json") as f:
    catalog = json.load(f)

for item in catalog["items"]:
    print(f"{item['type']:12s} {item['name']}")
```
