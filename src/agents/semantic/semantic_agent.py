"""Semantic Model Migration Agent — Agent 04.

Converts OAC RPD logical/presentation model into a Power BI Semantic Model
expressed in TMDL format.

Lifecycle:
  1. Discover: load logical tables, joins, subject areas from Lakehouse inventory
  2. Plan: build SemanticModelIR, translate expressions, map hierarchies
  3. Execute: generate TMDL files, write to disk
  4. Validate: check file completeness, DAX validity, review items
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

from .expression_translator import DAXTranslation, translate_expression
from .hierarchy_mapper import TMDLHierarchy, map_all_hierarchies
from .rpd_model_parser import (
    LogicalTable,
    SemanticModelIR,
    SubjectArea,
    parse_inventory_to_ir,
)
from .tmdl_generator import (
    TMDLGenerationResult,
    generate_tmdl,
    write_tmdl_to_disk,
)

logger = logging.getLogger(__name__)


class SemanticModelAgent(MigrationAgent):
    """Agent 04 — Semantic Model Migration (OAC RPD → TMDL)."""

    def __init__(
        self,
        lakehouse_client: Any | None = None,
        llm_client: Any | None = None,
        lakehouse_name: str = "MyLakehouse",
        output_dir: str | Path = "output/semantic_model",
    ) -> None:
        super().__init__(agent_id="agent-04", agent_name="Semantic Model Migration Agent")
        self._lakehouse = lakehouse_client
        self._llm = llm_client
        self._lakehouse_name = lakehouse_name
        self._output_dir = Path(output_dir)

        # Internal state
        self._ir: SemanticModelIR | None = None
        self._tmdl_result: TMDLGenerationResult | None = None
        self._table_mapping: dict[str, str] = {}

    # ------------------------------------------------------------------
    # MigrationAgent interface
    # ------------------------------------------------------------------

    async def discover(self, scope: MigrationScope) -> Inventory:
        """Load logical tables, joins, and subject areas from inventory."""
        items: list[InventoryItem] = []

        if self._lakehouse is not None:
            for asset_type_val in (
                AssetType.LOGICAL_TABLE.value,
                AssetType.SUBJECT_AREA.value,
                AssetType.PRESENTATION_TABLE.value,
            ):
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
            logger.warning("No Lakehouse client — using scope include_paths for discovery")
            for path in scope.include_paths:
                name = path.strip("/").split("/")[-1]
                items.append(
                    InventoryItem(
                        id=f"logicalTable__{name.lower()}",
                        asset_type=AssetType.LOGICAL_TABLE,
                        source_path=path,
                        name=name,
                        metadata={},
                    )
                )

        # Apply scope exclusions
        if scope.exclude_paths:
            items = [
                i for i in items
                if not any(i.source_path.startswith(ex) for ex in scope.exclude_paths)
            ]

        inventory = Inventory(items=items)
        logger.info(
            "Semantic model agent discovered %d items (%d logical tables, %d subject areas)",
            inventory.count,
            len(inventory.by_type(AssetType.LOGICAL_TABLE)),
            len(inventory.by_type(AssetType.SUBJECT_AREA)),
        )
        return inventory

    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """Build SemanticModelIR from inventory and prepare for TMDL generation."""
        plan = MigrationPlan(agent_id=self.agent_id, items=inventory.items)

        # Build the intermediate representation
        self._ir = parse_inventory_to_ir(inventory)
        self._ir.model_name = "SemanticModel"

        # Load table mapping from Lakehouse (OAC table → Fabric table)
        if self._lakehouse is not None:
            try:
                mapping_rows = self._lakehouse.read_inventory(asset_type="mapping")
                for row in mapping_rows:
                    self._table_mapping[row.get("source_name", "")] = row.get("target_name", "")
            except Exception:
                logger.warning("Could not load table mapping from Lakehouse")

        plan.estimated_duration_minutes = max(1, len(self._ir.tables) * 2)

        logger.info(
            "Plan: %d tables, %d joins, %d subject areas to convert",
            len(self._ir.tables), len(self._ir.joins), len(self._ir.subject_areas),
        )
        return plan

    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Generate TMDL files and write to disk."""
        result = MigrationResult(agent_id=self.agent_id, total=len(plan.items))

        if self._ir is None:
            result.failed = len(plan.items)
            result.errors.append({"error": "No SemanticModelIR available — run plan() first"})
            result.completed_at = datetime.now(timezone.utc)
            return result

        try:
            # Generate TMDL
            self._tmdl_result = generate_tmdl(
                ir=self._ir,
                table_mapping=self._table_mapping,
                lakehouse_name=self._lakehouse_name,
                llm_client=self._llm,
            )

            # Write to disk
            self._output_dir.mkdir(parents=True, exist_ok=True)
            write_tmdl_to_disk(self._tmdl_result, self._output_dir)

            # Write translation log
            if self._tmdl_result.translation_log:
                log_path = self._output_dir / "translation_log.json"
                log_data = [
                    {
                        "table": tx.table_name,
                        "column": tx.column_name,
                        "original": tx.original_expression,
                        "dax": tx.dax_expression,
                        "method": tx.method,
                        "confidence": tx.confidence,
                        "requires_review": tx.requires_review,
                    }
                    for tx in self._tmdl_result.translation_log
                ]
                log_path.write_text(json.dumps(log_data, indent=2), encoding="utf-8")

            # Write review queue
            if self._tmdl_result.review_items:
                review_path = self._output_dir / "review_queue.json"
                review_path.write_text(
                    json.dumps(self._tmdl_result.review_items, indent=2),
                    encoding="utf-8",
                )

            # Write summary report
            summary_path = self._output_dir / "semantic_model_summary.md"
            summary_path.write_text(self.generate_summary_report(), encoding="utf-8")

            result.succeeded = len(plan.items)
            result.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Semantic model agent wrote %d TMDL files to %s",
                len(self._tmdl_result.files), self._output_dir,
            )

        except Exception as exc:
            logger.exception("Semantic model agent execution failed")
            result.failed = len(plan.items)
            result.errors.append({"error": str(exc)})
            result.completed_at = datetime.now(timezone.utc)

        return result

    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Validate generated TMDL artefacts."""
        report = ValidationReport(agent_id=self.agent_id)

        # Check 1: execution succeeded
        report.total_checks += 1
        if result.failed == 0:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "execution_success", "status": "FAIL"})

        # Check 2: model.tmdl exists
        report.total_checks += 1
        model_file = self._output_dir / "model.tmdl"
        if model_file.exists():
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "model_tmdl_exists", "status": "FAIL"})

        # Check 3: table TMDL files exist
        report.total_checks += 1
        tables_dir = self._output_dir / "definition" / "tables"
        tmdl_files = list(tables_dir.glob("*.tmdl")) if tables_dir.exists() else []
        expected = len(self._ir.tables) if self._ir else 0
        if len(tmdl_files) >= expected:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "table_files",
                "status": "FAIL",
                "expected": expected,
                "actual": len(tmdl_files),
            })

        # Check 4: relationships file
        report.total_checks += 1
        rel_file = self._output_dir / "definition" / "relationships.tmdl"
        if self._ir and self._ir.joins:
            if rel_file.exists():
                report.passed += 1
            else:
                report.failed += 1
                report.details.append({"check": "relationships_file", "status": "FAIL"})
        else:
            report.passed += 1  # No joins expected

        # Check 5: TMDL files non-empty
        report.total_checks += 1
        empty_files = [f for f in tmdl_files if f.stat().st_size == 0]
        if not empty_files:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "non_empty_tmdl",
                "status": "FAIL",
                "empty_files": [str(f.name) for f in empty_files],
            })

        # Check 6: review items (warning, not failure)
        report.total_checks += 1
        review_count = len(self._tmdl_result.review_items) if self._tmdl_result else 0
        if review_count == 0:
            report.passed += 1
        else:
            report.warnings += 1
            report.details.append({
                "check": "review_items",
                "status": "WARN",
                "count": review_count,
            })

        return report

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def ir(self) -> SemanticModelIR | None:
        return self._ir

    @property
    def tmdl_result(self) -> TMDLGenerationResult | None:
        return self._tmdl_result

    def generate_summary_report(self) -> str:
        """Generate a Markdown summary report."""
        lines = [
            "# Semantic Model Migration Summary Report",
            "",
            f"**Generated at:** {datetime.now(timezone.utc).isoformat()}Z",
            f"**Agent:** {self.agent_name}",
            "",
        ]

        if self._ir:
            lines.extend([
                "## Model Overview",
                "",
                f"- **Model name:** {self._ir.model_name}",
                f"- **Tables:** {len(self._ir.tables)}",
                f"- **Relationships:** {len(self._ir.joins)}",
                f"- **Subject areas / perspectives:** {len(self._ir.subject_areas)}",
                "",
            ])

            # Per-table summary
            if self._ir.tables:
                lines.extend([
                    "## Tables",
                    "",
                    "| Table | Columns | Measures | Calc Columns | Hierarchies | Date Table |",
                    "|---|---|---|---|---|---|",
                ])
                for t in self._ir.tables:
                    n_hier = len(t.hierarchies)
                    lines.append(
                        f"| {t.name} | {len(t.direct_columns)} | {len(t.measures)} | "
                        f"{len(t.calculated_columns)} | {n_hier} | {'✓' if t.is_date_table else ''} |"
                    )
                lines.append("")

        if self._tmdl_result:
            # Translation stats
            log = self._tmdl_result.translation_log
            if log:
                rule_based = sum(1 for tx in log if tx.method == "rule-based")
                llm_based = sum(1 for tx in log if tx.method == "llm")
                manual = sum(1 for tx in log if tx.method == "manual")
                avg_conf = sum(tx.confidence for tx in log) / len(log) if log else 0

                lines.extend([
                    "## Expression Translations",
                    "",
                    f"- **Total expressions translated:** {len(log)}",
                    f"- **Rule-based:** {rule_based}",
                    f"- **LLM-assisted:** {llm_based}",
                    f"- **Manual review needed:** {manual}",
                    f"- **Average confidence:** {avg_conf:.0%}",
                    "",
                ])

            # Review items
            review = self._tmdl_result.review_items
            if review:
                lines.extend([
                    "## ⚠️ Items Requiring Manual Review",
                    "",
                    "| Type | Table | Item | Reason |",
                    "|---|---|---|---|",
                ])
                for ri in review:
                    item_name = ri.get("column") or ri.get("hierarchy") or ""
                    lines.append(
                        f"| {ri['type']} | {ri.get('table', '')} | "
                        f"{item_name} | {ri.get('reason', '')[:80]} |"
                    )
                lines.append("")

            # Files generated
            lines.extend([
                "## Generated Files",
                "",
                f"- **Total TMDL files:** {len(self._tmdl_result.files)}",
            ])
            for path in sorted(self._tmdl_result.files.keys()):
                lines.append(f"  - `{path}`")
            lines.append("")

        return "\n".join(lines)
