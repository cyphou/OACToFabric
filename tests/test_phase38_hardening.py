"""Tests for Phase 38 — Chaos Testing & Production Hardening v3."""

from __future__ import annotations

import pytest

from src.core.chaos_testing import (
    BaselineComparison,
    ChaosSimulator,
    FaultInjectionResult,
    FaultScenario,
    FaultSeverity,
    FaultType,
    GateStatus,
    PerformanceBaseline,
    PerformanceMetric,
    RecoveryCheck,
    RecoveryReport,
    RecoveryVerifier,
    ReleaseGate,
    ReleaseValidation,
    ReleaseValidator,
    SecurityFinding,
    SecurityFindingType,
    SecurityScanner,
)


# ===================================================================
# FaultScenario
# ===================================================================


class TestFaultScenario:
    def test_create(self):
        fs = FaultScenario(name="Timeout", fault_type=FaultType.NETWORK_TIMEOUT)
        assert fs.scenario_id.startswith("FAULT-")
        assert fs.fault_type == FaultType.NETWORK_TIMEOUT

    def test_should_activate_always(self):
        fs = FaultScenario(probability=1.0)
        assert fs.should_activate() is True

    def test_should_activate_never(self):
        fs = FaultScenario(probability=0.0)
        assert fs.should_activate() is False

    def test_severity(self):
        fs = FaultScenario(severity=FaultSeverity.CRITICAL)
        assert fs.severity == FaultSeverity.CRITICAL


# ===================================================================
# ChaosSimulator
# ===================================================================


class TestChaosSimulator:
    def test_load_builtins(self):
        sim = ChaosSimulator()
        sim.load_builtins()
        assert len(sim.all_scenarios) >= 6

    def test_add_scenario(self):
        sim = ChaosSimulator()
        fs = FaultScenario(name="Custom")
        sim.add_scenario(fs)
        assert sim.get_scenario(fs.scenario_id) is fs

    def test_inject_activates(self):
        sim = ChaosSimulator()
        fs = FaultScenario(name="Always", probability=1.0, target_component="test")
        sim.add_scenario(fs)
        result = sim.inject(fs.scenario_id)
        assert result.activated is True
        assert sim.active_fault_count == 1

    def test_inject_not_found(self):
        sim = ChaosSimulator()
        result = sim.inject("nonexistent")
        assert result.activated is False
        assert "not found" in result.error_raised

    def test_inject_probability_zero(self):
        sim = ChaosSimulator()
        fs = FaultScenario(name="Never", probability=0.0)
        sim.add_scenario(fs)
        result = sim.inject(fs.scenario_id)
        assert result.activated is False

    def test_clear_fault(self):
        sim = ChaosSimulator()
        fs = FaultScenario(name="X", probability=1.0, target_component="comp")
        sim.add_scenario(fs)
        sim.inject(fs.scenario_id)
        assert sim.active_fault_count == 1
        assert sim.clear_fault(fs.scenario_id) is True
        assert sim.active_fault_count == 0

    def test_clear_all(self):
        sim = ChaosSimulator()
        for i in range(3):
            fs = FaultScenario(name=f"F{i}", probability=1.0, target_component=f"c{i}")
            sim.add_scenario(fs)
            sim.inject(fs.scenario_id)
        assert sim.clear_all() == 3
        assert sim.active_fault_count == 0

    def test_is_component_faulted(self):
        sim = ChaosSimulator()
        fs = FaultScenario(name="X", probability=1.0, target_component="parser")
        sim.add_scenario(fs)
        sim.inject(fs.scenario_id)
        assert sim.is_component_faulted("parser") is True
        assert sim.is_component_faulted("other") is False

    def test_run_chaos_round(self):
        sim = ChaosSimulator()
        sim.load_builtins()
        # Set all to activate
        for s in sim.all_scenarios:
            s.probability = 1.0
        results = sim.run_chaos_round()
        assert len(results) >= 6
        assert all(isinstance(r, FaultInjectionResult) for r in results)

    def test_all_results_tracked(self):
        sim = ChaosSimulator()
        fs = FaultScenario(name="X", probability=1.0)
        sim.add_scenario(fs)
        sim.inject(fs.scenario_id)
        sim.inject(fs.scenario_id)
        assert len(sim.all_results) == 2


# ===================================================================
# RecoveryVerifier
# ===================================================================


