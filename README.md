<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Tests-2%2C108_passing-brightgreen?logo=pytest&logoColor=white" alt="Tests"/>
  <img src="https://img.shields.io/badge/Phases-40%2F50-blue" alt="Progress"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License"/>
</p>

<h1 align="center">🔄 OAC → Microsoft Fabric & Power BI</h1>
<h3 align="center">Enterprise-Grade Multi-Agent Migration Framework</h3>

<p align="center">
  Automate end-to-end migration from <strong>Oracle Analytics Cloud</strong> to<br/>
  <strong>Microsoft Fabric</strong> and <strong>Power BI</strong> using 8 specialized AI-powered agents.
</p>

---

## ✨ Why This Tool?

| Challenge | How We Solve It |
|:----------|:----------------|
| Manual migration takes months | **8 specialized agents** automate every layer |
| Expression translation is error-prone | **AI-assisted translator** — rules-first with GPT-4 fallback (90+ DAX mappings) |
| No visibility into progress | **React dashboard** with real-time WebSocket/SSE streaming |
| Security rules get lost | **Automated RLS/OLS** generation from OAC session variables |
| Rollback is impossible | **Incremental waves** with full checkpoint & rollback support |
| Locked into one source | **Multi-source connectors** — OAC, OBIEE, Tableau, Cognos, Qlik |

---

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph Sources["📊 Source Platforms"]
        OAC["Oracle Analytics Cloud"]
        OBIEE["Oracle BI EE"]
        TAB["Tableau Server/Cloud"]
        COG["IBM Cognos"]
        QLIK["Qlik Sense"]
    end

    subgraph Framework["⚙️ Migration Framework"]
        direction TB
        CONN["Multi-Source Connectors"]
        ORCH["Orchestrator Agent #40;08#41;"]

        subgraph Agents["Migration Agents"]
            direction LR
            A01["01 Discovery"]
            A02["02 Schema"]
            A03["03 ETL"]
            A04["04 Semantic Model"]
            A05["05 Reports"]
            A06["06 Security"]
            A07["07 Validation"]
        end

        LLM["Azure OpenAI GPT-4<br/>Hybrid Translator"]
    end

    subgraph Targets["🎯 Microsoft Fabric"]
        LH["Fabric Lakehouse<br/>#40;Delta Tables#41;"]
        WH["Fabric Warehouse"]
        PBI["Power BI<br/>Semantic Models + Reports"]
        PIPE["Data Factory<br/>Pipelines"]
    end

    subgraph Interface["🖥️ User Interface"]
        DASH["React Dashboard"]
        CLI2["CLI #40;argparse#41;"]
        API["FastAPI Backend<br/>REST + WebSocket + SSE"]
    end

    Sources --> CONN
    CONN --> ORCH
    ORCH --> Agents
    Agents --> LLM
    Agents --> Targets
    API --> ORCH
    DASH --> API
    CLI2 --> ORCH
```

---

## 🤖 Agent Pipeline

Each migration flows through **8 specialized agents** orchestrated as a DAG:

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

---

## 🔌 Multi-Source Connector Framework

Connect to any supported BI platform through a uniform interface:

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

    class OACConnector {
        OAC REST API
        RPD XML parser
    }
    class OBIEEConnector {
        RPD metadata
        Catalog API
    }
    class TableauConnector {
        REST API v3.21
        TWB/TWBX parser
        Calc → DAX translator
    }
    class CognosConnector {
        Report Studio XML
        REST API ~stub~
    }
    class QlikConnector {
        QVF/QVD extraction
        Engine API ~stub~
    }

    SourceConnector <|-- OACConnector
    SourceConnector <|-- OBIEEConnector
    SourceConnector <|-- TableauConnector
    SourceConnector <|-- CognosConnector
    SourceConnector <|-- QlikConnector
```

| Platform | Status | Capabilities |
|:---------|:------:|:-------------|
| **Oracle Analytics Cloud** | ✅ Full | REST API, RPD parsing, catalog discovery |
| **Oracle BI EE** | ✅ Full | RPD metadata extraction, catalog API |
| **Tableau** | ✅ Full | REST API, TWB/TWBX parsing, 55+ calc→DAX rules |
| **IBM Cognos** | 🔲 Stub | Planned for Phase 41 |
| **Qlik Sense** | 🔲 Stub | Planned for Phase 41 |

---

## 🧠 Expression Translation Engine

The **Hybrid Translator** uses a rules-first approach with LLM fallback for complex expressions:

