# Full OAC Object Gap Analysis — All Agents

**Date:** 2026-03-26 · v4.0.0 (Phase 46 complete)  
**Scope:** Every OAC object type, every agent's responsibility, migration target, implementation status, and gaps  
**Audience:** All 8 agents + Orchestrator  

---

## Executive Summary

| Metric | Value |
|--------|-------|
| OAC Object Categories | **12** (Catalog, RPD Physical, RPD Logical, RPD Presentation, Security, Data Flows, Scheduling, Prompts/Alerts, Themes, Mobile, Custom Plugins, Notifications) |
| Total OAC Object Types Identified | **62** |
| Fully Automated | **38** (61%) |
| Partially Automated (review needed) | **15** (24%) |
| Not Implemented / Manual Only | **9** (15%) |
| Agents Involved | All 8 (Discovery → Schema → ETL → Semantic → Report → Security → Validation → Orchestrator) |
| Tests Passing | 2,618 (96.2% coverage) |
| DAX Expression Rules | 260+ (across all connectors) |
| Visual Type Mappings | 25 OAC → PBI |

### Status Legend

| Icon | Meaning |
|------|---------|
| ✅ | Fully implemented and tested |
| 🟡 | Partially implemented or approximated — review recommended |
| ❌ | Not implemented — manual migration required |
| 🔮 | Planned for v5.0 |

---

## 1. Discovery & Inventory Layer (Agent 01)

**Owner:** Discovery Agent · `src/agents/discovery/`  
**Target:** `migration_inventory` Delta table, dependency DAG JSON, complexity CSV

### 1.1 OAC Catalog Objects (REST API)

| # | OAC Object Type | Discovered | Fabric/PBI Target | Status | Gap |
|---|----------------|:----------:|-------------------|:------:|-----|
| 1 | **Analyses** | ✅ | Report Agent (05) input | ✅ | — |
| 2 | **Dashboards** | ✅ | Report Agent (05) input | ✅ | — |
| 3 | **Data Models** | ✅ | Semantic Agent (04) input | ✅ | — |
| 4 | **Prompts** | ✅ | Report Agent (05) slicers | ✅ | — |
| 5 | **Filters (named)** | ✅ | Report Agent (05) filter config | ✅ | — |
| 6 | **Agents / Alerts** | ✅ | PBI data-driven alerts (manual mapping) | 🟡 | No automated alert-to-PBI-alert migration; only inventory extraction |
| 7 | **Data Flows** | ✅ | ETL Agent (03) input | ✅ | — |
| 8 | **Connections** | ✅ | Schema Agent (02) Fabric connection config | ✅ | Credential passthrough — secrets not migrated (Key Vault only) |
| 9 | **Published Data Sets** | ✅ | Semantic Agent (04) shared model | 🟡 | No shared semantic model merge engine (T2P has this) |
| 10 | **KPIs / Scorecards** | 🟡 | PBI Goals / Scorecard | 🟡 | Discovered as analysis sub-objects; no dedicated KPI→Goals converter |
| 11 | **Stories (Narration)** | 🟡 | PBI bookmarks + textbox | 🟡 | Story points partially mapped; narrative content loses interactivity |
| 12 | **Favorites / Tags** | ❌ | PBI favorites / endorsement | ❌ | Not extracted from OAC; no PBI favorites API integration |
| 13 | **Scheduler Jobs** | ✅ | ETL Agent (03) triggers | ✅ | — |
| 14 | **Custom Plugins / Extensions** | ❌ | Custom PBI visuals | ❌ | Flagged as unsupported; no fallback visual strategy |

### 1.2 RPD Physical Layer

| # | OAC Object Type | Discovered | Fabric Target | Status | Gap |
|---|----------------|:----------:|---------------|:------:|-----|
| 15 | **Physical Databases / Schemas** | ✅ | Fabric Lakehouse/Warehouse | ✅ | — |
| 16 | **Physical Tables** | ✅ | Delta tables | ✅ | — |
| 17 | **Physical Columns + Data Types** | ✅ | Delta/T-SQL columns | ✅ | 25 Oracle→Delta type mappings implemented |
| 18 | **Primary Keys** | ✅ | Not enforced in Delta | 🟡 | Discovered but Delta tables have no PK constraint enforcement |
| 19 | **Foreign Keys** | ✅ | TMDL relationships | 🟡 | Used for relationship generation; not enforced at storage layer |
| 20 | **Indexes** | ✅ | N/A (Delta auto-optimizes) | 🟡 | Discovered but no equivalent in Lakehouse; Z-ORDER suggested in docs |
| 21 | **Table Partitions** | 🟡 | Delta partitioning | 🟡 | Discovered but flattened — no partition strategy generated |
| 22 | **Materialized Views** | ❌ | Lakehouse views / computed tables | ❌ | Not migrated; no Fabric equivalent |
| 23 | **Virtual Columns** | 🟡 | TMDL calculated columns | 🟡 | Treated as regular columns; computed expression not preserved |
| 24 | **Oracle Sequences** | 🟡 | Identity columns | 🟡 | Mapping exists but not validated at scale |
| 25 | **Oracle Synonyms** | ❌ | N/A | ❌ | Not discovered or mapped |
| 26 | **Database Links** | ❌ | Fabric Shortcuts / linked services | ❌ | Not discovered or mapped |
| 27 | **Oracle Packages (DDL)** | 🟡 | PySpark notebooks | 🟡 | PL/SQL body translated; package-level state/context lost |

### 1.3 RPD Business/Logical Layer

| # | OAC Object Type | Discovered | Fabric/PBI Target | Status | Gap |
|---|----------------|:----------:|-------------------|:------:|-----|
| 28 | **Logical Tables** | ✅ | TMDL tables | ✅ | — |
| 29 | **Logical Columns (direct mapped)** | ✅ | TMDL columns | ✅ | — |
| 30 | **Logical Columns (calculated/derived)** | ✅ | TMDL measures / calc columns | ✅ | 60+ OAC→DAX rules; LLM fallback for complex |
| 31 | **Logical Table Sources (LTS)** | ✅ | TMDL partitions (SQL/M) | ✅ | — |
| 32 | **Logical Joins** | ✅ | TMDL relationships | ✅ | 1:N mapped; M:N flagged for manual bridge table |
| 33 | **Hierarchies** | ✅ | TMDL hierarchies with levels | ✅ | — |
| 34 | **Calculated Measures (OAC expressions)** | ✅ | DAX measures | ✅ | Hybrid: rules + LLM; confidence scoring |
| 35 | **Session Variables** | ✅ | RLS DAX filters (USERPRINCIPALNAME) | ✅ | — |
| 36 | **Init Blocks** | ✅ | Security lookup tables in Lakehouse | ✅ | Oracle SQL translated to Fabric |
| 37 | **Dimension Tables / Fact Tables** | ✅ | TMDL table types | ✅ | — |
| 38 | **Aggregation Rules** | 🟡 | DAX SUMMARIZE / aggregation tables | 🟡 | Pre-defined aggs not translated; schema optimizer (Phase 45) recommends |
| 39 | **Level-Based Measures** | 🟡 | CALCULATE + ALLEXCEPT pattern | 🟡 | Complex AGGREGATE_AT_LEVEL approximated; review needed |
| 40 | **Multi-database joins (Federation)** | ❌ | Fabric Shortcuts / cross-Lakehouse | ❌ | Federated physical sources not handled; single-source assumption |

### 1.4 RPD Presentation Layer

| # | OAC Object Type | Discovered | PBI Target | Status | Gap |
|---|----------------|:----------:|------------|:------:|-----|
| 41 | **Subject Areas** | ✅ | TMDL perspectives | ✅ | — |
| 42 | **Presentation Tables** | ✅ | Display folders / perspectives | ✅ | — |
| 43 | **Presentation Columns** | ✅ | Column visibility + display folders | 🟡 | All measures in single "Measures" folder; no intelligent grouping |
| 44 | **Column Aliases / Descriptions** | ✅ | TMDL column descriptions | 🟡 | Aliases preserved; descriptions may lose rich formatting |
| 45 | **Column Sorting / Ordering** | ✅ | TMDL sortByColumn | ✅ | — |

### 1.5 Discovery Gaps

| Gap ID | Description | Severity | Agent Owner | Recommendation |
|--------|-------------|:--------:|:-----------:|----------------|
| D-GAP-01 | **No incremental discovery** — full re-crawl every time | 🟡 | 01 | Add delta crawl using OAC modification timestamps |
| D-GAP-02 | **RPD circular references** detected but not resolved | 🔴 | 01 | Add automatic cycle-breaking with logged warnings |
| D-GAP-03 | **OAC version-specific API** differences not handled | 🟡 | 01 | Add OAC version detection + feature-flag API calls |
| D-GAP-04 | **Rate limit tracking** — no per-endpoint counter | 🟢 | 01 | Add 429 rate tracking dashboard metric |
| D-GAP-05 | **OAC Favorites/Tags** not extracted | 🟢 | 01 | Add catalog tag extraction for PBI endorsement mapping |
| D-GAP-06 | **Published Data Sets** — no shared model concept | 🟡 | 01→04 | Extract published dataset references for shared semantic model |

