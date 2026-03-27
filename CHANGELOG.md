# Changelog

All notable changes to the OAC-to-Fabric Migration Tool are documented here.

## [Unreleased] — v4.2.0 (T2P Parity Completion)

### Added — Phase 48: T2P Parity Completion

**New modules:**

- `src/agents/discovery/lineage_map.py` — Full JSON lineage/dependency graph generator with `LineageNode`, `LineageEdge`, `LineageMap` models, layer classification (physical/logical/presentation/consumption/etl/security), BFS `impact_analysis()` for upstream/downstream traversal, JSON serialization (v1.0 schema)
- `src/agents/semantic/shared_model_merge.py` — Multi-report shared semantic model merge engine with SHA256-based `TableFingerprint`, `jaccard_similarity()`, `find_merge_candidates(threshold=0.7)`, `merge_semantic_models()`, `generate_merge_manifest()`, thin report references for merged models

**Expanded modules:**

- `src/agents/semantic/expression_translator.py` — DAX conversion rules expanded from 60+ to 120+:
  - **Aggregate**: STDDEV→STDEV.S, STDDEV_POP→STDEV.P, VARIANCE→VAR.S, VAR_POP→VAR.P, MEDIAN, PERCENTILE→PERCENTILEX.INC, COUNT(*)→COUNTROWS, COUNTIF→CALCULATE+COUNT, SUMIF→CALCULATE+SUM, FIRST→FIRSTNONBLANK, LAST→LASTNONBLANK
  - **Time Intelligence**: MSUM, RCOUNT, RMAX, RMIN, PARALLELPERIOD, OPENINGBALANCEYEAR, CLOSINGBALANCEYEAR
  - **Scalar**: ABS, ROUND, TRUNC, CEIL→CEILING, FLOOR, POWER, SQRT, LOG→LN, LOG10, EXP, MOD, SIGN, RPAD, LEFT, RIGHT, INITCAP, ASCII→UNICODE, CHR→UNICHAR, DECODE→SWITCH (custom handler), NVL2, COALESCE, NULLIF, GREATEST, LEAST, SYSDATE→NOW, TO_DATE→DATEVALUE, TO_CHAR→FORMAT, TO_NUMBER→VALUE, LAST_DAY→EOMONTH, NEXT_DAY, ROWNUM→RANKX
- `src/agents/semantic/tmdl_self_healing.py` — Self-healing patterns expanded from 6 to 17:
  - New patterns (7–17): missing_sort_by, invalid_format_strings, duplicate_measures, missing_rel_columns, invalid_partition_mode, duplicate_columns, expression_brackets, missing_display_folder, unicode_bom, trailing_whitespace, unreferenced_hidden
- `src/agents/report/visual_mapper.py` — Visual types expanded from 47 to 80+:
  - 35+ new OACChartType entries (percentStackedBar, sunburst, bullet, boxPlot, radar, wordCloud, sankey, chord, gantt, network, card, decomposition, tornado, sparkline, pareto, shapeMap, etc.)
  - 12+ new PBIVisualType custom visual GUIDs (Sparkline, Pareto, FlowMap, Venn, CorrelationPlot, Dumbbell, RotatingChart, SpiderChart, DotPlot, Lollipop, Waffle, KPI_INDICATOR)
  - Mapping table expanded from ~24 to 60+ entries

### Fixed — Phase 48
- `tests/test_fabric_client.py` — Fixed `test_execute_sql_placeholder` hanging on pyodbc import (mocked sys.modules)
- `tests/test_phase16_fabric.py` — Fixed `test_execute_sql_accepts_endpoint` hanging on pyodbc import (mocked sys.modules)
- `src/agents/semantic/expression_translator.py` — Fixed COUNT(*) rule ordering so it matches before generic COUNT

### Testing — Phase 48

**3 new test files, 112 tests:**
- `tests/test_lineage_map.py` — 17 tests: LineageNode, LineageEdge, LineageMap, build_lineage_map, impact_analysis, layer classification, empty maps
- `tests/test_shared_model_merge.py` — 15 tests: TableFingerprint, jaccard similarity, extract_table_fingerprint, find_merge_candidates, merge_semantic_models, generate_merge_manifest
- `tests/test_t2p_parity_phase48.py` — 80 tests: self-healing patterns 7–17, expanded DAX aggregate/time-intel/scalar rules, expanded visual types and mappings

