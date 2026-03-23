# Agent 03: ETL/Data Pipeline Migration Agent — Technical Specification

## 1. Purpose

Convert **OAC Data Flows**, **Oracle stored procedures**, and **scheduled ETL jobs** into equivalent **Fabric Data Factory pipelines**, **Dataflows Gen2**, and **Fabric Notebooks** (PySpark).

## 1.1 File Ownership

| File | Purpose |
|------|--------|
| `src/agents/etl/etl_agent.py` | ETLAgent class — convert OAC Data Flows to Fabric |
| `src/agents/etl/dataflow_parser.py` | Parse OAC Data Flow XML; extract steps |
| `src/agents/etl/step_mapper.py` | Map OAC steps to Fabric activities |
| `src/agents/etl/plsql_translator.py` | PL/SQL → PySpark/SQL for stored procedures |
| `src/agents/etl/schedule_converter.py` | OAC scheduler → Fabric triggers |

## 1.2 Constraints

- Do NOT modify discovery, schema DDL, or semantic model logic
- Do NOT modify OAC extraction or RPD parsing
- Only produces Fabric pipeline JSON, notebook files, and schedule artifacts
- Use `src/core/llm_client.py` for LLM-assisted PL/SQL translation — never call Azure OpenAI directly

## 1.3 Delegation Guide

| If you encounter… | Delegate to |
|--------------------|-------------|
| Missing source table definitions | **Schema (02)** — DDL not yet generated |
| Data Flow references unknown OAC asset | **Discovery (01)** — inventory incomplete |
| DAX measure needed in destination model | **Semantic Model (04)** |
| Pipeline deployment to workspace | **Orchestrator (08)** |

---

## 2. Inputs

| Input | Source | Format |
|---|---|---|
| OAC Data Flow definitions | Fabric Lakehouse `migration_inventory` | Delta table (from Agent 01) |
| Oracle stored procedures (PL/SQL) | Oracle DB / source code repo | SQL files |
| Oracle scheduled jobs (DBMS_SCHEDULER) | Oracle DB metadata | JSON |
| Schema mapping results | Fabric Lakehouse `mapping_rules` | Delta table (from Agent 02) |

## 3. Outputs

| Output | Destination | Format |
|---|---|---|
| Fabric Data Factory pipelines | Git repo / Fabric workspace | JSON |
| Dataflow Gen2 definitions | Fabric workspace | M (Power Query) |
| PySpark Notebooks | Git repo / Fabric workspace | .py / .ipynb |
| Fabric triggers (schedules) | Fabric workspace | JSON |
| Migration mapping log | Fabric Lakehouse `mapping_rules` | Delta table |

## 4. OAC Data Flow Step → Fabric Mapping

| OAC Data Flow Step | Fabric Equivalent |
|---|---|
| **Source (Database)** | Data Factory Copy Activity (source) |
| **Source (File)** | Data Factory Copy Activity (file source from OneLake) |
| **Filter** | Data Factory Filter Activity / Dataflow filter step / Spark `.filter()` |
| **Join** | Data Factory Data Flow Join / Spark `.join()` |
| **Aggregate** | Data Factory Data Flow Aggregate / Spark `.groupBy().agg()` |
| **Lookup** | Data Factory Lookup Activity / Spark broadcast join |
| **Union** | Data Factory Data Flow Union / Spark `.union()` |
| **Sort** | Data Factory Data Flow Sort / Spark `.orderBy()` |
| **Add Column** | Data Factory Derived Column / Spark `.withColumn()` |
| **Rename Column** | Data Factory Select / Spark `.withColumnRenamed()` |
| **Data Type Conversion** | Data Factory Derived Column / Spark `.cast()` |
| **Target (Database)** | Data Factory Copy Activity (sink to Lakehouse/Warehouse) |
| **Target (File)** | Data Factory Copy Activity (sink to OneLake) |
| **Branch / Conditional** | Data Factory If Condition / Switch Activity |
| **Loop** | Data Factory ForEach Activity |
| **Stored Procedure Call** | Fabric Notebook (PySpark equivalent) |

