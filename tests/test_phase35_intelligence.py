"""Tests for Phase 35 — Migration Intelligence & Cost Estimation."""

from __future__ import annotations

import pytest

from src.core.migration_intelligence import (
    AssessmentReport,
    CheckStatus,
    ComplexityAnalyzer,
    ComplexityDimension,
    ComplexityScore,
    CostEstimate,
    CostEstimator,
    PreflightCheck,
    PreflightChecker,
    PreflightResult,
    RiskAssessment,
    RiskFactor,
    RiskLevel,
    RiskScorer,
    TimelineEstimate,
    TimelineEstimator,
)


# ===================================================================
# ComplexityScore
# ===================================================================


class TestComplexityScore:
    def test_compute_overall_basic(self):
        cs = ComplexityScore(asset_name="A", asset_type="table")
        cs.scores = {"schema": 5.0, "calculations": 3.0}
        result = cs.compute_overall()
        assert result == pytest.approx(4.0)

    def test_compute_overall_weighted(self):
        cs = ComplexityScore(asset_name="A", asset_type="table")
        cs.scores = {"schema": 10.0, "calculations": 0.0}
        result = cs.compute_overall({"schema": 1.0, "calculations": 1.0})
        assert result == pytest.approx(5.0)

    def test_risk_level_low(self):
        cs = ComplexityScore(asset_name="A", asset_type="table")
        cs.scores = {"schema": 2.0}
        cs.compute_overall()
        assert cs.risk_level == RiskLevel.LOW

    def test_risk_level_critical(self):
        cs = ComplexityScore(asset_name="A", asset_type="table")
        cs.scores = {"schema": 9.0}
        cs.compute_overall()
        assert cs.risk_level == RiskLevel.CRITICAL

    def test_compute_overall_empty(self):
        cs = ComplexityScore(asset_name="A", asset_type="table")
        assert cs.compute_overall() == 0.0


# ===================================================================
# ComplexityAnalyzer
# ===================================================================


class TestComplexityAnalyzer:
    def _sample_asset(self, **overrides) -> dict:
        base = {
            "name": "test_asset",
            "type": "table",
            "tables": 5,
            "calculations": 10,
            "rls_roles": 2,
            "visuals": 8,
            "row_count": 100000,
            "dependencies": 3,
            "custom_sql": 1,
        }
        base.update(overrides)
        return base

    def test_score_basic_asset(self):
        analyzer = ComplexityAnalyzer()
        cs = analyzer.score_asset(self._sample_asset())
        assert cs.asset_name == "test_asset"
        assert cs.overall > 0

    def test_score_simple_asset(self):
        analyzer = ComplexityAnalyzer()
        cs = analyzer.score_asset(self._sample_asset(tables=1, calculations=1, row_count=100))
        assert cs.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)

    def test_score_complex_asset(self):
        analyzer = ComplexityAnalyzer()
        cs = analyzer.score_asset(self._sample_asset(
            tables=100, calculations=200, rls_roles=15,
            visuals=50, row_count=10**9, dependencies=20, custom_sql=30,
        ))
        assert cs.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_score_adds_notes_for_high_rls(self):
        analyzer = ComplexityAnalyzer()
        cs = analyzer.score_asset(self._sample_asset(rls_roles=15))
        assert any("RLS" in n for n in cs.notes)

    def test_score_adds_notes_for_custom_sql(self):
        analyzer = ComplexityAnalyzer()
        cs = analyzer.score_asset(self._sample_asset(custom_sql=15))
        assert any("custom SQL" in n for n in cs.notes)

    def test_score_inventory(self):
        analyzer = ComplexityAnalyzer()
        assets = [self._sample_asset(name=f"a{i}") for i in range(5)]
        scores = analyzer.score_inventory(assets)
        assert len(scores) == 5

    def test_summary(self):
        analyzer = ComplexityAnalyzer()
        scores = analyzer.score_inventory([self._sample_asset(name=f"a{i}") for i in range(3)])
        summary = analyzer.summary(scores)
        assert summary["total"] == 3
        assert "avg_complexity" in summary
        assert "by_risk" in summary

    def test_summary_empty(self):
        analyzer = ComplexityAnalyzer()
        summary = analyzer.summary([])
        assert summary["total"] == 0

    def test_custom_weights(self):
        analyzer = ComplexityAnalyzer(weights={"schema": 10.0, "calculations": 0.0})
        cs = analyzer.score_asset(self._sample_asset(tables=10, calculations=0))
        assert cs.overall > 0

    def test_zero_row_count(self):
        analyzer = ComplexityAnalyzer()
        cs = analyzer.score_asset(self._sample_asset(row_count=0))
        assert cs.scores[ComplexityDimension.DATA_VOLUME.value] == 0.0


# ===================================================================
# CostEstimator
# ===================================================================


