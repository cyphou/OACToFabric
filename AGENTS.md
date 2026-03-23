# Multi-Agent Architecture — OAC to Fabric & Power BI Migration

## Quick Reference

| Agent | Invoke When | Owns |
|-------|-------------|------|
| **Discovery (01)** | Crawl OAC environment, inventory, dependency graph | `src/agents/discovery/`, `src/clients/oac_catalog.py`, `src/clients/oac_auth.py`, `src/clients/oac_dataflow_api.py` |
| **Schema (02)** | Oracle DDL → Fabric Lakehouse/Warehouse tables | `src/agents/schema/` |
| **ETL (03)** | OAC Data Flows/PL/SQL → Fabric pipelines/notebooks | `src/agents/etl/` |
| **Semantic Model (04)** | RPD logical model → TMDL semantic model | `src/agents/semantic/` |
| **Report (05)** | OAC Analyses/Dashboards → PBIR reports | `src/agents/report/` |
| **Security (06)** | Roles, RLS, OLS, workspace permissions | `src/agents/security/` |
| **Validation (07)** | Cross-layer validation, reconciliation, benchmarks | `src/agents/validation/`, `src/validation/` |
| **Orchestrator (08)** | Pipeline coordination, DAG execution, wave planning | `src/agents/orchestrator/`, `src/cli/`, `src/api/` |

---

## 1. Architecture Overview

The migration is driven by **8 specialized agents** coordinated by a central **Orchestrator Agent**. Each agent is responsible for one migration domain and exposes a consistent interface for task intake, execution, and reporting.

```
                           ┌──────────────────────┐
                           │   Orchestrator Agent  │
                           │   (08 - Coordinator)  │
                           └──────────┬───────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │              │          │          │               │
    ┌───────▼──────┐ ┌────▼─────┐ ┌──▼───┐ ┌───▼────┐ ┌───────▼──────┐
    │  Discovery   │ │  Schema  │ │  ETL │ │Semantic│ │   Report     │
    │  Agent (01)  │ │  Agent   │ │Agent │ │ Model  │ │   Agent (05) │
    │              │ │  (02)    │ │ (03) │ │Agent(04)│ │              │
    └──────────────┘ └──────────┘ └──────┘ └────────┘ └──────────────┘
            │              │          │          │               │
            │         ┌────▼─────┐   │     ┌────▼─────┐        │
            │         │ Security │   │     │Validation│        │
            │         │Agent (06)│   │     │Agent (07)│        │
            │         └──────────┘   │     └──────────┘        │
            │                        │                          │
    ┌───────▼────────────────────────▼──────────────────────────▼───┐
    │              Fabric Lakehouse (Delta Tables)                   │
    │   (Agent State, Migration Mappings, Validation Results)       │
    └──────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Communication Model

### 2.1 Coordination Store (Fabric Lakehouse — Delta Tables)

All agents communicate via a shared **Fabric Lakehouse** using **Delta tables** in OneLake. This keeps the entire solution within Microsoft Fabric, eliminating the need for an additional Azure service.

| Delta Table | Partition Column | Purpose |
|---|---|---|
| `agent_tasks` | `agent_id` | Task queue per agent (assigned, in-progress, done, failed) |
| `migration_inventory` | `asset_type` | Full inventory of OAC assets discovered |
| `mapping_rules` | `source_type` | Translation rules (OAC → Fabric/PBI mapping) |
| `validation_results` | `migration_id` | Test results, reconciliation outcomes |
| `agent_logs` | `agent_id` | Structured logs, diagnostics, timing |

> **Why Fabric Lakehouse?** Everything stays inside Fabric — no extra Azure service to provision, manage, or pay for. Delta tables provide ACID transactions, time travel, and efficient reads/writes. Agents connect via the Lakehouse SQL endpoint for reads or the Delta Lake API (PySpark) for writes. OneLake stores all coordination data alongside the migrated data itself.

### 2.2 Agent Interface Contract

Every agent implements the following interface:

```python
class MigrationAgent(ABC):
    """Base class for all migration agents."""
    
    agent_id: str           # Unique agent identifier
    agent_name: str         # Human-readable name
    
    @abstractmethod
    async def discover(self, scope: MigrationScope) -> Inventory:
        """Discover source assets within the given scope."""
        ...
    
    @abstractmethod
    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """Generate a migration plan from the inventory."""
        ...
    
    @abstractmethod
    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Execute the migration plan."""
        ...
    
    @abstractmethod
    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Validate the migration result against the source."""
        ...
    
    async def rollback(self, result: MigrationResult) -> RollbackResult:
        """Rollback a failed or incorrect migration."""
        ...
