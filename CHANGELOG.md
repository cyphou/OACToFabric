# Changelog

All notable changes to the OAC-to-Fabric Migration Tool are documented here.

## [8.0.0-alpha.4] — Intelligence Wired into Agent Lifecycle

**Phase 71-76 modules wired into live agents.** Intelligence is now invoked during actual migration runs — not just standalone. 25 new integration tests (3,897 total). All wiring is backward-compatible: agents work without LLM/intelligence (features are optional enrichments).

### Changed — Discovery Agent (Phase 71 wiring)
- `src/agents/discovery/discovery_agent.py` — AI assessment step after complexity scoring. `AIAssessor.assess()` enriches inventory with risk heatmap, anomalies, and strategy recommendations. Assessment exposed via `.assessment` property. Summary report appends AI narrative section via `AssessmentNarrator`.

### Changed — Expression Translator (Phase 72 wiring)
- `src/agents/semantic/expression_translator.py` — New `translate_with_intelligence()` async function: routes low-confidence rule-based translations to `IntelligentTranslator` cascade (cache → LLM → alternate → escalate). Falls back gracefully to rule-only when no translator is available.

### Changed — Orchestrator Agent (Phase 73-76 wiring)
- `src/agents/orchestrator/orchestrator_agent.py` — Accepts `MessageBus`, `HealingEngine`, `EscalationQueue`, `AIWavePlanner` via constructor. Discovery-complete handoff broadcast. AI wave plan generation (advisory, written to `ai_wave_plan.md`). Self-healing attempt before retry in `_execute_agent_with_retry()`. Escalation on max retries exhausted.

### Changed — Base Agent (Phase 73-74 wiring)
- `src/core/base_agent.py` — New helpers: `attach_bus()`, `attach_healing()`, `send_handoff()`, `receive_handoffs()`, `_try_heal()`. All no-op when intelligence not attached.

### Added — Integration Tests
- `tests/test_intelligence_wiring.py` — 25 tests covering: Discovery assessment wiring (3), expression translator intelligent fallback (4), base agent handoff (4), base agent healing (4), orchestrator intelligence (7), end-to-end pipeline (3).

## [8.0.0-alpha.3] — Phases 71–76: Multi-Agent Intelligence

**12 new intelligence modules** across Phases 71–76 — autonomous discovery & assessment, intelligent translation, inter-agent communication, self-healing pipeline, human-in-the-loop escalation, and intelligent orchestration. 112 new tests (3,872 total). Essbase DAX bracket bug fixed. 4 CLI tool commands wired. CI validation job added.

### Added — Phase 71: Autonomous Discovery & Assessment
- `src/agents/discovery/ai_assessor.py` — AI-powered migration complexity assessor: anomaly detection (orphaned tables, circular dependencies, excessive roles, wide fact tables, large models), risk scoring (0–1 with factors), risk heatmap, strategy grouping (lift-and-shift / refactor / rebuild / defer)
- `src/agents/discovery/strategy_recommender.py` — Domain classification (finance, sales, HR, supply chain, marketing), wave assignment, effort estimation, strategy plan generation
- `src/agents/discovery/assessment_narrator.py` — Markdown report generation from assessment data: executive summary, risk overview, anomaly table, strategy recommendations

### Added — Phase 72: Autonomous Translation
- `src/core/intelligence/translation_agent.py` — 5-strategy cascade translator (rules → cache → LLM primary → LLM alternate → escalate), syntax validators (DAX, T-SQL, PySpark, M-query), translation memory cache with token-overlap similarity matching
- `src/core/intelligence/rule_distiller.py` — Pattern extraction from successful LLM translations, function-call recognition, output template generation with placeholders

### Added — Phase 73: Agent Communication Protocol
- `src/core/intelligence/handoff_protocol.py` — Typed inter-agent messaging (ARTIFACT_READY, DEPENDENCY_REQUEST, CONFLICT, CONTEXT_SHARE, ESCALATION), priority-sorted MessageBus, ConflictResolver (storage mode, naming, relationship direction), ContextWindow (token-aware context aggregation)

### Added — Phase 74: Self-Healing Pipeline
- `src/core/intelligence/error_diagnostician.py` — 15 error categories with regex pattern matching, auto-repair flagging, known-error caching
- `src/core/intelligence/repair_strategies.py` — 6 pluggable repair strategies (Retranslate, AdjustTypeMapping, RetryWithBackoff, Quarantine, SkipAndContinue, FixSyntax)
- `src/core/intelligence/healing_engine.py` — HealingEngine (diagnosis → strategy → repair → persist), RegressionGuard (baseline comparison)

### Added — Phase 75: Human-in-the-Loop Escalation
- `src/core/intelligence/escalation.py` — EscalationQueue (priority-sorted with severity filtering), ReviewItem (context + suggested actions), FeedbackCollector (human decisions → training data + cache)

### Added — Phase 76: Intelligent Orchestration
- `src/core/intelligence/orchestration.py` — AIWavePlanner (topological sort + risk-based grouping), ResourceOptimizer (Fabric SKU sizing F2–F128), CostModeler (compute + storage + LLM cost estimation), AdaptiveScheduler (runtime adjustments)

### Fixed
- Essbase DAX bracket bug: `_accounts_to_measures()` now uses correct fact table name (`Fact_{model_name}`) and escapes `]` in column names via `_dax_column_ref()` helper

### Added — CLI & CI
- 4 new CLI subcommands: `validate-dax`, `validate-tmdl`, `reconcile`, `dry-run` — wire `src/tools/` into `src/cli/main.py`
- CI `validate` job in `.github/workflows/ci.yml` — DAX sample validation, TMDL import check, CLI help verification

### Tests
- `tests/test_phase71_76_intelligence.py` — 112 new tests across 22 test classes covering all Phases 71–76
- **Total: 3,872 tests passing**

## [8.0.0-alpha.2] — Practical Migration Tooling

**5 new migration tools** — DAX deep validator, TMDL file-system validator, data reconciliation CLI, OAC API test harness, Fabric deployment dry-run. 101 new tests (3,760 total).

### Added — Practical Tooling (`src/tools/`)
- `src/tools/dax_validator.py` — Deep DAX syntax validator with tokenizer, recursive structural checks (14 error codes: DAX001–DAX014), iterator anti-pattern detection, VAR/RETURN pairing, argument count validation, batch TMDL measure validation
- `src/tools/tmdl_file_validator.py` — File-system based TMDL output validator: structure checks, .platform JSON validation, table/column/measure counting, relationship cross-reference, integrated DAX validation, migration output batch validation
- `src/tools/reconciliation_cli.py` — Data reconciliation toolkit: `OfflineReconciler` (JSON snapshot comparison), `ReconciliationRunner` (live DB query execution), value comparison with tolerance, Markdown and JSON report generation
- `src/tools/oac_test_harness.py` — VCR-style OAC API test harness: `RequestRecorder` (cassette recording), `PlaybackEngine` (cassette replay with URL matching), `MockOACServer` (synthetic API responses), `OACTestHarness` (lifecycle management), pagination/rate-limit cassette generators, assertion helpers
- `src/tools/fabric_dry_run.py` — Fabric deployment dry-run validator: artifact scanning, Fabric naming rule validation, deployment order computation, cross-dependency checking, capacity estimation, JSON manifest export

