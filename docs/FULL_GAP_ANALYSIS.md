# Full OAC Object Gap Analysis — All Agents

**Date:** 2026-03-31 · v4.3.0 (Phase 49 complete)  
**Scope:** Every OAC object type, every agent's responsibility, migration target, implementation status, and gaps  
**Audience:** All 8 agents + Orchestrator  

---

## Executive Summary

| Metric | Value |
|--------|-------|
| OAC Object Categories | **12** (Catalog, RPD Physical, RPD Logical, RPD Presentation, Security, Data Flows, Scheduling, Prompts/Alerts, Themes, Mobile, Custom Plugins, Notifications) |
| Total OAC Object Types Identified | **62** |
| Fully Automated | **52** (84%) |
| Partially Automated (review needed) | **6** (10%) |
| Not Implemented / Manual Only | **4** (6%) |
| Agents Involved | All 8 (Discovery → Schema → ETL → Semantic → Report → Security → Validation → Orchestrator) |
| Tests Passing | 2,991 across 103 test files · 145 Python source modules |
| DAX Expression Rules | 380+ (across all connectors) |
| Visual Type Mappings | 80+ OAC → PBI (including 30+ AppSource custom visuals) |

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
| 9 | Published Data Sets | ✅ | Semantic Agent (04) shared model | ✅ | Shared model merge via `shared_model_merge.py` (Phase 48) |
| 10 | **KPIs / Scorecards** | 🟡 | PBI Goals / Scorecard | 🟡 | Discovered as analysis sub-objects; no dedicated KPI→Goals converter |
| 11 | **Stories (Narration)** | 🟡 | PBI bookmarks + textbox | 🟡 | Story points partially mapped; narrative content loses interactivity |
| 12 | **Favorites / Tags** | ❌ | PBI favorites / endorsement | ❌ | Not extracted from OAC; no PBI favorites API integration |
| 13 | **Scheduler Jobs** | ✅ | ETL Agent (03) triggers | ✅ | — |
| 14 | **Custom Plugins / Extensions** | 🟡 | Custom PBI visuals | 🟡 | 3-tier visual fallback cascade (`visual_fallback.py`); 18+ AppSource GUIDs registered |

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
| 25 | **Oracle Synonyms** | ✅ | CREATE VIEW alias | ✅ | **Resolved in Phase 49**: `ddl_generator.py` — `generate_synonym_view()` + `generate_synonym_script()` |
| 26 | **Database Links** | ✅ | Fabric Shortcuts | ✅ | **Resolved in Phase 49**: `ddl_generator.py` — `generate_fabric_shortcut()` + `generate_shortcut_script()` |
| 27 | **Oracle Packages (DDL)** | 🟡 | PySpark notebooks | 🟡 | PL/SQL body translated; package-level state/context lost |

### 1.3 RPD Business/Logical Layer

| # | OAC Object Type | Discovered | Fabric/PBI Target | Status | Gap |
|---|----------------|:----------:|-------------------|:------:|-----|
| 28 | **Logical Tables** | ✅ | TMDL tables | ✅ | — |
| 29 | **Logical Columns (direct mapped)** | ✅ | TMDL columns | ✅ | — |
| 3 | Logical Columns (calculated/derived) | ✅ | TMDL measures / calc columns | ✅ | 120+ OAC→DAX rules; LLM fallback for complex |
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
| D-GAP-06 | ~~**Published Data Sets** — no shared model concept~~ | ✅ | 01→04 | **Resolved in Phase 48**: `shared_model_merge.py` provides fingerprint + Jaccard deduplication |

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
| 8 | Oracle synonyms | → CREATE VIEW alias | Fabric views | ✅ | **Resolved in Phase 49**: `generate_synonym_view()` in `ddl_generator.py` |
| 9 | Oracle database links | → Fabric Shortcuts | Fabric Shortcuts | ✅ | **Resolved in Phase 49**: `generate_fabric_shortcut()` in `ddl_generator.py` |
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
| S-GAP-04 | ~~**Synonyms** not mapped~~ | ✅ | **Resolved in Phase 49**: `generate_synonym_view()` generates CREATE VIEW from synonym |
| S-GAP-05 | ~~**Database links** → Fabric Shortcuts~~ | ✅ | **Resolved in Phase 49**: `generate_fabric_shortcut()` generates REST API payload |
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
| E-GAP-07 | ~~**Data quality / error routing** not implemented~~ | ✅ | **Resolved in Phase 49**: `dq_profiler.py` — DQ profiling notebook generator |

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
| 6 | Logical Join (M:N) | — | ✅ | Bridge table auto-generated via `bridge_table_generator.py` (Phase 49) |
| 7 | Hierarchy | Hierarchy with Levels | ✅ | — |
| 8 | Presentation Table | Perspective / Display Folder | ✅ | — |
| 9 | Subject Area | Perspective | ✅ | — |
| 10 | Presentation Column | Column visibility + display folders | ✅ | Intelligent grouping from RPD subject areas via `_build_display_folder_map()` |

### 4.2 DAX Expression Translation (120+ rules)

| Category | Rules | Coverage | Status |
|----------|:-----:|:--------:|:------:|
| Aggregations (SUM, COUNT, AVG, MIN, MAX, STDDEV, MEDIAN, etc.) | 21 | 100% | ✅ |
| Time Intelligence (AGO, TODATE, PERIODROLLING, PARALLELPERIOD, etc.) | 21 | 95% | ✅ |
| String Functions (UPPER, LOWER, MID, REPLACE, LEFT, RIGHT, etc.) | 18 | 95% | ✅ |
| Math Functions (ABS, ROUND, POWER, SQRT, LOG, MOD, etc.) | 16 | 100% | ✅ |
| Date Functions (EXTRACT, ADD_MONTHS, TO_DATE, LAST_DAY, etc.) | 20 | 95% | ✅ |
| Logical Functions (CASE, IIF, COALESCE, DECODE, NVL2, NULLIF, etc.) | 12 | 100% | ✅ |
| Filter/Table Functions (FILTER, ALL, RELATED, etc.) | 5 | 85% | 🟡 |
| Statistical (PERCENTILE, RANK, NTILE, TOPN) | 4 | 80% | 🟡 |
| Level-Based (AGGREGATE_AT_LEVEL, SHARE) | 2 | 60% | 🟡 |
| Information (VALUEOF, DESCRIPTOR_IDOF, INDEXCOL) | 3 | 70% | 🟡 |
| **Total OAC-native** | **122** | **~93%** | ✅ |

