<p align="center">
  <img src="https://img.shields.io/badge/Oracle_Analytics-F80000?style=for-the-badge&logo=oracle&logoColor=white" alt="OAC"/>
  <img src="https://img.shields.io/badge/→-000000?style=for-the-badge" alt="arrow"/>
  <img src="https://img.shields.io/badge/Microsoft_Fabric-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white" alt="Fabric"/>
  <img src="https://img.shields.io/badge/Power_BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black" alt="Power BI"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/tests-3%2C760_passed-brightgreen?style=flat-square" alt="Tests"/>
  <img src="https://img.shields.io/badge/phases-62%2F62_+_Phase_70_+_Tooling-blue?style=flat-square" alt="Progress"/>
  <img src="https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/coverage-97%25_OAC_objects-green?style=flat-square" alt="Coverage"/>
  <img src="https://img.shields.io/badge/source-160%2B_modules-informational?style=flat-square" alt="Modules"/>
</p>

<h1 align="center">OAC → Microsoft Fabric & Power BI</h1>

<p align="center">
  <b>v8.0-alpha.2</b> — Migrate Oracle Analytics Cloud to Microsoft Fabric & Power BI — fully automated,<br/>
  8 AI-powered agents with LLM reasoning, practical migration tooling, 97% OAC object coverage, Essbase E2E migration, zero manual rework.
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-key-features">Features</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-expression-translation-300-rules">DAX Mappings</a> •
  <a href="#-cli-reference">CLI</a> •
  <a href="#-documentation">Docs</a>
</p>

---

## ⚡ Quick Start

```bash
# That's it. One command.
oac-migrate migrate --config config/migration.toml
```

> [!TIP]
> The output is deployed to Microsoft Fabric — Lakehouse tables, semantic models (TMDL), and Power BI reports (PBIR).

<details>
<summary>📦 Installation</summary>

```bash
# Clone & setup
git clone https://github.com/cyphou/OACToFabric.git
cd OACToFabric
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
```

</details>

### More ways to migrate

```bash
# 🔍 Discovery only — inventory all OAC assets
oac-migrate discover --config config/migration.toml

# 📋 Plan waves — see what will be migrated, without executing
oac-migrate plan --config config/migration.toml

# 🚀 Full migration with dry-run preview
oac-migrate migrate --config config/migration.toml --dry-run

# ✅ Validate migration results
oac-migrate validate --config config/migration.toml

# 📊 Check migration progress
oac-migrate status --config config/migration.toml

# 🔌 Plugin marketplace — list / install / publish plugins
oac-migrate marketplace list

# 📈 Export migration analytics
oac-migrate analytics --format powerbi

# ⚡ AI-assisted schema optimization
oac-migrate optimize --lakehouse MigrationLakehouse

# 🎯 Performance auto-tuning
oac-migrate tune --lakehouse MigrationLakehouse

# 🖥️ Start the API + React dashboard
uvicorn src.api.app:app --port 8000
cd dashboard && npm run dev     # → http://localhost:5173
```

---

## 🎯 Key Features

| 🤖 8 Specialized AI Agents | 🔌 6 Source Connectors |
| :--- | :--- |
| Discovery, Schema, ETL, Semantic Model, Reports, Security, Validation, and Orchestrator — each agent owns one migration domain end-to-end with discover → plan → execute → validate lifecycle. DAG-based orchestration with wave planning, retry logic, and checkpoint/rollback. | OAC, OBIEE, Tableau, Essbase, IBM Cognos, Qlik Sense — uniform `SourceConnector` interface. Each connector extracts metadata, translates expressions to DAX, and feeds the semantic bridge for TMDL generation. |

| 🧮 300+ DAX Conversion Rules | 🧠 Hybrid AI Translation |
| :--- | :--- |
| OAC expressions (30+), Tableau calculations (55+), Essbase calc scripts (55+), Essbase MDX (24+), Cognos report expressions (50+), Qlik set analysis & aggregations (72+), Oracle SQL→Fabric SQL (30+), Calculation Groups, DAX UDFs. All with confidence scoring. | Rules-first with Azure OpenAI GPT-4 fallback. 90%+ of expressions translate automatically via deterministic rules. Complex edge cases route to LLM with syntax validation. SQLite translation cache for performance. |

| 📊 React Dashboard & REST API | 🛡️ Security Migration |
| :--- | :--- |
| React 18 + TypeScript SPA with 5 pages (Migration List, Detail, Wizard, Inventory Browser, dark mode). FastAPI backend with REST + WebSocket + SSE streaming. JWT/API key auth with RBAC (Admin, Operator, Viewer). | OAC session variables → Power BI RLS (DAX filters). OAC object permissions → OLS. OAC application roles → Fabric workspace roles. Full security audit with credential leak detection. |

