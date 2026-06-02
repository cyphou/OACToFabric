# OAC on Essbase Parity Control Matrix

Date: 2026-06-01
Status: Review ready

## Purpose

Define the review controls that must pass before OAC-on-Essbase dashboards are accepted as migrated to Fabric and Power BI.

## Control Matrix

| Control ID | Category | What Must Match | Validation Method | Severity if Failed | Owner |
|---|---|---|---|---|---|
| C-TOT-01 | Totals | Revenue, COGS, EBITDA totals by Scenario/Period/Entity | Side-by-side query extracts | Critical | Validation Lead |
| C-TOT-02 | Totals | Budget, Forecast, Variance measures | Side-by-side query extracts | Critical | Validation Lead |
| C-HIER-01 | Hierarchy | Parent/child rollups by Entity | Hierarchy drill comparison | Critical | Semantic Lead |
| C-HIER-02 | Hierarchy | Scenario and Account drill path behavior | Drill interaction review | High | Semantic Lead |
| C-FILT-01 | Filters | Scenario, Period, Entity prompts | Prompt-to-slicer mapping review | Critical | Report Lead |
| C-FILT-02 | Filters | Default selections and reset behavior | Guided UAT steps | Medium | Report Lead |
| C-VIS-01 | Visuals | KPI value meaning and conditional state | Screenshot + value review | High | Report Lead |
| C-VIS-02 | Visuals | Table/matrix columns and sort order | Visual inspection + query support | Medium | Report Lead |
| C-SEC-01 | Security | Role visibility and row filtering | Role-based test execution | Critical | Security Lead |
| C-SEC-02 | Security | Restricted member suppression | Security regression check | Critical | Security Lead |
| C-WB-01 | Writeback | Longview/Smart View continuity assumptions | Workflow walkthrough | Critical | Essbase Lead |
| C-WB-02 | Writeback | Planning workflow dependent measures refresh correctly | UAT notebook + report refresh review | High | Essbase Lead |

## Dashboard Application Rules

1. Every Priority 1 dashboard must pass all Critical controls.
2. A dashboard may ship with at most 2 Medium accepted deltas.
3. Any High issue requires named approver sign-off before release.
4. Any Critical failure blocks migration sign-off.

## Evidence Pack Per Dashboard

1. Source screenshot or export
2. Target screenshot or PBIR render
3. Query extract for must-match measures
4. Filter/prompt behavior notes
5. Security test notes
6. Final sign-off decision

## Suggested First Dashboards

1. P&L dashboard
2. Budget vs Forecast dashboard
3. Entity performance dashboard
