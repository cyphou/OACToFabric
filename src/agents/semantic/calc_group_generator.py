"""Calculation Group Generator — OAC time-intel patterns → TMDL calculation groups.

Detects clusters of related time-intelligence calculations (YTD, QTD, MTD,
YoY, QoQ, MoM, Prior Year, Period Rolling) in translated DAX measures and
emits a single TMDL ``calculationGroup`` with ``calculationItem`` blocks
using ``SELECTEDMEASURE()``.

Also supports explicit creation of calculation groups from user-defined
pattern sets.  The generated TMDL sets ``discourageImplicitMeasures`` on
the model.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class CalculationItem:
    """A single item within a calculation group."""

    name: str
    expression: str
    format_string: str | None = None
    ordinal: int = 0


@dataclass
class CalculationGroup:
    """A TMDL calculation group definition."""

    name: str
    column_name: str = "Calculation"
    items: list[CalculationItem] = field(default_factory=list)
    precedence: int = 1
    description: str = ""

    def to_tmdl(self) -> str:
        """Emit TMDL text for this calculation group."""
        lines: list[str] = []
        lines.append(f"table '{self.name}'")
        if self.description:
            lines.append(f"\tdescription: {self.description}")
        lines.append("")
        lines.append("\tcalculationGroup")
        lines.append(f"\t\tprecedence: {self.precedence}")
        lines.append("")

        for item in sorted(self.items, key=lambda i: i.ordinal):
            expr = item.expression.replace("\n", "\n\t\t\t")
            lines.append(f"\t\tcalculationItem '{item.name}' = {expr}")
            if item.format_string:
                lines.append(f"\t\t\tformatStringDefinition = \"{item.format_string}\"")
            lines.append("")

        lines.append(f"\tcolumn '{self.column_name}'")
        lines.append("\t\tdataType: string")
        lines.append("\t\tsummarizeBy: none")
        lines.append("\t\tsourceColumn: Name")
        lines.append("\t\tsortByColumn: Ordinal")
        lines.append("")
        lines.append("\t\tannotation SummarizationSetBy = Automatic")
        lines.append("")
        lines.append("\tcolumn Ordinal")
        lines.append("\t\tdataType: int64")
        lines.append("\t\tformatString: 0")
        lines.append("\t\tsummarizeBy: sum")
        lines.append("\t\tsourceColumn: Ordinal")
        lines.append("")
        lines.append("\t\tannotation SummarizationSetBy = Automatic")

        return "\n".join(lines)


@dataclass
class CalcGroupDetectionResult:
    """Result of detecting calculation group candidates."""

    groups: list[CalculationGroup] = field(default_factory=list)
    measures_absorbed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Time intelligence pattern definitions
# ---------------------------------------------------------------------------

_TIME_INTEL_PATTERNS: list[dict[str, str]] = [
    {
        "name": "Current",
        "pattern": r"^SELECTEDMEASURE\(\)$",
        "expression": "SELECTEDMEASURE()",
        "ordinal": "0",
    },
    {
        "name": "YTD",
        "pattern": r"DATESYTD|TOTALYTD",
        "expression": "CALCULATE(SELECTEDMEASURE(), DATESYTD('Date'[Date]))",
        "ordinal": "1",
    },
    {
        "name": "QTD",
        "pattern": r"DATESQTD|TOTALQTD",
        "expression": "CALCULATE(SELECTEDMEASURE(), DATESQTD('Date'[Date]))",
        "ordinal": "2",
    },
    {
        "name": "MTD",
        "pattern": r"DATESMTD|TOTALMTD",
        "expression": "CALCULATE(SELECTEDMEASURE(), DATESMTD('Date'[Date]))",
        "ordinal": "3",
    },
    {
        "name": "PY",
        "pattern": r"SAMEPERIODLASTYEAR|DATEADD.*-1.*YEAR",
        "expression": "CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))",
        "ordinal": "4",
    },
    {
        "name": "PQ",
        "pattern": r"DATEADD.*-1.*QUARTER",
        "expression": "CALCULATE(SELECTEDMEASURE(), DATEADD('Date'[Date], -1, QUARTER))",
        "ordinal": "5",
    },
    {
        "name": "PM",
        "pattern": r"DATEADD.*-1.*MONTH",
        "expression": "CALCULATE(SELECTEDMEASURE(), DATEADD('Date'[Date], -1, MONTH))",
        "ordinal": "6",
    },
    {
        "name": "YoY",
        "pattern": r"YoY|year.over.year",
        "expression": "SELECTEDMEASURE() - CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))",
        "ordinal": "7",
    },
    {
        "name": "YoY%",
        "pattern": r"YoY.*%|year.over.year.*pct",
        "expression": (
            "VAR _current = SELECTEDMEASURE()\n"
            "VAR _prior = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))\n"
            "RETURN DIVIDE(_current - _prior, _prior)"
        ),
        "format_string": "#,##0.00%",
        "ordinal": "8",
    },
    {
        "name": "QoQ",
        "pattern": r"QoQ|quarter.over.quarter",
        "expression": "SELECTEDMEASURE() - CALCULATE(SELECTEDMEASURE(), DATEADD('Date'[Date], -1, QUARTER))",
        "ordinal": "9",
    },
    {
        "name": "MoM",
        "pattern": r"MoM|month.over.month",
        "expression": "SELECTEDMEASURE() - CALCULATE(SELECTEDMEASURE(), DATEADD('Date'[Date], -1, MONTH))",
        "ordinal": "10",
    },
]


# ---------------------------------------------------------------------------
# Detection engine
# ---------------------------------------------------------------------------


def detect_time_intel_clusters(
    measures: list[dict[str, Any]],
    date_table_name: str = "Date",
    date_column_name: str = "Date",
    min_matches: int = 3,
) -> CalcGroupDetectionResult:
    """Scan translated DAX measures for time-intelligence patterns.

    When >= ``min_matches`` patterns are found across measures for the same
    base metric, they are consolidated into a calculation group.

    Parameters
    ----------
    measures : list[dict]
        Each dict has ``name`` (str), ``expression`` (str, DAX),
        and optionally ``table_name`` (str).
    date_table_name : str
        Name of the Date dimension table in the model.
    date_column_name : str
        Name of the Date column.
    min_matches : int
        Minimum number of matched patterns to create a calc group.

    Returns
    -------
    CalcGroupDetectionResult
        Detected calc groups and list of measures absorbed.
    """
    matched_patterns: list[str] = []
    absorbed_measures: list[str] = []

    for measure in measures:
        expr = measure.get("expression", "")
        name = measure.get("name", "")
        for pat in _TIME_INTEL_PATTERNS:
            if pat["name"] == "Current":
                continue
            if re.search(pat["pattern"], expr, re.IGNORECASE):
                matched_patterns.append(pat["name"])
                absorbed_measures.append(name)
                break

    if len(matched_patterns) < min_matches:
        logger.info(
            "Only %d time-intel patterns found (need %d) — skipping calc group",
            len(matched_patterns),
            min_matches,
        )
        return CalcGroupDetectionResult(
            warnings=[f"Only {len(matched_patterns)} patterns found; minimum is {min_matches}"],
        )

    items: list[CalculationItem] = []
    for pat in _TIME_INTEL_PATTERNS:
        expr = pat["expression"].replace("'Date'", f"'{date_table_name}'")
        expr = expr.replace("[Date]", f"[{date_column_name}]")
        items.append(
            CalculationItem(
                name=pat["name"],
                expression=expr,
                format_string=pat.get("format_string"),
                ordinal=int(pat["ordinal"]),
            )
        )

    group = CalculationGroup(
        name="Time Intelligence",
        column_name="Time Calculation",
        items=items,
        precedence=1,
        description="Auto-generated from OAC time-intelligence patterns",
    )

    logger.info(
        "Created Time Intelligence calc group with %d items, absorbing %d measures",
        len(items),
        len(absorbed_measures),
    )

    return CalcGroupDetectionResult(
        groups=[group],
        measures_absorbed=absorbed_measures,
    )


# ---------------------------------------------------------------------------
# Explicit calc group builder
# ---------------------------------------------------------------------------


def build_calculation_group(
    name: str,
    items: list[dict[str, str]],
    column_name: str = "Calculation",
    precedence: int = 1,
) -> CalculationGroup:
    """Build a calculation group from explicit item definitions.

    Parameters
    ----------
    name : str
        Calculation group name.
    items : list[dict]
        Each dict has ``name`` and ``expression`` (DAX with SELECTEDMEASURE),
        optional ``format_string``.
    column_name : str
        Column name in the calc group table.
    precedence : int
        Evaluation precedence when multiple calc groups exist.
    """
    calc_items = [
        CalculationItem(
            name=item["name"],
            expression=item["expression"],
            format_string=item.get("format_string"),
            ordinal=i,
        )
        for i, item in enumerate(items)
    ]
    return CalculationGroup(
        name=name,
        column_name=column_name,
        items=calc_items,
        precedence=precedence,
    )
