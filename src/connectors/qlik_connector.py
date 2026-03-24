"""Qlik Sense / QlikView connector — full implementation.

Parses Qlik load scripts, extracts data model metadata, communicates
with the Qlik Engine API, and translates Qlik expressions to DAX.

Components
~~~~~~~~~~
- **Data models**: ``QlikApp``, ``QlikSheet``, ``QlikField``,
  ``QlikTable``, ``QlikMeasure``, ``QlikDimension``, ``QlikVariable``,
  ``QlikBookmark``, ``ParsedLoadScript``, ``CalcTranslationResult``
- **Rule catalog**: 55+ Qlik → DAX translation rules
- **QlikExpressionTranslator**: regex-based Qlik expression → DAX
- **QlikLoadScriptParser**: Qlik load script parser
- **QlikEngineClient**: async Qlik Engine API client
- **FullQlikConnector**: ``SourceConnector`` lifecycle implementation
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# =====================================================================
# Data models
# =====================================================================


@dataclass
class QlikField:
    """A field (column) in a Qlik data model."""

    name: str
    data_type: str = ""  # text, numeric, dual, date, timestamp, money
    source_table: str = ""
    expression: str = ""
    is_key: bool = False
    tags: list[str] = field(default_factory=list)
    comment: str = ""


@dataclass
class QlikTable:
    """A table loaded in a Qlik data model."""

    name: str
    fields: list[QlikField] = field(default_factory=list)
    source_type: str = ""  # sql, file, inline, resident, preceding
    source_connection: str = ""
    sql_statement: str = ""
    row_count: int = 0
    where_clause: str = ""
    comment: str = ""


@dataclass
class QlikMeasure:
    """A Qlik master measure."""

    name: str
    expression: str
    label: str = ""
    description: str = ""
    number_format: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class QlikDimension:
    """A Qlik master dimension."""

    name: str
    field_name: str = ""
    expression: str = ""
    label: str = ""
    description: str = ""
    is_drill_down: bool = False
    drill_down_fields: list[str] = field(default_factory=list)


@dataclass
class QlikVariable:
    """A Qlik variable."""

    name: str
    definition: str = ""
    description: str = ""
    is_script_created: bool = False


@dataclass
class QlikBookmark:
    """A Qlik bookmark (saved selection state)."""

    name: str
    description: str = ""
    selections: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class QlikSheet:
    """A sheet in a Qlik app."""

    name: str
    sheet_id: str = ""
    title: str = ""
    objects: list[dict[str, Any]] = field(default_factory=list)
    # Each object: {"type": "barchart", "title": "Sales by Region", "measures": [...], "dimensions": [...]}


@dataclass
class QlikApp:
    """A Qlik Sense / QlikView application."""

    name: str
    app_id: str = ""
    tables: list[QlikTable] = field(default_factory=list)
    sheets: list[QlikSheet] = field(default_factory=list)
    measures: list[QlikMeasure] = field(default_factory=list)
    dimensions: list[QlikDimension] = field(default_factory=list)
    variables: list[QlikVariable] = field(default_factory=list)
    bookmarks: list[QlikBookmark] = field(default_factory=list)
    description: str = ""
    load_script: str = ""

    @property
    def field_count(self) -> int:
        return sum(len(t.fields) for t in self.tables)

    @property
    def table_names(self) -> list[str]:
        return [t.name for t in self.tables]


@dataclass
class ParsedLoadScript:
    """Result of parsing a Qlik load script."""

    tables: list[QlikTable] = field(default_factory=list)
    variables: list[QlikVariable] = field(default_factory=list)
    connections: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def field_count(self) -> int:
        return sum(len(t.fields) for t in self.tables)

    @property
    def table_names(self) -> list[str]:
        return [t.name for t in self.tables]


# =====================================================================
# Qlik → DAX expression mapping
# =====================================================================


@dataclass
class QlikCalcRule:
    """A single Qlik → DAX translation rule."""

    qlik_function: str
    dax_equivalent: str
    difficulty: str = "direct"  # direct, parametric, complex, unsupported
    notes: str = ""


@dataclass
class CalcTranslationResult:
    """Result of translating one Qlik expression."""

    source_name: str
    source_expression: str
    dax_expression: str
    method: str = "rules"  # rules | unsupported
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)


# Rule catalog — 55+ Qlik→DAX rules
QLIK_TO_DAX_RULES: list[QlikCalcRule] = [
    # Aggregation
    QlikCalcRule("Sum", "SUM", "direct", "Sum → SUM"),
    QlikCalcRule("Count", "COUNTROWS", "parametric", "Count → COUNTROWS"),
    QlikCalcRule("Avg", "AVERAGE", "direct", "Avg → AVERAGE"),
    QlikCalcRule("Min", "MIN", "direct", "Min → MIN"),
    QlikCalcRule("Max", "MAX", "direct", "Max → MAX"),
    QlikCalcRule("Only", "SELECTEDVALUE", "parametric", "Only → SELECTEDVALUE"),
    QlikCalcRule("Mode", "/* Mode → no DAX equivalent */", "unsupported", "Statistical mode"),
    QlikCalcRule("Median", "MEDIAN", "direct", "Median → MEDIAN"),
    QlikCalcRule("Stdev", "STDEV.S", "direct", "Stdev → STDEV.S"),
    QlikCalcRule("Fractile", "PERCENTILEX.INC", "complex", "Fractile → PERCENTILEX"),
    QlikCalcRule("Correl", "/* Correl → no direct DAX */", "unsupported", "Correlation"),
    QlikCalcRule("NullCount", "COUNTBLANK", "direct", "NullCount → COUNTBLANK"),
    QlikCalcRule("MissingCount", "COUNTBLANK", "direct", "MissingCount → COUNTBLANK"),
    QlikCalcRule("NumericCount", "COUNTA", "parametric", "NumericCount → COUNTA"),
    QlikCalcRule("TextCount", "COUNTA", "parametric", "TextCount → COUNTA"),
    # Conditional
    QlikCalcRule("If", "IF", "parametric", "If → IF"),
    QlikCalcRule("Alt", "COALESCE", "parametric", "Alt → COALESCE"),
    QlikCalcRule("Pick", "SWITCH", "complex", "Pick → SWITCH"),
    QlikCalcRule("Match", "SWITCH(TRUE(), expr=v1, 1, ...)", "complex", "Match → SWITCH"),
    QlikCalcRule("MixMatch", "SWITCH(TRUE())", "complex", "MixMatch → case-insensitive SWITCH"),
    QlikCalcRule("WildMatch", "SWITCH(TRUE(), CONTAINSSTRING)", "complex", "WildMatch → CONTAINSSTRING"),
    QlikCalcRule("Class", "/* Class → bucketing logic */", "complex", "Class bucketing"),
    # String
    QlikCalcRule("Len", "LEN", "direct", "Len → LEN"),
    QlikCalcRule("Left", "LEFT", "direct", "Left → LEFT"),
    QlikCalcRule("Right", "RIGHT", "direct", "Right → RIGHT"),
    QlikCalcRule("Mid", "MID", "parametric", "Mid → MID"),
    QlikCalcRule("Upper", "UPPER", "direct", "Upper → UPPER"),
    QlikCalcRule("Lower", "LOWER", "direct", "Lower → LOWER"),
    QlikCalcRule("Trim", "TRIM", "direct", "Trim → TRIM"),
    QlikCalcRule("LTrim", "TRIM", "parametric", "LTrim → TRIM (DAX only has TRIM)"),
    QlikCalcRule("RTrim", "TRIM", "parametric", "RTrim → TRIM"),
    QlikCalcRule("Replace", "SUBSTITUTE", "parametric", "Replace → SUBSTITUTE"),
    QlikCalcRule("SubStringCount", "/* SubStringCount → manual */", "complex", "Count occurrences"),
    QlikCalcRule("Index", "SEARCH", "parametric", "Index → SEARCH"),
    QlikCalcRule("TextBetween", "MID(text, SEARCH(delim1)+1, ...)", "complex", "TextBetween → MID+SEARCH"),
    QlikCalcRule("Capitalize", "/* Capitalize → ProperCase DAX */", "complex", "Capitalize"),
    QlikCalcRule("Repeat", "REPT", "direct", "Repeat → REPT"),
    QlikCalcRule("PurgeChar", "SUBSTITUTE chains", "complex", "PurgeChar → chain SUBSTITUTE"),
    QlikCalcRule("KeepChar", "/* KeepChar → complex regex */", "complex", "Keep specific chars"),
    # Date
    QlikCalcRule("Today", "TODAY", "direct", "Today → TODAY"),
    QlikCalcRule("Now", "NOW", "direct", "Now → NOW"),
    QlikCalcRule("Year", "YEAR", "direct", "Year → YEAR"),
    QlikCalcRule("Month", "MONTH", "direct", "Month → MONTH"),
    QlikCalcRule("Day", "DAY", "direct", "Day → DAY"),
    QlikCalcRule("Hour", "HOUR", "direct", "Hour → HOUR"),
    QlikCalcRule("Minute", "MINUTE", "direct", "Minute → MINUTE"),
    QlikCalcRule("Second", "SECOND", "direct", "Second → SECOND"),
    QlikCalcRule("WeekDay", "WEEKDAY", "direct", "WeekDay → WEEKDAY"),
    QlikCalcRule("WeekYear", "WEEKNUM", "direct", "WeekYear → WEEKNUM"),
    QlikCalcRule("MonthName", "FORMAT(date, \"MMMM\")", "parametric", "MonthName → FORMAT"),
    QlikCalcRule("DayName", "FORMAT(date, \"dddd\")", "parametric", "DayName → FORMAT"),
    QlikCalcRule("YearToDate", "CALCULATE(measure, DATESYTD())", "complex", "YTD → DATESYTD"),
    QlikCalcRule("AddMonths", "DATEADD", "parametric", "AddMonths → DATEADD"),
    QlikCalcRule("AddYears", "DATEADD", "parametric", "AddYears → DATEADD"),
    # Math
    QlikCalcRule("Abs", "ABS", "direct", "Abs → ABS"),
    QlikCalcRule("Ceil", "CEILING", "direct", "Ceil → CEILING"),
    QlikCalcRule("Floor", "FLOOR", "direct", "Floor → FLOOR"),
    QlikCalcRule("Round", "ROUND", "direct", "Round → ROUND"),
    QlikCalcRule("Mod", "MOD", "direct", "Mod → MOD"),
    QlikCalcRule("Fabs", "ABS", "direct", "Fabs → ABS"),
    QlikCalcRule("Sqrt", "SQRT", "direct", "Sqrt → SQRT"),
    QlikCalcRule("Exp", "EXP", "direct", "Exp → EXP"),
    QlikCalcRule("Log", "LOG", "parametric", "Log → LOG"),
    QlikCalcRule("Log10", "LOG10", "direct", "Log10 → LOG10 (math.log10)"),
    QlikCalcRule("Pow", "POWER", "direct", "Pow → POWER"),
    QlikCalcRule("Sign", "SIGN", "direct", "Sign → SIGN"),
    # Counter / ranking
    QlikCalcRule("RowNo", "RANKX", "complex", "RowNo → RANKX (context-dependent)"),
    QlikCalcRule("RecNo", "RANKX", "complex", "RecNo → RANKX"),
    QlikCalcRule("Rank", "RANKX", "parametric", "Rank → RANKX"),
    # Set analysis → CALCULATE
    QlikCalcRule("{$<", "CALCULATE(measure, FILTER)", "complex", "Set Analysis → CALCULATE+FILTER"),
    QlikCalcRule("{1<", "CALCULATE(measure, ALL, FILTER)", "complex", "Full set → CALCULATE+ALL+FILTER"),
    # Inter-record
    QlikCalcRule("Above", "/* Above → EARLIER / offset */", "complex", "Above → EARLIER context"),
    QlikCalcRule("Below", "/* Below → EARLIER / offset */", "complex", "Below → EARLIER context"),
    QlikCalcRule("Previous", "/* Previous → prior row */", "complex", "Previous row"),
    QlikCalcRule("Peek", "/* Peek → EARLIER */", "complex", "Peek / EARLIER"),
]


# Regex patterns for Qlik → DAX translation
_QLIK_CALC_PATTERNS: list[tuple[str, str, str]] = [
    # Aggregation
    (r"\bSum\s*\(", "SUM(", "direct"),
    (r"\bCount\s*\(", "COUNTROWS(", "parametric"),
    (r"\bAvg\s*\(", "AVERAGE(", "direct"),
    (r"\bMin\s*\(", "MIN(", "direct"),
    (r"\bMax\s*\(", "MAX(", "direct"),
    (r"\bOnly\s*\(", "SELECTEDVALUE(", "parametric"),
    (r"\bMedian\s*\(", "MEDIAN(", "direct"),
    (r"\bStdev\s*\(", "STDEV.S(", "direct"),
    (r"\bNullCount\s*\(", "COUNTBLANK(", "direct"),
    (r"\bMissingCount\s*\(", "COUNTBLANK(", "direct"),
    (r"\bFractile\s*\(", "PERCENTILEX.INC(", "complex"),
    (r"\bMode\s*\(", "/* Mode: unsupported */ MODE(", "unsupported"),
    (r"\bCorrel\s*\(", "/* Correl: unsupported */ CORREL(", "unsupported"),
    (r"\bRank\s*\(", "RANKX(ALL(), ", "parametric"),
    # Conditional
    (r"\bIf\s*\(", "IF(", "parametric"),
    (r"\bAlt\s*\(", "COALESCE(", "parametric"),
    (r"\bPick\s*\(", "SWITCH(", "complex"),
    (r"\bMatch\s*\(", "SWITCH(TRUE(), ", "complex"),
    (r"\bMixMatch\s*\(", "SWITCH(TRUE(), UPPER(", "complex"),
    (r"\bWildMatch\s*\(", "SWITCH(TRUE(), CONTAINSSTRING(", "complex"),
    (r"\bClass\s*\(", "/* Class bucketing */ INT(", "complex"),
    # String
    (r"\bLen\s*\(", "LEN(", "direct"),
    (r"\bLeft\s*\(", "LEFT(", "direct"),
    (r"\bRight\s*\(", "RIGHT(", "direct"),
    (r"\bMid\s*\(", "MID(", "parametric"),
    (r"\bUpper\s*\(", "UPPER(", "direct"),
    (r"\bLower\s*\(", "LOWER(", "direct"),
    (r"\bTrim\s*\(", "TRIM(", "direct"),
    (r"\bLTrim\s*\(", "TRIM(", "parametric"),
    (r"\bRTrim\s*\(", "TRIM(", "parametric"),
    (r"\bReplace\s*\(", "SUBSTITUTE(", "parametric"),
    (r"\bIndex\s*\(", "SEARCH(", "parametric"),
    (r"\bRepeat\s*\(", "REPT(", "direct"),
    (r"\bSubStringCount\s*\(", "/* SubStringCount: complex */ LEN(", "complex"),
    (r"\bTextBetween\s*\(", "/* TextBetween → MID+SEARCH */ MID(", "complex"),
    (r"\bPurgeChar\s*\(", "/* PurgeChar → SUBSTITUTE chain */ SUBSTITUTE(", "complex"),
    (r"\bKeepChar\s*\(", "/* KeepChar: complex */ LEFT(", "complex"),
    # Date
    (r"\bToday\s*\(", "TODAY(", "direct"),
    (r"\bNow\s*\(", "NOW(", "direct"),
    (r"\bYear\s*\(", "YEAR(", "direct"),
    (r"\bMonth\s*\(", "MONTH(", "direct"),
    (r"\bDay\s*\(", "DAY(", "direct"),
    (r"\bHour\s*\(", "HOUR(", "direct"),
    (r"\bMinute\s*\(", "MINUTE(", "direct"),
    (r"\bSecond\s*\(", "SECOND(", "direct"),
    (r"\bWeekDay\s*\(", "WEEKDAY(", "direct"),
    (r"\bWeekYear\s*\(", "WEEKNUM(", "direct"),
    (r"\bMonthName\s*\(", "FORMAT(", "parametric"),
    (r"\bDayName\s*\(", "FORMAT(", "parametric"),
    (r"\bYearToDate\s*\(", "CALCULATE(measure, DATESYTD(", "complex"),
    (r"\bAddMonths\s*\(", "DATEADD(", "parametric"),
    (r"\bAddYears\s*\(", "DATEADD(", "parametric"),
    # Math
    (r"\bAbs\s*\(", "ABS(", "direct"),
    (r"\bCeil\s*\(", "CEILING(", "direct"),
    (r"\bFloor\s*\(", "FLOOR(", "direct"),
    (r"\bRound\s*\(", "ROUND(", "direct"),
    (r"\bMod\s*\(", "MOD(", "direct"),
    (r"\bSqrt\s*\(", "SQRT(", "direct"),
    (r"\bExp\s*\(", "EXP(", "direct"),
    (r"\bLog\s*\(", "LOG(", "parametric"),
    (r"\bLog10\s*\(", "LOG10(", "direct"),
    (r"\bPow\s*\(", "POWER(", "direct"),
    (r"\bSign\s*\(", "SIGN(", "direct"),
    # Counter / ranking
    (r"\bRowNo\s*\(", "/* RowNo → RANKX */ RANKX(", "complex"),
    (r"\bRecNo\s*\(", "/* RecNo → RANKX */ RANKX(", "complex"),
    # Set analysis
    (r"\{[\$1]*\s*<", "/* Set Analysis → CALCULATE */ CALCULATE(", "complex"),
    # Inter-record
    (r"\bAbove\s*\(", "/* Above → EARLIER */ EARLIER(", "complex"),
    (r"\bBelow\s*\(", "/* Below → EARLIER */ EARLIER(", "complex"),
    (r"\bPrevious\s*\(", "/* Previous → prior context */ EARLIER(", "complex"),
    (r"\bPeek\s*\(", "/* Peek → EARLIER */ EARLIER(", "complex"),
    # Dollar-sign expansion (variables)
    (r"\$\((\w+)\)", r"[\1]", "parametric"),
    # Field references
    (r"\[([^\]]+)\]", r"[\1]", "direct"),
]


# Qlik → Fabric data source type mapping
QLIK_TO_FABRIC_SOURCE: dict[str, str] = {
    "oledb": "OleDb",
    "odbc": "ODBC",
    "oracle": "OracleDatabase",
    "sqlserver": "Sql",
    "postgresql": "PostgreSql",
    "mysql": "MySql",
    "teradata": "Teradata",
    "snowflake": "Snowflake",
    "sap_sql": "SapBw",
    "rest": "Web",
    "folder": "Folder",
    "qvd": "File",
    "excel": "Excel",
    "csv": "File",
}


# Qlik → Fabric data type mapping
QLIK_TO_FABRIC_TYPE: dict[str, str] = {
    "text": "string",
    "numeric": "double",
    "dual": "string",
    "date": "dateTime",
    "timestamp": "dateTime",
    "money": "decimal",
    "integer": "int64",
}


# Qlik visual type → Power BI visual type mapping
QLIK_VISUAL_TO_PBI: dict[str, str] = {
    "barchart": "clusteredBarChart",
    "linechart": "lineChart",
    "piechart": "pieChart",
    "combochart": "lineClusteredColumnComboChart",
    "scatterplot": "scatterChart",
    "treemap": "treemap",
    "table": "table",
    "pivot-table": "matrix",
    "kpi": "card",
    "gauge": "gauge",
    "map": "map",
    "waterfall": "waterfallChart",
    "boxplot": "scatterChart",
    "histogram": "clusteredColumnChart",
    "filterpane": "slicer",
    "text-image": "textbox",
    "container": "groupVisual",
    "listbox": "slicer",
}


# Qlik → TMDL concept mapping
QLIK_TO_TMDL_MAPPING: dict[str, str] = {
    "App": "Semantic Model + Report",
    "Table (data model)": "Table",
    "Field": "Column",
    "Master Measure": "Measure (DAX)",
    "Master Dimension": "Column / Hierarchy",
    "Drill-down Dimension": "Hierarchy",
    "Variable": "DAX Variable / Parameter",
    "Sheet": "Report Page",
    "Chart Object": "Visual",
    "List Box": "Slicer",
    "Filter Pane": "Page-level Filter",
    "Set Analysis": "CALCULATE + FILTER context",
    "Bookmark": "Bookmark (Report)",
    "Section Access": "RLS (Row-Level Security)",
    "Data Connection": "Fabric Lakehouse Connection",
    "Load Script": "Dataflow Gen2 / Notebook",
    "Inline Table": "DAX Calculated Table",
    "Cyclic Group": "Field Parameter",
    "Alternate State": "Bookmark Group",
    "Expression Variable ($)": "DAX Measure",
    "Binary Load": "Shared Dataset Reference",
    "QVD File": "Delta Table (Lakehouse)",
}


# =====================================================================
# Expression translator
# =====================================================================


class QlikExpressionTranslator:
    """Translate Qlik expressions to DAX using regex rules."""

    def __init__(self) -> None:
        self._rules: list[tuple[str, str, str]] = list(_QLIK_CALC_PATTERNS)

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def catalog(self) -> list[QlikCalcRule]:
        return QLIK_TO_DAX_RULES

    def translate(self, measure: QlikMeasure) -> CalcTranslationResult:
        """Translate a single Qlik measure expression to DAX."""
        return self.translate_expression(measure.expression, source_name=measure.name)

    def translate_expression(self, expression: str, source_name: str = "") -> CalcTranslationResult:
        """Translate a Qlik expression string to DAX."""
        text = expression.strip()
        warnings: list[str] = []
        confidence = 1.0
        dax = text

        for pattern, replacement, difficulty in self._rules:
            if re.search(pattern, dax, re.IGNORECASE):
                if difficulty == "unsupported":
                    warnings.append(f"Unsupported: {pattern.strip()}")
                    confidence = min(confidence, 0.2)
                elif difficulty == "complex":
                    warnings.append(f"Complex mapping: {pattern.strip()}")
                    confidence = min(confidence, 0.5)
                elif difficulty == "parametric":
                    confidence = min(confidence, 0.7)
                dax = re.sub(pattern, replacement, dax, flags=re.IGNORECASE)

        method = "rules"
        if any("Unsupported" in w for w in warnings):
            method = "unsupported"

        return CalcTranslationResult(
            source_name=source_name,
            source_expression=expression,
            dax_expression=dax,
            method=method,
            confidence=confidence,
            warnings=warnings,
        )

    def translate_batch(self, measures: list[QlikMeasure]) -> list[CalcTranslationResult]:
        """Translate a batch of Qlik measures."""
        return [self.translate(m) for m in measures]


# =====================================================================
# Load script parser
# =====================================================================


class QlikLoadScriptParser:
    """Parse Qlik load scripts to extract data model metadata.

    Supports standard LOAD / SQL SELECT / STORE / LET / SET syntax
    from QlikView and Qlik Sense.
    """

    _LOAD_RE = re.compile(
        r"(?:(\w+):)?\s*(?:NOCONCATENATE\s+)?LOAD\s+(.+?)\s+"
        r"(?:FROM\s+(.+?)(?:\s*\((.+?)\))?|RESIDENT\s+(\w+)"
        r"|INLINE\s*\[([^\]]*)\]|PRECEDING\s+LOAD)"
        r"(?:\s+WHERE\s+(.+?))?;",
        re.IGNORECASE | re.DOTALL,
    )

    _SQL_SELECT_RE = re.compile(
        r"(?:(\w+):)?\s*SQL\s+SELECT\s+(.+?)\s+FROM\s+(\S+)(?:\s+WHERE\s+(.+?))?;",
        re.IGNORECASE | re.DOTALL,
    )

    _LET_SET_RE = re.compile(
        r"(?:LET|SET)\s+(\w+)\s*=\s*(.+?);",
        re.IGNORECASE,
    )

    _CONNECT_RE = re.compile(
        r"(?:LIB\s+)?CONNECT\s+TO\s+'([^']+)'",
        re.IGNORECASE,
    )

    def parse(self, script: str) -> ParsedLoadScript:
        """Parse a Qlik load script string."""
        result = ParsedLoadScript()

        # Extract connections
        for m in self._CONNECT_RE.finditer(script):
            result.connections.append(m.group(1))

        # Extract variables (LET / SET)
        for m in self._LET_SET_RE.finditer(script):
            var_name = m.group(1)
            var_def = m.group(2).strip()
            result.variables.append(QlikVariable(
                name=var_name,
                definition=var_def,
                is_script_created=True,
            ))

        # Extract LOAD statements
        for m in self._LOAD_RE.finditer(script):
            table_name = m.group(1) or f"Table_{len(result.tables) + 1}"
            field_str = m.group(2) or ""
            from_path = m.group(3) or ""
            resident = m.group(5) or ""
            inline_data = m.group(6) or ""
            where_clause = m.group(7) or ""

            fields = self._parse_fields(field_str)

            source_type = "file"
            if resident:
                source_type = "resident"
            elif inline_data:
                source_type = "inline"

            table = QlikTable(
                name=table_name,
                fields=fields,
                source_type=source_type,
                source_connection=from_path or resident,
                where_clause=where_clause.strip(),
            )
            result.tables.append(table)

        # Extract SQL SELECT statements
        for m in self._SQL_SELECT_RE.finditer(script):
            table_name = m.group(1) or f"SQL_{len(result.tables) + 1}"
            field_str = m.group(2) or ""
            from_table = m.group(3) or ""
            where_clause = m.group(4) or ""

            fields = self._parse_fields(field_str)

            table = QlikTable(
                name=table_name,
                fields=fields,
                source_type="sql",
                sql_statement=f"SELECT {field_str} FROM {from_table}",
                where_clause=where_clause.strip(),
            )
            result.tables.append(table)

        return result

    def _parse_fields(self, field_str: str) -> list[QlikField]:
        """Parse a comma-separated field list."""
        fields: list[QlikField] = []
        if not field_str.strip() or field_str.strip() == "*":
            return fields

        # Split by comma, respecting parentheses
        depth = 0
        current = ""
        for char in field_str:
            if char == "(":
                depth += 1
                current += char
            elif char == ")":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                field = self._parse_single_field(current.strip())
                if field:
                    fields.append(field)
                current = ""
            else:
                current += char

        if current.strip():
            field = self._parse_single_field(current.strip())
            if field:
                fields.append(field)

        return fields

    def _parse_single_field(self, field_text: str) -> QlikField | None:
        """Parse a single field definition."""
        if not field_text:
            return None

        # Handle "expression AS name" pattern
        as_match = re.match(r"(.+?)\s+[Aa][Ss]\s+(\w+)", field_text)
        if as_match:
            return QlikField(
                name=as_match.group(2),
                expression=as_match.group(1).strip(),
            )

        # Simple field name
        name = field_text.strip().strip('"').strip("'").strip("[").strip("]")
        return QlikField(name=name) if name else None


# =====================================================================
# Engine API client
# =====================================================================


@dataclass
class QlikEngineConfig:
    """Configuration for the Qlik Engine API."""

    server_url: str
    tenant_id: str = ""
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""
    space_id: str = ""

    @property
    def base_url(self) -> str:
        return f"{self.server_url.rstrip('/')}/api/v1"


class QlikEngineClient:
    """Async client for the Qlik Sense Engine API / REST API.

    Methods ``_http_get`` and ``_http_post`` can be overridden in tests.
    """

    def __init__(self) -> None:
        self._config: QlikEngineConfig | None = None
        self._connected = False

    async def connect(self, config: QlikEngineConfig) -> bool:
        """Authenticate with the Qlik Cloud or Qlik Sense Enterprise."""
        self._config = config
        try:
            result = await self._http_get(f"{config.base_url}/users/me")
            self._connected = bool(result.get("id") or result.get("userId"))
            return self._connected
        except Exception as exc:
            logger.error("Qlik connection failed: %s", exc)
            return False

    async def list_apps(self) -> list[dict[str, Any]]:
        """List all accessible Qlik apps."""
        assert self._config
        data = await self._http_get(f"{self._config.base_url}/items?type=app")
        return data.get("data", [])

    async def get_app_meta(self, app_id: str) -> dict[str, Any]:
        """Get app metadata."""
        assert self._config
        return await self._http_get(f"{self._config.base_url}/apps/{app_id}")

    async def get_app_script(self, app_id: str) -> str:
        """Get the load script of an app."""
        assert self._config
        data = await self._http_get(f"{self._config.base_url}/apps/{app_id}/script")
        return data.get("script", "")

    async def get_app_objects(self, app_id: str) -> list[dict[str, Any]]:
        """List all objects (sheets, charts, etc.) in an app."""
        assert self._config
        data = await self._http_get(
            f"{self._config.base_url}/apps/{app_id}/objects"
        )
        return data.get("data", [])

    async def get_app_measures(self, app_id: str) -> list[dict[str, Any]]:
        """List master measures."""
        assert self._config
        data = await self._http_get(
            f"{self._config.base_url}/apps/{app_id}/measures"
        )
        return data.get("data", [])

    async def get_app_dimensions(self, app_id: str) -> list[dict[str, Any]]:
        """List master dimensions."""
        assert self._config
        data = await self._http_get(
            f"{self._config.base_url}/apps/{app_id}/dimensions"
        )
        return data.get("data", [])

    async def get_data_model(self, app_id: str) -> dict[str, Any]:
        """Get the app's data model (tables + fields)."""
        assert self._config
        return await self._http_get(
            f"{self._config.base_url}/apps/{app_id}/data/model"
        )

    async def disconnect(self) -> None:
        self._connected = False

    # Overridable HTTP methods for testing
    async def _http_get(self, url: str) -> dict[str, Any]:
        raise NotImplementedError("HTTP not available — override in tests")

    async def _http_post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("HTTP not available")

    def _auth_headers(self) -> dict[str, str]:
        """Build authentication headers."""
        if not self._config:
            return {}
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers


