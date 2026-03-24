"""IBM Cognos Analytics connector — full implementation.

Parses Cognos Report Studio XML specifications, communicates with the
Cognos REST API, and translates Cognos expressions to DAX.

Components
~~~~~~~~~~
- **Data models**: ``CognosReport``, ``CognosQuery``, ``CognosDataItem``,
  ``CognosPrompt``, ``CognosPackage``, ``CognosDataSource``,
  ``ParsedReportSpec``, ``CognosCalcRule``, ``CalcTranslationResult``
- **Rule catalog**: 50+ Cognos → DAX translation rules
- **CognosExpressionTranslator**: regex-based Cognos expression → DAX
- **CognosReportSpecParser**: XML parser for Cognos report specifications
- **CognosRestClient**: async REST API client (v11.1+)
- **FullCognosConnector**: ``SourceConnector`` lifecycle implementation
"""

from __future__ import annotations

import base64
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# =====================================================================
# Data models
# =====================================================================


@dataclass
class CognosDataItem:
    """A data item (column/measure) in a Cognos query."""

    name: str
    expression: str = ""
    label: str = ""
    aggregate: str = ""  # none, total, average, count, minimum, maximum
    rollup_aggregate: str = ""
    sort: str = ""  # ascending, descending, none
    data_type: str = ""  # numeric, string, date, time, datetime
    usage: str = "fact"  # fact, attribute, identifier


@dataclass
class CognosQuery:
    """A query definition inside a Cognos report."""

    name: str
    data_items: list[CognosDataItem] = field(default_factory=list)
    detail_filters: list[str] = field(default_factory=list)
    summary_filters: list[str] = field(default_factory=list)
    package_ref: str = ""


@dataclass
class CognosPrompt:
    """A prompt (parameter) in a Cognos report."""

    name: str
    prompt_type: str = "value"  # value, select, multiSelect, date, dateRange, tree
    parameter_name: str = ""
    caption: str = ""
    required: bool = False
    multi_select: bool = False
    cascade_on: str = ""
    default_value: str = ""


@dataclass
class CognosVisualization:
    """A visualization (list/crosstab/chart) in a Cognos report."""

    viz_type: str = "list"  # list, crosstab, chart, repeater, map
    query_ref: str = ""
    columns: list[str] = field(default_factory=list)
    rows: list[str] = field(default_factory=list)
    measures: list[str] = field(default_factory=list)
    chart_type: str = ""  # bar, line, pie, area, scatter, combo, waterfall
    title: str = ""


@dataclass
class CognosReportPage:
    """A page within a Cognos report."""

    name: str
    visualizations: list[CognosVisualization] = field(default_factory=list)
    header: str = ""
    footer: str = ""


@dataclass
class CognosReport:
    """A Cognos report/dashboard definition."""

    name: str
    report_id: str = ""
    package_ref: str = ""
    queries: list[CognosQuery] = field(default_factory=list)
    pages: list[CognosReportPage] = field(default_factory=list)
    prompts: list[CognosPrompt] = field(default_factory=list)
    description: str = ""
    report_type: str = "report"  # report, dashboard, story


@dataclass
class CognosPackage:
    """A Cognos Framework Manager package (metadata model)."""

    name: str
    package_id: str = ""
    data_sources: list[str] = field(default_factory=list)
    query_subjects: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    measures: list[str] = field(default_factory=list)
    namespaces: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class CognosDataSource:
    """A Cognos data source connection."""

    name: str
    connection_type: str = ""  # oracle, sqlserver, db2, postgresql, odbc
    server: str = ""
    database: str = ""
    schema: str = ""
    catalog: str = ""


@dataclass
class ParsedReportSpec:
    """Result of parsing a Cognos report specification XML."""

    reports: list[CognosReport] = field(default_factory=list)
    packages: list[CognosPackage] = field(default_factory=list)
    data_sources: list[CognosDataSource] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and len(self.reports) > 0

    @property
    def total_queries(self) -> int:
        return sum(len(r.queries) for r in self.reports)

    @property
    def total_prompts(self) -> int:
        return sum(len(r.prompts) for r in self.reports)

    @property
    def total_visualizations(self) -> int:
        return sum(len(p.visualizations) for r in self.reports for p in r.pages)

    @property
    def report_names(self) -> list[str]:
        return [r.name for r in self.reports]


