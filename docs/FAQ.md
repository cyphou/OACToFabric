# Frequently Asked Questions

---

## General

### What is this project?
An automated migration framework that converts Oracle Analytics Cloud (OAC) environments to Microsoft Fabric and Power BI. It uses 8 specialized agents to handle discovery, schema, ETL, semantic model, report, security, validation, and orchestration.

### What source platforms are supported?

| Platform | Status |
|----------|--------|
| Oracle Analytics Cloud | Full support |
| Oracle BI EE (OBIEE) | Full support |
| Tableau Server/Cloud | Full support (Phase 40) |
| Oracle Essbase | Full support — REST API, outline parser, 55+ calc→DAX, 24+ MDX→DAX, filters→RLS |
| IBM Cognos | Full support (Phase 41) |
| Qlik Sense | Full support (Phase 41) |

### What gets migrated?
- **Schema**: Oracle tables → Fabric Lakehouse (Delta) or Warehouse (T-SQL)
- **ETL**: OAC Data Flows / PL/SQL → Fabric Data Factory pipelines + PySpark notebooks
- **Semantic Model**: RPD logical model → Power BI TMDL semantic model
- **Reports**: OAC Analyses/Dashboards → Power BI PBIR reports
- **Security**: OAC roles → Power BI RLS/OLS + Fabric workspace roles
- **Schedules**: OAC schedules → Fabric triggers

### Does this require Azure OpenAI?
Only for complex expression translations that can't be handled by the 120+ deterministic rules. The hybrid translator uses rules first and falls back to GPT-4 for edge cases. Unit tests run fully offline without any LLM dependency.

---

## Setup & Configuration

### What are the prerequisites?
- Python 3.12+ (3.14 recommended)
- Node.js 20+ (for React dashboard)
- Azure subscription with Fabric capacity (F2+ recommended)
- Azure OpenAI resource with GPT-4 deployment (optional, for complex translations)

