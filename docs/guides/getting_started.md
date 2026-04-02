# User Guide: Running Your First Migration

This guide walks you through a first OAC → Fabric & Power BI migration using the CLI.

---

## Prerequisites

| Requirement | Details |
|---|---|
| Python | 3.12 or later |
| OAC access | IDCS client credentials with catalog read permissions |
| Fabric workspace | Service principal with Contributor role |
| Power BI workspace | XMLA read/write endpoint enabled |
| Network | Access to OAC APIs, Fabric APIs, Azure OpenAI (if LLM enabled) |

---

## 1. Install

```bash
git clone <repo-url>
cd OACToFabric
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 2. Configure

### Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

### Migration Config

Edit `config/migration.toml`:

```toml
[migration]
environment = "dev"
output_dir = "output"

[scope]
include_paths = ["/shared/Sales", "/shared/Finance"]
exclude_paths = ["/shared/Archive"]
asset_types = []   # empty = all types

[orchestrator]
max_retries = 3
parallel_agents_per_wave = 3
max_items_per_wave = 50

[llm]
enabled = false    # Set to true if Azure OpenAI is configured
```

## 3. Discover

Run discovery to inventory all OAC assets in scope:

```bash
oac-migrate discover --config config/migration.toml --output-dir output/first_run
```

Review the output:
- `output/first_run/inventory.json` — All discovered assets
- Console output shows counts by asset type

## 4. Plan

Generate a migration plan without executing:

```bash
oac-migrate plan --config config/migration.toml --output-dir output/first_run
```

Review `output/first_run/wave_plan.md`:
- How many waves
- Which agents run in each wave
- Estimated complexity

## 5. Migrate (Dry Run)

Test the full pipeline without deploying to Fabric:

```bash
oac-migrate migrate --config config/migration.toml --dry-run --output-dir output/first_run
```

## 6. Migrate (Live)

Execute the full migration:

```bash
oac-migrate migrate --config config/migration.toml --output-dir output/first_run
```

Monitor progress:
- Console shows real-time agent status
- `output/first_run/notification_log.md` captures events

## 7. Validate

Run validation checks:

```bash
oac-migrate validate --config config/migration.toml --output-dir output/first_run
```

### Quick Validation with Migration Tools (v8.0)

Before deploying, use the practical tooling to catch issues:

```bash
# Validate DAX measure syntax across all TMDL files
python -c "from src.tools.dax_validator import validate_tmdl_directory; print(validate_tmdl_directory('output/first_run'))"

# Validate TMDL output directory structure
python -c "from src.tools.tmdl_file_validator import validate_output_directory; print(validate_output_directory('output/first_run'))"

# Dry-run deployment (check naming rules, ordering, dependencies)
python -c "from src.tools.fabric_dry_run import DeploymentDryRun; d = DeploymentDryRun('output/first_run'); print(d.validate())"
```

Review `output/first_run/validation_report.md`:
- Row count comparisons
- Schema validation
- Expression translation accuracy
- Security rule coverage

## 8. Review Results

```
output/first_run/
├── migration_summary.md     # Overall outcome
├── wave_plan.md             # Wave execution details
├── notification_log.md      # Events and alerts
├── validation_report.md     # Data quality
├── .checkpoint.json         # Resume point (if interrupted)
└── semantic_model/          # Generated TMDL files
    ├── model.tmdl
    └── tables/
```

---

## Next Steps

- **Enable LLM**: Set `[llm] enabled = true` in config for expression translation.
- **Production**: Use `config/prod.toml` overlay with stricter settings.
- **Scale**: See [Runbook: Scaling Fabric Capacity](../runbooks/06_scale_fabric_capacity.md).
- **Troubleshoot**: See [Runbook: Diagnosing a Failed Agent](../runbooks/02_diagnose_failed_agent.md).
