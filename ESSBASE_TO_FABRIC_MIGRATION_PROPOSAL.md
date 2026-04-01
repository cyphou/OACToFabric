# Essbase to Fabric Migration Proposal

**Status**: Proposal v1.1 — Core infrastructure validated  
**Date**: April 1, 2026  
**Target Release**: v7.0 (Phase 63+)  
**Type**: Multi-source connector extension  
**Validation**: 3 cubes migrated end-to-end (186 tests, 36 TMDL files, 66 DAX measures)

---

## Executive Summary

Oracle Essbase cubes are multidimensional OLAP systems that serve planning, analytics, and consolidation workloads. This proposal outlines a **7-phase migration framework** to convert Essbase cubes to **Microsoft Fabric** (semantic models + data warehouses) with full fidelity, leveraging the existing 8-agent OAC migration architecture.

### Key Capabilities

| Task | Approach | Status |
|------|----------|--------|
| **Outline Parsing** | XML/REST API parser + hierarchy extraction | ✅ Validated (`essbase_connector.py`, 133 tests) |
| **Calc Script Translation** | Essbase calc → DAX measures (55+ rules) | ✅ Validated (`EssbaseCalcTranslator`) |
| **MDX to DAX** | MDX Query Translation → DAX queries | ✅ Validated (`EssbaseMdxTranslator`) |
| **Semantic Bridge** | Outline → TMDL conversion | ✅ Validated (`essbase_semantic_bridge.py`, 53 tests) |
| **Security Migration** | Essbase filters → RLS/OLS roles | ✅ Validated (4 RLS roles across 3 cubes) |
| **Smart View → Excel** | CUBE formula recipes, write-back | ✅ Complete (`SMART_VIEW_TO_EXCEL_MIGRATION.md`, 780+ lines) |
| **E2E Migration Example** | 3 cubes → TMDL + DDL + report | ✅ Validated (`examples/essbase_migration_example.py`) |
| **Data Loading** | Cube export → Fabric Lakehouse staging | 🔄 Proposed |
| **Period-over-Period** | Time dimension auto-hierarchies | 🔄 Proposed |
| **Forecasting Bridge** | Essbase Planning → Fabric scenarios | 🔄 Proposed |

---

## 1. Migration Architecture

### 1.1 High-Level Data Flow

```
Essbase Server (Outline + Calc Scripts + Data)
    │
    ├─► Discovery Agent (01) ──────► inventory_essbase Delta table
    │       • Outline XML/REST API
    │       • Calc scripts, filters, substitution vars
    │       • Outline statistics & complexity
    │
    ├─► Data Extract Pipeline (02b) ──► Lakehouse staging area
    │       • MaxL/MDX tools export
    │       • Hierarchies + Members + Data
    │       • Compression & deduplication
    │
    ├─► Transform & Denormalize (03b) ──► Normalized tables
    │       • Dynamic calc members → fact table
    │       • Stored vs. dynamic hierarchy prep
    │       • Sparse/dense dimension optimization
    │
    ├─► Semantic Model (04) ──────► TMDL semantic model
    │       • Outline dimensions → dimension tables
    │       • Measures from accounts dimension
    │       • Dynamic calc members → DAX measures
    │
    ├─► Security (06) ──────► RLS/OLS roles
    │       • Essbase filters → RLS
    │       • User provisioning → AAD
    │
    └─► Validation (07) ──────► Reconciliation report
            • Member count reconciliation
            • Measure value validation (cube vs. semantic model)
            • Security verification
            • Performance benchmarking
```

### 1.2 Agent Responsibilities

| Agent | Essbase Task | Deliverables |
|-------|-------------|---|
| **Discovery (01)** Extended | Crawl Essbase server via REST API; parse outline XML; inventory cubes, dimensions, hierarchies, calc scripts | `essbase_inventory` table, `essbase_complexity_scores` |
| **Schema (02) Extended** | Create Lakehouse tables for each cube (fact + dimension tables); plan data partition strategy | Delta table schemas, data copy directives |
| **ETL (03) Extended** | Data extract (XML reports, MaxL scripts), hierarchy loading, dynamic calc evaluation | Notebooks, pipelines for periodic refresh |
| **Semantic Model (04)** | Outline → TMDL; calc scripts → DAX measures; hierarchy generation | TMDL + DAX, what-if parameters |
| **Report (05)** | Map Essbase analyses/dashboards → Power BI reports (if OAC Analysis layer exists) | PBIR reports |
| **Security (06)** | Filters → RLS; role mapping; Essbase user provisioning | RLS definitions, AAD groups |
| **Validation (07)** | Data reconciliation, measure reconciliation, security validation | Validation report + test report |
| **Orchestrator (08)** | Wave planning, parallel extraction, dependency resolution | Migration runbook, monitoring |

