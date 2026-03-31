# Comprehensive Gap Analysis — OAC to Fabric Migration Framework

**Date:** 2026-03-31 — updated through v4.3.0 (Phase 49 — Production Hardening & Report Fidelity)  
**Scope:** All source files, test files, agent specs, docs, and deep cross-project comparison with TableauToPowerBI  
**Status:** 2,991 tests passing across 103 test files · 145 Python source files in src/

---

## Implementation Coverage

```
 DISCOVERY           SCHEMA              ETL                SEMANTIC
+----------------+  +----------------+  +----------------+  +----------------+
| OAC REST API   |  | Oracle→Delta   |  | 16 step types  |  | 120+ OAC→DAX  |
| RPD XML parser |  | Oracle→T-SQL   |  | PL/SQL→PySpark |  | Hierarchy map  |
| Dependency DAG |  | 16 type maps   |  | Schedule→Trig  |  | TMDL generator |
| Complexity scr |  | 14 SQL func map|  | LLM-assisted   |  | LLM fallback   |
| OBIEE/Tab conn |  | Full + Incr    |  | Dataflow parse |  | RPD model parse|
+-------+--------+  +-------+--------+  +-------+--------+  +-------+--------+
        |                    |                    |                    |+

 REPORT              SECURITY            VALIDATION         ORCHESTRATOR
+----------------+  +----------------+  +----------------+  +----------------+
| 80+ PBI visuals|  | RLS DAX filter |  | Data reconcile |  | DAG engine     |
| 30+ AppSource  |  | OLS generation |  | Semantic valid |  | Wave planner   |
| 3-tier fallback|  | Governance eng |  | TMDL validator |  | SLA tracker    |
| Bookmarks      |  | PII detection  |  | Report visual  |  | 3-backend mon  |
| PBIR generator |  | Sensitivity lbl|  | Security test  |  | Recovery report|
| Layout engine  |  | Workspace roles|  | Perf benchmark |  | CLI + API      |
| Grid→pixel map |  | Session→AAD    |  | Leak detection |  | Notifications  |
+-------+--------+  +-------+--------+  +-------+--------+  +-------+--------+
        |                    |                    |                    |
        +--------------------+--------------------+--------------------+
                                     |
                     v1.0 → v4.3 (2,991 tests)
                     +-------------------------------+
                     | Multi-source connectors (OAC,  |
                     |   OBIEE, Tableau, Cognos, Qlik)|
                     | React dashboard               |
                     | Plugin architecture            |
                     | Multi-tenant SaaS              |
                     | Incremental migration          |
                     | Rollback & versioning          |
                     | UAT workflow                   |
                     | TMDL self-healing (17 patterns)|
                     | Calendar/Date table generation |
                     | DAX optimizer (5 rules)        |
                     | OAC function leak detector     |
                     | Governance framework           |
                     +-------------------------------+
```

---

## 1. Discovery Layer (`src/agents/discovery/`)

### What IS implemented
- **OAC REST API crawl**: Paginated catalog discovery (analyses, dashboards, models, prompts, agents, connections, data flows)
- **RPD XML parsing**: Physical, logical, and presentation layers extracted from XUDML/UDML format (XXE-protected via `safe_xml.py`)
- **Dependency graph**: DAG builder with cycle detection and topological sort
- **Complexity scoring**: 6-factor weighted formula (columns, calculations, prompts, pages, RLS, custom visuals)
- **Portfolio assessment**: 5-axis readiness scoring, effort estimation, wave planning recommendations (`portfolio_assessor.py`)
- **Streaming parser**: Memory-efficient XML parsing for RPD files >50 MB
- **Multi-source connectors**: OAC (full), OBIEE (full), Tableau (full — TWB/TWBX, REST API, 55+ calc→DAX), Essbase (full — REST API, outline parser, 55+ calc→DAX, 24+ MDX→DAX, 22 outline→TMDL), Cognos (full), Qlik (full)

### What is MISSING or INCOMPLETE
- **Incremental re-discovery**: No delta crawl — full re-scan required every time
- **Rate limit tracking**: Exponential backoff exists but no rate limit counter/dashboard
- **OAC version-specific API differences**: Not handled (may miss features in newer OAC versions)
- **Performance targets**: No documented SLA for discovery (how long for N assets?)
- **RPD circular reference handling**: Detected but not gracefully resolved (may cause infinite loops on malformed RPDs)

### What is APPROXIMATED
- **OAC Data Flow complexity**: Scored by step count only, not by transformation complexity
- **Dashboard layout extraction**: Grid positions captured but nested containers lose relative positioning

---

## 2. Schema Migration Layer (`src/agents/schema/`)

### What IS implemented
- **Oracle → Fabric Lakehouse (Spark/Delta)**: 16 type mappings with edge case handling
- **Oracle → Fabric Warehouse (T-SQL)**: 8 type mappings
- **Oracle SQL → Fabric SQL**: 14+ function translations (NVL, DECODE, SYSDATE, ROWNUM, CONNECT BY, etc.)
- **Data loading**: Full load (parallel copy by PK range, 100K batch) + incremental (watermark MERGE)
- **DDL generation**: CREATE TABLE, ALTER TABLE for both Lakehouse and Warehouse targets

### What is MISSING or INCOMPLETE
- **Constraint migration**: Primary keys, foreign keys, and indexes are not fully migrated (Delta tables have limited support)
- **View dependency resolution**: Views are translated individually; complex cross-view dependencies may fail
- **Materialized views**: Not handled (no Fabric equivalent)
- **Oracle partitioning**: Table partitions are flattened — no Delta Lake partitioning strategy generated
- **Virtual columns**: Not explicitly handled (treated as regular columns)
- **Edition-based redefinition**: Not supported (Oracle-specific feature)
- **Sequence migration**: Oracle sequences → identity columns mapping exists but not fully tested at scale

---

## 3. ETL Migration Layer (`src/agents/etl/`)