```

### 2.3 Agent Lifecycle

```
  IDLE → DISCOVERING → PLANNING → EXECUTING → VALIDATING → DONE
                                       │                      │
                                       └──► FAILED ──► ROLLBACK
```

---

## 3. Agent Definitions

### Agent 01: Discovery & Inventory Agent

**Purpose**: Crawl the OAC environment and produce a complete inventory of all assets.

| Attribute | Detail |
|---|---|
| **Inputs** | OAC API credentials, RPD export (XML/JSON), OAC catalog endpoints |
| **Outputs** | Structured inventory in Fabric Lakehouse (`migration_inventory` Delta table) |
| **Discovers** | Subject Areas, Analyses, Dashboards, Data Models, Connections, Prompts, Agents/Alerts, Security Roles, Data Flows |
| **Key Logic** | Parse RPD XML for logical/physical model; call OAC REST APIs for catalog; extract dependencies graph |
| **Dependencies** | None (first agent to run) |

**Owns**: `src/agents/discovery/` (discovery_agent.py, oac_client.py, rpd_parser.py, dependency_graph.py, complexity_scorer.py), `src/clients/oac_catalog.py`, `src/clients/oac_auth.py`, `src/clients/oac_dataflow_api.py`

**Constraints**: Do NOT modify schema DDL, ETL pipelines, semantic models, or reports. Only produces inventory and dependency metadata.

### Agent 02: Schema & Data Model Migration Agent

**Purpose**: Migrate Oracle database schemas to Fabric Lakehouse/Warehouse.

| Attribute | Detail |
|---|---|
| **Inputs** | Inventory (physical tables, views, columns, data types), Oracle connection |
| **Outputs** | Fabric Lakehouse tables (Delta format), DDL scripts, data type mapping log |
| **Key Logic** | Oracle → Fabric Delta type mapping; generate CREATE TABLE statements; orchestrate data copy via Fabric Data Factory or Notebooks |
| **Dependencies** | Agent 01 (inventory must exist) |

**Owns**: `src/agents/schema/` (schema_agent.py, ddl_generator.py, sql_translator.py, type_mapper.py, pipeline_generator.py)

**Constraints**: Do NOT modify OAC extraction logic, DAX/TMDL generation, or report visuals. Only produces Fabric table DDL, data type mappings, and data copy pipelines.

### Agent 03: ETL/Data Pipeline Migration Agent

**Purpose**: Convert OAC Data Flows and Oracle ETL jobs to Fabric pipelines.

| Attribute | Detail |
|---|---|
| **Inputs** | OAC Data Flow definitions, Oracle stored procedures, scheduling metadata |
| **Outputs** | Fabric Data Factory pipeline JSON, Dataflow Gen2 definitions, Fabric Notebooks (PySpark) |
| **Key Logic** | Map OAC data flow steps to Fabric activities; convert PL/SQL to PySpark/SQL; preserve scheduling via Fabric triggers |
| **Dependencies** | Agent 01, Agent 02 (schemas must be migrated first) |

**Owns**: `src/agents/etl/` (etl_agent.py, dataflow_parser.py, step_mapper.py, plsql_translator.py, schedule_converter.py)

**Constraints**: Do NOT modify discovery, schema DDL, or semantic model logic. Only produces Fabric pipeline/notebook/schedule artifacts.

### Agent 04: Semantic Model Migration Agent

**Purpose**: Convert OAC RPD logical model and business layer to Power BI Semantic Models.

| Attribute | Detail |
|---|---|
| **Inputs** | RPD logical model (parsed from XML), OAC calculation definitions, hierarchies |
| **Outputs** | Power BI Semantic Model in TMDL format (tables, relationships, measures, hierarchies) |
| **Key Logic** | Map OAC logical columns → TMDL columns; convert OAC expressions → DAX measures; map OAC hierarchies → Power BI hierarchies; generate relationships from RPD joins |
| **Dependencies** | Agent 01, Agent 02 |

**Owns**: `src/agents/semantic/` (semantic_agent.py, rpd_model_parser.py, expression_translator.py, hierarchy_mapper.py, tmdl_generator.py), `src/core/expression_translator.py`, `src/core/hybrid_translator.py`, `src/core/translation_cache.py`, `src/core/translation_catalog.py`

**Constraints**: Do NOT modify report visuals, security roles, or schema DDL. Only produces TMDL semantic model artifacts and DAX expressions.

### Agent 05: Report & Dashboard Migration Agent

**Purpose**: Convert OAC Analyses and Dashboards to Power BI Reports.

| Attribute | Detail |
|---|---|
| **Inputs** | OAC analysis XML/JSON definitions, prompt definitions, dashboard layouts |
| **Outputs** | Power BI Report definitions (PBIR format), visual configurations, slicers, bookmarks |
| **Key Logic** | Map OAC visualization types → Power BI visuals; convert OAC prompts → PBI slicers/parameters; translate OAC conditional formatting → PBI format rules; reconstruct page layouts |
| **Dependencies** | Agent 01, Agent 04 (semantic model must exist) |

**Owns**: `src/agents/report/` (report_agent.py, prompt_converter.py, visual_mapper.py, layout_engine.py, pbir_generator.py)

**Constraints**: Do NOT modify semantic model TMDL, security roles, or schema DDL. Only produces PBIR report JSON, visual configs, and slicer definitions.

### Agent 06: Security & Governance Migration Agent

**Purpose**: Migrate OAC security model to Fabric/Power BI security.

| Attribute | Detail |
|---|---|
| **Inputs** | OAC application roles, row-level security (session variable-based), object permissions |
| **Outputs** | Power BI RLS role definitions (DAX filters), Fabric workspace role assignments, sensitivity labels |
| **Key Logic** | Map OAC session variables → RLS DAX filters; map OAC app roles → Fabric workspace roles + PBI RLS roles; migrate object-level permissions to OLS |
| **Dependencies** | Agent 01, Agent 04 |

**Owns**: `src/agents/security/` (security_agent.py, role_mapper.py, rls_converter.py, ols_generator.py), `src/core/security_audit.py`

**Constraints**: Do NOT modify TMDL tables/measures, report visuals, or schema DDL. Only produces RLS/OLS definitions and workspace role mappings.

### Agent 07: Validation & Testing Agent

**Purpose**: Validate migration correctness across all layers.

| Attribute | Detail |
|---|---|
| **Inputs** | Source OAC data/metadata, migrated Fabric/PBI artifacts |
| **Outputs** | Validation reports in Fabric Lakehouse, comparison dashboards, defect tickets |
| **Key Logic** | Data reconciliation (row counts, checksums, sample queries); visual comparison screenshots; RLS testing (same user, different results); performance benchmarks |
| **Dependencies** | All other agents (runs after each wave) |

**Owns**: `src/agents/validation/` (validation_agent.py, data_reconciliation.py, semantic_validator.py, report_validator.py, security_validator.py), `src/validation/`, `tests/`

**Constraints**: Do NOT modify source extraction, generation, or deployment logic. Only produces validation reports and test results. Cross-cutting: reads all source files for verification but writes only to validation outputs and `tests/`.

### Agent 08: Orchestrator Agent

**Purpose**: Coordinate all agents, manage dependencies, monitor progress.

| Attribute | Detail |
|---|---|
| **Inputs** | Migration scope definition, wave plan, agent configurations |
| **Outputs** | Migration dashboard, status reports, alerts |
| **Key Logic** | DAG-based execution of agent tasks; retry failed tasks; aggregate progress; notify stakeholders; manage wave transitions |
| **Dependencies** | None (controls all others) |

**Owns**: `src/agents/orchestrator/` (orchestrator_agent.py, dag_engine.py, wave_planner.py, notification_manager.py), `src/cli/`, `src/api/`, `src/core/agent_registry.py`, `src/core/runner_factory.py`, `src/core/state_coordinator.py`, `src/core/graceful_shutdown.py`

**Constraints**: Do NOT modify domain-specific migration logic (discovery, schema, ETL, semantic, report, security, validation). Delegates all domain work to the appropriate agent.

**Delegation Guide**:

| Task | Delegate To |
|------|-------------|
| Crawl OAC, parse RPD, build inventory | **Discovery (01)** |
| Oracle DDL → Fabric tables | **Schema (02)** |
| Data Flows/PL/SQL → Fabric pipelines | **ETL (03)** |
| RPD logical model → TMDL semantic model | **Semantic Model (04)** |
| OAC Analyses → PBIR reports | **Report (05)** |
| Roles, RLS, OLS → Fabric/PBI security | **Security (06)** |
| Reconciliation, visual comparison, benchmarks | **Validation (07)** |

---

## 4. Data Flow Between Agents

```
                    ┌──────────────┐
                    │ Orchestrator │  ← CLI entry, DAG coordination, wave planning
                    │   (08)       │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼──────┐   ┌────▼─────┐   ┌─────▼──────┐
    │ Discovery  │   │  Schema  │   │    ETL     │
    │   (01)     │   │   (02)   │   │   (03)     │
    └─────┬──────┘   └────┬─────┘   └────────────┘
          │                │
          │  inventory     │  table definitions
          │  + RPD model   │
          ▼                ▼
    ┌───────────┐   ┌───────────┐          ┌───────────┐
    │ Semantic  │   │ Security  │◄─────────│  Report   │
    │Model (04) │──►│   (06)    │          │   (05)    │
    └─────┬─────┘   └───────────┘          └─────┬─────┘
          │                                       │
          │  semantic model                       │
          └───────────────────────────────────────►│
                                                   │
          ┌────────────────────────────────────────┘
          │  all artifacts
          ▼
    ┌───────────┐
    │Validation │
    │   (07)    │
    └───────────┘