| 🔄 Incremental & Reversible | ⚡ AI Schema Optimization |
| :--- | :--- |
| Wave-based migration with full checkpoint support. Resume from last completed agent. Rollback any wave. Delta crawl with incremental TMDL merge. Multi-tenant isolation. Delta table coordination store in Fabric Lakehouse — no extra Azure services. | AI-assisted partition key recommendations (cardinality scoring), storage mode advisor (Import vs DirectLake vs Dual), Fabric SKU capacity sizing (F2–F1024), column pruning for wide tables, Oracle MV detection, Fabric Mirroring config generation. |

| 🔌 Plugin Marketplace | 📈 Migration Analytics |
| :--- | :--- |
| Extensible plugin framework with 8 lifecycle hooks (PRE/POST for Discover, Translate, Deploy, Validate). Built-in plugins for visual mapping overrides and data quality checks. JSON-backed registry with publish/install/uninstall. | Real-time metrics collection with agent progress, wave tracking, and cost analysis. Export to JSON, CSV, or Power BI template. Executive summary with risk detection (failure rates, budget overruns, critical issues). |

> [!NOTE]
> Zero external services for coordination. The entire agent state lives in Fabric Lakehouse Delta tables alongside your migrated data.

---

## 🔧 How It Works

### End-to-End Pipeline Architecture

```mermaid
graph TB
    subgraph SOURCE["📊 Source Platforms"]
        OAC["Oracle Analytics<br/>Cloud"]
        OBIEE["Oracle BI EE"]
        TAB["Tableau"]
        ESS["Essbase"]
        COG["IBM Cognos"]
        QLIK["Qlik Sense"]
    end

    subgraph EXTRACT["🔍 Extraction Layer"]
        CONN["SourceConnector<br/>Interface"]
        RPD["RPD Parser<br/>(XML + Binary)"]
        REST["REST API<br/>Clients"]
        EXPR["Expression<br/>Extractor"]
    end

    subgraph AGENTS["🤖 8 Agent Pipeline"]
        direction LR
        A01["01 Discovery<br/>Inventory + DAG"]
        A02["02 Schema<br/>DDL + MVs"]
        A03["03 ETL<br/>Pipelines"]
        A04["04 Semantic<br/>TMDL + DAX"]
        A05["05 Report<br/>PBIR + RDL"]
        A06["06 Security<br/>RLS + OLS"]
        A07["07 Validation<br/>Reconcile"]
        A08["08 Orchestrator<br/>DAG + Waves"]
    end

    subgraph TRANSLATE["🧮 Translation Engine"]
        RULES["Rule Engine<br/>300+ rules"]
        LLM["Azure OpenAI<br/>GPT-4 Fallback"]
        CACHE["SQLite<br/>Translation Cache"]
    end

    subgraph TARGET["🚀 Microsoft Fabric + Power BI"]
        LH["Fabric<br/>Lakehouse<br/>(Delta)"]
        WH["Fabric<br/>Warehouse<br/>(MVs)"]
        SM["Semantic<br/>Model<br/>(TMDL)"]
        RPT["Reports<br/>(PBIR)"]
        PAG["Paginated<br/>Reports<br/>(RDL)"]
        PIPE["Data Factory<br/>Pipelines"]
        ACT["Data<br/>Activator"]
        SEC["RLS / OLS<br/>Roles"]
    end

    SOURCE --> EXTRACT
    EXTRACT --> AGENTS
    AGENTS --> TRANSLATE
    TRANSLATE --> TARGET
    A08 -.->|coordinates| A01 & A02 & A03 & A04 & A05 & A06 & A07

    style SOURCE fill:#F80000,stroke:#C00,color:#fff
    style EXTRACT fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style AGENTS fill:#2ECC71,stroke:#1A9F55,color:#fff
    style TRANSLATE fill:#7B68EE,stroke:#5B48CE,color:#fff
    style TARGET fill:#0078D4,stroke:#005A9E,color:#fff
```

### Migration Pipeline (5 Steps)

```mermaid
flowchart LR
    SRC["📊 Source Platform<br/>(OAC / Tableau / Cognos / Qlik)"] --> DISC["🔍 Discover<br/>Assets & Dependencies"]
    DISC --> PLAN["📋 Plan<br/>Waves & DAG"]
    PLAN --> EXEC["⚙️ Execute<br/>8 Agents in Parallel"]
    EXEC --> VALID["✅ Validate<br/>Reconcile & Compare"]
    VALID --> DEPLOY["🚀 Deploy<br/>Fabric + Power BI"]

    style SRC fill:#F80000,stroke:#C00,color:#fff
    style DISC fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style PLAN fill:#7B68EE,stroke:#5B48CE,color:#fff
    style EXEC fill:#2ECC71,stroke:#1A9F55,color:#fff
    style VALID fill:#F39C12,stroke:#D68910,color:#fff
    style DEPLOY fill:#0078D4,stroke:#005A9E,color:#fff
```

**Step 1 — Discover**: Crawls OAC (REST API + RPD XML/binary), builds dependency graph, scores complexity.

**Step 2 — Plan**: Groups assets into migration waves, builds DAG with agent dependencies, estimates effort.

