"""Tests for Phase 49 — Production Hardening & Report Fidelity.

Covers all 22 new features / enhancements:
  1. M:N bridge table generator
  2. Hierarchy-based dynamic RLS
  3. Drill-through wiring
  4. What-If parameters
  5. Theme migration
  6. Display folder intelligence
  7. Cascading slicer DAX
  8. KPI → PBI Goals
  9. Tooltip pages
 10. Environment parameterization
 11. DQ profiling template
 12. Visual z-order / overlap detection
 13. Dead letter queue
 14. Approval gates
 15. Mobile layout generation
 16. Auto-pagination enhancement
 17. Auto-refresh config
 18. Schema drift detection
 19. Multi-culture TMDL
 20. Copilot annotations
 21. Fabric Shortcuts
 22. Oracle synonym → Fabric view
"""

from __future__ import annotations

import json
import unittest
from dataclasses import dataclass, field

# ── Item 1: Bridge table generator ──────────────────────────────────────

from src.agents.semantic.bridge_table_generator import (
    BridgeGenerationResult,
    BridgeTableSpec,
    ManyToManyJoin,
    detect_many_to_many,
    generate_bridge_ddl,
    generate_bridge_m_expression,
    generate_bridge_relationships,
    generate_bridge_tables,
    generate_bridge_tmdl,
    _bridge_table_name,
)


class TestBridgeTableGenerator(unittest.TestCase):
    """Item 1: M:N bridge table generator."""

    def _make_join(self, lt="Orders", rt="Products", card="many-to-many"):
        return {
            "left_table": lt,
            "left_column": "OrderID",
            "right_table": rt,
            "right_column": "ProductID",
            "cardinality": card,
        }

    def test_detect_many_to_many(self):
        joins = [
            self._make_join(card="many-to-many"),
            self._make_join(lt="A", rt="B", card="one-to-many"),
        ]
        results = detect_many_to_many(joins)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], ManyToManyJoin)
        self.assertEqual(results[0].left_table, "Orders")

    def test_detect_mn_variant_cardinalities(self):
        for card in ("M:N", "N:M", "many-to-many"):
            joins = [self._make_join(card=card)]
            self.assertEqual(len(detect_many_to_many(joins)), 1, f"Failed for {card}")

    def test_no_mn_detected(self):
        joins = [self._make_join(card="one-to-many")]
        self.assertEqual(len(detect_many_to_many(joins)), 0)

    def test_generate_bridge_ddl(self):
        mn = ManyToManyJoin(
            left_table="Orders",
            left_column="OrderID",
            right_table="Products",
            right_column="ProductID",
        )
        ddl = generate_bridge_ddl(mn)
        self.assertIn("OrderID", ddl)
        self.assertIn("ProductID", ddl)

    def test_generate_bridge_tmdl(self):
        mn = ManyToManyJoin(
            left_table="A",
            left_column="AKey",
            right_table="B",
            right_column="BKey",
        )
        tmdl = generate_bridge_tmdl(mn)
        self.assertIn("table Bridge_A_B", tmdl)
        self.assertIn("AKey", tmdl)
        self.assertIn("BKey", tmdl)

    def test_generate_bridge_relationships(self):
        mn = ManyToManyJoin(
            left_table="A",
            left_column="AKey",
            right_table="B",
            right_column="BKey",
        )
        rels = generate_bridge_relationships(mn)
        # Returns a string with 2 relationship blocks
        self.assertIn("relationship", rels)

    def test_generate_bridge_m_expression(self):
        mn = ManyToManyJoin(
            left_table="Orders",
            left_column="OID",
            right_table="Products",
            right_column="PID",
        )
        m = generate_bridge_m_expression(mn)
        self.assertIn("Orders", m)
        self.assertIn("Products", m)

    def test_generate_bridge_tables_full(self):
        joins = [self._make_join()]
        result = generate_bridge_tables(joins)
        self.assertIsInstance(result, BridgeGenerationResult)
        self.assertEqual(result.count, 1)

    def test_generate_bridge_tables_empty(self):
        result = generate_bridge_tables([])
        self.assertEqual(result.count, 0)


# ── Item 2: Hierarchy-based dynamic RLS ─────────────────────────────────

from src.agents.security.rls_converter import (
    detect_hierarchy_columns,
    generate_hierarchy_rls,
    generate_hierarchy_rls_dax,
    generate_hierarchy_lookup_ddl,
    HierarchyRLSSpec,
)