---

## 2. Phase Roadmap (v7.0 — Phases 63–69)

### Phase 63: Essbase Discovery & Inventory Agent (1 week)

**Objective**: Build full Essbase environment crawler.

**Deliverables**:
- `EssbaseDiscoveryAgent` class (extends `MigrationAgent`)
- REST API client for Essbase 21.3+
- Outline XML parser (hierarchies, storage types, UDAs)
- Cube complexity scoring (dimension count, member cardinality, calc complexity)
- Essbase server metadata extraction (`admin.properties`, version, deployment mode)
- Integration tests (5+)

**Inputs**:
- Essbase server URL + credentials (service account)
- Application/database filter scope

**Outputs**:
- `essbase_inventory` Delta table (app, db, cube, dimensions, members, calc scripts)
- `essbase_outline_metadata` Delta table (storage types, aliases, UDAs, hierarchies)
- Migration readiness report (complexity bands: Low/Medium/High/Expert)

**Constraints**:
- Do NOT modify Essbase data or metadata
- Do NOT evaluate calc scripts (rules engine only; LLM for edge cases)
- Support Essbase 21.3+ (legacy 11g via XML export fallback)

---

### Phase 64: Essbase Data Extract & Staging (1.5 weeks)

**Objective**: Extract Essbase cube data into Fabric staging layers.

**Deliverables**:
- `EssbaseDataExtractor` (MaxL / MDX script generator)
- Cube export strategies (XML reports, MDX queries, native export format)
- Sparse/dense dimension detection & optimization
- Hierarchical member export (level-0 focus + roll-up strategy)
- Partition-friendly staging (by time period, by product line, etc.)
- Integration tests (8+)

**Inputs**:
- Outline metadata (from Phase 63)
- Cube data access (service account)
- Partition strategy (time-based, product-based, etc.)

**Outputs**:
- Lakehouse staging area: `essbase_raw_<app>_<db>_<cube>_<date>`
- Extracted hierarchies: member names, parent links, levels, aliases
- Data reconciliation summary (row counts, value ranges, NULL patterns)

**Constraints**:
- Minimize cube query load during extraction (off-peak windows)
- Handle sparse dimensions efficiently (only non-zero cells)
- Support incremental extraction (change detection by member/time)

---

### Phase 65: Schema & Normalization Agent (1.5 weeks)

**Objective**: Design and create Fabric warehouse schema from Essbase outline.

**Deliverables**:
- `EssbaseSchemaDesigner` (Star schema generator)
- Dimension table DDL (one per sparse dimension + accounts dimension)
- Fact table DDL (dense dimensions + measures)
- Slowly Changing Dimension (SCD) handling (Type 1 for hierarchies)
- Fabric naming convention enforcement (`essbase_<cube>_<dim>`, `essbase_<cube>_fact`)
- Hybrid storage mode advisor (Import vs. DirectQuery vs. Composite)
- DDL script generation + CI/CD integration
- Integration tests (5+)

**Inputs**:
- Outline metadata + staging data (from Phase 64)
- Partition strategy (time, region, etc.)
- Scale expectations (row count, refresh cadence)

**Outputs**:
- Lakehouse schemas: dimension + fact tables (Delta format)
- Metadata table: `essbase_dim_mappings` (dimension → table mapping)
- Storage mode recommendation report

**Constraints**:
- Ensure dimension tables < 2 GB per partition (Fabric limit)
- Support many-to-many scenarios via bridge tables (if hierarchies have multiple parents)
- Preserve member aliases in dimension tables

---

### Phase 66: ETL & Transformation Pipeline (2 weeks)

**Objective**: Build data pipelines for incremental cube refresh.

**Deliverables**:
- `EssbaseETLOrchestrator` (notebook + pipeline generator)
- Hierarchy loading strategy (insert dimension members, handle reparenting)
- Fact table aggregation (level-0 detail + roll-ups)
- Dynamic calc member evaluation (as DAX measures, not stored)
- Incremental detection (changed members, deleted members, new time periods)
- Refresh scheduling (daily/weekly, aligned to Essbase load cycles)
- Error handling & retry logic (truncate on full refresh, upsert on incremental)
- Integration tests (6+)

**Inputs**:
- Staging data (from Phase 64)
- Schema (from Phase 65)
- Calc script translations (from Phase 67)

**Outputs**:
- Fabric notebooks (PySpark) for dimension + fact loading
- Fabric pipelines for orchestration
- Incremental checkpoint tables