### What IS implemented
- **16 OAC Data Flow step types** mapped to Fabric equivalents
- **12 PL/SQL → PySpark patterns**: Cursors, DML, MERGE, exceptions, temp tables, sequences
- **LLM-assisted translation**: Azure OpenAI GPT-4 for complex PL/SQL with prompt template
- **Schedule migration**: DBMS_SCHEDULER → Fabric triggers (daily, hourly, cron)
- **Dataflow Gen2**: M (Power Query) generation for simple transformations

### What is MISSING or INCOMPLETE
- **Dataflow Gen2 depth**: Only simple M queries generated; complex Power Query logic not yet supported
- ✅ ~~**Error handling in ETL**~~: DQ profiling notebook generator implemented in `dq_profiler.py`
- ✅ ~~**Parameterization**~~: Environment-specific config (dev/test/prod) implemented in `fabric_pipeline_generator.py` — `parameterize_pipeline()` + `generate_env_config_json()`
- **Pipeline monitoring/alerting**: No post-deployment alerting rules generated
- **Complex PL/SQL packages**: Multi-procedure packages with inter-dependency not fully decomposed

### What is APPROXIMATED
- **Job chains**: Sequential pipeline activities — parallel branches not generated
- **Complex DBMS_SCHEDULER expressions**: Converted to basic cron; advanced calendar expressions may lose precision

---

## 4. Semantic Model Layer (`src/agents/semantic/`)

### What IS implemented
- **RPD → TMDL mapping**: 10 concept-level mappings (logical table → TMDL table, etc.)
- **120+ OAC expression → DAX rules**: AGO, TODATE, PERIODROLLING, RANK, RSUM, session variables, STDDEV, MEDIAN, PERCENTILE, DECODE, NVL2, GREATEST, LEAST, PARALLELPERIOD, OPENINGBALANCEYEAR, CLOSINGBALANCEYEAR, etc.
- **Hybrid translation**: Rules-first + LLM fallback with confidence scoring
- **Hierarchies**: Multi-level hierarchy generation with proper TMDL formatting
- **TMDL file generation**: Complete folder structure (model.tmdl, tables/, relationships.tmdl, roles.tmdl, perspectives.tmdl, expressions.tmdl)

### TMDL Output Comparison vs. TableauToPowerBI

| TMDL Component | OAC→Fabric | T2P | Gap |
|---|:---:|:---:|---|
| `model.tmdl` (culture, data access) | ✅ `culture: en-US` + 19 locales | ✅ multi-culture | Parity (implemented in `tmdl_generator.py`) |
| `tables/*.tmdl` (columns, measures, partitions) | ✅ | ✅ | Parity on basic structure |
| `relationships.tmdl` (cardinality, cross-filter) | ✅ | ✅ + inactive cycle-breaking | OAC missing auto-deactivation of ambiguous relationship cycles |
| `roles.tmdl` (RLS DAX filters) | ✅ | ✅ | Parity |
| `perspectives.tmdl` | ✅ | ✅ | Parity (OAC maps subject areas → perspectives) |
| `expressions.tmdl` (M data sources) | ✅ | ✅ | Parity |
| `cultures/*.tmdl` (multi-language) | ✅ 19 locales | ✅ 19 languages | Parity (implemented in `tmdl_generator.py`) |
| `database.tmdl` (compatibility level) | ✅ | ✅ 1600+ | Parity (implemented) |
| `lineageTag` UUIDs | ✅ | ✅ | Parity |
| `sortByColumn` | ✅ | ✅ | Parity (MonthName → Month) |
| `displayFolder` | ✅ intelligent grouping from subject areas | ✅ intelligent grouping | Parity (implemented in `tmdl_generator.py`) |
| `formatString` | ✅ | ✅ | Parity |
| `isHidden` | ✅ | ✅ | Parity |
| `summarizeBy` | ✅ | ✅ | Parity |
| `description` / annotations | ✅ `Copilot_TableDescription` annotations | ✅ `Copilot_TableDescription` annotations | Parity (implemented in `tmdl_generator.py`) |
| DAX→M calculated column conversion | ❌ | ✅ 15+ patterns (IF→each, UPPER→Text.Upper, etc.) | **Gap**: No DAX→M optimization for calculated columns |
| Calendar/Date table auto-generation | ✅ | ✅ 8 columns + hierarchy + 3 TI measures | Parity (implemented in `calendar_generator.py`) |
| Self-healing (17 patterns) | ✅ | ✅ duplicates, broken refs, orphans, empty names, circular rels, M errors, sort-by, format strings, partition mode, expression brackets, BOM, whitespace, display folders, unreferenced hidden | **Exceeds T2P** (implemented in `tmdl_self_healing.py`) |
| DAX Optimizer (5 rules) | ✅ pre-deployment | ✅ ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding | Parity (implemented in `dax_optimizer.py`) |
| Relationship inference (3-phase) | 🟡 from RPD joins only | ✅ explicit + inferred (DAX scan) + cardinality heuristic | **Gap**: No DAX-based relationship inference |
| Calculated tables | ❌ | ✅ | **Gap**: Only direct + calculated columns + measures |
| Composite model / aggregation tables | ❌ gen, 🟡 advisor | ✅ auto-generated Import-mode aggregation tables | **Gap**: Advisor recommends but doesn't generate |
| Shared semantic model merge | ✅ | ✅ fingerprint + Jaccard deduplication | Parity (implemented in `shared_model_merge.py`) |

### What is MISSING or INCOMPLETE
- ✅ ~~**M:N relationships**~~: Detected and resolved via bridge table generation in `bridge_table_generator.py` — DDL + TMDL + relationships + M expression
- **Calculation groups**: Not implemented (Power BI feature with no direct OAC equivalent)
- ✅ ~~**Display folder strategy**~~: Intelligent grouping from RPD subject areas implemented in `tmdl_generator.py` — `_build_display_folder_map()`
- **Incremental model updates**: Full regeneration only; no delta TMDL update
- **Composite models / aggregation tables**: Not generated (all tables use Import mode)
- ✅ ~~**Multi-culture TMDL**~~: 19 locale `cultures/*.tmdl` files generated via `generate_culture_tmdl()` / `generate_all_cultures()` in `tmdl_generator.py`
- ✅ ~~**Annotations**~~: `Copilot_TableDescription` annotations generated via `annotate_for_copilot()` in `tmdl_generator.py`
- **DAX→M column optimization**: T2P converts DAX calculated columns to M query `each` expressions for better performance (15+ patterns: IF→each if/then, UPPER→Text.Upper, YEAR→Date.Year, etc.)

