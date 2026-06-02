# OAC on Essbase Accepted-Delta Signoff Pack

Date: 2026-06-01
Status: Review ready

## Purpose

Provide a consistent signoff rubric for differences that are acceptable after migration, and clearly block unacceptable regressions.

## Decision Table

| Delta Type | Example | Allowed | Approval Needed | Notes |
|---|---|---|---|---|
| Visual restyling | Different font, border, or spacing | Yes | No | Meaning must stay identical |
| Layout shift | Visual moved on page but still discoverable | Yes | Yes | Business owner approval required if workflow changes |
| Slicer UI difference | Dropdown vs tile slicer | Yes | No | Same logical filtering required |
| Minor sort difference | Secondary sort differs but totals unchanged | Yes | Yes | Must be documented in review notes |
| Totals mismatch | Revenue or EBITDA differs | No | N/A | Automatic blocker |
| Missing filter | Scenario or Period selection unavailable | No | N/A | Automatic blocker |
| Security drift | User sees forbidden members | No | N/A | Automatic blocker |
| Hierarchy drift | Parent rollup differs from source | No | N/A | Automatic blocker |
| Writeback break | Planning workflow cannot complete | No | N/A | Automatic blocker |

## Signoff Workflow

1. Reviewer records each detected delta.
2. Reviewer classifies it using the decision table.
3. Business owner approves any allowed delta that changes interaction flow.
4. Validation lead signs off only if no blocker remains.

## Signoff Record Template

| Dashboard | Delta ID | Delta Summary | Classification | Approved By | Decision |
|---|---|---|---|---|---|
| Draft P&L | D-001 | Slicer rendered as dropdown instead of prompt bar | Allowed | TBD | Pending |
| Draft Budget vs Forecast | D-002 | Variance total mismatch | Blocker | N/A | Rejected |

## Release Rule

No dashboard enters signoff complete state with any blocker unresolved.
