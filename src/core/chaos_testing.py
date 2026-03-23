"""Chaos testing & production hardening — fault injection, recovery verification.

Provides:
- ``FaultType`` / ``FaultScenario`` — define injectable faults.
- ``ChaosSimulator`` — inject and manage faults during test runs.
- ``RecoveryVerifier`` — verify system recovery after faults.
- ``SecurityScanner`` — scan for common security issues in migration artifacts.
- ``ReleaseValidator`` — pre-release validation gates.
- ``PerformanceBaseline`` — capture and compare performance baselines.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fault injection
# ---------------------------------------------------------------------------


class FaultType(str, Enum):
    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_REFUSED = "connection_refused"
    DISK_FULL = "disk_full"
    OOM = "out_of_memory"
    CORRUPT_DATA = "corrupt_data"
    PERMISSION_DENIED = "permission_denied"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMIT = "rate_limit"
    SLOW_RESPONSE = "slow_response"
    PARTIAL_FAILURE = "partial_failure"


class FaultSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FaultScenario:
    """A scenario that injects a specific fault."""
    scenario_id: str = ""
    name: str = ""
    fault_type: FaultType = FaultType.NETWORK_TIMEOUT
    severity: FaultSeverity = FaultSeverity.MEDIUM
    target_component: str = ""  # which component to inject into
    duration_seconds: float = 5.0
    probability: float = 1.0  # 0..1, chance of fault activating
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.scenario_id:
            self.scenario_id = f"FAULT-{uuid.uuid4().hex[:8]}"

    def should_activate(self) -> bool:
        """Decide whether to activate based on probability."""
        return random.random() < self.probability


@dataclass
class FaultInjectionResult:
    """Result of a fault injection."""
    scenario_id: str = ""
    activated: bool = False
    start_time: str = ""
    end_time: str = ""
    affected_operations: int = 0
    error_raised: str = ""
    recovered: bool = False
    recovery_time_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.start_time:
            self.start_time = datetime.now(timezone.utc).isoformat()


class ChaosSimulator:
    """Inject and manage faults during test runs.

    Supports pre-built scenarios and custom fault injection.
    """

    # Pre-defined chaos scenarios
    BUILTIN_SCENARIOS: list[dict[str, Any]] = [
        {"name": "Source DB timeout", "fault_type": FaultType.NETWORK_TIMEOUT,
         "target_component": "source_connector", "severity": FaultSeverity.HIGH,
         "duration_seconds": 10.0, "description": "Simulate source database timeout"},
        {"name": "Fabric API 503", "fault_type": FaultType.SERVICE_UNAVAILABLE,
         "target_component": "fabric_deployer", "severity": FaultSeverity.HIGH,
         "duration_seconds": 30.0, "description": "Simulate Fabric API unavailable"},
        {"name": "Rate limited", "fault_type": FaultType.RATE_LIMIT,
         "target_component": "azure_openai", "severity": FaultSeverity.MEDIUM,
         "duration_seconds": 5.0, "description": "Simulate Azure OpenAI 429"},
        {"name": "Disk full", "fault_type": FaultType.DISK_FULL,
         "target_component": "staging_area", "severity": FaultSeverity.CRITICAL,
         "duration_seconds": 0, "description": "Simulate disk full during data copy"},
        {"name": "Corrupt RPD", "fault_type": FaultType.CORRUPT_DATA,
         "target_component": "rpd_parser", "severity": FaultSeverity.MEDIUM,
         "description": "Inject corrupt XML in RPD"},
        {"name": "Slow Lakehouse", "fault_type": FaultType.SLOW_RESPONSE,
         "target_component": "lakehouse_client", "severity": FaultSeverity.LOW,
         "duration_seconds": 15.0, "parameters": {"latency_ms": 5000},
         "description": "Simulate slow Lakehouse responses"},
    ]

    def __init__(self) -> None:
        self._scenarios: dict[str, FaultScenario] = {}
        self._results: list[FaultInjectionResult] = []
        self._active_faults: dict[str, FaultScenario] = {}

    def load_builtins(self) -> None:
        """Load pre-defined chaos scenarios."""
        for s in self.BUILTIN_SCENARIOS:
            scenario = FaultScenario(**s)
            self._scenarios[scenario.scenario_id] = scenario

    def add_scenario(self, scenario: FaultScenario) -> None:
        self._scenarios[scenario.scenario_id] = scenario

    def get_scenario(self, scenario_id: str) -> FaultScenario | None:
        return self._scenarios.get(scenario_id)

    @property
    def all_scenarios(self) -> list[FaultScenario]:
        return list(self._scenarios.values())

    def inject(self, scenario_id: str) -> FaultInjectionResult:
        """Inject a fault (simulate it)."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return FaultInjectionResult(scenario_id=scenario_id, activated=False,
                                         error_raised="Scenario not found")

        result = FaultInjectionResult(scenario_id=scenario_id)

        if scenario.should_activate():
            result.activated = True
            self._active_faults[scenario_id] = scenario
            result.affected_operations = 1
            logger.info(f"Chaos: Injected {scenario.fault_type.value} into {scenario.target_component}")
        else:
            result.activated = False

        self._results.append(result)
        return result

    def clear_fault(self, scenario_id: str) -> bool:
        """Clear an active fault."""
        if scenario_id in self._active_faults:
            del self._active_faults[scenario_id]
            return True
        return False

    def clear_all(self) -> int:
        """Clear all active faults."""
        count = len(self._active_faults)
        self._active_faults.clear()
        return count

    @property
    def active_fault_count(self) -> int:
        return len(self._active_faults)

    @property
    def all_results(self) -> list[FaultInjectionResult]:
        return list(self._results)

    def is_component_faulted(self, component: str) -> bool:
        """Check if a specific component has an active fault."""
        return any(s.target_component == component for s in self._active_faults.values())

    def run_chaos_round(self) -> list[FaultInjectionResult]:
        """Inject all scenarios in random order."""
        results = []
        scenario_ids = list(self._scenarios.keys())
        random.shuffle(scenario_ids)
        for sid in scenario_ids:
            results.append(self.inject(sid))
        return results