### Documentation — Phase 48
- Updated GAP_ANALYSIS.md: shared semantic model merge and lineage map marked as ✅; DAX rules 60→120+; self-healing 6→17; visual types 47→80+
- Updated CHANGELOG.md with Phase 48 additions

---

## [4.1.0] — v4.1.0 (T2P Gap Implementation + Full Test Coverage)

### Added — Phase 47: T2P Gap Implementation (COMPLETE)

**16 new modules ported from TableauToPowerBI patterns:**

**Discovery (Agent 01)**:
- `src/agents/discovery/portfolio_assessor.py` — 5-axis readiness assessment (expression, filter, connection, security, semantic), effort scoring, GREEN/YELLOW/RED classification, wave planning by effort bands
- `src/agents/discovery/safe_xml.py` — XXE-protected XML parsing, DOCTYPE/ENTITY/SYSTEM rejection, path traversal validation

**Schema (Agent 02)**:
- `src/agents/schema/fabric_naming.py` — Fabric name sanitization: strip brackets, OAC prefix removal (`v_`, `tbl_`, `f_`, `d_`), PascalCase/snake_case conversion
- `src/agents/schema/lakehouse_generator.py` — 3-artifact Lakehouse generation (definition JSON, DDL scripts, metadata JSON), 16+ Oracle→Spark type mappings

**ETL (Agent 03)**:
- `src/agents/etl/fabric_pipeline_generator.py` — 3-stage pipeline orchestration (RefreshDataflow → TridentNotebook → TridentDatasetRefresh), 9 JDBC connector templates (Oracle, PostgreSQL, SQL Server, Snowflake, BigQuery, CSV, Excel, Custom SQL, Databricks)
- `src/agents/etl/incremental_merger.py` — Safe re-migration merge engine with USER_OWNED_FILES preservation and USER_EDITABLE_KEYS (displayName, description, title) protection

**Semantic Model (Agent 04)**:
- `src/agents/semantic/calendar_generator.py` — Auto-detect date columns → 8-column Calendar table + Date Hierarchy + sortByColumn + M query partition + 3 time intelligence DAX measures (YTD, PY, YoY%)
- `src/agents/semantic/dax_optimizer.py` — 5 pre-deployment DAX optimization rules: ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding
- `src/agents/semantic/leak_detector.py` — 22 OAC function leak patterns (NVL, DECODE, SYSDATE, ROWNUM, SUBSTR, VALUEOF, etc.) with auto-fix rules
- `src/agents/semantic/tmdl_self_healing.py` — 6 auto-repair patterns: duplicate table names, broken column refs, orphan measures, empty names, circular relationship Union-Find deactivation, M query try/otherwise wrapping

**Report (Agent 05)**:
- `src/agents/report/visual_fallback.py` — 3-tier visual degradation cascade (complex→simpler→table→card) with per-type cascade map and approximation notes
- `src/agents/report/bookmark_generator.py` — PBI bookmark JSON from OAC story points and saved filter states

**Security (Agent 06)**:
- `src/agents/security/governance_engine.py` — Governance engine: warn/enforce modes, naming conventions, 15 PII regex patterns, 10 credential redaction patterns, sensitivity label mapping, full governance scan

**Validation (Agent 07)**:
- `src/agents/validation/tmdl_validator.py` — TMDL structural validation (required files/dirs/keys, JSON schema, table declarations) + 8-point migration readiness assessment

**Orchestrator (Agent 08)**:
- `src/agents/orchestrator/sla_tracker.py` — SLA compliance evaluation (duration, validation, accuracy) with breach/at-risk/met status + summary reports
- `src/agents/orchestrator/monitoring.py` — 3-backend metrics export: JSON (always), Azure Monitor (Application Insights), Prometheus (push gateway)
- `src/agents/orchestrator/recovery_report.py` — Recovery action tracking: record retries, self-heal actions, manual fixes with severity categorization

**Modified files**:
- `src/agents/semantic/tmdl_generator.py` — Added steps 9-13: database.tmdl generation, compatibility level 1600
- `src/agents/report/visual_mapper.py` — Expanded PBIVisualType 23→47 types, data roles 20→38, added 18+ AppSource custom visual GUIDs

### Testing — Phase 47 (COMPLETE)

