# ADR-003: Multi-Agent Architecture with DAG-Based Orchestration

## Status

**Accepted** — 2025-01

## Context

An OAC-to-Fabric migration involves multiple independent but interdependent workstreams: schema migration, ETL conversion, semantic model translation, report generation, security mapping, and validation. These can be organized as:

1. **Monolithic script**: One program does everything sequentially.
2. **Pipeline stages**: Linear pipeline with handoffs.
3. **Multi-agent with DAG orchestration**: Specialized agents with dependency-aware execution.

## Decision

Use **8 specialized agents** coordinated by a **DAG-based orchestrator**.

## Rationale

- **Separation of concerns**: Each agent is an expert in one domain (schema, ETL, semantic model, etc.) with its own codebase, tests, and configuration.
- **Parallel execution**: DAG-based scheduling allows independent agents to run concurrently (e.g., Schema and Semantic agents after Discovery).
- **Fault isolation**: A failure in the Report agent doesn't affect the Schema agent.
- **Retry semantics**: Per-agent retry with exponential backoff; failed agents don't block independent peers.
- **Testability**: Each agent can be tested in isolation with mock inputs.
- **Extensibility**: New agents can be added by registering in the DAG.

## Agent Dependency Graph

```
01-discovery → 02-schema  → 03-etl
01-discovery → 04-semantic → 05-reports
                04-semantic → 06-security
01..06       → 07-validation
```

## Consequences

- More complex than a simple script, but justified by the breadth of migration tasks.
- Requires a coordination store (Fabric Lakehouse — see ADR-001).
- Agents communicate via the shared store, not direct method calls.
- The orchestrator must handle wave planning, retry, blocking, and notification.

## Alternatives Rejected

- **Monolithic**: Too fragile for 7+ migration domains. A failure anywhere stops everything.
- **Linear pipeline**: Misses parallelism opportunities (e.g., Schema and Semantic can run concurrently).
