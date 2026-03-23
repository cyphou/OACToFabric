# Migration Project — Task Tracking

## Current Status
- **Phases 0–40 complete** (v3.0.0 + Phases 39–40 — 2,108 tests passing, 2 skipped)
- **v4.0 in progress** (Phases 39–40 done, Phases 41–46 planned)
- **v5.0 planned** (Phases 47–50 — GraphQL, Dry-Run Simulator, Regression Testing, Self-Service Portal)

---

## v4.0 — Next Development Phases

### Phase 39: React Dashboard ✅
- [x] Scaffold React 18 + Vite project in `dashboard/`
- [x] Migration wizard (step-by-step guided workflow)
- [x] Inventory browser with filtering/search
- [x] Real-time log streaming (WebSocket + SSE)
- [x] Migration list and detail pages
- [x] Dark mode support
- [x] 121 tests in `test_phase39_dashboard.py`

### Phase 40: Tableau Connector ✅
- [x] TWB/TWBX XML parser (`TableauWorkbookParser`)
- [x] Tableau REST API client (`TableauRestClient` — PAT & password auth)
- [x] Calculated field → DAX translation (`TableauCalcTranslator` — 55+ rules)
- [x] Data source mapping to Fabric (11 connection types, 6 data types)
- [x] Full `SourceConnector` implementation replacing Phase 26 stub
- [x] 116 tests in `test_phase40_tableau.py`

### Phase 41: Cognos & Qlik Connectors
- [ ] Cognos Report Studio XML parser
- [ ] Cognos REST API client
- [ ] Qlik QVF/QVD file extraction
- [ ] Qlik Engine API client
- [ ] Expression mapping (Cognos/Qlik → DAX)

### Phase 42: Plugin Marketplace
- [ ] Plugin registry index and discovery
- [ ] CLI `plugin install` / `plugin publish` commands
- [ ] Sample plugin: custom visual mapping overrides
- [ ] Sample plugin: data quality checks
- [ ] Plugin documentation and contributor guide

### Phase 43: Migration Analytics Dashboard
- [ ] Power BI dashboard template (.pbit)
- [ ] Auto-refresh dataset from Lakehouse coordination tables
- [ ] Migration progress visuals (wave/agent)
- [ ] Cost burn-down and timeline forecast
- [ ] Executive summary page

### Phase 44: Advanced RPD Binary Parser
- [ ] RPD binary format reverse-engineering
- [ ] Streaming parser for large files (>500 MB)
- [ ] Physical/business/presentation layer extraction
- [ ] Integration with OBIEE connector

### Phase 45: AI-Assisted Schema Optimization
- [ ] Query workload pattern analysis
- [ ] Hierarchical partition key recommendations
- [ ] Direct Lake vs. import mode recommendations
- [ ] Fabric capacity sizing estimates

### Phase 46: Performance Auto-Tuning
- [ ] Post-migration query performance analysis
- [ ] DAX measure optimization recommendations
- [ ] Aggregation table suggestions
- [ ] Composite model pattern recommendations

---

## v5.0 — Platform & Enterprise (Phases 47–50)

### Phase 47: GraphQL API & Federation
- [ ] Strawberry GraphQL schema over FastAPI (`/graphql` endpoint)
- [ ] Real-time subscriptions via WebSocket transport (migration events)
- [ ] Field-level authorization (admin/operator/viewer)
- [ ] Query complexity & depth limits to prevent abuse
- [ ] DataLoader pattern for N+1 prevention
- [ ] REST + GraphQL coexistence (shared service layer)

### Phase 48: Migration Dry-Run Simulator
- [ ] `--dry-run` flag on all agent `execute()` methods
- [ ] Instrumented output collectors (capture without writing to target)
- [ ] Cost estimate from data volume + pipeline count
- [ ] Risk score per asset (complexity, unsupported features)
- [ ] Change manifest output (JSON + HTML report)
- [ ] Time estimate calibrated from historical migrations

### Phase 49: Automated Regression Testing
- [ ] Baseline data snapshots at go-live (row counts, checksums, sample rows)
- [ ] Periodic comparison job (daily/weekly)
- [ ] Report screenshot baselines with SSIM / GPT-4o visual diff
- [ ] Schema drift detection (column additions/removals/type changes)
- [ ] Notification pipeline integration (Teams, email, PagerDuty)
- [ ] Regression dashboard in React UI

### Phase 50: Self-Service Migration Portal
- [ ] Multi-org SSO (Azure AD B2C / Entra External ID)
- [ ] Drag-and-drop file upload (TWB, RPD, Cognos XML)
- [ ] Pre-built migration templates (quick-start configurations)
- [ ] Project management (create / clone / archive migrations)
- [ ] Public API with API key authentication
- [ ] Usage analytics & billing metering

---

## Completed Phases

- [x] Phase 0–8: Core agents (Discovery, Schema, ETL, Semantic, Report, Security, Validation, Orchestrator)
- [x] Phase 9: Integration Tests & CLI
- [x] Phase 10: Live OAC API Integration
- [x] Phase 11: Fabric & PBI API Integration
- [x] Phase 12: LLM Translation (hybrid rules-first, LLM-fallback)
- [x] Phase 13: CI/CD Pipeline
- [x] Phase 14: Monitoring & Observability (telemetry, runbooks)
- [x] Phase 15: Production Hardening (checkpoint, streaming parser, graceful shutdown, resilience, docs)
- [x] Phase 16–22: Live validation, advanced translation, operational readiness, v1.0 GA release
- [x] Phase 23–30: Web API, containerization, incremental sync, multi-source, plugins, multi-tenant, rollback, v2.0 release
- [x] Phase 31–38: E2E testing, DAX maturity, migration intelligence, UAT workflow, delivery package, v3.0 release

See [DEV_PLAN.md](../DEV_PLAN.md) for the complete consolidated development plan.

---

## Documentation Accuracy Fixes (2026-03-23)

- [x] Fixed README.md: removed non-existent `dashboard/` reference, corrected CLI description (argparse not Typer), added missing `src/` directories
- [x] Fixed CONTRIBUTING.md: corrected CLI description, added missing directories (connectors, plugins, testing, validation, api)
- [x] Updated PROJECT_PLAN.md: added v3.0 status banner, framework readiness table, v4.0 roadmap section, corrected tech stack
- [x] Updated DEV_PLAN.md: added v4.0 phases (39–46), updated release timeline, fixed CLI reference
- [x] Fixed pyproject.toml: version updated to 3.0.0

---

## Review Notes

_Add review findings here after each session._
