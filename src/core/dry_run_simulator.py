"""Migration dry-run simulator — end-to-end simulation without writing to targets.

Runs all agents in ``--dry-run`` mode with instrumented output collectors,
producing a detailed simulation report including:

* Per-asset risk score (complexity + translation confidence)
* Translation coverage and confidence statistics
* Estimated Fabric compute & storage cost
* Estimated timeline
* Risk heatmap (dimension × asset)
* Change manifest (what *would* be created / modified)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.agents.discovery.complexity_scorer import score_item
from src.agents.semantic.expression_translator import DAXTranslation, translate_expression
from src.core.migration_intelligence import (
    AssessmentReport,
    ComplexityAnalyzer,
    ComplexityScore,
    CostEstimate,
    CostEstimator,
    RiskAssessment,
    RiskLevel,
    RiskScorer,
    TimelineEstimate,
    TimelineEstimator,
)
from src.core.models import (
    AssetType,
    ComplexityCategory,
    Inventory,
    InventoryItem,
    MigrationPlan,
    MigrationScope,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SimulationMode(str, Enum):
    """Simulation depth."""

    QUICK = "quick"  # Complexity + cost only
    STANDARD = "standard"  # + translation coverage
    FULL = "full"  # + per-expression confidence


class ChangeAction(str, Enum):
    """What the migration would do."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    SKIP = "skip"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ChangeManifestEntry:
    """A single entry in the change manifest."""

    asset_name: str
    asset_type: str
    action: ChangeAction
    target_path: str = ""
    details: str = ""


@dataclass
class TranslationCoverageStats:
    """Translation coverage statistics."""

    total_expressions: int = 0
    translated: int = 0
    rule_based: int = 0
    llm_assisted: int = 0
    manual_required: int = 0
    avg_confidence: float = 0.0
    min_confidence: float = 1.0
    max_confidence: float = 0.0
    low_confidence_count: int = 0  # confidence < 0.7

    @property
    def coverage_pct(self) -> float:
        if self.total_expressions == 0:
            return 100.0
        return (self.translated / self.total_expressions) * 100.0


@dataclass
class AssetSimulationResult:
    """Simulation result for a single asset."""

    asset_name: str
    asset_type: str
    complexity_score: float = 0.0
    complexity_category: str = "LOW"
    risk_level: str = "low"
    risk_score: float = 0.0
    translation_confidence: float = 1.0
    translation_coverage: float = 100.0
    expressions_total: int = 0
    expressions_translated: int = 0
    requires_review: bool = False
    estimated_cost_usd: float = 0.0
    estimated_hours: float = 0.0
    change_action: ChangeAction = ChangeAction.CREATE
    target_path: str = ""
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class RiskHeatmapCell:
    """A single cell in the risk heatmap."""

    asset_name: str
    dimension: str
    score: float = 0.0
    risk_level: str = "low"