class TestHierarchyRLS(unittest.TestCase):
    """Item 2: Hierarchy-based dynamic RLS."""

    def test_generate_hierarchy_rls_dax(self):
        dax = generate_hierarchy_rls_dax(
            table_name="Org",
            key_column="EmployeeKey",
            hierarchy_column="Path_EmployeeKey",
            parent_column="ManagerKey",
        )
        self.assertIn("PATH", dax)
        self.assertIn("PATHCONTAINS", dax)
        self.assertIn("USERPRINCIPALNAME()", dax)
        self.assertIn("Org", dax)

    def test_detect_hierarchy_columns_found(self):
        table_meta = {
            "columns": [
                {"name": "employee_id"},
                {"name": "manager_id"},
                {"name": "Name"},
            ],
        }
        result = detect_hierarchy_columns(table_meta)
        self.assertIsNotNone(result)

    def test_detect_hierarchy_columns_not_found(self):
        table_meta = {"columns": [{"name": "Revenue"}, {"name": "Region"}]}
        result = detect_hierarchy_columns(table_meta)
        self.assertIsNone(result)

    def test_generate_hierarchy_rls_full(self):
        result = generate_hierarchy_rls(
            role_name="OrgRLS",
            table_name="Employees",
            key_column="employee_id",
            parent_column="manager_id",
        )
        self.assertIsInstance(result, HierarchyRLSSpec)
        self.assertEqual(result.role_name, "OrgRLS")
        self.assertIn("PATH", result.dax_filter)

    def test_generate_hierarchy_rls_dax_content(self):
        result = generate_hierarchy_rls(
            role_name="TestRLS",
            table_name="Org",
            key_column="id",
            parent_column="parent_id",
        )
        self.assertIn("PATHCONTAINS", result.dax_filter)
        self.assertTrue(len(result.warnings) > 0)

    def test_generate_hierarchy_lookup_ddl(self):
        ddl = generate_hierarchy_lookup_ddl("SecurityHierarchy")
        self.assertIn("SecurityHierarchy", ddl)
        self.assertIn("UserPrincipal", ddl)


# ── Item 3: Drill-through wiring ────────────────────────────────────────

from src.agents.report.pbir_generator import (
    generate_drillthrough_page,
    wire_drillthrough,
)


class TestDrillthrough(unittest.TestCase):
    """Item 3: Drill-through wiring."""

    def test_wire_drillthrough(self):
        visual_json = {"config": {"singleVisual": {"vcObjects": {}}}}
        result = wire_drillthrough(visual_json, "DetailPage", ["Product", "Region"])
        self.assertIn("drillthrough", result["config"]["singleVisual"]["vcObjects"])

    def test_wire_drillthrough_creates_vcobjects(self):
        visual_json = {"config": {"singleVisual": {}}}
        result = wire_drillthrough(visual_json, "Page2", ["ID"])
        self.assertIn("vcObjects", result["config"]["singleVisual"])

    def test_generate_drillthrough_page(self):
        page = generate_drillthrough_page(
            "Detail", "Detail Page",
            [{"table": "Orders", "column": "OrderID"}],
        )
        self.assertEqual(page["name"], "Detail")
        self.assertEqual(page["displayName"], "Detail Page")
        config = json.loads(page["config"])
        self.assertTrue(config["isDrillthrough"])


# ── Item 4: What-If parameters ──────────────────────────────────────────

from src.agents.report.pbir_generator import (
    generate_whatif_slicer,
    generate_whatif_tmdl,
)


class TestWhatIfParameters(unittest.TestCase):
    """Item 4: What-If parameters."""

    def test_generate_whatif_slicer(self):
        visual = generate_whatif_slicer("Discount", 0, 50, 5, 10)
        self.assertIn("Discount", str(visual))
        self.assertIn("whatIfParameter", str(visual.get("metadata", {})))

    def test_generate_whatif_tmdl(self):
        tmdl = generate_whatif_tmdl("Markup", 0, 100, 1, 25)
        self.assertIn("Markup", tmdl)
        self.assertIn("GENERATESERIES", tmdl)
        self.assertIn("SELECTEDVALUE", tmdl)
        self.assertIn("measure", tmdl)

    def test_whatif_defaults(self):
        tmdl = generate_whatif_tmdl("Rate", 1, 10, 0.5, 5)
        self.assertIn("1", tmdl)
        self.assertIn("10", tmdl)


# ── Item 5: Theme migration ─────────────────────────────────────────────

from src.agents.report.theme_converter import (
    OACTheme,
    PBITheme,
    convert_theme,
    extract_oac_theme,
    generate_pbi_theme,
)


