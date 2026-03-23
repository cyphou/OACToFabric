# Agent 07: Validation & Testing Agent — Technical Specification

## 1. Purpose

Provide **end-to-end validation** across all migration layers — data, semantic model, reports, and security — to ensure functional equivalence between OAC and Fabric/Power BI.

## 1.1 File Ownership

| File | Purpose |
|------|--------|
| `src/agents/validation/validation_agent.py` | ValidationAgent class — cross-layer validation |
| `src/agents/validation/data_reconciliation.py` | Row count, checksum, sample data QA |
| `src/agents/validation/semantic_validator.py` | Validate semantic model: measures, hierarchies |
| `src/agents/validation/report_validator.py` | Visual comparison, slicer tests, bookmarks |
| `src/agents/validation/security_validator.py` | RLS testing, user-level access verification |
| `src/validation/` | Shared validation utilities |
| `tests/` | All test files (co-owned — cross-cutting) |

## 1.2 Constraints

- Do NOT modify source extraction, generation, or deployment logic
- Only produces validation reports and test results
- Cross-cutting: reads all source files for verification but writes only to validation outputs and `tests/`
- Performance benchmarks must include both warm-cache and cold-cache measurements
- Visual comparison screenshots must be stored in Blob Storage, not in Git

## 1.3 Delegation Guide

| If you encounter… | Delegate to |
|--------------------|-------------|
| Data reconciliation finds missing rows | **Schema (02)** — data load issue |
| DAX measure returns wrong result | **Semantic Model (04)** — expression bug |
| Visual renders incorrectly | **Report (05)** — visual mapping bug |
| RLS filter too permissive | **Security (06)** — filter expression bug |
| Regression in cross-agent pipeline | **Orchestrator (08)** — coordinate fix |

---

## 2. Inputs

| Input | Source | Format |
|---|---|---|
| Source OAC data and metadata | OAC APIs / Oracle DB | Live queries |
| Migrated Fabric data | Fabric Lakehouse/Warehouse | Delta tables |
| Migrated semantic model | Fabric workspace | TMDL / XMLA |
| Migrated reports | Fabric workspace | PBIR |
| Migration inventory | Fabric Lakehouse `migration_inventory` | Delta table |
| Mapping rules | Fabric Lakehouse `mapping_rules` | Delta table |

## 3. Outputs

| Output | Destination | Format |
|---|---|---|
| Validation results | Fabric Lakehouse `validation_results` | Delta table |
| Data reconciliation report | Git repo / Blob Storage | Markdown + CSV |
| Visual comparison gallery | Blob Storage | PNG pairs |
| Performance benchmark report | Git repo | Markdown |
| Defect tickets | Azure DevOps / Fabric Lakehouse | Work items / Delta table |

## 4. Validation Layers

### 4.1 Data Layer Validation

| Check | Method | Tolerance |
|---|---|---|
| **Row count** | `SELECT COUNT(*) FROM` (Oracle) vs `SELECT COUNT(*) FROM` (Fabric) | Exact match |
| **Checksum** | `SUM(HASH(pk_columns))` comparison | Exact match |
| **Null counts per column** | Count nulls per column, compare | Exact match |
| **Distinct counts per column** | Count distinct per column, compare | Exact match |
| **Min/Max per column** | Compare min/max for numeric and date columns | Exact match |
| **Sample rows** | Random sample of N rows, compare | Exact match |
| **Aggregate totals** | Key business metrics (SUM, AVG) on fact tables | ≤ 0.01% variance |
| **Data type verification** | Compare Oracle types vs Fabric types vs mapping | No mismatches |

### 4.2 Semantic Model Validation

| Check | Method | Tolerance |
|---|---|---|
| **Measure results** | Execute DAX `EVALUATE` query vs OAC logical SQL | ≤ 0.01% variance |
| **Relationship correctness** | Query across relationships, compare join results | Exact row count match |
| **Hierarchy drill** | Drill from top to bottom level, compare aggregates | ≤ 0.01% variance |
| **Filter context** | Apply filters, compare filtered results | Exact match |
| **Calculated column values** | Compare calculated column values for sample rows | Exact match |
| **Time intelligence** | YTD, PY, MTD measures compared to OAC | ≤ 0.01% variance |

### 4.3 Report Validation

| Check | Method | Tolerance |
|---|---|---|
| **Visual count** | Count visuals per page, compare to OAC | Exact match |
| **Visual types** | Verify mapped visual type matches expected | Exact match |
| **Data displayed** | Compare data shown in visuals (via API) | ≤ 0.01% variance |
| **Slicer/filter behavior** | Apply same filter selections, compare results | Functional equivalence |
| **Drillthrough** | Verify drillthrough targets and context passing | Functional equivalence |
| **Conditional formatting** | Visual inspection of formatting rules | Manual review |
| **Screenshot comparison** | Side-by-side OAC vs PBI screenshots | Manual review (flagged > threshold) |

