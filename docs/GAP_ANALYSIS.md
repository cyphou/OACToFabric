# Comprehensive Gap Analysis — OAC to Fabric Migration Framework

**Date:** 2026-03-23 — updated through v3.0.0 (Phase 40)  
**Scope:** All source files, test files, agent specs, docs, and cross-project comparison with TableauToPowerBI  
**Status:** 2,108 tests passing across 82 test files · 110 Python source files in src/

---

## Implementation Coverage

```
 DISCOVERY           SCHEMA              ETL                SEMANTIC
+----------------+  +----------------+  +----------------+  +----------------+
| OAC REST API   |  | Oracle→Delta   |  | 16 step types  |  | 60+ OAC→DAX   |
| RPD XML parser |  | Oracle→T-SQL   |  | PL/SQL→PySpark |  | Hierarchy map  |
| Dependency DAG |  | 16 type maps   |  | Schedule→Trig  |  | TMDL generator |
| Complexity scr |  | 14 SQL func map|  | LLM-assisted   |  | LLM fallback   |
| OBIEE/Tab conn |  | Full + Incr    |  | Dataflow parse |  | RPD model parse|
+-------+--------+  +-------+--------+  +-------+--------+  +-------+--------+
        |                    |                    |                    |+

 REPORT              SECURITY            VALIDATION         ORCHESTRATOR
+----------------+  +----------------+  +----------------+  +----------------+
| 21 visual types|  | RLS DAX filter |  | Data reconcile |  | DAG engine     |
| 8 prompt types |  | OLS generation |  | Semantic valid |  | Wave planner   |
| PBIR generator |  | Lookup table   |  | Report visual  |  | CLI + API      |
| Layout engine  |  | Workspace roles|  | Security test  |  | Notifications  |
| Grid→pixel map |  | Session→AAD    |  | Perf benchmark |  | Retry+rollback |
+-------+--------+  +-------+--------+  +-------+--------+  +-------+--------+
        |                    |                    |                    |
        +--------------------+--------------------+--------------------+
                                     |
                     v1.0 → v3.0 (2,108 tests)
                     +-------------------------------+
                     | Multi-source connectors (OAC,  |
                     |   OBIEE, Tableau, Cognos, Qlik)|
                     | React dashboard               |
                     | Plugin architecture            |
                     | Multi-tenant SaaS              |
                     | Incremental migration          |
                     | Rollback & versioning          |
                     | UAT workflow                   |
                     | Delivery packaging             |
                     | Chaos testing                  |
                     +-------------------------------+
```

---

## 1. Discovery Layer (`src/agents/discovery/`)

### What IS implemented
- **OAC REST API crawl**: Paginated catalog discovery (analyses, dashboards, models, prompts, agents, connections, data flows)
- **RPD XML parsing**: Physical, logical, and presentation layers extracted from XUDML/UDML format
- **Dependency graph**: DAG builder with cycle detection and topological sort
- **Complexity scoring**: 6-factor weighted formula (columns, calculations, prompts, pages, RLS, custom visuals)
- **Streaming parser**: Memory-efficient XML parsing for RPD files >50 MB
- **Multi-source connectors**: OAC (full), OBIEE (full), Tableau (full — TWB/TWBX, REST API, 55+ calc→DAX), Essbase (full — REST API, outline parser, 55+ calc→DAX, 24+ MDX→DAX, 22 outline→TMDL), Cognos/Qlik (stubs)

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
- **Error handling in ETL**: No data quality profiling during migration
- **Parameterization**: Environment-specific config (dev/test/prod connection strings) not injected
- **Pipeline monitoring/alerting**: No post-deployment alerting rules generated
- **Complex PL/SQL packages**: Multi-procedure packages with inter-dependency not fully decomposed

### What is APPROXIMATED
- **Job chains**: Sequential pipeline activities — parallel branches not generated
- **Complex DBMS_SCHEDULER expressions**: Converted to basic cron; advanced calendar expressions may lose precision

---

## 4. Semantic Model Layer (`src/agents/semantic/`)

### What IS implemented
- **RPD → TMDL mapping**: 10 concept-level mappings (logical table → TMDL table, etc.)
- **60+ OAC expression → DAX rules**: AGO, TODATE, PERIODROLLING, RANK, RSUM, session variables, etc.
- **Hybrid translation**: Rules-first + LLM fallback with confidence scoring
- **Hierarchies**: Multi-level hierarchy generation with proper TMDL formatting
- **TMDL file generation**: Complete folder structure (model.tmdl, tables/, relationships.tmdl, roles.tmdl, perspectives.tmdl, expressions.tmdl)

### What is MISSING or INCOMPLETE
- **M:N relationships**: Detected but not resolved (requires bridge table generation — flagged for manual review)
- **Calculation groups**: Not implemented (Power BI feature with no direct OAC equivalent)
- **Display folder strategy**: All measures placed in "Measures" folder — no intelligent grouping
- **Incremental model updates**: Full regeneration only; no delta TMDL update
- **Composite models / aggregation tables**: Not generated (all tables use Import mode)
- **Auto-generated Calendar table**: Not implemented (unlike T2P which auto-detects date tables and generates Calendar if missing)