class TestThemeConverter(unittest.TestCase):
    """Item 5: Theme migration."""

    def test_extract_oac_theme(self):
        meta = {
            "name": "Corporate",
            "primaryColor": "#336699",
            "secondaryColor": "#66CCFF",
            "backgroundColor": "#FFFFFF",
            "foregroundColor": "#333333",
            "fontFamily": "Arial",
        }
        theme = extract_oac_theme(meta)
        self.assertEqual(theme.name, "Corporate")
        self.assertIn("#336699", theme.colors)

    def test_convert_theme_pads_colors(self):
        oac = OACTheme(name="Test", colors=["#FF0000", "#00FF00"])
        pbi = convert_theme(oac)
        self.assertIsInstance(pbi, PBITheme)
        self.assertEqual(len(pbi.data_colors), 12)
        self.assertEqual(pbi.data_colors[0], "#FF0000")

    def test_generate_pbi_theme_json(self):
        meta = {"name": "Test", "primaryColor": "rgb(255,0,0)"}
        result, warnings = generate_pbi_theme(meta)
        parsed = json.loads(result)
        self.assertIn("dataColors", parsed)
        self.assertIn("name", parsed)

    def test_empty_theme_defaults(self):
        result, warnings = generate_pbi_theme({})
        parsed = json.loads(result)
        self.assertEqual(len(parsed["dataColors"]), 12)


# ── Item 6: Display folder intelligence ─────────────────────────────────

from src.agents.semantic.tmdl_generator import _build_display_folder_map
from src.agents.semantic.rpd_model_parser import (
    ColumnKind,
    LogicalColumn,
    LogicalTable,
    SemanticModelIR,
    SubjectArea,
)


class TestDisplayFolderIntelligence(unittest.TestCase):
    """Item 6: Display folder intelligence from subject areas."""

    def _make_ir(self):
        cols = [
            LogicalColumn(name="Revenue", kind=ColumnKind.MEASURE, expression="SUM(Amount)"),
            LogicalColumn(name="Cost", kind=ColumnKind.MEASURE, expression="SUM(Cost)", display_folder="Finance"),
        ]
        tbl = LogicalTable(name="Sales", columns=cols)
        sa = SubjectArea(name="Financial", tables=["Sales"], columns={"Sales": ["Revenue"]})
        return SemanticModelIR(model_name="Test", tables=[tbl], subject_areas=[sa])

    def test_build_folder_map_from_sa(self):
        ir = self._make_ir()
        folder_map = _build_display_folder_map(ir)
        self.assertEqual(folder_map["Sales"]["Revenue"], "Financial")

    def test_column_display_folder_takes_precedence(self):
        ir = self._make_ir()
        folder_map = _build_display_folder_map(ir)
        # Cost has explicit display_folder="Finance" on the column
        self.assertEqual(folder_map["Sales"]["Cost"], "Finance")


# ── Item 7: Cascading slicer DAX ────────────────────────────────────────

from src.agents.report.prompt_converter import (
    SlicerConfig,
    build_cascading_chain,
    generate_cascading_filter_dax,
)


class TestCascadingSlicerDAX(unittest.TestCase):
    """Item 7: Cascading slicer DAX generation."""

    def test_generate_cascading_filter_dax(self):
        dax = generate_cascading_filter_dax("Dim_Country", "Country", "Dim_City", "City")
        self.assertIn("CALCULATE", dax)
        self.assertIn("DISTINCTCOUNT", dax)
        self.assertIn("VALUES", dax)
        self.assertIn("Dim_Country", dax)

    def test_build_cascading_chain(self):
        parent = SlicerConfig(
            visual_id="s1",
            title="Country",
            table_name="Dim_Country",
            column_name="Country",
        )
        child = SlicerConfig(
            visual_id="s2",
            title="City",
            table_name="Dim_City",
            column_name="City",
            parent_slicer_id="Country",
        )
        chain = build_cascading_chain([parent, child])
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["parent"], "Country")
        self.assertEqual(chain[0]["child"], "City")
        self.assertIn("CALCULATE", chain[0]["dax_filter"])

    def test_cascading_chain_no_parent(self):
        child = SlicerConfig(
            visual_id="s2",
            title="City",
            table_name="Dim",
            column_name="City",
            parent_slicer_id="NonExistent",
        )
        chain = build_cascading_chain([child])
        self.assertEqual(len(chain), 0)

    def test_cascading_chain_empty(self):
        chain = build_cascading_chain([])
        self.assertEqual(len(chain), 0)


# ── Item 8: KPI → PBI Goals ─────────────────────────────────────────────

