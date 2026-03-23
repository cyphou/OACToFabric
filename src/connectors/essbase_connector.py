"""Essbase connector — outline extraction + calc script parsing + REST API.

Provides full support for migrating Oracle Essbase cubes to Microsoft
Fabric & Power BI:

- ``EssbaseOutlineParser`` — parse Essbase outline XML (dimensions, hierarchies, members)
- ``EssbaseCalcTranslator`` — translate Essbase calc scripts → DAX
- ``EssbaseMdxTranslator`` — translate Essbase MDX → DAX
- ``EssbaseRestClient`` — async wrapper around Essbase REST API (21.3+)
- ``EssbaseConnector`` — full SourceConnector implementation
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree as ET

from src.connectors.base_connector import (
    ConnectorInfo,
    ExtractedAsset,
    ExtractionResult,
    SourceConnector,
    SourcePlatform,
)

logger = logging.getLogger(__name__)


# =====================================================================
# Essbase-specific data models
# =====================================================================


@dataclass
class EssbaseMember:
    """A member inside a dimension."""

    name: str
    alias: str = ""
    parent: str = ""
    generation: int = 0
    level: int = 0
    consolidation: str = "+"  # + - * / ~ ^
    storage_type: str = "store"  # store | dynamic_calc | shared | label_only | never_share
    formula: str = ""
    uda_list: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)


@dataclass
class EssbaseDimension:
    """An Essbase dimension extracted from an outline."""

    name: str
    dimension_type: str = "regular"  # regular | accounts | time | attribute
    members: list[str] = field(default_factory=list)
    member_details: list[EssbaseMember] = field(default_factory=list)
    generation_count: int = 0
    storage_type: str = "dense"  # dense | sparse
    alias_table: str = "Default"


@dataclass
class EssbaseCalcScript:
    """A calc script extracted from an Essbase application."""

    name: str
    content: str
    application: str = ""
    database: str = ""
    description: str = ""


@dataclass
class EssbaseFilter:
    """An Essbase security filter."""

    name: str
    rows: list[dict[str, str]] = field(default_factory=list)
    # Each row: {"member": "...", "access": "read|write|none|metaread"}


@dataclass
class EssbaseSubstitutionVar:
    """An Essbase substitution variable."""

    name: str
    value: str
    scope: str = "application"  # application | database | server


@dataclass
class ParsedOutline:
    """Result of parsing an Essbase outline."""

    application: str = ""
    database: str = ""
    dimensions: list[EssbaseDimension] = field(default_factory=list)
    calc_scripts: list[EssbaseCalcScript] = field(default_factory=list)
    filters: list[EssbaseFilter] = field(default_factory=list)
    substitution_vars: list[EssbaseSubstitutionVar] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and len(self.dimensions) > 0

    @property
    def total_members(self) -> int:
        return sum(len(d.members) for d in self.dimensions)

    @property
    def total_dynamic_calcs(self) -> int:
        count = 0
        for d in self.dimensions:
            for m in d.member_details:
                if m.storage_type == "dynamic_calc":
                    count += 1
        return count

    @property
    def dimension_names(self) -> list[str]:
        return [d.name for d in self.dimensions]


@dataclass
class EssbaseCalcRule:
    """A translation rule for Essbase calc script → DAX."""

    essbase_function: str
    dax_equivalent: str
    difficulty: str = "direct"  # direct | parametric | complex | unsupported
    notes: str = ""


@dataclass
class CalcTranslationResult:
    """Result of translating one calc script or formula."""

    source_name: str
    source_formula: str
    dax_expression: str
    method: str = "rules"  # rules | unsupported
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)


# =====================================================================
# Calc script → DAX mapping
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
    EssbaseCalcRule("@IRSIBLINGS", "FILTER + ALLEXCEPT", "complex", "Right siblings"),
    EssbaseCalcRule("@ILSIBLINGS", "FILTER + ALLEXCEPT", "complex", "Left siblings"),
    EssbaseCalcRule("@CURGEN", "hierarchy generation reference", "complex", "Current gen"),
    EssbaseCalcRule("@CURLEV", "hierarchy level reference", "complex", "Current level"),
    EssbaseCalcRule("@MDANCESTVAL", "LOOKUPVALUE + ancestor hierarchy", "complex", "MD ancestor"),
    EssbaseCalcRule("@MDPARENTVAL", "LOOKUPVALUE + parent", "complex", "MD parent value"),
    EssbaseCalcRule("@MDSHIFT", "CALCULATE(measure, DATEADD)", "complex", "Multi-dim time shift"),
    EssbaseCalcRule("@SHIFT", "CALCULATE(measure, DATEADD)", "parametric", "Time shift"),
    EssbaseCalcRule("@SHIFTSIBLING", "CALCULATE + sibling filter", "complex", "Sibling shift"),
    # Allocation
    EssbaseCalcRule("@ALLOCATE", "manual DAX allocation pattern", "unsupported", "Allocation → manual"),
    EssbaseCalcRule("@MDALLOCATE", "manual DAX allocation pattern", "unsupported", "MD allocation → manual"),
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
    EssbaseCalcRule("@INT", "INT", "direct", "Integer truncation"),
    EssbaseCalcRule("@REMAINDER", "MOD", "direct", "Remainder"),
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
    # Range / cross-dim
    EssbaseCalcRule("@RANGE", "FILTER range pattern", "complex", "Member range"),
    EssbaseCalcRule("@TODATE", "DATESYTD / DATESMTD", "parametric", "Essbase TODATE → DAX period-to-date"),
    EssbaseCalcRule("@CONCATENATE", "CONCATENATE / &", "direct", "String concat"),
    EssbaseCalcRule("@SUBSTRING", "MID", "direct", "Substring"),
    EssbaseCalcRule("@NAME", "SELECTEDVALUE / FORMAT", "parametric", "Member name"),
    # Boolean / existence
    EssbaseCalcRule("@ISUDA", "column check", "complex", "UDA membership test"),
    EssbaseCalcRule("@ISSAMEGEN", "generation comparison", "complex", "Same gen test"),
    EssbaseCalcRule("@ISSAMELEV", "level comparison", "complex", "Same level test"),
    EssbaseCalcRule("#MISSING", "BLANK()", "direct", "#MISSING → BLANK()"),
    EssbaseCalcRule("@ISMISSING", "ISBLANK", "direct", "Missing test → ISBLANK"),
]


# Regex-based pattern matching for calc script translation
_ESSBASE_CALC_PATTERNS: list[tuple[str, str, str]] = [
    # (regex pattern, replacement, difficulty)
    # Aggregation
    (r"@SUM\s*\(", "SUM(", "direct"),
    (r"@AVG\s*\(", "AVERAGE(", "direct"),
    (r"@COUNT\s*\(", "COUNTROWS(", "parametric"),
    (r"@MIN\s*\(", "MIN(", "direct"),
    (r"@MAX\s*\(", "MAX(", "direct"),
    # Math
    (r"@ABS\s*\(", "ABS(", "direct"),
    (r"@ROUND\s*\(", "ROUND(", "direct"),
    (r"@POWER\s*\(", "POWER(", "direct"),
    (r"@LOG10\s*\(", "LOG10(", "direct"),
    (r"@LOG\s*\(", "LOG(", "direct"),
    (r"@EXP\s*\(", "EXP(", "direct"),
    (r"@SQRT\s*\(", "SQRT(", "direct"),
    (r"@MOD\s*\(", "MOD(", "direct"),
    (r"@TRUNCATE\s*\(", "TRUNC(", "direct"),
    (r"@INT\s*\(", "INT(", "direct"),
    (r"@REMAINDER\s*\(", "MOD(", "direct"),
    # String
    (r"@CONCATENATE\s*\(", "CONCATENATE(", "direct"),
    (r"@SUBSTRING\s*\(", "MID(", "direct"),
    (r"@NAME\s*\(", "SELECTEDVALUE(", "parametric"),
    # Missing
    (r"#MISSING", "BLANK()", "direct"),
    (r"@ISMISSING\s*\(", "ISBLANK(", "direct"),
    # Cross-dimensional → CALCULATE pattern
    (r"@PRIOR\s*\(", "CALCULATE( /* @PRIOR */ ", "parametric"),
    (r"@NEXT\s*\(", "CALCULATE( /* @NEXT */ ", "parametric"),
    (r"@SHIFT\s*\(", "CALCULATE( /* @SHIFT */ ", "parametric"),
    (r"@PARENTVAL\s*\(", "CALCULATE( /* @PARENTVAL */ ", "complex"),
    (r"@ANCEST\s*\(", "CALCULATE( /* @ANCEST */ ", "complex"),
    (r"@SUMRANGE\s*\(", "CALCULATE(SUM( /* @SUMRANGE */ ", "complex"),
    (r"@AVGRANGE\s*\(", "CALCULATE(AVERAGE( /* @AVGRANGE */ ", "complex"),
    (r"@TODATE\s*\(", "CALCULATE( /* @TODATE */ ", "parametric"),
    # Member functions → comments
    (r"@CHILDREN\s*\(", "/* @CHILDREN → hierarchy filter */ FILTER(", "complex"),
    (r"@DESCENDANTS\s*\(", "/* @DESCENDANTS → PATH filter */ FILTER(", "complex"),
    (r"@SIBLINGS\s*\(", "/* @SIBLINGS → level filter */ FILTER(", "complex"),
    (r"@PARENT\s*\(", "/* @PARENT → LOOKUPVALUE */ LOOKUPVALUE(", "complex"),
    (r"@ISMBR\s*\(", "/* @ISMBR */ HASONEVALUE(", "parametric"),
    (r"@ISLEV\s*\(", "/* @ISLEV level check */ ", "complex"),
    (r"@ISGEN\s*\(", "/* @ISGEN generation check */ ", "complex"),
    (r"@ISUDA\s*\(", "/* @ISUDA check */ ", "complex"),
    # Allocation → unsupported
    (r"@ALLOCATE\s*\(", "/* @ALLOCATE: manual allocation needed */ ", "unsupported"),
    (r"@MDALLOCATE\s*\(", "/* @MDALLOCATE: manual allocation needed */ ", "unsupported"),
    # Financial
    (r"@VAR\s*\(", "/* @VAR variance pattern */ ", "complex"),
    (r"@VARPER\s*\(", "DIVIDE( /* @VARPER */ ", "complex"),
]


class EssbaseCalcTranslator:
    """Translate Essbase calc script formulas to DAX.

    Uses rule-based regex translation for standard functions
    and flags complex/unsupported patterns for manual review.
    """

    def __init__(self) -> None:
        self._rules = _ESSBASE_CALC_PATTERNS

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    @property
    def catalog(self) -> list[EssbaseCalcRule]:
        return ESSBASE_TO_DAX_RULES

    def translate(self, script: EssbaseCalcScript) -> CalcTranslationResult:
        """Translate a single calc script."""
        return self.translate_formula(script.content, source_name=script.name)

    def translate_formula(self, formula: str, source_name: str = "") -> CalcTranslationResult:
        """Translate a single formula string."""
        text = formula.strip()
        warnings: list[str] = []
        confidence = 1.0
        dax = text

        for pattern, replacement, difficulty in self._rules:
            if re.search(pattern, dax, re.IGNORECASE):
                if difficulty == "unsupported":
                    warnings.append(f"Unsupported: {pattern.strip()}")
                    confidence = min(confidence, 0.2)
                elif difficulty == "complex":
                    warnings.append(f"Complex mapping: {pattern.strip()}")
                    confidence = min(confidence, 0.5)
                elif difficulty == "parametric":
                    confidence = min(confidence, 0.7)
                dax = re.sub(pattern, replacement, dax, flags=re.IGNORECASE)

        method = "rules"
        if any("Unsupported" in w for w in warnings):
            method = "unsupported"

        return CalcTranslationResult(
            source_name=source_name,
            source_formula=formula,
            dax_expression=dax,
            method=method,
            confidence=confidence,
            warnings=warnings,
        )

    def translate_batch(self, scripts: list[EssbaseCalcScript]) -> list[CalcTranslationResult]:
        """Translate a batch of calc scripts."""
        return [self.translate(s) for s in scripts]


# =====================================================================
# MDX → DAX translation
# =====================================================================


# Regex-based MDX → DAX patterns
_ESSBASE_MDX_PATTERNS: list[tuple[str, str, str]] = [
    # Measure references
    (r"\[Measures\]\.\[([^\]]+)\]", r"[\1]", "direct"),
    # Member access
    (r"\[(\w+)\]\.CurrentMember", r"SELECTEDVALUE('\1'[\1])", "parametric"),
    (r"\[(\w+)\]\.Children", r"VALUES('\1'[\1])", "parametric"),
    (r"\[(\w+)\]\.Parent", r"LOOKUPVALUE(/* parent of \1 */)", "complex"),
    # Lag / Lead
    (r"\.Lag\s*\(\s*(\d+)\s*\)", r"/* Lag(\1) → DATEADD */ ", "complex"),
    (r"\.Lead\s*\(\s*(\d+)\s*\)", r"/* Lead(\1) → DATEADD */ ", "complex"),
    # Time intelligence
    (r"\bYTD\s*\(", "CALCULATE(measure, DATESYTD(", "parametric"),
    (r"\bQTD\s*\(", "CALCULATE(measure, DATESQTD(", "parametric"),
    (r"\bMTD\s*\(", "CALCULATE(measure, DATESMTD(", "parametric"),
    (r"\bPeriodsToDate\s*\(", "/* PeriodsToDate */ DATESYTD(", "parametric"),
    (r"\bParallelPeriod\s*\(", "PARALLELPERIOD(", "parametric"),
    # Functions
    (r"\bAggregate\s*\(", "CALCULATE(SUM(", "complex"),
    (r"\bFilter\s*\(", "CALCULATE(measure, FILTER(", "complex"),
    (r"\bCrossJoin\s*\(", "CROSSJOIN(", "complex"),
    (r"\bIIF\s*\(", "IF(", "direct"),
    (r"\bIsEmpty\s*\(", "ISBLANK(", "direct"),
    (r"\bCASE\s+WHEN\b", "SWITCH(TRUE(),", "parametric"),
    # Set operations
    (r"\bUnion\s*\(", "UNION(", "direct"),
    (r"\bIntersect\s*\(", "INTERSECT(", "direct"),
    (r"\bExcept\s*\(", "EXCEPT(", "direct"),
    # Ordering
    (r"\bOrder\s*\(", "/* Order → TOPN/RANKX */ ", "complex"),
    (r"\bTopCount\s*\(", "TOPN(", "parametric"),
    (r"\bBottomCount\s*\(", "TOPN( /* reversed */ ", "parametric"),
    # Numeric
    (r"\bCoalesceEmpty\s*\(", "COALESCE(", "direct"),
    (r"\bAbs\s*\(", "ABS(", "direct"),
    (r"\bRound\s*\(", "ROUND(", "direct"),
    (r"\bInt\s*\(", "INT(", "direct"),
]


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
    ("Union(set1, set2)", "UNION(Table1, Table2)", "Union"),
    ("Intersect(set1, set2)", "INTERSECT(Table1, Table2)", "Intersect"),
    ("Except(set1, set2)", "EXCEPT(Table1, Table2)", "Except"),
    ("TopCount(set, n, expr)", "TOPN(n, Table, expr)", "Top count"),
    ("BottomCount(set, n, expr)", "TOPN(n, Table, expr, ASC)", "Bottom count"),
    ("CoalesceEmpty(expr, default)", "COALESCE(expr, default)", "Coalesce empty"),
    ("Order(set, expr)", "TOPN / RANKX pattern", "Ordering"),
]


class EssbaseMdxTranslator:
    """Translate Essbase MDX to DAX expressions."""

    def __init__(self) -> None:
        self._rules = _ESSBASE_MDX_PATTERNS

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def translate(self, mdx: str, source_name: str = "") -> CalcTranslationResult:
        """Translate an MDX query or expression to DAX."""
        text = mdx.strip()
        warnings: list[str] = []
        confidence = 1.0
        dax = text

        for pattern, replacement, difficulty in self._rules:
            if re.search(pattern, dax, re.IGNORECASE):
                if difficulty == "complex":
                    warnings.append(f"Complex MDX mapping: {pattern}")
                    confidence = min(confidence, 0.5)
                elif difficulty == "parametric":
                    confidence = min(confidence, 0.7)
                dax = re.sub(pattern, replacement, dax, flags=re.IGNORECASE)

        return CalcTranslationResult(
            source_name=source_name,
            source_formula=mdx,
            dax_expression=dax,
            method="rules",
            confidence=confidence,
            warnings=warnings,
        )


# =====================================================================
# Essbase → Fabric type mapping (outline → semantic model)
# =====================================================================

ESSBASE_TO_TMDL_MAPPING: dict[str, str] = {
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
# Essbase Outline Parser
# =====================================================================


class EssbaseOutlineParser:
    """Parse Essbase outline XML exported via REST API or MaxL.

    Supports the JSON format returned by:
      GET /essbase/rest/v1/applications/{app}/databases/{db}/outline

    Also parses XML produced by outline export tools.
    """

    def parse_xml(self, data: bytes | str, app: str = "", db: str = "") -> ParsedOutline:
        """Parse outline from XML bytes or string."""
        result = ParsedOutline(application=app, database=db)

        try:
            if isinstance(data, bytes):
                root = ET.fromstring(data)
            else:
                root = ET.fromstring(data.encode("utf-8"))
        except ET.ParseError as exc:
            result.errors.append(f"XML parse error: {exc}")
            return result

        # Parse dimensions
        for dim_elem in root.iter("dimension"):
            result.dimensions.append(self._parse_dimension(dim_elem))

        # If no <dimension> tags, try top-level members as dimensions
        if not result.dimensions:
            for member_elem in root.iter("member"):
                if member_elem.get("dimension", "").lower() == "true":
                    dim = self._member_as_dimension(member_elem)
                    result.dimensions.append(dim)

        # If root is an outline tag with direct children
        if not result.dimensions and root.tag in ("outline", "Outline"):
            for child in root:
                if child.tag in ("dimension", "Dimension", "member", "Member"):
                    result.dimensions.append(self._parse_dimension(child))

        return result

    def parse_json(self, data: dict[str, Any], app: str = "", db: str = "") -> ParsedOutline:
        """Parse outline from JSON dict (REST API response)."""
        result = ParsedOutline(application=app, database=db)

        dims = data.get("dimensions", data.get("children", []))
        if isinstance(dims, list):
            for dim_data in dims:
                result.dimensions.append(self._parse_dimension_json(dim_data))

        return result

    def _parse_dimension(self, elem: ET.Element) -> EssbaseDimension:
        """Parse a <dimension> or <member> element as a dimension."""
        dim = EssbaseDimension(
            name=elem.get("name", elem.get("Name", elem.text or "")),
            dimension_type=self._detect_dim_type(elem),
            storage_type=elem.get("storageType", elem.get("storage", "dense")).lower(),
        )

        for mbr_elem in elem.iter("member"):
            mbr = self._parse_member(mbr_elem)
            dim.members.append(mbr.name)
            dim.member_details.append(mbr)

        dim.generation_count = max(
            (m.generation for m in dim.member_details), default=0
        )

        return dim

    def _member_as_dimension(self, elem: ET.Element) -> EssbaseDimension:
        """Convert a member element flagged as dimension."""
        return self._parse_dimension(elem)

    def _parse_member(self, elem: ET.Element, generation: int = 0) -> EssbaseMember:
        """Parse a <member> element."""
        name = elem.get("name", elem.get("Name", elem.text or ""))
        return EssbaseMember(
            name=name,
            alias=elem.get("alias", ""),
            parent=elem.get("parent", ""),
            generation=int(elem.get("generation", str(generation))),
            level=int(elem.get("level", "0")),
            consolidation=elem.get("consolidation", "+"),
            storage_type=elem.get("storageType", "store"),
            formula=elem.get("formula", ""),
            uda_list=[u.strip() for u in elem.get("uda", "").split(",") if u.strip()],
        )

    def _parse_dimension_json(self, data: dict[str, Any]) -> EssbaseDimension:
        """Parse a dimension from JSON (REST API format)."""
        dim = EssbaseDimension(
            name=data.get("name", ""),
            dimension_type=data.get("dimensionType", "regular").lower(),
            storage_type=data.get("storageType", "dense").lower(),
        )

        for mbr_data in data.get("children", data.get("members", [])):
            mbr = self._parse_member_json(mbr_data)
            dim.members.append(mbr.name)
            dim.member_details.append(mbr)
            self._collect_members_json(mbr_data, dim)

        dim.generation_count = max(
            (m.generation for m in dim.member_details), default=0
        )

        return dim

    def _parse_member_json(self, data: dict[str, Any]) -> EssbaseMember:
        """Parse a member from JSON."""
        return EssbaseMember(
            name=data.get("name", ""),
            alias=data.get("aliases", {}).get("Default", ""),
            parent=data.get("parentName", ""),
            generation=data.get("generation", 0),
            level=data.get("levelNumber", 0),
            consolidation=data.get("consolidation", "+"),
            storage_type=data.get("memberSolveOrder", "store"),
            formula=data.get("formula", ""),
            uda_list=data.get("uda", []),
        )

    def _collect_members_json(self, data: dict[str, Any], dim: EssbaseDimension) -> None:
        """Recursively collect members from JSON data."""
        for child in data.get("children", []):
            mbr = self._parse_member_json(child)
            dim.members.append(mbr.name)
            dim.member_details.append(mbr)
            self._collect_members_json(child, dim)

    def _detect_dim_type(self, elem: ET.Element) -> str:
        """Detect dimension type from XML attributes."""
        raw = (
            elem.get("type", "")
            or elem.get("dimType", "")
            or elem.get("dimensionType", "")
        ).lower()
        if "account" in raw:
            return "accounts"
        if "time" in raw:
            return "time"
        if "attribute" in raw or "attr" in raw:
            return "attribute"
        return "regular"


# =====================================================================
# Essbase REST API client
# =====================================================================


@dataclass
class EssbaseApiConfig:
    """Configuration for Essbase REST API access."""

    server_url: str = ""
    username: str = ""
    password: str = ""
    api_version: str = "v1"

    @property
    def base_url(self) -> str:
        return f"{self.server_url.rstrip('/')}/essbase/rest/{self.api_version}"


class EssbaseRestClient:
    """Async client for Essbase REST API (21.3+).

    Supports listing applications/databases, getting outlines,
    listing calc scripts, filters, substitution variables, and
    exporting data.

    HTTP methods are overridable for testing.
    """

    def __init__(self) -> None:
        self._config: EssbaseApiConfig | None = None
        self._connected: bool = False
        self._session_token: str = ""

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, config: EssbaseApiConfig) -> bool:
        """Authenticate via Essbase REST API."""
        self._config = config

        response = await self._http_get(f"{config.base_url}/about")
        if response.get("status") == "error":
            return False

        self._connected = True
        return True

    async def list_applications(self) -> list[dict[str, Any]]:
        """GET /applications — list all Essbase applications."""
        self._require_connected()
        resp = await self._http_get(f"{self._config.base_url}/applications")  # type: ignore[union-attr]
        return resp.get("items", [])

    async def list_databases(self, app_name: str) -> list[dict[str, Any]]:
        """GET /applications/{app}/databases — list databases in an application."""
        self._require_connected()
        resp = await self._http_get(
            f"{self._config.base_url}/applications/{app_name}/databases"  # type: ignore[union-attr]
        )
        return resp.get("items", [])

    async def get_outline(self, app: str, db: str) -> dict[str, Any]:
        """GET /applications/{app}/databases/{db}/outline — get cube outline."""
        self._require_connected()
        return await self._http_get(
            f"{self._config.base_url}/applications/{app}/databases/{db}/outline"  # type: ignore[union-attr]
        )

    async def list_calc_scripts(self, app: str, db: str) -> list[dict[str, Any]]:
        """GET /applications/{app}/databases/{db}/scripts — list calc scripts."""
        self._require_connected()
        resp = await self._http_get(
            f"{self._config.base_url}/applications/{app}/databases/{db}/scripts"  # type: ignore[union-attr]
        )
        return resp.get("items", [])

    async def get_calc_script(self, app: str, db: str, script_name: str) -> str:
        """GET /applications/{app}/databases/{db}/scripts/{name} — get script content."""
        self._require_connected()
        resp = await self._http_get(
            f"{self._config.base_url}/applications/{app}/databases/{db}/scripts/{script_name}"  # type: ignore[union-attr]
        )
        return resp.get("content", "")

    async def list_filters(self, app: str, db: str) -> list[dict[str, Any]]:
        """GET /applications/{app}/databases/{db}/filters — list security filters."""
        self._require_connected()
        resp = await self._http_get(
            f"{self._config.base_url}/applications/{app}/databases/{db}/filters"  # type: ignore[union-attr]
        )
        return resp.get("items", [])

    async def list_variables(self, app: str) -> list[dict[str, Any]]:
        """GET /applications/{app}/variables — list substitution variables."""
        self._require_connected()
        resp = await self._http_get(
            f"{self._config.base_url}/applications/{app}/variables"  # type: ignore[union-attr]
        )
        return resp.get("items", [])

    async def disconnect(self) -> None:
        """Close the session."""
        self._session_token = ""
        self._connected = False

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Not connected — call connect() first")

    # --- HTTP transport (overridable for testing) ---

    async def _http_get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """GET request returning JSON. Override for testing."""
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required: pip install httpx")
        async with httpx.AsyncClient() as client:
            headers = self._auth_headers()
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _http_post(self, url: str, json_body: dict[str, Any]) -> dict[str, Any]:
        """POST request returning JSON. Override for testing."""
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required: pip install httpx")
        async with httpx.AsyncClient() as client:
            headers = self._auth_headers()
            resp = await client.post(url, json=json_body, headers=headers)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    def _auth_headers(self) -> dict[str, str]:
        """Build auth headers (Basic auth for Essbase REST API)."""
        if self._config and self._config.username:
            import base64

            creds = base64.b64encode(
                f"{self._config.username}:{self._config.password}".encode()
            ).decode()
            return {"Authorization": f"Basic {creds}"}
        return {}


# =====================================================================
# Full Essbase SourceConnector
# =====================================================================


class EssbaseConnector(SourceConnector):
    """Production Oracle Essbase connector — REST API + outline parsing.

    Capabilities:
    - Connect to Essbase via REST API (cloud/on-prem)
    - Discover applications, databases (cubes), dimensions, members
    - Extract calc scripts and translate to DAX
    - Extract MDX queries and translate to DAX
    - Extract security filters for RLS migration
    - Extract substitution variables for What-if parameter mapping
    """

    def __init__(self) -> None:
        self._client = EssbaseRestClient()
        self._parser = EssbaseOutlineParser()
        self._calc_translator = EssbaseCalcTranslator()
        self._mdx_translator = EssbaseMdxTranslator()
        self._discovered: list[ExtractedAsset] = []
        self._connected = False

    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            platform=SourcePlatform.ESSBASE,
            name="Oracle Essbase Connector",
            version="1.0.0",
            description=(
                "Full Essbase connector — REST API + outline parsing + "
                "calc script → DAX + MDX → DAX translation"
            ),
            supported_asset_types=[
                "cube",
                "dimension",
                "calcScript",
                "businessRule",
                "filter",
                "substitutionVariable",
                "mdxQuery",
            ],
            is_stub=False,
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        """Connect to Essbase REST API."""
        api_config = EssbaseApiConfig(
            server_url=config.get("server_url", ""),
            username=config.get("username", ""),
            password=config.get("password", ""),
            api_version=config.get("api_version", "v1"),
        )
        try:
            result = await self._client.connect(api_config)
            self._connected = result
            if result:
                logger.info("Essbase connector connected to %s", api_config.server_url)
            return result
        except Exception as exc:
            logger.error("Essbase connection failed: %s", exc)
            return False

    async def discover(self) -> list[ExtractedAsset]:
        """Discover all Essbase assets via REST API."""
        if not self._connected:
            raise RuntimeError("Not connected")

        assets: list[ExtractedAsset] = []

        apps = await self._client.list_applications()
        for app_data in apps:
            app_name = app_data.get("name", "")
            if not app_name:
                continue

            dbs = await self._client.list_databases(app_name)
            for db_data in dbs:
                db_name = db_data.get("name", "")
                cube_id = f"{app_name}.{db_name}"

                assets.append(ExtractedAsset(
                    asset_id=cube_id,
                    asset_type="cube",
                    name=db_name,
                    source_path=f"/{app_name}/{db_name}",
                    platform="essbase",
                    metadata={
                        "application": app_name,
                        "database": db_name,
                        "cube_type": db_data.get("type", "BSO"),
                    },
                ))

                # Get outline → dimensions
                try:
                    outline_data = await self._client.get_outline(app_name, db_name)
                    parsed = self._parser.parse_json(outline_data, app=app_name, db=db_name)
                    for dim in parsed.dimensions:
                        dim_id = f"{cube_id}.{dim.name}"
                        assets.append(ExtractedAsset(
                            asset_id=dim_id,
                            asset_type="dimension",
                            name=dim.name,
                            source_path=f"/{app_name}/{db_name}/{dim.name}",
                            platform="essbase",
                            metadata={
                                "dimension_type": dim.dimension_type,
                                "storage_type": dim.storage_type,
                                "member_count": len(dim.members),
                                "generation_count": dim.generation_count,
                            },
                            dependencies=[cube_id],
                        ))
                except Exception as exc:
                    logger.warning("Failed to get outline for %s: %s", cube_id, exc)

                # List calc scripts
                try:
                    scripts = await self._client.list_calc_scripts(app_name, db_name)
                    for script_data in scripts:
                        script_name = script_data.get("name", "")
                        script_id = f"{cube_id}.calc.{script_name}"
                        assets.append(ExtractedAsset(
                            asset_id=script_id,
                            asset_type="calcScript",
                            name=script_name,
                            source_path=f"/{app_name}/{db_name}/scripts/{script_name}",
                            platform="essbase",
                            metadata={"application": app_name, "database": db_name},
                            dependencies=[cube_id],
                        ))
                except Exception as exc:
                    logger.warning("Failed to list calc scripts for %s: %s", cube_id, exc)

                # List filters
                try:
                    filters = await self._client.list_filters(app_name, db_name)
                    for flt_data in filters:
                        flt_name = flt_data.get("name", "")
                        flt_id = f"{cube_id}.filter.{flt_name}"
                        assets.append(ExtractedAsset(
                            asset_id=flt_id,
                            asset_type="filter",
                            name=flt_name,
                            source_path=f"/{app_name}/{db_name}/filters/{flt_name}",
                            platform="essbase",
                            metadata={"application": app_name, "database": db_name},
                            dependencies=[cube_id],
                        ))
                except Exception as exc:
                    logger.warning("Failed to list filters for %s: %s", cube_id, exc)

            # List substitution variables per application
            try:
                variables = await self._client.list_variables(app_name)
                for var_data in variables:
                    var_name = var_data.get("name", "")
                    var_id = f"{app_name}.var.{var_name}"
                    assets.append(ExtractedAsset(
                        asset_id=var_id,
                        asset_type="substitutionVariable",
                        name=var_name,
                        source_path=f"/{app_name}/variables/{var_name}",
                        platform="essbase",
                        metadata={
                            "value": var_data.get("value", ""),
                            "scope": var_data.get("scope", "application"),
                        },
                    ))
            except Exception as exc:
                logger.warning("Failed to list variables for %s: %s", app_name, exc)

        self._discovered = assets
        logger.info("Essbase discovery: found %d assets", len(assets))
        return assets

    async def extract_metadata(
        self, asset_ids: list[str] | None = None
    ) -> ExtractionResult:
        """Extract detailed metadata for discovered assets."""
        if asset_ids is None:
            assets = self._discovered
        else:
            id_set = set(asset_ids)
            assets = [a for a in self._discovered if a.asset_id in id_set]

        errors: list[str] = []
        enriched: list[ExtractedAsset] = []

        for asset in assets:
            try:
                if asset.asset_type == "calcScript":
                    app = asset.metadata.get("application", "")
                    db = asset.metadata.get("database", "")
                    content = await self._client.get_calc_script(app, db, asset.name)
                    translation = self._calc_translator.translate_formula(
                        content, source_name=asset.name
                    )
                    asset.metadata["content"] = content
                    asset.metadata["dax_translation"] = translation.dax_expression
                    asset.metadata["translation_confidence"] = translation.confidence
                    asset.metadata["translation_warnings"] = translation.warnings
                    asset.raw_definition = content
                enriched.append(asset)
            except Exception as exc:
                errors.append(f"Error extracting {asset.asset_id}: {exc}")
                enriched.append(asset)

        return ExtractionResult(
            platform="essbase",
            assets=enriched,
            errors=errors,
        )

    async def disconnect(self) -> None:
        """Disconnect from Essbase."""
        await self._client.disconnect()
        self._connected = False
        self._discovered = []
        logger.info("Essbase connector disconnected")
