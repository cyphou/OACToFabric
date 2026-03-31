"""Mirroring Config Generator — Fabric Mirroring setup for Oracle databases.

Generates Fabric Mirroring configuration JSON for near-real-time replication
of Oracle databases into OneLake Delta tables.  Supports:
  - Database mirroring (full table replication)
  - Table selection (include / exclude patterns)
  - Replication schedule and retention policy
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class MirroringTableConfig:
    """Configuration for a single table in mirroring."""

    schema_name: str
    table_name: str
    include: bool = True


@dataclass
class MirroringConfig:
    """Fabric Mirroring configuration for an Oracle database."""

    source_type: str = "Oracle"
    display_name: str = "Oracle Mirroring"
    connection_server: str = ""
    connection_database: str = ""
    tables: list[MirroringTableConfig] = field(default_factory=list)
    replication_frequency_seconds: int = 60
    retention_days: int = 7
    workspace_id: str = ""
    capacity_id: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to Fabric REST API-compatible dict."""
        return {
            "type": "MirroredDatabase",
            "displayName": self.display_name,
            "definition": {
                "parts": [
                    {
                        "path": "mirroringDefinition.json",
                        "payload": json.dumps(self._mirroring_definition()),
                        "payloadType": "InlineBase64",
                    }
                ]
            },
        }

    def _mirroring_definition(self) -> dict[str, Any]:
        return {
            "sourceType": self.source_type,
            "connection": {
                "server": self.connection_server,
                "database": self.connection_database,
            },
            "tables": [
                {
                    "schemaName": t.schema_name,
                    "tableName": t.table_name,
                    "include": t.include,
                }
                for t in self.tables
            ],
            "replication": {
                "frequencySeconds": self.replication_frequency_seconds,
                "retentionDays": self.retention_days,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialise to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Config generation from inventory
# ---------------------------------------------------------------------------


def generate_mirroring_config(
    server: str,
    database: str,
    tables: list[dict[str, Any]],
    display_name: str | None = None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    retention_days: int = 7,
    frequency_seconds: int = 60,
) -> MirroringConfig:
    """Generate a Fabric Mirroring configuration for an Oracle database.

    Parameters
    ----------
    server : str
        Oracle server hostname or connection string.
    database : str
        Oracle database / service name.
    tables : list[dict]
        Table metadata dicts with ``name`` and ``schema`` keys.
    display_name : str | None
        Fabric item display name (default: ``Oracle_<database>``).
    include_patterns : list[str] | None
        Glob patterns for tables to include (default: all).
    exclude_patterns : list[str] | None
        Glob patterns for tables to exclude.
    retention_days : int
        Delta table retention in days.
    frequency_seconds : int
        Replication polling interval.

    Returns
    -------
    MirroringConfig
        Complete mirroring configuration ready for Fabric REST API.
    """
    import fnmatch

    if display_name is None:
        display_name = f"Oracle_{database}"

    table_configs: list[MirroringTableConfig] = []
    warnings: list[str] = []

    for t in tables:
        tname = t.get("name", "")
        tschema = t.get("schema", "dbo")
        full = f"{tschema}.{tname}"

        include = True
        if include_patterns:
            include = any(fnmatch.fnmatch(full, p) for p in include_patterns)
        if exclude_patterns and any(fnmatch.fnmatch(full, p) for p in exclude_patterns):
            include = False

        table_configs.append(
            MirroringTableConfig(
                schema_name=tschema,
                table_name=tname,
                include=include,
            )
        )

    included = sum(1 for t in table_configs if t.include)
    logger.info(
        "Mirroring config: %d/%d tables included for %s",
        included,
        len(table_configs),
        database,
    )

    if included == 0:
        warnings.append("No tables selected for mirroring — check include/exclude patterns")

    return MirroringConfig(
        source_type="Oracle",
        display_name=display_name,
        connection_server=server,
        connection_database=database,
        tables=table_configs,
        replication_frequency_seconds=frequency_seconds,
        retention_days=retention_days,
        warnings=warnings,
    )
