# Runbook: Diagnosing a Failed Agent

## Symptoms

- Migration summary shows `failed` status for an agent.
- Notification log contains `WARN` or `HIGH` severity entries.
- Agent retry count reached maximum (`max_retries` in config).

---

## Step 1: Identify the Failure

Check the migration summary:

```bash
cat output/run_001/migration_summary.md
```

Look for rows with `failed` status:

| Agent | Status | Duration (s) | Retries | Error |
|---|---|---|---|---|
| 02-schema | failed | 12.3 | 3 | ConnectionError: Oracle DB unreachable |

---

## Step 2: Check Notification Log

```bash
cat output/run_001/notification_log.md
```

Look for:
- `agent_failed_first` — First failure with retry info.
- `agent_failed_max` — Final failure after all retries.
- `migration_halted` — If the failure blocked the entire run.

---

## Step 3: Check Agent Logs

Increase log verbosity and re-run the specific agent:

```bash
# Run only the failing agent with debug logging
OAC_LOG_LEVEL=DEBUG oac-migrate migrate --config config/migration.toml --wave 1 --verbose
```

Structured log fields include:
- `agent_id` — Which agent produced the log.
- `run_id` / `span_id` — Correlation IDs for tracing.
- `duration_ms` — How long each operation took.

---

## Step 4: Common Failure Patterns

### Connection Failures (`ConnectionError`, `TimeoutError`)

| Symptom | Cause | Fix |
|---|---|---|
| Oracle DB unreachable | Network / firewall | Verify VPN, firewall rules, Oracle listener status |
| Fabric API 401 | Expired credentials | Refresh service principal token, check `FABRIC_CLIENT_SECRET` |
| OAC API 403 | Insufficient permissions | Verify IDCS app role grants |

### Data Mapping Failures (`ValueError`, `KeyError`)

| Symptom | Cause | Fix |
|---|---|---|
| Unknown Oracle data type | Unmapped type in `type_mapper.py` | Add mapping to `ORACLE_TO_DELTA_MAP` |
| Expression translation failed | Unsupported OAC expression syntax | Check `expression_translator.py` rules, enable LLM fallback |

### Rate Limiting (`429 Too Many Requests`)

| Symptom | Cause | Fix |
|---|---|---|
| Fabric API 429 | Too many concurrent calls | Reduce `parallel_agents_per_wave`, increase retry backoff |
| OAC API 429 | Request quota exceeded | Add delay between discovery pages |

---

## Step 5: Retry the Failed Agent

Option A — Resume full migration (skips completed agents):
```bash
oac-migrate migrate --config config/migration.toml --resume --output-dir output/run_001
```

Option B — Re-run single wave:
```bash
oac-migrate migrate --config config/migration.toml --wave 2 --output-dir output/run_001
```

---

## Step 6: Escalation

If retries fail:
1. Capture the full log output (`output/run_001/` directory).
2. Capture Application Insights trace (filter by `run_id`).
3. Raise a ticket with the migration team including:
   - Agent ID and wave number.
   - Error message and stack trace.
   - Steps already attempted.