class TestCostEstimator:
    def test_estimate_basic(self):
        estimator = CostEstimator()
        est = estimator.estimate(total_rows=1_000_000, total_tables=10,
                                  total_calculations=50, total_reports=5)
        assert est.total_cost_usd > 0
        assert est.storage_gb > 0
        assert est.compute_hours > 0

    def test_estimate_zero_scope(self):
        estimator = CostEstimator()
        est = estimator.estimate(total_rows=0, total_tables=0,
                                  total_calculations=0, total_reports=0)
        assert est.total_cost_usd == 0.0

    def test_estimate_breakdown_keys(self):
        estimator = CostEstimator()
        est = estimator.estimate(total_rows=100000, total_tables=5,
                                  total_calculations=20, total_reports=3)
        assert "data_copy" in est.breakdown
        assert "translation" in est.breakdown
        assert "report_gen" in est.breakdown
        assert "storage" in est.breakdown

    def test_custom_rates(self):
        estimator = CostEstimator(cu_price_per_hour=0.50)
        est1 = estimator.estimate(total_rows=100, total_tables=1,
                                   total_calculations=1, total_reports=1)
        estimator2 = CostEstimator(cu_price_per_hour=0.10)
        est2 = estimator2.estimate(total_rows=100, total_tables=1,
                                    total_calculations=1, total_reports=1)
        assert est1.estimated_cost_usd > est2.estimated_cost_usd

    def test_assumptions_list(self):
        estimator = CostEstimator()
        est = estimator.estimate(total_rows=100, total_tables=1,
                                  total_calculations=1, total_reports=1)
        assert len(est.assumptions) >= 2

    def test_compute_total(self):
        est = CostEstimate(estimated_cost_usd=10.0, storage_cost_usd=2.0)
        total = est.compute_total()
        assert total == 12.0


# ===================================================================
# TimelineEstimator
# ===================================================================


class TestTimelineEstimator:
    def test_basic_timeline(self):
        te = TimelineEstimator(team_size=2)
        result = te.estimate(total_tables=10, total_calculations=20, total_reports=5)
        assert result.total_days > 0
        assert result.buffered_days > result.total_days

    def test_larger_team_faster(self):
        te1 = TimelineEstimator(team_size=1)
        te2 = TimelineEstimator(team_size=3)
        r1 = te1.estimate(total_tables=10, total_calculations=20, total_reports=5)
        r2 = te2.estimate(total_tables=10, total_calculations=20, total_reports=5)
        assert r2.total_days < r1.total_days

    def test_phases_populated(self):
        te = TimelineEstimator()
        result = te.estimate(total_tables=5, total_calculations=10, total_reports=3)
        assert "discovery" in result.phases
        assert "schema" in result.phases
        assert "reports" in result.phases
        assert "validation" in result.phases

    def test_buffer_default(self):
        result = TimelineEstimate(total_days=10.0, buffer_pct=0.2)
        buffered = result.compute_buffered()
        assert buffered == pytest.approx(12.0)

    def test_security_included(self):
        te = TimelineEstimator()
        result = te.estimate(total_tables=5, total_calculations=10, total_reports=3, total_rls_roles=5)
        assert "security" in result.phases
        assert result.phases["security"] > 0

    def test_complexity_increases_time(self):
        te = TimelineEstimator()
        r1 = te.estimate(total_tables=10, total_calculations=10, total_reports=5, complexity_avg=2.0)
        r2 = te.estimate(total_tables=10, total_calculations=10, total_reports=5, complexity_avg=8.0)
        assert r2.total_days > r1.total_days


# ===================================================================
# PreflightChecker
# ===================================================================


class TestPreflightChecker:
    def test_all_pass(self):
        checker = PreflightChecker()
        result = checker.check({
            "source_connection": "oracle://...",
            "fabric_workspace": "ws1",
            "fabric_capacity": "F2",
            "azure_openai_key": "key123",
            "tables": 10,
            "disk_space_gb": 100,
            "estimated_data_gb": 5,
        })
        assert result.overall_ready is True
        assert result.fail_count == 0

    def test_fail_no_source(self):
        checker = PreflightChecker()
        result = checker.check({"fabric_workspace": "ws1", "tables": 5})
        assert result.overall_ready is False
        assert result.fail_count >= 1

    def test_fail_no_workspace(self):
        checker = PreflightChecker()
        result = checker.check({"source_connection": "x", "tables": 5})
        assert result.overall_ready is False

    def test_warn_no_capacity(self):
        checker = PreflightChecker()
        result = checker.check({"source_connection": "x", "fabric_workspace": "w", "tables": 5})
        assert result.warn_count >= 1

    def test_warn_large_scope(self):
        checker = PreflightChecker()
        result = checker.check({
            "source_connection": "x", "fabric_workspace": "w",
            "tables": 600, "fabric_capacity": "F4",
        })
        warns = [c for c in result.checks if c.status == CheckStatus.WARN and "tables" in c.name]
        assert len(warns) >= 1

    def test_disk_space_tight(self):
        checker = PreflightChecker()
        result = checker.check({
            "source_connection": "x", "fabric_workspace": "w",
            "tables": 5, "disk_space_gb": 10, "estimated_data_gb": 8,
        })
        disk_checks = [c for c in result.checks if "disk" in c.name]
        assert any(c.status == CheckStatus.WARN for c in disk_checks)

    def test_summary_string(self):
        result = PreflightResult(
            checks=[
                PreflightCheck("a", CheckStatus.PASS),
                PreflightCheck("b", CheckStatus.WARN),
                PreflightCheck("c", CheckStatus.FAIL),
            ],
            overall_ready=False,
        )
        s = result.summary()
        assert "1 pass" in s
        assert "NOT READY" in s


