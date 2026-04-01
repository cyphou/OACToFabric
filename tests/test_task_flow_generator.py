"""Tests for task_flow_generator — OAC actions → Fabric Task Flows."""

from __future__ import annotations

import json
import unittest

from src.agents.report.task_flow_generator import (
    OACActionLink,
    TaskFlowDefinition,
    TaskFlowStep,
    WriteBackDefinition,
    generate_all_task_flows,
    generate_task_flow,
    generate_writeback_step,
    generate_writeback_task_flow,
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


class TestWriteBackActions(unittest.TestCase):
    """Test write-back / submit / setValue action types map correctly."""

    def test_writeback_action_type(self):
        action = OACActionLink(name="Save", action_type="writeBack", target="plan_table")
        step = map_action_to_step(action, 0)
        self.assertEqual(step.step_type, "InvokeUserDataFunction")

    def test_submitdata_action_type(self):
        action = OACActionLink(name="Submit", action_type="submitData", target="budget")
        step = map_action_to_step(action, 0)
        self.assertEqual(step.step_type, "InvokeUserDataFunction")

    def test_setvalue_action_type(self):
        action = OACActionLink(name="Set", action_type="setValue", target="plan")
        step = map_action_to_step(action, 0)
        self.assertEqual(step.step_type, "InvokeUserDataFunction")


class TestWriteBackDefinition(unittest.TestCase):
    """Test WriteBackDefinition SQL generation and UDF stubs."""

    def _make_wb(self) -> WriteBackDefinition:
        return WriteBackDefinition(
            name="budget_update",
            target_table="fact_plan",
            key_columns=["time_key", "entity_key", "account_key"],
            value_column="value",
            lakehouse_name="PlanningLakehouse",
        )

    def test_udf_sql(self):
        sql = self._make_wb().to_udf_sql()
        self.assertIn("UPDATE fact_plan", sql)
        self.assertIn("SET value = @NewValue", sql)
        self.assertIn("time_key = @time_key", sql)
        self.assertIn("entity_key = @entity_key", sql)
        self.assertIn("account_key = @account_key", sql)

    def test_udf_stub(self):
        stub = self._make_wb().to_udf_stub()
        self.assertEqual(stub["displayName"], "udf_budget_update")
        self.assertEqual(stub["lakehouse"], "PlanningLakehouse")
        self.assertEqual(len(stub["parameters"]), 4)  # 3 keys + NewValue
        self.assertEqual(stub["parameters"][-1]["type"], "decimal")

    def test_udf_stub_has_sql(self):
        stub = self._make_wb().to_udf_stub()
        self.assertIn("UPDATE", stub["sql"])


class TestGenerateWritebackStep(unittest.TestCase):

    def test_step_type_is_invoke(self):
        wb = WriteBackDefinition(
            name="wb1", target_table="t", key_columns=["k1"], lakehouse_name="LH",
        )
        step = generate_writeback_step(wb, 0)
        self.assertEqual(step.step_type, "InvokeUserDataFunction")
        self.assertEqual(step.parameters["functionName"], "udf_wb1")
        self.assertEqual(step.parameters["targetTable"], "t")

    def test_dependency_chaining(self):
        wb = WriteBackDefinition(name="wb2", target_table="t", key_columns=["k"])
        step = generate_writeback_step(wb, 1, previous_step_id="step_000")
        self.assertIn("step_000", step.depends_on)


class TestGenerateWritebackTaskFlow(unittest.TestCase):

    def test_multi_target(self):
        wbs = [
            WriteBackDefinition(name="rev", target_table="fact_revenue", key_columns=["period"]),
            WriteBackDefinition(name="cost", target_table="fact_cost", key_columns=["period"]),
        ]
        tf = generate_writeback_task_flow("PlanSubmit", wbs)
        self.assertEqual(tf.name, "PlanSubmit")
        self.assertEqual(len(tf.steps), 2)
        self.assertEqual(tf.steps[0].step_type, "InvokeUserDataFunction")
        self.assertEqual(tf.steps[1].depends_on, ["step_000"])

    def test_to_json_roundtrip(self):
        wbs = [WriteBackDefinition(name="x", target_table="t", key_columns=["k"])]
        tf = generate_writeback_task_flow("WB", wbs)
        parsed = json.loads(tf.to_json())
        self.assertEqual(parsed["displayName"], "WB")
        self.assertEqual(len(parsed["steps"]), 1)


if __name__ == "__main__":
    unittest.main()