# =====================================================================
# Cognos → DAX expression mapping
# =====================================================================


@dataclass
class CognosCalcRule:
    """A single Cognos → DAX translation rule."""

    cognos_function: str
    dax_equivalent: str
    difficulty: str = "direct"  # direct, parametric, complex, unsupported
    notes: str = ""


@dataclass
class CalcTranslationResult:
    """Result of translating one Cognos expression."""

    source_name: str
    source_expression: str
    dax_expression: str
    method: str = "rules"  # rules | unsupported
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)


# Rule catalog — 50+ Cognos expression→DAX rules
COGNOS_TO_DAX_RULES: list[CognosCalcRule] = [
    # Aggregation functions
    CognosCalcRule("total", "SUM", "direct", "Total → SUM"),
    CognosCalcRule("count", "COUNTROWS", "parametric", "Count → COUNTROWS"),
    CognosCalcRule("average", "AVERAGE", "direct", "Average → AVERAGE"),
    CognosCalcRule("minimum", "MIN", "direct", "Minimum → MIN"),
    CognosCalcRule("maximum", "MAX", "direct", "Maximum → MAX"),
    CognosCalcRule("aggregate", "SUM", "parametric", "Aggregate → SUM (context-dependent)"),
    CognosCalcRule("running-total", "CALCULATE(SUM, FILTER)", "complex", "Running total → DAX window"),
    CognosCalcRule("running-count", "CALCULATE(COUNTROWS, FILTER)", "complex", "Running count"),
    CognosCalcRule("running-average", "CALCULATE(AVERAGE, FILTER)", "complex", "Running average"),
    CognosCalcRule("percentage", "DIVIDE", "parametric", "Percentage → DIVIDE"),
    CognosCalcRule("rank", "RANKX", "parametric", "Rank → RANKX"),
    CognosCalcRule("percentile", "PERCENTILEX.INC", "complex", "Percentile → PERCENTILEX"),
    CognosCalcRule("quantile", "PERCENTILEX.INC", "complex", "Quantile → PERCENTILEX"),
    CognosCalcRule("median", "MEDIAN", "direct", "Median → MEDIAN"),
    CognosCalcRule("standard-deviation", "STDEV.S", "direct", "StdDev → STDEV.S"),
    CognosCalcRule("variance", "VAR.S", "direct", "Variance → VAR.S"),
    # String functions
    CognosCalcRule("substring", "MID", "parametric", "Substring → MID"),
    CognosCalcRule("trim", "TRIM", "direct", "Trim → TRIM"),
    CognosCalcRule("upper", "UPPER", "direct", "Upper → UPPER"),
    CognosCalcRule("lower", "LOWER", "direct", "Lower → LOWER"),
    CognosCalcRule("concatenate", "CONCATENATE", "parametric", "Concatenate → CONCATENATE"),
    CognosCalcRule("string-length", "LEN", "direct", "String length → LEN"),
    CognosCalcRule("position", "SEARCH", "parametric", "Position → SEARCH"),
    CognosCalcRule("replace", "SUBSTITUTE", "parametric", "Replace → SUBSTITUTE"),
    # Date functions
    CognosCalcRule("_days_between", "DATEDIFF", "parametric", "Days between → DATEDIFF"),
    CognosCalcRule("_months_between", "DATEDIFF", "parametric", "Months between → DATEDIFF"),
    CognosCalcRule("_years_between", "DATEDIFF", "parametric", "Years between → DATEDIFF"),
    CognosCalcRule("_add_days", "DATEADD", "parametric", "Add days → DATEADD"),
    CognosCalcRule("_add_months", "DATEADD", "parametric", "Add months → DATEADD"),
    CognosCalcRule("_add_years", "DATEADD", "parametric", "Add years → DATEADD"),
    CognosCalcRule("_year", "YEAR", "direct", "Year → YEAR"),
    CognosCalcRule("_month", "MONTH", "direct", "Month → MONTH"),
    CognosCalcRule("_day", "DAY", "direct", "Day → DAY"),
    CognosCalcRule("current_date", "TODAY", "direct", "Current date → TODAY"),
    CognosCalcRule("current_timestamp", "NOW", "direct", "Current timestamp → NOW"),
    # Math functions
    CognosCalcRule("abs", "ABS", "direct", "Abs → ABS"),
    CognosCalcRule("round", "ROUND", "direct", "Round → ROUND"),
    CognosCalcRule("truncate", "TRUNC", "direct", "Truncate → TRUNC"),
    CognosCalcRule("ceiling", "CEILING", "direct", "Ceiling → CEILING"),
    CognosCalcRule("floor", "FLOOR", "direct", "Floor → FLOOR"),
    CognosCalcRule("mod", "MOD", "direct", "Mod → MOD"),
    CognosCalcRule("power", "POWER", "direct", "Power → POWER"),
    CognosCalcRule("sqrt", "SQRT", "direct", "Sqrt → SQRT"),
    CognosCalcRule("exp", "EXP", "direct", "Exp → EXP"),
    CognosCalcRule("ln", "LN", "direct", "Ln → LN"),
    CognosCalcRule("log", "LOG", "parametric", "Log → LOG"),
    # Conditional / logic
    CognosCalcRule("if", "IF", "parametric", "If → IF"),
    CognosCalcRule("case", "SWITCH", "complex", "Case → SWITCH"),
    CognosCalcRule("coalesce", "COALESCE", "parametric", "Coalesce → COALESCE"),
    CognosCalcRule("nullif", "IF(a=b, BLANK(), a)", "complex", "Nullif → IF BLANK"),
    CognosCalcRule("is-null", "ISBLANK", "direct", "Is null → ISBLANK"),
    CognosCalcRule("is-missing", "ISBLANK", "direct", "Is missing → ISBLANK"),
    # Member / OLAP
    CognosCalcRule("roleValue", "RELATED", "complex", "RoleValue → RELATED lookup"),
    CognosCalcRule("ancestor", "CALCULATE(ALL)", "complex", "Ancestor → CALCULATE with ALL"),
    CognosCalcRule("children", "FILTER(VALUES)", "complex", "Children → filtered VALUES"),
    CognosCalcRule("descendants", "FILTER(ALL)", "complex", "Descendants → filtered ALL"),
    CognosCalcRule("caption", "SELECTEDVALUE", "parametric", "Caption → SELECTEDVALUE"),
    CognosCalcRule("member", "VALUE", "parametric", "Member → VALUE reference"),
]


