"""Assessment narrator — natural language report from structured assessment — Phase 71.

Generates executive-ready assessment reports from ``AIAssessor`` output.
When an LLM is available, produces richer narrative prose; otherwise generates
a well-structured Markdown report from templates.

Usage::

    narrator = AssessmentNarrator()
    report = narrator.generate(assessment_result)
    # report.markdown → ready-to-share Markdown text
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NarrativeReport:
    """Generated assessment report."""

    markdown: str = ""
    title: str = "Migration Assessment Report"
    generated_at: str = ""
    sections: list[str] = field(default_factory=list)
    word_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "word_count": self.word_count,
            "section_count": len(self.sections),
        }


class AssessmentNarrator:
    """Generate natural language assessment reports.

    Parameters
    ----------
    reasoning_loop
        Optional LLM reasoning loop for narrative enrichment.
    """

    def __init__(self, reasoning_loop: Any = None) -> None:
        self._reasoning = reasoning_loop

    def generate(self, assessment: Any) -> NarrativeReport:
        """Generate a Markdown report from assessment data.

        Parameters
        ----------
        assessment
            An ``AssessmentResult`` from ``AIAssessor``.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sections: list[str] = []

        # Title
        sections.append(f"# Migration Assessment Report\n\n*Generated: {now}*\n")

        # Executive summary
        sections.append(self._executive_summary(assessment))

        # Risk overview
        sections.append(self._risk_overview(assessment))

        # Anomalies
        if assessment.anomalies:
            sections.append(self._anomaly_section(assessment))

        # Strategy recommendations
        if assessment.strategy_recommendations:
            sections.append(self._strategy_section(assessment))

        # Detailed risk table
        sections.append(self._risk_table(assessment))

        markdown = "\n---\n\n".join(sections)
        word_count = len(markdown.split())

        return NarrativeReport(
            markdown=markdown,
            title="Migration Assessment Report",
            generated_at=now,
            sections=[s[:50] for s in sections],
            word_count=word_count,
        )

    async def generate_with_llm(self, assessment: Any) -> NarrativeReport:
        """Generate report with optional LLM narrative enrichment."""
        report = self.generate(assessment)

        if self._reasoning:
            try:
                enriched = await self._reasoning.run(
                    task="narrate_assessment",
                    source=report.markdown[:2000],
                    context={"total_assets": assessment.total_assets},
                )
                if enriched.success and enriched.output:
                    # Prepend LLM executive narrative
                    report.markdown = (
                        f"## AI-Generated Executive Summary\n\n{enriched.output}\n\n---\n\n"
                        + report.markdown
                    )
            except Exception:
                logger.debug("LLM narrative enrichment skipped")

        return report

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    @staticmethod
    def _executive_summary(assessment: Any) -> str:
        lines = ["## Executive Summary\n"]
        lines.append(f"**Total assets assessed:** {assessment.total_assets}\n")

        dist = assessment.risk_distribution
        if dist:
            lines.append("**Risk distribution:**\n")
            for level, count in sorted(dist.items()):
                emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(level, "⚪")
                lines.append(f"- {emoji} {level.title()}: {count}")
            lines.append("")

        if assessment.anomalies:
            lines.append(f"**Anomalies detected:** {len(assessment.anomalies)}\n")

        return "\n".join(lines)

    @staticmethod
    def _risk_overview(assessment: Any) -> str:
        lines = ["## Risk Overview\n"]

        critical = assessment.critical_count
        high = assessment.high_count

        if critical > 0:
            lines.append(
                f"⚠️ **{critical} critical-risk asset(s)** require manual review "
                f"before migration can proceed safely.\n"
            )
        if high > 0:
            lines.append(
                f"**{high} high-risk asset(s)** are recommended for refactoring "
                f"rather than direct lift-and-shift.\n"
            )
        if critical == 0 and high == 0:
            lines.append("✅ No critical or high-risk assets detected. Migration can proceed with confidence.\n")

        return "\n".join(lines)

    @staticmethod
    def _anomaly_section(assessment: Any) -> str:
        lines = ["## Detected Anomalies\n"]
        lines.append("| # | Type | Severity | Description | Recommendation |")
        lines.append("|---|------|----------|-------------|----------------|")

        for i, anomaly in enumerate(assessment.anomalies, 1):
            lines.append(
                f"| {i} | {anomaly.anomaly_type.value} | {anomaly.severity.value} | "
                f"{anomaly.description} | {anomaly.recommendation} |"
            )

        return "\n".join(lines)

    @staticmethod
    def _strategy_section(assessment: Any) -> str:
        lines = ["## Recommended Migration Strategy\n"]
        lines.append("| Priority | Group | Strategy | Assets | Est. Hours |")
        lines.append("|----------|-------|----------|--------|------------|")

        for rec in assessment.strategy_recommendations:
            lines.append(
                f"| {rec.priority} | {rec.group_name} | {rec.strategy.value} | "
                f"{len(rec.asset_ids)} | {rec.estimated_effort_hours:.0f} |"
            )

        total_hours = sum(r.estimated_effort_hours for r in assessment.strategy_recommendations)
        lines.append(f"\n**Total estimated effort:** {total_hours:.0f} hours\n")

        return "\n".join(lines)

    @staticmethod
    def _risk_table(assessment: Any) -> str:
        lines = ["## Detailed Risk Assessment\n"]

        if not assessment.risk_heatmap:
            lines.append("No assets to display.")
            return "\n".join(lines)

        lines.append("| Asset | Risk | Score | Strategy | Factors |")
        lines.append("|-------|------|-------|----------|---------|")

        # Show top 50 by risk score
        sorted_risks = sorted(assessment.risk_heatmap, key=lambda r: r.risk_score, reverse=True)
        for risk in sorted_risks[:50]:
            factors = "; ".join(risk.factors) if risk.factors else "—"
            lines.append(
                f"| {risk.asset_name} | {risk.risk_level.value} | "
                f"{risk.risk_score:.2f} | {risk.suggested_strategy.value} | {factors} |"
            )

        if len(assessment.risk_heatmap) > 50:
            lines.append(f"\n*Showing top 50 of {len(assessment.risk_heatmap)} assets.*")

        return "\n".join(lines)