# ---------------------------------------------------------------------------
# Recovery verification
# ---------------------------------------------------------------------------


@dataclass
class RecoveryCheck:
    """A single recovery check."""
    name: str = ""
    passed: bool = False
    message: str = ""
    recovery_time_seconds: float = 0.0


@dataclass
class RecoveryReport:
    """Report of recovery verification."""
    checks: list[RecoveryCheck] = field(default_factory=list)
    overall_recovered: bool = True
    total_recovery_time: float = 0.0

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    def summary(self) -> str:
        return (
            f"Recovery: {self.pass_count}/{len(self.checks)} passed, "
            f"total recovery time: {self.total_recovery_time:.1f}s — "
            f"{'RECOVERED' if self.overall_recovered else 'NOT RECOVERED'}"
        )


class RecoveryVerifier:
    """Verify system recovery after faults are cleared."""

    def verify(self, simulator: ChaosSimulator, component_checks: dict[str, bool] | None = None) -> RecoveryReport:
        """Verify recovery.

        component_checks: component_name → is_healthy (True/False).
        """
        report = RecoveryReport()
        component_checks = component_checks or {}

        # Check that all faults are cleared
        if simulator.active_fault_count > 0:
            report.checks.append(RecoveryCheck(
                name="active_faults_cleared",
                passed=False,
                message=f"{simulator.active_fault_count} faults still active",
            ))
            report.overall_recovered = False
        else:
            report.checks.append(RecoveryCheck(
                name="active_faults_cleared",
                passed=True,
                message="All faults cleared",
            ))

        # Check component health
        for component, healthy in component_checks.items():
            report.checks.append(RecoveryCheck(
                name=f"component_{component}",
                passed=healthy,
                message=f"{component}: {'healthy' if healthy else 'unhealthy'}",
            ))
            if not healthy:
                report.overall_recovered = False

        # Analyze injection results for recovery times
        for result in simulator.all_results:
            if result.activated and result.recovery_time_seconds > 0:
                report.total_recovery_time += result.recovery_time_seconds

        return report