### What WAS MISSING (now implemented in Phase 47)
- ✅ **Auto-generated Calendar table**: Implemented in `calendar_generator.py` — 8-column Calendar with M query, hierarchy, and 3 time intelligence measures
- ✅ **Self-healing (6→17 patterns)**: Implemented in `tmdl_self_healing.py` — Phase 47: 6 core patterns; Phase 48: +11 (sort-by, format strings, duplicate measures/columns, partition mode, expression brackets, BOM, whitespace, display folders, unreferenced hidden)
- ✅ **database.tmdl**: Implemented in `tmdl_generator.py` — compatibility level 1600+
- ✅ **DAX Optimizer (5 rules)**: Implemented in `dax_optimizer.py` — ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding
- ✅ **OAC Function Leak Detector**: Implemented in `leak_detector.py` — 22 OAC patterns + auto-fix
- ✅ **Relationship cycle detection**: Implemented via Union-Find in `tmdl_self_healing.py`
- ✅ **Shared semantic model merge**: Implemented in `shared_model_merge.py` — fingerprint + Jaccard deduplication + thin report references
- ✅ **Lineage map (JSON)**: Implemented in `lineage_map.py` — full dependency graph with BFS impact analysis
- ✅ **DAX rules expanded (60→120+)**: Added STDDEV, VARIANCE, MEDIAN, PERCENTILE, COUNT(*), COUNTIF, SUMIF, DECODE, NVL2, GREATEST, LEAST, PARALLELPERIOD, etc.

### What is APPROXIMATED
- **Complex nested OAC expressions**: LLM translation with confidence < 0.7 flagged for review
- **INDEXCOL / DESCRIPTOR_IDOF**: Best-effort column key reference mapping

---

## 5. Report Layer (`src/agents/report/`)

### What IS implemented
- **80+ OAC visual types** mapped to Power BI visuals (60+ OAC chart types → 60+ PBI visual types including 30+ AppSource custom visual GUIDs)
- **3-tier visual fallback cascade** (`visual_fallback.py`): complex→simpler→table→card
- **18+ AppSource custom visuals**: Sankey, Chord, Word Cloud, Gantt, Network, Radar, Timeline, Bullet, Tornado, etc.
- **Bookmark generation** (`bookmark_generator.py`): PBI bookmarks from OAC story points + saved states
- **9 prompt types** → slicer/parameter configurations
- **Conditional formatting**: Color, data bars, icon sets
- **Layout engine**: OAC grid → 1280×720 pixel canvas conversion
- **Dashboard actions**: Navigate, filter, master-detail → drillthrough, bookmarks
- **PBIR generation**: Complete folder structure (definition.pbir, report.json, pages/, visuals/)

### PBIR Output Comparison vs. TableauToPowerBI

| PBIR Component | OAC→Fabric | T2P | Gap |
|---|:---:|:---:|---|
| `definition.pbir` (4.0 format, model ref) | ✅ | ✅ | Parity |
| `report.json` (page config, theme) | ✅ | ✅ | Parity |
| `pages/{page}/visuals/{visual}.json` | ✅ | ✅ | Parity on structure |
| `SemanticQueryDataShapeCommand` in visuals | ✅ | ✅ | OAC generates projections + prototypeQuery |
| `StaticResources/BaseThemes/` | ✅ OAC theme → PBI JSON | ✅ default theme | OAC advantage (implemented in `theme_converter.py`) |
| `.platform` (Git integration) | ✅ | ✅ | Parity |
| `.pbip` project file | ✅ | ✅ | Parity |
| Bookmarks (saved filter states) | ✅ | ✅ | Parity (implemented in `bookmark_generator.py` — Phase 47) |
| Drill-through visual interactions | ✅ wired into visual JSON | ✅ wired into visual JSON | Parity (implemented in `pbir_generator.py` — Phase 49) |
| Page navigation between reports | ✅ `wire_drillthrough()` | ✅ | Parity (Phase 49) |
| Visual title, axis labels, legend config | ✅ `vcObjects` | ✅ `vcObjects` | Parity |
| Visual conditional formatting | ✅ color, data bars, icons | ✅ color, data bars, icons | Parity |
| Custom visuals (AppSource) | ✅ 30+ custom visual GUIDs | ✅ 18+ custom visual GUIDs | OAC advantage (more custom visuals) |
| Visual `z-order` / overlap resolution | ✅ `assign_z_order()` + `detect_overlaps()` | ✅ ordered by z | Parity (implemented in `layout_engine.py` — Phase 49) |
| Mobile/responsive layout | ✅ phone layout (360×640) | ❌ | OAC advantage (implemented in `layout_engine.py` — Phase 49) |
| What-If parameters | ✅ `generate_whatif_slicer()` + TMDL | ✅ wired | Parity (implemented in `pbir_generator.py` — Phase 49) |
| Slicer cascading (cross-filter) | ✅ auto DAX filter generation | ✅ auto DAX filter | Parity (implemented in `prompt_converter.py` — Phase 49) |

### Visual Type Coverage Comparison