**8 new test files, 168 tests:**
- `tests/test_portfolio_assessor.py` — 17 tests: ReadinessLevel, assess_readiness, assess_portfolio, plan_waves, safe_xml parsing, XXE rejection, path validation
- `tests/test_fabric_naming_lakehouse.py` — 27 tests: sanitize_table/column/schema, PascalCase/snake_case, map_to_spark_type, build/generate_ddl/json
- `tests/test_pipeline_merger.py` — 17 tests: PipelineActivity, build_3_stage_pipeline, connectors, generate_notebook_cell, merge_artifacts
- `tests/test_semantic_new_modules.py` — 20 tests: detect_date_columns, generate_calendar, dax_optimizer rules, leak_detector, auto_fix, self_heal
- `tests/test_visual_fallback_bookmarks.py` — 17 tests: resolve_visual_fallback, bookmark model, story points, saved states, JSON generation
- `tests/test_governance_engine.py` — 16 tests: naming checks, PII detection, credential redaction, sensitivity labels, full governance scan
- `tests/test_tmdl_validator.py` — 18 tests: TMDL structural validation, readiness assessment
- `tests/test_sla_monitoring_recovery.py` — 16 tests: SLA evaluation, monitoring export, recovery tracker

### Documentation
- Updated GAP_ANALYSIS.md: 28/49 items marked as ✅ implemented; comparison tables updated to reflect parity
- Updated CHANGELOG.md with all Phase 47 additions

---

## [4.0.0] — v4.0.0 (Production Dashboard & Multi-Source Maturity)

### Added — Phase 41: Cognos & Qlik Connectors (COMPLETE)

**IBM Cognos Analytics Connector** (`src/connectors/cognos_connector.py`, 650+ lines)
- `CognosReportSpecParser` — XML parser for Cognos report specs (queries, prompts, visualizations, filters)
- `CognosExpressionTranslator` — 50+ Cognos→DAX rule catalog, 57 regex patterns, confidence scoring
- `CognosRestClient` — async REST API client (v11.1+) with overridable HTTP for testing
- `FullCognosConnector` — full `SourceConnector` lifecycle (connect, discover, extract, disconnect)
- Mappings: 11 source types, 8 data types, 15 visual types, 8 prompt types, 21 TMDL concepts
- `CognosToSemanticModelConverter` (`cognos_semantic_bridge.py`) — ParsedReportSpec → SemanticModelIR
- 70 tests (`test_cognos_connector.py`)

**Qlik Sense / QlikView Connector** (`src/connectors/qlik_connector.py`, 700+ lines)
- `QlikLoadScriptParser` — parses LOAD, SQL SELECT, LET/SET, CONNECT statements
- `QlikExpressionTranslator` — 72+ Qlik→DAX rules, set analysis→CALCULATE patterns
- `QlikEngineClient` — async Engine API client with overridable HTTP for testing
- `FullQlikConnector` — full `SourceConnector` lifecycle
- Mappings: 14 source types, 7 data types, 18 visual types, 22 TMDL concepts
- `QlikToSemanticModelConverter` (`qlik_semantic_bridge.py`) — QlikApp → SemanticModelIR
  - Tables → LogicalTable, measures → DAX, drill-down dims → hierarchies, variables → What-if params
  - Field associations → inferred joins (Qlik associative model)
- 85 tests (`test_qlik_connector.py`)

**Infrastructure updates**
- `base_connector.py` — replaced inline Cognos/Qlik stubs with lazy-import proxy pattern
- `test_phase26_connectors.py` — updated from stub assertions to full connector assertions

### Added — Phase 42: Plugin Marketplace (COMPLETE)

- **Plugin Registry** (`src/plugins/marketplace.py`) — `PluginRegistry` with JSON-backed index, search by name/tags, publish/unpublish
- **Plugin Installer** — install from registry entry or manifest, uninstall with cleanup
- **CLI helpers** — `cmd_plugin_list`, `cmd_plugin_install`, `cmd_plugin_publish`
- **Sample plugin: Visual Mapping Overrides** — override OAC→PBI visual type mappings via POST_TRANSLATE hook
- **Sample plugin: Data Quality Checks** — null ratio threshold, row count variance, PRE/POST_VALIDATE hooks
- `load_builtin_plugins()` convenience for auto-registration
- 48 tests (`test_plugin_marketplace.py`)

### Added — Phase 43: Migration Analytics Dashboard (COMPLETE)