```

### Execution Sequence

```
1. Orchestrator receives migration scope (CLI / API / Dashboard)
2. Orchestrator delegates to Discovery (01) → inventory + dependency graph + complexity scores
3. Orchestrator delegates to Schema (02) → Fabric Lakehouse/Warehouse DDL + data copy
4. Orchestrator delegates to ETL (03) → Fabric pipelines, notebooks, schedules (parallel with 04/05)
5. Orchestrator delegates to Semantic Model (04) → TMDL semantic model
6. Orchestrator delegates to Report (05) → PBIR reports, visuals, slicers
7. Orchestrator delegates to Security (06) → RLS/OLS roles, workspace permissions
8. Orchestrator delegates to Validation (07) → reconciliation, visual comparison, benchmarks
9. Orchestrator aggregates results → migration dashboard + status report
```

---

## 5. File Ownership Rules

- **One owner per file** — each source file has exactly one owning agent
- **Read access is universal** — any agent can read any file for context
- **Write access is restricted** — only the owning agent modifies a file
- **Validation (07) is cross-cutting** — reads all source files, writes only to `src/validation/`, `src/agents/validation/`, and `tests/`
- **Orchestrator (08) owns infrastructure** — CLI, API, agent registry, state coordination, graceful shutdown

### Shared / Cross-Cutting Modules

| Module | Used By | Purpose |
|--------|---------|---------|
| `src/core/base_agent.py` | All agents | MigrationAgent ABC — lifecycle methods |
| `src/core/models.py` | All agents | Pydantic domain models (Inventory, MigrationPlan, etc.) |
| `src/core/config.py` | All agents | Configuration loader (migration.toml) |
| `src/core/telemetry.py` | All agents | Structured observability, App Insights |
| `src/core/resilience.py` | All agents | Circuit breakers, fallback strategies |
| `src/core/lakehouse_client.py` | All agents | Async Delta table client for coordination |
| `src/core/keyvault_provider.py` | All agents | Azure Key Vault secret management |
| `src/core/llm_client.py` | 03, 04 | Azure OpenAI async wrapper |
| `src/core/security_audit.py` | 06, 07, 08 | Credential leak detection, hardening checks |

---

## 6. Handoff Protocol

When an agent encounters work outside its domain:

1. **Complete your part** — finish everything within your file scope (including tests for your domain)
2. **State the handoff** — clearly describe what needs to happen next
3. **Name the target agent** — e.g., "Hand off to Semantic Model (04) for TMDL updates"
4. **List artifacts** — specify files, functions, and data structures involved
5. **Include context** — provide any intermediate results (Delta table rows, JSON, dicts) the next agent needs

### Example Handoff

```
Discovery (01) → Schema (02):
  "Inventory complete. 347 tables discovered in RPD physical layer.
   See `migration_inventory` Delta table, filtered by asset_type='table'.
   Each row has: table_name, schema, columns (JSON array), estimated_rows, oracle_data_types.
   Ready for DDL generation."