**Step 3 — Execute**: 7 agents run in DAG order — Schema (Oracle DDL→Delta), ETL (PL/SQL→PySpark), Semantic Model (RPD→TMDL+DAX), Reports (visuals→PBIR), Security (roles→RLS/OLS).

**Step 4 — Validate**: Row count reconciliation, semantic model comparison, visual diff, RLS testing, performance benchmarks.

**Step 5 — Deploy**: One-click deploy to Fabric Lakehouse + Power BI Service via REST APIs with Azure AD auth.

<details>
<summary>🤖 Agent Pipeline (DAG)</summary>

```mermaid
flowchart LR
    D["🔍 Discovery<br/>Agent 01"] --> S["🗄️ Schema<br/>Agent 02"]
    D --> SM["📐 Semantic<br/>Agent 04"]
    S --> E["🔄 ETL<br/>Agent 03"]
    S --> SM
    SM --> R["📊 Reports<br/>Agent 05"]
    SM --> SEC["🔒 Security<br/>Agent 06"]
    D --> SEC
    E --> V["✅ Validation<br/>Agent 07"]
    R --> V
    SEC --> V

    style D fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style S fill:#7B68EE,stroke:#5B48CE,color:#fff
    style E fill:#FF8C42,stroke:#D96B20,color:#fff
    style SM fill:#2ECC71,stroke:#1A9F55,color:#fff
    style R fill:#E74C3C,stroke:#C0392B,color:#fff
    style SEC fill:#F39C12,stroke:#D68910,color:#fff
    style V fill:#1ABC9C,stroke:#16A085,color:#fff
```

Every agent implements four lifecycle methods:

```python
class MigrationAgent(ABC):
    async def discover(self, scope) -> Inventory         # Find source assets
    async def plan(self, inventory) -> MigrationPlan     # Create migration plan
    async def execute(self, plan) -> MigrationResult     # Execute migration
    async def validate(self, result) -> ValidationReport # Verify correctness
```

</details>

<details>
<summary>🔄 Data Flow (Sequence Diagram)</summary>

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant UI as 🖥️ Dashboard / CLI
    participant API as ⚡ FastAPI
    participant O as 🎯 Orchestrator
    participant A as 🤖 Agents (01-07)
    participant LH as 🗃️ Fabric Lakehouse
    participant PBI as 📊 Power BI

    U->>UI: Configure migration
    UI->>API: POST /migrations
    API->>O: Create & queue
    O->>A: Execute DAG (wave 1)

    loop For each agent
        A->>A: discover()
        A->>A: plan()
        A->>A: execute()
        A->>LH: Write Delta tables
        A->>A: validate()
        A-->>O: Report status
        O-->>API: WebSocket event
        API-->>UI: Real-time update
    end

    A->>PBI: Deploy semantic models
    A->>PBI: Deploy reports
    O->>API: Migration complete
    API->>UI: ✅ Done
    UI->>U: View results
```

</details>

---

## 🔌 Multi-Source Connectors

| Platform | Status | Expression Rules | Capabilities |
|:---------|:------:|:----------------:|:-------------|
| **Oracle Analytics Cloud** | ✅ Full | 30+ | REST API, RPD XML/binary parsing, catalog discovery |
| **Oracle BI EE** | ✅ Full | — | RPD metadata extraction, catalog API |
| **Tableau** | ✅ Full | 55+ | REST API v3.21, TWB/TWBX parsing, calc→DAX, semantic bridge |
| **Oracle Essbase** | ✅ Full | 79+ | REST API, outline parsing, calc script→DAX, MDX→DAX, filters→RLS |
| **IBM Cognos** | ✅ Full | 50+ | REST API, report spec XML parsing, expression→DAX, semantic bridge |
| **Qlik Sense** | ✅ Full | 72+ | Engine API, load script parsing, set analysis→DAX, semantic bridge |

<details>
<summary>🔌 Connector class diagram</summary>

```mermaid
classDiagram
    class SourceConnector {
        <<abstract>>
        +info() ConnectorInfo
        +connect(config) bool
        +discover() List~ExtractedAsset~
        +extract_metadata(ids) ExtractionResult
        +disconnect()
    }

    class OACConnector { OAC REST API + RPD parser }
    class OBIEEConnector { RPD metadata + Catalog API }
    class TableauConnector { REST API + TWB/TWBX parser }
    class EssbaseConnector { REST API + outline + calc/MDX }
    class CognosConnector { REST API + report spec XML }
    class QlikConnector { Engine API + load script parser }

    SourceConnector <|-- OACConnector
    SourceConnector <|-- OBIEEConnector
    SourceConnector <|-- TableauConnector
    SourceConnector <|-- EssbaseConnector
    SourceConnector <|-- CognosConnector
    SourceConnector <|-- QlikConnector
