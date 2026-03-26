"""TMDL structural validation and pre-migration readiness assessment.

Provides:
1. TMDL structural validation — checks required files, dirs, keys
2. Pre-migration readiness assessment — 8-point check ported from T2P
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TMDL structural validation
# ---------------------------------------------------------------------------

_REQUIRED_FILES = frozenset({
    "model.tmdl",
    ".platform",
})

_REQUIRED_DIRS = frozenset({
    "definition/tables",
})

_REQUIRED_PLATFORM_KEYS = frozenset({
    "$schema",
    "metadata",
    "config",
})


@dataclass
class TMDLValidationResult:
    """Result of TMDL structural validation."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_count: int = 0
    table_count: int = 0


def validate_tmdl_structure(files: dict[str, str]) -> TMDLValidationResult:
    """Validate that a TMDL file set has all required files and structure.

    Parameters
    ----------
    files
        Dict of relative_path → content (from TMDLGenerationResult.files).

    Returns
    -------
    TMDLValidationResult
    """
    result = TMDLValidationResult(file_count=len(files))

    # Check required files
    for req_file in _REQUIRED_FILES:
        if req_file not in files:
            result.errors.append(f"Missing required file: {req_file}")
            result.valid = False

    # Check required directories (at least one file in each)
    for req_dir in _REQUIRED_DIRS:
        has_files = any(path.startswith(req_dir + "/") for path in files)
        if not has_files:
            result.errors.append(f"Missing required directory: {req_dir}")
            result.valid = False

    # Validate .platform JSON structure
    if ".platform" in files:
        try:
            platform = json.loads(files[".platform"])
            for key in _REQUIRED_PLATFORM_KEYS:
                if key not in platform:
                    result.errors.append(f".platform missing required key: {key}")
                    result.valid = False
        except json.JSONDecodeError:
            result.errors.append(".platform is not valid JSON")
            result.valid = False

    # Validate model.tmdl structure
    if "model.tmdl" in files:
        model_content = files["model.tmdl"]
        if not re.search(r"^model\s+", model_content, re.MULTILINE):
            result.errors.append("model.tmdl missing 'model' declaration")
            result.valid = False
        if "culture:" not in model_content:
            result.warnings.append("model.tmdl missing 'culture:' property")

    # Count and validate tables
    table_files = [p for p in files if p.startswith("definition/tables/")]
    result.table_count = len(table_files)

    for path in table_files:
        content = files[path]
        if not re.search(r"^table\s+", content, re.MULTILINE):
            result.errors.append(f"{path} missing 'table' declaration")
            result.valid = False

        # Check for lineageTag
        if "lineageTag:" not in content:
            result.warnings.append(f"{path} missing lineageTag")

        # Check for at least one column or measure
        has_col = bool(re.search(r"^\s+column\s+", content, re.MULTILINE))
        has_measure = bool(re.search(r"^\s+measure\s+", content, re.MULTILINE))
        if not has_col and not has_measure:
            result.warnings.append(f"{path} has no columns or measures")

    # Validate relationships
    if "definition/relationships.tmdl" in files:
        rel_content = files["definition/relationships.tmdl"]
        rel_count = len(re.findall(r"^relationship\s+", rel_content, re.MULTILINE))
        if rel_count == 0:
            result.warnings.append("relationships.tmdl is empty")

    # Validate database.tmdl if present
    if "definition/database.tmdl" in files:
        db_content = files["definition/database.tmdl"]
        if "compatibilityLevel:" not in db_content:
            result.warnings.append("database.tmdl missing compatibilityLevel")

    logger.info(
        "TMDL validation: %s (%d errors, %d warnings, %d tables)",
        "PASS" if result.valid else "FAIL",
        len(result.errors), len(result.warnings), result.table_count,
    )

    return result


# ---------------------------------------------------------------------------
# Pre-migration readiness assessment (8-point check)
# ---------------------------------------------------------------------------


@dataclass
class ReadinessCheck:
    """A single readiness check result."""

    name: str
    status: str     # pass | warn | fail
    details: str = ""
    count: int = 0


@dataclass
class ReadinessAssessment:
    """Complete 8-point readiness assessment."""

    checks: list[ReadinessCheck] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "pass")

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.status == "warn")

    @property
    def failures(self) -> int:
        return sum(1 for c in self.checks if c.status == "fail")

    @property
    def is_ready(self) -> bool:
        return self.failures == 0


# Supported connection types
_SUPPORTED_CONNECTIONS = frozenset({
    "oracle", "postgresql", "sqlserver", "mysql", "snowflake",
    "bigquery", "databricks", "csv", "excel", "web", "odata",
    "azure_sql", "fabric_lakehouse", "synapse",
})

