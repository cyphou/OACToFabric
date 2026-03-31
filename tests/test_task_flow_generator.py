"""Tests for task_flow_generator — OAC actions → Fabric Task Flows."""

from __future__ import annotations

import json
import unittest

from src.agents.report.task_flow_generator import (
    OACActionLink,
    TaskFlowDefinition,
    TaskFlowStep,
    generate_all_task_flows,
    generate_task_flow,
    map_action_to_step,
)


class TestMapActionToStep(unittest.TestCase):

    def test_navigate_action(self):
        action = OACActionLink(name="Go", action_type="navigate", target="/reports/sales")
        step = map_action_to_step(action, 0)
        self.assertEqual(step.step_type, "OpenReport")
        self.assertEqual(step.target_artifact, "/reports/sales")
        self.assertEqual(step.step_id, "step_000")

    def test_drilldown_action(self):
        action = OACActionLink(name="Drill", action_type="drillDown", target="DetailPage")
        step = map_action_to_step(action, 1)
        self.assertEqual(step.step_type, "NavigateToPage")

    def test_url_action(self):
        action = OACActionLink(name="Link", action_type="url", target="https://example.com")
        step = map_action_to_step(action, 0)
        self.assertEqual(step.step_type, "OpenUrl")

    def test_dependency_chaining(self):
        action = OACActionLink(name="S2", action_type="navigate", target="p2")
        step = map_action_to_step(action, 1, previous_step_id="step_000")
        self.assertIn("step_000", step.depends_on)

    def test_source_column_in_params(self):
        action = OACActionLink(name="A", action_type="navigate", target="T", source_column="Region")
        step = map_action_to_step(action, 0)
        self.assertEqual(step.parameters["sourceColumn"], "Region")


class TestGenerateTaskFlow(unittest.TestCase):

    def test_basic_flow(self):
        actions = [
            OACActionLink(name="Step1", action_type="navigate", target="P1"),
            OACActionLink(name="Step2", action_type="drillThrough", target="P2"),
        ]
        tf = generate_task_flow("MyFlow", actions)
        self.assertEqual(tf.name, "MyFlow")
        self.assertEqual(len(tf.steps), 2)
        self.assertEqual(tf.steps[1].depends_on, ["step_000"])

    def test_to_dict(self):
        tf = TaskFlowDefinition(
            name="F1",
            steps=[TaskFlowStep(step_id="s1", step_type="OpenReport")],
        )
        d = tf.to_dict()
        self.assertEqual(d["displayName"], "F1")
        self.assertEqual(d["entryPoint"], "s1")

    def test_to_json(self):
        tf = TaskFlowDefinition(name="F2", steps=[])
        j = tf.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["displayName"], "F2")


class TestGenerateAllTaskFlows(unittest.TestCase):

    def test_multiple_groups(self):
        groups = {
            "Analysis1": [OACActionLink(name="A", action_type="navigate", target="T")],
            "Analysis2": [OACActionLink(name="B", action_type="url", target="http://x")],
        }
        result = generate_all_task_flows(groups)
        self.assertEqual(len(result.task_flows), 2)

    def test_empty_group_skipped(self):
        result = generate_all_task_flows({"Empty": []})
        self.assertEqual(len(result.task_flows), 0)

    def test_unmapped_tracked(self):
        groups = {
            "A": [OACActionLink(name="X", action_type="unknownType", target="T")],
        }
        result = generate_all_task_flows(groups)
        self.assertGreater(len(result.unmapped_actions), 0)


if __name__ == "__main__":
    unittest.main()
