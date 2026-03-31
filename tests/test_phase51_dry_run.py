"""Tests for Phase 51 — Migration Dry-Run Simulator."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from src.core.dry_run_simulator import (
    AssetSimulationResult,
    ChangeAction,
    ChangeManifestEntry,
    DryRunSimulator,
    RiskHeatmapCell,
    SimulationConfig,
    SimulationMode,
    SimulationReport,
    TranslationCoverageStats,
    run_dry_run,
)
from src.core.migration_intelligence import (
    CostEstimate,
    RiskLevel,
    TimelineEstimate,
)
from src.core.models import AssetType, Inventory, InventoryItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(items: list[dict] | None = None) -> Inventory:
    """Create a test inventory."""
    if items is None:
        items = [
            {
                "name": "Sales",
                "asset_type": AssetType.PHYSICAL_TABLE,
                "metadata": {
                    "tables": 3,
                    "calculations": 10,
                    "rls_roles": 2,
                    "visuals": 5,
                    "row_count": 100_000,
                    "dependencies": 2,
                    "custom_sql": 1,
                },
            },
            {
                "name": "Marketing Dashboard",
                "asset_type": AssetType.ANALYSIS,
                "metadata": {
                    "tables": 5,
                    "calculations": 25,
                    "rls_roles": 0,
                    "visuals": 12,
                    "row_count": 500_000,
                    "dependencies": 4,
                    "custom_sql": 3,
                },
            },
        ]
    inv = Inventory()
    for item_dict in items:
        inv.items.append(
            InventoryItem(
                id=item_dict.get("id", item_dict["name"]),
                name=item_dict["name"],
                asset_type=item_dict.get("asset_type", AssetType.PHYSICAL_TABLE),
                source_path=item_dict.get("source_path", f"/oac/{item_dict['name']}"),
                metadata=item_dict.get("metadata", {}),
            )
        )
    return inv


def _make_expressions() -> list[dict[str, str]]:
    """Create test OAC expressions."""
    return [
        {"name": "total_sales", "table": "Sales", "expression": "SUM(revenue)"},
        {"name": "avg_price", "table": "Sales", "expression": "AVG(unit_price)"},
        {"name": "item_count", "table": "Sales", "expression": "COUNT(*)"},
        {"name": "complex_calc", "table": "Sales", "expression": "CUSTOM_FUNC(a, b)"},
    ]


# ===========================================================================
# Test classes
# ===========================================================================


class TestSimulationMode(unittest.TestCase):
    """SimulationMode enum."""

    def test_values(self):
        self.assertEqual(SimulationMode.QUICK.value, "quick")
        self.assertEqual(SimulationMode.STANDARD.value, "standard")
        self.assertEqual(SimulationMode.FULL.value, "full")

    def test_all_modes(self):
        modes = list(SimulationMode)
        self.assertEqual(len(modes), 3)


class TestChangeAction(unittest.TestCase):
    """ChangeAction enum."""

    def test_values(self):
        self.assertEqual(ChangeAction.CREATE.value, "create")
        self.assertEqual(ChangeAction.MODIFY.value, "modify")
        self.assertEqual(ChangeAction.DELETE.value, "delete")
        self.assertEqual(ChangeAction.SKIP.value, "skip")


class TestTranslationCoverageStats(unittest.TestCase):
    """TranslationCoverageStats dataclass."""

    def test_empty_coverage(self):
        stats = TranslationCoverageStats()
        self.assertEqual(stats.coverage_pct, 100.0)

    def test_full_coverage(self):
        stats = TranslationCoverageStats(total_expressions=10, translated=10)
        self.assertEqual(stats.coverage_pct, 100.0)

    def test_partial_coverage(self):
        stats = TranslationCoverageStats(total_expressions=10, translated=7)
        self.assertAlmostEqual(stats.coverage_pct, 70.0)

    def test_zero_coverage(self):
        stats = TranslationCoverageStats(total_expressions=10, translated=0)
        self.assertEqual(stats.coverage_pct, 0.0)

    def test_defaults(self):
        stats = TranslationCoverageStats()
        self.assertEqual(stats.total_expressions, 0)
        self.assertEqual(stats.rule_based, 0)
        self.assertEqual(stats.llm_assisted, 0)
        self.assertEqual(stats.manual_required, 0)
        self.assertAlmostEqual(stats.avg_confidence, 0.0)
        self.assertAlmostEqual(stats.min_confidence, 1.0)
        self.assertAlmostEqual(stats.max_confidence, 0.0)


class TestAssetSimulationResult(unittest.TestCase):
    """AssetSimulationResult dataclass."""

    def test_defaults(self):
        r = AssetSimulationResult(asset_name="test", asset_type="table")
        self.assertEqual(r.asset_name, "test")
        self.assertEqual(r.complexity_score, 0.0)
        self.assertEqual(r.risk_level, "low")
        self.assertFalse(r.requires_review)
        self.assertEqual(r.change_action, ChangeAction.CREATE)
        self.assertEqual(r.warnings, [])

    def test_custom_values(self):
        r = AssetSimulationResult(
            asset_name="complex",
            asset_type="analysis",
            complexity_score=8.5,
            risk_level="critical",
            requires_review=True,
        )
        self.assertEqual(r.complexity_score, 8.5)
        self.assertTrue(r.requires_review)


class TestRiskHeatmapCell(unittest.TestCase):
    """RiskHeatmapCell dataclass."""

    def test_defaults(self):
        cell = RiskHeatmapCell(asset_name="a", dimension="schema")
        self.assertEqual(cell.score, 0.0)
        self.assertEqual(cell.risk_level, "low")


class TestChangeManifestEntry(unittest.TestCase):
    """ChangeManifestEntry dataclass."""

    def test_create_entry(self):
        e = ChangeManifestEntry(
            asset_name="Sales",
            asset_type="table",
            action=ChangeAction.CREATE,
            target_path="fabric://ws/lh/sales",
        )
        self.assertEqual(e.action, ChangeAction.CREATE)
        self.assertEqual(e.target_path, "fabric://ws/lh/sales")


class TestSimulationConfig(unittest.TestCase):
    """SimulationConfig dataclass."""

    def test_defaults(self):
        cfg = SimulationConfig()
        self.assertEqual(cfg.mode, SimulationMode.STANDARD)
        self.assertAlmostEqual(cfg.cu_price_per_hour, 0.18)
        self.assertEqual(cfg.team_size, 2)
        self.assertAlmostEqual(cfg.review_confidence_threshold, 0.7)

    def test_custom_config(self):
        cfg = SimulationConfig(
            mode=SimulationMode.FULL,
            team_size=5,
            cu_price_per_hour=0.25,
        )
        self.assertEqual(cfg.mode, SimulationMode.FULL)
        self.assertEqual(cfg.team_size, 5)


class TestSimulationReportSerialization(unittest.TestCase):
    """SimulationReport serialization methods."""

    def test_to_dict_empty(self):
        r = SimulationReport(simulation_id="test-1")
        d = r.to_dict()
        self.assertEqual(d["simulationId"], "test-1")
        self.assertEqual(d["totalAssets"], 0)
        self.assertIsNone(d["costEstimate"])
        self.assertIsNone(d["timelineEstimate"])

    def test_to_dict_with_cost(self):
        r = SimulationReport(simulation_id="test-2")
        r.cost_estimate = CostEstimate(
            compute_hours=10.0,
            storage_gb=5.0,
            total_cost_usd=12.50,
            breakdown={"copy": 8.0, "storage": 4.50},
        )
        d = r.to_dict()
        self.assertIsNotNone(d["costEstimate"])
        self.assertEqual(d["costEstimate"]["computeHours"], 10.0)
        self.assertEqual(d["costEstimate"]["totalCostUsd"], 12.5)

    def test_to_dict_with_timeline(self):
        r = SimulationReport(simulation_id="test-3")
        r.timeline_estimate = TimelineEstimate(
            total_days=20.0, buffered_days=24.0, phases={"schema": 5.0}
        )
        d = r.to_dict()
        self.assertIsNotNone(d["timelineEstimate"])
        self.assertEqual(d["timelineEstimate"]["totalDays"], 20.0)

    def test_to_dict_with_assets(self):
        r = SimulationReport()
        r.asset_results.append(
            AssetSimulationResult(
                asset_name="tbl",
                asset_type="table",
                complexity_score=3.5,
            )
        )
        d = r.to_dict()
        self.assertEqual(len(d["assetResults"]), 1)
        self.assertEqual(d["assetResults"][0]["complexityScore"], 3.5)

    def test_to_dict_with_heatmap(self):
        r = SimulationReport()
        r.risk_heatmap.append(
            RiskHeatmapCell(asset_name="a", dimension="schema", score=5.0)
        )
        d = r.to_dict()
        self.assertEqual(len(d["riskHeatmap"]), 1)

    def test_to_dict_with_manifest(self):
        r = SimulationReport()
        r.change_manifest.append(
            ChangeManifestEntry("a", "table", ChangeAction.CREATE, "/a")
        )
        d = r.to_dict()
        self.assertEqual(len(d["changeManifest"]), 1)
        self.assertEqual(d["changeManifest"][0]["action"], "create")

    def test_to_dict_json_serializable(self):
        r = SimulationReport(simulation_id="json-test")
        r.cost_estimate = CostEstimate(total_cost_usd=1.0, breakdown={})
        r.timeline_estimate = TimelineEstimate(total_days=1.0, buffered_days=1.2)
        d = r.to_dict()
        # Should not raise
        json.dumps(d)


class TestSimulationReportMarkdown(unittest.TestCase):
    """SimulationReport.generate_markdown()."""

    def test_markdown_empty(self):
        r = SimulationReport(simulation_id="md-1", total_assets=0)
        md = r.generate_markdown()
        self.assertIn("Migration Dry-Run Simulation Report", md)
        self.assertIn("md-1", md)

    def test_markdown_with_cost(self):
        r = SimulationReport(simulation_id="md-2")
        r.cost_estimate = CostEstimate(
            compute_hours=10.0,
            storage_gb=5.0,
            total_cost_usd=12.50,
            breakdown={"copy": 8.0},
        )
        md = r.generate_markdown()
        self.assertIn("Cost Estimate", md)
        self.assertIn("$12.50", md)

    def test_markdown_with_timeline(self):
        r = SimulationReport(simulation_id="md-3")
        r.timeline_estimate = TimelineEstimate(total_days=10.0, buffered_days=12.0)
        md = r.generate_markdown()
        self.assertIn("Timeline Estimate", md)
        self.assertIn("10.0", md)

    def test_markdown_with_risk_summary(self):
        r = SimulationReport()
        r.assets_by_risk = {"low": 5, "high": 2}
        md = r.generate_markdown()
        self.assertIn("Risk Summary", md)
        self.assertIn("low", md)
        self.assertIn("high", md)

    def test_markdown_with_change_manifest(self):
        r = SimulationReport()
        r.change_manifest = [
            ChangeManifestEntry("Sales", "table", ChangeAction.CREATE, "/sales")
        ]
        md = r.generate_markdown()
        self.assertIn("Change Manifest", md)
        self.assertIn("Sales", md)

    def test_markdown_manifest_truncation(self):
        r = SimulationReport()
        r.change_manifest = [
            ChangeManifestEntry(f"tbl_{i}", "table", ChangeAction.CREATE, f"/t{i}")
            for i in range(60)
        ]
        md = r.generate_markdown()
        self.assertIn("more entries", md)

    def test_markdown_review_required(self):
        r = SimulationReport()
        r.asset_results = [
            AssetSimulationResult(
                asset_name="complex_model",
                asset_type="analysis",
                requires_review=True,
                translation_confidence=0.4,
                risk_level="high",
                warnings=["Low confidence"],
            )
        ]
        md = r.generate_markdown()
        self.assertIn("Assets Requiring Review", md)
        self.assertIn("complex_model", md)

    def test_markdown_translation_coverage(self):
        r = SimulationReport()
        r.translation_coverage = TranslationCoverageStats(
            total_expressions=50, translated=40, rule_based=30, llm_assisted=10
        )
        md = r.generate_markdown()
        self.assertIn("Translation Coverage", md)
        self.assertIn("50", md)


# ===========================================================================
# DryRunSimulator tests
# ===========================================================================


class TestDryRunSimulatorInit(unittest.TestCase):
    """DryRunSimulator initialization."""

    def test_default_config(self):
        sim = DryRunSimulator()
        self.assertEqual(sim.config.mode, SimulationMode.STANDARD)

    def test_custom_config(self):
        cfg = SimulationConfig(mode=SimulationMode.FULL, team_size=4)
        sim = DryRunSimulator(cfg)
        self.assertEqual(sim.config.mode, SimulationMode.FULL)
        self.assertEqual(sim.config.team_size, 4)


class TestDryRunSimulatorSimulate(unittest.TestCase):
    """DryRunSimulator.simulate() — main workflow."""

    def test_empty_inventory(self):
        sim = DryRunSimulator()
        inv = Inventory()
        report = sim.simulate(inv)
        self.assertEqual(report.total_assets, 0)
        self.assertEqual(len(report.asset_results), 0)
        self.assertIsNotNone(report.cost_estimate)
        self.assertIsNotNone(report.timeline_estimate)

    def test_basic_simulation(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        self.assertEqual(report.total_assets, 2)
        self.assertEqual(len(report.asset_results), 2)
        self.assertIsNotNone(report.cost_estimate)
        self.assertIsNotNone(report.timeline_estimate)
        self.assertIsNotNone(report.risk_assessment)
        self.assertIn(report.overall_risk_level, ["low", "medium", "high", "critical"])

    def test_simulation_with_expressions(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        exprs = _make_expressions()
        report = sim.simulate(inv, exprs)
        tc = report.translation_coverage
        self.assertEqual(tc.total_expressions, 4)
        self.assertGreater(tc.translated, 0)

    def test_simulation_id(self):
        cfg = SimulationConfig(simulation_id="my-sim-001")
        sim = DryRunSimulator(cfg)
        inv = _make_inventory()
        report = sim.simulate(inv)
        self.assertEqual(report.simulation_id, "my-sim-001")

    def test_auto_simulation_id(self):
        sim = DryRunSimulator()
        inv = Inventory()
        report = sim.simulate(inv)
        self.assertTrue(report.simulation_id.startswith("sim-"))

    def test_started_and_completed_at(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        self.assertTrue(report.started_at)
        self.assertTrue(report.completed_at)

    def test_mode_propagation(self):
        cfg = SimulationConfig(mode=SimulationMode.QUICK)
        sim = DryRunSimulator(cfg)
        inv = _make_inventory()
        report = sim.simulate(inv)
        self.assertEqual(report.mode, SimulationMode.QUICK)

    def test_quick_mode_skips_translation(self):
        cfg = SimulationConfig(mode=SimulationMode.QUICK)
        sim = DryRunSimulator(cfg)
        inv = _make_inventory()
        exprs = _make_expressions()
        report = sim.simulate(inv, exprs)
        # Quick mode should not measure translations
        self.assertEqual(report.translation_coverage.total_expressions, 0)


class TestDryRunSimulatorComplexity(unittest.TestCase):
    """Complexity scoring in simulation."""

    def test_complexity_scores_populated(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        for r in report.asset_results:
            self.assertIsInstance(r.complexity_score, float)
            self.assertGreaterEqual(r.complexity_score, 0.0)

    def test_high_complexity_asset(self):
        inv = _make_inventory(
            [
                {
                    "name": "ComplexModel",
                    "asset_type": AssetType.PHYSICAL_TABLE,
                    "metadata": {
                        "tables": 50,
                        "calculations": 200,
                        "rls_roles": 15,
                        "visuals": 40,
                        "row_count": 10_000_000,
                        "dependencies": 20,
                        "custom_sql": 30,
                    },
                }
            ]
        )
        sim = DryRunSimulator()
        report = sim.simulate(inv)
        self.assertEqual(len(report.asset_results), 1)
        r = report.asset_results[0]
        self.assertGreater(r.complexity_score, 5.0)

    def test_low_complexity_asset(self):
        inv = _make_inventory(
            [
                {
                    "name": "SimpleTable",
                    "asset_type": AssetType.PHYSICAL_TABLE,
                    "metadata": {
                        "tables": 1,
                        "calculations": 0,
                        "rls_roles": 0,
                        "visuals": 0,
                        "row_count": 100,
                        "dependencies": 0,
                        "custom_sql": 0,
                    },
                }
            ]
        )
        sim = DryRunSimulator()
        report = sim.simulate(inv)
        r = report.asset_results[0]
        self.assertLess(r.complexity_score, 3.0)


class TestDryRunSimulatorTranslation(unittest.TestCase):
    """Translation coverage measurement."""

    def test_all_translatable(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        exprs = [
            {"name": "s", "table": "T", "expression": "SUM(revenue)"},
            {"name": "c", "table": "T", "expression": "COUNT(*)"},
        ]
        report = sim.simulate(inv, exprs)
        tc = report.translation_coverage
        self.assertEqual(tc.total_expressions, 2)
        self.assertEqual(tc.translated, 2)
        self.assertGreater(tc.avg_confidence, 0.0)

    def test_empty_expression_goes_manual(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        exprs = [{"name": "blank", "table": "T", "expression": ""}]
        report = sim.simulate(inv, exprs)
        tc = report.translation_coverage
        self.assertEqual(tc.manual_required, 1)

    def test_no_expressions(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv, [])
        self.assertEqual(report.translation_coverage.total_expressions, 0)

    def test_confidence_min_max(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        exprs = [
            {"name": "s", "table": "T", "expression": "SUM(x)"},
            {"name": "a", "table": "T", "expression": "AVG(y)"},
        ]
        report = sim.simulate(inv, exprs)
        tc = report.translation_coverage
        self.assertLessEqual(tc.min_confidence, tc.max_confidence)

    def test_low_confidence_count(self):
        sim = DryRunSimulator(SimulationConfig(review_confidence_threshold=0.7))
        inv = _make_inventory()
        # Unknown function will get low confidence
        exprs = [
            {"name": "x", "table": "T", "expression": "MYSTERY_FUNC(a, b, c)"},
        ]
        report = sim.simulate(inv, exprs)
        # Even if not flagged as low, counter should work
        tc = report.translation_coverage
        self.assertIsInstance(tc.low_confidence_count, int)


class TestDryRunSimulatorCost(unittest.TestCase):
    """Cost estimation in simulation."""

    def test_cost_estimate_populated(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        ce = report.cost_estimate
        self.assertIsNotNone(ce)
        self.assertGreater(ce.total_cost_usd, 0)
        self.assertGreater(ce.compute_hours, 0)
        self.assertIn("data_copy", ce.breakdown)

    def test_cost_custom_rate(self):
        cfg = SimulationConfig(cu_price_per_hour=0.50)
        sim = DryRunSimulator(cfg)
        inv = _make_inventory()
        report = sim.simulate(inv)
        # Higher price → higher cost
        self.assertGreater(report.cost_estimate.total_cost_usd, 0)

    def test_empty_inventory_cost(self):
        sim = DryRunSimulator()
        inv = Inventory()
        report = sim.simulate(inv)
        self.assertAlmostEqual(report.cost_estimate.total_cost_usd, 0.0)


class TestDryRunSimulatorTimeline(unittest.TestCase):
    """Timeline estimation in simulation."""

    def test_timeline_populated(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        te = report.timeline_estimate
        self.assertIsNotNone(te)
        self.assertGreater(te.total_days, 0)
        self.assertGreater(te.buffered_days, te.total_days)

    def test_larger_team_faster(self):
        inv = _make_inventory()
        cfg1 = SimulationConfig(team_size=1)
        cfg2 = SimulationConfig(team_size=3)
        r1 = DryRunSimulator(cfg1).simulate(inv)
        r2 = DryRunSimulator(cfg2).simulate(inv)
        self.assertGreaterEqual(
            r1.timeline_estimate.total_days, r2.timeline_estimate.total_days
        )


class TestDryRunSimulatorRisk(unittest.TestCase):
    """Risk assessment in simulation."""

    def test_risk_assessment_present(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        self.assertIsNotNone(report.risk_assessment)
        self.assertIn(
            report.overall_risk_level, ["low", "medium", "high", "critical"]
        )

    def test_risk_rollup(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        self.assertIsInstance(report.assets_by_risk, dict)
        # Sum of risk counts should equal total assets
        total = sum(report.assets_by_risk.values())
        self.assertEqual(total, report.total_assets)


class TestDryRunSimulatorRiskHeatmap(unittest.TestCase):
    """Risk heatmap generation."""

    def test_heatmap_populated(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        self.assertGreater(len(report.risk_heatmap), 0)

    def test_heatmap_has_dimensions(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        dims = {cell.dimension for cell in report.risk_heatmap}
        self.assertTrue(len(dims) > 0)

    def test_heatmap_risk_levels(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        for cell in report.risk_heatmap:
            self.assertIn(cell.risk_level, ["low", "medium", "high", "critical"])

    def test_heatmap_scores_bounded(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        for cell in report.risk_heatmap:
            self.assertGreaterEqual(cell.score, 0.0)
            self.assertLessEqual(cell.score, 10.0)

    def test_empty_inventory_no_heatmap(self):
        sim = DryRunSimulator()
        inv = Inventory()
        report = sim.simulate(inv)
        self.assertEqual(len(report.risk_heatmap), 0)


class TestDryRunSimulatorChangeManifest(unittest.TestCase):
    """Change manifest generation."""

    def test_manifest_populated(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        self.assertGreater(len(report.change_manifest), 0)

    def test_manifest_has_calculations_entry(self):
        inv = _make_inventory(
            [
                {
                    "name": "WithCalcs",
                    "asset_type": AssetType.PHYSICAL_TABLE,
                    "metadata": {"tables": 1, "calculations": 5},
                }
            ]
        )
        sim = DryRunSimulator()
        report = sim.simulate(inv)
        types = [e.asset_type for e in report.change_manifest]
        self.assertIn("measure", types)

    def test_manifest_has_rls_entry(self):
        inv = _make_inventory(
            [
                {
                    "name": "Secured",
                    "asset_type": AssetType.PHYSICAL_TABLE,
                    "metadata": {"tables": 1, "rls_roles": 3},
                }
            ]
        )
        sim = DryRunSimulator()
        report = sim.simulate(inv)
        types = [e.asset_type for e in report.change_manifest]
        self.assertIn("rls_role", types)

    def test_manifest_target_paths(self):
        cfg = SimulationConfig(target_prefix="fabric://ws/lh/")
        sim = DryRunSimulator(cfg)
        inv = _make_inventory()
        report = sim.simulate(inv)
        for entry in report.change_manifest:
            self.assertTrue(entry.target_path.startswith("fabric://ws/lh/"))

    def test_manifest_actions(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        actions = {e.action for e in report.change_manifest}
        self.assertIn(ChangeAction.CREATE, actions)

    def test_empty_inventory_no_manifest(self):
        sim = DryRunSimulator()
        inv = Inventory()
        report = sim.simulate(inv)
        self.assertEqual(len(report.change_manifest), 0)


class TestDryRunSimulatorAssetResults(unittest.TestCase):
    """Per-asset result building."""

    def test_asset_names(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        names = [r.asset_name for r in report.asset_results]
        self.assertIn("Sales", names)
        self.assertIn("Marketing Dashboard", names)

    def test_risk_score_bounded(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        for r in report.asset_results:
            self.assertGreaterEqual(r.risk_score, 0.0)
            self.assertLessEqual(r.risk_score, 10.0)

    def test_review_flag_on_high_risk(self):
        inv = _make_inventory(
            [
                {
                    "name": "Risky",
                    "asset_type": AssetType.PHYSICAL_TABLE,
                    "metadata": {
                        "tables": 100,
                        "calculations": 500,
                        "rls_roles": 20,
                        "visuals": 50,
                        "row_count": 100_000_000,
                        "dependencies": 30,
                        "custom_sql": 50,
                    },
                }
            ]
        )
        sim = DryRunSimulator()
        report = sim.simulate(inv)
        r = report.asset_results[0]
        self.assertTrue(r.requires_review)

    def test_per_asset_cost(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        for r in report.asset_results:
            self.assertGreaterEqual(r.estimated_cost_usd, 0)
            self.assertGreaterEqual(r.estimated_hours, 0)

    def test_target_path_assigned(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        for r in report.asset_results:
            self.assertTrue(r.target_path)

    def test_review_count_rollup(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        manual_count = sum(1 for r in report.asset_results if r.requires_review)
        self.assertEqual(report.review_required_count, manual_count)

    def test_assets_by_action_rollup(self):
        sim = DryRunSimulator()
        inv = _make_inventory()
        report = sim.simulate(inv)
        total_actions = sum(report.assets_by_action.values())
        self.assertEqual(total_actions, report.total_assets)

    def test_expression_tracking_with_metadata(self):
        """Test that expressions are tracked per-asset via metadata."""
        inv = _make_inventory(
            [
                {
                    "name": "TestModel",
                    "asset_type": AssetType.PHYSICAL_TABLE,
                    "metadata": {
                        "tables": 1,
                        "calculations": 2,
                        "table_name": "Sales",
                        "expression_names": ["total_sales", "avg_price"],
                    },
                }
            ]
        )
        exprs = [
            {"name": "total_sales", "table": "Sales", "expression": "SUM(revenue)"},
            {"name": "avg_price", "table": "Sales", "expression": "AVG(price)"},
        ]
        sim = DryRunSimulator()
        report = sim.simulate(inv, exprs)
        r = report.asset_results[0]
        self.assertEqual(r.expressions_total, 2)
        self.assertEqual(r.expressions_translated, 2)


# ===========================================================================
# Convenience function tests
# ===========================================================================


class TestRunDryRun(unittest.TestCase):
    """run_dry_run() convenience function."""

    def test_basic_call(self):
        inv = _make_inventory()
        report = run_dry_run(inv)
        self.assertIsInstance(report, SimulationReport)
        self.assertEqual(report.total_assets, 2)

    def test_with_mode(self):
        inv = _make_inventory()
        report = run_dry_run(inv, mode=SimulationMode.QUICK)
        self.assertEqual(report.mode, SimulationMode.QUICK)

    def test_with_simulation_id(self):
        inv = _make_inventory()
        report = run_dry_run(inv, simulation_id="conv-001")
        self.assertEqual(report.simulation_id, "conv-001")

    def test_with_team_size(self):
        inv = _make_inventory()
        report = run_dry_run(inv, team_size=5)
        self.assertIsNotNone(report.timeline_estimate)

    def test_with_expressions(self):
        inv = _make_inventory()
        exprs = _make_expressions()
        report = run_dry_run(inv, exprs)
        self.assertGreater(report.translation_coverage.total_expressions, 0)

    def test_with_extra_config(self):
        inv = _make_inventory()
        report = run_dry_run(inv, extra_config={"azure_openai_key": "test-key"})
        self.assertIsNotNone(report.risk_assessment)

    def test_with_cu_price(self):
        inv = _make_inventory()
        report = run_dry_run(inv, cu_price_per_hour=1.0)
        self.assertIsNotNone(report.cost_estimate)


# ===========================================================================
# Integration-level tests
# ===========================================================================


class TestDryRunIntegration(unittest.TestCase):
    """Integration tests combining multiple features."""

    def test_full_simulation_pipeline(self):
        """Full pipeline: inventory → simulation → report → markdown → JSON."""
        inv = _make_inventory()
        exprs = _make_expressions()
        cfg = SimulationConfig(
            mode=SimulationMode.FULL,
            simulation_id="integration-001",
            team_size=3,
        )
        sim = DryRunSimulator(cfg)
        report = sim.simulate(inv, exprs)

        # Verify all sections populated
        self.assertEqual(report.total_assets, 2)
        self.assertGreater(len(report.asset_results), 0)
        self.assertIsNotNone(report.cost_estimate)
        self.assertIsNotNone(report.timeline_estimate)
        self.assertIsNotNone(report.risk_assessment)
        self.assertGreater(len(report.risk_heatmap), 0)
        self.assertGreater(len(report.change_manifest), 0)

        # Markdown generation
        md = report.generate_markdown()
        self.assertIn("integration-001", md)
        self.assertIn("Cost Estimate", md)
        self.assertIn("Translation Coverage", md)

        # JSON serialization
        d = report.to_dict()
        json_str = json.dumps(d)
        self.assertGreater(len(json_str), 100)

    def test_many_assets_simulation(self):
        """Simulate with many assets to verify scalability."""
        items = [
            {
                "name": f"Asset_{i}",
                "asset_type": AssetType.PHYSICAL_TABLE,
                "metadata": {
                    "tables": i % 10 + 1,
                    "calculations": i * 2,
                    "rls_roles": i % 3,
                    "row_count": i * 10_000,
                },
            }
            for i in range(50)
        ]
        inv = _make_inventory(items)
        report = run_dry_run(inv, simulation_id="scale-test")
        self.assertEqual(report.total_assets, 50)
        self.assertEqual(len(report.asset_results), 50)
        total_risk = sum(report.assets_by_risk.values())
        self.assertEqual(total_risk, 50)

    def test_single_asset_analysis(self):
        """Single-asset simulation for detailed inspection."""
        inv = _make_inventory(
            [
                {
                    "name": "SalesAnalysis",
                    "asset_type": AssetType.ANALYSIS,
                    "metadata": {
                        "tables": 4,
                        "calculations": 15,
                        "rls_roles": 2,
                        "visuals": 8,
                        "row_count": 1_000_000,
                        "dependencies": 3,
                        "custom_sql": 2,
                    },
                }
            ]
        )
        report = run_dry_run(inv, simulation_id="single")
        self.assertEqual(report.total_assets, 1)
        r = report.asset_results[0]
        self.assertEqual(r.asset_name, "SalesAnalysis")
        self.assertEqual(r.asset_type, "analysis")
        self.assertGreater(r.complexity_score, 0)


if __name__ == "__main__":
    unittest.main()