### 4.3 Missing DAX Capabilities vs. T2P

| Feature | T2P Status | OAC→Fabric Status | Priority |
|---------|:----------:|:-----------------:|:--------:|
| 180+ DAX rules (all sources combined) | ✅ | 260+ (across 5 connectors) | ✅ Parity achieved |
| DAX Optimizer (AST rewriter: IF→SWITCH, COALESCE) | ✅ | ✅ pre-deployment in `dax_optimizer.py` (Phase 47) | ✅ Parity |
| Auto Calendar/Date table generation | ✅ | ✅ `calendar_generator.py` (Phase 47) | ✅ Parity |
| TMDL Self-Healing (duplicate tables, broken refs) | ✅ | ✅ 6 patterns in `tmdl_self_healing.py` (Phase 47) | ✅ Parity |
| Calculation Groups | ✅ (partial) | ❌ | 🟡 P2 |
| Composite model / aggregation tables | ✅ | 🟡 Phase 46 `CompositeModelAdvisor` recommends but doesn't generate | 🟡 P2 |
| Shared semantic model (merge engine) | ✅ | ✅ `shared_model_merge.py` (Phase 48) | ✅ Parity |
| Incremental TMDL update (delta) | ✅ | ❌ (full regeneration only) | 🟢 P3 |
| Display folder intelligence | ✅ (by data source) | ✅ `_build_display_folder_map()` in `tmdl_generator.py` (Phase 49) | ✅ Parity |