**Constraints**:
- Preserve Essbase audit trail (load date, source member)
- Support both snapshot (full refresh) and delta (incremental) modes
- Handle member reparenting / hierarchy changes gracefully

---

### Phase 67: Semantic Model & DAX Translation (2 weeks)

**Objective**: Convert Essbase outline + calc scripts to TMDL semantic model.

**Deliverables**:
- `EssbaseSemanticModelAgent` (extends Agent 04 pattern)
- TMDL generator for Essbase cubes
- Calc script → DAX measure translation (extend existing 80+ rules)
- Hierarchy generation from Essbase generations
- Accounts dimension → measures + calculated columns
- Time dimension → date table + auto hierarchies
- What-if parameters from substitution variables
- DAX optimizer (IF→SWITCH, aggregation patterns, etc.)
- Confidence scoring for translations
- Integration tests (10+)

**Inputs**:
- Outline metadata (from Phase 63)
- Calc script translations (rules engine + LLM fallback)
- Normalized warehouse schema (from Phase 65)

**Outputs**:
- TMDL semantic model (tables, relationships, measures, hierarchies)
- DAX measure definitions
- Translation confidence report (% auto-translated, % review items)
- RLS role skeletons (for Phase 68)

**Constraints**:
- Preserve Essbase naming (dimension names → table names, member names → hierarchy levels)
- Support both stored and dynamic calc members
- Generate DAX measures that produce equivalent results to Essbase calc scripts

---

### Phase 68: Security & Governance Migration (1.5 weeks)

**Objective**: Migrate Essbase security model to Fabric/Power BI.

**Deliverables**:
- `EssbaseSecurityAgent` (extends Agent 06 pattern)
- Essbase filter → RLS DAX filter converter
- User provisioning to Azure AD
- Application role → Fabric role + RLS role mapping
- Dimension security → Column-Level Security (CLS, via OLS)
- Cell-level access → row-level security DAX
- Essbase `maxl` privilege mapping → Fabric permission matrix
- Security test suite
- Integration tests (5+)

**Inputs**:
- Outline filters + security definitions (from Phase 63)
- TMDL semantic model (from Phase 67)
- User directory connector (LDAP, Azure AD, CSV)

**Outputs**:
- RLS role definitions (DAX filters)
- OLS definitions (column security)
- AAD group memberships
- Security validation report

**Constraints**:
- Essbase "read", "write", "none" → RLS filter logic translation
- Support dense dimension cell security (via calculated columns + RLS)
- Audit trail for security policy changes

---

### Phase 69: Validation & User Acceptance Testing (1.5 weeks)

**Objective**: Validate Essbase→Fabric fidelity across all layers.

**Deliverables**:
- `EssbaseValidationAgent` (extends Agent 07 pattern)
- Cube data reconciliation (member count, value totals, roll-up logic)
- Measure validation (compare Essbase results vs. Power BI DAX results)
- Hierarchy validation (parent-child relationships, level counts)
- Dynamic calc accuracy testing
- RLS security validation (same user, different cell access)
- Performance benchmarking (query latency, throughput)
- Visual comparison (Essbase Analysis vs. Power BI report)
- Defect reclassification:
  - **Green**: Equivalent results (< 1% variance)
  - **Yellow**: Acceptable variance (1-5%) due to rounding
  - **Red**: Significant gap (> 5%) — requires review/remediation
- UAT sign-off workflow
- Integration tests (8+)

**Inputs**:
- Source: Essbase cubes + calc scripts
- Target: Fabric warehouse + semantic model + reports
- Test queries (predefined + custom)

**Outputs**:
- Reconciliation report (member count, value totals)
- Measure variance report (tolerance thresholds)
- Security verification report
- Performance report (latency SLA: < 5s for 1M rows)
- Visual diff screenshots (Analysis vs. Power BI)
- UAT sign-off checklist

**Constraints**:
- Test on production-representative data volumes
- Cover all dynamic calc formulas
- Validate all RLS scenarios (minimum 10 roles × 5 queries)

---

## 3. Data Model Mapping

### 3.1 Essbase Outline → TMDL Mapping

| Essbase | TMDL | Cardinality |
|---------|------|---|
| **Dimension** (regular) | `LogicalTable` (dimension table, one row per member) | sparse→fact FK; dense→columns |
| **Dimension** (time) | `LogicalTable` + `is_date_table=True` + hierarchy | linked to fact |
| **Dimension** (accounts) | Measures + Calculated columns | embedded in fact |
| **Generation** | `Hierarchy` + `HierarchyLevel` per generation | multi-level |
| **Member (L0)** | Dimension table row | parent FK |
| **Member (parent/aggregate)** | Hierarchy level | generated from parent relationships |
| **Dynamic Calc Member** | `Measure` (DAX formula) | calculated, not stored |
| **Stored Member** | Fact table row + dimension member reference | denormalized |
| **Calc Script** | `Measure` (DAX equivalent) | one per rule |
| **Filter** | `Role` with RLS DAX filter | per dimension |