class TestRecoveryVerifier:
    def test_all_clear(self):
        sim = ChaosSimulator()
        verifier = RecoveryVerifier()
        report = verifier.verify(sim, {"db": True, "api": True})
        assert report.overall_recovered is True
        assert report.pass_count >= 3

    def test_active_faults_fail(self):
        sim = ChaosSimulator()
        fs = FaultScenario(probability=1.0, target_component="x")
        sim.add_scenario(fs)
        sim.inject(fs.scenario_id)
        verifier = RecoveryVerifier()
        report = verifier.verify(sim)
        assert report.overall_recovered is False

    def test_unhealthy_component(self):
        sim = ChaosSimulator()
        verifier = RecoveryVerifier()
        report = verifier.verify(sim, {"db": True, "api": False})
        assert report.overall_recovered is False

    def test_recovery_summary(self):
        report = RecoveryReport(
            checks=[RecoveryCheck("a", True), RecoveryCheck("b", False)],
            overall_recovered=False,
        )
        s = report.summary()
        assert "1/2" in s
        assert "NOT RECOVERED" in s


# ===================================================================
# SecurityScanner
# ===================================================================


class TestSecurityScanner:
    def test_detect_credential(self):
        scanner = SecurityScanner()
        findings = scanner.scan_text("connection_string = 'password=secret123'", "config.py")
        assert any(f.finding_type == SecurityFindingType.HARDCODED_CREDENTIAL for f in findings)

    def test_detect_insecure_connection(self):
        scanner = SecurityScanner()
        findings = scanner.scan_text("endpoint = 'http://insecure.example.com'", "config.py")
        assert any(f.finding_type == SecurityFindingType.INSECURE_CONNECTION for f in findings)

    def test_detect_pii(self):
        scanner = SecurityScanner()
        findings = scanner.scan_text("SELECT social_security_number FROM employees", "query.sql")
        has_pii = any(f.finding_type == SecurityFindingType.UNMASKED_PII for f in findings)
        assert has_pii

    def test_no_findings_clean(self):
        scanner = SecurityScanner()
        findings = scanner.scan_text("SELECT name, age FROM users", "clean.sql")
        assert len(findings) == 0

    def test_scan_artifacts(self):
        scanner = SecurityScanner()
        artifacts = [
            {"name": "pipeline.json", "content": "password=abc123"},
            {"name": "query.sql", "content": "SELECT id FROM t"},
        ]
        findings = scanner.scan_artifacts(artifacts)
        assert len(findings) >= 1

    def test_check_rls_coverage(self):
        scanner = SecurityScanner()
        findings = scanner.check_rls_coverage(
            tables=["sales", "customers", "products"],
            rls_tables=["sales"],
        )
        assert len(findings) == 2  # customers and products uncovered

    def test_generate_report(self):
        scanner = SecurityScanner()
        findings = scanner.scan_text("password=test", "file.py")
        md = scanner.generate_report(findings)
        assert "Security Scan Report" in md
        assert "SEC-" in md

    def test_generate_empty_report(self):
        scanner = SecurityScanner()
        md = scanner.generate_report([])
        assert "Findings" in md


# ===================================================================
# ReleaseValidator
# ===================================================================


class TestReleaseValidator:
    def test_all_pass(self):
        validator = ReleaseValidator()
        rv = validator.validate(
            test_pass_rate=100.0,
            security_findings_critical=0,
            uat_signed_off=True,
            checklist_complete=True,
        )
        assert rv.release_approved is True
        assert rv.fail_count == 0

    def test_fail_low_test_rate(self):
        validator = ReleaseValidator()
        rv = validator.validate(
            test_pass_rate=80.0,
            security_findings_critical=0,
            uat_signed_off=True,
            checklist_complete=True,
        )
        assert rv.release_approved is False

    def test_fail_security(self):
        validator = ReleaseValidator()
        rv = validator.validate(
            test_pass_rate=100.0,
            security_findings_critical=3,
            uat_signed_off=True,
            checklist_complete=True,
        )
        assert rv.release_approved is False

    def test_fail_no_uat(self):
        validator = ReleaseValidator()
        rv = validator.validate(
            test_pass_rate=100.0,
            security_findings_critical=0,
            uat_signed_off=False,
            checklist_complete=True,
        )
        assert rv.release_approved is False

    def test_warn_test_rate(self):
        validator = ReleaseValidator()
        rv = validator.validate(
            test_pass_rate=97.0,
            security_findings_critical=0,
            uat_signed_off=True,
            checklist_complete=True,
        )
        warns = [g for g in rv.gates if g.status == GateStatus.WARN]
        assert len(warns) >= 1
        assert rv.release_approved is True  # warn doesn't block

    def test_performance_degraded_non_blocking(self):
        validator = ReleaseValidator()
        rv = validator.validate(
            test_pass_rate=100.0,
            security_findings_critical=0,
            uat_signed_off=True,
            checklist_complete=True,
            performance_acceptable=False,
        )
        assert rv.release_approved is True  # performance is non-required

    def test_release_gate_counts(self):
        rv = ReleaseValidation(gates=[
            ReleaseGate("a", GateStatus.PASS),
            ReleaseGate("b", GateStatus.FAIL),
            ReleaseGate("c", GateStatus.PASS),
        ])
        assert rv.pass_count == 2
        assert rv.fail_count == 1


