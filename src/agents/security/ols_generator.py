"""OLS generator — OAC object-level permissions → PBI Object-Level Security.

Translates OAC column-hide / table-hide permissions into Power BI
Object-Level Security (OLS) definitions in TMDL format.

OLS allows hiding tables, columns, or measures from specific roles.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OLSPermission(str, Enum):
    """OLS metadata permission levels."""

    NONE = "none"           # Hidden — object not visible
    READ = "read"           # Visible (default)


class OACObjectPermissionType(str, Enum):
    """Types of OAC object-level permissions."""

    HIDE_COLUMN = "hideColumn"
    HIDE_TABLE = "hideTable"
    HIDE_MEASURE = "hideMeasure"
    RESTRICT_ACCESS = "restrictAccess"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class OLSColumnPermission:
    """A column-level OLS permission within a role."""

    table_name: str
    column_name: str
    permission: OLSPermission = OLSPermission.NONE


@dataclass
class OLSTablePermission:
    """A table-level OLS permission within a role."""

    table_name: str
    permission: OLSPermission = OLSPermission.NONE


@dataclass
class OLSRoleDefinition:
    """A complete OLS role definition."""

    role_name: str
    description: str = ""
    column_permissions: list[OLSColumnPermission] = field(default_factory=list)
    table_permissions: list[OLSTablePermission] = field(default_factory=list)
    source_oac_role: str = ""
    warnings: list[str] = field(default_factory=list)
    requires_review: bool = False


@dataclass
class OLSGenerationResult:
    """Result of OLS generation."""

    ols_roles: list[OLSRoleDefinition] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    review_items: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# OAC permission parsing
# ---------------------------------------------------------------------------


def _parse_permission_type(raw: str) -> OACObjectPermissionType:
    """Normalise an OAC object permission type string."""
    s = raw.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    mapping: dict[str, OACObjectPermissionType] = {
        "hidecolumn": OACObjectPermissionType.HIDE_COLUMN,
        "columnhide": OACObjectPermissionType.HIDE_COLUMN,
        "hidetable": OACObjectPermissionType.HIDE_TABLE,
        "tablehide": OACObjectPermissionType.HIDE_TABLE,
        "hidemeasure": OACObjectPermissionType.HIDE_MEASURE,
        "measurehide": OACObjectPermissionType.HIDE_MEASURE,
        "restrictaccess": OACObjectPermissionType.RESTRICT_ACCESS,
        "deny": OACObjectPermissionType.RESTRICT_ACCESS,
        "none": OACObjectPermissionType.HIDE_COLUMN,
    }
    return mapping.get(s, OACObjectPermissionType.UNKNOWN)


# ---------------------------------------------------------------------------
# OLS conversion
# ---------------------------------------------------------------------------


def convert_object_permissions(
    role_name: str,
    permissions: list[dict[str, Any]],
    table_mapping: dict[str, str] | None = None,
) -> OLSRoleDefinition:
    """Convert OAC object-level permissions to a PBI OLS role definition.

    Parameters
    ----------
    role_name : str
        Name of the OAC role.
    permissions : list[dict]
        Object permissions from the inventory.  Expected keys::

            - type: str (hideColumn | hideTable | hideMeasure)
            - table: str
            - column: str (for column-level)
            - measure: str (for measure-level, optional)
    table_mapping : dict
        OAC table name → PBI semantic model table name.
    """
    tmap = table_mapping or {}
    col_perms: list[OLSColumnPermission] = []
    tbl_perms: list[OLSTablePermission] = []
    warnings: list[str] = []

    for perm in permissions:
        perm_type = _parse_permission_type(perm.get("type", ""))
        table = tmap.get(perm.get("table", ""), perm.get("table", ""))
        column = perm.get("column", "")
        measure = perm.get("measure", "")

        if perm_type == OACObjectPermissionType.HIDE_TABLE:
            tbl_perms.append(
                OLSTablePermission(
                    table_name=table,
                    permission=OLSPermission.NONE,
                )
            )

        elif perm_type == OACObjectPermissionType.HIDE_COLUMN:
            col_perms.append(
                OLSColumnPermission(
                    table_name=table,
                    column_name=column,
                    permission=OLSPermission.NONE,
                )
            )

        elif perm_type == OACObjectPermissionType.HIDE_MEASURE:
            warnings.append(
                f"Measure-level OLS for '{measure or column}' on '{table}' "
                "is not natively supported in Power BI. "
                "Consider using a Perspective or conditional visibility instead."
            )
            # Still add as column permission (best effort)
            if measure or column:
                col_perms.append(
                    OLSColumnPermission(
                        table_name=table,
                        column_name=measure or column,
                        permission=OLSPermission.NONE,
                    )
                )

        elif perm_type == OACObjectPermissionType.RESTRICT_ACCESS:
            # Generic restrict → table hide
            tbl_perms.append(
                OLSTablePermission(
                    table_name=table,
                    permission=OLSPermission.NONE,
                )
            )
            warnings.append(
                f"Restricted access on '{table}' — mapped to table-level OLS. "
                "Review if column-level restrictions were intended."
            )

        else:
            warnings.append(
                f"Unknown object permission type '{perm.get('type', '')}' "
                f"for role '{role_name}' on '{table}' — skipped"
            )

    return OLSRoleDefinition(
        role_name=role_name,
        description=f"OLS definitions migrated from OAC role '{role_name}'",
        column_permissions=col_perms,
        table_permissions=tbl_perms,
        source_oac_role=role_name,
        warnings=warnings,
        requires_review=bool(warnings),
    )


def convert_all_object_permissions(
    roles_with_permissions: list[dict[str, Any]],
    table_mapping: dict[str, str] | None = None,
) -> OLSGenerationResult:
    """Convert object permissions from multiple OAC roles.

    Parameters
    ----------
    roles_with_permissions : list[dict]
        Each dict has ``name`` and ``object_permissions`` keys.
    """
    result = OLSGenerationResult()

    for role_data in roles_with_permissions:
        name = role_data.get("name", "UnknownRole")
        perms = role_data.get("object_permissions", [])
        if not perms:
            continue

        ols_role = convert_object_permissions(name, perms, table_mapping)
        result.ols_roles.append(ols_role)
        result.warnings.extend(ols_role.warnings)
        if ols_role.requires_review:
            result.review_items.append({
                "type": "ols_role",
                "role": name,
                "warnings": ols_role.warnings,
            })

    logger.info(
        "OLS conversion: %d roles with object-level permissions",
        len(result.ols_roles),
    )
    return result


# ---------------------------------------------------------------------------
# TMDL rendering
# ---------------------------------------------------------------------------


def render_ols_tmdl(ols_roles: list[OLSRoleDefinition]) -> str:
    """Render OLS role definitions as TMDL content.

    OLS permissions are expressed within role definitions
    as ``columnPermission`` with ``metadataPermission: none``.
    """
    if not ols_roles:
        return "// No OLS roles defined\n"

    lines: list[str] = [
        "// ==========================================================",
        "// OLS Roles — generated by Agent 06 (Security Migration Agent)",
        "// ==========================================================",
        "",
    ]

    for role in ols_roles:
        lines.extend(_render_ols_role(role))
        lines.append("")

    return "\n".join(lines)


def _render_ols_role(role: OLSRoleDefinition) -> list[str]:
    """Render a single OLS role as TMDL."""
    lines = [
        f"/// {role.description}" if role.description else f"/// OLS role: {role.role_name}",
        f"role '{role.role_name}'",
        f"\tmodelPermission: read",
        "",
    ]

    # Group by table
    tables: dict[str, list[OLSColumnPermission]] = {}
    for cp in role.column_permissions:
        tables.setdefault(cp.table_name, []).append(cp)

    # Table-level OLS
    hidden_tables = {tp.table_name for tp in role.table_permissions}

    for table in sorted(hidden_tables):
        lines.extend([
            f"\ttablePermission '{table}'",
            f"\t\tfilterExpression = FALSE()  // Table hidden via OLS",
            "",
        ])

    # Column-level OLS
    for table_name in sorted(tables.keys()):
        if table_name in hidden_tables:
            continue  # Already hidden at table level
        lines.append(f"\ttablePermission '{table_name}'")
        lines.append(f"\t\tfilterExpression = TRUE()")
        lines.append("")
        for cp in tables[table_name]:
            lines.extend([
                f"\t\tcolumnPermission '{cp.column_name}'",
                f"\t\t\tmetadataPermission: {cp.permission.value}",
                "",
            ])

    return lines


# ---------------------------------------------------------------------------
# Security matrix report
# ---------------------------------------------------------------------------


def generate_security_matrix(
    ols_roles: list[OLSRoleDefinition],
) -> str:
    """Generate a Markdown security matrix showing what each role can see."""
    lines = [
        "# Object-Level Security Matrix",
        "",
    ]

    if not ols_roles:
        lines.append("No OLS roles defined.")
        return "\n".join(lines)

    # Collect all tables and columns
    all_objects: set[str] = set()
    for role in ols_roles:
        for tp in role.table_permissions:
            all_objects.add(tp.table_name)
        for cp in role.column_permissions:
            all_objects.add(f"{cp.table_name}.{cp.column_name}")

    sorted_objects = sorted(all_objects)
    role_names = [r.role_name for r in ols_roles]

    # Header
    lines.append("| Object | " + " | ".join(role_names) + " |")
    lines.append("|---|" + "|".join(["---"] * len(role_names)) + "|")

    # Rows
    for obj in sorted_objects:
        cells: list[str] = [obj]
        for role in ols_roles:
            hidden_tables = {tp.table_name for tp in role.table_permissions}
            hidden_cols = {
                f"{cp.table_name}.{cp.column_name}"
                for cp in role.column_permissions
            }
            if obj in hidden_tables or obj in hidden_cols:
                cells.append("HIDDEN")
            else:
                cells.append("Visible")
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    return "\n".join(lines)