# ---------------------------------------------------------------------------
# Security scanner
# ---------------------------------------------------------------------------


class SecurityFindingType(str, Enum):
    HARDCODED_CREDENTIAL = "hardcoded_credential"
    INSECURE_CONNECTION = "insecure_connection"
    MISSING_ENCRYPTION = "missing_encryption"
    OVERPRIVILEGED_ROLE = "overprivileged_role"
    EXPOSED_API_KEY = "exposed_api_key"
    MISSING_RLS = "missing_rls"
    WEAK_PASSWORD = "weak_password"
    UNMASKED_PII = "unmasked_pii"


@dataclass
class SecurityFinding:
    """A security finding."""
    finding_id: str = ""
    finding_type: SecurityFindingType = SecurityFindingType.HARDCODED_CREDENTIAL
    severity: str = "medium"
    location: str = ""
    description: str = ""
    recommendation: str = ""

    def __post_init__(self) -> None:
        if not self.finding_id:
            self.finding_id = f"SEC-{uuid.uuid4().hex[:6]}"


class SecurityScanner:
    """Scan migration artifacts for common security issues."""

    # Patterns that indicate potential security issues
    CREDENTIAL_PATTERNS = [
        "password=", "pwd=", "secret=", "api_key=", "apikey=",
        "token=", "access_key=", "private_key=",
    ]

    INSECURE_PATTERNS = [
        "http://", "jdbc:oracle:thin:@//", "Allow_Self_Signed=True",
    ]

    PII_PATTERNS = [
        "ssn", "social_security", "credit_card", "card_number",
        "date_of_birth", "dob", "passport",
    ]

    def scan_text(self, text: str, source: str = "") -> list[SecurityFinding]:
        """Scan text content for security issues."""
        findings: list[SecurityFinding] = []
        text_lower = text.lower()

        # Check for credentials
        for pattern in self.CREDENTIAL_PATTERNS:
            if pattern.lower() in text_lower:
                findings.append(SecurityFinding(
                    finding_type=SecurityFindingType.HARDCODED_CREDENTIAL,
                    severity="critical",
                    location=source,
                    description=f"Potential hardcoded credential: '{pattern}'",
                    recommendation="Use environment variables or Azure Key Vault",
                ))

        # Check for insecure connections
        for pattern in self.INSECURE_PATTERNS:
            if pattern.lower() in text_lower:
                findings.append(SecurityFinding(
                    finding_type=SecurityFindingType.INSECURE_CONNECTION,
                    severity="high",
                    location=source,
                    description=f"Insecure connection pattern: '{pattern}'",
                    recommendation="Use HTTPS/TLS encrypted connections",
                ))

        # Check for PII
        for pattern in self.PII_PATTERNS:
            if pattern.lower() in text_lower:
                findings.append(SecurityFinding(
                    finding_type=SecurityFindingType.UNMASKED_PII,
                    severity="high",
                    location=source,
                    description=f"Potential unmasked PII field: '{pattern}'",
                    recommendation="Apply data masking or sensitivity labels",
                ))

        return findings

    def scan_artifacts(self, artifacts: list[dict[str, str]]) -> list[SecurityFinding]:
        """Scan multiple artifacts. Each dict has 'name' and 'content'."""
        all_findings: list[SecurityFinding] = []
        for artifact in artifacts:
            name = artifact.get("name", "unknown")
            content = artifact.get("content", "")
            findings = self.scan_text(content, source=name)
            all_findings.extend(findings)
        return all_findings

    def check_rls_coverage(self, tables: list[str], rls_tables: list[str]) -> list[SecurityFinding]:
        """Check that all tables with sensitive data have RLS."""
        findings: list[SecurityFinding] = []
        uncovered = set(tables) - set(rls_tables)
        for table in uncovered:
            findings.append(SecurityFinding(
                finding_type=SecurityFindingType.MISSING_RLS,
                severity="medium",
                location=table,
                description=f"Table '{table}' has no RLS role",
                recommendation="Add RLS role or confirm data is non-sensitive",
            ))
        return findings

    def generate_report(self, findings: list[SecurityFinding]) -> str:
        """Generate a markdown security report."""
        lines = ["# Security Scan Report\n"]
        lines.append(f"**Findings**: {len(findings)}")

        by_severity: dict[str, int] = {}
        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        for sev, count in sorted(by_severity.items()):
            lines.append(f"- {sev}: {count}")
        lines.append("")

        if findings:
            lines.append("## Details\n")
            for f in findings:
                lines.append(f"### {f.finding_id} [{f.severity.upper()}]")
                lines.append(f"- **Type**: {f.finding_type.value}")
                lines.append(f"- **Location**: {f.location}")
                lines.append(f"- **Description**: {f.description}")
                lines.append(f"- **Fix**: {f.recommendation}")
                lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Release validator
