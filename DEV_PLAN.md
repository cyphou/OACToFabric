# Development Plan — OAC to Fabric & Power BI Migration Platform

> **Status**: v1.0–v4.1 COMPLETE (47 phases)  
> **Tests**: 2,784 passing (2 skipped)  
> **Latest Release**: v4.1.0 — T2P Gap Implementation + Full Test Coverage  
> **Current Milestone**: v5.0.0 — Intelligent Platform (Phases 48–50)  
> **Next Milestone**: v5.0.0 GA — Phases 48–50

---

## Table of Contents

- [Release Timeline](#release-timeline)
- [Phase Summary](#phase-summary)
- [v1.0 — Core Migration Framework (Phases 0–22)](#v10--core-migration-framework-phases-022)
- [v2.0 — Enterprise Platform (Phases 23–30)](#v20--enterprise-platform-phases-2330)
- [v3.0 — Field-Proven Delivery (Phases 31–38)](#v30--field-proven-delivery-phases-3138)
- [v4.0 — Production Dashboard & Multi-Source Maturity (Phases 39–46)](#v40--production-dashboard--multi-source-maturity-phases-3946)
- [Architecture Evolution](#architecture-evolution)
- [Technology Stack](#technology-stack)
- [Development Environment](#development-environment)
- [Sprint Cadence](#sprint-cadence)
- [Team Structure](#team-structure)
- [Risk Register](#risk-register)
- [Success Metrics](#success-metrics)

---

## Release Timeline

| Milestone | Phases | Tests | Weeks | Status |
|-----------|--------|-------|-------|--------|
| **v1.0 GA** | 0–22 | 1,243 | 1–42 | ✅ Complete |
| **v2.0 Enterprise** | 23–30 | 1,508 | 43–62 | ✅ Complete |
| **v3.0 Field-Proven** | 31–38 | 1,871 | 63–78 | ✅ Complete |
| **v4.0 Dashboard & Multi-Source** | 39–46 | 2,618 | 79–98 | ✅ Complete |
| **v4.1 T2P Gap Implementation** | 47 | 2,784 | 99 | ✅ Complete |
| **v5.0 Intelligent Platform** | 48–50 | 2,900+ | 100–110 | 🟡 In Progress |

---

## Phase Summary

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 0 | Foundation & Infrastructure | ✅ | Agent framework, `MigrationAgent` base class, Lakehouse client, logging |
| 1 | Discovery Agent | ✅ | OAC API client, RPD XML parser, dependency graph, inventory |
| 2 | Schema & Data Migration Agent | ✅ | Oracle→Fabric type mapping, DDL generation, Data Factory pipelines |
| 3 | ETL Migration Agent | ✅ | Data flow parsing, pattern catalog, PL/SQL→PySpark notebooks |
| 4 | Semantic Model Agent | ✅ | RPD→TMDL conversion, OAC expression→DAX, hierarchy generation |
| 5 | Report & Dashboard Agent | ✅ | Visual mapping, PBIR generation, layout engine, screenshot comparison |
| 6 | Security Agent | ✅ | Role extraction, RLS/OLS migration, session variable→AAD mapping |
| 7 | Validation Agent | ✅ | Data reconciliation, semantic model validation, visual regression |
| 8 | Cutover & Hypercare | ✅ | Final sync, user access switch, monitoring, runbooks |
| 9 | Integration Tests & CLI | ✅ | Typer CLI, `--dry-run`/`--wave`/`--config` flags, integration test framework |
| 10 | Live OAC API | ✅ | OAuth2/IDCS auth, real OAC catalog/dataflow clients, VCR cassettes |
| 11 | Fabric & PBI API | ✅ | Real LakehouseClient, XMLA endpoint, PBI REST, workspace roles |
| 12 | LLM-Assisted Translation | ✅ | Azure OpenAI wrapper, prompt templates, confidence scorer, guardrails |
| 13 | CI/CD | ✅ | GitHub Actions, CD pipeline, Fabric Git integration, Terraform/Bicep IaC |
| 14 | Monitoring & Observability | ✅ | App Insights, distributed tracing, PBI dashboard, alerting |
| 15 | Production Hardening | ✅ | Performance optimization, resilience, documentation, Sphinx/MkDocs |
| 16 | Stub Elimination | ✅ | Real Fabric SQL (pyodbc), real TMDL deployment (XMLA), AAD Graph API |
| 17 | Agent Wiring | ✅ | `AgentRegistry`, `RunnerFactory`, state coordination, CLI `--resume` |
| 18 | Live OAC Validation | ✅ | Real OAC connection, RPD parser against production data, anonymized fixtures |
| 19 | Live Fabric/PBI Deployment | ✅ | Real Lakehouse deployment, TMDL to workspace, PBIR reports, RLS/OLS verify |
| 20 | Advanced Translation | ✅ | Complex PL/SQL (FOR, CURSOR, BULK COLLECT), advanced OAC expressions |
| 21 | Operational Readiness | ✅ | Teams/email/PagerDuty notifications, Key Vault, security scans |
| 22 | Performance & GA | ✅ | Benchmarking, 10K-asset load test, v1.0.0 release |
| 23 | Web API & Dashboard | ✅ | FastAPI backend, WebSocket/SSE, REST endpoints (React frontend deferred to Phase 39) |
| 24 | Containerization | ✅ | Multi-stage Dockerfile, Docker Compose, Bicep for Azure Container Apps, Helm |
| 25 | Incremental & Delta Migration | ✅ | `ChangeDetector`, `SyncJournal`, `--mode incremental`, conflict resolution |
| 26 | Multi-Source Connectors | ✅ | `SourceConnector` ABC, OBIEE connector, Tableau/Cognos/Qlik stubs |
| 27 | AI Visual Validation | ✅ | Playwright screenshots, GPT-4o comparison, SSIM fallback, PDF report |
| 28 | Plugin Architecture | ✅ | `PluginManager`, `plugin.toml`, lifecycle hooks, plugin isolation |
| 29 | Multi-Tenant SaaS | ✅ | Tenant model, Azure AD SSO, RBAC, JWT auth, metering, rate limiting |
| 30 | Rollback & Versioning | ✅ | `ArtifactVersioner`, `RollbackEngine`, diff viewer, v2.0 release |
| 31 | E2E Integration Testing | ✅ | Golden fixtures, `IntegrationTestHarness`, `OutputComparator` |
| 32 | Documentation & Hygiene | ✅ | `DocValidator`, `ChangelogGenerator`, `ProjectHealthCheck` |
| 33 | Data Pipeline Execution | ✅ | `PipelineDeployer`, `DataCopyOrchestrator`, `PipelineMonitor` |
| 34 | DAX Translation Maturity | ✅ | `TranslationCatalog`, 80+ DAX mappings, `ConfidenceCalibrator` |
| 35 | Migration Intelligence | ✅ | `ComplexityAnalyzer`, `CostEstimator`, `PreflightChecker` |
| 36 | UAT Workflow | ✅ | `UATSession`, state machine, `SignOffTracker`, `DefectLog` |
| 37 | Customer Delivery Package | ✅ | `DeliveryPackage`, `AssetCatalog`, `HandoverChecklist` |
| 38 | Production Hardening v3 | ✅ | `ChaosSimulator`, `SecurityScanner`, `ReleaseValidator`, v3.0 release |
| 39 | React Dashboard | ✅ | React 18 + Vite + TanStack Query, migration wizard, inventory browser, real-time streaming, dark mode |
| 40 | Tableau Connector | ✅ | TWB/TWBX parser, REST API client, 55+ calc→DAX rules, data source mapping, full `SourceConnector` |
| 41 | Cognos & Qlik Connectors | ✅ | CognosReportSpecParser, QlikLoadScriptParser, expression→DAX, semantic bridges |
| 42 | Plugin Marketplace | ✅ | PluginRegistry, CLI install/publish, sample plugins |
| 43 | Migration Analytics Dashboard | ✅ | MetricsCollector, DashboardDataExporter, PBI template |
| 44 | Advanced RPD Binary Parser | ✅ | RPDBinaryParser (10g/11g/12c), streaming, XML converter |
| 45 | AI-Assisted Schema Optimization | ✅ | PartitionKeyRecommender, StorageModeAdvisor, CapacitySizer |
| 46 | Performance Auto-Tuning | ✅ | PerformanceAnalyzer, DAXOptimizer, AggregationAdvisor |
| 47 | T2P Gap Implementation | ✅ | 16 new modules, 47 visual types, calendar gen, self-healing, DAX optimizer, governance, SLA tracker |

---

## v1.0 — Core Migration Framework (Phases 0–22)

### Phases 0–8: Agent Framework & Core Implementation (664 tests)

**Goal**: Build the 8-agent migration engine from foundation to cutover.

| Phase | Weeks | Focus | Key Source Files |
|-------|-------|-------|-----------------|
| 0 | 1–2 | Infrastructure, agent base class, Lakehouse client | `src/core/models.py`, `src/core/base_agent.py`, `src/core/config.py` |
| 1 | 2–3 | OAC discovery, RPD XML parsing, dependency graph | `src/agents/discovery/`, `src/clients/oac_client.py` |
| 2 | 3–5 | Oracle→Fabric type mapping, DDL generation | `src/agents/schema/`, `src/core/type_mapper.py` |
| 3 | 5–7 | Data flow parsing, PL/SQL→PySpark translation | `src/agents/etl/`, `src/core/plsql_translator.py` |
| 4 | 5–8 | OAC RPD→TMDL, expression→DAX conversion | `src/agents/semantic/`, `src/core/dax_translator.py` |
| 5 | 7–11 | Visual mapping, PBIR generation, layout engine | `src/agents/report/`, `src/core/pbir_generator.py` |
| 6 | 9–12 | Role extraction, RLS/OLS, AAD mapping | `src/agents/security/` |
| 7 | 11–14 | Data reconciliation, visual regression, UAT | `src/agents/validation/` |
| 8 | 14–16 | Final sync, cutover, hypercare | `src/agents/orchestrator/` |

### Phases 9–15: Integration, Deployment & Production Readiness (942 tests)

**Goal**: Connect to real services, add CLI, CI/CD, monitoring, and harden for production.

| Phase | Weeks | Focus | Key Source Files |
|-------|-------|-------|-----------------|
| 9 | 17–18 | argparse CLI, integration test framework, config management | `src/cli/main.py`, `config/` |
| 10 | 19–20 | OAuth2/IDCS auth, real OAC API clients, VCR cassettes | `src/clients/oac_client.py`, `src/clients/idcs_auth.py` |
| 11 | 20–22 | Real Lakehouse/PBI clients, XMLA, workspace roles | `src/clients/fabric_client.py`, `src/clients/pbi_client.py` |
| 12 | 22–23 | Azure OpenAI integration, prompt templates, confidence | `src/core/llm_translator.py` |
| 13 | 23–25 | GitHub Actions, CD pipeline, Terraform/Bicep | `.github/workflows/`, `infra/` |
| 14 | 25–26 | App Insights, distributed tracing, alerting | `src/core/telemetry.py` |
| 15 | 27–28 | Performance, resilience, Sphinx/MkDocs docs | `docs/` |

**Effort**: 112 person-days (73 dev + 39 QA)

### Phases 16–22: Live Validation & GA Release (1,243 tests)

**Goal**: Eliminate all stubs, validate against live environments, achieve v1.0 GA.

**Stubs eliminated**: Fabric SQL execution, TMDL deployment, TMDL roles/expressions, PL/SQL loops, AAD group resolution, `.env.example`, `datetime.utcnow()` fix.

| Phase | Weeks | Focus | Key Source Files |
|-------|-------|-------|-----------------|
| 16 | 29–31 | Real Fabric SQL (pyodbc), real TMDL (XMLA), AAD Graph API | `src/clients/fabric_client.py`, `src/deployers/` |
| 17 | 31–33 | AgentRegistry, RunnerFactory, state coordination, CLI `--resume`/`--agents` | `src/core/agent_registry.py`, `src/core/runner_factory.py` |
| 18 | 33–35 | Real OAC connection, RPD validation against production | `src/clients/oac_client.py` |
| 19 | 35–37 | Real Lakehouse/Warehouse deployment, TMDL/PBIR/RLS/OLS deploy | `src/deployers/` |
| 20 | 37–39 | Complex PL/SQL (CURSOR, BULK COLLECT, dynamic SQL), advanced expressions | `src/core/plsql_translator.py`, `src/core/dax_translator.py` |
| 21 | 39–41 | Notifications (Teams/email/PagerDuty), App Insights, Key Vault, security scans | `src/core/telemetry.py`, `src/core/secret_manager.py` |
| 22 | 41–42 | Benchmarking, 10K-asset load test, memory profiling, v1.0.0 release | `scripts/benchmark.py` |

**Phase dependency chain**: 16 → 17 → 18 → 19 → {20, 21} → 22

---

## v2.0 — Enterprise Platform (Phases 23–30)

**Goal**: Evolve from CLI tool into a full enterprise platform with web UI, containers, multi-source support, plugins, multi-tenancy, and rollback.

**Gaps addressed**: No web UI → FastAPI + React; no containers → Docker + ACA; no incremental sync → change detection + sync journal; single-source → multi-source connectors; manual visual validation → AI-powered comparison; no plugins → extensible plugin architecture; no multi-tenancy → tenant isolation + RBAC; no rollback versioning → content-addressable snapshots.

| Phase | Weeks | Focus | Key Source Files | New Tests |
|-------|-------|-------|-----------------|-----------|
| 23 | 43–45 | FastAPI backend, WebSocket/SSE, REST endpoints (React frontend deferred to Phase 39) | `src/api/` | 35 |
| 24 | 45–48 | Dockerfile, Docker Compose, Bicep ACA, Helm, CI/CD | `infra/`, `.github/workflows/` | 30 |
| 25 | 48–50 | ChangeDetector, SyncJournal, `--mode incremental` | `src/core/change_detector.py`, `src/core/sync_journal.py` | 35 |
| 26 | 50–53 | SourceConnector ABC, OBIEE connector, Tableau/Cognos/Qlik stubs | `src/connectors/` | 30 |
| 27 | 53–55 | Playwright screenshots, GPT-4o comparison, SSIM, PDF report | `src/core/visual_validator.py` | 35 |
| 28 | 55–57 | PluginManager, plugin.toml, lifecycle hooks, sandboxing | `src/core/plugin_manager.py` | 35 |
| 29 | 57–60 | Tenant model, Azure AD SSO, JWT, RBAC, metering, rate limiting | `src/core/tenant_manager.py`, `src/api/middleware/` | 35 |
| 30 | 60–62 | ArtifactVersioner, RollbackEngine, diff viewer, v2.0 release | `src/core/artifact_versioner.py`, `src/core/rollback_engine.py` | 30 |

**Total new tests**: 265 | **Cumulative**: 1,508 (2 skipped)

### Architecture Evolution

```
v1.0 CLI Tool                          v2.0 Enterprise Platform
┌──────────┐                           ┌─────────────────┐
│  CLI     │                           │  React Dashboard│
│ (Typer)  │                           │  (Vite + React) │
└────┬─────┘                           └───────┬─────────┘
     │                                         │
┌────▼─────────────┐               ┌───────────▼──────────┐
│ Migration Engine │               │   FastAPI Backend    │
│ (8 Agents + DAG) │               │   (REST + WebSocket) │
└────┬─────────────┘               └───────────┬──────────┘
     │                                         │
┌────▼─────────────┐               ┌───────────▼──────────┐
│ Fabric Lakehouse │               │   Migration Engine   │
│ (Delta Tables)   │               │   (8 Agents + DAG)   │
└──────────────────┘               └───────────┬──────────┘
                                               │
                                   ┌───────────▼──────────┐
                                   │ Docker / Azure       │
                                   │ Container Apps       │
                                   └──────────────────────┘
```

---

## v3.0 — Field-Proven Delivery (Phases 31–38)

**Goal**: Achieve production-grade confidence with E2E testing, mature DAX translation, UAT workflows, and customer delivery packaging.

**Gaps addressed**: No E2E integration tests → golden fixtures + test harness; stale docs → automated validation + generation; no pipeline execution → full deploy + monitor; limited DAX (~30 functions) → 80+ mappings; no pre-migration assessment → complexity analyzer + cost estimator; no UAT workflow → state machine + sign-off tracker; no Data Factory deployer → pipeline deployer; no GitHub Actions CI → CI workflow generator.

| Phase | Weeks | Focus | Key Source Files | New Tests |
|-------|-------|-------|-----------------|-----------|
| 31 | 63–65 | Golden fixtures, IntegrationTestHarness, OutputComparator | `src/testing/integration_harness.py` | 30 |
| 32 | 65–67 | DocValidator, ChangelogGenerator, ProjectHealthCheck | `src/core/doc_validator.py` | 25 |
| 33 | 67–69 | PipelineDeployer, DataCopyOrchestrator, PipelineMonitor | `src/deployers/pipeline_deployer.py` | 30 |
| 34 | 69–71 | TranslationCatalog, 80+ DAX mappings, ConfidenceCalibrator | `src/core/translation_catalog.py` | 35 |
| 35 | 71–73 | ComplexityAnalyzer, CostEstimator, PreflightChecker | `src/core/migration_intelligence.py` | 30 |
| 36 | 73–75 | UATSession, UAT state machine, SignOffTracker, DefectLog | `src/core/uat_workflow.py` | 28 |
| 37 | 75–77 | DeliveryPackage, AssetCatalog, HandoverChecklist | `src/core/delivery_package.py` | 25 |
| 38 | 77–78 | ChaosSimulator, SecurityScanner, ReleaseValidator, v3.0 release | `src/core/chaos_testing.py` | 25 |

**Total new tests**: 228 | **Cumulative**: 1,871 (2 skipped)

### Key Metrics v2.0 → v3.0

| Metric | v2.0 | v3.0 |
|--------|------|------|
| Automated tests | 1,508 | 1,871 |
| DAX function mappings | ~30 | 80+ |
| Integration test scenarios | 0 | 30+ |
| Pipeline support | Generation only | Deploy + monitor |
| Pre-migration assessment | None | Automated |
| UAT workflow | None | Full state machine |
| Delivery package | None | Auto-generated |
| Chaos test scenarios | 0 | 10+ |

---

## Technology Stack

### Core

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| CLI | argparse (async commands) |
| Web API | FastAPI + Uvicorn |
| Frontend | React 18 + Vite + TanStack Query + Recharts |
| Agent Framework | Custom (`MigrationAgent` ABC) |
| Data Models | Pydantic |
| Testing | pytest + pytest-asyncio + Great Expectations |
| LLM | Azure OpenAI GPT-4 / GPT-4o |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Containers | Docker + Docker Compose |
| Cloud Hosting | Azure Container Apps (Bicep) |
| Kubernetes | Helm charts (AKS) |
| IaC | Terraform + Bicep |
| CI/CD | GitHub Actions |
| Secret Management | Azure Key Vault |
| Monitoring | Application Insights + OpenTelemetry |
| Security Scanning | Trivy, bandit, pip-audit |

### Integrations

| Component | Technology |
|-----------|-----------|
| OAC API | REST + IDCS OAuth2 |
| RPD Parsing | XML (standard + streaming) |
| Fabric | pyodbc + PySpark + Delta Lake |
| Power BI | XMLA (pyadomd) + REST API |
| TMDL | Tabular Editor CLI |
| Multi-source | OBIEE RPD binary, Tableau REST API (stubs: Cognos, Qlik) |
| Visual Validation | Playwright + GPT-4o vision + SSIM (scikit-image) |
| Notifications | Teams webhook, Azure Communication Services (email), PagerDuty Events API v2 |
| Auth | Azure AD / Entra ID, MSAL, JWT |

---

## Development Environment

### Prerequisites

- **Python 3.12+** (3.14 recommended)
- **Node.js 18+** (for React dashboard)
- **Docker** (for containerized deployment)
- **Azure CLI** (`az login` for cloud resources)
- **Git**

### Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd OACToFabric
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Environment config
cp .env.example .env            # Fill in credentials

# Run tests
python -m pytest tests/ -v

# Start API server
uvicorn src.api.main:app --reload

# Start dashboard
cd dashboard && npm install && npm run dev
```

---

## Sprint Cadence

| Day | Activity |
|-----|----------|
| Monday | Sprint planning, task assignment |
| Daily | 15-min standup (blockers, progress) |
| Friday | Sprint review + retrospective |

- **Sprint length**: 1 week
- **PR reviews**: Required before merge
- **Definition of Done**: Tests pass, docs updated, reviewed

---

## Team Structure

| Role | Count | Responsibility |
|------|-------|---------------|
| Project Manager | 1 | Scope, timeline, stakeholder communication |
| Dev Lead | 1 | Architecture, code review, technical decisions |
| Backend Developer | 3 | Agent implementation, API, integrations |
| Data Engineer | 1 | Fabric/Lakehouse, ETL pipelines, data validation |
| Power BI Developer | 1 | Semantic models, reports, DAX translation |
| QA Engineer | 1 | Test strategy, automation, validation |
| Platform/Infra | 1 | Docker, CI/CD, IaC, monitoring |
| Oracle SME | 0.5 | OAC/RPD expertise (part-time) |

**Total**: 9.5 FTEs

---

## Risk Register

| ID | Risk | Mitigation |
|----|------|-----------|
| R1 | OAC API rate limits | Implement exponential backoff, cache responses |
| R2 | RPD XML complexity | Streaming parser for large files, golden fixtures |
| R3 | DAX translation gaps | LLM fallback, confidence scoring, manual review queue |
| R4 | Fabric API changes | SDK version pinning, integration test suite |
| R5 | Large migration volumes | Incremental sync, wave-based execution, performance benchmarks |
| R6 | Security model mismatch | Early RLS/OLS testing, multi-persona validation |
| R7 | LLM hallucination | Syntax validation, golden test set, confidence thresholds |
| R8 | Multi-tenant isolation | Tenant-scoped storage, middleware enforcement, chaos testing |
| R9 | Plugin stability | Sandboxing, schema validation, resource limits |
| R10 | Visual regression | AI + SSIM dual validation, human review escalation |
| R11 | Rollback data loss | Content-addressable snapshots, action log replay |
| R12 | Customer UAT delays | Structured workflow, automated report generation |

---

## Success Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Automated test count | ≥1,500 | ✅ 1,871 |
| Test pass rate | 100% | ✅ 100% (2 skipped) |
| DAX function coverage | ≥60 mappings | ✅ 80+ |
| Migration asset types | ≥8 | ✅ 10+ |
| Source platforms | ≥2 | ✅ 3 (OAC, OBIEE, + stubs) |
| E2E test scenarios | ≥20 | ✅ 30+ |
| API response time (p95) | <500ms | ✅ Achieved |
| Container cold start | <30s | ✅ Achieved |
| Rollback success rate | 100% | ✅ Verified |
| Documentation coverage | ≥90% modules | ✅ Achieved |

---

## v4.0 — Production Dashboard & Multi-Source Maturity (Phases 39–46)

**Goal**: Deliver a production-grade web dashboard, complete multi-source connector coverage, and add AI-driven optimization — evolving the tool from a CLI-first framework into a fully self-service migration platform.

**Gaps addressed**: No web dashboard (referenced in v2.0 docs but not shipped) → React + Vite app; Tableau/Cognos/Qlik stubs → full connectors; no plugin marketplace → registry + distribution; no post-migration optimization → AI-assisted tuning; no visual migration wizard → guided workflow.

### Phase Summary

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 39 | React Dashboard | ✅ Complete | React 18 + Vite + TanStack Query, migration wizard, inventory browser, real-time logs, dark mode |
| 40 | Tableau Connector | ✅ Complete | TWB/TWBX parser, REST API client, 55+ calc→DAX rules, data source mapping, full connector |
| 41 | Cognos, Qlik & Essbase Connectors | 🟡 Partial | Cognos/Qlik stubs; **Essbase ✅ complete** — REST API, outline parser, 55+ calc→DAX, 24+ MDX→DAX, filters→RLS |
| 42 | Plugin Marketplace | 🟡 Planned | Plugin registry, versioned distribution, sample plugins, community docs |
| 43 | Migration Analytics Dashboard | 🟡 Planned | PBI dashboard template, cost/time tracking, progress metrics, executive summary |
| 44 | Advanced RPD Binary Parser | 🟡 Planned | Direct RPD binary parsing, streaming for large files, metadata extraction |
| 45 | AI-Assisted Schema Optimization | 🟡 Planned | LLM-driven partition key selection, index recommendations, capacity sizing |
| 46 | Performance Auto-Tuning | 🟡 Planned | Automated RU/capacity tuning, query plan analysis, semantic model optimization |

### Phase Details

#### Phase 39: React Dashboard (Weeks 79–82)

**Purpose**: Ship the web dashboard that was designed in Phase 23 (FastAPI backend) but whose frontend was deferred.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | FastAPI endpoints (REST + WebSocket + SSE), auth middleware (JWT/OAuth2) |
| **Outputs** | React 18 + Vite SPA in `dashboard/`, Docker Compose integration |
| **Key Features** | Migration wizard (step-by-step), inventory browser with filtering/search, real-time log streaming, validation results viewer, rollback UI, dark mode |
| **Dependencies** | Phase 23 API (complete), Phase 29 auth (complete) |

#### Phase 40: Tableau Connector (Weeks 82–85) ✅ COMPLETE

**Purpose**: Extend `SourceConnector` from Phase 26 with full Tableau support.

| Attribute | Detail |
|-----------|--------|
| **Status** | **Complete** — 2026-03-24 |
| **Files** | `src/connectors/tableau_connector.py` (530 lines), updated `base_connector.py` |
| **Inputs** | TWB/TWBX files, Tableau Server/Cloud REST API |
| **Outputs** | Normalized inventory, extracted calculations → DAX, data source mappings |
| **Key Logic** | TWB/TWBX XML parser (datasources, worksheets, dashboards, calc fields, parameters); 55+ rule-based Tableau → DAX translations with confidence scoring; async REST API client (PAT & password auth); 11 connection-type and 6 data-type Fabric mappings |
| **Tests** | 116 new tests (`test_phase40_tableau.py`), 1 updated in `test_phase26_connectors.py` |
| **Dependencies** | Phase 26 connector framework (complete) |

#### Phase 41: Cognos, Qlik & Essbase Connectors (Weeks 85–88)

**Purpose**: Complete the multi-source connector portfolio.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Cognos Report Studio XML, Qlik QVF/QVD files, Cognos REST API, Qlik Engine API, Essbase REST API, Essbase outlines, calc scripts, MDX queries |
| **Outputs** | Normalized inventory per `SourceConnector` interface |
| **Key Logic** | Parse Cognos report specs and data modules; extract Qlik load scripts and set analysis; parse Essbase outlines (dimensions, hierarchies, members) and translate calc scripts/MDX to DAX; map Essbase filters to RLS; map expressions to DAX equivalents |
| **Essbase** | **✅ COMPLETE** — `src/connectors/essbase_connector.py` (700+ lines): REST API client, outline parser (XML+JSON), EssbaseCalcTranslator (55+ calc→DAX rules), EssbaseMdxTranslator (24+ MDX→DAX rules), 22 outline→TMDL concept mappings, full SourceConnector lifecycle. 133 tests. **Essbase→Semantic Model bridge** (`essbase_semantic_bridge.py`, 480+ lines): ParsedOutline→SemanticModelIR converter — sparse dims→dim tables, accounts→DAX measures, time→date tables, hierarchies, star-schema joins, filters→RLS, substitution vars→What-if params, calc scripts→measures. 53 tests. |
| **Cognos** | **✅ COMPLETE** — `src/connectors/cognos_connector.py` (650+ lines): 50+ calc→DAX rules, CognosExpressionTranslator, CognosReportSpecParser (XML), CognosRestClient (async, v11.1+), FullCognosConnector. `cognos_semantic_bridge.py` (250+ lines): ParsedReportSpec→SemanticModelIR. 70 tests. |
| **Qlik** | **✅ COMPLETE** — `src/connectors/qlik_connector.py` (700+ lines): 72+ calc→DAX rules, QlikExpressionTranslator, QlikLoadScriptParser, QlikEngineClient (async), FullQlikConnector. `qlik_semantic_bridge.py` (250+ lines): QlikApp→SemanticModelIR. 85 tests. |
| **Dependencies** | Phase 26 connector framework (complete) |

#### Phase 42: Plugin Marketplace (Weeks 88–90) ✅

**Purpose**: Enable community extensibility beyond the core framework.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Phase 28 `PluginManager`, `plugin.toml` manifest |
| **Outputs** | Plugin registry index, CLI `plugin install/publish`, sample plugins |
| **Implementation** | `src/plugins/marketplace.py` — PluginRegistry (JSON-backed), PluginInstaller, PluginRegistryEntry, InstallResult, CLI helpers (cmd_plugin_list/install/publish). **Sample plugins**: VisualMappingOverridePlugin (POST_TRANSLATE hook, visual type overrides), DataQualityPlugin (PRE/POST_VALIDATE hooks, null ratio, row count variance checks). 48 tests. |
| **Dependencies** | Phase 28 plugin architecture (complete) |

#### Phase 43: Migration Analytics Dashboard (Weeks 90–92) ✅

**Purpose**: Provide executive-level visibility into migration progress and costs.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Lakehouse coordination tables, agent logs, cost estimator (Phase 35) |
| **Outputs** | Power BI dashboard template (.pbit), auto-refresh dataset |
| **Implementation** | `src/plugins/analytics_dashboard.py` — MigrationMetrics, AgentMetrics, WaveMetrics, CostMetrics, MetricsCollector, DashboardDataExporter (JSON/CSV), PBITTemplateGenerator (5-page manifest: Executive Summary, Wave Progress, Agent Details, Cost Analysis, Validation), ExecutiveSummary. 31 tests. |
| **Dependencies** | Phase 35 migration intelligence (complete) |

#### Phase 44: Advanced RPD Binary Parser (Weeks 92–94) ✅

**Purpose**: Parse OBIEE RPD files natively without requiring XML export.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | RPD binary files (.rpd) |
| **Outputs** | Same inventory model as XML parser |
| **Implementation** | `src/core/rpd_binary_parser.py` — RPDBinaryParser (header/section/object/property decoding), LargeFileStreamingParser (4MB chunks, memory-bounded), RPDBinaryToXMLConverter (binary→XML for existing parser compatibility), build_test_rpd_binary (synthetic test data). Supports OBIEE 10g/11g/12c formats. 7 section types, 12 object types. 38 tests. |
| **Dependencies** | Phase 26 OBIEE connector (complete) |

#### Phase 45: AI-Assisted Schema Optimization (Weeks 94–96) ✅

**Purpose**: Use rule-based + AI-assisted analysis to recommend optimal Fabric target schemas.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Source schema, query patterns, data volume statistics |
| **Outputs** | Partition key recommendations, storage mode advice, capacity sizing |
| **Implementation** | `src/core/schema_optimizer.py` — SchemaOptimizer (orchestrates all), PartitionKeyRecommender (cardinality scoring, HPK for >20GB), StorageModeAdvisor (Direct Lake/Import/Dual heuristics), CapacitySizer (F2–F1024 SKU selection with workload scaling). Models: ColumnProfile, TableProfile, SchemaProfile, WorkloadPattern, OptimizationRecommendation, OptimizationReport. 27 tests. |
| **Dependencies** | Phase 2 schema agent (complete), Phase 12 LLM client (complete) |

#### Phase 46: Performance Auto-Tuning (Weeks 96–98) ✅

**Purpose**: Automated post-migration performance optimization.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Deployed Fabric/PBI artifacts, query logs, DAX Studio traces |
| **Outputs** | Optimization report, automated tuning actions |
| **Implementation** | `src/core/perf_auto_tuner.py` — PerformanceAutoTuner (orchestrates all), PerformanceAnalyzer (categorize fast/normal/slow/critical, SE/FE ratio, hot tables, P95), DAXOptimizer (6 anti-pattern detections: SUMX→SUM, AVERAGEX→AVERAGE, ISBLANK→COALESCE, nesting depth, bidir warnings), AggregationAdvisor (scan-based suggestions), CompositeModelAdvisor (DL/Import/Dual assignment). Models: QueryProfile, DAXMeasureProfile, DAXOptimization, AggregationTableSpec, CompositeModelPattern, PerformanceTuningReport. 39 tests. |
| **Dependencies** | Phase 19 deployment (complete), Phase 22 benchmarking (complete) |

### Key Metrics v3.0 → v4.0 → v5.0 (Targets)

| Metric | v3.0 | v4.0 Final | v4.0 Target | v5.0 Target |
|--------|------|-------------|-------------|-------------|
| Automated tests | 1,871 | **2,618** | ≥2,500 ✅ | ≥3,000 |
| Source platforms (full) | 2 (OAC, OBIEE) | **5** (+ Tableau, Cognos, Qlik) | 5 ✅ | 5+ community |
| Web dashboard | API only | React SPA + PBI analytics | React + PBI analytics ✅ | GraphQL + portal |
| Plugin ecosystem | Framework | Marketplace + 2 samples | Marketplace + samples ✅ | Self-service portal |
| DAX function mappings | 80+ | **260+** (Tableau 55, Cognos 50, Qlik 72, Essbase 79) | 160+ ✅ | 200+ ✅ |
| AI features | Translation only | Schema optimization + perf auto-tuning | Schema + perf tuning ✅ | Simulation + regression |

---

## v5.0 — Intelligent Platform (Phases 47–50)

**Goal**: Transform from a migration tool into a self-service, AI-powered migration platform with simulation, regression testing, GraphQL API, and a multi-org portal.

**Gaps addressed**: REST-only API → GraphQL federation; no pre-flight simulation → full dry-run with cost/risk estimates; no post-migration regression → automated visual + data snapshot comparison; no self-service onboarding → multi-org portal with drag-and-drop.

### Phase Summary

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 47 | GraphQL API & Federation | 📋 Planned | Strawberry GraphQL schema, real-time subscriptions, REST+GQL coexistence |
| 48 | Migration Dry-Run Simulator | 📋 Planned | Full simulation without target writes, cost/time estimates, risk scoring |
| 49 | Automated Regression Testing | 📋 Planned | Snapshot-based regression, visual diff for reports, data drift detection |
| 50 | Self-Service Migration Portal | 📋 Planned | Multi-org SSO, drag-and-drop upload, migration templates, public API |

### Phase Details

#### Phase 47: GraphQL API & Federation (Weeks 99–102)

**Purpose**: Add a GraphQL layer on top of the FastAPI backend for flexible querying and real-time subscriptions, enabling richer frontend experiences and third-party integrations.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Existing FastAPI endpoints, migration data store, agent state |
| **Outputs** | GraphQL schema (Strawberry), subscriptions for real-time events, unified query endpoint |
| **Key Logic** | Schema stitching with REST endpoints; real-time subscriptions via WebSocket transport; field-level authorization; query complexity limits; DataLoader pattern for N+1 prevention |
| **Dependencies** | Phase 23 FastAPI (complete), Phase 29 auth (complete) |

#### Phase 48: Migration Dry-Run Simulator (Weeks 102–106)

**Purpose**: Enable users to simulate an entire migration end-to-end without writing to any target system, producing a detailed report of what would happen, estimated cost, time, and risk.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Source inventory (from discovery), migration plan, translation engine |
| **Outputs** | Simulation report (JSON/HTML), cost estimate, time estimate, risk heatmap, change manifest |
| **Key Logic** | Run all agents in `--dry-run` mode with instrumented output collectors; measure translation coverage and confidence across every asset; produce a risk score per asset based on complexity + confidence; estimate Fabric capacity cost based on data volume and pipeline count |
| **Dependencies** | Phase 35 intelligence (complete), Phase 22 benchmarking (complete) |

#### Phase 49: Automated Regression Testing (Weeks 106–109)

**Purpose**: Provide continuous regression testing after migration, catching data drift, schema changes, or visual regressions in migrated Power BI reports.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Baseline snapshots (data, schema, report images), live Fabric/PBI environment |
| **Outputs** | Regression test suite, diff reports (data + visual), alert notifications |
| **Key Logic** | Capture baseline data snapshots (row counts, checksums, sample queries) at go-live; schedule periodic comparison against live data; capture report screenshot baselines and SSIM/GPT-4o visual diff; detect schema drift (new columns, type changes, missing tables); integrate with Phase 21 notification pipeline for alerts |
| **Dependencies** | Phase 7 validation agent (complete), Phase 27 visual validation (complete) |

#### Phase 50: Self-Service Migration Portal (Weeks 109–113)

**Purpose**: Build a multi-organization self-service portal where teams can upload source artifacts, configure migrations, and monitor progress without needing CLI or API knowledge.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | User-uploaded source files (RPD XML, TWB/TWBX, QVF), admin portal config |
| **Outputs** | Web portal (React), organization management, migration templates, public REST/GraphQL API |
| **Key Logic** | Multi-org SSO via Azure AD B2C or Entra External ID; drag-and-drop file upload with server-side validation; pre-built migration templates (OAC→Fabric, OBIEE→Fabric, Tableau→PBI); migration project management (create/clone/archive); public API with API key auth for CI/CD integration; usage analytics and billing metering per org |
| **Dependencies** | Phase 29 multi-tenant (complete), Phase 47 GraphQL (planned), Phase 48 simulator (planned) |

---

## Key References

| Document | Path | Purpose |
|----------|------|---------|
| Agent Architecture | `AGENTS.md` | Agent definitions, file ownership, handoff protocol |
| Architecture | `docs/ARCHITECTURE.md` | System architecture, module responsibilities, data flow |
| Deployment Guide | `docs/DEPLOYMENT_GUIDE.md` | Fabric/PBI deployment, auth, CI/CD, troubleshooting |
| Mapping Reference | `docs/MAPPING_REFERENCE.md` | All translation rules — types, SQL, DAX, visuals, security |
| Gap Analysis | `docs/GAP_ANALYSIS.md` | Implementation coverage & priority improvements |
| Known Limitations | `docs/KNOWN_LIMITATIONS.md` | Current gaps, workarounds & severity ratings |
| FAQ | `docs/FAQ.md` | Frequently asked questions |
| Migration Playbook | `MIGRATION_PLAYBOOK.md` | Step-by-step production migration guide |
| Security | `docs/security.md` | Credentials, data handling, LLM security |
| ADRs | `docs/adrs/` | Architecture Decision Records |
| Runbooks | `docs/runbooks/` | Operational runbooks |
| Agent SPECs | `agents/01-discovery-agent/SPEC.md` … `agents/08-orchestrator-agent/SPEC.md` | Per-agent technical specifications |

---

*Consolidated from DEV_PLAN.md (Phases 0–8), DEV_PLAN_V2 (Phases 9–15), DEV_PLAN_V3 (Phases 16–22), DEV_PLAN_V4 (Phases 23–30), DEV_PLAN_V5 (Phases 31–38), v4.0 roadmap (Phases 39–46), and v5.0 roadmap (Phases 47–50).*
