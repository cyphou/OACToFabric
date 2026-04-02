<h1 align="center">📋 Migration Playbook</h1>
<h3 align="center">OAC → Microsoft Fabric & Power BI</h3>

<p align="center">
  Step-by-step production migration guide.<br/>
  Covers prerequisites, all 8 migration phases, validation, and go-live.
</p>

---

## 🗺️ Migration Journey

```mermaid
graph LR
    P["📋 Prerequisites"] --> D["🔍 Discovery"]
    D --> S["🗄️ Schema"]
    S --> E["🔄 ETL"]
    S --> SM["📐 Semantic"]
    SM --> R["📊 Reports"]
    SM --> SEC["🔒 Security"]
    E --> V["✅ Validation"]
    R --> V
    SEC --> V
    V --> GO["🚀 Go-Live"]

    style P fill:#95A5A6,stroke:#7F8C8D,color:#fff
    style D fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style S fill:#7B68EE,stroke:#5B48CE,color:#fff
    style E fill:#FF8C42,stroke:#D96B20,color:#fff
    style SM fill:#2ECC71,stroke:#1A9F55,color:#fff
    style R fill:#E74C3C,stroke:#C0392B,color:#fff
    style SEC fill:#F39C12,stroke:#D68910,color:#fff
    style V fill:#1ABC9C,stroke:#16A085,color:#fff
    style GO fill:#27AE60,stroke:#1E8449,color:#fff
```

---

## 📑 Table of Contents

