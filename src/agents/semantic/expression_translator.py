"""OAC Expression → DAX translator.

Converts Oracle Analytics Cloud calculated column / measure expressions
to equivalent DAX (Data Analysis Expressions) for Power BI Semantic Models.

Translation strategy:
  1. Rule-based mapping for known OAC functions (≈120+ patterns)
  2. LLM-assisted translation for complex / unmapped expressions
  3. Untranslatable expressions flagged for manual review
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class DAXTranslation:
    """Result of translating one OAC expression to DAX."""

    column_name: str
    table_name: str
    original_expression: str
    dax_expression: str
    method: str = "rule-based"      # rule-based | llm | manual
    confidence: float = 1.0
    is_measure: bool = False
    format_string: str = ""
    display_folder: str = ""
    warnings: list[str] = field(default_factory=list)
    requires_review: bool = False


# ---------------------------------------------------------------------------
# OAC → DAX rule table
# ---------------------------------------------------------------------------

# Each rule: (regex, replacement_template, description, is_measure_hint)
# Replacement templates use {table} and {col} for qualified references.
# They can also use regex group backreferences (\1, \2, etc.)

_AGGREGATE_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\bSUM\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"SUM({tbl}[\1])",
        "SUM → SUM",
    ),
    # COUNT(*) → COUNTROWS  (must precede generic COUNT)
    (
        re.compile(r"\bCOUNT\s*\(\s*\*\s*\)", re.IGNORECASE),
        r"COUNTROWS({tbl})",
        "COUNT(*) → COUNTROWS",
    ),
    (
        re.compile(r"\bCOUNT\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"COUNT({tbl}[\1])",
        "COUNT → COUNT",
    ),
    (
        re.compile(r"\bCOUNTDISTINCT\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"DISTINCTCOUNT({tbl}[\1])",
        "COUNTDISTINCT → DISTINCTCOUNT",
    ),
    (
        re.compile(r"\bAVG\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"AVERAGE({tbl}[\1])",
        "AVG → AVERAGE",
    ),
    (
        re.compile(r"\bMIN\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"MIN({tbl}[\1])",
        "MIN → MIN",
    ),
    (
        re.compile(r"\bMAX\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"MAX({tbl}[\1])",
        "MAX → MAX",
    ),
    # STDEV(col) → STDEV.S
    (
        re.compile(r"\bSTDDEV\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"STDEV.S({tbl}[\1])",
        "STDDEV → STDEV.S",
    ),
    (
        re.compile(r"\bSTDDEV_POP\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"STDEV.P({tbl}[\1])",
        "STDDEV_POP → STDEV.P",
    ),
    # VARIANCE / VAR
    (
        re.compile(r"\bVARIANCE\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"VAR.S({tbl}[\1])",
        "VARIANCE → VAR.S",
    ),
    (
        re.compile(r"\bVAR_POP\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"VAR.P({tbl}[\1])",
        "VAR_POP → VAR.P",
    ),
    # MEDIAN
    (
        re.compile(r"\bMEDIAN\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"MEDIAN({tbl}[\1])",
        "MEDIAN → MEDIAN",
    ),
    # PERCENTILE
    (
        re.compile(r"\bPERCENTILE\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"PERCENTILEX.INC({tbl}, {tbl}[\1], \2)",
        "PERCENTILE → PERCENTILEX.INC",
    ),
    # COUNTIF(col, condition) → COUNTAX with filter
    (
        re.compile(r"\bCOUNTIF\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"CALCULATE(COUNT({tbl}[\1]), \2)",
        "COUNTIF → CALCULATE+COUNT",
    ),
    # SUMIF(col, condition) → CALCULATE(SUM)
    (
        re.compile(r"\bSUMIF\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"CALCULATE(SUM({tbl}[\1]), \2)",
        "SUMIF → CALCULATE+SUM",
    ),
    # FIRST / LAST → FIRSTNONBLANK / LASTNONBLANK
    (
        re.compile(r"\bFIRST\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"FIRSTNONBLANK({tbl}[\1], 1)",
        "FIRST → FIRSTNONBLANK",
    ),
    (
        re.compile(r"\bLAST\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"LASTNONBLANK({tbl}[\1], 1)",
        "LAST → LASTNONBLANK",
    ),
    # RATIO_TO_REPORT(measure) → DIVIDE(measure, CALCULATE(measure, ALL(tbl)))
    (
        re.compile(r"\bRATIO_TO_REPORT\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"DIVIDE(\1, CALCULATE(\1, ALL({tbl})))",
        "RATIO_TO_REPORT → DIVIDE+ALL",
    ),
]

# Time-intelligence rules (these produce CALCULATE-based DAX)
_TIME_INTEL_RULES: list[tuple[re.Pattern[str], str, str]] = [
    # AGO(measure, time_level, N) → CALCULATE(measure, DATEADD(Date[Date], -N, period))
    (
        re.compile(
            r"\bAGO\s*\(\s*(.+?)\s*,\s*(\w+)\s*,\s*(\d+)\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, DATEADD('Date'[Date], -\3, \2))",
        "AGO → CALCULATE + DATEADD",
    ),
    # TODATE(measure, time_level) → CALCULATE(measure, DATESYTD|DATESQTD|DATESMTD)
    (
        re.compile(
            r"\bTODATE\s*\(\s*(.+?)\s*,\s*['\"]?YEAR['\"]?\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, DATESYTD('Date'[Date]))",
        "TODATE(YEAR) → DATESYTD",
    ),
    (
        re.compile(
            r"\bTODATE\s*\(\s*(.+?)\s*,\s*['\"]?QUARTER['\"]?\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, DATESQTD('Date'[Date]))",
        "TODATE(QUARTER) → DATESQTD",
    ),
    (
        re.compile(
            r"\bTODATE\s*\(\s*(.+?)\s*,\s*['\"]?MONTH['\"]?\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, DATESMTD('Date'[Date]))",
        "TODATE(MONTH) → DATESMTD",
    ),
    # PERIODROLLING(measure, N) → DATESINPERIOD
    (
        re.compile(
            r"\bPERIODROLLING\s*\(\s*(.+?)\s*,\s*(-?\d+)\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, DATESINPERIOD('Date'[Date], MAX('Date'[Date]), \2, DAY))",
        "PERIODROLLING → DATESINPERIOD",
    ),
    # RSUM(measure) → running sum
    (
        re.compile(r"\bRSUM\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"CALCULATE(\1, FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date])))",
        "RSUM → running sum with CALCULATE",
    ),
    # MAVG(measure, N) → moving average
    (
        re.compile(
            r"\bMAVG\s*\(\s*(.+?)\s*,\s*(\d+)\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -\2, DAY)) / \2",
        "MAVG → moving average",
    ),
    # MSUM(measure, N) → moving sum
    (
        re.compile(
            r"\bMSUM\s*\(\s*(.+?)\s*,\s*(\d+)\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -\2, DAY))",
        "MSUM → moving sum",
    ),
    # RCOUNT(measure) → running count
    (
        re.compile(r"\bRCOUNT\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"CALCULATE(COUNTROWS({tbl}), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date])))",
        "RCOUNT → running count",
    ),
    # RMAX / RMIN → running max / running min
    (
        re.compile(r"\bRMAX\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"CALCULATE(MAX(\1), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date])))",
        "RMAX → running max",
    ),
    (
        re.compile(r"\bRMIN\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"CALCULATE(MIN(\1), FILTER(ALL('Date'), 'Date'[Date] <= MAX('Date'[Date])))",
        "RMIN → running min",
    ),
    # TODATE with WEEK → DATESINPERIOD
    (
        re.compile(
            r"\bTODATE\s*\(\s*(.+?)\s*,\s*['\"]?WEEK['\"]?\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -7, DAY))",
        "TODATE(WEEK) → DATESINPERIOD 7 days",
    ),
    # PARALLELPERIOD — same period prior year
    (
        re.compile(
            r"\bPARALLELPERIOD\s*\(\s*(.+?)\s*,\s*(-?\d+)\s*,\s*(\w+)\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, PARALLELPERIOD('Date'[Date], \2, \3))",
        "PARALLELPERIOD → PARALLELPERIOD",
    ),
    # OPENINGBALANCEYEAR / CLOSINGBALANCEYEAR
    (
        re.compile(r"\bOPENINGBALANCE(?:YEAR)?\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"OPENINGBALANCEYEAR(\1, 'Date'[Date])",
        "OPENINGBALANCEYEAR",
    ),
    (
        re.compile(r"\bCLOSINGBALANCE(?:YEAR)?\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"CLOSINGBALANCEYEAR(\1, 'Date'[Date])",
        "CLOSINGBALANCEYEAR",
    ),
]

# Scalar / row-level function rules
_SCALAR_RULES: list[tuple[re.Pattern[str], str, str]] = [
    # IFNULL(a, b) → IF(ISBLANK(a), b, a)
    (
        re.compile(r"\bIFNULL\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"IF(ISBLANK(\1), \2, \1)",
        "IFNULL → IF/ISBLANK",
    ),
    # NVL(a, b) → IF(ISBLANK(a), b, a)
    (
        re.compile(r"\bNVL\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"IF(ISBLANK(\1), \2, \1)",
        "NVL → IF/ISBLANK",
    ),
    # CONCAT(a, b) → a & b
    (
        re.compile(r"\bCONCAT\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"\1 & \2",
        "CONCAT → &",
    ),
    # CASE WHEN ... THEN ... ELSE ... END
    (
        re.compile(
            r"\bCASE\b(.+?)\bEND\b",
            re.IGNORECASE | re.DOTALL,
        ),
        None,   # Handled by custom logic
        "CASE WHEN → SWITCH",
    ),
    # CAST(col AS type)
    (
        re.compile(r"\bCAST\s*\(\s*(.+?)\s+AS\s+(\w+)\s*\)", re.IGNORECASE),
        None,   # Handled by custom logic
        "CAST → CONVERT/INT/VALUE",
    ),
    # RANK(measure) → RANKX
    (
        re.compile(r"\bRANK\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"RANKX(ALL({tbl}), \1)",
        "RANK → RANKX",
    ),
    # DENSE_RANK(measure) → RANKX with DENSE
    (
        re.compile(r"\bDENSE_RANK\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"RANKX(ALL({tbl}), \1, , ASC, DENSE)",
        "DENSE_RANK → RANKX DENSE",
    ),
    # ROW_NUMBER() → RANKX
    (
        re.compile(r"\bROW_NUMBER\s*\(\s*\)", re.IGNORECASE),
        r"RANKX(ALL({tbl}), 1)",
        "ROW_NUMBER → RANKX",
    ),
    # NTILE(n) → NTILE approximation via PERCENTILE
    (
        re.compile(r"\bNTILE\s*\(\s*(\d+)\s*\)", re.IGNORECASE),
        r"INT(RANKX(ALL({tbl}), 1, , ASC) * \1 / COUNTROWS(ALL({tbl}))) + 1",
        "NTILE → RANKX-based bucket",
    ),
    # LEAD(col, n) → OFFSET (DAX 2023+, requires window)
    (
        re.compile(r"\bLEAD\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"OFFSET(\2, ALLSELECTED({tbl}), ORDERBY({tbl}[\1]))",
        "LEAD → OFFSET (DAX 2023+)",
    ),
    # LEAD(col) — single-arg version (offset 1)
    (
        re.compile(r"\bLEAD\s*\(\s*([^),]+?)\s*\)", re.IGNORECASE),
        r"OFFSET(1, ALLSELECTED({tbl}), ORDERBY({tbl}[\1]))",
        "LEAD → OFFSET 1",
    ),
    # LAG(col, n) → OFFSET negative
    (
        re.compile(r"\bLAG\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"OFFSET(-\2, ALLSELECTED({tbl}), ORDERBY({tbl}[\1]))",
        "LAG → OFFSET negative (DAX 2023+)",
    ),
    # LAG(col) — single-arg version (offset -1)
    (
        re.compile(r"\bLAG\s*\(\s*([^),]+?)\s*\)", re.IGNORECASE),
        r"OFFSET(-1, ALLSELECTED({tbl}), ORDERBY({tbl}[\1]))",
        "LAG → OFFSET -1",
    ),
    # CUME_DIST() → cumulative distribution approx
    (
        re.compile(r"\bCUME_DIST\s*\(\s*\)", re.IGNORECASE),
        r"DIVIDE(RANKX(ALL({tbl}), 1, , ASC), COUNTROWS(ALL({tbl})))",
        "CUME_DIST → RANKX/COUNTROWS",
    ),
    # PERCENT_RANK() → percent rank approx
    (
        re.compile(r"\bPERCENT_RANK\s*\(\s*\)", re.IGNORECASE),
        r"DIVIDE(RANKX(ALL({tbl}), 1, , ASC) - 1, COUNTROWS(ALL({tbl})) - 1)",
        "PERCENT_RANK → (RANKX-1)/(N-1)",
    ),
    # TOPN(N, measure) → TOPN
    (
        re.compile(r"\bTOPN\s*\(\s*(\d+)\s*,\s*(.+?)\s*\)", re.IGNORECASE),
        r"TOPN(\1, {tbl}, \2)",
        "TOPN → TOPN",
    ),
    # FILTER(column USING (filter_expr)) → CALCULATE
    (
        re.compile(
            r"\bFILTER\s*\(\s*(.+?)\s+USING\s*\(\s*(.+?)\s*\)\s*\)",
            re.IGNORECASE | re.DOTALL,
        ),
        r"CALCULATE(\1, \2)",
        "FILTER USING → CALCULATE",
    ),
    # EVALUATE_PREDICATE → CALCULATE filter
    (
        re.compile(
            r"\bEVALUATE_PREDICATE\s*\(\s*(.+?)\s*,\s*(.+?)\s*\)",
            re.IGNORECASE,
        ),
        r"CALCULATE(\1, \2)",
        "EVALUATE_PREDICATE → CALCULATE",
    ),
    # VALUEOF(NQ_SESSION.variable) → USERPRINCIPALNAME()
    (
        re.compile(r"\bVALUEOF\s*\(\s*NQ_SESSION\.\w+\s*\)", re.IGNORECASE),
        "USERPRINCIPALNAME()",
        "Session variable → USERPRINCIPALNAME",
    ),
    # DESCRIPTOR_IDOF(col) → column key reference
    (
        re.compile(r"\bDESCRIPTOR_IDOF\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"\1",
        "DESCRIPTOR_IDOF → column ref",
    ),
    # INDEXCOL → level column
    (
        re.compile(r"\bINDEXCOL\s*\(\s*(.+?)\s*\)", re.IGNORECASE),
        r"\1",
        "INDEXCOL → column ref",
    ),
    # --- String functions ---
    # SUBSTRING(col, start, length) → MID(col, start, length)
    (
        re.compile(r"\bSUBSTRING\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"MID(\1, \2, \3)",
        "SUBSTRING → MID",
    ),
    # SUBSTR(col, start, length) → MID(col, start, length)
    (
        re.compile(r"\bSUBSTR\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"MID(\1, \2, \3)",
        "SUBSTR → MID",
    ),
    # UPPER(col) → UPPER(col)   — same name in DAX
    (
        re.compile(r"\bUPPER\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"UPPER(\1)",
        "UPPER → UPPER",
    ),
    # LOWER(col) → LOWER(col)   — same name in DAX
    (
        re.compile(r"\bLOWER\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"LOWER(\1)",
        "LOWER → LOWER",
    ),
    # TRIM(col) → TRIM(col)     — same name in DAX
    (
        re.compile(r"\bTRIM\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"TRIM(\1)",
        "TRIM → TRIM",
    ),
    # REPLACE(col, old, new) → SUBSTITUTE(col, old, new)
    (
        re.compile(r"\bREPLACE\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"SUBSTITUTE(\1, \2, \3)",
        "REPLACE → SUBSTITUTE",
    ),
    # LENGTH(col) → LEN(col)
    (
        re.compile(r"\bLENGTH\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"LEN(\1)",
        "LENGTH → LEN",
    ),
    # INSTR(string, substring) → FIND(substring, string)
    (
        re.compile(r"\bINSTR\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"FIND(\2, \1)",
        "INSTR → FIND",
    ),
    # LPAD(col, n, char) → REPT(char, n - LEN(col)) & col
    (
        re.compile(r"\bLPAD\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"REPT(\3, \2 - LEN(\1)) & \1",
        "LPAD → REPT & concatenation",
    ),
    # --- Date functions ---
    # TIMESTAMPADD(interval, n, date) → DATEADD('Date'[Date], n, interval)
    (
        re.compile(r"\bTIMESTAMPADD\s*\(\s*SQL_TSI_(\w+)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"DATEADD('Date'[Date], \2, \1)",
        "TIMESTAMPADD → DATEADD",
    ),
    # TIMESTAMPDIFF(interval, start, end) → DATEDIFF(start, end, interval)
    (
        re.compile(r"\bTIMESTAMPDIFF\s*\(\s*SQL_TSI_(\w+)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"DATEDIFF(\2, \3, \1)",
        "TIMESTAMPDIFF → DATEDIFF",
    ),
    # CURRENT_DATE → TODAY()
    (
        re.compile(r"\bCURRENT_DATE\b", re.IGNORECASE),
        "TODAY()",
        "CURRENT_DATE → TODAY",
    ),
    # CURRENT_TIMESTAMP → NOW()
    (
        re.compile(r"\bCURRENT_TIMESTAMP\b", re.IGNORECASE),
        "NOW()",
        "CURRENT_TIMESTAMP → NOW",
    ),
    # ADD_MONTHS(date, n) → EDATE(date, n)
    (
        re.compile(r"\bADD_MONTHS\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"EDATE(\1, \2)",
        "ADD_MONTHS → EDATE",
    ),
    # MONTHS_BETWEEN(d1, d2) → DATEDIFF(d2, d1, MONTH)
    (
        re.compile(r"\bMONTHS_BETWEEN\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"DATEDIFF(\2, \1, MONTH)",
        "MONTHS_BETWEEN → DATEDIFF MONTH",
    ),
    # EXTRACT(part FROM date) → part(date) in DAX
    (
        re.compile(r"\bEXTRACT\s*\(\s*(\w+)\s+FROM\s+([^)]+?)\s*\)", re.IGNORECASE),
        None,  # Handled by custom _translate_extract
        "EXTRACT → YEAR/MONTH/DAY",
    ),
    # || (string concatenation) → &
    (
        re.compile(r"(\S+)\s*\|\|\s*(\S+)"),
        r"\1 & \2",
        "|| → &",
    ),
    # --- Math functions ---
    # ABS(x) → ABS(x)
    (
        re.compile(r"\bABS\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"ABS(\1)",
        "ABS → ABS",
    ),
    # ROUND(x, n) → ROUND(x, n)
    (
        re.compile(r"\bROUND\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"ROUND(\1, \2)",
        "ROUND → ROUND",
    ),
    # TRUNC(x) → TRUNC(x)
    (
        re.compile(r"\bTRUNC\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"TRUNC(\1)",
        "TRUNC → TRUNC",
    ),
    # CEIL / CEILING
    (
        re.compile(r"\bCEIL(?:ING)?\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"CEILING(\1, 1)",
        "CEIL → CEILING",
    ),
    # FLOOR
    (
        re.compile(r"\bFLOOR\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"FLOOR(\1, 1)",
        "FLOOR → FLOOR",
    ),
    # POWER(x, n) → POWER(x, n)
    (
        re.compile(r"\bPOWER\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"POWER(\1, \2)",
        "POWER → POWER",
    ),
    # SQRT(x)
    (
        re.compile(r"\bSQRT\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"SQRT(\1)",
        "SQRT → SQRT",
    ),
    # LOG(x) → LN(x) (Oracle LOG is natural log)
    (
        re.compile(r"\bLOG\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"LN(\1)",
        "LOG → LN",
    ),
    # LOG10(x) → LOG10(x) — or LOG(x, 10)
    (
        re.compile(r"\bLOG10\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"LOG(\1, 10)",
        "LOG10 → LOG(x,10)",
    ),
    # EXP(x)
    (
        re.compile(r"\bEXP\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"EXP(\1)",
        "EXP → EXP",
    ),
    # MOD(a, b) → MOD(a, b)
    (
        re.compile(r"\bMOD\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"MOD(\1, \2)",
        "MOD → MOD",
    ),
    # SIGN(x)
    (
        re.compile(r"\bSIGN\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"SIGN(\1)",
        "SIGN → SIGN",
    ),
    # --- Additional string functions ---
    # RPAD(col, n, char) → col & REPT(char, n - LEN(col))
    (
        re.compile(r"\bRPAD\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"\1 & REPT(\3, \2 - LEN(\1))",
        "RPAD → concatenation & REPT",
    ),
    # LEFT(col, n)
    (
        re.compile(r"\bLEFT\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"LEFT(\1, \2)",
        "LEFT → LEFT",
    ),
    # RIGHT(col, n)
    (
        re.compile(r"\bRIGHT\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"RIGHT(\1, \2)",
        "RIGHT → RIGHT",
    ),
    # REVERSE(col)
    (
        re.compile(r"\bREVERSE\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"REVERSE(\1)",
        "REVERSE → REVERSE (custom measure needed)",
    ),
    # INITCAP(col) → PROPER equivalent (no native DAX)
    (
        re.compile(r"\bINITCAP\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"UPPER(LEFT(\1, 1)) & LOWER(MID(\1, 2, LEN(\1)))",
        "INITCAP → UPPER+MID approximation",
    ),
    # LTRIM(col) → left-trim
    (
        re.compile(r"\bLTRIM\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"TRIM(\1)",
        "LTRIM → TRIM (DAX only has symmetric TRIM)",
    ),
    # RTRIM(col) → right-trim
    (
        re.compile(r"\bRTRIM\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"TRIM(\1)",
        "RTRIM → TRIM (DAX only has symmetric TRIM)",
    ),
    # TRANSLATE(col, from, to) → chained SUBSTITUTE (approximation)
    (
        re.compile(r"\bTRANSLATE\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"SUBSTITUTE(\1, \2, \3)",
        "TRANSLATE → SUBSTITUTE (single-char approx)",
    ),
    # REGEXP_REPLACE — no DAX equivalent, flag for review
    (
        re.compile(r"\bREGEXP_REPLACE\s*\(\s*(.+?)\s*\)", re.IGNORECASE | re.DOTALL),
        r"/* REGEXP_REPLACE not supported in DAX — manual conversion required */ \1",
        "REGEXP_REPLACE → manual review",
    ),
    # REGEXP_SUBSTR — no DAX equivalent
    (
        re.compile(r"\bREGEXP_SUBSTR\s*\(\s*(.+?)\s*\)", re.IGNORECASE | re.DOTALL),
        r"/* REGEXP_SUBSTR not supported in DAX — manual conversion required */ \1",
        "REGEXP_SUBSTR → manual review",
    ),
    # REGEXP_INSTR — no DAX equivalent
    (
        re.compile(r"\bREGEXP_INSTR\s*\(\s*(.+?)\s*\)", re.IGNORECASE | re.DOTALL),
        r"/* REGEXP_INSTR not supported in DAX — manual conversion required */ \1",
        "REGEXP_INSTR → manual review",
    ),
    # REGEXP_LIKE — no DAX equivalent
    (
        re.compile(r"\bREGEXP_LIKE\s*\(\s*(.+?)\s*\)", re.IGNORECASE | re.DOTALL),
        r"/* REGEXP_LIKE not supported in DAX — manual conversion required */ \1",
        "REGEXP_LIKE → manual review",
    ),
    # SOUNDEX — no DAX equivalent
    (
        re.compile(r"\bSOUNDEX\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"/* SOUNDEX not supported in DAX */ \1",
        "SOUNDEX → manual review",
    ),
    # ASCII(col)
    (
        re.compile(r"\bASCII\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"UNICODE(\1)",
        "ASCII → UNICODE",
    ),
    # CHR(n) → UNICHAR(n)
    (
        re.compile(r"\bCHR\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"UNICHAR(\1)",
        "CHR → UNICHAR",
    ),
    # --- Logical functions ---
    # DECODE(col, val1, res1, val2, res2, ..., default) → SWITCH
    (
        re.compile(r"\bDECODE\s*\(\s*(.+?)\s*\)", re.IGNORECASE | re.DOTALL),
        None,  # Custom handler
        "DECODE → SWITCH",
    ),
    # NVL2(expr, not_null_val, null_val) → IF(ISBLANK(expr), null_val, not_null_val)
    (
        re.compile(r"\bNVL2\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"IF(ISBLANK(\1), \3, \2)",
        "NVL2 → IF/ISBLANK",
    ),
    # COALESCE(a, b, ...) → COALESCE(a, b, ...)
    (
        re.compile(r"\bCOALESCE\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"COALESCE(\1)",
        "COALESCE → COALESCE",
    ),
    # NULLIF(a, b) → IF(a = b, BLANK(), a)
    (
        re.compile(r"\bNULLIF\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"IF(\1 = \2, BLANK(), \1)",
        "NULLIF → IF/BLANK",
    ),
    # GREATEST(a, b) → MAX(a, b) scalar
    (
        re.compile(r"\bGREATEST\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"IF(\1 >= \2, \1, \2)",
        "GREATEST → IF comparison",
    ),
    # LEAST(a, b) → MIN scalar
    (
        re.compile(r"\bLEAST\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"IF(\1 <= \2, \1, \2)",
        "LEAST → IF comparison",
    ),
    # --- Additional date functions ---
    # SYSDATE → NOW()
    (
        re.compile(r"\bSYSDATE\b", re.IGNORECASE),
        "NOW()",
        "SYSDATE → NOW",
    ),
    # TRUNC(date) → INT(date) (date truncation)
    (
        re.compile(r"\bTRUNC\s*\(\s*([^,)]+?)\s*,\s*['\"]?(\w+)['\"]?\s*\)", re.IGNORECASE),
        None,  # Custom handler for TRUNC with date part
        "TRUNC(date, part) → date truncation",
    ),
    # TO_DATE(str, fmt) → DATEVALUE(str)
    (
        re.compile(r"\bTO_DATE\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"DATEVALUE(\1)",
        "TO_DATE → DATEVALUE",
    ),
    # TO_CHAR(date, fmt) → FORMAT(date, fmt)
    (
        re.compile(r"\bTO_CHAR\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"FORMAT(\1, \2)",
        "TO_CHAR → FORMAT",
    ),
    # TO_NUMBER(str) → VALUE(str)
    (
        re.compile(r"\bTO_NUMBER\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"VALUE(\1)",
        "TO_NUMBER → VALUE",
    ),
    # LAST_DAY(date) → EOMONTH(date, 0)
    (
        re.compile(r"\bLAST_DAY\s*\(\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"EOMONTH(\1, 0)",
        "LAST_DAY → EOMONTH",
    ),
    # NEXT_DAY is approximated  
    (
        re.compile(r"\bNEXT_DAY\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", re.IGNORECASE),
        r"\1 + (7 - WEEKDAY(\1) + \2)",
        "NEXT_DAY → weekday arithmetic (approx)",
    ),
    # ROWNUM → not translatable in DAX (flag)
    (
        re.compile(r"\bROWNUM\b", re.IGNORECASE),
        "RANKX(ALL({tbl}), 1)",
        "ROWNUM → RANKX approximation",
    ),
    # EVALUATE(db_expr) → direct passthrough, flag for review
    (
        re.compile(r"\bEVALUATE\s*\(\s*(.+?)\s*\)", re.IGNORECASE | re.DOTALL),
        r"/* EVALUATE() passthrough not supported in DAX */ \1",
        "EVALUATE → manual review",
    ),
    # LOOKUP(measure, dim1=val1, ...) → LOOKUPVALUE
    (
        re.compile(r"\bLOOKUP\s*\(\s*([^,]+?)\s*,\s*(.+?)\s*\)", re.IGNORECASE | re.DOTALL),
        r"LOOKUPVALUE(\1, \2)",
        "LOOKUP → LOOKUPVALUE",
    ),
    # RAND() → RAND()
    (
        re.compile(r"\bRAND\s*\(\s*\)", re.IGNORECASE),
        "RAND()",
        "RAND → RAND",
    ),
    # BETWEEN — rewrite as >= AND <=
    (
        re.compile(r"(\S+)\s+BETWEEN\s+(\S+)\s+AND\s+(\S+)", re.IGNORECASE),
        r"(\1 >= \2 && \1 <= \3)",
        "BETWEEN → >= AND <=",
    ),
    # IN (val1, val2) → col IN {val1, val2} in DAX or OR chain
    (
        re.compile(r"(\S+)\s+IN\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"\1 IN {\2}",
        "IN (list) → IN {list}",
    ),
]


# ---------------------------------------------------------------------------
# CASE WHEN → SWITCH translator
# ---------------------------------------------------------------------------

_WHEN_THEN = re.compile(
    r"WHEN\s+(.+?)\s+THEN\s+(.+?)(?=\s+WHEN|\s+ELSE|\s+END)",
    re.IGNORECASE | re.DOTALL,
)
_ELSE_CLAUSE = re.compile(r"ELSE\s+(.+?)(?=\s+END)", re.IGNORECASE | re.DOTALL)


def _translate_case_when(expr: str) -> str:
    """Translate CASE WHEN … THEN … ELSE … END to SWITCH(TRUE(), …)."""
    # Extract all WHEN/THEN pairs
    whens = _WHEN_THEN.findall(expr)
    else_match = _ELSE_CLAUSE.search(expr)
    else_val = else_match.group(1).strip() if else_match else "BLANK()"

    parts = ["SWITCH(TRUE()"]
    for condition, value in whens:
        parts.append(f",\n    {condition.strip()}, {value.strip()}")
    parts.append(f",\n    {else_val}")
    parts.append("\n)")
    return "".join(parts)


# ---------------------------------------------------------------------------
# CAST → DAX type conversion
# ---------------------------------------------------------------------------

_CAST_TYPE_MAP = {
    "INT": "INT",
    "INTEGER": "INT",
    "NUMBER": "VALUE",
    "FLOAT": "VALUE",
    "DOUBLE": "VALUE",
    "DECIMAL": "VALUE",
    "VARCHAR": "FORMAT",
    "VARCHAR2": "FORMAT",
    "CHAR": "FORMAT",
    "STRING": "FORMAT",
    "DATE": "DATEVALUE",
    "TIMESTAMP": "DATEVALUE",
}


def _translate_cast(col_expr: str, target_type: str) -> str:
    """Translate CAST(expr AS type) to DAX equivalent."""
    dax_fn = _CAST_TYPE_MAP.get(target_type.upper(), "CONVERT")
    if dax_fn in ("INT", "VALUE"):
        return f"{dax_fn}({col_expr})"
    if dax_fn == "FORMAT":
        return f"FORMAT({col_expr}, \"General\")"
    if dax_fn == "DATEVALUE":
        return f"DATEVALUE({col_expr})"
    return f"CONVERT({col_expr}, {target_type})"


# ---------------------------------------------------------------------------
# DECODE → SWITCH translator
# ---------------------------------------------------------------------------

def _translate_decode(args_str: str) -> str:
    """Translate DECODE(expr, val1, res1, val2, res2, ..., default) to SWITCH."""
    # Split arguments carefully (respecting nested parens/quotes)
    args: list[str] = []
    depth = 0
    current = ""
    for ch in args_str:
        if ch == "(" :
            depth += 1
            current += ch
        elif ch == ")":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            args.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        args.append(current.strip())

    if len(args) < 3:
        return f"SWITCH({args_str})"

    expr = args[0]
    pairs = args[1:]
    parts = [f"SWITCH({expr}"]
    i = 0
    while i < len(pairs) - 1:
        parts.append(f",\n    {pairs[i]}, {pairs[i+1]}")
        i += 2
    if i < len(pairs):
        # Remaining arg is the default
        parts.append(f",\n    {pairs[i]}")
    parts.append("\n)")
    return "".join(parts)


# ---------------------------------------------------------------------------
# EXTRACT → DAX date-part functions
# ---------------------------------------------------------------------------

_EXTRACT_PART_MAP: dict[str, str] = {
    "YEAR": "YEAR",
    "MONTH": "MONTH",
    "DAY": "DAY",
    "HOUR": "HOUR",
    "MINUTE": "MINUTE",
    "SECOND": "SECOND",
    "QUARTER": "QUARTER",  # maps to QUARTER() in DAX
    "WEEK": "WEEKNUM",
    "DOW": "WEEKDAY",
    "DOY": "DAYOFYEAR",  # custom — not native DAX, but common pattern
}


def _translate_extract(part: str, date_expr: str) -> str:
    """Translate EXTRACT(part FROM expr) to DAX date-part function.

    Examples
    --------
    EXTRACT(YEAR FROM order_date) → YEAR(order_date)
    EXTRACT(QUARTER FROM ship_date) → QUARTER(ship_date)
    """
    dax_fn = _EXTRACT_PART_MAP.get(part.strip().upper(), part.strip().upper())
    return f"{dax_fn}({date_expr.strip()})"


# ---------------------------------------------------------------------------
# Main translation function
# ---------------------------------------------------------------------------


def translate_expression(
    expression: str,
    table_name: str = "",
    column_name: str = "",
    is_measure: bool = False,
    table_mapping: dict[str, str] | None = None,
) -> DAXTranslation:
    """Translate an OAC expression to DAX.

    Parameters
    ----------
    expression : str
        The OAC/OBIEE calculated column or measure expression.
    table_name, column_name : str
        Context for generating qualified DAX references.
    is_measure : bool
        Hint: whether the expression is expected to be a measure.
    table_mapping : dict
        Optional OAC table name → TMDL table name mapping.
    """
    tmap = table_mapping or {}
    tbl = tmap.get(table_name, table_name) if table_name else ""
    warnings: list[str] = []
    confidence = 1.0
    dax = expression.strip()
    applied_rules: list[str] = []

    # --- Aggregate function rules ---
    for pattern, repl_template, desc in _AGGREGATE_RULES:
        if pattern.search(dax):
            repl = repl_template.replace("{tbl}", f"'{tbl}'") if tbl else repl_template.replace("{tbl}", "Table")
            dax = pattern.sub(repl, dax)
            is_measure = True
            applied_rules.append(desc)

    # --- Time-intelligence rules ---
    for pattern, repl_template, desc in _TIME_INTEL_RULES:
        if pattern.search(dax):
            dax = pattern.sub(repl_template, dax)
            is_measure = True
            applied_rules.append(desc)
            confidence = min(confidence, 0.85)

    # --- Scalar function rules ---
    for pattern, repl_template, desc in _SCALAR_RULES:
        m = pattern.search(dax)
        if m:
            if repl_template is None:
                # Custom handlers
                if "CASE" in desc.upper():
                    dax = _translate_case_when(dax)
                    applied_rules.append(desc)
                    confidence = min(confidence, 0.8)
                elif "CAST" in desc.upper():
                    dax = _translate_cast(m.group(1), m.group(2))
                    applied_rules.append(desc)
                elif "EXTRACT" in desc.upper():
                    dax = _translate_extract(m.group(1), m.group(2))
                    applied_rules.append(desc)
                elif "DECODE" in desc.upper():
                    dax = _translate_decode(m.group(1))
                    applied_rules.append(desc)
                    confidence = min(confidence, 0.8)
                elif "TRUNC" in desc.upper() and "date" in desc.lower():
                    # TRUNC(date, part) → date-floor approximation
                    dax = f"INT({m.group(1)})"
                    applied_rules.append(desc)
                    confidence = min(confidence, 0.7)
            else:
                repl = repl_template.replace("{tbl}", f"'{tbl}'") if tbl else repl_template.replace("{tbl}", "Table")
                dax = pattern.sub(repl, dax)
                applied_rules.append(desc)

    # --- Check for untranslated OAC-specific patterns ---
    untranslated_patterns = [
        (r"\bFETCH\s+FIRST\b", "FETCH FIRST"),
        (r"\bCONNECT\s+BY\b", "CONNECT BY (hierarchical query)"),
        (r"\bPRIOR\b", "PRIOR (hierarchical)"),
        (r"\bMODEL\s+CLAUSE\b", "MODEL clause"),
        (r"\bANALYTIC\b", "Analytic function"),
    ]
    for pat_str, desc in untranslated_patterns:
        if re.search(pat_str, dax, re.IGNORECASE):
            warnings.append(f"Untranslatable pattern: {desc}")
            confidence = min(confidence, 0.3)

    # If nothing was applied and expression is non-trivial, lower confidence
    if not applied_rules and len(expression.strip()) > 20:
        confidence = min(confidence, 0.6)
        warnings.append("No translation rules matched — expression may need manual review")

    # Determine display folder
    display_folder = "Measures" if is_measure else ""
    if any(r for r in applied_rules if "AGO" in r or "TODATE" in r or "PERIOD" in r or "RSUM" in r):
        display_folder = "Time Intelligence"

    return DAXTranslation(
        column_name=column_name,
        table_name=table_name,
        original_expression=expression,
        dax_expression=dax,
        method="rule-based",
        confidence=confidence,
        is_measure=is_measure,
        format_string="",
        display_folder=display_folder,
        warnings=warnings,
        requires_review=confidence < 0.7,
    )


# ---------------------------------------------------------------------------
# LLM-assisted translation
# ---------------------------------------------------------------------------


def build_dax_llm_prompt(
    expression: str,
    table_name: str = "",
    column_name: str = "",
    available_columns: list[str] | None = None,
    table_mapping: dict[str, str] | None = None,
) -> str:
    """Build a prompt for LLM-assisted OAC → DAX translation."""
    cols_str = ", ".join(available_columns or [])
    tmap_str = ""
    if table_mapping:
        import json
        tmap_str = json.dumps(table_mapping, indent=2)

    return f"""You are an expert in Oracle Analytics Cloud (OAC/OBIEE) and Power BI DAX.
