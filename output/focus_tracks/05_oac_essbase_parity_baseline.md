# OAC on Essbase Parity Baseline (Draft)

Date: 2026-06-01
Status: Baseline captured - pending dashboard names

## Goal

Define the parity control set for Track C so OAC-on-Essbase dashboards can be validated consistently after migration to Fabric and Power BI.

## Priority Dashboard Buckets

### Wave 1 Candidates

1. P&L dashboard
2. Budget vs Forecast dashboard
3. Entity performance dashboard
4. Scenario variance dashboard

### Wave 2 Candidates

1. Product mix dashboard
2. Currency exposure dashboard
3. Planning operations dashboard

## Mandatory Parity Controls

1. Totals parity by Scenario, Period, Entity
2. Hierarchy roll-up parity
3. Filter and prompt parity
4. Security and RLS parity
5. Writeback-connected workflow continuity

## Accepted Delta Rubric

### Allowed

1. Visual style differences that do not change meaning
2. Minor layout changes due to Power BI visual model
3. Equivalent slicer behavior with different UI rendering

### Not Allowed

1. Totals mismatch on financial measures
2. Broken hierarchy expansion logic
3. Missing security filter behavior
4. Missing Scenario/Period prompts
5. Writeback workflow breakage

## Dashboard Baseline Template

| Dashboard | Cube | Owner | Must-Match Measures | Must-Match Filters | Security Role | Status |
|---|---|---|---|---|---|---|
| Draft P&L | BSO Finance | TBD | Revenue, COGS, EBITDA | Scenario, Period, Entity | Finance Reader | Draft |
| Draft Budget vs Forecast | BSO Finance | TBD | Budget, Forecast, Variance | Scenario, Year | Planner | Draft |

## Exit Condition for Track C1

At least 3 top dashboards are named with owners and parity controls before report conversion begins.