### 4.4 Security Validation

| Check | Method | Tolerance |
|---|---|---|
| **RLS row count** | Same user, same query → compare row counts | Exact match |
| **RLS data content** | Same user, same query → compare actual data | Exact match |
| **OLS visibility** | Verify hidden columns not accessible | Binary pass/fail |
| **Cross-role testing** | Switch roles, verify different data views | Functional equivalence |
| **Negative testing** | Verify restricted data is NOT visible | Binary pass/fail |

### 4.5 Performance Validation

| Metric | Measurement | Acceptable Threshold |
|---|---|---|
| **Report load time** | Time from open to fully rendered | ≤ 2x OAC load time (target: faster) |
| **Query execution time** | Individual DAX query duration | ≤ 2x OAC query time |
| **Data refresh time** | Full/incremental refresh duration | Within Fabric capacity SLA |
| **Concurrent user capacity** | Load test with N users | Meet or exceed OAC concurrency |

## 5. Core Logic

### 5.1 Validation Workflow

```
1. Receive validation request (triggered by Orchestrator after each wave)
2. Identify validation scope (which layer, which assets)
3. For data validation:
   3.1 Connect to Oracle source and Fabric target
   3.2 Run reconciliation queries in parallel
   3.3 Compare results, log discrepancies
4. For semantic model validation:
   4.1 Generate test queries from mapping rules
   4.2 Execute on both OAC (logical SQL) and PBI (DAX)
   4.3 Compare results
5. For report validation:
   5.1 Capture screenshots of OAC reports
   5.2 Capture screenshots of PBI reports (via PBI API)
   5.3 Generate side-by-side comparison
   5.4 Run visual diff algorithm (pixel comparison)
6. For security validation:
   6.1 Test with each mapped user persona
   6.2 Run same queries with RLS context
   6.3 Compare row counts and data
7. Aggregate results to Lakehouse Delta table
8. Generate validation report
9. Create defect tickets for failures
```

### 5.2 Reconciliation Query Generator

```python
def generate_reconciliation_queries(table_inventory: list) -> list:
    """Generate paired queries (Oracle + Fabric) for data reconciliation."""
    queries = []
    for table in table_inventory:
        oracle_table = table["source_name"]
        fabric_table = table["target_name"]
        
        # Row count
        queries.append({
            "check": "row_count",
            "oracle_sql": f"SELECT COUNT(*) FROM {oracle_table}",
            "fabric_sql": f"SELECT COUNT(*) FROM {fabric_table}",
            "tolerance": 0
        })
        
        # Null counts per column
        for col in table["columns"]:
            queries.append({
                "check": f"null_count_{col['name']}",
                "oracle_sql": f"SELECT COUNT(*) FROM {oracle_table} WHERE {col['name']} IS NULL",
                "fabric_sql": f"SELECT COUNT(*) FROM {fabric_table} WHERE {col['name']} IS NULL",
                "tolerance": 0
            })
        
        # Aggregates for numeric columns
        for col in table["columns"]:
            if col["type"] in ("number", "decimal", "int"):
                queries.append({
                    "check": f"sum_{col['name']}",
                    "oracle_sql": f"SELECT SUM({col['name']}) FROM {oracle_table}",
                    "fabric_sql": f"SELECT SUM({col['name']}) FROM {fabric_table}",
                    "tolerance": 0.0001
                })
    
    return queries
```

### 5.3 Validation Result Delta Table Schema

```json
{
  "id": "val_20260301_sales_rowcount",
  "migrationId": "wave1_data_20260301",
  "validationType": "data_reconciliation",
  "check": "row_count",
  "asset": "Sales",
  "sourceValue": 1500000,
  "targetValue": 1500000,
  "variance": 0,
  "variancePercent": 0,
  "status": "PASS",
  "executedAt": "2026-03-01T14:00:00Z",
  "duration_ms": 1234
}
```

## 6. Visual Comparison Approach

```
1. Render OAC report page → screenshot (Selenium/Playwright against OAC URL)
2. Render PBI report page → screenshot (PBI Embedded API or Export API)
3. Resize both to same dimensions
4. Run pixel-level diff (using Pillow/OpenCV)
5. Calculate similarity score (SSIM or perceptual hash)
6. If similarity < 0.85: flag as "needs review"
7. Generate side-by-side HTML gallery
```

## 7. Error Handling

| Error | Handling |
|---|---|
| Oracle source unavailable | Skip data validation, log as blocked, retry later |
| Fabric query timeout | Increase timeout, retry with sampling |
| Screenshot capture failure | Log error, create manual validation task |
| Variance exceeds tolerance | Create defect ticket with details |
| Test infrastructure failure | Alert, retry, escalate to platform team |

## 8. Testing Strategy

| Test Type | Approach |
|---|---|
| Unit | Reconciliation query generation with known schemas |
| Integration | Run validation against dev environment with known data |
| Framework | Validate the validator — inject known discrepancies |