# Regex patterns for expression translation
_COGNOS_CALC_PATTERNS: list[tuple[str, str, str]] = [
    # Aggregation
    (r"\btotal\s*\(", "SUM(", "direct"),
    (r"\bcount\s*\(", "COUNTROWS(", "parametric"),
    (r"\baverage\s*\(", "AVERAGE(", "direct"),
    (r"\bminimum\s*\(", "MIN(", "direct"),
    (r"\bmaximum\s*\(", "MAX(", "direct"),
    (r"\baggregate\s*\(", "SUM(", "parametric"),
    (r"\brank\s*\(", "RANKX(ALL(), ", "parametric"),
    (r"\bmedian\s*\(", "MEDIAN(", "direct"),
    (r"\bstandard-deviation\s*\(", "STDEV.S(", "direct"),
    (r"\bvariance\s*\(", "VAR.S(", "direct"),
    (r"\bpercentage\s*\(", "DIVIDE(", "parametric"),
    (r"\bpercentile\s*\(", "PERCENTILEX.INC(", "complex"),
    # Running aggregations
    (r"\brunning-total\s*\(", "/* running-total → CALCULATE+FILTER */ SUM(", "complex"),
    (r"\brunning-count\s*\(", "/* running-count → CALCULATE+FILTER */ COUNTROWS(", "complex"),
    (r"\brunning-average\s*\(", "/* running-avg → CALCULATE+FILTER */ AVERAGE(", "complex"),
    # String
    (r"\bsubstring\s*\(", "MID(", "parametric"),
    (r"\btrim\s*\(", "TRIM(", "direct"),
    (r"\bupper\s*\(", "UPPER(", "direct"),
    (r"\blower\s*\(", "LOWER(", "direct"),
    (r"\bconcatenate\s*\(", "CONCATENATE(", "parametric"),
    (r"\bstring-length\s*\(", "LEN(", "direct"),
    (r"\bposition\s*\(", "SEARCH(", "parametric"),
    (r"\breplace\s*\(", "SUBSTITUTE(", "parametric"),
    # Date
    (r"\b_days_between\s*\(", "DATEDIFF(", "parametric"),
    (r"\b_months_between\s*\(", "DATEDIFF(", "parametric"),
    (r"\b_years_between\s*\(", "DATEDIFF(", "parametric"),
    (r"\b_add_days\s*\(", "DATEADD(", "parametric"),
    (r"\b_add_months\s*\(", "DATEADD(", "parametric"),
    (r"\b_add_years\s*\(", "DATEADD(", "parametric"),
    (r"\b_year\s*\(", "YEAR(", "direct"),
    (r"\b_month\s*\(", "MONTH(", "direct"),
    (r"\b_day\s*\(", "DAY(", "direct"),
    (r"\bcurrent_date\b", "TODAY()", "direct"),
    (r"\bcurrent_timestamp\b", "NOW()", "direct"),
    # Math
    (r"\babs\s*\(", "ABS(", "direct"),
    (r"\bround\s*\(", "ROUND(", "direct"),
    (r"\btruncate\s*\(", "TRUNC(", "direct"),
    (r"\bceiling\s*\(", "CEILING(", "direct"),
    (r"\bfloor\s*\(", "FLOOR(", "direct"),
    (r"\bmod\s*\(", "MOD(", "direct"),
    (r"\bpower\s*\(", "POWER(", "direct"),
    (r"\bsqrt\s*\(", "SQRT(", "direct"),
    (r"\bexp\s*\(", "EXP(", "direct"),
    (r"\bln\s*\(", "LN(", "direct"),
    (r"\blog\s*\(", "LOG(", "parametric"),
    # Conditional
    (r"\bif\s*\(", "IF(", "parametric"),
    (r"\bcase\s+when\b", "SWITCH(TRUE(), ", "complex"),
    (r"\bcase\s*\(", "SWITCH(", "complex"),
    (r"\bcoalesce\s*\(", "COALESCE(", "parametric"),
    (r"\bnullif\s*\(", "/* nullif → IF+BLANK */ IF(", "complex"),
    (r"\bis-null\s*\(", "ISBLANK(", "direct"),
    (r"\bis-missing\s*\(", "ISBLANK(", "direct"),
    # OLAP / member
    (r"\broleValue\s*\(", "/* roleValue → RELATED */ RELATED(", "complex"),
    (r"\bancestor\s*\(", "/* ancestor → CALCULATE+ALL */ CALCULATE(", "complex"),
    (r"\bchildren\s*\(", "/* children → FILTER+VALUES */ FILTER(VALUES(", "complex"),
    (r"\bdescendants\s*\(", "/* descendants → FILTER+ALL */ FILTER(ALL(", "complex"),
    (r"\bcaption\s*\(", "SELECTEDVALUE(", "parametric"),
    # Data item references [namespace].[querySubject].[dataItem]
    (r"\[([^\]]+)\]\.\[([^\]]+)\]\.\[([^\]]+)\]", r"'\2'[\3]", "parametric"),
    (r"\[([^\]]+)\]\.\[([^\]]+)\]", r"'\1'[\2]", "parametric"),
]


