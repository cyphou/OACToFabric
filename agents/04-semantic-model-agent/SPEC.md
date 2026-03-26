# Agent 04: Semantic Model Migration Agent — Technical Specification

## 1. Purpose

Convert the OAC **RPD logical/business model** (including calculated columns, hierarchies, and derived metrics) into a **Power BI Semantic Model** expressed in **TMDL (Tabular Model Definition Language)** format.

## 1.1 File Ownership

| File | Purpose |
|------|--------|
| `src/agents/semantic/semantic_agent.py` | SemanticModelAgent class — RPD → PBI Semantic Model |
| `src/agents/semantic/rpd_model_parser.py` | Extract logical model: columns, hierarchies, joins |
| `src/agents/semantic/expression_translator.py` | OAC calc expressions → DAX measures (60+ rules) |
| `src/agents/semantic/hierarchy_mapper.py` | Convert OAC hierarchies to PBI hierarchy objects |
| `src/agents/semantic/tmdl_generator.py` | Generate TMDL (Tabular Model Definition Language) |
| `src/core/expression_translator.py` | Core OAC → DAX rule engine (shared) |
| `src/core/hybrid_translator.py` | Rules-first + LLM fallback translation engine |
| `src/core/translation_cache.py` | SQLite deterministic cache for LLM translation hits |
| `src/core/translation_catalog.py` | Expanded DAX function mappings & coverage stats |
| `src/agents/semantic/calendar_generator.py` | Auto-detect date columns → 8-column Calendar table + hierarchy + 3 TI measures (Phase 47) |
| `src/agents/semantic/dax_optimizer.py` | 5 DAX optimization rules: ISBLANK→COALESCE, IF→SWITCH, SUMX→SUM, etc. (Phase 47) |
| `src/agents/semantic/leak_detector.py` | 22 OAC function leak patterns (NVL, DECODE, SYSDATE, VALUEOF) + auto-fix (Phase 47) |
| `src/agents/semantic/tmdl_self_healing.py` | 6 auto-repair patterns: duplicates, broken refs, orphans, empty names, circular rels, M errors (Phase 47) |

## 1.2 Constraints

- Do NOT modify report visuals, security roles, or schema DDL
- Do NOT modify discovery/extraction logic
- Only produces TMDL semantic model artifacts and DAX expressions
- All expression translation rules go through `hybrid_translator.py` — do not bypass with direct LLM calls
- Confidence < 0.7 from LLM → flag for manual review, do NOT silently accept

## 1.3 Delegation Guide

| If you encounter… | Delegate to |
|--------------------|-------------|
| Missing physical table in Fabric | **Schema (02)** — DDL not generated |
| RLS filter expression on a table | **Security (06)** — role definition |
| Visual referencing a measure | **Report (05)** — visual mapping |
| Complex PL/SQL in a derived column | **ETL (03)** — PySpark translation |

---

## 2. Inputs

| Input | Source | Format |
|---|---|---|
| RPD logical layer inventory | Fabric Lakehouse `migration_inventory` | Delta table (from Agent 01) |
| RPD presentation layer inventory | Fabric Lakehouse `migration_inventory` | Delta table (from Agent 01) |
| Fabric table schemas | Fabric Lakehouse `mapping_rules` | Delta table (from Agent 02) |
| OAC expression definitions | Fabric Lakehouse `migration_inventory` | Delta table |

## 3. Outputs

| Output | Destination | Format |
|---|---|---|
| TMDL folder structure | Git repo | `.tmdl` files |
| Deployed semantic model | Fabric workspace | Power BI Semantic Model |
| Expression translation log | Fabric Lakehouse `mapping_rules` | Delta table |
| Untranslatable expression queue | Fabric Lakehouse `agent_tasks` | Delta table |

## 4. TMDL Structure Generated

```
SemanticModel/
├── model.tmdl                     # Model-level properties
├── definition/
│   ├── tables/
│   │   ├── Sales.tmdl             # Table definition with columns, measures
│   │   ├── Products.tmdl
│   │   └── Date.tmdl
│   ├── relationships.tmdl         # All relationships
│   ├── perspectives.tmdl          # Maps to OAC Subject Areas
│   ├── roles.tmdl                 # RLS roles (from Agent 06)
│   ├── cultures/
│   │   └── en-US.tmdl             # Translations/display folders
│   └── expressions.tmdl           # Shared M expressions (data sources)
└── .platform                      # Fabric platform config
```

## 5. Mapping Rules

### 5.1 RPD Logical → TMDL Table Mapping

| RPD Concept | TMDL Concept |
|---|---|
| Logical Table | Table |
| Logical Column (direct mapped) | Column (with `sourceColumn` binding) |
| Logical Column (derived/calculated) | Measure (DAX) or Calculated Column |
| Logical Table Source (LTS) | Partition (with SQL/M expression) |
| Logical Join | Relationship |
| Hierarchy | Hierarchy with Levels |
| Presentation Table | Perspective or Display Folder |
| Presentation Column | Column visibility + display folder |
| Subject Area | Perspective |

### 5.2 RPD Join → TMDL Relationship Mapping

| RPD Join Property | TMDL Relationship Property |
|---|---|
| Join type (inner/outer) | `crossFilteringBehavior` |
| 1:N cardinality | `fromCardinality: one`, `toCardinality: many` |
| M:N cardinality | `fromCardinality: many`, `toCardinality: many` (requires bridge) |
| Join columns | `fromColumn`, `toColumn` |
| Join expression (complex) | May require calculated column to normalize |

### 5.3 OAC Expression → DAX Translation

