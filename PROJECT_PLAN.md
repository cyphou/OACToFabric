# Master Project Plan — OAC to Microsoft Fabric & Power BI Migration

> **Framework Status**: v4.1.0 — Phases 0–47 complete (2,784 tests passing)  
> **Current Milestone**: v5.0.0 — Intelligent Platform (Phases 48–50)  
> **Next Milestone**: v5.0.0 GA  
> **Last Updated**: 2026-03-26

## 1. Executive Summary

This project delivers an **automated, multi-agent migration framework** that converts an Oracle Analytics Cloud (OAC) estate — including data models, ETL pipelines, semantic layers, reports, dashboards, and security policies — into equivalent assets on **Microsoft Fabric** (Lakehouse, Data Warehouse, Data Factory, Notebooks) and **Power BI** (Semantic Models, Reports, Dashboards).

### Migration Scope Map

| OAC Component | Target in Microsoft Fabric / Power BI |
|---|---|
| Oracle Database schemas | Fabric Lakehouse / Warehouse (via PostgreSQL or direct) |
| OAC Data Models (RPD / Logical Layer) | Fabric Lakehouse tables + Power BI Semantic Models (TMDL) |
| OAC Data Flows / ETL | Fabric Data Factory Pipelines + Dataflows Gen2 + Notebooks |
| OAC Analyses & Dashboards | Power BI Reports (.pbip / .pbir) |
| OAC Prompts & Filters | Power BI Slicers, Parameters, Bookmarks |
| OAC Agents / Alerts | Power BI Data Alerts + Fabric Data Activator |
| OAC Catalog & Subject Areas | Power BI Semantic Model perspectives + Fabric domains |
| OAC Security (App Roles, Row-Level) | Fabric Workspace Roles + Power BI RLS/OLS |
| OAC Connections & Data Sources | Fabric Connections + Gateway configurations |

---

## 2. Migration Strategy

### 2.1 Approach: **Phased Parallel Migration**

We adopt a **wave-based** migration approach:

- **Wave 0 — Foundation**: Set up Fabric workspace, connections, governance.
- **Wave 1 — Data Layer**: Migrate schemas, data, ETL pipelines.
- **Wave 2 — Semantic Layer**: Convert OAC RPD/logical models to Power BI Semantic Models.
- **Wave 3 — Presentation Layer**: Convert OAC reports/dashboards to Power BI.
- **Wave 4 — Security & Governance**: Migrate row-level security, roles, auditing.
- **Wave 5 — Validation & Cutover**: End-to-end testing, UAT, cutover.

### 2.2 Guiding Principles

1. **No manual report recreation** — agents auto-generate Power BI artifacts from OAC metadata.
2. **Schema-on-read** where possible — land data in Lakehouse (Delta/Parquet), model in Semantic Model.
3. **Git-backed artifacts** — all generated Power BI reports and semantic models stored as PBIP/TMDL in Git.
4. **Fabric Lakehouse as coordination store** — agent state, mapping tables, and validation results stored as Delta tables in a dedicated Fabric Lakehouse, keeping everything within the Fabric platform with zero extra Azure services.

---

## 3. Timeline (Indicative — 16 weeks)

```
Week  1-2   ░░ Wave 0: Foundation & Agent Framework Setup
Week  3-5   ████ Wave 1: Data Layer Migration
Week  5-8   ██████ Wave 2: Semantic Layer Migration
Week  7-11  ████████ Wave 3: Report & Dashboard Migration
Week  9-12  ██████ Wave 4: Security & Governance Migration
Week 11-14  ██████ Wave 5: Validation, UAT, Performance Tuning
Week 14-16  ████ Cutover, Hypercare, Decommission Planning
```

> Waves overlap intentionally — agents work in parallel.

---

## 4. Workstreams & Ownership

| Workstream | Lead Agent | Human Oversight Needed |
|---|---|---|
| Discovery & Inventory | Discovery Agent | Low — review completeness |
| Schema & Data Migration | Schema Migration Agent | Medium — validate DDL |
| ETL Pipeline Migration | ETL Migration Agent | Medium — validate pipeline logic |
| Semantic Model Migration | Semantic Model Agent | High — validate business logic |
| Report & Dashboard Migration | Report Migration Agent | Medium — visual QA |
| Security & Governance | Security Migration Agent | High — approve RLS rules |
| Validation & Testing | Validation Agent | Medium — review test results |
| Orchestration | Orchestrator Agent | Low — monitor dashboards |

---

## 5. Risks & Mitigations

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | OAC metadata not fully extractable via API | High | Supplement with RPD XML export, catalog scraping |
| R2 | Complex OAC calculations have no Power BI DAX equivalent | High | Build a calculation translation library; flag for manual review |
| R3 | Data volume too large for initial full load | Medium | Use incremental load patterns in Fabric Data Factory |
| R4 | Row-level security model differences | Medium | Map to Power BI RLS with validation agent |
| R5 | User adoption resistance | Medium | Provide training materials, side-by-side comparison reports |
| R6 | Performance regression after migration | Medium | Benchmark queries pre/post, tune Fabric capacity |

---

## 6. Success Criteria