| Category | OAC→Fabric Types | T2P Types | Missing in OAC |
|----------|:-:|:-:|---|
| **Bar charts** | 4 (clustered, stacked, horiz clustered, horiz stacked) + 2 (100% stacked bar, 100% stacked column) | 6 (+ 100% stacked bar, 100% stacked column) | Parity |
| **Line/Area** | 3 (line, area, combo) + 2 (stacked area, 100% stacked area) | 5 (+ stacked area, 100% stacked area) | Parity |
| **Pie/Donut** | 2 | 2 | Parity |
| **Table/Matrix** | 2 (table, pivot) | 3 (table, pivot, matrix) | explicit `matrix` type |
| **Card** | 2 (card, multiRowCard) | 2 (card, multiRowCard) | Parity |
| **Map** | 3 (filled, bubble, shapeMap) | 3 (filled, bubble, shapeMap) | Parity |
| **Scatter/Bubble** | 2 | 2 | Parity |
| **Gauge** | 1 | 1 | Parity |
| **Funnel/Treemap/Waterfall** | 3 | 3 | Parity |
| **Specialty** | 18+ (sunburst, boxAndWhisker, histogram, decompositionTree, keyInfluencers, Sankey, Chord, WordCloud, Gantt, Network, Radar, Timeline, Bullet, Tornado, etc.) | 10+ (sunburst, boxAndWhisker, histogram→binning, wordCloud, sankeyDiagram, chordChart, ganttChart, networkNavigator, etc.) | Narrowed gap — 13 more in T2P |
| **Text/Image** | 2 | 2 | Parity |
| **Slicer** | 1 | 1 | Parity |
| **TOTAL** | **80+** | **60+** | **OAC advantage** (expanded to 80+ types in Phase 48 incl. 30+ AppSource GUIDs) |

### Visual Fallback Cascade Comparison

```
T2P Fallback Chain:
  scatterChart → tableEx
  lineClusteredColumnComboChart → clusteredBarChart
  boxAndWhisker → clusteredColumnChart
  gauge → card
  [any unknown] → tableEx → card (terminal)

OAC fallback (Phase 47 — visual_fallback.py):
  scatterChart → tableEx
  combo → clusteredBarChart
  boxAndWhisker → clusteredColumnChart
  gauge → card
  [any unknown] → tableEx → card (terminal)
  → Parity with T2P
```

### Custom Visual GUID Registry — Implemented (Phase 47)

Both T2P and OAC→Fabric now maintain registries of 18+ AppSource custom visual GUIDs:
- `ChicagoITSankey1.1.0` (Sankey Diagram)
- `ChicagoITChord1.0.0` (Chord Diagram)
- `WordCloud1633006498960` (Word Cloud)
- `GanttByMAQSoftware1.0.0` (Gantt Chart)
- `networkNavigator` (Network Graph)
- + 13 more with data role mappings

### What is MISSING or INCOMPLETE
- ✅ ~~**Theme migration**~~: OAC color palette/fonts → PBI CY24SU11 theme JSON in `theme_converter.py`
- ✅ ~~**Mobile layouts**~~: Phone layout generation (360×640, single-column stacked) in `layout_engine.py` — `generate_mobile_layout()`
- ✅ ~~**Drill-through wiring**~~: Visuals configured for drill-through navigation in `pbir_generator.py` — `wire_drillthrough()` + `generate_drillthrough_page()`
- ✅ ~~**Pagination**~~: Reports with 50+ visuals auto-split across pages in `layout_engine.py` — improved `paginate()` with y-cursor reflow
- ✅ ~~**Tooltip pages**~~: Generated from OAC drill-down configs in `pbir_generator.py` — `generate_tooltip_page()` + `wire_tooltip_to_visual()`
- **Small multiples**: OAC trellis → PBI small multiples mapping incomplete for complex scenarios
- ✅ ~~**Visual z-order**~~: Area-based z-order assignment + AABB overlap detection in `layout_engine.py` — `assign_z_order()` + `detect_overlaps()`
- ✅ ~~**What-If parameters**~~: Wired into generation pipeline in `pbir_generator.py` — `generate_whatif_slicer()` + `generate_whatif_tmdl()`
- ✅ ~~**Cascading slicers**~~: Auto DAX filter generation in `prompt_converter.py` — `generate_cascading_filter_dax()` + `build_cascading_chain()`

### What is APPROXIMATED
- **Dashboard layout**: Grid positions → pixel positions; deeply nested containers (4+ levels) may misalign
- **Conditional formatting thresholds**: OAC percentage-based → PBI value-based (may need manual adjustment)

---

## 6. Security Layer (`src/agents/security/`)

### What IS implemented
- **Session variable → RLS**: USERPRINCIPALNAME() + security lookup table pattern
- **OLS**: Column/table-level hiding with TMDL metadataPermission
- **Init block SQL → Security lookup table**: Oracle SQL translated to Fabric, population strategy
- **Workspace role mapping**: OAC Admin/Creator/Viewer → Fabric Admin/Contributor/Member/Viewer
- **Governance engine** (`governance_engine.py`): warn|enforce modes, naming rules, PII detection (15 regex patterns), credential redaction (10 patterns), sensitivity label mapping, audit trail

### What is MISSING or INCOMPLETE
- ✅ ~~**Dynamic security**~~: Hierarchy-based RLS with `PATHCONTAINS`/`PATH` in `rls_converter.py` — `generate_hierarchy_rls()` + `generate_hierarchy_rls_dax()`
- **Azure AD group provisioning**: Manual — no automated group creation from OAC role assignments
- **Audit trail migration**: OAC audit logs not migrated to Fabric governance events

### What is APPROXIMATED
- **Multi-valued session variables**: Lookup table with one-to-many mapping (works for simple cases; complex OR/AND combinations may need manual tuning)

---

## 7. Validation Layer (`src/agents/validation/`)

### What IS implemented
- **4 validation layers**: Data (row counts, checksums, aggregates), Semantic (measures, hierarchies, time intelligence), Reports (visual count, screenshots), Security (per-user RLS/OLS)
- **Performance benchmarks**: Load time, query time, refresh time, concurrency
- **Reconciliation query generator**: Paired Oracle/Fabric queries with tolerance thresholds
- **Visual comparison**: Playwright screenshots + SSIM scoring + GPT-4o comparison
- **Defect ticket generation**: Azure DevOps work items from validation failures

### What is MISSING or INCOMPLETE
- ✅ ~~**Automated regression detection**~~: Schema drift detection between snapshots in `schema_drift.py` — `SchemaSnapshot`, `DriftReport`, critical drift flagging
- **Statistical sampling**: No sampling strategy for very large tables (>100M rows)
- **Test data masking**: No handling of data masking in lower environments
- **Continuous validation**: No scheduled re-validation after go-live

---

## 8. Orchestration Layer (`src/agents/orchestrator/`)

