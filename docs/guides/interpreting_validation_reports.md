# User Guide: Interpreting Validation Reports

The Validation Agent (Agent 07) produces reports that verify migration correctness across all layers. This guide explains how to read and act on validation results.

---

## Report Location

After running validation:

```bash
oac-migrate validate --config config/migration.toml --output-dir output/run_001
```

The report is saved to `output/run_001/validation_report.md`.

---

## Report Structure

### 1. Summary Section

```
## Validation Summary

| Metric           | Value |
|-----------------|-------|
| Total Checks    | 150   |
| Passed          | 142   |
| Failed          | 5     |
| Warnings        | 3     |
| Pass Rate       | 94.7% |
```

**Target**: ≥ 95% pass rate for production sign-off.

### 2. Data Reconciliation

Compares source (Oracle/OAC) data with target (Fabric Lakehouse):

```
## Data Reconciliation

| Table          | Source Rows | Target Rows | Match | Status  |
|---------------|------------|------------|-------|---------|
| DIM_PRODUCT   | 10,000     | 10,000     | ✅    | PASS    |
| FACT_SALES    | 1,234,567  | 1,234,560  | ❌    | FAIL    |
| DIM_DATE      | 3,652      | 3,652      | ✅    | PASS    |
```

**How to interpret**:
- **PASS**: Row counts match exactly.
- **FAIL**: Row count mismatch — investigate missing or duplicate rows.
- **WARN**: Minor variance (< 0.1%) that may be acceptable (e.g., in-flight data).

**Action on FAIL**: Run the data reconciliation query to identify missing rows:
```sql
-- Find rows in source but not in target
SELECT source.id FROM source_table source
LEFT JOIN target_table target ON source.id = target.id
WHERE target.id IS NULL
```

### 3. Schema Validation

Verifies column names, data types, and constraints:

```
## Schema Validation

| Table       | Column      | Source Type   | Target Type | Status |
|------------|-------------|--------------|-------------|--------|
| DIM_PRODUCT | PRODUCT_ID  | NUMBER(10)   | INT         | PASS   |
| DIM_PRODUCT | NAME        | VARCHAR2(100)| STRING      | PASS   |
| FACT_SALES  | AMOUNT      | NUMBER(15,2) | DECIMAL     | PASS   |
| FACT_SALES  | FLAG        | CHAR(1)      | STRING      | WARN   |
```

**WARN on type mapping**: Some Oracle types map to broader Fabric types (e.g., `CHAR(1)` → `STRING`). This is expected but worth noting.

### 4. Expression Translation Validation

Checks that translated DAX/PySpark expressions produce correct results:

```
## Expression Validation

| Expression                  | Method | Syntax Valid | Semantic Valid | Status |
|---------------------------|--------|--------------|----------------|--------|
| SUM(Sales.Amount)          | Rule   | ✅           | ✅             | PASS   |
| CASE WHEN status='A'...    | LLM    | ✅           | ✅             | PASS   |
| DECODE(type, 'X', 1, 0)   | LLM    | ✅           | ⚠️             | WARN   |
| CUSTOM_AGG(col1, col2)     | None   | —            | —              | FAIL   |
```

**Statuses**:
- **PASS**: Expression translates and validates correctly.
- **WARN**: Syntax is valid but semantic equivalence couldn't be verified.
- **FAIL**: No translation available — requires manual translation.

### 5. Security Validation

Verifies RLS/OLS rules:

```
## Security Validation

| Role              | Source Filter        | Target RLS (DAX)        | Status |
|------------------|---------------------|-----------------------|--------|
| Regional_Manager  | USER().REGION='US'  | [Region] = USERPRINCIPALNAME() | PASS |
| Finance_Reader    | DEPT='FIN'          | [Department] = "FIN"  | PASS   |
```

### 6. Report Visual Validation

Lists migrated visuals and their mapping status:

```
## Report Validation

| Source Analysis    | Visuals | Mapped | Unmapped | Status |
|-------------------|---------|--------|----------|--------|
| Sales Dashboard   | 12      | 12     | 0        | PASS   |
| Finance Report    | 8       | 7      | 1        | WARN   |
```

---

## Acting on Results

### FAIL — Must Fix

1. Identify the specific check that failed.
2. Consult the relevant runbook:
   - Data issues → Re-run ETL agent
   - Translation issues → [Runbook: LLM Translation Failures](../runbooks/04_llm_translation_failures.md)
   - Security issues → Check RLS definitions
3. Fix and re-validate.

### WARN — Review Required

1. Determine if the warning is acceptable for your use case.
2. Document accepted warnings with justification.
3. Add to the validation exceptions list if appropriate.

### Acceptance Criteria

For production sign-off:
- **Data reconciliation**: 100% row count match on all tables.
- **Schema**: All columns mapped with correct types.
- **Expressions**: ≥ 90% translated (remainder documented for manual translation).
- **Security**: 100% RLS roles migrated and tested.
- **Reports**: All critical dashboards migrated with visual parity.