from src.agents.report.goals_generator import (
    OACKpi,
    PBIGoal,
    PBIScorecard,
    convert_kpi_to_goal,
    generate_scorecard,
    parse_oac_kpi,
)


class TestGoalsGenerator(unittest.TestCase):
    """Item 8: KPI → PBI Goals."""

    def test_parse_oac_kpi(self):
        meta = {
            "id": "kpi-1",
            "name": "Revenue Target",
            "targetValue": 1000000,
            "actualExpression": "SUM(Revenue)",
        }
        kpi = parse_oac_kpi(meta)
        self.assertEqual(kpi.name, "Revenue Target")
        self.assertEqual(kpi.target_value, 1000000)

    def test_convert_kpi_to_goal(self):
        kpi = OACKpi(id="k1", name="Rev", target_value=500, actual_expression="SUM(Rev)")
        goal = convert_kpi_to_goal(kpi)
        self.assertIsInstance(goal, PBIGoal)
        self.assertEqual(goal.name, "Rev")

    def test_generate_scorecard(self):
        kpi_dicts = [
            {"id": "1", "name": "KPI1", "targetValue": 100},
            {"id": "2", "name": "KPI2", "targetValue": 200},
        ]
        sc = generate_scorecard(kpi_dicts, "Test Scorecard")
        self.assertEqual(sc.name, "Test Scorecard")
        self.assertEqual(sc.count, 2)
        j = sc.to_json()
        parsed = json.loads(j)
        self.assertIn("goals", parsed)

    def test_scorecard_empty(self):
        sc = generate_scorecard([], "Empty")
        self.assertEqual(sc.count, 0)


# ── Item 9: Tooltip pages ───────────────────────────────────────────────

from src.agents.report.pbir_generator import (
    generate_tooltip_page,
    wire_tooltip_to_visual,
)


class TestTooltipPages(unittest.TestCase):
    """Item 9: Tooltip pages."""

    def test_generate_tooltip_page(self):
        page = generate_tooltip_page("TP1", "Detail Tooltip")
        self.assertEqual(page["name"], "TP1")
        config = json.loads(page["config"])
        self.assertTrue(config["tooltip"]["enabled"])
        self.assertEqual(config["visibility"], 1)

    def test_wire_tooltip_to_visual(self):
        visual = {"config": {"singleVisual": {"vcObjects": {}}}}
        result = wire_tooltip_to_visual(visual, "TP1")
        self.assertIn("tooltip", result["config"]["singleVisual"]["vcObjects"])


# ── Item 10: Environment parameterization ────────────────────────────────

from src.agents.etl.fabric_pipeline_generator import (
    DEFAULT_ENVIRONMENTS,
    EnvironmentConfig,
    FabricPipeline,
    generate_env_config_json,
    parameterize_pipeline,
)


class TestEnvironmentParameterization(unittest.TestCase):
    """Item 10: Environment parameterization."""

    def _make_pipeline(self):
        return FabricPipeline(name="TestPipeline", description="Test")

    def test_parameterize_pipeline_dev(self):
        p = parameterize_pipeline(self._make_pipeline(), "dev")
        self.assertIn("dev", p.name)

    def test_parameterize_pipeline_prod(self):
        p = parameterize_pipeline(self._make_pipeline(), "prod")
        self.assertIn("prod", p.name)

    def test_parameterize_with_overrides(self):
        p = parameterize_pipeline(
            self._make_pipeline(), "dev",
            env_overrides={"workspace_id": "custom-ws"},
        )
        self.assertIn("dev", p.description)

    def test_generate_env_config_json(self):
        j = generate_env_config_json()
        parsed = json.loads(j)
        self.assertIn("environments", parsed)
        self.assertIn("dev", parsed["environments"])
        self.assertIn("prod", parsed["environments"])

    def test_default_environments_keys(self):
        self.assertIn("dev", DEFAULT_ENVIRONMENTS)
        self.assertIn("test", DEFAULT_ENVIRONMENTS)
        self.assertIn("prod", DEFAULT_ENVIRONMENTS)


# ── Item 11: DQ profiling template ──────────────────────────────────────

from src.agents.etl.dq_profiler import (
    DQCheck,
    DQNotebook,
    DQProfile,
    generate_dq_notebook,
)


