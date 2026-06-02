# Phase 77 MVP Scope Freeze (Draft)

Date: 2026-06-01
Status: Draft - in review

## Objective

Deliver the minimum usable self-service migration portal without reopening platform architecture.

## In Scope

1. Project creation screen
2. File upload for source artifacts
3. Template selection for migration type
4. Trigger migration run
5. Status view with latest run state and outputs

## Out of Scope

1. Multi-org billing and metering
2. Public API key program
3. Deep project lifecycle features (clone/archive)
4. Rich admin console
5. Cross-tenant custom branding

## Acceptance Criteria

1. User can upload a supported source artifact.
2. User can choose a migration template.
3. User can trigger a run and see status updates.
4. User can download or open generated outputs.

## Engineering Notes

1. Reuse existing API and dashboard assets where possible.
2. Avoid adding new backend abstractions unless directly required by upload/template/run/status flow.
3. All new flows must preserve current CLI-first execution path.