# ---------------------------------------------------------------------------


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class ReleaseGate:
    """A single release validation gate."""
    name: str = ""
    status: GateStatus = GateStatus.SKIP
    message: str = ""
    required: bool = True  # if True, FAIL blocks release


@dataclass
class ReleaseValidation:
    """Result of release validation."""
    gates: list[ReleaseGate] = field(default_factory=list)
    release_approved: bool = False

    @property
    def pass_count(self) -> int:
        return sum(1 for g in self.gates if g.status == GateStatus.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for g in self.gates if g.status == GateStatus.FAIL)

    def evaluate(self) -> bool:
        """Determine if release is approved (no required gates failed)."""
        self.release_approved = not any(
            g.status == GateStatus.FAIL and g.required for g in self.gates
        )
        return self.release_approved


class ReleaseValidator:
    """Pre-release validation gates."""

    def validate(
        self,
        test_pass_rate: float,
        security_findings_critical: int,
        uat_signed_off: bool,
        checklist_complete: bool,
        data_validated: bool = True,
        performance_acceptable: bool = True,
    ) -> ReleaseValidation:
        """Run all release gates."""
        rv = ReleaseValidation()

        # Test pass rate
        if test_pass_rate >= 100.0:
            rv.gates.append(ReleaseGate("test_pass_rate", GateStatus.PASS,
                                         f"Tests: {test_pass_rate:.1f}%"))
        elif test_pass_rate >= 95.0:
            rv.gates.append(ReleaseGate("test_pass_rate", GateStatus.WARN,
                                         f"Tests: {test_pass_rate:.1f}% (below 100%)"))
        else:
            rv.gates.append(ReleaseGate("test_pass_rate", GateStatus.FAIL,
                                         f"Tests: {test_pass_rate:.1f}% (below 95%)"))

        # Security
        if security_findings_critical == 0:
            rv.gates.append(ReleaseGate("security", GateStatus.PASS, "No critical findings"))
        else:
            rv.gates.append(ReleaseGate("security", GateStatus.FAIL,
                                         f"{security_findings_critical} critical findings"))

        # UAT
        if uat_signed_off:
            rv.gates.append(ReleaseGate("uat_signoff", GateStatus.PASS, "UAT signed off"))
        else:
            rv.gates.append(ReleaseGate("uat_signoff", GateStatus.FAIL, "UAT not signed off"))

        # Checklist
        if checklist_complete:
            rv.gates.append(ReleaseGate("checklist", GateStatus.PASS, "Checklist complete"))
        else:
            rv.gates.append(ReleaseGate("checklist", GateStatus.FAIL, "Checklist incomplete"))

        # Data validation
        if data_validated:
            rv.gates.append(ReleaseGate("data_validation", GateStatus.PASS, "Data validated"))
        else:
            rv.gates.append(ReleaseGate("data_validation", GateStatus.FAIL, "Data not validated"))

        # Performance
        if performance_acceptable:
            rv.gates.append(ReleaseGate("performance", GateStatus.PASS, "Performance OK",
                                         required=False))
        else:
            rv.gates.append(ReleaseGate("performance", GateStatus.WARN, "Performance degraded",
                                         required=False))

        rv.evaluate()
        return rv