```

</details>

---

## 🧮 Expression Translation (300+ Rules)

The **Hybrid Translator** uses a rules-first approach with LLM fallback:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  OAC / Tableau / Cognos / Qlik          →  Power BI DAX                │
├──────────────────────────────────────────────────────────────────────────┤
│  IFNULL([Revenue], 0)                   →  COALESCE([Revenue], 0)      │
│  FILTER("Orders"."Status" = 'Active')   →  CALCULATE(...,              │
│                                              'Orders'[Status]="Active") │
│  ZN(SUM([Sales]))                       →  IF(ISBLANK(SUM([Sales])),   │
│                                              0, SUM([Sales]))           │
│  TIMESTAMPDIFF(day, [Start], [End])     →  DATEDIFF([Start],[End],DAY) │
│  RANK(SUM([Revenue]))                   →  RANKX(ALL(...), SUM(...))   │
│  {FIXED [Region] : SUM([Sales])}        →  CALCULATE(SUM([Sales]),     │
│                                              ALLEXCEPT('T',[Region]))   │
└──────────────────────────────────────────────────────────────────────────┘
```

| Source | Rules | Confidence | Engine |
|:-------|:-----:|:----------:|:-------|
| OAC → DAX | 30+ | 95% auto | Rule-based catalog |
| Tableau → DAX | 55+ | 85% auto | Rule-based + LOD patterns |
| Essbase Calc → DAX | 55+ | 90% auto | Calc script parser |
| Essbase MDX → DAX | 24+ | 85% auto | MDX pattern matcher |
| Cognos → DAX | 50+ | 85% auto | Report spec expression engine |
| Qlik → DAX | 72+ | 80% auto | Set analysis + aggregation rules |
| Oracle SQL → Fabric SQL | 30+ | 90% auto | SQL dialect translator |
| **Complex / Edge cases** | — | — | **Azure OpenAI GPT-4 fallback** |

> **Full reference**: [docs/MAPPING_REFERENCE.md](docs/MAPPING_REFERENCE.md)

---

## 📊 OAC Object Coverage (97%)

```mermaid
pie title OAC Object Type Migration Coverage
    "Fully Automated (60)" : 60
    "Manual Review (2)" : 2
```

<details>
<summary>📋 Object type coverage detail</summary>

| Layer | Object Type | Status | Target |
|:------|:-----------|:------:|:-------|
| **Discovery** | Subject Areas, Analyses, Dashboards, Data Models, Connections, Prompts, Agents/Alerts, Data Flows, Calc Scripts | ✅ | Inventory + dependency graph |
| **Schema** | Tables, Views, Columns, Indexes, Constraints, Materialized Views, Sequences | ✅ | Fabric DDL (Delta + Warehouse MVs) |
| **Replication** | Oracle database mirroring | ✅ | Fabric Mirroring config |
| **ETL** | Data Flows (Filter, Join, Aggregate, Sort, Lookup, Union, Pivot, Unpivot) | ✅ | Fabric Pipelines + PySpark Notebooks |
| **ETL** | PL/SQL (FOR, CURSOR, BULK COLLECT, dynamic SQL, DBMS_SCHEDULER) | ✅ | PySpark + Notebook job triggers |
| **ETL** | Error rows, parallel branches | ✅ | Dead-letter Delta + ForEach concurrency |
| **Semantic** | Logical columns, Hierarchies, Joins, Expressions (30+ OAC rules) | ✅ | TMDL tables, measures, relationships |
| **Semantic** | Calculation Groups (YTD/QTD/MTD/YoY/QoQ/MoM) | ✅ | TMDL calculationGroup blocks |
| **Semantic** | Complex expressions → DAX UDFs | ✅ | DAX DEFINE FUNCTION |
| **Semantic** | Direct Lake on OneLake | ✅ | DirectLake TMDL mode |
| **Semantic** | Incremental TMDL updates | ✅ | Delta merge (preserves manual edits) |
| **Reports** | 80+ visual types, Layouts, Bookmarks, Conditional formatting | ✅ | PBIR JSON |
| **Reports** | Prompts (8 types) → Slicers/Parameters | ✅ | Slicer + parameter visuals |
| **Reports** | BI Publisher templates → Paginated Reports | ✅ | .rdl (Power BI Report Builder) |
| **Reports** | OAC Agents/Alerts → Data Activator triggers | ✅ | Fabric Reflex items |
| **Reports** | Action links → Task Flows, drillthrough, bookmarks | ✅ | Translytical + PBI actions |
| **Reports** | Visual calculations (custom totals, running sums) | ✅ | PBI visual calculations |
| **Reports** | Fluent 2 themes (CY26SU03) | ✅ | Theme JSON |
| **Security** | App roles → RLS (DAX filters) | ✅ | RLS role definitions |
| **Security** | Object permissions → OLS | ✅ | metadataPermission |
| **Security** | Workspace roles → Fabric workspace roles | ✅ | REST API assignment |
| **Security** | AAD group provisioning | ✅ | Microsoft Graph API |
| **Security** | Dynamic RLS (multi-valued, hierarchy) | ✅ | PATHCONTAINS + CONTAINSSTRING |
| **Security** | Audit trail → Fabric audit log | ✅ | Delta audit table |
| **Validation** | Data, semantic, report, RLS, performance | ✅ | Reconciliation reports |
| **Not Supported** | Cell-level security, custom OAC visual plugins | ❌ | No PBI API equivalent |