# ===================================================================
# RiskScorer
# ===================================================================


class TestRiskScorer:
    def _make_scores(self, overall: float, count: int = 5) -> list[ComplexityScore]:
        scores = []
        for i in range(count):
            cs = ComplexityScore(asset_name=f"a{i}", asset_type="table")
            cs.scores = {"schema": overall}
            cs.compute_overall()
            scores.append(cs)
        return scores

    def test_low_risk(self):
        scorer = RiskScorer()
        ra = scorer.assess(self._make_scores(2.0))
        assert ra.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)

    def test_high_risk(self):
        scorer = RiskScorer()
        ra = scorer.assess(self._make_scores(9.0), config={"azure_openai_key": "k"})
        assert ra.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_empty_scores(self):
        scorer = RiskScorer()
        ra = scorer.assess([])
        assert ra.overall_risk == 0.0

    def test_custom_code_risk(self):
        scorer = RiskScorer()
        scores = []
        for i in range(3):
            cs = ComplexityScore(asset_name=f"a{i}", asset_type="table")
            cs.scores = {"custom_code": 8.0, "schema": 3.0}
            cs.compute_overall()
            scores.append(cs)
        ra = scorer.assess(scores)
        assert any(f.name == "custom_code" for f in ra.factors)

    def test_no_llm_risk(self):
        scorer = RiskScorer()
        ra = scorer.assess(self._make_scores(3.0), config={})
        assert any(f.name == "no_llm" for f in ra.factors)

    def test_risk_factor_score(self):
        rf = RiskFactor("test", "desc", likelihood=0.5, impact=8.0)
        assert rf.risk_score == pytest.approx(4.0)

    def test_risk_assessment_compute(self):
        ra = RiskAssessment(factors=[
            RiskFactor("a", "x", 0.5, 6.0),
            RiskFactor("b", "y", 0.3, 4.0),
        ])
        ra.compute_overall()
        assert ra.overall_risk > 0


# ===================================================================
# AssessmentReport
# ===================================================================


class TestAssessmentReport:
    def test_empty_report_markdown(self):
        report = AssessmentReport()
        md = report.generate_markdown()
        assert "# Migration Assessment Report" in md

    def test_full_report_markdown(self):
        analyzer = ComplexityAnalyzer()
        assets = [{"name": "t1", "type": "table", "tables": 5, "calculations": 10,
                    "rls_roles": 2, "visuals": 4, "row_count": 10000,
                    "dependencies": 2, "custom_sql": 1}]
        scores = analyzer.score_inventory(assets)

        estimator = CostEstimator()
        cost = estimator.estimate(10000, 5, 10, 3)

        te = TimelineEstimator()
        timeline = te.estimate(5, 10, 3)

        checker = PreflightChecker()
        preflight = checker.check({"source_connection": "x", "fabric_workspace": "w", "tables": 5})

        scorer = RiskScorer()
        risk = scorer.assess(scores)

        report = AssessmentReport(
            complexity_scores=scores,
            complexity_summary=analyzer.summary(scores),
            cost_estimate=cost,
            timeline_estimate=timeline,
            preflight=preflight,
            risk_assessment=risk,
        )
        md = report.generate_markdown()
        assert "Complexity Summary" in md
        assert "Cost Estimate" in md
        assert "Timeline Estimate" in md
        assert "Preflight" in md
        assert "Risk Assessment" in md

    def test_report_with_cost_only(self):
        cost = CostEstimate(estimated_cost_usd=100.0, storage_cost_usd=5.0)
        cost.compute_total()
        report = AssessmentReport(cost_estimate=cost)
        md = report.generate_markdown()
        assert "$105.00" in md


# ===================================================================
# Enums
# ===================================================================


class TestIntelligenceEnums:
    def test_complexity_dimension_values(self):
        assert ComplexityDimension.SCHEMA.value == "schema"
        assert ComplexityDimension.CUSTOM_CODE.value == "custom_code"

    def test_risk_level_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_check_status_values(self):
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.FAIL.value == "fail"
