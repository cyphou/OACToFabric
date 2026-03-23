"""Role mapper — OAC application roles → Fabric workspace & PBI RLS roles.

Maps OAC application roles to:
 1. **Fabric workspace roles** (Admin / Contributor / Member / Viewer)
 2. **Power BI RLS role definitions** (names + table permissions)
 3. **Azure AD security group → role assignments** (deployment script input)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FabricWorkspaceRole(str, Enum):
    """Fabric workspace-level roles."""

    ADMIN = "Admin"
    CONTRIBUTOR = "Contributor"
    MEMBER = "Member"
    VIEWER = "Viewer"


class OACPermissionLevel(str, Enum):
    """OAC application role permission levels."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    CONTENT_CREATOR = "contentCreator"
    VIEWER_EDIT = "viewerEdit"
    VIEWER = "viewer"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class OACRole:
    """An OAC application role extracted from the inventory."""

    name: str
    permission_level: OACPermissionLevel = OACPermissionLevel.UNKNOWN
    users: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    rls_filters: list[dict[str, Any]] = field(default_factory=list)
    object_permissions: list[dict[str, Any]] = field(default_factory=list)
    session_variables: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricRoleAssignment:
    """A Fabric workspace role assignment."""

    role_name: str
    workspace_role: FabricWorkspaceRole
    aad_group: str = ""
    users: list[str] = field(default_factory=list)
    source_oac_role: str = ""


@dataclass
class RLSRoleDefinition:
    """A Power BI RLS role definition."""

    role_name: str
    description: str = ""
    table_permissions: list[RLSTablePermission] = field(default_factory=list)
    source_oac_role: str = ""
    warnings: list[str] = field(default_factory=list)
    requires_review: bool = False


@dataclass
class RLSTablePermission:
    """A table-level RLS filter within a role."""

    table_name: str
    filter_expression: str  # DAX filter expression
    source_expression: str = ""  # Original OAC expression


@dataclass
class RoleMappingResult:
    """Result of mapping OAC roles to Fabric/PBI roles."""

    workspace_assignments: list[FabricRoleAssignment] = field(default_factory=list)
    rls_roles: list[RLSRoleDefinition] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    review_items: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# OAC permission level normalisation
# ---------------------------------------------------------------------------


_PERMISSION_KEYWORDS: dict[str, OACPermissionLevel] = {
    "admin": OACPermissionLevel.ADMIN,
    "administrator": OACPermissionLevel.ADMIN,
    "developer": OACPermissionLevel.DEVELOPER,
    "bi developer": OACPermissionLevel.DEVELOPER,
    "content creator": OACPermissionLevel.CONTENT_CREATOR,
    "contentcreator": OACPermissionLevel.CONTENT_CREATOR,
    "author": OACPermissionLevel.CONTENT_CREATOR,
    "viewer": OACPermissionLevel.VIEWER,
    "consumer": OACPermissionLevel.VIEWER,
    "read": OACPermissionLevel.VIEWER,
    "readonly": OACPermissionLevel.VIEWER,
    "read-only": OACPermissionLevel.VIEWER,
    "vieweredit": OACPermissionLevel.VIEWER_EDIT,
    "editor": OACPermissionLevel.VIEWER_EDIT,
}


def _parse_permission_level(raw: str) -> OACPermissionLevel:
    """Normalise a raw OAC permission string to an enum value."""
    s = raw.strip().lower()
    if s in _PERMISSION_KEYWORDS:
        return _PERMISSION_KEYWORDS[s]
    # Attempt partial match
    for kw, lvl in _PERMISSION_KEYWORDS.items():
        if kw in s:
            return lvl
    return OACPermissionLevel.UNKNOWN


# ---------------------------------------------------------------------------
# Workspace role mapping
# ---------------------------------------------------------------------------