- **Metrics models** (`src/plugins/analytics_dashboard.py`) — `AgentMetrics`, `WaveMetrics`, `CostMetrics`, `MigrationMetrics` with computed properties
- **MetricsCollector** — create snapshots, add waves, update agents, compute totals
- **DashboardDataExporter** — export to JSON + agent CSV + wave CSV
- **PBITTemplateGenerator** — 5-page Power BI template manifest (Executive Summary, Wave Progress, Agent Details, Cost Analysis, Validation)
- **ExecutiveSummary** — computed from metrics with risk detection (failures, critical issues, budget)
- 31 tests (`test_analytics_dashboard.py`)

### Added — Phase 44: Advanced RPD Binary Parser (COMPLETE)

- **Binary RPD parser** (`src/core/rpd_binary_parser.py`) — `RPDBinaryParser` supporting OBIEE 10g/11g/12c binary format
- Header parsing (magic, version, section count, RPD name)
- Section parsing (7 types: physical, logical, presentation, security, init blocks, connections, variables)
- Object parsing (12 types: table, column, join, measure, hierarchy, level, role, permission, init block, connection, variable, subject area)
- Property decoding (TLV key-value format)
- **LargeFileStreamingParser** — memory-efficient streaming for >500 MB files (4 MB chunks)
- **RPDBinaryToXMLConverter** — convert binary RPD to XML for compatibility with existing parsers
- **build_test_rpd_binary()** — synthetic binary RPD generator for testing
- 38 tests (`test_rpd_binary_parser.py`)

### Added — Phase 45: AI-Assisted Schema Optimization (COMPLETE)

- **Schema Optimizer** (`src/core/schema_optimizer.py`) — orchestrates all optimization engines
- **PartitionKeyRecommender** — cardinality-based scoring, filter-column bonus from workload, HPK recommendation for >20 GB tables
- **StorageModeAdvisor** — Direct Lake / Import / Dual mode heuristics based on data size and workload mix
- **CapacitySizer** — F2–F1024 SKU selection with headroom and workload scaling factors
- Models: `ColumnProfile`, `TableProfile`, `SchemaProfile`, `WorkloadPattern`, `OptimizationRecommendation`, `OptimizationReport`
- Column pruning (>100 cols warning), data type optimization (low-cardinality string detection)
- 27 tests (`test_schema_optimizer.py`)

### Added — Phase 46: Performance Auto-Tuning (COMPLETE)

- **PerformanceAutoTuner** (`src/core/perf_auto_tuner.py`) — orchestrates all performance tuning
- **PerformanceAnalyzer** — categorize queries (fast/normal/slow/critical), SE/FE ratio, P95 latency, hot tables
- **DAXOptimizer** — 6 anti-pattern detections: SUMX→SUM, AVERAGEX→AVERAGE, ISBLANK→COALESCE, deep nesting, bidirectional relationships, FILTER(ALL()) patterns
- **AggregationAdvisor** — scan-based aggregation table suggestions for slow queries with high row scans
- **CompositeModelAdvisor** — automatic DL/Import/Dual table assignment (writeback, row count, query frequency)
- Models: `QueryProfile`, `DAXMeasureProfile`, `DAXOptimization`, `AggregationTableSpec`, `CompositeModelPattern`, `PerformanceTuningReport`
- 39 tests (`test_perf_auto_tuner.py`)

### Testing
- **324 new tests** across all phases
- Full suite: **2,618 passed** (2 skipped), ~12 seconds
- v4.0 target of ≥2,500 tests exceeded ✅

### Added — Phase 39: React Dashboard (2026-03-23)

**Dashboard Application**
- React 18 + Vite + TypeScript SPA in `dashboard/`
- TanStack Query for server-state management with auto-refetch
- React Router v7 for client-side routing
- Recharts for data visualization (pie charts)
- Lucide React icons

**Pages & Components**
- Migration list with status icons, progress bars, and links to detail view
- Migration detail page with stat cards, pie chart breakdown, agent status table, log stream, and metadata
- 3-step migration wizard: Source → Configure → Review & Launch
- Inventory browser with search, type/complexity/status filters, and sortable columns
- Sidebar layout with navigation, health badge, and dark mode toggle

**Real-Time Features**
- WebSocket hook for live migration events
- Server-Sent Events (SSE) hook for log streaming
- Health endpoint polling every 30s

