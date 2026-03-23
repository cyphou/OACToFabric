"""Essbase connector — outline extraction + calc script parsing (stub).

Provides stub support for migrating Oracle Essbase cubes to Microsoft
Fabric & Power BI:

- ``EssbaseOutlineParser`` — parse Essbase outlines (dimensions, hierarchies, members)
- ``EssbaseCalcTranslator`` — translate Essbase calc scripts → DAX
- ``EssbaseMdxTranslator`` — translate Essbase MDX → DAX
- ``EssbaseRestClient`` — async wrapper around Essbase REST API
- ``EssbaseConnector`` — SourceConnector stub implementation

Planned implementation in Phase 41.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.connectors.base_connector import (
    ConnectorInfo,
    ExtractedAsset,
    ExtractionResult,
    SourceConnector,
)

logger = logging.getLogger(__name__)


# =====================================================================
# Essbase-specific data models
# =====================================================================


@dataclass
class EssbaseDimension:
    """An Essbase dimension extracted from an outline."""

    name: str
    dimension_type: str = "regular"  # regular | accounts | time | attribute
    members: list[str] = field(default_factory=list)
    generation_count: int = 0
    storage_type: str = "dense"  # dense | sparse


@dataclass
class EssbaseCalcRule:
    """A translation rule for Essbase calc script → DAX."""

    essbase_function: str
    dax_equivalent: str
    difficulty: str = "stub"  # stub | direct | parametric | complex
    notes: str = ""


# =====================================================================
# Calc script → DAX mapping (planned rules)
# =====================================================================

ESSBASE_TO_DAX_RULES: list[EssbaseCalcRule] = [
    # Aggregation
    EssbaseCalcRule("@SUM", "SUM", "direct", "Member aggregation → DAX SUM"),
    EssbaseCalcRule("@AVG", "AVERAGE", "direct", "Average → DAX AVERAGE"),
    EssbaseCalcRule("@COUNT", "COUNTROWS", "parametric", "Count → COUNTROWS"),
    EssbaseCalcRule("@MIN", "MIN", "direct", "Minimum → DAX MIN"),
    EssbaseCalcRule("@MAX", "MAX", "direct", "Maximum → DAX MAX"),
    # Cross-dimensional
    EssbaseCalcRule("@SUMRANGE", "CALCULATE(SUM, DATESINPERIOD)", "complex", "Range sum → CALCULATE"),
    EssbaseCalcRule("@AVGRANGE", "CALCULATE(AVERAGE, DATESINPERIOD)", "complex", "Range avg → CALCULATE"),
    EssbaseCalcRule("@PRIOR", "CALCULATE(measure, PREVIOUSMONTH)", "parametric", "Prior period"),
    EssbaseCalcRule("@NEXT", "CALCULATE(measure, NEXTMONTH)", "parametric", "Next period"),
    EssbaseCalcRule("@PARENTVAL", "CALCULATE(measure, ALLEXCEPT)", "complex", "Parent value"),
    EssbaseCalcRule("@ANCEST", "CALCULATE(measure, ALL)", "complex", "Ancestor value"),
    # Member functions
    EssbaseCalcRule("@CHILDREN", "FILTER + hierarchy", "complex", "Children → hierarchy filter"),
    EssbaseCalcRule("@DESCENDANTS", "FILTER + PATH", "complex", "Descendants → path filter"),
    EssbaseCalcRule("@SIBLINGS", "FILTER + ALLEXCEPT", "complex", "Siblings → level filter"),
    EssbaseCalcRule("@PARENT", "LOOKUPVALUE + hierarchy", "complex", "Parent → lookup"),
    EssbaseCalcRule("@ISMBR", "HASONEVALUE / SELECTEDVALUE", "parametric", "Member test → filter context"),
    EssbaseCalcRule("@ISLEV", "hierarchy level check", "complex", "Level test"),
    EssbaseCalcRule("@ISGEN", "hierarchy generation check", "complex", "Generation test"),
    # Allocation
    EssbaseCalcRule("@ALLOCATE", "manual", "complex", "Allocation → manual DAX pattern"),
    # Math
    EssbaseCalcRule("@ABS", "ABS", "direct", "Absolute value"),
    EssbaseCalcRule("@ROUND", "ROUND", "direct", "Round"),
    EssbaseCalcRule("@POWER", "POWER", "direct", "Power"),
    EssbaseCalcRule("@LOG", "LOG", "direct", "Logarithm"),
    EssbaseCalcRule("@LOG10", "LOG10", "direct", "Log base 10"),
    EssbaseCalcRule("@EXP", "EXP", "direct", "Exponential"),
    EssbaseCalcRule("@SQRT", "SQRT", "direct", "Square root"),
    EssbaseCalcRule("@MOD", "MOD", "direct", "Modulo"),
    EssbaseCalcRule("@TRUNCATE", "TRUNC", "direct", "Truncate"),
    # Conditional
    EssbaseCalcRule("IF/ELSEIF/ELSE/ENDIF", "IF / SWITCH(TRUE())", "parametric", "Conditional → IF/SWITCH"),
    EssbaseCalcRule("@ISMBR + IF", "SWITCH(TRUE(), condition, value)", "parametric", "Member conditional"),
    # Financial
    EssbaseCalcRule("@VAR", "variance pattern", "complex", "Variance → CALCULATE pattern"),
    EssbaseCalcRule("@VARPER", "DIVIDE(variance, base)", "complex", "Variance % → DIVIDE"),
    # Time balance
    EssbaseCalcRule("TB First", "FIRSTNONBLANK", "parametric", "Time balance first → FIRSTNONBLANK"),
    EssbaseCalcRule("TB Last", "LASTNONBLANK", "parametric", "Time balance last → LASTNONBLANK"),
    EssbaseCalcRule("TB Average", "AVERAGEX over date", "complex", "Time balance average → AVERAGEX"),
]


# =====================================================================
# MDX → DAX mapping (planned rules)
# =====================================================================

ESSBASE_MDX_TO_DAX: list[tuple[str, str, str]] = [
    # (Essbase MDX pattern, DAX equivalent, notes)
    ("[Measures].[member]", "Table[Measure]", "Measure reference"),
    ("[Dimension].CurrentMember", "SELECTEDVALUE(Table[Column])", "Current member"),
    ("[Dimension].Children", "VALUES(Table[Column])", "Children → VALUES"),
    ("[Dimension].Parent", "LOOKUPVALUE(parent, ...)", "Parent navigation"),
    ("Aggregate(set)", "CALCULATE(SUM, filter)", "Set aggregation"),
    ("Filter(set, condition)", "CALCULATE(measure, FILTER)", "MDX Filter → DAX FILTER"),
    ("CrossJoin(set1, set2)", "CROSSJOIN(Table1, Table2)", "Cross join"),
    ("IIF(cond, true, false)", "IF(cond, true, false)", "Conditional"),
    ("IsEmpty(expr)", "ISBLANK(expr)", "Empty test"),
    ("CASE WHEN", "SWITCH(TRUE())", "Case statement"),
    (".Lag(n)", "CALCULATE(measure, DATEADD(..., -n))", "Lag → DATEADD"),
    (".Lead(n)", "CALCULATE(measure, DATEADD(..., n))", "Lead → DATEADD"),
    ("PeriodsToDate", "DATESYTD / DATESMTD / DATESQTD", "Period to date"),
    ("ParallelPeriod", "PARALLELPERIOD", "Parallel period"),
    ("YTD(member)", "CALCULATE(measure, DATESYTD)", "Year to date"),
    ("QTD(member)", "CALCULATE(measure, DATESQTD)", "Quarter to date"),
    ("MTD(member)", "CALCULATE(measure, DATESMTD)", "Month to date"),
]


# =====================================================================
# Essbase → Fabric type mapping (outline → semantic model)
# =====================================================================

ESSBASE_TO_TMDL_MAPPING: dict[str, str] = {
    # Essbase concept → TMDL/Power BI concept
    "Cube": "Semantic Model",
    "Dimension (Accounts)": "Measures + Calculated Columns",
    "Dimension (Time)": "Date Table (mark as date table)",
    "Dimension (Regular)": "Table with hierarchy",
    "Dimension (Attribute)": "Column on parent dimension table",
    "Generation": "Hierarchy Level",
    "Level0 Member": "Leaf-level row in dimension table",
    "Upper-level Member": "Parent in parent-child hierarchy or level",
    "Dense Dimension": "Column (inline in fact table if small)",
    "Sparse Dimension": "Separate dimension table with relationship",
    "Stored Member": "Column / Row",
    "Dynamic Calc Member": "DAX Measure",
    "Calc Script": "DAX Measures + Calculated Tables",
    "Business Rule": "DAX Measures (or Fabric Notebook for ETL rules)",
    "Essbase Filter (Security)": "RLS Role (DAX filter)",
    "Substitution Variable": "What-if Parameter or DAX variable",
    "UDA (User-Defined Attribute)": "Column on dimension table",
    "Alias Table": "Display name mapping (translations or column rename)",
    "Shared Member": "Alternate hierarchy (or role-playing dimension)",
    "Data Cell": "Fact table row (measures + dimension keys)",
    "ASO Cube": "Import mode semantic model",
    "BSO Cube": "Import mode with scheduled refresh",
}


# =====================================================================
# Essbase Connector (stub)
# =====================================================================


class EssbaseConnector(SourceConnector):
    """Oracle Essbase connector — REST API + outline parsing (stub).

    Planned capabilities:
    - Connect to Essbase via REST API (cloud) or MaxL (on-prem)
    - Extract cube outlines (dimensions, hierarchies, members)
    - Parse calc scripts and translate to DAX
    - Parse MDX queries and translate to DAX
    - Extract Essbase filters for RLS migration
    - Map substitution variables to What-if parameters
    """

    def __init__(self) -> None:
        self._connected = False
        self._config: dict[str, Any] = {}

    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            platform="essbase",  # type: ignore[arg-type]
            name="Oracle Essbase Connector",
            version="0.1.0",
            description="Essbase REST API + outline parsing (stub)",
            supported_asset_types=[
                "cube",
                "dimension",
                "calcScript",
                "businessRule",
                "filter",
                "substitutionVariable",
                "mdxQuery",
            ],
            is_stub=True,
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        self._config = config
        self._connected = True
        logger.info("Essbase connector connected (stub)")
        return True

    async def discover(self) -> list[ExtractedAsset]:
        return []

    async def extract_metadata(
        self, asset_ids: list[str] | None = None
    ) -> ExtractionResult:
        return ExtractionResult(platform="essbase")

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("Essbase connector disconnected")
