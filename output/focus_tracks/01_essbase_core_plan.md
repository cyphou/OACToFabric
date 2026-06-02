# Track 1 — Essbase Migration (Core)

## Goal

Migrate Essbase cubes to Fabric semantic + writeback stack with validation and cutover.

## Scope

- Outline parsing, calc translation, TMDL generation
- BSO writeback backend for Longview/Smart View replacement path
- UAT and cutover readiness

## Execute

1. Run Essbase connector/bridge tests:

```powershell
pytest tests/test_essbase_connector.py tests/test_essbase_semantic_bridge.py -q
```

2. Generate BSO writeback package:

```powershell
py -3 scripts/prepare_bso_writeback.py --outline examples/essbase_samples/longview_budget_writeback.xml --enable-allocation --enable-currency
```

3. Review artifacts:

- output/etl/bso_writeback_prep/warehouse_ddl.sql
- output/etl/bso_writeback_prep/stored_procedures.sql
- output/etl/bso_writeback_prep/calc_notebook.py
- output/etl/bso_writeback_prep/tds_connection.json
- output/etl/bso_writeback_prep/cutover_checklist.md

## Exit Criteria

- UAT notebook passes
- Writeback round-trip passes
- Cutover checklist approved