# Agent 02: Schema & Data Model Migration Agent — Technical Specification

## 1. Purpose

Migrate Oracle Database schemas (tables, views, data types, constraints) to **Microsoft Fabric Lakehouse** (Delta tables) or **Fabric Warehouse** (T-SQL), and orchestrate initial and incremental data loading.

## 2. Inputs

| Input | Source | Format |
|---|---|---|
| Physical layer inventory | Fabric Lakehouse `migration_inventory` | Delta table (from Agent 01) |
| Oracle connection details | Key Vault | Connection string |
| Data type mapping rules | Fabric Lakehouse `mapping_rules` | Delta table |
| Migration scope (tables to migrate) | Orchestrator | JSON (include/exclude) |

## 3. Outputs

| Output | Destination | Format |
|---|---|---|
| Fabric Lakehouse tables | OneLake | Delta / Parquet |
| DDL scripts | Git repo | Spark SQL / T-SQL |
| Data Factory pipeline definitions | Git repo | JSON |
| Data type mapping log | Fabric Lakehouse `mapping_rules` | Delta table |
| Migration results | Fabric Lakehouse `agent_tasks` | Delta table |

## 4. Data Type Mapping

### Oracle → Fabric Lakehouse (Spark/Delta) Mapping

| Oracle Type | Fabric Delta Type | Notes |
|---|---|---|
| `NUMBER(p,0)` where p ≤ 9 | `INT` | Integer |
| `NUMBER(p,0)` where p ≤ 18 | `BIGINT` | Long integer |
| `NUMBER(p,s)` | `DECIMAL(p,s)` | Exact numeric |
| `NUMBER` (no precision) | `DOUBLE` | Floating point |
| `VARCHAR2(n)` | `STRING` | UTF-8 string |
| `NVARCHAR2(n)` | `STRING` | UTF-8 string |
| `CHAR(n)` | `STRING` | Fixed-width → variable |
| `CLOB` | `STRING` | Large text |
| `DATE` | `TIMESTAMP` | Oracle DATE includes time |
| `TIMESTAMP` | `TIMESTAMP` | Direct map |
| `TIMESTAMP WITH TIME ZONE` | `TIMESTAMP` | Convert to UTC |
| `BLOB` | `BINARY` | Binary data |
| `RAW(n)` | `BINARY` | Binary data |
| `FLOAT` | `DOUBLE` | IEEE 754 |
| `XMLTYPE` | `STRING` | Serialize as XML string |
| `INTERVAL` | `STRING` | Serialize as ISO 8601 |

### Oracle → Fabric Warehouse (T-SQL) Mapping

| Oracle Type | Fabric Warehouse Type |
|---|---|
| `NUMBER(p,0)` p ≤ 9 | `INT` |
| `NUMBER(p,0)` p ≤ 18 | `BIGINT` |
| `NUMBER(p,s)` | `DECIMAL(p,s)` |
| `VARCHAR2(n)` | `VARCHAR(n)` |
| `CLOB` | `VARCHAR(MAX)` |
| `DATE` | `DATETIME2` |
| `TIMESTAMP` | `DATETIME2(7)` |
| `BLOB` | `VARBINARY(MAX)` |

## 5. Core Logic

### 5.1 Schema Migration Flow

```
1. Read physical layer inventory from Lakehouse
2. For each table in scope:
   2.1 Apply data type mapping rules
   2.2 Handle special cases (composite keys, check constraints, etc.)
   2.3 Generate CREATE TABLE DDL (Spark SQL for Lakehouse / T-SQL for Warehouse)
   2.4 Execute DDL against Fabric
   2.5 Log schema creation result to Lakehouse
3. For each view in scope:
   3.1 Translate Oracle SQL → Spark SQL / T-SQL
   3.2 Handle Oracle-specific functions (NVL→COALESCE, DECODE→CASE, etc.)
   3.3 Generate CREATE VIEW DDL
   3.4 Execute DDL
4. Generate Data Factory pipelines for data loading
   4.1 Full load pipeline (initial migration)
   4.2 Incremental load pipeline (ongoing sync)
5. Execute data loading
6. Validate (row counts, sample data)
```

### 5.2 Oracle SQL → Fabric SQL Function Mapping

| Oracle Function | Fabric Equivalent |
|---|---|
| `NVL(a, b)` | `COALESCE(a, b)` |
| `NVL2(a, b, c)` | `CASE WHEN a IS NOT NULL THEN b ELSE c END` |
| `DECODE(a, b, c, d)` | `CASE WHEN a = b THEN c ELSE d END` |
| `SYSDATE` | `CURRENT_TIMESTAMP()` |
| `TO_CHAR(date, fmt)` | `DATE_FORMAT(date, fmt)` (Spark) |
| `TO_DATE(str, fmt)` | `TO_DATE(str, fmt)` (Spark) |
| `ROWNUM` | `ROW_NUMBER() OVER(...)` |
| `(+)` outer join | `LEFT/RIGHT JOIN` |
| `CONNECT BY` | Recursive CTE |
| `LISTAGG` | `CONCAT_WS` / `STRING_AGG` |
| `SUBSTR` | `SUBSTRING` |
| `INSTR` | `LOCATE` (Spark) / `CHARINDEX` (T-SQL) |
| `TRUNC(date)` | `DATE_TRUNC('day', date)` |
| `MONTHS_BETWEEN` | `MONTHS_BETWEEN` (Spark) / `DATEDIFF(month,...)` |

## 6. Data Loading Strategy

### Full Load (Initial)

```
Oracle DB → Copy Activity (Fabric Data Factory) → OneLake (Delta)
                     │
                     ├── Parallel copy (partitioned by PK range) for large tables
                     ├── Batch size: 100,000 rows per batch
                     └── Compression: Snappy (Delta default)
```

### Incremental Load (Ongoing)

```
Oracle DB → Copy Activity (watermark-based) → OneLake (Delta, MERGE)
                     │
                     ├── Watermark column: last_modified_date or rowversion
                     ├── High watermark stored in Lakehouse Delta table per table
                     └── MERGE into Delta for upserts
```

## 7. Error Handling

| Error | Handling |
|---|---|
| Unsupported Oracle type | Log warning, use STRING as fallback, flag for review |
| Oracle connection timeout | Retry with exponential backoff (3 attempts) |
| Fabric DDL execution failure | Log error, skip table, continue with next |
| Data copy failure (partial) | Retry from last checkpoint; Data Factory handles restartability |
| Row count mismatch | Log as validation failure, flag for investigation |

## 8. Testing Strategy

| Test Type | Approach |
|---|---|
| Unit tests | Data type mapping with edge cases |
| DDL generation tests | Golden file comparison for generated DDL |
| Integration tests | Schema creation on Fabric dev workspace |
| Data validation | Row counts, checksums, sample comparisons |
