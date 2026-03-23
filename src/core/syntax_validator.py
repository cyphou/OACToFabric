"""Syntax validators for translated code.

Validates:
- DAX expressions (balanced parentheses, known functions, basic grammar)
- PySpark code (Python AST parse)
- Spark SQL (basic SQL grammar checks)
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: ValidationSeverity
    message: str
    line: int | None = None
    column: int | None = None


@dataclass
class SyntaxValidationResult:
    """Result of syntax validation."""

    language: str
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    code: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)


# ---------------------------------------------------------------------------
# DAX Validator
# ---------------------------------------------------------------------------

_KNOWN_DAX_FUNCTIONS = {
    "SUM", "SUMX", "COUNT", "COUNTA", "COUNTX", "COUNTROWS", "DISTINCTCOUNT",
    "AVERAGE", "AVERAGEX", "MIN", "MINX", "MAX", "MAXX",
    "CALCULATE", "CALCULATETABLE", "FILTER", "ALL", "ALLEXCEPT", "ALLSELECTED",
    "VALUES", "DISTINCT", "RELATED", "RELATEDTABLE", "LOOKUPVALUE",
    "IF", "SWITCH", "AND", "OR", "NOT", "TRUE", "FALSE", "BLANK", "ISBLANK",
    "DIVIDE", "INT", "ROUND", "ROUNDUP", "ROUNDDOWN", "ABS", "MOD",
    "CONCATENATE", "CONCATENATEX", "LEFT", "RIGHT", "MID", "LEN", "UPPER", "LOWER", "TRIM",
    "FORMAT", "CONVERT", "CURRENCY", "FIXED",
    "DATE", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND",
    "TODAY", "NOW", "DATEADD", "DATEDIFF", "CALENDAR", "CALENDARAUTO",
    "EOMONTH", "SAMEPERIODLASTYEAR", "TOTALYTD", "TOTALQTD", "TOTALMTD",
    "RANKX", "TOPN", "EARLIER", "EARLIEST",
    "HASONEVALUE", "HASONEFILTER", "ISFILTERED", "ISCROSSFILTERED",
    "SELECTEDVALUE", "USERRELATIONSHIP", "USERELATIONSHIP",
    "VAR", "RETURN",
    "USERPRINCIPALNAME", "USERNAME",
    "SUBSTITUTE", "SEARCH", "FIND", "CONTAINSSTRING",
    "UNION", "INTERSECT", "EXCEPT", "NATURALINNERJOIN", "NATURALLEFTOUTERJOIN",
    "ADDCOLUMNS", "SELECTCOLUMNS", "SUMMARIZE", "SUMMARIZECOLUMNS",
    "GENERATESERIES", "GENERATE", "CROSSJOIN",
    "ROW", "DATATABLE", "TABLE",
    "PATH", "PATHITEM", "PATHCONTAINS", "PATHLENGTH",
    "POWER", "SQRT", "LOG", "LN", "EXP",
    "GEOMEAN", "GEOMEANX", "MEDIAN", "MEDIANX",
    "PERCENTILE.EXC", "PERCENTILE.INC",
}


def validate_dax(code: str) -> SyntaxValidationResult:
    """Validate a DAX expression for basic syntax correctness."""
    issues: list[ValidationIssue] = []

    # 1. Balanced parentheses
    paren_count = 0
    for i, ch in enumerate(code):
        if ch == "(":
            paren_count += 1
        elif ch == ")":
            paren_count -= 1
        if paren_count < 0:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Unmatched closing parenthesis at position {i}",
                    column=i,
                )
            )
            break
    if paren_count > 0:
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"{paren_count} unclosed parenthesis(es)",
            )
        )

    # 2. Check for known functions
    func_pattern = re.compile(r"\b([A-Z_][A-Z0-9_.]*)\s*\(", re.IGNORECASE)
    found_functions = func_pattern.findall(code)
    for func_name in found_functions:
        if func_name.upper() not in _KNOWN_DAX_FUNCTIONS:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Unknown DAX function: {func_name}",
                )
            )

    # 3. Check balanced square brackets (column references)
    bracket_count = 0
    for ch in code:
        if ch == "[":
            bracket_count += 1
        elif ch == "]":
            bracket_count -= 1
    if bracket_count != 0:
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Unbalanced square brackets in column references",
            )
        )

    # 4. Check for common anti-patterns
    if "EVALUATE" in code.upper() and code.strip().upper().startswith("EVALUATE"):
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="EVALUATE is a DAX query keyword, not a measure expression",
            )
        )

    valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
    return SyntaxValidationResult(language="dax", valid=valid, issues=issues, code=code)


# ---------------------------------------------------------------------------
# PySpark Validator
# ---------------------------------------------------------------------------


def validate_pyspark(code: str) -> SyntaxValidationResult:
    """Validate Python/PySpark code via AST parsing."""
    issues: list[ValidationIssue] = []

    try:
        ast.parse(code)
    except SyntaxError as e:
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Python syntax error: {e.msg}",
                line=e.lineno,
                column=e.offset,
            )
        )

    # Check for common PySpark anti-patterns
    if "spark.sql" in code and ".select(" in code:
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                message="Mixed spark.sql() and DataFrame API — consider using one style consistently",
            )
        )

    if "collect()" in code:
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="collect() brings all data to driver — avoid for large datasets",
            )
        )

    valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
    return SyntaxValidationResult(language="pyspark", valid=valid, issues=issues, code=code)


# ---------------------------------------------------------------------------
# Spark SQL Validator
# ---------------------------------------------------------------------------


def validate_spark_sql(code: str) -> SyntaxValidationResult:
    """Validate Spark SQL for basic syntax correctness."""
    issues: list[ValidationIssue] = []

    # Balanced parentheses
    paren_count = 0
    for ch in code:
        if ch == "(":
            paren_count += 1
        elif ch == ")":
            paren_count -= 1
    if paren_count != 0:
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Unbalanced parentheses (delta={paren_count})",
            )
        )

    # Check for Oracle-specific syntax that shouldn't be in Spark SQL
    oracle_patterns = [
        (r"\bCONNECT\s+BY\b", "CONNECT BY is Oracle-specific — use CTEs in Spark SQL"),
        (r"\bSTART\s+WITH\b", "START WITH is Oracle-specific — use CTEs in Spark SQL"),
        (r"\bROWNUM\b", "ROWNUM is Oracle-specific — use ROW_NUMBER() OVER () in Spark SQL"),
        (r"\bSYSDATE\b", "SYSDATE is Oracle-specific — use CURRENT_DATE() in Spark SQL"),
        (r"\bNVL\b", "NVL is Oracle-specific — use COALESCE() in Spark SQL"),
        (r"\bDECODE\b", "DECODE is Oracle-specific — use CASE WHEN in Spark SQL"),
        (r"\bFROM\s+DUAL\b", "FROM DUAL is Oracle-specific — remove in Spark SQL"),
    ]

    for pattern, message in oracle_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=message,
                )
            )

    # Basic keyword presence check
    upper_code = code.upper().strip()
    if not any(upper_code.startswith(kw) for kw in ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "MERGE", "WITH")):
        issues.append(
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="SQL query does not start with a recognized keyword",
            )
        )

    valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
    return SyntaxValidationResult(language="spark_sql", valid=valid, issues=issues, code=code)


# ---------------------------------------------------------------------------
# Unified validator
# ---------------------------------------------------------------------------


def validate(code: str, language: str) -> SyntaxValidationResult:
    """Validate code for the given language."""
    validators = {
        "dax": validate_dax,
        "pyspark": validate_pyspark,
        "python": validate_pyspark,
        "spark_sql": validate_spark_sql,
        "sql": validate_spark_sql,
    }
    validator = validators.get(language.lower())
    if validator is None:
        return SyntaxValidationResult(
            language=language,
            valid=True,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    message=f"No validator available for language: {language}",
                )
            ],
            code=code,
        )
    return validator(code)