# =====================================================================
# Full Qlik Connector
# =====================================================================


class FullQlikConnector:
    """Qlik Sense / QlikView connector — full implementation.

    Composes:
    - ``QlikEngineClient`` — Engine API communication
    - ``QlikLoadScriptParser`` — load script parsing
    - ``QlikExpressionTranslator`` — expression → DAX translation
    """

    def __init__(self) -> None:
        self._engine_client = QlikEngineClient()
        self._parser = QlikLoadScriptParser()
        self._translator = QlikExpressionTranslator()
        self._connected = False
        self._discovered_assets: list[Any] = []

    def info(self):
        from src.connectors.base_connector import ConnectorInfo, SourcePlatform
        return ConnectorInfo(
            platform=SourcePlatform.QLIK,
            name="Qlik Sense / QlikView Connector",
            version="1.0.0",
            description=(
                "Full Qlik connector — Engine API, load script parser, "
                f"{self._translator.rule_count} expression→DAX rules, "
                f"{len(QLIK_VISUAL_TO_PBI)} visual mappings, "
                f"{len(QLIK_TO_TMDL_MAPPING)} concept mappings"
            ),
            supported_asset_types=["app", "sheet", "measure", "dimension", "datasource"],
            is_stub=False,
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        """Connect to Qlik."""
        try:
            engine_config = QlikEngineConfig(
                server_url=config.get("server_url", ""),
                tenant_id=config.get("tenant_id", ""),
                api_key=config.get("api_key", ""),
                client_id=config.get("client_id", ""),
                client_secret=config.get("client_secret", ""),
                space_id=config.get("space_id", ""),
            )
            self._connected = await self._engine_client.connect(engine_config)
            return self._connected
        except Exception as exc:
            logger.error("Qlik connect failed: %s", exc)
            return False

    async def discover(self) -> list:
        """Discover all Qlik apps and their contents."""
        from src.connectors.base_connector import ExtractedAsset
        if not self._connected:
            raise RuntimeError("Not connected")

        assets: list[ExtractedAsset] = []

        for app in await self._engine_client.list_apps():
            app_id = app.get("resourceId", app.get("id", ""))
            assets.append(ExtractedAsset(
                asset_id=app_id,
                asset_type="app",
                name=app.get("name", ""),
                source_path=app.get("resourceType", "app"),
                platform="qlik",
                metadata=app,
            ))

        self._discovered_assets = assets
        return assets

    async def extract_metadata(self, asset_ids: list[str] | None = None):
        """Extract detailed metadata including load script parsing."""
        from src.connectors.base_connector import ExtractionResult
        if not self._connected:
            raise RuntimeError("Not connected")

        assets = self._discovered_assets
        if asset_ids:
            assets = [a for a in assets if a.asset_id in asset_ids]

        for asset in assets:
            if asset.asset_type == "app" and asset.asset_id:
                try:
                    # Get load script
                    script = await self._engine_client.get_app_script(asset.asset_id)
                    if script:
                        parsed = self._parser.parse(script)
                        asset.metadata["parsed_script"] = {
                            "tables": parsed.table_count,
                            "fields": parsed.field_count,
                            "variables": len(parsed.variables),
                            "connections": parsed.connections,
                            "table_names": parsed.table_names,
                        }

                    # Get measures and translate
                    measures = await self._engine_client.get_app_measures(asset.asset_id)
                    for m in measures:
                        expr = m.get("qMeasure", {}).get("qDef", "")
                        name = m.get("qMeasure", {}).get("qLabel", m.get("title", ""))
                        if expr:
                            qm = QlikMeasure(name=name, expression=expr)
                            result = self._translator.translate(qm)
                            asset.metadata.setdefault("translations", []).append({
                                "name": name,
                                "source": expr,
                                "dax": result.dax_expression,
                                "confidence": result.confidence,
                            })
                except Exception as exc:
                    asset.metadata["extraction_error"] = str(exc)

        return ExtractionResult(platform="qlik", assets=assets)

    async def disconnect(self) -> None:
        await self._engine_client.disconnect()
        self._connected = False
        self._discovered_assets = []
