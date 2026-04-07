"""Smoke tests — Schema Migration Agent end-to-end."""

from __future__ import annotations

import unittest


class TestSchemaSmoke(unittest.TestCase):
    """Verify Schema Agent can produce DDL for a small set of Oracle tables."""

    def test_ddl_generator_import(self) -> None:
        from src.agents.schema import ddl_generator  # noqa: F401

    def test_type_mapper_import(self) -> None:
        from src.agents.schema import type_mapper  # noqa: F401

    def test_sql_translator_import(self) -> None:
        from src.agents.schema import sql_translator  # noqa: F401

    def test_lakehouse_generator_import(self) -> None:
        from src.agents.schema import lakehouse_generator  # noqa: F401

    def test_basic_type_mapping(self) -> None:
        """Oracle NUMBER(10) maps to a Fabric-compatible type."""
        from src.agents.schema.type_mapper import map_oracle_type

        result = map_oracle_type("NUMBER(10)")
        self.assertIsNotNone(result)
        self.assertTrue(len(result.fabric_type) > 0)

    def test_ddl_generation_simple_table(self) -> None:
        """DDL generator produces a CREATE TABLE statement."""
        from src.agents.schema.ddl_generator import generate_create_table

        columns = [
            {"name": "ID", "data_type": "NUMBER", "precision": 10, "scale": 0, "nullable": False},
            {"name": "NAME", "data_type": "VARCHAR2", "precision": 100, "scale": None, "nullable": True},
        ]
        ddl = generate_create_table("SMOKE_TABLE", columns)
        self.assertIn("SMOKE_TABLE", ddl)
        self.assertIn("CREATE", ddl.upper())


if __name__ == "__main__":
    unittest.main()