### Bug Discovered
- Essbase DAX generator produces nested bracket column references (`'Fact'[Column]` instead of `[Column]`), caught by new DAX validator (DAX002). Tracked for fix in Essbase semantic bridge.

### Tests
- `tests/test_tools.py` — 101 new tests across 16 test classes covering all 5 tools + real Essbase output integration test

## [8.0.0-alpha.1] — v8.0 Phase 70: Agent Intelligence Framework

**Multi-Agent Intelligence foundation** — 5 new intelligence modules, 90 new tests (3,659 total), LLM reasoning loop with ReAct pattern, agent memory, tool-use protocol, cost controls.

### Added — Phase 70: Agent Intelligence Framework
- `src/core/intelligence/reasoning_loop.py` — ReAct reasoning loop: task→prompt→LLM→plan→execute→validate; step-level retry with backoff
- `src/core/intelligence/agent_memory.py` — Per-agent persistent memory store; vector-indexed semantic retrieval; TTL-based eviction
- `src/core/intelligence/tool_registry.py` — Typed tool definitions; schema validation on tool calls; permission scoping per agent
- `src/core/intelligence/cost_controller.py` — Token budget per agent per wave; semantic cache; request batching; cost logging
- `src/core/intelligence/prompt_builder.py` — Domain-specific prompt templates; few-shot examples from translation catalog; context window management

### Enhanced — Phase 70
- `src/core/base_agent.py` — `IntelligentMixin` with optional `reasoning_loop` injection (backward-compatible)
- `src/core/llm_client.py` — `complete_json()` structured output, `complete_with_tools()` tool-use protocol, token counting
- `src/core/config.py` — 9 new `intelligence_*` settings (model, temperature, token budgets, cache TTL)

### Added — Essbase End-to-End Migration Validation
- `examples/essbase_migration_example.py` — Full Essbase migration pipeline (3 cubes → 36 TMDL files, 66 DAX measures, 15 DDL tables)
- `output/essbase_migration/` — Generated artifacts: TMDL semantic models, DDL scripts, migration report
- `SMART_VIEW_TO_EXCEL_MIGRATION.md` — Section 11: Essbase-specific CUBE formula recipes for all 3 sample cubes (780+ lines total)
- `ESSBASE_MIGRATION_PLAYBOOK.md` — 9-step executable Essbase migration guide (728 lines)
- `ESSBASE_TO_FABRIC_MIGRATION_PROPOSAL.md` — 7-phase architecture proposal (Phases 63–69)

### Testing — Phase 70 + Essbase
**90 new intelligence tests** + 186 Essbase connector/bridge tests validated. **3,659 total tests, 0 failures.**

---

## [6.0.0] — v6.0.0 Full Coverage Upgrade (Phases 54–62)

**97% OAC object coverage** — 20 new source modules, 20 new test files, 285 new tests (3,559 total), 7,246 lines of code.

### Added — Phase 54: Materialized Views & Oracle Mirroring
- `src/agents/schema/materialized_view_generator.py` — Oracle MV DDL parser, Fabric Warehouse MV generator, refresh mode mapping
- `src/agents/schema/mirroring_config_generator.py` — Fabric Mirroring configuration: Oracle connection, table selection, replication schedule

### Added — Phase 55: Calculation Groups & DAX UDFs
- `src/agents/semantic/calc_group_generator.py` — Detect time-intel clusters, generate TMDL `calculationGroup` blocks
- `src/agents/semantic/dax_udf_generator.py` — Complex expression → DAX UDF with `DEFINE FUNCTION`, parameter type hints

### Added — Phase 56: BI Publisher → Paginated Reports
- `src/agents/report/bip_parser.py` — BI Publisher XML data model parser, RTF template extractor
- `src/agents/report/rdl_generator.py` — RDL XML generator (Tablix, Matrix, Chart, List regions)
- `src/agents/report/bip_expression_mapper.py` — BI Publisher XSL/XPath expressions → RDL expressions

### Added — Phase 57: Data Activator & Alert Migration
- `src/agents/report/alert_migrator.py` — OAC Agent parser, Data Activator trigger generator, PBI data alert rules
- `src/agents/report/activator_config.py` — Data Activator Reflex item configuration (event streams, conditions, actions)

### Added — Phase 58: Translytical Task Flows & Action Links
- `src/agents/report/task_flow_generator.py` — OAC action classifier, Translytical task flow definition generator
- `src/agents/report/action_link_mapper.py` — OAC action → PBI action type mapping (drillthrough, bookmarks, URL)

### Added — Phase 59: ETL Gap Closure
- `src/agents/etl/pivot_unpivot_mapper.py` — Pivot/Unpivot → M query + PySpark, column detection, aggregation mapping
- `src/agents/etl/error_row_router.py` — Rejected row routing to dead-letter Delta table, error metadata enrichment

### Added — Phase 60: Incremental Discovery & Delta TMDL
- `src/agents/discovery/incremental_crawler.py` — Delta crawl with `modifiedSince`, inventory diffing (ADDED/MODIFIED/DELETED)
- `src/agents/semantic/tmdl_incremental.py` — TMDL folder parser, merge engine, manual-edit preservation

### Added — Phase 61: Direct Lake & Modern Themes
- `src/agents/semantic/direct_lake_generator.py` — Direct Lake TMDL emitter: OneLake mode, expression partitions
- `src/agents/report/visual_calc_mapper.py` — OAC custom aggregation → PBI visual calculations (COLLAPSE, EXPAND)

### Added — Phase 62: Advanced Security & Governance
- `src/agents/security/aad_group_provisioner.py` — Graph API: create security groups, add members, assign workspace roles
- `src/agents/security/audit_trail_migrator.py` — OAC audit log parser, Fabric-compatible audit event mapping
- `src/agents/security/dynamic_rls_generator.py` — Multi-valued session variable → complex DAX RLS

### Testing — Phases 54–62
**20 new test files, 285 tests** covering all new modules with comprehensive edge cases, error handling, and integration scenarios.

---

## [5.0.0-alpha] — v5.0.0-alpha (GraphQL API, Dry-Run Simulator & Regression Testing)

### Added — Phase 52: Automated Regression Testing

**New modules (1):**

- `src/core/regression_tester.py` — Automated post-migration regression testing:
  - **DataBaseline**: JSON-serializable row count & checksum baselines with `to_json()`/`from_json()` roundtrip
  - **VisualBaseline**: SHA-256 hash-based screenshot baselines with dimensions
  - **RegressionBaseline**: Combined data + schema + visual baseline capture
  - **Data regression**: Row count drift detection with configurable tolerance, new/missing table detection, checksum comparison
  - **Schema regression**: Integration with `schema_drift.compare_snapshots()` for column type changes, table additions/drops
  - **Visual regression**: Hash comparison + SSIM score support (pre-computed externally), threshold-based severity classification
  - **RegressionReport**: Markdown generation, `to_dict()` serialization, finding/critical/warning counters
  - **Notification integration**: Critical/warning alerts via NotificationManager pipeline
  - **RegressionSchedule**: Configurable frequency (HOURLY/DAILY/WEEKLY/ON_DEMAND), tolerance thresholds
  - **Convenience wrappers**: `capture_baseline()` and `run_regression()` module-level functions