### 3.2 Essbase Calc → DAX Translation Rules (Sample)

| Essbase Function | DAX Equivalent | Difficulty |
|---|---|---|
| `SUM(D1)` | `SUM([Measure])` | direct |
| `A:H` (ancestors-to-here) | `SUMMARIZE` with ANCESTORS nav | complex |
| `CURRENTMEMBER` | Context member from filter context | direct |
| `CHILDREN(@CURR,,1)` | `CALCULATE` with DAX DESCENDANTS | complex |
| `IF` condition | `IF` or `SWITCH` | direct |
| `XREF(...,...)` | `LOOKUPVALUE` + foreign cube join | expert |
| `@CURRMBR` | Active member context | direct |
| `FIX / ENDFIX` | Implicit filter context | parametric |

---

## 4. Integration with Existing Architecture

### 4.1 CLI Enhancement

```bash
# Essbase-specific discovery
oac-to-fabric discover --source essbase \
    --essbase-server https://essbase.example.com:21000 \
    --essbase-app MyApp \
    --essbase-db MyDb

# Full migration
oac-to-fabric migrate --source essbase \
    --essbase-app MyApp \
    --essbase-db MyDb \
    --config migration.toml \
    --wave high-complexity-cubes \
    --mode incremental
```

### 4.2 Coordination Store Extension

New Delta tables for Essbase tracking:

| Table | Purpose |
|-------|---------|
| `essbase_inventory` | Cubes, dimensions, hierarchies, members |
| `essbase_metadata` | Outline properties, storage types, aliases |
| `essbase_calc_scripts` | Script content + translation results |
| `essbase_filters` | Security filter definitions |
| `essbase_extraction_log` | Data extract timestamps, row counts |
| `essbase_validation_results` | Reconciliation results per cube |

### 4.3 Testing Framework

Extend existing test suite:

- **Unit tests** (40+): Outline parser, calc translator, schema designer, security converter
- **Integration tests** (20+): Essbase server → Lakehouse → TMDL → Power BI
- **E2E tests** (5+): Real Essbase instance (if available) or mock server
- **Performance tests** (3+): Data extraction, calculation evaluation, query latency

---

## 5. Implementation Roadmap

### Phase 63 (Week 1)
- [ ] Discovery agent implementation
- [ ] Essbase REST API client
- [ ] Outline XML parser completion
- [ ] Inventory Delta table schema
- [ ] Unit tests (5+)

### Phase 64 (Weeks 2–3)
- [ ] Data extraction utilities (MaxL, MDX, XML export)
- [ ] Hierarchy flattening logic
- [ ] Incremental detection
- [ ] Integration tests (8+)

### Phase 65 (Weeks 4–5)
- [ ] Schema designer (fact + dimension DDL)
- [ ] Naming convention enforcement
- [ ] Storage mode advisor
- [ ] Integration tests (5+)

### Phase 66 (Weeks 6–9)
- [ ] ETL notebooks (dimension loading, fact aggregation)
- [ ] Refresh pipeline
- [ ] Incremental merge logic
- [ ] Error recovery
- [ ] Integration tests (6+)

### Phase 67 (Weeks 10–13)
- [ ] Calc translator (extend to 100+ rules)
- [ ] TMDL generator
- [ ] DAX optimizer
- [ ] What-if parameter generation
- [ ] Integration tests (10+)

### Phase 68 (Weeks 14–15)
- [ ] Security converter (filters → RLS/OLS)
- [ ] User provisioning
- [ ] Security test suite
- [ ] Integration tests (5+)

### Phase 69 (Weeks 16–17)
- [ ] Validation agent
- [ ] Reconciliation queries
- [ ] Performance benchmarking
- [ ] UAT workflow
- [ ] Integration tests (8+)

**Total Duration**: 17 weeks (~4 months)  
**Target Release**: v7.0.0  

---

## 6. Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Calc complexity** (expert-level formulas) | High | LLM-assisted translation + manual review queue |
| **Data volume** (100M+ cells) | High | Partition strategy + incremental extraction + compression |
| **Essbase version variance** (11g → 21.3) | Medium | Version detection + fallback parsers (XML export) |
| **User skill transfer** | Medium | Documentation + training + migration playbook |
| **Legacy Essbase knowledge loss** | Low | Automated translation confidence tracking + comments |

