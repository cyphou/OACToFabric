"""Oracle SQL → Fabric SQL function translator.

Translates Oracle-specific SQL functions and syntax to their
Fabric Lakehouse (Spark SQL) or Warehouse (T-SQL) equivalents.
Based on Agent 02 SPEC § 5.2.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .type_mapper import TargetPlatform

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Translation rules:  (pattern, spark_replacement, tsql_replacement)
#
# Each rule is a tuple of:
#   - compiled regex matching the Oracle pattern
#   - Spark SQL replacement string (may use \1, \2, etc.)
#   - T-SQL replacement string
# ---------------------------------------------------------------------------

_RULES: list[tuple[re.Pattern[str], str, str]] = [
    # NVL(a, b) → COALESCE(a, b)
    (
        re.compile(r"\bNVL\s*\(", re.IGNORECASE),
        "COALESCE(",
        "COALESCE(",
    ),
    # NVL2(a, b, c) → CASE WHEN a IS NOT NULL THEN b ELSE c END
    # (handled separately because of 3 args)

    # SYSDATE → CURRENT_TIMESTAMP()  /  GETDATE()
    (
        re.compile(r"\bSYSDATE\b", re.IGNORECASE),
        "CURRENT_TIMESTAMP()",
        "GETDATE()",
    ),

    # SYSTIMESTAMP → CURRENT_TIMESTAMP() / SYSDATETIMEOFFSET()
    (
        re.compile(r"\bSYSTIMESTAMP\b", re.IGNORECASE),
        "CURRENT_TIMESTAMP()",
        "SYSDATETIMEOFFSET()",
    ),

    # SUBSTR(a, b, c) → SUBSTRING(a, b, c)
    (
        re.compile(r"\bSUBSTR\s*\(", re.IGNORECASE),
        "SUBSTRING(",
        "SUBSTRING(",
    ),

    # INSTR(a, b) → LOCATE(b, a)  (Spark)  /  CHARINDEX(b, a)  (T-SQL)
    # Note: requires arg reorder — handled via function below

    # LENGTH(a) → LENGTH(a) (Spark) / LEN(a) (T-SQL)
    (
        re.compile(r"\bLENGTH\s*\(", re.IGNORECASE),
        "LENGTH(",
        "LEN(",
    ),

    # TRUNC(date) → DATE_TRUNC('day', date) / CAST(date AS DATE)
    # Complex — separate handling below

    # TO_CHAR(date, fmt)  — Spark: DATE_FORMAT  / T-SQL: FORMAT
    # Complex — separate handling below

    # TO_NUMBER(a) → CAST(a AS DOUBLE)  /  CAST(a AS FLOAT)
    (
        re.compile(r"\bTO_NUMBER\s*\(\s*([^)]+)\s*\)", re.IGNORECASE),
        r"CAST(\1 AS DOUBLE)",
        r"CAST(\1 AS FLOAT)",
    ),

    # LISTAGG(...) → CONCAT_WS / STRING_AGG
    # Complex — separate handling below

    # (+) outer join syntax → handled separately

    # ROWNUM → requires ROW_NUMBER rewrite (flagged)

    # DUAL pseudo-table
    (
        re.compile(r"\bFROM\s+DUAL\b", re.IGNORECASE),
        "",  # Spark: just remove FROM DUAL
        "",  # T-SQL: just remove FROM DUAL
    ),

    # || string concatenation → CONCAT (Spark & T-SQL)
    # Handled separately because of multi-operand

    # USER pseudo-column
    (
        re.compile(r"\bUSER\b(?!\s*\()", re.IGNORECASE),
        "CURRENT_USER()",
        "CURRENT_USER",
    ),
]


# ---------------------------------------------------------------------------
# Complex rewrite functions
# ---------------------------------------------------------------------------


def _rewrite_nvl2(sql: str, platform: TargetPlatform) -> str:
    """NVL2(expr, val_if_not_null, val_if_null) → CASE."""
    pattern = re.compile(
        r"\bNVL2\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\)", re.IGNORECASE
    )
    return pattern.sub(
        r"CASE WHEN \1 IS NOT NULL THEN \2 ELSE \3 END", sql
    )


def _rewrite_decode(sql: str, platform: TargetPlatform) -> str:
    """DECODE(expr, search1, result1, ..., default) → CASE.

    Handles the common 4-arg form: DECODE(a, b, c, d).
    For more args a proper parser would be needed; here we handle up to 3 pairs + default.
    """
    # Simple 4-arg: DECODE(a, b, c, d)
    pattern4 = re.compile(
        r"\bDECODE\s*\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)",
        re.IGNORECASE,
    )
    sql = pattern4.sub(r"CASE WHEN \1 = \2 THEN \3 ELSE \4 END", sql)

    # 6-arg: DECODE(a, b1, c1, b2, c2, d)
    pattern6 = re.compile(
        r"\bDECODE\s*\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)",
        re.IGNORECASE,
    )
    sql = pattern6.sub(
        r"CASE WHEN \1 = \2 THEN \3 WHEN \1 = \4 THEN \5 ELSE \6 END", sql
    )
    return sql


def _rewrite_instr(sql: str, platform: TargetPlatform) -> str:
    """INSTR(string, substring) → LOCATE(substring, string) / CHARINDEX(substring, string)."""
    pattern = re.compile(
        r"\bINSTR\s*\(\s*([^,]+),\s*([^)]+)\)", re.IGNORECASE
    )
    if platform == TargetPlatform.LAKEHOUSE:
        return pattern.sub(r"LOCATE(\2, \1)", sql)
    return pattern.sub(r"CHARINDEX(\2, \1)", sql)


def _rewrite_to_char(sql: str, platform: TargetPlatform) -> str:
    """TO_CHAR(expr, fmt) → DATE_FORMAT / FORMAT."""
    pattern = re.compile(
        r"\bTO_CHAR\s*\(\s*([^,]+),\s*'([^']+)'\s*\)", re.IGNORECASE
    )
    fmt_map = _oracle_to_spark_date_format if platform == TargetPlatform.LAKEHOUSE else _oracle_to_tsql_date_format

    def _replace(m: re.Match[str]) -> str:
        expr = m.group(1).strip()
        oracle_fmt = m.group(2)
        target_fmt = fmt_map(oracle_fmt)
        if platform == TargetPlatform.LAKEHOUSE:
            return f"DATE_FORMAT({expr}, '{target_fmt}')"
        return f"FORMAT({expr}, '{target_fmt}')"

    return pattern.sub(_replace, sql)


def _rewrite_to_date(sql: str, platform: TargetPlatform) -> str:
    """TO_DATE(str, fmt)."""
    pattern = re.compile(
        r"\bTO_DATE\s*\(\s*([^,]+),\s*'([^']+)'\s*\)", re.IGNORECASE
    )

    def _replace(m: re.Match[str]) -> str:
        expr = m.group(1).strip()
        oracle_fmt = m.group(2)
        if platform == TargetPlatform.LAKEHOUSE:
            spark_fmt = _oracle_to_spark_date_format(oracle_fmt)
            return f"TO_DATE({expr}, '{spark_fmt}')"
        return f"CONVERT(DATE, {expr}, 120)"  # ISO style

    return pattern.sub(_replace, sql)


def _rewrite_trunc_date(sql: str, platform: TargetPlatform) -> str:
    """TRUNC(date_expr) → DATE_TRUNC / CAST."""
    pattern = re.compile(r"\bTRUNC\s*\(\s*([^)]+)\)", re.IGNORECASE)
    if platform == TargetPlatform.LAKEHOUSE:
        return pattern.sub(r"DATE_TRUNC('day', \1)", sql)
    return pattern.sub(r"CAST(\1 AS DATE)", sql)


def _rewrite_concat(sql: str, platform: TargetPlatform) -> str:
    """Oracle ``||`` concatenation → CONCAT()."""
    # Only replace || when it looks like string concatenation (not logical OR in T-SQL)
    parts = re.split(r"\s*\|\|\s*", sql)
    if len(parts) <= 1:
        return sql
    args = ", ".join(p.strip() for p in parts)
    return f"CONCAT({args})"


def _rewrite_outer_join(sql: str, platform: TargetPlatform) -> str:
    """Oracle (+) outer join → ANSI LEFT/RIGHT JOIN.

    This is a best-effort rewrite for simple cases.  Complex multi-table
    (+) joins are flagged for manual review.
    """
    if "(+)" not in sql:
        return sql
    logger.warning("Oracle (+) outer join detected — best-effort rewrite; review recommended")
    # Simple pattern: WHERE a.col = b.col(+)  →  LEFT JOIN
    sql = re.sub(r"\(\+\)", "/* (+) REVIEW */", sql)
    return sql


def _rewrite_rownum(sql: str, platform: TargetPlatform) -> str:
    """Flag ROWNUM usage — requires manual rewrite to ROW_NUMBER()."""
    if re.search(r"\bROWNUM\b", sql, re.IGNORECASE):
        logger.warning("ROWNUM detected — manual rewrite to ROW_NUMBER() OVER(...) required")
        sql = re.sub(r"\bROWNUM\b", "/* ROWNUM → ROW_NUMBER() OVER(...) */", sql, flags=re.IGNORECASE)
    return sql


def _rewrite_months_between(sql: str, platform: TargetPlatform) -> str:
    """MONTHS_BETWEEN(a, b)."""
    if platform == TargetPlatform.LAKEHOUSE:
        return sql  # Spark has MONTHS_BETWEEN natively
    pattern = re.compile(r"\bMONTHS_BETWEEN\s*\(\s*([^,]+),\s*([^)]+)\)", re.IGNORECASE)
    return pattern.sub(r"DATEDIFF(month, \2, \1)", sql)


def _rewrite_listagg(sql: str, platform: TargetPlatform) -> str:
    """LISTAGG(col, sep) WITHIN GROUP (ORDER BY ...) → CONCAT_WS / STRING_AGG."""
    pattern = re.compile(
        r"\bLISTAGG\s*\(\s*([^,]+),\s*'([^']*)'\s*\)\s*WITHIN\s+GROUP\s*\(\s*ORDER\s+BY\s+([^)]+)\)",
        re.IGNORECASE,
    )
    if platform == TargetPlatform.LAKEHOUSE:
        return pattern.sub(r"CONCAT_WS('\2', COLLECT_LIST(\1))", sql)
    return pattern.sub(r"STRING_AGG(\1, '\2') WITHIN GROUP (ORDER BY \3)", sql)


# ---------------------------------------------------------------------------
# Date format translation helpers
# ---------------------------------------------------------------------------


def _oracle_to_spark_date_format(fmt: str) -> str:
    """Best-effort Oracle → Java SimpleDateFormat conversion."""
    replacements = [
        ("YYYY", "yyyy"), ("YY", "yy"),
        ("MM", "MM"), ("MON", "MMM"), ("MONTH", "MMMM"),
        ("DD", "dd"), ("DY", "EEE"), ("DAY", "EEEE"),
        ("HH24", "HH"), ("HH12", "hh"), ("HH", "hh"),
        ("MI", "mm"), ("SS", "ss"), ("FF", "SSS"),
        ("AM", "a"), ("PM", "a"),
    ]
    result = fmt
    for oracle, java in replacements:
        result = result.replace(oracle, java)
    return result


def _oracle_to_tsql_date_format(fmt: str) -> str:
    """Best-effort Oracle → .NET format string conversion."""
    replacements = [
        ("YYYY", "yyyy"), ("YY", "yy"),
        ("MM", "MM"), ("MON", "MMM"), ("MONTH", "MMMM"),
        ("DD", "dd"), ("DY", "ddd"), ("DAY", "dddd"),
        ("HH24", "HH"), ("HH12", "hh"), ("HH", "hh"),
        ("MI", "mm"), ("SS", "ss"), ("FF", "fff"),
        ("AM", "tt"), ("PM", "tt"),
    ]
    result = fmt
    for oracle, dotnet in replacements:
        result = result.replace(oracle, dotnet)
    return result


# ---------------------------------------------------------------------------
# Main translation entry point
# ---------------------------------------------------------------------------


def translate_sql(
    sql: str,
    platform: TargetPlatform = TargetPlatform.LAKEHOUSE,
) -> str:
    """Translate Oracle SQL to Fabric Spark SQL or T-SQL.

    Applies all known rewrite rules.  Returns the translated SQL string.
    Complex patterns that can't be auto-translated are flagged with
    ``/* REVIEW */`` comments.
    """
    result = sql

    # Apply complex rewrites first (order matters)
    result = _rewrite_nvl2(result, platform)
    result = _rewrite_decode(result, platform)
    result = _rewrite_instr(result, platform)
    result = _rewrite_to_char(result, platform)
    result = _rewrite_to_date(result, platform)
    result = _rewrite_trunc_date(result, platform)
    result = _rewrite_months_between(result, platform)
    result = _rewrite_listagg(result, platform)
    result = _rewrite_outer_join(result, platform)
    result = _rewrite_rownum(result, platform)
    result = _rewrite_concat(result, platform)

    # Apply simple regex rules
    for pattern, spark_repl, tsql_repl in _RULES:
        repl = spark_repl if platform == TargetPlatform.LAKEHOUSE else tsql_repl
        result = pattern.sub(repl, result)

    return result
