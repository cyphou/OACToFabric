# Runbook: Starting a New Migration Run

## Prerequisites

1. **OAC Access**: Verify IDCS credentials in `.env` file or environment:
   - `OAC_BASE_URL`
   - `OAC_CLIENT_ID`
   - `OAC_CLIENT_SECRET`
   - `OAC_IDCS_URL`

2. **Fabric Access**: Service Principal configured:
   - `FABRIC_TENANT_ID`
   - `FABRIC_CLIENT_ID`
   - `FABRIC_CLIENT_SECRET`
   - `FABRIC_WORKSPACE_ID`

3. **Configuration**: Review `config/migration.toml` — set scope, wave, and agent settings.

---

## Step-by-Step

### 1. Review Configuration

```bash
# Verify config loads correctly
oac-migrate --config config/migration.toml status
```

### 2. Run Discovery Only (Recommended First Step)

```bash
oac-migrate --config config/migration.toml --output-dir output/run_001 discover
```

Review the generated inventory in `output/run_001/inventory.json`. Verify all expected assets are discovered.

### 3. Generate Migration Plan (Dry Run)

```bash
oac-migrate --config config/migration.toml --output-dir output/run_001 plan
```

Review the wave plan in `output/run_001/wave_plan.md`.

### 4. Execute Full Migration

```bash
# Single wave
oac-migrate --config config/migration.toml --output-dir output/run_001 migrate --wave 1

# All waves
oac-migrate --config config/migration.toml --output-dir output/run_001 migrate
```

### 5. Run Validation

```bash
oac-migrate --config config/migration.toml --output-dir output/run_001 validate
```

### 6. Check Results

Review output files:
- `output/run_001/migration_summary.md` — Overall outcome
- `output/run_001/wave_plan.md` — Wave execution details
- `output/run_001/notification_log.md` — Events and alerts
- `output/run_001/validation_report.md` — Data quality checks

---

## Environment Overlays

Use per-environment overlays to change settings:

```bash
# Development (LLM disabled, debug logging)
oac-migrate migrate --config config/migration.toml  # picks up config/dev.toml

# Production (LLM enabled, stricter settings)
OAC_ENVIRONMENT=prod oac-migrate migrate --config config/migration.toml
```

---

## Resuming a Failed Run

If a migration fails mid-run, use the checkpoint system:

```bash
# Resume from last checkpoint
oac-migrate migrate --config config/migration.toml --resume --output-dir output/run_001
```

The orchestrator reads `output/run_001/.checkpoint.json` and skips completed waves/agents.
