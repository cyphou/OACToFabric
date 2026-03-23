# Multi-Agent Architecture — OAC to Fabric & Power BI Migration

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

### Agent 02: Schema & Data Model Migration Agent

**Purpose**: Migrate Oracle database schemas to Fabric Lakehouse/Warehouse.

| Attribute | Detail |
|---|---|
| **Inputs** | Inventory (physical tables, views, columns, data types), Oracle connection |
| **Outputs** | Fabric Lakehouse tables (Delta format), DDL scripts, data type mapping log |
| **Key Logic** | Oracle → PostgreSQL type mapping (if intermediate) → Fabric Delta type mapping; generate CREATE TABLE statements; orchestrate data copy via Fabric Data Factory or Notebooks |
| **Dependencies** | Agent 01 (inventory must exist) |

### Agent 03: ETL/Data Pipeline Migration Agent

**Purpose**: Convert OAC Data Flows and Oracle ETL jobs to Fabric pipelines.

| Attribute | Detail |
|---|---|
| **Inputs** | OAC Data Flow definitions, Oracle stored procedures, scheduling metadata |
| **Outputs** | Fabric Data Factory pipeline JSON, Dataflow Gen2 definitions, Fabric Notebooks (PySpark) |
| **Key Logic** | Map OAC data flow steps to Fabric activities; convert PL/SQL to PySpark/SQL; preserve scheduling via Fabric triggers |
| **Dependencies** | Agent 01, Agent 02 (schemas must be migrated first) |

### Agent 04: Semantic Model Migration Agent

**Purpose**: Convert OAC RPD logical model and business layer to Power BI Semantic Models.

| Attribute | Detail |
|---|---|
| **Inputs** | RPD logical model (parsed from XML), OAC calculation definitions, hierarchies |
| **Outputs** | Power BI Semantic Model in TMDL format (tables, relationships, measures, hierarchies) |
| **Key Logic** | Map OAC logical columns → TMDL columns; convert OAC expressions → DAX measures; map OAC hierarchies → Power BI hierarchies; generate relationships from RPD joins |
| **Dependencies** | Agent 01, Agent 02 |

### Agent 05: Report & Dashboard Migration Agent

**Purpose**: Convert OAC Analyses and Dashboards to Power BI Reports.

| Attribute | Detail |
|---|---|
| **Inputs** | OAC analysis XML/JSON definitions, prompt definitions, dashboard layouts |
| **Outputs** | Power BI Report definitions (PBIR format), visual configurations, slicers, bookmarks |
| **Key Logic** | Map OAC visualization types → Power BI visuals; convert OAC prompts → PBI slicers/parameters; translate OAC conditional formatting → PBI format rules; reconstruct page layouts |
| **Dependencies** | Agent 01, Agent 04 (semantic model must exist) |

### Agent 06: Security & Governance Migration Agent

**Purpose**: Migrate OAC security model to Fabric/Power BI security.

| Attribute | Detail |
|---|---|
| **Inputs** | OAC application roles, row-level security (session variable-based), object permissions |
| **Outputs** | Power BI RLS role definitions (DAX filters), Fabric workspace role assignments, sensitivity labels |
| **Key Logic** | Map OAC session variables → RLS DAX filters; map OAC app roles → Fabric workspace roles + PBI RLS roles; migrate object-level permissions to OLS |
| **Dependencies** | Agent 01, Agent 04 |

### Agent 07: Validation & Testing Agent

**Purpose**: Validate migration correctness across all layers.

| Attribute | Detail |
|---|---|
| **Inputs** | Source OAC data/metadata, migrated Fabric/PBI artifacts |
| **Outputs** | Validation reports in Fabric Lakehouse, comparison dashboards, defect tickets |
| **Key Logic** | Data reconciliation (row counts, checksums, sample queries); visual comparison screenshots; RLS testing (same user, different results); performance benchmarks |
| **Dependencies** | All other agents (runs after each wave) |

### Agent 08: Orchestrator Agent

**Purpose**: Coordinate all agents, manage dependencies, monitor progress.

| Attribute | Detail |
|---|---|
| **Inputs** | Migration scope definition, wave plan, agent configurations |
| **Outputs** | Migration dashboard, status reports, alerts |
| **Key Logic** | DAG-based execution of agent tasks; retry failed tasks; aggregate progress; notify stakeholders; manage wave transitions |
| **Dependencies** | None (controls all others) |

---

## 4. Data Flow Between Agents

```
┌─────────┐     inventory      ┌──────────┐     schemas       ┌──────────┐
│Discovery├────────────────────►│  Schema  ├───────────────────►│   ETL    │
│Agent 01 │                    │ Agent 02 │                    │Agent 03  │
└────┬────┘                    └────┬─────┘                    └──────────┘
     │                              │
     │   inventory + RPD model      │  table definitions
     │                              │
     ▼                              ▼
┌──────────┐                  ┌──────────┐     semantic model  ┌──────────┐
│ Semantic │                  │ Security │◄────────────────────│  Report  │
│Model 04  │──────────────────►│Agent 06  │                    │Agent 05  │
└────┬─────┘   semantic model └──────────┘                    └────┬─────┘
     │                                                              │
     │         semantic model                                       │
     └─────────────────────────────────────────────────────────────►│
                                                                    │
     ┌──────────────────────────────────────────────────────────────┘
     │              all artifacts
     ▼
┌──────────┐
│Validation│
│Agent 07  │
└──────────┘
```

---

## 5. Agent Technology Choices

| Component | Technology | Rationale |
|---|---|---|
| Agent Framework | **Python + Semantic Kernel** or **AutoGen** | Native Azure integration, multi-model LLM support |
| LLM (Code Translation) | **Azure OpenAI GPT-4** | Translate OAC expressions → DAX, PL/SQL → PySpark |
| Coordination | **Fabric Lakehouse (Delta tables)** | All-in-Fabric state management, no extra service needed |
| Orchestration | **Fabric Data Factory** or **Azure Durable Functions** | DAG execution, retry, monitoring |
| Source Metadata API | **OAC REST API + RPD XML Parser** | Full catalog + model extraction |
| Target Artifact Gen | **TMDL SDK, Tabular Editor, PBI REST API** | Generate/deploy Power BI artifacts |
| Testing | **pytest + Great Expectations** | Data quality validation framework |
| CI/CD | **Azure DevOps + Fabric Git Integration** | Promote artifacts across dev/test/prod |