### Testing — Phase 52

**1 new test file, 65 tests:**
- `tests/test_phase52_regression.py` — 65 tests across 14 test classes:
  - `TestDataBaseline` (4 tests) — creation, JSON roundtrip, empty checksums
  - `TestVisualBaseline` (2 tests) — fields, defaults
  - `TestRegressionBaseline` (2 tests) — creation, JSON serialization
  - `TestRegressionFinding` (1 test) — default values
  - `TestRegressionTestResult` (2 tests) — defaults, with findings
  - `TestRegressionReport` (4 tests) — counters, to_dict, markdown, empty report
  - `TestRegressionSchedule` (2 tests) — defaults, custom config
  - `TestRegressionTesterCapture` (5 tests) — data/visual/full baseline capture
  - `TestRunDataRegression` (11 tests) — no drift, tolerance, warning/critical drift, new/missing tables, checksums, zero rows
  - `TestRunSchemaRegression` (4 tests) — no drift, added table, dropped table, type change
  - `TestRunVisualRegression` (7 tests) — identical, hash mismatch, missing screenshot, SSIM pass/warning/critical
  - `TestRunFullRegression` (5 tests) — all pass, data-only, selective types, skip when no data, completed_at
  - `TestNotificationIntegration` (4 tests) — critical/warning sent, clean/no-manager
  - `TestConvenienceFunctions` (5 tests) — capture_baseline, run_regression with drift/thresholds
  - `TestEnumValues` (3 tests) — severity, type, frequency enums
  - `TestEdgeCases` (4 tests) — empty tables, 100 tables, multiple visuals, minimal JSON

**Test suite totals:** 3,274 passed (up from 3,209)

### Added — Phase 51: Migration Dry-Run Simulator

**New modules (1):**

- `src/core/dry_run_simulator.py` — Full migration dry-run simulation engine:
  - **SimulationMode**: QUICK (complexity only), STANDARD (+ translations), FULL (+ cost/timeline/risk)
  - **Per-asset simulation**: Translation coverage stats (translated/total/coverage %), risk scoring via complexity analyzer
  - **Cost estimation**: Fabric capacity cost via CostEstimator from migration-intelligence
  - **Timeline estimation**: Duration projections via TimelineEstimator
  - **Risk heatmap**: Asset-by-risk-level matrix with HIGH/MEDIUM/LOW classification
  - **Change manifests**: CREATE/MODIFY/DELETE/SKIP action records per asset
  - **SimulationReport**: Aggregated results with overall risk score, markdown/JSON output

### Testing — Phase 51

**1 new test file, 83 tests:**
- `tests/test_phase51_dry_run.py` — 83 tests across 12 test classes:
  - `TestDryRunSimulatorBasic` (4 tests) — initialization, simulation modes
  - `TestTranslationCoverageStats` (6 tests) — coverage calculation, properties, edge cases
  - `TestAssetSimulationResult` (3 tests) — result structure, risk levels
  - `TestDryRunSimulatorTranslation` (8 tests) — expression translation, coverage tracking
  - `TestDryRunSimulatorCost` (6 tests) — cost estimation integration
  - `TestDryRunSimulatorTimeline` (5 tests) — timeline estimation
  - `TestDryRunSimulatorRisk` (9 tests) — risk scoring, complexity-based classification
  - `TestDryRunSimulatorRiskHeatmap` (6 tests) — heatmap generation, asset distribution
  - `TestDryRunSimulatorChangeManifest` (8 tests) — manifest entries, action types
  - `TestDryRunSimulatorAssetResults` (6 tests) — per-asset results aggregation
  - `TestRunDryRun` (8 tests) — end-to-end dry run execution
  - `TestDryRunIntegration` (14 tests) — full integration scenarios

**Test suite totals:** 3,209 passed (up from 3,126)

### Added — Phase 50: GraphQL API & Federation

**New modules (2):**

- `src/api/graphql_schema.py` — Strawberry GraphQL schema with full query/mutation/subscription support:
  - **Queries**: `health` (status, version, uptime), `migrations` (list all), `migration(id)` (by ID with nested agents/inventory/logs via DataLoader)
  - **Mutations**: `createMigration` (name, sourceType, mode, wave, dryRun), `cancelMigration` (graceful cancellation)
  - **Subscriptions**: `migrationLogs` (real-time log streaming), `migrationEvents` (WebSocket event feed)
  - **Field-level authorization**: `require_permission()` / `check_field_permission()` integrated with existing `TokenClaims` RBAC system
  - **Query complexity/depth limiting**: `MAX_QUERY_DEPTH=10`, `MAX_QUERY_COMPLEXITY=500`, `QueryComplexityError` for violations
  - **Module-level Strawberry types**: `Migration`, `HealthStatus`, `AgentStatus`, `InventoryItem`, `LogEntry`, `CancelResult`, `MigrationCreateInput`, `GQLMigrationMode`
  - **Graceful degradation**: Schema builds at import time; module falls back cleanly when strawberry not installed

- `src/api/dataloaders.py` — DataLoader pattern for N+1 query prevention:
  - `MigrationLoader` — batch-loads MigrationRecord by ID with per-request caching
  - `InventoryLoader` — batch-loads inventory items for a migration
  - `LogLoader` — batch-loads log entries for a migration
  - `DataLoaderContext` — per-request context holding all DataLoaders (created fresh per GraphQL request)

**Enhanced modules (1):**

- `src/api/app.py` — GraphQL router mounted at `/graphql` via `strawberry.fastapi.GraphQLRouter` with automatic `DataLoaderContext` injection; graceful fallback when strawberry not installed

### Testing — Phase 50

**1 new test file, 60 tests:**
- `tests/test_phase50_graphql.py` — 60 tests across 10 test classes:
  - `TestDataLoaderContext` (12 tests) — caching, load_many, clear, missing IDs
  - `TestQueryComplexity` (9 tests) — depth measurement, complexity estimation, limit enforcement
  - `TestFieldAuthorization` (6 tests) — permission checks, role-based access, context types
  - `TestSchemaAvailability` (4 tests) — singleton, availability flag, error on missing
  - `TestQueryResolvers` (5 tests) — health, migrations list, by-ID with/without loader
  - `TestMutationResolvers` (4 tests) — create, cancel, already-completed, not-found
  - `TestSubscriptions` (3 tests) — log streaming, events not-found
  - `TestMigrationTypeResolvers` (4 tests) — inventory, logs with limit, agents, no-loader fallback
  - `TestRESTGraphQLCoexistence` (1 test) — /graphql route alongside REST endpoints
  - `TestSchemaExecution` (6 tests) — full GQL query execution, mutations, auth denial
  - `TestGQLTypeShapes` (6 tests) — type field verification

**Test suite totals:** 3,051 passed (up from 2,991)

### Dependencies — Phase 50
- `strawberry-graphql[fastapi]` — optional dependency for GraphQL support

### Added — Full Migration Example & HTML Report

**New modules (1):**

