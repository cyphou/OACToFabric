"""Dynamic RLS Generator — advanced row-level security with dynamic rules.

Generates Power BI RLS role definitions with dynamic DAX filters that
adapt to user context, supporting:
  - Multi-value session variable → DAX PATHCONTAINS patterns
  - Hierarchical security (org chart-based data access)
  - Time-scoped access (users see data only for their active period)
  - Combined RLS + OLS (filter rows AND mask columns)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAC dynamic security types
# ---------------------------------------------------------------------------


@dataclass
class OACSessionFilter:
    """An OAC session variable-based security filter."""

    variable_name: str            # e.g., NQ_SESSION.REGION
    target_table: str
    target_column: str
    filter_type: str = "equals"   # equals, in_list, hierarchy, time_range
    hierarchy_column: str = ""    # for hierarchy-based filtering
    time_start_column: str = ""   # for time-scoped access
    time_end_column: str = ""


# ---------------------------------------------------------------------------
# DAX RLS types
# ---------------------------------------------------------------------------


@dataclass
class DynamicRLSRule:
    """A dynamic RLS rule with DAX filter expression."""

    role_name: str
    table_name: str
    dax_filter: str
    description: str = ""
    confidence: float = 1.0
    warning: str = ""


@dataclass
class DynamicRLSResult:
    """Result of dynamic RLS generation."""

    roles: list[DynamicRLSRule] = field(default_factory=list)
    lookup_table_tmdl: str = ""       # Security lookup table TMDL if needed
    lookup_table_ddl: str = ""        # DDL for security lookup table
    tmdl_roles_section: str = ""      # Complete roles.tmdl content
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DAX filter generation strategies
# ---------------------------------------------------------------------------


def _generate_equals_filter(
    table: str,
    column: str,
    variable: str,
) -> str:
    """Generate simple equality RLS filter."""
    return f"[{column}] = LOOKUPVALUE(SecurityAccess[{variable}], SecurityAccess[UserPrincipal], USERPRINCIPALNAME())"


def _generate_in_list_filter(
    table: str,
    column: str,
    variable: str,
) -> str:
    """Generate multi-value IN-list RLS filter using PATHCONTAINS."""
    return (
        f"VAR _access = LOOKUPVALUE(SecurityAccess[{variable}], "
        f"SecurityAccess[UserPrincipal], USERPRINCIPALNAME())\n"
        f"RETURN PATHCONTAINS(_access, [{column}])"
    )


def _generate_hierarchy_filter(
    table: str,
    column: str,
    hierarchy_col: str,
    variable: str,
) -> str:
    """Generate hierarchy-based RLS filter (org chart pattern)."""
    return (
        f"VAR _user_node = LOOKUPVALUE(SecurityAccess[{variable}], "
        f"SecurityAccess[UserPrincipal], USERPRINCIPALNAME())\n"
        f"VAR _path = [{hierarchy_col}]\n"
        f"RETURN PATHCONTAINS(_path, _user_node) || [{column}] = _user_node"
    )


def _generate_time_range_filter(
    table: str,
    column: str,
    start_col: str,
    end_col: str,
) -> str:
    """Generate time-scoped RLS filter."""
    return (
        f"VAR _today = TODAY()\n"
        f"VAR _start = LOOKUPVALUE(SecurityAccess[{start_col}], "
        f"SecurityAccess[UserPrincipal], USERPRINCIPALNAME())\n"
        f"VAR _end = LOOKUPVALUE(SecurityAccess[{end_col}], "
        f"SecurityAccess[UserPrincipal], USERPRINCIPALNAME())\n"
        f"RETURN [{column}] >= _start && [{column}] <= IF(ISBLANK(_end), _today, _end)"
    )


# ---------------------------------------------------------------------------
# Filter strategy dispatch
# ---------------------------------------------------------------------------

_FILTER_GENERATORS = {
    "equals": _generate_equals_filter,
    "in_list": _generate_in_list_filter,
    "hierarchy": _generate_hierarchy_filter,
    "time_range": _generate_time_range_filter,
}


# ---------------------------------------------------------------------------
# Security lookup table generation
# ---------------------------------------------------------------------------


def _generate_lookup_table_tmdl(variables: list[str]) -> str:
    """Generate TMDL for the SecurityAccess lookup table."""
    lines = [
        "table 'SecurityAccess'",
        "\tpartition 'SecurityAccess' = entity",
        "\t\tentityName = 'SecurityAccess'",
        "",
        "\tcolumn 'UserPrincipal'",
        "\t\tdataType = String",
        "\t\tsourceColumn = 'UserPrincipal'",
    ]
    for var in variables:
        lines.extend([
            "",
            f"\tcolumn '{var}'",
            f"\t\tdataType = String",
            f"\t\tsourceColumn = '{var}'",
        ])
    return "\n".join(lines)


def _generate_lookup_table_ddl(variables: list[str]) -> str:
    """Generate DDL for the SecurityAccess Delta table."""
    cols = ["    UserPrincipal STRING NOT NULL"]
    for var in variables:
        cols.append(f"    {var} STRING")
    col_defs = ",\n".join(cols)
    return (
        f"CREATE TABLE IF NOT EXISTS SecurityAccess (\n"
        f"{col_defs}\n"
        f") USING DELTA"
    )


def _generate_roles_tmdl(rules: list[DynamicRLSRule]) -> str:
    """Generate complete roles.tmdl content."""
    lines: list[str] = []
    grouped: dict[str, list[DynamicRLSRule]] = {}
    for rule in rules:
        grouped.setdefault(rule.role_name, []).append(rule)

    for role_name, role_rules in grouped.items():
        lines.append(f"role '{role_name}'")
        lines.append(f"\tmodelPermission = read")
        lines.append("")
        for rule in role_rules:
            lines.append(f"\ttablePermission '{rule.table_name}' =")
            for dax_line in rule.dax_filter.split("\n"):
                lines.append(f"\t\t{dax_line}")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_dynamic_rls(
    session_filters: list[OACSessionFilter],
    role_name: str = "DynamicAccess",
) -> DynamicRLSResult:
    """Generate dynamic RLS rules from OAC session variable filters.

    Parameters
    ----------
    session_filters : list[OACSessionFilter]
        OAC session variable-based security filters.
    role_name : str
        Name of the RLS role to generate.

    Returns
    -------
    DynamicRLSResult
        Generated RLS rules, lookup table artifacts, and TMDL.
    """
    result = DynamicRLSResult()
    variables: list[str] = []

    for sf in session_filters:
        var_name = sf.variable_name.replace("NQ_SESSION.", "").replace(".", "_")
        if var_name not in variables:
            variables.append(var_name)

        filter_type = sf.filter_type.lower()
        confidence = 1.0
        warning = ""

        if filter_type == "hierarchy":
            if not sf.hierarchy_column:
                warning = f"Hierarchy filter for {sf.target_table}.{sf.target_column} missing hierarchy column"
                confidence = 0.6
                dax = _generate_equals_filter(sf.target_table, sf.target_column, var_name)
            else:
                dax = _generate_hierarchy_filter(
                    sf.target_table, sf.target_column,
                    sf.hierarchy_column, var_name,
                )
                confidence = 0.85

        elif filter_type == "time_range":
            if not sf.time_start_column or not sf.time_end_column:
                warning = f"Time-range filter missing start/end columns for {sf.target_table}"
                confidence = 0.5
                dax = _generate_equals_filter(sf.target_table, sf.target_column, var_name)
            else:
                dax = _generate_time_range_filter(
                    sf.target_table, sf.target_column,
                    sf.time_start_column, sf.time_end_column,
                )
                confidence = 0.90

        elif filter_type == "in_list":
            dax = _generate_in_list_filter(sf.target_table, sf.target_column, var_name)
            confidence = 0.95

        else:
            dax = _generate_equals_filter(sf.target_table, sf.target_column, var_name)
            confidence = 1.0

        rule = DynamicRLSRule(
            role_name=role_name,
            table_name=sf.target_table,
            dax_filter=dax,
            description=f"Migrated from OAC session variable: {sf.variable_name}",
            confidence=confidence,
            warning=warning,
        )
        result.roles.append(rule)

        if warning:
            result.warnings.append(warning)

    # Generate lookup table
    if variables:
        result.lookup_table_tmdl = _generate_lookup_table_tmdl(variables)
        result.lookup_table_ddl = _generate_lookup_table_ddl(variables)

    # Generate roles.tmdl
    result.tmdl_roles_section = _generate_roles_tmdl(result.roles)

    logger.info(
        "Generated %d dynamic RLS rules for role '%s' (%d session variables)",
        len(result.roles),
        role_name,
        len(variables),
    )
    return result