```mermaid
flowchart LR
    SRC["Source Expression<br/>#40;OAC / Tableau / SQL#41;"] --> RULES{"Rule-Based<br/>Translator<br/>#40;90+ mappings#41;"}
    RULES -->|"✅ Match"| DAX["DAX Expression"]
    RULES -->|"❌ No Match"| LLM["Azure OpenAI<br/>GPT-4"]
    LLM --> VALID{"Syntax<br/>Validator"}
    VALID -->|"✅ Valid"| DAX
    VALID -->|"❌ Invalid"| MANUAL["Manual Review<br/>Queue"]
    DAX --> CACHE["Translation<br/>Cache #40;SQLite#41;"]

    style RULES fill:#2ECC71,stroke:#1A9F55,color:#fff
    style LLM fill:#9B59B6,stroke:#7D3C98,color:#fff
    style DAX fill:#3498DB,stroke:#2980B9,color:#fff
    style CACHE fill:#95A5A6,stroke:#7F8C8D,color:#fff
```

**Coverage:**

| Source | Functions Mapped | Confidence |
|:-------|:----------------:|:----------:|
| OAC → DAX | 30+ | 95% auto |
| Tableau → DAX | 55+ | 85% auto |
| Oracle SQL → Fabric SQL | 30+ | 90% auto |
| LOD / Table calcs | — | Manual review |

---

## 🖥️ User Interfaces

### React Dashboard

A full-featured SPA for managing migrations:

```mermaid
graph LR
    subgraph Dashboard["React 18 + TypeScript + Vite"]
        ML["📋 Migration List<br/>Status • Progress • Sort"]
        MD["📊 Migration Detail<br/>Agent Status • Charts • Logs"]
        MW["🧙 Migration Wizard<br/>Source → Configure → Launch"]
        IB["🔍 Inventory Browser<br/>Search • Filter • Sort"]
        DM["🌙 Dark Mode<br/>System Preference • Toggle"]
    end

    API2["FastAPI<br/>Backend"] <-->|"REST + WebSocket + SSE"| Dashboard

    style Dashboard fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    style API2 fill:#009688,stroke:#00796B,color:#fff
```

### CLI

```bash
# Discover source assets
oac-migrate discover --config migration.toml

# Generate migration plan
oac-migrate plan --config migration.toml --waves 3

# Run full migration
oac-migrate migrate --config migration.toml

# Validate results
oac-migrate validate --config migration.toml

# Check status
oac-migrate status --config migration.toml
```

### REST API

| Method | Endpoint | Purpose |
|:------:|:---------|:--------|
| `POST` | `/migrations` | Create new migration |
| `GET` | `/migrations` | List all migrations |
| `GET` | `/migrations/{id}` | Get migration status |
| `GET` | `/migrations/{id}/inventory` | Browse discovered assets |
| `GET` | `/migrations/{id}/logs` | Stream logs (SSE) |
| `POST` | `/migrations/{id}/cancel` | Cancel migration |
| `WS` | `/ws/migrations/{id}` | Real-time events |
| `GET` | `/health` | Health check |

---

## 📂 Project Structure

```
OACToFabric/
├── 📄 README.md                 ← You're here
├── 📄 AGENTS.md                 # Agent architecture & definitions
├── 📄 DEV_PLAN.md               # Development plan (Phases 0–50)
├── 📄 MIGRATION_PLAYBOOK.md     # Step-by-step production guide
├── 📄 CONTRIBUTING.md           # Contributor guide
├── 📄 CHANGELOG.md              # Release history
├── 📄 PROJECT_PLAN.md           # Master project plan
│
├── 🐍 src/
│   ├── core/                    # 35 modules — config, models, LLM, telemetry
│   ├── agents/                  # 8 agents × ~5 modules each
│   │   ├── discovery/           # OAC crawling, RPD parsing, dependency graph
│   │   ├── schema/              # DDL generation, type mapping, SQL translation
│   │   ├── etl/                 # Dataflow → pipeline, PL/SQL → PySpark
│   │   ├── semantic/            # RPD → TMDL, expressions → DAX, hierarchies
│   │   ├── report/              # Visuals, layouts, prompts → slicers (PBIR)
│   │   ├── security/            # Roles → RLS/OLS, workspace permissions
│   │   ├── validation/          # Data reconciliation, semantic + report validation
│   │   └── orchestrator/        # DAG engine, wave planner, notifications
│   ├── api/                     # FastAPI (REST + WebSocket + SSE) + JWT/RBAC auth
│   ├── cli/                     # argparse CLI — 5 commands
│   ├── clients/                 # OAC, Fabric, Power BI API clients
│   ├── connectors/              # Multi-source: OAC, OBIEE, Tableau, Cognos, Qlik
│   ├── deployers/               # Fabric, PBI, Pipeline deployers
│   ├── plugins/                 # Plugin framework & manager
│   ├── testing/                 # Integration test harness, fixture generators
│   └── validation/              # Visual diff, data quality checks
│
├── ⚛️  dashboard/                # React 18 + Vite + TypeScript SPA
│   ├── src/pages/               # MigrationList, Detail, Wizard, InventoryBrowser
│   ├── src/hooks/               # TanStack Query, WebSocket, SSE hooks
│   └── src/context/             # Theme (dark mode) context
│
├── 🧪 tests/                    # 2,108 tests across 88+ files
├── ⚙️  config/                   # TOML configs (dev, migration, prod)
├── 🏗️  infra/                    # Bicep IaC for Azure resources
├── 📚 docs/                     # ADRs, runbooks, API notes
├── 📋 agents/                   # Agent SPEC documents (01–08)
├── 🔧 scripts/                  # Dev setup, deployment scripts
└── 📝 templates/                # Migration checklists
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+** (3.14 recommended)
- **Node.js 20+** (for dashboard)
- **Azure subscription** with Fabric capacity
- **Azure OpenAI** resource (GPT-4 deployment)

### Installation

```bash
# Clone
git clone <repo-url>
cd OACToFabric