### What IS implemented
- **DAG engine**: Topological sort with parallel execution and retry logic
- **Wave planner**: Multi-wave planning with resource allocation
- **Task state machine**: PENDING → ASSIGNED → IN_PROGRESS → VALIDATING → COMPLETED (+ FAILED → RETRYING → BLOCKED)
- **Notifications**: Teams, email, PagerDuty integration
- **CLI**: Full Typer CLI with `--dry-run`, `--wave`, `--config`, `--resume` flags
- **REST API**: FastAPI with 7 endpoints (CRUD migrations, inventory, logs, health)
- **SLA tracker** (`sla_tracker.py`): Per-agent timeout enforcement, compliance evaluation, reporting
- **3-backend monitoring** (`monitoring.py`): JSON + Azure Monitor + Prometheus export
- **Recovery report** (`recovery_report.py`): Record/categorize all self-healing actions

### What is MISSING or INCOMPLETE
- ✅ ~~**Dead letter queue**~~: `DeadLetterQueue` with entry tracking, JSON export, summary in `dag_engine.py`
- ✅ ~~**Manual approval gates**~~: `ApprovalGate` workflow with `GatedWavePlan` in `wave_planner.py` — approve/reject per wave
- **Cost tracking**: No RU/compute cost estimation per wave

---

## 9. Documentation Gaps

### Compared to TableauToPowerBI project

| Document | OACToFabric | TableauToPowerBI | Gap |
|----------|:-----------:|:----------------:|-----|
| README | ✅ | ✅ | OAC missing performance benchmarks section |
| ARCHITECTURE | ✅ (new) | ✅ | Parity — created based on T2P model |
| AGENTS / Agent specs | ✅ | ✅ | Parity — ownership/constraints added |
| DEV_PLAN | ✅ | ✅ | OAC missing burndown/velocity data |
| DEPLOYMENT_GUIDE | ✅ (new) | ✅ | Parity — created based on T2P model |
| GAP_ANALYSIS | ✅ (this file) | ✅ | Parity |
| KNOWN_LIMITATIONS | ✅ (new) | ✅ | Parity |
| MIGRATION_PLAYBOOK | ✅ | N/A | OAC advantage (T2P has Enterprise Guide) |
| CONTRIBUTING | ✅ | ✅ | OAC missing branching strategy |
| Security | ✅ | ✅ | OAC missing threat model, compliance mapping |
| ADRs | ✅ (4) | N/A | OAC advantage |
| Runbooks | ✅ (6) | N/A | OAC advantage |
| Guides | ✅ (3) | ✅ (multiple) | Comparable |
| FAQ | ✅ | ✅ | Parity — `docs/FAQ.md` created |
| API Reference | ❌ | ❌ | Both missing — generate from FastAPI/OpenAPI |
| MAPPING_REFERENCE | ✅ (new) | ✅ | Parity — created |
| KNOWN_LIMITATIONS | ✅ (new) | ✅ | Parity |

---

## 10. Cross-Project Comparison — Deep Power BI Component Analysis

### TMDL Feature Parity

