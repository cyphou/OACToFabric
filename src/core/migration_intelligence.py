"""Migration intelligence — complexity analysis, cost estimation, preflight checks.

Provides:
- ``ComplexityDimension`` / ``ComplexityScore`` — multi-dimensional complexity.
- ``ComplexityAnalyzer`` — score individual assets and full inventories.
- ``CostEstimator`` — estimate Fabric compute costs for a migration.
- ``TimelineEstimator`` — estimate wall-clock duration for a migration.
- ``PreflightChecker`` — run pre-migration readiness checks.
- ``RiskScorer`` — aggregate risk across dimensions.
- ``AssessmentReport`` — composite assessment report.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Complexity analysis
# ---------------------------------------------------------------------------


class ComplexityDimension(str, Enum):
    SCHEMA = "schema"
    CALCULATIONS = "calculations"
    SECURITY = "security"
    VISUALIZATIONS = "visualizations"
    DATA_VOLUME = "data_volume"
    DEPENDENCIES = "dependencies"
    CUSTOM_CODE = "custom_code"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplexityScore:
    """Multi-dimensional complexity score for a migration asset."""
    asset_name: str
    asset_type: str
    scores: dict[str, float] = field(default_factory=dict)  # dimension → 0..10
    overall: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    notes: list[str] = field(default_factory=list)

    def compute_overall(self, weights: dict[str, float] | None = None) -> float:
        """Compute weighted overall score."""
        if not self.scores:
            self.overall = 0.0
            return 0.0
        if weights is None:
            weights = {d: 1.0 for d in self.scores}
        total_weight = sum(weights.get(d, 1.0) for d in self.scores)
        if total_weight == 0:
            self.overall = 0.0
            return 0.0
        weighted = sum(self.scores[d] * weights.get(d, 1.0) for d in self.scores)
        self.overall = weighted / total_weight
        # Derive risk level
        if self.overall >= 8.0:
            self.risk_level = RiskLevel.CRITICAL
        elif self.overall >= 6.0:
            self.risk_level = RiskLevel.HIGH
        elif self.overall >= 4.0:
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW
        return self.overall


class ComplexityAnalyzer:
    """Analyze migration complexity for assets."""

    # Default weights per dimension
    DEFAULT_WEIGHTS: dict[str, float] = {
        ComplexityDimension.SCHEMA.value: 1.0,
        ComplexityDimension.CALCULATIONS.value: 2.0,
        ComplexityDimension.SECURITY.value: 1.5,
        ComplexityDimension.VISUALIZATIONS.value: 1.0,
        ComplexityDimension.DATA_VOLUME.value: 1.5,
        ComplexityDimension.DEPENDENCIES.value: 1.5,
        ComplexityDimension.CUSTOM_CODE.value: 2.0,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    def score_asset(self, asset: dict[str, Any]) -> ComplexityScore:
        """Score a single asset dict.

        Expected keys: name, type, tables, calculations, rls_roles,
        visuals, row_count, dependencies, custom_sql
        """
        name = asset.get("name", "unknown")
        asset_type = asset.get("type", "unknown")
        cs = ComplexityScore(asset_name=name, asset_type=asset_type)

        # Schema complexity: number of tables
        tables = asset.get("tables", 0)
        cs.scores[ComplexityDimension.SCHEMA.value] = min(10.0, tables / 10.0 * 10.0)

        # Calculations complexity
        calcs = asset.get("calculations", 0)
        cs.scores[ComplexityDimension.CALCULATIONS.value] = min(10.0, calcs / 50.0 * 10.0)

        # Security complexity
        rls = asset.get("rls_roles", 0)
        cs.scores[ComplexityDimension.SECURITY.value] = min(10.0, rls / 5.0 * 10.0)
        if rls > 10:
            cs.notes.append(f"High RLS role count: {rls}")

        # Visualization complexity
        visuals = asset.get("visuals", 0)
        cs.scores[ComplexityDimension.VISUALIZATIONS.value] = min(10.0, visuals / 30.0 * 10.0)

        # Data volume
        rows = asset.get("row_count", 0)
        if rows > 0:
            cs.scores[ComplexityDimension.DATA_VOLUME.value] = min(10.0, math.log10(max(1, rows)) / 9.0 * 10.0)
        else:
            cs.scores[ComplexityDimension.DATA_VOLUME.value] = 0.0

        # Dependencies
        deps = asset.get("dependencies", 0)
        cs.scores[ComplexityDimension.DEPENDENCIES.value] = min(10.0, deps / 10.0 * 10.0)

        # Custom code (SQL/PLSQL)
        custom = asset.get("custom_sql", 0)
        cs.scores[ComplexityDimension.CUSTOM_CODE.value] = min(10.0, custom / 20.0 * 10.0)
        if custom > 10:
            cs.notes.append(f"Significant custom SQL: {custom} blocks")

        cs.compute_overall(self.weights)
        return cs

    def score_inventory(self, assets: list[dict[str, Any]]) -> list[ComplexityScore]:
        """Score all assets in an inventory."""
        return [self.score_asset(a) for a in assets]

    def summary(self, scores: list[ComplexityScore]) -> dict[str, Any]:
        """Summarize scored inventory."""
        if not scores:
            return {"total": 0, "avg_complexity": 0.0, "by_risk": {}}
        by_risk: dict[str, int] = {}
        for s in scores:
            by_risk[s.risk_level.value] = by_risk.get(s.risk_level.value, 0) + 1
        return {
            "total": len(scores),
            "avg_complexity": round(sum(s.overall for s in scores) / len(scores), 2),
            "by_risk": by_risk,
            "max_complexity": round(max(s.overall for s in scores), 2),
            "min_complexity": round(min(s.overall for s in scores), 2),
        }


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


@dataclass
class CostEstimate:
    """Estimated costs for a migration."""
    compute_hours: float = 0.0
    fabric_cu_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    storage_gb: float = 0.0
    storage_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    breakdown: dict[str, float] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)

    def compute_total(self) -> float:
        self.total_cost_usd = self.estimated_cost_usd + self.storage_cost_usd
        return self.total_cost_usd


class CostEstimator:
    """Estimate Fabric compute and storage costs for a migration.

    Uses configurable rate cards.
    """

    def __init__(
        self,
        cu_price_per_hour: float = 0.18,  # USD per CU-hour
        storage_price_per_gb: float = 0.023,  # USD per GB-month
        data_transfer_gb_price: float = 0.01,
    ) -> None:
        self.cu_price_per_hour = cu_price_per_hour
        self.storage_price_per_gb = storage_price_per_gb
        self.data_transfer_gb_price = data_transfer_gb_price

    def estimate(
        self,
        total_rows: int,
        total_tables: int,
        total_calculations: int,
        total_reports: int,
        avg_row_bytes: int = 200,
    ) -> CostEstimate:
        """Produce a cost estimate based on migration scope."""
        est = CostEstimate()

        # Storage
        est.storage_gb = (total_rows * avg_row_bytes) / (1024 ** 3)
        est.storage_cost_usd = est.storage_gb * self.storage_price_per_gb

        # Compute — model: tables take time to copy, calculations take time to translate
        copy_hours = total_tables * 0.1  # ~6 min per table copy
        transform_hours = total_calculations * 0.02  # ~1.2 min per calculation
        report_hours = total_reports * 0.05  # ~3 min per report
        est.compute_hours = copy_hours + transform_hours + report_hours

        # Fabric CU-seconds (approximate: 1 CU-hour = 3600 CU-seconds)
        est.fabric_cu_seconds = est.compute_hours * 3600

        est.estimated_cost_usd = est.compute_hours * self.cu_price_per_hour

        # Data transfer
        transfer_cost = est.storage_gb * self.data_transfer_gb_price
        est.estimated_cost_usd += transfer_cost

        est.breakdown = {
            "data_copy": round(copy_hours * self.cu_price_per_hour, 2),
            "translation": round(transform_hours * self.cu_price_per_hour, 2),
            "report_gen": round(report_hours * self.cu_price_per_hour, 2),
            "data_transfer": round(transfer_cost, 2),
            "storage": round(est.storage_cost_usd, 2),
        }

        est.assumptions = [
            f"CU price: ${self.cu_price_per_hour}/CU-hour",
            f"Storage price: ${self.storage_price_per_gb}/GB-month",
            f"Avg row size: {avg_row_bytes} bytes",
        ]

        est.compute_total()
        return est


# ---------------------------------------------------------------------------
# Timeline estimation
# ---------------------------------------------------------------------------


@dataclass
class TimelineEstimate:
    """Estimated wall-clock timeline for a migration."""
    total_days: float = 0.0
    phases: dict[str, float] = field(default_factory=dict)  # phase → days
    parallel_factor: float = 1.0
    buffer_pct: float = 0.2
    buffered_days: float = 0.0

    def compute_buffered(self) -> float:
        self.buffered_days = self.total_days * (1 + self.buffer_pct)
        return self.buffered_days


class TimelineEstimator:
    """Estimate migration timeline based on scope and team size."""

    def __init__(
        self,
        team_size: int = 2,
        hours_per_day: float = 6.0,  # effective hours
    ) -> None:
        self.team_size = max(1, team_size)
        self.hours_per_day = hours_per_day

    def estimate(
        self,
        total_tables: int,
        total_calculations: int,
        total_reports: int,
        total_rls_roles: int = 0,
        complexity_avg: float = 5.0,
    ) -> TimelineEstimate:
        """Estimate timeline in business days."""
        te = TimelineEstimate()
        complexity_factor = 0.5 + (complexity_avg / 10.0)

        # Discovery & planning: fixed + scope-based
        discovery_hrs = 8 + total_tables * 0.1
        te.phases["discovery"] = discovery_hrs / self.hours_per_day

        # Schema migration
        schema_hrs = total_tables * 0.5 * complexity_factor
        te.phases["schema"] = schema_hrs / self.hours_per_day

        # Data pipeline
        pipeline_hrs = total_tables * 1.0 * complexity_factor
        te.phases["data_pipeline"] = pipeline_hrs / self.hours_per_day

        # Semantic model + calculations
        calc_hrs = total_calculations * 0.3 * complexity_factor
        te.phases["semantic_model"] = calc_hrs / self.hours_per_day

        # Reports
        report_hrs = total_reports * 1.5 * complexity_factor
        te.phases["reports"] = report_hrs / self.hours_per_day

        # Security
        security_hrs = max(4, total_rls_roles * 2.0)
        te.phases["security"] = security_hrs / self.hours_per_day

        # Validation
        validation_hrs = sum(te.phases.values()) * self.hours_per_day * 0.3
        te.phases["validation"] = validation_hrs / self.hours_per_day

        # Total with team parallelism
        raw_days = sum(te.phases.values())
        te.parallel_factor = min(self.team_size, 3)  # diminishing returns above 3
        te.total_days = raw_days / te.parallel_factor
        te.compute_buffered()

        return te


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------


class CheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class PreflightCheck:
    """A single preflight check result."""
    name: str
    status: CheckStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreflightResult:
    """Aggregate preflight check results."""
    checks: list[PreflightCheck] = field(default_factory=list)
    overall_ready: bool = True

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.WARN)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    def summary(self) -> str:
        return (
            f"Preflight: {self.pass_count} pass, {self.warn_count} warn, "
            f"{self.fail_count} fail — {'READY' if self.overall_ready else 'NOT READY'}"
        )


class PreflightChecker:
    """Run pre-migration readiness checks."""

    def check(self, config: dict[str, Any]) -> PreflightResult:
        """Run all preflight checks against a config dict.

        Expected config keys: source_connection, fabric_workspace,
        fabric_capacity, azure_openai_key, tables, calculations,
        disk_space_gb, estimated_data_gb
        """
        result = PreflightResult()

        # 1. Source connection
        src = config.get("source_connection")
        if src:
            result.checks.append(PreflightCheck("source_connection", CheckStatus.PASS, "Source configured"))
        else:
            result.checks.append(PreflightCheck("source_connection", CheckStatus.FAIL, "No source connection"))
            result.overall_ready = False

        # 2. Fabric workspace
        ws = config.get("fabric_workspace")
        if ws:
            result.checks.append(PreflightCheck("fabric_workspace", CheckStatus.PASS, f"Workspace: {ws}"))
        else:
            result.checks.append(PreflightCheck("fabric_workspace", CheckStatus.FAIL, "No Fabric workspace"))
            result.overall_ready = False

        # 3. Fabric capacity
        cap = config.get("fabric_capacity")
        if cap:
            result.checks.append(PreflightCheck("fabric_capacity", CheckStatus.PASS, f"Capacity: {cap}"))
        else:
            result.checks.append(PreflightCheck("fabric_capacity", CheckStatus.WARN, "No capacity specified"))

        # 4. Azure OpenAI
        ai = config.get("azure_openai_key")
        if ai:
            result.checks.append(PreflightCheck("azure_openai", CheckStatus.PASS, "OpenAI key present"))
        else:
            result.checks.append(PreflightCheck("azure_openai", CheckStatus.WARN, "No OpenAI key — LLM translation disabled"))

        # 5. Scope sanity
        tables = config.get("tables", 0)
        calcs = config.get("calculations", 0)
        if tables > 500:
            result.checks.append(PreflightCheck("scope_tables", CheckStatus.WARN, f"{tables} tables — consider phased migration"))
        elif tables > 0:
            result.checks.append(PreflightCheck("scope_tables", CheckStatus.PASS, f"{tables} tables"))
        else:
            result.checks.append(PreflightCheck("scope_tables", CheckStatus.FAIL, "No tables specified"))
            result.overall_ready = False

        # 6. Disk space
        disk = config.get("disk_space_gb", 0)
        data_gb = config.get("estimated_data_gb", 0)
        if disk > 0 and data_gb > 0:
            if disk < data_gb * 2:
                result.checks.append(PreflightCheck("disk_space", CheckStatus.WARN,
                                                      f"Tight disk space: {disk}GB for {data_gb}GB data"))
            else:
                result.checks.append(PreflightCheck("disk_space", CheckStatus.PASS, f"{disk}GB available"))
        else:
            result.checks.append(PreflightCheck("disk_space", CheckStatus.SKIP, "Disk check skipped"))

        return result


# ---------------------------------------------------------------------------
# Risk scorer
# ---------------------------------------------------------------------------


@dataclass
class RiskFactor:
    """A risk factor with impact and likelihood."""
    name: str
    description: str
    likelihood: float  # 0..1
    impact: float  # 0..10
    mitigation: str = ""

    @property
    def risk_score(self) -> float:
        return self.likelihood * self.impact


@dataclass
class RiskAssessment:
    """Aggregate risk assessment."""
    factors: list[RiskFactor] = field(default_factory=list)
    overall_risk: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW

    def compute_overall(self) -> float:
        if not self.factors:
            self.overall_risk = 0.0
            self.risk_level = RiskLevel.LOW
            return 0.0
        self.overall_risk = sum(f.risk_score for f in self.factors) / len(self.factors)
        if self.overall_risk >= 7.0:
            self.risk_level = RiskLevel.CRITICAL
        elif self.overall_risk >= 5.0:
            self.risk_level = RiskLevel.HIGH
        elif self.overall_risk >= 3.0:
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW
        return self.overall_risk


class RiskScorer:
    """Assess migration risks from complexity scores and config."""

    def assess(
        self,
        scores: list[ComplexityScore],
        config: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Produce a risk assessment."""
        ra = RiskAssessment()
        config = config or {}

        if not scores:
            ra.compute_overall()
            return ra

        avg_complexity = sum(s.overall for s in scores) / len(scores)
        max_complexity = max(s.overall for s in scores)

        # R1: High average complexity
        if avg_complexity > 5.0:
            ra.factors.append(RiskFactor(
                "high_complexity", f"Average complexity {avg_complexity:.1f}/10",
                likelihood=0.7, impact=avg_complexity,
                mitigation="Break into smaller waves",
            ))

        # R2: Extreme outlier
        if max_complexity > 8.0:
            ra.factors.append(RiskFactor(
                "complexity_outlier", f"Max complexity {max_complexity:.1f}/10",
                likelihood=0.8, impact=max_complexity,
                mitigation="Dedicated team for complex assets",
            ))

        # R3: Large scope
        if len(scores) > 100:
            ra.factors.append(RiskFactor(
                "large_scope", f"{len(scores)} assets to migrate",
                likelihood=0.5, impact=6.0,
                mitigation="Phased rollout with wave planning",
            ))

        # R4: Custom code
        custom_heavy = [s for s in scores if s.scores.get("custom_code", 0) > 7]
        if custom_heavy:
            ra.factors.append(RiskFactor(
                "custom_code", f"{len(custom_heavy)} assets with heavy custom code",
                likelihood=0.6, impact=7.0,
                mitigation="Manual review and rewrite for custom SQL",
            ))

        # R5: No AI key
        if not config.get("azure_openai_key"):
            ra.factors.append(RiskFactor(
                "no_llm", "No LLM key — translations will be rule-based only",
                likelihood=0.3, impact=4.0,
                mitigation="Configure Azure OpenAI for better translations",
            ))

        # Ensure at least one factor for scoring
        if not ra.factors:
            ra.factors.append(RiskFactor(
                "low_risk", "No significant risks identified",
                likelihood=0.1, impact=1.0,
            ))

        ra.compute_overall()
        return ra