# Python setup
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Dashboard setup
cd dashboard
npm install
npm run dev                     # → http://localhost:5173
```

### Configuration

```toml
# config/migration.toml
[migration]
name = "OAC_to_Fabric_2025"
waves = 3

[oac]
url = "https://your-oac.analytics.ocp.oraclecloud.com"
rpd_path = "./exports/rpd_export.xml"

[fabric]
workspace_id = "<workspace-guid>"
lakehouse_name = "MigrationLakehouse"

[openai]
deployment = "gpt-4"
endpoint = "https://<resource>.openai.azure.com"
```

### Run

```bash
# Full migration
python -m src.cli.main migrate --config config/migration.toml

# Or start the API + React dashboard
uvicorn src.api.app:app --port 8000
cd dashboard && npm run dev
```

---

## 🔄 Data Flow

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

---

## 📊 Coordination Store

All agents communicate via **Delta tables** in Fabric Lakehouse:

```mermaid
erDiagram
    AGENT_TASKS {
        string task_id PK
        string agent_id FK
        string status
        string migration_id
        datetime created_at
        datetime completed_at
    }
    MIGRATION_INVENTORY {
        string asset_id PK
        string asset_type
        string name
        string source_path
        json metadata
        json dependencies
    }
    MAPPING_RULES {
        string rule_id PK
        string source_type
        string source_expr
        string target_expr
        float confidence
    }
    VALIDATION_RESULTS {
        string test_id PK
        string migration_id FK
        string test_type
        string status
        json details
    }
    AGENT_LOGS {
        string log_id PK
        string agent_id FK
        string level
        string message
        datetime timestamp
    }

    AGENT_TASKS ||--o{ AGENT_LOGS : "generates"
    AGENT_TASKS ||--o{ VALIDATION_RESULTS : "produces"
    MIGRATION_INVENTORY ||--o{ MAPPING_RULES : "uses"
```

---

## 🛡️ Security & Authentication

```mermaid
graph LR
    subgraph Auth["Authentication"]
        JWT["JWT Tokens"]
        PAT["Personal Access Tokens"]
        APIKEY["API Keys"]
    end

    subgraph RBAC["Role-Based Access"]
        ADMIN["👑 Admin<br/>Full access"]
        OPER["⚙️ Operator<br/>Run migrations"]
        VIEW["👁️ Viewer<br/>Read-only"]
    end

    subgraph Migration["Migrated Security"]
        RLS["Row-Level Security<br/>DAX filters from<br/>OAC session vars"]
        OLS["Object-Level Security<br/>Column restrictions"]
        WSR["Workspace Roles<br/>From OAC app roles"]
    end

    Auth --> RBAC
    RBAC --> Migration

    style ADMIN fill:#E74C3C,stroke:#C0392B,color:#fff
    style OPER fill:#F39C12,stroke:#D68910,color:#fff
    style VIEW fill:#3498DB,stroke:#2980B9,color:#fff
```

---

## 📈 Development Progress

```mermaid
gantt
    title v4.0 & v5.0 Roadmap
    dateFormat YYYY-MM-DD
    axisFormat %b %Y

    section ✅ Complete
    Phase 39 — React Dashboard       :done, p39, 2026-03-15, 3d
    Phase 40 — Tableau Connector      :done, p40, 2026-03-18, 5d

    section 🔜 v4.0 Next
    Phase 41 — Cognos & Qlik          :p41, 2026-03-25, 14d
    Phase 42 — Plugin Marketplace     :p42, after p41, 10d
    Phase 43 — Analytics Dashboard    :p43, after p42, 7d
    Phase 44 — RPD Binary Parser      :p44, after p43, 14d
    Phase 45 — AI Schema Optimizer    :p45, after p44, 14d
    Phase 46 — Perf Auto-Tuning       :p46, after p45, 14d

    section 📋 v5.0 Planned
    Phase 47 — GraphQL API            :p47, after p46, 21d
    Phase 48 — Dry-Run Simulator      :p48, after p47, 28d
    Phase 49 — Regression Testing     :p49, after p48, 21d
    Phase 50 — Self-Service Portal    :p50, after p49, 28d
```

| Phase | Status | Tests | Highlights |
|:------|:------:|------:|:-----------|
| **0–38** | ✅ | 1,871 | Core framework, 8 agents, all deployers, incremental sync |
| **39** | ✅ | +121 | React 18 dashboard (5 pages, dark mode, real-time) |
| **40** | ✅ | +116 | Tableau connector (TWB parser, 55+ calc→DAX rules, REST API) |
| **41** | 🔜 | — | Cognos & Qlik connectors |
| **42–46** | 📋 | — | Plugin marketplace, analytics, RPD binary, AI optimization |
| **47** | 📋 | — | GraphQL API & Federation (Strawberry, subscriptions) |
| **48** | 📋 | — | Migration Dry-Run Simulator (cost/risk estimation) |
| **49** | 📋 | — | Automated Regression Testing (snapshot diffs, drift detection) |
| **50** | 📋 | — | Self-Service Migration Portal (SSO, drag-and-drop, templates) |
| **Total** | | **2,108** | **88+ test files, 2 skipped, 0 failures** |

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific phase
python -m pytest tests/test_phase40_tableau.py -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html

# Quick summary
python -m pytest tests/ -q
# → 2,108 passed, 2 skipped in ~20s
```

---

## 🔗 Documentation

| Document | Description |
|:---------|:------------|
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | Master project plan, phase timeline |
| [AGENTS.md](AGENTS.md) | Multi-agent architecture, file ownership & handoff protocol |
| [DEV_PLAN.md](DEV_PLAN.md) | Detailed dev plan (Phases 0–50) |
| [MIGRATION_PLAYBOOK.md](MIGRATION_PLAYBOOK.md) | Step-by-step production guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [CHANGELOG.md](CHANGELOG.md) | Version history & release notes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, module responsibilities, data flow |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Fabric/PBI deployment, auth, CI/CD, troubleshooting |
| [docs/MAPPING_REFERENCE.md](docs/MAPPING_REFERENCE.md) | All translation rules — types, SQL, DAX, visuals, security |
| [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | Implementation coverage & priority improvements |
| [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | Current gaps, workarounds & severity ratings |
| [docs/FAQ.md](docs/FAQ.md) | Frequently asked questions |

---

## ⚠️ Known Limitations

| Area | Limitation | Severity | Workaround |
|:-----|:-----------|:--------:|:-----------|
| RPD Parser | XML export only — binary RPD not supported | 🟡 Medium | Export RPD to XML via OAC Admin first |
| DAX Translation | LOD expressions / level-based aggregations — partial | 🟡 Medium | Manual review queue for complex cases |
| Visual Mapping | Custom/third-party OAC plugins — not supported | 🟡 Medium | Map to closest PBI native visual |
| Security | Measure-level OLS — not natively supported in PBI | 🟡 Medium | Use perspectives for conditional visibility |
| Connectors | Cognos & Qlik — stub only | 🔴 High | Planned for Phase 41 |
| Performance | 10K+ assets — sequential agent execution may be slow | 🟡 Medium | Use wave-based migration with parallelism |

> **Full details**: [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md)

---

## 🏛️ Key Design Principles

> **Automation-first** — Every migration step that can be automated, should be.
>
> **Agent specialization** — Each agent owns one migration domain end-to-end.
>
> **Orchestrated workflow** — DAG-based execution with dependency tracking.
>
> **Validation at every stage** — No step is "done" without automated verification.
>
> **Incremental & reversible** — Migrate in waves with full checkpoint & rollback.
>
> **Multi-source ready** — Not just OAC — Tableau, OBIEE, Cognos, Qlik too.

---

<p align="center">
  <sub>Built with ❤️ for enterprise BI migration</sub>
</p>
