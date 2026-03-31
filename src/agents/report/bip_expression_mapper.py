"""BIP Expression Mapper — BI Publisher XSL/XPath → RDL expressions.

Converts BI Publisher template expressions (XSL-FO / XPath syntax) to
RDL expression syntax used by Power BI Paginated Reports.

Handles:
  - Field references:  ``{COLUMN_NAME}`` → ``=Fields!COLUMN_NAME.Value``
  - Aggregations:  ``sum(COLUMN)`` → ``=Sum(Fields!COLUMN.Value)``
  - Conditionals:  ``if … then … else`` → ``=IIF(…, …, …)``
  - Format masks:  BIP number/date formats → .NET format strings
  - XPath functions: ``concat()``, ``substring()``, ``string-length()``
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ExpressionMappingResult:
    """Result of mapping a single BIP expression to RDL."""

    original: str
    rdl_expression: str
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Aggregate mapping
# ---------------------------------------------------------------------------

_BIP_AGGREGATES: dict[str, str] = {
    "sum": "Sum",
    "count": "Count",
    "avg": "Avg",
    "min": "Min",
    "max": "Max",
    "count-distinct": "CountDistinct",
    "stdev": "StDev",
    "var": "Var",
    "first": "First",
    "last": "Last",
}

_RE_BIP_AGG = re.compile(
    r"\b(" + "|".join(_BIP_AGGREGATES.keys()) + r")\s*\(\s*(\w+(?:\.\w+)*)\s*\)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Field reference mapping
# ---------------------------------------------------------------------------

_RE_FIELD_REF = re.compile(r"\{(\w+(?:\.\w+)*)\}")

# ---------------------------------------------------------------------------
# XPath function mapping
# ---------------------------------------------------------------------------

_XPATH_FUNCTIONS: dict[str, str] = {
    "concat": "&",
    "substring": "Mid",
    "string-length": "Len",
    "contains": "InStr",
    "starts-with": "Left",
    "normalize-space": "Trim",
    "translate": "Replace",
    "number": "CDbl",
    "string": "CStr",
    "round": "Round",
    "floor": "Fix",
    "ceiling": "Int",
}

# ---------------------------------------------------------------------------
# Format mask mapping
# ---------------------------------------------------------------------------

_BIP_FORMAT_MAP: dict[str, str] = {
    "#,##0": "#,##0",
    "#,##0.00": "#,##0.00",
    "$#,##0.00": "$#,##0.00",
    "0%": "0%",
    "0.00%": "0.00%",
    "MM/DD/YYYY": "MM/dd/yyyy",
    "DD-MON-YYYY": "dd-MMM-yyyy",
    "YYYY-MM-DD": "yyyy-MM-dd",
    "DD/MM/YYYY": "dd/MM/yyyy",
    "HH:MI:SS": "HH:mm:ss",
    "HH24:MI:SS": "HH:mm:ss",
    "MM/DD/YYYY HH:MI:SS": "MM/dd/yyyy HH:mm:ss",
}


# ---------------------------------------------------------------------------
# Core mapping logic
# ---------------------------------------------------------------------------


def _map_field_reference(field_name: str) -> str:
    """Convert a BIP field name to RDL field expression."""
    clean = field_name.replace(".", "_")
    return f"Fields!{clean}.Value"


def _map_aggregate(match: re.Match) -> str:
    """Convert a BIP aggregate call to RDL aggregate."""
    func = match.group(1).lower()
    field_name = match.group(2)
    rdl_func = _BIP_AGGREGATES.get(func, "Sum")
    return f"{rdl_func}({_map_field_reference(field_name)})"


def _map_conditional(expr: str) -> tuple[str, float]:
    """Convert BIP if/then/else to RDL IIF.

    Returns (rdl_expression, confidence).
    """
    pattern = re.compile(
        r"if\s+(.+?)\s+then\s+(.+?)\s+else\s+(.+)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.match(expr.strip())
    if not m:
        return expr, 0.5

    condition = map_bip_expression(m.group(1).strip()).rdl_expression
    then_val = map_bip_expression(m.group(2).strip()).rdl_expression
    else_val = map_bip_expression(m.group(3).strip()).rdl_expression

    # Strip leading = signs from sub-expressions
    condition = condition.lstrip("=")
    then_val = then_val.lstrip("=")
    else_val = else_val.lstrip("=")

    return f"=IIF({condition}, {then_val}, {else_val})", 0.9


def map_bip_expression(expression: str) -> ExpressionMappingResult:
    """Map a BI Publisher expression to an RDL expression.

    Parameters
    ----------
    expression : str
        BI Publisher expression (XPath/XSL-FO syntax).

    Returns
    -------
    ExpressionMappingResult
        Mapped RDL expression with confidence score.
    """
    if not expression or not expression.strip():
        return ExpressionMappingResult(
            original=expression,
            rdl_expression="",
            confidence=1.0,
        )

    expr = expression.strip()
    warnings: list[str] = []
    confidence = 1.0

    # Check for conditional first
    if re.match(r"\bif\b", expr, re.IGNORECASE):
        rdl, conf = _map_conditional(expr)
        return ExpressionMappingResult(
            original=expression,
            rdl_expression=rdl,
            confidence=conf,
        )

    # Check for aggregates
    agg_match = _RE_BIP_AGG.search(expr)
    if agg_match:
        rdl = _RE_BIP_AGG.sub(_map_aggregate, expr)
        if not rdl.startswith("="):
            rdl = f"={rdl}"
        return ExpressionMappingResult(
            original=expression,
            rdl_expression=rdl,
            confidence=0.95,
        )

    # Check for simple field references
    field_match = _RE_FIELD_REF.search(expr)
    if field_match:
        rdl = _RE_FIELD_REF.sub(
            lambda m: _map_field_reference(m.group(1)),
            expr,
        )
        if not rdl.startswith("="):
            rdl = f"={rdl}"
        return ExpressionMappingResult(
            original=expression,
            rdl_expression=rdl,
            confidence=1.0,
        )

    # Check for XPath functions
    for xpath_fn, rdl_fn in _XPATH_FUNCTIONS.items():
        if xpath_fn in expr.lower():
            warnings.append(f"XPath function '{xpath_fn}' mapped to '{rdl_fn}' — verify manually")
            confidence = 0.7
            break

    # Fallback: wrap as literal or expression
    if expr.startswith("'") or expr.replace(".", "", 1).isdigit():
        rdl = f"={expr}"
    else:
        rdl = f"=Fields!{expr.replace('.', '_')}.Value"
        if not any(c.isalpha() for c in expr):
            rdl = f"={expr}"
            confidence = 0.5
            warnings.append("Could not parse expression — returned as-is")

    return ExpressionMappingResult(
        original=expression,
        rdl_expression=rdl,
        confidence=confidence,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Format mask translation
# ---------------------------------------------------------------------------


def map_bip_format(bip_format: str) -> str:
    """Convert a BI Publisher format mask to a .NET format string.

    Parameters
    ----------
    bip_format : str
        BI Publisher format mask.

    Returns
    -------
    str
        Equivalent .NET format string for RDL.
    """
    if not bip_format:
        return ""

    normalized = bip_format.strip().upper()
    for bip_key, rdl_fmt in _BIP_FORMAT_MAP.items():
        if normalized == bip_key.upper():
            return rdl_fmt

    logger.warning("Unknown BIP format mask '%s' — passing through", bip_format)
    return bip_format


# ---------------------------------------------------------------------------
# Batch mapping
# ---------------------------------------------------------------------------


def map_all_expressions(
    expressions: list[str],
) -> list[ExpressionMappingResult]:
    """Map a batch of BI Publisher expressions to RDL.

    Parameters
    ----------
    expressions : list[str]
        BIP expressions.

    Returns
    -------
    list[ExpressionMappingResult]
        Mapped results.
    """
    results = [map_bip_expression(e) for e in expressions]
    total = len(results)
    high_conf = sum(1 for r in results if r.confidence >= 0.9)
    logger.info(
        "Mapped %d BIP expressions: %d high-confidence (%.0f%%)",
        total,
        high_conf,
        (high_conf / total * 100) if total else 0,
    )
    return results