1. [Prerequisites](#1--prerequisites)
2. [Environment Setup](#2--environment-setup)
3. [Phase 1 — Discovery](#3--phase-1--discovery)
4. [Phase 2 — Schema Migration](#4--phase-2--schema-migration)
5. [Phase 3 — ETL Pipeline Migration](#5--phase-3--etl-pipeline-migration)
6. [Phase 4 — Semantic Model Migration](#6--phase-4--semantic-model-migration)
7. [Phase 5 — Report Migration](#7--phase-5--report-migration)
8. [Phase 6 — Security Migration](#8--phase-6--security-migration)
9. [Phase 7 — Validation](#9--phase-7--validation)
10. [Phase 8 — Cutover & Go-Live](#10--phase-8--cutover--go-live)
11. [Troubleshooting](#11--troubleshooting)

---

## 1. 📦 Prerequisites

### Source Environment (Oracle)

| Requirement | Details |
|:------------|:--------|
| ☐ OAC Instance | URL + admin credentials (IDCS) |
| ☐ RPD Export | XML format from OAC admin console |
| ☐ Oracle Database | Connection details for physical data layer |
| ☐ Application Roles | Full list of OAC roles + user mappings |
| ☐ Data Flows | Exported data flow definitions |

### Target Environment (Microsoft)

| Requirement | Details |
|:------------|:--------|
| ☐ Azure Subscription | With Fabric capacity (F2 or higher) |
| ☐ Fabric Workspace | Created and configured |
| ☐ Power BI Licenses | Pro or Premium Per User for creators |
| ☐ Azure AD | Tenant with groups mapped to OAC roles |
| ☐ Azure Key Vault | For secret management |
| ☐ Azure OpenAI | GPT-4 deployment for LLM-assisted translation |

### Tool Setup

```bash
# Python 3.12+ required
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -e .
```

---

## 2. ⚙️ Environment Setup

### 2.1 Configure Secrets

Store credentials in Azure Key Vault (**never** in config files):

```bash
az keyvault secret set --vault-name <vault> --name oac-url         --value "https://your-oac.analytics.ocp.oraclecloud.com"
az keyvault secret set --vault-name <vault> --name oac-client-id    --value "<idcs-client-id>"
az keyvault secret set --vault-name <vault> --name oac-client-secret --value "<idcs-client-secret>"
az keyvault secret set --vault-name <vault> --name fabric-sql-endpoint --value "<lakehouse-sql-endpoint>"
az keyvault secret set --vault-name <vault> --name openai-api-key   --value "<api-key>"
```

### 2.2 Configure `migration.toml`

```toml
[migration]
name = "OAC_to_Fabric_2025"
waves = 3

[oac]
url = "https://your-oac.analytics.ocp.oraclecloud.com"
rpd_path = "./exports/rpd_export.xml"

[fabric]
workspace_id = "<workspace-guid>"
lakehouse_name = "MigrationLakehouse"

[keyvault]
vault_url = "https://<vault>.vault.azure.net/"

[openai]
deployment = "gpt-4"
endpoint = "https://<resource>.openai.azure.com"

[notifications]
teams_webhook = "https://outlook.office.com/webhook/..."
email_recipients = ["admin@company.com"]
```

### 2.3 Architecture in Your Environment

```mermaid
graph TB
    subgraph Source["Oracle Environment"]
        OAC["OAC Instance"]
        ORCL["Oracle Database"]
        RPD["RPD Export #40;XML#41;"]
    end

    subgraph Migration["Migration Tool #40;This Repo#41;"]
        TOOL["OAC-to-Fabric<br/>Framework"]
        LLM["Azure OpenAI<br/>GPT-4"]
    end

    subgraph Target["Microsoft Fabric"]
        LH["Lakehouse<br/>#40;Delta Tables#41;"]
        WH["Warehouse"]
        PBI["Power BI Service<br/>Semantic Models<br/>+ Reports"]
        PIPE["Data Factory<br/>Pipelines"]
    end

    subgraph Security["Azure AD"]
        KV["Key Vault"]
        AD["Groups & Roles"]
    end

    OAC -->|"REST API"| TOOL
    ORCL -->|"JDBC"| TOOL
    RPD -->|"XML Parse"| TOOL
    TOOL -->|"GPT-4 API"| LLM
    TOOL -->|"Deploy"| LH
    TOOL -->|"Deploy"| WH
    TOOL -->|"XMLA / REST"| PBI
    TOOL -->|"Deploy"| PIPE
    KV -->|"Secrets"| TOOL
    TOOL -->|"RLS/Roles"| AD

    style Source fill:#E74C3C,stroke:#C0392B,color:#fff
    style Target fill:#2ECC71,stroke:#27AE60,color:#fff
    style Migration fill:#3498DB,stroke:#2980B9,color:#fff
    style Security fill:#F39C12,stroke:#D68910,color:#fff
```

---

## 3. 🔍 Phase 1 — Discovery

> **Agent**: 01 — Discovery & Inventory

```bash
python -m src.cli.main discover --config migration.toml
```

```mermaid
flowchart LR
    OAC["OAC REST API"] --> DISC["Discovery Agent"]
    RPD2["RPD XML"] --> DISC
    DISC --> INV["migration_inventory<br/>#40;Delta table#41;"]
    DISC --> DEP["Dependency Graph<br/>#40;JSON#41;"]
    DISC --> COMP["Complexity Assessment<br/>#40;CSV#41;"]

    style DISC fill:#4A90D9,stroke:#2C5F8A,color:#fff
```

**Expected output:**
- `migration_inventory` Delta table populated in Fabric Lakehouse
- Dependency graph JSON
- Complexity assessment CSV

**✅ Verification checklist:**

| Check | Command / Action |
|:------|:-----------------|
| ☐ All subject areas discovered | Review inventory table |
| ☐ All analyses & dashboards listed | `SELECT COUNT(*) FROM migration_inventory WHERE asset_type IN ('analysis','dashboard')` |
| ☐ Physical table count matches Oracle | Compare with `dba_tables` count |
| ☐ Data flows captured | Verify step counts per flow |
| ☐ No RPD parse errors | Check `agent_logs` for errors |

---

## 4. 🗄️ Phase 2 — Schema Migration

> **Agent**: 02 — Schema & Data Model

```bash
python -m src.cli.main migrate --agents 02-schema --config migration.toml
```

```mermaid
flowchart LR
    INV2["Inventory"] --> SCHEMA["Schema Agent"]
    ORCL2["Oracle DDL"] --> SCHEMA
    SCHEMA --> DDL["DDL Scripts"]
    SCHEMA --> DELTA["Fabric Lakehouse<br/>Delta Tables"]
    SCHEMA --> MAP["Type Mapping Log"]

    style SCHEMA fill:#7B68EE,stroke:#5B48CE,color:#fff
```

**Type mapping examples:**

| Oracle Type | Fabric Type |
|:------------|:------------|
| `NUMBER(10)` | `bigint` |
| `VARCHAR2(100)` | `string` |
| `DATE` | `timestamp` |
| `CLOB` | `string` |
| `RAW` | `binary` |

**✅ Verification:**
- ☐ DDL scripts generated in `output/ddl/`
- ☐ Tables visible in Fabric Lakehouse
- ☐ Data types correctly mapped (check `mapping_rules` table)
- ☐ No unmapped Oracle types (review warnings)

---

## 5. 🔄 Phase 3 — ETL Pipeline Migration

> **Agent**: 03 — ETL/Data Pipeline

```bash
python -m src.cli.main migrate --agents 03-etl --config migration.toml
```

```mermaid
flowchart LR
    DF["OAC Data Flows"] --> ETL["ETL Agent"]
    PLSQL["PL/SQL Jobs"] --> ETL
    SCHED["Schedule Metadata"] --> ETL
    ETL --> PIPE2["Fabric Data Factory<br/>Pipeline JSON"]
    ETL --> NB["PySpark Notebooks"]
    ETL --> TRIG["Fabric Triggers<br/>#40;scheduling#41;"]

    style ETL fill:#FF8C42,stroke:#D96B20,color:#fff
```

**✅ Verification:**
- ☐ Pipeline JSON in `output/pipelines/`
- ☐ PySpark notebooks in `output/notebooks/`
- ☐ No untranslatable PL/SQL blocks (review warnings)
- ☐ Scheduling metadata preserved

---

## 6. 📐 Phase 4 — Semantic Model Migration

> **Agent**: 04 — Semantic Model

```bash
python -m src.cli.main migrate --agents 04-semantic --config migration.toml
```

```mermaid
flowchart LR
    RPD3["RPD Logical Model"] --> SEM["Semantic Agent"]
    CALC["OAC Calculations"] --> SEM
    HIER["Hierarchies"] --> SEM
    SEM -->|"Rules + LLM"| TMDL["Power BI TMDL<br/>Tables • Columns<br/>Measures • Relationships"]

    style SEM fill:#2ECC71,stroke:#1A9F55,color:#fff
```

**Translation engine flow:**

```mermaid
flowchart LR
    EXPR["OAC Expression"] --> RB{"Rule-Based<br/>#40;30+ mappings#41;"}
    RB -->|"✅"| DAX2["DAX Measure"]
    RB -->|"❌"| GPT["GPT-4<br/>Fallback"]
    GPT --> VAL2{"Syntax<br/>Valid?"}
    VAL2 -->|"✅"| DAX2
    VAL2 -->|"❌"| MAN["Manual<br/>Review"]

    style RB fill:#2ECC71,stroke:#27AE60,color:#fff
    style GPT fill:#9B59B6,stroke:#8E44AD,color:#fff
```

**✅ Verification:**
- ☐ TMDL files in `output/semantic_model/`
- ☐ Tables, columns, and relationships present
- ☐ DAX measures generated for all calculated columns
- ☐ Hierarchies preserved
- ☐ Open in Tabular Editor to verify

---

## 7. 📊 Phase 5 — Report Migration

> **Agent**: 05 — Report & Dashboard

```bash
python -m src.cli.main migrate --agents 05-report --config migration.toml
```

```mermaid
flowchart LR
    ANA["OAC Analyses"] --> REP["Report Agent"]
    DASH2["OAC Dashboards"] --> REP
    PROMPT["OAC Prompts"] --> REP
    REP --> PBIR["PBIR Files"]
    REP --> VIS["Visual Configs"]
    REP --> SLIC["Slicers &<br/>Bookmarks"]

    style REP fill:#E74C3C,stroke:#C0392B,color:#fff
```

**Visual type mapping:**

| OAC Visual | Power BI Visual |
|:-----------|:----------------|
| Pivot Table | Matrix |
| Bar/Column Chart | Clustered Column |
| Line Chart | Line Chart |
| Pie Chart | Pie Chart |
| Gauge | Gauge |
| Map | Azure Map |
| KPI | Card / KPI |

**✅ Verification:**
- ☐ PBIR files in `output/reports/`
- ☐ Visual types mapped correctly
- ☐ Slicers created from OAC prompts
- ☐ Page layouts approximate OAC dashboards
- ☐ Deploy to PBI Service and visually compare

---

## 8. 🔒 Phase 6 — Security Migration

> **Agent**: 06 — Security & Governance

```bash
python -m src.cli.main migrate --agents 06-security --config migration.toml
```

```mermaid
flowchart LR
    ROLES["OAC App Roles"] --> SECAG["Security Agent"]
    SESS["Session Variables"] --> SECAG
    OBJP["Object Permissions"] --> SECAG
    SECAG --> RLS["RLS Roles<br/>#40;DAX filters#41;"]
    SECAG --> OLS["OLS Rules<br/>#40;column restrictions#41;"]
    SECAG --> WSR2["Workspace Roles"]

    style SECAG fill:#F39C12,stroke:#D68910,color:#fff
```

**Security mapping:**

| OAC Concept | Power BI Equivalent |
|:------------|:--------------------|
| Application Role | Workspace Role + RLS Role |
| Session Variable Filter | RLS DAX filter (`USERPRINCIPALNAME()`) |
| Object Permission | Object-Level Security (OLS) |
| Data-Level Security | Row-Level Security (RLS) |

**✅ Verification:**
- ☐ RLS roles defined in semantic model
- ☐ OLS column restrictions applied
- ☐ Workspace roles assigned
- ☐ Test with different user accounts

---

## 9. ✅ Phase 7 — Validation

> **Agent**: 07 — Validation & Testing

```bash
python -m src.cli.main validate --config migration.toml
```

```mermaid
flowchart TB
    subgraph Checks["Validation Checks"]
        DC["Data Reconciliation<br/>Row counts • Checksums"]
        SC["Semantic Validation<br/>Measures • Relationships"]
        RC["Report Validation<br/>Visual comparison"]
        RLSC["Security Validation<br/>RLS per-user tests"]
    end

    DC --> RESULTS["validation_results<br/>#40;Delta table#41;"]
    SC --> RESULTS
    RC --> RESULTS
    RLSC --> RESULTS
    RESULTS --> REPORT2["Validation Report"]

    style DC fill:#3498DB,stroke:#2980B9,color:#fff
    style SC fill:#2ECC71,stroke:#27AE60,color:#fff
    style RC fill:#E74C3C,stroke:#C0392B,color:#fff
    style RLSC fill:#F39C12,stroke:#D68910,color:#fff
```

**✅ Verification:**
- ☐ Row count reconciliation passes (±1%)
- ☐ Measure values match within tolerance
- ☐ RLS produces correct filtered results per user
- ☐ All results written to `validation_results` Delta table

---

## 10. 🚀 Phase 8 — Cutover & Go-Live

### Full Migration Run

```bash
python -m src.cli.main migrate --config migration.toml
```

### Go-Live Timeline

```mermaid
gantt
    title Cutover Weekend Plan
    dateFormat HH:mm
    axisFormat %H:%M

    section Friday
    Freeze OAC changes          :f1, 18:00, 1h
    Final data sync             :f2, after f1, 2h
    Run full migration          :crit, f3, after f2, 4h

    section Saturday
    Validation suite            :s1, 01:00, 3h
    Fix any issues              :s2, after s1, 3h
    UAT with key users          :s3, 08:00, 4h

    section Sunday
    Final sign-off              :su1, 09:00, 2h
    Switch DNS / URLs           :crit, su2, after su1, 1h
    Monitor                     :su3, after su2, 4h
    Go / No-Go decision         :milestone, after su3, 0h
```

### 📋 Go-Live Checklist

| Category | Check | Status |
|:---------|:------|:------:|
| **Data** | All validation tests pass | ☐ |
| **Data** | Row counts match ±1% | ☐ |
| **Reports** | Visual comparison approved | ☐ |
| **Security** | RLS tested per role | ☐ |
| **Users** | UAT complete, sign-off received | ☐ |
| **Training** | Materials distributed | ☐ |
| **Access** | OAC set to read-only | ☐ |
| **Access** | PBI reports shared with end users | ☐ |
| **Monitoring** | App Insights dashboards active | ☐ |
| **Rollback** | Rollback plan documented & tested | ☐ |

---

## 11. 🔧 Troubleshooting

| Issue | Solution |
|:------|:---------|
| RPD parse error | Check XML encoding, run with `--log-level DEBUG` |
| 429 rate limit from OAC API | Reduce `--concurrency` setting |
| TMDL deployment fails | Verify XMLA endpoint enabled on Fabric capacity |
| DAX measure compilation error | Run `src/tools/dax_validator.py` on output, review DAX001–DAX014 errors |
| TMDL structure issues | Run `src/tools/tmdl_file_validator.py` to check output directory structure |
| Data type mismatch | Check `mapping_rules` table, add custom mapping |
| RLS not working | Verify DAX filter syntax, check `USERPRINCIPALNAME()` |
| Checkpoint resume fails | Delete `.checkpoint/` directory and restart |
| LLM translation poor quality | Review prompt templates in `src/core/prompt_templates.py` |
| Deployment naming errors | Run `src/tools/fabric_dry_run.py` to validate naming before deploy |

### Pre-Deployment Validation (v8.0 Tooling)

```mermaid
flowchart LR
    OUT["Migration<br/>Output"] --> DAX["DAX<br/>Validator"]
    OUT --> TMDL["TMDL<br/>Validator"]
    OUT --> DRY["Fabric<br/>Dry-Run"]
    DAX --> CHK{"All<br/>passed?"}
    TMDL --> CHK
    DRY --> CHK
    CHK -->|Yes| DEPLOY["Deploy to<br/>Fabric"]
    CHK -->|No| FIX["Review &<br/>Fix Issues"]
    FIX --> OUT

    style OUT fill:#4A90D9,stroke:#2C5F8A,color:#fff
    style DAX fill:#E74C3C,stroke:#C0392B,color:#fff
    style TMDL fill:#2ECC71,stroke:#1A9F55,color:#fff
    style DRY fill:#7B68EE,stroke:#5B48CE,color:#fff
    style DEPLOY fill:#0078D4,stroke:#005A9E,color:#fff
    style FIX fill:#F39C12,stroke:#D68910,color:#fff
```

### Diagnostic Commands

```bash
# Verbose logging
python -m src.cli.main migrate --config migration.toml --log-level DEBUG

# Check agent logs
# → query agent_logs Delta table in Fabric

# View migration status
python -m src.cli.main status --config migration.toml

# Start dashboard for visual monitoring
uvicorn src.api.app:app --port 8000
cd dashboard && npm run dev
```

### Getting Help

| Resource | Location |
|:---------|:---------|
| OAC API quirks | `docs/oac-api-notes.md` |
| Credential setup | `docs/security.md` |
| Agent diagnostics | `agent_logs` Delta table |
| Architecture decisions | `docs/adrs/` |
| Operational runbooks | `docs/runbooks/` |
| Essbase migration | `ESSBASE_MIGRATION_PLAYBOOK.md` |
| Smart View → Excel | `SMART_VIEW_TO_EXCEL_MIGRATION.md` |
| Essbase architecture | `ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md` |

---

<p align="center">
  <sub>Happy migrating! 🎉</sub>
</p>