class TestDQProfiler(unittest.TestCase):
    """Item 11: DQ profiling template."""

    def _inventory(self):
        return [
            {
                "name": "Sales",
                "columns": [
                    {"name": "Amount", "data_type": "DECIMAL"},
                    {"name": "Region", "data_type": "VARCHAR"},
                ],
            },
            {
                "name": "Products",
                "columns": [
                    {"name": "Name", "data_type": "VARCHAR"},
                ],
            },
        ]

    def test_generate_dq_notebook(self):
        nb = generate_dq_notebook(self._inventory())
        self.assertIsInstance(nb, DQNotebook)
        self.assertTrue(nb.cell_count >= 2)
        self.assertTrue(len(nb.cells) > 0)

    def test_notebook_json_valid(self):
        nb = generate_dq_notebook(self._inventory())
        j = nb.to_notebook_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["nbformat"], 4)
        self.assertTrue(len(parsed["cells"]) > 0)

    def test_empty_inventory(self):
        nb = generate_dq_notebook([])
        # Header + summary cell, no per-table cells
        self.assertEqual(nb.cell_count, 2)


# ── Item 12: Z-order / overlap detection ─────────────────────────────────

from src.agents.report.layout_engine import (
    VisualPosition,
    assign_z_order,
    detect_overlaps,
    generate_mobile_layout,
)


class TestZOrderOverlap(unittest.TestCase):
    """Item 12: Visual z-order / overlap detection."""

    def _make_visuals(self):
        return [
            VisualPosition(x=0, y=0, width=200, height=100, visual_name="large"),
            VisualPosition(x=10, y=10, width=50, height=50, visual_name="small"),
        ]

    def test_assign_z_order(self):
        visuals = self._make_visuals()
        result = assign_z_order(visuals)
        # Larger visual should have lower z_order (renders below)
        z_map = {v.visual_name: v.z_order for v in result}
        self.assertLess(z_map["large"], z_map["small"])

    def test_detect_overlaps(self):
        visuals = self._make_visuals()
        overlaps = detect_overlaps(visuals)
        self.assertEqual(len(overlaps), 1)
        self.assertIn("large", overlaps[0])
        self.assertIn("small", overlaps[0])

    def test_no_overlaps(self):
        visuals = [
            VisualPosition(x=0, y=0, width=100, height=100, visual_name="a"),
            VisualPosition(x=200, y=200, width=100, height=100, visual_name="b"),
        ]
        self.assertEqual(len(detect_overlaps(visuals)), 0)


# ── Item 13: Dead letter queue ──────────────────────────────────────────

from src.agents.orchestrator.dag_engine import (
    DeadLetterEntry,
    DeadLetterQueue,
    ExecutionDAG,
    NodeStatus,
)


class TestDeadLetterQueue(unittest.TestCase):
    """Item 13: Dead letter queue."""

    def _make_dag(self):
        dag = ExecutionDAG()
        dag.add_node("A", "Agent A")
        dag.add_node("B", "Agent B")
        dag.add_node("C", "Agent C")
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        return dag

    def test_dlq_add(self):
        dag = self._make_dag()
        dlq = DeadLetterQueue()
        entry = dlq.add(dag, "A", "Connection timeout")
        self.assertEqual(entry.node_id, "A")
        self.assertEqual(entry.error, "Connection timeout")
        self.assertEqual(dlq.count, 1)

    def test_dlq_blocks_dependents(self):
        dag = self._make_dag()
        dlq = DeadLetterQueue()
        entry = dlq.add(dag, "A", "Failed")
        # B and C should be blocked
        self.assertIn("B", entry.blocked_dependents)
        self.assertIn("C", entry.blocked_dependents)
        self.assertEqual(dag.get_node("B").status, NodeStatus.BLOCKED)
        self.assertEqual(dag.get_node("C").status, NodeStatus.BLOCKED)

    def test_dlq_to_json(self):
        dag = self._make_dag()
        dlq = DeadLetterQueue()
        dlq.add(dag, "A", "Error")
        j = dlq.to_json()
        parsed = json.loads(j)
        self.assertIn("dead_letter_queue", parsed)
        self.assertEqual(len(parsed["dead_letter_queue"]), 1)

    def test_dlq_summary_empty(self):
        dlq = DeadLetterQueue()
        self.assertIn("empty", dlq.summary())

    def test_dlq_summary_has_entries(self):
        dag = self._make_dag()
        dlq = DeadLetterQueue()
        dlq.add(dag, "A", "Error")
        self.assertIn("A", dlq.summary())


# ── Item 14: Approval gates ─────────────────────────────────────────────

from src.agents.orchestrator.wave_planner import (
    ApprovalGate,
    ApprovalStatus,
    GatedWavePlan,
    MigrationWave,
    WavePlan,
    add_approval_gates,
)


