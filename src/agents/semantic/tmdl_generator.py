"""TMDL generator — produce Tabular Model Definition Language files.

Generates the full TMDL folder structure for a Power BI Semantic Model
from the ``SemanticModelIR`` intermediate representation.

Output structure::

    SemanticModel/
    ├── .platform
    ├── definition.pbism
    └── definition/
        ├── database.tmdl
        ├── model.tmdl
        ├── tables/
        │   ├── Sales.tmdl
        │   ├── Products.tmdl
        │   └── Date.tmdl
        ├── relationships.tmdl
        ├── perspectives.tmdl
        ├── roles.tmdl
        └── expressions.tmdl
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .expression_translator import DAXTranslation, translate_expression
from .hierarchy_mapper import TMDLHierarchy, hierarchy_to_tmdl, map_all_hierarchies
from .rpd_model_parser import (
    CalculationGroup,
    CalculationItem,
    ColumnKind,
    CrossFilterBehaviour,
    JoinCardinality,
    LogicalColumn,
    LogicalJoin,
    LogicalTable,
    RefreshPolicy,
    SemanticModelIR,
    SubjectArea,
)
from .calendar_generator import detect_date_columns, generate_calendar_table_tmdl, should_generate_calendar
from .tmdl_self_healing import self_heal
from .dax_optimizer import optimize_dax
from .leak_detector import scan_dax_for_leaks, auto_fix_dax

import re as _re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lineage tag helper
# ---------------------------------------------------------------------------

def _tag() -> str:
    """Generate a random lineage tag (UUID)."""
    return str(uuid.uuid4())


def _quote_name(name: str) -> str:
    """Quote a TMDL name with single quotes if it contains special chars."""
    if not name:
        return "''"
    if _re.search(r"[^a-zA-Z0-9_]", name):
        return f"'{name}'"
    return name


def _safe_filename(name: str) -> str:
    """Create a safe filename for a table (strip chars invalid on Windows)."""
    return _re.sub(r'[<>:"/\\|?*]', '_', name)


# ---------------------------------------------------------------------------
# Data type mapping  (OAC/Oracle → TMDL)
# ---------------------------------------------------------------------------

_TMDL_TYPE_MAP: dict[str, str] = {
    "VARCHAR": "string",
    "VARCHAR2": "string",
    "CHAR": "string",
    "NVARCHAR": "string",
    "NVARCHAR2": "string",
    "CLOB": "string",
    "NCLOB": "string",
    "TEXT": "string",
    "STRING": "string",
    "NUMBER": "double",
    "NUMERIC": "double",
    "DECIMAL": "decimal",
    "FLOAT": "double",
    "DOUBLE": "double",
    "BINARY_FLOAT": "double",
    "BINARY_DOUBLE": "double",
    "INT": "int64",
    "INTEGER": "int64",
    "SMALLINT": "int64",
    "BIGINT": "int64",
    "TINYINT": "int64",
    "DATE": "dateTime",
    "TIMESTAMP": "dateTime",
    "DATETIME": "dateTime",
    "BOOLEAN": "boolean",
    "BOOL": "boolean",
    "BLOB": "binary",
    "RAW": "binary",
}


def _map_data_type(oracle_type: str) -> str:
    """Map an Oracle/OAC data type to a TMDL data type."""
    base = oracle_type.split("(")[0].strip().upper()
    return _TMDL_TYPE_MAP.get(base, "string")


# ---------------------------------------------------------------------------
# Format string heuristics
# ---------------------------------------------------------------------------


def _format_string(data_type: str, name: str) -> str:
    """Guess a DAX format string based on data type and column name."""
    name_l = name.lower()
    dt = data_type.lower()
    if dt in ("decimal", "double", "int64"):
        if any(kw in name_l for kw in ("amount", "revenue", "price", "cost", "total", "salary")):
            return r"\$#,0.00;(\$#,0.00);\$#,0.00"
        if any(kw in name_l for kw in ("percent", "pct", "ratio", "rate")):
            return "0.00%"
        if dt == "int64":
            return "0"
        return "#,0.00"
    if dt == "dateTime":
        return "yyyy-MM-dd"
    return ""


# ---------------------------------------------------------------------------
# Data category heuristic (for geographic auto-detection in PBI)
# ---------------------------------------------------------------------------

_DATA_CATEGORY_MAP: dict[str, str] = {
    "country": "Country",
    "country_name": "Country",
    "country_code": "Country",
    "state": "StateOrProvince",
    "state_province": "StateOrProvince",
    "province": "StateOrProvince",
    "region": "StateOrProvince",
    "city": "City",
    "city_name": "City",
    "postal_code": "PostalCode",
    "zip_code": "PostalCode",
    "zip": "PostalCode",
    "latitude": "Latitude",
    "lat": "Latitude",
    "longitude": "Longitude",
    "lon": "Longitude",
    "lng": "Longitude",
    "address": "Address",
    "continent": "Continent",
    "county": "County",
    "web_url": "WebUrl",
    "url": "WebUrl",
    "image_url": "ImageUrl",
}


def _data_category(name: str) -> str:
    """Infer PBI dataCategory from a column name (geographic, URL, etc.)."""
    return _DATA_CATEGORY_MAP.get(name.lower().strip(), "")


def _is_technical_column(name: str) -> bool:
    """Detect technical/ID columns that should be hidden from Copilot Q&A."""
    n = name.lower().strip()
    # Normalize separators: "Customer Key" → "customer_key"
    n_norm = _re.sub(r"[\s\-]+", "_", n)
    return (
        n_norm.endswith("_id") or n_norm.endswith("_key") or n_norm.endswith("_sk")
        or n_norm.startswith("sk_") or n_norm.startswith("fk_") or n_norm.startswith("pk_")
        or n_norm in ("id", "key", "rowkey", "row_id", "surrogate_key")
    )


# ---------------------------------------------------------------------------
# TMDL text rendering
# ---------------------------------------------------------------------------


def _render_column(col: LogicalColumn, tmdl_type: str) -> str:
    """Render a TMDL physical column definition."""
    name = _quote_name(col.name)
    lines = [f"\tcolumn {name}"]
    lines.append(f"\t\tdataType: {tmdl_type}")
    fmt = _format_string(tmdl_type, col.name)
    if fmt:
        lines.append(f"\t\tformatString: {fmt}")
    lines.append(f"\t\tlineageTag: {_tag()}")
    summarize = "sum" if tmdl_type in ("decimal", "double", "int64") else "none"
    lines.append(f"\t\tsummarizeBy: {summarize}")
    source_col = col.source_column or col.name
    lines.append(f"\t\tsourceColumn: {source_col}")
    cat = _data_category(col.name)
    if cat:
        lines.append(f"\t\tdataCategory: {cat}")
    if col.sort_by_column:
        lines.append(f"\t\tsortByColumn: {_quote_name(col.sort_by_column)}")
    if col.is_hidden:
        lines.append("\t\tisHidden")
    lines.append("")
    lines.append("\t\tannotation SummarizationSetBy = Automatic")
    if _is_technical_column(col.name):
        lines.append("\t\tannotation Copilot_Hidden = true")
    lines.append("")
    return "\n".join(lines)


def _render_calculated_column(col: LogicalColumn, dax: str) -> str:
    """Render a TMDL calculated column."""
    tmdl_type = _map_data_type(col.data_type) if col.data_type else "string"
    name = _quote_name(col.name)
    if "\n" in dax:
        lines = [f"\tcolumn {name} = ```"]
        for expr_line in dax.split("\n"):
            lines.append(f"\t\t\t{expr_line}")
        lines.append("\t\t\t```")
    else:
        lines = [f"\tcolumn {name} = {dax}"]
    lines.append(f"\t\tdataType: {tmdl_type}")
    lines.append(f"\t\tlineageTag: {_tag()}")
    lines.append(f"\t\tsummarizeBy: none")
    if col.is_hidden:
        lines.append("\t\tisHidden")
    lines.append("")
    return "\n".join(lines)


def _render_measure(col: LogicalColumn, dax: str, display_folder: str = "") -> str:
    """Render a TMDL measure definition."""
    name = _quote_name(col.name)
    if "\n" in dax:
        lines = [f"\tmeasure {name} = ```"]
        for expr_line in dax.split("\n"):
            lines.append(f"\t\t\t{expr_line}")
        lines.append("\t\t\t```")
    else:
        lines = [f"\tmeasure {name} = {dax}"]
    fmt = _format_string("double", col.name)
    if fmt:
        lines.append(f"\t\tformatString: {fmt}")
    folder = display_folder or col.display_folder or "Measures"
    lines.append(f"\t\tdisplayFolder: {folder}")
    if col.is_hidden:
        lines.append("\t\tisHidden")
    lines.append(f"\t\tlineageTag: {_tag()}")
    lines.append("")
    return "\n".join(lines)


def _render_partition(table: LogicalTable, lakehouse_name: str = "MyLakehouse") -> str:
    """Render a TMDL partition expression using M (Power Query)."""
    tbl_name = _re.sub(r"[^A-Za-z0-9_]", "", table.name.replace(" ", "_"))
    part_name = f"{table.name}-{uuid.uuid4()}"

    # Calculation group partitions have a special source type
    if table.calculation_group is not None:
        lines = [
            f"\tpartition {_quote_name(part_name)} = calculationGroup",
            "\t\tmode: import",
            "",
        ]
        return "\n".join(lines)

    lines = [
        f"\tpartition {_quote_name(part_name)} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        f'\t\t\t\t    Source = #table(type table [], {{}}),',
        f'\t\t\t\t    // TODO: Configure data source',
        f'\t\t\t\t    {tbl_name} = Source',
        "\t\t\t\tin",
        f"\t\t\t\t    {tbl_name}",
        "",
    ]
    return "\n".join(lines)


def _render_calculation_group(cg: CalculationGroup) -> str:
    """Render a TMDL calculation group block."""
    lines = ["\tcalculationGroup"]
    lines.append(f"\t\tprecedence: {cg.precedence}")
    lines.append("")
    for item in cg.items:
        item_name = _quote_name(item.name)
        lines.append(f"\t\tcalculationItem {item_name}")
        expr = item.expression
        if "\n" in expr:
            lines.append("\t\t\texpression = ```")
            for el in expr.split("\n"):
                lines.append(f"\t\t\t\t{el}")
            lines.append("\t\t\t\t```")
        else:
            lines.append(f"\t\t\texpression = {expr}")
        if item.ordinal is not None:
            lines.append(f"\t\t\tordinal: {item.ordinal}")
        lines.append("")
    return "\n".join(lines)


def _render_refresh_policy(policy: RefreshPolicy) -> str:
    """Render a TMDL incremental refresh policy block."""
    lines = ["\trefreshPolicy"]
    lines.append(f"\t\tincrementalGranularity: {policy.incremental_granularity}")
    lines.append(f"\t\tincrementalPeriods: {policy.incremental_periods}")
    lines.append(f"\t\trollingWindowGranularity: {policy.rolling_window_granularity}")
    lines.append(f"\t\trollingWindowPeriods: {policy.rolling_window_periods}")
    if policy.polling_expression:
        lines.append("\t\tpollingExpression =")
        for pl in policy.polling_expression.split("\n"):
            lines.append(f"\t\t\t{pl}")
    if policy.source_expression:
        lines.append("\t\tsourceExpression =")
        for sl in policy.source_expression.split("\n"):
            lines.append(f"\t\t\t{sl}")
    lines.append("")
    return "\n".join(lines)


def _detect_sort_by(columns: list[LogicalColumn]) -> dict[str, str]:
    """Auto-detect sortByColumn for common patterns.

    Returns dict of {column_name: sort_by_column_name}.
    Detects:
    - MonthName sorted by MonthNumber
    - DayOfWeek sorted by DayOfWeekNumber
    """
    col_names_lower = {c.name.lower(): c.name for c in columns}
    sort_map: dict[str, str] = {}
    patterns = [
        # (text column pattern, numeric sort column patterns)
        ("month_name", ["month_number", "month_num", "month_sort", "monthnum"]),
        ("month name", ["month number", "month num", "month sort"]),
        ("monthname", ["monthnumber", "monthnum", "monthsort"]),
        ("day_of_week", ["day_of_week_number", "dayofweeknum", "dow_num"]),
        ("day of week", ["day of week number"]),
        ("dayofweek", ["dayofweeknumber", "dayofweeknum"]),
        ("quarter_name", ["quarter_number", "quarternum"]),
        ("quarter name", ["quarter number"]),
    ]
    for text_col, sort_candidates in patterns:
        if text_col in col_names_lower:
            for sc in sort_candidates:
                if sc in col_names_lower:
                    sort_map[col_names_lower[text_col]] = col_names_lower[sc]
                    break
    return sort_map


# ---------------------------------------------------------------------------
# Display folder intelligence (Phase 49)
# ---------------------------------------------------------------------------


def _build_display_folder_map(ir: SemanticModelIR) -> dict[str, dict[str, str]]:
    """Build a mapping of table→column→display_folder from IR subject areas.

    Uses RPD subject area / presentation table grouping to infer
    display folders for measures and columns.

    Returns:
        Dict of {table_name: {column_name: folder_path}}
    """
    folder_map: dict[str, dict[str, str]] = {}

    # From subject areas — use the SA name as top-level folder
    for sa in ir.subject_areas:
        for tbl_name in sa.tables:
            cols = sa.columns.get(tbl_name, [])
            for col_name in cols:
                folder_map.setdefault(tbl_name, {})[col_name] = sa.name

    # From table descriptions that hint at grouping (e.g. "Finance > Revenue")
    for table in ir.tables:
        for col in table.measures + table.calculated_columns:
            if col.display_folder:
                folder_map.setdefault(table.name, {})[col.name] = col.display_folder

    return folder_map


# ---------------------------------------------------------------------------
# Table-level TMDL generator
# ---------------------------------------------------------------------------


def generate_table_tmdl(
    table: LogicalTable,
    hierarchies: list[TMDLHierarchy],
    translations: dict[str, DAXTranslation],
    lakehouse_name: str = "MyLakehouse",
    display_folder_map: dict[str, dict[str, str]] | None = None,
) -> str:
    """Generate the TMDL file content for a single table.

    Parameters
    ----------
    table : LogicalTable
        The logical table from the IR.
    hierarchies : list[TMDLHierarchy]
        Hierarchies belonging to this table.
    translations : dict[str, DAXTranslation]
        Column name → DAX translation for calculated columns / measures.
    lakehouse_name : str
        Fabric Lakehouse name for partition expressions.
    display_folder_map : dict
        Optional table→column→folder mapping for display folder intelligence.
    """
    tbl_folders = (display_folder_map or {}).get(table.name, {})
    tbl_name = _quote_name(table.name)
    lines = [f"table {tbl_name}"]
    lines.append(f"\tlineageTag: {_tag()}")
    lines.append("")

    # Calculation group block (must come before columns/measures)
    if table.calculation_group is not None:
        lines.append(_render_calculation_group(table.calculation_group))

    # Measures (before columns, matching PBI Desktop ordering)
    for col in table.measures:
        tx = translations.get(col.name)
        dax = tx.dax_expression if tx else col.expression
        folder = tx.display_folder if tx else tbl_folders.get(col.name, "")
        lines.append(_render_measure(col, dax, folder))

    # Auto-detect sortByColumn pairs
    sort_map = _detect_sort_by(table.direct_columns)

    # Direct columns
    for col in table.direct_columns:
        # Apply auto-detected sortByColumn if not already set
        if not col.sort_by_column and col.name in sort_map:
            col.sort_by_column = sort_map[col.name]
        tmdl_type = _map_data_type(col.data_type) if col.data_type else "string"
        lines.append(_render_column(col, tmdl_type))

    # Calculated columns — promote to measure if DAX uses session-only functions
    _SESSION_FUNCS_RE = _re.compile(
        r"\b(CUSTOMDATA|USERNAME|USERCULTURE|USERPRINCIPALNAME)\s*\(",
        _re.IGNORECASE,
    )
    for col in table.calculated_columns:
        tx = translations.get(col.name)
        dax = tx.dax_expression if tx else col.expression
        if _SESSION_FUNCS_RE.search(dax or ""):
            # These functions are forbidden in calculated columns;
            # emit as a measure instead.
            folder = tx.display_folder if tx else tbl_folders.get(col.name, "")
            lines.append(_render_measure(col, dax, folder))
        else:
            lines.append(_render_calculated_column(col, dax))

    # Hierarchies — deduplicate by name and validate levels against actual columns
    actual_col_names = {c.name for c in table.columns}
    seen_hierarchies: set[str] = set()
    for h in hierarchies:
        if h.name in seen_hierarchies:
            continue
        # Filter levels to only those with columns that exist in this table
        valid_levels = [lv for lv in h.levels if lv.column_name in actual_col_names]
        if len(valid_levels) < 2:
            continue
        h.levels = valid_levels
        seen_hierarchies.add(h.name)
        lines.append(hierarchy_to_tmdl(h))
        lines.append("")

    # Partition
    lines.append(_render_partition(table, lakehouse_name))

    # Incremental refresh policy
    if table.refresh_policy is not None:
        lines.append(_render_refresh_policy(table.refresh_policy))

    # Annotations
    lines.append("\tannotation PBI_ResultType = Table")
    if table.is_date_table:
        lines.append("\tannotation Copilot_DateTable = true")
    table_desc = table.description or f"Data from {table.name}"
    lines.append(f"\tannotation Copilot_TableDescription = {table_desc}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Relationship TMDL
# ---------------------------------------------------------------------------


def _cardinality_tmdl(card: JoinCardinality) -> tuple[str, str]:
    """Map JoinCardinality to TMDL fromCardinality/toCardinality."""
    mapping = {
        JoinCardinality.ONE_TO_ONE: ("one", "one"),
        JoinCardinality.ONE_TO_MANY: ("one", "many"),
        JoinCardinality.MANY_TO_ONE: ("many", "one"),
        JoinCardinality.MANY_TO_MANY: ("many", "many"),
    }
    return mapping.get(card, ("one", "many"))


def generate_relationships_tmdl(joins: list[LogicalJoin]) -> str:
    """Generate the relationships.tmdl file content."""
    lines: list[str] = []
    for i, j in enumerate(joins):
        from_card, to_card = _cardinality_tmdl(j.cardinality)
        rel_id = str(uuid.uuid4())

        from_table = _quote_name(j.from_table)
        from_col = _quote_name(j.from_column or "ID")
        to_table = _quote_name(j.to_table)
        to_col = _quote_name(j.to_column or "ID")

        lines.append(f"relationship {rel_id}")
        lines.append(f"\tfromColumn: {from_table}.{from_col}")
        lines.append(f"\ttoColumn: {to_table}.{to_col}")

        # Only emit cardinality for non-default (many-to-one is default)
        if from_card == "many" and to_card == "many":
            lines.append(f"\tfromCardinality: many")
            lines.append(f"\ttoCardinality: many")
        elif from_card == "one" and to_card == "one":
            lines.append(f"\tfromCardinality: one")
            lines.append(f"\ttoCardinality: one")

        # Cross-filter direction
        cf = "oneDirection"
        if j.join_type.lower() in ("full", "cross"):
            cf = "bothDirections"
        lines.append(f"\tcrossFilteringBehavior: {cf}")

        if not j.is_active:
            lines.append("\tisActive: false")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Perspectives TMDL (from Subject Areas)
# ---------------------------------------------------------------------------


def generate_perspectives_tmdl(
    subject_areas: list[SubjectArea],
    valid_tables: set[str] | None = None,
    valid_columns: dict[str, set[str]] | None = None,
    measure_names: dict[str, set[str]] | None = None,
) -> str:
    """Generate the perspectives.tmdl content.

    If valid_tables/valid_columns are provided, perspective entries
    referencing non-existent tables or columns are silently dropped.
    measure_names maps table_name -> set of measure names so we can
    emit ``perspectiveMeasure`` instead of ``perspectiveColumn``.
    """
    if not subject_areas:
        return ""
    measure_names = measure_names or {}
    lines: list[str] = []
    for sa in subject_areas:
        sa_lines: list[str] = []
        for tbl in sa.tables:
            # Skip tables not in the model
            if valid_tables is not None and tbl not in valid_tables:
                continue
            tbl_lines = [f"\tperspectiveTable {_quote_name(tbl)}"]
            cols = sa.columns.get(tbl, [])
            tbl_measures = measure_names.get(tbl, set())
            for col in cols:
                if valid_columns is not None:
                    tbl_cols = valid_columns.get(tbl, set())
                    if col not in tbl_cols:
                        continue
                if col in tbl_measures:
                    tbl_lines.append(f"\t\tperspectiveMeasure {_quote_name(col)}")
                else:
                    tbl_lines.append(f"\t\tperspectiveColumn {_quote_name(col)}")
            sa_lines.extend(tbl_lines)
        if sa_lines:
            lines.append(f"perspective {_quote_name(sa.name)}")
            lines.extend(sa_lines)
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model-level TMDL
# ---------------------------------------------------------------------------


def generate_model_tmdl(
    ir: SemanticModelIR,
    rls_roles: list[dict[str, Any]] | None = None,
    actual_perspectives: set[str] | None = None,
) -> str:
    """Generate the model.tmdl (model-level properties + ref entries).

    Parameters
    ----------
    actual_perspectives : set[str] | None
        If provided, only emit ``ref perspective`` entries for these names
        (i.e. perspectives that survived validation filtering).
    """
    has_calc_groups = any(t.calculation_group is not None for t in ir.tables)
    culture = ir.culture or "en-US"

    lines = [
        f"model Model",
        f"\tculture: {culture}",
        f"\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        f"\tsourceQueryCulture: en-US",
    ]
    if has_calc_groups:
        lines.append("\tdiscourageImplicitMeasures")
    lines.extend([
        f"\tdataAccessOptions",
        f"\t\tlegacyRedirects",
        f"\t\treturnErrorValuesAsNull",
    ])
    lines.append("")

    # PBI_QueryOrder annotation — controls table load order in PBI Desktop
    table_names_ordered: list[str] = []
    seen_order: set[str] = set()
    for table in ir.tables:
        if table.name not in seen_order and table.columns:
            seen_order.add(table.name)
            table_names_ordered.append(table.name)
    if table_names_ordered:
        names_json = '["' + '","'.join(table_names_ordered) + '"]'
        lines.append(f"annotation PBI_QueryOrder = {names_json}")
        lines.append("")

    # ref table entries (deduplicated, skip empty tables)
    seen_tables: set[str] = set()
    for table in ir.tables:
        if not table.columns:
            continue
        tname = _quote_name(table.name)
        if tname not in seen_tables:
            seen_tables.add(tname)
            lines.append(f"ref table {tname}")
    lines.append("")

    # ref relationships
    if ir.joins:
        for j in ir.joins:
            rel_name = f"rel_{j.from_table}_{j.to_table}".replace(" ", "_")
            lines.append(f"ref relationship {rel_name}")
        lines.append("")

    # ref expression (shared M data source parameters)
    lines.append("ref expression ServerName")
    lines.append("ref expression DatabaseName")
    lines.append("")

    # ref roles
    if rls_roles:
        for role in rls_roles:
            rname = role.get("role_name", "UnnamedRole") if isinstance(role, dict) else getattr(role, "role_name", "UnnamedRole")
            lines.append(f"ref role {_quote_name(rname)}")
        lines.append("")

    # ref perspectives (deduplicated, filtered to actual output)
    if ir.subject_areas:
        seen_perspectives: set[str] = set()
        for sa in ir.subject_areas:
            # Skip perspectives that were filtered out during generation
            if actual_perspectives is not None and sa.name not in actual_perspectives:
                continue
            pname = _quote_name(sa.name)
            if pname not in seen_perspectives:
                seen_perspectives.add(pname)
                lines.append(f"ref perspective {pname}")
        if seen_perspectives:
            lines.append("")

    # ref culture (non-default locales)
    for c in ir.cultures:
        if c != "en-US":
            lines.append(f"ref culture {_quote_name(c)}")
    if ir.cultures:
        lines.append("")

    content = "\n".join(lines) + "\n"
    return content


# ---------------------------------------------------------------------------
# Fabric .platform config
# ---------------------------------------------------------------------------


def generate_platform_json(model_name: str = "SemanticModel") -> str:
    """Generate the .platform config file."""
    config = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "SemanticModel",
            "displayName": model_name,
        },
        "config": {
            "version": "2.0",
            "logicalId": str(uuid.uuid4()),
        },
    }
    return json.dumps(config, indent=2)


def generate_definition_pbism() -> str:
    """Generate the definition.pbism file required by Power BI Desktop."""
    definition = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2",
        "settings": {
            "qnaEnabled": True,
        },
    }
    return json.dumps(definition, indent=2)


# ---------------------------------------------------------------------------
# database.tmdl
# ---------------------------------------------------------------------------


def _generate_database_tmdl(
    model_name: str = "SemanticModel",
    compatibility_level: int = 1604,
) -> str:
    """Generate the database.tmdl file with compatibility level and options."""
    lines = [
        "database",
        f"\tcompatibilityLevel: {compatibility_level}",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full TMDL generation pipeline
# ---------------------------------------------------------------------------


@dataclass
class TMDLGenerationResult:
    """Result of generating the full TMDL folder structure."""

    files: dict[str, str]               # relative_path → content
    translation_log: list[DAXTranslation]
    warnings: list[str]
    review_items: list[dict[str, Any]]
    table_count: int = 0
    measure_count: int = 0
    relationship_count: int = 0
    hierarchy_count: int = 0


def generate_roles_tmdl(
    rls_roles: list[dict[str, Any]] | None = None,
) -> str:
    """Generate the roles.tmdl content from RLS role definitions.

    Parameters
    ----------
    rls_roles
        List of role definitions.  Accepts either dicts with
        ``role_name``, ``description``, ``table_permissions`` keys,
        or dataclass / object instances with matching attributes.
        Typically produced by Agent 06 (Security Agent).
    """
    if not rls_roles:
        return ""

    def _get(obj: Any, key: str, default: Any = "") -> Any:
        """Get attribute from dict or object."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    lines: list[str] = []
    for role in rls_roles:
        name = _get(role, "role_name", "UnnamedRole")
        desc = _get(role, "description", "")
        lines.append(f"role '{name}'")
        lines.append(f"\tmodelPermission: read")
        lines.append(f"\tlineageTag: {_tag()}")
        if desc:
            lines.append(f"\tdescription: {desc}")

        for tp in _get(role, "table_permissions", []):
            table = _get(tp, "table_name", "")
            expr = _get(tp, "filter_expression", "TRUE()")
            lines.append(f"\ttablePermission '{table}'")
            filter_clean = expr.replace('\n', ' ').replace('\r', ' ').strip()
            lines.append(f"\t\tfilterExpression = {filter_clean}")
        lines.append("")

    return "\n".join(lines)


