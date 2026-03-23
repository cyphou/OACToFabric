"""ETL/Data Pipeline Migration Agent — Agent 03.

Implements the full ETL migration lifecycle:
  1. Discover OAC data flows & Oracle scheduled jobs from Lakehouse inventory
  2. Parse data flow definitions and PL/SQL procedures
  3. Map OAC steps → Fabric equivalents (pipelines + notebooks)
  4. Convert Oracle schedules → Fabric triggers
  5. Write artefacts to disk and optionally deploy
  6. Validate generated artefacts
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.base_agent import MigrationAgent
from src.core.models import (
    AssetType,
    Inventory,
    InventoryItem,
    MigrationPlan,
    MigrationResult,
    MigrationScope,
    ValidationReport,
)

from .dataflow_parser import DataFlow, parse_dataflow_json, parse_multiple_dataflows
from .plsql_translator import TranslationResult, translate_plsql, translate_with_fallback
from .schedule_converter import (
    FabricTrigger,
    OracleSchedule,
    convert_multiple_schedules,
    convert_schedule,
    parse_oracle_job_metadata,
)
from .step_mapper import MappedDataFlow, map_dataflow, map_multiple_dataflows

logger = logging.getLogger(__name__)


class ETLAgent(MigrationAgent):
    """Agent 03 — ETL/Data Pipeline Migration."""

    def __init__(
        self,
        lakehouse_client: Any | None = None,
        llm_client: Any | None = None,
        oracle_schema: str = "OACS",
        output_dir: str | Path = "output/etl",
    ) -> None:
        super().__init__(agent_id="agent-03", agent_name="ETL/Data Pipeline Migration Agent")
        self._lakehouse = lakehouse_client
        self._llm = llm_client
        self._oracle_schema = oracle_schema
        self._output_dir = Path(output_dir)

        # Internal state accumulated during plan/execute
        self._data_flows: list[DataFlow] = []
        self._mapped_flows: list[MappedDataFlow] = []
        self._plsql_translations: list[TranslationResult] = []
        self._schedules: list[OracleSchedule] = []
        self._triggers: list[FabricTrigger] = []

    # ------------------------------------------------------------------
    # MigrationAgent interface
    # ------------------------------------------------------------------

    async def discover(self, scope: MigrationScope) -> Inventory:
        """Discover OAC data flows, stored procedures, and scheduled jobs."""
        items: list[InventoryItem] = []

        if self._lakehouse is not None:
            # Read data flows and stored procedures from migration_inventory
            for asset_type_val in (AssetType.DATA_FLOW.value,):
                rows = self._lakehouse.read_inventory(asset_type=asset_type_val)
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
            logger.warning("No Lakehouse client — using scope metadata for data flow list")
            for path in scope.include_paths:
                name = path.strip("/").split("/")[-1]
                asset_type = AssetType.DATA_FLOW
                items.append(
                    InventoryItem(
                        id=f"dataflow__{name.lower()}",
                        asset_type=asset_type,
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

        inventory = Inventory(items=items)
        logger.info("ETL agent discovered %d data flows / procedures", inventory.count)
        return inventory

    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """Parse data flows, map steps, translate PL/SQL, convert schedules."""
        plan = MigrationPlan(agent_id=self.agent_id, items=inventory.items)

        # Reset internal state
        self._data_flows.clear()
        self._mapped_flows.clear()
        self._plsql_translations.clear()
        self._schedules.clear()
        self._triggers.clear()

        # 1. Parse data flow definitions from metadata
        for item in inventory.items:
            if item.asset_type == AssetType.DATA_FLOW:
                flow_def = item.metadata.get("definition", {})
                if flow_def:
                    # Use the full definition from metadata
                    flow_def.setdefault("id", item.id)
                    flow_def.setdefault("name", item.name)
                    flow = parse_dataflow_json(flow_def)
                else:
                    # Minimal placeholder flow
                    flow = DataFlow(id=item.id, name=item.name)
                self._data_flows.append(flow)

        # 2. Map data flow steps to Fabric equivalents
        self._mapped_flows = map_multiple_dataflows(self._data_flows, self._oracle_schema)

        # 3. Translate PL/SQL procedures
        for item in inventory.items:
            plsql_body = item.metadata.get("procedure_body", "")
            if plsql_body:
                table_mapping = item.metadata.get("table_mapping", {})
                result = translate_with_fallback(
                    plsql=plsql_body,
                    procedure_name=item.name,
                    table_mapping=table_mapping,
                    llm_client=self._llm,
                )
                self._plsql_translations.append(result)

        # 4. Convert Oracle schedules
        for item in inventory.items:
            schedule_meta = item.metadata.get("schedule", {})
            if schedule_meta:
                schedule = parse_oracle_job_metadata({
                    "job_name": item.name,
                    **schedule_meta,
                })
                self._schedules.append(schedule)

        self._triggers = convert_multiple_schedules(self._schedules)

        plan.estimated_duration_minutes = max(1, len(inventory.items) * 3)

        logger.info(
            "Plan: %d data flows mapped, %d PL/SQL translated, %d schedules converted "
            "(%d require review)",
            len(self._mapped_flows),
            len(self._plsql_translations),
            len(self._triggers),
            sum(1 for mf in self._mapped_flows for s in mf.mapped_steps if s.requires_review)
            + sum(1 for t in self._plsql_translations if t.requires_review)
            + sum(1 for t in self._triggers if t.requires_review),
        )
        return plan

    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Write generated artefacts to disk."""
        result = MigrationResult(agent_id=self.agent_id, total=len(plan.items))

        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)

            # 1. Write pipeline JSON files
            pipelines_dir = self._output_dir / "pipelines"
            pipelines_dir.mkdir(exist_ok=True)
            for mf in self._mapped_flows:
                p_path = pipelines_dir / f"{mf.flow_name.replace(' ', '_')}.json"
                p_path.write_text(json.dumps(mf.pipeline_json, indent=2), encoding="utf-8")

            # 2. Write notebook files
            notebooks_dir = self._output_dir / "notebooks"
            notebooks_dir.mkdir(exist_ok=True)
            for mf in self._mapped_flows:
                nb_path = notebooks_dir / f"nb_{mf.flow_name.replace(' ', '_')}.py"
                nb_path.write_text(mf.notebook_code, encoding="utf-8")

            # 3. Write PL/SQL translation results
            if self._plsql_translations:
                translations_dir = self._output_dir / "translations"
                translations_dir.mkdir(exist_ok=True)
                for tr in self._plsql_translations:
                    tr_path = translations_dir / f"{tr.procedure_name}.py"
                    tr_path.write_text(tr.pyspark_code, encoding="utf-8")

            # 4. Write trigger definitions
            if self._triggers:
                triggers_dir = self._output_dir / "triggers"
                triggers_dir.mkdir(exist_ok=True)
                for trigger in self._triggers:
                    t_path = triggers_dir / f"{trigger.name}.json"
                    t_path.write_text(json.dumps(trigger.to_json(), indent=2), encoding="utf-8")

            # 5. Write review queue
            review_items = self._collect_review_items()
            if review_items:
                review_path = self._output_dir / "review_queue.json"
                review_path.write_text(json.dumps(review_items, indent=2), encoding="utf-8")

            # 6. Write mapping summary
            summary_path = self._output_dir / "etl_migration_summary.md"
            summary_path.write_text(self.generate_summary_report(), encoding="utf-8")

            result.succeeded = len(plan.items)
            result.completed_at = datetime.now(timezone.utc)

            logger.info(
                "ETL agent wrote %d pipelines, %d notebooks, %d translations, %d triggers",
                len(self._mapped_flows), len(self._mapped_flows),
                len(self._plsql_translations), len(self._triggers),
            )

        except Exception as exc:
            logger.exception("ETL agent execution failed")
            result.failed = len(plan.items)
            result.errors.append({"error": str(exc)})
            result.completed_at = datetime.now(timezone.utc)

        return result

    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Validate generated ETL artefacts."""
        report = ValidationReport(agent_id=self.agent_id)

        # Check 1: execution succeeded
        report.total_checks += 1
        if result.failed == 0:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "execution_success", "status": "FAIL"})

        # Check 2: pipeline files exist
        report.total_checks += 1
        pipelines_dir = self._output_dir / "pipelines"
        pipeline_files = list(pipelines_dir.glob("*.json")) if pipelines_dir.exists() else []
        if len(pipeline_files) >= len(self._mapped_flows):
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "pipeline_files", "status": "FAIL",
                "expected": len(self._mapped_flows), "actual": len(pipeline_files),
            })

        # Check 3: notebook files exist
        report.total_checks += 1
        notebooks_dir = self._output_dir / "notebooks"
        nb_files = list(notebooks_dir.glob("*.py")) if notebooks_dir.exists() else []
        if len(nb_files) >= len(self._mapped_flows):
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "notebook_files", "status": "FAIL",
                "expected": len(self._mapped_flows), "actual": len(nb_files),
            })

        # Check 4: pipeline JSON validity
        report.total_checks += 1
        invalid_json = 0
        for pf in pipeline_files:
            try:
                data = json.loads(pf.read_text(encoding="utf-8"))
                if "name" not in data:
                    invalid_json += 1
            except (json.JSONDecodeError, KeyError):
                invalid_json += 1
        if invalid_json == 0:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "pipeline_json_valid", "status": "FAIL",
                "invalid_count": invalid_json,
            })

        # Check 5: items requiring review (warning, not failure)
        report.total_checks += 1
        review_count = len(self._collect_review_items())
        if review_count == 0:
            report.passed += 1
        else:
            report.warnings += 1
            report.details.append({
                "check": "review_items", "status": "WARN",
                "review_count": review_count,
            })

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_review_items(self) -> list[dict[str, Any]]:
        """Collect all items needing manual review."""
        items: list[dict[str, Any]] = []

        for mf in self._mapped_flows:
            for ms in mf.review_required:
                items.append({
                    "type": "step_mapping",
                    "flow": mf.flow_name,
                    "step": ms.original_step.name,
                    "reason": ms.review_reason,
                })

        for tr in self._plsql_translations:
            if tr.requires_review:
                items.append({
                    "type": "plsql_translation",
                    "procedure": tr.procedure_name,
                    "confidence": tr.confidence,
                    "reason": "; ".join(tr.warnings),
                })

        for trigger in self._triggers:
            if trigger.requires_review:
                items.append({
                    "type": "schedule",
                    "trigger": trigger.name,
                    "reason": trigger.review_reason,
                })

        return items

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def mapped_flows(self) -> list[MappedDataFlow]:
        return self._mapped_flows

    @property
    def plsql_translations(self) -> list[TranslationResult]:
        return self._plsql_translations

    @property
    def triggers(self) -> list[FabricTrigger]:
        return self._triggers

    def generate_summary_report(self) -> str:
        """Generate a Markdown summary of the ETL migration."""
        lines = [
            "# ETL Migration Summary Report",
            "",
            f"**Generated at:** {datetime.now(timezone.utc).isoformat()}Z",
            f"**Agent:** {self.agent_name}",
            "",
            "## Data Flows",
            "",
            f"- **Total data flows mapped:** {len(self._mapped_flows)}",
            f"- **Total steps:** {sum(len(mf.mapped_steps) for mf in self._mapped_flows)}",
        ]

        # Per-flow summary
        if self._mapped_flows:
            lines.extend([
                "",
                "| Data Flow | Steps | Review Required | Warnings |",
                "|---|---|---|---|",
            ])
            for mf in self._mapped_flows:
                review = len(mf.review_required)
                lines.append(f"| {mf.flow_name} | {len(mf.mapped_steps)} | {review} | {len(mf.warnings)} |")

        # Step type distribution
        type_counts: dict[str, int] = {}
        for mf in self._mapped_flows:
            for ms in mf.mapped_steps:
                ft = ms.fabric_type
                type_counts[ft] = type_counts.get(ft, 0) + 1

        if type_counts:
            lines.extend([
                "",
                "## Fabric Activity Distribution",
                "",
                "| Fabric Type | Count |",
                "|---|---|",
            ])
            for ft, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| {ft} | {cnt} |")

        # PL/SQL translations
        if self._plsql_translations:
            lines.extend([
                "",
                "## PL/SQL Translations",
                "",
                f"- **Total procedures translated:** {len(self._plsql_translations)}",
                f"- **Rule-based:** {sum(1 for t in self._plsql_translations if t.method == 'rule-based')}",
                f"- **LLM-assisted:** {sum(1 for t in self._plsql_translations if t.method == 'llm')}",
                f"- **Manual review needed:** {sum(1 for t in self._plsql_translations if t.requires_review)}",
            ])

        # Schedules
        if self._triggers:
            lines.extend([
                "",
                "## Schedule Conversions",
                "",
                f"- **Total triggers generated:** {len(self._triggers)}",
                f"- **Review needed:** {sum(1 for t in self._triggers if t.requires_review)}",
            ])

        # Review queue
        review_items = self._collect_review_items()
        if review_items:
            lines.extend([
                "",
                "## ⚠️ Items Requiring Manual Review",
                "",
                "| Type | Item | Reason |",
                "|---|---|---|",
            ])
            for ri in review_items:
                name = ri.get("step") or ri.get("procedure") or ri.get("trigger", "")
                lines.append(f"| {ri['type']} | {name} | {ri['reason'][:80]} |")

        lines.append("")
        return "\n".join(lines)