_OAC_TO_WORKSPACE: dict[OACPermissionLevel, FabricWorkspaceRole] = {
    OACPermissionLevel.ADMIN: FabricWorkspaceRole.ADMIN,
    OACPermissionLevel.DEVELOPER: FabricWorkspaceRole.CONTRIBUTOR,
    OACPermissionLevel.CONTENT_CREATOR: FabricWorkspaceRole.CONTRIBUTOR,
    OACPermissionLevel.VIEWER_EDIT: FabricWorkspaceRole.MEMBER,
    OACPermissionLevel.VIEWER: FabricWorkspaceRole.VIEWER,
    OACPermissionLevel.CUSTOM: FabricWorkspaceRole.MEMBER,
    OACPermissionLevel.UNKNOWN: FabricWorkspaceRole.VIEWER,
}


def map_workspace_role(permission_level: OACPermissionLevel) -> FabricWorkspaceRole:
    """Map an OAC permission level to a Fabric workspace role."""
    return _OAC_TO_WORKSPACE.get(permission_level, FabricWorkspaceRole.VIEWER)


# ---------------------------------------------------------------------------
# Role parsing
# ---------------------------------------------------------------------------


def parse_oac_role(role_meta: dict[str, Any]) -> OACRole:
    """Parse an OAC security role inventory item's metadata into an OACRole."""
    return OACRole(
        name=role_meta.get("name", "UnknownRole"),
        permission_level=_parse_permission_level(
            role_meta.get("permission_level", role_meta.get("type", "unknown"))
        ),
        users=role_meta.get("users", []),
        groups=role_meta.get("groups", []),
        rls_filters=role_meta.get("rls_filters", []),
        object_permissions=role_meta.get("object_permissions", []),
        session_variables=role_meta.get("session_variables", []),
        metadata=role_meta,
    )


# ---------------------------------------------------------------------------
# Full role mapping
# ---------------------------------------------------------------------------


def map_roles(oac_roles: list[OACRole]) -> RoleMappingResult:
    """Map a list of OAC roles to Fabric workspace + PBI RLS roles.

    Returns workspace role assignments and RLS role definitions.
    """
    result = RoleMappingResult()

    for oac_role in oac_roles:
        # 1. Workspace role assignment
        ws_role = map_workspace_role(oac_role.permission_level)
        aad_group = _suggest_aad_group(oac_role)

        result.workspace_assignments.append(
            FabricRoleAssignment(
                role_name=oac_role.name,
                workspace_role=ws_role,
                aad_group=aad_group,
                users=oac_role.users,
                source_oac_role=oac_role.name,
            )
        )

        if oac_role.permission_level == OACPermissionLevel.UNKNOWN:
            result.warnings.append(
                f"Role '{oac_role.name}': unknown permission level — defaulting to Viewer"
            )

        # 2. RLS role definition (if role has RLS filters or session variables)
        if oac_role.rls_filters or oac_role.session_variables:
            rls_role = _build_rls_role(oac_role)
            result.rls_roles.append(rls_role)
            if rls_role.requires_review:
                result.review_items.append({
                    "type": "rls_role",
                    "role": oac_role.name,
                    "warnings": rls_role.warnings,
                })

    logger.info(
        "Mapped %d OAC roles → %d workspace assignments, %d RLS roles",
        len(oac_roles), len(result.workspace_assignments), len(result.rls_roles),
    )
    return result


