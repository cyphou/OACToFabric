"""Tests for alert_migrator — OAC alerts → Data Activator triggers."""

from __future__ import annotations

import unittest

from src.agents.report.alert_migrator import (
    ActivatorTrigger,
    AlertMigrationResult,
    OACAgentDefinition,
    OACAlertCondition,
    OACAlertDelivery,
    OACAlertSchedule,
    migrate_alert,
    migrate_all_alerts,
)


class TestMigrateAlert(unittest.TestCase):

    def _make_agent(self, **kwargs) -> OACAgentDefinition:
        defaults = {
            "name": "TestAlert",
            "conditions": [OACAlertCondition(measure="Revenue", operator="gt", threshold=1000)],
            "schedule": OACAlertSchedule(frequency="daily"),
            "delivery": OACAlertDelivery(channel="email", recipients=["user@example.com"]),
        }
        defaults.update(kwargs)
        return OACAgentDefinition(**defaults)

    def test_basic_migration(self):
        trigger = migrate_alert(self._make_agent())
        self.assertEqual(trigger.name, "TestAlert")
        self.assertEqual(len(trigger.conditions), 1)
        self.assertEqual(trigger.conditions[0].operator, "GreaterThan")
        self.assertEqual(trigger.conditions[0].threshold, 1000)

    def test_schedule_mapping_daily(self):
        trigger = migrate_alert(self._make_agent())
        self.assertEqual(trigger.evaluation_frequency, "PT24H")

    def test_schedule_mapping_hourly(self):
        agent = self._make_agent(schedule=OACAlertSchedule(frequency="hourly"))
        trigger = migrate_alert(agent)
        self.assertEqual(trigger.evaluation_frequency, "PT1H")

    def test_delivery_email(self):
        trigger = migrate_alert(self._make_agent())
        self.assertEqual(trigger.actions[0].action_type, "Email")
        self.assertIn("user@example.com", trigger.actions[0].recipients)

    def test_delivery_dashboard_maps_to_teams(self):
        agent = self._make_agent(delivery=OACAlertDelivery(channel="dashboard"))
        trigger = migrate_alert(agent)
        self.assertEqual(trigger.actions[0].action_type, "Teams")

    def test_between_operator(self):
        agent = self._make_agent(conditions=[
            OACAlertCondition(measure="Score", operator="between", threshold=10, threshold_high=90)
        ])
        trigger = migrate_alert(agent)
        self.assertEqual(trigger.conditions[0].operator, "Between")
        self.assertEqual(trigger.conditions[0].threshold_high, 90)

    def test_to_dict(self):
        trigger = migrate_alert(self._make_agent())
        d = trigger.to_dict()
        self.assertEqual(d["name"], "TestAlert")
        self.assertIsInstance(d["conditions"], list)
        self.assertIsInstance(d["actions"], list)

    def test_disabled_agent(self):
        agent = self._make_agent(enabled=False)
        trigger = migrate_alert(agent)
        self.assertFalse(trigger.enabled)


class TestMigrateAllAlerts(unittest.TestCase):

    def test_skip_no_conditions(self):
        agents = [OACAgentDefinition(name="NoConditions")]
        result = migrate_all_alerts(agents)
        self.assertEqual(len(result.triggers), 0)
        self.assertEqual(len(result.skipped), 1)

    def test_multiple_agents(self):
        agents = [
            OACAgentDefinition(
                name=f"Alert{i}",
                conditions=[OACAlertCondition(measure="M", operator="gt", threshold=i)],
            )
            for i in range(5)
        ]
        result = migrate_all_alerts(agents)
        self.assertEqual(len(result.triggers), 5)

    def test_mixed_valid_invalid(self):
        agents = [
            OACAgentDefinition(name="Valid", conditions=[OACAlertCondition(measure="X", operator="gt", threshold=1)]),
            OACAgentDefinition(name="Empty"),
        ]
        result = migrate_all_alerts(agents)
        self.assertEqual(len(result.triggers), 1)
        self.assertEqual(len(result.skipped), 1)


if __name__ == "__main__":
    unittest.main()