---

## 2. Schema & Data Model Migration Layer (Agent 02)

**Owner:** Schema Agent · `src/agents/schema/`  
**Target:** Fabric Lakehouse (Delta) / Fabric Warehouse (T-SQL)

### 2.1 Schema Object Coverage

| # | Source Object | Mapping | Target | Status | Gap |
|---|-------------|---------|--------|:------:|-----|
| 1 | Oracle tables | 25 type mappings | Delta CREATE TABLE | ✅ | — |
| 2 | Oracle views | SQL translation | Lakehouse views | 🟡 | Complex cross-view dependencies may fail |
| 3 | Oracle materialized views | — | — | ❌ | No Fabric equiv; manual recreation as view/computed table |
| 4 | Oracle sequences | → identity columns | Fabric identity | 🟡 | Not validated at scale |
| 5 | Oracle constraints (PK/FK) | — | N/A in Delta | 🟡 | Discovered; used for TMDL relationships, not enforced at storage |
| 6 | Oracle indexes | — | N/A in Delta | 🟡 | No equiv; Z-ORDER optimization guidance generated |
| 7 | Oracle partitions | — | Delta partitioning | 🟡 | Flattened; no auto-partition strategy |
| 8 | Oracle synonyms | — | — | ❌ | Not handled |
| 9 | Oracle database links | — | Fabric Shortcuts | ❌ | Not handled |
| 10 | Oracle virtual columns | → regular columns | Delta columns | 🟡 | Expression not preserved |
| 11 | Oracle Edition-based redefinition | — | — | ❌ | Oracle-specific; no equivalent |
| 12 | Oracle packages (DDL only) | — | Notebooks | 🟡 | Package body only; state/context lost |

### 2.2 SQL Translation Coverage (14+ functions)

| Oracle SQL | Spark SQL | T-SQL | Status |
|-----------|-----------|-------|:------:|
| NVL / NVL2 | COALESCE / CASE | COALESCE / CASE | ✅ |
| DECODE | CASE WHEN | CASE WHEN | ✅ |
| SYSDATE / SYSTIMESTAMP | CURRENT_TIMESTAMP | GETDATE / SYSDATETIMEOFFSET | ✅ |
| TO_CHAR / TO_DATE / TO_NUMBER | DATE_FORMAT / TO_DATE / CAST | FORMAT / CONVERT / CAST | ✅ |
| SUBSTR / INSTR / LENGTH | SUBSTRING / LOCATE / LENGTH | SUBSTRING / CHARINDEX / LEN | ✅ |
| TRUNC / MONTHS_BETWEEN | DATE_TRUNC / MONTHS_BETWEEN | CAST / DATEDIFF | ✅ |
| LISTAGG | CONCAT_WS(COLLECT_LIST) | STRING_AGG | ✅ |
| ROWNUM | → ROW_NUMBER() | → ROW_NUMBER() | 🟡 Flagged |
| (+) outer join | → Flagged | → Flagged | 🟡 Flagged |
| CONNECT BY (hierarchical) | → Flagged | → Flagged | 🟡 Flagged |
| MERGE | Delta MERGE | T-SQL MERGE | ✅ |
| PL/SQL CURSOR loops | spark.sql().collect() | — | ✅ |
| BULK COLLECT | DataFrame ops | — | ✅ |
| Dynamic SQL (EXECUTE IMMEDIATE) | — | — | 🟡 LLM-assisted |
| Analytical functions (OVER) | Spark window functions | T-SQL window functions | ✅ |
| XMLType functions | → STRING parse | → VARCHAR(MAX) parse | 🟡 Structure lost |
| Regular expressions (REGEXP_*) | Spark regex | T-SQL LIKE/PATINDEX | 🟡 Partial mapping |

### 2.3 Data Loading

| Mode | Implementation | Status |
|------|---------------|:------:|
| Full load (parallel by PK range, 100K batch) | Copy Activity / PySpark | ✅ |
| Incremental (watermark MERGE) | Delta MERGE | ✅ |
| Partition-aware copy | — | ❌ |

### 2.4 Schema Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| S-GAP-01 | **Materialized views** not migrated | 🔴 | Add manual guidance doc; generate placeholder view DDL |
| S-GAP-02 | **Oracle partitioning** flattened | 🟡 | Use Phase 45 schema optimizer for Delta partition recommendations |
| S-GAP-03 | **Cross-view dependency** resolution incomplete | 🟡 | Migrate views in dependency order from DAG |
| S-GAP-04 | **Synonyms** not mapped | 🟡 | Add synonym→view alias generation |
| S-GAP-05 | **Database links** → Fabric Shortcuts | 🟡 | Add Fabric Shortcut generation for cross-source references |
| S-GAP-06 | **No partition-aware data copy** | 🟡 | Parallelize by partition for large tables |
| S-GAP-07 | **XMLTYPE structure** serialized as string | 🟢 | Add PySpark XML parsing template for downstream use |

---

## 3. ETL / Pipeline Migration Layer (Agent 03)

**Owner:** ETL Agent · `src/agents/etl/`  
**Target:** Fabric Data Factory pipelines, Dataflow Gen2, PySpark Notebooks, Fabric triggers

### 3.1 OAC Data Flow Step Coverage (16 steps mapped)

| # | OAC Data Flow Step | Fabric Target | Status | Gap |
|---|-------------------|---------------|:------:|-----|
| 1 | Source (Database) | Copy Activity | ✅ | — |
| 2 | Source (File) | Copy Activity | ✅ | — |
| 3 | Filter | Filter Activity / Spark `.filter()` | ✅ | — |
| 4 | Join | Join Activity / Spark `.join()` | ✅ | — |
| 5 | Aggregate | Aggregate Activity / `.groupBy().agg()` | ✅ | — |
| 6 | Lookup | Lookup Activity / broadcast join | ✅ | — |
| 7 | Union | Union / `.union()` | ✅ | — |
| 8 | Sort | Sort / `.orderBy()` | ✅ | — |
| 9 | Add Column | Derived Column / `.withColumn()` | ✅ | — |
| 10 | Rename Column | Column rename / `.withColumnRenamed()` | ✅ | — |
| 11 | Type Conversion | CAST / `.cast()` | ✅ | — |
| 12 | Branch / Conditional | If Condition Activity | ✅ | — |
| 13 | Loop | ForEach Activity | ✅ | — |
| 14 | Target (Database) | Copy Activity (sink) | ✅ | — |
| 15 | Target (File) | Copy Activity (sink) | ✅ | — |
| 16 | Stored Procedure Call | Notebook Activity (PySpark) | ✅ | — |
| 17 | **Pivot / Unpivot** | — | 🟡 | Not yet mapped to M-query or Spark |
| 18 | **Data Quality / Profiling** | — | ❌ | No DQ step migration; add data profiling template |
| 19 | **Error row handling** | — | ❌ | No rejected row routing strategy |

### 3.2 PL/SQL → PySpark Translation (12 patterns)

| PL/SQL Pattern | PySpark Target | Status |
|---------------|----------------|:------:|
| Cursor loop (FOR r IN ...) | spark.sql().collect() + Python loop | ✅ |
| INSERT INTO SELECT | df.write.mode("append") | ✅ |
| UPDATE with SET | Delta MERGE (whenMatched) | ✅ |
| DELETE with WHERE | Delta MERGE (whenMatched → delete) | ✅ |
| MERGE INTO | Delta MERGE (full) | ✅ |
| EXCEPTION WHEN | try/except | ✅ |
| BULK COLLECT | DataFrame collection ops | ✅ |
| Temporary tables | Spark temp views / Delta | ✅ |
| Sequences | monotonically_increasing_id() | 🟡 |
| FOR ... LOOP | Python for loop | ✅ |
| EXECUTE IMMEDIATE (dynamic SQL) | spark.sql(f-string) | 🟡 LLM-assisted |
| PL/SQL packages (multi-procedure) | Notebook cells (one per proc) | 🟡 Inter-proc deps may break |

### 3.3 Schedule Migration

| OAC/Oracle Source | Fabric Target | Status |
|------------------|---------------|:------:|
| DBMS_SCHEDULER — daily | Fabric trigger (daily) | ✅ |
| DBMS_SCHEDULER — hourly | Fabric trigger (hourly) | ✅ |
| DBMS_SCHEDULER — cron | Fabric trigger (cron) | ✅ |
| DBMS_SCHEDULER — calendar expressions | Cron approximation | 🟡 Complex expressions may lose precision |
| Job chains (sequential) | Sequential pipeline activities | ✅ |
| Job chains (parallel branches) | — | ❌ Parallel branches not generated |
| Inter-job dependencies | — | 🟡 Trigger dependencies not chained |