</details>

---

## 🏗️ v6.0 New Capabilities (Phases 54–62)

```mermaid
graph LR
    subgraph P54["Phase 54"]
        MV["Materialized<br/>Views"]
        MIR["Oracle<br/>Mirroring"]
    end
    subgraph P55["Phase 55"]
        CG["Calculation<br/>Groups"]
        UDF["DAX<br/>UDFs"]
    end
    subgraph P56["Phase 56"]
        BIP["BI Publisher<br/>→ RDL"]
    end
    subgraph P57["Phase 57"]
        ALT["Data<br/>Activator"]
    end
    subgraph P58["Phase 58"]
        TF["Task<br/>Flows"]
    end
    subgraph P59["Phase 59"]
        PIV["Pivot /<br/>Unpivot"]
        ERR["Error Row<br/>Routing"]
    end
    subgraph P60["Phase 60"]
        INC["Incremental<br/>Discovery"]
        DTM["Delta<br/>TMDL"]
    end
    subgraph P61["Phase 61"]
        DL["Direct<br/>Lake"]
        VC["Visual<br/>Calcs"]
    end
    subgraph P62["Phase 62"]
        AAD["AAD Group<br/>Provisioning"]
        DYN["Dynamic<br/>RLS"]
        AUD["Audit<br/>Trail"]
    end

    P54 --> P55 --> P56 --> P57 --> P58 --> P59 --> P60 --> P61 --> P62

    style P54 fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style P55 fill:#7B68EE,stroke:#5B48CE,color:#fff
    style P56 fill:#E74C3C,stroke:#C0392B,color:#fff
    style P57 fill:#F39C12,stroke:#D68910,color:#fff
    style P58 fill:#2ECC71,stroke:#1A9F55,color:#fff
    style P59 fill:#FF8C42,stroke:#D96B20,color:#fff
    style P60 fill:#1ABC9C,stroke:#16A085,color:#fff
    style P61 fill:#9B59B6,stroke:#7D3C98,color:#fff
    style P62 fill:#34495E,stroke:#2C3E50,color:#fff
```

---

## 🧠 v8.0 — Multi-Agent Intelligence & Practical Tooling

### Phase 70: Agent Intelligence Framework ✅

LLM reasoning loop that wraps around each agent's existing rule engine — rules fire first (fast, deterministic), the LLM handles planning, error diagnosis, and novel patterns.

```mermaid
graph TB
    subgraph ORCH["Intelligent Orchestrator (08+)"]
        WP["AI Wave Planner"]
        RO["Resource Optimizer"]
        AS["Adaptive Scheduler"]
    end

    subgraph AGENT1["Agent (01–06)"]
        LLM1["LLM Reasoning<br/>Loop (ReAct)"]
        RE1["Rule Engine<br/>(300+ rules)"]
        MEM1["Agent Memory<br/>(Lakehouse)"]
    end

    subgraph AGENT2["Agent (01–06)"]
        LLM2["LLM Reasoning<br/>Loop (ReAct)"]
        RE2["Rule Engine<br/>(300+ rules)"]
        MEM2["Agent Memory<br/>(Lakehouse)"]
    end

    subgraph STORE["Shared Memory Store (Lakehouse Delta)"]
        AM["agent_memory"]
        HM["handoff_messages"]
        EQ["escalation_queue"]
    end

    ORCH --> AGENT1
    ORCH --> AGENT2
    AGENT1 --> STORE
    AGENT2 --> STORE

    style ORCH fill:#FF6B35,stroke:#C44D1A,color:#fff
    style AGENT1 fill:#2ECC71,stroke:#1A9F55,color:#fff
    style AGENT2 fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style STORE fill:#7B68EE,stroke:#5B48CE,color:#fff
```

**5 intelligence modules** (90 tests):
- `reasoning_loop.py` — ReAct (Reason+Act) pattern with step-level retry
- `agent_memory.py` — Per-agent persistent memory, vector-indexed semantic retrieval
- `tool_registry.py` — Typed tool definitions with permission scoping per agent
- `cost_controller.py` — Token budgets, semantic cache, request batching
- `prompt_builder.py` — Domain-specific prompt templates, context window management

### Practical Migration Tooling ✅

5 validation & testing tools that catch real migration bugs — a prerequisite for safe AI-assisted translation.

```mermaid
graph LR
    subgraph TOOLS["Migration Tooling (src/tools/)"]
        DAX["DAX Deep<br/>Validator<br/>14 error codes"]
        TMDL["TMDL File<br/>Validator<br/>structure checks"]
        REC["Reconciliation<br/>CLI<br/>offline + live"]
        OAC["OAC Test<br/>Harness<br/>VCR cassettes"]
        FAB["Fabric<br/>Dry-Run<br/>naming + order"]
    end

    subgraph CATCHES["Real Bugs Caught"]
        BUG1["Essbase nested<br/>bracket refs"]
        BUG2["Missing VAR/<br/>RETURN pairs"]
        BUG3["Deprecated<br/>DAX functions"]
    end

    TOOLS --> CATCHES

    style TOOLS fill:#E74C3C,stroke:#C0392B,color:#fff
    style CATCHES fill:#F39C12,stroke:#D68910,color:#fff
```