# Supported chart types (what we can map)
_SUPPORTED_CHARTS = frozenset({
    "table", "pivotTable", "verticalBar", "horizontalBar",
    "stackedBar", "stackedColumn", "line", "area", "combo",
    "pie", "donut", "scatter", "bubble", "filledMap", "bubbleMap",
    "gauge", "kpi", "funnel", "treemap", "heatmap", "waterfall",
    "narrative", "image", "trellis",
})

# Unsupported OAC functions (known blockers)
_UNSUPPORTED_FUNCTIONS = [
    re.compile(r"\bEVALUATE_PREDICATE\b", re.IGNORECASE),
    re.compile(r"\bCONNECT\s+BY\b", re.IGNORECASE),
    re.compile(r"\bMODEL\s+RETURN\b", re.IGNORECASE),
]


def assess_migration_readiness(
    inventory: dict[str, Any],
) -> ReadinessAssessment:
    """Run an 8-point pre-migration readiness check.

    Parameters
    ----------
    inventory
        Dict with keys: connections, chart_types, expressions, parameters,
        data_blending, dashboard_features, security_roles, filters.

    Returns
    -------
    ReadinessAssessment
    """
    checks: list[ReadinessCheck] = []

    # 1. Connectors
    connections = inventory.get("connections", [])
    unsupported_conns = [
        c for c in connections
        if (c if isinstance(c, str) else c.get("type", "")).lower() not in _SUPPORTED_CONNECTIONS
    ]
    checks.append(ReadinessCheck(
        name="Connectors",
        status="fail" if unsupported_conns else "pass",
        details=f"Unsupported: {unsupported_conns}" if unsupported_conns else "All connectors supported",
        count=len(connections),
    ))

    # 2. Chart types
    chart_types = inventory.get("chart_types", [])
    unsupported_charts = [
        c for c in chart_types
        if (c if isinstance(c, str) else str(c)).lower() not in _SUPPORTED_CHARTS
    ]
    checks.append(ReadinessCheck(
        name="Chart Types",
        status="warn" if unsupported_charts else "pass",
        details=f"Unsupported: {unsupported_charts}" if unsupported_charts else "All chart types supported",
        count=len(chart_types),
    ))

    # 3. Functions / expressions
    expressions = inventory.get("expressions", [])
    blocked_funcs: list[str] = []
    for expr in expressions:
        expr_text = expr if isinstance(expr, str) else str(expr.get("expression", ""))
        for pat in _UNSUPPORTED_FUNCTIONS:
            if pat.search(expr_text):
                blocked_funcs.append(pat.pattern)
    checks.append(ReadinessCheck(
        name="Functions",
        status="fail" if blocked_funcs else "pass",
        details=f"Blocked: {blocked_funcs}" if blocked_funcs else "All functions translatable",
        count=len(expressions),
    ))

    # 4. Parameters / prompts
    parameters = inventory.get("parameters", [])
    checks.append(ReadinessCheck(
        name="Parameters",
        status="warn" if len(parameters) > 10 else "pass",
        details=f"{len(parameters)} parameters (>10 may need manual review)",
        count=len(parameters),
    ))

    # 5. Data blending (cross-source joins)
    blending = inventory.get("data_blending", [])
    checks.append(ReadinessCheck(
        name="Data Blending",
        status="warn" if blending else "pass",
        details=f"{len(blending)} cross-source joins detected" if blending else "No data blending",
        count=len(blending),
    ))

    # 6. Dashboard features
    features = inventory.get("dashboard_features", {})
    cascade_filters = features.get("cascade_filters", 0)
    actions = features.get("actions", 0)
    viz_tooltip = features.get("viz_in_tooltip", 0)
    complex_features = cascade_filters + actions + viz_tooltip
    checks.append(ReadinessCheck(
        name="Dashboard Features",
        status="warn" if complex_features > 5 else "pass",
        details=f"Cascade filters: {cascade_filters}, Actions: {actions}, Viz-tooltip: {viz_tooltip}",
        count=complex_features,
    ))

    # 7. Security
    security_roles = inventory.get("security_roles", [])
    session_vars = inventory.get("session_variables", [])
    checks.append(ReadinessCheck(
        name="Security",
        status="warn" if session_vars else "pass",
        details=f"{len(security_roles)} roles, {len(session_vars)} session variables",
        count=len(security_roles),
    ))

    # 8. Filters
    filters = inventory.get("filters", [])
    checks.append(ReadinessCheck(
        name="Filters",
        status="warn" if len(filters) > 20 else "pass",
        details=f"{len(filters)} filters (>20 may need manual review)",
        count=len(filters),
    ))

    assessment = ReadinessAssessment(checks=checks)

    logger.info(
        "Readiness assessment: %d pass, %d warn, %d fail — %s",
        assessment.passed, assessment.warnings, assessment.failures,
        "READY" if assessment.is_ready else "NOT READY",
    )

    return assessment