### 3.4 ETL Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| E-GAP-01 | **Dataflow Gen2** only simple M queries | 🟡 | Route complex transforms to PySpark notebooks |
| E-GAP-02 | **No environment parameterization** (dev/test/prod) | 🟡 | Inject connection params via pipeline parameters |
| E-GAP-03 | **Complex PL/SQL packages** with inter-proc deps | 🔴 | LLM-assisted decomposition + manual review |
| E-GAP-04 | **Parallel job chains** not generated | 🟡 | Add parallel branch detection in DAG analysis |
| E-GAP-05 | **No post-deployment alerting** on pipelines | 🟡 | Add Fabric alerting template generation |
| E-GAP-06 | **Pivot/Unpivot** steps not mapped | 🟡 | Add Spark pivot/unpivot templates |
| E-GAP-07 | **Data quality / error routing** not implemented | 🟡 | Add DQ profiling notebook template |

---

## 4. Semantic Model Migration Layer (Agent 04)

**Owner:** Semantic Model Agent · `src/agents/semantic/`  
**Target:** TMDL semantic model (model.tmdl, tables/*.tmdl, relationships.tmdl, roles.tmdl, perspectives.tmdl)

### 4.1 RPD → TMDL Concept Mapping

| # | RPD Concept | TMDL Concept | Status | Gap |
|---|------------|-------------|:------:|-----|
| 1 | Logical Table | Table | ✅ | — |
| 2 | Logical Column (direct) | Column (sourceColumn binding) | ✅ | — |
| 3 | Logical Column (calculated) | Measure or Calculated Column | ✅ | 60+ rules + LLM |
| 4 | Logical Table Source | Partition (SQL/M expression) | ✅ | — |
| 5 | Logical Join (1:N) | Relationship (one→many) | ✅ | — |
| 6 | Logical Join (M:N) | — | 🟡 | Detected; bridge table not auto-generated |
| 7 | Hierarchy | Hierarchy with Levels | ✅ | — |
| 8 | Presentation Table | Perspective / Display Folder | ✅ | — |
| 9 | Subject Area | Perspective | ✅ | — |
| 10 | Presentation Column | Column visibility | 🟡 | Flat "Measures" folder; no intelligent grouping |

### 4.2 DAX Expression Translation (60+ rules)

| Category | Rules | Coverage | Status |
|----------|:-----:|:--------:|:------:|
| Aggregations (SUM, COUNT, AVG, MIN, MAX, etc.) | 10 | 100% | ✅ |
| Time Intelligence (AGO, TODATE, PERIODROLLING, etc.) | 14 | 90% | ✅ |
| String Functions (UPPER, LOWER, MID, REPLACE, etc.) | 14 | 95% | ✅ |
| Math Functions (ABS, ROUND, POWER, etc.) | 12 | 100% | ✅ |
| Date Functions (EXTRACT, ADD_MONTHS, etc.) | 16 | 95% | ✅ |
| Logical Functions (CASE, IIF, COALESCE, etc.) | 6 | 100% | ✅ |
| Filter/Table Functions (FILTER, ALL, RELATED, etc.) | 5 | 85% | 🟡 |
| Statistical (PERCENTILE, RANK, NTILE, TOPN) | 4 | 80% | 🟡 |
| Level-Based (AGGREGATE_AT_LEVEL, SHARE) | 2 | 60% | 🟡 |
| Information (VALUEOF, DESCRIPTOR_IDOF, INDEXCOL) | 3 | 70% | 🟡 |
| **Total OAC-native** | **86** | **~90%** | ✅ |

### 4.3 Missing DAX Capabilities vs. T2P

| Feature | T2P Status | OAC→Fabric Status | Priority |
|---------|:----------:|:-----------------:|:--------:|
| 180+ DAX rules (all sources combined) | ✅ | 260+ (across 5 connectors) | ✅ Parity achieved |
| DAX Optimizer (AST rewriter: IF→SWITCH, COALESCE) | ✅ | ❌ phase 46 has DAXOptimizer in perf_auto_tuner but post-translation only | 🔴 P1 |
| Auto Calendar/Date table generation | ✅ | ❌ | 🔴 P1 |
| TMDL Self-Healing (duplicate tables, broken refs) | ✅ | ❌ | 🔴 P1 |
| Calculation Groups | ✅ (partial) | ❌ | 🟡 P2 |
| Composite model / aggregation tables | ✅ | 🟡 Phase 46 `CompositeModelAdvisor` recommends but doesn't generate | 🟡 P2 |
| Shared semantic model (merge engine) | ✅ | ❌ | 🟡 P2 |
| Incremental TMDL update (delta) | ✅ | ❌ (full regeneration only) | 🟢 P3 |
| Display folder intelligence | ✅ (by data source) | ❌ (flat "Measures") | 🟢 P3 |

### 4.4 Semantic Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| SM-GAP-01 | **M:N relationships** — bridge table not auto-generated | 🔴 | Generate bridge table DDL + TMDL relationship |
| SM-GAP-02 | **No Auto Calendar table** — date dimension must exist | 🔴 | Detect date columns, generate Calendar table + time intel measures |
| SM-GAP-03 | **No TMDL self-healing** — broken refs crash deployment | 🔴 | Add pre-deployment TMDL validator + auto-fix (duplicates, empty names, broken refs) |
| SM-GAP-04 | **No DAX post-translation optimizer** | 🟡 | Add AST rewriter: IF→SWITCH, ISBLANK→COALESCE, constant folding |
| SM-GAP-05 | **Calculation groups** not generated | 🟡 | Add calculation group templates for common patterns (currency, time) |
| SM-GAP-06 | **Display folder** strategy is flat | 🟢 | Group by RPD presentation table/subject area |
| SM-GAP-07 | **No shared semantic model** for multiple reports | 🟡 | Add merge engine (fingerprint matching as in T2P) |
| SM-GAP-08 | **No lineage tracking** (OAC source → TMDL target) | 🟡 | Generate lineage_map.json per migration |

---

## 5. Report & Dashboard Migration Layer (Agent 05)

**Owner:** Report Agent · `src/agents/report/`  
**Target:** PBIR reports (definition.pbir, report.json, pages/*, visuals/*)

### 5.1 Visual Type Coverage

| # | OAC Visual Type | PBI Visual | Status | Gap |
|---|----------------|-----------|:------:|-----|
| 1 | Table | tableEx | ✅ | — |
| 2 | Pivot Table | pivotTable (Matrix) | ✅ | — |
| 3 | Vertical Bar | clusteredColumnChart | ✅ | — |
| 4 | Horizontal Bar | clusteredBarChart | ✅ | — |
| 5 | Stacked Bar | stackedBarChart | ✅ | — |
| 6 | Stacked Column | stackedColumnChart | ✅ | — |
| 7 | Line Chart | lineChart | ✅ | — |
| 8 | Area Chart | areaChart | ✅ | — |
| 9 | Combo (Bar+Line) | lineClusteredColumnComboChart | ✅ | — |
| 10 | Pie Chart | pieChart | ✅ | — |
| 11 | Donut Chart | donutChart | ✅ | — |
| 12 | Scatter Plot | scatterChart | ✅ | — |
| 13 | Bubble Chart | scatterChart (with size) | ✅ | — |
| 14 | Filled Map | filledMap | ✅ | — |
| 15 | Bubble Map | map (lat/long) | ✅ | — |
| 16 | Gauge | gauge | ✅ | — |
| 17 | KPI / Metric | card | ✅ | — |
| 18 | Funnel | funnel | ✅ | — |
| 19 | Treemap | treemap | ✅ | — |
| 20 | Heatmap | Matrix + conditional formatting | ✅ | — |
| 21 | Waterfall | waterfallChart | ✅ | — |
| 22 | Narrative / Text | textbox | ✅ | — |
| 23 | Image | image | ✅ | — |
| 24 | Trellis / Small Multiples | Small Multiples field | 🟡 | Complex multi-axis trellis incomplete |
| 25 | Unknown/Fallback | tableEx | ✅ (fallback) | — |
| — | **MISSING TYPES** | | | |
| 26 | 100% Stacked Bar/Column | percentStackedBarChart | ❌ | Not mapped |
| 27 | Box Plot / Box-and-Whisker | — | ❌ | No PBI native; needs custom visual |
| 28 | Histogram (native) | — | ❌ | Map to clusteredColumnChart with binning |
| 29 | Radar / Spider Chart | — | ❌ | AppSource custom visual needed |
| 30 | Sankey / Flow | — | ❌ | AppSource custom visual needed |
| 31 | Sunburst | — | ❌ | AppSource custom visual needed |
| 32 | Parallel Coordinates | — | ❌ | No PBI equivalent |
| 33 | Network / Graph | — | ❌ | No PBI native; Force-Directed Graph custom visual |
| 34 | Calendar Heatmap | — | ❌ | Custom visual needed |
| 35 | Sparklines (inline) | Sparklines in table/matrix | 🟡 | PBI supports natively; not mapped yet |
| 36 | Multi-Row Card | multiRowCard | ❌ | Not mapped from OAC metric cards |

### 5.2 Prompt/Filter → Slicer Mapping

| # | OAC Prompt Type | PBI Equivalent | Status |
|---|----------------|----------------|:------:|
| 1 | Dropdown (single) | Slicer (dropdown, single) | ✅ |
| 2 | Dropdown (multi) | Slicer (dropdown, multi) | ✅ |
| 3 | Search / Type-ahead | Slicer with search | ✅ |
| 4 | Slider (range) | Slicer (between range) | ✅ |
| 5 | Date Picker | Slicer (date range / relative) | ✅ |
| 6 | Radio Button | Slicer (tile, single) | ✅ |
| 7 | Checkbox | Slicer (tile, multi) | ✅ |
| 8 | Text Input | What-if parameter / text filter | ✅ |
| 9 | Cascading Prompt | Multiple slicers + relationship filtering | 🟡 | Approximated |
| 10 | **Variable prompt** (bind to session var) | — | ❌ | Not mapped to PBI What-if parameter |

### 5.3 Interactivity & Layout

| Feature | OAC | PBI Target | Status | Gap |
|---------|-----|-----------|:------:|-----|
| Dashboard actions (navigate) | ✅ | Drillthrough pages | ✅ | — |
| Dashboard actions (filter) | ✅ | Cross-filter / highlight | ✅ | — |
| Master-detail | ✅ | Drillthrough + bookmarks | ✅ | — |
| Conditional formatting (color) | ✅ | Field value rules | ✅ | — |
| Conditional formatting (data bars) | ✅ | Data bars in matrix | ✅ | — |
| Conditional formatting (icons/stoplight) | ✅ | Icons formatting | ✅ | — |
| Theme / custom palette | ✅ | — | ❌ | No OAC theme → PBI theme mapping |
| Mobile / responsive layout | ✅ | Phone layout | ❌ | Not generated |
| Bookmarks (story points) | ✅ | PBI bookmarks | 🟡 | Action-based only; story content loses interactivity |
| Tooltip pages | ✅ (drill-down) | Tooltip pages | ❌ | Not generated |
| Pagination (50+ visuals) | ✅ | Multi-page reports | ❌ | Auto-pagination not implemented |
| Dynamic zone visibility | ✅ | Selection pane + bookmarks | 🟡 | Approximated |
| Real-time / auto-refresh | ✅ | Automatic page refresh | ❌ | Not configured in PBIR |

### 5.4 Report Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| R-GAP-01 | **Only 25 visual types** (T2P maps 118+) | 🔴 | Expand to 40+ mappings; add 100% stacked, box plot, histogram, sparklines |
| R-GAP-02 | **No theme migration** | 🟡 | Extract OAC color palette → PBI theme JSON |
| R-GAP-03 | **No mobile layout** | 🟡 | Generate phone layout from grid positions |
| R-GAP-04 | **No tooltip pages** | 🟡 | Map OAC drill-down configs to PBI tooltip pages |
| R-GAP-05 | **No pagination** for large reports | 🟢 | Auto-split reports > 30 visuals |
| R-GAP-06 | **Custom plugins** unsupported with no fallback | 🔴 | Add fallback visual cascade (custom → nearest PBI → table) |
| R-GAP-07 | **Deeply nested containers** (4+ levels) misalign | 🟡 | Flatten nested containers before layout calculation |
| R-GAP-08 | **No real-time / auto-refresh** config | 🟢 | Add automatic page refresh setting in PBIR |
| R-GAP-09 | **Variable prompts** not mapped | 🟡 | Map to PBI What-if parameters |

---

## 6. Security & Governance Migration Layer (Agent 06)

**Owner:** Security Agent · `src/agents/security/`  
**Target:** PBI RLS roles (TMDL roles.tmdl), OLS definitions, Fabric workspace roles, security lookup tables

### 6.1 Security Object Coverage

| # | OAC Security Object | PBI/Fabric Target | Status | Gap |
|---|--------------------|--------------------|:------:|-----|
| 1 | Application Roles | PBI RLS roles + Fabric workspace roles | ✅ | — |
| 2 | User → Role assignments | AAD group → RLS role membership | ✅ | Manual AAD group creation |
| 3 | Session variable (NQ_SESSION.USER) | USERPRINCIPALNAME() | ✅ | — |
| 4 | Session variable (NQ_SESSION.GROUP) | Lookup table + USERPRINCIPALNAME() | ✅ | — |
| 5 | Session variable (NQ_SESSION.REGION) | Lookup table + USERPRINCIPALNAME() | ✅ | — |
| 6 | Init blocks (Oracle SQL) | Security lookup tables (Delta) | ✅ | — |
| 7 | Object-level permissions (hide col/table) | OLS metadataPermission = none | ✅ | — |
| 8 | **Row filter with hierarchy-based access** | — | ❌ | Complex parent-child RLS not auto-generated |
| 9 | **Multi-valued session variables** | Lookup table (1:many) | 🟡 | Complex OR/AND combos need manual tuning |
| 10 | **Data-level permissions (cell-level)** | — | ❌ | Not expressible in PBI RLS (row-level only) |
| 11 | **Dynamic dashboard permissions** | — | ❌ | Not expressible in PBI workspace roles alone |
| 12 | **Sensitivity labels** | Purview labels | ❌ | Not migrated |
| 13 | **Audit trail** | Fabric governance | ❌ | Historical OAC audit events not migrated |
| 14 | **Azure AD group provisioning** | AAD groups | 🟡 | CSV mapping generated; no automated group creation |

### 6.2 Workspace Role Mapping

| OAC Role | Fabric/PBI Role | Status |
|----------|-----------------|:------:|
| Admin | Workspace Admin | ✅ |
| Creator / Publisher | Workspace Contributor | ✅ |
| Consumer / Viewer | Workspace Viewer | ✅ |
| Custom roles | — | 🟡 | Mapped to nearest built-in; custom workspace roles not supported in Fabric |

### 6.3 Security Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| SEC-GAP-01 | **Hierarchy-based RLS** not auto-generated | 🔴 | Add parent-child hierarchy RLS DAX generator |
| SEC-GAP-02 | **Sensitivity labels** not migrated to Purview | 🟡 | Add Purview API integration for label mapping |
| SEC-GAP-03 | **No AAD group provisioning** automation | 🟡 | Add Microsoft Graph API batch group creation |
| SEC-GAP-04 | **Cell-level security** not expressible in PBI | 🔴 | Document as known limitation; suggest OLS + row filter combo |
| SEC-GAP-05 | **Audit trail** not migrated | 🟢 | Export OAC audit logs to archive; Fabric generates its own audit |
| SEC-GAP-06 | **Governance framework** (naming, PII detection) missing | 🟡 | Port from T2P: naming convention enforcement, PII column scanning |

---

## 7. Validation & Testing Layer (Agent 07)

**Owner:** Validation Agent · `src/agents/validation/`, `src/validation/`, `tests/`  
**Target:** validation_results Delta table, reconciliation reports, visual comparison gallery

### 7.1 Validation Layer Coverage

| Validation Type | Checks | Status | Gap |
|----------------|:------:|:------:|-----|
| **Data reconciliation** | Row counts, checksums, null counts, distinct counts, min/max, sample rows, aggregate totals, data types | ✅ | No statistical sampling for >100M row tables |
| **Semantic model** | Measure results, relationship joins, hierarchy drill, filter context, calc columns, time intelligence | ✅ | — |
| **Report validation** | Visual count, visual types, data displayed, slicer behavior, drillthrough, conditional formatting | ✅ | — |
| **Visual comparison** | Playwright screenshots + SSIM scoring + GPT-4o comparison | ✅ | Pixel-based; borderline cases need manual review |
| **Security validation** | Per-user RLS test, OLS enforcement, role membership | ✅ | — |
| **Performance benchmarks** | Load time, query time, refresh time, concurrency | ✅ | — |
| **Schema drift detection** | — | ❌ | No post-migration schema drift monitoring |
| **Continuous regression** | — | ❌ | No scheduled re-validation after go-live (planned Phase 49) |
| **Statistical sampling** | — | ❌ | No sampling strategy for very large tables |
| **Test data masking** | — | ❌ | No masking for lower environments |

### 7.2 Validation Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| V-GAP-01 | **No schema drift detection** post-migration | 🟡 | Add periodic schema snapshot + comparison (Phase 49) |
| V-GAP-02 | **No sampling strategy** for >100M rows | 🟡 | Add configurable statistical sampling (1%, 5%, 10%) |
| V-GAP-03 | **No continuous validation** after go-live | 🟡 | Schedule periodic re-validation via Fabric triggers |
| V-GAP-04 | **No test data masking** | 🟡 | Add data masking for non-prod environments |
| V-GAP-05 | **Visual comparison** is screenshot-only | 🟢 | SSIM + GPT-4o covers most cases; add DOM-level diff as backup |

---

## 8. Orchestration & Platform Layer (Agent 08)

**Owner:** Orchestrator Agent · `src/agents/orchestrator/`, `src/cli/`, `src/api/`  
**Target:** DAG execution, wave management, notifications, dashboard

### 8.1 Platform Feature Coverage

| Feature | Status | Gap |
|---------|:------:|-----|
| DAG engine (topological sort, parallel exec, retry) | ✅ | — |
| Wave planner (multi-wave, resource allocation) | ✅ | — |
| Task state machine (7 states) | ✅ | — |
| CLI (Typer: --dry-run, --wave, --config, --resume) | ✅ | — |
| REST API (FastAPI: 7 endpoints) | ✅ | — |
| Team/email/PagerDuty notifications | ✅ | — |
| React dashboard (migration wizard, inventory browser, streaming) | ✅ | — |
| Plugin marketplace (install/publish, sample plugins) | ✅ | — |
| Analytics dashboard (PBI template, 5 pages) | ✅ | — |
| **Dead letter queue** | ❌ | Tasks exceeding max retries stuck in BLOCKED |
| **SLA enforcement** per agent | ❌ | No timeout per agent task |
| **Manual approval gates** between waves | ❌ | No human-in-the-loop approval |
| **Cost tracking** per wave/agent | ❌ | No RU/compute cost metering |
| **GraphQL API** | ❌ | Planned Phase 47 |
| **Dry-run simulator** | ❌ | Planned Phase 48 |
| **Self-service portal** | ❌ | Planned Phase 50 |

### 8.2 Orchestrator Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| O-GAP-01 | **No dead letter queue** for permanently failed tasks | 🟡 | Add DLQ Delta table + alerting |
| O-GAP-02 | **No SLA enforcement** per agent | 🟡 | Add timeout per agent task with escalation |
| O-GAP-03 | **No approval gates** between waves | 🟡 | Add human-approval step in orchestrator DAG |
| O-GAP-04 | **No cost tracking** | 🟢 | Add RU/compute metering from Fabric API |

---

## 9. Cross-Cutting Gaps — Deep Power BI Component Comparison with TableauToPowerBI

### 9.1 TMDL Feature-by-Feature Comparison

| TMDL Feature | T2P | OAC→Fabric | Gap | Severity |
|---|:---:|:---:|---|:---:|
| `model.tmdl` | ✅ multi-culture | ✅ en-US only | OAC hardcodes `en-US` | 🟡 |
| `database.tmdl` (compat level 1600) | ✅ | ❌ | Not generated | 🟡 |
| `tables/*.tmdl` (columns, measures, partitions) | ✅ | ✅ | Parity on basic structure | ✅ |
| `relationships.tmdl` + Union-Find cycle-breaking | ✅ + auto-deactivate | ✅ no cycle-breaking | Missing auto-deactivation of ambiguous cycles | 🟡 |
| `roles.tmdl` (RLS / OLS) | ✅ | ✅ | Parity | ✅ |
| `perspectives.tmdl` | ✅ | ✅ | Parity | ✅ |
| `expressions.tmdl` (M data sources) | ✅ 42 connectors | ✅ Fabric-native | Different scope — both complete for their domain | ✅ |
| `cultures/*.tmdl` (19 languages) | ✅ | ❌ | No multi-language support | 🟡 |
| `lineageTag` UUIDs | ✅ | ✅ | Parity | ✅ |
| `sortByColumn` | ✅ | ✅ | Parity | ✅ |
| `displayFolder` (intelligent grouping) | ✅ | 🟡 flat "Measures" | All measures in one folder | 🟡 |
| `formatString` | ✅ | ✅ | Parity | ✅ |
| `isHidden` | ✅ | ✅ | Parity | ✅ |
| `Copilot_TableDescription` annotations | ✅ | ❌ | No @-tagged metadata | 🟡 |
| Calendar/Date table auto-generation | ✅ 8 cols + hierarchy + 3 TI measures | ❌ | **Not implemented** | 🔴 |
| Self-healing (6 patterns) | ✅ duplicates, broken refs, orphans, empties, circular rels, M try/otherwise | ❌ | **Not implemented** | 🔴 |
| DAX Optimizer (5 pre-deploy rules) | ✅ ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding | 🟡 post-deploy only | perf_auto_tuner has rules but not pre-deploy | 🟡 |
| DAX→M calculated column conversion (15+ patterns) | ✅ | ❌ | No DAX→M optimization | 🟡 |
| 3-phase relationship detection | ✅ explicit + inferred (DAX scan) + cardinality heuristic | 🟡 explicit only | No DAX-based relationship inference | 🟡 |
| Calculated tables | ✅ | ❌ | Not supported | 🟡 |
| Aggregation table auto-generation | ✅ auto-gen Import-mode agg | 🟡 advisor only | Advisor recommends but doesn't generate | 🟡 |
| Shared model merge (fingerprint + Jaccard dedup) | ✅ | ❌ | Not implemented | 🟡 |
| Thin report byPath reference | ✅ | ❌ | Not implemented | 🟡 |

### 9.2 PBIR Feature-by-Feature Comparison

| PBIR Feature | T2P | OAC→Fabric | Gap | Severity |
|---|:---:|:---:|---|:---:|
| Visual type count | **60+** (18 custom GUIDs) | **24** standard only | **36+ types missing** | 🔴 |
| Custom visual GUID registry | ✅ Sankey, Chord, WordCloud, Gantt, Network, + 13 | ❌ zero custom visuals | Not implemented | 🔴 |
| Visual fallback cascade | ✅ 3-tier: complex→simple→table→card | ❌ single fallback to tableEx | Not implemented | 🔴 |
| Bookmarks (saved filter states) | ✅ | ❌ | Not generated | 🔴 |
| Drill-through wiring | ✅ wired into visual JSON | 🟡 metadata stored | actions.json not wired to visuals | 🟡 |
| What-If parameters | ✅ wired | ❌ orphaned code | ParameterConfig exists but unused | 🟡 |
| Cascading slicers (cross-filter DAX) | ✅ auto DAX | 🟡 flagged for manual | No auto DAX generation | 🟡 |
| Visual z-order / overlap detection | ✅ | ❌ arbitrary z | No overlap detection | 🟡 |
| Approximation map (unsupported→nearest + migration notes) | ✅ | ❌ | Not implemented | 🟡 |
| DAX leak detector (source function regex + auto-fix) | ✅ Tableau leaks | ❌ no OAC leak check | Not implemented | 🟡 |
| Pre-migration 8-point assessment | ✅ | ❌ has complexity scoring only | No readiness/feasibility check per asset | 🟡 |

### 9.3 Missing Visual Types (OAC vs. T2P)

| Visual | T2P PBI Type | OAC Status | AppSource? |
|--------|-------------|:---:|:---:|
| 100% Stacked Bar | `hundredPercentStackedBarChart` | ❌ | Built-in |
| 100% Stacked Column | `hundredPercentStackedColumnChart` | ❌ | Built-in |
| Stacked Area | `stackedAreaChart` | ❌ | Built-in |
| 100% Stacked Area | `hundredPercentStackedAreaChart` | ❌ | Built-in |
| Multi-Row Card | `multiRowCard` | ❌ | Built-in |
| Shape Map | `shapeMap` | ❌ | Built-in |
| Sunburst | `sunburst` | ❌ | Built-in |
| Box & Whisker | `boxAndWhisker` | ❌ | Built-in |
| Histogram (binned column) | `clusteredColumnChart` + binning | ❌ | Built-in |
| Sankey Diagram | `ChicagoITSankey1.1.0` | ❌ | AppSource |
| Chord Diagram | `ChicagoITChord1.0.0` | ❌ | AppSource |
| Word Cloud | `WordCloud1633006498960` | ❌ | AppSource |
| Gantt Chart | `GanttByMAQSoftware1.0.0` | ❌ | AppSource |
| Network Navigator | `networkNavigator` | ❌ | AppSource |
| + 13 more custom visuals | various GUIDs | ❌ | AppSource |

### 9.4 T2P Self-Healing Patterns (All Missing in OAC)

| # | Pattern | T2P Implementation | OAC Status |
|---|---------|-------------------|:---:|
| 1 | Duplicate table names | Rename: `Product` → `Product_2` → `Product_3` | ❌ |
| 2 | Broken column references | Hide measure + add `MigrationNote` annotation | ❌ |
| 3 | Orphan measures | Reassign to main table (by column count) | ❌ |
| 4 | Empty table names | Remove from model | ❌ |
| 5 | Circular relationships | Deactivate lowest-priority rel (Union-Find) | ❌ |
| 6 | M query errors | Wrap with `try...otherwise` error handling | ❌ |

### 9.5 T2P Calendar Table (Missing in OAC)

T2P auto-detects date columns and generates:

**Calendar Columns (8):**
| Column | Type | Special |
|--------|------|---------|
| Date | DateTime | Primary key, `isKey: true` |
| Year | Int64 | — |
| Quarter | Text | "Q1"–"Q4" |
| Month | Int64 | 1–12 |
| MonthName | Text | `sortByColumn: Month` |
| Day | Int64 | 1–31 |
| DayOfWeek | Int64 | 1–7 |
| DayName | Text | `sortByColumn: DayOfWeek` |

**Calendar Hierarchy:** Year → Quarter → MonthName → Day

**Auto-Generated Time Intelligence Measures (3):**
```dax
Year To Date = TOTALYTD([Base Measure], 'Calendar'[Date])
Previous Year = CALCULATE([Base Measure], SAMEPERIODLASTYEAR('Calendar'[Date]))
Year Over Year % = DIVIDE([Year To Date] - [Previous Year], [Previous Year])
    formatString: 0.00%
```

### 9.6 New Capabilities Needed (Not in T2P)

| Capability | Description | Owner Agent | Priority |
|-----------|-------------|:-----------:|:--------:|
| Fabric Shortcut generation | For cross-workspace / external data | 02 (Schema) | 🟡 P2 |
| OAC Agents → PBI Alerts | Migrate OAC alert conditions to data-driven alerts | 05 (Report) | 🟡 P2 |
| Real-time / auto-refresh config | Set automatic page refresh in PBIR | 05 (Report) | 🟢 P3 |
| OAC KPIs → PBI Scorecards/Goals | Dedicated KPI migrator | 05 (Report) | 🟡 P2 |
| Hierarchy-based dynamic RLS | Parent-child hierarchy RLS DAX | 06 (Security) | 🔴 P1 |
| Purview sensitivity label mapping | OAC classification → Purview labels | 06 (Security) | 🟡 P2 |
| Data quality profiling in ETL | DQ checks embedded in pipeline | 03 (ETL) | 🟡 P2 |
| OAC function leak detector | Regex scan for untranslated NVL, DECODE, SYSDATE, VALUEOF, etc. | 04 (Semantic) | 🟡 P2 |

---

## 10. Complete OAC Object Inventory — Summary Matrix

### All 62 OAC Object Types by Agent Responsibility

| # | OAC Object | Discovery (01) | Schema (02) | ETL (03) | Semantic (04) | Report (05) | Security (06) | Validation (07) | Status |
|---|-----------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:------:|
| 1 | Analyses | ✅ | | | | ✅ | | ✅ | ✅ |
| 2 | Dashboards | ✅ | | | | ✅ | | ✅ | ✅ |
| 3 | Data Models | ✅ | | | ✅ | | | ✅ | ✅ |
| 4 | Prompts | ✅ | | | | ✅ | | ✅ | ✅ |
| 5 | Named Filters | ✅ | | | | ✅ | | ✅ | ✅ |
| 6 | Agents/Alerts | ✅ | | | | | | | 🟡 |
| 7 | Data Flows | ✅ | | ✅ | | | | ✅ | ✅ |
| 8 | Connections | ✅ | ✅ | | | | | | ✅ |
| 9 | Published Data Sets | ✅ | | | 🟡 | | | | 🟡 |
| 10 | KPIs/Scorecards | 🟡 | | | | 🟡 | | | 🟡 |
| 11 | Stories | 🟡 | | | | 🟡 | | | 🟡 |
| 12 | Favorites/Tags | ❌ | | | | | | | ❌ |
| 13 | Scheduler Jobs | ✅ | | ✅ | | | | | ✅ |
| 14 | Custom Plugins | ❌ | | | | ❌ | | | ❌ |
| 15 | Physical Databases | ✅ | ✅ | | | | | | ✅ |
| 16 | Physical Tables | ✅ | ✅ | | | | | ✅ | ✅ |
| 17 | Physical Columns | ✅ | ✅ | | | | | ✅ | ✅ |
| 18 | Primary Keys | ✅ | 🟡 | | | | | | 🟡 |
| 19 | Foreign Keys | ✅ | 🟡 | | ✅ | | | | 🟡 |
| 20 | Indexes | ✅ | 🟡 | | | | | | 🟡 |
| 21 | Table Partitions | 🟡 | 🟡 | | | | | | 🟡 |
| 22 | Materialized Views | ❌ | ❌ | | | | | | ❌ |
| 23 | Virtual Columns | 🟡 | 🟡 | | | | | | 🟡 |
| 24 | Sequences | 🟡 | 🟡 | | | | | | 🟡 |
| 25 | Synonyms | ❌ | ❌ | | | | | | ❌ |
| 26 | Database Links | ❌ | ❌ | | | | | | ❌ |
| 27 | Oracle Packages | 🟡 | | 🟡 | | | | | 🟡 |
| 28 | Logical Tables | ✅ | | | ✅ | | | ✅ | ✅ |
| 29 | Logical Columns (direct) | ✅ | | | ✅ | | | ✅ | ✅ |
| 30 | Logical Columns (calc) | ✅ | | | ✅ | | | ✅ | ✅ |
| 31 | Logical Table Sources | ✅ | | | ✅ | | | | ✅ |
| 32 | Logical Joins (1:N) | ✅ | | | ✅ | | | ✅ | ✅ |
| 33 | Logical Joins (M:N) | ✅ | | | 🟡 | | | | 🟡 |
| 34 | Hierarchies | ✅ | | | ✅ | | | ✅ | ✅ |
| 35 | Calculated Measures | ✅ | | | ✅ | | | ✅ | ✅ |
| 36 | Session Variables | ✅ | | | | | ✅ | ✅ | ✅ |
| 37 | Init Blocks | ✅ | ✅ | | | | ✅ | ✅ | ✅ |
| 38 | Aggregation Rules | 🟡 | | | 🟡 | | | | 🟡 |
| 39 | Level-Based Measures | 🟡 | | | 🟡 | | | | 🟡 |
| 40 | Federated Joins | ❌ | ❌ | | | | | | ❌ |
| 41 | Subject Areas | ✅ | | | ✅ | | | | ✅ |
| 42 | Presentation Tables | ✅ | | | ✅ | | | | ✅ |
| 43 | Presentation Columns | ✅ | | | 🟡 | | | | 🟡 |
| 44 | Column Aliases | ✅ | | | 🟡 | | | | 🟡 |
| 45 | Column Sorting | ✅ | | | ✅ | | | | ✅ |
| 46 | App Roles | ✅ | | | | | ✅ | ✅ | ✅ |
| 47 | User→Role Assignments | ✅ | | | | | ✅ | ✅ | ✅ |
| 48 | Row-Level Filters | ✅ | | | | | ✅ | ✅ | ✅ |
| 49 | Object Permissions | ✅ | | | | | ✅ | ✅ | ✅ |
| 50 | Hierarchy-Based RLS | ❌ | | | | | ❌ | | ❌ |
| 51 | Multi-Valued Session Vars | ✅ | | | | | 🟡 | | 🟡 |
| 52 | Sensitivity Labels | ❌ | | | | | ❌ | | ❌ |
| 53 | Audit Trail | ❌ | | | | | ❌ | | ❌ |
| 54 | Visual Types (25 of ~36) | ✅ | | | | ✅ | | ✅ | 🟡 |
| 55 | Prompts → Slicers (8 types) | ✅ | | | | ✅ | | ✅ | ✅ |
| 56 | Conditional Formatting | ✅ | | | | ✅ | | ✅ | ✅ |
| 57 | Dashboard Actions | ✅ | | | | ✅ | | ✅ | ✅ |
| 58 | Themes/Palettes | ❌ | | | | ❌ | | | ❌ |
| 59 | Mobile Layouts | ❌ | | | | ❌ | | | ❌ |
| 60 | Tooltip Pages | ❌ | | | | ❌ | | | ❌ |
| 61 | Story Points/Bookmarks | 🟡 | | | | 🟡 | | | 🟡 |
| 62 | Auto-Refresh Config | ❌ | | | | ❌ | | | ❌ |

---

## 11. Prioritized Remediation Roadmap

### Priority 1 — Critical Gaps (blocks production migration)

| # | Gap | Owner | Effort | Description |
|---|-----|:-----:|:------:|-------------|
| 1 | Auto Calendar/Date table | Agent 04 | M | Auto-detect date columns → generate Calendar table with 8 columns (Date, Year, Quarter, Month, MonthName with sortByColumn, Day, DayOfWeek, DayName with sortByColumn), hierarchy (Year→Quarter→Month→Day), M query partition, and 3 time intelligence DAX measures (YTD, PY, YoY%). Port from T2P pattern. |
| 2 | TMDL self-healing (6 patterns) | Agent 04 | L | Port T2P's 6 auto-repair mechanisms: (1) duplicate table names → rename with suffix, (2) broken column refs → hide measure + MigrationNote annotation, (3) orphan measures → reassign to main table, (4) empty table names → remove, (5) circular relationships → Union-Find auto-deactivation, (6) M query errors → `try...otherwise` wrapping |
| 3 | Visual fallback cascade | Agent 05 | S | Port T2P's 3-tier degradation: `scatterChart→tableEx`, `combo→clusteredBarChart`, `boxAndWhisker→clusteredColumnChart`, `gauge→card`, `[unknown]→tableEx→card`. Always renders something. |
| 4 | Custom visual GUID registry | Agent 05 | M | Register 18+ AppSource custom visuals with GUIDs and data role mappings: Sankey (`ChicagoITSankey1.1.0`), Chord (`ChicagoITChord1.0.0`), Word Cloud (`WordCloud1633006498960`), Gantt (`GanttByMAQSoftware1.0.0`), Network Navigator, etc. |
| 5 | Expand visual types to 60+ | Agent 05 | M | Add: `hundredPercentStackedBarChart`, `hundredPercentStackedColumnChart`, `stackedAreaChart`, `hundredPercentStackedAreaChart`, `multiRowCard`, `shapeMap`, `sunburst`, `boxAndWhisker`, histogram binning, + 18 custom visuals from GUID registry |
| 6 | Bookmark generation | Agent 05 | M | Generate PBI bookmark JSON from OAC story points, saved filter states, and dashboard page selections |
| 7 | M:N bridge table auto-generation | Agent 04 | M | Detect M:N joins → generate bridge table DDL + TMDL relationship |
| 8 | Hierarchy-based dynamic RLS | Agent 06 | L | Parent-child hierarchy → recursive RLS DAX using PATH() / PATHCONTAINS() |

### Priority 2 — Important Gaps (quality/completeness)

| # | Gap | Owner | Effort | Description |
|---|-----|:-----:|:------:|-------------|
| 7 | DAX post-translation optimizer | Agent 04 | M | AST rewriter: IF→SWITCH, ISBLANK→COALESCE, nesting reduction, constant folding |
| 8 | Lineage tracking | Agent 01 | M | Generate lineage_map.json: OAC path → Fabric/PBI target for every object |
| 9 | Schema drift detection | Agent 07 | M | Periodic schema snapshot + comparison + alerting |
| 10 | Governance (PII, naming) | Agent 06 | M | PII column scanning, naming convention enforcement, endorsement labels |
| 11 | Theme migration | Agent 05 | S | Extract OAC color palette → PBI theme JSON |
| 12 | Shared semantic model merge | Agent 04 | L | Fingerprint-based table deduplication for multi-report shared model |
| 13 | Mobile layout generation | Agent 05 | M | OAC responsive → PBI phone layout |
| 14 | KPI → PBI Goals converter | Agent 05 | S | OAC KPIs → PBI Scorecards/Goals JSON |
| 15 | Tooltip pages | Agent 05 | S | OAC drill-down → PBI tooltip page |
| 16 | Purview sensitivity labels | Agent 06 | M | Purview REST API integration for label assignment |
| 17 | OAC Alerts → PBI data-driven alerts | Agent 05 | S | Alert conditions → PBI alert rules |
| 18 | Data quality profiling in ETL | Agent 03 | M | DQ notebook template: null %, distinct count, outlier detection |
| 19 | Incremental discovery (delta crawl) | Agent 01 | M | OAC modification timestamp-based delta |
| 20 | Environment parameterization | Agent 03 | S | Pipeline parameters for dev/test/prod connections |

### Priority 3 — Nice-to-Have (polish)

| # | Gap | Owner | Effort | Description |
|---|-----|:-----:|:------:|-------------|
| 21 | Dead letter queue | Agent 08 | S | DLQ Delta table for permanently failed tasks |
| 22 | SLA enforcement per agent | Agent 08 | S | Timeout per agent task with escalation |
| 23 | Approval gates between waves | Agent 08 | M | Human-in-the-loop approval step |
| 24 | Statistical sampling for large tables | Agent 07 | S | Configurable sampling (1/5/10%) |
| 25 | Display folder intelligence | Agent 04 | S | Group measures by RPD presentation table |
| 26 | Pagination for large reports | Agent 05 | S | Auto-split > 30 visuals |
| 27 | Auto-refresh config in PBIR | Agent 05 | S | Set automatic page refresh interval |
| 28 | Favorites/Tags extraction | Agent 01 | S | Extract OAC favorites → PBI endorsement |
| 29 | Oracle synonyms mapping | Agent 02 | S | Synonym → view alias |
| 30 | Fabric Shortcut generation | Agent 02 | M | For cross-workspace data references |

**Effort Key:** S = Small (1–3 days), M = Medium (3–7 days), L = Large (1–2 weeks)

---

## 12. Agent Action Items

### Agent 01 — Discovery
- [ ] Add incremental discovery (delta crawl) using OAC modification timestamps
- [ ] Resolve RPD circular references automatically (break cycles, log warnings)
- [ ] Add OAC version detection for API feature flags
- [ ] Extract OAC Favorites/Tags for PBI endorsement mapping
- [ ] Generate lineage_map.json (OAC path → Fabric/PBI target)
- [ ] Extract KPI/Scorecard objects as dedicated inventory type
- [ ] **Add portfolio-level assessment** — Port T2P's `WorkbookReadiness` class: effort formula `1.0 + expr_count × 0.2 + conn_count × 0.25`, 5 complexity axes (expression, filter, connection, security, semantic), wave planning by shared datasources + effort bands
- [ ] **Add paginated OAC API client** — Port T2P's `_paginated_get(url, root_key, item_key, page_size=100)` pattern with `totalAvailable` tracking for OAC catalog endpoints
- [ ] **Add safe XML parsing** — Port T2P's `safe_parse_xml()` with XXE protection for RPD XML extraction
- [ ] **Add datasource deduplication** — Port T2P's highest-richness-wins strategy: keep datasource with max `len(tables) + len(calculations)` when duplicates detected

### Agent 02 — Schema
- [ ] Generate Delta partitioning strategy from Oracle partition metadata
- [ ] Map Oracle synonyms to view aliases
- [ ] Add Fabric Shortcut generation for database link equivalents
- [ ] Add partition-aware parallel data copy
- [ ] Document materialized view workaround (Lakehouse view template)
- [ ] **Add 3-level type mapping** — Port T2P's `SPARK_TYPE_MAP` pattern with OAC-specific levels: (1) Physical Oracle→Delta (`NUMBER→DECIMAL(19,4)`, `VARCHAR2→STRING`, `DATE→TIMESTAMP`, `CLOB→STRING`), (2) Logical RPD semantic→Delta (`NUMERIC→DOUBLE`, `TEXT→STRING`), (3) Fallback ISO SQL→Delta
- [ ] **Add Fabric name sanitization** — Port T2P's `sanitize_table_name()`: strip brackets `[\[\]]`, replace non-alnum with `_`, collapse `_+`, strip leading digits, lowercase; add OAC-specific prefix stripping (`v_`, `tbl_`, `f_`, `d_` for view/table/fact/dimension)
- [ ] **Add Lakehouse 3-artifact generation** — Port T2P's `LakehouseGenerator`: `lakehouse_definition.json` (tables + metadata), `ddl/` folder with `CREATE TABLE IF NOT EXISTS`, `table_metadata.json` (summary)
- [ ] **Add calculated column classification** — Port T2P's `classify_calculations()`: separate row-level calc columns vs aggregates using `role == 'dimension'` or `not has_aggregation` heuristic

### Agent 03 — ETL
- [ ] Add Spark pivot/unpivot templates for unmapped dataflow steps
- [ ] Inject environment parameters (dev/test/prod) in pipeline JSON
- [ ] Add data quality profiling notebook template
- [ ] Generate parallel pipeline branches from job chain analysis
- [ ] Add post-deployment alert template generation
- [ ] **Add 3-stage pipeline orchestration** — Port T2P's `PipelineGenerator` pattern: Stage 1 = `RefreshDataflow` activities (per datasource, parallel ingestion), Stage 2 = `TridentNotebook` activity (PySpark ETL + calculated columns), Stage 3 = `TridentDatasetRefresh` activity (DirectLake model refresh); with dependency chaining and `{"timeout": "0.12:00:00", "retry": 2}` policy
- [ ] **Add 9 JDBC connector templates** — Port T2P's `_SPARK_READ_TEMPLATES`: Oracle (`jdbc:oracle:thin:@`), PostgreSQL, SQL Server, Snowflake, BigQuery, CSV, Excel, Custom SQL, Databricks; each with proper driver class and options
- [ ] **Add OAC expression→PySpark translator** — Port T2P's `tableau_formula_to_pyspark()` pattern: `IF/THEN/ELSE→F.when(cond,val).otherwise(val2)`, `ROUND→F.round()`, `LEFT→F.substring()`, `UPPER→F.upper()`, `CASE→F.when().when().otherwise()`
- [ ] **Add OAC expression→M query translator** — Port T2P's `tableau_formula_to_m()` pattern: `IF→if/then/else`, `ROUND→Number.Round()`, `LEFT→Text.Start()`, `UPPER→Text.Upper()`, `LEN→Text.Length()`
- [ ] **Add incremental merge engine** — Port T2P's `IncrementalMerger`: `USER_OWNED_FILES` set (staticResources, custom_measures), `USER_EDITABLE_KEYS` set (displayName, title, description); merge logic: added→add, removed→keep if user-owned, modified→preserve user JSON keys, unchanged→keep

### Agent 04 — Semantic Model
- [ ] **Implement Auto Calendar table** — Port T2P: detect date columns → generate Calendar with 8 columns (Date/Year/Quarter/Month/MonthName/Day/DayOfWeek/DayName), sortByColumn on MonthName→Month and DayName→DayOfWeek, hierarchy (Year→Quarter→Month→Day), M query partition, 3 TI measures (YTD, PY, YoY%)
- [ ] **Implement TMDL self-healing (6 patterns)** — Port T2P: (1) duplicate table names→rename, (2) broken refs→hide+annotation, (3) orphan measures→reassign, (4) empty names→remove, (5) circular rels→Union-Find deactivate, (6) M errors→try/otherwise
- [ ] **Auto-generate M:N bridge tables** from detected M:N RPD joins
- [ ] **Move DAXOptimizer to pre-deploy** — Port 5 rules from perf_auto_tuner to semantic agent: ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding
- [ ] **Add OAC function leak detector** — Regex scan for untranslated OAC functions in generated DAX: `NVL`, `NVL2`, `DECODE`, `SYSDATE`, `ROWNUM`, `SUBSTR`, `INSTR`, `TRUNC`, `VALUEOF(NQ_SESSION.*)`, `EVALUATE_PREDICATE`, etc.
- [ ] **Add DAX→M calculated column conversion** — Port T2P's 15+ patterns: IF→each if/then, UPPER→Text.Upper, LOWER→Text.Lower, YEAR→Date.Year, MONTH→Date.Month, LEN→Text.Length, DATEDIFF→Duration.Days, TRIM→Text.Trim, LEFT→Text.Start, RIGHT→Text.End (performance optimization)
- [ ] **Add database.tmdl generation** — Emit compatibility level 1600+ and data model options
- [ ] **Add multi-culture TMDL** — Generate `cultures/*.tmdl` files for 19 languages (en-US, fr-FR, de-DE, ja-JP, etc.)
- [ ] **Add Copilot-friendly annotations** — Emit `@Copilot_TableDescription` annotations with column count and measure count per table
- [ ] Add calculation group templates (currency, time)
- [ ] Implement display folder strategy (group by RPD presentation table/subject area)
- [ ] Add shared semantic model merge engine (port T2P's SHA256 table fingerprint + Jaccard dedup)
- [ ] Add thin report generator with `byPath` semantic model reference
- [ ] Add relationship cycle-breaking (port T2P Union-Find algorithm)

### Agent 05 — Report
- [ ] **Expand visual types from 24 to 60+** — Add: `hundredPercentStackedBarChart`, `hundredPercentStackedColumnChart`, `stackedAreaChart`, `hundredPercentStackedAreaChart`, `multiRowCard`, `shapeMap`, `sunburst`, `boxAndWhisker`, histogram binning, `lineStackedColumnComboChart`, + 18 custom visuals
- [ ] **Add custom visual GUID registry** — Register 18+ AppSource visuals with data role mappings: Sankey (`ChicagoITSankey1.1.0` — Source/Destination/Weight), Chord (`ChicagoITChord1.0.0` — From/To/Values), Word Cloud (`WordCloud1633006498960` — Category/Values), Gantt (`GanttByMAQSoftware1.0.0` — Task/Start/Duration), Network Navigator, etc.
- [ ] **Add visual fallback cascade** — Port T2P's 3-tier: `scatterChart→tableEx`, `combo→clusteredBarChart`, `boxAndWhisker→clusteredColumnChart`, `gauge→card`, `[unknown]→tableEx→card`
- [ ] **Add bookmark generation** — Generate PBI bookmark JSON from OAC story points and saved filter states
- [ ] **Wire drill-through** — Connect actions.json metadata to visual JSON for actual drill-through page navigation
- [ ] **Wire What-If parameters** — Connect orphaned ParameterConfig into generation pipeline
- [ ] **Add cascading slicer DAX** — Auto-generate cross-filter DAX expressions for cascading slicers
- [ ] **Add approximation map** — For each unsupported visual type, document nearest PBI equivalent and migration notes (port T2P's APPROXIMATION_MAP pattern)
- [ ] **Add visual z-order/overlap detection** — Order visuals by z-index and detect overlapping positions
- [ ] Implement OAC theme → PBI theme JSON converter
- [ ] Generate phone/tablet mobile layouts
- [ ] Generate tooltip pages from OAC drill-down configs
- [ ] Add auto-pagination for >30 visual reports
- [ ] Add OAC Agent/Alert → PBI data-driven alert migration
- [ ] Add KPI/Scorecard → PBI Goals generator
- [ ] Add auto-refresh page configuration

### Agent 06 — Security
- [ ] **Implement hierarchy-based dynamic RLS** (PATH/PATHCONTAINS pattern)
- [ ] Add Purview sensitivity label mapping via REST API
- [ ] Add Microsoft Graph API batch AAD group creation
- [ ] Document cell-level security limitation + workaround
- [ ] **Add governance engine** — Port T2P's `GovernanceEngine` with `DEFAULT_GOVERNANCE_CONFIG`: `mode: "warn"|"enforce"`, naming rules (`measure_prefix: "m_"`, `column_style: "snake_case"`, `table_style: "PascalCase"`, `max_name_length: 128`), PII detection toggle, sensitivity mapping dict, audit trail
- [ ] **Add PII detector (15 regex patterns)** — Port T2P's `_PII_PATTERNS`: email (`\bemail\b`), SSN (`\bssn|social.?security\b`), phone (`\bphone|mobile\b`), personal name (`\b(?:first|last|full).?name\b`), credit card (`\bcredit.?card|pan\b`); add OAC-specific: Oracle schema names, VALUEOF session vars, ROWNUM references
- [ ] **Add credential redaction (10 patterns)** — Port T2P's `_CREDENTIAL_PATTERNS`: redact `password=*`, `Bearer *`, `client_secret=*`, connection strings, API keys in all generated artifacts and logs
- [ ] **Add safe RPD ZIP extraction** — Port T2P's ZIP slip defense: `safe_zip_extract_member()` with boundary check, reject `..` in paths, validate `os.path.isabs()`, log warnings for skipped entries
- [ ] **Add sensitivity label auto-mapping** — Port T2P's `sensitivity_mapping` config: map OAC roles to Purview labels (`Administrator→Highly Confidential`, `Viewer→General`, custom role→label mapping)

### Agent 07 — Validation
- [ ] Add schema drift detection (periodic snapshot + comparison)
- [ ] Add statistical sampling strategy for >100M row tables
- [ ] Add continuous regression testing (scheduled re-validation)
- [ ] Add test data masking for non-prod environments
- [ ] **Add TMDL structural validation** — Port T2P's checks: required files (model.tmdl), required dirs, required keys ($schema, name), JSON schema validation
- [ ] **Add DAX leak detector** — Port T2P's regex-based OAC function leak detection: scan generated DAX for untranslated `NVL`, `DECODE`, `SYSDATE`, `VALUEOF(NQ_SESSION.*)`, `SUBSTR`, `INSTR`, `(+)` outer join, `FROM DUAL`, etc.
- [ ] **Add pre-migration readiness assessment** — Port T2P's 8-point check: connectors, chart types, functions, expressions, parameters, data blending, dashboard features, security

### Agent 08 — Orchestrator
- [ ] Add dead letter queue (DLQ) Delta table for permanently failed tasks
- [ ] Add SLA timeout enforcement per agent task
- [ ] Add human-in-the-loop approval gates between waves
- [ ] Add cost tracking (RU/compute metering from Fabric API)
- [ ] **Add telemetry collector (v2 schema)** — Port T2P's `TelemetryCollector`: session_id, timestamp, duration_seconds, platform, stats dict (`tables_extracted`, `expressions_translated`, `analyses_migrated`, `failed_analyses`), errors list (`category`, `message`, `ts`), events list (`type`, `ts`, `status`, per-object); emit JSONL locally
- [ ] **Add SLA tracker** — Port T2P's `SLATracker` with `SLAResult` dataclass: `max_analysis_migration_seconds: 120`, `min_expression_fidelity: 85.0`, `require_data_reconciliation: True`, `require_security_validation: True`, `alert_on_breach: True`; compliant property checks time + fidelity + validation
- [ ] **Add 3-backend monitoring exporter** — Port T2P's `MigrationMonitor`: (1) `_JsonBackend` (JSONL local log, always available), (2) `_AzureMonitorBackend` (REST to Application Insights), (3) `_PrometheusBackend` (push to push gateway); auto-select based on available dependencies
- [ ] **Add recovery report tracker** — Port T2P's `RecoveryReport.record(category, repair_type, description, action, severity, follow_up)`: categories = expression|visual|m_query|relationship, severity = info|warning|error; tracks all self-healing actions for audit trail
- [ ] **Add 4-tab telemetry dashboard** — Port T2P's `TelemetryDashboard`: Tab 1 = Portfolio Overview (GREEN/YELLOW/RED counts, total effort), Tab 2 = Per-Analysis Results (status, fidelity, duration table), Tab 3 = Error Trends (histogram by category, bottleneck analysis), Tab 4 = Event Timeline (drill-down per expression/visual/connection)

---

*Generated 2026-03-26 · Based on v4.0.0 codebase analysis (2,618 tests, 110+ Python modules, 8 agents)*
