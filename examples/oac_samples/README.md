# OAC RPD XML Samples

Sample Oracle Analytics Cloud Repository (RPD) XML exports at multiple complexity levels.

## Files

| File | Complexity | Tables | Expressions | Features |
|------|-----------|--------|-------------|----------|
| `simple_sales.xml` | Simple | 2 | 1 | Basic columns, SUM aggregate |
| `medium_hr.xml` | Medium | 4 | 3 | Hierarchies, security roles, init blocks, AVG, `\|\|` concat |
| `complex_enterprise.xml` | Complex | 8 | 7 | Full enterprise RPD, CASE WHEN, multi-fact, data flows |
| `advanced_analytics.xml` | Advanced | 5 | 35 | Time intelligence (AGO, TODATE, PERIODROLLING, RSUM, MAVG, MSUM, PARALLELPERIOD, OPENINGBALANCE/CLOSINGBALANCE), window analytics (RANK, DENSE_RANK, NTILE, RATIO_TO_REPORT, CUME_DIST, PERCENT_RANK), advanced aggregates (COUNTDISTINCT, MEDIAN, STDDEV, PERCENTILE, COUNTIF, SUMIF) |
| `financial_functions.xml` | Advanced | 6 | 50+ | String functions (CONCAT, SUBSTRING, UPPER, LOWER, TRIM, LTRIM, RTRIM, REPLACE, LENGTH, INSTR, LPAD, RPAD, INITCAP, LEFT, RIGHT, ASCII, CHR, TRANSLATE), date functions (EXTRACT, MONTHS_BETWEEN, ADD_MONTHS, CURRENT_DATE, SYSDATE, TO_CHAR, LAST_DAY), math (ABS, ROUND, CEIL, FLOOR, POWER, SQRT, LOG, EXP, MOD, SIGN), logical (DECODE, CASE WHEN, IFNULL, NVL, NVL2, COALESCE, NULLIF, GREATEST, LEAST, CAST, TOPN), special (VALUEOF, RAND) |

## XML Structure

The RPD XML uses a `<Repository>` root element with the following top-level tags:

- `<PhysicalTable>` — Physical database tables with `<PhysicalColumn>` children
- `<LogicalTable>` — Business model tables with `<LogicalColumn>`, `<LogicalHierarchy>`, `<LogicalTableSource>`
- `<SubjectArea>` — Presentation layer groupings with `<PresentationTable>` / `<PresentationColumn>`
- `<SecurityRole>` — Application roles with `<Member>` and `<Permission>`
- `<InitBlock>` — Session variable initialisation blocks with `<SQL>` and `<Variable>`
- `<Connection>` — Database connection definitions
- `<DataFlow>` — Data flow definitions

## Usage

```python
from src.agents.discovery.rpd_parser import RPDParser

parser = RPDParser()
with open("examples/oac_samples/simple_sales.xml") as f:
    inventory = parser.parse(f.read())

for table in inventory.get("physical_tables", []):
    print(table["name"])
```