@dataclass
class SimulationReport:
    """Full dry-run simulation report."""

    simulation_id: str = ""
    mode: SimulationMode = SimulationMode.STANDARD
    started_at: str = ""
    completed_at: str = ""
    total_assets: int = 0

    # Per-asset results
    asset_results: list[AssetSimulationResult] = field(default_factory=list)

    # Aggregated coverage
    translation_coverage: TranslationCoverageStats = field(
        default_factory=TranslationCoverageStats
    )

    # Cost & timeline
    cost_estimate: CostEstimate | None = None
    timeline_estimate: TimelineEstimate | None = None

    # Risk
    risk_assessment: RiskAssessment | None = None
    risk_heatmap: list[RiskHeatmapCell] = field(default_factory=list)

    # Change manifest
    change_manifest: list[ChangeManifestEntry] = field(default_factory=list)

    # Roll-up stats
    assets_by_risk: dict[str, int] = field(default_factory=dict)
    assets_by_action: dict[str, int] = field(default_factory=dict)
    review_required_count: int = 0
    overall_risk_level: str = "low"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for JSON output."""
        return {
            "simulationId": self.simulation_id,
            "mode": self.mode.value,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "totalAssets": self.total_assets,
            "overallRiskLevel": self.overall_risk_level,
            "reviewRequiredCount": self.review_required_count,
            "assetsByRisk": self.assets_by_risk,
            "assetsByAction": self.assets_by_action,
            "translationCoverage": {
                "totalExpressions": self.translation_coverage.total_expressions,
                "translated": self.translation_coverage.translated,
                "ruleBased": self.translation_coverage.rule_based,
                "llmAssisted": self.translation_coverage.llm_assisted,
                "manualRequired": self.translation_coverage.manual_required,
                "avgConfidence": round(self.translation_coverage.avg_confidence, 3),
                "coveragePct": round(self.translation_coverage.coverage_pct, 1),
                "lowConfidenceCount": self.translation_coverage.low_confidence_count,
            },
            "costEstimate": {
                "computeHours": round(self.cost_estimate.compute_hours, 2),
                "storageGb": round(self.cost_estimate.storage_gb, 2),
                "totalCostUsd": round(self.cost_estimate.total_cost_usd, 2),
                "breakdown": self.cost_estimate.breakdown,
            }
            if self.cost_estimate
            else None,
            "timelineEstimate": {
                "totalDays": round(self.timeline_estimate.total_days, 1),
                "bufferedDays": round(self.timeline_estimate.buffered_days, 1),
                "phases": {
                    k: round(v, 1)
                    for k, v in self.timeline_estimate.phases.items()
                },
            }
            if self.timeline_estimate
            else None,
            "riskHeatmap": [
                {
                    "asset": cell.asset_name,
                    "dimension": cell.dimension,
                    "score": round(cell.score, 2),
                    "riskLevel": cell.risk_level,
                }
                for cell in self.risk_heatmap
            ],
            "changeManifest": [
                {
                    "assetName": e.asset_name,
                    "assetType": e.asset_type,
                    "action": e.action.value,
                    "targetPath": e.target_path,
                    "details": e.details,
                }
                for e in self.change_manifest
            ],
            "assetResults": [
                {
                    "assetName": r.asset_name,
                    "assetType": r.asset_type,
                    "complexityScore": round(r.complexity_score, 2),
                    "riskLevel": r.risk_level,
                    "riskScore": round(r.risk_score, 2),
                    "translationConfidence": round(r.translation_confidence, 3),
                    "translationCoverage": round(r.translation_coverage, 1),
                    "requiresReview": r.requires_review,
                    "estimatedCostUsd": round(r.estimated_cost_usd, 4),
                    "estimatedHours": round(r.estimated_hours, 2),
                    "changeAction": r.change_action.value,
                    "warnings": r.warnings,
                }
                for r in self.asset_results
            ],
        }

    def generate_markdown(self) -> str:
        """Generate a Markdown summary of the simulation."""
        lines = ["# Migration Dry-Run Simulation Report\n"]
        lines.append(f"**Simulation ID**: {self.simulation_id}  ")
        lines.append(f"**Mode**: {self.mode.value}  ")
        lines.append(f"**Date**: {self.started_at}  ")
        lines.append(f"**Total assets**: {self.total_assets}  ")
        lines.append(f"**Overall risk**: {self.overall_risk_level}  ")
        lines.append("")

        # Translation coverage
        tc = self.translation_coverage
        lines.append("## Translation Coverage\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total expressions | {tc.total_expressions} |")
        lines.append(f"| Translated | {tc.translated} ({tc.coverage_pct:.1f}%) |")
        lines.append(f"| Rule-based | {tc.rule_based} |")
        lines.append(f"| LLM-assisted | {tc.llm_assisted} |")
        lines.append(f"| Manual required | {tc.manual_required} |")
        lines.append(f"| Avg confidence | {tc.avg_confidence:.3f} |")
        lines.append(f"| Low confidence (< 0.7) | {tc.low_confidence_count} |")
        lines.append("")

        # Cost
        if self.cost_estimate:
            ce = self.cost_estimate
            lines.append("## Cost Estimate\n")
            lines.append(f"| Item | Cost |")
            lines.append(f"|------|------|")
            for item, cost in ce.breakdown.items():
                lines.append(f"| {item} | ${cost:.2f} |")
            lines.append(f"| **Total** | **${ce.total_cost_usd:.2f}** |")
            lines.append("")

        # Timeline
        if self.timeline_estimate:
            te = self.timeline_estimate
            lines.append("## Timeline Estimate\n")
            lines.append(f"- Estimated days: {te.total_days:.1f}")
            lines.append(f"- With buffer: {te.buffered_days:.1f}")
            lines.append("")

        # Risk by asset
        lines.append("## Risk Summary\n")
        lines.append(f"| Risk Level | Count |")
        lines.append(f"|------------|-------|")
        for level, count in sorted(self.assets_by_risk.items()):
            lines.append(f"| {level} | {count} |")
        lines.append("")

        # Change manifest
        lines.append("## Change Manifest\n")
        lines.append(f"| Asset | Type | Action | Target |")
        lines.append(f"|-------|------|--------|--------|")
        for entry in self.change_manifest[:50]:  # Cap at 50 in markdown
            lines.append(
                f"| {entry.asset_name} | {entry.asset_type} "
                f"| {entry.action.value} | {entry.target_path} |"
            )
        if len(self.change_manifest) > 50:
            lines.append(f"\n*... and {len(self.change_manifest) - 50} more entries*\n")
        lines.append("")

        # Assets requiring review
        review_assets = [r for r in self.asset_results if r.requires_review]
        if review_assets:
            lines.append("## Assets Requiring Review\n")
            for r in review_assets:
                lines.append(
                    f"- **{r.asset_name}** ({r.asset_type}): "
                    f"confidence={r.translation_confidence:.2f}, "
                    f"risk={r.risk_level}"
                )
                for w in r.warnings:
                    lines.append(f"  - ⚠ {w}")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Simulation configuration
# ---------------------------------------------------------------------------


@dataclass
class SimulationConfig:
    """Configuration for a dry-run simulation."""

    mode: SimulationMode = SimulationMode.STANDARD
    simulation_id: str = ""
    # Cost estimator overrides
    cu_price_per_hour: float = 0.18
    storage_price_per_gb: float = 0.023
    # Timeline estimator overrides
    team_size: int = 2
    hours_per_day: float = 6.0
    # Confidence threshold for review flagging
    review_confidence_threshold: float = 0.7
    # Target path prefix for change manifest
    target_prefix: str = "fabric://workspace/lakehouse/"
    # Extra config dict (passed to risk scorer)
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Dry-run simulator
# ---------------------------------------------------------------------------


class DryRunSimulator:
    """Simulate a full migration without writing to target systems.

    Orchestrates complexity analysis, translation coverage measurement,
    cost/timeline estimation, risk scoring, and change manifest generation.
    """

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()
        self._complexity_analyzer = ComplexityAnalyzer()
        self._cost_estimator = CostEstimator(
            cu_price_per_hour=self.config.cu_price_per_hour,
            storage_price_per_gb=self.config.storage_price_per_gb,
        )
        self._timeline_estimator = TimelineEstimator(
            team_size=self.config.team_size,
            hours_per_day=self.config.hours_per_day,
        )
        self._risk_scorer = RiskScorer()

    # ----- public API -------------------------------------------------------

    def simulate(
        self,
        inventory: Inventory,
        expressions: list[dict[str, str]] | None = None,
    ) -> SimulationReport:
        """Run a full dry-run simulation.

        Args:
            inventory: Discovered source inventory.
            expressions: Optional list of dicts with ``name``, ``table``,
                ``expression`` keys for translation coverage analysis.

        Returns:
            SimulationReport with full results.
        """
        now = datetime.now(timezone.utc).isoformat()
        report = SimulationReport(
            simulation_id=self.config.simulation_id or f"sim-{now}",
            mode=self.config.mode,
            started_at=now,
            total_assets=len(inventory.items),
        )

        # Step 1: Score complexity per asset
        complexity_scores = self._score_complexity(inventory)

        # Step 2: Translation coverage (if mode allows)
        translations: list[DAXTranslation] = []
        if self.config.mode in (SimulationMode.STANDARD, SimulationMode.FULL):
            translations = self._measure_translation_coverage(
                expressions or [], report.translation_coverage
            )

        # Step 3: Build per-asset results
        self._build_asset_results(
            inventory, complexity_scores, translations, report
        )

        # Step 4: Cost estimation
        report.cost_estimate = self._estimate_costs(inventory)

        # Step 5: Timeline estimation
        report.timeline_estimate = self._estimate_timeline(
            inventory, complexity_scores
        )

        # Step 6: Risk assessment
        report.risk_assessment = self._risk_scorer.assess(
            complexity_scores, self.config.extra
        )
        report.overall_risk_level = report.risk_assessment.risk_level.value

        # Step 7: Risk heatmap
        report.risk_heatmap = self._build_risk_heatmap(complexity_scores)

        # Step 8: Change manifest
        report.change_manifest = self._build_change_manifest(inventory)

        # Step 9: Roll-up stats
        self._compute_rollup(report)

        report.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Dry-run simulation complete: %d assets, risk=%s, cost=$%.2f",
            report.total_assets,
            report.overall_risk_level,
            report.cost_estimate.total_cost_usd if report.cost_estimate else 0,
        )
        return report

    # ----- private helpers --------------------------------------------------

    def _score_complexity(
        self, inventory: Inventory
    ) -> list[ComplexityScore]:
        """Convert inventory items to complexity scores."""
        asset_dicts: list[dict[str, Any]] = []
        for item in inventory.items:
            meta = item.metadata or {}
            asset_dicts.append(
                {
                    "name": item.name,
                    "type": item.asset_type.value
                    if isinstance(item.asset_type, AssetType)
                    else str(item.asset_type),
                    "tables": meta.get("tables", 0),
                    "calculations": meta.get("calculations", 0),
                    "rls_roles": meta.get("rls_roles", 0),
                    "visuals": meta.get("visuals", 0),
                    "row_count": meta.get("row_count", 0),
                    "dependencies": meta.get("dependencies", 0),
                    "custom_sql": meta.get("custom_sql", 0),
                }
            )
        return self._complexity_analyzer.score_inventory(asset_dicts)

    def _measure_translation_coverage(
        self,
        expressions: list[dict[str, str]],
        stats: TranslationCoverageStats,
    ) -> list[DAXTranslation]:
        """Translate all expressions and collect coverage stats."""
        results: list[DAXTranslation] = []
        stats.total_expressions = len(expressions)
        if not expressions:
            return results

        confidences: list[float] = []
        for expr_dict in expressions:
            name = expr_dict.get("name", "unknown")
            table = expr_dict.get("table", "Table")
            expression = expr_dict.get("expression", "")
            if not expression:
                stats.manual_required += 1
                continue

            translation = translate_expression(expression, table, name)
            results.append(translation)

            if translation.dax_expression and translation.dax_expression != expression:
                stats.translated += 1
                if translation.method == "rule-based":
                    stats.rule_based += 1
                elif translation.method == "llm":
                    stats.llm_assisted += 1
                else:
                    stats.manual_required += 1
            else:
                stats.manual_required += 1

            confidences.append(translation.confidence)
            if translation.confidence < self.config.review_confidence_threshold:
                stats.low_confidence_count += 1

        if confidences:
            stats.avg_confidence = sum(confidences) / len(confidences)
            stats.min_confidence = min(confidences)
            stats.max_confidence = max(confidences)

        return results

    def _build_asset_results(
        self,
        inventory: Inventory,
        complexity_scores: list[ComplexityScore],
        translations: list[DAXTranslation],
        report: SimulationReport,
    ) -> None:
        """Build per-asset simulation results."""
        # Index translations by table+name for lookup
        translation_map: dict[str, DAXTranslation] = {}
        for t in translations:
            key = f"{t.table_name}.{t.column_name}"
            translation_map[key] = t

        score_map: dict[str, ComplexityScore] = {
            cs.asset_name: cs for cs in complexity_scores
        }

        for item in inventory.items:
            cs = score_map.get(item.name)
            result = AssetSimulationResult(
                asset_name=item.name,
                asset_type=item.asset_type.value
                if isinstance(item.asset_type, AssetType)
                else str(item.asset_type),
            )

            # Complexity
            if cs:
                result.complexity_score = cs.overall
                result.complexity_category = cs.risk_level.value
                result.risk_level = cs.risk_level.value

            # Translation confidence for this asset's expressions
            meta = item.metadata or {}
            expr_names = meta.get("expression_names", [])
            table_name = meta.get("table_name", item.name)
            asset_translations = [
                translation_map[f"{table_name}.{n}"]
                for n in expr_names
                if f"{table_name}.{n}" in translation_map
            ]

            if asset_translations:
                confs = [t.confidence for t in asset_translations]
                result.translation_confidence = sum(confs) / len(confs)
                translated = sum(
                    1
                    for t in asset_translations
                    if t.dax_expression and t.dax_expression != t.original_expression
                )
                result.expressions_total = len(asset_translations)
                result.expressions_translated = translated
                result.translation_coverage = (
                    (translated / len(asset_translations)) * 100.0
                    if asset_translations
                    else 100.0
                )

            # Risk score = complexity × (1 - confidence)
            confidence_penalty = 1.0 - result.translation_confidence
            result.risk_score = result.complexity_score * (1.0 + confidence_penalty)
            # Cap at 10
            result.risk_score = min(10.0, result.risk_score)

            # Derive risk level from risk score
            if result.risk_score >= 8.0:
                result.risk_level = RiskLevel.CRITICAL.value
            elif result.risk_score >= 6.0:
                result.risk_level = RiskLevel.HIGH.value
            elif result.risk_score >= 4.0:
                result.risk_level = RiskLevel.MEDIUM.value
            else:
                result.risk_level = RiskLevel.LOW.value

            # Review flag
            result.requires_review = (
                result.translation_confidence
                < self.config.review_confidence_threshold
                or result.risk_score >= 6.0
            )

            # Warnings
            if cs and cs.notes:
                result.warnings.extend(cs.notes)
            if result.translation_confidence < 0.5:
                result.warnings.append(
                    f"Very low translation confidence: {result.translation_confidence:.2f}"
                )

            # Per-asset cost estimate (proportional)
            meta = item.metadata or {}
            rows = meta.get("row_count", 0)
            tables_count = meta.get("tables", 1)
            calcs = meta.get("calculations", 0)
            copy_h = tables_count * 0.1
            calc_h = calcs * 0.02
            result.estimated_hours = copy_h + calc_h
            result.estimated_cost_usd = (
                result.estimated_hours * self.config.cu_price_per_hour
            )

            # Target path
            result.target_path = (
                f"{self.config.target_prefix}{item.name.lower().replace(' ', '_')}"
            )
            result.change_action = ChangeAction.CREATE

            report.asset_results.append(result)

    def _estimate_costs(self, inventory: Inventory) -> CostEstimate:
        """Aggregate cost estimate from inventory totals."""
        total_rows = 0
        total_tables = 0
        total_calculations = 0
        total_reports = 0

        for item in inventory.items:
            meta = item.metadata or {}
            total_rows += meta.get("row_count", 0)
            total_tables += meta.get("tables", 0)
            total_calculations += meta.get("calculations", 0)
            asset_type_str = (
                item.asset_type.value
                if isinstance(item.asset_type, AssetType)
                else str(item.asset_type)
            )
            if asset_type_str in ("analysis", "dashboard", "report"):
                total_reports += 1

        return self._cost_estimator.estimate(
            total_rows=total_rows,
            total_tables=total_tables,
            total_calculations=total_calculations,
            total_reports=total_reports,
        )

    def _estimate_timeline(
        self,
        inventory: Inventory,
        complexity_scores: list[ComplexityScore],
    ) -> TimelineEstimate:
        """Estimate migration timeline from totals."""
        total_tables = 0
        total_calculations = 0
        total_reports = 0
        total_rls = 0

        for item in inventory.items:
            meta = item.metadata or {}
            total_tables += meta.get("tables", 0)
            total_calculations += meta.get("calculations", 0)
            total_rls += meta.get("rls_roles", 0)
            asset_type_str = (
                item.asset_type.value
                if isinstance(item.asset_type, AssetType)
                else str(item.asset_type)
            )
            if asset_type_str in ("analysis", "dashboard", "report"):
                total_reports += 1

        avg_complexity = 5.0
        if complexity_scores:
            avg_complexity = sum(s.overall for s in complexity_scores) / len(
                complexity_scores
            )

        return self._timeline_estimator.estimate(
            total_tables=total_tables,
            total_calculations=total_calculations,
            total_reports=total_reports,
            total_rls_roles=total_rls,
            complexity_avg=avg_complexity,
        )

    def _build_risk_heatmap(
        self, complexity_scores: list[ComplexityScore]
    ) -> list[RiskHeatmapCell]:
        """Build a risk heatmap: asset × dimension cells."""
        cells: list[RiskHeatmapCell] = []
        for cs in complexity_scores:
            for dim, score in cs.scores.items():
                level = "low"
                if score >= 8.0:
                    level = "critical"
                elif score >= 6.0:
                    level = "high"
                elif score >= 4.0:
                    level = "medium"
                cells.append(
                    RiskHeatmapCell(
                        asset_name=cs.asset_name,
                        dimension=dim,
                        score=score,
                        risk_level=level,
                    )
                )
        return cells

    def _build_change_manifest(
        self, inventory: Inventory
    ) -> list[ChangeManifestEntry]:
        """Build a manifest of what the migration would create/modify."""
        entries: list[ChangeManifestEntry] = []
        for item in inventory.items:
            asset_type_str = (
                item.asset_type.value
                if isinstance(item.asset_type, AssetType)
                else str(item.asset_type)
            )
            target = (
                f"{self.config.target_prefix}"
                f"{item.name.lower().replace(' ', '_')}"
            )

            # Base table / model creation
            entries.append(
                ChangeManifestEntry(
                    asset_name=item.name,
                    asset_type=asset_type_str,
                    action=ChangeAction.CREATE,
                    target_path=target,
                    details=f"Create {asset_type_str} from OAC source",
                )
            )

            # If asset has calculations → additional semantic model entries
            meta = item.metadata or {}
            if meta.get("calculations", 0) > 0:
                entries.append(
                    ChangeManifestEntry(
                        asset_name=f"{item.name}_measures",
                        asset_type="measure",
                        action=ChangeAction.CREATE,
                        target_path=f"{target}/measures",
                        details=f"{meta['calculations']} calculations to translate",
                    )
                )

            # If asset has RLS → security entries
            if meta.get("rls_roles", 0) > 0:
                entries.append(
                    ChangeManifestEntry(
                        asset_name=f"{item.name}_rls",
                        asset_type="rls_role",
                        action=ChangeAction.CREATE,
                        target_path=f"{target}/security",
                        details=f"{meta['rls_roles']} RLS roles to migrate",
                    )
                )

        return entries

    def _compute_rollup(self, report: SimulationReport) -> None:
        """Compute roll-up statistics on the report."""
        risk_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        review_count = 0

        for r in report.asset_results:
            risk_counts[r.risk_level] = risk_counts.get(r.risk_level, 0) + 1
            action_counts[r.change_action.value] = (
                action_counts.get(r.change_action.value, 0) + 1
            )
            if r.requires_review:
                review_count += 1

        report.assets_by_risk = risk_counts
        report.assets_by_action = action_counts
        report.review_required_count = review_count


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def run_dry_run(
    inventory: Inventory,
    expressions: list[dict[str, str]] | None = None,
    *,
    mode: SimulationMode = SimulationMode.STANDARD,
    simulation_id: str = "",
    team_size: int = 2,
    cu_price_per_hour: float = 0.18,
    extra_config: dict[str, Any] | None = None,
) -> SimulationReport:
    """Convenience wrapper to run a dry-run simulation.

    Args:
        inventory: Discovered source inventory.
        expressions: Optional OAC expressions for translation analysis.
        mode: Simulation depth (quick / standard / full).
        simulation_id: Optional identifier for the simulation.
        team_size: Number of team members for timeline estimation.
        cu_price_per_hour: Fabric CU price override.
        extra_config: Additional config dict passed to risk scorer.

    Returns:
        SimulationReport with full results.
    """
    cfg = SimulationConfig(
        mode=mode,
        simulation_id=simulation_id,
        team_size=team_size,
        cu_price_per_hour=cu_price_per_hour,
        extra=extra_config or {},
    )
    simulator = DryRunSimulator(cfg)
    return simulator.simulate(inventory, expressions)