## 5. PL/SQL → PySpark Translation

### 5.1 Translation Strategy

1. **Rule-based translation** for common patterns (cursors, loops, DML).
2. **LLM-assisted translation** (Azure OpenAI GPT-4) for complex logic.
3. **Manual review queue** for untranslatable patterns.

### 5.2 Common PL/SQL → PySpark Patterns

| PL/SQL Pattern | PySpark Equivalent |
|---|---|
| `CURSOR ... LOOP ... END LOOP` | `spark.sql("SELECT ...").collect()` + Python loop, or DataFrame ops |
| `INSERT INTO ... SELECT` | `df.write.mode("append").saveAsTable(...)` |
| `UPDATE ... SET ... WHERE` | Delta Lake MERGE operation |
| `DELETE FROM ... WHERE` | Delta Lake MERGE with delete condition |
| `MERGE INTO ... USING` | Delta `DeltaTable.forPath(...).merge(...)` |
| `EXCEPTION WHEN` | `try/except` blocks |
| `DBMS_OUTPUT.PUT_LINE` | `print()` or `logger.info()` |
| `BULK COLLECT` | DataFrame operations (inherently bulk) |
| `%ROWTYPE`, `%TYPE` | Not needed (schema inferred) |
| `EXECUTE IMMEDIATE (DDL)` | `spark.sql(ddl_string)` |
| Temporary tables | Spark temp views or Delta temp tables |
| Package variables | Python module-level variables or class attributes |
| Sequences | `monotonically_increasing_id()` or Delta identity columns |

### 5.3 LLM Translation Prompt Template

```
You are an expert data engineer. Convert the following Oracle PL/SQL stored procedure 
into a PySpark Notebook that runs on Microsoft Fabric.

Rules:
- Use Delta Lake for all table operations
- Use spark.sql() for SQL operations where appropriate
- Use DataFrame API for transformations
- Replace Oracle-specific functions with PySpark equivalents
- Maintain the same business logic and error handling
- Add logging using Python's logging module
- The Lakehouse is already attached; tables are in the default catalog

Source PL/SQL:
```sql
{plsql_code}
```

Target table mapping:
{table_mapping_json}

Generate the PySpark notebook code:
```

## 6. Schedule Migration

| Oracle Scheduler Concept | Fabric Equivalent |
|---|---|
| `DBMS_SCHEDULER.CREATE_JOB` | Fabric Data Factory Trigger (Schedule) |
| `REPEAT_INTERVAL` (FREQ=DAILY) | Recurrence: Daily |
| `REPEAT_INTERVAL` (FREQ=HOURLY) | Recurrence: Hourly |
| `REPEAT_INTERVAL` (cron-style) | Cron expression in trigger |
| Job chains (A → B → C) | Pipeline with sequential activities |
| Job dependencies | Pipeline dependency configuration |
| Job parameters | Pipeline parameters |

## 7. Error Handling

| Error | Handling |
|---|---|
| Unsupported OAC flow step type | Log warning, create placeholder activity, flag for manual review |
| PL/SQL too complex for auto-translation | Send to LLM; if still failing, add to manual review queue |
| Generated pipeline validation failure | Log error, attempt auto-fix (common issues), else flag |
| Schedule conversion ambiguity | Default to most conservative (less frequent) schedule, flag for review |

## 8. Testing Strategy

| Test Type | Approach |
|---|---|
| Unit tests | Step mapping with sample OAC flow definitions |
| PL/SQL translation tests | Golden file comparison for known procedures |
| Pipeline validation | Dry-run in Fabric dev workspace |
| End-to-end | Run migrated pipeline, compare output to OAC data flow output |
| Schedule tests | Verify trigger fires at expected times |
