# Mapping Reference — OAC to Fabric & Power BI

> **Centralized reference** for all translation rules used by the migration agents.
> Consolidates mappings from Agent SPECs, `type_mapper.py`, `sql_translator.py`,
> `expression_translator.py`, `visual_mapper.py`, and `translation_catalog.py`.

---

## Table of Contents

1. [Oracle → Fabric Data Type Mappings](#1-oracle--fabric-data-type-mappings)
2. [Oracle SQL → Fabric SQL Function Mappings](#2-oracle-sql--fabric-sql-function-mappings)
3. [OAC Expression → DAX Translation Rules](#3-oac-expression--dax-translation-rules)
4. [RPD Logical Model → TMDL Semantic Model Mapping](#4-rpd-logical-model--tmdl-semantic-model-mapping)
5. [OAC Visual → Power BI Visual Type Mappings](#5-oac-visual--power-bi-visual-type-mappings)
6. [Security Model Mappings](#6-security-model-mappings)
7. [Essbase → Fabric & Power BI Mappings](#7-essbase--fabric--power-bi-mappings)

---

## 1. Oracle → Fabric Data Type Mappings

*Owned by: Schema Agent (02) — `src/agents/schema/type_mapper.py`*

### 1A. Oracle → Fabric Lakehouse (Spark/Delta)

| Oracle Type | Fabric Delta Type | Notes |
|---|---|---|
| `NUMBER(p,0)` where p ≤ 9 | `INT` | Integer |
| `NUMBER(p,0)` where p ≤ 18 | `BIGINT` | Long integer |
| `NUMBER(p,0)` where p > 18 | `DECIMAL(p,0)` | Large precision |
| `NUMBER(p,s)` | `DECIMAL(p,s)` | Exact numeric |
| `NUMBER` (no precision) | `DOUBLE` | Floating point |
| `VARCHAR2(n)` | `STRING` | UTF-8 string |
| `NVARCHAR2(n)` | `STRING` | UTF-8 string |
| `CHAR(n)` / `NCHAR(n)` | `STRING` | Fixed-width → variable |
| `CLOB` / `NCLOB` | `STRING` | Large text |
| `DATE` | `TIMESTAMP` | Oracle DATE includes time |
| `TIMESTAMP` | `TIMESTAMP` | Direct map |
| `TIMESTAMP WITH TIME ZONE` | `TIMESTAMP` | Convert to UTC |
| `TIMESTAMP WITH LOCAL TIME ZONE` | `TIMESTAMP` | Convert to UTC |
| `BLOB` | `BINARY` | Binary data |
| `RAW(n)` | `BINARY` | Binary data |
| `FLOAT` | `DOUBLE` | IEEE 754 |
| `BINARY_FLOAT` | `FLOAT` | Single-precision |
| `BINARY_DOUBLE` | `DOUBLE` | Double-precision |
| `XMLTYPE` | `STRING` | Serialized as XML string |
| `INTERVAL` | `STRING` | Serialized as ISO 8601 |
| `LONG` | `STRING` | Legacy type |
| `LONG RAW` | `BINARY` | Legacy type |
| `BOOLEAN` | `BOOLEAN` | Oracle 23c |
| `INTEGER` / `INT` / `SMALLINT` | `INT` | Integer alias |
| *Unknown type* | `STRING` | Fallback (`is_fallback=True`) |

### 1B. Oracle → Fabric Warehouse (T-SQL)

| Oracle Type | Fabric Warehouse Type | Notes |
|---|---|---|
| `NUMBER(p,0)` p ≤ 9 | `INT` | |
| `NUMBER(p,0)` p ≤ 18 | `BIGINT` | |
| `NUMBER(p,0)` p > 18 | `DECIMAL(p,0)` | |
| `NUMBER(p,s)` | `DECIMAL(p,s)` | |
| `NUMBER` (no precision) | `FLOAT` | |
| `VARCHAR2(n)` | `VARCHAR(n)` | |
| `NVARCHAR2(n)` | `VARCHAR(n)` | |
| `CHAR(n)` / `NCHAR(n)` | `CHAR(n)` | |
| `CLOB` / `NCLOB` | `VARCHAR(MAX)` | |
| `DATE` | `DATETIME2` | |
| `TIMESTAMP` | `DATETIME2(7)` | |
| `TIMESTAMP WITH TIME ZONE` | `DATETIME2(7)` | Converted to UTC |
| `BLOB` | `VARBINARY(MAX)` | |
| `RAW(n)` | `VARBINARY(MAX)` | |
| `FLOAT` | `FLOAT` | |
| `BINARY_FLOAT` | `REAL` | |
| `BINARY_DOUBLE` | `FLOAT` | |
| `XMLTYPE` | `VARCHAR(MAX)` | Serialized as XML string |
| `INTERVAL` | `VARCHAR(100)` | Serialized as ISO 8601 |
| `LONG` | `VARCHAR(MAX)` | Legacy |
| `LONG RAW` | `VARBINARY(MAX)` | Legacy |
| `BOOLEAN` | `BOOLEAN` | |
| `INTEGER` / `INT` / `SMALLINT` | `INT` | |
| *Unknown type* | `VARCHAR(MAX)` | Fallback |

---

## 2. Oracle SQL → Fabric SQL Function Mappings

*Owned by: Schema Agent (02) — `src/agents/schema/sql_translator.py`*

### 2A. Function Rewrites

| Oracle Function/Syntax | Spark SQL (Lakehouse) | T-SQL (Warehouse) |
|---|---|---|
| `NVL(a, b)` | `COALESCE(a, b)` | `COALESCE(a, b)` |
| `NVL2(a, b, c)` | `CASE WHEN a IS NOT NULL THEN b ELSE c END` | `CASE WHEN a IS NOT NULL THEN b ELSE c END` |
| `DECODE(a, b, c, d)` | `CASE WHEN a = b THEN c ELSE d END` | `CASE WHEN a = b THEN c ELSE d END` |
| `DECODE(a, b1, c1, b2, c2, d)` | multi-branch CASE | multi-branch CASE |
| `SYSDATE` | `CURRENT_TIMESTAMP()` | `GETDATE()` |
| `SYSTIMESTAMP` | `CURRENT_TIMESTAMP()` | `SYSDATETIMEOFFSET()` |
| `TO_CHAR(date, fmt)` | `DATE_FORMAT(date, fmt)` | `FORMAT(date, fmt)` |
| `TO_DATE(str, fmt)` | `TO_DATE(str, fmt)` | `CONVERT(DATE, str, 120)` |
| `TO_NUMBER(a)` | `CAST(a AS DOUBLE)` | `CAST(a AS FLOAT)` |
| `SUBSTR(a, b, c)` | `SUBSTRING(a, b, c)` | `SUBSTRING(a, b, c)` |
| `INSTR(string, substr)` | `LOCATE(substr, string)` | `CHARINDEX(substr, string)` |
| `LENGTH(a)` | `LENGTH(a)` | `LEN(a)` |
| `TRUNC(date)` | `DATE_TRUNC('day', date)` | `CAST(date AS DATE)` |
| `MONTHS_BETWEEN(a, b)` | `MONTHS_BETWEEN(a, b)` | `DATEDIFF(month, b, a)` |
| `LISTAGG(col, sep) WITHIN GROUP (ORDER BY ...)` | `CONCAT_WS(sep, COLLECT_LIST(col))` | `STRING_AGG(col, sep) WITHIN GROUP (ORDER BY ...)` |
| `ROWNUM` | Flagged → `ROW_NUMBER() OVER(...)` | Flagged → `ROW_NUMBER() OVER(...)` |
| `(+)` outer join | Flagged → manual review | Flagged → manual review |
| `FROM DUAL` | *(removed)* | *(removed)* |
| `\|\|` (concat) | `CONCAT(a, b, ...)` | `CONCAT(a, b, ...)` |
| `USER` | `CURRENT_USER()` | `CURRENT_USER` |

### 2B. Date Format Token Translation

| Oracle Token | Spark (Java SimpleDateFormat) | T-SQL (.NET format) |
|---|---|---|
| `YYYY` | `yyyy` | `yyyy` |
| `YY` | `yy` | `yy` |
| `MM` | `MM` | `MM` |
| `MON` | `MMM` | `MMM` |
| `MONTH` | `MMMM` | `MMMM` |
| `DD` | `dd` | `dd` |
| `DY` | `EEE` | `ddd` |
| `DAY` | `EEEE` | `dddd` |
| `HH24` | `HH` | `HH` |
| `HH12` | `hh` | `hh` |
| `HH` | `hh` | `hh` |
| `MI` | `mm` | `mm` |
| `SS` | `ss` | `ss` |
| `FF` | `SSS` | `fff` |
| `AM` / `PM` | `a` | `tt` |

---

## 3. OAC Expression → DAX Translation Rules

*Owned by: Semantic Model Agent (04) — `src/core/expression_translator.py`, `src/core/translation_catalog.py`*

### 3A. Aggregate Functions

| OAC Function | DAX Equivalent | Difficulty |
|---|---|---|
| `SUM(column)` | `SUM(Table[Column])` | Direct |
| `COUNT(column)` | `COUNT(Table[Column])` | Direct |
| `COUNTDISTINCT(column)` | `DISTINCTCOUNT(Table[Column])` | Direct |
| `AVG(column)` | `AVERAGE(Table[Column])` | Direct |
| `MIN(column)` | `MIN(Table[Column])` | Direct |
| `MAX(column)` | `MAX(Table[Column])` | Direct |
| `MEDIAN(column)` | `MEDIAN(Table[Column])` | Direct |
| `STDDEV(column)` | `STDEV.S(Table[Column])` | Direct |
| `VARIANCE(column)` | `VAR.S(Table[Column])` | Direct |
| `COUNT(*)` / `COUNT_STAR` | `COUNTROWS(table)` | Parametric |

### 3B. Time Intelligence Functions

| OAC Function | DAX Equivalent | Difficulty |
|---|---|---|
| `AGO(measure, time, N)` | `CALCULATE(measure, DATEADD('Date'[Date], -N, period))` | Parametric |
| `TODATE(measure, YEAR)` | `CALCULATE(measure, DATESYTD('Date'[Date]))` | Parametric |
| `TODATE(measure, QUARTER)` | `CALCULATE(measure, DATESQTD('Date'[Date]))` | Parametric |
| `TODATE(measure, MONTH)` | `CALCULATE(measure, DATESMTD('Date'[Date]))` | Parametric |
| `PERIODROLLING(measure, N)` | `CALCULATE(measure, DATESINPERIOD('Date'[Date], MAX('Date'[Date]), N, DAY))` | Complex |
| `RSUM(measure)` | `CALCULATE(measure, FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date])))` | Complex |
| `MAVG(measure, N)` | `CALCULATE(measure, DATESINPERIOD(..., -N, DAY)) / N` | Complex |
| `SAMEPERIODLASTYEAR` | `SAMEPERIODLASTYEAR(...)` | Direct |
| `PARALLELPERIOD` | `PARALLELPERIOD(...)` | Direct |
| `DATESYTD` / `DATESMTD` / `DATESQTD` | `DATESYTD(...)` / `DATESMTD(...)` / `DATESQTD(...)` | Direct |
| `FIRSTDATE` / `LASTDATE` | `FIRSTDATE(...)` / `LASTDATE(...)` | Direct |
| `OPENINGBALANCEYEAR` / `CLOSINGBALANCEYEAR` | Direct DAX equivalent | Direct |
| `PREVIOUSYEAR` / `PREVIOUSMONTH` / `PREVIOUSQUARTER` | Direct DAX equivalent | Direct |
| `NEXTYEAR` / `NEXTMONTH` / `NEXTQUARTER` | Direct DAX equivalent | Direct |

### 3C. String Functions

| OAC Function | DAX Equivalent | Difficulty |
|---|---|---|
| `UPPER(col)` | `UPPER(col)` | Direct |
| `LOWER(col)` | `LOWER(col)` | Direct |
| `TRIM(col)` | `TRIM(col)` | Direct |
| `LENGTH(col)` | `LEN(col)` | Direct |
| `SUBSTRING(col, s, l)` / `SUBSTR(col, s, l)` | `MID(col, s, l)` | Parametric |
| `REPLACE(col, old, new)` | `SUBSTITUTE(col, old, new)` | Parametric |
| `CONCAT(a, b)` | `a & b` or `CONCATENATE(a, b)` | Direct |
| `INSTR(string, substring)` | `FIND(substring, string)` | Parametric |
| `LPAD(col, n, char)` | `REPT(char, n - LEN(col)) & col` | Complex |
| `RPAD(col, n, char)` | `col & REPT(char, n - LEN(col))` | Complex |
| `LEFT(col, n)` / `RIGHT(col, n)` | `LEFT(col, n)` / `RIGHT(col, n)` | Direct |
| `INITCAP(col)` | `PROPER(col)` | Direct |
| `REGEXP(...)` | `CONTAINSSTRING(...)` | Complex |
| `\|\|` (string concat) | `&` | Direct |

### 3D. Math Functions

| OAC Function | DAX Equivalent | Notes |
|---|---|---|
| `ABS` | `ABS` | Direct |
| `CEILING` | `CEILING(expr, 1)` | DAX takes significance param |
| `FLOOR` | `FLOOR(expr, 1)` | DAX takes significance param |
| `ROUND` | `ROUND` | Direct |
| `MOD` | `MOD` | Direct |
| `POWER` | `POWER` | Direct |
| `LOG` / `LOG10` | `LOG` / `LOG10` | Direct |
| `EXP` / `SQRT` / `SIGN` | `EXP` / `SQRT` / `SIGN` | Direct |
| `TRUNCATE` | `TRUNC` | Direct |
| `PI` / `RAND` | `PI()` / `RAND()` | Direct |

### 3E. Date Functions

| OAC Function | DAX Equivalent | Difficulty |
|---|---|---|
| `CURRENT_DATE` | `TODAY()` | Direct |
| `CURRENT_TIMESTAMP` | `NOW()` | Direct |
| `EXTRACT(YEAR FROM date)` | `YEAR(date)` | Direct |
| `EXTRACT(MONTH FROM date)` | `MONTH(date)` | Direct |
| `EXTRACT(DAY FROM date)` | `DAY(date)` | Direct |
| `EXTRACT(HOUR FROM date)` | `HOUR(date)` | Direct |
| `EXTRACT(MINUTE FROM date)` | `MINUTE(date)` | Direct |
| `EXTRACT(SECOND FROM date)` | `SECOND(date)` | Direct |
| `EXTRACT(QUARTER FROM date)` | `QUARTER(date)` | Direct |
| `EXTRACT(WEEK FROM date)` | `WEEKNUM(date)` | Direct |
| `EXTRACT(DOW FROM date)` | `WEEKDAY(date)` | Direct |
| `EXTRACT(DOY FROM date)` | `DAYOFYEAR(date)` | Direct |
| `ADD_MONTHS(date, n)` | `EDATE(date, n)` | Parametric |
| `TIMESTAMPADD(SQL_TSI_X, n, date)` | `DATEADD('Date'[Date], n, X)` | Parametric |
| `TIMESTAMPDIFF(SQL_TSI_X, s, e)` | `DATEDIFF(s, e, X)` | Parametric |
| `MONTHS_BETWEEN(d1, d2)` | `DATEDIFF(d2, d1, MONTH)` | Parametric |
| `MONTHNAME(date)` | `FORMAT(date, "MMMM")` | Parametric |
| `DAYNAME(date)` | `FORMAT(date, "dddd")` | Parametric |
| `EOMONTH(date)` | `EOMONTH(date)` | Direct |

### 3F. Logical Functions

| OAC Function | DAX Equivalent | Difficulty |
|---|---|---|
| `CASE WHEN ... THEN ... ELSE ... END` | `SWITCH(TRUE(), cond, val, ..., default)` | Parametric |
| `IIF(cond, a, b)` | `IF(cond, a, b)` | Direct |
| `IFNULL(a, b)` / `NVL(a, b)` | `COALESCE(a, b)` | Direct |
| `NULLIF(a, b)` | `IF(a = b, BLANK(), a)` | Parametric |
| `COALESCE(...)` | `COALESCE(...)` | Direct |
| `ISBLANK(col)` / `ISNULL(col)` | `ISBLANK(col)` | Direct |

### 3G. Filter / Table Functions

| OAC Function | DAX Equivalent | Difficulty |
|---|---|---|
| `FILTER(column USING (expr))` | `CALCULATE(measure, filter)` | Parametric |
| `EVALUATE_PREDICATE(a, b)` | `CALCULATE(a, b)` / `CALCULATETABLE` | Parametric |
| `FILTER` / `ALL` / `ALLEXCEPT` | Direct DAX equivalent | Direct |
| `RELATED` / `RELATEDTABLE` | Direct DAX equivalent | Direct |
| `VALUES` / `DISTINCT` | Direct DAX equivalent | Direct |

### 3H. Statistical Functions

| OAC Function | DAX Equivalent | Difficulty |
|---|---|---|
| `PERCENTILE` | `PERCENTILEX.INC` | Parametric |
| `RANK(measure)` | `RANKX(ALL(Table), measure)` | Complex |
| `NTILE` | `RANKX`-based pattern | Complex |
| `TOPN(N, measure)` | `TOPN(N, Table, measure)` | Direct |

### 3I. Level-Based & Information Functions

| OAC Function | DAX Equivalent | Difficulty |
|---|---|---|
| `AGGREGATE_AT_LEVEL` | `CALCULATE + ALLEXCEPT` | Complex |
| `SHARE` | `DIVIDE([M], CALCULATE([M], ALL(dim)))` | Complex |
| `CAST(col AS type)` | `CONVERT` / `INT` / `VALUE` / `DATEVALUE` | Parametric |
| `VALUEOF(NQ_SESSION.var)` | `USERPRINCIPALNAME()` | Direct |
| `DESCRIPTOR_IDOF(col)` | Column key reference (passthrough) | Direct |
| `INDEXCOL(...)` | Column reference (passthrough) | Direct |

### 3J. CAST Type Map

| Oracle Target Type | DAX Function |
|---|---|
| `INT` / `INTEGER` | `INT(expr)` |
| `NUMBER` / `FLOAT` / `DOUBLE` / `DECIMAL` | `VALUE(expr)` |
| `VARCHAR` / `VARCHAR2` / `CHAR` / `STRING` | `FORMAT(expr, "General")` |
| `DATE` / `TIMESTAMP` | `DATEVALUE(expr)` |
| *Other* | `CONVERT(expr, type)` |

---

## 4. RPD Logical Model → TMDL Semantic Model Mapping

*Owned by: Semantic Model Agent (04) — `src/agents/semantic/rpd_model_parser.py`, `src/agents/semantic/tmdl_generator.py`*

### 4A. RPD → TMDL Concepts

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

### 4B. RPD Join → TMDL Relationship

| RPD Join Property | TMDL Relationship Property |
|---|---|
| Join type (inner/outer) | `crossFilteringBehavior` |
| 1:N cardinality | `fromCardinality: one`, `toCardinality: many` |
| M:N cardinality | `fromCardinality: many`, `toCardinality: many` (requires bridge) |
| Join columns | `fromColumn`, `toColumn` |
| Join expression (complex) | May require calculated column |

---

## 5. OAC Visual → Power BI Visual Type Mappings

*Owned by: Report Agent (05) — `src/agents/report/visual_mapper.py`*

### 5A. Chart / View Type Mapping

| OAC View / Chart Type | PBI Visual Type ID | Notes |
|---|---|---|
| Table | `tableEx` | Direct column mapping |
| Pivot Table | `pivotTable` (Matrix) | Row/Col/Value mapping |
| Vertical Bar | `clusteredColumnChart` | Category + Value |
| Horizontal Bar | `clusteredBarChart` | Category + Value |
| Stacked Bar | `stackedBarChart` | Category + Series + Value |
| Stacked Column | `stackedColumnChart` | Category + Series + Value |
| Line Chart | `lineChart` | Axis + Values + Legend |
| Area Chart | `areaChart` | Axis + Values |
| Combo Chart (Bar+Line) | `lineClusteredColumnComboChart` | Dual axis |
| Pie Chart | `pieChart` | Category + Values |
| Donut Chart | `donutChart` | Category + Values |
| Scatter Plot | `scatterChart` | X + Y + Size + Color |
| Bubble Chart | `scatterChart` (with size) | Size field configured |
| Map (filled) | `filledMap` | Location + Value |
| Map (bubble) | `map` | Lat/Long + Size |
| Gauge | `gauge` | Value + Min + Max + Target |
| KPI / Metric | `card` | Single value display |
| Funnel | `funnel` | Category + Values |
| Treemap | `treemap` | Group + Values |
| Heatmap | `pivotTable` (Matrix) | + conditional formatting |
| Waterfall | `waterfallChart` | Category + Values |
| Narrative / Text | `textbox` | Rich text |
| Image | `image` | Static image |
| Trellis / Small Multiples | `clusteredColumnChart` | + Small Multiples field |
| *Unknown type* | `tableEx` | Fallback default |

### 5B. PBI Visual Data Roles

| PBI Visual Type | Data Roles |
|---|---|
| `tableEx` | Values |
| `pivotTable` (Matrix) | Rows, Columns, Values |
| `clusteredBarChart` / `clusteredColumnChart` | Category, Y |
| `stackedBarChart` / `stackedColumnChart` | Category, Series, Y |
| `lineChart` | Category, Y, Series |
| `areaChart` | Category, Y |
| `lineClusteredColumnComboChart` | Category, ColumnY, LineY |
| `pieChart` / `donutChart` | Category, Y |
| `scatterChart` | X, Y, Size, Legend |
| `filledMap` | Location, Values |
| `map` | Latitude, Longitude, Size |
| `gauge` | Y, MinValue, MaxValue, TargetValue |
| `card` / `multiRowCard` | Fields |
| `funnel` | Category, Y |
| `treemap` | Group, Values |
| `waterfallChart` | Category, Y |

### 5C. OAC Prompt → Power BI Slicer/Parameter

| OAC Prompt Type | Power BI Equivalent |
|---|---|
| Dropdown (single select) | Slicer (dropdown, single select) |
| Dropdown (multi select) | Slicer (dropdown, multi select) |
| Search / Type-ahead | Slicer with search enabled |
| Slider (range) | Slicer (between range) |
| Date Picker | Slicer (date range / relative date) |
| Radio Button | Slicer (tile style, single select) |
| Checkbox | Slicer (tile style, multi select) |
| Text Input | What-if parameter or text filter |
| Cascading Prompt | Multiple slicers with relationship-based filtering |

### 5D. Formatting Translation

| OAC Formatting | Power BI Equivalent |
|---|---|
| Conditional formatting (color) | Conditional formatting rules (field value rules) |
| Data bars | Data bars in table/matrix |
| Stoplight (icon set) | Icons conditional formatting |
| Number format (#,##0.00) | Format string in visual config |
| Font / size / color | Visual formatting pane settings |
| Borders | Visual border settings |
| Background color | Visual background fill |
| Sorting (column, direction) | Sort settings in visual config |

### 5E. Number/Date Format Strings

| OAC Format | PBI Format |
|---|---|
| `#,##0` | `#,0` |
| `#,##0.00` | `#,0.00` |
| `#,##0.0` | `#,0.0` |
| `0.00%` | `0.00%` |
| `0%` | `0%` |
| `$#,##0.00` | `$#,0.00` |
| `€#,##0.00` | `€#,0.00` |
| `yyyy-MM-dd` | `yyyy-MM-dd` |
| `MM/dd/yyyy` | `M/d/yyyy` |
| `dd/MM/yyyy` | `d/M/yyyy` |

### 5F. Dashboard Actions → PBI Interactivity

| OAC Action | PBI Equivalent |
|---|---|
| Navigate to analysis | Drillthrough page |
| Navigate to URL | Button with URL action |
| Navigate to dashboard page | Page navigation button / bookmark |
| Filter on click | Cross-filter (default PBI behavior) |
| Master-detail | Drillthrough with context |
| Guided navigation | Bookmarks + buttons |

---

## 6. Security Model Mappings

*Owned by: Security Agent (06) — `src/agents/security/`*

### 6A. OAC Roles → Fabric/PBI Roles

| OAC Concept | Fabric/PBI Equivalent |
|---|---|
| Application Role | Power BI RLS Role + Fabric Workspace Role |
| User → Role assignment | Azure AD Security Group → RLS Role membership |
| Row-level filter (session variable) | RLS DAX filter expression |
| Object permission (hide column/table) | OLS `none` permission |
| Data-level security (init block) | RLS with `USERPRINCIPALNAME()` or lookup table |

### 6B. OAC Session Variable → PBI RLS Pattern

| OAC Pattern | PBI RLS DAX Equivalent |
|---|---|
| `VALUEOF(NQ_SESSION.USER)` | `USERPRINCIPALNAME()` |
| `VALUEOF(NQ_SESSION.GROUP)` | Lookup: `UserRoles[UserEmail] = USERPRINCIPALNAME()` |
| `VALUEOF(NQ_SESSION.REGION)` | Lookup: `UserRegions[UserEmail] = USERPRINCIPALNAME()` |
| Init block (SQL populates var) | Create security lookup table in Lakehouse |
| Multi-valued session variable | Lookup table with one-to-many mapping |

### 6C. Object-Level Security (OLS)

| OAC Object Permission | PBI OLS Configuration |
|---|---|
| Column hidden for role | `columnPermission: none` (metadataPermission) |
| Table hidden for role | `tablePermission: none` |
| Measure hidden for role | Not natively supported (use perspective) |

### 6D. Fabric Workspace Roles

| OAC Permission Level | Fabric Workspace Role |
|---|---|
| Admin | Admin |
| Content creator / developer | Contributor |
| Report viewer (some edit) | Member |
| Report viewer (read-only) | Viewer |

---

## 7. Essbase → Fabric & Power BI Mappings

*Owned by: Essbase Connector — `src/connectors/essbase_connector.py` (full implementation)*

### 7A. Essbase Calc Script → DAX

| Essbase Function | DAX Equivalent | Difficulty |
|---|---|---|
| `@SUM` | `SUM` | Direct |
| `@AVG` | `AVERAGE` | Direct |
| `@COUNT` | `COUNTROWS` | Parametric |
| `@MIN` | `MIN` | Direct |
| `@MAX` | `MAX` | Direct |
| `@SUMRANGE` | `CALCULATE(SUM, DATESINPERIOD)` | Complex |
| `@AVGRANGE` | `CALCULATE(AVERAGE, DATESINPERIOD)` | Complex |
| `@PRIOR` | `CALCULATE(measure, PREVIOUSMONTH)` | Parametric |
| `@NEXT` | `CALCULATE(measure, NEXTMONTH)` | Parametric |
| `@PARENTVAL` | `CALCULATE(measure, ALLEXCEPT)` | Complex |
| `@ANCEST` | `CALCULATE(measure, ALL)` | Complex |
| `@CHILDREN` | `FILTER + hierarchy` | Complex |
| `@DESCENDANTS` | `FILTER + PATH` | Complex |
| `@SIBLINGS` | `FILTER + ALLEXCEPT` | Complex |
| `@PARENT` | `LOOKUPVALUE + hierarchy` | Complex |
| `@ISMBR` | `HASONEVALUE / SELECTEDVALUE` | Parametric |
| `@ISLEV` / `@ISGEN` | hierarchy level/generation check | Complex |
| `@ALLOCATE` | manual DAX pattern | Complex |
| `@ABS` | `ABS` | Direct |
| `@ROUND` | `ROUND` | Direct |
| `@POWER` | `POWER` | Direct |
| `@LOG` / `@LOG10` | `LOG` / `LOG10` | Direct |
| `@EXP` / `@SQRT` | `EXP` / `SQRT` | Direct |
| `@MOD` | `MOD` | Direct |
| `@TRUNCATE` | `TRUNC` | Direct |
| `IF/ELSEIF/ELSE/ENDIF` | `IF / SWITCH(TRUE())` | Parametric |
| `@VAR` | variance `CALCULATE` pattern | Complex |
| `@VARPER` | `DIVIDE(variance, base)` | Complex |
| `TB First` | `FIRSTNONBLANK` | Parametric |
| `TB Last` | `LASTNONBLANK` | Parametric |
| `TB Average` | `AVERAGEX over date` | Complex |

### 7B. Essbase MDX → DAX

| Essbase MDX | DAX Equivalent | Notes |
|---|---|---|
| `[Measures].[member]` | `Table[Measure]` | Measure reference |
| `[Dim].CurrentMember` | `SELECTEDVALUE(Table[Column])` | Current member |
| `[Dim].Children` | `VALUES(Table[Column])` | Children → VALUES |
| `[Dim].Parent` | `LOOKUPVALUE(parent, ...)` | Parent navigation |
| `Aggregate(set)` | `CALCULATE(SUM, filter)` | Set aggregation |
| `Filter(set, condition)` | `CALCULATE(measure, FILTER)` | MDX Filter → DAX FILTER |
| `CrossJoin(set1, set2)` | `CROSSJOIN(Table1, Table2)` | Cross join |
| `IIF(cond, true, false)` | `IF(cond, true, false)` | Conditional |
| `IsEmpty(expr)` | `ISBLANK(expr)` | Empty test |
| `.Lag(n)` / `.Lead(n)` | `CALCULATE(measure, DATEADD)` | Lag/Lead → DATEADD |
| `PeriodsToDate` | `DATESYTD / DATESMTD / DATESQTD` | Period to date |
| `ParallelPeriod` | `PARALLELPERIOD` | Parallel period |
| `YTD(member)` | `CALCULATE(measure, DATESYTD)` | Year to date |
| `QTD(member)` | `CALCULATE(measure, DATESQTD)` | Quarter to date |
| `MTD(member)` | `CALCULATE(measure, DATESMTD)` | Month to date |

### 7C. Essbase Outline → TMDL Semantic Model

| Essbase Concept | TMDL / Power BI Concept |
|---|---|
| Cube | Semantic Model |
| Dimension (Accounts) | Measures + Calculated Columns |
| Dimension (Time) | Date Table (mark as date table) |
| Dimension (Regular) | Table with hierarchy |
| Dimension (Attribute) | Column on parent dimension table |
| Generation | Hierarchy Level |
| Level0 Member | Leaf-level row in dimension table |
| Upper-level Member | Parent in parent-child hierarchy |
| Dense Dimension | Column (inline in fact if small) |
| Sparse Dimension | Separate dimension table with relationship |
| Stored Member | Column / Row |
| Dynamic Calc Member | DAX Measure |
| Calc Script | DAX Measures + Calculated Tables |
| Business Rule | DAX Measures (or Fabric Notebook for ETL) |
| Essbase Filter (Security) | RLS Role (DAX filter) |
| Substitution Variable | What-if Parameter or DAX variable |
| UDA | Column on dimension table |
| Alias Table | Display name mapping (translations) |
| Shared Member | Alternate hierarchy (role-playing dimension) |
| Data Cell | Fact table row (measures + dimension keys) |
| ASO Cube | Import mode semantic model |
| BSO Cube | Import mode with scheduled refresh |

---

## Summary

| Category | Count |
|----------|-------|
| Oracle → Fabric data type mappings | 25+ per target |
| Oracle SQL function rewrites | 20+ |
| OAC → DAX expression rules | 80+ |
| Date format token translations | 15 |
| Visual type mappings | 24 |
| Prompt → slicer mappings | 9 |
| Action → interactivity mappings | 6 |
| Security concept mappings | 12+ |
| Essbase calc script → DAX rules | 55+ |
| Essbase MDX → DAX rules | 24+ |
| Essbase → TMDL concept mappings | 22 |

---

## Related Docs

- [Architecture](ARCHITECTURE.md) — System architecture and data flow
- [Agent SPECs](../agents/) — Per-agent technical specifications
- [Known Limitations](KNOWN_LIMITATIONS.md) — Translation gaps and workarounds
- [Gap Analysis](GAP_ANALYSIS.md) — Implementation coverage assessment
