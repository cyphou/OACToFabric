# Agent 08: Orchestrator Agent — Technical Specification

## 1. Purpose

**Coordinate all migration agents**, manage execution dependencies, track progress, handle failures, and provide a unified migration dashboard.

## 2. Inputs

| Input | Source | Format |
|---|---|---|
| Migration scope definition | Project configuration | JSON |
| Wave plan | PROJECT_PLAN.md / config | JSON |
| Agent configurations | Environment / Key Vault | Config files |
| Agent status updates | Fabric Lakehouse `agent_tasks` | Delta table |

## 3. Outputs

| Output | Destination | Format |
|---|---|---|
| Agent task assignments | Fabric Lakehouse `agent_tasks` | Delta table |
| Migration dashboard data | Fabric Lakehouse `agent_logs` | Delta table |
| Status notifications | Email / Teams / Slack | Messages |
| Migration summary reports | Git repo / Blob Storage | Markdown |

## 4. Execution DAG (Directed Acyclic Graph)

```
                    ┌─────────────┐
                    │  START      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Agent 01   │
                    │  Discovery  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐    │     ┌──────▼──────┐
       │  Agent 02   │    │     │  Agent 04   │
       │  Schema     │    │     │  Semantic   │ (can start from inventory)
       └──────┬──────┘    │     └──────┬──────┘
              │            │            │
       ┌──────▼──────┐    │     ┌──────▼──────┐
       │  Agent 03   │    │     │  Agent 05   │
       │  ETL        │    │     │  Reports    │
       └──────┬──────┘    │     └──────┬──────┘
              │            │            │
              │     ┌──────▼──────┐     │
              │     │  Agent 06   │     │
              │     │  Security   │     │
              │     └──────┬──────┘     │
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │  Agent 07   │
                    │  Validation │  (runs after each wave + final)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    END      │
                    └─────────────┘
```

### Dependency Rules

| Agent | Depends On | Can Run In Parallel With |
|---|---|---|
| 01 Discovery | — | — |
| 02 Schema | 01 | 04 (partially) |
| 03 ETL | 01, 02 | 04, 05 |
| 04 Semantic | 01 | 02, 03 |
| 05 Reports | 01, 04 | 03, 06 |
| 06 Security | 01, 04 | 03, 05 |
| 07 Validation | Depends on wave (runs after each completed wave) | — |

## 5. Core Logic

### 5.1 Orchestration Flow

```python
class OrchestratorAgent:
    """
    Central coordination agent that manages migration execution.
    """
    
    async def run_migration(self, scope: MigrationScope):
        # Phase 0: Initialize
        await self.initialize_lakehouse()
        await self.register_agents()
        
        # Phase 1: Discovery
        await self.execute_agent("01-discovery", scope)
        inventory = await self.get_inventory()
        
        # Phase 2: Plan waves based on inventory
        waves = self.plan_waves(inventory)
        
        for wave in waves:
            # Execute wave with dependency resolution
            await self.execute_wave(wave)
            
            # Validate after each wave
            await self.execute_agent("07-validation", wave.scope)
            
            # Check validation results
            if not await self.wave_passed_validation(wave):
                await self.handle_wave_failure(wave)
                continue
            
            await self.notify_stakeholders(f"Wave {wave.id} complete")
        
        # Final validation
        await self.execute_agent("07-validation", scope)
        await self.generate_final_report()
    
    async def execute_wave(self, wave: MigrationWave):
        """Execute agents in a wave respecting dependencies."""
        dag = self.build_dag(wave.agents)
        
        for batch in dag.topological_batches():
            # Run independent agents in parallel
            tasks = [self.execute_agent(agent, wave.scope) for agent in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle failures
            for agent, result in zip(batch, results):
                if isinstance(result, Exception):
                    await self.handle_agent_failure(agent, result, wave)
    
    async def handle_agent_failure(self, agent_id, error, wave):
        """Handle agent execution failure."""
        # Log failure
        await self.log_event(agent_id, "FAILED", str(error))
        
        # Check retry policy
        retry_count = await self.get_retry_count(agent_id, wave.id)
        if retry_count < self.max_retries:
            await self.schedule_retry(agent_id, wave, delay=2**retry_count * 60)
        else:
            # Escalate
            await self.notify_stakeholders(
                f"Agent {agent_id} failed after {self.max_retries} retries in Wave {wave.id}",
                severity="HIGH"
            )
            # Check if wave can continue without this agent
            if self.is_blocking(agent_id, wave):
                await self.pause_wave(wave)
```