### What is APPROXIMATED
- **Complex nested OAC expressions**: LLM translation with confidence < 0.7 flagged for review
- **INDEXCOL / DESCRIPTOR_IDOF**: Best-effort column key reference mapping

---

## 5. Report Layer (`src/agents/report/`)

### What IS implemented
- **21 OAC visual types** mapped to Power BI visuals
- **8 prompt types** → slicer/parameter configurations
- **Conditional formatting**: Color, data bars, icon sets
- **Layout engine**: OAC grid → 1280×720 pixel canvas conversion
- **Dashboard actions**: Navigate, filter, master-detail → drillthrough, bookmarks
- **PBIR generation**: Complete folder structure (definition.pbir, report.json, pages/, visuals/)

### What is MISSING or INCOMPLETE
- **Custom OAC plugins/extensions**: Flagged as unsupported, no fallback visual
- **Theme migration**: OAC themes not extracted or mapped to PBI themes (uses default CY24SU06 theme)
- **Mobile layouts**: Not generated (OAC responsive → PBI phone layout)
- **Bookmarks beyond actions**: OAC story points not yet converted to PBI bookmarks
- **Pagination**: Reports with 50+ visuals not split across pages
- **Tooltip pages**: Not generated from OAC drill-down configurations
- **Small multiples**: OAC trellis → PBI small multiples mapping incomplete for complex scenarios

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

### What is MISSING or INCOMPLETE
- **Dynamic security**: Complex hierarchy-based row filtering (e.g., manager sees subordinate data)
- **Sensitivity labels**: Not migrated from OAC to PBI/Purview sensitivity labels
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
- **Automated regression detection**: No drift monitoring post-migration (schema drift detection exists in T2P but not here)
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

### What is MISSING or INCOMPLETE
- **Dead letter queue**: No permanent failure sink for tasks that exceed max retries
- **SLA enforcement**: No timeout enforcement per agent (only global retry limits)
- **Manual approval gates**: No human-in-the-loop approval between waves
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
| FAQ | ❌ | ✅ | Create `docs/FAQ.md` |
| API Reference | ❌ | ❌ | Both missing — generate from FastAPI/OpenAPI |
| MAPPING_REFERENCE | ✅ (new) | ✅ | Parity — created |
| KNOWN_LIMITATIONS | ✅ (new) | ✅ | Parity |

---

## 10. Cross-Project Comparison

### Feature Parity with TableauToPowerBI

| Capability | T2P | OAC→Fabric | Notes |
|------------|:---:|:----------:|-------|
| Source extraction | 20 object types | 9 via API + 3 RPD layers | T2P extracts more granularly from XML |
| DAX conversions | 180+ | 60+ (OAC) + 55+ (Tableau connector) | T2P has more formula depth |
| Visual types | 118+ | 21 OAC visual types | T2P maps far more visual types |
| Data connectors (M query) | 42 | N/A (Fabric-native sources) | Different target — OAC uses Spark/Delta, not M |
| Self-healing / auto-fix | Yes (TMDL self-repair, visual fallback) | No | Gap — add self-healing to semantic and report agents |
| Schema drift detection | Yes | No | Gap — add schema drift tracking |
| Shared semantic model | Yes (merge engine) | No | Gap — add multi-model merge for shared reporting |
| Fabric-native output | Yes (Lakehouse+Dataflow+Notebook+DirectLake) | Yes (native target) | Parity |
| DAX optimizer | Yes (AST rewriter) | No | Gap — add DAX optimization post-translation |
| Lineage map | Yes (lineage_map.json) | Dependency graph only | Gap — add full lineage tracking |
| QA suite | Yes (`--qa` flag) | Validation agent exists | Comparable architecture |
| Governance framework | Yes (naming conventions, PII detection) | No | Gap — add governance to security agent |
| Security hardening | Yes (ZIP slip, XXE, credential redaction) | Yes (credit leak detection, Key Vault) | Comparable |
| Docker / containerization | Yes | Yes | Parity |
| REST API | Yes (stdlib http.server) | Yes (FastAPI) | OAC advantage (FastAPI > stdlib) |
| Multi-tenant | Yes | Yes | Parity |
| Incremental migration | Yes (`--sync`) | Yes (`--mode incremental`) | Parity |
| Plugin system | N/A | Yes | OAC advantage |

---

## 11. Priority Improvement Areas

1. **Visual type depth** — Expand from 21 to 40+ visual type mappings (add combo charts, gauge variants, KPI cards, etc.)
2. **DAX translation depth** — Expand from 60+ to 120+ rules (table calcs, window functions, LOD equivalents)
3. **Self-healing pipeline** — Add TMDL self-repair (duplicate tables, broken refs, empty names) and visual fallback cascade
4. **Auto Calendar table** — Detect date tables and auto-generate Calendar table with time intelligence measures
5. **Schema drift detection** — Compare extraction snapshots, detect added/removed/changed objects
6. **DAX optimizer** — Post-translation optimization (IF→SWITCH, COALESCE, constant folding)
7. **Lineage tracking** — Full provenance map: OAC source → Fabric/PBI target for every object
8. **Governance** — Naming convention enforcement, PII detection, sensitivity label mapping
9. **Theme migration** — Extract OAC themes and map to PBI theme JSON
10. **Mobile layout** — Generate phone/tablet layouts from OAC responsive dashboards