**101 new tests** (3,760 total) | [Full tool docs →](docs/ARCHITECTURE.md)

---

## 📝 CLI Reference

<details>
<summary>🔧 All CLI commands</summary>

| Command | Description |
|:--------|:------------|
| `oac-migrate discover` | Run Discovery Agent (01) — inventory all OAC assets |
| `oac-migrate plan` | Generate wave plan without executing |
| `oac-migrate migrate` | Full orchestrated migration (all 7 agents) |
| `oac-migrate migrate --dry-run` | Preview migration without executing |
| `oac-migrate migrate --agents 01-discovery,02-schema` | Run specific agents only |
| `oac-migrate migrate --resume` | Resume from last checkpoint |
| `oac-migrate validate` | Run validation suite standalone |
| `oac-migrate status` | Show migration progress |
| `oac-migrate marketplace list\|install\|publish` | Plugin marketplace operations |
| `oac-migrate analytics --format json\|csv\|powerbi` | Export migration analytics |
| `oac-migrate optimize` | AI-assisted schema optimization |
| `oac-migrate tune` | Performance auto-tuning analysis |

**Global flags:**

| Flag | Description |
|:-----|:------------|
| `--config, -c` | Path to TOML config (default: `config/migration.toml`) |
| `--env, -e` | Environment overlay (`dev`, `test`, `prod`) |
| `--output-dir, -o` | Output directory for reports |
| `--verbose, -v` | Enable DEBUG logging |
| `--quiet, -q` | Suppress non-error output |

</details>

---

## 🖥️ User Interfaces

### React Dashboard

5-page SPA: Migration List → Detail → Wizard → Inventory Browser → Dark Mode.

Built with React 18 + TypeScript + Vite + TanStack Query. Real-time updates via WebSocket/SSE.

```bash
cd dashboard && npm install && npm run dev    # → http://localhost:5173
```

### REST API

| Method | Endpoint | Purpose |
|:------:|:---------|:--------|
| `POST` | `/migrations` | Create new migration |
| `GET` | `/migrations` | List all migrations |
| `GET` | `/migrations/{id}` | Get status + details |
| `GET` | `/migrations/{id}/inventory` | Browse discovered assets |
| `GET` | `/migrations/{id}/logs` | Stream logs (SSE) |
| `POST` | `/migrations/{id}/cancel` | Cancel migration |
| `WS` | `/ws/migrations/{id}` | Real-time events |
| `GET` | `/health` | Health check |

---

## 📂 Generated Output

```
output/
├── discovery/
│   └── discovery_inventory.md              ← Asset inventory + dependency graph
├── schema/
│   ├── ddl/                                ← CREATE TABLE (Delta format)
│   └── type_mapping_log.json               ← Oracle → Fabric type map
├── etl/
│   ├── pipelines/                          ← Fabric Data Factory JSON
│   ├── notebooks/                          ← PySpark notebooks
│   └── schedules/                          ← Fabric triggers
├── semantic/
│   └── definition/
│       ├── model.tmdl                      ← Tables, measures, relationships
│       ├── expressions.tmdl                ← Power Query M queries
│       └── tables/
│           ├── DimCustomer.tmdl            ← Columns + DAX measures
│           └── Calendar.tmdl              ← Auto-generated date table
├── reports/
│   └── definition/
│       ├── report.json                     ← PBIR report config
│       └── pages/
│           └── Overview/
│               ├── page.json               ← Layout + filters
│               └── visuals/
│                   └── [id]/visual.json    ← Each visual definition
├── security/
│   ├── rls_roles.json                      ← Row-Level Security (DAX filters)
│   ├── ols_rules.json                      ← Object-Level Security
│   └── workspace_roles.json                ← Fabric workspace role assignments
├── validation/
│   ├── reconciliation_report.md            ← Row counts, checksums
│   └── semantic_validation.json            ← Model comparison results
└── orchestrator/
    └── migration_summary.md                ← Overall status + timing
```

<details>
<summary>📁 Project structure</summary>

