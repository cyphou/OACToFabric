"""Tests for aad_group_provisioner — Entra ID group generation."""

from __future__ import annotations

import unittest

from src.agents.security.aad_group_provisioner import (
    EntraGroupDef,
    FabricWorkspaceRoleAssignment,
    GroupProvisioningResult,
    OACAppRole,
    provision_groups,
)


class TestEntraGroupDef(unittest.TestCase):

    def test_graph_api_payload(self):
        group = EntraGroupDef(display_name="Fabric-Sales", description="Sales team")
        payload = group.to_graph_api_payload()
        self.assertEqual(payload["displayName"], "Fabric-Sales")
        self.assertTrue(payload["securityEnabled"])
        self.assertFalse(payload["mailEnabled"])
        self.assertEqual(payload["groupTypes"], [])


class TestFabricWorkspaceRoleAssignment(unittest.TestCase):

    def test_api_payload(self):
        assignment = FabricWorkspaceRoleAssignment(
            group_name="Fabric-Admins", workspace_role="Admin"
        )
        payload = assignment.to_api_payload()
        self.assertEqual(payload["role"], "Admin")
        self.assertEqual(payload["principal"]["type"], "Group")


class TestProvisionGroups(unittest.TestCase):

    def test_basic_provisioning(self):
        roles = [
            OACAppRole(name="Sales-Read", members=["user1@corp.com"], permissions=["read"]),
            OACAppRole(name="Sales-Write", members=["user2@corp.com"], permissions=["write"]),
        ]
        result = provision_groups(roles)
        self.assertEqual(len(result.groups), 2)
        self.assertEqual(len(result.workspace_assignments), 2)

    def test_prefix(self):
        roles = [OACAppRole(name="Analysts")]
        result = provision_groups(roles, group_prefix="Mig")
        self.assertTrue(result.groups[0].display_name.startswith("Mig-"))

    def test_permission_to_role_mapping(self):
        roles = [
            OACAppRole(name="Admin", permissions=["admin"]),
            OACAppRole(name="Editor", permissions=["write"]),
            OACAppRole(name="Reader", permissions=["read"]),
        ]
        result = provision_groups(roles)
        assignments = {a.group_name: a.workspace_role for a in result.workspace_assignments}
        self.assertEqual(assignments["Fabric-Admin"], "Admin")
        self.assertEqual(assignments["Fabric-Editor"], "Contributor")
        self.assertEqual(assignments["Fabric-Reader"], "Viewer")

    def test_hierarchy_nesting(self):
        roles = [
            OACAppRole(name="Global", members=["admin@corp.com"]),
            OACAppRole(name="Regional", parent_role="Global", members=["regional@corp.com"]),
        ]
        result = provision_groups(roles)
        global_group = next(g for g in result.groups if "Global" in g.display_name)
        self.assertEqual(len(global_group.member_groups), 1)

    def test_app_audiences(self):
        roles = [
            OACAppRole(name="Viewer1", permissions=["read"]),
            OACAppRole(name="Admin1", permissions=["admin"]),
        ]
        result = provision_groups(roles)
        viewer_audiences = [a for a in result.app_audiences if "Viewer1" in a.group_name]
        self.assertEqual(len(viewer_audiences), 1)

    def test_data_access_full_maps_admin(self):
        roles = [OACAppRole(name="SuperUser", data_access_level="full")]
        result = provision_groups(roles)
        self.assertEqual(result.workspace_assignments[0].workspace_role, "Admin")

    def test_empty_roles(self):
        result = provision_groups([])
        self.assertEqual(len(result.groups), 0)


if __name__ == "__main__":
    unittest.main()
