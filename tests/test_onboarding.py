"""Tests for Phase 83 — Customer Onboarding Accelerator."""

from __future__ import annotations

import unittest

from src.core.onboarding.env_scanner import (
    ComponentStatus,
    EnvironmentProfile,
    EnvironmentScanner,
)
from src.core.onboarding.prereq_checker import (
    PrereqStatus,
    PrerequisiteChecker,
)
from src.core.onboarding.effort_estimator import (
    EffortEstimator,
)


# ---------------------------------------------------------------------------
# Environment Scanner
# ---------------------------------------------------------------------------


class TestEnvironmentScanner(unittest.TestCase):
    def test_scan_empty_config(self) -> None:
        scanner = EnvironmentScanner({})
        profile = scanner.scan("TestCustomer")
        self.assertEqual(profile.customer_name, "TestCustomer")
        self.assertEqual(profile.total_checks, 6)
        # Most should be NOT_CONFIGURED
        self.assertGreater(profile.unreachable_count + sum(
            1 for c in profile.checks if c.status == ComponentStatus.NOT_CONFIGURED
        ), 0)

    def test_scan_with_full_config(self) -> None:
        config = {
            "oac_base_url": "https://oac.example.com",
            "oracle_connection_string": "oracle://user:pass@host/db",
            "fabric_workspace_id": "ws-123",
            "fabric_lakehouse_id": "lh-456",
            "azure_openai_endpoint": "https://openai.example.com",
            "keyvault_url": "https://kv.example.com",
        }
        scanner = EnvironmentScanner(config)
        profile = scanner.scan("FullCustomer")
        self.assertTrue(profile.all_reachable)
        self.assertEqual(profile.reachable_count, 6)

    def test_get_check(self) -> None:
        scanner = EnvironmentScanner({"oac_base_url": "https://oac.example.com"})
        profile = scanner.scan()
        oac = profile.get_check("oac_api")
        self.assertIsNotNone(oac)
        self.assertEqual(oac.status, ComponentStatus.REACHABLE)

    def test_profile_to_dict(self) -> None:
        scanner = EnvironmentScanner({})
        profile = scanner.scan("Test")
        d = profile.to_dict()
        self.assertIn("checks", d)
        self.assertEqual(d["customer_name"], "Test")

    def test_profile_summary(self) -> None:
        scanner = EnvironmentScanner({})
        profile = scanner.scan("Test")
        s = profile.summary()
        self.assertIn("Test", s)


# ---------------------------------------------------------------------------
# Prerequisite Checker
# ---------------------------------------------------------------------------


class TestPrerequisiteChecker(unittest.TestCase):
    def test_check_basic(self) -> None:
        checker = PrerequisiteChecker({})
        report = checker.check()
        self.assertGreater(report.total, 0)
        # Python version should pass (we're running 3.12+)
        python_check = next((c for c in report.checks if c.name == "python_version"), None)
        self.assertIsNotNone(python_check)
        self.assertEqual(python_check.status, PrereqStatus.PASS)

    def test_pydantic_available(self) -> None:
        checker = PrerequisiteChecker({})
        report = checker.check()
        pd_check = next((c for c in report.checks if c.name == "pydantic"), None)
        self.assertIsNotNone(pd_check)
        self.assertEqual(pd_check.status, PrereqStatus.PASS)

    def test_missing_config_fails(self) -> None:
        checker = PrerequisiteChecker({"config_path": "/nonexistent/path.toml"})
        report = checker.check()
        cfg_check = next((c for c in report.checks if c.name == "config_file"), None)
        self.assertIsNotNone(cfg_check)
        self.assertEqual(cfg_check.status, PrereqStatus.FAIL)

    def test_missing_workspace_fails(self) -> None:
        checker = PrerequisiteChecker({})
        report = checker.check()
        ws_check = next((c for c in report.checks if c.name == "fabric_workspace"), None)
        self.assertIsNotNone(ws_check)
        self.assertEqual(ws_check.status, PrereqStatus.FAIL)

    def test_report_to_dict(self) -> None:
        checker = PrerequisiteChecker({})
        report = checker.check()
        d = report.to_dict()
        self.assertIn("total", d)
        self.assertIn("ready", d)

    def test_report_summary(self) -> None:
        checker = PrerequisiteChecker({})
        report = checker.check()
        s = report.summary()
        self.assertIn("Prerequisites", s)


# ---------------------------------------------------------------------------
# Effort Estimator
# ---------------------------------------------------------------------------


class TestEffortEstimator(unittest.TestCase):
    def test_empty_inventory(self) -> None:
        estimator = EffortEstimator()
        result = estimator.estimate([])
        self.assertEqual(result.total_assets, 0)
        self.assertEqual(result.total_hours, 0.0)

    def test_single_simple_asset(self) -> None:
        estimator = EffortEstimator()
        inventory = [{"asset_type": "analysis", "complexity": "Low"}]
        result = estimator.estimate(inventory)
        self.assertEqual(result.total_assets, 1)
        self.assertGreater(result.total_hours, 0)

    def test_mixed_complexity(self) -> None:
        estimator = EffortEstimator()
        inventory = [
            {"asset_type": "analysis", "complexity": "Low"},
            {"asset_type": "analysis", "complexity": "High"},
            {"asset_type": "dataModel", "complexity": "Medium"},
        ]
        result = estimator.estimate(inventory)
        self.assertEqual(result.total_assets, 3)
        self.assertGreater(result.grand_total_hours, result.total_hours)  # overhead

    def test_overhead_applied(self) -> None:
        estimator = EffortEstimator(overhead_pct=0.25)
        inventory = [{"asset_type": "physicalTable", "complexity": "Low"}] * 10
        result = estimator.estimate(inventory)
        expected_overhead = result.total_hours * 0.25
        self.assertAlmostEqual(result.overhead_hours, expected_overhead, places=1)

    def test_team_size_affects_days(self) -> None:
        inv = [{"asset_type": "analysis", "complexity": "Medium"}] * 20
        small_team = EffortEstimator(team_size=1).estimate(inv)
        big_team = EffortEstimator(team_size=4).estimate(inv)
        self.assertGreater(small_team.estimated_days, big_team.estimated_days)

    def test_risk_notes_for_high_complexity(self) -> None:
        estimator = EffortEstimator()
        # >50% high complexity
        inventory = [
            {"asset_type": "dataflow", "complexity": "High"},
            {"asset_type": "dataflow", "complexity": "High"},
            {"asset_type": "dataflow", "complexity": "Low"},
        ]
        result = estimator.estimate(inventory)
        self.assertTrue(len(result.risk_notes) > 0)

    def test_to_dict(self) -> None:
        estimator = EffortEstimator()
        result = estimator.estimate([{"asset_type": "analysis", "complexity": "Low"}])
        d = result.to_dict()
        self.assertIn("total_assets", d)
        self.assertIn("breakdowns", d)

    def test_summary(self) -> None:
        estimator = EffortEstimator()
        result = estimator.estimate([{"asset_type": "analysis", "complexity": "Low"}])
        s = result.summary()
        self.assertIn("Effort Estimate", s)

    def test_unknown_asset_type_uses_default(self) -> None:
        estimator = EffortEstimator()
        inventory = [{"asset_type": "unknown_type", "complexity": "Medium"}]
        result = estimator.estimate(inventory)
        self.assertEqual(result.total_assets, 1)
        self.assertGreater(result.total_hours, 0)


if __name__ == "__main__":
    unittest.main()