def generate_expressions_tmdl(
    lakehouse_name: str = "MyLakehouse",
    sql_endpoint: str = "",
    additional_sources: list[dict[str, str]] | dict[str, str] | None = None,
) -> str:
    """Generate the expressions.tmdl content with shared M data sources.

    Produces parameterized M expressions for easy environment switching:
    - ``Lakehouse`` — main data source connection
    - ``ServerName`` — SQL endpoint parameter (dev/staging/prod)
    - ``DatabaseName`` — database/lakehouse name parameter

    Parameters
    ----------
    lakehouse_name
        Fabric Lakehouse name.
    sql_endpoint
        Optional SQL endpoint override.
    additional_sources
        Extra named expressions.  Accepts either:
        - A list of ``{name, expression}`` dicts, or
        - A dict mapping ``name → expression``.
    """
    endpoint = sql_endpoint or "localhost"
    lines: list[str] = []

    # M parameter: ServerName (enables dev/staging/prod switching)
    lines.append(f'expression ServerName = "{endpoint}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]')
    lines.append("")

    # M parameter: DatabaseName
    lines.append(f'expression DatabaseName = "{lakehouse_name}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]')
    lines.append("")

    # Additional source parameters (simple string parameters)
    sources_list: list[dict[str, str]] = []
    if isinstance(additional_sources, dict):
        sources_list = [{"name": k, "expression": v} for k, v in additional_sources.items()]
    elif additional_sources:
        sources_list = additional_sources

    for src in sources_list:
        name = src.get("name", "Source")
        expr = src.get("expression", "")
        # Emit as simple parameter expression
        safe_expr = expr.replace('"', '\\"') if expr else ""
        lines.append(f'expression {_quote_name(name)} = "{safe_expr}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]')
        lines.append("")

    return "\n".join(lines)


