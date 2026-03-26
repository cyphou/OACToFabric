"""Fabric name sanitization for Lakehouse / Warehouse table and column names.

Ported from T2P's fabric_naming — sanitizes names to comply with
Fabric Delta table naming rules (alphanumeric + underscore, no leading
digits, lowercase).
"""

from __future__ import annotations

import re

# Pre-compiled patterns
_BRACKETS = re.compile(r"[\[\]]")
_NON_ALNUM_UNDER = re.compile(r"[^a-zA-Z0-9_]")
_LEADING_DIGITS = re.compile(r"^[0-9]+")
_MULTI_UNDERSCORE = re.compile(r"_{2,}")

# OAC-specific prefixes to strip (view, table, fact, dimension)
_OAC_PREFIXES = re.compile(r"^(?:v_|tbl_|f_|d_|vw_|dim_|fact_)", re.IGNORECASE)


def sanitize_table_name(name: str, strip_oac_prefix: bool = True) -> str:
    """Sanitize a table name for Fabric Lakehouse (Delta table naming rules).

    Rules:
    1. Strip square brackets
    2. Optionally strip common OAC prefixes (v_, tbl_, f_, d_, dim_, fact_)
    3. Replace non-alphanumeric chars with underscore
    4. Collapse multiple underscores
    5. Strip leading/trailing underscores
    6. Strip leading digits
    7. Lowercase
    8. Fallback to 'table' if empty

    Parameters
    ----------
    name : str
        Original table name from OAC/Oracle.
    strip_oac_prefix : bool
        Whether to strip common OAC naming prefixes.

    Returns
    -------
    str
        Sanitized table name.
    """
    result = _BRACKETS.sub("", name)
    if strip_oac_prefix:
        result = _OAC_PREFIXES.sub("", result)
    result = _NON_ALNUM_UNDER.sub("_", result)
    result = _MULTI_UNDERSCORE.sub("_", result)
    result = result.strip("_")
    result = _LEADING_DIGITS.sub("", result)
    result = result.strip("_").lower()
    return result or "table"


def sanitize_column_name(name: str) -> str:
    """Sanitize a column name for Fabric Lakehouse.

    More permissive than table names — allows mixed case.
    """
    result = _BRACKETS.sub("", name)
    result = _NON_ALNUM_UNDER.sub("_", result)
    result = _MULTI_UNDERSCORE.sub("_", result)
    result = result.strip("_")
    result = _LEADING_DIGITS.sub("", result)
    result = result.strip("_")
    return result or "column"


def sanitize_schema_name(name: str) -> str:
    """Sanitize a schema name for Fabric."""
    result = _NON_ALNUM_UNDER.sub("_", name)
    result = _MULTI_UNDERSCORE.sub("_", result)
    return result.strip("_").lower() or "dbo"


def to_pascal_case(name: str) -> str:
    """Convert a name to PascalCase (for TMDL table display names)."""
    parts = re.split(r"[_\s-]+", name)
    return "".join(p.capitalize() for p in parts if p)


def to_snake_case(name: str) -> str:
    """Convert a name to snake_case (for column names)."""
    # Insert underscore before uppercase letters
    result = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    result = re.sub(r"[^a-zA-Z0-9]+", "_", result)
    return result.strip("_").lower()
