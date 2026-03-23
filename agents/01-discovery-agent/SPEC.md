# Agent 01: Discovery & Inventory Agent — Technical Specification

## 1. Purpose

Crawl the Oracle Analytics Cloud (OAC) environment and produce a **complete, structured inventory** of all assets, including their dependencies, metadata, and migration complexity scores.

## 1.1 File Ownership

| File | Purpose |
|------|--------|
| `src/agents/discovery/discovery_agent.py` | DiscoveryAgent class — main lifecycle |
| `src/agents/discovery/oac_client.py` | OAC API + RPD parser orchestration |
| `src/agents/discovery/rpd_parser.py` | Parse OracleBI.xml (physical/logical/presentation layers) |
| `src/agents/discovery/dependency_graph.py` | Build asset DAG; cycle detection, topological sort |
| `src/agents/discovery/complexity_scorer.py` | Complexity scoring (LOW/MEDIUM/HIGH) |
| `src/clients/oac_catalog.py` | OAC catalog REST API discovery endpoints |
| `src/clients/oac_auth.py` | Multi-method OAC auth (OAuth2, API key, mTLS) |
| `src/clients/oac_dataflow_api.py` | OAC Data Flow REST API extraction |

## 1.2 Constraints

- Do NOT modify schema DDL, ETL pipelines, semantic models, or reports
- Do NOT write to any Delta table other than `migration_inventory` and `agent_logs`
- Only produces inventory and dependency metadata
- RPD parsing must use streaming XML for files >50 MB (see `src/core/streaming_parser.py`)

## 1.3 Delegation Guide

| If you encounter… | Delegate to |
|--------------------|-------------|
| Oracle table DDL or data type mapping | **Schema (02)** |
| Data Flow step definitions needing pipeline conversion | **ETL (03)** |
| Expression translation (OAC → DAX) | **Semantic Model (04)** |
| Report/dashboard visual definitions | **Report (05)** |
| Security roles or RLS filter definitions | **Security (06)** |

---

## 2. Inputs

| Input | Source | Format |
|---|---|---|
| OAC REST API credentials | Key Vault / Environment | OAuth2 token |
| OAC base URL | Config | URL string |
| RPD export file | Manual export from OAC | XML (UDML/XUDML format) |
| Migration scope definition | Orchestrator | JSON (include/exclude filters) |

## 3. Outputs

| Output | Destination | Format |
|---|---|---|
| Asset inventory | Fabric Lakehouse `migration_inventory` | Delta table rows |
| Dependency graph | Fabric Lakehouse `migration_inventory` | Adjacency list (JSON column) |
| Complexity scores | Fabric Lakehouse `migration_inventory` | Per-asset numeric score |
| Discovery summary report | Git repo / Blob Storage | Markdown |

## 4. OAC Asset Types to Discover

### 4.1 Catalog Objects (via OAC REST API)

```
GET /api/20210901/catalog/
```

| Asset Type | API Endpoint | Key Metadata |
|---|---|---|
| Analyses | `/catalog?type=analysis` | Name, path, owner, columns used, filters, prompts |
| Dashboards | `/catalog?type=dashboard` | Name, path, pages, embedded analyses |
| Data Models | `/catalog?type=dataModel` | Name, tables, joins, relationships |
| Prompts | `/catalog?type=prompt` | Name, type, bound columns |
| Filters | `/catalog?type=filter` | Name, filter expression |
| Agents / Alerts | `/catalog?type=agent` | Name, schedule, conditions |
| Data Flows | `/catalog?type=dataflow` | Name, steps, source/target |
| Connections | `/connections` | Name, type, connection string |

### 4.2 RPD Model (via XML Parsing)

| Layer | Elements to Extract |
|---|---|
| **Physical Layer** | Databases, tables, columns, data types, constraints, keys |
| **Business Model (Logical)** | Logical tables, columns, joins, calculated columns, expressions, hierarchies, dimensions |
| **Presentation Layer** | Subject areas, presentation tables, presentation columns, ordering |

### 4.3 Security Objects

| Object | Source |
|---|---|
| Application Roles | OAC REST API / RPD |
| Role Assignments (User → Role) | OAC Identity API |
| Row-Level Security Filters | RPD session variable initialization blocks |
| Object Permissions | RPD presentation layer permissions |

## 5. Core Logic

### 5.1 Discovery Flow

```
1. Authenticate to OAC (OAuth2)
2. Crawl catalog recursively (paginated)
   2.1 For each catalog item, extract metadata
   2.2 Store in Lakehouse Delta table (MERGE by path)
3. Parse RPD XML export
   3.1 Extract physical layer → table/column definitions
   3.2 Extract logical layer → business model
   3.3 Extract presentation layer → subject areas
   3.4 Extract security → roles, RLS, permissions
4. Build dependency graph
   4.1 Analysis → Subject Area → Logical Table → Physical Table
   4.2 Dashboard → Analysis dependencies
   4.3 Data Flow → Source/Target table dependencies
5. Calculate migration complexity score per asset
6. Generate summary report
```

### 5.2 Complexity Scoring

| Factor | Weight | Score Range |
|---|---|---|
| Number of columns / measures | 0.1 | 1–10 |
| Custom calculations (OAC expressions) | 0.3 | 1–10 |
| Number of prompts / filters | 0.1 | 1–10 |
| Number of dashboard pages | 0.1 | 1–10 |
| RLS complexity | 0.2 | 1–10 |
| Custom visualizations or plugins | 0.2 | 1–10 |

**Total complexity = Σ(weight × score)** → categorized as Low (1–3), Medium (4–6), High (7–10).

### 5.3 Delta Table Row Schema

```json
{
  "id": "analysis__shared__sales__revenue_analysis",
  "assetType": "analysis",
  "sourcePath": "/shared/Sales/Revenue Analysis",
  "name": "Revenue Analysis",
  "owner": "admin",
  "lastModified": "2025-01-15T10:30:00Z",
  "metadata": {
    "columns": ["Revenue", "Region", "Product"],
    "filters": ["Year = 2024"],
    "prompts": ["Region Prompt"],
    "subjectArea": "Sales - Revenue"
  },
  "dependencies": [
    { "type": "subjectArea", "id": "sa__sales_revenue" },
    { "type": "prompt", "id": "prompt__region" }
  ],
  "complexityScore": 4.2,
  "complexityCategory": "Medium",
  "migrationStatus": "not-started",
  "migrationWave": 3
}
```

## 6. Error Handling

| Error | Handling |
|---|---|
| OAC API 401/403 | Refresh token; if still failing, log and alert |
| OAC API 429 (throttling) | Exponential backoff with jitter |
| RPD XML parse error | Log specific element; continue with partial parse |
| Missing asset metadata | Create placeholder with `incomplete: true` flag |
| Lakehouse write failure | Retry with backoff; dead-letter after 3 attempts |

## 7. Testing Strategy

| Test Type | Approach |
|---|---|
| Unit tests | Mock OAC API responses; parse sample RPD XML fragments |
| Integration tests | Use recorded OAC API responses (VCR pattern) |
| Completeness tests | Compare discovered count vs known OAC catalog count |
| Idempotency tests | Run discovery twice; verify no duplicates in Lakehouse |
