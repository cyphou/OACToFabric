"""Direct Lake Generator — optimize semantic models for Direct Lake mode.

Generates TMDL configurations that leverage Direct Lake connectivity
in Fabric, enabling in-memory performance with OneLake Delta tables
without data import/duplication.

Handles:
  - DirectLake partition expressions (entity-based, no M query)
  - Framing detection and partition configuration
  - Fallback mode configuration (DirectQuery / Import)
  - Column mapping to Delta column names
  - V-Order optimization hints
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration types
# ---------------------------------------------------------------------------


@dataclass
class DirectLakeTableConfig:
    """Direct Lake configuration for a single table."""

    table_name: str
    entity_name: str              # Delta table name in Lakehouse
    schema_name: str = ""         # OneLake schema (default: dbo)
    lakehouse_id: str = ""
    workspace_id: str = ""
    columns: list[DirectLakeColumnMap] = field(default_factory=list)
    framing_enabled: bool = True
    v_order: bool = True


@dataclass
class DirectLakeColumnMap:
    """Mapping from semantic model column to Delta table column."""

    model_column: str
    delta_column: str
    data_type: str = "String"
    is_key: bool = False


@dataclass
class DirectLakeConfig:
    """Complete Direct Lake semantic model configuration."""

    model_name: str
    lakehouse_name: str
    lakehouse_id: str = ""
    workspace_id: str = ""
    tables: list[DirectLakeTableConfig] = field(default_factory=list)
    fallback_mode: str = "DirectQuery"   # DirectQuery, Import, Automatic
    default_schema: str = "dbo"
    framing_type: str = "Automatic"      # Automatic, Manual, None

    def to_tmdl_model_section(self) -> str:
        """Generate model-level TMDL for Direct Lake configuration."""
        lines = [
            "model Model",
            f"\tculture = en-US",
            f"\tdefaultPowerBIDataSourceVersion = powerBI_V3",
            "",
            "\tannotation __PBI_DirectLakeFallback = 1",
            f"\tannotation __PBI_DirectLakeFallbackMode = {self.fallback_mode}",
        ]
        return "\n".join(lines)


@dataclass
class DirectLakeResult:
    """Result of Direct Lake generation."""

    table_tmdl_snippets: dict[str, str] = field(default_factory=dict)
    model_tmdl: str = ""
    expression_tmdl: str = ""
    warnings: list[str] = field(default_factory=list)
    table_count: int = 0


# ---------------------------------------------------------------------------
# TMDL generation
# ---------------------------------------------------------------------------


def _generate_entity_partition(config: DirectLakeTableConfig) -> str:
    """Generate Direct Lake entity partition TMDL."""
    lines = [
        f"\tpartition '{config.table_name}' = entity",
        f"\t\tentityName = '{config.entity_name}'",
        f"\t\tschemaCheck = warn",
    ]
    if config.schema_name:
        lines.append(f"\t\tschemaName = '{config.schema_name}'")
    return "\n".join(lines)


def _generate_table_tmdl(config: DirectLakeTableConfig) -> str:
    """Generate TMDL for a Direct Lake table."""
    lines = [f"table '{config.table_name}'"]

    # Partition
    lines.append(_generate_entity_partition(config))
    lines.append("")

    # Columns
    for col in config.columns:
        lines.append(f"\tcolumn '{col.model_column}'")
        lines.append(f"\t\tdataType = {col.data_type}")
        lines.append(f"\t\tsourceColumn = '{col.delta_column}'")
        if col.is_key:
            lines.append(f"\t\tisKey = true")
        lines.append("")

    return "\n".join(lines)


def _generate_expression_tmdl(lakehouse_name: str, lakehouse_id: str = "") -> str:
    """Generate the shared expression (data source) for Direct Lake."""
    lines = [
        "expression 'DatabaseQuery' =",
        '\tlet',
        f"\t\tSource = Sql.Database(\"sqluserendpoint\", \"{lakehouse_name}\")",
        '\tin',
        '\t\tSource',
        "",
        "\tannotation PBI_IncludeInAutoRefresh = false",
    ]
    if lakehouse_id:
        lines.append(f"\tannotation PBI_DirectLakeLakehouseId = {lakehouse_id}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_direct_lake_config(
    model_name: str,
    tables: list[dict[str, Any]],
    lakehouse_name: str,
    lakehouse_id: str = "",
    workspace_id: str = "",
    fallback_mode: str = "DirectQuery",
) -> DirectLakeConfig:
    """Create a Direct Lake configuration from table definitions.

    Parameters
    ----------
    model_name : str
        Semantic model name.
    tables : list[dict[str, Any]]
        Table definitions with name, entity_name, and columns.
    lakehouse_name : str
        Target Fabric Lakehouse name.
    lakehouse_id : str
        Lakehouse GUID.
    workspace_id : str
        Workspace GUID.
    fallback_mode : str
        Fallback behavior (DirectQuery, Import, Automatic).

    Returns
    -------
    DirectLakeConfig
        Complete Direct Lake configuration.
    """
    dl_tables: list[DirectLakeTableConfig] = []

    for tbl in tables:
        columns = [
            DirectLakeColumnMap(
                model_column=c.get("model_column", c.get("name", "")),
                delta_column=c.get("delta_column", c.get("name", "")),
                data_type=c.get("data_type", "String"),
                is_key=c.get("is_key", False),
            )
            for c in tbl.get("columns", [])
        ]

        dl_tables.append(DirectLakeTableConfig(
            table_name=tbl.get("name", ""),
            entity_name=tbl.get("entity_name", tbl.get("name", "")),
            schema_name=tbl.get("schema", "dbo"),
            lakehouse_id=lakehouse_id,
            workspace_id=workspace_id,
            columns=columns,
        ))

    return DirectLakeConfig(
        model_name=model_name,
        lakehouse_name=lakehouse_name,
        lakehouse_id=lakehouse_id,
        workspace_id=workspace_id,
        tables=dl_tables,
        fallback_mode=fallback_mode,
    )


def generate_direct_lake_tmdl(config: DirectLakeConfig) -> DirectLakeResult:
    """Generate TMDL files for a Direct Lake semantic model.

    Parameters
    ----------
    config : DirectLakeConfig
        Direct Lake configuration.

    Returns
    -------
    DirectLakeResult
        Generated TMDL snippets for tables, model, and expressions.
    """
    result = DirectLakeResult()

    # Model-level TMDL
    result.model_tmdl = config.to_tmdl_model_section()

    # Expression (shared data source)
    result.expression_tmdl = _generate_expression_tmdl(
        config.lakehouse_name, config.lakehouse_id
    )

    # Table TMDL snippets
    for tbl in config.tables:
        tmdl = _generate_table_tmdl(tbl)
        result.table_tmdl_snippets[tbl.table_name] = tmdl
        result.table_count += 1

    logger.info(
        "Generated Direct Lake TMDL for '%s': %d tables, fallback=%s",
        config.model_name,
        result.table_count,
        config.fallback_mode,
    )
    return result