- `examples/full_migration_example.py` — Self-contained full migration pipeline example:
  - 8-step pipeline: Discovery → Schema → Semantic → Report → Security → ETL → Validation → HTML Report
  - **5 source connectors**: OAC RPD, Essbase, Cognos, Qlik, Tableau
  - `MigrationResult` dataclass with `.summary()` method
  - CLI interface: `python examples/full_migration_example.py -o output/migration_report`
  - Programmatic API: `result = await run_full_migration()` for embedding in scripts/notebooks
  - Produces: HTML report (self-contained with SVG charts, dark mode, 8 sections), Markdown report, TMDL files, DDL scripts, PBIR pages, RLS TMDL, validation output
  - Pipeline summary: 145 assets / 5 platforms / 36 DDL / 27 TMDL / 76 expressions / 18 pages / 3 roles / 89 ETL steps

**1 new test file, 75 tests:**
- `tests/test_full_migration_example.py` — 75 tests across 16 test classes:
  - **Discovery** (17 tests): OAC, Essbase, Cognos, Qlik, Tableau parsers, multi-source, specific files
  - **Schema** (4 tests): DDL generation, required keys, CREATE TABLE, logical-only exclusion
  - **Semantic** (5 tests): TMDL generation, files, translations, content, empty input
  - **Visual** (3+2+4 tests): visual mappings, prompt conversion, PBIR generation
  - **Security** (3 tests): role mapping, entry fields, empty roles
  - **ETL** (3 tests): step mapping, entry fields, empty tables
  - **Validation** (1 test): Agent 07 cross-layer validation
  - **HTML Report** (6+1+12 tests): structure, sections, dark mode, stats, SVG charts, self-contained, 8 sections, TOC, CSS/JS embedded, no external resources, print/responsive styles, badges, confidence
  - **MigrationResult** (2+1 tests): summary metrics, markdown builder
  - **End-to-end** (6 tests): single file, complex enterprise, all connectors, output dir creation, artifact verification

**Test suite totals:** 3,126 passed (up from 3,051)

---

## [4.3.0] — v4.3.0 (Production Hardening & Report Fidelity)

### Added — Phase 49: Production Hardening & Report Fidelity

**New modules (5):**

- `src/agents/semantic/bridge_table_generator.py` — M:N bridge table detection from RPD joins, generates Delta DDL + TMDL table + relationships + M expression for many-to-many patterns
- `src/agents/report/theme_converter.py` — OAC color palette/font extraction → PBI CY24SU11 theme JSON (12-color palette, typography, visual styles)
- `src/agents/report/goals_generator.py` — OAC KPI/Scorecard metrics → PBI Goals/Scorecard JSON with target/actual/status mapping
- `src/agents/etl/dq_profiler.py` — PySpark notebook generator for DQ profiling on migrated Delta tables (null %, distinct counts, min/max, pattern validation)
- `src/agents/validation/schema_drift.py` — Schema drift detection between snapshots: added/dropped tables, added/dropped columns, type changes, row count changes with critical drift flagging

**Enhanced modules (8):**

- `src/agents/security/rls_converter.py` — Hierarchy-aware RLS: `HierarchyRLSSpec`, parent-child DAX generation with `PATHCONTAINS`/`PATH`, hierarchy column detection, lookup table DDL
- `src/agents/report/pbir_generator.py` — Drill-through page wiring, What-If parameter slicers + TMDL, tooltip page generation, auto-refresh interval configuration
- `src/agents/report/layout_engine.py` — Z-order assignment (area-based), overlap detection (AABB), mobile phone layout generation (360×640 single-column), improved pagination with y-cursor reflow
- `src/agents/semantic/tmdl_generator.py` — Display folder intelligence from subject areas, multi-culture TMDL (19 locales), Copilot annotations with friendly column names
- `src/agents/report/prompt_converter.py` — Cascading slicer DAX generation with `CALCULATE`/`VALUES` parent-child filtering, chain builder from slicer configs
- `src/agents/etl/fabric_pipeline_generator.py` — Environment parameterization (dev/test/prod) with `EnvironmentConfig`, pipeline cloning per environment, JSON config export
- `src/agents/orchestrator/dag_engine.py` — Dead letter queue: `DeadLetterEntry` tracking (error, retry count, blocked dependents, timestamp), JSON export, summary reporting
- `src/agents/orchestrator/wave_planner.py` — Approval gates: `ApprovalStatus` enum, `ApprovalGate` approve/reject workflow, `GatedWavePlan` with `can_proceed()` checks, auto-gate all waves except first

**Enhanced modules (continued):**

- `src/agents/schema/ddl_generator.py` — Fabric Shortcuts (REST API payload generation), Oracle synonym → CREATE VIEW DDL translation

### Testing — Phase 49

**1 new test file, 91 tests:**
- `tests/test_phase49_production_hardening.py` — 91 tests across 22 test classes covering all Phase 49 features: bridge tables, hierarchy RLS, drill-through, What-If, themes, display folders, cascading slicers, goals/scorecard, tooltips, environment params, DQ profiling, z-order/overlap, dead letter queue, approval gates, mobile layout, pagination, auto-refresh, schema drift, multi-culture, Copilot annotations, Fabric Shortcuts, Oracle synonyms

**Test suite totals:** 2989 passed, 2 skipped (up from 2898)

### Documentation — Phase 49
- Updated CHANGELOG.md with Phase 49 additions
- Updated GAP_ANALYSIS.md: bridge tables, hierarchy RLS, drill-through, themes, goals, DQ profiling, schema drift, cascading slicers, mobile layout, environment params, approval gates, dead letter queue, Fabric Shortcuts marked as ✅
- Updated KNOWN_LIMITATIONS.md to reflect resolved items

---

## [4.2.0] — v4.2.0 (T2P Parity Completion)

### Added — Phase 48: T2P Parity Completion

**New modules:**

- `src/agents/discovery/lineage_map.py` — Full JSON lineage/dependency graph generator with `LineageNode`, `LineageEdge`, `LineageMap` models, layer classification (physical/logical/presentation/consumption/etl/security), BFS `impact_analysis()` for upstream/downstream traversal, JSON serialization (v1.0 schema)
- `src/agents/semantic/shared_model_merge.py` — Multi-report shared semantic model merge engine with SHA256-based `TableFingerprint`, `jaccard_similarity()`, `find_merge_candidates(threshold=0.7)`, `merge_semantic_models()`, `generate_merge_manifest()`, thin report references for merged models

**Expanded modules:**

- `src/agents/semantic/expression_translator.py` — DAX conversion rules expanded from 60+ to 120+:
  - **Aggregate**: STDDEV→STDEV.S, STDDEV_POP→STDEV.P, VARIANCE→VAR.S, VAR_POP→VAR.P, MEDIAN, PERCENTILE→PERCENTILEX.INC, COUNT(*)→COUNTROWS, COUNTIF→CALCULATE+COUNT, SUMIF→CALCULATE+SUM, FIRST→FIRSTNONBLANK, LAST→LASTNONBLANK
  - **Time Intelligence**: MSUM, RCOUNT, RMAX, RMIN, PARALLELPERIOD, OPENINGBALANCEYEAR, CLOSINGBALANCEYEAR
  - **Scalar**: ABS, ROUND, TRUNC, CEIL→CEILING, FLOOR, POWER, SQRT, LOG→LN, LOG10, EXP, MOD, SIGN, RPAD, LEFT, RIGHT, INITCAP, ASCII→UNICODE, CHR→UNICHAR, DECODE→SWITCH (custom handler), NVL2, COALESCE, NULLIF, GREATEST, LEAST, SYSDATE→NOW, TO_DATE→DATEVALUE, TO_CHAR→FORMAT, TO_NUMBER→VALUE, LAST_DAY→EOMONTH, NEXT_DAY, ROWNUM→RANKX