---

## 7. Success Criteria

| Metric | Target | Validation |
|--------|--------|-----------|
| **Object coverage** | > 95% of cubes discoverable | Inventory completeness check |
| **Data accuracy** | > 99% measure value parity | Reconciliation report (< 0.1% variance) |
| **Performance** | Query latency < 5s (1M rows) | Load test with real data |
| **Security** | 100% RLS role mapping | Security audit + manual verification |
| **Automation** | > 85% calc script auto-translation | LLM confidence score reporting |
| **Test coverage** | > 90% | pytest coverage report |
| **Documentation** | Full playbook + videos + examples | Documentation audit |

---

## 8. Dependencies & Assumptions

### Dependencies
- Essbase 21.3+ with REST API enabled
- Fabric Lakehouse + SQL Endpoint provisioned
- Power BI Premium capacity (for TMDL deployment)
- Azure AD for user provisioning

### Assumptions
- Essbase outlines are well-maintained (< 5% orphaned members)
- Calc scripts follow standard patterns (80/20 rule)
- User community available for UAT (~5 power users)
- Source data extraction window available (4-6 hours)

---

## 9. Deliverables Summary

### Code Deliverables
- 1 new agent: `EssbaseDiscoveryAgent` (Phase 63)
- 5 new service classes:
  - `EssbaseDataExtractor` (Phase 64)
  - `EssbaseSchemaDesigner` (Phase 65)
  - `EssbaseETLOrchestrator` (Phase 66)
  - `EssbaseSemanticModelAgent` (Phase 67)
  - `EssbaseValidationAgent` (Phase 69)
- 200+ lines of additional Essbase-specific utilities
- 40+ unit tests + 42+ integration tests

### Documentation Deliverables
- `ESSBASE_MIGRATION_PLAYBOOK.md` (step-by-step customer guide)
- `ESSBASE_CALC_TRANSLATOR_REFERENCE.md` (100+ conversion rules + examples)
- `ESSBASE_TROUBLESHOOTING.md` (common issues + solutions)
- `ESSBASE_TO_FABRIC_ARCHITECTURE.md` (technical deep dive)
- 4 video tutorials (discovery, data extract, semantic model, validation)

### Operational Deliverables
- Migration dashboard (real-time progress tracking)
- Runbooks for:
  - Essbase server connectivity troubleshooting
  - Data extraction in production
  - Incremental refresh scheduling
  - Rollback procedures
- SLA templates (uptime, data freshness, query performance)

---

## 10. Next Steps

1. **Week 1**: Socialize proposal with stakeholders (Essbase SMEs, Fabric platform team, customer success)
2. **Week 2**: Finalize Phase 63 requirements (API contracts, test fixtures)
3. **Week 3**: Kick off Phase 63 development
4. **Post-v7.0**: Consider Phase 70 (Essbase Planning bridge for scenario management)

---

## Appendix: Quick-Start Example

```python
# Quick-start: Essbase outline → TMDL in 3 steps

from src.connectors.essbase_connector import EssbaseOutlineParser, EssbaseCalcTranslator
from src.connectors.essbase_semantic_bridge import EssbaseToSemanticModelConverter
from src.agents.semantic.tmdl_generator import TmdlGenerator

# Step 1: Parse Essbase outline
parser = EssbaseOutlineParser()
outline = parser.parse_xml(open("planning_app.xml").read())

# Step 2: Convert to semantic model IR
converter = EssbaseToSemanticModelConverter()
result = converter.convert(outline, model_name="PlanningModel")

# Step 3: Generate TMDL
generator = TmdlGenerator()
tmdl = generator.generate(result.ir)

# Output: TMDL ready for Power BI Desktop
print(tmdl.to_yaml())
```

---

## Glossary

| Term | Definition |
|------|-----------|
| **Outline** | Essbase dimension + hierarchy metadata |
| **Member** | A node in an Essbase dimension (leaf level-0 or parent) |
| **Generation** | Parent-child relationship level (Gen 1 = parents of L0) |
| **Level** | Depth in a hierarchy (L0 = leaf, L1+ = parents) |
| **Dynamic Calc** | Member calculated on-the-fly (not stored) |
| **Stored Member** | Member data persisted in cube |
| **Sparse Dimension** | Few combinations present (high cardinality) |
| **Dense Dimension** | Most combinations present (low cardinality) |
| **Consolidation Operator** | Function for aggregation (+, -, *, /, ~, ^) |
| **UDA** | User-Defined Attribute (metadata label on members) |
| **Filter** | Essbase security rule (row-level access) |