- [ ] 100% of in-scope OAC reports migrated to Power BI with equivalent functionality.
- [ ] Data reconciliation passes for all migrated datasets (row counts, aggregates).
- [ ] All RLS/OLS policies validated in Power BI against OAC baselines.
- [ ] End-user UAT sign-off with < 5% defect rate.
- [ ] Migration completed within agreed timeline (± 2 weeks).
- [ ] Zero data loss during migration.

### Framework Readiness (v3.0.0)

| Capability | Status |
|---|---|
| 8-agent orchestrated migration engine | ✅ Complete |
| CLI with discover / plan / migrate / validate / status | ✅ Complete |
| FastAPI web API with WebSocket streaming | ✅ Complete |
| 80+ DAX function mappings | ✅ Complete |
| PL/SQL → PySpark translation (rule-based + LLM) | ✅ Complete |
| Fabric Lakehouse & PBI deployment | ✅ Complete |
| Incremental / delta migration | ✅ Complete |
| Multi-source connectors (OAC, OBIEE + stubs) | ✅ Complete |
| Tableau connector (TWB/TWBX + calc→DAX) | ✅ Complete (Phase 40) |
| Plugin architecture | ✅ Complete |
| Multi-tenant SaaS model | ✅ Complete |
| Rollback & artifact versioning | ✅ Complete |
| UAT workflow & delivery packaging | ✅ Complete |
| React web dashboard | ✅ Complete (Phase 39) |
| Tableau / Cognos / Qlik full connectors | 🟡 Tableau done, Cognos & Qlik planned (v4.0) |
| GraphQL API / Self-Service Portal | ⬜ Planned (v5.0) |

---

## 7. Technology Stack

| Layer | Technology |
|---|---|
| **Source** | Oracle Analytics Cloud, Oracle Database |
| **Intermediate** | PostgreSQL (if Oracle→PostgreSQL migration in scope) |
| **Data Platform** | Microsoft Fabric (Lakehouse, Warehouse, OneLake) |
| **ETL/ELT** | Fabric Data Factory, Dataflows Gen2, Fabric Notebooks (PySpark) |
| **Semantic Layer** | Power BI Semantic Models (TMDL format) |
| **Reporting** | Power BI Reports (PBIP/PBIR format) |
| **Web API** | FastAPI + Uvicorn (REST + WebSocket + SSE) |
| **Coordination Store** | Fabric Lakehouse — Delta tables (agent state, mappings, validation results) |
| **Agent Framework** | Python 3.12+ (custom `MigrationAgent` ABC with async lifecycle) |
| **CLI** | argparse-based (`discover`, `plan`, `migrate`, `validate`, `status`) |
| **LLM** | Azure OpenAI GPT-4 / GPT-4o (rule-based first, LLM fallback) |
| **Containers** | Docker + Docker Compose, Azure Container Apps (Bicep), Helm (AKS) |
| **Source Control** | Azure DevOps Git / GitHub |
| **CI/CD** | GitHub Actions + Fabric Git Integration |
| **Monitoring** | Application Insights + OpenTelemetry |

---

## 8. Next Development Phase — v4.0 Roadmap

With the core framework complete (v3.0), the next milestone focuses on **production-grade UI**, **full multi-source maturity**, and **real-world deployment hardening**.

| Phase | Name | Focus | Key Deliverables |
|-------|------|-------|------------------|
| 39 | React Dashboard | Production web UI | React + Vite + TanStack Query dashboard, migration wizard, real-time status, inventory browser |
| 40 | Tableau Connector | Full Tableau migration support | TWB/TWBX parsing, REST API client, 55+ calc field → DAX rules, data source mapping |
| 41 | Cognos & Qlik Connectors | Expand connector coverage | Cognos Report Studio XML parsing, Qlik QVF/QVD extraction, expression mapping |
| 42 | Plugin Marketplace | Community extensibility | Plugin registry, versioned distribution, sample plugins (custom visuals, data quality) |
| 43 | Migration Analytics Dashboard | Operational intelligence | Power BI dashboard for migration metrics, cost tracking, progress visualization |
| 44 | Advanced RPD Binary Parser | OBIEE native format support | Direct RPD binary parsing without XML export, streaming for large files |
| 45 | AI-Assisted Schema Optimization | Intelligent target modeling | LLM-driven partition key selection, index recommendations, Fabric capacity sizing |
| 46 | Performance Auto-Tuning | Post-migration optimization | Automated RU/capacity tuning, query plan analysis, semantic model optimization |

### v5.0 Roadmap — Intelligent Platform

| Phase | Name | Focus | Key Deliverables |
|-------|------|-------|------------------|
| 47 | GraphQL API & Federation | Flexible querying & subscriptions | Strawberry GraphQL, real-time subscriptions, REST+GQL coexistence, query complexity limits |
| 48 | Migration Dry-Run Simulator | Risk-free simulation | Full simulation without target writes, cost/time estimates, risk heatmap, change manifest |
| 49 | Automated Regression Testing | Post-migration confidence | Snapshot-based data regression, visual diff for reports, schema drift detection, alert pipeline |
| 50 | Self-Service Migration Portal | Self-service onboarding | Multi-org SSO (Entra External ID), drag-and-drop upload, migration templates, public API |