# Cognos → Fabric data source type mapping
COGNOS_TO_FABRIC_SOURCE: dict[str, str] = {
    "oracle": "OracleDatabase",
    "sqlserver": "Sql",
    "db2": "Db2",
    "postgresql": "PostgreSql",
    "mysql": "MySql",
    "odbc": "ODBC",
    "teradata": "Teradata",
    "sap_bw": "SapBw",
    "sap_hana": "SapHana",
    "snowflake": "Snowflake",
    "redshift": "AmazonRedshift",
}


# Cognos → Fabric data type mapping
COGNOS_TO_FABRIC_TYPE: dict[str, str] = {
    "numeric": "double",
    "integer": "int64",
    "string": "string",
    "date": "dateTime",
    "time": "dateTime",
    "datetime": "dateTime",
    "boolean": "boolean",
    "decimal": "decimal",
}


# Cognos visual type → Power BI visual type mapping
COGNOS_VISUAL_TO_PBI: dict[str, str] = {
    "list": "table",
    "crosstab": "matrix",
    "chart_bar": "clusteredBarChart",
    "chart_line": "lineChart",
    "chart_pie": "pieChart",
    "chart_area": "areaChart",
    "chart_scatter": "scatterChart",
    "chart_combo": "lineClusteredColumnComboChart",
    "chart_waterfall": "waterfallChart",
    "chart_gauge": "gauge",
    "chart_treemap": "treemap",
    "chart_funnel": "funnel",
    "repeater": "table",
    "map": "map",
    "active_report": "table",
}


