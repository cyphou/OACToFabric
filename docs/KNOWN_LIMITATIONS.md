# Known Limitations — OAC to Fabric Migration Framework

**Version:** 6.0.0 (Phase 62)  
**Updated:** 2026-03-31

This document consolidates all known limitations, approximations, and unsupported features across the migration framework. For each limitation, the severity and recommended workaround are provided.

---

## Severity Key

| Severity | Description |
|----------|------------|
| 🔴 **High** | Functional gap — manual intervention always required |
| 🟡 **Medium** | Approximated — result may need manual review |
| 🟢 **Low** | Cosmetic or edge-case only |

---

## 1. Discovery & Extraction

| # | Limitation | Severity | Workaround |
|---|-----------|----------|------------|
| D-1 | Full re-crawl required (no incremental discovery) | 🟡 | Use `--resume` to skip already-processed assets |
| D-2 | RPD files >200 MB may cause high memory usage | 🟡 | Use streaming parser (`src/core/streaming_parser.py`) — enabled by default for >50 MB |
| D-3 | OAC REST API rate limits not tracked per-endpoint | 🟢 | Exponential backoff handles throttling; monitor `agent_logs` for 429s |
| D-4 | Circular references in RPD XML detected but not resolved | 🔴 | Manual RPD cleanup required before migration |
| D-5 | OAC version-specific API differences not handled | 🟡 | Test against target OAC version; file issues for unsupported features |
| D-6 | Cognos and Qlik connectors are ~~stubs only~~ fully implemented (Phase 41) | ✅ | Phase 41 delivered full Cognos + Qlik connectors |
| D-7 | Essbase connector is fully implemented | ✅ | REST API client, outline parser, 55+ calc→DAX, 24+ MDX→DAX, 22 TMDL mappings |

## 2. Schema & Data Migration

| # | Limitation | Severity | Workaround |
|---|-----------|----------|------------|
| S-1 | Oracle constraints (PK, FK, indexes) not fully migrated | 🟡 | Delta tables have limited constraint support; enforce at application layer |
| S-2 | Materialized views not migrated | 🔴 | Recreate as Fabric Lakehouse views or computed tables manually |
| S-3 | Oracle table partitioning flattened | 🟡 | Add Delta Lake partitioning manually in DDL post-migration |
| S-4 | Virtual columns treated as regular columns | 🟡 | May need computed column definition in TMDL |
| S-5 | Oracle sequences → identity columns not tested at scale | 🟡 | Verify sequence continuity after migration |
| S-6 | Complex cross-view dependencies may fail translation | 🟡 | Migrate views in dependency order; review `mapping_rules` log |
| S-7 | `XMLTYPE` serialized as string (XML structure lost) | 🟢 | Parse XML in downstream PySpark if structure needed |

## 3. ETL & Pipelines

| # | Limitation | Severity | Workaround |
|---|-----------|----------|------------|
| E-1 | Complex PL/SQL packages with inter-procedure dependencies | 🔴 | LLM-assisted translation + manual review queue |
| E-2 | Dataflow Gen2 (Power Query M) limited to simple queries | 🟡 | Complex ETL routed to PySpark notebooks instead |
| E-3 | Advanced DBMS_SCHEDULER expressions may lose precision | 🟡 | Review generated cron triggers manually |
| E-4 | ~~No environment-specific parameterization injected~~ | ✅ | **Resolved in Phase 49**: `fabric_pipeline_generator.py` provides `parameterize_pipeline()` + `generate_env_config_json()` for dev/test/prod |
| E-5 | Job chain parallel branches not generated | 🟡 | Pipeline uses sequential activities; add parallel branches manually if needed |
| E-6 | No post-deployment alerting rules generated | 🟢 | Configure Fabric Data Factory alerts manually |

## 4. Semantic Model (TMDL)

| # | Limitation | Severity | Workaround |
|---|-----------|----------|------------|
| M-1 | ~~M:N relationships flagged for manual review~~ | ✅ | **Resolved in Phase 49**: `bridge_table_generator.py` auto-generates bridge table DDL + TMDL + relationships + M expression |
| M-2 | Calculation groups not implemented | 🟡 | Create calculation groups manually in Tabular Editor |
| M-3 | ~~All measures placed in "Measures" display folder~~ | ✅ | **Resolved in Phase 49**: `tmdl_generator.py` groups measures by RPD subject area via `_build_display_folder_map()` |
| M-4 | ~~No auto-generated Calendar/Date table~~ | ✅ | **Resolved in Phase 47**: `calendar_generator.py` auto-detects date columns and generates 8-column Calendar table with hierarchy and 3 time intelligence measures |
| M-5 | No composite model / aggregation tables | 🟡 | All tables use Import mode; configure DirectQuery/Composite manually |
| M-6 | LLM translations with confidence < 0.7 flagged | 🟡 | Review queue in `agent_tasks` Delta table; manual DAX correction |
| M-7 | `INDEXCOL` / `DESCRIPTOR_IDOF` approximated | 🟡 | Best-effort column key reference; verify in Tabular Editor |
| M-8 | ~~No TMDL self-healing (duplicate names, broken refs)~~ | ✅ | **Resolved in Phase 47+48**: `tmdl_self_healing.py` provides 17 auto-repair patterns |
| M-9 | No incremental TMDL update (full regeneration only) | 🟢 | Use `--resume` to regenerate only changed tables |

## 5. Reports (PBIR)

