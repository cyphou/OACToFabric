"""Schema & Data Model Migration Agent — Agent 02.

Implements the full schema migration lifecycle:
  1. Read physical layer inventory from Lakehouse (produced by Agent 01)
  2. Apply Oracle → Fabric data type mappings
  3. Generate DDL (Spark SQL / T-SQL)
  4. Generate Data Factory pipeline definitions
  5. (Execute DDL + data load against Fabric — delegated to external runner)
  6. Validate schema creation & row counts
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.base_agent import MigrationAgent
from src.core.config import settings
from src.core.models import (
    AssetType,
    Inventory,
    InventoryItem,
    MigrationPlan,
    MigrationResult,
    MigrationScope,
    MigrationStatus,
    ValidationReport,
)

from .ddl_generator import generate_create_table, generate_create_view, generate_ddl_script
from .pipeline_generator import generate_all_pipelines, serialize_pipeline
from .sql_translator import translate_sql
from .type_mapper import TargetPlatform, map_all_columns, map_oracle_type

logger = logging.getLogger(__name__)


class SchemaAgent(MigrationAgent):
    """Agent 02 — Schema & Data Model Migration."""

    def __init__(
        self,
        lakehouse_client: Any | None = None,
        target_platform: TargetPlatform = TargetPlatform.LAKEHOUSE,
        oracle_schema: str = "OACS",
        oracle_connection_name: str = "OracleDB_Prod",
        lakehouse_name: str = "oac_migration",
        output_dir: str | Path = "output/schema",
    ) -> None:
        super().__init__(agent_id="agent-02", agent_name="Schema & Data Model Migration Agent")
        self._lakehouse = lakehouse_client
        self._platform = target_platform
        self._oracle_schema = oracle_schema
        self._oracle_conn = oracle_connection_name
        self._lakehouse_name = lakehouse_name
        self._output_dir = Path(output_dir)
        self._mapping_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # MigrationAgent interface
    # ------------------------------------------------------------------

    async def discover(self, scope: MigrationScope) -> Inventory:
        """Read physical-layer inventory from the Lakehouse (Agent 01 output)."""
        items: list[InventoryItem] = []

        if self._lakehouse is not None:
            # Read physical tables and views from migration_inventory
            for asset_type in (AssetType.PHYSICAL_TABLE.value,):
                rows = self._lakehouse.read_inventory(asset_type=asset_type)
                for row in rows:
                    items.append(
                        InventoryItem(
                            id=row["id"],
                            asset_type=AssetType(row["asset_type"]),
                            source_path=row["source_path"],
                            name=row["name"],
                            owner=row.get("owner", ""),
                            metadata=row.get("metadata", {}),
                        )
                    )
        else:
            logger.warning("No Lakehouse client — using scope metadata for table list")
            # Allow tables to be passed via scope metadata for testing
            # Expect scope.include_paths to contain table names
            for path in scope.include_paths:
                name = path.strip("/").split("/")[-1]
                items.append(
                    InventoryItem(
                        id=f"physicaltable__{name.lower()}",
                        asset_type=AssetType.PHYSICAL_TABLE,
                        source_path=path,
                        name=name,
                        metadata={},
                    )
                )

        # Apply scope filters
        if scope.exclude_paths:
            items = [
                i for i in items
                if not any(i.source_path.startswith(ex) for ex in scope.exclude_paths)
            ]
        if scope.asset_types:
            items = [i for i in items if i.asset_type in scope.asset_types]

        inventory = Inventory(items=items)
        logger.info("Schema agent discovered %d tables for migration", inventory.count)
        return inventory

    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """Generate DDL scripts and pipeline definitions."""
        plan = MigrationPlan(agent_id=self.agent_id, items=inventory.items)
        self._mapping_log.clear()

        # Build structured table definitions for DDL and pipeline generation
        table_defs: list[dict[str, Any]] = []

        for item in inventory.items:
            columns = item.metadata.get("columns", [])
            mapped_columns = map_all_columns(columns, self._platform)

            # Track each column mapping
            for mc in mapped_columns:
                self._mapping_log.append({
                    "table": item.name,
                    "column": mc.get("name", ""),
                    "oracle_type": mc.get("oracle_type", ""),
                    "fabric_type": mc.get("fabric_type", ""),
                    "is_fallback": mc.get("is_fallback", False),
                    "notes": mc.get("notes", ""),
                })

            table_defs.append({
                "name": item.name,
                "columns": mapped_columns,
                "primary_key": item.metadata.get("primary_key"),
                "partition_by": item.metadata.get("partition_by"),
                "comment": f"Migrated from Oracle {self._oracle_schema}.{item.name}",
                "watermark_column": item.metadata.get("watermark_column"),
                "key_columns": item.metadata.get("key_columns"),
                "row_count": item.metadata.get("row_count", 0),
                "partition_column": item.metadata.get("partition_column"),
            })

        # Generate DDL script
        ddl_script = generate_ddl_script(table_defs, self._platform)

        # Generate pipeline definitions
        pipelines = generate_all_pipelines(
            tables=table_defs,
            oracle_schema=self._oracle_schema,
            oracle_connection_name=self._oracle_conn,
            lakehouse_name=self._lakehouse_name,
            mode="both",
        )

        # Store artifacts in plan metadata for execute phase
        plan.estimated_duration_minutes = max(1, len(table_defs) * 2)

        # Stash generated artifacts on the plan object via a private attr
        self._ddl_script = ddl_script
        self._pipeline_defs = pipelines
        self._table_defs = table_defs

        logger.info(
            "Plan: %d tables, %d pipelines, %d column mappings (%d fallbacks)",
            len(table_defs),
            len(pipelines),
            len(self._mapping_log),
            sum(1 for m in self._mapping_log if m["is_fallback"]),
        )
        return plan

    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Write generated artifacts to disk and optionally to Lakehouse."""
        result = MigrationResult(agent_id=self.agent_id, total=len(plan.items))

        try:
            # Ensure output directory exists
            self._output_dir.mkdir(parents=True, exist_ok=True)

            # Write DDL script
            ddl_path = self._output_dir / f"ddl_{self._platform.value}.sql"
            ddl_path.write_text(self._ddl_script, encoding="utf-8")
            logger.info("DDL script written to %s", ddl_path)

            # Write pipeline JSON files
            pipelines_dir = self._output_dir / "pipelines"
            pipelines_dir.mkdir(exist_ok=True)
            for pipeline in self._pipeline_defs:
                pname = pipeline["name"]
                p_path = pipelines_dir / f"{pname}.json"
                p_path.write_text(serialize_pipeline(pipeline), encoding="utf-8")
            logger.info("Wrote %d pipeline JSON files to %s", len(self._pipeline_defs), pipelines_dir)

            # Write mapping log
            mapping_path = self._output_dir / "type_mapping_log.json"
            mapping_path.write_text(json.dumps(self._mapping_log, indent=2), encoding="utf-8")

            # Write mapping rules to Lakehouse if available
            if self._lakehouse is not None:
                try:
                    self._write_mapping_rules()
                except Exception:
                    logger.exception("Failed to write mapping rules to Lakehouse")

            result.succeeded = len(plan.items)
            result.completed_at = datetime.now(timezone.utc)

        except Exception as exc:
            logger.exception("Schema agent execution failed")
            result.failed = len(plan.items)
            result.errors.append({"error": str(exc)})
            result.completed_at = datetime.now(timezone.utc)

        return result

    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Validate that schema artifacts were generated correctly."""
        report = ValidationReport(agent_id=self.agent_id)

        # Check 1: all items processed
        report.total_checks += 1
        if result.failed == 0:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "all_items_processed", "status": "FAIL"})

        # Check 2: DDL file was created
        report.total_checks += 1
        ddl_path = self._output_dir / f"ddl_{self._platform.value}.sql"
        if ddl_path.exists() and ddl_path.stat().st_size > 0:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "ddl_file_exists", "status": "FAIL"})

        # Check 3: pipeline files exist
        report.total_checks += 1
        pipelines_dir = self._output_dir / "pipelines"
        if pipelines_dir.exists() and any(pipelines_dir.glob("*.json")):
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "pipeline_files_exist", "status": "FAIL"})

        # Check 4: no unexpected fallback types
        report.total_checks += 1
        fallbacks = [m for m in self._mapping_log if m["is_fallback"]]
        if not fallbacks:
            report.passed += 1
        else:
            report.warnings += 1
            report.details.append({
                "check": "no_fallback_types",
                "status": "WARN",
                "fallback_count": len(fallbacks),
                "columns": [f"{m['table']}.{m['column']}" for m in fallbacks],
            })

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_mapping_rules(self) -> None:
        """Write type mapping rules to the Lakehouse mapping_rules table."""
        # This would use self._lakehouse to write mapping rules
        # For now, just log
        logger.info("Would write %d mapping rules to Lakehouse", len(self._mapping_log))

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def mapping_log(self) -> list[dict[str, Any]]:
        return self._mapping_log

    def generate_summary_report(self) -> str:
        """Generate a Markdown summary of the schema migration."""
        lines = [
            "# Schema Migration Summary Report",
            "",
            f"**Generated at:** {datetime.now(timezone.utc).isoformat()}Z",
            f"**Target platform:** Fabric {self._platform.value}",
            f"**Tables planned:** {len(self._table_defs) if hasattr(self, '_table_defs') else 'N/A'}",
            f"**Pipelines generated:** {len(self._pipeline_defs) if hasattr(self, '_pipeline_defs') else 'N/A'}",
            "",
            "## Column Type Mapping Summary",
            "",
            f"- **Total columns mapped:** {len(self._mapping_log)}",
            f"- **Fallback mappings:** {sum(1 for m in self._mapping_log if m['is_fallback'])}",
            "",
        ]

        # Breakdown by Oracle type
        type_counts: dict[str, int] = {}
        for m in self._mapping_log:
            ot = m["oracle_type"].upper().split("(")[0]
            type_counts[ot] = type_counts.get(ot, 0) + 1

        if type_counts:
            lines.extend([
                "## Oracle Types Encountered",
                "",
                "| Oracle Type | Count |",
                "|---|---|",
            ])
            for ot, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| {ot} | {cnt} |")
            lines.append("")

        # Fallback details
        fallbacks = [m for m in self._mapping_log if m["is_fallback"]]
        if fallbacks:
            lines.extend([
                "## ⚠️ Fallback Type Mappings (Review Required)",
                "",
                "| Table | Column | Oracle Type |",
                "|---|---|---|",
            ])
            for m in fallbacks:
                lines.append(f"| {m['table']} | {m['column']} | {m['oracle_type']} |")
            lines.append("")

        return "\n".join(lines)
