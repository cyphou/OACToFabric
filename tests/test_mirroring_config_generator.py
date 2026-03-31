"""Tests for mirroring_config_generator — Fabric Mirroring for Oracle."""

from __future__ import annotations

import json
import unittest

from src.agents.schema.mirroring_config_generator import (
    MirroringConfig,
    MirroringTableConfig,
    generate_mirroring_config,
)


class TestMirroringConfig(unittest.TestCase):

    def test_to_dict(self):
        config = MirroringConfig(
            connection_server="oracle-host.example.com",
            connection_database="ORCL",
            tables=[MirroringTableConfig(schema_name="HR", table_name="EMPLOYEES")],
        )
        d = config.to_dict()
        self.assertIn("mirroringDefinition.json", str(d) or json.dumps(d))

    def test_to_json(self):
        config = MirroringConfig(connection_server="s", connection_database="d", tables=[])
        j = config.to_json()
        parsed = json.loads(j)
        self.assertIsInstance(parsed, dict)


class TestGenerateMirroringConfig(unittest.TestCase):

    def test_basic_generation(self):
        config = generate_mirroring_config(
            server="oracle-host",
            database="ORCL",
            tables=[{"name": "EMPLOYEES", "schema": "HR"}, {"name": "DEPARTMENTS", "schema": "HR"}],
        )
        self.assertEqual(config.connection_server, "oracle-host")
        self.assertEqual(len(config.tables), 2)

    def test_include_pattern(self):
        config = generate_mirroring_config(
            server="s",
            database="d",
            tables=[{"name": "EMP", "schema": "HR"}, {"name": "DEPT", "schema": "HR"}, {"name": "LEDGER", "schema": "FIN"}],
            include_patterns=["HR.*"],
        )
        included = [t for t in config.tables if t.include]
        self.assertEqual(len(included), 2)

    def test_exclude_pattern(self):
        config = generate_mirroring_config(
            server="s",
            database="d",
            tables=[{"name": "EMP", "schema": "HR"}, {"name": "TEMP_DATA", "schema": "HR"}, {"name": "DEPT", "schema": "HR"}],
            exclude_patterns=["*TEMP*"],
        )
        included = [t for t in config.tables if t.include]
        self.assertEqual(len(included), 2)

    def test_empty_tables(self):
        config = generate_mirroring_config(server="s", database="d", tables=[])
        self.assertEqual(len(config.tables), 0)


if __name__ == "__main__":
    unittest.main()