### 5.2 Task State Machine

```
PENDING → ASSIGNED → IN_PROGRESS → VALIDATING → COMPLETED
                         │                           │
                         └──► FAILED ──► RETRYING ───┘
                                │
                                └──► BLOCKED (manual intervention needed)
```

### 5.3 Lakehouse Task Row Schema

```json
{
  "id": "task_wave1_agent02_table_sales",
  "agentId": "02-schema-migration",
  "waveId": "wave1",
  "taskType": "migrate_table",
  "status": "completed",
  "asset": {
    "type": "table",
    "sourceName": "SALES",
    "targetName": "Sales"
  },
  "startedAt": "2026-03-01T10:00:00Z",
  "completedAt": "2026-03-01T10:05:30Z",
  "duration_ms": 330000,
  "retryCount": 0,
  "result": {
    "rowsMigrated": 1500000,
    "validationStatus": "PASS"
  },
  "assignedBy": "orchestrator",
  "lastUpdated": "2026-03-01T10:05:30Z"
}
```

## 6. Monitoring & Dashboards

### 6.1 Key Metrics

| Metric | Source | Update Frequency |
|---|---|---|
| Total assets discovered | `migration-inventory` count | After discovery |
| Assets migrated (by type) | `agent-tasks` where status=completed | Real-time |
| Assets failed (by type) | `agent-tasks` where status=failed | Real-time |
| Validation pass rate | `validation-results` pass/total | After each validation run |
| Migration progress % | completed / total tasks | Real-time |
| Agent health | `agent-logs` heartbeats | Every 60 seconds |
| Average migration time per asset | `agent-tasks` duration aggregation | Hourly |

### 6.2 Notification Rules

| Event | Channel | Recipients |
|---|---|---|
| Wave started | Teams + Email | Project team |
| Wave completed (success) | Teams + Email | Project team + stakeholders |
| Agent failure (first) | Teams | Dev team |
| Agent failure (max retries) | Teams + Email + PagerDuty | Dev team + PM |
| Validation failure rate > 10% | Teams + Email | Dev team + PM |
| Migration complete | Email | All stakeholders |

## 7. Configuration

```json
{
  "orchestrator": {
    "maxRetries": 3,
    "retryBackoffSeconds": [60, 300, 900],
    "heartbeatIntervalSeconds": 60,
    "validationAfterEachWave": true,
    "autoAdvanceWaves": false,
    "parallelAgentsPerWave": 3,
    "notificationChannels": ["teams", "email"],
    "lakehouseId": "<lakehouse-guid>",
    "agents": {
      "01-discovery": { "enabled": true, "priority": 1 },
      "02-schema": { "enabled": true, "priority": 2 },
      "03-etl": { "enabled": true, "priority": 3 },
      "04-semantic": { "enabled": true, "priority": 2 },
      "05-reports": { "enabled": true, "priority": 3 },
      "06-security": { "enabled": true, "priority": 3 },
      "07-validation": { "enabled": true, "priority": 4 }
    }
  }
}
```

## 8. Error Handling

| Error | Handling |
|---|---|
| Agent not responding (heartbeat miss) | Alert after 3 missed heartbeats; restart agent |
| Lakehouse unavailable | Local queue + retry; alert platform team |
| Circular dependency detected | Log error, halt wave, notify architect |
| All retries exhausted | Mark task as BLOCKED, pause dependent tasks, notify PM |
| Capacity throttling (Fabric) | Back off, reduce parallelism, schedule for off-peak |

## 9. Testing Strategy

| Test Type | Approach |
|---|---|
| Unit | DAG resolution, dependency ordering |
| Integration | Run mini-migration (1 table, 1 report) end-to-end |
| Failure injection | Simulate agent failures, verify retry and escalation |
| Load | Run with large inventory, verify parallelism and throughput |