- `src/agents/semantic/tmdl_self_healing.py` — Self-healing patterns expanded from 6 to 17:
  - New patterns (7–17): missing_sort_by, invalid_format_strings, duplicate_measures, missing_rel_columns, invalid_partition_mode, duplicate_columns, expression_brackets, missing_display_folder, unicode_bom, trailing_whitespace, unreferenced_hidden
- `src/agents/report/visual_mapper.py` — Visual types expanded from 47 to 80+:
  - 35+ new OACChartType entries (percentStackedBar, sunburst, bullet, boxPlot, radar, wordCloud, sankey, chord, gantt, network, card, decomposition, tornado, sparkline, pareto, shapeMap, etc.)
  - 12+ new PBIVisualType custom visual GUIDs (Sparkline, Pareto, FlowMap, Venn, CorrelationPlot, Dumbbell, RotatingChart, SpiderChart, DotPlot, Lollipop, Waffle, KPI_INDICATOR)
  - Mapping table expanded from ~24 to 60+ entries

### Fixed — Phase 48
- `tests/test_fabric_client.py` — Fixed `test_execute_sql_placeholder` hanging on pyodbc import (mocked sys.modules)
- `tests/test_phase16_fabric.py` — Fixed `test_execute_sql_accepts_endpoint` hanging on pyodbc import (mocked sys.modules)
- `src/agents/semantic/expression_translator.py` — Fixed COUNT(*) rule ordering so it matches before generic COUNT

### Testing — Phase 48

**3 new test files, 112 tests:**
- `tests/test_lineage_map.py` — 17 tests: LineageNode, LineageEdge, LineageMap, build_lineage_map, impact_analysis, layer classification, empty maps
- `tests/test_shared_model_merge.py` — 15 tests: TableFingerprint, jaccard similarity, extract_table_fingerprint, find_merge_candidates, merge_semantic_models, generate_merge_manifest
- `tests/test_t2p_parity_phase48.py` — 80 tests: self-healing patterns 7–17, expanded DAX aggregate/time-intel/scalar rules, expanded visual types and mappings

### Documentation — Phase 48
- Updated GAP_ANALYSIS.md: shared semantic model merge and lineage map marked as ✅; DAX rules 60→120+; self-healing 6→17; visual types 47→80+
- Updated CHANGELOG.md with Phase 48 additions

---

## [4.1.0] — v4.1.0 (T2P Gap Implementation + Full Test Coverage)

### Added — Phase 47: T2P Gap Implementation (COMPLETE)

**16 new modules ported from TableauToPowerBI patterns:**

**Discovery (Agent 01)**:
- `src/agents/discovery/portfolio_assessor.py` — 5-axis readiness assessment (expression, filter, connection, security, semantic), effort scoring, GREEN/YELLOW/RED classification, wave planning by effort bands
- `src/agents/discovery/safe_xml.py` — XXE-protected XML parsing, DOCTYPE/ENTITY/SYSTEM rejection, path traversal validation

**Schema (Agent 02)**:
- `src/agents/schema/fabric_naming.py` — Fabric name sanitization: strip brackets, OAC prefix removal (`v_`, `tbl_`, `f_`, `d_`), PascalCase/snake_case conversion
- `src/agents/schema/lakehouse_generator.py` — 3-artifact Lakehouse generation (definition JSON, DDL scripts, metadata JSON), 16+ Oracle→Spark type mappings

**ETL (Agent 03)**:
- `src/agents/etl/fabric_pipeline_generator.py` — 3-stage pipeline orchestration (RefreshDataflow → TridentNotebook → TridentDatasetRefresh), 9 JDBC connector templates (Oracle, PostgreSQL, SQL Server, Snowflake, BigQuery, CSV, Excel, Custom SQL, Databricks)
- `src/agents/etl/incremental_merger.py` — Safe re-migration merge engine with USER_OWNED_FILES preservation and USER_EDITABLE_KEYS (displayName, description, title) protection

**Semantic Model (Agent 04)**:
- `src/agents/semantic/calendar_generator.py` — Auto-detect date columns → 8-column Calendar table + Date Hierarchy + sortByColumn + M query partition + 3 time intelligence DAX measures (YTD, PY, YoY%)
- `src/agents/semantic/dax_optimizer.py` — 5 pre-deployment DAX optimization rules: ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, CALCULATE collapse, constant folding
- `src/agents/semantic/leak_detector.py` — 22 OAC function leak patterns (NVL, DECODE, SYSDATE, ROWNUM, SUBSTR, VALUEOF, etc.) with auto-fix rules
- `src/agents/semantic/tmdl_self_healing.py` — 6 auto-repair patterns: duplicate table names, broken column refs, orphan measures, empty names, circular relationship Union-Find deactivation, M query try/otherwise wrapping

**Report (Agent 05)**:
- `src/agents/report/visual_fallback.py` — 3-tier visual degradation cascade (complex→simpler→table→card) with per-type cascade map and approximation notes
- `src/agents/report/bookmark_generator.py` — PBI bookmark JSON from OAC story points and saved filter states

**Security (Agent 06)**:
- `src/agents/security/governance_engine.py` — Governance engine: warn/enforce modes, naming conventions, 15 PII regex patterns, 10 credential redaction patterns, sensitivity label mapping, full governance scan

**Validation (Agent 07)**:
- `src/agents/validation/tmdl_validator.py` — TMDL structural validation (required files/dirs/keys, JSON schema, table declarations) + 8-point migration readiness assessment

**Orchestrator (Agent 08)**:
- `src/agents/orchestrator/sla_tracker.py` — SLA compliance evaluation (duration, validation, accuracy) with breach/at-risk/met status + summary reports
- `src/agents/orchestrator/monitoring.py` — 3-backend metrics export: JSON (always), Azure Monitor (Application Insights), Prometheus (push gateway)
- `src/agents/orchestrator/recovery_report.py` — Recovery action tracking: record retries, self-heal actions, manual fixes with severity categorization

**Modified files**:
- `src/agents/semantic/tmdl_generator.py` — Added steps 9-13: database.tmdl generation, compatibility level 1600
- `src/agents/report/visual_mapper.py` — Expanded PBIVisualType 23→47 types, data roles 20→38, added 18+ AppSource custom visual GUIDs

### Testing — Phase 47 (COMPLETE)