| TMDL Feature | T2P Implementation | OAC→Fabric Implementation | Gap Severity |
|---|---|---|:---:|
| **model.tmdl** structure | culture, defaultPBIDS, metadata | culture: en-US + 19 locales, metadata | ✅ Parity (Phase 49: `generate_all_cultures()`) |
| **database.tmdl** (compatibility level) | ✅ `compatibilityLevel: 1600` | ✅ `compatibilityLevel: 1600` | Parity (implemented in `tmdl_generator.py`) |
| **tables/*.tmdl** | columns, measures, calc columns, partitions, hierarchies, annotations | columns, measures, calc columns, partitions, hierarchies, annotations | ✅ Parity (Phase 49: `annotate_for_copilot()`) |
| **relationships.tmdl** | explicit + inferred (DAX scan) + cardinality heuristic; Union-Find cycle-breaking | explicit from RPD joins + Union-Find cycle-breaking | 🟡 No DAX-based inference |
| **roles.tmdl** | RLS with USERNAME(), ISMEMBEROF(), multi-table filters | RLS with USERPRINCIPALNAME() + lookup table + hierarchy RLS | ✅ comparable |
| **perspectives.tmdl** | from Tableau dashboard scoping | from RPD subject areas | ✅ |
| **expressions.tmdl** | M data source expressions (42 connector types) | M data source expressions (Fabric Lakehouse) | ✅ different scope |
| **cultures/*.tmdl** | 19 language files (en-US, fr-FR, de-DE, ja-JP, etc.) | ✅ 19 locales via `generate_culture_tmdl()` (Phase 49) | ✅ Parity |
| **lineageTag** UUIDs | ✅ on all objects | ✅ on all objects | ✅ |
| **sortByColumn** | ✅ MonthName→Month, DayName→DayOfWeek | ✅ | ✅ |
| **displayFolder** | ✅ intelligent grouping by data source | ✅ `_build_display_folder_map()` from RPD subject areas (Phase 49) | ✅ Parity |
| **formatString** | ✅ currency, percentage, decimal, date, custom | ✅ | ✅ |
| **isHidden** | ✅ | ✅ | ✅ |
| **Annotations** | ✅ `Copilot_TableDescription`, migration metadata | ✅ `annotate_for_copilot()` in `tmdl_generator.py` (Phase 49) | ✅ Parity |
| **Calendar/Date table** | ✅ auto-detect → 8 columns + hierarchy + 3 TI measures + M query | ✅ `calendar_generator.py` (Phase 47) | ✅ Parity |
| **Self-healing (17 patterns)** | ✅ duplicate names, broken refs, orphan measures, empty names, circular rels, M query try/otherwise | ✅ 17 patterns in `tmdl_self_healing.py` (Phase 47+48) **Exceeds T2P** | ✅ |
| **DAX Optimizer** | ✅ 5 rules: ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding | ✅ 5 rules in `dax_optimizer.py` (Phase 47) | ✅ Parity |
| **DAX→M column conversion** | ✅ 15+ patterns: IF→each, UPPER→Text.Upper, YEAR→Date.Year, DATEDIFF→Duration.Days | ❌ not implemented | 🟡 |
| **3-phase relationship detection** | ✅ explicit (joins) → inferred (DAX cross-table refs) → cardinality heuristic | 🟡 explicit (RPD joins) only | 🟡 |
| **Calculated tables** | ✅ DAX-based calculated tables | ❌ not supported | 🟡 |
| **Aggregation tables** | ✅ auto-generated Import-mode agg for DQ tables | 🟡 advisor recommends only | 🟡 |
| **Shared model merge** | ✅ SHA256 table fingerprint + Jaccard dedup | ✅ `shared_model_merge.py` (Phase 48) | ✅ Parity |
| **Thin report byPath reference** | ✅ `"byPath": {"path": "../SharedModel.SemanticModel"}` | ✅ `shared_model_merge.py` (Phase 48) | ✅ Parity |

### PBIR Feature Parity

| PBIR Feature | T2P Implementation | OAC→Fabric Implementation | Gap Severity |
|---|---|---|:---:|
| **definition.pbir** | ✅ PBIR v4.0, semantic model ref | ✅ PBIR v4.0, semantic model ref | ✅ |
| **report.json** | ✅ page ordering, relationships | ✅ page config, theme | ✅ |
| **pages/{id}.json** | ✅ displayName, width/height, ordinal, filters | ✅ | ✅ |
| **visuals/{id}/visual.json** | ✅ SemanticQueryDataShapeCommand, vcObjects, filterConfig | ✅ | ✅ |
| **.platform** | ✅ Git integration | ✅ | ✅ |
| **.pbip** project file | ✅ | ✅ | ✅ |
| **StaticResources/BaseThemes** | ✅ default CY24SU06 theme | ✅ default CY24SU06 theme | ✅ |
| **Visual type count** | **60+** (including 18 custom visual GUIDs) | **80+** (including 30+ AppSource GUIDs) | ✅ OAC advantage (expanded Phase 48) |
| **Custom visual GUID registry** | ✅ 18+ AppSource visuals with data role mappings | ✅ 18+ AppSource visuals registered | Parity (implemented in `visual_mapper.py`) |
| **Visual fallback cascade** | ✅ 3-tier: complex→simpler→table→card | ✅ 3-tier: complex→simpler→table→card | Parity (implemented in `visual_fallback.py`) |
| **Bookmarks** | ✅ saved filter states | ✅ from OAC story points + saved states | Parity (implemented in `bookmark_generator.py`) |
| **Drill-through** | ✅ wired into visual JSON, page navigation | ✅ wired into visual JSON | Parity (implemented in `pbir_generator.py`) |
| **What-If parameters** | ✅ wired into visuals | ✅ wired into visuals | Parity (implemented in `pbir_generator.py`) |
| **Cascading slicers** | ✅ auto DAX filter generation | ✅ auto DAX filter generation | Parity (implemented in `prompt_converter.py`) |
| **Visual z-order** | ✅ ordered by z-index, overlap detection | ✅ area-based z-order + AABB overlap detection | Parity (implemented in `layout_engine.py`) |
| **Approximation map** | ✅ maps unsupported→nearest with migration notes | ❌ | 🟡 |
| **Mobile/responsive layout** | ❌ | ✅ phone layout generation (360×640) | OAC advantage (implemented in `layout_engine.py`) |

### Visual Type Comparison — Full Detail

| Visual Category | T2P Mapped Types | OAC Mapped Types | Gap |
|---|---|---|---|
| **Standard bar/column** | clusteredBarChart, stackedBarChart, hundredPercentStackedBarChart, clusteredColumnChart, stackedColumnChart, hundredPercentStackedColumnChart | clusteredBarChart, stackedBarChart, hundredPercentStackedBarChart, clusteredColumnChart, stackedColumnChart, hundredPercentStackedColumnChart | Parity |
| **Line/Area** | lineChart, areaChart, stackedAreaChart, hundredPercentStackedAreaChart | lineChart, areaChart, stackedAreaChart, hundredPercentStackedAreaChart | Parity |
| **Combo** | lineStackedColumnComboChart, lineClusteredColumnComboChart | lineClusteredColumnComboChart | -1 |
| **Pie/Donut** | pieChart, donutChart | pieChart, donutChart | Parity |
| **Scatter/Bubble** | scatterChart (+ size field) | scatterChart (+ size field) | Parity |
| **Card** | card, multiRowCard | card, multiRowCard | Parity |
| **Table/Matrix** | tableEx, pivotTable, matrix | tableEx, pivotTable | -1 (explicit matrix) |
| **Map** | map, filledMap, shapeMap | map, filledMap, shapeMap | Parity |
| **Gauge** | gauge | gauge | Parity |
| **Funnel/Treemap/Waterfall** | funnel, treemap, waterfallChart | funnel, treemap, waterfallChart | Parity |
| **Specialty (built-in)** | sunburst, boxAndWhisker, histogram→binning, decompositionTree, keyInfluencers | sunburst, boxAndWhisker, histogram, decompositionTree, keyInfluencers | Parity |
| **Custom visuals** | sankeyDiagram, chordChart, wordCloud, ganttChart, networkNavigator, + 13 more | sankeyDiagram, chordChart, wordCloud, ganttChart, networkNavigator, radar, timeline, bullet, tornado, + 9 more | Narrowed gap — ~13 more in T2P |
| **Text/Image** | textbox, image | textbox, image | Parity |
| **TOTAL** | **60+** | **80+** | OAC advantage |

### DAX Leak Detector — Implemented (Phase 47)

Both T2P and OAC→Fabric now have dedicated DAX leak detectors:

**T2P**: Detects 5+ Tableau function leak patterns (`COUNTD`, `ZN`, `IFNULL`, `ATTR`, LOD expressions) + auto-fix rules.

**OAC→Fabric** (`leak_detector.py`): Detects 22 OAC function leak patterns (`NVL`, `NVL2`, `DECODE`, `SYSDATE`, `ROWNUM`, `SUBSTR`, `INSTR`, `TRUNC`, `VALUEOF(NQ_SESSION.*)`, etc.) + auto-fix rules.

### Pre-Migration Assessment — Implemented (Phase 47)

Both T2P and OAC→Fabric now have 8-point pre-migration readiness checks:
1. **Connectors** — supported/unsupported data sources
2. **Chart Types** — against visual mapping table
3. **Functions** — regex scan for unsupported functions
4. **Expressions** — warns about complex OAC expressions (T2P: LOD expressions)
5. **Parameters** — count and classification
6. **Data Blending** — multi-source join detection
7. **Dashboard Features** — cascade filters, actions, drillthrough
8. **Security** — RLS roles, session variables

OAC→Fabric implementation in `tmdl_validator.py` (Phase 47).

### Feature Parity Summary

| Capability | T2P | OAC→Fabric | Notes |
|------------|:---:|:----------:|-------|
| Source extraction | 20 object types | 18+ via API + 3 RPD layers | OAC advantage (more source types) |
| DAX conversions | 180+ | 60+ (OAC) + 200+ (all connectors) | OAC 260+ total across all connectors — **parity** |
| Visual types | 60+ with 18 custom GUIDs | 80+ with 30+ custom GUIDs | **OAC advantage** (expanded Phase 48) |
| Data connectors (M query) | 42 | N/A (Fabric-native sources) | Different target architecture |
| TMDL self-healing | 6 auto-repair patterns | ✅ 17 patterns **Exceeds T2P** | **OAC advantage** |
| DAX→M column optimization | 15+ conversion patterns | None | Gap — performance opportunity |
| Calendar table generation | 8 columns + hierarchy + 3 TI measures | ✅ 8 columns + hierarchy + 3 TI measures | **Parity** |
| DAX optimizer | 5 pre-deployment rules | ✅ 5 pre-deployment rules | **Parity** |
| DAX leak detector | Tableau function leak regex + auto-fix | ✅ 22 OAC patterns + auto-fix | **Parity** |
| Visual fallback cascade | 3-tier: complex→simple→table→card | ✅ 3-tier cascade | **Parity** |
| Custom visual GUIDs | 18+ AppSource visuals registered | ✅ 18+ registered | **Parity** |
| Bookmarks | Generated from Tableau bookmarks | ✅ from OAC story points | **Parity** |
| Drill-through wiring | Wired into visual JSON | ✅ Wired into visual JSON | **Parity** |
| Table fingerprinting/merge | SHA256 fingerprint + Jaccard | ✅ `shared_model_merge.py` (Phase 48) | **Parity** |
| Thin report (byPath ref) | Generated | ✅ `shared_model_merge.py` (Phase 48) | **Parity** |
| Multi-culture TMDL | 19 language files | ✅ 19 locales | **Parity** |
| Pre-migration assessment | 8-point readiness check | ✅ 8-point readiness check | **Parity** |
| Schema drift detection | Yes | ✅ Yes | **Parity** |
| Shared semantic model | Yes (merge engine) | ✅ Yes (fingerprint + Jaccard) | **Parity** |
| Fabric-native output | Yes (Lakehouse+Dataflow+Notebook+DirectLake) | Yes (native target) | Parity |
| Lineage map | Yes (lineage_map.json) | ✅ Full lineage with BFS | **Parity** |
| Governance framework | Yes (naming conventions, PII detection) | ✅ (naming, PII, credentials, sensitivity) | **Parity** |
| Docker / containerization | Yes | Yes | Parity |
| REST API | Yes (stdlib http.server) | Yes (FastAPI) | OAC advantage |
| Multi-tenant | Yes | Yes | Parity |
| Incremental migration | Yes (`--sync`) | Yes (`--mode incremental`) | Parity |
| Plugin system | N/A | Yes | OAC advantage |
| Multi-source connectors | Tableau only | OAC + OBIEE + Tableau + Essbase + Cognos + Qlik | OAC advantage |
| Runbooks + ADRs | None | 6 runbooks + 4 ADRs | OAC advantage |
| React dashboard | None | Full React SPA | OAC advantage |

---

## 11. Priority Improvement Areas

### Tier 1 — Critical (blocks production enterprise migration)

1. ✅ **TMDL Self-Healing** — 6 auto-repair patterns implemented in `src/agents/semantic/tmdl_self_healing.py` (168 tests)
2. ✅ **Calendar/Date Table Generation** — Auto-detect + 8-column Calendar table + hierarchy + 3 TI measures in `src/agents/semantic/calendar_generator.py` (168 tests)
3. ✅ **Visual Fallback Cascade** — 3-tier degradation cascade in `src/agents/report/visual_fallback.py` (168 tests)
4. ✅ **Custom Visual GUID Registry** — 18+ AppSource visuals registered in `src/agents/report/visual_mapper.py` (expanded 23→47 types)
5. ✅ **Visual Type Expansion** — 47 visual types now mapped (was 23) in `src/agents/report/visual_mapper.py`
6. ✅ **Bookmark Generation** — PBI bookmark JSON from OAC story points in `src/agents/report/bookmark_generator.py` (168 tests)

### Tier 2 — Important (quality and completeness)

**Semantic Model (Agent 04)**:
7. ✅ **DAX Pre-Deploy Optimizer** — 5 optimization rules in `src/agents/semantic/dax_optimizer.py`: IF→SWITCH, ISBLANK→COALESCE, SUMX→SUM, CALCULATE collapse, constant folding (168 tests)
8. ✅ **OAC Function Leak Detector** — 22 OAC function leak patterns + auto-fix in `src/agents/semantic/leak_detector.py` (168 tests)
9. **DAX→M Column Optimization** — Port T2P's 15+ DAX→M conversion patterns for calculated columns (IF→each, UPPER→Text.Upper, YEAR→Date.Year, DATEDIFF→Duration.Days)
10. ✅ **Relationship Cycle-Breaking** — Union-Find cycle detection in `src/agents/semantic/tmdl_self_healing.py`
11. **Shared Semantic Model Merge** — Port T2P's SHA256 fingerprint + Jaccard table dedup for cross-report shared models
12. ✅ **database.tmdl Generation** — Added steps 9-13 in `src/agents/semantic/tmdl_generator.py`
13. ✅ **Multi-Culture TMDL** — Generate `cultures/*.tmdl` files for 19 languages in `tmdl_generator.py` — `generate_culture_tmdl()` + `generate_all_cultures()`

**Report (Agent 05)**:
14. ✅ **Drill-Through Wiring** — Wired into visual JSON for drill-through navigation in `pbir_generator.py` — `wire_drillthrough()` + `generate_drillthrough_page()`
15. ✅ **What-If Parameter Wiring** — Wired into generation pipeline in `pbir_generator.py` — `generate_whatif_slicer()` + `generate_whatif_tmdl()`
16. ✅ **Cascading Slicer DAX** — Auto-generated in `prompt_converter.py` — `generate_cascading_filter_dax()` + `build_cascading_chain()`
17. ✅ **Pre-Migration Assessment** — 8-point readiness check in `src/agents/validation/tmdl_validator.py` (168 tests)

**Discovery (Agent 01)**:
18. ✅ **Portfolio-Level Assessment** — 5-axis readiness + effort scoring + wave planning in `src/agents/discovery/portfolio_assessor.py` (168 tests)
19. **Paginated OAC API Client** — Port T2P's `_paginated_get(url, root_key, item_key, page_size)` with `totalAvailable` tracking for OAC catalog endpoints
20. **Lineage Tracking** — Generate lineage_map.json: OAC source path → Fabric/PBI target for every object

**Schema (Agent 02)**:
21. ✅ **3-Level Type Mapping** — Oracle→Delta type map in `src/agents/schema/lakehouse_generator.py` (168 tests)
22. ✅ **Fabric Name Sanitization** — sanitize_table/column/schema + PascalCase/snake_case in `src/agents/schema/fabric_naming.py` (168 tests)
23. ✅ **Lakehouse 3-Artifact Generation** — definition + DDL + metadata in `src/agents/schema/lakehouse_generator.py` (168 tests)

**ETL (Agent 03)**:
24. ✅ **3-Stage Pipeline Orchestration** — RefreshDataflow→TridentNotebook→TridentDatasetRefresh in `src/agents/etl/fabric_pipeline_generator.py` (168 tests)
25. ✅ **9 JDBC Connector Templates** — Oracle, PostgreSQL, SQL Server, Snowflake, BigQuery, CSV, Excel, Custom SQL, Databricks in `src/agents/etl/fabric_pipeline_generator.py`
26. **OAC Expression→PySpark Translator** — Port T2P's `tableau_formula_to_pyspark()`: `IF/THEN/ELSE→F.when().otherwise()`, `ROUND→F.round()`, `UPPER→F.upper()`, `CASE→F.when().when().otherwise()`
27. ✅ **Incremental Merge Engine** — USER_OWNED_FILES + USER_EDITABLE_KEYS merge in `src/agents/etl/incremental_merger.py` (168 tests)

**Security (Agent 06)**:
28. ✅ **Governance Engine** — warn|enforce modes, naming rules, PII detection, sensitivity mapping, audit trail in `src/agents/security/governance_engine.py` (168 tests)
29. ✅ **PII Detector (15 regex patterns)** — email, SSN, phone, personal name, credit card + 10 more in `src/agents/security/governance_engine.py`
30. ✅ **Credential Redaction (10 patterns)** — password, Bearer, client_secret, api_key, connection_string, etc. in `src/agents/security/governance_engine.py`
31. ✅ **Safe RPD XML Parsing** — XXE-protected parsing + path validation in `src/agents/discovery/safe_xml.py` (168 tests)

**Validation (Agent 07)**:
32. ✅ **TMDL Structural Validation** — Required files/dirs/keys + 8-point readiness check in `src/agents/validation/tmdl_validator.py` (168 tests)
33. ✅ **DAX Leak Detector Validation** — 22 OAC function leak patterns scanned via `src/agents/semantic/leak_detector.py`
34. ✅ **Schema Drift Detection** — Snapshot comparison with critical drift flagging in `schema_drift.py` — `SchemaSnapshot`, `DriftReport`

**Orchestrator (Agent 08)**:
35. ✅ **Telemetry Collector (v2)** — Session/duration/stats/per-object events in existing `src/core/telemetry.py` + `src/agents/orchestrator/monitoring.py`
36. ✅ **SLA Tracker** — SLA compliance evaluation + reporting in `src/agents/orchestrator/sla_tracker.py` (168 tests)
37. ✅ **3-Backend Monitoring** — JSON + Azure Monitor + Prometheus export in `src/agents/orchestrator/monitoring.py` (168 tests)
38. ✅ **Recovery Report Tracker** — Record/categorize all recovery actions in `src/agents/orchestrator/recovery_report.py` (168 tests)
39. **4-Tab Telemetry Dashboard** — Port T2P's interactive HTML: Portfolio Overview, Per-Analysis Results, Error Trends, Event Timeline

### Tier 3 — Nice-to-Have (polish)

40. ✅ **Annotations** — `Copilot_TableDescription` annotations generated via `annotate_for_copilot()` in `tmdl_generator.py`
41. ✅ **Display Folder Intelligence** — Measures grouped by RPD subject area in `tmdl_generator.py` — `_build_display_folder_map()`
42. ✅ **Visual z-Order** — Area-based z-order + AABB overlap detection in `layout_engine.py`
43. **Approximation Map** — For each unsupported visual, document what PBI visual it maps to and why
44. **Thin Report Generator** — Create thin reports with `byPath` reference to shared semantic model
45. ✅ **Theme Migration** — OAC color palette → PBI CY24SU11 theme JSON in `theme_converter.py`
46. ✅ **Mobile Layout** — Phone layout generation (360×640) in `layout_engine.py` — `generate_mobile_layout()`
47. **Calculated Tables** — Support DAX-based calculated tables in TMDL
48. **Calculated Column Classification** — Port T2P's `classify_calculations()`: separate row-level calc columns vs aggregates
49. **Sensitivity Label Auto-Mapping** — Map OAC roles → Purview labels via config dict
