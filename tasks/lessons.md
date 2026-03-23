# Lessons Learned

Rules to prevent recurring mistakes. Updated after every correction.

---

## 1. Shared Model Field Names — Always Verify

**Mistake**: Tests used `AssetType.TABLE` but the enum was `AssetType.PHYSICAL_TABLE`. Tests used `MigrationResult.status` but the field is `MigrationResult.succeeded`.

**Rule**: Before writing tests for any model in `src/core/models.py`, read the actual field names. Never assume from memory. Key models and their real fields:
- `InventoryItem`: `asset_type`, `source_id`, `name`, `metadata`, `complexity`
- `MigrationPlan`: `agent_id`, `wave`, `items` (not `scope`, `steps`)
- `MigrationResult`: `agent_id`, `total`, `succeeded`, `failed`, `skipped`, `errors`
- `ValidationReport`: `agent_id`, `total_checks`, `passed`, `failed`, `warnings`, `details`
- `AssetType` values: `PHYSICAL_TABLE`, `LOGICAL_TABLE`, `PRESENTATION_TABLE`, `ANALYSIS`, `DASHBOARD`, etc.

---

## 2. Config Loader Tests — Isolate from Real Config Files

**Mistake**: `test_loads_base_config` loaded the real `config/dev.toml` overlay because `config_dir` defaulted to the project root.

**Rule**: Always pass `config_dir=tmp_path` in config loader tests to prevent real config files from contaminating test expectations.

---

## 3. DAG Engine API — Returns Lists, Not Dicts

**Mistake**: Tests treated `dag.nodes` as a dict and called `.values()`. Tests assumed `topological_batches()` returns `list[set]`.

**Rule**: 
- `dag.nodes` is a `list[str]`, use `dag.get_node(name)` for node details
- `topological_batches()` returns `list[list[str]]`
- `ready_nodes()` returns `list[str]`

---

## 4. NotificationManager API — Constructor and Methods

**Mistake**: Used `channels=` parameter and `info()`/`warn()`/`error()` methods.

**Rule**: 
- Constructor uses `enabled_channels=` (not `channels=`)
- Single method: `notify(title, message, severity, channel)`
- Severity enum: `Severity.INFO`, `Severity.WARNING`, `Severity.ERROR`, `Severity.CRITICAL`

---

## 5. Always Run Full Test Suite

**Mistake**: Marking phases complete without running `pytest tests/ -v`.

**Rule**: After ANY code change, run `& ".venv/Scripts/python.exe" -m pytest tests/ -v`. At 4 seconds for 942 tests, there is no reason to skip this. Never declare completion without a passing full suite.

---

## 6. Shared Module Changes Require Consumer Audit

**Rule**: Before modifying `models.py`, `base_agent.py`, `config.py`, or `config_loader.py`, grep for all importers:
```
grep_search "from src.core.models import" --includePattern "**/*.py"
```
Verify all consumers are compatible with the change before committing.

---

## 7. Test Fixtures Must Match Current Enums

**Mistake**: `conftest.py` fixture `small_inventory` used `AssetType.TABLE` after it was renamed.

**Rule**: When an enum value changes, search all fixtures in `conftest.py` and test files for the old value.