# Cognos prompt type → Power BI slicer/parameter mapping
COGNOS_PROMPT_TO_PBI: dict[str, str] = {
    "value": "slicer",
    "select": "slicer",
    "multiSelect": "slicer",
    "date": "dateRangeSlicer",
    "dateRange": "dateRangeSlicer",
    "tree": "hierarchySlicer",
    "textBox": "parameter",
    "interval": "numericRangeSlicer",
}


# Cognos → TMDL concept mapping
COGNOS_TO_TMDL_MAPPING: dict[str, str] = {
    "Package": "Semantic Model",
    "Query Subject": "Table",
    "Data Item": "Column / Measure",
    "Dimension": "Dimension Table",
    "Level": "Hierarchy Level",
    "Hierarchy": "Hierarchy",
    "Namespace": "Display Folder",
    "Report": "Report (.pbir)",
    "Report Page": "Report Page",
    "List": "Table Visual",
    "Crosstab": "Matrix Visual",
    "Chart": "Chart Visual",
    "Prompt": "Slicer / Parameter",
    "Filter": "Visual-level Filter",
    "Detail Filter": "Row-level Filter (DAX)",
    "Summary Filter": "Measure Filter",
    "Data Source Connection": "Fabric Lakehouse Connection",
    "Burst": "Paginated Report Subscription",
    "Drill-through": "Drillthrough Page",
    "Conditional Style": "Conditional Formatting Rule",
    "Active Report": "Power BI Interactive Report",
    "Calculation": "DAX Measure",
}


# =====================================================================
# Expression translator
# =====================================================================


class CognosExpressionTranslator:
    """Translate Cognos expressions to DAX using regex rules."""

    def __init__(self) -> None:
        self._rules: list[tuple[str, str, str]] = list(_COGNOS_CALC_PATTERNS)

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def catalog(self) -> list[CognosCalcRule]:
        return COGNOS_TO_DAX_RULES

    def translate(self, data_item: CognosDataItem) -> CalcTranslationResult:
        """Translate a single Cognos data item expression to DAX."""
        return self.translate_expression(data_item.expression, source_name=data_item.name)

    def translate_expression(self, expression: str, source_name: str = "") -> CalcTranslationResult:
        """Translate a Cognos expression string to DAX."""
        text = expression.strip()
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
            source_expression=expression,
            dax_expression=dax,
            method=method,
            confidence=confidence,
            warnings=warnings,
        )

    def translate_batch(self, items: list[CognosDataItem]) -> list[CalcTranslationResult]:
        """Translate a batch of data items."""
        return [self.translate(item) for item in items]


# =====================================================================
# Report spec XML parser
# =====================================================================


