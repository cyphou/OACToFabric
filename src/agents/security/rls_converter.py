"""RLS converter — OAC row-level security → Power BI RLS TMDL definitions.

Generates TMDL `roles.tmdl` content from mapped RLS role definitions.

Handles:
  - Direct user-based filters  (NQ_SESSION.USER → USERPRINCIPALNAME())
  - Session-variable lookup patterns  (NQ_SESSION.<VAR> → lookup table DAX)
  - Security lookup table DDL generation for init-block variables
  - TMDL role / tablePermission rendering
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .role_mapper import RLSRoleDefinition, RLSTablePermission

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security lookup table
# ---------------------------------------------------------------------------


@dataclass
class SecurityLookupTable:
    """Definition of a security lookup table for session-variable RLS."""

    table_name: str = "Security_UserAccess"
    columns: list[LookupColumn] = field(default_factory=list)
    source_init_block: str = ""     # Original OAC init block SQL
    warnings: list[str] = field(default_factory=list)


@dataclass
class LookupColumn:
    """A column in the security lookup table."""

    name: str
    data_type: str = "VARCHAR(256)"
    description: str = ""


# ---------------------------------------------------------------------------
# Init-block analysis
# ---------------------------------------------------------------------------


def analyse_init_blocks(
    init_blocks: list[dict[str, Any]],
) -> list[SecurityLookupTable]:
    """Analyse OAC init blocks and produce security lookup table definitions.

    Each init block typically populates session variables via SQL.
    We create lookup table definitions that store the same data accessible
    via ``USERPRINCIPALNAME()`` in DAX.

    Parameters
    ----------
    init_blocks : list[dict]
        Init block metadata from the inventory.  Expected keys::

            - name: str
            - sql: str (the Oracle SQL populating variables)
            - variables: list[str] (session variables populated)
            - table: str (optional: source table)
            - column: str (optional: source column)
    """
    tables: list[SecurityLookupTable] = []
    variables_seen: set[str] = set()

    for ib in init_blocks:
        sql = ib.get("sql", "")
        variables = ib.get("variables", [])
        name = ib.get("name", "")

        columns: list[LookupColumn] = [
            LookupColumn(
                name="UserEmail",
                data_type="VARCHAR(256)",
                description="Maps to USERPRINCIPALNAME()",
            ),
        ]

        warnings: list[str] = []

        for var in variables:
            if var.upper() in variables_seen:
                continue
            variables_seen.add(var.upper())
            columns.append(
                LookupColumn(
                    name=var,
                    data_type="VARCHAR(256)",
                    description=f"Populated by init block '{name}'",
                )
            )

        # Detect complex SQL patterns
        if _is_complex_sql(sql):
            warnings.append(
                f"Init block '{name}' contains complex SQL (dynamic/PL/SQL) — "
                "review the generated lookup table manually"
            )

        tables.append(
            SecurityLookupTable(
                table_name="Security_UserAccess",
                columns=columns,
                source_init_block=sql,
                warnings=warnings,
            )
        )

    # Merge into a single table (all variables in one lookup table)
    if tables:
        merged = _merge_lookup_tables(tables)
        return [merged]
    return []


def _is_complex_sql(sql: str) -> bool:
    """Detect whether SQL is complex (dynamic SQL, PL/SQL blocks)."""
    if not sql:
        return False
    lower = sql.lower()
    indicators = [
        "execute immediate",
        "dbms_sql",
        "begin",
        "declare",
        "cursor",
        "loop",
        "dynamic",
        "sys_context",
    ]
    return any(ind in lower for ind in indicators)


def _merge_lookup_tables(tables: list[SecurityLookupTable]) -> SecurityLookupTable:
    """Merge multiple lookup table definitions into one."""
    all_cols: dict[str, LookupColumn] = {}
    warnings: list[str] = []
    source_sqls: list[str] = []

    for t in tables:
        for col in t.columns:
            if col.name not in all_cols:
                all_cols[col.name] = col
        warnings.extend(t.warnings)
        if t.source_init_block:
            source_sqls.append(t.source_init_block)

    return SecurityLookupTable(
        table_name="Security_UserAccess",
        columns=list(all_cols.values()),
        source_init_block="\n---\n".join(source_sqls),
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Lookup table DDL
# ---------------------------------------------------------------------------


def generate_lookup_table_ddl(table: SecurityLookupTable) -> str:
    """Generate SQL DDL for the security lookup table (Fabric Lakehouse)."""
    lines = [
        f"-- Security lookup table for RLS",
        f"-- Source init block(s): see migration report",
        f"CREATE TABLE {table.table_name} (",
    ]
    col_defs: list[str] = []
    for col in table.columns:
        comment = f"  -- {col.description}" if col.description else ""
        col_defs.append(f"    {col.name:<24s} {col.data_type}{comment}")
    lines.append(",\n".join(col_defs))
    lines.append(");")
    return "\n".join(lines)


def generate_lookup_table_tmdl(table: SecurityLookupTable) -> str:
    """Generate TMDL table definition for the security lookup table."""
    lines = [
        f"/// Security lookup table — maps USERPRINCIPALNAME() to filter values",
        f"table '{table.table_name}'",
        f"\tlineageTag: security-lookup-table",
        "",
    ]
    for col in table.columns:
        lines.extend([
            f"\tcolumn '{col.name}'",
            f"\t\tdataType: string",
            f"\t\tlineageTag: {_tmdl_tag(col.name)}",
            f"\t\tsummarizeBy: none",
            "",
        ])

    # Partition placeholder
    lines.extend([
        f"\tpartition '{table.table_name}' = m",
        f'\t\tmode: import',
        f'\t\tsource =',
        f'\t\t\tlet',
        f'\t\t\t\tSource = Lakehouse.Contents(null){{[Name="{table.table_name}"]}}[Data]',
        f"\t\t\tin",
        f"\t\t\t\tSource",
        "",
    ])

    return "\n".join(lines)


def _tmdl_tag(name: str) -> str:
    """Generate a deterministic lineage tag from a name."""
    import hashlib
    return hashlib.md5(name.encode()).hexdigest()[:8] + "-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# TMDL RLS role rendering
# ---------------------------------------------------------------------------


def render_roles_tmdl(
    rls_roles: list[RLSRoleDefinition],
    lookup_tables: list[SecurityLookupTable] | None = None,
) -> str:
    """Render TMDL content for roles.tmdl.

    Includes RLS role definitions with table permissions.
    Optionally prepends the security lookup table definition.
    """
    lines: list[str] = [
        "// ==========================================================",
        "// RLS Roles — generated by Agent 06 (Security Migration Agent)",
        "// ==========================================================",
        "",
    ]

    # Security lookup table(s) as TMDL table definitions
    if lookup_tables:
        for lt in lookup_tables:
            lines.append(generate_lookup_table_tmdl(lt))
            lines.append("")

    # Role definitions
    for role in rls_roles:
        lines.extend(_render_single_role(role))
        lines.append("")

    return "\n".join(lines)


def _render_single_role(role: RLSRoleDefinition) -> list[str]:
    """Render a single RLS role as TMDL."""
    lines = [
        f"/// {role.description}" if role.description else f"/// RLS role: {role.role_name}",
        f"role '{role.role_name}'",
        f"\tmodelPermission: read",
        "",
    ]

    for tp in role.table_permissions:
        lines.append(f"\ttablePermission '{tp.table_name}'")
        # Indent the DAX filter expression
        dax_lines = tp.filter_expression.strip().split("\n")
        if len(dax_lines) == 1:
            lines.append(f"\t\tfilterExpression = {dax_lines[0]}")
        else:
            lines.append(f"\t\tfilterExpression =")
            for dl in dax_lines:
                lines.append(f"\t\t\t{dl}")
        lines.append("")

    return lines


# ---------------------------------------------------------------------------
# RLS validation test plan
# ---------------------------------------------------------------------------


@dataclass
class RLSTestCase:
    """A single RLS validation test case."""

    role_name: str
    test_user: str
    table_name: str
    expected_filter: str
    description: str = ""


def generate_rls_test_plan(
    rls_roles: list[RLSRoleDefinition],
) -> list[RLSTestCase]:
    """Generate a test plan for validating RLS roles.

    Creates test cases for each role × table combination.
    """
    test_cases: list[RLSTestCase] = []

    for role in rls_roles:
        for tp in role.table_permissions:
            test_cases.append(
                RLSTestCase(
                    role_name=role.role_name,
                    test_user=f"test_user_{role.role_name.lower().replace(' ', '_')}",
                    table_name=tp.table_name,
                    expected_filter=tp.filter_expression[:100],
                    description=(
                        f"Validate {role.role_name} on {tp.table_name}: "
                        f"user should see only rows matching filter"
                    ),
                )
            )

    # Add admin / no-RLS test
    test_cases.append(
        RLSTestCase(
            role_name="Admin (no RLS)",
            test_user="test_admin",
            table_name="*",
            expected_filter="All rows visible",
            description="Admin user should see all data across all tables",
        )
    )

    return test_cases


def render_test_plan_markdown(test_cases: list[RLSTestCase]) -> str:
    """Render the RLS test plan as Markdown."""
    lines = [
        "# RLS Validation Test Plan",
        "",
        "| # | Role | Test User | Table | Expected | Description |",
        "|---|---|---|---|---|---|",
    ]
    for i, tc in enumerate(test_cases, 1):
        expected = tc.expected_filter.replace("|", "\\|")[:60]
        lines.append(
            f"| {i} | {tc.role_name} | {tc.test_user} | {tc.table_name} | "
            f"{expected} | {tc.description[:80]} |"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hierarchy-based dynamic RLS (parent-child)
# ---------------------------------------------------------------------------


@dataclass
class HierarchyRLSSpec:
    """Specification for hierarchy-based row-level security."""

    role_name: str
    table_name: str
    hierarchy_column: str
    parent_column: str
    key_column: str
    dax_filter: str
    lookup_table: str = "SecurityHierarchy"
    warnings: list[str] = field(default_factory=list)


def generate_hierarchy_rls_dax(
    table_name: str,
    key_column: str,
    hierarchy_column: str,
    parent_column: str,
    lookup_table: str = "SecurityHierarchy",
) -> str:
    """Generate DAX filter for hierarchy-based dynamic RLS.

    Uses PATH() / PATHCONTAINS() pattern for parent-child security:
    - A security lookup table maps user → allowed hierarchy node
    - PATH() builds the full ancestry path for each row
    - PATHCONTAINS() checks if the user's node appears in the path

    Args:
        table_name: Fact/dimension table to filter
        key_column: Primary key column in the hierarchy table
        hierarchy_column: Column containing the PATH expression
        parent_column: Parent key column
        lookup_table: Security lookup table for user→node mapping

    Returns:
        DAX filter expression for RLS role
    """
    return (
        f"VAR __UserNodes = "
        f"CALCULATETABLE("
        f"VALUES('{lookup_table}'[AllowedNodeID]), "
        f"'{lookup_table}'[UserPrincipal] = USERPRINCIPALNAME()"
        f")\n"
        f"VAR __Path = PATH('{table_name}'[{key_column}], "
        f"'{table_name}'[{parent_column}])\n"
        f"RETURN\n"
        f"    COUNTROWS("
        f"FILTER(__UserNodes, "
        f"PATHCONTAINS(__Path, '{lookup_table}'[AllowedNodeID]))"
        f") > 0"
    )


def detect_hierarchy_columns(
    table_meta: dict,
) -> tuple[str, str] | None:
    """Detect parent-child hierarchy columns in a table.

    Looks for common patterns: parent_id/child_id, manager_id/employee_id, etc.

    Returns:
        (key_column, parent_column) tuple or None if not detected.
    """
    columns = [c.get("name", "").lower() for c in table_meta.get("columns", [])]
    col_set = set(columns)

    # Common parent-child column pairs
    pairs = [
        ("employee_id", "manager_id"),
        ("id", "parent_id"),
        ("node_id", "parent_node_id"),
        ("child_id", "parent_id"),
        ("account_id", "parent_account_id"),
        ("org_id", "parent_org_id"),
        ("dept_id", "parent_dept_id"),
        ("category_id", "parent_category_id"),
        ("region_id", "parent_region_id"),
    ]

    for key_col, parent_col in pairs:
        if key_col in col_set and parent_col in col_set:
            # Return original-case names
            orig_cols = {c.get("name", "").lower(): c.get("name", "") for c in table_meta.get("columns", [])}
            return (orig_cols.get(key_col, key_col), orig_cols.get(parent_col, parent_col))

    return None


def generate_hierarchy_rls(
    role_name: str,
    table_name: str,
    key_column: str,
    parent_column: str,
    lookup_table: str = "SecurityHierarchy",
) -> HierarchyRLSSpec:
    """Generate a complete hierarchy-based RLS specification.

    Args:
        role_name: Name of the RLS role
        table_name: Table with parent-child hierarchy
        key_column: PK column in hierarchy
        parent_column: Parent FK column
        lookup_table: User→node mapping table name

    Returns:
        HierarchyRLSSpec with DAX filter and metadata
    """
    hierarchy_col = f"Path_{key_column}"
    dax = generate_hierarchy_rls_dax(
        table_name, key_column, hierarchy_col, parent_column, lookup_table
    )

    warnings = []
    warnings.append(
        f"Ensure '{lookup_table}' table exists with columns: "
        f"UserPrincipal (string), AllowedNodeID (string)"
    )
    warnings.append(
        f"Add calculated column '{hierarchy_col}' = "
        f"PATH('{table_name}'[{key_column}], '{table_name}'[{parent_column}])"
    )

    return HierarchyRLSSpec(
        role_name=role_name,
        table_name=table_name,
        hierarchy_column=hierarchy_col,
        parent_column=parent_column,
        key_column=key_column,
        dax_filter=dax,
        lookup_table=lookup_table,
        warnings=warnings,
    )


def generate_hierarchy_lookup_ddl(
    lookup_table: str = "SecurityHierarchy",
) -> str:
    """Generate DDL for the security hierarchy lookup table."""
    return (
        f"CREATE TABLE IF NOT EXISTS {lookup_table} (\n"
        f"    UserPrincipal STRING NOT NULL,\n"
        f"    AllowedNodeID STRING NOT NULL,\n"
        f"    NodeName STRING,\n"
        f"    GrantedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
        f") USING DELTA\n"
        f"COMMENT 'Security lookup for hierarchy-based RLS - maps users to hierarchy nodes';\n"
    )

