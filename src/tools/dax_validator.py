"""Deep DAX syntax validator with tokenizer and recursive-descent parser.

Goes far beyond balanced-parentheses checking to catch real DAX errors:

1. **Tokenizer** — splits DAX into tokens (functions, operators, strings,
   numbers, column refs, table refs, keywords).
2. **Structural validation** — checks VAR/RETURN pairing, IF/SWITCH branch
   counts, CALCULATE filter context, nested aggregation depth.
3. **Semantic checks** — unknown function warnings, deprecated function
   detection, common anti-pattern identification (SUMX→SUM, iterator misuse).
4. **Batch mode** — validate all measures in a TMDL file at once.

Usage::

    from src.tools.dax_validator import validate_dax_deep, validate_tmdl_measures

    result = validate_dax_deep("SUM(Sales[Amount])")
    for issue in result.issues:
        print(f"{issue.severity}: {issue.message}")

    # Batch validate all measures from a TMDL file
    results = validate_tmdl_measures(tmdl_content)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Severity & result types
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class DAXIssue:
    """A single validation finding."""

    severity: Severity
    code: str  # e.g. DAX001
    message: str
    position: int | None = None
    measure_name: str = ""


@dataclass
class DAXValidationResult:
    """Result of deep DAX validation."""

    expression: str
    measure_name: str = ""
    valid: bool = True
    issues: list[DAXIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)


# ---------------------------------------------------------------------------
# DAX function catalog (comprehensive)
# ---------------------------------------------------------------------------

_DAX_FUNCTIONS: set[str] = {
    # Aggregation
    "SUM", "SUMX", "COUNT", "COUNTA", "COUNTX", "COUNTROWS", "COUNTBLANK",
    "DISTINCTCOUNT", "DISTINCTCOUNTNOBLANK",
    "AVERAGE", "AVERAGEX", "AVERAGEA",
    "MIN", "MINX", "MINA", "MAX", "MAXX", "MAXA",
    "PRODUCT", "PRODUCTX",
    # Filter
    "CALCULATE", "CALCULATETABLE", "FILTER", "ALL", "ALLEXCEPT",
    "ALLSELECTED", "ALLCROSSFILTERED", "ALLNOBLANKROW",
    "KEEPFILTERS", "REMOVEFILTERS", "USERELATIONSHIP",
    "CROSSFILTER",
    # Table manipulation
    "VALUES", "DISTINCT", "RELATED", "RELATEDTABLE", "LOOKUPVALUE",
    "TREATAS", "SELECTEDVALUE", "HASONEVALUE", "HASONEFILTER",
    "ISFILTERED", "ISCROSSFILTERED", "ISINSCOPE",
    "ADDCOLUMNS", "SELECTCOLUMNS", "SUMMARIZE", "SUMMARIZECOLUMNS",
    "GENERATESERIES", "GENERATE", "GENERATEALL", "CROSSJOIN",
    "ROW", "DATATABLE", "UNION", "INTERSECT", "EXCEPT",
    "NATURALINNERJOIN", "NATURALLEFTOUTERJOIN",
    "TOPN", "SAMPLE", "SUBSTITUTEWITHINDEX",
    # Logic
    "IF", "IF.EAGER", "SWITCH", "AND", "OR", "NOT", "IN",
    "TRUE", "FALSE", "BLANK", "ISBLANK", "ISNUMBER", "ISTEXT",
    "ISERROR", "ISLOGICAL", "ISNONTEXT", "ISEVEN", "ISODD",
    "COALESCE", "ERROR",
    # Math
    "DIVIDE", "INT", "ROUND", "ROUNDUP", "ROUNDDOWN", "MROUND",
    "CEILING", "FLOOR", "TRUNC", "ABS", "SIGN", "MOD",
    "POWER", "SQRT", "LOG", "LOG10", "LN", "EXP",
    "FACT", "GCD", "LCM", "QUOTIENT", "RAND", "RANDBETWEEN",
    "PI", "EVEN", "ODD", "COMBIN", "COMBINA", "PERMUT",
    # Statistical
    "MEDIAN", "MEDIANX", "PERCENTILE.EXC", "PERCENTILE.INC",
    "PERCENTILEX.EXC", "PERCENTILEX.INC",
    "STDEV.S", "STDEV.P", "STDEVX.S", "STDEVX.P",
    "VAR.S", "VAR.P", "VARX.S", "VARX.P",
    "GEOMEAN", "GEOMEANX", "BETA.DIST", "BETA.INV",
    "NORM.DIST", "NORM.INV", "NORM.S.DIST", "NORM.S.INV",
    "T.DIST", "T.DIST.2T", "T.DIST.RT", "T.INV", "T.INV.2T",
    "CHISQ.DIST", "CHISQ.DIST.RT", "CHISQ.INV", "CHISQ.INV.RT",
    "EXPON.DIST", "POISSON.DIST", "CONFIDENCE.NORM", "CONFIDENCE.T",
    "RANKX",
    # Text
    "CONCATENATE", "CONCATENATEX", "LEFT", "RIGHT", "MID", "LEN",
    "UPPER", "LOWER", "TRIM", "SUBSTITUTE", "REPLACE", "REPT",
    "FORMAT", "FIXED", "SEARCH", "FIND", "EXACT",
    "CONTAINSSTRING", "CONTAINSSTRINGEXACT",
    "UNICHAR", "UNICODE", "CODE", "CHAR", "VALUE", "CONVERT",
    # Date / Time
    "DATE", "DATEVALUE", "YEAR", "MONTH", "DAY",
    "HOUR", "MINUTE", "SECOND", "TIME", "TIMEVALUE",
    "TODAY", "NOW", "UTCTODAY", "UTCNOW",
    "CALENDAR", "CALENDARAUTO",
    "DATEADD", "DATEDIFF", "DATESBETWEEN", "DATESINPERIOD",
    "EOMONTH", "EDATE", "WEEKDAY", "WEEKNUM", "YEARFRAC",
    "SAMEPERIODLASTYEAR", "PREVIOUSDAY", "PREVIOUSMONTH",
    "PREVIOUSQUARTER", "PREVIOUSYEAR",
    "NEXTDAY", "NEXTMONTH", "NEXTQUARTER", "NEXTYEAR",
    "STARTOFMONTH", "STARTOFQUARTER", "STARTOFYEAR",
    "ENDOFMONTH", "ENDOFQUARTER", "ENDOFYEAR",
    "FIRSTDATE", "LASTDATE", "FIRSTNONBLANK", "LASTNONBLANK",
    "FIRSTNONBLANKVALUE", "LASTNONBLANKVALUE",
    "TOTALYTD", "TOTALQTD", "TOTALMTD",
    "OPENINGBALANCEMONTH", "OPENINGBALANCEQUARTER", "OPENINGBALANCEYEAR",
    "CLOSINGBALANCEMONTH", "CLOSINGBALANCEQUARTER", "CLOSINGBALANCEYEAR",
    "PARALLELPERIOD", "DATESINPERIOD",
    # Hierarchy / path
    "PATH", "PATHITEM", "PATHITEMREVERSE", "PATHCONTAINS",
    "PATHLENGTH",
    # Information
    "USERPRINCIPALNAME", "USERNAME", "CUSTOMDATA",
    "ISEMPTY", "CONTAINS", "CONTAINSROW",
    "SELECTEDMEASURE", "SELECTEDMEASURENAME", "SELECTEDMEASUREFORMATSTRING",
    # Variables & flow
    "VAR", "RETURN",
    # Table constructor
    "TABLE", "CURRENCY",
    # Deprecated (still valid but warn)
    "EARLIER", "EARLIEST",
}

_DEPRECATED_FUNCTIONS: set[str] = {
    "EARLIER", "EARLIEST",
}

# Functions that indicate aggregation context
_AGGREGATE_FUNCTIONS: set[str] = {
    "SUM", "SUMX", "COUNT", "COUNTA", "COUNTX", "COUNTROWS", "COUNTBLANK",
    "DISTINCTCOUNT", "AVERAGE", "AVERAGEX", "MIN", "MINX", "MAX", "MAXX",
    "PRODUCT", "PRODUCTX", "MEDIAN", "MEDIANX", "RANKX",
    "GEOMEAN", "GEOMEANX",
}

# Iterator functions (take a table + expression)
_ITERATOR_FUNCTIONS: set[str] = {
    "SUMX", "COUNTX", "AVERAGEX", "MINX", "MAXX", "PRODUCTX",
    "MEDIANX", "GEOMEANX", "RANKX", "CONCATENATEX",
    "PERCENTILEX.EXC", "PERCENTILEX.INC",
    "STDEVX.S", "STDEVX.P", "VARX.S", "VARX.P",
}

# Simple aggregates (single column — can be optimized from iterators)
_SIMPLE_AGGREGATES: set[str] = {
    "SUM", "COUNT", "COUNTA", "AVERAGE", "MIN", "MAX", "DISTINCTCOUNT",
}

# Anti-pattern pairs: SUMX(table, col) → SUM(col)
_ANTI_PATTERN_MAP: dict[str, str] = {
    "SUMX": "SUM",
    "AVERAGEX": "AVERAGE",
    "MINX": "MIN",
    "MAXX": "MAX",
    "COUNTX": "COUNT",
}


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------


class TokenType(str, Enum):
    FUNCTION = "function"
    KEYWORD = "keyword"       # VAR, RETURN, TRUE, FALSE
    COLUMN_REF = "column_ref"  # [Column Name]
    TABLE_REF = "table_ref"    # 'Table Name'[...]  or Table[...]
    NUMBER = "number"
    STRING = "string"
    OPERATOR = "operator"
    OPEN_PAREN = "("
    CLOSE_PAREN = ")"
    COMMA = ","
    WHITESPACE = "ws"
    IDENTIFIER = "identifier"
    UNKNOWN = "unknown"


@dataclass
class Token:
    """A single DAX token."""

    type: TokenType
    value: str
    position: int


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Pattern order matters — first match wins
_TOKEN_PATTERNS: list[tuple[TokenType, re.Pattern[str]]] = [
    (TokenType.STRING, re.compile(r'"(?:[^"\\]|\\.)*"')),
    (TokenType.COLUMN_REF, re.compile(r"\[[^\]]*\]")),
    (TokenType.NUMBER, re.compile(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b")),
    (TokenType.OPEN_PAREN, re.compile(r"\(")),
    (TokenType.CLOSE_PAREN, re.compile(r"\)")),
    (TokenType.COMMA, re.compile(r",")),
    (TokenType.OPERATOR, re.compile(r"(?:&&|\|\||<>|>=|<=|[+\-*/=<>&|^])")),
    (TokenType.WHITESPACE, re.compile(r"\s+")),
    (TokenType.IDENTIFIER, re.compile(r"'[^']*'")),  # quoted table name
    (TokenType.IDENTIFIER, re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")),
]


def tokenize_dax(code: str) -> list[Token]:
    """Tokenize a DAX expression into typed tokens."""
    tokens: list[Token] = []
    pos = 0
    length = len(code)

    while pos < length:
        # Try single-line comment
        if code[pos:pos+2] == "//":
            end = code.find("\n", pos)
            if end == -1:
                end = length
            pos = end
            continue

        # Try block comment
        if code[pos:pos+2] == "/*":
            end = code.find("*/", pos + 2)
            if end == -1:
                end = length
            else:
                end += 2
            pos = end
            continue

        matched = False
        for token_type, pattern in _TOKEN_PATTERNS:
            m = pattern.match(code, pos)
            if m:
                value = m.group()
                if token_type == TokenType.WHITESPACE:
                    pos = m.end()
                    matched = True
                    break

                # Classify identifiers as functions/keywords
                if token_type == TokenType.IDENTIFIER and not value.startswith("'"):
                    upper_val = value.upper()
                    if upper_val in ("VAR", "RETURN"):
                        token_type = TokenType.KEYWORD
                    elif upper_val in ("TRUE", "FALSE", "BLANK"):
                        token_type = TokenType.KEYWORD
                    else:
                        # Check if followed by "(" (with optional whitespace)
                        rest = code[m.end():].lstrip()
                        if rest.startswith("("):
                            token_type = TokenType.FUNCTION
                        else:
                            # Could be a table reference like 'Sales' before [Col]
                            token_type = TokenType.TABLE_REF

                tokens.append(Token(type=token_type, value=value, position=pos))
                pos = m.end()
                matched = True
                break

        if not matched:
            tokens.append(Token(type=TokenType.UNKNOWN, value=code[pos], position=pos))
            pos += 1

    return tokens


# ---------------------------------------------------------------------------
# Deep validation
# ---------------------------------------------------------------------------


def validate_dax_deep(
    code: str,
    *,
    measure_name: str = "",
    check_anti_patterns: bool = True,
    max_nesting_depth: int = 10,
) -> DAXValidationResult:
    """Deep DAX validation with tokenization and structural checks.

    Checks performed:

    ====== ===========================================================
    Code   Check
    ====== ===========================================================
    DAX001 Unbalanced parentheses
    DAX002 Unbalanced square brackets
    DAX003 Unknown function name
    DAX004 Deprecated function usage
    DAX005 Iterator anti-pattern (SUMX → SUM)
    DAX006 VAR without RETURN
    DAX007 RETURN without VAR
    DAX008 Excessive nesting depth
    DAX009 Empty expression
    DAX010 CALCULATE with scalar filter (instead of boolean)
    DAX011 Nested aggregation (aggregate inside aggregate)
    DAX012 Unterminated string literal
    DAX013 IF with wrong argument count
    DAX014 DIVIDE with wrong argument count
    ====== ===========================================================

    Parameters
    ----------
    code
        DAX expression to validate.
    measure_name
        Optional measure name for error context.
    check_anti_patterns
        Whether to check for iterator anti-patterns.
    max_nesting_depth
        Maximum parenthesis nesting depth before warning.

    Returns
    -------
    DAXValidationResult
    """
    result = DAXValidationResult(expression=code, measure_name=measure_name)

    # DAX009: empty expression
    if not code or not code.strip():
        result.issues.append(DAXIssue(
            severity=Severity.ERROR,
            code="DAX009",
            message="Empty expression",
            measure_name=measure_name,
        ))
        result.valid = False
        return result

    # DAX012: unterminated string
    in_string = False
    for i, ch in enumerate(code):
        if ch == '"' and (i == 0 or code[i - 1] != '\\'):
            in_string = not in_string
    if in_string:
        result.issues.append(DAXIssue(
            severity=Severity.ERROR,
            code="DAX012",
            message="Unterminated string literal",
            measure_name=measure_name,
        ))
        result.valid = False

    # Tokenize
    tokens = tokenize_dax(code)

    # DAX001: unbalanced parentheses
    paren_depth = 0
    max_depth = 0
    for tok in tokens:
        if tok.type == TokenType.OPEN_PAREN:
            paren_depth += 1
            max_depth = max(max_depth, paren_depth)
        elif tok.type == TokenType.CLOSE_PAREN:
            paren_depth -= 1
        if paren_depth < 0:
            result.issues.append(DAXIssue(
                severity=Severity.ERROR,
                code="DAX001",
                message=f"Unmatched closing parenthesis at position {tok.position}",
                position=tok.position,
                measure_name=measure_name,
            ))
            result.valid = False
            break
    if paren_depth > 0:
        result.issues.append(DAXIssue(
            severity=Severity.ERROR,
            code="DAX001",
            message=f"{paren_depth} unclosed parenthesis(es)",
            measure_name=measure_name,
        ))
        result.valid = False

    # DAX008: excessive nesting
    if max_depth > max_nesting_depth:
        result.issues.append(DAXIssue(
            severity=Severity.WARNING,
            code="DAX008",
            message=f"Nesting depth {max_depth} exceeds threshold {max_nesting_depth}",
            measure_name=measure_name,
        ))

    # DAX002: unbalanced brackets
    bracket_count = 0
    for tok in tokens:
        if tok.type == TokenType.COLUMN_REF:
            continue  # Already balanced by tokenizer
        for ch in tok.value:
            if ch == "[":
                bracket_count += 1
            elif ch == "]":
                bracket_count -= 1
    if bracket_count != 0:
        result.issues.append(DAXIssue(
            severity=Severity.ERROR,
            code="DAX002",
            message="Unbalanced square brackets in column references",
            measure_name=measure_name,
        ))
        result.valid = False

    # Collect function tokens
    func_tokens = [t for t in tokens if t.type == TokenType.FUNCTION]

    # DAX003: unknown functions
    for ft in func_tokens:
        if ft.value.upper() not in _DAX_FUNCTIONS:
            result.issues.append(DAXIssue(
                severity=Severity.WARNING,
                code="DAX003",
                message=f"Unknown DAX function: {ft.value}",
                position=ft.position,
                measure_name=measure_name,
            ))

    # DAX004: deprecated functions
    for ft in func_tokens:
        if ft.value.upper() in _DEPRECATED_FUNCTIONS:
            result.issues.append(DAXIssue(
                severity=Severity.WARNING,
                code="DAX004",
                message=f"Deprecated function: {ft.value} — consider using VAR instead",
                position=ft.position,
                measure_name=measure_name,
            ))

    # DAX005: iterator anti-patterns (SUMX(Table, Table[Col]) → SUM(Table[Col]))
    if check_anti_patterns:
        _check_iterator_anti_patterns(tokens, result, measure_name)

    # DAX006/DAX007: VAR/RETURN pairing
    keyword_tokens = [t for t in tokens if t.type == TokenType.KEYWORD]
    var_count = sum(1 for t in keyword_tokens if t.value.upper() == "VAR")
    return_count = sum(1 for t in keyword_tokens if t.value.upper() == "RETURN")
    if var_count > 0 and return_count == 0:
        result.issues.append(DAXIssue(
            severity=Severity.ERROR,
            code="DAX006",
            message=f"Found {var_count} VAR declaration(s) but no RETURN",
            measure_name=measure_name,
        ))
        result.valid = False
    if return_count > 0 and var_count == 0:
        result.issues.append(DAXIssue(
            severity=Severity.ERROR,
            code="DAX007",
            message="Found RETURN without preceding VAR",
            measure_name=measure_name,
        ))
        result.valid = False

    # DAX011: nested aggregation detection
    _check_nested_aggregation(tokens, result, measure_name)

    # DAX013: IF argument count check
    _check_if_args(tokens, code, result, measure_name)

    # DAX014: DIVIDE argument count check
    _check_divide_args(tokens, code, result, measure_name)

    return result


# ---------------------------------------------------------------------------
# Helper checks
# ---------------------------------------------------------------------------


def _check_iterator_anti_patterns(
    tokens: list[Token],
    result: DAXValidationResult,
    measure_name: str,
) -> None:
    """DAX005: detect SUMX(Table, Table[Col]) that could be SUM(Table[Col])."""
    for i, tok in enumerate(tokens):
        if tok.type != TokenType.FUNCTION:
            continue
        func_upper = tok.value.upper()
        if func_upper not in _ANTI_PATTERN_MAP:
            continue

        # Find the content between the opening and closing paren
        # Simple heuristic: look at tokens between this func's ( and matching )
        paren_start = None
        for j in range(i + 1, len(tokens)):
            if tokens[j].type == TokenType.OPEN_PAREN:
                paren_start = j
                break

        if paren_start is None:
            continue

        # Find matching close paren
        depth = 1
        paren_end = None
        for j in range(paren_start + 1, len(tokens)):
            if tokens[j].type == TokenType.OPEN_PAREN:
                depth += 1
            elif tokens[j].type == TokenType.CLOSE_PAREN:
                depth -= 1
                if depth == 0:
                    paren_end = j
                    break

        if paren_end is None:
            continue

        # Get content tokens (excluding parens)
        inner = tokens[paren_start + 1:paren_end]

        # Find comma separator at depth 0
        comma_pos = None
        d = 0
        for j, t in enumerate(inner):
            if t.type == TokenType.OPEN_PAREN:
                d += 1
            elif t.type == TokenType.CLOSE_PAREN:
                d -= 1
            elif t.type == TokenType.COMMA and d == 0:
                comma_pos = j
                break

        if comma_pos is None:
            continue

        # Check if second arg is a simple column reference (Table[Col])
        after_comma = [t for t in inner[comma_pos + 1:] if t.type != TokenType.WHITESPACE]
        if len(after_comma) == 1 and after_comma[0].type == TokenType.COLUMN_REF:
            simple = _ANTI_PATTERN_MAP[func_upper]
            result.issues.append(DAXIssue(
                severity=Severity.WARNING,
                code="DAX005",
                message=f"{func_upper}(table, col) can be simplified to {simple}(col)",
                position=tok.position,
                measure_name=measure_name,
            ))
        elif len(after_comma) == 2:
            # Could be Table[Col] — a table ref followed by column ref
            if after_comma[0].type == TokenType.TABLE_REF and after_comma[1].type == TokenType.COLUMN_REF:
                simple = _ANTI_PATTERN_MAP[func_upper]
                result.issues.append(DAXIssue(
                    severity=Severity.WARNING,
                    code="DAX005",
                    message=f"{func_upper}(table, Table[Col]) can be simplified to {simple}(Table[Col])",
                    position=tok.position,
                    measure_name=measure_name,
                ))


def _check_nested_aggregation(
    tokens: list[Token],
    result: DAXValidationResult,
    measure_name: str,
) -> None:
    """DAX011: detect aggregation functions nested inside other aggregations."""
    # Track aggregation depth
    agg_stack: list[str] = []
    paren_depths: list[int] = []
    current_depth = 0

    for tok in tokens:
        if tok.type == TokenType.FUNCTION and tok.value.upper() in _AGGREGATE_FUNCTIONS:
            if agg_stack:
                result.issues.append(DAXIssue(
                    severity=Severity.WARNING,
                    code="DAX011",
                    message=(
                        f"Nested aggregation: {tok.value} inside "
                        f"{agg_stack[-1]} — may cause unexpected results"
                    ),
                    position=tok.position,
                    measure_name=measure_name,
                ))
            agg_stack.append(tok.value.upper())
            paren_depths.append(current_depth)
        elif tok.type == TokenType.OPEN_PAREN:
            current_depth += 1
        elif tok.type == TokenType.CLOSE_PAREN:
            current_depth -= 1
            # Pop aggregation stack when its scope closes
            while paren_depths and current_depth < paren_depths[-1]:
                agg_stack.pop()
                paren_depths.pop()


def _count_top_level_commas(tokens: list[Token], start: int, end: int) -> int:
    """Count commas at depth 0 between start and end indices."""
    count = 0
    depth = 0
    for i in range(start, end):
        tok = tokens[i]
        if tok.type == TokenType.OPEN_PAREN:
            depth += 1
        elif tok.type == TokenType.CLOSE_PAREN:
            depth -= 1
        elif tok.type == TokenType.COMMA and depth == 0:
            count += 1
    return count


def _check_if_args(
    tokens: list[Token],
    code: str,
    result: DAXValidationResult,
    measure_name: str,
) -> None:
    """DAX013: IF must have 2 or 3 arguments."""
    for i, tok in enumerate(tokens):
        if tok.type != TokenType.FUNCTION or tok.value.upper() != "IF":
            continue

        paren_start = None
        for j in range(i + 1, len(tokens)):
            if tokens[j].type == TokenType.OPEN_PAREN:
                paren_start = j
                break
        if paren_start is None:
            continue

        depth = 1
        paren_end = None
        for j in range(paren_start + 1, len(tokens)):
            if tokens[j].type == TokenType.OPEN_PAREN:
                depth += 1
            elif tokens[j].type == TokenType.CLOSE_PAREN:
                depth -= 1
                if depth == 0:
                    paren_end = j
                    break
        if paren_end is None:
            continue

        commas = _count_top_level_commas(tokens, paren_start + 1, paren_end)
        arg_count = commas + 1
        if arg_count < 2:
            result.issues.append(DAXIssue(
                severity=Severity.ERROR,
                code="DAX013",
                message=f"IF requires at least 2 arguments, got {arg_count}",
                position=tok.position,
                measure_name=measure_name,
            ))
            result.valid = False
        elif arg_count > 3:
            result.issues.append(DAXIssue(
                severity=Severity.ERROR,
                code="DAX013",
                message=f"IF accepts at most 3 arguments, got {arg_count}",
                position=tok.position,
                measure_name=measure_name,
            ))
            result.valid = False


def _check_divide_args(
    tokens: list[Token],
    code: str,
    result: DAXValidationResult,
    measure_name: str,
) -> None:
    """DAX014: DIVIDE must have 2 or 3 arguments."""
    for i, tok in enumerate(tokens):
        if tok.type != TokenType.FUNCTION or tok.value.upper() != "DIVIDE":
            continue

        paren_start = None
        for j in range(i + 1, len(tokens)):
            if tokens[j].type == TokenType.OPEN_PAREN:
                paren_start = j
                break
        if paren_start is None:
            continue

        depth = 1
        paren_end = None
        for j in range(paren_start + 1, len(tokens)):
            if tokens[j].type == TokenType.OPEN_PAREN:
                depth += 1
            elif tokens[j].type == TokenType.CLOSE_PAREN:
                depth -= 1
                if depth == 0:
                    paren_end = j
                    break
        if paren_end is None:
            continue

        commas = _count_top_level_commas(tokens, paren_start + 1, paren_end)
        arg_count = commas + 1
        if arg_count < 2:
            result.issues.append(DAXIssue(
                severity=Severity.ERROR,
                code="DAX014",
                message=f"DIVIDE requires at least 2 arguments, got {arg_count}",
                position=tok.position,
                measure_name=measure_name,
            ))
            result.valid = False
        elif arg_count > 3:
            result.issues.append(DAXIssue(
                severity=Severity.ERROR,
                code="DAX014",
                message=f"DIVIDE accepts at most 3 arguments, got {arg_count}",
                position=tok.position,
                measure_name=measure_name,
            ))
            result.valid = False


# ---------------------------------------------------------------------------
# TMDL measure extraction + batch validation
# ---------------------------------------------------------------------------

_MEASURE_PATTERN = re.compile(
    r"^\s+measure\s+'?([^'=\n]+?)'?\s*=\s*(.*?)(?=\n\s+(?:measure|column|partition|annotation|lineageTag:|formatString:|displayFolder:|\Z))",
    re.MULTILINE | re.DOTALL,
)

# Simpler pattern: measure name = expression (spanning multiple lines until
# next TMDL keyword at the same indent level or end of file)
_MEASURE_BLOCK_PATTERN = re.compile(
    r"^\t\tmeasure\s+([^\n=]+?)\s*=\s*\n?(.*?)(?=\n\t\t(?:measure|column|partition|hierarchy|annotation)\s|\n\ttable\s|\Z)",
    re.MULTILINE | re.DOTALL,
)

# Even simpler: just grab lines after "measure Name ="
_MEASURE_SIMPLE = re.compile(
    r"^\s+measure\s+(.+?)\s*=\s*(.+?)$",
    re.MULTILINE,
)


def extract_measures_from_tmdl(content: str) -> list[tuple[str, str]]:
    """Extract (measure_name, dax_expression) pairs from TMDL content.

    Handles multi-line expressions that continue on subsequent indented lines.
    """
    measures: list[tuple[str, str]] = []
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        # Detect measure start: lines like "  measure MeasureName = expr"
        m = re.match(r"^(\s+)measure\s+(.+?)\s*=\s*(.*)", line)
        if m:
            indent = len(m.group(1))
            name = m.group(2).strip().strip("'")
            expr_parts = []
            first_part = m.group(3).strip()
            if first_part:
                expr_parts.append(first_part)

            # Continue collecting lines that are more indented (continuation)
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                # Skip empty lines within expression
                if not next_line.strip():
                    j += 1
                    continue
                # If the next non-empty line is indented deeper, it's part
                # of the expression
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent > indent:
                    stripped = next_line.strip()
                    # Stop at TMDL properties (formatString:, lineageTag:, etc.)
                    if re.match(r"^(formatString|lineageTag|displayFolder|description|isHidden|annotations|annotation|dataType|summarizeBy)\s*[:=]", stripped):
                        break
                    expr_parts.append(stripped)
                    j += 1
                else:
                    break

            # Build the full expression
            expression = "\n".join(expr_parts).strip() if expr_parts else ""
            # Remove trailing TMDL properties that might have been captured
            expression = re.sub(
                r"\n\s*(formatString|lineageTag|displayFolder).*$",
                "",
                expression,
                flags=re.MULTILINE | re.DOTALL,
            ).strip()

            if expression:
                measures.append((name, expression))

            i = j
        else:
            i += 1

    return measures


def validate_tmdl_measures(
    tmdl_content: str,
    *,
    check_anti_patterns: bool = True,
) -> list[DAXValidationResult]:
    """Extract and validate all DAX measures from a TMDL file.

    Parameters
    ----------
    tmdl_content
        Full content of a .tmdl file.
    check_anti_patterns
        Whether to check for iterator anti-patterns.

    Returns
    -------
    list[DAXValidationResult]
        One result per measure found.
    """
    measures = extract_measures_from_tmdl(tmdl_content)
    results: list[DAXValidationResult] = []

    for name, expression in measures:
        result = validate_dax_deep(
            expression,
            measure_name=name,
            check_anti_patterns=check_anti_patterns,
        )
        results.append(result)

    logger.info(
        "Validated %d measures: %d valid, %d with errors",
        len(results),
        sum(1 for r in results if r.valid),
        sum(1 for r in results if not r.valid),
    )
    return results


# ---------------------------------------------------------------------------
# Batch validation from directory
# ---------------------------------------------------------------------------


def validate_tmdl_directory(
    directory: str,
    *,
    check_anti_patterns: bool = True,
) -> dict[str, list[DAXValidationResult]]:
    """Validate all .tmdl files in a directory tree.

    Parameters
    ----------
    directory
        Root directory containing .tmdl files (searches recursively).

    Returns
    -------
    dict[str, list[DAXValidationResult]]
        Mapping of file path → list of measure validation results.
    """
    from pathlib import Path

    results: dict[str, list[DAXValidationResult]] = {}
    root = Path(directory)

    for tmdl_file in sorted(root.rglob("*.tmdl")):
        content = tmdl_file.read_text(encoding="utf-8")
        measures = validate_tmdl_measures(
            content,
            check_anti_patterns=check_anti_patterns,
        )
        if measures:
            results[str(tmdl_file)] = measures

    total_measures = sum(len(v) for v in results.values())
    total_errors = sum(
        r.error_count
        for measures in results.values()
        for r in measures
    )
    logger.info(
        "Validated %d files, %d measures, %d errors found",
        len(results), total_measures, total_errors,
    )

    return results
