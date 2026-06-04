# Roadmap Execution Board (Sprint 1)

Window: 2026-06-01 to 2026-06-12

Reference roadmap: docs/ROADMAP_NEXT.md

## Status Summary (2026-06-04)

1. Completed: A1, A3, B1, B2, C1, C2, C3, V1.
2. In Review: A2, D1, D2.
3. Pending Approval: B3.
4. Main active risk: Exadata scope is still generic until real dashboard ownership is confirmed.
5. No new delivery changes since June 2; remaining items are still approval driven.

## Sprint Goal

Start active delivery for the 3 priority migration tracks and establish objective pass/fail gates.

## Work Board

| ID | Week | Track | Deliverable | Owner | Status | Gate |
|---|---|---|---|---|---|---|
| A1 | W1 | Essbase/Writeback | Run Track 1 commands and regenerate package | Essbase Lead | Done | Artifacts generated |
| A2 | W1 | Essbase/Writeback | Freeze writeback artifact contract v1 | Essbase Lead | In Review | Contract approved |
| A3 | W1 | Essbase/Writeback | UAT data pack definition (allocation + FX cases) | Validation Lead | Done | UAT pack approved |
| B1 | W1 | OAC on Exadata | Discovery run with scoped domains | Exadata Lead | Done | Inventory reviewed |
| B2 | W1 | OAC on Exadata | Plan run with wave review | Exadata Lead | Done | Plan accepted |
| C1 | W1 | OAC on Essbase | Define top dashboard parity baseline | OAC-on-Essbase Lead | Done | Baseline list approved |
| C2 | W1 | OAC on Essbase | Define parity controls (totals, filters, visuals, security) | OAC-on-Essbase Lead | Done | Control matrix published |
| C3 | W1 | OAC on Essbase | Publish accepted-delta rubric | OAC-on-Essbase Lead | Done | Signoff pack published |
| D1 | W2 | Platform 77 | Define MVP boundaries (upload/template/trigger/status) | Platform Lead | In Review | Scope frozen |
| D2 | W2 | Platform 84 | Define MVP boundaries (lineage/audit/labels) | Platform Lead | In Review | Scope frozen |
| V1 | W2 | Validation | First integrated pass/fail scorecard | Validation Lead | Done | Scorecard published |

## Daily Standup Template

1. Yesterday: what moved to Done
2. Today: top 1 deliverable per owner
3. Blockers: owner and mitigation
4. Gate risk: what may fail this week

## Weekly Gates

1. Test gate:

```powershell
pytest tests/ --tb=short -q
```

2. Track gate:

- Track 1: writeback package + UAT evidence
- Track 2: discover/plan artifacts and dashboard scope sign-off
- Track 3: parity baseline + control matrix + accepted-delta signoff pack

3. Review gate:

- Friday go/no-go with risks and carry-over items

## Dependencies

1. BSO outline inputs available for pilot cubes
2. OAC credentials and domain scope approved
3. Named owners assigned for A/B/C/D workstreams

## Definition of Done (Sprint 1)

1. Writeback contract approved and referenced by Track 1 outputs
2. Track 2 discover and plan runs completed for scoped domains
3. Track 3 parity baseline captured for top dashboards
4. Phase 77 and Phase 84 MVP boundaries documented
5. Integrated scorecard published
