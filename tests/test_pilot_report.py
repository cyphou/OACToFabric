"""Tests for Phase 78 — Pilot Report."""

from __future__ import annotations

import unittest

from src.core.pilot_report import (
    AgentVerdict,
    PerformanceProfile,
    PilotAgentResult,
    PilotDefect,
    PilotOutcome,
    PilotReport,
    PilotReportBuilder,
)


class TestPilotAgentResult(unittest.TestCase):
    def test_success_rate_all_processed(self) -> None:
        r = PilotAgentResult(agent_id="01", items_processed=10, items_failed=0)
        self.assertEqual(r.success_rate, 1.0)

    def test_success_rate_partial(self) -> None:
        r = PilotAgentResult(agent_id="01", items_processed=7, items_failed=3)
        self.assertAlmostEqual(r.success_rate, 0.7)

    def test_success_rate_no_items(self) -> None:
        r = PilotAgentResult(agent_id="01")
        self.assertEqual(r.success_rate, 1.0)

    def test_to_dict(self) -> None:
        r = PilotAgentResult(agent_id="01", agent_name="Discovery", items_processed=5)
        d = r.to_dict()
        self.assertEqual(d["agent_id"], "01")
        self.assertEqual(d["items_processed"], 5)
        self.assertIn("success_rate", d)


class TestPilotReport(unittest.TestCase):
    def _make_report(self, *, failed_agent: bool = False, critical_defect: bool = False) -> PilotReport:
        report = PilotReport(pilot_id="test-001")
        report.agent_results = [
            PilotAgentResult(agent_id="01", verdict=AgentVerdict.OK, items_processed=10),
            PilotAgentResult(
                agent_id="02",
                verdict=AgentVerdict.FAILED if failed_agent else AgentVerdict.OK,
                items_processed=5,
                items_failed=2 if failed_agent else 0,
            ),
        ]
        if critical_defect:
            report.defects.append(
                PilotDefect(defect_id="DEF-001", agent_id="02", severity="critical", title="Crash")
            )
        return report

    def test_outcome_passed(self) -> None:
        report = self._make_report()
        self.assertEqual(report.compute_outcome(), PilotOutcome.PASSED)

    def test_outcome_failed_agent(self) -> None:
        report = self._make_report(failed_agent=True)
        self.assertEqual(report.compute_outcome(), PilotOutcome.FAILED)

    def test_outcome_critical_defect(self) -> None:
        report = self._make_report(critical_defect=True)
        self.assertEqual(report.compute_outcome(), PilotOutcome.FAILED)

    def test_outcome_high_defect(self) -> None:
        report = self._make_report()
        report.defects.append(PilotDefect(defect_id="D-1", agent_id="01", severity="high"))
        self.assertEqual(report.compute_outcome(), PilotOutcome.PASSED_WITH_WARNINGS)

    def test_total_items(self) -> None:
        report = self._make_report()
        self.assertEqual(report.total_items_processed, 15)

    def test_finalize(self) -> None:
        report = self._make_report()
        report.finalize()
        self.assertIsNotNone(report.completed_at)
        self.assertEqual(report.outcome, PilotOutcome.PASSED)

    def test_to_dict(self) -> None:
        report = self._make_report()
        report.finalize()
        d = report.to_dict()
        self.assertEqual(d["pilot_id"], "test-001")
        self.assertIn("agent_results", d)
        self.assertIn("performance", d)

    def test_summary(self) -> None:
        report = self._make_report()
        report.finalize()
        s = report.summary()
        self.assertIn("test-001", s)
        self.assertIn("PASSED", s.upper())


class TestPilotReportBuilder(unittest.TestCase):
    def test_builder_flow(self) -> None:
        builder = PilotReportBuilder("pilot-999", scope_description="Test scope")
        builder.add_agent_result(PilotAgentResult(agent_id="01", verdict=AgentVerdict.OK, items_processed=5))
        builder.set_performance(PerformanceProfile(total_duration_ms=500))
        builder.add_recommendation("Increase page size for large catalogs.")
        report = builder.build()
        self.assertEqual(report.pilot_id, "pilot-999")
        self.assertEqual(report.outcome, PilotOutcome.PASSED)
        self.assertEqual(len(report.recommendations), 1)
        self.assertEqual(report.performance.total_duration_ms, 500)


if __name__ == "__main__":
    unittest.main()
