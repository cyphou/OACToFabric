# Phase A Cutover Checklist — longview_budget_writeback

**Application**: longview_budget_writeback/longview_budget_writeback
**Target**: Fabric Warehouse `BudgetWarehouse` in `BudgetWorkspace`
**Strategy**: Keep Longview, replace Essbase backend

---

## Pre-Cutover (Day −1)

- [ ] All UAT tests pass (run `UAT_Validation_Notebook`)
- [ ] Row counts match between Essbase and Fabric
- [ ] Grand totals match within tolerance (±0.01)
- [ ] Writeback round-trip test passes
- [ ] Longview forms tested with TDS endpoint in staging
- [ ] Rollback plan documented and tested
- [ ] Stakeholders notified of cutover window

## Cutover Steps (Day 0)

### 1. Freeze Essbase (read-only)
```
ALTER SYSTEM "longview_budget_writeback" SET READONLY;
```

### 2. Final data sync
- [ ] Run final Essbase export
- [ ] Execute `Data_Migration_Notebook` with latest export
- [ ] Verify row counts match

### 3. Switch Longview connection
- [ ] Update Longview data source: `BudgetWorkspace.datawarehouse.fabric.microsoft.com:1433`
- [ ] Set database: `BudgetWarehouse`
- [ ] Switch auth to Entra ID (Azure AD)
- [ ] Map writeback to `dbo.usp_WriteBudget`

### 4. Smoke tests
- [ ] Open Longview form → verify data loads
- [ ] Submit a test budget entry → verify writeback
- [ ] Check `Budget_Audit` table for audit trail
- [ ] Run one calc cycle (PySpark notebook via pipeline)
- [ ] Verify `Budget_Consolidated` has calculated values

### 5. Enable monitoring
- [ ] Fabric pipeline alert on failure
- [ ] Warehouse query performance baseline
- [ ] Longview connection health check

## Post-Cutover (Day +1 to +5)

- [ ] Monitor Longview → Fabric writeback latency
- [ ] Verify scheduled pipeline runs succeed
- [ ] Collect user feedback (budget planners, finance)
- [ ] Confirm Essbase can be shut down (after 1-week soak)

## Rollback Plan

If critical issues arise:

1. Revert Longview connection to Essbase endpoint
2. Essbase is still running in parallel — no data loss
3. Investigate and fix the Fabric-side issue
4. Re-attempt cutover after fix

---

## Time Savings Summary

| Phase | Traditional | Automated (This Tool) | Time Saved |
|-------|-------------|----------------------|------------|
| Assessment | 1–2 weeks | 2 days | 80% |
| Warehouse DDL | 3–5 days | Minutes (auto-gen) | 95% |
| Data Migration | 1–2 weeks | 3–5 days | 60% |
| Calc Scripts → PySpark | 2–4 weeks | 3–5 days | 75% |
| Connection Config | 2–3 days | Auto-generated | 90% |
| UAT Validation | 1–2 weeks | 3–5 days | 60% |
| Go-Live | 2–3 days | 2 days | 30% |
| **Total** | **6–10 weeks** | **2–4 weeks** | **~65%** |