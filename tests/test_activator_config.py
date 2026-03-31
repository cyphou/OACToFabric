"""Tests for activator_config — Data Activator Reflex configuration."""

from __future__ import annotations

import json
import unittest

from src.agents.report.alert_migrator import ActivatorCondition, ActivatorAction, ActivatorTrigger
from src.agents.report.activator_config import (
    ObjectStream,
    ReflexConfig,
    generate_reflex_config,
)


class TestReflexConfig(unittest.TestCase):

    def _make_trigger(self, name: str = "T1", obj: str = "Sales") -> ActivatorTrigger:
        return ActivatorTrigger(
            name=name,
            object_type=obj,
            conditions=[ActivatorCondition(property_name="Revenue", operator="GreaterThan", threshold=100)],
            actions=[ActivatorAction(action_type="Email", recipients=["a@b.com"])],
        )

    def test_to_dict(self):
        config = ReflexConfig(
            reflex_name="TestReflex",
            triggers=[self._make_trigger()],
            object_streams=[ObjectStream(name="Sales", table_name="Sales")],
        )
        d = config.to_dict()
        self.assertEqual(d["displayName"], "TestReflex")
        self.assertEqual(d["type"], "Reflex")
        parts = d["definition"]["parts"]
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["path"], "reflex.json")

    def test_to_json(self):
        config = ReflexConfig(reflex_name="R", triggers=[], object_streams=[])
        j = config.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["displayName"], "R")


class TestGenerateReflexConfig(unittest.TestCase):

    def test_basic_generation(self):
        triggers = [
            ActivatorTrigger(
                name="Alert1",
                object_type="Orders",
                conditions=[ActivatorCondition(property_name="Total", operator="GreaterThan", threshold=500)],
                actions=[ActivatorAction(action_type="Email")],
            )
        ]
        config = generate_reflex_config("MyReflex", triggers, table_name="Orders")
        self.assertEqual(config.reflex_name, "MyReflex")
        self.assertEqual(len(config.object_streams), 1)
        self.assertEqual(config.object_streams[0].name, "Orders")
        self.assertIn("Total", config.object_streams[0].properties)

    def test_deduplicates_streams(self):
        triggers = [
            ActivatorTrigger(
                name=f"A{i}", object_type="Sales",
                conditions=[ActivatorCondition(property_name=f"M{i}", operator="Equals")],
            )
            for i in range(3)
        ]
        config = generate_reflex_config("R", triggers)
        self.assertEqual(len(config.object_streams), 1)

    def test_multiple_object_types(self):
        triggers = [
            ActivatorTrigger(name="A1", object_type="Sales", conditions=[]),
            ActivatorTrigger(name="A2", object_type="Orders", conditions=[]),
        ]
        config = generate_reflex_config("R", triggers)
        self.assertEqual(len(config.object_streams), 2)


if __name__ == "__main__":
    unittest.main()
