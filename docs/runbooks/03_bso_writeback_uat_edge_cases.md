# BSO Writeback UAT Edge-Case Pack (v1)

Date: 2026-06-01
Scope: Track A (Essbase and Writeback)

## Goal

Validate that Fabric writeback behavior matches required BSO planning semantics for high-risk scenarios.

## Dataset Matrix

1. Baseline budget rows (normal values)
2. Null and missing values
3. Negative values and reversals
4. Large precision values (decimal stress)
5. Multi-entity allocation cases
6. Multi-currency conversion cases
7. Concurrent update simulation rows

## Test Cases

### WB-01: Round-trip write and read

- Input: 10 baseline rows
- Expectation: values persisted and query returns exact match

### WB-02: Idempotent merge behavior

- Input: resend identical payload
- Expectation: no duplicate logical records

### WB-03: Allocation distribution integrity

- Input: one driver row allocated to N entities
- Expectation: sum(children) equals parent source amount

### WB-04: Currency conversion parity

- Input: same amount across two currencies with known FX rates
- Expectation: converted totals match expected precision rules

### WB-05: Scenario/Period overwrite rules

- Input: same dimensional key with revised amount
- Expectation: merge updates target row correctly

### WB-06: Validation procedure rejection

- Input: invalid dimensional combinations
- Expectation: validation procedure returns deterministic error output

### WB-07: Audit trail completeness

- Input: insert + update sequence
- Expectation: audit table contains both events with required metadata

### WB-08: Concurrent writer conflict handling

- Input: simulated near-simultaneous updates on same key
- Expectation: deterministic final state and no corruption

## Pass Criteria

1. 100% pass on WB-01..WB-08
2. No critical data-quality issues
3. No credential leakage in artifacts/logs
4. Cutover checklist pre-conditions satisfied

## Evidence to Collect

1. SQL result extracts for each case
2. Notebook execution logs
3. Procedure execution output logs
4. Audit table sample rows
5. Final summary in output/etl/bso_writeback_prep/PREP_SUMMARY.md

## Mapping to Existing Assets

1. UAT notebook: output/etl/bso_writeback_prep/uat_notebook.py
2. Validation procedures: output/etl/bso_writeback_prep/stored_procedures.sql
3. Contract baseline: docs/runbooks/02_bso_writeback_artifact_contract.md