class TestApprovalGates(unittest.TestCase):
    """Item 14: Approval gates."""

    def _make_plan(self):
        return WavePlan(waves=[
            MigrationWave(id=1, name="Wave 1"),
            MigrationWave(id=2, name="Wave 2"),
            MigrationWave(id=3, name="Wave 3"),
        ])

    def test_add_approval_gates_default(self):
        plan = self._make_plan()
        gated = add_approval_gates(plan)
        self.assertIsInstance(gated, GatedWavePlan)
        # Should have gates before wave 2 and 3
        self.assertEqual(len(gated.gates), 2)

    def test_can_proceed_no_gate(self):
        plan = self._make_plan()
        gated = add_approval_gates(plan)
        # Wave 1 has no gate → can proceed
        self.assertTrue(gated.can_proceed(1))

    def test_cannot_proceed_pending_gate(self):
        plan = self._make_plan()
        gated = add_approval_gates(plan)
        # Wave 2 has pending gate
        self.assertFalse(gated.can_proceed(2))

    def test_can_proceed_after_approval(self):
        plan = self._make_plan()
        gated = add_approval_gates(plan)
        gated.gates[0].approve("admin", "Looks good")
        self.assertTrue(gated.can_proceed(2))

    def test_reject_gate(self):
        plan = self._make_plan()
        gated = add_approval_gates(plan)
        gated.gates[0].reject("admin", "Not ready")
        self.assertEqual(gated.gates[0].status, ApprovalStatus.REJECTED)

    def test_pending_gates(self):
        plan = self._make_plan()
        gated = add_approval_gates(plan)
        self.assertEqual(len(gated.pending_gates()), 2)
        gated.gates[0].approve("admin")
        self.assertEqual(len(gated.pending_gates()), 1)

    def test_custom_gate_waves(self):
        plan = self._make_plan()
        gated = add_approval_gates(plan, gate_before_waves=[3])
        self.assertEqual(len(gated.gates), 1)
        self.assertEqual(gated.gates[0].wave_id, 3)


# ── Item 15: Mobile layout ──────────────────────────────────────────────


class TestMobileLayout(unittest.TestCase):
    """Item 15: Mobile layout generation."""

    def test_generate_mobile_layout(self):
        visuals = [
            VisualPosition(x=0, y=0, width=600, height=400, visual_name="chart1"),
            VisualPosition(x=600, y=0, width=600, height=200, visual_name="chart2"),
        ]
        mobile = generate_mobile_layout(visuals)
        self.assertEqual(len(mobile), 2)
        # All visuals should be stacked vertically
        self.assertTrue(all(v.width == 352 for v in mobile))  # PHONE_WIDTH - 2*PADDING

    def test_mobile_max_visuals(self):
        visuals = [
            VisualPosition(x=0, y=i * 100, width=100, height=100, visual_name=f"v{i}")
            for i in range(20)
        ]
        mobile = generate_mobile_layout(visuals, max_visuals=5)
        self.assertEqual(len(mobile), 5)

    def test_mobile_priority_by_area(self):
        visuals = [
            VisualPosition(x=0, y=0, width=50, height=50, visual_name="small"),
            VisualPosition(x=0, y=0, width=500, height=400, visual_name="large"),
        ]
        mobile = generate_mobile_layout(visuals, max_visuals=1)
        # Largest visual should be shown first
        self.assertEqual(mobile[0].visual_name, "large")


# ── Item 16: Auto-pagination enhancement ─────────────────────────────────

from src.agents.report.layout_engine import paginate


class TestAutoPagination(unittest.TestCase):
    """Item 16: Auto-pagination enhancement."""

    def test_paginate_basic(self):
        visuals = [
            VisualPosition(x=0, y=i * 200, width=200, height=150, visual_name=f"v{i}")
            for i in range(5)
        ]
        result = paginate(visuals, max_per_page=3, canvas_height=720)
        pages = {v.page_index for v in result}
        self.assertTrue(len(pages) >= 2)

    def test_paginate_empty(self):
        result = paginate([], max_per_page=20, canvas_height=720)
        self.assertEqual(len(result), 0)

    def test_paginate_overflow(self):
        visuals = [
            VisualPosition(x=0, y=0, width=200, height=800, visual_name="tall"),
            VisualPosition(x=0, y=800, width=200, height=100, visual_name="normal"),
        ]
        result = paginate(visuals, max_per_page=20, canvas_height=720)
        # Second visual overflows page so should be on a later page
        page_map = {v.visual_name: v.page_index for v in result}
        self.assertGreaterEqual(page_map["normal"], 1)


# ── Item 17: Auto-refresh config ─────────────────────────────────────────

from src.agents.report.pbir_generator import set_auto_refresh


