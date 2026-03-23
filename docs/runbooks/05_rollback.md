# Runbook: Performing a Rollback

## When to Rollback

- Validation agent reports critical data quality failures.
- Migrated artifacts are incorrect or incomplete.
- Business decision to revert to OAC while issues are fixed.

---

## Rollback Scope

| Layer | Rollback Action | Difficulty |
|---|---|---|
| **Fabric Lakehouse tables** | Drop/truncate migrated Delta tables | Easy |
| **Fabric Data Pipelines** | Delete deployed pipelines via API | Easy |
| **Power BI Semantic Models** | Delete/overwrite via XMLA/REST API | Medium |
| **Power BI Reports** | Delete deployed reports | Medium |
| **Security (RLS/OLS)** | Remove RLS roles from semantic models | Easy |
| **OAC configuration** | No changes needed — source is read-only | N/A |

---

## Step-by-Step Rollback

### 1. Stop the Current Migration

```bash
# If migration is running — send SIGINT for graceful shutdown
Ctrl+C

# The orchestrator persists state to checkpoint file before exiting
```

### 2. Identify What Was Deployed

Check the migration summary:

```bash
cat output/run_001/migration_summary.md
```

The DAG status section shows which agents completed successfully — those are the layers with deployed artifacts.

### 3. Rollback Per Layer

#### Fabric Tables (Agent 02 — Schema)

```python
# Using Fabric client
from src.clients.fabric_client import FabricClient
client = FabricClient(workspace_id="...", credential=...)

# List and delete migrated tables
for table in migrated_tables:
    await client.delete_table(table.name)
```

#### Data Pipelines (Agent 03 — ETL)

```python
from src.deployers.fabric_deployer import FabricDeployer
deployer = FabricDeployer(client)
await deployer.delete_pipeline("pipeline_name")
```

#### Semantic Models (Agent 04 — Semantic)

```python
from src.deployers.pbi_deployer import PBIDeployer
deployer = PBIDeployer(client)
await deployer.delete_dataset("dataset_id")
```

#### Reports (Agent 05 — Reports)

```python
await deployer.delete_report("report_id")
```

### 4. Clean Up Coordination State

If you want to re-run the migration from scratch:

```bash
# Delete the checkpoint file
rm output/run_001/.checkpoint.json

# Optionally clear the Lakehouse coordination tables
# (agent_tasks, validation_results)
```

### 5. Verify Rollback

```bash
# Re-run validation against an empty target
oac-migrate validate --config config/migration.toml --output-dir output/run_001
```

---

## Partial Rollback

To rollback only specific waves or agents:

```bash
# Rollback wave 3 only
oac-migrate rollback --wave 3 --output-dir output/run_001

# Rollback specific agent
oac-migrate rollback --agent 05-reports --output-dir output/run_001
```

*Note: Partial rollback may leave dependencies in an inconsistent state. Always validate after rollback.*

---

## Recovery After Rollback

1. Fix the root cause (check runbook 02 for diagnosis).
2. Update configuration if needed.
3. Re-run migration:
   ```bash
   oac-migrate migrate --config config/migration.toml --output-dir output/run_002
   ```

---

## Data Safety

- **OAC is read-only**: The migration framework never writes to OAC. Rolling back only cleans Fabric/PBI targets.
- **Delta tables have time travel**: If tables were overwritten rather than created, use Delta time travel to restore previous versions:
  ```sql
  RESTORE TABLE my_table TO VERSION AS OF 5
  ```
