"""Oracle → Fabric data type mapping engine.

Maps Oracle data types to Fabric Lakehouse (Delta/Spark) and
Fabric Warehouse (T-SQL) types based on the rules defined in
Agent 02 SPEC § 4.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TargetPlatform(str, Enum):
    LAKEHOUSE = "lakehouse"  # Spark SQL / Delta
    WAREHOUSE = "warehouse"  # T-SQL


@dataclass(frozen=True)
class TypeMapping:
    """Result of mapping a single Oracle column type."""

    oracle_type: str
    fabric_type: str
    platform: TargetPlatform
    notes: str = ""
    is_fallback: bool = False


# ---------------------------------------------------------------------------
# Regex helpers to parse Oracle type declarations
# ---------------------------------------------------------------------------

_RE_NUMBER = re.compile(r"NUMBER\s*\(\s*(\d+)\s*(?:,\s*(\d+))?\s*\)", re.IGNORECASE)
_RE_VARCHAR2 = re.compile(r"(?:N?VARCHAR2|NCHAR\s+VARYING)\s*\(\s*(\d+)\s*(?:\s+(?:BYTE|CHAR))?\s*\)", re.IGNORECASE)
_RE_CHAR = re.compile(r"N?CHAR\s*\(\s*(\d+)\s*\)", re.IGNORECASE)
_RE_RAW = re.compile(r"RAW\s*\(\s*(\d+)\s*\)", re.IGNORECASE)
_RE_TIMESTAMP_TZ = re.compile(r"TIMESTAMP\s*(?:\(\d+\))?\s+WITH\s+(?:LOCAL\s+)?TIME\s+ZONE", re.IGNORECASE)
_RE_TIMESTAMP = re.compile(r"TIMESTAMP\s*(?:\(\d+\))?", re.IGNORECASE)
_RE_FLOAT = re.compile(r"FLOAT\s*(?:\(\d+\))?", re.IGNORECASE)
_RE_INTERVAL = re.compile(r"INTERVAL\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Mapping engine
# ---------------------------------------------------------------------------


def map_oracle_type(
    oracle_type: str,
    platform: TargetPlatform = TargetPlatform.LAKEHOUSE,
) -> TypeMapping:
    """Map a single Oracle data type string to a Fabric type.

    Returns a TypeMapping with ``is_fallback=True`` if the type was
    unknown and fell back to STRING / VARCHAR(MAX).
    """
    otype = oracle_type.strip().upper()

    # --- NUMBER variants ---
    m = _RE_NUMBER.match(otype)
    if m:
        precision = int(m.group(1))
        scale = int(m.group(2)) if m.group(2) else 0
        if scale == 0:
            if precision <= 9:
                return TypeMapping(oracle_type, "INT" if platform == TargetPlatform.LAKEHOUSE else "INT", platform)
            elif precision <= 18:
                return TypeMapping(oracle_type, "BIGINT", platform)
            else:
                return TypeMapping(oracle_type, f"DECIMAL({precision},{scale})", platform)
        return TypeMapping(oracle_type, f"DECIMAL({precision},{scale})", platform)

    if otype == "NUMBER" or otype.startswith("NUMBER"):
        # NUMBER without precision
        return TypeMapping(oracle_type, "DOUBLE" if platform == TargetPlatform.LAKEHOUSE else "FLOAT", platform,
                           notes="No precision — mapped to floating point")

    # --- VARCHAR2 / NVARCHAR2 ---
    m = _RE_VARCHAR2.match(otype)
    if m:
        length = int(m.group(1))
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "STRING", platform)
        return TypeMapping(oracle_type, f"VARCHAR({length})", platform)

    # --- CHAR / NCHAR ---
    m = _RE_CHAR.match(otype)
    if m:
        length = int(m.group(1))
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "STRING", platform, notes="Fixed-width → variable")
        return TypeMapping(oracle_type, f"CHAR({length})", platform)

    # --- CLOB / NCLOB ---
    if otype in ("CLOB", "NCLOB"):
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "STRING", platform, notes="Large text")
        return TypeMapping(oracle_type, "VARCHAR(MAX)", platform, notes="Large text")

    # --- DATE ---
    if otype == "DATE":
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "TIMESTAMP", platform, notes="Oracle DATE includes time")
        return TypeMapping(oracle_type, "DATETIME2", platform, notes="Oracle DATE includes time")

    # --- TIMESTAMP WITH TIME ZONE ---
    if _RE_TIMESTAMP_TZ.match(otype):
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "TIMESTAMP", platform, notes="Converted to UTC")
        return TypeMapping(oracle_type, "DATETIME2(7)", platform, notes="Converted to UTC")

    # --- TIMESTAMP ---
    if _RE_TIMESTAMP.match(otype):
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "TIMESTAMP", platform)
        return TypeMapping(oracle_type, "DATETIME2(7)", platform)

    # --- BLOB ---
    if otype == "BLOB":
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "BINARY", platform)
        return TypeMapping(oracle_type, "VARBINARY(MAX)", platform)

    # --- RAW ---
    m = _RE_RAW.match(otype)
    if m:
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "BINARY", platform)
        return TypeMapping(oracle_type, "VARBINARY(MAX)", platform)

    # --- FLOAT ---
    if _RE_FLOAT.match(otype):
        return TypeMapping(oracle_type, "DOUBLE" if platform == TargetPlatform.LAKEHOUSE else "FLOAT", platform)

    # --- XMLTYPE ---
    if otype == "XMLTYPE":
        return TypeMapping(oracle_type, "STRING" if platform == TargetPlatform.LAKEHOUSE else "VARCHAR(MAX)", platform,
                           notes="Serialized as XML string")

    # --- INTERVAL ---
    if _RE_INTERVAL.match(otype):
        return TypeMapping(oracle_type, "STRING" if platform == TargetPlatform.LAKEHOUSE else "VARCHAR(100)", platform,
                           notes="Serialized as ISO 8601")

    # --- LONG / LONG RAW (legacy) ---
    if otype in ("LONG", "LONG RAW"):
        if platform == TargetPlatform.LAKEHOUSE:
            return TypeMapping(oracle_type, "STRING" if otype == "LONG" else "BINARY", platform,
                               notes="Legacy type")
        return TypeMapping(oracle_type, "VARCHAR(MAX)" if otype == "LONG" else "VARBINARY(MAX)", platform,
                           notes="Legacy type")

    # --- BOOLEAN (Oracle 23c) ---
    if otype == "BOOLEAN":
        return TypeMapping(oracle_type, "BOOLEAN", platform)

    # --- INTEGER alias ---
    if otype in ("INTEGER", "INT", "SMALLINT"):
        return TypeMapping(oracle_type, "INT", platform)

    # --- BINARY_FLOAT / BINARY_DOUBLE ---
    if otype == "BINARY_FLOAT":
        return TypeMapping(oracle_type, "FLOAT" if platform == TargetPlatform.LAKEHOUSE else "REAL", platform)
    if otype == "BINARY_DOUBLE":
        return TypeMapping(oracle_type, "DOUBLE" if platform == TargetPlatform.LAKEHOUSE else "FLOAT", platform)

    # --- Fallback ---
    logger.warning("Unknown Oracle type '%s' — falling back to STRING", oracle_type)
    fallback = "STRING" if platform == TargetPlatform.LAKEHOUSE else "VARCHAR(MAX)"
    return TypeMapping(oracle_type, fallback, platform, notes="Unknown type — fallback", is_fallback=True)


def map_all_columns(
    columns: list[dict[str, Any]],
    platform: TargetPlatform = TargetPlatform.LAKEHOUSE,
) -> list[dict[str, Any]]:
    """Map a list of column dicts (with ``name``, ``data_type``) and return
    enriched dicts with ``fabric_type``, ``notes``, ``is_fallback``.
    """
    result: list[dict[str, Any]] = []
    for col in columns:
        oracle_type = col.get("data_type", "VARCHAR2(255)")
        mapping = map_oracle_type(oracle_type, platform)
        result.append({
            **col,
            "oracle_type": oracle_type,
            "fabric_type": mapping.fabric_type,
            "notes": mapping.notes,
            "is_fallback": mapping.is_fallback,
        })
    return result
