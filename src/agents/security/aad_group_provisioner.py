"""AAD Group Provisioner — map OAC application roles to Entra ID groups.

Generates the Entra ID (Azure AD) group provisioning requests needed to
replicate OAC role-based access in Fabric workspaces and Power BI
app audiences.

Handles:
  - OAC app role → Entra ID security group mapping
  - Nested group structures (role hierarchies)
  - Fabric workspace role assignment (Admin, Member, Contributor, Viewer)
  - Power BI app audience segmentation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAC role types
# ---------------------------------------------------------------------------


@dataclass
class OACAppRole:
    """An OAC application role."""

    name: str
    description: str = ""
    members: list[str] = field(default_factory=list)     # user principals
    parent_role: str = ""                                  # role hierarchy
    permissions: list[str] = field(default_factory=list)  # read, write, admin
    data_access_level: str = "read"                        # read, write, full


# ---------------------------------------------------------------------------
# Entra ID / Fabric types
# ---------------------------------------------------------------------------


@dataclass
class EntraGroupDef:
    """Entra ID security group definition."""

    display_name: str
    description: str = ""
    mail_nickname: str = ""
    members: list[str] = field(default_factory=list)
    member_groups: list[str] = field(default_factory=list)  # nested groups
    security_enabled: bool = True
    mail_enabled: bool = False

    def to_graph_api_payload(self) -> dict[str, Any]:
        """Generate Microsoft Graph API payload for group creation."""
        nickname = self.mail_nickname or self.display_name.replace(" ", "").replace("-", "")
        return {
            "displayName": self.display_name,
            "description": self.description,
            "mailNickname": nickname,
            "securityEnabled": self.security_enabled,
            "mailEnabled": self.mail_enabled,
            "groupTypes": [],
        }


@dataclass
class FabricWorkspaceRoleAssignment:
    """Fabric workspace role assignment."""

    group_name: str
    workspace_role: str     # Admin, Member, Contributor, Viewer
    workspace_id: str = ""

    def to_api_payload(self) -> dict[str, Any]:
        return {
            "principal": {
                "id": "",   # to be filled with actual group ID
                "type": "Group",
                "displayName": self.group_name,
            },
            "role": self.workspace_role,
        }


@dataclass
class AppAudienceSegment:
    """Power BI app audience segment."""

    group_name: str
    audience_name: str = "Default"
    pages: list[str] = field(default_factory=list)  # page names visible to this audience


@dataclass
class GroupProvisioningResult:
    """Result of AAD group provisioning generation."""

    groups: list[EntraGroupDef] = field(default_factory=list)
    workspace_assignments: list[FabricWorkspaceRoleAssignment] = field(default_factory=list)
    app_audiences: list[AppAudienceSegment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Permission → workspace role mapping
# ---------------------------------------------------------------------------

_PERMISSION_TO_ROLE: dict[str, str] = {
    "admin": "Admin",
    "full": "Admin",
    "write": "Contributor",
    "edit": "Contributor",
    "create": "Member",
    "read": "Viewer",
    "view": "Viewer",
    "execute": "Viewer",
}


def _map_workspace_role(permissions: list[str], data_access: str) -> str:
    """Determine Fabric workspace role from OAC permissions."""
    if data_access in ("full", "admin"):
        return "Admin"

    highest = "Viewer"
    role_rank = {"Viewer": 0, "Member": 1, "Contributor": 2, "Admin": 3}

    for perm in permissions:
        role = _PERMISSION_TO_ROLE.get(perm.lower(), "Viewer")
        if role_rank.get(role, 0) > role_rank.get(highest, 0):
            highest = role

    return highest


# ---------------------------------------------------------------------------
# Group name sanitization
# ---------------------------------------------------------------------------


def _sanitize_group_name(role_name: str, prefix: str = "Fabric") -> str:
    """Generate a valid Entra ID group display name from OAC role."""
    clean = role_name.replace("/", "-").replace("\\", "-").replace(":", "-")
    return f"{prefix}-{clean}"


# ---------------------------------------------------------------------------
# Core provisioning logic
# ---------------------------------------------------------------------------


def provision_groups(
    oac_roles: list[OACAppRole],
    group_prefix: str = "Fabric",
    workspace_id: str = "",
) -> GroupProvisioningResult:
    """Generate Entra ID group definitions and workspace assignments from OAC roles.

    Parameters
    ----------
    oac_roles : list[OACAppRole]
        OAC application role definitions.
    group_prefix : str
        Prefix for generated Entra ID group names.
    workspace_id : str
        Target Fabric workspace ID.

    Returns
    -------
    GroupProvisioningResult
        Generated groups, workspace assignments, and app audiences.
    """
    result = GroupProvisioningResult()
    group_map: dict[str, str] = {}  # role_name → group display name

    # First pass: create groups
    for role in oac_roles:
        group_name = _sanitize_group_name(role.name, group_prefix)
        group_map[role.name] = group_name

        group = EntraGroupDef(
            display_name=group_name,
            description=role.description or f"Migrated from OAC role: {role.name}",
            members=list(role.members),
        )
        result.groups.append(group)

    # Second pass: resolve nested groups (role hierarchies)
    for role in oac_roles:
        if role.parent_role and role.parent_role in group_map:
            parent_group_name = group_map[role.parent_role]
            child_group_name = group_map[role.name]

            for group in result.groups:
                if group.display_name == parent_group_name:
                    group.member_groups.append(child_group_name)
                    break

    # Third pass: workspace assignments
    for role in oac_roles:
        group_name = group_map[role.name]
        ws_role = _map_workspace_role(role.permissions, role.data_access_level)

        result.workspace_assignments.append(FabricWorkspaceRoleAssignment(
            group_name=group_name,
            workspace_role=ws_role,
            workspace_id=workspace_id,
        ))

    # Fourth pass: app audiences
    viewer_groups = [
        a for a in result.workspace_assignments
        if a.workspace_role == "Viewer"
    ]
    for va in viewer_groups:
        result.app_audiences.append(AppAudienceSegment(
            group_name=va.group_name,
        ))

    logger.info(
        "Provisioned %d Entra ID groups, %d workspace assignments, %d app audiences",
        len(result.groups),
        len(result.workspace_assignments),
        len(result.app_audiences),
    )
    return result