# ---------------------------------------------------------------------------
# Performance baseline
# ---------------------------------------------------------------------------


@dataclass
class PerformanceMetric:
    """A single performance measurement."""
    name: str = ""
    value: float = 0.0
    unit: str = ""  # "ms", "seconds", "rows/sec", "MB/s"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class BaselineComparison:
    """Comparison of current metrics against a baseline."""
    metric_name: str = ""
    baseline_value: float = 0.0
    current_value: float = 0.0
    change_pct: float = 0.0
    regression: bool = False
    threshold_pct: float = 10.0  # % change that counts as regression

    def evaluate(self) -> bool:
        """Evaluate whether this is a regression."""
        if self.baseline_value == 0:
            self.change_pct = 0.0
            self.regression = False
        else:
            self.change_pct = ((self.current_value - self.baseline_value) / self.baseline_value) * 100
            self.regression = self.change_pct > self.threshold_pct
        return self.regression


class PerformanceBaseline:
    """Capture and compare performance baselines."""

    def __init__(self) -> None:
        self._baselines: dict[str, PerformanceMetric] = {}
        self._current: dict[str, PerformanceMetric] = {}

    def set_baseline(self, metric: PerformanceMetric) -> None:
        self._baselines[metric.name] = metric

    def record_current(self, metric: PerformanceMetric) -> None:
        self._current[metric.name] = metric

    def set_baselines(self, metrics: list[PerformanceMetric]) -> None:
        for m in metrics:
            self._baselines[m.name] = m

    def record_currents(self, metrics: list[PerformanceMetric]) -> None:
        for m in metrics:
            self._current[m.name] = m

    @property
    def baseline_count(self) -> int:
        return len(self._baselines)

    @property
    def current_count(self) -> int:
        return len(self._current)

    def compare(self, threshold_pct: float = 10.0) -> list[BaselineComparison]:
        """Compare current metrics against baselines."""
        comparisons: list[BaselineComparison] = []
        for name, baseline in self._baselines.items():
            current = self._current.get(name)
            if current:
                comp = BaselineComparison(
                    metric_name=name,
                    baseline_value=baseline.value,
                    current_value=current.value,
                    threshold_pct=threshold_pct,
                )
                comp.evaluate()
                comparisons.append(comp)
        return comparisons

    def has_regressions(self, threshold_pct: float = 10.0) -> bool:
        """Check if any metrics regressed beyond threshold."""
        return any(c.regression for c in self.compare(threshold_pct))

    def generate_report(self, threshold_pct: float = 10.0) -> str:
        """Generate a markdown performance report."""
        comparisons = self.compare(threshold_pct)
        lines = ["# Performance Baseline Report\n"]
        lines.append(f"**Metrics compared**: {len(comparisons)}")
        regressions = sum(1 for c in comparisons if c.regression)
        lines.append(f"**Regressions**: {regressions}")
        lines.append("")

        if comparisons:
            lines.append("| Metric | Baseline | Current | Change | Status |")
            lines.append("|--------|----------|---------|--------|--------|")
            for c in comparisons:
                status = "REGRESSION" if c.regression else "OK"
                lines.append(
                    f"| {c.metric_name} | {c.baseline_value:.2f} | "
                    f"{c.current_value:.2f} | {c.change_pct:+.1f}% | {status} |"
                )
        return "\n".join(lines)
