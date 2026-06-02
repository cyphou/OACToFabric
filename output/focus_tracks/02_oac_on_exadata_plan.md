# Track 2 — OAC Reports on Exadata

## Goal

Migrate OAC reporting and semantic layer fed by Exadata to Fabric Warehouse + Power BI.

## Scope

- OAC inventory and report extraction
- Oracle/Exadata schema and ETL migration
- OAC report to PBIR conversion

## Execute

1. Discovery and planning:

```powershell
oac-migrate --config config/migration.toml --output-dir output/focus_oac_exadata discover
oac-migrate --config config/migration.toml --output-dir output/focus_oac_exadata plan
```

2. Run schema and ETL migration phases:

```powershell
py -3 -m src.cli.main --config config/migration.toml migrate --agents 02-schema
py -3 -m src.cli.main --config config/migration.toml migrate --agents 03-etl
```

3. Run semantic and report phases:

```powershell
py -3 -m src.cli.main --config config/migration.toml migrate --agents 04-semantic
py -3 -m src.cli.main --config config/migration.toml migrate --agents 05-report
```

4. Validate:

```powershell
oac-migrate --config config/migration.toml --output-dir output/focus_oac_exadata validate
```

## Exit Criteria

- Exadata-backed subject areas present in semantic model
- Priority OAC dashboards converted and validated
- Validation report has no critical mismatches