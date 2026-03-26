"""Auto Calendar / Date table generation for TMDL.

Ported from T2P — auto-detects date columns and generates a Calendar
table with 8 columns, hierarchy, sortByColumn, M query partition,
and 3 time intelligence DAX measures (YTD, PY, YoY%).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


def _tag() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Date column detection
# ---------------------------------------------------------------------------

_DATE_TYPE_KEYWORDS = frozenset({
    "date", "datetime", "timestamp", "dateTime",
})

_DATE_NAME_KEYWORDS = frozenset({
    "date", "dt", "created", "modified", "updated", "order_date",
    "ship_date", "due_date", "start_date", "end_date", "hire_date",
    "birth_date", "close_date", "effective_date", "transaction_date",
})


def detect_date_columns(tables: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Detect date columns across all tables.

    Returns a list of dicts with 'table' and 'column' keys for each
    date column found.
    """
    results: list[dict[str, str]] = []

    for table in tables:
        table_name = table.get("name", "")
        for col in table.get("columns", []):
            col_name = col.get("name", "")
            data_type = col.get("data_type", "").lower()

            is_date_type = any(kw in data_type for kw in _DATE_TYPE_KEYWORDS)
            is_date_name = col_name.lower().replace("_", "").replace(" ", "") in _DATE_NAME_KEYWORDS

            if is_date_type or is_date_name:
                results.append({"table": table_name, "column": col_name})

    logger.info("Detected %d date columns across %d tables", len(results), len(tables))
    return results


# ---------------------------------------------------------------------------
# Calendar table TMDL generation
# ---------------------------------------------------------------------------

_CALENDAR_COLUMNS = [
    ("Date", "dateTime", "yyyy-MM-dd"),
    ("Year", "int64", "0"),
    ("Quarter", "int64", "0"),
    ("Month", "int64", "0"),
    ("MonthName", "string", ""),
    ("Day", "int64", "0"),
    ("DayOfWeek", "int64", "0"),
    ("DayName", "string", ""),
]

_SORT_BY_COLUMN = {
    "MonthName": "Month",
    "DayName": "DayOfWeek",
}

_CALENDAR_M_QUERY = '''let
    StartDate = Date.StartOfYear(List.Min({{min_date_expr}})),
    EndDate = Date.EndOfYear(List.Max({{max_date_expr}})),
    DateList = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1,0,0,0)),
    #"Convert to Table" = Table.FromList(DateList, Splitter.SplitByNothing(), {{"Date"}}),
    #"Changed Type" = Table.TransformColumnTypes(#"Convert to Table", {{"Date", type date}}),
    #"Added Year" = Table.AddColumn(#"Changed Type", "Year", each Date.Year([Date]), Int64.Type),
    #"Added Quarter" = Table.AddColumn(#"Added Year", "Quarter", each Date.QuarterOfYear([Date]), Int64.Type),
    #"Added Month" = Table.AddColumn(#"Added Quarter", "Month", each Date.Month([Date]), Int64.Type),
    #"Added MonthName" = Table.AddColumn(#"Added Month", "MonthName", each Date.MonthName([Date]), type text),
    #"Added Day" = Table.AddColumn(#"Added MonthName", "Day", each Date.Day([Date]), Int64.Type),
    #"Added DayOfWeek" = Table.AddColumn(#"Added Day", "DayOfWeek", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type),
    #"Added DayName" = Table.AddColumn(#"Added DayOfWeek", "DayName", each Date.DayOfWeekName([Date]), type text)
in
    #"Added DayName"'''


def generate_calendar_table_tmdl(
    date_column_refs: list[dict[str, str]] | None = None,
    table_name: str = "Calendar",
) -> str:
    """Generate the TMDL content for an auto-generated Calendar table.

    Parameters
    ----------
    date_column_refs
        List of date columns detected (used for M query date range).
    table_name
        Name for the calendar table.

    Returns
    -------
    str
        TMDL file content for the Calendar table.
    """
    lines = [f"table '{table_name}'"]
    lines.append(f"    lineageTag: {_tag()}")
    lines.append("    description: Auto-generated Calendar table for time intelligence")
    lines.append("    isHidden")
    lines.append("")

    # Partition (M query)
    if date_column_refs:
        first_ref = date_column_refs[0]
        min_expr = f"'{first_ref['table']}'[{first_ref['column']}]"
        max_expr = min_expr
    else:
        min_expr = "#date(2020, 1, 1)"
        max_expr = "#date(2030, 12, 31)"

    m_query = _CALENDAR_M_QUERY.replace("{{min_date_expr}}", min_expr)
    m_query = m_query.replace("{{max_date_expr}}", max_expr)

    lines.append(f"    partition '{table_name}' = m")
    lines.append("        mode: import")
    lines.append("        source")
    for m_line in m_query.strip().splitlines():
        lines.append(f"            {m_line}")
    lines.append("")

    # Columns
    for col_name, col_type, fmt_str in _CALENDAR_COLUMNS:
        lines.append(f"    column {col_name}")
        lines.append(f"        dataType: {col_type}")
        lines.append(f"        lineageTag: {_tag()}")
        if fmt_str:
            lines.append(f"        formatString: {fmt_str}")
        lines.append(f"        sourceColumn: {col_name}")

        # sortByColumn
        if col_name in _SORT_BY_COLUMN:
            lines.append(f"        sortByColumn: {_SORT_BY_COLUMN[col_name]}")

        summarize = "none"
        if col_type == "int64" and col_name not in ("Year",):
            summarize = "none"
        lines.append(f"        summarizeBy: {summarize}")
        lines.append("")

    # Hierarchy (Year → Quarter → Month → Day)
    lines.append("    hierarchy 'Date Hierarchy'")
    lines.append(f"        lineageTag: {_tag()}")
    for level_name in ["Year", "Quarter", "Month", "Day"]:
        lines.append(f"        level {level_name}")
        lines.append(f"            lineageTag: {_tag()}")
        lines.append(f"            column: {level_name}")
    lines.append("")

    # Time Intelligence measures (YTD, PY, YoY%)
    measures = [
        (
            "YTD Sales",
            "TOTALYTD(SUM('Calendar'[Date]), 'Calendar'[Date])",
            "YTD aggregate — replace SUM('Calendar'[Date]) with your actual measure",
        ),
        (
            "PY Sales",
            "CALCULATE([YTD Sales], SAMEPERIODLASTYEAR('Calendar'[Date]))",
            "Prior Year — references YTD Sales measure",
        ),
        (
            "YoY %",
            'DIVIDE([YTD Sales] - [PY Sales], [PY Sales], BLANK())',
            "Year-over-Year percentage change",
        ),
    ]
    for m_name, m_dax, m_desc in measures:
        lines.append(f"    measure '{m_name}' = {m_dax}")
        lines.append(f"        lineageTag: {_tag()}")
        if "%" in m_name:
            lines.append("        formatString: 0.00%")
        else:
            lines.append(r"        formatString: \$#,0.00;(\$#,0.00);\$#,0.00")
        lines.append(f"        displayFolder: Time Intelligence")
        lines.append(f"        description: {m_desc}")
        lines.append("")

    return "\n".join(lines)


def should_generate_calendar(tables: list[dict[str, Any]]) -> bool:
    """Check if any date columns exist that warrant a Calendar table."""
    return bool(detect_date_columns(tables))
