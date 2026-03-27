"""TMDL generator — produce Tabular Model Definition Language files.

Generates the full TMDL folder structure for a Power BI Semantic Model
from the ``SemanticModelIR`` intermediate representation.

Output structure::

    SemanticModel/
    ├── model.tmdl
    ├── definition/
    │   ├── tables/
    │   │   ├── Sales.tmdl
    │   │   ├── Products.tmdl
    │   │   └── Date.tmdl
    │   ├── relationships.tmdl
    │   ├── perspectives.tmdl
    │   ├── roles.tmdl
    │   └── expressions.tmdl
    └── .platform
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
    ColumnKind,
    CrossFilterBehaviour,
    JoinCardinality,
    LogicalColumn,
    LogicalJoin,
    LogicalTable,
    SemanticModelIR,
    SubjectArea,
)
from .calendar_generator import detect_date_columns, generate_calendar_table_tmdl, should_generate_calendar
from .tmdl_self_healing import self_heal
from .dax_optimizer import optimize_dax
from .leak_detector import scan_dax_for_leaks, auto_fix_dax

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lineage tag helper
# ---------------------------------------------------------------------------

def _tag() -> str:
    """Generate a random lineage tag (UUID)."""
    return str(uuid.uuid4())


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
# TMDL text rendering
# ---------------------------------------------------------------------------


def _render_column(col: LogicalColumn, tmdl_type: str) -> str:
    """Render a TMDL column definition."""
    lines = [f"    column {col.name}"]
    lines.append(f"        dataType: {tmdl_type}")
    lines.append(f"        lineageTag: {_tag()}")
    fmt = _format_string(tmdl_type, col.name)
    if fmt:
        lines.append(f"        formatString: {fmt}")
    if col.source_column and col.kind == ColumnKind.DIRECT:
        lines.append(f"        sourceColumn: {col.source_column or col.name}")
    if col.kind == ColumnKind.DIRECT:
        summarize = "sum" if tmdl_type in ("decimal", "double") else "none"
        lines.append(f"        summarizeBy: {summarize}")
    if col.is_hidden:
        lines.append("        isHidden")
    if col.description:
        lines.append(f"        description: {col.description}")
    lines.append("")
    return "\n".join(lines)


def _render_calculated_column(col: LogicalColumn, dax: str) -> str:
    """Render a TMDL calculated column."""
    tmdl_type = _map_data_type(col.data_type) if col.data_type else "string"
    lines = [f"    column '{col.name}' = {dax}"]
    lines.append(f"        dataType: {tmdl_type}")
    lines.append(f"        lineageTag: {_tag()}")
    if col.is_hidden:
        lines.append("        isHidden")
    lines.append("")
    return "\n".join(lines)


def _render_measure(col: LogicalColumn, dax: str, display_folder: str = "") -> str:
    """Render a TMDL measure definition."""
    lines = [f"    measure '{col.name}' = {dax}"]
    lines.append(f"        lineageTag: {_tag()}")
    fmt = _format_string("double", col.name)
    if fmt:
        lines.append(f"        formatString: {fmt}")
    folder = display_folder or col.display_folder or "Measures"
    lines.append(f"        displayFolder: {folder}")
    if col.description:
        lines.append(f"        description: {col.description}")
    lines.append("")
    return "\n".join(lines)


def _render_partition(table: LogicalTable, lakehouse_name: str = "MyLakehouse") -> str:
    """Render a TMDL partition expression using M (Power Query)."""
    tbl_name = table.name.replace(" ", "_")
    lines = [
        f"    partition {table.name} = m",
        "        mode: import",
        "        source",
        "            let",
        f'                Source = Sql.Database("onelake-sql-endpoint", "{lakehouse_name}"),',
        f'                {tbl_name} = Source{{[Schema="dbo", Item="{tbl_name}"]}}[Data]',
        "            in",
        f"                {tbl_name}",
        "",
    ]
    return "\n".join(lines)


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
    lines = [f"table {table.name}"]
    lines.append(f"    lineageTag: {_tag()}")
    if table.description:
        lines.append(f"    description: {table.description}")
    lines.append("")

    # Partition
    lines.append(_render_partition(table, lakehouse_name))

    # Direct columns
    for col in table.direct_columns:
        tmdl_type = _map_data_type(col.data_type) if col.data_type else "string"
        lines.append(_render_column(col, tmdl_type))

    # Calculated columns
    for col in table.calculated_columns:
        tx = translations.get(col.name)
        dax = tx.dax_expression if tx else col.expression
        lines.append(_render_calculated_column(col, dax))

    # Measures
    for col in table.measures:
        tx = translations.get(col.name)
        dax = tx.dax_expression if tx else col.expression
        folder = tx.display_folder if tx else tbl_folders.get(col.name, "")
        lines.append(_render_measure(col, dax, folder))

    # Hierarchies
    for h in hierarchies:
        lines.append(hierarchy_to_tmdl(h))
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
        name = f"rel_{j.from_table}_{j.to_table}".replace(" ", "_")

        lines.append(f"relationship {name}")
        lines.append(f"    fromTable: '{j.from_table}'")
        lines.append(f"    fromColumn: {j.from_column or 'ID'}")
        lines.append(f"    toTable: '{j.to_table}'")
        lines.append(f"    toColumn: {j.to_column or 'ID'}")
        lines.append(f"    fromCardinality: {from_card}")
        lines.append(f"    toCardinality: {to_card}")

        # Cross-filter direction
        cf = "singleDirection"
        if j.join_type.lower() in ("full", "cross"):
            cf = "bothDirections"
        lines.append(f"    crossFilteringBehavior: {cf}")

        if not j.is_active:
            lines.append("    isActive: false")
        lines.append(f"    lineageTag: {_tag()}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Perspectives TMDL (from Subject Areas)
# ---------------------------------------------------------------------------


def generate_perspectives_tmdl(subject_areas: list[SubjectArea]) -> str:
    """Generate the perspectives.tmdl content."""
    if not subject_areas:
        return ""
    lines: list[str] = []
    for sa in subject_areas:
        lines.append(f"perspective '{sa.name}'")
        for tbl in sa.tables:
            lines.append(f"    perspectiveTable '{tbl}'")
            cols = sa.columns.get(tbl, [])
            for col in cols:
                lines.append(f"        perspectiveColumn {col}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model-level TMDL
# ---------------------------------------------------------------------------


def generate_model_tmdl(ir: SemanticModelIR) -> str:
    """Generate the model.tmdl (model-level properties)."""
    lines = [
        f"model {ir.model_name}",
        f"    culture: en-US",
        f"    defaultPowerBIDataSourceVersion: powerBI_V3",
        f"    sourceQueryCulture: en-US",
        f"    lineageTag: {_tag()}",
    ]
    if ir.description:
        lines.append(f"    description: {ir.description}")
    lines.append("")
    return "\n".join(lines)


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


# ---------------------------------------------------------------------------
# database.tmdl
# ---------------------------------------------------------------------------


def _generate_database_tmdl(
    model_name: str = "SemanticModel",
    compatibility_level: int = 1604,
) -> str:
    """Generate the database.tmdl file with compatibility level and options."""
    lines = [
        f"compatibilityLevel: {compatibility_level}",
        "",
        f"model {model_name}",
        "    defaultMode: import",
        "    discourageImplicitMeasures",
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
        lines.append(f"    modelPermission: read")
        lines.append(f"    lineageTag: {_tag()}")
        if desc:
            lines.append(f"    description: {desc}")

        for tp in _get(role, "table_permissions", []):
            table = _get(tp, "table_name", "")
            expr = _get(tp, "filter_expression", "TRUE()")
            lines.append(f"    tablePermission '{table}'")
            lines.append(f"        filterExpression: {expr}")
        lines.append("")

    return "\n".join(lines)


def generate_expressions_tmdl(
    lakehouse_name: str = "MyLakehouse",
    sql_endpoint: str = "",
    additional_sources: list[dict[str, str]] | dict[str, str] | None = None,
) -> str:
    """Generate the expressions.tmdl content with shared M data sources.

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
    endpoint = sql_endpoint or f"{{lakehouse_sql_endpoint}}"
    lines = [
        f"expression 'Lakehouse' =",
        f"    let",
        f'        Source = Sql.Database("{endpoint}", "{lakehouse_name}"),',
        f"    in",
        f"        Source",
        f"    lineageTag: {_tag()}",
        f"    queryGroup: 'Data Sources'",
        f"",
    ]

    # Normalise additional_sources to list[dict]
    sources_list: list[dict[str, str]] = []
    if isinstance(additional_sources, dict):
        sources_list = [{"name": k, "expression": v} for k, v in additional_sources.items()]
    elif additional_sources:
        sources_list = additional_sources

    for src in sources_list:
        name = src.get("name", "Source")
        expr = src.get("expression", "")
        lines.append(f"expression '{name}' =")
        for line in expr.strip().splitlines():
            lines.append(f"    {line}")
        lines.append(f"    lineageTag: {_tag()}")
        lines.append("")

    return "\n".join(lines)


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

    # 1. Model-level
    files["model.tmdl"] = generate_model_tmdl(ir)

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
        safe_name = table.name.replace(" ", "_")
        files[f"definition/tables/{safe_name}.tmdl"] = tmdl_content

    # 4. Relationships
    if ir.joins:
        files["definition/relationships.tmdl"] = generate_relationships_tmdl(ir.joins)

    # 5. Perspectives
    if ir.subject_areas:
        files["definition/perspectives.tmdl"] = generate_perspectives_tmdl(ir.subject_areas)

    # 6. Roles (from Agent 06 Security Agent)
    files["definition/roles.tmdl"] = generate_roles_tmdl(rls_roles)

    # 7. Shared M expressions / data sources
    files["definition/expressions.tmdl"] = generate_expressions_tmdl(
        lakehouse_name=lakehouse_name,
        sql_endpoint=sql_endpoint,
        additional_sources=additional_sources,
    )

    # 8. .platform config
    files[".platform"] = generate_platform_json(ir.model_name)

    # 9. database.tmdl (compatibility level)
    files["definition/database.tmdl"] = _generate_database_tmdl(ir.model_name)

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

    # 11. DAX optimizer (pre-deploy)
    for path in list(files.keys()):
        if path.startswith("definition/tables/"):
            content = files[path]
            # Optimize measures in place
            import re as _re
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
    translations: dict[str, dict[str, str]] | None = None,
) -> str:
    """Generate a culture TMDL file for a specific locale.

    Args:
        culture: Locale code (e.g. "fr-FR")
        translations: Optional {table_name: {original: translated}} map

    Returns:
        TMDL content for the culture file
    """
    lines = [f"culture {culture}"]
    lines.append(f"    linguisticMetadata =")
    lines.append(f"        linguisticMetadata")
    lines.append(f"            culture: {culture}")
    lines.append("")

    if translations:
        for table_name, col_map in translations.items():
            for original, translated in col_map.items():
                lines.append(f"    // {table_name}.{original} → {translated}")

    lines.append("")
    return "\n".join(lines)


def generate_all_cultures(
    cultures: list[str] | None = None,
) -> dict[str, str]:
    """Generate culture TMDL files for multiple locales.

    Args:
        cultures: List of locale codes (default: SUPPORTED_CULTURES)

    Returns:
        Dict of relative_path → TMDL content
    """
    target_cultures = cultures or SUPPORTED_CULTURES
    files: dict[str, str] = {}
    for culture in target_cultures:
        safe_name = culture.replace("-", "_")
        files[f"definition/cultures/{safe_name}.tmdl"] = generate_culture_tmdl(culture)
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