| OAC Expression / Function | DAX Equivalent |
|---|---|
| `SUM(column)` | `SUM(Table[Column])` |
| `COUNT(column)` | `COUNT(Table[Column])` |
| `AVG(column)` | `AVERAGE(Table[Column])` |
| `COUNTDISTINCT(column)` | `DISTINCTCOUNT(Table[Column])` |
| `FILTER(column USING ...)` | `CALCULATE(measure, filter)` |
| `AGO(measure, time, N)` | `CALCULATE(measure, DATEADD(Date[Date], -N, period))` |
| `TODATE(measure, time)` | `CALCULATE(measure, DATESYTD(Date[Date]))` |
| `PERIODROLLING(measure, N)` | `CALCULATE(measure, DATESINPERIOD(Date[Date], MAX(Date[Date]), -N, DAY))` |
| `RANK(measure)` | `RANKX(ALL(Table), measure)` |
| `RSUM(measure)` | `CALCULATE(measure, FILTER(ALL(Date), Date[Date] <= MAX(Date[Date])))` |
| `TOPN(N, measure)` | `TOPN(N, Table, measure)` |
| `CASE WHEN ... THEN ... ELSE ... END` | `SWITCH(TRUE(), condition1, val1, condition2, val2, default)` |
| `IFNULL(a, b)` | `IF(ISBLANK(a), b, a)` |
| `CONCAT(a, b)` | `a & b` |
| `CAST(col AS type)` | `CONVERT(col, type)` or `INT(col)`, `VALUE(col)` |
| Session variable (`VALUEOF(NQ_SESSION.var)`) | `USERPRINCIPALNAME()` or RLS filter pattern |
| `EVALUATE_PREDICATE` | Embedded in `CALCULATE` filter |
| `DESCRIPTOR_IDOF(col)` | Column key reference |
| `INDEXCOL(...)` | Level-based column in hierarchy |

### 5.4 LLM-Assisted Translation

For expressions that don't match rule-based patterns:

```
You are an expert in Oracle Analytics Cloud (OAC/OBIEE) and Power BI DAX.
Convert the following OAC logical column expression to an equivalent DAX measure.

Context:
- Table: {table_name}
- Column: {column_name}
- Data type: {data_type}
- Available columns in the model: {available_columns}

OAC Expression:
{oac_expression}

Generate:
1. The DAX measure expression
2. Confidence score (0-1)
3. Any assumptions made
4. Whether manual review is recommended
```

## 6. Core Logic

### 6.1 Semantic Model Generation Flow

```
1. Load RPD logical layer from Lakehouse
2. For each logical table:
   2.1 Create TMDL table definition
   2.2 Map columns (detect type: column vs measure vs calculated column)
   2.3 Generate partition expression (SQL query against Fabric Lakehouse)
   2.4 For each calculated/derived column:
       2.4.1 Attempt rule-based OAC → DAX translation
       2.4.2 If no rule matches, use LLM translation
       2.4.3 If LLM confidence < 0.7, flag for manual review
3. For each logical join:
   3.1 Create TMDL relationship
   3.2 Determine cardinality and cross-filter direction
4. For each hierarchy:
   4.1 Create TMDL hierarchy with levels
5. For each subject area:
   5.1 Create TMDL perspective
6. Write TMDL files to disk / Git
7. Deploy to Fabric workspace via XMLA endpoint
8. Run validation queries
```

### 6.2 TMDL Table Example Output

```tmdl
table Sales
    lineageTag: a1b2c3d4-e5f6-7890-abcd-ef1234567890
    
    partition Sales = m
        mode: import
        source
            let
                Source = Sql.Database("onelake-sql-endpoint", "MyLakehouse"),
                Sales = Source{[Schema="dbo", Item="Sales"]}[Data]
            in
                Sales
    
    column OrderID
        dataType: int64
        formatString: 0
        sourceColumn: OrderID
        summarizeBy: none
    
    column Revenue
        dataType: decimal
        formatString: \$#,0.00;(\$#,0.00);\$#,0.00
        sourceColumn: Revenue
        summarizeBy: sum
    
    column OrderDate
        dataType: dateTime
        sourceColumn: OrderDate
        summarizeBy: none
    
    measure 'Total Revenue' = SUM(Sales[Revenue])
        formatString: \$#,0.00
        displayFolder: Measures
    
    measure 'Revenue YTD' = CALCULATE([Total Revenue], DATESYTD('Date'[Date]))
        formatString: \$#,0.00
        displayFolder: Time Intelligence
    
    measure 'Revenue Prior Year' = CALCULATE([Total Revenue], DATEADD('Date'[Date], -1, YEAR))
        formatString: \$#,0.00
        displayFolder: Time Intelligence
    
    hierarchy Geography
        level Country
            column: Country
        level Region
            column: Region
        level City
            column: City
```

## 7. Error Handling

| Error | Handling |
|---|---|
| Unknown OAC expression function | Log, attempt LLM translation, else flag for manual review |
| M:N join without bridge table | Log warning, suggest bridge table creation |
| Circular dependency in relationships | Detect, break cycle by deactivating relationships, flag |
| TMDL deployment failure | Parse error, attempt fix, log diagnostic |
| LLM translation timeout | Retry once, then queue for manual review |

## 8. Testing Strategy

| Test Type | Approach |
|---|---|
| Unit | Expression translation for all known OAC functions |
| Integration | TMDL generation → deployment → query |
| DAX comparison | Run equivalent queries on OAC and PBI, compare results |
| Golden file | Compare generated TMDL against hand-crafted expected output |