```
OACToFabric/
├── 📄 README.md                 ← You're here
├── 📄 AGENTS.md                 # 8-agent architecture & handoff protocol
├── 📄 DEV_PLAN.md               # Development plan (Phases 0–50)
├── 📄 MIGRATION_PLAYBOOK.md     # Step-by-step production guide
├── 📄 CONTRIBUTING.md           # Contributor guide
├── 📄 CHANGELOG.md              # Release history
│
├── 🐍 src/
│   ├── core/                    # 38 modules — config, models, LLM, telemetry,
│   │                            #   RPD binary parser, schema optimizer, perf tuner
│   ├── agents/                  # 8 agents × ~7 modules each
│   │   ├── discovery/           # OAC crawling, RPD parsing, dependency graph, incremental crawler
│   │   ├── schema/              # DDL generation, type mapping, SQL translation, MV gen, mirroring
│   │   ├── etl/                 # Dataflow → pipeline, PL/SQL → PySpark, pivot/unpivot, error routing
│   │   ├── semantic/            # RPD → TMDL, expressions → DAX, calc groups, UDFs, Direct Lake
│   │   ├── report/              # Visuals, layouts, prompts → slicers (PBIR), BIP → RDL, Data Activator
│   │   ├── security/            # Roles → RLS/OLS, AAD provisioning, dynamic RLS, audit trail
│   │   ├── validation/          # Data reconciliation, semantic + report validation
│   │   └── orchestrator/        # DAG engine, wave planner, notifications
│   ├── api/                     # FastAPI (REST + WebSocket + SSE) + GraphQL + JWT/RBAC
│   ├── cli/                     # argparse CLI — 12 commands
│   ├── clients/                 # OAC, Fabric, Power BI API clients
│   ├── connectors/              # 6 connectors: OAC, OBIEE, Tableau, Essbase, Cognos, Qlik
│   ├── deployers/               # Fabric, PBI, Pipeline deployers
│   ├── plugins/                 # Plugin framework, marketplace, analytics dashboard
│   ├── testing/                 # Integration test harness
│   ├── tools/                   # 5 practical migration tools (DAX/TMDL validator,
│   │                            #   reconciliation, OAC harness, Fabric dry-run)
│   └── validation/              # Visual diff, data quality checks
│
├── ⚙️  dashboard/                # React 18 + Vite + TypeScript SPA
├── 🧪 tests/                    # 3,760 tests across 140+ files
├── ⚙️  config/                   # TOML configs (dev, migration, prod)
├── 🏗️  infra/                    # Bicep IaC for Azure resources
├── 📚 docs/                     # ADRs, runbooks, guides
├── 📋 agents/                   # Agent SPEC documents (01–08)
└── 🔧 scripts/                  # Dev setup, deployment scripts
```

</details>

---

## 🚀 Deployment

<details>
<summary>☁️ Microsoft Fabric</summary>

```toml
# config/migration.toml
[fabric]
workspace_id = "<workspace-guid>"
lakehouse_name = "MigrationLakehouse"

[openai]
deployment = "gpt-4"
endpoint = "https://<resource>.openai.azure.com"
```

```bash
oac-migrate migrate --config config/migration.toml
```

Deploys: Lakehouse (Delta tables) + Semantic Model (TMDL) + Reports (PBIR) + Data Factory Pipelines.

</details>

<details>
<summary>⚙️ Configuration</summary>

```toml
# config/migration.toml
[migration]
environment = "dev"
output_dir = "output"
log_level = "INFO"

[scope]
include_paths = ["/shared"]
exclude_paths = ["/shared/archive"]
asset_types = []                    # empty = all types

[orchestrator]
max_retries = 3
parallel_agents_per_wave = 3
max_items_per_wave = 50
validate_after_each_wave = true

[llm]
enabled = false                     # Enable for GPT-4 fallback
model = "gpt-4"
temperature = 0.1
cache_enabled = true

[marketplace]
enabled = true
registry_path = "plugins/registry.json"

[schema_optimizer]
ai_enabled = true
direct_lake_threshold_gb = 10

[perf_auto_tuner]
scan_threshold_rows = 1_000_000
slow_query_threshold_seconds = 5
```

</details>

---

## ✅ Validation

```python
from src.agents.validation.validation_agent import ValidationAgent

agent = ValidationAgent(config=agent_config)
report = await agent.validate(migration_result)
# → {"status": "PASSED", "checks": 42, "failures": 0, "warnings": 2}
```

The validation agent checks:
- **Data reconciliation** — row counts, checksums, sample queries
- **Semantic model** — tables, columns, measures, relationships match
- **Report structure** — pages, visuals, slicers, formatting
- **Security** — RLS filters produce correct results per role
- **Performance** — query benchmarks against baseline

---

## 🧪 Testing

<p align="center">
  <img src="https://img.shields.io/badge/tests-3%2C760_passed-brightgreen?style=for-the-badge" alt="Tests"/>
  <img src="https://img.shields.io/badge/phases-62_+_Phase_70_+_Tooling-blue?style=for-the-badge" alt="Phases"/>
  <img src="https://img.shields.io/badge/warnings-0-green?style=for-the-badge" alt="Warnings"/>
</p>

```bash
python -m pytest tests/ -v                        # Run all 3,760 tests
python -m pytest tests/test_expression_translator.py -v  # Specific module
python -m pytest tests/ --cov=src --cov-report=html      # Coverage report
python -m pytest tests/ -q                        # Quick → 3,760 passed in ~40s
```

<details>
<summary>📋 Test suite breakdown</summary>

