# BSO Writeback Artifact Contract (v1)

Status: Draft for Sprint 1 freeze
Date: 2026-06-01

## Purpose

Define the minimum required artifact set and interface expectations for BSO writeback migration outputs.

Primary output folder:

- output/etl/bso_writeback_prep

## Required Files

1. warehouse_ddl.sql
2. stored_procedures.sql
3. calc_notebook.py
4. pipeline.json
5. model_hints.json
6. dimension_ddl.sql
7. data_migration_notebook.py
8. uat_notebook.py
9. cutover_checklist.md
10. tds_connection.json
11. assessment.json
12. PREP_SUMMARY.md

## Interface Contract

### warehouse_ddl.sql

- Must include input, consolidated, and audit table definitions.
- Must be idempotent where possible.

### stored_procedures.sql

- Must include write/merge procedure and validation procedure.
- Must return deterministic error output for failed validation.

### calc_notebook.py

- Must include AGG, allocation, and YTD calculation stages when enabled.
- Must be runnable in Fabric notebook runtime without additional private dependencies.

### pipeline.json

- Must include lookup/check stage, calc notebook stage, validation stage, and refresh stage.
- Must use consistent activity names across runs.

### tds_connection.json

- Must include server, database, auth mode, and target writeback table names.
- Must not include plain text secrets.

### assessment.json

- Must expose cube complexity summary and warnings list.
- Must include confidence or risk markers used in triage.

## Non-Functional Requirements

1. Reproducible generation from the same outline input.
2. No credential leaks in generated artifacts.
3. Naming consistency across DDL, procedures, notebooks, and pipeline.

## Validation Gates

1. Schema gate: all required files present.
2. Syntax gate: SQL and JSON parse without fatal errors.
3. Behavior gate: UAT notebook validates writeback round-trip.
4. Security gate: no secret material in output files.

## Change Control

1. Any breaking artifact change requires version bump (v1 -> v2).
2. Contract changes must be reflected in:
   - output/focus_tracks/01_essbase_core_plan.md
   - docs/ROADMAP_EXECUTION_BOARD.md
3. Validation tests must be updated in the same change set.
