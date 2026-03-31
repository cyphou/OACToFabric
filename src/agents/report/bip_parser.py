"""BIP Parser — Oracle BI Publisher report definition parser.

Extracts data model (SQL queries, parameters) and layout structure
(header/detail/footer/groups) from BI Publisher XML data models and
RTF/XSL-FO templates.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ..discovery.safe_xml import safe_parse_xml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class BIPParameter:
    """A BI Publisher report parameter."""

    name: str
    data_type: str = "string"
    default_value: str = ""
    prompt: str = ""
    required: bool = False
    lov_query: str = ""


@dataclass
class BIPDataSet:
    """A BI Publisher data set (SQL query or data source)."""

    name: str
    sql_query: str = ""
    data_source: str = ""
    parameters: list[BIPParameter] = field(default_factory=list)


@dataclass
class BIPLayoutRegion:
    """A layout region (header, detail, footer, group)."""

    region_type: str  # header, detail, footer, group, chart, crosstab
    fields: list[str] = field(default_factory=list)
    group_by: str | None = None
    sort_by: str | None = None
    label: str = ""


@dataclass
class BIPReportDefinition:
    """Complete BI Publisher report definition."""

    name: str
    description: str = ""
    data_sets: list[BIPDataSet] = field(default_factory=list)
    parameters: list[BIPParameter] = field(default_factory=list)
    layout_regions: list[BIPLayoutRegion] = field(default_factory=list)
    page_orientation: str = "portrait"
    page_width: str = "8.5in"
    page_height: str = "11in"
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# XML data model parser
# ---------------------------------------------------------------------------

_RE_PARAM = re.compile(r":(\w+)", re.IGNORECASE)


def parse_bip_data_model(xml_text: str) -> list[BIPDataSet]:
    """Parse a BI Publisher XML data model.

    Parameters
    ----------
    xml_text : str
        BI Publisher data model XML.

    Returns
    -------
    list[BIPDataSet]
        Extracted data sets with SQL and parameters.
    """
    try:
        root = safe_parse_xml(xml_text)
    except Exception:
        logger.warning("Failed to parse BIP data model XML")
        return []

    datasets: list[BIPDataSet] = []

    for ds_elem in root.iter():
        tag = ds_elem.tag.lower() if isinstance(ds_elem.tag, str) else ""
        if "dataset" not in tag and "dataquery" not in tag:
            continue

        name = ds_elem.get("name", ds_elem.get("id", f"DataSet_{len(datasets)}"))
        sql = ""
        params: list[BIPParameter] = []

        for child in ds_elem:
            child_tag = child.tag.lower() if isinstance(child.tag, str) else ""
            if "sql" in child_tag or "query" in child_tag:
                sql = (child.text or "").strip()
            elif "parameter" in child_tag:
                params.append(BIPParameter(
                    name=child.get("name", ""),
                    data_type=child.get("dataType", "string"),
                    default_value=child.get("defaultValue", ""),
                ))

        if not params and sql:
            for m in _RE_PARAM.finditer(sql):
                params.append(BIPParameter(name=m.group(1)))

        if sql or params:
            datasets.append(BIPDataSet(name=name, sql_query=sql, parameters=params))

    logger.info("Parsed %d BI Publisher data sets", len(datasets))
    return datasets


# ---------------------------------------------------------------------------
# RTF template parser (simplified)
# ---------------------------------------------------------------------------

_RE_FIELD = re.compile(r"\{(\w+(?:\.\w+)*)\}")
_RE_GROUP = re.compile(r"<\?for-each:\s*(\w+)\?>", re.IGNORECASE)
_RE_SORT = re.compile(r"<\?sort:\s*(\w+)\?>", re.IGNORECASE)


def parse_bip_rtf_template(rtf_text: str) -> list[BIPLayoutRegion]:
    """Parse a BI Publisher RTF template for layout regions.

    Parameters
    ----------
    rtf_text : str
        RTF template text content.

    Returns
    -------
    list[BIPLayoutRegion]
        Extracted layout regions with fields and grouping.
    """
    regions: list[BIPLayoutRegion] = []
    current_fields: list[str] = []
    current_group: str | None = None
    current_sort: str | None = None

    for field_match in _RE_FIELD.finditer(rtf_text):
        current_fields.append(field_match.group(1))

    for group_match in _RE_GROUP.finditer(rtf_text):
        current_group = group_match.group(1)

    for sort_match in _RE_SORT.finditer(rtf_text):
        current_sort = sort_match.group(1)

    if current_fields:
        region_type = "group" if current_group else "detail"
        regions.append(BIPLayoutRegion(
            region_type=region_type,
            fields=current_fields,
            group_by=current_group,
            sort_by=current_sort,
        ))

    if not regions:
        regions.append(BIPLayoutRegion(region_type="detail", fields=["(no fields detected)"]))

    logger.info("Parsed %d RTF layout regions with %d fields", len(regions), len(current_fields))
    return regions


# ---------------------------------------------------------------------------
# Full report parser
# ---------------------------------------------------------------------------


def parse_bip_report(
    name: str,
    data_model_xml: str | None = None,
    rtf_template: str | None = None,
    description: str = "",
) -> BIPReportDefinition:
    """Parse a complete BI Publisher report from data model + template.

    Parameters
    ----------
    name : str
        Report name.
    data_model_xml : str | None
        XML data model content.
    rtf_template : str | None
        RTF template content.
    description : str
        Report description.

    Returns
    -------
    BIPReportDefinition
        Complete parsed report definition.
    """
    datasets: list[BIPDataSet] = []
    regions: list[BIPLayoutRegion] = []
    params: list[BIPParameter] = []
    warnings: list[str] = []

    if data_model_xml:
        datasets = parse_bip_data_model(data_model_xml)
        for ds in datasets:
            params.extend(ds.parameters)
    else:
        warnings.append("No data model XML provided — report will have no data source")

    if rtf_template:
        regions = parse_bip_rtf_template(rtf_template)
    else:
        warnings.append("No RTF template provided — using default detail layout")
        regions = [BIPLayoutRegion(region_type="detail")]

    return BIPReportDefinition(
        name=name,
        description=description,
        data_sets=datasets,
        parameters=params,
        layout_regions=regions,
        warnings=warnings,
    )