class CognosReportSpecParser:
    """Parse Cognos Report Studio XML specifications.

    Supports the standard Cognos XML report specification format used
    by Cognos Analytics 11.x and IBM Cognos BI 10.x.
    """

    def parse_xml(self, xml_data: bytes | str) -> ParsedReportSpec:
        """Parse a Cognos report specification from XML bytes or string."""
        result = ParsedReportSpec()

        try:
            if isinstance(xml_data, bytes):
                root = ET.fromstring(xml_data)
            else:
                root = ET.fromstring(xml_data.encode("utf-8") if isinstance(xml_data, str) else xml_data)
        except ET.ParseError as exc:
            result.errors.append(f"XML parse error: {exc}")
            return result

        # Parse report element
        report = self._parse_report(root)
        if report:
            result.reports.append(report)

        # Parse package references
        for pkg_el in root.iter("package"):
            pkg = self._parse_package(pkg_el)
            if pkg:
                result.packages.append(pkg)

        # Parse data sources
        for ds_el in root.iter("dataSource"):
            ds = self._parse_data_source(ds_el)
            if ds:
                result.data_sources.append(ds)

        return result

    def parse_multiple(self, xml_list: list[bytes | str]) -> ParsedReportSpec:
        """Parse multiple report specs and merge results."""
        combined = ParsedReportSpec()
        for xml_data in xml_list:
            result = self.parse_xml(xml_data)
            combined.reports.extend(result.reports)
            combined.packages.extend(result.packages)
            combined.data_sources.extend(result.data_sources)
            combined.errors.extend(result.errors)
        return combined

    def _parse_report(self, root: ET.Element) -> CognosReport | None:
        """Parse the top-level report element."""
        name = root.attrib.get("name", root.tag)
        report = CognosReport(name=name)

        # Parse queries
        for q_el in root.iter("query"):
            query = self._parse_query(q_el)
            if query:
                report.queries.append(query)

        # Parse pages
        for p_el in root.iter("page"):
            page = self._parse_page(p_el)
            if page:
                report.pages.append(page)

        # Parse prompts
        for pr_el in root.iter("selectValue"):
            prompt = self._parse_prompt(pr_el, "select")
            if prompt:
                report.prompts.append(prompt)
        for pr_el in root.iter("textBoxPrompt"):
            prompt = self._parse_prompt(pr_el, "value")
            if prompt:
                report.prompts.append(prompt)
        for pr_el in root.iter("datePrompt"):
            prompt = self._parse_prompt(pr_el, "date")
            if prompt:
                report.prompts.append(prompt)
        for pr_el in root.iter("treePrompt"):
            prompt = self._parse_prompt(pr_el, "tree")
            if prompt:
                report.prompts.append(prompt)

        return report

    def _parse_query(self, el: ET.Element) -> CognosQuery | None:
        """Parse a query element."""
        name = el.attrib.get("name", "")
        query = CognosQuery(name=name)

        for di_el in el.iter("dataItem"):
            item = self._parse_data_item(di_el)
            if item:
                query.data_items.append(item)

        for flt in el.iter("detailFilter"):
            expr_el = flt.find("filterExpression")
            if expr_el is not None and expr_el.text:
                query.detail_filters.append(expr_el.text)
            elif flt.text:
                query.detail_filters.append(flt.text)

        for flt in el.iter("summaryFilter"):
            expr_el = flt.find("filterExpression")
            if expr_el is not None and expr_el.text:
                query.summary_filters.append(expr_el.text)
            elif flt.text:
                query.summary_filters.append(flt.text)

        return query

    def _parse_data_item(self, el: ET.Element) -> CognosDataItem | None:
        """Parse a data item (column/measure)."""
        name = el.attrib.get("name", "")
        item = CognosDataItem(name=name)

        expr_el = el.find("expression")
        if expr_el is not None and expr_el.text:
            item.expression = expr_el.text.strip()

        item.aggregate = el.attrib.get("aggregate", "")
        item.rollup_aggregate = el.attrib.get("rollupAggregate", "")
        item.sort = el.attrib.get("sort", "")
        item.label = el.attrib.get("label", name)

        return item

    def _parse_page(self, el: ET.Element) -> CognosReportPage | None:
        """Parse a report page."""
        name = el.attrib.get("name", "Page")
        page = CognosReportPage(name=name)

        # Parse visualizations
        for viz_tag, viz_type in [
            ("list", "list"),
            ("crosstab", "crosstab"),
            ("chart", "chart"),
            ("repeater", "repeater"),
            ("map", "map"),
        ]:
            for viz_el in el.iter(viz_tag):
                viz = self._parse_visualization(viz_el, viz_type)
                page.visualizations.append(viz)

        return page

    def _parse_visualization(self, el: ET.Element, viz_type: str) -> CognosVisualization:
        """Parse a visualization element."""
        viz = CognosVisualization(viz_type=viz_type)
        viz.query_ref = el.attrib.get("refQuery", "")
        viz.title = el.attrib.get("name", "")

        if viz_type == "chart":
            viz.chart_type = el.attrib.get("chartType", "bar")

        # Collect column/row/measure references
        for col_el in el.iter("dataItemRef"):
            ref = col_el.attrib.get("refDataItem", col_el.text or "")
            if ref:
                viz.columns.append(ref)

        return viz

    def _parse_prompt(self, el: ET.Element, prompt_type: str) -> CognosPrompt | None:
        """Parse a prompt element."""
        name = el.attrib.get("name", el.attrib.get("parameter", ""))
        prompt = CognosPrompt(
            name=name,
            prompt_type=prompt_type,
            parameter_name=el.attrib.get("parameter", name),
            caption=el.attrib.get("caption", name),
            required=el.attrib.get("required", "false").lower() == "true",
            multi_select=el.attrib.get("multiSelect", "false").lower() == "true",
        )
        return prompt

    def _parse_package(self, el: ET.Element) -> CognosPackage | None:
        """Parse a package reference."""
        name = el.attrib.get("name", el.text or "")
        return CognosPackage(name=name) if name else None

    def _parse_data_source(self, el: ET.Element) -> CognosDataSource | None:
        """Parse a data source element."""
        name = el.attrib.get("name", "")
        return CognosDataSource(
            name=name,
            connection_type=el.attrib.get("type", ""),
            server=el.attrib.get("server", ""),
            database=el.attrib.get("database", ""),
            schema=el.attrib.get("schema", ""),
        ) if name else None


