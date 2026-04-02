# Development Plan — OAC to Fabric & Power BI Migration Platform

> **Status**: v1.0–v6.0 COMPLETE (62 phases — 0–52, 54–62) | v8.0 Phases 70–76 ✅ | Practical Tooling ✅ | Essbase migration validated  
> **Tests**: 3,872 collected (3,872 passed)  
> **Latest Release**: v8.0.0-alpha.3 — Phases 71–76 Multi-Agent Intelligence (12 modules, 112 tests)  
> **Current Milestone**: v8.0 — Multi-Agent Intelligence (Phases 70–76 complete)  
> **Essbase**: End-to-end migration validated (3 cubes → 36 TMDL files, 66 DAX measures) + Smart View Excel guide (780+ lines)  
> **Remaining**: Phase 53 — Self-Service Portal

---

## Table of Contents

- [Release Timeline](#release-timeline)
- [Phase Summary](#phase-summary)
- [v1.0 — Core Migration Framework (Phases 0–22)](#v10--core-migration-framework-phases-022)
- [v2.0 — Enterprise Platform (Phases 23–30)](#v20--enterprise-platform-phases-2330)
- [v3.0 — Field-Proven Delivery (Phases 31–38)](#v30--field-proven-delivery-phases-3138)
- [v4.0 — Production Dashboard & Multi-Source Maturity (Phases 39–46)](#v40--production-dashboard--multi-source-maturity-phases-3946)
- [v4.1 — T2P Gap Implementation (Phase 47)](#v41--t2p-gap-implementation-phase-47)
- [v4.2 — T2P Parity Completion (Phase 48)](#v42--t2p-parity-completion-phase-48)
- [v4.3 — Production Hardening (Phase 49)](#v43--production-hardening-phase-49)
- [v5.0 — Intelligent Platform (Phases 50–53)](#v50--intelligent-platform-phases-5053)
- [Architecture Evolution](#architecture-evolution)
- [Technology Stack](#technology-stack)
- [Development Environment](#development-environment)
- [Sprint Cadence](#sprint-cadence)
- [Team Structure](#team-structure)
- [v7.0 — Essbase to Fabric Migration (Phases 63–69)](#v70--essbase-to-fabric-migration-phases-6369)
- [v8.0 — Multi-Agent Intelligence (Phases 70–76)](#v80--multi-agent-intelligence-phases-7076)
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
| **v4.2 T2P Parity Completion** | 48 | 2,898 | 100 | ✅ Complete |
| **v4.3 Production Hardening** | 49 | 2,991 | 101 | ✅ Complete |
| **v5.0 GraphQL API** | 50 | 3,126 | 102 | ✅ Complete |
| **v5.0 Intelligent Platform** | 51–52 | 3,274 | 103–106 | ✅ Complete |
| **v6.0 Full Coverage Upgrade** | 54–62 | 3,559 | 107–143 | ✅ Complete |
| **v5.0 Self-Service Portal** | 53 | — | — | 📋 Planned |
| **v7.0 Essbase to Fabric** | 63–69 | 3,947 | 144–160 | 🔄 Validated (connector + bridge + migration example + Smart View guide) |
| **v8.0 Multi-Agent Intelligence** | 70–76 | ~4,500 | 161–180 | 🔄 Phase 70 ✅ (intelligence framework: 90 tests) |
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
| 48 | T2P Parity Completion | ✅ | Lineage map, shared model merge, DAX rules 60→120+, self-healing 6→17, visual types 47→80+ |
| 49 | Production Hardening & Report Fidelity | ✅ | Bridge tables, hierarchy RLS, theme converter, mobile layout, tooltip pages, drill-through, DQ profiler, schema drift, DLQ, approval gates |
| 50 | GraphQL API & Federation | ✅ | Strawberry GraphQL schema, real-time subscriptions, field-level auth, query complexity limits, DataLoader N+1 prevention, REST+GQL coexistence |
| 51 | Migration Dry-Run Simulator | ✅ | Full simulation without target writes, cost/time estimates, risk scoring |
| 52 | Automated Regression Testing | ✅ | Snapshot-based regression, visual diff for reports, data drift detection |
| 53 | Self-Service Migration Portal | 📋 Planned | Multi-org SSO, drag-and-drop upload, migration templates, public API |

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
| Multi-source | OBIEE RPD binary, Tableau REST API, Cognos Report Spec, Qlik Load Script, Essbase REST API |
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
| Automated test count | ≥1,500 | ✅ 3,760 |
| Test pass rate | 100% | ✅ 100% (0 skipped) |
| DAX function coverage | ≥60 mappings | ✅ 80+ (core OAC) + 260+ (multi-source) |
| Migration asset types | ≥8 | ✅ 10+ |
| Source platforms | ≥2 | ✅ 5 (OAC, OBIEE, Tableau, Cognos, Qlik) + Essbase |
| Agent intelligence | Rules-only | 🔄 v8.0 Phase 70 ✅: ReAct reasoning loop, agent memory, tool registry, cost controls + Practical tooling (DAX validator, TMDL validator, reconciliation CLI, OAC test harness, Fabric dry-run) |
| Essbase E2E migration | Not started | ✅ 3 cubes migrated (36 TMDL, 66 DAX measures, 15 DDL tables, 4 RLS roles) |
| Essbase Smart View guide | Not started | ✅ 780+ lines, 11 sections, CUBE formula recipes for all 3 cubes |
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
| 41 | Cognos, Qlik & Essbase Connectors | ✅ Complete | Cognos (full), Qlik (full), Essbase (full) — REST APIs, parsers, expression→DAX, semantic bridges |
| 42 | Plugin Marketplace | ✅ Complete | PluginRegistry, CLI install/publish, sample plugins |
| 43 | Migration Analytics Dashboard | ✅ Complete | MetricsCollector, DashboardDataExporter, PBI template |
| 44 | Advanced RPD Binary Parser | ✅ Complete | RPDBinaryParser (10g/11g/12c), streaming, XML converter |
| 45 | AI-Assisted Schema Optimization | ✅ Complete | PartitionKeyRecommender, StorageModeAdvisor, CapacitySizer |
| 46 | Performance Auto-Tuning | ✅ Complete | PerformanceAnalyzer, DAXOptimizer, AggregationAdvisor |

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

### Key Metrics v3.0 → v4.0 → v4.1 → v4.2 → v4.3 → v5.0

| Metric | v3.0 | v4.0 | v4.1 | v4.2 | v4.3 | v5.0 (Phase 50) |
|--------|------|------|------|------|------|----------------|
| Automated tests | 1,871 | 2,618 | 2,784 | 2,898 | 2,991 | **3,051** |
| Source platforms (full) | 2 | 5 | 5 + Essbase | 5 + Essbase | 5 + Essbase | 5 + Essbase |
| Visual types supported | 24 | 24 | 47 | **80+** | 80+ | 80+ |
| Web dashboard | API only | React SPA | React SPA | React SPA | React SPA | **React SPA + GraphQL** |
| Plugin ecosystem | Framework | Marketplace | Marketplace | Marketplace | Marketplace | Marketplace |
| DAX function mappings | 80+ | 260+ | 260+ | **300+** (120+ OAC) | 300+ | 300+ |
| Self-healing patterns | 0 | 0 | 6 | **17** | 17 | 17 |
| AI features | Translation | Schema opt + perf | + DAX optimizer | + lineage, merge | + DQ profiling | **+ GraphQL API** |

---

## v4.1 — T2P Gap Implementation (Phase 47) ✅

**Goal**: Close the feature gap identified by comparing against the TableauToPowerBI (T2P) project. Add calendar generation, DAX optimization, self-healing, visual fallback, bookmarks, governance, SLA tracking, monitoring, and portfolio assessment — bringing the OAC→Fabric framework to near-parity with the mature T2P codebase.

**Gaps addressed**: No auto Calendar table → `calendar_generator.py`; no TMDL self-healing → `tmdl_self_healing.py`; no visual fallback → `visual_fallback.py`; no bookmarks → `bookmark_generator.py`; no DAX optimizer → `dax_optimizer.py`; no governance → `governance_engine.py`; no SLA enforcement → `sla_tracker.py`; 24 visual types → 47; no portfolio assessment → `portfolio_assessor.py`; no OAC leak detection → `leak_detector.py`.

### Phase Summary

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 47 | T2P Gap Implementation | ✅ Complete | 16 new modules, 47 visual types, 18+ custom visuals, 168 new tests |

### Key Deliverables

- **16 new modules** across all 8 agents (see CHANGELOG v4.1.0 for full list)
- **47 visual types** (expanded from 24) including 18+ AppSource custom visual GUIDs
- **168 new tests** in 8 test files — total: 2,784 tests
- **Modified**: `tmdl_generator.py` (steps 9-13, database.tmdl), `visual_mapper.py` (23→47 types, 20→38 data roles)

### Key Metrics v4.0 → v4.1

| Metric | v4.0 Final | v4.1 Final |
|--------|------------|------------|
| Automated tests | 2,618 | **2,784** |
| Visual types supported | 24 | **47** |
| Custom visual GUIDs | 0 | **18+** |
| New modules | — | **16** |
| DAX optimization rules | 0 | **5** |
| Self-healing patterns | 0 | **6** |
| Governance patterns (PII) | 0 | **15** |

---

## v4.2 — T2P Parity Completion (Phase 48) ✅

**Goal**: Complete feature parity with the TableauToPowerBI reference project — full lineage/dependency graph, shared semantic model merge, 120+ DAX rules, 80+ visual types, 17 self-healing patterns.

### Phase Summary

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 48 | T2P Parity Completion | ✅ Complete | Lineage map, shared model merge, DAX rules 60→120+, self-healing 6→17, visual types 47→80+ |

### Key Deliverables

- **2 new modules**: `lineage_map.py` (full JSON lineage/dependency graph with BFS impact analysis), `shared_model_merge.py` (SHA256 fingerprint-based table matching, jaccard scoring, merge manifests)
- **DAX rules**: 60+ → 120+ (aggregate, time intelligence, scalar expansions)
- **Self-healing patterns**: 6 → 17 (missing_sort_by, invalid_format_strings, duplicate_measures, etc.)
- **Visual types**: 47 → 80+ (35+ new OACChartType entries, 12+ custom visual GUIDs)
- **112 new tests** in 3 test files — total: 2,898 tests

---

## v4.3 — Production Hardening (Phase 49) ✅

**Goal**: Production-grade report fidelity — bridge tables, hierarchy RLS, drill-through, theme conversion, mobile layout, DQ profiling, schema drift detection, dead letter queue, and approval gates.

### Phase Summary

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 49 | Production Hardening & Report Fidelity | ✅ Complete | Bridge tables, hierarchy RLS, theme converter, mobile layout, tooltip pages, drill-through, DQ profiler, schema drift, DLQ, approval gates |

### Key Deliverables

- **5 new modules**: `bridge_table_generator.py`, `theme_converter.py`, `goals_generator.py`, `dq_profiler.py`, `schema_drift.py`
- **8 enhanced modules**: hierarchy RLS with `PATHCONTAINS`, drill-through + What-If + tooltip pages, mobile layout (360×640), display folder intelligence, cascading slicers, environment parameterization, dead letter queue, approval gates
- **91 new tests** in 1 test file — total: 2,991 tests

---

## v5.0 — Intelligent Platform (Phases 50–53)

**Goal**: Transform from a migration tool into a self-service, AI-powered migration platform with GraphQL API, simulation, regression testing, and a multi-org portal.

**Gaps addressed**: REST-only API → GraphQL federation; no pre-flight simulation → full dry-run with cost/risk estimates; no post-migration regression → automated visual + data snapshot comparison; no self-service onboarding → multi-org portal with drag-and-drop.

### Phase Summary

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 50 | GraphQL API & Federation | ✅ Complete | Strawberry GraphQL schema, real-time subscriptions, field-level auth, query complexity limits, DataLoader N+1 prevention, REST+GQL coexistence |
| 51 | Migration Dry-Run Simulator | ✅ Complete | Full simulation without target writes, cost/time estimates, risk heatmap, change manifests |
| 52 | Automated Regression Testing | ✅ Complete | Data/schema/visual regression, SSIM comparison, notification alerts, scheduling |
| 53 | Self-Service Migration Portal | 📋 Planned | Multi-org SSO, drag-and-drop upload, migration templates, public API |

### Phase Details

#### Phase 50: GraphQL API & Federation (Week 102) ✅ COMPLETE

**Purpose**: Add a GraphQL layer on top of the FastAPI backend for flexible querying and real-time subscriptions, enabling richer frontend experiences and third-party integrations.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Existing FastAPI endpoints, migration data store, auth system |
| **Outputs** | GraphQL schema (Strawberry), subscriptions for real-time events, unified query endpoint |
| **Key Logic** | Strawberry GraphQL types at module level; real-time subscriptions via WebSocket transport; field-level authorization with `require_permission()`; query depth/complexity limiting; DataLoader pattern for N+1 prevention; REST+GraphQL coexistence on `/graphql` |
| **Dependencies** | Phase 23 FastAPI (complete), Phase 29 auth (complete) |

**New modules (2):**
- `src/api/graphql_schema.py` — Strawberry GraphQL schema: Query (health, migrations, migration by ID), Mutation (createMigration, cancelMigration), Subscription (migrationLogs, migrationEvents), field-level auth, complexity/depth limits
- `src/api/dataloaders.py` — DataLoader pattern: MigrationLoader, InventoryLoader, LogLoader, DataLoaderContext (per-request caching)

**Enhanced modules (1):**
- `src/api/app.py` — GraphQL router mounted at `/graphql` via `strawberry.fastapi.GraphQLRouter`

**Tests:** 60 tests in `tests/test_phase50_graphql.py` (10 test classes)

**Test suite totals:** 3,051 passed (up from 2,991)

#### Phase 51: Migration Dry-Run Simulator (Weeks 103–106) ✅ COMPLETE

**Purpose**: Enable users to simulate an entire migration end-to-end without writing to any target system, producing a detailed report of what would happen, estimated cost, time, and risk.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Source inventory (from discovery), migration plan, translation engine |
| **Outputs** | Simulation report (JSON/HTML), cost estimate, time estimate, risk heatmap, change manifest |
| **Key Logic** | Run all agents in `--dry-run` mode with instrumented output collectors; measure translation coverage and confidence across every asset; produce a risk score per asset based on complexity + confidence; estimate Fabric capacity cost based on data volume and pipeline count |
| **Dependencies** | Phase 35 intelligence (complete), Phase 22 benchmarking (complete) |

**New modules (1):**
- `src/core/dry_run_simulator.py` — DryRunSimulator with SimulationMode (QUICK/STANDARD/FULL), per-asset risk scoring, translation coverage stats, cost/timeline estimation via migration-intelligence, risk heatmaps, change manifests, SimulationReport with markdown/JSON output

**Tests:** 83 tests in `tests/test_phase51_dry_run.py` (12 test classes)

**Test suite totals:** 3,209 passed (up from 3,126)

#### Phase 52: Automated Regression Testing (Weeks 107–109) ✅ COMPLETE

**Purpose**: Provide continuous regression testing after migration, catching data drift, schema changes, or visual regressions in migrated Power BI reports.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Baseline snapshots (data, schema, report images), live Fabric/PBI environment |
| **Outputs** | Regression test suite, diff reports (data + visual), alert notifications |
| **Key Logic** | Capture baseline data snapshots (row counts, checksums, sample queries) at go-live; schedule periodic comparison against live data; capture report screenshot baselines and SSIM/GPT-4o visual diff; detect schema drift (new columns, type changes, missing tables); integrate with Phase 21 notification pipeline for alerts |
| **Dependencies** | Phase 7 validation agent (complete), Phase 27 visual validation (complete) |

**New modules (1):**
- `src/core/regression_tester.py` — RegressionTester with DataBaseline (JSON-serializable), VisualBaseline (SHA-256 hash), RegressionBaseline (combined), data regression (row count drift, checksum comparison), schema regression (via schema_drift module), visual regression (hash + SSIM), RegressionReport with markdown generation, notification integration (critical/warning alerts), RegressionSchedule, convenience wrappers

**Tests:** 65 tests in `tests/test_phase52_regression.py` (14 test classes)

**Test suite totals:** 3,659 passed (up from 3,559)

#### Phase 53: Self-Service Migration Portal (Weeks 110–113)

**Purpose**: Build a multi-organization self-service portal where teams can upload source artifacts, configure migrations, and monitor progress without needing CLI or API knowledge.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | User-uploaded source files (RPD XML, TWB/TWBX, QVF), admin portal config |
| **Outputs** | Web portal (React), organization management, migration templates, public REST/GraphQL API |
| **Key Logic** | Multi-org SSO via Azure AD B2C or Entra External ID; drag-and-drop file upload with server-side validation; pre-built migration templates (OAC→Fabric, OBIEE→Fabric, Tableau→PBI); migration project management (create/clone/archive); public API with API key auth for CI/CD integration; usage analytics and billing metering per org |
| **Dependencies** | Phase 29 multi-tenant (complete), Phase 50 GraphQL (complete), Phase 51 simulator (complete) |

---

## v6.0 — Full Coverage Upgrade (Phases 54–62)

**Goal**: Close every remaining coverage gap by leveraging new Fabric and Power BI features (March 2026 wave), upgrade from 84% → 97%+ automated OAC migration. Materialized Views in Fabric Warehouse, Calculation Groups in TMDL, Fabric Mirroring for Oracle, Paginated Reports for BI Publisher, Translytical Task Flows, DAX UDFs, Direct Lake on OneLake GA, and Data Activator for Alerts are now available and unblock previously impossible mappings.

**Platform features leveraged (new since v5.0)**:

| Fabric / Power BI Feature | GA Status | Unblocks |
|---|---|---|
| **Materialized Views** (Fabric Warehouse) | GA | Oracle materialized views → Fabric Warehouse MVs |
| **Calculation Groups** (TMDL) | GA | OAC time intel patterns → reusable calc groups |
| **Fabric Mirroring for Oracle** | GA | Oracle DB → near-real-time replication to OneLake |
| **Paginated Reports** (Power BI) | GA | BI Publisher reports → PBI Paginated Reports (.rdl) |
| **Data Activator / Fabric Alerts** | GA | OAC Agents/Alerts → data-driven alert rules |
| **Translytical Task Flows** | GA (March 2026) | OAC action links/write-back → report-embedded actions |
| **Direct Lake on OneLake** | GA (March 2026) | Semantic models bypass import; faster queries |
| **DAX User-Defined Functions** | Preview | Complex OAC expressions → reusable DAX UDFs |
| **TMDL View on Web** | Preview (March 2026) | Browser-based TMDL editing post-migration |
| **Modern Visual Defaults (Fluent 2)** | Preview (March 2026) | Theme converter upgrades to CY26 base theme |
| **Custom Totals (Visual Calculations)** | Preview (March 2026) | OAC custom aggregation → PBI visual calculations |
| **Pivot/Unpivot** (Dataflow Gen2 + PySpark) | GA | Missing ETL step types |
| **Incremental Discovery** (OAC REST `modifiedDate`) | API available | Delta crawl for large environments |

### Phase Summary

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 54 | Materialized Views & Oracle Mirroring | ✅ | Oracle MVs → Fabric Warehouse MVs, Oracle Mirroring setup generator |
| 55 | Calculation Groups & DAX UDFs | ✅ | OAC time-intel → TMDL calc groups, complex expr → DAX UDFs |
| 56 | BI Publisher → Paginated Reports | ✅ | BI Publisher XML → .rdl paginated reports |
| 57 | Data Activator & Alert Migration | ✅ | OAC Agents/Alerts → Fabric Data Activator rules |
| 58 | Translytical Task Flows & Action Links | ✅ | OAC action links/navigation → translytical write-back flows |
| 59 | ETL Gap Closure (Pivot/Unpivot/Parallel) | ✅ | Missing ETL steps, parallel job chains, error row routing |
| 60 | Incremental Discovery & Delta Crawl | ✅ | Modification-timestamp crawl, incremental TMDL updates |
| 61 | Direct Lake Optimization & Modern Themes | ✅ | Direct Lake on OneLake models, Fluent 2 themes, custom totals |
| 62 | Advanced Security & Governance | ✅ | AAD group provisioning, dynamic RLS, audit trail migration |

### Phase Details

#### Phase 54: Materialized Views & Oracle Mirroring (Weeks 114–117)

**Purpose**: Oracle materialized views now have a direct equivalent in Fabric Warehouse. Generate `CREATE MATERIALIZED VIEW` statements and configure Oracle database mirroring for near-real-time replication.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Oracle MV definitions (DDL), refresh schedules, Oracle connection metadata |
| **Outputs** | Fabric Warehouse MV DDL, Mirroring configuration JSON, refresh schedule mapping |
| **Key Logic** | Parse Oracle `CREATE MATERIALIZED VIEW` → generate Fabric Warehouse `CREATE MATERIALIZED VIEW AS SELECT` with equivalent query; map Oracle `REFRESH FAST/COMPLETE/FORCE` to Fabric MV refresh modes; detect MV-eligible views in RPD physical layer; generate Fabric Mirroring setup for source Oracle databases (connection, table selection, replication config) |
| **Dependencies** | Phase 2 schema agent (complete), Phase 1 discovery (complete) |

**New modules:**
- `src/agents/schema/materialized_view_generator.py` — Oracle MV DDL parser, Fabric Warehouse MV generator, refresh mode mapping, MV dependency ordering
- `src/agents/schema/mirroring_config_generator.py` — Fabric Mirroring configuration: Oracle connection setup, table selection, replication schedule, retention policy

**Enhanced modules:**
- `src/agents/schema/ddl_generator.py` — Add MV DDL pass after table DDL
- `src/agents/discovery/rpd_parser.py` — Extract materialized view definitions from physical layer
- `src/agents/schema/type_mapper.py` — MV column type mappings (Oracle → Fabric Warehouse T-SQL types)

**Agent ownership:** Schema (02) + Discovery (01)

**Tests:** ~50 tests covering MV parsing, DDL generation, refresh mapping, mirroring config

---

#### Phase 55: Calculation Groups & DAX UDFs (Weeks 118–121)

**Purpose**: Generate TMDL Calculation Groups from OAC time intelligence patterns (AGO/TODATE/PERIODROLLING), and emit DAX User-Defined Functions for complex expressions that don't map cleanly to a single measure.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | RPD expression catalog, existing DAX translations, time intel patterns |
| **Outputs** | TMDL calculation group definitions, DAX UDF scripts, updated model.tmdl |
| **Key Logic** | Detect clusters of related time calculations (YTD, QTD, MTD, YoY, QoQ, MoM, Prior Year, Period Rolling) → emit a single `Time Intelligence` calculation group with SELECTEDMEASURE(); detect complex OAC expressions with confidence < 0.7 → generate DAX UDF with typed parameters; emit calculation group TMDL with `calculationItem` blocks and `precedence` ordering; set `discourageImplicitMeasures` on model |
| **Dependencies** | Phase 4 semantic agent (complete), Phase 48 DAX rules (complete) |

**New modules:**
- `src/agents/semantic/calc_group_generator.py` — Detect time-intel clusters, generate TMDL `calculationGroup` blocks, `calculationItem` DAX, precedence ordering, dynamic format strings
- `src/agents/semantic/dax_udf_generator.py` — Complex expression → DAX UDF with `DEFINE FUNCTION`, parameter type hints (Scalar, Table, ColumnRef), JSDoc documentation

**Enhanced modules:**
- `src/agents/semantic/tmdl_generator.py` — Emit `calculationGroups` section in model.tmdl, set `discourageImplicitMeasures`
- `src/agents/semantic/expression_translator.py` — Route recurring patterns to calc group instead of individual measures

**Agent ownership:** Semantic Model (04)

**Tests:** ~60 tests covering time-intel detection, calc group TMDL, UDF generation, precedence

---

#### Phase 56: BI Publisher → Paginated Reports (Weeks 122–125)

**Purpose**: Map OAC BI Publisher report templates (.xdo, .rtf, .xsl-fo) to Power BI Paginated Reports (.rdl) using Power BI Report Builder format.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | BI Publisher report definitions (XML data model, RTF/XSL-FO layout templates), OAC catalog |
| **Outputs** | .rdl paginated report files, embedded data source definitions, parameter mappings |
| **Key Logic** | Parse BI Publisher XML data model → extract SQL queries and parameters; map RTF template regions (header/detail/footer/groups) → RDL Tablix/Matrix/List regions; convert BI Publisher expressions to RDL expressions; map sub-reports and burst configurations; generate shared data sources pointing to Fabric Lakehouse SQL endpoint; map BI Publisher parameters → RDL report parameters |
| **Dependencies** | Phase 1 discovery (complete), Phase 2 schema (complete) |

**New modules:**
- `src/agents/report/bip_parser.py` — BI Publisher XML data model parser, RTF template extractor, XSL-FO layout parser
- `src/agents/report/rdl_generator.py` — RDL XML generator (Tablix, Matrix, Chart, List regions), data source embedding, parameter mapping, expression converter, page layout (portrait/landscape), grouping + sorting
- `src/agents/report/bip_expression_mapper.py` — BI Publisher XSL/XPath expressions → RDL expressions

**Enhanced modules:**
- `src/agents/discovery/oac_client.py` — Discover BI Publisher reports from OAC catalog (new `_CATALOG_TYPE_MAP` entry)
- `src/agents/report/report_agent.py` — Route BI Publisher assets to rdl_generator instead of pbir_generator

**Agent ownership:** Report (05) + Discovery (01)

**Tests:** ~55 tests covering BIP parsing, RDL generation, expression mapping, parameter conversion

---

#### Phase 57: Data Activator & Alert Migration (Weeks 126–128)

**Purpose**: Migrate OAC Agents and scheduled alerts to Fabric Data Activator (Reflex) triggers with conditions, actions, and notification rules.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | OAC Agent definitions (conditions, schedules, actions, recipients), alert thresholds |
| **Outputs** | Fabric Data Activator trigger definitions (JSON), Power Automate flow scaffolds, PBI data alert rules |
| **Key Logic** | Parse OAC Agent conditions (measure threshold, trend detection, schedule) → map to Data Activator trigger conditions; map OAC Agent actions (email, delivery channel, custom script) → Data Activator actions (Teams message, email, Power Automate flow); map OAC Agent schedules → Activator evaluation frequency; for simple threshold alerts on dashboards → generate PBI data-driven alert rules via REST API |
| **Dependencies** | Phase 1 discovery (complete), Phase 5 report agent (complete) |

**New modules:**
- `src/agents/report/alert_migrator.py` — OAC Agent parser, Data Activator trigger generator, Power Automate flow scaffolder, PBI data alert rule generator
- `src/agents/report/activator_config.py` — Data Activator Reflex item configuration (event streams, conditions, action templates)

**Enhanced modules:**
- `src/agents/discovery/oac_client.py` — Expand Agent/Alert metadata extraction (conditions, recipients, schedules)
- `src/deployers/fabric_deployer.py` — Deploy Data Activator Reflex items via Fabric REST API

**Agent ownership:** Report (05) + Orchestrator (08)

**Tests:** ~40 tests covering agent parsing, trigger generation, alert rules, flow scaffolds

---

#### Phase 58: Translytical Task Flows & Action Links (Weeks 129–131)

**Purpose**: Map OAC action links (navigate, drill, invoke script) to PBI Translytical Task Flows that enable users to take action directly from reports — write-back, record updates, external API calls.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | OAC action link definitions (navigate, invoke, HTTP), dashboard action configurations |
| **Outputs** | PBI drillthrough page configurations, Translytical task flow definitions (Fabric User Data Functions), Power Automate connector scaffolds |
| **Key Logic** | Classify OAC actions: navigation → drillthrough + bookmarks (already supported); invoke script → Translytical task flow with Fabric User Data Functions (write-back to Lakehouse/Warehouse/SQL Database); HTTP POST/GET → Power Automate connector scaffold; generate write-back UDF stubs with parameterized SQL (INSERT/UPDATE); link task flow to report visual buttons |
| **Dependencies** | Phase 5 report agent (complete), Phase 49 drillthrough (complete) |

**New modules:**
- `src/agents/report/task_flow_generator.py` — OAC action classifier, Translytical task flow definition generator, Fabric User Data Function stubs, write-back SQL templates
- `src/agents/report/action_link_mapper.py` — OAC action → PBI action type mapping (6 types), Power Automate HTTP connector scaffold

**Enhanced modules:**
- `src/agents/report/pbir_generator.py` — Embed task flow references in report visual button configs
- `src/agents/discovery/oac_client.py` — Extract action link definitions from OAC analysis metadata

**Agent ownership:** Report (05)

**Tests:** ~45 tests covering action classification, task flow generation, UDF stubs, button wiring

---

#### Phase 59: ETL Gap Closure — Pivot/Unpivot/Parallel (Weeks 132–134)

**Purpose**: Close remaining ETL migration gaps: Pivot/Unpivot transformations, parallel job chain branches, and error row routing.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | OAC Data Flow definitions with Pivot/Unpivot steps, job chain DAGs, error handling config |
| **Outputs** | Dataflow Gen2 M queries (pivot/unpivot), PySpark transformations, parallel pipeline branches, dead-letter error tables |
| **Key Logic** | Map OAC PIVOT step → M `Table.Pivot` / PySpark `pivot()` with aggregation; map OAC UNPIVOT → M `Table.UnpivotOtherColumns` / PySpark `unpivot()`; detect parallel branches in OAC job chains → emit Fabric pipeline parallel activities (ForEach with concurrency > 1); generate error row routing: rejected rows → dead-letter Delta table with error metadata; advanced DBMS_SCHEDULER expressions → Notebook job triggers with cron precision |
| **Dependencies** | Phase 3 ETL agent (complete), Phase 49 DLQ (complete) |

**New modules:**
- `src/agents/etl/pivot_unpivot_mapper.py` — Pivot/Unpivot → M query + PySpark, column detection, aggregation mapping
- `src/agents/etl/error_row_router.py` — Rejected row routing to dead-letter Delta table, error metadata enrichment

**Enhanced modules:**
- `src/agents/etl/step_mapper.py` — Add PIVOT, UNPIVOT step type handlers
- `src/agents/etl/fabric_pipeline_generator.py` — Parallel ForEach activity emission, concurrency settings
- `src/agents/etl/schedule_converter.py` — Full DBMS_SCHEDULER expression parser (intervals, windows, chains)

**Agent ownership:** ETL (03)

**Tests:** ~50 tests covering pivot/unpivot M + PySpark, parallel pipelines, error routing, scheduler precision

---

#### Phase 60: Incremental Discovery & Delta TMDL (Weeks 135–137)

**Purpose**: Enable delta crawl for large OAC environments (1000+ assets) using modification timestamps, and support incremental TMDL updates instead of full regeneration.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Previous inventory snapshot, OAC catalog `modifiedDate` fields, prior TMDL output |
| **Outputs** | Incremental inventory delta, merged TMDL files (add/modify/remove), change report |
| **Key Logic** | Query OAC catalog with `modifiedSince` filter → discover only changed assets; diff new inventory against previous snapshot → classify as ADDED/MODIFIED/DELETED; for TMDL: parse existing output folder, merge only changed tables/measures/relationships (preserve manual edits); generate human-readable change report (what was added/modified/removed); support `--full-crawl` flag to force complete rediscovery |
| **Dependencies** | Phase 1 discovery (complete), Phase 4 semantic (complete) |

**New modules:**
- `src/agents/discovery/incremental_crawler.py` — Delta crawl with `modifiedSince`, inventory diffing (ADDED/MODIFIED/DELETED), snapshot persistence
- `src/agents/semantic/tmdl_incremental.py` — TMDL folder parser, merge engine (additive + modify + tombstone), manual-edit preservation, change report

**Enhanced modules:**
- `src/clients/oac_catalog.py` — Add `modified_since` parameter to catalog discovery calls
- `src/agents/discovery/discovery_agent.py` — Route to incremental crawler when `--incremental` flag set
- `src/agents/semantic/semantic_agent.py` — Route to incremental TMDL when prior output exists

**Agent ownership:** Discovery (01) + Semantic Model (04)

**Tests:** ~55 tests covering delta crawl, inventory diff, TMDL merge, manual-edit preservation

---

#### Phase 61: Direct Lake Optimization & Modern Themes (Weeks 138–140)

**Purpose**: Generate Direct Lake semantic models on OneLake (GA March 2026), upgrade theme converter to Fluent 2 base theme, and map OAC custom aggregation to PBI visual calculations / custom totals.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Lakehouse table catalog, existing TMDL output, OAC theme/palette definitions, OAC custom agg configs |
| **Outputs** | Direct Lake TMDL (OneLake mode), Fluent 2 theme JSON (CY26SU03), visual calculation definitions |
| **Key Logic** | Detect Lakehouse Delta tables → generate TMDL with `mode: directLake` and OneLake storage; emit `expression` partitions pointing to Lakehouse SQL endpoint; upgrade `theme_converter.py` to emit Fluent 2 base: Segoe UI Variable, gray canvas (#F5F5F5), 1920×1080 default page, subtitles enabled; map OAC custom aggregation (weighted avg, custom total labels) → PBI visual calculations with `COLLAPSE`/`EXPAND` functions |
| **Dependencies** | Phase 2 schema (complete), Phase 49 theme converter (complete) |

**New modules:**
- `src/agents/semantic/direct_lake_generator.py` — Direct Lake TMDL emitter: OneLake mode, expression partitions, Lakehouse SQL endpoint wiring, table binding validation
- `src/agents/report/visual_calc_mapper.py` — OAC custom aggregation → PBI visual calculations (COLLAPSE, EXPAND, COLLAPSEALL, custom totals)

**Enhanced modules:**
- `src/agents/report/theme_converter.py` — Fluent 2 base theme (CY26SU03), named colors, page size in theme JSON, subtitle defaults
- `src/agents/semantic/tmdl_generator.py` — Emit DirectLake storage mode when Lakehouse target detected
- `src/agents/report/pbir_generator.py` — Embed visual calculation references in table/matrix visuals

**Agent ownership:** Semantic Model (04) + Report (05)

**Tests:** ~50 tests covering Direct Lake TMDL, OneLake binding, Fluent 2 theme, visual calculations

---

#### Phase 62: Advanced Security & Governance (Weeks 141–143)

**Purpose**: Close remaining security gaps — Microsoft Graph API for AAD group provisioning, dynamic RLS patterns, OLS with column masks, audit trail migration, and multi-valued session variable support.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | OAC app roles with members, OAC audit events, complex session variable filters |
| **Outputs** | AAD security group creation (via Graph API), enhanced RLS rules, OLS column masks, Fabric audit log entries |
| **Key Logic** | Use Microsoft Graph API to create/update AAD security groups matching OAC app roles → assign to Fabric workspace roles; detect complex multi-valued session variables → generate DAX RLS with `CONTAINSSTRING` / `PATHCONTAINS` patterns; map OAC column masks → OLS `metadataPermission` with column-level `DENY SELECT`; migrate OAC audit log events → Fabric unified audit log entries (via Fabric Admin REST API); generate audit compliance report (who had access to what, when) |
| **Dependencies** | Phase 6 security (complete), Phase 49 governance (complete) |

**New modules:**
- `src/agents/security/aad_group_provisioner.py` — Graph API client: create security groups, add members, assign to Fabric workspace roles, dry-run mode
- `src/agents/security/audit_trail_migrator.py` — OAC audit log parser, Fabric-compatible audit event mapping, compliance report generator
- `src/agents/security/dynamic_rls_generator.py` — Multi-valued session variable → complex DAX RLS (CONTAINSSTRING, PATHCONTAINS, nested OR), column mask mapping

**Enhanced modules:**
- `src/agents/security/role_mapper.py` — Integration with Graph API provisioner for automated group creation
- `src/agents/security/rls_converter.py` — Multi-valued variable support, dynamic hierarchy RLS
- `src/agents/security/ols_generator.py` — Column-level DENY SELECT, mask patterns

**Agent ownership:** Security (06)

**Tests:** ~50 tests covering Graph API mocking, dynamic RLS, audit parsing, column masks, compliance report

---

### v6.0 Coverage Impact

| Gap Category | Before (v5.0) | After (v6.0) | Phase |
|---|---|---|---|
| **Materialized Views** | ❌ Not supported | ✅ Fabric Warehouse MVs | 54 |
| **Oracle Replication** | ❌ Manual setup | ✅ Fabric Mirroring config | 54 |
| **Calculation Groups** | ❌ Not generated | ✅ TMDL calc groups | 55 |
| **DAX UDFs** | ❌ N/A | ✅ Complex expr → UDFs | 55 |
| **BI Publisher** | ❌ Not supported | ✅ Paginated Reports (.rdl) | 56 |
| **OAC Alerts/Agents** | 🟡 Discovered only | ✅ Data Activator triggers | 57 |
| **Action Links (write-back)** | 🟡 Drillthrough only | ✅ Translytical task flows | 58 |
| **Pivot/Unpivot ETL** | ❌ Not mapped | ✅ M + PySpark transforms | 59 |
| **Parallel job chains** | ❌ Sequential only | ✅ Parallel ForEach | 59 |
| **Error row routing** | ❌ Missing | ✅ Dead-letter Delta tables | 59 |
| **Incremental discovery** | ❌ Full re-crawl | ✅ Delta crawl | 60 |
| **Incremental TMDL** | ❌ Full regen | ✅ Merge engine | 60 |
| **Direct Lake on OneLake** | 🟡 Import mode | ✅ DirectLake TMDL | 61 |
| **Modern themes (Fluent 2)** | 🟡 CY24 theme | ✅ CY26 Fluent 2 | 61 |
| **Custom totals** | ❌ Not mapped | ✅ Visual calculations | 61 |
| **AAD group provisioning** | ❌ CSV only | ✅ Graph API automated | 62 |
| **Dynamic RLS** | 🟡 Simple patterns | ✅ Multi-valued + hierarchy | 62 |
| **Audit trail** | ❌ Not migrated | ✅ Fabric audit log | 62 |

**Coverage upgrade: 84% → 97% automated** (52 → 60 of 62 object types; remaining 2 = cell-level security and OAC custom plugins with no PBI API)

### Key Metrics v5.0 → v6.0 (projected)

| Metric | v5.0 (Phase 52) | v6.0 (Phase 62) |
|--------|-----------------|-----------------|
| Automated tests | 3,364 | ~3,900 |
| OAC object types automated | 52 / 62 (84%) | 60 / 62 (97%) |
| Expression rules | 120+ | 120+ (+ calc groups + UDFs) |
| Visual types | 80+ | 80+ (+ visual calcs) |
| ETL step types | 16 | 19 (+ Pivot/Unpivot/ErrorRoute) |
| Report formats | PBIR only | PBIR + Paginated (.rdl) |
| Security features | RLS + OLS + workspace roles | + AAD provisioning + dynamic RLS + audit trail |
| Storage modes | Import | Import + Direct Lake on OneLake |
| Replication | Manual | Fabric Mirroring (Oracle) |
| Theme version | CY24SU11 | CY26SU03 (Fluent 2) |

---

## v7.0 — Essbase to Fabric Migration (Phases 63–69)

**Goal**: Complete end-to-end Essbase cube migration to Microsoft Fabric with full fidelity — outline parsing, calc script/MDX translation, semantic model generation, security migration, Smart View → Excel migration, and write-back support.

**Status**: Core infrastructure **validated** — connector, semantic bridge, migration example, and Smart View Excel guide are complete and tested. Phases 63–69 define the production-grade pipeline for large-scale Essbase estates.

### Current Essbase Capabilities (Already Delivered)

| Capability | Module | Status | Tests |
|-----------|--------|--------|-------|
| Outline parsing (XML + JSON) | `src/connectors/essbase_connector.py` | ✅ Complete | 133 |
| Calc script → DAX (55+ rules) | `EssbaseCalcTranslator` | ✅ Complete | incl. |
| MDX → DAX (24+ rules) | `EssbaseMdxTranslator` | ✅ Complete | incl. |
| Outline → SemanticModelIR | `src/connectors/essbase_semantic_bridge.py` | ✅ Complete | 53 |
| TMDL generation (star schema) | Via SemanticModelIR → `tmdl_generator.py` | ✅ Complete | — |
| Filters → RLS roles | Semantic bridge | ✅ Complete | incl. |
| Substitution vars → What-if params | Semantic bridge | ✅ Complete | incl. |
| DDL generation (Lakehouse tables) | Via `ddl_generator.py` | ✅ Complete | — |
| Migration example (3 cubes) | `examples/essbase_migration_example.py` | ✅ Validated | — |
| Smart View → Excel guide | `SMART_VIEW_TO_EXCEL_MIGRATION.md` (780+ lines) | ✅ Complete | — |
| Write-back (Translytical) | `src/agents/report/task_flow_generator.py` | ✅ Complete | 21 |

### Migration Example Results (3 Sample Cubes)

| Cube | Dims | DAX Measures | TMDL Files | DDL Tables | RLS Roles | What-If Params |
|------|------|-------------|------------|------------|-----------|---------------|
| `simple_budget` | 3 | 10 | 10 | 3 | 0 | 0 |
| `medium_finance` | 5 | 19 | 12 | 5 | 1 | 2 |
| `complex_planning` | 7 | 43 | 14 | 7 | 3 | 5 |
| **Total** | — | **66** | **36** | **15** | **4** | **7** |

Output artifacts: `output/essbase_migration/` (TMDL semantic models, DDL scripts, migration report)

### Documentation Suite

| Document | Lines | Purpose |
|----------|-------|---------|
| `ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md` | 250+ | Architecture & 7-phase roadmap (Phases 63–69) |
| `ESSBASE_MIGRATION_PLAYBOOK.md` | 728 | 9-step executable migration guide with verified examples |
| `SMART_VIEW_TO_EXCEL_MIGRATION.md` | 780+ | Smart View → Excel migration (11 sections, CUBE formula recipes) |
| `examples/essbase_migration_example.py` | 180+ | End-to-end pipeline for all 3 sample cubes |

### Remaining Phases (Production Pipeline)

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 63 | Essbase Discovery & Inventory Agent | 📋 Proposed | REST API client enhancements, outline crawl, complexity scoring, inventory Delta tables |
| 64 | Essbase Data Extract & Staging | 📋 Proposed | MaxL/MDX extractors, hierarchical member export, sparse/dense detection, staging layer |
| 65 | Essbase Schema & Normalization | 📋 Proposed | Star schema designer, dimension/fact DDL, storage mode advisor |
| 66 | Essbase ETL & Transform Pipeline | 📋 Proposed | Dimension/fact loading notebooks, hierarchy handling, incremental detection |
| 67 | Essbase Semantic Model & DAX | 📋 Proposed | TMDL gen enhancements, calc→DAX expansion to 100+ rules, what-if, time intelligence |
| 68 | Essbase Security & Governance | 📋 Proposed | Filter→RLS/OLS converters, user provisioning, Graph API group sync |
| 69 | Essbase Validation & UAT | 📋 Proposed | Data reconciliation, measure validation, security verification, performance benchmarks |

---

## v8.0 — Multi-Agent Intelligence (Phases 70–76)

**Goal**: Evolve the 8 deterministic migration agents into LLM-powered autonomous agents with reasoning, memory, inter-agent communication, and self-healing — turning the platform from a rule-execution engine into an AI-driven migration advisor that can handle novel migration patterns, self-correct errors, and adapt to each customer's environment without code changes.

**Architecture evolution**: Currently agents follow hardcoded rules (120+ DAX mappings, type maps, visual maps) with LLM fallback only for low-confidence translations (Phase 12). v8.0 gives each agent an **LLM reasoning loop** that wraps around the existing rule engine — rules still fire first (fast, deterministic), but the LLM handles planning, error diagnosis, cross-agent negotiation, and novel patterns that no rule covers.

**Why now**: Azure OpenAI GPT-4.1 (GA April 2025) provides the reasoning quality needed. Fabric Copilot APIs (GA March 2026) enable in-Fabric agent actions. The existing `hybrid_translator.py` (rules-first + LLM fallback) proves the pattern works at the translation level — v8.0 lifts it to the full agent lifecycle.

### Architecture Diagram

```
                        ┌────────────────────────┐
                        │  Intelligent           │
                        │  Orchestrator (08+)    │
                        │  ┌──────────────────┐  │
                        │  │ AI Wave Planner  │  │
                        │  │ Resource Optimizer│  │
                        │  │ Adaptive Scheduler│  │
                        │  └──────────────────┘  │
                        └───────────┬────────────┘
                                    │ structured handoff messages
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
    ┌───────▼────────┐     ┌───────▼────────┐     ┌───────▼────────┐
    │  Agent (01–06) │     │  Agent (01–06) │     │  Agent (01–06) │
    │  ┌───────────┐ │     │  ┌───────────┐ │     │  ┌───────────┐ │
    │  │ LLM       │ │     │  │ LLM       │ │     │  │ LLM       │ │
    │  │ Reasoning │ │     │  │ Reasoning │ │     │  │ Reasoning │ │
    │  │ Loop      │ │     │  │ Loop      │ │     │  │ Loop      │ │
    │  └─────┬─────┘ │     │  └─────┬─────┘ │     │  └─────┬─────┘ │
    │        │       │     │        │       │     │        │       │
    │  ┌─────▼─────┐ │     │  ┌─────▼─────┐ │     │  ┌─────▼─────┐ │
    │  │ Rule      │ │     │  │ Rule      │ │     │  │ Rule      │ │
    │  │ Engine    │ │     │  │ Engine    │ │     │  │ Engine    │ │
    │  │ (existing)│ │     │  │ (existing)│ │     │  │ (existing)│ │
    │  └───────────┘ │     │  └───────────┘ │     │  └───────────┘ │
    │  ┌───────────┐ │     │  ┌───────────┐ │     │  ┌───────────┐ │
    │  │ Agent     │ │     │  │ Agent     │ │     │  │ Agent     │ │
    │  │ Memory    │ │     │  │ Memory    │ │     │  │ Memory    │ │
    │  └───────────┘ │     │  └───────────┘ │     │  └───────────┘ │
    └────────────────┘     └────────────────┘     └────────────────┘
            │                       │                       │
    ┌───────▼───────────────────────▼───────────────────────▼──────┐
    │            Shared Memory Store (Lakehouse Delta)              │
    │  agent_memory │ handoff_messages │ escalation_queue           │
    └──────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Rules first, LLM second** — deterministic rules stay as the fast path; LLM handles the long tail
2. **Confidence-gated execution** — actions below confidence threshold route to human review
3. **Agent memory** — each agent accumulates context within and across migrations
4. **Structured handoffs** — agents communicate via typed messages, not free text
5. **Cost control** — LLM calls are batched, cached, and budget-capped per agent per wave
6. **Observability** — every LLM decision is logged with reasoning chain, tokens used, and latency

### Platform Features Leveraged

| Feature | Status | Unblocks |
|---------|--------|----------|
| **Azure OpenAI GPT-4.1** | GA | Agent reasoning, planning, code generation |
| **Azure AI Agent Service** | GA | Hosted agent runtime, tool-use protocol, memory |
| **Fabric Copilot APIs** | GA (March 2026) | In-Fabric actions (create items, deploy, configure) |
| **Semantic Kernel** | GA 1.x | Agent orchestration, plugin system, memory connectors |
| **Prompt Flow** | GA | LLM pipeline evaluation, A/B testing, monitoring |
| **Azure AI Content Safety** | GA | Output filtering for generated code/DAX |

### Phase Summary

| Phase | Name | Weeks | Key Deliverables | New Tests |
|-------|------|-------|------------------|-----------|
| 70 | Agent Intelligence Framework | 161–164 | LLM reasoning loop, agent memory, tool-use protocol, cost controls | 90 |
| 71 | Autonomous Discovery & Assessment | 165–167 | AI-powered crawl, anomaly detection, strategy recommendation | ~75 |
| 72 | Autonomous Translation Agents | 168–171 | LLM schema/ETL/semantic translation, multi-strategy, self-correction | ~90 |
| 73 | Agent Communication Protocol | 172–173 | Structured handoffs, negotiation, conflict resolution, shared context | ~70 |
| 74 | Self-Healing Migration Pipeline | 174–176 | Error diagnosis, auto-fix, alternative strategies, regression guard | ~80 |
| 75 | Human-in-the-Loop Escalation | 177–178 | Confidence routing, approval UI, interactive review, feedback loop | ~60 |
| 76 | Intelligent Orchestration & Optimization | 179–180 | AI wave planning, resource optimization, adaptive scheduling, cost modeling | ~75 |

**Total new tests**: ~530 | **Cumulative**: ~4,500 (3,760 actual after Phase 70 + Tooling)

### Phase Details

#### Phase 70: Agent Intelligence Framework (Weeks 161–164)

**Purpose**: Build the shared intelligence layer that all 8 agents use — an LLM reasoning loop that wraps around each agent's existing rule engine, plus a persistent memory store for cross-task learning.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Existing agent lifecycle (discover → plan → execute → validate), Azure OpenAI config |
| **Outputs** | `IntelligentAgent` mixin, `AgentMemory` store, `ReasoningLoop` executor, `ToolRegistry` protocol |
| **Key Logic** | Each agent gets a `ReasoningLoop` that (1) receives the current task context, (2) decides whether rules suffice or LLM reasoning is needed, (3) if LLM: constructs a prompt with agent memory + task context + tool definitions, (4) executes the LLM plan step-by-step, (5) validates each step's output, (6) persists decisions to memory for future tasks. Cost control: per-agent token budgets, response caching (semantic dedup), batch mode for bulk operations. |
| **Dependencies** | Phase 12 LLM client (complete), Phase 17 agent registry (complete) |

**New modules:**
- `src/core/intelligence/reasoning_loop.py` — ReasoningLoop: task→prompt→LLM→plan→execute→validate cycle; supports ReAct (Reason+Act) pattern; step-level retry with backoff; observation logging
- `src/core/intelligence/agent_memory.py` — AgentMemory: per-agent persistent memory (Lakehouse-backed); stores decisions, patterns learned, error resolutions; vector-indexed for semantic retrieval; TTL-based eviction for stale entries
- `src/core/intelligence/tool_registry.py` — ToolRegistry: typed tool definitions (name, description, parameters, return type); tools = existing agent methods exposed to LLM; schema validation on tool calls; permission scoping per agent
- `src/core/intelligence/cost_controller.py` — Token budget per agent per wave; request batching (group similar translations); semantic cache (embedding-based dedup of similar prompts); cost logging to `agent_logs` Delta table
- `src/core/intelligence/prompt_builder.py` — Domain-specific prompt templates per agent; system prompts with agent role + file ownership rules from AGENTS.md; few-shot examples from translation catalog; context window management (priority-based truncation)

**Enhanced modules:**
- `src/core/base_agent.py` — Add `IntelligentMixin` with optional `reasoning_loop` injection; backward-compatible (agents work without LLM)
- `src/core/llm_client.py` — Add structured output mode (JSON schema enforcement), streaming, token counting
- `src/core/config.py` — Add `[intelligence]` config section: model, temperature, token budgets, cache TTL

**Agent ownership:** Orchestrator (08) — shared infrastructure

**Tests:** 90 tests covering reasoning loop, memory CRUD, tool registry, cost controls, prompt building, cache hits

---

### Practical Migration Tooling (interlude between Phase 70 and 71) ✅ COMPLETE

**Purpose**: Before proceeding with LLM-powered autonomous agents (Phases 71–76), deliver practical validation and testing tooling that catches real migration bugs *today* — a prerequisite for safe AI-assisted translation.

**Rationale**: The DAX validator immediately caught a real bug in Essbase output (nested bracket column references). These tools must exist before Phase 72 (Autonomous Translation) because LLMs will generate plausible-but-broken DAX, and without syntax validation there's no feedback loop.

| Tool | Module | Status | Tests |
|------|--------|--------|-------|
| **DAX Deep Validator** | `src/tools/dax_validator.py` | ✅ Complete | 33 |
| **TMDL File-System Validator** | `src/tools/tmdl_file_validator.py` | ✅ Complete | 11 |
| **Data Reconciliation CLI** | `src/tools/reconciliation_cli.py` | ✅ Complete | 22 |
| **OAC API Test Harness** | `src/tools/oac_test_harness.py` | ✅ Complete | 24 |
| **Fabric Deployment Dry-Run** | `src/tools/fabric_dry_run.py` | ✅ Complete | 11 |
| **Total** | 5 new modules | ✅ | **101 tests** |

**Key capabilities delivered:**

- **DAX validator** (14 error codes DAX001–DAX014): Tokenizer with function/keyword/column-ref classification, balanced parentheses + brackets, VAR/RETURN pairing, IF/DIVIDE argument counts, iterator anti-patterns (SUMX→SUM), nested aggregation detection, excessive nesting warnings, deprecated function alerts, batch TMDL measure validation, directory-level validation
- **TMDL file-system validator**: Validates real output directories (SemanticModel/definition/tables/*.tmdl), checks .platform JSON, model declaration, lineageTags, integrated DAX validation per measure, cross-reference relationship checking, DDL validation
- **Data reconciliation CLI**: OfflineReconciler (JSON snapshot comparison), ReconciliationRunner (live DB with pluggable executors), tolerance support, Markdown + JSON report generators
- **OAC API test harness**: VCR-style cassette recording/playback, MockOACServer (synthetic responses), rate-limit + pagination cassette generators, assertion helpers (call sequence, duplicate detection)
- **Fabric deployment dry-run**: Artifact scanning, Fabric naming rules (length, chars, reserved names), deployment order computation, cross-dependency validation, JSON manifest export

**Bug discovered:** Essbase DAX generator produces nested bracket references (`'Fact'[Revenue]]`) — caught by DAX002 validation. Tracked for fix.

**Test suite totals:** 3,760 passed (up from 3,659)

---

#### Phase 71: Autonomous Discovery & Assessment (Weeks 165–167)

**Purpose**: Upgrade the Discovery Agent (01) with LLM reasoning so it can autonomously assess migration complexity, detect anomalies in source metadata, recommend migration strategies, and generate executive-ready assessment reports.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | OAC catalog, RPD XML, inventory, agent memory from prior migrations |
| **Outputs** | Enriched inventory with AI annotations, risk heat map, strategy recommendations, assessment narrative |
| **Key Logic** | After rule-based discovery (Phase 1 — unchanged), the LLM reviews the inventory and: (1) classifies each asset's migration complexity using patterns learned from prior migrations; (2) detects anomalies — orphaned tables, circular dependencies, unusually large models, suspicious security patterns; (3) recommends migration strategy per asset group (lift-and-shift vs. refactor vs. rebuild); (4) generates a natural-language assessment report for stakeholders; (5) suggests wave grouping based on business domain analysis (not just dependency depth) |
| **Dependencies** | Phase 70 intelligence framework, Phase 1 discovery (complete), Phase 35 complexity analyzer (complete) |

**New modules:**
- `src/agents/discovery/ai_assessor.py` — LLM-powered complexity assessment: reviews inventory + dependency graph → classifies migration difficulty (simple/medium/complex/manual); detects anomalies; generates risk heat map; recommends strategy per asset group
- `src/agents/discovery/strategy_recommender.py` — Migration strategy engine: lift-and-shift (direct mapping exists), refactor (partial mapping + optimization), rebuild (no mapping, requires redesign); uses agent memory to improve with each migration
- `src/agents/discovery/assessment_narrator.py` — Natural language report generator: executive summary, technical findings, risk register, recommended timeline; uses LLM to produce professional prose from structured assessment data

**Enhanced modules:**
- `src/agents/discovery/discovery_agent.py` — Add `assess()` step after `discover()` that invokes AI assessor
- `src/agents/discovery/complexity_scorer.py` — Feed ML-enhanced complexity signals alongside rule-based scores

**Agent ownership:** Discovery (01)

**Tests:** ~75 tests covering AI assessment, anomaly detection, strategy recommendation, narrative generation

---

#### Phase 72: Autonomous Translation Agents (Weeks 168–171)

**Purpose**: Upgrade Schema (02), ETL (03), and Semantic Model (04) agents with LLM-powered translation that handles the long tail of unmappable patterns — complex PL/SQL, nested OAC expressions, exotic data types, and customer-specific customizations.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Source expressions/DDL/data flows, existing rule catalog, translation cache, agent memory |
| **Outputs** | Translated artifacts with higher coverage, self-corrected translations, new rules learned |
| **Key Logic** | For each translation task: (1) attempt rule-based translation (existing 120+ rules); (2) if confidence < threshold → invoke LLM with few-shot examples from translation catalog; (3) LLM generates candidate translation + explanation; (4) validate output syntax (DAX parser, SQL parser, PySpark lint); (5) if validation fails → LLM retries with error message (up to 3 attempts); (6) if succeeds → optionally extract new rule from successful translation (rule distillation); (7) persist to translation cache for future identical/similar patterns |
| **Dependencies** | Phase 70 intelligence framework, Phase 34 translation catalog (complete), Phase 20 advanced translation (complete) |

**New modules:**
- `src/core/intelligence/translation_agent.py` — IntelligentTranslator: wraps `HybridTranslator` with multi-strategy fallback (rules → cached similar → LLM → LLM with different prompt → escalate); syntax validation per target language; confidence re-scoring after LLM translation
- `src/core/intelligence/rule_distiller.py` — Extracts new deterministic rules from successful LLM translations: pattern detection → rule template → test case generation → human review queue; grows the rule catalog over time
- `src/core/intelligence/syntax_validators.py` — Pluggable validators: DAX (AST parse), T-SQL (sqlparse), PySpark (ast.parse), M query (bracket matching + keyword validation); returns structured error for LLM retry

**Enhanced modules:**
- `src/agents/schema/sql_translator.py` — Route to IntelligentTranslator for complex DDL constructs
- `src/agents/etl/plsql_translator.py` — Route to IntelligentTranslator for complex PL/SQL
- `src/agents/semantic/expression_translator.py` — Route to IntelligentTranslator for complex OAC expressions
- `src/core/translation_cache.py` — Add embedding-based similarity search (not just exact match)

**Agent ownership:** Schema (02) + ETL (03) + Semantic Model (04)

**Tests:** ~90 tests covering multi-strategy fallback, syntax validation, rule distillation, cache similarity, LLM retry

---

#### Phase 73: Agent Communication Protocol (Weeks 172–173)

**Purpose**: Replace the current implicit data-passing (Delta table reads) with a formal **structured handoff protocol** so agents can negotiate, share context, raise cross-domain issues, and resolve conflicts.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Agent task results, cross-agent dependencies, shared context |
| **Outputs** | Typed handoff messages, negotiation logs, conflict resolution records |
| **Key Logic** | Define `HandoffMessage` schema (sender_agent, receiver_agent, message_type, payload, priority, requires_response); message types: ARTIFACT_READY (agent finished, artifact available), DEPENDENCY_REQUEST (need data from another agent), CONFLICT (incompatible decisions — e.g., Schema chose Import mode but Semantic wants DirectLake), CONTEXT_SHARE (background info for downstream), ESCALATION (can't resolve, needs human). Agents use LLM to generate and interpret context-rich handoff messages instead of raw data structures. |
| **Dependencies** | Phase 70 intelligence framework, Phase 17 agent wiring (complete) |

**New modules:**
- `src/core/intelligence/handoff_protocol.py` — HandoffMessage dataclass, MessageBus (Lakehouse `handoff_messages` Delta table), message routing (agent_id → inbox), priority queue, acknowledgment protocol
- `src/core/intelligence/conflict_resolver.py` — Detects cross-agent conflicts (e.g., storage mode disagreement between Schema and Semantic agents); uses LLM to propose resolution; escalates to human if confidence < threshold
- `src/core/intelligence/context_window.py` — Shared context builder: aggregates relevant context from all upstream agents into a priority-ranked window that fits within token limits; includes: inventory summary, mapping decisions, warnings, validation results

**Enhanced modules:**
- `src/core/state_coordinator.py` — Integrate HandoffMessage routing into lifecycle hooks
- `src/agents/orchestrator/orchestrator_agent.py` — Process handoff messages between waves; route conflicts to resolver
- `src/core/base_agent.py` — Add `send_handoff()` / `receive_handoffs()` methods

**Agent ownership:** Orchestrator (08)

**Tests:** ~70 tests covering message routing, conflict detection, resolution, context window, priority queuing

---

#### Phase 74: Self-Healing Migration Pipeline (Weeks 174–176)

**Purpose**: Build an automated error diagnosis and repair system so migration failures trigger intelligent recovery instead of manual debugging — the agent identifies what went wrong, proposes a fix, validates it, and re-runs only the affected items.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Failed migration tasks, error messages, agent logs, validation failures |
| **Outputs** | Diagnosed error categories, auto-fix patches, re-run results, healing report |
| **Key Logic** | When an agent task fails: (1) capture full error context (traceback, input data, agent state, prior decisions); (2) LLM diagnoses root cause from error patterns (type mismatch, missing dependency, syntax error, permission issue, API limit, data quality); (3) select repair strategy based on diagnosis: for translation errors → re-translate with different approach; for schema errors → adjust type mapping; for deployment errors → retry with backoff or fallback config; for data quality → quarantine and continue; (4) apply fix to affected items only (not full re-run); (5) validate fix; (6) if fix fails → try next strategy (up to 3); (7) persist diagnosis + resolution to agent memory for future learning |
| **Dependencies** | Phase 70 intelligence framework, Phase 73 communication protocol |

**New modules:**
- `src/core/intelligence/error_diagnostician.py` — Error pattern classifier: maps exceptions + context to diagnosis categories (15+ categories); uses LLM for novel errors; maintains a known-error database that grows over migrations
- `src/core/intelligence/repair_strategies.py` — Strategy catalog: RetranslateStrategy, AdjustTypeMappingStrategy, RetryWithBackoffStrategy, QuarantineStrategy, FallbackConfigStrategy, SkipAndContinueStrategy; each strategy is a pluggable class with `can_handle()` / `repair()` / `validate()`
- `src/core/intelligence/healing_engine.py` — Coordinates diagnosis → strategy selection → repair → validation → memory persistence; generates healing report (what broke, why, how it was fixed)
- `src/core/intelligence/regression_guard.py` — Before applying a fix, checks that it doesn't break previously passing items; runs targeted validation on affected scope

**Enhanced modules:**
- `src/agents/orchestrator/orchestrator_agent.py` — Integrate healing engine into failure path (before escalation to human)
- `src/core/resilience.py` — Add circuit breaker awareness of healing engine (don't circuit-break if auto-fix is in progress)

**Agent ownership:** Orchestrator (08) + Validation (07)

**Tests:** ~80 tests covering error diagnosis, repair strategies, regression guard, healing report, memory persistence

---

#### Phase 75: Human-in-the-Loop Escalation (Weeks 177–178)

**Purpose**: Build the escalation path for when AI agents can't resolve an issue autonomously — confidence-based routing to human reviewers with interactive UI, contextual explanations, and feedback that improves future agent decisions.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Low-confidence translations, unresolved conflicts, healing failures, novel patterns |
| **Outputs** | Review queue, interactive review UI, approved/rejected decisions, feedback loop |
| **Key Logic** | Escalation triggers: (1) translation confidence < 0.5 after LLM attempt; (2) conflict resolver confidence < 0.6; (3) healing engine exhausted all strategies; (4) agent explicitly marks item as "needs human review". Review queue: each item has context (source, proposed translation, confidence, LLM reasoning chain, similar items). Reviewer can: approve, reject + provide correct answer, skip, or mark as "out of scope". Feedback loop: approved decisions → translation cache + rule distiller; rejected decisions → negative examples in prompt templates. |
| **Dependencies** | Phase 70 intelligence framework, Phase 73 communication protocol, Phase 74 self-healing |

**New modules:**
- `src/core/intelligence/escalation_manager.py` — EscalationManager: routes items to review queue based on confidence thresholds; priority scoring (business impact × complexity); SLA tracking per escalation
- `src/core/intelligence/review_queue.py` — ReviewQueue: FIFO with priority override; persistent (Lakehouse Delta); supports batch approve/reject; tracks reviewer identity and timestamp
- `src/api/routes/review.py` — REST API endpoints: GET /review/queue, POST /review/{id}/approve, POST /review/{id}/reject, GET /review/stats; WebSocket for real-time queue updates
- `src/core/intelligence/feedback_loop.py` — Processes reviewer decisions: approved → add to translation cache + trigger rule distillation; rejected → add negative example to prompt builder; track reviewer accuracy over time

**Enhanced modules:**
- `src/api/main.py` — Register review router
- `dashboard/src/` — Add review queue page (table with source/proposed/confidence, approve/reject buttons, context panel)
- `src/core/intelligence/prompt_builder.py` — Incorporate negative examples from rejected reviews

**Agent ownership:** Orchestrator (08)

**Tests:** ~60 tests covering escalation triggers, queue management, API endpoints, feedback loop, reviewer metrics

---

#### Phase 76: Intelligent Orchestration & Optimization (Weeks 179–180)

**Purpose**: Upgrade the Orchestrator Agent (08) to use LLM reasoning for wave planning, resource allocation, adaptive scheduling, and migration cost optimization — replacing the current heuristic-based wave planner with an AI planner that learns from each migration.

| Attribute | Detail |
|-----------|--------|
| **Inputs** | Enriched inventory (Phase 71), agent capacity, Fabric capacity SKU, prior migration history |
| **Outputs** | Optimized wave plan, resource allocation schedule, cost projection, adaptive schedule adjustments |
| **Key Logic** | (1) AI wave planner: analyzes inventory by business domain (not just dependency depth) — groups related assets so validation is meaningful per wave; considers agent parallelism and Fabric capacity limits; (2) resource optimizer: allocates Fabric CU budget across agents based on workload profile (discovery = low CU, ETL = high CU, semantic = medium CU); (3) adaptive scheduler: monitors agent execution speed in real-time → adjusts remaining wave estimates → rebalances if an agent is bottlenecked; (4) cost modeler: predicts total migration cost (LLM tokens + Fabric CU-hours + human review hours) using historical data from agent memory |
| **Dependencies** | Phase 70 intelligence framework, Phase 71 autonomous discovery, Phase 73 communication |

**New modules:**
- `src/agents/orchestrator/ai_wave_planner.py` — LLM-powered wave planner: business domain grouping, agent capacity modeling, blast radius optimization, what-if simulation (preview wave plans before execution)
- `src/agents/orchestrator/resource_optimizer.py` — Fabric capacity allocation: maps agent workloads to CU requirements; monitors CU consumption in real-time; suggests capacity scaling (pause/resume, scale up/down)
- `src/agents/orchestrator/adaptive_scheduler.py` — Real-time schedule adjustment: tracks agent velocity (items/hour); detects bottlenecks; redistributes work or adjusts wave boundaries; notifies stakeholders of timeline changes
- `src/agents/orchestrator/cost_modeler.py` — Migration cost projection: LLM token cost per phase, Fabric CU cost per wave, human review cost per escalation; uses historical data from agent memory; generates cost breakdown report

**Enhanced modules:**
- `src/agents/orchestrator/wave_planner.py` — Add `use_ai_planner` flag; delegate to `ai_wave_planner` when enabled
- `src/agents/orchestrator/orchestrator_agent.py` — Integrate adaptive scheduler into wave execution loop; add cost tracking

**Agent ownership:** Orchestrator (08)

**Tests:** ~75 tests covering AI wave planning, resource allocation, adaptive scheduling, cost modeling, what-if simulation

---

### v8.0 Intelligence Impact

| Capability | Before (v6.0) | After (v8.0) |
|---|---|---|
| **Translation coverage** | 120+ rules + LLM fallback | 120+ rules + intelligent multi-strategy + rule distillation |
| **Novel pattern handling** | Manual rule addition | Autonomous LLM translation + auto-rule extraction |
| **Error recovery** | Manual debugging + retry | Automated diagnosis → repair → validate cycle |
| **Migration assessment** | Rule-based complexity score | AI reasoning + anomaly detection + strategy recommendation |
| **Wave planning** | Heuristic (dependency depth) | AI domain-aware grouping + capacity optimization |
| **Cross-agent coordination** | Implicit data passing | Structured handoffs + conflict resolution |
| **Human involvement** | Always required for low confidence | Only for genuinely ambiguous items |
| **Cost visibility** | Post-hoc estimation | Real-time cost projection + optimization |
| **Learning across migrations** | None (stateless) | Agent memory → improves with each migration |

### Key Metrics v6.0 → v8.0 (projected)

| Metric | v6.0 (Phase 62) | v8.0 (Phase 76) |
|--------|-----------------|-----------------|
| Automated tests | ~3,900 | ~4,500 |
| Translation confidence (avg) | 0.82 | 0.93 |
| Auto-resolved failures | 0% | ~70% |
| Human review items (per 1000 assets) | ~150 | ~40 |
| Novel patterns auto-handled | 0% | ~60% |
| Migration planning time | Hours (manual) | Minutes (AI-generated) |
| Cost prediction accuracy | N/A | ±15% |
| Rules auto-distilled per migration | 0 | ~10–20 new rules |

### Technology Choices

| Component | Technology | Rationale |
|---|---|---|
| LLM backbone | Azure OpenAI GPT-4.1 | Best reasoning quality, structured output, Azure-native |
| Agent framework | Semantic Kernel 1.x (Python) | Plugin system, memory connectors, planner abstraction |
| Memory store | Lakehouse Delta + Azure AI Search (vector) | Hybrid: structured queries + semantic similarity |
| Prompt management | Prompt Flow | Version control, A/B testing, evaluation pipelines |
| Content safety | Azure AI Content Safety | Filter generated code for injection/malicious patterns |
| Cost tracking | Azure Monitor + custom metrics | Token usage, CU consumption, latency per agent |

### Risk Register (v8.0 Specific)

| ID | Risk | Mitigation |
|----|------|-----------|
| R13 | LLM cost overrun | Per-agent token budgets, response caching, batch mode, cost alerts |
| R14 | LLM hallucination in translations | Syntax validation, golden test regression, dual-check (rules + LLM) |
| R15 | Agent memory pollution | TTL eviction, human review of auto-distilled rules, memory quality scores |
| R16 | Latency increase from LLM calls | Rules-first (cache hit = 0ms), LLM calls only for misses, async execution |
| R17 | Prompt injection via source metadata | Input sanitization, content safety filter, system prompt hardening |
| R18 | Over-reliance on LLM (fragile) | Graceful degradation — if LLM unavailable, fall back to rule-only mode |

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
| Essbase Proposal | `ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md` | Essbase migration architecture (v7.0) |
| Essbase Playbook | `ESSBASE_MIGRATION_PLAYBOOK.md` | Step-by-step Essbase migration guide |
| Smart View Guide | `SMART_VIEW_TO_EXCEL_MIGRATION.md` | Smart View → Excel on Semantic Model |

---

*Consolidated from DEV_PLAN.md (Phases 0–8), DEV_PLAN_V2 (Phases 9–15), DEV_PLAN_V3 (Phases 16–22), DEV_PLAN_V4 (Phases 23–30), DEV_PLAN_V5 (Phases 31–38), v4.0 roadmap (Phases 39–46), v4.1 T2P gap (Phase 47), v4.2 parity (Phase 48), v4.3 hardening (Phase 49), v5.0 roadmap (Phases 50–53), v6.0 full coverage upgrade (Phases 54–62), v7.0 Essbase to Fabric (Phases 63–69), and v8.0 Multi-Agent Intelligence (Phases 70–76).*

| 63 | Essbase Discovery & Inventory Agent | 📋 Proposed | Essbase REST API client, outline XML parser, complexity scoring, inventory Delta tables |
| 64 | Essbase Data Extract & Staging | 📋 Proposed | MaxL/MDX extractors, hierarchical member export, sparse/dense dimension detection, staging layer |
| 65 | Essbase Schema & Normalization | 📋 Proposed | Star schema designer, dimension + fact DDL, Fabric naming conventions, storage mode advisor |
| 66 | Essbase ETL & Transform Pipeline | 📋 Proposed | Dimension/fact loading notebooks, hierarchy handling, incremental detection, refresh scheduling |
| 67 | Essbase Semantic Model & DAX | 📋 Proposed | TMDL generation, calc→DAX translator (100+ rules), hierarchy generation, what-if parameters |
| 68 | Essbase Security & Governance | 📋 Proposed | Filter→RLS/OLS converters, user provisioning, role mapping, security test suite |
| 69 | Essbase Validation & UAT | 📋 Proposed | Data reconciliation, measure validation, security verification, performance benchmarking, UAT workflow |
| 70 | Agent Intelligence Framework | ✅ Complete | LLM reasoning loop, agent memory store, tool-use protocol, confidence-gated execution |
| 71 | Autonomous Discovery & Assessment | 📋 Proposed | AI-powered crawl decisions, anomaly detection, complexity reasoning, migration strategy recommendation |
| 72 | Autonomous Translation Agents | 📋 Proposed | LLM-powered schema/ETL/semantic translation, multi-strategy fallback, self-correction |
| 73 | Agent Communication Protocol | 📋 Proposed | Structured handoff messages, negotiation, conflict resolution, shared context window |
| 74 | Self-Healing Migration Pipeline | 📋 Proposed | Error diagnosis, auto-fix strategies, retry with alternative approach, regression guard |
| 75 | Human-in-the-Loop Escalation | 📋 Proposed | Confidence routing, approval workflows, interactive review UI, feedback learning |
| 76 | Intelligent Orchestration & Optimization | 📋 Proposed | AI wave planning, resource optimization, adaptive scheduling, migration cost modeling |