| # | Limitation | Severity | Workaround |
|---|-----------|----------|------------|
| R-1 | Custom OAC plugins/extensions unsupported | � | **Improved in Phase 47**: 3-tier visual fallback cascade in `visual_fallback.py` handles unknown visuals gracefully |
| R-2 | ~~Theme migration not implemented~~ | ✅ | **Resolved in Phase 49**: `theme_converter.py` extracts OAC colors/fonts → PBI CY24SU11 theme JSON |
| R-3 | ~~Mobile layouts not generated~~ | ✅ | **Resolved in Phase 49**: `layout_engine.py` generates phone layout (360×640, single-column stacked) |
| R-4 | ~~Bookmarks limited to action-based mappings~~ | ✅ | **Resolved in Phase 47**: `bookmark_generator.py` generates PBI bookmarks from OAC story points and saved states |
| R-5 | Deeply nested containers (4+ levels) may misalign | 🟡 | Review layout and adjust positions in PBI Desktop |
| R-6 | ~~Reports with 50+ visuals not paginated~~ | ✅ | **Resolved in Phase 49**: `layout_engine.py` improved `paginate()` with y-cursor reflow for proper multi-page splitting |
| R-7 | ~~Tooltip pages not generated~~ | ✅ | **Resolved in Phase 49**: `pbir_generator.py` generates tooltip pages + wires to visuals |
| R-8 | Small multiples mapping incomplete for complex trellis | 🟡 | Simple trellis works; complex multi-axis trellis needs manual rework |
| R-9 | Conditional formatting thresholds use value-based (not percentage) | 🟢 | Adjust threshold values in PBI visual formatting |

## 6. Security

| # | Limitation | Severity | Workaround |
|---|-----------|----------|------------|
| SEC-1 | ~~Complex hierarchy-based dynamic security not migrated~~ | ✅ | **Resolved in Phase 49**: `rls_converter.py` generates hierarchy RLS with `PATHCONTAINS`/`PATH` DAX |
| SEC-2 | ~~Sensitivity labels not migrated~~ | ✅ | **Resolved in Phase 47**: `governance_engine.py` maps OAC roles to Purview sensitivity labels |
| SEC-3 | No automated Azure AD group provisioning | 🟡 | Create AD groups manually using generated CSV mapping |
| SEC-4 | Multi-valued session variables may need manual tuning | 🟡 | Review lookup table for complex OR/AND filter combinations |
| SEC-5 | OAC audit trail not migrated to Fabric governance | 🟢 | Historical audit data must be archived separately |

## 7. Validation

| # | Limitation | Severity | Workaround |
|---|-----------|----------|------------|
| V-1 | ~~No schema drift detection post-migration~~ | ✅ | **Resolved in Phase 49**: `schema_drift.py` provides `SchemaSnapshot` comparison, `DriftReport` with critical drift flagging |
| V-2 | No statistical sampling for very large tables (>100M rows) | 🟡 | Reduce sample size in reconciliation config |
| V-3 | Visual comparison relies on screenshots (pixel-based) | 🟡 | SSIM scoring flags differences; manual review for borderline cases |
| V-4 | No continuous validation after go-live | 🟡 | Schedule periodic validation runs manually |

## 8. Platform / Infrastructure

| # | Limitation | Severity | Workaround |
|---|-----------|----------|------------|
| P-1 | Dashboard requires Node.js for development | 🟢 | Pre-built dashboard served by FastAPI in production |
| P-2 | ~~No SLA enforcement per agent~~ | ✅ | **Resolved in Phase 47**: `sla_tracker.py` evaluates duration, validation, and accuracy SLAs per agent |
| P-3 | ~~No dead letter queue for permanently failed tasks~~ | ✅ | **Resolved in Phase 49**: `dag_engine.py` provides `DeadLetterQueue` with entry tracking, JSON export, summary |
| P-4 | ~~Cognos and Qlik connectors are stubs~~ | ✅ | **Resolved in Phase 41**: Full connectors implemented |
| P-5 | No VNET/Private Endpoint guidance for production | 🟡 | Follow Azure networking best practices; see `infra/main.bicep` |

---

## Feature Comparison vs. TableauToPowerBI

| Feature | T2P Status | OAC→Fabric Status |
|---------|:----------:|:-----------------:|
| Auto Calendar table | ✅ | ✅ (Phase 47) |
| TMDL self-healing | ✅ | ✅ (Phase 47+48, 17 patterns) |
| Visual fallback cascade | ✅ | ✅ (Phase 47) |
| DAX optimizer (AST rewriter) | ✅ | ✅ (Phase 47) |
| Schema drift detection | ✅ | ✅ (Phase 49) |
| Lineage map (JSON) | ✅ | ✅ (Phase 48) |
| Governance framework (PII, naming) | ✅ | ✅ (Phase 47) |
| QA auto-fix (17 patterns) | ✅ | ✅ (Phase 48) |
| Shared semantic model merge | ✅ | ✅ (Phase 48) |
| 180+ DAX conversions | ✅ | 120+ (expanded in Phase 48) |
| 118+ visual types | ✅ | 80+ (expanded in Phase 48) |
| 42 data connectors (M query) | ✅ | N/A (Spark/Delta native) |
| Essbase migration | ❌ | ✅ Full (55+ calc→DAX, 24+ MDX→DAX, REST API, outlines) |
| Plugin system | ❌ | ✅ |
| Runbooks (operational) | ❌ | ✅ (6 runbooks) |
| ADRs | ❌ | ✅ (4 ADRs) |
| FastAPI REST backend | ❌ (stdlib) | ✅ |
| React dashboard | ❌ | ✅ |