Convert the following OAC logical column expression to an equivalent DAX measure.

Context:
- Table: {table_name}
- Column: {column_name}
- Available columns in the model: {cols_str}
- Table mapping (OAC → Power BI): {tmap_str or 'N/A'}

OAC Expression:
{expression}

Generate:
1. The DAX measure expression
2. Confidence score (0-1)
3. Any assumptions made
4. Whether manual review is recommended

Return the DAX expression only on the first line, then notes below."""


def translate_with_llm_fallback(
    expression: str,
    table_name: str = "",
    column_name: str = "",
    is_measure: bool = False,
    table_mapping: dict[str, str] | None = None,
    available_columns: list[str] | None = None,
    llm_client: Any = None,
) -> DAXTranslation:
    """Rule-based translation with LLM fallback for low-confidence results."""
    result = translate_expression(expression, table_name, column_name, is_measure, table_mapping)

    if result.confidence < 0.6 and llm_client is not None:
        logger.info(
            "Rule-based confidence %.0f%% for '%s.%s' — invoking LLM",
            result.confidence * 100, table_name, column_name,
        )
        prompt = build_dax_llm_prompt(expression, table_name, column_name, available_columns, table_mapping)
        try:
            llm_output = llm_client.complete(prompt)
            # Take the first line as the DAX expression
            dax_line = llm_output.strip().split("\n")[0].strip()
            result = DAXTranslation(
                column_name=column_name,
                table_name=table_name,
                original_expression=expression,
                dax_expression=dax_line,
                method="llm",
                confidence=0.7,
                is_measure=is_measure,
                warnings=["Generated by LLM — review recommended"],
                requires_review=True,
            )
        except Exception:
            logger.exception("LLM DAX translation failed for '%s.%s'", table_name, column_name)
            result.warnings.append("LLM fallback failed")

    if result.confidence < 0.5:
        result.method = "manual"
        result.requires_review = True

    return result


# ---------------------------------------------------------------------------
# Batch translation
# ---------------------------------------------------------------------------


def translate_all_expressions(
    expressions: list[dict[str, Any]],
    table_mapping: dict[str, str] | None = None,
    llm_client: Any = None,
) -> list[DAXTranslation]:
    """Translate a list of OAC expressions to DAX.

    Each dict in *expressions* should have keys:
    ``expression``, ``table_name``, ``column_name``, optionally ``is_measure``.
    """
    results: list[DAXTranslation] = []
    for e in expressions:
        result = translate_with_llm_fallback(
            expression=e.get("expression", ""),
            table_name=e.get("table_name", ""),
            column_name=e.get("column_name", ""),
            is_measure=e.get("is_measure", False),
            table_mapping=table_mapping,
            llm_client=llm_client,
        )
        results.append(result)
    return results