### 4.4 Semantic Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| SM-GAP-01 | ~~**M:N relationships** — bridge table not auto-generated~~ | ✅ | **Resolved in Phase 49**: `bridge_table_generator.py` generates bridge table DDL + TMDL relationships + M expression |
| SM-GAP-02 | ~~**No Auto Calendar table**~~ | ✅ | **Resolved in Phase 47**: `calendar_generator.py` auto-detects date columns, generates Calendar table with 8 columns, hierarchy, 3 TI measures |
| SM-GAP-03 | ~~**No TMDL self-healing**~~ | ✅ | **Resolved in Phase 47**: `tmdl_self_healing.py` provides 6 auto-repair patterns (duplicates, broken refs, orphans, empty names, circular rels, M errors) |
| SM-GAP-04 | ~~**No DAX post-translation optimizer**~~ | ✅ | **Resolved in Phase 47**: `dax_optimizer.py` provides 5 pre-deployment rules (ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding) |
| SM-GAP-05 | **Calculation groups** not generated | 🟡 | Add calculation group templates for common patterns (currency, time) |
| SM-GAP-06 | ~~**Display folder** strategy is flat~~ | ✅ | **Resolved in Phase 49**: `_build_display_folder_map()` in `tmdl_generator.py` groups by RPD subject area |
| SM-GAP-07 | ~~**No shared semantic model** for multiple reports~~ | ✅ | **Resolved in Phase 48**: `shared_model_merge.py` provides fingerprint + Jaccard deduplication + thin report references |
| SM-GAP-08 | ~~**No lineage tracking**~~ (OAC source → TMDL target) | ✅ | **Resolved in Phase 48**: `lineage_map.py` provides full JSON lineage graph with BFS impact analysis |

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
| 26 | 100% Stacked Bar | hundredPercentStackedBarChart | ✅ | Phase 47 |
| 27 | 100% Stacked Column | hundredPercentStackedColumnChart | ✅ | Phase 47 |
| 28 | Stacked Area | stackedAreaChart | ✅ | Phase 47 |
| 29 | 100% Stacked Area | hundredPercentStackedAreaChart | ✅ | Phase 47 |
| 30 | Multi-Row Card | multiRowCard | ✅ | Phase 47 |
| 31 | Shape Map | shapeMap | ✅ | Phase 47 |
| 32 | Sunburst | sunburst (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 33 | Box & Whisker | boxAndWhisker (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 34 | Histogram | clusteredColumnChart + binning | ✅ | Phase 47 |
| 35 | Decomposition Tree | decompositionTreeMap | ✅ | Phase 47 |
| 36 | Key Influencers | keyDriversVisual | ✅ | Phase 47 |
| 37 | Sankey Diagram | ChicagoITSankey1.1.0 (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 38 | Chord Diagram | ChicagoITChord1.0.0 (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 39 | Word Cloud | WordCloud1633006498960 (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 40 | Gantt Chart | GanttByMAQSoftware1.0.0 (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 41 | Network Navigator | networkNavigator (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 42 | Radar / Spider | radarChart (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 43 | Timeline | ChicagoITTimeline1.0.0 (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 44 | Bullet Chart | BulletByMAQSoftware1.0.0 (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| 45 | Tornado Chart | tornadoChart (AppSource) | ✅ | Phase 47 — custom visual GUID registered |
| — | **REMAINING GAPS** | | | |
| 46 | Parallel Coordinates | — | ❌ | No PBI equivalent |
| 47 | Calendar Heatmap | — | ❌ | Custom visual needed |
| 48 | Sparklines (inline) | Sparklines in table/matrix | 🟡 | PBI supports natively; not mapped yet |

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
| 9 | Cascading Prompt | Multiple slicers + relationship filtering | ✅ | **Resolved in Phase 49**: `generate_cascading_filter_dax()` + `build_cascading_chain()` in `prompt_converter.py` |
| 10 | **Variable prompt** (bind to session var) | PBI What-if parameter | ✅ | **Resolved in Phase 49**: `generate_whatif_slicer()` + `generate_whatif_tmdl()` in `pbir_generator.py` |

### 5.3 Interactivity & Layout

| Feature | OAC | PBI Target | Status | Gap |
|---------|-----|-----------|:------:|-----|
| Dashboard actions (navigate) | ✅ | Drillthrough pages | ✅ | — |
| Dashboard actions (filter) | ✅ | Cross-filter / highlight | ✅ | — |
| Master-detail | ✅ | Drillthrough + bookmarks | ✅ | — |
| Conditional formatting (color) | ✅ | Field value rules | ✅ | — |
| Conditional formatting (data bars) | ✅ | Data bars in matrix | ✅ | — |
| Conditional formatting (icons/stoplight) | ✅ | Icons formatting | ✅ | — |
| Theme / custom palette | ✅ | PBI CY24SU11 theme JSON | ✅ | **Resolved in Phase 49**: `theme_converter.py` extracts OAC palette → PBI theme |
| Mobile / responsive layout | ✅ | Phone layout | ✅ | **Resolved in Phase 49**: `layout_engine.py` — `generate_mobile_layout()` (360×640) |
| Bookmarks (story points) | ✅ | PBI bookmarks | ✅ | **Resolved in Phase 47**: `bookmark_generator.py` generates bookmarks from OAC story points and saved states |
| Tooltip pages | ✅ (drill-down) | Tooltip pages | ✅ | **Resolved in Phase 49**: `pbir_generator.py` — `generate_tooltip_page()` + `wire_tooltip_to_visual()` |
| Pagination (50+ visuals) | ✅ | Multi-page reports | ✅ | **Resolved in Phase 49**: `layout_engine.py` — `paginate()` with y-cursor reflow |
| Dynamic zone visibility | ✅ | Selection pane + bookmarks | 🟡 | Approximated |
| Real-time / auto-refresh | ✅ | Automatic page refresh | ❌ | Not configured in PBIR |

### 5.4 Report Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| R-GAP-01 | ~~**Only 25 visual types**~~ | ✅ | **Resolved in Phase 47**: 47 visual types mapped (25 built-in + 22 via 18+ AppSource custom visual GUIDs) |
| R-GAP-02 | ~~**No theme migration**~~ | ✅ | **Resolved in Phase 49**: `theme_converter.py` extracts OAC color palette → PBI CY24SU11 theme JSON |
| R-GAP-03 | ~~**No mobile layout**~~ | ✅ | **Resolved in Phase 49**: `layout_engine.py` — `generate_mobile_layout()` (360×640, single-column stacked) |
| R-GAP-04 | ~~**No tooltip pages**~~ | ✅ | **Resolved in Phase 49**: `pbir_generator.py` — `generate_tooltip_page()` + `wire_tooltip_to_visual()` |
| R-GAP-05 | ~~**No pagination** for large reports~~ | ✅ | **Resolved in Phase 49**: `layout_engine.py` — `paginate()` with y-cursor reflow for 50+ visual reports |
| R-GAP-06 | ~~**Custom plugins** unsupported with no fallback~~ | ✅ | **Resolved in Phase 47**: 3-tier visual fallback cascade in `visual_fallback.py` (complex→simpler→table→card) |
| R-GAP-07 | **Deeply nested containers** (4+ levels) misalign | 🟡 | Flatten nested containers before layout calculation |
| R-GAP-08 | **No real-time / auto-refresh** config | 🟢 | Add automatic page refresh setting in PBIR |
| R-GAP-09 | ~~**Variable prompts** not mapped~~ | ✅ | **Resolved in Phase 49**: `pbir_generator.py` — `generate_whatif_slicer()` + `generate_whatif_tmdl()` maps to PBI What-if parameters |

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
| 8 | **Row filter with hierarchy-based access** | — | ✅ | **Resolved in Phase 49**: `rls_converter.py` — `generate_hierarchy_rls()` + `generate_hierarchy_rls_dax()` using PATH()/PATHCONTAINS() |
| 9 | **Multi-valued session variables** | Lookup table (1:many) | 🟡 | Complex OR/AND combos need manual tuning |
| 10 | **Data-level permissions (cell-level)** | — | ❌ | Not expressible in PBI RLS (row-level only) |
| 11 | **Dynamic dashboard permissions** | — | ❌ | Not expressible in PBI workspace roles alone |
| 12 | **Sensitivity labels** | Purview labels | ✅ | **Resolved in Phase 47**: `governance_engine.py` maps OAC roles to Purview sensitivity labels |
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
| SEC-GAP-01 | ~~**Hierarchy-based RLS** not auto-generated~~ | ✅ | **Resolved in Phase 49**: `rls_converter.py` — `generate_hierarchy_rls()` + `generate_hierarchy_rls_dax()` with PATH()/PATHCONTAINS() |
| SEC-GAP-02 | ~~**Sensitivity labels** not migrated to Purview~~ | ✅ | **Resolved in Phase 47**: `governance_engine.py` maps roles to Purview labels |
| SEC-GAP-03 | **No AAD group provisioning** automation | 🟡 | Add Microsoft Graph API batch group creation |
| SEC-GAP-04 | **Cell-level security** not expressible in PBI | 🔴 | Document as known limitation; suggest OLS + row filter combo |
| SEC-GAP-05 | **Audit trail** not migrated | 🟠 | Export OAC audit logs to archive; Fabric generates its own audit |
| SEC-GAP-06 | ~~**Governance framework** (naming, PII detection) missing~~ | ✅ | **Resolved in Phase 47**: `governance_engine.py` provides naming rules, 15 PII regex patterns, 10 credential redaction patterns, sensitivity label mapping, audit trail |

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
| **Schema drift detection** | ✅ | — | **Resolved in Phase 49**: `schema_drift.py` — `SchemaSnapshot`, `DriftReport`, critical drift flagging |
| **Continuous regression** | — | ❌ | No scheduled re-validation after go-live (planned Phase 50) |
| **Statistical sampling** | — | ❌ | No sampling strategy for very large tables |
| **Test data masking** | — | ❌ | No masking for lower environments |

### 7.2 Validation Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| V-GAP-01 | ~~**No schema drift detection** post-migration~~ | ✅ | **Resolved in Phase 49**: `schema_drift.py` provides periodic snapshot + comparison + critical drift flagging |
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
| **Dead letter queue** | ✅ | **Resolved in Phase 49**: `DeadLetterQueue` in `dag_engine.py` with entry tracking + JSON export |
| **SLA enforcement** per agent | ✅ | **Resolved in Phase 47**: `sla_tracker.py` provides per-agent timeout + compliance evaluation |
| **Manual approval gates** between waves | ✅ | **Resolved in Phase 49**: `ApprovalGate` + `GatedWavePlan` in `wave_planner.py` — approve/reject per wave |
| **Cost tracking** per wave/agent | ❌ | No RU/compute cost metering |
| **GraphQL API** | ❌ | Planned v5.0 (Phase 48) |
| **Dry-run simulator** | ❌ | Planned Phase 49 |
| **Self-service portal** | ❌ | Planned Phase 51 |

### 8.2 Orchestrator Gaps

| Gap ID | Description | Severity | Recommendation |
|--------|-------------|:--------:|----------------|
| O-GAP-01 | ~~**No dead letter queue** for permanently failed tasks~~ | ✅ | **Resolved in Phase 49**: `DeadLetterQueue` in `dag_engine.py` with entry tracking, JSON export, summary |
| O-GAP-02 | ~~**No SLA enforcement** per agent~~ | ✅ | **Resolved in Phase 47**: `sla_tracker.py` provides per-agent timeout with compliance evaluation and reporting |
| O-GAP-03 | ~~**No approval gates** between waves~~ | ✅ | **Resolved in Phase 49**: `ApprovalGate` + `GatedWavePlan` in `wave_planner.py` — approve/reject per wave |
| O-GAP-04 | **No cost tracking** | 🟢 | Add RU/compute metering from Fabric API |

---

## 9. Cross-Cutting Gaps — Deep Power BI Component Comparison with TableauToPowerBI

### 9.1 TMDL Feature-by-Feature Comparison

| TMDL Feature | T2P | OAC→Fabric | Gap | Severity |
|---|:---:|:---:|---|:---:|
| `model.tmdl` | ✅ multi-culture | ✅ en-US only | OAC hardcodes `en-US` | 🟡 |
| `database.tmdl` (compat level 1600) | ✅ | ✅ `compatibilityLevel: 1600` in `tmdl_generator.py` (Phase 47) | Parity | ✅ |
| `tables/*.tmdl` (columns, measures, partitions) | ✅ | ✅ | Parity on basic structure | ✅ |
| `relationships.tmdl` + Union-Find cycle-breaking | ✅ + auto-deactivate | ✅ cycle-breaking via Union-Find in `tmdl_self_healing.py` (Phase 47) | Parity | ✅ |
| `roles.tmdl` (RLS / OLS) | ✅ | ✅ | Parity | ✅ |
| `perspectives.tmdl` | ✅ | ✅ | Parity | ✅ |
| `expressions.tmdl` (M data sources) | ✅ 42 connectors | ✅ Fabric-native | Different scope — both complete for their domain | ✅ |
| `cultures/*.tmdl` (19 languages) | ✅ | ✅ 19 locales via `generate_culture_tmdl()` + `generate_all_cultures()` (Phase 49) | Parity | ✅ |
| `lineageTag` UUIDs | ✅ | ✅ | Parity | ✅ |
| `sortByColumn` | ✅ | ✅ | Parity | ✅ |
| `displayFolder` (intelligent grouping) | ✅ | ✅ `_build_display_folder_map()` from RPD subject areas (Phase 49) | Parity | ✅ |
| `formatString` | ✅ | ✅ | Parity | ✅ |
| `isHidden` | ✅ | ✅ | Parity | ✅ |
| `Copilot_TableDescription` annotations | ✅ | ✅ `annotate_for_copilot()` in `tmdl_generator.py` (Phase 49) | Parity | ✅ |
| Calendar/Date table auto-generation | ✅ 8 cols + hierarchy + 3 TI measures | ✅ `calendar_generator.py` (Phase 47) | Parity | ✅ |
| TMDL Self-Healing (17 patterns) | ✅ duplicates, broken refs, orphans, empties, circular rels, M try/otherwise + 11 more | ✅ 17 patterns in `tmdl_self_healing.py` (Phase 47+48) | **Exceeds T2P** | ✅ |
| DAX Optimizer (5 pre-deploy rules) | ✅ ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding | ✅ 5 rules in `dax_optimizer.py` (Phase 47) | Parity | ✅ |
| DAX→M calculated column conversion (15+ patterns) | ✅ | ❌ | No DAX→M optimization | 🟡 |
| 3-phase relationship detection | ✅ explicit + inferred (DAX scan) + cardinality heuristic | 🟡 explicit only | No DAX-based relationship inference | 🟡 |
| Calculated tables | ✅ | ❌ | Not supported | 🟡 |
| Aggregation table auto-generation | ✅ auto-gen Import-mode agg | 🟡 advisor only | Advisor recommends but doesn't generate | 🟡 |
| Shared model merge (fingerprint + Jaccard dedup) | ✅ | ✅ `shared_model_merge.py` (Phase 48) | Parity | ✅ |
| Thin report byPath reference | ✅ | ✅ `shared_model_merge.py` (Phase 48) | Parity | ✅ |

### 9.2 PBIR Feature-by-Feature Comparison

| PBIR Feature | T2P | OAC→Fabric | Gap | Severity |
|---|:---:|:---:|---|:---:|
| Visual type count | **80+** (30+ custom GUIDs) | **80+** (including 30+ AppSource GUIDs) | Parity | ✅ |
| Custom visual GUID registry | ✅ Sankey, Chord, WordCloud, Gantt, Network, + 13 | ✅ 18+ registered in `visual_mapper.py` (Phase 47) | Parity | ✅ |
| Visual fallback cascade | ✅ 3-tier: complex→simple→table→card | ✅ 3-tier in `visual_fallback.py` (Phase 47) | Parity | ✅ |
| Bookmarks (saved filter states) | ✅ | ✅ `bookmark_generator.py` (Phase 47) | Parity | ✅ |
| Drill-through wiring | ✅ wired into visual JSON | ✅ `wire_drillthrough()` + `generate_drillthrough_page()` in `pbir_generator.py` (Phase 49) | Parity | ✅ |
| What-If parameters | ✅ wired | ✅ `generate_whatif_slicer()` + `generate_whatif_tmdl()` in `pbir_generator.py` (Phase 49) | Parity | ✅ |
| Cascading slicers (cross-filter DAX) | ✅ auto DAX | ✅ `generate_cascading_filter_dax()` + `build_cascading_chain()` in `prompt_converter.py` (Phase 49) | Parity | ✅ |
| Visual z-order / overlap detection | ✅ | ✅ `assign_z_order()` + `detect_overlaps()` in `layout_engine.py` (Phase 49) | Parity | ✅ |
| Approximation map (unsupported→nearest + migration notes) | ✅ | ❌ | Not implemented | 🟡 |
| DAX leak detector (source function regex + auto-fix) | ✅ Tableau leaks | ✅ 22 OAC patterns + auto-fix in `leak_detector.py` (Phase 47) | Parity | ✅ |
| Pre-migration 8-point assessment | ✅ | ✅ 8-point readiness check in `tmdl_validator.py` (Phase 47) | Parity | ✅ |

### 9.3 Visual Types — Previously Missing, Now Resolved (Phase 47)

| Visual | T2P PBI Type | OAC Status | AppSource? |
|--------|-------------|:---:|:---:|
| 100% Stacked Bar | `hundredPercentStackedBarChart` | ✅ | Built-in |
| 100% Stacked Column | `hundredPercentStackedColumnChart` | ✅ | Built-in |
| Stacked Area | `stackedAreaChart` | ✅ | Built-in |
| 100% Stacked Area | `hundredPercentStackedAreaChart` | ✅ | Built-in |
| Multi-Row Card | `multiRowCard` | ✅ | Built-in |
| Shape Map | `shapeMap` | ✅ | Built-in |
| Sunburst | `sunburst` | ✅ | AppSource |
| Box & Whisker | `boxAndWhisker` | ✅ | AppSource |
| Histogram (binned column) | `clusteredColumnChart` + binning | ✅ | Built-in |
| Sankey Diagram | `ChicagoITSankey1.1.0` | ✅ | AppSource |
| Chord Diagram | `ChicagoITChord1.0.0` | ✅ | AppSource |
| Word Cloud | `WordCloud1633006498960` | ✅ | AppSource |
| Gantt Chart | `GanttByMAQSoftware1.0.0` | ✅ | AppSource |
| Network Navigator | `networkNavigator` | ✅ | AppSource |
| + 8 more custom visuals | Radar, Timeline, Bullet, Tornado, etc. | ✅ | AppSource |

**Remaining unmatched**: Parallel Coordinates (❌ no PBI equivalent), Calendar Heatmap (❌ custom visual needed), Sparklines (🟡 PBI native but not yet mapped).

### 9.4 T2P Self-Healing Patterns — All Implemented (Phase 47)

| # | Pattern | T2P Implementation | OAC Status |
|---|---------|-------------------|:---:|
| 1 | Duplicate table names | Rename: `Product` → `Product_2` → `Product_3` | ✅ `tmdl_self_healing.py` |
| 2 | Broken column references | Hide measure + add `MigrationNote` annotation | ✅ `tmdl_self_healing.py` |
| 3 | Orphan measures | Reassign to main table (by column count) | ✅ `tmdl_self_healing.py` |
| 4 | Empty table names | Remove from model | ✅ `tmdl_self_healing.py` |
| 5 | Circular relationships | Deactivate lowest-priority rel (Union-Find) | ✅ `tmdl_self_healing.py` |
| 6 | M query errors | Wrap with `try...otherwise` error handling | ✅ `tmdl_self_healing.py` |

### 9.5 Calendar Table — Implemented (Phase 47)

Both T2P and OAC→Fabric now auto-detect date columns and generate:

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
| Hierarchy-based dynamic RLS | Parent-child hierarchy RLS DAX | 06 (Security) | ✅ Resolved — `rls_converter.py` (Phase 49) |
| Purview sensitivity label mapping | OAC classification → Purview labels | 06 (Security) | ✅ Resolved — `governance_engine.py` (Phase 47) |
| Data quality profiling in ETL | DQ checks embedded in pipeline | 03 (ETL) | 🟡 P2 |
| OAC function leak detector | Regex scan for untranslated NVL, DECODE, SYSDATE, VALUEOF, etc. | 04 (Semantic) | ✅ Resolved — `leak_detector.py` (Phase 47) |

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
| 14 | Custom Plugins | 🟡 | | | | 🟡 | | | 🟡 |
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
| 25 | Synonyms | ✅ | ✅ | | | | | | ✅ |
| 26 | Database Links | ✅ | ✅ | | | | | | ✅ |
| 27 | Oracle Packages | 🟡 | | 🟡 | | | | | 🟡 |
| 28 | Logical Tables | ✅ | | | ✅ | | | ✅ | ✅ |
| 29 | Logical Columns (direct) | ✅ | | | ✅ | | | ✅ | ✅ |
| 30 | Logical Columns (calc) | ✅ | | | ✅ | | | ✅ | ✅ |
| 31 | Logical Table Sources | ✅ | | | ✅ | | | | ✅ |
| 32 | Logical Joins (1:N) | ✅ | | | ✅ | | | ✅ | ✅ |
| 33 | Logical Joins (M:N) | ✅ | | | ✅ | | | | ✅ |
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
| 50 | Hierarchy-Based RLS | ✅ | | | | | ✅ | | ✅ |
| 51 | Multi-Valued Session Vars | ✅ | | | | | 🟡 | | 🟡 |
| 52 | Sensitivity Labels | ✅ | | | | | ✅ | | ✅ |
| 53 | Audit Trail | ❌ | | | | | ❌ | | ❌ |
| 54 | Visual Types (80+ of ~85) | ✅ | | | | ✅ | | ✅ | ✅ |
| 55 | Prompts → Slicers (10 types) | ✅ | | | | ✅ | | ✅ | ✅ |
| 56 | Conditional Formatting | ✅ | | | | ✅ | | ✅ | ✅ |
| 57 | Dashboard Actions | ✅ | | | | ✅ | | ✅ | ✅ |
| 58 | Themes/Palettes | ✅ | | | | ✅ | | | ✅ |
| 59 | Mobile Layouts | ✅ | | | | ✅ | | | ✅ |
| 60 | Tooltip Pages | ✅ | | | | ✅ | | | ✅ |
| 61 | Story Points/Bookmarks | ✅ | | | | ✅ | | | ✅ |
| 62 | Auto-Refresh Config | ❌ | | | | ❌ | | | ❌ |

---

## 11. Prioritized Remediation Roadmap

### Priority 1 — Critical Gaps (blocks production migration)

| # | Gap | Owner | Effort | Status | Description |
|---|-----|:-----:|:------:|:------:|-------------|
| 1 | Auto Calendar/Date table | Agent 04 | M | ✅ Phase 47 | `calendar_generator.py` — 8-column Calendar, hierarchy, 3 TI measures |
| 2 | TMDL Self-Healing (6→17 patterns) | Agent 04 | L | ✅ Phase 47+48 | `tmdl_self_healing.py` — 6 core patterns (Phase 47) + 11 new patterns (Phase 48: sort-by, format strings, duplicates, partition mode, expression brackets, BOM, whitespace, display folders, unreferenced hidden) |
| 3 | Visual fallback cascade | Agent 05 | S | ✅ Phase 47 | `visual_fallback.py` — 3-tier cascade: complex→simpler→table→card |
| 4 | Custom visual GUID registry | Agent 05 | M | ✅ Phase 47 | `visual_mapper.py` — 18+ AppSource visuals (Sankey, Chord, WordCloud, Gantt, Network, etc.) |
| 5 | Expand visual types to 80+ | Agent 05 | M | ✅ Phase 47+48 | `visual_mapper.py` — 80+ types mapped (was 24); 30+ custom visual GUIDs registered |
| 6 | Bookmark generation | Agent 05 | M | ✅ Phase 47 | `bookmark_generator.py` — PBI bookmarks from OAC story points |
| 7 | M:N bridge table auto-generation | Agent 04 | M | ✅ Phase 49 | `bridge_table_generator.py` — DDL + TMDL relationships + M expression |
| 8 | Hierarchy-based dynamic RLS | Agent 06 | L | ✅ Phase 49 | `rls_converter.py` — `generate_hierarchy_rls()` + `generate_hierarchy_rls_dax()` with PATH()/PATHCONTAINS() |

### Priority 2 — Important Gaps (quality/completeness)

| # | Gap | Owner | Effort | Status | Description |
|---|-----|:-----:|:------:|:------:|-------------|
| 9 | DAX post-translation optimizer | Agent 04 | M | ✅ Phase 47 | `dax_optimizer.py` — 5 rules (IF→SWITCH, ISBLANK→COALESCE, SUMX→SUM, CALCULATE collapse, constant folding) |
| 10 | Lineage tracking | Agent 01 | M | ✅ Phase 48 | `lineage_map.py` — JSON dependency graph with BFS impact analysis |
| 11 | Schema drift detection | Agent 07 | M | ✅ Phase 49 | `schema_drift.py` — `SchemaSnapshot`, `DriftReport`, critical drift flagging |
| 12 | Governance (PII, naming) | Agent 06 | M | ✅ Phase 47 | `governance_engine.py` — naming rules, 15 PII patterns, 10 credential patterns, sensitivity labels |
| 13 | Theme migration | Agent 05 | S | ✅ Phase 49 | `theme_converter.py` — OAC color palette → PBI CY24SU11 theme JSON |
| 14 | Shared semantic model merge | Agent 04 | L | ✅ Phase 48 | `shared_model_merge.py` — Fingerprint + Jaccard deduplication + thin report references |
| 15 | Mobile layout generation | Agent 05 | M | ✅ Phase 49 | `layout_engine.py` — `generate_mobile_layout()` (360×640, single-column) |
| 16 | KPI → PBI Goals converter | Agent 05 | S | ❌ | OAC KPIs → PBI Scorecards/Goals JSON |
| 17 | Tooltip pages | Agent 05 | S | ✅ Phase 49 | `pbir_generator.py` — `generate_tooltip_page()` + `wire_tooltip_to_visual()` |
| 18 | Purview sensitivity labels | Agent 06 | M | ✅ Phase 47 | `governance_engine.py` — OAC roles → Purview labels via config dict |
| 19 | OAC Alerts → PBI data-driven alerts | Agent 05 | S | ❌ | Alert conditions → PBI alert rules |
| 20 | Data quality profiling in ETL | Agent 03 | M | ✅ Phase 49 | `dq_profiler.py` — DQ profiling notebook generator |
| 21 | Incremental discovery (delta crawl) | Agent 01 | M | ❌ | OAC modification timestamp-based delta |
| 22 | Environment parameterization | Agent 03 | S | ❌ | Pipeline parameters for dev/test/prod connections |

### Priority 3 — Nice-to-Have (polish)

| # | Gap | Owner | Effort | Description |
|---|-----|:-----:|:------:|-------------|
| 21 | Dead letter queue | Agent 08 | S | ✅ Phase 49 | `DeadLetterQueue` in `dag_engine.py` with entry tracking + JSON export |
| 22 | SLA enforcement per agent | Agent 08 | S | ✅ Phase 47 | `sla_tracker.py` per-agent timeout + compliance |
| 23 | Approval gates between waves | Agent 08 | M | ✅ Phase 49 | `ApprovalGate` + `GatedWavePlan` in `wave_planner.py` |
| 24 | Statistical sampling for large tables | Agent 07 | S | Configurable sampling (1/5/10%) |
| 25 | Display folder intelligence | Agent 04 | S | ✅ Phase 49 | `_build_display_folder_map()` in `tmdl_generator.py` |
| 26 | Pagination for large reports | Agent 05 | S | ✅ Phase 49 | `layout_engine.py` `paginate()` with y-cursor reflow |
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
- [x] **Generate lineage_map.json** — `lineage_map.py`: JSON dependency graph with BFS upstream/downstream impact analysis (Phase 48)
- [ ] Extract KPI/Scorecard objects as dedicated inventory type
- [x] **Add portfolio-level assessment** — `portfolio_assessor.py`: 5-axis readiness scoring, effort estimation, wave planning (Phase 47)
- [ ] **Add paginated OAC API client** — Port T2P's `_paginated_get(url, root_key, item_key, page_size=100)` pattern with `totalAvailable` tracking for OAC catalog endpoints
- [x] **Add safe XML parsing** — `safe_xml.py`: XXE-protected parsing + path validation (Phase 47)
- [ ] **Add datasource deduplication** — Port T2P's highest-richness-wins strategy: keep datasource with max `len(tables) + len(calculations)` when duplicates detected

### Agent 02 — Schema
- [ ] Generate Delta partitioning strategy from Oracle partition metadata
- [ ] Map Oracle synonyms to view aliases
- [ ] Add Fabric Shortcut generation for database link equivalents
- [ ] Add partition-aware parallel data copy
- [ ] Document materialized view workaround (Lakehouse view template)
- [x] **Add 3-level type mapping** — `lakehouse_generator.py`: Oracle→Delta, RPD semantic→Delta, ISO SQL→Delta (Phase 47)
- [x] **Add Fabric name sanitization** — `fabric_naming.py`: sanitize_table/column/schema + PascalCase/snake_case (Phase 47)
- [x] **Add Lakehouse 3-artifact generation** — `lakehouse_generator.py`: definition + DDL + metadata (Phase 47)
- [ ] **Add calculated column classification** — Port T2P's `classify_calculations()`: separate row-level calc columns vs aggregates

### Agent 03 — ETL
- [ ] Add Spark pivot/unpivot templates for unmapped dataflow steps
- [ ] Inject environment parameters (dev/test/prod) in pipeline JSON
- [ ] Add data quality profiling notebook template
- [ ] Generate parallel pipeline branches from job chain analysis
- [ ] Add post-deployment alert template generation
- [x] **Add 3-stage pipeline orchestration** — `fabric_pipeline_generator.py`: RefreshDataflow→TridentNotebook→TridentDatasetRefresh (Phase 47)
- [x] **Add 9 JDBC connector templates** — `fabric_pipeline_generator.py`: Oracle, PostgreSQL, SQL Server, Snowflake, BigQuery, CSV, Excel, Custom SQL, Databricks (Phase 47)
- [ ] **Add OAC expression→PySpark translator** — Port T2P's `tableau_formula_to_pyspark()` pattern
- [ ] **Add OAC expression→M query translator** — Port T2P's `tableau_formula_to_m()` pattern
- [x] **Add incremental merge engine** — `incremental_merger.py`: USER_OWNED_FILES + USER_EDITABLE_KEYS merge (Phase 47)

### Agent 04 — Semantic Model
- [x] **Implement Auto Calendar table** — `calendar_generator.py`: 8-column Calendar, hierarchy, 3 TI measures (Phase 47)
- [x] **Implement TMDL self-healing (6→17 patterns)** — `tmdl_self_healing.py`: Phase 47: 6 core; Phase 48: +11 (sort-by, format, duplicates, partition, brackets, BOM, whitespace, display folders, unreferenced hidden)
- [x] **Auto-generate M:N bridge tables** — `bridge_table_generator.py`: DDL + TMDL relationships + M expression (Phase 49)
- [x] **Move DAXOptimizer to pre-deploy** — `dax_optimizer.py`: 5 rules (Phase 47)
- [x] **Add OAC function leak detector** — `leak_detector.py`: 22 OAC function leak patterns + auto-fix (Phase 47)
- [ ] **Add DAX→M calculated column conversion** — Port T2P's 15+ patterns (performance optimization)
- [x] **Add database.tmdl generation** — `tmdl_generator.py`: compatibility level 1600+ (Phase 47)
- [x] **Add multi-culture TMDL** — `tmdl_generator.py`: `generate_culture_tmdl()` + `generate_all_cultures()` for 19 locales (Phase 49)
- [x] **Add Copilot-friendly annotations** — `tmdl_generator.py`: `annotate_for_copilot()` emits `Copilot_TableDescription` annotations (Phase 49)
- [ ] Add calculation group templates (currency, time)
- [x] Implement display folder strategy — `_build_display_folder_map()` groups by RPD subject area (Phase 49)
- [x] Add shared semantic model merge engine — `shared_model_merge.py`: fingerprint + Jaccard deduplication (Phase 48)
- [x] Add thin report generator with `byPath` semantic model reference — `shared_model_merge.py` (Phase 48)
- [x] Add relationship cycle-breaking — Union-Find in `tmdl_self_healing.py` (Phase 47)

### Agent 05 — Report
- [x] **Expand visual types from 24 to 80+** — `visual_mapper.py`: 80+ types (60+ OAC, 60+ PBI including 30+ AppSource GUIDs) (Phase 47+48)
- [x] **Add custom visual GUID registry** — `visual_mapper.py`: 18+ AppSource visuals (Sankey, Chord, WordCloud, Gantt, Network, Radar, Timeline, Bullet, Tornado, etc.) (Phase 47)
- [x] **Add visual fallback cascade** — `visual_fallback.py`: 3-tier cascade: complex→simpler→table→card (Phase 47)
- [x] **Add bookmark generation** — `bookmark_generator.py`: PBI bookmarks from OAC story points + saved states (Phase 47)
- [x] **Wire drill-through** — `pbir_generator.py`: `wire_drillthrough()` + `generate_drillthrough_page()` (Phase 49)
- [x] **Wire What-If parameters** — `pbir_generator.py`: `generate_whatif_slicer()` + `generate_whatif_tmdl()` (Phase 49)
- [x] **Add cascading slicer DAX** — `prompt_converter.py`: `generate_cascading_filter_dax()` + `build_cascading_chain()` (Phase 49)
- [ ] **Add approximation map** — For each unsupported visual type, document nearest PBI equivalent
- [x] **Add visual z-order/overlap detection** — `layout_engine.py`: `assign_z_order()` + `detect_overlaps()` (Phase 49)
- [x] Implement OAC theme → PBI theme JSON converter — `theme_converter.py` (Phase 49)
- [x] Generate phone/tablet mobile layouts — `layout_engine.py`: `generate_mobile_layout()` (360×640) (Phase 49)
- [x] Generate tooltip pages from OAC drill-down configs — `pbir_generator.py`: `generate_tooltip_page()` + `wire_tooltip_to_visual()` (Phase 49)
- [x] Add auto-pagination for >30 visual reports — `layout_engine.py`: `paginate()` with y-cursor reflow (Phase 49)
- [ ] Add OAC Agent/Alert → PBI data-driven alert migration
- [ ] Add KPI/Scorecard → PBI Goals generator
- [ ] Add auto-refresh page configuration

### Agent 06 — Security
- [x] **Implement hierarchy-based dynamic RLS** — `rls_converter.py`: `generate_hierarchy_rls()` + `generate_hierarchy_rls_dax()` with PATH/PATHCONTAINS (Phase 49)
- [x] **Add Purview sensitivity label mapping** — `governance_engine.py`: OAC roles → Purview labels via config dict (Phase 47)
- [ ] Add Microsoft Graph API batch AAD group creation
- [ ] Document cell-level security limitation + workaround
- [x] **Add governance engine** — `governance_engine.py`: warn|enforce modes, naming rules, PII detection, sensitivity mapping, audit trail (Phase 47)
- [x] **Add PII detector (15 regex patterns)** — `governance_engine.py`: email, SSN, phone, personal name, credit card + 10 more (Phase 47)
- [x] **Add credential redaction (10 patterns)** — `governance_engine.py`: password, Bearer, client_secret, connection strings, API keys (Phase 47)
- [x] **Add safe RPD XML parsing** — `safe_xml.py`: XXE-protected + path validation (Phase 47)
- [x] **Add sensitivity label auto-mapping** — `governance_engine.py`: Administrator→Highly Confidential, Viewer→General, custom mapping (Phase 47)

### Agent 07 — Validation
- [x] Add schema drift detection — `schema_drift.py`: `SchemaSnapshot`, `DriftReport`, critical drift flagging (Phase 49)
- [ ] Add statistical sampling strategy for >100M row tables
- [ ] Add continuous regression testing (scheduled re-validation)
- [ ] Add test data masking for non-prod environments
- [x] **Add TMDL structural validation** — `tmdl_validator.py`: required files, dirs, keys, JSON schema + 8-point readiness check (Phase 47)
- [x] **Add DAX leak detector** — `leak_detector.py`: 22 OAC function leak patterns + auto-fix (Phase 47)
- [x] **Add pre-migration readiness assessment** — `tmdl_validator.py`: 8-point check (connectors, chart types, functions, expressions, parameters, data blending, dashboard features, security) (Phase 47)

### Agent 08 — Orchestrator
- [x] Add dead letter queue (DLQ) — `dag_engine.py`: `DeadLetterQueue` with entry tracking + JSON export (Phase 49)
- [x] **Add SLA timeout enforcement per agent task** — `sla_tracker.py`: per-agent timeout, compliance evaluation, reporting (Phase 47)
- [x] Add human-in-the-loop approval gates — `wave_planner.py`: `ApprovalGate` + `GatedWavePlan` (Phase 49)
- [ ] Add cost tracking (RU/compute metering from Fabric API)
- [ ] **Add telemetry collector (v2 schema)** — Extend existing `telemetry.py` with per-object events
- [x] **Add 3-backend monitoring exporter** — `monitoring.py`: JSON + Azure Monitor + Prometheus export (Phase 47)
- [x] **Add recovery report tracker** — `recovery_report.py`: record/categorize recovery actions with severity and follow-up (Phase 47)
- [ ] **Add 4-tab telemetry dashboard** — Port T2P's interactive HTML: Portfolio Overview, Per-Analysis Results, Error Trends, Event Timeline

---

*Generated 2026-03-31 · Based on v4.3.0 codebase analysis (2,991 tests, 145 Python modules, 103 test files, 8 agents)*