**8 new test files, 168 tests:**
- `tests/test_portfolio_assessor.py` — 17 tests: ReadinessLevel, assess_readiness, assess_portfolio, plan_waves, safe_xml parsing, XXE rejection, path validation
- `tests/test_fabric_naming_lakehouse.py` — 27 tests: sanitize_table/column/schema, PascalCase/snake_case, map_to_spark_type, build/generate_ddl/json
- `tests/test_pipeline_merger.py` — 17 tests: PipelineActivity, build_3_stage_pipeline, connectors, generate_notebook_cell, merge_artifacts
- `tests/test_semantic_new_modules.py` — 20 tests: detect_date_columns, generate_calendar, dax_optimizer rules, leak_detector, auto_fix, self_heal
- `tests/test_visual_fallback_bookmarks.py` — 17 tests: resolve_visual_fallback, bookmark model, story points, saved states, JSON generation
- `tests/test_governance_engine.py` — 16 tests: naming checks, PII detection, credential redaction, sensitivity labels, full governance scan
- `tests/test_tmdl_validator.py` — 18 tests: TMDL structural validation, readiness assessment
- `tests/test_sla_monitoring_recovery.py` — 16 tests: SLA evaluation, monitoring export, recovery tracker

### Documentation
- Updated GAP_ANALYSIS.md: 28/49 items marked as ✅ implemented; comparison tables updated to reflect parity
- Updated CHANGELOG.md with all Phase 47 additions

---

## [4.0.0] — v4.0.0 (Production Dashboard & Multi-Source Maturity)

### Added — Phase 41: Cognos & Qlik Connectors (COMPLETE)

**IBM Cognos Analytics Connector** (`src/connectors/cognos_connector.py`, 650+ lines)
- `CognosReportSpecParser` — XML parser for Cognos report specs (queries, prompts, visualizations, filters)
- `CognosExpressionTranslator` — 50+ Cognos→DAX rule catalog, 57 regex patterns, confidence scoring
- `CognosRestClient` — async REST API client (v11.1+) with overridable HTTP for testing
- `FullCognosConnector` — full `SourceConnector` lifecycle (connect, discover, extract, disconnect)
- Mappings: 11 source types, 8 data types, 15 visual types, 8 prompt types, 21 TMDL concepts
- `CognosToSemanticModelConverter` (`cognos_semantic_bridge.py`) — ParsedReportSpec → SemanticModelIR
- 70 tests (`test_cognos_connector.py`)

**Qlik Sense / QlikView Connector** (`src/connectors/qlik_connector.py`, 700+ lines)
- `QlikLoadScriptParser` — parses LOAD, SQL SELECT, LET/SET, CONNECT statements
- `QlikExpressionTranslator` — 72+ Qlik→DAX rules, set analysis→CALCULATE patterns
- `QlikEngineClient` — async Engine API client with overridable HTTP for testing
- `FullQlikConnector` — full `SourceConnector` lifecycle
- Mappings: 14 source types, 7 data types, 18 visual types, 22 TMDL concepts
- `QlikToSemanticModelConverter` (`qlik_semantic_bridge.py`) — QlikApp → SemanticModelIR
  - Tables → LogicalTable, measures → DAX, drill-down dims → hierarchies, variables → What-if params
  - Field associations → inferred joins (Qlik associative model)
- 85 tests (`test_qlik_connector.py`)

**Infrastructure updates**
- `base_connector.py` — replaced inline Cognos/Qlik stubs with lazy-import proxy pattern
- `test_phase26_connectors.py` — updated from stub assertions to full connector assertions

### Added — Phase 42: Plugin Marketplace (COMPLETE)

- **Plugin Registry** (`src/plugins/marketplace.py`) — `PluginRegistry` with JSON-backed index, search by name/tags, publish/unpublish
- **Plugin Installer** — install from registry entry or manifest, uninstall with cleanup
- **CLI helpers** — `cmd_plugin_list`, `cmd_plugin_install`, `cmd_plugin_publish`
- **Sample plugin: Visual Mapping Overrides** — override OAC→PBI visual type mappings via POST_TRANSLATE hook
- **Sample plugin: Data Quality Checks** — null ratio threshold, row count variance, PRE/POST_VALIDATE hooks
- `load_builtin_plugins()` convenience for auto-registration
- 48 tests (`test_plugin_marketplace.py`)

### Added — Phase 43: Migration Analytics Dashboard (COMPLETE)

- **Metrics models** (`src/plugins/analytics_dashboard.py`) — `AgentMetrics`, `WaveMetrics`, `CostMetrics`, `MigrationMetrics` with computed properties
- **MetricsCollector** — create snapshots, add waves, update agents, compute totals
- **DashboardDataExporter** — export to JSON + agent CSV + wave CSV
- **PBITTemplateGenerator** — 5-page Power BI template manifest (Executive Summary, Wave Progress, Agent Details, Cost Analysis, Validation)
- **ExecutiveSummary** — computed from metrics with risk detection (failures, critical issues, budget)
- 31 tests (`test_analytics_dashboard.py`)

### Added — Phase 44: Advanced RPD Binary Parser (COMPLETE)

- **Binary RPD parser** (`src/core/rpd_binary_parser.py`) — `RPDBinaryParser` supporting OBIEE 10g/11g/12c binary format
- Header parsing (magic, version, section count, RPD name)
- Section parsing (7 types: physical, logical, presentation, security, init blocks, connections, variables)
- Object parsing (12 types: table, column, join, measure, hierarchy, level, role, permission, init block, connection, variable, subject area)
- Property decoding (TLV key-value format)
- **LargeFileStreamingParser** — memory-efficient streaming for >500 MB files (4 MB chunks)
- **RPDBinaryToXMLConverter** — convert binary RPD to XML for compatibility with existing parsers
- **build_test_rpd_binary()** — synthetic binary RPD generator for testing
- 38 tests (`test_rpd_binary_parser.py`)

### Added — Phase 45: AI-Assisted Schema Optimization (COMPLETE)

- **Schema Optimizer** (`src/core/schema_optimizer.py`) — orchestrates all optimization engines
- **PartitionKeyRecommender** — cardinality-based scoring, filter-column bonus from workload, HPK recommendation for >20 GB tables
- **StorageModeAdvisor** — Direct Lake / Import / Dual mode heuristics based on data size and workload mix
- **CapacitySizer** — F2–F1024 SKU selection with headroom and workload scaling factors
- Models: `ColumnProfile`, `TableProfile`, `SchemaProfile`, `WorkloadPattern`, `OptimizationRecommendation`, `OptimizationReport`
- Column pruning (>100 cols warning), data type optimization (low-cardinality string detection)
- 27 tests (`test_schema_optimizer.py`)

### Added — Phase 46: Performance Auto-Tuning (COMPLETE)

- **PerformanceAutoTuner** (`src/core/perf_auto_tuner.py`) — orchestrates all performance tuning
- **PerformanceAnalyzer** — categorize queries (fast/normal/slow/critical), SE/FE ratio, P95 latency, hot tables
- **DAXOptimizer** — 6 anti-pattern detections: SUMX→SUM, AVERAGEX→AVERAGE, ISBLANK→COALESCE, deep nesting, bidirectional relationships, FILTER(ALL()) patterns
- **AggregationAdvisor** — scan-based aggregation table suggestions for slow queries with high row scans
- **CompositeModelAdvisor** — automatic DL/Import/Dual table assignment (writeback, row count, query frequency)
- Models: `QueryProfile`, `DAXMeasureProfile`, `DAXOptimization`, `AggregationTableSpec`, `CompositeModelPattern`, `PerformanceTuningReport`
- 39 tests (`test_perf_auto_tuner.py`)