def _suggest_aad_group(role: OACRole, *, graph_client: Any = None) -> str:
    """Suggest an Azure AD security group name for a role.

    If a Microsoft Graph client is provided, attempt to find an existing
    AAD group whose display name matches common patterns derived from the
    OAC role name.  Falls back to a deterministic naming convention when
    Graph is unavailable or no match is found.

    Parameters
    ----------
    role : OACRole
        The OAC role to map.
    graph_client : optional
        An authenticated ``GraphServiceClient`` from the
        ``msgraph-sdk-python`` package, or any object that exposes an
        async ``groups.get()`` method.  When *None*, the function returns
        a convention-based group name without calling Graph.
    """
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", role.name)
    convention_name = f"SG-PBI-{safe}"

    if graph_client is None:
        return convention_name

    # --- Attempt Graph API lookup ---
    search_names = [
        convention_name,
        f"SG-Fabric-{safe}",
        safe,
        role.name,
    ]

    try:
        import asyncio

        async def _lookup() -> str | None:
            for candidate in search_names:
                try:
                    # Graph SDK v1.x  uses request configuration
                    from msgraph.generated.groups.groups_request_builder import (  # type: ignore[import-untyped]
                        GroupsRequestBuilder,
                    )
                    query = GroupsRequestBuilder.GroupsRequestBuilderGetQueryParameters(
                        filter=f"displayName eq '{candidate}'",
                        top=1,
                        select=["id", "displayName"],
                    )
                    config = GroupsRequestBuilder.GroupsRequestBuilderGetRequestConfiguration(
                        query_parameters=query,
                    )
                    result = await graph_client.groups.get(request_configuration=config)
                    if result and result.value:
                        found = result.value[0].display_name
                        logger.info("AAD group resolved via Graph: '%s' → '%s'", role.name, found)
                        return found
                except Exception:
                    # Fallback: simpler API (e.g. httpx-based stub in tests)
                    try:
                        result = await graph_client.groups.get(filter=f"displayName eq '{candidate}'")
                        if result and hasattr(result, "value") and result.value:
                            return result.value[0].display_name
                    except Exception:
                        pass
            return None

        # Run in existing event loop or create one
        try:
            loop = asyncio.get_running_loop()
            # Already in async context — can't await here; return convention
            logger.debug("In async context — skipping Graph lookup for '%s'", role.name)
            return convention_name
        except RuntimeError:
            found = asyncio.run(_lookup())
            if found:
                return found
    except ImportError:
        logger.debug("msgraph SDK not installed — using convention name for '%s'", role.name)
    except Exception:
        logger.warning("Graph API lookup failed for role '%s' — using convention name", role.name, exc_info=True)

    return convention_name


def _build_rls_role(role: OACRole) -> RLSRoleDefinition:
    """Build a PBI RLS role from an OAC role's filters and session variables."""
    warnings: list[str] = []
    table_perms: list[RLSTablePermission] = []

    # Process explicit RLS filters
    for flt in role.rls_filters:
        table = flt.get("table", "")
        expr = flt.get("expression", "")
        dax = translate_rls_expression(expr)
        if dax.startswith("/* REVIEW"):
            warnings.append(f"Table '{table}': complex filter requires review")
        table_perms.append(
            RLSTablePermission(
                table_name=table,
                filter_expression=dax,
                source_expression=expr,
            )
        )

    # Process session variable filters
    for sv in role.session_variables:
        table = sv.get("table", "")
        column = sv.get("column", "")
        variable = sv.get("variable", "")
        dax = _session_variable_to_dax(variable, table, column)
        if "REVIEW" in dax:
            warnings.append(
                f"Session variable '{variable}' on {table}.{column}: needs lookup table"
            )
        table_perms.append(
            RLSTablePermission(
                table_name=table,
                filter_expression=dax,
                source_expression=f"VALUEOF(NQ_SESSION.{variable})",
            )
        )

    return RLSRoleDefinition(
        role_name=_safe_role_name(role.name),
        description=f"Migrated from OAC role '{role.name}'",
        table_permissions=table_perms,
        source_oac_role=role.name,
        warnings=warnings,
        requires_review=bool(warnings),
    )


def _safe_role_name(name: str) -> str:
    """Sanitise a role name for TMDL."""
    safe = re.sub(r"[^a-zA-Z0-9_ ]", "", name).strip()
    return safe or "UnknownRole"


# ---------------------------------------------------------------------------
# Expression translation helpers
# ---------------------------------------------------------------------------