**Dark Mode**
- Full light/dark theme via CSS custom properties and `[data-theme]` attribute
- System preference detection (`prefers-color-scheme`)
- Persisted to `localStorage`

**Developer Experience**
- Vite dev server with API proxy (`/api` → backend, `/ws` → WebSocket)
- TypeScript strict mode, zero type errors
- Production build generates optimized bundle

**Testing**
- 121 new tests in `test_phase39_dashboard.py`
- Project structure, dependency, config, type alignment, component content validation
- Total: 1,992 tests (up from 1,871)

### Added — Phase 40: Tableau Connector (2026-03-24)

**TWB/TWBX Parser**
- `TableauWorkbookParser` — parse .twb XML and .twbx zip archives
- Extracts datasources, connection info, tables, columns, calculated fields
- Extracts worksheets (mark types, filters, column references)
- Extracts dashboards (size, worksheet zones)
- Parameter extraction from special "Parameters" datasource

**Calculated Field → DAX Translator**
- `TableauCalcTranslator` with 55+ rule-based regex translations
- Coverage: aggregates, string, date, logical, math, type conversion
- Flags unsupported patterns: LOD expressions (FIXED/INCLUDE/EXCLUDE), table calcs (RUNNING_SUM, INDEX, etc.)
- Confidence scoring per translation (1.0 = direct, 0.5 = complex, 0.2 = unsupported)

**REST API Client**
- `TableauRestClient` — async client for Tableau Server/Cloud REST API (v3.21)
- Personal Access Token and username/password authentication
- List workbooks, datasources, views with pagination
- Download workbook content (.twbx)
- Overridable HTTP transport for testing

**Data Source Mapping**
- `map_connection_type()` — 11 Tableau connection types → Fabric targets
- `map_data_type()` — 6 Tableau types → Fabric/Power BI column types

**Full SourceConnector**
- `FullTableauConnector` replaces Phase 26 stub (`is_stub=False`, version 1.0.0)
- Connects via REST API, discovers workbooks/datasources/views
- Downloads & parses workbooks, translates calc fields, maps data sources
- Integrated into `build_default_registry()`

**Testing**
- 116 new tests in `test_phase40_tableau.py`
- Updated `test_phase26_connectors.py` (stub → full connector assertion)
- Total: 2,108 tests (up from 1,992)

### v4.0 Phases 41–46: COMPLETE ✅

All v4.0 phases are now implemented and tested. See individual sections above.

### Planned — v5.0 (Phases 48–51)
- **Phase 48**: GraphQL API & Federation — Strawberry GraphQL on FastAPI, real-time subscriptions via WebSocket transport, field-level authorization, query complexity limits, DataLoader for N+1 prevention
- **Phase 49**: Migration Dry-Run Simulator — full agent pipeline simulation in `--dry-run` mode, cost/time/risk estimates per asset, instrumented output collectors, change manifest (JSON/HTML)
- **Phase 50**: Automated Regression Testing — baseline data snapshots at go-live, periodic comparison, report screenshot diffs (SSIM), schema drift detection, notification pipeline integration
- **Phase 51**: Self-Service Migration Portal — multi-org SSO (Azure AD B2C / Entra External ID), drag-and-drop file upload, pre-built migration templates, project management (create/clone/archive), public API with API key auth

### Fixed (Documentation — 2026-03-23)
- Corrected CLI description across all docs: `argparse`-based (was incorrectly listed as Typer/Click)
- Removed non-existent `dashboard/` directory from README.md project structure
- Added missing `src/` directories to README.md and CONTRIBUTING.md (connectors, plugins, testing, validation, api)
- Updated `pyproject.toml` version from `0.1.0` to `3.0.0`
- Added framework readiness table and v4.0 roadmap to PROJECT_PLAN.md
- Updated DEV_PLAN.md technology stack (CLI, Web API entries)

## [3.0.0] — 2025-09-15

### Added — Field-Proven Delivery (Phases 31–38)

**E2E Integration Testing (Phase 31)**
- Golden fixture generator and `IntegrationTestHarness`
- `OutputComparator` for deterministic end-to-end validation
- 30+ integration test scenarios covering incremental sync and rollback

**Documentation & Project Hygiene (Phase 32)**
- `DocValidator` for automated documentation freshness checks
- `ChangelogGenerator` and `ProjectHealthCheck` utilities
- `CIWorkflowGenerator` for GitHub Actions pipeline scaffolding

