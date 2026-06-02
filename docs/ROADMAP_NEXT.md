# Next Roadmap (June-August 2026)

Status date: 2026-06-02

## Progress Snapshot (2026-06-02)

Completed in Sprint 1 so far:

1. Track A execution package generated, snapshotted, and validated (focused tests passed).
2. Track B discovery and planning run completed (`output/focus_oac_exadata`).
3. Track C baseline, parity control matrix, and accepted-delta signoff pack published.
4. Phase 77 and Phase 84 MVP scopes drafted and moved to review.
5. Integrated scorecard published for execution monitoring.

Open review items:

1. A2 approval: writeback artifact contract freeze.
2. B3 approval: named Exadata dashboard priority list.
3. D1/D2 approval: Phase 77 and Phase 84 scope freeze.

## Objective

Deliver production-ready migration execution for:

1. Essbase migration with BSO writeback replacement
2. OAC reporting on Exadata
3. OAC reporting on Essbase

In parallel, close remaining platform milestones:

- Phase 77: Self-Service Migration Portal
- Phase 82: Multi-Region and Disaster Recovery
- Phase 84: Compliance and Audit Automation
- Phase 85: v9.0 GA release package

## Strategic Priorities

1. Execution-first: complete migration tracks with customer-usable runbooks and validated outputs.
2. Risk-first: treat writeback correctness, report parity, and security parity as release gates.
3. GA-first: time-box platform backlog to unblock v9.0 GA.

## Timeline (12 Weeks)

### Wave 1 (Weeks 1-4): Essbase and Writeback Hardening

Targets:

- Complete Track 1 execution and UAT evidence
- Freeze BSO writeback artifact schema for pilot use
- Close high-risk calc translation gaps

Deliverables:

- Stable writeback package under output/etl/bso_writeback_prep
- Pilot UAT evidence for writeback round-trip and allocations
- Gap log for low-confidence translations (<0.7) with owner per item

Exit criteria:

- All Track 1 exit criteria met
- No critical issues in writeback UAT

### Wave 2 (Weeks 5-8): OAC on Exadata and OAC on Essbase

Targets:

- Execute Track 2 runbook end-to-end on priority domains
- Execute Track 3 parity validation for top business dashboards
- Lock report and security parity scorecards

Deliverables:

- output/focus_oac_exadata migration outputs and validation report
- OAC-on-Essbase parity matrix (totals, filters, visuals)
- Security parity validation report (RLS and role mappings)

Exit criteria:

- No critical mismatches in validation reports
- Priority dashboard set signed off by business owners

### Wave 3 (Weeks 9-12): GA Readiness and Platform Closure

Targets:

- Deliver minimum viable Phase 77 portal flow
- Implement Phase 82 disaster recovery baseline
- Implement Phase 84 audit/compliance automation baseline
- Package Phase 85 release notes and GA checklist

Deliverables:

- Phase 77 MVP: upload, template selection, migration trigger, status view
- Phase 82 runbook: failover simulation and recovery verification
- Phase 84 controls: lineage export, audit trail checks, sensitivity label checks
- Phase 85 GA dossier: release checklist, upgrade notes, known limitations

Exit criteria:

- Phase 77/82/84 marked feature-complete (MVP scope)
- GA decision meeting package ready

## Workstreams

### Workstream A: Essbase and Writeback

Scope:

- Connector and semantic bridge stability
- Writeback backend replacement for Longview/Smart View workflows

Key outputs:

- Warehouse DDL, stored procedures, calc notebooks, pipeline, TDS config
- UAT notebook and cutover checklist

Primary risks:

- Allocation logic regressions
- Currency conversion parity

Mitigation:

- Expand targeted tests for allocation and FX cases
- Enforce UAT data packs covering edge scenarios

### Workstream B: OAC Reports on Exadata

Scope:

- Discovery, schema, ETL, semantic, report conversion

Key outputs:

- Migration artifacts for priority Exadata-backed subject areas
- Validation report with data and report parity outcomes

Primary risks:

- SQL translation edge cases
- Data type and precision drift

Mitigation:

- Preflight SQL compatibility checks
- Precision-focused reconciliation checks

### Workstream C: OAC on Essbase

Scope:

- OAC dashboard/report conversion dependent on Essbase-derived semantics
- Security mapping and parity validation

Key outputs:

- Report parity matrix and accepted deltas
- Security/RLS equivalence validation

Primary risks:

- Complex calc semantics divergence
- Hierarchy and aggregation mismatches

Mitigation:

- Low-confidence calc triage board
- Totals parity checkpoints by Scenario/Period/Entity

### Workstream D: Platform Closure to v9.0 GA

Scope:

- Phase 77, 82, 84, 85 completion

Key outputs:

- Portal MVP, DR baseline, compliance baseline, GA package

Primary risks:

- Scope creep in portal and compliance layers
- Late-stage integration defects

Mitigation:

- Strict MVP scope lock per phase
- Weekly stabilization gate with regression suite

## Weekly Execution Cadence

1. Monday: planning and risk review
2. Wednesday: parity and quality checkpoint
3. Friday: demo plus go/no-go gate

Mandatory gates each week:

- Full test run: pytest tests/ --tb=short -q
- Track-level artifact review
- Updated risk and blocker log

## Recommended Ownership Model

1. Track lead: Essbase and Writeback
2. Track lead: OAC on Exadata
3. Track lead: OAC on Essbase
4. Platform lead: Phases 77/82/84/85
5. Validation lead: parity and release gates

## Immediate Next 10 Working Days (Updated)

1. Finalize A2 by approving `docs/runbooks/02_bso_writeback_artifact_contract.md`.
2. Finalize B3 by replacing draft dashboard names with real owners and OAC paths.
3. Finalize D1 and D2 scope freeze decisions in Phase 77/84 MVP docs.
4. Convert Track C draft dashboard placeholders into named signoff candidates.
5. Run full regression gate and publish a refreshed scorecard with approval status.

## Related Plans

- output/focus_tracks/01_essbase_core_plan.md
- output/focus_tracks/02_oac_on_exadata_plan.md
- output/focus_tracks/03_oac_on_essbase_plan.md
- output/focus_tracks/command_book.md
- output/focus_tracks/readiness_checklist.md
- output/focus_tracks/integrated_scorecard_2026-06-01.md
- output/focus_tracks/integrated_scorecard_2026-06-02.md