def translate_rls_expression(oac_expr: str) -> str:
    """Translate an OAC RLS filter expression to DAX.

    Handles common patterns:
      - VALUEOF(NQ_SESSION.USER) → USERPRINCIPALNAME()
      - VALUEOF(NQ_SESSION.GROUP) → lookup table pattern
      - Simple column = value → DAX equivalent
    """
    if not oac_expr:
        return "TRUE()"

    expr = oac_expr.strip()

    # VALUEOF(NQ_SESSION.USER) → direct UPN match
    user_pattern = re.compile(
        r"VALUEOF\s*\(\s*NQ_SESSION\.USER\s*\)", re.IGNORECASE
    )
    if user_pattern.search(expr):
        return user_pattern.sub("USERPRINCIPALNAME()", expr)

    # VALUEOF(NQ_SESSION.<var>) → lookup table pattern
    session_pattern = re.compile(
        r"VALUEOF\s*\(\s*NQ_SESSION\.(\w+)\s*\)", re.IGNORECASE
    )
    match = session_pattern.search(expr)
    if match:
        var_name = match.group(1)
        return (
            f"/* REVIEW: session variable {var_name} — "
            f"create Security_UserAccess lookup table */\n"
            f"VAR CurrentUser = USERPRINCIPALNAME()\n"
            f"VAR UserValues = CALCULATETABLE(\n"
            f"    VALUES(Security_UserAccess[{var_name}]),\n"
            f"    Security_UserAccess[UserEmail] = CurrentUser\n"
            f")\n"
            f"RETURN [FilterColumn] IN UserValues"
        )

    # Simple column filters  (column = 'value')
    simple_eq = re.compile(r"^(\w+)\s*=\s*'([^']+)'$")
    m = simple_eq.match(expr)
    if m:
        col, val = m.group(1), m.group(2)
        return f'[{col}] = "{val}"'

    # Fallback — pass through with review flag
    return f"/* REVIEW: complex expression */ {expr}"


def _session_variable_to_dax(
    variable: str, table: str, column: str,
) -> str:
    """Convert an OAC session variable reference to a DAX RLS pattern."""
    var_upper = variable.upper()

    if var_upper == "USER":
        return f'[{column}] = USERPRINCIPALNAME()'

    # General session variable → lookup table pattern
    return (
        f"/* REVIEW: session variable {variable} — needs Security_UserAccess table */\n"
        f"VAR CurrentUser = USERPRINCIPALNAME()\n"
        f"VAR UserValues = CALCULATETABLE(\n"
        f"    VALUES(Security_UserAccess[{variable}]),\n"
        f"    Security_UserAccess[UserEmail] = CurrentUser\n"
        f")\n"
        f"RETURN [{column}] IN UserValues"
    )


# ---------------------------------------------------------------------------
# Workspace role assignment script generation
# ---------------------------------------------------------------------------


def generate_role_assignment_script(
    assignments: list[FabricRoleAssignment],
    workspace_id: str = "<WORKSPACE_ID>",
) -> str:
    """Generate a PowerShell script to assign workspace roles.

    Can be run via ``Invoke-FabricRestMethod`` or the Fabric REST API.
    """
    lines = [
        "# Fabric Workspace Role Assignment Script",
        "# Generated by Agent 06 — Security Migration Agent",
        f"# Workspace ID: {workspace_id}",
        "",
        '$workspaceId = "' + workspace_id + '"',
        "",
    ]

    for a in assignments:
        group = a.aad_group or f"SG-PBI-{re.sub(r'[^a-zA-Z0-9_-]', '_', a.role_name)}"
        lines.extend([
            f"# Role: {a.role_name} (from OAC role: {a.source_oac_role})",
            f'$groupId = (Get-AzADGroup -DisplayName "{group}").Id',
            f'$body = @{{ groupId = $groupId; role = "{a.workspace_role.value}" }} | ConvertTo-Json',
            f'Invoke-FabricRestMethod -Method POST -Uri "workspaces/$workspaceId/roleAssignments" -Body $body',
            "",
        ])

    return "\n".join(lines)
