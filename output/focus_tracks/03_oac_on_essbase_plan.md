# Track 3 — OAC on Top of Essbase

## Goal

Migrate OAC reports that depend on Essbase cubes while preserving planning/writeback capabilities.

## Scope

- Essbase cube semantic migration
- OAC report conversion referencing migrated semantics
- Longview/BSO writeback backend replacement

## Execute

1. Migrate Essbase core first (Track 1).

2. Run OAC report migration phases:

```powershell
py -3 -m src.cli.main --config config/migration.toml migrate --agents 05-report
py -3 -m src.cli.main --config config/migration.toml migrate --agents 06-security
```

3. Validate parity against OAC on Essbase:

```powershell
py -3 -m src.cli.main --config config/migration.toml migrate --agents 07-validation
```

## Key Controls

- Track low-confidence Essbase calc translations (<0.7)
- Prioritize Scenario/Period/Entity totals parity
- Validate RLS equivalence for Essbase filters

## Exit Criteria

- OAC dashboards over Essbase have validated Power BI equivalents
- Security roles and totals validated
- Writeback path operational in Fabric