# ===================================================================
# PerformanceBaseline
# ===================================================================


class TestPerformanceBaseline:
    def test_set_and_compare(self):
        pb = PerformanceBaseline()
        pb.set_baseline(PerformanceMetric("query_time", 100.0, "ms"))
        pb.record_current(PerformanceMetric("query_time", 105.0, "ms"))
        comps = pb.compare()
        assert len(comps) == 1
        assert comps[0].change_pct == pytest.approx(5.0)
        assert comps[0].regression is False

    def test_regression_detected(self):
        pb = PerformanceBaseline()
        pb.set_baseline(PerformanceMetric("query_time", 100.0, "ms"))
        pb.record_current(PerformanceMetric("query_time", 150.0, "ms"))
        assert pb.has_regressions(threshold_pct=10.0) is True

    def test_no_regression(self):
        pb = PerformanceBaseline()
        pb.set_baseline(PerformanceMetric("query_time", 100.0, "ms"))
        pb.record_current(PerformanceMetric("query_time", 105.0, "ms"))
        assert pb.has_regressions(threshold_pct=10.0) is False

    def test_set_baselines_batch(self):
        pb = PerformanceBaseline()
        pb.set_baselines([
            PerformanceMetric("a", 10),
            PerformanceMetric("b", 20),
        ])
        assert pb.baseline_count == 2

    def test_record_currents_batch(self):
        pb = PerformanceBaseline()
        pb.record_currents([
            PerformanceMetric("a", 11),
            PerformanceMetric("b", 22),
        ])
        assert pb.current_count == 2

    def test_compare_missing_current(self):
        pb = PerformanceBaseline()
        pb.set_baseline(PerformanceMetric("a", 10))
        comps = pb.compare()
        assert len(comps) == 0  # no current for 'a'

    def test_generate_report(self):
        pb = PerformanceBaseline()
        pb.set_baseline(PerformanceMetric("query_ms", 100.0, "ms"))
        pb.record_current(PerformanceMetric("query_ms", 120.0, "ms"))
        md = pb.generate_report()
        assert "Performance Baseline Report" in md
        assert "query_ms" in md

    def test_baseline_comparison_zero_baseline(self):
        comp = BaselineComparison(metric_name="x", baseline_value=0.0, current_value=10.0)
        comp.evaluate()
        assert comp.regression is False
        assert comp.change_pct == 0.0

    def test_baseline_comparison_regression(self):
        comp = BaselineComparison(metric_name="x", baseline_value=100.0,
                                   current_value=115.0, threshold_pct=10.0)
        is_reg = comp.evaluate()
        assert is_reg is True
        assert comp.change_pct == pytest.approx(15.0)

    def test_metric_timestamp(self):
        m = PerformanceMetric("test", 42.0)
        assert m.timestamp  # auto-generated


# ===================================================================
# Enums
# ===================================================================


class TestChaosEnums:
    def test_fault_type_values(self):
        assert FaultType.NETWORK_TIMEOUT.value == "network_timeout"
        assert FaultType.RATE_LIMIT.value == "rate_limit"

    def test_fault_severity_values(self):
        assert FaultSeverity.LOW.value == "low"
        assert FaultSeverity.CRITICAL.value == "critical"

    def test_security_finding_types(self):
        assert SecurityFindingType.HARDCODED_CREDENTIAL.value == "hardcoded_credential"
        assert SecurityFindingType.UNMASKED_PII.value == "unmasked_pii"

    def test_gate_status_values(self):
        assert GateStatus.PASS.value == "pass"
        assert GateStatus.FAIL.value == "fail"
