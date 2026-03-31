"""Materialized View Generator — Oracle MVs → Fabric Warehouse materialized views.

Parses Oracle ``CREATE MATERIALIZED VIEW`` DDL and generates equivalent
Fabric Warehouse ``CREATE MATERIALIZED VIEW AS SELECT`` statements.
Also detects MV-eligible views in the RPD physical layer.

Refresh mode mapping:
  - Oracle FAST   → incremental (Fabric auto-managed)
  - Oracle COMPLETE → full (Fabric auto-managed)
  - Oracle FORCE   → auto (Fabric default)
  - Oracle ON DEMAND / ON COMMIT → schedule metadata preserved as comments
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .type_mapper import TargetPlatform, map_oracle_type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class RefreshMode:
    FAST = "FAST"
    COMPLETE = "COMPLETE"
    FORCE = "FORCE"
    ON_DEMAND = "ON DEMAND"
    ON_COMMIT = "ON COMMIT"


@dataclass
class MaterializedViewDef:
    """Parsed Oracle materialized view definition."""

    name: str
    schema: str | None = None
    query: str = ""
    refresh_mode: str = RefreshMode.FORCE
    refresh_trigger: str = RefreshMode.ON_DEMAND
    build_type: str = "IMMEDIATE"
    partition_by: list[str] = field(default_factory=list)
    depends_on_tables: list[str] = field(default_factory=list)
    estimated_rows: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class FabricMVResult:
    """Result of generating a Fabric Warehouse materialized view."""

    ddl: str
    source_name: str
    target_name: str
    refresh_comment: str = ""
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Oracle MV DDL parser
# ---------------------------------------------------------------------------

_RE_CREATE_MV = re.compile(
    r"CREATE\s+MATERIALIZED\s+VIEW\s+"
    r"(?:(\w+)\.)?(\w+)"
    r"(.*?)\s+AS\s+(SELECT\b.+)",
    re.IGNORECASE | re.DOTALL,
)

_RE_REFRESH = re.compile(
    r"REFRESH\s+(FAST|COMPLETE|FORCE)",
    re.IGNORECASE,
)

_RE_TRIGGER = re.compile(
    r"ON\s+(DEMAND|COMMIT)",
    re.IGNORECASE,
)

_RE_BUILD = re.compile(
    r"BUILD\s+(IMMEDIATE|DEFERRED)",
    re.IGNORECASE,
)

_RE_TABLE_REF = re.compile(
    r"\bFROM\s+(?:(\w+)\.)?(\w+)\b",
    re.IGNORECASE,
)


def parse_oracle_mv(ddl: str) -> MaterializedViewDef:
    """Parse an Oracle CREATE MATERIALIZED VIEW statement.

    Parameters
    ----------
    ddl : str
        Oracle DDL text.

    Returns
    -------
    MaterializedViewDef
        Parsed MV definition with query, refresh mode, and dependencies.
    """
    m = _RE_CREATE_MV.search(ddl)
    if not m:
        return MaterializedViewDef(
            name="UNKNOWN",
            query=ddl,
            warnings=["Could not parse MV DDL — passing through as-is"],
        )

    schema = m.group(1)
    name = m.group(2)
    options_block = m.group(3)
    query = m.group(4).rstrip(";").strip()

    refresh_mode = RefreshMode.FORCE
    rm = _RE_REFRESH.search(options_block)
    if rm:
        refresh_mode = rm.group(1).upper()

    refresh_trigger = RefreshMode.ON_DEMAND
    rt = _RE_TRIGGER.search(options_block)
    if rt:
        refresh_trigger = f"ON {rt.group(1).upper()}"

    build_type = "IMMEDIATE"
    bt = _RE_BUILD.search(options_block)
    if bt:
        build_type = bt.group(1).upper()

    tables = [t.group(2) for t in _RE_TABLE_REF.finditer(query)]

    return MaterializedViewDef(
        name=name,
        schema=schema,
        query=query,
        refresh_mode=refresh_mode,
        refresh_trigger=refresh_trigger,
        build_type=build_type,
        depends_on_tables=tables,
    )


# ---------------------------------------------------------------------------
# Fabric Warehouse MV generator
# ---------------------------------------------------------------------------

_REFRESH_COMMENT_MAP = {
    RefreshMode.FAST: "-- Oracle REFRESH FAST → Fabric auto-incremental refresh",
    RefreshMode.COMPLETE: "-- Oracle REFRESH COMPLETE → Fabric full refresh",
    RefreshMode.FORCE: "-- Oracle REFRESH FORCE → Fabric auto-managed refresh",
}


def _safe_name(name: str) -> str:
    """Sanitise a name for T-SQL."""
    clean = re.sub(r"[^\w]", "_", name)
    return f"[{clean}]"


def generate_fabric_mv(
    mv_def: MaterializedViewDef,
    target_schema: str = "dbo",
) -> FabricMVResult:
    """Generate a Fabric Warehouse CREATE MATERIALIZED VIEW statement.

    Parameters
    ----------
    mv_def : MaterializedViewDef
        Parsed Oracle MV definition.
    target_schema : str
        Target schema in Fabric Warehouse.

    Returns
    -------
    FabricMVResult
        Generated DDL and metadata.
    """
    target_name = f"{target_schema}.{_safe_name(mv_def.name)}"
    refresh_comment = _REFRESH_COMMENT_MAP.get(
        mv_def.refresh_mode,
        f"-- Oracle refresh mode: {mv_def.refresh_mode}",
    )

    trigger_comment = ""
    if mv_def.refresh_trigger == RefreshMode.ON_COMMIT:
        trigger_comment = "\n-- NOTE: Oracle ON COMMIT refresh has no Fabric equivalent — use scheduled refresh"

    warnings: list[str] = list(mv_def.warnings)
    if mv_def.build_type == "DEFERRED":
        warnings.append("Oracle BUILD DEFERRED not supported — Fabric MVs build immediately")

    ddl = (
        f"{refresh_comment}{trigger_comment}\n"
        f"CREATE MATERIALIZED VIEW {target_name}\n"
        f"AS\n"
        f"{mv_def.query}\n;"
    )

    return FabricMVResult(
        ddl=ddl,
        source_name=mv_def.name,
        target_name=target_name,
        refresh_comment=refresh_comment,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Detect MV-eligible views from RPD physical layer
# ---------------------------------------------------------------------------


def detect_mv_candidates(
    tables: list[dict[str, Any]],
    threshold_rows: int = 100_000,
) -> list[str]:
    """Identify physical tables/views that could benefit from materialisation.

    Tables with high row counts and aggregation-heavy queries are good
    candidates for Fabric Warehouse materialized views.

    Parameters
    ----------
    tables : list[dict]
        Physical table metadata, each with ``name``, ``estimated_rows``,
        ``is_view`` (bool), and optional ``sql_query``.
    threshold_rows : int
        Row count threshold for MV recommendation.

    Returns
    -------
    list[str]
        Table names recommended for materialisation.
    """
    candidates: list[str] = []
    agg_keywords = re.compile(
        r"\b(SUM|COUNT|AVG|MIN|MAX|GROUP\s+BY)\b", re.IGNORECASE
    )

    for t in tables:
        is_view = t.get("is_view", False)
        rows = t.get("estimated_rows", 0)
        sql = t.get("sql_query", "")

        if is_view and rows >= threshold_rows:
            candidates.append(t["name"])
        elif sql and agg_keywords.search(sql) and rows >= threshold_rows:
            candidates.append(t["name"])

    logger.info("Detected %d MV candidates (threshold=%d rows)", len(candidates), threshold_rows)
    return candidates


# ---------------------------------------------------------------------------
# Batch generation
# ---------------------------------------------------------------------------


def generate_all_mvs(
    mv_ddls: list[str],
    target_schema: str = "dbo",
) -> list[FabricMVResult]:
    """Parse and generate Fabric MVs for a list of Oracle MV DDL strings."""
    results: list[FabricMVResult] = []
    for ddl in mv_ddls:
        parsed = parse_oracle_mv(ddl)
        result = generate_fabric_mv(parsed, target_schema)
        results.append(result)
    logger.info("Generated %d Fabric materialized views", len(results))
    return results