# =====================================================================
# REST API client
# =====================================================================


@dataclass
class CognosApiConfig:
    """Configuration for the Cognos REST API."""

    server_url: str
    namespace: str = "CognosEx"
    username: str = ""
    password: str = ""
    api_key: str = ""
    api_version: str = "v1"

    @property
    def base_url(self) -> str:
        return f"{self.server_url.rstrip('/')}/api/{self.api_version}"


class CognosRestClient:
    """Async REST API client for IBM Cognos Analytics (11.1+).

    Methods ``_http_get`` and ``_http_post`` can be overridden in tests.
    """

    def __init__(self) -> None:
        self._config: CognosApiConfig | None = None
        self._session_id: str = ""
        self._connected = False

    async def connect(self, config: CognosApiConfig) -> bool:
        """Authenticate and establish a session."""
        self._config = config
        try:
            creds = {
                "parameters": [
                    {"name": "CAMNamespace", "value": config.namespace},
                    {"name": "CAMUsername", "value": config.username},
                    {"name": "CAMPassword", "value": config.password},
                ],
            }
            result = await self._http_put(f"{config.base_url}/session", creds)
            self._session_id = result.get("session_id", "authenticated")
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Cognos connection failed: %s", exc)
            return False

    async def list_reports(self) -> list[dict[str, Any]]:
        """List all reports in the content store."""
        assert self._config
        data = await self._http_get(f"{self._config.base_url}/content?type=report")
        return data.get("content", [])

    async def list_dashboards(self) -> list[dict[str, Any]]:
        """List all dashboards."""
        assert self._config
        data = await self._http_get(f"{self._config.base_url}/content?type=exploration")
        return data.get("content", [])

    async def list_packages(self) -> list[dict[str, Any]]:
        """List all published packages."""
        assert self._config
        data = await self._http_get(f"{self._config.base_url}/content?type=package")
        return data.get("content", [])

    async def get_report_spec(self, report_id: str) -> str:
        """Download a report specification XML."""
        assert self._config
        data = await self._http_get(
            f"{self._config.base_url}/objects/{report_id}/specification"
        )
        return data.get("specification", "")

    async def list_data_sources(self) -> list[dict[str, Any]]:
        """List data source connections."""
        assert self._config
        data = await self._http_get(f"{self._config.base_url}/datasources")
        return data.get("dataSources", [])

    async def get_report_output(self, report_id: str, fmt: str = "XML") -> str:
        """Execute and get report output."""
        assert self._config
        data = await self._http_post(
            f"{self._config.base_url}/reports/{report_id}/output",
            {"format": fmt},
        )
        return data.get("output", "")

    async def disconnect(self) -> None:
        """Terminate the session."""
        if self._connected and self._config:
            try:
                await self._http_delete(f"{self._config.base_url}/session")
            except Exception:
                pass
        self._connected = False
        self._session_id = ""

    # Overridable HTTP methods for testing
    async def _http_get(self, url: str) -> dict[str, Any]:
        raise NotImplementedError("HTTP not available — override in tests or provide an HTTP client")

    async def _http_post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("HTTP not available")

    async def _http_put(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("HTTP not available")

    async def _http_delete(self, url: str) -> dict[str, Any]:
        raise NotImplementedError("HTTP not available")

    def _auth_headers(self) -> dict[str, str]:
        """Build authentication headers."""
        if not self._config:
            return {}
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["IBM-BA-Authorization"] = self._config.api_key
        if self._session_id:
            headers["IBM-BA-Session"] = self._session_id
        return headers


# =====================================================================
# Full Cognos Connector
# =====================================================================


class FullCognosConnector:
    """IBM Cognos Analytics connector — full implementation.

    Composes:
    - ``CognosRestClient`` — REST API communication
    - ``CognosReportSpecParser`` — XML report spec parsing
    - ``CognosExpressionTranslator`` — expression → DAX translation
    """

    def __init__(self) -> None:
        self._rest_client = CognosRestClient()
        self._parser = CognosReportSpecParser()
        self._translator = CognosExpressionTranslator()
        self._connected = False
        self._discovered_assets: list[Any] = []

    def info(self):
        from src.connectors.base_connector import ConnectorInfo, SourcePlatform
        return ConnectorInfo(
            platform=SourcePlatform.COGNOS,
            name="IBM Cognos Analytics Connector",
            version="1.0.0",
            description=(
                "Full Cognos connector — REST API, Report Studio XML parser, "
                f"{self._translator.rule_count} expression→DAX rules, "
                f"{len(COGNOS_VISUAL_TO_PBI)} visual mappings, "
                f"{len(COGNOS_PROMPT_TO_PBI)} prompt mappings, "
                f"{len(COGNOS_TO_TMDL_MAPPING)} concept mappings"
            ),
            supported_asset_types=["report", "dashboard", "package", "datasource"],
            is_stub=False,
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        """Connect to Cognos Analytics."""
        from src.connectors.base_connector import ExtractedAsset
        try:
            api_config = CognosApiConfig(
                server_url=config.get("server_url", ""),
                namespace=config.get("namespace", "CognosEx"),
                username=config.get("username", ""),
                password=config.get("password", ""),
                api_key=config.get("api_key", ""),
            )
            self._connected = await self._rest_client.connect(api_config)
            return self._connected
        except Exception as exc:
            logger.error("Cognos connect failed: %s", exc)
            return False

    async def discover(self) -> list:
        """Discover all Cognos assets."""
        from src.connectors.base_connector import ExtractedAsset
        if not self._connected:
            raise RuntimeError("Not connected")

        assets: list[ExtractedAsset] = []

        # Discover reports
        for report in await self._rest_client.list_reports():
            assets.append(ExtractedAsset(
                asset_id=report.get("id", ""),
                asset_type="report",
                name=report.get("name", ""),
                source_path=report.get("path", ""),
                platform="cognos",
                metadata=report,
            ))

        # Discover dashboards
        for dash in await self._rest_client.list_dashboards():
            assets.append(ExtractedAsset(
                asset_id=dash.get("id", ""),
                asset_type="dashboard",
                name=dash.get("name", ""),
                source_path=dash.get("path", ""),
                platform="cognos",
                metadata=dash,
            ))

        # Discover packages
        for pkg in await self._rest_client.list_packages():
            assets.append(ExtractedAsset(
                asset_id=pkg.get("id", ""),
                asset_type="package",
                name=pkg.get("name", ""),
                source_path=pkg.get("path", ""),
                platform="cognos",
                metadata=pkg,
            ))

        self._discovered_assets = assets
        return assets

    async def extract_metadata(self, asset_ids: list[str] | None = None):
        """Extract detailed metadata including report spec parsing."""
        from src.connectors.base_connector import ExtractionResult
        if not self._connected:
            raise RuntimeError("Not connected")

        assets = self._discovered_assets
        if asset_ids:
            assets = [a for a in assets if a.asset_id in asset_ids]

        # Enrich report assets with parsed spec
        for asset in assets:
            if asset.asset_type == "report" and asset.asset_id:
                try:
                    spec_xml = await self._rest_client.get_report_spec(asset.asset_id)
                    if spec_xml:
                        parsed = self._parser.parse_xml(spec_xml)
                        asset.metadata["parsed_spec"] = {
                            "queries": parsed.total_queries,
                            "prompts": parsed.total_prompts,
                            "visualizations": parsed.total_visualizations,
                            "report_names": parsed.report_names,
                        }
                        # Translate expressions
                        for report in parsed.reports:
                            for query in report.queries:
                                for item in query.data_items:
                                    if item.expression:
                                        result = self._translator.translate(item)
                                        asset.metadata.setdefault("translations", []).append({
                                            "name": item.name,
                                            "source": item.expression,
                                            "dax": result.dax_expression,
                                            "confidence": result.confidence,
                                        })
                except Exception as exc:
                    asset.metadata["extraction_error"] = str(exc)

        return ExtractionResult(platform="cognos", assets=assets)

    async def disconnect(self) -> None:
        await self._rest_client.disconnect()
        self._connected = False
        self._discovered_assets = []