def _deduplicate_tables(tables: list[LogicalTable]) -> list[LogicalTable]:
    """Merge duplicate-named tables into one with the superset of columns."""
    merged: dict[str, LogicalTable] = {}
    for table in tables:
        if table.name not in merged:
            merged[table.name] = table
        else:
            existing = merged[table.name]
            # Merge columns (superset by name, keeping existing kind priority)
            existing_col_names = {c.name for c in existing.columns}
            for col in table.columns:
                if col.name not in existing_col_names:
                    existing.columns.append(col)
                    existing_col_names.add(col.name)
            # Merge hierarchies (superset by name)
            existing_hier_names = {h.name for h in existing.hierarchies}
            for h in table.hierarchies:
                if h.name not in existing_hier_names:
                    existing.hierarchies.append(h)
                    existing_hier_names.add(h.name)
            # Merge physical sources
            existing_sources = set(existing.physical_sources)
            for src in table.physical_sources:
                if src not in existing_sources:
                    existing.physical_sources.append(src)
            # Keep richer metadata (non-empty description, calculation_group, etc.)
            if not existing.description and table.description:
                existing.description = table.description
            if existing.calculation_group is None and table.calculation_group is not None:
                existing.calculation_group = table.calculation_group
            if existing.refresh_policy is None and table.refresh_policy is not None:
                existing.refresh_policy = table.refresh_policy
            if not existing.partition_sql and table.partition_sql:
                existing.partition_sql = table.partition_sql
    return list(merged.values())