### Testing
- **324 new tests** across all phases
- Full suite: **2,618 passed** (2 skipped), ~12 seconds
- v4.0 target of ≥2,500 tests exceeded ✅

### Added — Phase 39: React Dashboard (2026-03-23)

**Dashboard Application**
- React 18 + Vite + TypeScript SPA in `dashboard/`
- TanStack Query for server-state management with auto-refetch
- React Router v7 for client-side routing
- Recharts for data visualization (pie charts)
- Lucide React icons

**Pages & Components**
- Migration list with status icons, progress bars, and links to detail view
- Migration detail page with stat cards, pie chart breakdown, agent status table, log stream, and metadata
- 3-step migration wizard: Source → Configure → Review & Launch
- Inventory browser with search, type/complexity/status filters, and sortable columns
- Sidebar layout with navigation, health badge, and dark mode toggle

**Real-Time Features**
- WebSocket hook for live migration events
- Server-Sent Events (SSE) hook for log streaming
- Health endpoint polling every 30s

**Dark Mode**
- Full light/dark theme via CSS custom properties and `[data-theme]` attribute
- System preference detection (`prefers-color-scheme`)
- Persisted to `localStorage`

**Developer Experience**
- Vite dev server with API proxy (`/api` → backend, `/ws` → WebSocket)
- TypeScript strict mode, zero type errors
- Production build generates optimized bundle

**Testing**
- 121 new tests in `test_phase39_dashboard.py`
- Project structure, dependency, config, type alignment, component content validation
- Total: 1,992 tests (up from 1,871)

### Added — Phase 40: Tableau Connector (2026-03-24)

**TWB/TWBX Parser**
- `TableauWorkbookParser` — parse .twb XML and .twbx zip archives
- Extracts datasources, connection info, tables, columns, calculated fields
- Extracts worksheets (mark types, filters, column references)
- Extracts dashboards (size, worksheet zones)
- Parameter extraction from special "Parameters" datasource

**Calculated Field → DAX Translator**
- `TableauCalcTranslator` with 55+ rule-based regex translations
- Coverage: aggregates, string, date, logical, math, type conversion
- Flags unsupported patterns: LOD expressions (FIXED/INCLUDE/EXCLUDE), table calcs (RUNNING_SUM, INDEX, etc.)
- Confidence scoring per translation (1.0 = direct, 0.5 = complex, 0.2 = unsupported)

**REST API Client**
- `TableauRestClient` — async client for Tableau Server/Cloud REST API (v3.21)
- Personal Access Token and username/password authentication
- List workbooks, datasources, views with pagination
- Download workbook content (.twbx)
- Overridable HTTP transport for testing

**Data Source Mapping**
- `map_connection_type()` — 11 Tableau connection types → Fabric targets
- `map_data_type()` — 6 Tableau types → Fabric/Power BI column types

**Full SourceConnector**
- `FullTableauConnector` replaces Phase 26 stub (`is_stub=False`, version 1.0.0)
- Connects via REST API, discovers workbooks/datasources/views
- Downloads & parses workbooks, translates calc fields, maps data sources
- Integrated into `build_default_registry()`

**Testing**
- 116 new tests in `test_phase40_tableau.py`
- Updated `test_phase26_connectors.py` (stub → full connector assertion)
- Total: 2,108 tests (up from 1,992)

### v4.0 Phases 41–46: COMPLETE ✅

All v4.0 phases are now implemented and tested. See individual sections above.

### Planned — v5.0 (Phases 48–51)
- **Phase 48**: GraphQL API & Federation — Strawberry GraphQL on FastAPI, real-time subscriptions via WebSocket transport, field-level authorization, query complexity limits, DataLoader for N+1 prevention
- **Phase 49**: Migration Dry-Run Simulator — full agent pipeline simulation in `--dry-run` mode, cost/time/risk estimates per asset, instrumented output collectors, change manifest (JSON/HTML)
- **Phase 50**: Automated Regression Testing — baseline data snapshots at go-live, periodic comparison, report screenshot diffs (SSIM), schema drift detection, notification pipeline integration
- **Phase 51**: Self-Service Migration Portal — multi-org SSO (Azure AD B2C / Entra External ID), drag-and-drop file upload, pre-built migration templates, project management (create/clone/archive), public API with API key auth

### Fixed (Documentation — 2026-03-23)
- Corrected CLI description across all docs: `argparse`-based (was incorrectly listed as Typer/Click)
- Removed non-existent `dashboard/` directory from README.md project structure
- Added missing `src/` directories to README.md and CONTRIBUTING.md (connectors, plugins, testing, validation, api)
- Updated `pyproject.toml` version from `0.1.0` to `3.0.0`
- Added framework readiness table and v4.0 roadmap to PROJECT_PLAN.md
- Updated DEV_PLAN.md technology stack (CLI, Web API entries)

## [3.0.0] — 2025-09-15

### Added — Field-Proven Delivery (Phases 31–38)

**E2E Integration Testing (Phase 31)**
- Golden fixture generator and `IntegrationTestHarness`
- `OutputComparator` for deterministic end-to-end validation
- 30+ integration test scenarios covering incremental sync and rollback

**Documentation & Project Hygiene (Phase 32)**
- `DocValidator` for automated documentation freshness checks
- `ChangelogGenerator` and `ProjectHealthCheck` utilities
- `CIWorkflowGenerator` for GitHub Actions pipeline scaffolding

**Data Pipeline Execution (Phase 33)**
- `PipelineDeployer` for Fabric Data Factory pipeline deployment
- `DataCopyOrchestrator` with partition strategies and watermark tracking
- `PipelineMonitor` and `LandingZoneManager`

**DAX Translation Maturity (Phase 34)**
- `TranslationCatalog` with 80+ DAX function mappings (up from ~30)
- Time intelligence, level-based measures, advanced string/math functions
- `ConfidenceCalibrator` for translation quality scoring

**Migration Intelligence (Phase 35)**
- `ComplexityAnalyzer` for pre-migration asset complexity scoring
- `CostEstimator` and `TimelineEstimator` for project planning
- `PreflightChecker` and `RiskScorer` for migration readiness assessment

**UAT Workflow (Phase 36)**
- `UATSession` and `UATWorkflow` state machine (draft → active → review → signed-off)
- `ComparisonSpec`, `SignOffTracker`, `DefectLog`, and `UATReport`

**Customer Delivery Package (Phase 37)**
- `DeliveryPackage` with `AssetCatalog` and `ChangeDocGenerator`
- `TrainingContentGen`, `KnownIssueTracker`, `HandoverChecklist`

**Production Hardening v3 (Phase 38)**
- `ChaosSimulator` and `RecoveryVerifier` for resilience testing
- `SecurityScanner` and `ReleaseValidator`
- `PerformanceBaseline` for regression detection

### Testing
- 1,871 automated tests (2 skipped for FastAPI), up from 1,508