```

---

## 7. Agent Technology Choices

| Component | Technology | Rationale |
|---|---|---|
| Agent Framework | **Python 3.11+ async/await** with custom `MigrationAgent` ABC | Full lifecycle control, Pydantic models, async I/O |
| LLM (Code Translation) | **Azure OpenAI GPT-4** | Translate OAC expressions → DAX, PL/SQL → PySpark |
| Translation Engine | **Hybrid: Rules-first + LLM fallback** | 90+ deterministic rules, LLM for complex edge cases |
| Coordination | **Fabric Lakehouse (Delta tables)** | All-in-Fabric state management, no extra service needed |
| Orchestration | **DAG engine** (`dag_engine.py`) with wave planning | Topological sort, parallel execution, retry logic |
| Source Metadata API | **OAC REST API + RPD XML Parser** (streaming) | Full catalog + model extraction, memory-efficient |
| Target Artifact Gen | **TMDL generator + PBIR generator** | Generate Power BI artifacts natively |
| Deployment | **Fabric REST API + PBI REST API** clients | Deploy Lakehouse, semantic models, reports |
| Testing | **pytest** (2,100+ tests) | Comprehensive unit + integration coverage |
| CI/CD | **Azure DevOps + Fabric Git Integration** | Promote artifacts across dev/test/prod |

---

## 8. When NOT to Use Specialized Agents

Use the **Orchestrator (08)** or the default development workflow for:
- Quick questions about the project
- Multi-domain tasks that touch 3+ agents simultaneously
- Documentation updates (CHANGELOG, README, CONTRIBUTING, etc.)
- Sprint planning and development plan updates
- Git operations (commit, push, branch)
- Infrastructure changes (Bicep, config files)

---

## 9. Key References

| Document | Path | Purpose |
|----------|------|---------|
| Agent SPECs | `agents/01-discovery-agent/SPEC.md` … `agents/08-orchestrator-agent/SPEC.md` | Detailed per-agent technical specifications |
| Architecture | `docs/guides/getting_started.md` | Getting started guide |
| Dev Plan | `DEV_PLAN.md` | Phase-by-phase development tracking |
| Migration Playbook | `MIGRATION_PLAYBOOK.md` | Step-by-step production migration guide |
| Project Plan | `PROJECT_PLAN.md` | Executive-level scope and timeline |
| OAC API Notes | `docs/oac-api-notes.md` | OAC REST API quirks and workarounds |
| Security | `docs/security.md` | Credentials, data handling, LLM security |
| ADRs | `docs/adrs/` | Architecture Decision Records (4 ADRs) |
| Runbooks | `docs/runbooks/` | Operational runbooks (6 runbooks) |