def generate_tmdl(
    ir: SemanticModelIR,
    table_mapping: dict[str, str] | None = None,
    lakehouse_name: str = "MyLakehouse",
    llm_client: Any = None,
    rls_roles: list[dict[str, Any]] | None = None,
    sql_endpoint: str = "",
    additional_sources: list[dict[str, str]] | None = None,
) -> TMDLGenerationResult:
    """Generate the complete TMDL file set from a SemanticModelIR.

    Returns a ``TMDLGenerationResult`` with all files as a dict
    (relative path → content string).
    """
    files: dict[str, str] = {}
    translation_log: list[DAXTranslation] = []
    warnings: list[str] = []
    review_items: list[dict[str, Any]] = []

    # 0. Deduplicate tables — merge duplicate-named tables into one
    ir.tables = _deduplicate_tables(ir.tables)

    # 0b. Drop empty tables (no columns at all — cause PBI errors)
    ir.tables = [t for t in ir.tables if t.columns]

    # 1. Model-level (deferred — needs table list + roles)
    # Generated after tables so ref entries are correct

    # 2. Map all hierarchies
    all_hierarchies = map_all_hierarchies(ir)
    hierarchies_by_table: dict[str, list[TMDLHierarchy]] = {}
    for h in all_hierarchies:
        hierarchies_by_table.setdefault(h.table_name, []).append(h)
        if h.requires_review:
            review_items.append({
                "type": "hierarchy",
                "table": h.table_name,
                "hierarchy": h.name,
                "reason": h.review_reason,
            })

    # 2b. Build display folder map from subject areas
    display_folder_map = _build_display_folder_map(ir)

    # 3. Translate expressions and generate table files
    for table in ir.tables:
        table_translations: dict[str, DAXTranslation] = {}

        # Translate calculated columns and measures
        for col in table.calculated_columns + table.measures:
            if col.expression:
                tx = translate_expression(
                    expression=col.expression,
                    table_name=table.name,
                    column_name=col.name,
                    is_measure=(col.kind == ColumnKind.MEASURE),
                    table_mapping=table_mapping,
                )
                table_translations[col.name] = tx
                translation_log.append(tx)

                if tx.requires_review:
                    review_items.append({
                        "type": "expression",
                        "table": table.name,
                        "column": col.name,
                        "confidence": tx.confidence,
                        "reason": "; ".join(tx.warnings),
                    })

        table_hierarchies = hierarchies_by_table.get(table.name, [])
        tmdl_content = generate_table_tmdl(
            table, table_hierarchies, table_translations, lakehouse_name,
            display_folder_map=display_folder_map,
        )
        safe_name = _safe_filename(table.name)
        files[f"definition/tables/{safe_name}.tmdl"] = tmdl_content

    # 4. Relationships
    if ir.joins:
        files["definition/relationships.tmdl"] = generate_relationships_tmdl(ir.joins)

    # 5. Perspectives — validate against actual tables/columns
    if ir.subject_areas:
        valid_tables = {t.name for t in ir.tables}
        valid_columns: dict[str, set[str]] = {}
        _measure_names: dict[str, set[str]] = {}
        for t in ir.tables:
            cols = {c.name for c in t.columns}
            cols.update(c.name for c in t.calculated_columns)
            cols.update(c.name for c in t.measures)
            valid_columns[t.name] = cols
            _measure_names[t.name] = {c.name for c in t.measures}
        persp_content = generate_perspectives_tmdl(
            ir.subject_areas,
            valid_tables=valid_tables,
            valid_columns=valid_columns,
            measure_names=_measure_names,
        )
        if persp_content.strip():
            files["definition/perspectives.tmdl"] = persp_content

    # 6. Roles (from Agent 06 Security Agent)
    roles_content = generate_roles_tmdl(rls_roles)
    if roles_content:
        files["definition/roles.tmdl"] = roles_content

    # 1b. Model-level (deferred so ref entries can list all tables/roles)
    # Extract actual perspective names from generated content
    _actual_persps: set[str] | None = None
    persp_file = files.get("definition/perspectives.tmdl", "")
    if persp_file:
        import re as _re2
        _actual_persps = set()
        for _pm in _re2.finditer(r"^perspective\s+(?:'([^']+)'|(\w+))", persp_file, _re2.MULTILINE):
            _actual_persps.add(_pm.group(1) or _pm.group(2))
    files["definition/model.tmdl"] = generate_model_tmdl(
        ir, rls_roles=rls_roles, actual_perspectives=_actual_persps,
    )

    # 7. Shared M expressions / data sources
    files["definition/expressions.tmdl"] = generate_expressions_tmdl(
        lakehouse_name=lakehouse_name,
        sql_endpoint=sql_endpoint,
        additional_sources=additional_sources,
    )

    # 8. .platform config
    files[".platform"] = generate_platform_json(ir.model_name)

    # 8b. definition.pbism (required by Power BI Desktop)
    files["definition.pbism"] = generate_definition_pbism()

    # 9. database.tmdl (compatibility level)
    files["definition/database.tmdl"] = _generate_database_tmdl(ir.model_name)

    # 9b. Culture files (multi-language support)
    if ir.cultures:
        # Build Copilot synonyms from column names
        synonyms: dict[str, list[str]] = {}
        for table in ir.tables:
            for col in table.direct_columns + table.calculated_columns:
                friendly = _column_to_friendly_name(col.name)
                if friendly != col.name:
                    synonyms[col.name] = [friendly]
        culture_files = generate_all_cultures(
            cultures=ir.cultures,
            tables=ir.tables,
            linguistic_synonyms=synonyms,
        )
        files.update(culture_files)

    # 10. Calendar table (auto-detect date columns)
    table_dicts = [
        {
            "name": t.name,
            "columns": [
                {"name": c.name, "data_type": c.data_type or ""}
                for c in t.direct_columns
            ],
        }
        for t in ir.tables
    ]
    if should_generate_calendar(table_dicts):
        date_refs = detect_date_columns(table_dicts)
        calendar_tmdl = generate_calendar_table_tmdl(date_refs)
        files["definition/tables/Calendar.tmdl"] = calendar_tmdl
        warnings.append("Auto-generated Calendar table — review TI measures")

        # Add ref table Calendar to model.tmdl (Calendar is generated after model)
        model_content = files.get("definition/model.tmdl", "")
        if "ref table Calendar" not in model_content:
            # Insert before the first ref expression line
            model_content = model_content.replace(
                "\nref expression ",
                "\nref table Calendar\n\nref expression ",
                1,
            )
            files["definition/model.tmdl"] = model_content

    # 11. DAX optimizer (pre-deploy)
    for path in list(files.keys()):
        if path.startswith("definition/tables/"):
            content = files[path]
            # Optimize measures in place
            for m in _re.finditer(r"(measure\s+'[^']+'\s*=\s*)(.+?)(?=\n\s+\w|\Z)", content, _re.DOTALL):
                original_dax = m.group(2).strip()
                optimized_dax, _ = optimize_dax(original_dax)
                if optimized_dax != original_dax:
                    content = content.replace(m.group(0), m.group(1) + optimized_dax)
            files[path] = content

    # 12. Leak detector (scan for un-translated OAC functions)
    for path in list(files.keys()):
        if path.startswith("definition/tables/"):
            content = files[path]
            fixed, fix_count = auto_fix_dax(content)
            if fix_count:
                files[path] = fixed
                warnings.append(f"Auto-fixed {fix_count} OAC function leaks in {path}")

    # 13. Self-healing (6 patterns)
    heal_result = self_heal(files)
    files = heal_result.files
    for repair in heal_result.repairs:
        warnings.append(f"Self-heal [{repair.pattern}]: {repair.description}")

    result = TMDLGenerationResult(
        files=files,
        translation_log=translation_log,
        warnings=warnings,
        review_items=review_items,
        table_count=len(ir.tables),
        measure_count=sum(len(t.measures) for t in ir.tables),
        relationship_count=len(ir.joins),
        hierarchy_count=len(all_hierarchies),
    )

    logger.info(
        "TMDL generated: %d tables, %d measures, %d relationships, %d hierarchies, %d files",
        result.table_count, result.measure_count, result.relationship_count,
        result.hierarchy_count, len(files),
    )
    return result


