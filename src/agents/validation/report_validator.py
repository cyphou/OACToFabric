"""Report validator — verify migrated Power BI reports match OAC originals.

Covers:
  - Visual count per page
  - Visual type mapping verification
  - Slicer / filter behaviour equivalence
  - Drillthrough target validation
  - Conditional formatting rules
  - Screenshot-based visual regression (stub — needs Playwright/Selenium)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------


class ReportCheckType(str, Enum):
    """Types of report validation checks."""

    VISUAL_COUNT = "visual_count"
    VISUAL_TYPE = "visual_type"
    SLICER_BEHAVIOUR = "slicer_behaviour"
    DRILLTHROUGH = "drillthrough"
    CONDITIONAL_FORMAT = "conditional_format"
    SCREENSHOT_DIFF = "screenshot_diff"
    DATA_ACCURACY = "data_accuracy"


class ReportCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"
    ERROR = "ERROR"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass
class ReportTestCase:
    """A single report validation test case."""

    check_type: ReportCheckType
    report_name: str
    page_name: str = ""
    visual_id: str = ""
    description: str = ""
    expected_value: Any = None
    oac_metadata: dict[str, Any] = field(default_factory=dict)
    pbi_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportCheckResult:
    """Result of a single report validation check."""

    check_type: ReportCheckType
    report_name: str
    page_name: str = ""
    visual_id: str = ""
    expected_value: Any = None
    actual_value: Any = None
    status: ReportCheckStatus = ReportCheckStatus.PASS
    description: str = ""
    error: str = ""
    similarity_score: float = 1.0  # For screenshot diff (0–1)


@dataclass
class ReportValidationReport:
    """Aggregated report validation results."""

    results: list[ReportCheckResult] = field(default_factory=list)
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    manual_review: int = 0

    def add(self, result: ReportCheckResult) -> None:
        self.results.append(result)
        self.total_checks += 1
        if result.status == ReportCheckStatus.PASS:
            self.passed += 1
        elif result.status == ReportCheckStatus.FAIL:
            self.failed += 1
        elif result.status == ReportCheckStatus.WARN:
            self.warnings += 1
        elif result.status == ReportCheckStatus.MANUAL_REVIEW:
            self.manual_review += 1

    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.passed / self.total_checks * 100


# ---------------------------------------------------------------------------
# Visual count validation
# ---------------------------------------------------------------------------


def generate_visual_count_tests(
    oac_reports: list[dict[str, Any]],
    pbi_reports: list[dict[str, Any]],
) -> list[ReportTestCase]:
    """Generate visual-count validation tests for each page.

    Parameters
    ----------
    oac_reports : list[dict]
        Each dict::

            - name: str
            - pages: list[dict] — each with ``name``, ``visual_count``
    pbi_reports : list[dict]
        Same structure with migrated report data.
    """
    pbi_by_name = {r.get("name", ""): r for r in pbi_reports}
    tests: list[ReportTestCase] = []

    for oac in oac_reports:
        rname = oac.get("name", "")
        pbi = pbi_by_name.get(rname)
        if pbi is None:
            tests.append(
                ReportTestCase(
                    check_type=ReportCheckType.VISUAL_COUNT,
                    report_name=rname,
                    description=f"PBI report '{rname}' not found — migration gap",
                    expected_value=sum(
                        p.get("visual_count", 0) for p in oac.get("pages", [])
                    ),
                    oac_metadata=oac,
                )
            )
            continue

        for oac_page in oac.get("pages", []):
            pname = oac_page.get("name", "")
            oac_count = oac_page.get("visual_count", 0)
            # Find matching PBI page
            pbi_page = next(
                (p for p in pbi.get("pages", []) if p.get("name") == pname),
                None,
            )
            pbi_count = pbi_page.get("visual_count", 0) if pbi_page else 0

            tests.append(
                ReportTestCase(
                    check_type=ReportCheckType.VISUAL_COUNT,
                    report_name=rname,
                    page_name=pname,
                    description=f"Visual count on {rname}/{pname}",
                    expected_value=oac_count,
                    oac_metadata=oac_page,
                    pbi_metadata=pbi_page or {},
                )
            )

    logger.info("Generated %d visual count test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Visual type validation
# ---------------------------------------------------------------------------


def generate_visual_type_tests(
    oac_visuals: list[dict[str, Any]],
    pbi_visuals: list[dict[str, Any]],
    type_mapping: dict[str, str] | None = None,
) -> list[ReportTestCase]:
    """Generate visual-type mapping verification tests.

    Parameters
    ----------
    oac_visuals : list[dict]
        ``id``, ``report``, ``page``, ``type`` (OAC chart type).
    pbi_visuals : list[dict]
        ``id``, ``report``, ``page``, ``type`` (PBI visual type).
    type_mapping : dict
        OAC visual type → expected PBI visual type.
    """
    mapping = type_mapping or {}
    pbi_by_id = {v["id"]: v for v in pbi_visuals}
    tests: list[ReportTestCase] = []

    for oac in oac_visuals:
        vid = oac["id"]
        oac_type = oac.get("type", "")
        expected_pbi_type = mapping.get(oac_type, oac_type)
        pbi = pbi_by_id.get(vid, {})

        tests.append(
            ReportTestCase(
                check_type=ReportCheckType.VISUAL_TYPE,
                report_name=oac.get("report", ""),
                page_name=oac.get("page", ""),
                visual_id=vid,
                description=(
                    f"Visual {vid}: OAC type '{oac_type}' "
                    f"→ expected PBI type '{expected_pbi_type}'"
                ),
                expected_value=expected_pbi_type,
                oac_metadata=oac,
                pbi_metadata=pbi,
            )
        )

    logger.info("Generated %d visual type test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Slicer / filter validation
# ---------------------------------------------------------------------------


def generate_slicer_tests(
    oac_slicers: list[dict[str, Any]],
) -> list[ReportTestCase]:
    """Generate slicer/filter behaviour validation tests.

    Parameters
    ----------
    oac_slicers : list[dict]
        ``report``, ``page``, ``slicer_type``, ``bound_column``,
        ``values`` (default selections).
    """
    tests: list[ReportTestCase] = []

    for s in oac_slicers:
        tests.append(
            ReportTestCase(
                check_type=ReportCheckType.SLICER_BEHAVIOUR,
                report_name=s.get("report", ""),
                page_name=s.get("page", ""),
                description=(
                    f"Slicer {s.get('slicer_type', '')} on "
                    f"{s.get('bound_column', '')}: verify filter behaviour"
                ),
                expected_value=s.get("values", []),
                oac_metadata=s,
            )
        )

    logger.info("Generated %d slicer test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Drillthrough validation
# ---------------------------------------------------------------------------


def generate_drillthrough_tests(
    drillthroughs: list[dict[str, Any]],
) -> list[ReportTestCase]:
    """Generate drillthrough target validation tests.

    Parameters
    ----------
    drillthroughs : list[dict]
        ``report``, ``source_page``, ``target_page``,
        ``context_columns`` (list of columns passed).
    """
    tests: list[ReportTestCase] = []

    for dt in drillthroughs:
        tests.append(
            ReportTestCase(
                check_type=ReportCheckType.DRILLTHROUGH,
                report_name=dt.get("report", ""),
                page_name=dt.get("source_page", ""),
                description=(
                    f"Drillthrough from {dt.get('source_page', '')} "
                    f"→ {dt.get('target_page', '')}"
                ),
                expected_value=dt.get("target_page", ""),
                oac_metadata=dt,
            )
        )

    logger.info("Generated %d drillthrough test cases", len(tests))
    return tests


# ---------------------------------------------------------------------------
# Result evaluation
# ---------------------------------------------------------------------------


def evaluate_visual_count(
    test_case: ReportTestCase,
    actual_count: int,
) -> ReportCheckResult:
    """Evaluate a visual-count test case."""
    expected = test_case.expected_value or 0
    status = ReportCheckStatus.PASS if actual_count == expected else ReportCheckStatus.FAIL
    return ReportCheckResult(
        check_type=test_case.check_type,
        report_name=test_case.report_name,
        page_name=test_case.page_name,
        expected_value=expected,
        actual_value=actual_count,
        status=status,
        description=test_case.description,
    )


def evaluate_visual_type(
    test_case: ReportTestCase,
    actual_type: str,
) -> ReportCheckResult:
    """Evaluate a visual-type test case."""
    expected = test_case.expected_value or ""
    status = (
        ReportCheckStatus.PASS
        if actual_type.lower() == str(expected).lower()
        else ReportCheckStatus.FAIL
    )
    return ReportCheckResult(
        check_type=test_case.check_type,
        report_name=test_case.report_name,
        page_name=test_case.page_name,
        visual_id=test_case.visual_id,
        expected_value=expected,
        actual_value=actual_type,
        status=status,
        description=test_case.description,
    )


def evaluate_screenshot_diff(
    report_name: str,
    page_name: str,
    similarity_score: float,
    threshold: float = 0.85,
) -> ReportCheckResult:
    """Evaluate a screenshot comparison result.

    Parameters
    ----------
    similarity_score : float
        0–1, where 1 = identical.
    threshold : float
        Below this, flag for manual review.
    """
    if similarity_score >= threshold:
        status = ReportCheckStatus.PASS
    elif similarity_score >= 0.6:
        status = ReportCheckStatus.MANUAL_REVIEW
    else:
        status = ReportCheckStatus.FAIL

    return ReportCheckResult(
        check_type=ReportCheckType.SCREENSHOT_DIFF,
        report_name=report_name,
        page_name=page_name,
        expected_value=f">= {threshold}",
        actual_value=similarity_score,
        status=status,
        similarity_score=similarity_score,
        description=f"Screenshot similarity for {report_name}/{page_name}",
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_report_validation_report(report: ReportValidationReport) -> str:
    """Render a Markdown report validation summary."""
    lines = [
        "# Report Validation Report",
        "",
        f"- **Total checks:** {report.total_checks}",
        f"- **Passed:** {report.passed}",
        f"- **Failed:** {report.failed}",
        f"- **Warnings:** {report.warnings}",
        f"- **Manual review:** {report.manual_review}",
        f"- **Pass rate:** {report.pass_rate:.1f}%",
        "",
    ]

    # Group by report
    by_report: dict[str, list[ReportCheckResult]] = {}
    for r in report.results:
        by_report.setdefault(r.report_name, []).append(r)

    for rname, results in sorted(by_report.items()):
        passed = sum(1 for r in results if r.status == ReportCheckStatus.PASS)
        lines.extend([
            f"## {rname} ({passed}/{len(results)} passed)",
            "",
            "| Check | Page | Expected | Actual | Status |",
            "|---|---|---|---|---|",
        ])
        for r in results:
            lines.append(
                f"| {r.check_type.value} | {r.page_name or '-'} | "
                f"{r.expected_value} | {r.actual_value} | {r.status.value} |"
            )
        lines.append("")

    return "\n".join(lines)
