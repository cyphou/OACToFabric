"""Smoke tests — Security Migration Agent end-to-end."""

from __future__ import annotations

import unittest


class TestSecuritySmoke(unittest.TestCase):
    """Verify Security Agent can produce RLS/OLS rules from OAC roles."""

    def test_rls_converter_import(self) -> None:
        from src.agents.security import rls_converter  # noqa: F401

    def test_ols_generator_import(self) -> None:
        from src.agents.security import ols_generator  # noqa: F401

    def test_role_mapper_import(self) -> None:
        from src.agents.security import role_mapper  # noqa: F401

    def test_rls_conversion_basic(self) -> None:
        """analyse_init_blocks parses init blocks into lookup tables."""
        from src.agents.security.rls_converter import analyse_init_blocks

        init_blocks = [
            {"variable": "REGION", "type": "session", "expression": "Region.RegionCode"},
        ]
        results = analyse_init_blocks(init_blocks)
        self.assertIsNotNone(results)
        self.assertIsInstance(results, list)

    def test_ols_generation_basic(self) -> None:
        """OLS generator can produce an OLS role definition."""
        from src.agents.security.ols_generator import convert_object_permissions

        permissions = [
            {"table": "Salaries", "column": "Amount", "permission": "none"},
        ]
        ols = convert_object_permissions("Analyst", permissions)
        self.assertIsNotNone(ols)


if __name__ == "__main__":
    unittest.main()