# ---------------------------------------------------------------------------
# Assessment report
# ---------------------------------------------------------------------------


@dataclass
class AssessmentReport:
    """Composite migration assessment for an entire scope."""
    complexity_scores: list[ComplexityScore] = field(default_factory=list)
    complexity_summary: dict[str, Any] = field(default_factory=dict)
    cost_estimate: CostEstimate | None = None
    timeline_estimate: TimelineEstimate | None = None
    preflight: PreflightResult | None = None
    risk_assessment: RiskAssessment | None = None

    def generate_markdown(self) -> str:
        """Generate a markdown summary of the assessment."""
        lines = ["# Migration Assessment Report\n"]

        # Complexity
        lines.append("## Complexity Summary\n")
        if self.complexity_summary:
            for k, v in self.complexity_summary.items():
                lines.append(f"- **{k}**: {v}")
        lines.append("")

        # Cost
        if self.cost_estimate:
            lines.append("## Cost Estimate\n")
            lines.append(f"- Compute hours: {self.cost_estimate.compute_hours:.1f}")
            lines.append(f"- Storage: {self.cost_estimate.storage_gb:.2f} GB")
            lines.append(f"- **Total estimated cost**: ${self.cost_estimate.total_cost_usd:.2f}")
            if self.cost_estimate.breakdown:
                lines.append("\n### Breakdown\n")
                for item, cost in self.cost_estimate.breakdown.items():
                    lines.append(f"- {item}: ${cost:.2f}")
            lines.append("")

        # Timeline
        if self.timeline_estimate:
            lines.append("## Timeline Estimate\n")
            lines.append(f"- Total days: {self.timeline_estimate.total_days:.1f}")
            lines.append(f"- Buffered days: {self.timeline_estimate.buffered_days:.1f}")
            if self.timeline_estimate.phases:
                lines.append("\n### Phase breakdown\n")
                for phase, days in self.timeline_estimate.phases.items():
                    lines.append(f"- {phase}: {days:.1f} days")
            lines.append("")

        # Preflight
        if self.preflight:
            lines.append("## Preflight Checks\n")
            lines.append(self.preflight.summary())
            lines.append("")

        # Risk
        if self.risk_assessment:
            lines.append("## Risk Assessment\n")
            lines.append(f"- Overall risk: {self.risk_assessment.overall_risk:.1f}/10")
            lines.append(f"- Risk level: {self.risk_assessment.risk_level.value}")
            for f in self.risk_assessment.factors:
                lines.append(f"- **{f.name}** ({f.risk_score:.1f}): {f.description}")
            lines.append("")

        return "\n".join(lines)