def write_tmdl_to_disk(result: TMDLGenerationResult, output_dir: Path) -> None:
    """Write generated TMDL files to the filesystem."""
    for rel_path, content in result.files.items():
        full_path = output_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
    logger.info("Wrote %d TMDL files to %s", len(result.files), output_dir)


# ---------------------------------------------------------------------------
# Multi-culture TMDL generation (Phase 49)
# ---------------------------------------------------------------------------

# 19 commonly-used locale codes
SUPPORTED_CULTURES: list[str] = [
    "en-US", "fr-FR", "de-DE", "es-ES", "pt-BR",
    "ja-JP", "zh-CN", "zh-TW", "ko-KR", "it-IT",
    "nl-NL", "ru-RU", "ar-SA", "hi-IN", "pl-PL",
    "sv-SE", "nb-NO", "da-DK", "fi-FI",
]


def generate_culture_tmdl(
    culture: str,
    tables: list[LogicalTable] | None = None,
    linguistic_synonyms: dict[str, list[str]] | None = None,
) -> str:
    """Generate a culture TMDL file for a specific locale.

    Args:
        culture: Locale code (e.g. "fr-FR")
        tables: List of tables for generating display folder translations
        linguistic_synonyms: Optional {field_name: [synonym, ...]} map for Q&A

    Returns:
        TMDL content for the culture file
    """
    lines = [f"culture {_quote_name(culture)}"]

    # Linguistic metadata with synonyms (JSON block)
    lines.append("\tlinguisticMetadata =")
    lines.append("\t\t```")
    metadata: dict[str, Any] = {
        "Version": "1.0.0",
        "Language": culture,
        "DynamicImprovement": "HighConfidence",
    }
    if linguistic_synonyms:
        entities: dict[str, Any] = {}
        for field_name, syns in linguistic_synonyms.items():
            if syns:
                entities[field_name] = {
                    "State": "Generated",
                    "Terms": [
                        {"Value": s, "State": "Suggested", "Weight": 0.9}
                        for s in syns[:5]
                    ],
                }
        if entities:
            metadata["Entities"] = entities
    lines.append(f"\t\t\t{json.dumps(metadata, ensure_ascii=False)}")
    lines.append("\t\t\t```")
    lines.append("")

    return "\n".join(lines)