class TestAutoRefresh(unittest.TestCase):
    """Item 17: Auto-refresh config."""

    def test_set_auto_refresh(self):
        report = {"config": {}}
        result = set_auto_refresh(report, interval_seconds=30)
        self.assertIn("autoRefresh", result["config"])
        self.assertTrue(result["config"]["autoRefresh"]["enabled"])

    def test_set_auto_refresh_disabled(self):
        report = {"config": {}}
        result = set_auto_refresh(report, interval_seconds=60, enabled=False)
        self.assertFalse(result["config"]["autoRefresh"]["enabled"])

    def test_set_auto_refresh_interval(self):
        report = {"config": {}}
        result = set_auto_refresh(report, interval_seconds=45)
        self.assertEqual(result["config"]["autoRefresh"]["intervalMs"], 45000)


# ── Item 18: Schema drift detection ─────────────────────────────────────

from src.agents.validation.schema_drift import (
    ColumnSnapshot,
    DriftItem,
    DriftReport,
    SchemaSnapshot,
    TableSnapshot,
    capture_snapshot,
    compare_snapshots,
)


class TestSchemaDrift(unittest.TestCase):
    """Item 18: Schema drift detection."""

    def _make_snapshot(self, tables=None):
        if tables is None:
            tables = [
                TableSnapshot(
                    table_name="Sales",
                    columns=[
                        ColumnSnapshot(name="Amount", data_type="DECIMAL"),
                        ColumnSnapshot(name="Region", data_type="VARCHAR"),
                    ],
                    row_count=1000,
                ),
            ]
        return SchemaSnapshot(snapshot_id="baseline", tables=tables)

    def test_capture_snapshot(self):
        inventory = [
            {
                "name": "Sales",
                "columns": [
                    {"name": "Amount", "data_type": "DECIMAL"},
                ],
                "row_count": 500,
            },
        ]
        snap = capture_snapshot(inventory, "v1")
        self.assertEqual(snap.snapshot_id, "v1")
        self.assertEqual(len(snap.tables), 1)

    def test_no_drift(self):
        baseline = self._make_snapshot()
        current = self._make_snapshot()
        report = compare_snapshots(baseline, current)
        self.assertEqual(len(report.drifts), 0)
        self.assertFalse(report.has_critical)

    def test_table_added(self):
        baseline = self._make_snapshot()
        current = self._make_snapshot()
        current.tables.append(
            TableSnapshot(table_name="NewTable", columns=[], row_count=0)
        )
        report = compare_snapshots(baseline, current)
        self.assertTrue(any(d.drift_type == "added_table" for d in report.drifts))

    def test_table_dropped(self):
        baseline = self._make_snapshot()
        current = SchemaSnapshot(snapshot_id="v2", tables=[])
        report = compare_snapshots(baseline, current)
        self.assertTrue(any(d.drift_type == "dropped_table" for d in report.drifts))
        self.assertTrue(report.has_critical)

    def test_column_type_changed(self):
        baseline = self._make_snapshot()
        current = self._make_snapshot()
        current.tables[0].columns[0] = ColumnSnapshot(
            name="Amount", data_type="INT"
        )
        report = compare_snapshots(baseline, current)
        self.assertTrue(any(d.drift_type == "type_change" for d in report.drifts))

    def test_snapshot_json_roundtrip(self):
        snap = self._make_snapshot()
        j = snap.to_json()
        loaded = SchemaSnapshot.from_json(j)
        self.assertEqual(loaded.snapshot_id, snap.snapshot_id)
        self.assertEqual(len(loaded.tables), len(snap.tables))


# ── Item 19: Multi-culture TMDL ──────────────────────────────────────────

from src.agents.semantic.tmdl_generator import (
    SUPPORTED_CULTURES,
    generate_all_cultures,
    generate_culture_tmdl,
)


class TestMultiCultureTMDL(unittest.TestCase):
    """Item 19: Multi-culture TMDL generation."""

    def test_generate_culture_tmdl(self):
        content = generate_culture_tmdl("fr-FR")
        self.assertIn("culture fr-FR", content)

    def test_generate_culture_with_translations(self):
        trans = {"Sales": {"Revenue": "Chiffre d'affaires"}}
        content = generate_culture_tmdl("fr-FR", trans)
        self.assertIn("Chiffre d'affaires", content)

    def test_generate_all_cultures(self):
        files = generate_all_cultures(["en-US", "fr-FR"])
        self.assertEqual(len(files), 2)
        for path in files:
            self.assertTrue(path.startswith("definition/cultures/"))

    def test_supported_cultures_count(self):
        self.assertEqual(len(SUPPORTED_CULTURES), 19)

    def test_all_cultures_default(self):
        files = generate_all_cultures()
        self.assertEqual(len(files), 19)


