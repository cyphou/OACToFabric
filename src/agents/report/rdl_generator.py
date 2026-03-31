"""RDL Generator — produce Report Definition Language XML for Paginated Reports.

Converts parsed BI Publisher report definitions to RDL XML compatible with
Power BI Paginated Reports (SSRS-based).

Output:
  - ``<Report>`` root with data sources, data sets, body, and page settings
  - Tablix, Matrix, Chart, and List regions
  - Parameter definitions with prompts and defaults
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from .bip_parser import (
    BIPDataSet,
    BIPLayoutRegion,
    BIPParameter,
    BIPReportDefinition,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RDL_NAMESPACE = "http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition"
_RD_NAMESPACE = "http://schemas.microsoft.com/SQLServer/reporting/reportdesigner"

_BIP_TO_RDL_TYPE: dict[str, str] = {
    "string": "String",
    "varchar": "String",
    "varchar2": "String",
    "char": "String",
    "number": "Float",
    "integer": "Integer",
    "int": "Integer",
    "float": "Float",
    "double": "Float",
    "decimal": "Float",
    "date": "DateTime",
    "datetime": "DateTime",
    "timestamp": "DateTime",
    "boolean": "Boolean",
}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class RDLGenerationResult:
    """Result of RDL generation."""

    report_name: str
    rdl_xml: str
    data_source_count: int = 0
    data_set_count: int = 0
    body_region_count: int = 0
    parameter_count: int = 0
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def _indent(elem: Element, level: int = 0) -> None:
    """Add indentation to XML tree for readability."""
    indent_str = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent_str + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent_str
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent_str
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent_str


def _add_text(parent: Element, tag: str, text: str) -> Element:
    """Add a child element with text content."""
    elem = SubElement(parent, tag)
    elem.text = text
    return elem


# ---------------------------------------------------------------------------
# Data source / data set generation
# ---------------------------------------------------------------------------


def _build_data_sources(parent: Element, datasets: list[BIPDataSet]) -> int:
    """Build <DataSources> from BIP data sets."""
    sources_seen: set[str] = set()
    ds_container = SubElement(parent, "DataSources")

    for ds in datasets:
        source_name = ds.data_source or "OracleSource"
        if source_name in sources_seen:
            continue
        sources_seen.add(source_name)

        ds_elem = SubElement(ds_container, "DataSource")
        ds_elem.set("Name", source_name)
        conn = SubElement(ds_elem, "ConnectionProperties")
        _add_text(conn, "DataProvider", "System.Data.OleDb")
        _add_text(conn, "ConnectString", f"<!-- Migrated from BIP source: {source_name} -->")

    return len(sources_seen)


def _build_data_sets(parent: Element, datasets: list[BIPDataSet]) -> int:
    """Build <DataSets> from BIP data sets."""
    sets_container = SubElement(parent, "DataSets")

    for ds in datasets:
        ds_elem = SubElement(sets_container, "DataSet")
        ds_elem.set("Name", ds.name)

        query_elem = SubElement(ds_elem, "Query")
        _add_text(query_elem, "DataSourceName", ds.data_source or "OracleSource")
        _add_text(query_elem, "CommandText", ds.sql_query)

        if ds.parameters:
            qp_container = SubElement(query_elem, "QueryParameters")
            for p in ds.parameters:
                qp = SubElement(qp_container, "QueryParameter")
                qp.set("Name", f"@{p.name}")
                _add_text(qp, "Value", f"=Parameters!{p.name}.Value")

    return len(datasets)


# ---------------------------------------------------------------------------
# Body / region generation
# ---------------------------------------------------------------------------


def _build_tablix(parent: Element, region: BIPLayoutRegion, ds_name: str) -> None:
    """Build a <Tablix> element for a detail or group region."""
    tablix = SubElement(parent, "Tablix")
    tablix.set("Name", f"Tablix_{id(region) & 0xFFFF:04X}")

    ds_ref = SubElement(tablix, "DataSetName")
    ds_ref.text = ds_name

    # Columns
    cols = SubElement(tablix, "TablixColumns")
    for fld in region.fields:
        col = SubElement(cols, "TablixColumn")
        _add_text(col, "Width", "1.5in")

    # Body
    body = SubElement(tablix, "TablixBody")
    row = SubElement(SubElement(body, "TablixRows"), "TablixRow")
    _add_text(row, "Height", "0.25in")
    cells = SubElement(row, "TablixCells")

    for fld in region.fields:
        cell = SubElement(cells, "TablixCell")
        contents = SubElement(cell, "CellContents")
        textbox = SubElement(contents, "Textbox")
        textbox.set("Name", f"txt_{fld.replace('.', '_')}")
        _add_text(textbox, "Value", f"=Fields!{fld}.Value")

    # Grouping
    if region.group_by:
        row_hier = SubElement(tablix, "TablixRowHierarchy")
        members = SubElement(row_hier, "TablixMembers")
        member = SubElement(members, "TablixMember")
        group = SubElement(member, "Group")
        group.set("Name", f"Group_{region.group_by}")
        group_expr = SubElement(SubElement(group, "GroupExpressions"), "GroupExpression")
        group_expr.text = f"=Fields!{region.group_by}.Value"

    # Sorting
    if region.sort_by:
        sort_exprs = SubElement(tablix, "SortExpressions")
        sort = SubElement(sort_exprs, "SortExpression")
        _add_text(sort, "Value", f"=Fields!{region.sort_by}.Value")
        _add_text(sort, "Direction", "Ascending")


def _build_body(parent: Element, regions: list[BIPLayoutRegion], ds_name: str) -> int:
    """Build the <Body> section from layout regions."""
    body = SubElement(parent, "Body")
    items = SubElement(body, "ReportItems")

    for region in regions:
        if region.region_type in ("detail", "group"):
            _build_tablix(items, region, ds_name)
        elif region.region_type == "chart":
            chart = SubElement(items, "Chart")
            chart.set("Name", f"Chart_{id(region) & 0xFFFF:04X}")
            _add_text(chart, "DataSetName", ds_name)
        elif region.region_type == "crosstab":
            _build_tablix(items, region, ds_name)

    _add_text(body, "Height", "6in")
    return len(regions)


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


def _build_parameters(parent: Element, params: list[BIPParameter]) -> int:
    """Build <ReportParameters> section."""
    if not params:
        return 0

    params_container = SubElement(parent, "ReportParameters")
    seen: set[str] = set()

    for p in params:
        if p.name in seen:
            continue
        seen.add(p.name)

        rp = SubElement(params_container, "ReportParameter")
        rp.set("Name", p.name)
        _add_text(rp, "DataType", _BIP_TO_RDL_TYPE.get(p.data_type.lower(), "String"))
        _add_text(rp, "Prompt", p.prompt or p.name)
        _add_text(rp, "Hidden", "false")

        if p.default_value:
            dv = SubElement(rp, "DefaultValue")
            vals = SubElement(dv, "Values")
            _add_text(vals, "Value", p.default_value)

    return len(seen)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_rdl(report_def: BIPReportDefinition) -> RDLGenerationResult:
    """Generate RDL XML from a parsed BI Publisher report definition.

    Parameters
    ----------
    report_def : BIPReportDefinition
        Parsed BI Publisher report.

    Returns
    -------
    RDLGenerationResult
        Generated RDL XML string and metadata.
    """
    root = Element("Report")
    root.set("xmlns", _RDL_NAMESPACE)
    root.set("xmlns:rd", _RD_NAMESPACE)

    warnings: list[str] = list(report_def.warnings)

    # Data sources & data sets
    ds_count = _build_data_sources(root, report_def.data_sets)
    dset_count = _build_data_sets(root, report_def.data_sets)

    # Parameters
    param_count = _build_parameters(root, report_def.parameters)

    # Body
    ds_name = report_def.data_sets[0].name if report_def.data_sets else "DataSet_0"
    body_count = _build_body(root, report_def.layout_regions, ds_name)

    # Page settings
    page = SubElement(root, "Page")
    _add_text(page, "PageWidth", report_def.page_width)
    _add_text(page, "PageHeight", report_def.page_height)
    _add_text(page, "LeftMargin", "0.5in")
    _add_text(page, "RightMargin", "0.5in")
    _add_text(page, "TopMargin", "0.5in")
    _add_text(page, "BottomMargin", "0.5in")

    _indent(root)
    xml_bytes = tostring(root, encoding="unicode", xml_declaration=True)

    logger.info(
        "Generated RDL for '%s': %d sources, %d datasets, %d params, %d regions",
        report_def.name,
        ds_count,
        dset_count,
        param_count,
        body_count,
    )

    return RDLGenerationResult(
        report_name=report_def.name,
        rdl_xml=xml_bytes,
        data_source_count=ds_count,
        data_set_count=dset_count,
        body_region_count=body_count,
        parameter_count=param_count,
        warnings=warnings,
    )
