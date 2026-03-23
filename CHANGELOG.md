# Changelog

All notable changes to the OAC-to-Fabric Migration Tool are documented here.

## [Unreleased] — v4.0.0 (Production Dashboard & Multi-Source Maturity)

### Added — Essbase → Semantic Model Bridge

- **Essbase Semantic Bridge** (`src/connectors/essbase_semantic_bridge.py`, 480+ lines):
  - `EssbaseToSemanticModelConverter` — converts `ParsedOutline` → `SemanticModelIR` for TMDL generation
  - Sparse dimensions → dimension tables with Key, Name, Parent, Level, Generation, UDA, Alias columns
  - Dense dimensions → fact table columns
  - Accounts dimension → DAX measures (dynamic calc formulas translated, stored→SUM)
  - Time dimension → date table (`is_date_table=True`) with auto-generated hierarchy
  - Star-schema joins (fact → dimension, MANY_TO_ONE)
  - Essbase filters → RLS role definitions (DAX CONTAINSSTRING expressions)
  - Substitution variables → What-if parameters (DAX VAR syntax)
  - Calc scripts → DAX measures via `EssbaseCalcTranslator` (confidence ≥ 0.5 added as measures)
  - `EssbaseConversionResult` with `ir`, `rls_roles`, `whatif_parameters`, `calc_translations`, `warnings`, `review_items`
  - 53 tests (`tests/test_essbase_semantic_bridge.py`)

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

### Planned — v4.0 (Phases 41–46)
- **Phase 41**: Cognos & Qlik connectors (Report Studio XML, QVF/QVD extraction, expression mapping)
- **Phase 42**: Plugin marketplace with registry, distribution, and sample plugins
- **Phase 43**: Migration analytics Power BI dashboard template
- **Phase 44**: Advanced RPD binary parser for native OBIEE format
- **Phase 45**: AI-assisted schema optimization (partition keys, capacity sizing)
- **Phase 46**: Performance auto-tuning (query analysis, DAX optimization)

### Planned — v5.0 (Phases 47–50)
- **Phase 47**: GraphQL API & Federation — Strawberry GraphQL on FastAPI, real-time subscriptions via WebSocket transport, field-level authorization, query complexity limits, DataLoader for N+1 prevention
- **Phase 48**: Migration Dry-Run Simulator — full agent pipeline simulation in `--dry-run` mode, cost/time/risk estimates per asset, instrumented output collectors, change manifest (JSON/HTML)
- **Phase 49**: Automated Regression Testing — baseline data snapshots at go-live, periodic comparison, report screenshot diffs (SSIM), schema drift detection, notification pipeline integration
- **Phase 50**: Self-Service Migration Portal — multi-org SSO (Azure AD B2C / Entra External ID), drag-and-drop file upload, pre-built migration templates, project management (create/clone/archive), public API with API key auth

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
