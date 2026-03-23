# ADR-001: Fabric Lakehouse as Coordination Store

## Status

**Accepted** — 2025-01

## Context

The multi-agent migration architecture needs a shared coordination store for:
- Task queues (agent assignments, status tracking)
- Migration inventory (discovered assets)
- Mapping rules (OAC → Fabric/PBI translations)
- Validation results (test outcomes, reconciliation data)
- Agent logs (structured diagnostics)

Options considered:
1. **Azure Cosmos DB** — NoSQL, global distribution, strong consistency mode.
2. **Azure SQL Database** — Relational, familiar, transactional.
3. **Fabric Lakehouse (Delta tables)** — Native Fabric integration, Delta format.
4. **Redis/Azure Cache** — In-memory, fast, but volatile.

## Decision

Use **Fabric Lakehouse with Delta tables** as the coordination store.

## Rationale

- **All-in-Fabric**: No additional Azure service to provision, manage, or pay for. The coordination data lives alongside the migrated data itself.
- **ACID transactions**: Delta Lake provides ACID guarantees, schema enforcement, and time travel.
- **Efficient I/O**: Agents connect via the Lakehouse SQL endpoint for reads or Delta Lake API (PySpark) for writes.
- **Cost**: Included in Fabric capacity — no separate billing.
- **Observability**: Delta tables are queryable from Power BI for the migration dashboard.

## Consequences

- Agents must use PySpark or the SQL endpoint to interact with coordination tables.
- Write throughput is lower than dedicated databases (acceptable for coordination traffic).
- Local development requires either a Fabric workspace or a mock Lakehouse client.
- Time travel enables audit trail without custom implementation.

## Alternatives Rejected

- **Cosmos DB**: Excellent performance but adds cost and operational complexity for a service that only runs during migration.
- **Azure SQL**: Capable but requires separate provisioning and doesn't integrate natively with Fabric analytics.
- **Redis**: Too volatile for migration state that must survive restarts.
