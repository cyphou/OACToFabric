# Essbase → Fabric Migration Report

> **Generated:** 2026-04-01 16:21:08 UTC  
> **Cubes:** 3 | **Elapsed:** 0.1s  
> **Output:** `C:\Users\pidoudet\OneDrive - Microsoft\Boulot\PBI SME\OracleToPostgre\OACToFabric\output\essbase_migration`

## Summary

| Metric | Value |
|--------|-------|
| Cubes processed | **3** |
| Dimensions | 15 |
| Members | 187 |
| Dynamic calcs | 21 |
| Semantic tables | 15 |
| DAX measures | 66 |
| Relationships | 12 |
| Hierarchies | 3 |
| TMDL files | 36 |
| DDL tables | 15 |
| Calc translations | 22 |
| RLS roles | 4 |
| What-if params | 7 |

## Translation Confidence

| Level | Count |
|-------|-------|
| High (≥0.7) | 19 |
| Medium (0.5–0.7) | 3 |
| Low (<0.5) | 0 |

## Cube: complex_planning

- **Dimensions:** 7
- **Members:** 114
- **Dynamic calcs:** 14
- **Tables generated:** 7
- **Measures:** 43
- **Relationships:** 6
- **TMDL files:** 14
- **DDL tables:** 7

### Calc Script Translations

| Script | Source | DAX | Confidence |
|--------|--------|-----|------------|
| CalcGrossProfit | `Revenue + COGS` | `Revenue + COGS` | 100% |
| CalcEBITDA | `Gross Profit + OpEx` | `Gross Profit + OpEx` | 100% |
| CalcEBIT | `EBITDA + Depreciation` | `EBITDA + Depreciation` | 100% |
| CalcGrossMarginPct | `@ROUND(Gross Profit % Revenue, 4)` | `ROUND(Gross Profit % Revenue, 4)` | 100% |
| CalcEBITDAMarginPct | `@ROUND(EBITDA % Revenue, 4)` | `ROUND(EBITDA % Revenue, 4)` | 100% |
| CalcRevPerFTE | `@ROUND(Revenue / (Headcount SM + Headcou` | `ROUND(Revenue / (Headcount SM + Headcount RD + Hea` | 100% |
| CalcBudVariance | `Actual - Budget` | `Actual - Budget` | 100% |
| CalcBudVariancePct | `@ROUND((Actual - Budget) % Budget, 4)` | `ROUND((Actual - Budget) % Budget, 4)` | 100% |
| CalcYTD | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(T` | `CALCULATE(SUM( /* @SUMRANGE */ Time, CALCULATE( /*` | 50% |
| CalcPriorYear | `@PRIOR(Time, 12, @LEVMBRS(Time, 3))` | `CALCULATE( /* @PRIOR */ Time, 12, @LEVMBRS(Time, 3` | 70% |
| CalcYoYGrowth | `@ROUND((Actual - @PRIOR(Actual, 1, @LEVM` | `ROUND((Actual - CALCULATE( /* @PRIOR */ Actual, 1,` | 70% |
| CalcCurrencyConvert | `@CALCMBR(Local, @XREF(ExchangeRates, Rat` | `@CALCMBR(Local, @XREF(ExchangeRates, Rate))` | 100% |
| YTD Revenue | `SELECT {[Measures].[Revenue]} ON COLUMNS` | `SELECT {[Revenue]} ON COLUMNS, CALCULATE(measure, ` | 70% |
| Top 5 Products | `SELECT TopCount([Product].Children, 5, [` | `SELECT TOPN(VALUES('Product'[Product]), 5, [Revenu` | 70% |
| Variance Filter | `SELECT Filter([Entity].Children, IIF([Me` | `SELECT CALCULATE(measure, FILTER(VALUES('Entity'[E` | 50% |

### RLS Roles

| Role | Filter |
|------|--------|
| RegionalManager | `CONTAINSSTRING({table}[member], "Americas") && CONTAINSSTRIN` |
| FinanceAnalyst | `CONTAINSSTRING({table}[member], "Actual") && CONTAINSSTRING(` |
| PlanningAdmin | `CONTAINSSTRING({table}[member], "Worldwide") && CONTAINSSTRI` |

### What-If Parameters

| Parameter | Value | DAX Variable |
|-----------|-------|-------------|
| CurMonth | Mar-24 | `VAR __CurMonth = "Mar-24"` |
| CurYear | FY2024 | `VAR __CurYear = "FY2024"` |
| BudYear | FY2024 | `VAR __BudYear = "FY2024"` |
| FcstStart | Apr-24 | `VAR __FcstStart = "Apr-24"` |
| BaseCurrency | USD | `VAR __BaseCurrency = "USD"` |

## Cube: medium_finance

- **Dimensions:** 5
- **Members:** 55
- **Dynamic calcs:** 6
- **Tables generated:** 5
- **Measures:** 19
- **Relationships:** 4
- **TMDL files:** 12
- **DDL tables:** 5

### Calc Script Translations

| Script | Source | DAX | Confidence |
|--------|--------|-----|------------|
| CalcGrossProfit | `Revenue - COGS` | `Revenue - COGS` | 100% |
| CalcOperatingIncome | `Gross Profit - Operating Expenses` | `Gross Profit - Operating Expenses` | 100% |
| CalcGrossMarginPct | `@ROUND(Gross Profit % Revenue, 4)` | `ROUND(Gross Profit % Revenue, 4)` | 100% |
| CalcVariance | `Actual - Budget` | `Actual - Budget` | 100% |
| CalcVariancePct | `@ROUND((Actual - Budget) % Budget, 4)` | `ROUND((Actual - Budget) % Budget, 4)` | 100% |
| CalcYTD | `@SUMRANGE(Time, @TODATE(Time, @CURRMBR(T` | `CALCULATE(SUM( /* @SUMRANGE */ Time, CALCULATE( /*` | 50% |

### RLS Roles

| Role | Filter |
|------|--------|
| RegionalAccess | `CONTAINSSTRING({table}[member], "North America") && CONTAINS` |

### What-If Parameters

| Parameter | Value | DAX Variable |
|-----------|-------|-------------|
| CurMonth | Jun | `VAR __CurMonth = "Jun"` |
| CurYear | FY2024 | `VAR __CurYear = "FY2024"` |

## Cube: simple_budget

- **Dimensions:** 3
- **Members:** 18
- **Dynamic calcs:** 1
- **Tables generated:** 3
- **Measures:** 4
- **Relationships:** 2
- **TMDL files:** 10
- **DDL tables:** 3

### Calc Script Translations

| Script | Source | DAX | Confidence |
|--------|--------|-----|------------|
| CalcGrossProfit | `Revenue - COGS` | `Revenue - COGS` | 100% |

## Essbase → Fabric Mapping Reference

| Essbase Concept | Fabric / Power BI Equivalent |
|----------------|------------------------------|
| Cube | Semantic Model |
| Dimension (Accounts) | DAX Measures + Calculated Columns |
| Dimension (Time) | Date Table (mark as date table) |
| Dimension (Regular, Sparse) | Dimension Table with hierarchy |
| Dense Dimension | Columns in fact table |
| Dynamic Calc Member | DAX Measure |
| Calc Script | DAX Measures / Calculated Tables |
| Essbase Filter | RLS Role (DAX filter) |
| Substitution Variable | What-if Parameter |
| UDA | Boolean column on dimension table |
| Shared Member | Alternate hierarchy |

---
*Generated by OAC-to-Fabric Migration Accelerator — 2026-04-01 16:21:08 UTC*