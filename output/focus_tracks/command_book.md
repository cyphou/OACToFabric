# Focus Command Book

## Full Test Gate

```powershell
pytest tests/ --tb=short -q
```

## Essbase + Writeback

```powershell
pytest tests/test_essbase_connector.py tests/test_essbase_semantic_bridge.py tests/test_writeback_generator.py tests/test_longview_migration.py -q
py -3 scripts/prepare_bso_writeback.py --outline examples/essbase_samples/longview_budget_writeback.xml --enable-allocation --enable-currency
```

## OAC Discovery/Plan

```powershell
oac-migrate --config config/migration.toml --output-dir output/focus_run discover
oac-migrate --config config/migration.toml --output-dir output/focus_run plan
```

## OAC Migration Phases

```powershell
py -3 -m src.cli.main --config config/migration.toml migrate --agents 02-schema
py -3 -m src.cli.main --config config/migration.toml migrate --agents 03-etl
py -3 -m src.cli.main --config config/migration.toml migrate --agents 04-semantic
py -3 -m src.cli.main --config config/migration.toml migrate --agents 05-report
py -3 -m src.cli.main --config config/migration.toml migrate --agents 06-security
py -3 -m src.cli.main --config config/migration.toml migrate --agents 07-validation
```