# ── Item 20: Copilot annotations ─────────────────────────────────────────

from src.agents.semantic.tmdl_generator import (
    _column_to_friendly_name,
    annotate_for_copilot,
)


class TestCopilotAnnotations(unittest.TestCase):
    """Item 20: Copilot annotations."""

    def _make_ir(self):
        cols = [
            LogicalColumn(name="order_date", kind=ColumnKind.DIRECT, data_type="DATE"),
            LogicalColumn(name="TotalRevenue", kind=ColumnKind.MEASURE, expression="SUM(Revenue)"),
        ]
        tbl = LogicalTable(name="Sales", columns=cols, description="Sales data")
        return SemanticModelIR(model_name="Test", tables=[tbl])

    def test_annotate_for_copilot(self):
        ir = self._make_ir()
        annotations = annotate_for_copilot(ir)
        self.assertIn("Sales", annotations)
        self.assertIn("Copilot_TableDescription", annotations["Sales"])

    def test_column_to_friendly_snake(self):
        self.assertEqual(_column_to_friendly_name("order_date"), "Order Date")

    def test_column_to_friendly_camel(self):
        result = _column_to_friendly_name("customerID")
        self.assertIn("Customer", result)
        self.assertIn("Id", result.title())

    def test_column_to_friendly_simple(self):
        self.assertEqual(_column_to_friendly_name("Name"), "Name")

    def test_copilot_measure_annotations(self):
        ir = self._make_ir()
        annotations = annotate_for_copilot(ir)
        self.assertIn("Copilot_MeasureDescription_TotalRevenue", annotations["Sales"])


# ── Item 21: Fabric Shortcuts ────────────────────────────────────────────

from src.agents.schema.ddl_generator import (
    generate_fabric_shortcut,
    generate_shortcut_script,
)


class TestFabricShortcuts(unittest.TestCase):
    """Item 21: Fabric Shortcuts."""

    def test_generate_fabric_shortcut(self):
        sc = generate_fabric_shortcut("Sales", "ws-123", "lh-456", "Sales")
        self.assertEqual(sc["name"], "Sales")
        self.assertEqual(sc["target"]["oneLake"]["workspaceId"], "ws-123")
        self.assertEqual(sc["target"]["oneLake"]["itemId"], "lh-456")
        self.assertIn("Tables/Sales", sc["target"]["oneLake"]["path"])

    def test_generate_shortcut_custom_path(self):
        sc = generate_fabric_shortcut("MySales", "ws", "lh", "Sales", target_path="Files/raw")
        self.assertEqual(sc["path"], "Files/raw")

    def test_generate_shortcut_script(self):
        shortcuts = [
            {"name": "Sales", "source_workspace_id": "w1", "source_lakehouse_id": "l1"},
            {"name": "Products", "source_workspace_id": "w2", "source_lakehouse_id": "l2"},
        ]
        script = generate_shortcut_script(shortcuts)
        parsed = json.loads(script)
        self.assertEqual(len(parsed), 2)


# ── Item 22: Oracle synonyms ─────────────────────────────────────────────

from src.agents.schema.ddl_generator import (
    generate_synonym_script,
    generate_synonym_view,
)
from src.agents.schema.type_mapper import TargetPlatform


class TestOracleSynonyms(unittest.TestCase):
    """Item 22: Oracle synonym → Fabric view."""

    def test_generate_synonym_view_lakehouse(self):
        ddl = generate_synonym_view("EMP_ALIAS", "EMPLOYEES", TargetPlatform.LAKEHOUSE)
        self.assertIn("CREATE OR REPLACE VIEW", ddl)
        self.assertIn("EMP_ALIAS", ddl)
        self.assertIn("EMPLOYEES", ddl)

    def test_generate_synonym_view_warehouse(self):
        ddl = generate_synonym_view("DEPT_ALIAS", "DEPARTMENTS", TargetPlatform.WAREHOUSE)
        self.assertIn("CREATE VIEW", ddl)
        self.assertIn("DEPT_ALIAS", ddl)

    def test_generate_synonym_script(self):
        synonyms = [
            {"synonym_name": "EMP", "target_table": "EMPLOYEES"},
            {"synonym_name": "DEPT", "target_table": "DEPARTMENTS"},
        ]
        script = generate_synonym_script(synonyms, TargetPlatform.LAKEHOUSE)
        self.assertIn("Oracle Synonym", script)
        self.assertEqual(script.count("CREATE OR REPLACE VIEW"), 2)


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