**Data Pipeline Execution (Phase 33)**
- `PipelineDeployer` for Fabric Data Factory pipeline deployment
- `DataCopyOrchestrator` with partition strategies and watermark tracking
- `PipelineMonitor` and `LandingZoneManager`

**DAX Translation Maturity (Phase 34)**
- `TranslationCatalog` with 80+ DAX function mappings (up from ~30)
- Time intelligence, level-based measures, advanced string/math functions
- `ConfidenceCalibrator` for translation quality scoring

**Migration Intelligence (Phase 35)**
- `ComplexityAnalyzer` for pre-migration asset complexity scoring
- `CostEstimator` and `TimelineEstimator` for project planning
- `PreflightChecker` and `RiskScorer` for migration readiness assessment

**UAT Workflow (Phase 36)**
- `UATSession` and `UATWorkflow` state machine (draft → active → review → signed-off)
- `ComparisonSpec`, `SignOffTracker`, `DefectLog`, and `UATReport`

**Customer Delivery Package (Phase 37)**
- `DeliveryPackage` with `AssetCatalog` and `ChangeDocGenerator`
- `TrainingContentGen`, `KnownIssueTracker`, `HandoverChecklist`

**Production Hardening v3 (Phase 38)**
- `ChaosSimulator` and `RecoveryVerifier` for resilience testing
- `SecurityScanner` and `ReleaseValidator`
- `PerformanceBaseline` for regression detection

### Testing
- 1,871 automated tests (2 skipped for FastAPI), up from 1,508

---

## [2.0.0] — 2025-07-28

### Added — Enterprise Platform (Phases 23–30)

**Web API & Dashboard (Phase 23)**
- FastAPI backend with REST endpoints (`POST /migrations`, `GET /migrations/{id}`)
- WebSocket and SSE real-time event streaming
- API endpoints designed for React + Vite dashboard (frontend implementation deferred to Phase 39)

**Containerization (Phase 24)**
- Multi-stage Dockerfile (Python 3.11+ slim)
- Docker Compose stack (API + dashboard + PostgreSQL)
- Bicep IaC for Azure Container Apps with managed identity
- Helm chart for AKS deployment
- Trivy container scanning in CI/CD

**Incremental & Delta Migration (Phase 25)**
- `ChangeDetector` with RPD diff and catalog `lastModified` tracking
- `SyncJournal` for migration state tracking
- `--mode incremental` CLI flag with per-agent `execute_incremental()`
- `SyncScheduler` (cron/interval) with conflict resolution

**Multi-Source Connectors (Phase 26)**
- `SourceConnector` abstract base class and connector registry
- OBIEE connector (RPD binary + web catalog)
- Tableau, Cognos, and Qlik connector stubs
- `--source` CLI flag for source platform selection

**AI Visual Validation (Phase 27)**
- Playwright screenshot capture (OAC + PBI, multiple viewports)
- GPT-4o visual comparison with structured JSON diff and similarity scoring
- SSIM pixel-level fallback validation
- Dashboard side-by-side viewer and PDF validation reports

**Plugin Architecture (Phase 28)**
- `PluginManager` with discover/load/validate lifecycle
- `plugin.toml` manifest format and lifecycle hooks (pre/post discover/translate/deploy)
- Plugin isolation and sandboxing with resource limits
- Custom YAML translation rules with hot-reload
- Plugin CLI commands

**Multi-Tenant SaaS (Phase 29)**
- Tenant model with context middleware for request-scoped isolation
- Tenant-scoped storage, secrets, and telemetry
- Azure AD / Entra ID SSO integration
- RBAC (admin/operator/viewer) with JWT auth middleware and API keys
- Metering (assets/tokens/API calls per tenant) and rate limiting (SlowAPI)
- Admin dashboard and tenant onboarding API

**Rollback & Versioning (Phase 30)**
- `ArtifactVersioner` with timestamped + SHA-256 content-addressable snapshots
- Diff viewer for artifact comparison
- `RollbackEngine` with reverse action replay
- Per-agent rollback support, CLI `rollback` command, and API rollback endpoint

### Testing
- 1,508 automated tests (2 skipped for FastAPI), up from 1,243

---

## [1.0.0] — 2025-07-09

### Added — GA Release

