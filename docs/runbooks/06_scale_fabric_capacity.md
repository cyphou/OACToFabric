# Runbook: Scaling Fabric Capacity During Migration

## Overview

Large migrations (1000+ assets) may require temporarily scaling up Microsoft Fabric capacity to avoid throttling and improve throughput.

---

## When to Scale

| Signal | Action |
|---|---|
| Fabric API returns `429 Too Many Requests` frequently | Scale up |
| Pipeline deployments are queuing | Scale up |
| Migration takes > 4 hours for < 1000 assets | Scale up |
| Migration is complete | Scale back down |

---

## Capacity Tiers (Fabric)

| SKU | CUs | Best For |
|---|---|---|
| F2 | 2 | Development / testing |
| F4 | 4 | Small migrations (< 200 assets) |
| F8 | 8 | Medium migrations (200–1000 assets) |
| F16 | 16 | Large migrations (1000–5000 assets) |
| F32+ | 32+ | Very large migrations / parallel runs |

---

## Step-by-Step: Scale via Azure Portal

1. Navigate to **Azure Portal** → **Microsoft Fabric** → **Capacity**.
2. Select the capacity assigned to your migration workspace.
3. Click **Scale** → select the target SKU.
4. Wait for scaling to complete (typically 1–5 minutes).

---

## Step-by-Step: Scale via Bicep/CLI

The infrastructure code in `infra/main.bicep` supports capacity provisioning:

```bash
# Scale up to F16 for migration
az deployment group create \
  --resource-group rg-oac-migration \
  --template-file infra/main.bicep \
  --parameters fabricCapacitySku=F16

# Scale back to F4 after migration
az deployment group create \
  --resource-group rg-oac-migration \
  --template-file infra/main.bicep \
  --parameters fabricCapacitySku=F4
```

---

## Configuration for High Throughput

Adjust migration settings when running on higher capacity:

```toml
# config/prod.toml — high-capacity overrides
[orchestrator]
parallel_agents_per_wave = 5    # More parallel agents
max_items_per_wave = 200        # Larger wave batches

[llm]
max_retries = 5
token_budget_per_run = 2_000_000
```

---

## Cost Management

- **Scale up** only during active migration windows.
- **Scale down** immediately after the run completes.
- Use **Azure Cost Management** alerts to monitor spending.
- Consider **Fabric pause/resume** for dev/test capacities outside business hours.

---

## Monitoring During Scale

Monitor the migration dashboard (Phase 14) for:
- **Throughput**: Items migrated per minute.
- **Error rate**: Should decrease after scale-up.
- **API latency**: Should decrease after scale-up.
- **RU consumption**: Track Cosmos DB or Lakehouse usage.
