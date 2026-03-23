# Deployment Guide — Fabric & Power BI

This guide covers deploying migrated artifacts to Microsoft Fabric workspaces and Power BI Service.

---

## Prerequisites

1. **Microsoft Fabric workspace** with capacity assigned (F2+ recommended)
2. **Azure AD App Registration** (Entra ID) with API permissions:
   - `Power BI Service` → `Dataset.ReadWrite.All`
   - `Power BI Service` → `Report.ReadWrite.All`
   - `Power BI Service` → `Workspace.ReadWrite.All`
3. **Admin consent** granted for the above permissions
4. **Client secret** or **Managed Identity** configured
5. **Azure Key Vault** with secrets provisioned (see [security.md](security.md))

## Configuration

### migration.toml

The primary configuration file at `config/migration.toml`:

```toml
[fabric]
workspace_id = "<your-workspace-guid>"
lakehouse_name = "MigrationLakehouse"

[azure]
tenant_id = "<your-tenant-guid>"
client_id = "<app-registration-client-id>"
keyvault_url = "https://your-keyvault.vault.azure.net/"

[deployment]
timeout_seconds = 600
retry_attempts = 3
retry_delay_seconds = 10
```

### Environment-Specific Configs

| Config File | Purpose |
|-------------|---------|
| `config/dev.toml` | Development — verbose logging, short timeouts |
| `config/migration.toml` | Default — balanced settings |
| `config/prod.toml` | Production — retry hardened, minimal logging |

## Authentication Methods

### Service Principal (Recommended for CI/CD)

Set secrets in Azure Key Vault:
- `fabric-tenant-id`
- `fabric-client-id`
- `fabric-client-secret`

The framework reads from Key Vault at startup via `src/core/keyvault_provider.py`.

### Managed Identity (For Azure-hosted runners)

When deployed to Azure Container Apps or Azure VMs, the framework uses `DefaultAzureCredential` which automatically picks up managed identity credentials.

### No Authentication (Local Dev)

Use `--dry-run` mode to generate artifacts without deploying:
```bash
python -m src.cli migrate --scope /shared/Sales --dry-run
```

## Deployment Pipeline

### CLI Deployment

```bash
# Full migration: discover → schema → ETL → semantic → reports → security → validation
python -m src.cli migrate --config config/prod.toml --scope /shared/Sales

# Single wave
python -m src.cli migrate --config config/prod.toml --wave 1

# Resume after failure
python -m src.cli migrate --config config/prod.toml --resume

# Dry run (no deployment)
python -m src.cli migrate --config config/prod.toml --scope /shared/Sales --dry-run
```

### REST API Deployment

```bash
# Start the API server
python -m src.api.app

# Create a new migration
curl -X POST http://localhost:8000/migrations \
  -H "Content-Type: application/json" \
  -d '{"scope": "/shared/Sales", "config": "prod"}'

# Check status
curl http://localhost:8000/migrations/{migration_id}

# Stream logs
curl http://localhost:8000/migrations/{migration_id}/logs
```

### Docker Deployment

```bash
# Build the container
docker build -t oac-to-fabric .

# Run with config mounted
docker run -v $(pwd)/config:/app/config oac-to-fabric \
  migrate --config config/prod.toml --scope /shared/Sales
```

## What Gets Deployed

| Artifact | Fabric Target | API Used |
|----------|---------------|----------|
| Delta tables | Fabric Lakehouse | Lakehouse REST API / Spark SQL |
| Semantic model (TMDL) | Power BI workspace | XMLA endpoint |
| Reports (PBIR) | Power BI workspace | PBI REST API |
| Data Factory pipelines | Fabric workspace | Fabric REST API |
| PySpark notebooks | Fabric workspace | Fabric REST API |
| RLS/OLS roles | Semantic model | XMLA endpoint |

## Deployment Order

The framework deploys artifacts in dependency order:

```
1. Lakehouse tables (Delta)     → Schema Agent (02)
2. Data Factory pipelines       → ETL Agent (03)
3. PySpark notebooks            → ETL Agent (03)
4. Semantic model (TMDL)        → Semantic Model Agent (04) + Security Agent (06)
5. Reports (PBIR)               → Report Agent (05)
6. Workspace role assignments   → Security Agent (06)
```

## Retry & Error Handling

The `FabricClient` includes built-in retry logic:

- **HTTP 429** (Rate Limited): Respects `Retry-After` header, waits and retries
- **HTTP 5xx** (Server Error): Retries up to configured attempts with exponential backoff
- **Timeout**: Operations time out after `deployment.timeout_seconds`
- **Circuit breaker**: After 5 consecutive failures, circuit opens for 60s (`src/core/resilience.py`)

## Validation After Deployment

The Validation Agent (07) runs automatically after each wave:

```bash
# Manual validation trigger
python -m src.cli validate --config config/prod.toml --scope /shared/Sales

# View validation results
python -m src.cli report --config config/prod.toml --migration-id <id>
```

## Environment Promotion

### Using Fabric Git Integration

```
dev workspace ──git push──► dev branch ──PR──► main branch ──git push──► prod workspace
```

1. Generate artifacts in dev workspace
2. Commit to Git (Fabric Git Integration)
3. PR to main branch (review + CI validation)
4. Fabric Git Integration syncs to prod workspace

### Using Bicep (Infrastructure-as-Code)

```bash
# Deploy Fabric resources
az deployment group create \
  --resource-group rg-migration \
  --template-file infra/main.bicep \
  --parameters environment=prod
```

## Monitoring

### Application Insights

The framework exports telemetry to Application Insights:
- Agent execution traces (start, end, duration, status)
- LLM translation metrics (tokens, latency, confidence)
- Deployment success/failure rates
- Lakehouse read/write latency

### Dashboard

The React dashboard provides real-time visibility:
- Migration progress by wave and agent
- Validation pass/fail rates
- Asset inventory browser
- Agent log streaming (WebSocket)

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `401 Unauthorized` | Verify Key Vault secrets (tenant ID, client ID, client secret). Ensure admin consent granted. |
| `403 Forbidden` | Verify service principal has workspace Admin/Contributor role. |
| `429 Too Many Requests` | Retry logic handles this. If persistent, reduce `parallelAgentsPerWave` in config. |
| XMLA endpoint unavailable | Ensure Fabric capacity supports XMLA read/write (P1+ or F2+). |
| Agent stuck in IN_PROGRESS | Check `agent_logs` for errors. Use `--resume` to restart from last checkpoint. |
| Lakehouse table creation fails | Verify Lakehouse exists and service principal has Contributor access. |
| TMDL deployment fails | Validate TMDL files locally with Tabular Editor before deploying. |

## Capacity Planning

| Scale | Fabric SKU | Estimated Time | Notes |
|-------|-----------|---------------|-------|
| ≤50 tables, ≤10 reports | F2 | ~30 min | Dev/test |
| 50–200 tables, 10–50 reports | F4 | ~2 hours | Small production |
| 200–1,000 tables, 50–200 reports | F8+ | ~6 hours | Medium enterprise |
| 1,000+ tables, 200+ reports | F16+ | ~12+ hours | Large enterprise (multi-wave) |

---

## Related Docs

- [Migration Playbook](../MIGRATION_PLAYBOOK.md) — Step-by-step production migration guide
- [Security](security.md) — Credential management and data handling
- [Runbook: Scale Fabric Capacity](runbooks/06_scale_fabric_capacity.md) — Scaling during migration
- [Runbook: Diagnose Failed Agent](runbooks/02_diagnose_failed_agent.md) — Troubleshooting agent failures