**Core Architecture**
- 8-agent DAG orchestration (Discovery → Schema → ETL → Semantic → Report → Security → Validation → Orchestrator)
- Lakehouse-based agent coordination via Delta tables
- CLI entry point (`python -m src.cli.main`) with `migrate`, `discover`, `validate`, `status` commands
- Checkpoint/resume support with `--resume` flag
- Selective agent execution with `--agents` flag

**Agent Implementations**
- **Agent 01 — Discovery**: OAC catalog crawl, RPD XML parsing (standard + streaming), dependency graph, complexity scoring
- **Agent 02 — Schema**: Oracle → Fabric type mapping, DDL generation, lakehouse table creation
- **Agent 03 — ETL**: PL/SQL → PySpark translation (rule-based + LLM), data pipeline generation, scheduling
- **Agent 04 — Semantic Model**: OAC RPD → Power BI TMDL conversion (tables, relationships, measures, hierarchies)
- **Agent 05 — Report**: OAC analyses/dashboards → Power BI PBIR reports, visual mapping, slicer conversion
- **Agent 06 — Security**: OAC roles → PBI RLS/OLS, AAD group mapping, workspace role assignment
- **Agent 07 — Validation**: Data reconciliation, metric comparison, visual verification
- **Agent 08 — Orchestrator**: DAG execution, wave planning, retry logic, notification dispatch

**Translation Engine**
- PL/SQL patterns: INSERT SELECT, UPDATE SET, DELETE FROM, MERGE INTO, CURSOR LOOP, EXECUTE IMMEDIATE, FORALL, BULK COLLECT, FOR numeric loop, WHILE loop, RAISE_APPLICATION_ERROR, exception blocks
- OAC expression → DAX: 30+ function mappings (aggregates, time intelligence, string, date, EXTRACT, CASE, CAST)
- LLM-assisted fallback via Azure OpenAI GPT-4 for complex expressions
- Confidence scoring with manual review flagging

**Deployment**
- Fabric Lakehouse DDL deployment (5 coordination tables)
- Power BI semantic model deployment via TMDL (Tabular Editor + REST + PBIX import fallback)
- PBIR report deployment
- RLS/OLS configuration
- Dry-run mode with performance baselining

**Observability**
- Structured telemetry (events, metrics, spans) with correlation IDs
- Application Insights exporter
- OTLP compatibility layer (OpenTelemetry Protocol)
- Notification channels: Teams webhook, email (Azure Communication Services), PagerDuty Events API v2

**Security**
- Azure Key Vault integration for secret management
- Managed identity authentication support
- Credential scanner for source code and config audit
- SecretValue redaction in logs

**Infrastructure**
- Bicep IaC templates (App Insights, Key Vault, OpenAI, Fabric workspace)
- CI/CD pipeline support via Fabric Git integration

### Testing
- 1,200+ automated tests
- Unit, integration, and regression test suites
- Phase-by-phase test organization (Phases 0–22)

---

## [0.9.0] — Phase 20 (Advanced Translation)

### Added
- Complex PL/SQL patterns (FOR loop, WHILE loop, RAISE, EXECUTE IMMEDIATE USING)
- OAC string functions (SUBSTRING, UPPER, LOWER, TRIM, REPLACE, LENGTH, INSTR, LPAD)
- OAC date functions (TIMESTAMPADD, TIMESTAMPDIFF, CURRENT_DATE, ADD_MONTHS, EXTRACT)
- Edge case handling for untranslatable patterns

## [0.8.0] — Phase 19 (Live Deployment)

### Added
- Coordination table DDL deployment
- PBIR report deployment
- OLS (Object-Level Security) support
- End-to-end dry-run migration with performance baseline

## [0.7.0] — Phase 18 (OAC Validation)

### Added
- Live OAC connection validation
- RPD streaming parser for large files
- Real-world RPD fixture generation

## [0.6.0] — Phase 17 (Agent Wiring)

### Added
- Agent registry and runner factory
- State coordinator with lifecycle hooks
- CLI end-to-end verification

## [0.5.0] — Phase 16 (Stub Elimination)

### Added
- Real Fabric SQL execution (pyodbc)
- Real PBI deployment (TMDL + REST)
- Graph API group resolution
- OAC authentication (IDCS OAuth2)

## [0.1.0–0.4.0] — Phases 0–15

### Added
- Initial project scaffolding and architecture
- Core data models and abstractions
- Type mapping engine
- Wave planner
- All 8 agent stubs with full interface contracts
- Test framework with 942 tests