| Phase | Status | Tests | Highlights |
|:------|:------:|------:|:-----------|
| **0–38** | ✅ | 1,871 | Core framework, 8 agents, all deployers, incremental sync, multi-tenant |
| **39** | ✅ | +121 | React 18 dashboard (5 pages, dark mode, real-time WebSocket/SSE) |
| **40** | ✅ | +116 | Tableau connector (TWB parser, 55+ calc→DAX rules, REST API, semantic bridge) |
| **41** | ✅ | +155 | Cognos connector (50+ rules, report spec parser) + Qlik connector (72+ rules, load script parser) |
| **42** | ✅ | +48 | Plugin marketplace (registry, installer, visual override & data quality plugins) |
| **43** | ✅ | +31 | Migration analytics dashboard (metrics collector, CSV/JSON/PBIT export) |
| **44** | ✅ | +38 | RPD binary parser (streaming, large-file support, binary→XML converter) |
| **45** | ✅ | +27 | AI schema optimizer (partition key, storage mode, capacity sizing, column pruning) |
| **46** | ✅ | +39 | Performance auto-tuner (DAX optimizer, aggregation advisor, composite model advisor) |
| **47** | ✅ | +168 | T2P gap: 16 modules, calendar gen, self-healing, DAX optimizer, governance |
| **48** | ✅ | +112 | Lineage map, shared model merge, 120+ DAX rules, 80+ visual types |
| **49** | ✅ | +91 | Bridge tables, hierarchy RLS, theme converter, mobile layout, DQ profiler |
| **50** | ✅ | +135 | Strawberry GraphQL schema, DataLoader N+1 prevention, field-level auth |
| **51** | ✅ | +72 | Dry-run simulator (cost/time estimates, risk scoring, preview mode) |
| **52** | ✅ | +65 | Regression tester (data/schema/visual baselines, drift detection) |
| **54–62** | ✅ | +195 | v6.0: MV gen, mirroring, calc groups, DAX UDFs, BIP→RDL, Data Activator, task flows, pivot/unpivot, incremental crawl, Direct Lake, visual calcs, dynamic RLS, audit trail |
| **70** | ✅ | +90 | v8.0: Agent Intelligence Framework — ReAct reasoning loop, agent memory, tool registry, cost controller, prompt builder |
| **Tooling** | ✅ | +101 | Practical tools: DAX deep validator (14 checks), TMDL file validator, reconciliation CLI, OAC test harness, Fabric dry-run |
| **Total** | | **3,760** | **140+ test files, 0 failures, 0 warnings** |

</details>

---

## 📚 Documentation

| Document | Description |
|:---------|:------------|
| 📋 [PROJECT_PLAN.md](PROJECT_PLAN.md) | Master project plan & phase timeline |
| 🤖 [AGENTS.md](AGENTS.md) | 8-agent architecture, file ownership & handoff protocol |
| 🗓️ [DEV_PLAN.md](DEV_PLAN.md) | Detailed dev plan (Phases 0–76, v8.0 intelligence) |
| 📖 [MIGRATION_PLAYBOOK.md](MIGRATION_PLAYBOOK.md) | Step-by-step production migration guide |
| 🧊 [ESSBASE_MIGRATION_PLAYBOOK.md](ESSBASE_MIGRATION_PLAYBOOK.md) | Essbase cube → Fabric migration guide (9 steps) |
| 📐 [ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md](ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md) | Essbase migration architecture (Phases 63–69) |
| 📊 [SMART_VIEW_TO_EXCEL_MIGRATION.md](SMART_VIEW_TO_EXCEL_MIGRATION.md) | Smart View → Excel on Semantic Model (11 sections) |
| 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| 📝 [CHANGELOG.md](CHANGELOG.md) | Version history & release notes |
| 🏗️ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture & data flow |
| 🚀 [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Fabric/PBI deployment, auth, CI/CD |
| 🔢 [docs/MAPPING_REFERENCE.md](docs/MAPPING_REFERENCE.md) | All translation rules — types, SQL, DAX, visuals |
| 📊 [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | Implementation coverage & improvements |
| ⚠️ [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | Current gaps & workarounds |
| ❓ [docs/FAQ.md](docs/FAQ.md) | Frequently asked questions |
| 🔐 [docs/security.md](docs/security.md) | Credentials, data handling, LLM security |

---

## ⚠️ Known Limitations

- `MAKEPOINT()` / spatial expressions have no DAX equivalent — skipped with warning
- LOD / level-based aggregations are partially supported — complex cases go to manual review queue
- Custom/third-party OAC visual plugins are not mapped — closest PBI native visual used
- Measure-level OLS is not natively supported in PBI — use perspectives instead
- Binary RPD parsing is experimental — XML export is preferred (Phase 44 binary parser available)
- 10K+ assets may be slow with sequential execution — use wave-based parallelism
- See [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for the full list

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/cyphou/OACToFabric.git
cd OACToFabric
python -m pytest tests/ -q    # Make sure tests pass
```

---

## License

MIT

---

<p align="center">
  Built with ❤️ for enterprise BI migration<br/>
  <sub>If this tool saves you time, consider giving it a ⭐</sub>
</p>
