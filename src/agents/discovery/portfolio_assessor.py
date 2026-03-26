"""Portfolio-level migration readiness assessment.

Ported from T2P WorkbookReadiness — provides a pre-migration feasibility
check and effort estimation per OAC asset, enabling wave planning by
shared datasources and effort bands.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.models import AssetType, ComplexityCategory, InventoryItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Readiness level
# ---------------------------------------------------------------------------


class ReadinessLevel(str, Enum):
    GREEN = "green"       # Fully automatable
    YELLOW = "yellow"     # Automatable with manual review
    RED = "red"           # Requires manual intervention


# ---------------------------------------------------------------------------
# Assessment axes
# ---------------------------------------------------------------------------

_EXPRESSION_WEIGHT = 0.20
_FILTER_WEIGHT = 0.15
_CONNECTION_WEIGHT = 0.25
_SECURITY_WEIGHT = 0.20
_SEMANTIC_WEIGHT = 0.20


# ---------------------------------------------------------------------------
# Unsupported function patterns (OAC-specific)
# ---------------------------------------------------------------------------

_UNSUPPORTED_FUNCTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bEVALUATE_PREDICATE\b", re.IGNORECASE),
    re.compile(r"\bVALUEOF\s*\(\s*NQ_SESSION\.", re.IGNORECASE),
    re.compile(r"\bEVALUATE\b", re.IGNORECASE),
    re.compile(r"\bFETCH_FIRST\b", re.IGNORECASE),
    re.compile(r"\bPRESENTATION_VARIABLE\b", re.IGNORECASE),
    re.compile(r"\bREPOSITORY_VARIABLE\b", re.IGNORECASE),
    re.compile(r"\bSESSION_VARIABLE\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Unsupported chart types
# ---------------------------------------------------------------------------

_UNSUPPORTED_CHART_TYPES = frozenset({
    "trellis", "mapview", "sunburst", "chord", "sankey",
    "parallelCoordinates", "tagCloud", "networkDiagram",
})


@dataclass
class ReadinessResult:
    """Migration readiness assessment for a single OAC asset."""

    asset_id: str
    asset_name: str
    readiness: ReadinessLevel = ReadinessLevel.GREEN
    effort_score: float = 1.0
    expression_score: float = 0.0
    filter_score: float = 0.0
    connection_score: float = 0.0
    security_score: float = 0.0
    semantic_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "readiness": self.readiness.value,
            "effort_score": round(self.effort_score, 2),
            "expression_score": round(self.expression_score, 2),
            "filter_score": round(self.filter_score, 2),
            "connection_score": round(self.connection_score, 2),
            "security_score": round(self.security_score, 2),
            "semantic_score": round(self.semantic_score, 2),
            "warnings": self.warnings,
            "blockers": self.blockers,
        }


# ---------------------------------------------------------------------------
# Assessment helpers
# ---------------------------------------------------------------------------


def _assess_expressions(meta: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    """Assess expression complexity — detect unsupported OAC functions."""
    warnings: list[str] = []
    blockers: list[str] = []
    expressions = meta.get("expressions", [])
    calc_count = meta.get("custom_calc_count", len(expressions))

    score = min(calc_count * 0.2, 10.0)

    # Check for unsupported function patterns
    for expr in expressions:
        expr_text = expr if isinstance(expr, str) else str(expr.get("expression", ""))
        for pattern in _UNSUPPORTED_FUNCTION_PATTERNS:
            if pattern.search(expr_text):
                blockers.append(f"Unsupported function: {pattern.pattern} in expression")
                score = max(score, 8.0)

    return score, warnings, blockers


def _assess_filters(meta: dict[str, Any]) -> tuple[float, list[str]]:
    """Assess filter complexity — cascading, cross-filtering, custom."""
    warnings: list[str] = []
    filters = meta.get("filters", [])
    prompts = meta.get("prompts", [])
    total = len(filters) + len(prompts)

    score = min(total * 0.3, 10.0)

    cascade_count = sum(1 for f in filters if isinstance(f, dict) and f.get("cascade"))
    if cascade_count > 0:
        warnings.append(f"{cascade_count} cascading filters — verify slicer chain")
        score += cascade_count * 0.5

    return min(score, 10.0), warnings


def _assess_connections(meta: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    """Assess data connection complexity — multiple sources, unsupported types."""
    warnings: list[str] = []
    blockers: list[str] = []
    connections = meta.get("connections", [])
    conn_count = len(connections) if isinstance(connections, list) else meta.get("connection_count", 1)

    score = 1.0 + conn_count * 0.25

    for conn in (connections if isinstance(connections, list) else []):
        conn_type = conn.get("type", "") if isinstance(conn, dict) else str(conn)
        # Check for unsupported connection types
        if conn_type.lower() in ("essbase", "sap_bw", "hyperion"):
            blockers.append(f"Unsupported connection type: {conn_type}")
            score = max(score, 9.0)

    return min(score, 10.0), warnings, blockers


def _assess_security(meta: dict[str, Any]) -> tuple[float, list[str]]:
    """Assess security migration complexity — RLS, session vars, data grants."""
    warnings: list[str] = []
    roles = meta.get("security_roles", [])
    init_blocks = meta.get("init_blocks", [])

    score = len(roles) * 1.0 + len(init_blocks) * 1.5

    if any(
        isinstance(ib, dict) and "VALUEOF" in str(ib.get("expression", ""))
        for ib in init_blocks
    ):
        warnings.append("Session variable RLS detected — requires manual DAX review")
        score += 3.0

    return min(score, 10.0), warnings


def _assess_semantic(meta: dict[str, Any]) -> tuple[float, list[str]]:
    """Assess semantic model complexity — tables, joins, hierarchies."""
    warnings: list[str] = []
    tables = meta.get("tables", [])
    joins = meta.get("joins", [])
    hierarchies = meta.get("hierarchies", [])

    score = (
        len(tables) * 0.1
        + len(joins) * 0.5
        + len(hierarchies) * 0.3
    )

    if len(joins) > 20:
        warnings.append(f"{len(joins)} relationships — verify DAG is acyclic")

    return min(score, 10.0), warnings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assess_readiness(item: InventoryItem) -> ReadinessResult:
    """Assess migration readiness for a single OAC asset.

    Returns a ReadinessResult with 5-axis scoring and effort estimate.
    """
    meta = item.metadata

    expr_score, expr_warn, expr_block = _assess_expressions(meta)
    filt_score, filt_warn = _assess_filters(meta)
    conn_score, conn_warn, conn_block = _assess_connections(meta)
    sec_score, sec_warn = _assess_security(meta)
    sem_score, sem_warn = _assess_semantic(meta)

    # Check chart types for reports
    chart_types = meta.get("chart_types", [])
    chart_warn: list[str] = []
    for ct in chart_types:
        ct_str = ct if isinstance(ct, str) else str(ct)
        if ct_str.lower() in _UNSUPPORTED_CHART_TYPES:
            chart_warn.append(f"Unsupported chart type: {ct_str}")

    all_warnings = expr_warn + filt_warn + conn_warn + sec_warn + sem_warn + chart_warn
    all_blockers = expr_block + conn_block

    # Weighted effort
    effort = (
        1.0
        + meta.get("custom_calc_count", 0) * 0.2
        + meta.get("connection_count", len(meta.get("connections", []))) * 0.25
        + len(meta.get("filters", [])) * 0.1
        + len(meta.get("security_roles", [])) * 0.3
    )

    # Determine readiness level
    if all_blockers:
        readiness = ReadinessLevel.RED
    elif len(all_warnings) > 5 or effort > 8.0:
        readiness = ReadinessLevel.YELLOW
    else:
        readiness = ReadinessLevel.GREEN

    return ReadinessResult(
        asset_id=item.id,
        asset_name=item.name,
        readiness=readiness,
        effort_score=round(effort, 2),
        expression_score=round(expr_score, 2),
        filter_score=round(filt_score, 2),
        connection_score=round(conn_score, 2),
        security_score=round(sec_score, 2),
        semantic_score=round(sem_score, 2),
        warnings=all_warnings,
        blockers=all_blockers,
    )


def assess_portfolio(
    items: list[InventoryItem],
) -> tuple[list[ReadinessResult], dict[str, Any]]:
    """Assess readiness for a portfolio of OAC assets.

    Returns (results, summary) where summary contains aggregate stats.
    """
    results = [assess_readiness(item) for item in items]

    green = sum(1 for r in results if r.readiness == ReadinessLevel.GREEN)
    yellow = sum(1 for r in results if r.readiness == ReadinessLevel.YELLOW)
    red = sum(1 for r in results if r.readiness == ReadinessLevel.RED)
    total_effort = sum(r.effort_score for r in results)

    summary = {
        "total_assets": len(results),
        "green": green,
        "yellow": yellow,
        "red": red,
        "total_effort_score": round(total_effort, 2),
        "avg_effort_score": round(total_effort / max(len(results), 1), 2),
    }

    logger.info(
        "Portfolio assessment: %d GREEN, %d YELLOW, %d RED (avg effort: %.1f)",
        green, yellow, red, summary["avg_effort_score"],
    )

    return results, summary


def plan_waves_by_effort(
    results: list[ReadinessResult],
    max_effort_per_wave: float = 50.0,
) -> list[list[str]]:
    """Group assets into migration waves based on effort bands.

    Returns a list of waves, each containing asset IDs.
    """
    # Sort by effort (ascending — easy items first)
    sorted_results = sorted(results, key=lambda r: r.effort_score)

    waves: list[list[str]] = [[]]
    current_effort = 0.0

    for r in sorted_results:
        if current_effort + r.effort_score > max_effort_per_wave and waves[-1]:
            waves.append([])
            current_effort = 0.0
        waves[-1].append(r.asset_id)
        current_effort += r.effort_score

    return waves