def generate_all_cultures(
    cultures: list[str] | None = None,
    tables: list[LogicalTable] | None = None,
    linguistic_synonyms: dict[str, list[str]] | None = None,
) -> dict[str, str]:
    """Generate culture TMDL files for multiple locales.

    Args:
        cultures: List of locale codes (default: SUPPORTED_CULTURES)
        tables: Tables list for display folder translations
        linguistic_synonyms: {field_name: [synonym, ...]} for Q&A

    Returns:
        Dict of relative_path → TMDL content
    """
    target_cultures = cultures or SUPPORTED_CULTURES
    files: dict[str, str] = {}
    for culture in target_cultures:
        if culture == "en-US":
            continue  # Default culture, no translation file needed
        files[f"definition/cultures/{culture}.tmdl"] = generate_culture_tmdl(
            culture, tables=tables, linguistic_synonyms=linguistic_synonyms,
        )
    logger.info("Generated %d culture TMDL files", len(files))
    return files


# ---------------------------------------------------------------------------
# Copilot annotations (Phase 49)
# ---------------------------------------------------------------------------


def annotate_for_copilot(
    ir: SemanticModelIR,
) -> dict[str, str]:
    """Generate Copilot-friendly annotations for tables and measures.

    Emits extended property annotations that Microsoft Copilot in Power BI
    uses for natural language Q&A:
    - Table descriptions
    - Column synonyms
    - Measure descriptions

    Returns:
        Dict of {table_name: annotation_tmdl_fragment}
    """
    annotations: dict[str, str] = {}

    for table in ir.tables:
        lines: list[str] = []

        # Table-level description annotation
        desc = table.description or f"Data from {table.name}"
        lines.append(f"    annotation Copilot_TableDescription = {desc}")

        # Column synonyms from names (camelCase/snake_case → friendly)
        for col in table.direct_columns:
            friendly = _column_to_friendly_name(col.name)
            if friendly != col.name:
                lines.append(
                    f"    annotation Copilot_ColumnSynonym_{col.name} = {friendly}"
                )

        # Measure descriptions
        for col in table.measures:
            m_desc = col.description or f"Measure: {col.name}"
            lines.append(
                f"    annotation Copilot_MeasureDescription_{col.name} = {m_desc}"
            )

        annotations[table.name] = "\n".join(lines)

    logger.info("Generated Copilot annotations for %d tables", len(annotations))
    return annotations


def _column_to_friendly_name(name: str) -> str:
    """Convert a column name to a friendly name for Copilot synonyms.

    E.g. 'order_date' → 'Order Date', 'customerID' → 'Customer ID'
    """
    import re as _re
    # snake_case to words
    words = _re.sub(r"[_\-]", " ", name)
    # camelCase to words
    words = _re.sub(r"([a-z])([A-Z])", r"\1 \2", words)
    # Capitalize each word
    return " ".join(w.capitalize() for w in words.split())