---

## [2.0.0] — 2025-07-28

### Added — Enterprise Platform (Phases 23–30)

**Web API & Dashboard (Phase 23)**
- FastAPI backend with REST endpoints (`POST /migrations`, `GET /migrations/{id}`)
- WebSocket and SSE real-time event streaming
- API endpoints designed for React + Vite dashboard (frontend implementation deferred to Phase 39)

**Containerization (Phase 24)**
- Multi-stage Dockerfile (Python 3.11+ slim)
- Docker Compose stack (API + dashboard + PostgreSQL)
- Bicep IaC for Azure Container Apps with managed identity
- Helm chart for AKS deployment
- Trivy container scanning in CI/CD

**Incremental & Delta Migration (Phase 25)**
- `ChangeDetector` with RPD diff and catalog `lastModified` tracking
- `SyncJournal` for migration state tracking
- `--mode incremental` CLI flag with per-agent `execute_incremental()`
- `SyncScheduler` (cron/interval) with conflict resolution

**Multi-Source Connectors (Phase 26)**
- `SourceConnector` abstract base class and connector registry
- OBIEE connector (RPD binary + web catalog)
- Tableau, Cognos, and Qlik connector stubs
- `--source` CLI flag for source platform selection

**AI Visual Validation (Phase 27)**
- Playwright screenshot capture (OAC + PBI, multiple viewports)
- GPT-4o visual comparison with structured JSON diff and similarity scoring
- SSIM pixel-level fallback validation
- Dashboard side-by-side viewer and PDF validation reports

**Plugin Architecture (Phase 28)**
- `PluginManager` with discover/load/validate lifecycle
- `plugin.toml` manifest format and lifecycle hooks (pre/post discover/translate/deploy)
- Plugin isolation and sandboxing with resource limits
- Custom YAML translation rules with hot-reload
- Plugin CLI commands

**Multi-Tenant SaaS (Phase 29)**
- Tenant model with context middleware for request-scoped isolation
- Tenant-scoped storage, secrets, and telemetry
- Azure AD / Entra ID SSO integration
- RBAC (admin/operator/viewer) with JWT auth middleware and API keys
- Metering (assets/tokens/API calls per tenant) and rate limiting (SlowAPI)
- Admin dashboard and tenant onboarding API

**Rollback & Versioning (Phase 30)**
- `ArtifactVersioner` with timestamped + SHA-256 content-addressable snapshots
- Diff viewer for artifact comparison
- `RollbackEngine` with reverse action replay
- Per-agent rollback support, CLI `rollback` command, and API rollback endpoint

### Testing
- 1,508 automated tests (2 skipped for FastAPI), up from 1,243

---

## [1.0.0] — 2025-07-09

### Added — GA Release

**Core Architecture**
- 8-agent DAG orchestration (Discovery → Schema → ETL → Semantic → Report → Security → Validation → Orchestrator)
- Lakehouse-based agent coordination via Delta tables
- CLI entry point (`python -m src.cli.main`) with `migrate`, `discover`, `validate`, `status` commands
- Checkpoint/resume support with `--resume` flag
- Selective agent execution with `--agents` flag

**Agent Implementations**
- **Agent 01 — Discovery**: OAC catalog crawl, RPD XML parsing (standard + streaming), dependency graph, complexity scoring
- **Agent 02 — Schema**: Oracle → Fabric type mapping, DDL generation, lakehouse table creation
- **Agent 03 — ETL**: PL/SQL → PySpark translation (rule-based + LLM), data pipeline generation, scheduling
- **Agent 04 — Semantic Model**: OAC RPD → Power BI TMDL conversion (tables, relationships, measures, hierarchies)
- **Agent 05 — Report**: OAC analyses/dashboards → Power BI PBIR reports, visual mapping, slicer conversion
- **Agent 06 — Security**: OAC roles → PBI RLS/OLS, AAD group mapping, workspace role assignment
- **Agent 07 — Validation**: Data reconciliation, metric comparison, visual verification
- **Agent 08 — Orchestrator**: DAG execution, wave planning, retry logic, notification dispatch

**Translation Engine**
- PL/SQL patterns: INSERT SELECT, UPDATE SET, DELETE FROM, MERGE INTO, CURSOR LOOP, EXECUTE IMMEDIATE, FORALL, BULK COLLECT, FOR numeric loop, WHILE loop, RAISE_APPLICATION_ERROR, exception blocks
- OAC expression → DAX: 30+ function mappings (aggregates, time intelligence, string, date, EXTRACT, CASE, CAST)
- LLM-assisted fallback via Azure OpenAI GPT-4 for complex expressions
- Confidence scoring with manual review flagging

**Deployment**
- Fabric Lakehouse DDL deployment (5 coordination tables)
- Power BI semantic model deployment via TMDL (Tabular Editor + REST + PBIX import fallback)
- PBIR report deployment
- RLS/OLS configuration
- Dry-run mode with performance baselining

**Observability**
- Structured telemetry (events, metrics, spans) with correlation IDs
- Application Insights exporter
- OTLP compatibility layer (OpenTelemetry Protocol)
- Notification channels: Teams webhook, email (Azure Communication Services), PagerDuty Events API v2

**Security**
- Azure Key Vault integration for secret management
- Managed identity authentication support
- Credential scanner for source code and config audit
- SecretValue redaction in logs

**Infrastructure**
- Bicep IaC templates (App Insights, Key Vault, OpenAI, Fabric workspace)
- CI/CD pipeline support via Fabric Git integration

### Testing
- 1,200+ automated tests
- Unit, integration, and regression test suites
- Phase-by-phase test organization (Phases 0–22)

---

## [0.9.0] — Phase 20 (Advanced Translation)

### Added
- Complex PL/SQL patterns (FOR loop, WHILE loop, RAISE, EXECUTE IMMEDIATE USING)
- OAC string functions (SUBSTRING, UPPER, LOWER, TRIM, REPLACE, LENGTH, INSTR, LPAD)
- OAC date functions (TIMESTAMPADD, TIMESTAMPDIFF, CURRENT_DATE, ADD_MONTHS, EXTRACT)
- Edge case handling for untranslatable patterns

## [0.8.0] — Phase 19 (Live Deployment)

### Added
- Coordination table DDL deployment
- PBIR report deployment
- OLS (Object-Level Security) support
- End-to-end dry-run migration with performance baseline

## [0.7.0] — Phase 18 (OAC Validation)

### Added
- Live OAC connection validation
- RPD streaming parser for large files
- Real-world RPD fixture generation

## [0.6.0] — Phase 17 (Agent Wiring)

### Added
- Agent registry and runner factory
- State coordinator with lifecycle hooks
- CLI end-to-end verification

## [0.5.0] — Phase 16 (Stub Elimination)

### Added
- Real Fabric SQL execution (pyodbc)
- Real PBI deployment (TMDL + REST)
- Graph API group resolution
- OAC authentication (IDCS OAuth2)

## [0.1.0–0.4.0] — Phases 0–15

### Added
- Initial project scaffolding and architecture
- Core data models and abstractions
- Type mapping engine
- Wave planner
- All 8 agent stubs with full interface contracts
- Test framework with 942 tests