### How do I run it locally?
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest tests/ -v       # Verify setup — all 3,760 tests should pass
```

### Do I need OAC/Fabric credentials for development?
No. All tests use mocked APIs and run fully offline. You only need credentials for live testing against actual OAC/Fabric environments.

### Where do I configure credentials?
Store secrets in Azure Key Vault. The framework reads them via `src/core/keyvault_provider.py`. For local dev, copy `.env.example` to `.env` and fill in values.

---

## Migration

### How long does a migration take?
It depends on scale. See the [Deployment Guide](DEPLOYMENT_GUIDE.md#capacity-planning) for estimates by environment size.

### Can I migrate incrementally?
Yes. Use `--mode incremental` to only migrate assets that changed since the last run. The `ChangeDetector` and `SyncJournal` track what was previously migrated.

### Can I rollback a migration?
Yes. The `ArtifactVersioner` snapshots every deployed artifact. Use the `RollbackEngine` to revert to any previous version.

### What happens if an agent fails mid-migration?
The framework checkpoints progress after each agent task. Use `--resume` to restart from the last successful checkpoint.

### How does wave-based migration work?
The orchestrator groups assets into waves by complexity and dependencies. Wave 1 migrates the simplest, most independent assets. Later waves handle complex, interdependent ones. Use `--wave N` to run a specific wave.

---

## Expression Translation

### How are OAC expressions converted to DAX?
The hybrid translator (`src/core/hybrid_translator.py`) applies deterministic rules first (120+ mappings in `translation_catalog.py`). If no rule matches, it falls back to Azure OpenAI GPT-4 with syntax validation. Translations with confidence < 0.7 are flagged for manual review.

### What OAC functions are supported?
See the [Mapping Reference](MAPPING_REFERENCE.md#3-oac-expression--dax-translation-rules) for the complete list of 120+ supported functions across aggregates, time intelligence, strings, math, dates, logical, filters, and statistics.

### What about Oracle SQL → Fabric SQL?
See [Mapping Reference §2](MAPPING_REFERENCE.md#2-oracle-sql--fabric-sql-function-mappings) — 20+ function rewrites covering NVL, DECODE, SYSDATE, TO_CHAR, SUBSTR, etc., with separate mappings for Spark SQL (Lakehouse) and T-SQL (Warehouse).

### Are LOD expressions / Table calculations supported?
Not yet. These require manual review. See [Known Limitations](KNOWN_LIMITATIONS.md).

---

## Reports & Visuals

### What OAC visual types are supported?
80+ visual types including Table, Pivot Table, Bar, Line, Area, Combo, Pie, Donut, Scatter, Map, Gauge, KPI, Funnel, Treemap, Waterfall, Sankey, Chord, Word Cloud, Gantt, and more (including AppSource custom visuals). See [Mapping Reference §5](MAPPING_REFERENCE.md#5-oac-visual--power-bi-visual-type-mappings).

### What about OAC prompts?
9 prompt types are mapped to Power BI slicers: dropdown, multi-select, search, slider, date picker, radio, checkbox, text input, and cascading prompts.

### Are conditional formats preserved?
Yes — color rules, data bars, icon sets, and number formats are translated. See [Mapping Reference §5D](MAPPING_REFERENCE.md#5d-formatting-translation).

---

## Security

### How is Row-Level Security migrated?
OAC session variable filters are converted to DAX RLS expressions. `VALUEOF(NQ_SESSION.USER)` becomes `USERPRINCIPALNAME()`. Group-based and region-based filters use lookup tables. See [Mapping Reference §6](MAPPING_REFERENCE.md#6-security-model-mappings).

### How is Object-Level Security migrated?
OAC column/table hide permissions become PBI OLS `none` permissions. Measure-level OLS is not natively supported in Power BI — use perspectives as a workaround.

### Are workspace roles migrated?
Yes. OAC application roles are mapped to Fabric workspace roles (Admin, Contributor, Member, Viewer).

---

## Testing & Validation

### How many tests are there?
3,760 tests across 140+ files, running in ~40 seconds. All tests work offline with mocked APIs.

### How is migration correctness validated?
The Validation Agent (07) performs:
- **Data reconciliation**: Row counts, checksums, sample query comparisons
- **Semantic model validation**: Measure definitions, relationships, hierarchies
- **Report validation**: Visual types, data bindings, layout fidelity
- **Security validation**: RLS role testing, OLS permission verification
- **Visual comparison**: Screenshot diff using Playwright + GPT-4o (or SSIM fallback)
- **DAX deep validation**: 14 syntax checks (DAX001–DAX014) via `src/tools/dax_validator.py`
- **TMDL structure validation**: File-system checks via `src/tools/tmdl_file_validator.py`

### How do I run tests?
```bash
python -m pytest tests/ -v                    # All tests
python -m pytest tests/test_expression_translator.py -v  # Specific file
python -m pytest tests/ --cov=src --cov-report=html      # With coverage
```

---

## Architecture & Design

### Why 8 agents instead of one monolithic tool?
Each agent specializes in one migration domain (schema, ETL, semantic model, etc.). This enables parallel execution, independent testing, and clear ownership. The DAG-based orchestrator manages dependencies between agents.

### Why Fabric Lakehouse for coordination?
All coordination data stays inside Microsoft Fabric — no extra Azure service to provision. Delta tables provide ACID transactions, time travel, and efficient reads/writes.

### Can I extend the framework?
Yes. See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Adding new agents (extend `MigrationAgent`)
- Adding new connectors (extend `SourceConnector`)
- Adding translation rules (`translation_catalog.py`)
- Building plugins (`src/plugins/`)

---

## v8.0 Intelligence & Tooling

### What is the Agent Intelligence Framework?
Phase 70 adds an LLM reasoning loop (ReAct pattern) that wraps around each agent's existing rule engine. Rules fire first (fast, deterministic). The LLM handles planning, error diagnosis, and novel patterns that no rule covers. Agent memory persists decisions across migrations.

### What are the practical migration tools?
Five validation tools in `src/tools/` that catch real migration bugs:
- **DAX Deep Validator** — 14 syntax checks (parentheses, brackets, VAR/RETURN, anti-patterns)
- **TMDL File Validator** — validates output directory structure (model.tmdl, .platform, tables/)
- **Reconciliation CLI** — source vs target data comparison with tolerance support
- **OAC Test Harness** — VCR-style cassette recording/playback for API testing
- **Fabric Dry-Run** — validates naming rules, deployment order, and cross-dependencies

### Do I need Azure OpenAI for the intelligence layer?
No. The intelligence layer is opt-in. All agents work without LLM (backward-compatible). Rules handle 90%+ of patterns. Enable via `intelligence_enabled = true` in `config/migration.toml`.

### What bugs did the tools catch?
The DAX validator immediately discovered that the Essbase semantic bridge generates nested bracket column references (`'Fact'[Column]]`). This is a real bug tracked for fix — proving the value of syntax validation before deployment.

---

## Troubleshooting

### Common errors

| Error | Solution |
|-------|---------|
| `401 Unauthorized` | Check Key Vault secrets. Ensure admin consent granted for Azure AD app. |
| `403 Forbidden` | Verify service principal has workspace Contributor role. |
| `429 Too Many Requests` | Built-in retry handles this. If persistent, reduce parallelism in config. |
| `Tests fail with import error` | Run `pip install -e ".[dev]"` to install all dependencies. |

### Where are logs?
- Agent logs: `agent_logs` Delta table in Fabric Lakehouse
- CLI logs: stdout (use `--verbose` for debug level)
- API logs: Application Insights (if configured)
- Dashboard: Real-time log streaming via WebSocket/SSE

---

## Related Docs

| Document | Description |
|----------|-------------|
| [Architecture](ARCHITECTURE.md) | System architecture and data flow |
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | Step-by-step deployment instructions |
| [Mapping Reference](MAPPING_REFERENCE.md) | All translation rules in one place |
| [Known Limitations](KNOWN_LIMITATIONS.md) | Current gaps and workarounds |
| [Gap Analysis](GAP_ANALYSIS.md) | Implementation coverage assessment |
| [Migration Playbook](../MIGRATION_PLAYBOOK.md) | Production migration guide |
