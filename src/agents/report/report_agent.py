"""Report & Dashboard Migration Agent — Agent 05.

Converts OAC Analyses and Dashboards into Power BI Reports in PBIR format,
preserving layouts, visuals, filters, prompts, and interactivity.

Lifecycle:
  1. Discover: load analyses/dashboards from Lakehouse inventory
  2. Plan: resolve semantic model, map visual types, compute layouts
  3. Execute: generate PBIR files, write to disk
  4. Validate: check file completeness, visual coverage
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

from .layout_engine import (
    OACPageLayout,
    OACSection,
    PBIPage,
    VisualPosition,
    compute_page_layouts,
)
from .pbir_generator import (
    NavigationAction,
    PBIRGenerationResult,
    VisualSpec,
    generate_pbir,
    map_oac_action,
    write_pbir_to_disk,
    _visual_id,
)
from .prompt_converter import (
    ParameterConfig,
    SlicerConfig,
    convert_all_prompts,
)
from .visual_mapper import (
    OACChartType,
    PBIVisualType,
    VisualFieldMapping,
    map_oac_columns_to_roles,
    map_visual_type,
    translate_conditional_format,
    translate_sort,
)

logger = logging.getLogger(__name__)


class ReportMigrationAgent(MigrationAgent):
    """Agent 05 — Report & Dashboard Migration (OAC → PBIR)."""

    def __init__(
        self,
        lakehouse_client: Any | None = None,
        semantic_model_id: str = "",
        semantic_model_name: str = "SemanticModel",
        table_mapping: dict[str, str] | None = None,
        output_dir: str | Path = "output/reports",
    ) -> None:
        super().__init__(agent_id="agent-05", agent_name="Report & Dashboard Migration Agent")
        self._lakehouse = lakehouse_client
        self._semantic_model_id = semantic_model_id
        self._semantic_model_name = semantic_model_name
        self._table_mapping = table_mapping or {}
        self._output_dir = Path(output_dir)

        # Internal state
        self._pbir_results: list[PBIRGenerationResult] = []
        self._reports_generated: list[str] = []

    # ------------------------------------------------------------------
    # MigrationAgent interface
    # ------------------------------------------------------------------

    async def discover(self, scope: MigrationScope) -> Inventory:
        """Load analyses and dashboards from inventory."""
        items: list[InventoryItem] = []

        if self._lakehouse is not None:
            for asset_type_val in (AssetType.ANALYSIS.value, AssetType.DASHBOARD.value):
                rows = self._lakehouse.read_inventory(asset_type=asset_type_val)
                for row in rows:
                    items.append(
                        InventoryItem(
                            id=row["id"],
                            asset_type=AssetType(row["asset_type"]),
                            source_path=row["source_path"],
                            name=row["name"],
                            metadata=row.get("metadata", {}),
                        )
                    )
        else:
            logger.warning("No Lakehouse client — using scope include_paths for discovery")
            for path in scope.include_paths:
                name = path.strip("/").split("/")[-1]
                items.append(
                    InventoryItem(
                        id=f"report__{name.lower().replace(' ', '_')}",
                        asset_type=AssetType.ANALYSIS,
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
            "Report agent discovered %d items (%d analyses, %d dashboards)",
            inventory.count,
            len(inventory.by_type(AssetType.ANALYSIS)),
            len(inventory.by_type(AssetType.DASHBOARD)),
        )
        return inventory

    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """Build migration plan for reports."""
        plan = MigrationPlan(agent_id=self.agent_id, items=inventory.items)
        plan.estimated_duration_minutes = max(1, inventory.count * 3)
        logger.info("Plan: %d reports to convert", inventory.count)
        return plan

    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Generate PBIR files for each analysis/dashboard."""
        result = MigrationResult(agent_id=self.agent_id, total=len(plan.items))
        self._output_dir.mkdir(parents=True, exist_ok=True)

        for item in plan.items:
            try:
                pbir_result = self._convert_report(item)
                self._pbir_results.append(pbir_result)

                # Write to disk
                report_dir = self._output_dir / _safe_name(item.name)
                write_pbir_to_disk(pbir_result, report_dir)
                self._reports_generated.append(item.name)
                result.succeeded += 1

            except Exception as exc:
                logger.exception("Failed to convert report '%s'", item.name)
                result.failed += 1
                result.errors.append({
                    "report": item.name,
                    "error": str(exc),
                })

        result.completed_at = datetime.now(timezone.utc)

        # Write summary
        summary_path = self._output_dir / "report_migration_summary.md"
        summary_path.write_text(self.generate_summary_report(), encoding="utf-8")

        # Write review queue
        all_review = []
        for pr in self._pbir_results:
            all_review.extend(pr.review_items)
        if all_review:
            review_path = self._output_dir / "review_queue.json"
            review_path.write_text(json.dumps(all_review, indent=2), encoding="utf-8")

        logger.info(
            "Report agent: %d succeeded, %d failed out of %d",
            result.succeeded, result.failed, result.total,
        )
        return result

    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Validate generated PBIR artefacts."""
        report = ValidationReport(agent_id=self.agent_id)

        # Check 1: execution succeeded
        report.total_checks += 1
        if result.failed == 0:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "execution_success", "status": "FAIL"})

        # Check 2: reports generated
        report.total_checks += 1
        if len(self._reports_generated) == result.total:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "reports_generated",
                "status": "FAIL",
                "expected": result.total,
                "actual": len(self._reports_generated),
            })

        # Check 3: PBIR files on disk
        report.total_checks += 1
        missing: list[str] = []
        for name in self._reports_generated:
            rdir = self._output_dir / _safe_name(name)
            if not (rdir / "definition.pbir").exists():
                missing.append(name)
        if not missing:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "pbir_files_exist",
                "status": "FAIL",
                "missing": missing,
            })

        # Check 4: each report has at least one page+visual
        report.total_checks += 1
        empty_reports: list[str] = []
        for name in self._reports_generated:
            rdir = self._output_dir / _safe_name(name)
            pages_dir = rdir / "pages"
            if not pages_dir.exists() or not list(pages_dir.iterdir()):
                empty_reports.append(name)
        if not empty_reports:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "pages_exist",
                "status": "FAIL",
                "empty_reports": empty_reports,
            })

        # Check 5: review items count (warning)
        report.total_checks += 1
        review_count = sum(len(pr.review_items) for pr in self._pbir_results)
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
    # Internal conversion
    # ------------------------------------------------------------------

    def _convert_report(self, item: InventoryItem) -> PBIRGenerationResult:
        """Convert a single OAC analysis/dashboard to PBIR."""
        meta = item.metadata
        report_name = item.name

        # --- Parse pages ---
        pages_meta = meta.get("pages", [])
        if not pages_meta:
            # Single-page analysis — wrap in one page
            pages_meta = [{"name": report_name, "views": meta.get("views", [])}]

        all_pbi_pages: list[PBIPage] = []
        all_visual_specs: dict[str, VisualSpec] = {}

        for page_idx, page_meta in enumerate(pages_meta):
            oac_page = self._parse_oac_page(page_meta, page_idx)
            pbi_pages = compute_page_layouts(oac_page)

            for pbi_page in pbi_pages:
                all_pbi_pages.append(pbi_page)

                # Generate visual specs for each positioned visual
                for vpos in pbi_page.visuals:
                    view_meta = self._find_view_meta(page_meta, vpos.visual_name)
                    if view_meta:
                        spec = self._build_visual_spec(vpos, view_meta)
                        all_visual_specs[vpos.visual_name] = spec

        # --- Parse prompts ---
        prompts_meta = meta.get("prompts", [])
        slicer_results = convert_all_prompts(prompts_meta, self._table_mapping)
        slicers = [s for s in slicer_results if isinstance(s, SlicerConfig)]

        # --- Parse actions ---
        actions_meta = meta.get("actions", [])
        actions = [map_oac_action(a) for a in actions_meta]

        # --- Generate PBIR ---
        return generate_pbir(
            report_name=report_name,
            pages=all_pbi_pages,
            visual_specs=all_visual_specs,
            slicers=slicers,
            actions=actions,
            semantic_model_id=self._semantic_model_id,
            semantic_model_name=self._semantic_model_name,
        )

    def _parse_oac_page(self, page_meta: dict[str, Any], page_idx: int) -> OACPageLayout:
        """Parse an OAC page metadata dict to OACPageLayout."""
        sections_meta = page_meta.get("sections", [])
        sections: list[OACSection] = []

        for sm in sections_meta:
            views = sm.get("views", [])
            sections.append(
                OACSection(
                    name=sm.get("name", ""),
                    relative_x=sm.get("x", 0.0),
                    relative_y=sm.get("y", 0.0),
                    relative_width=sm.get("width", 1.0),
                    relative_height=sm.get("height", 1.0),
                    views=views,
                )
            )

        return OACPageLayout(
            page_name=page_meta.get("name", f"Page {page_idx + 1}"),
            page_index=page_idx,
            sections=sections,
            views=page_meta.get("views", []),
        )

    def _find_view_meta(
        self, page_meta: dict[str, Any], visual_name: str,
    ) -> dict[str, Any] | None:
        """Find view metadata by name within a page."""
        # Check top-level views
        for v in page_meta.get("views", []):
            if v.get("name") == visual_name:
                return v
        # Check section views
        for section in page_meta.get("sections", []):
            for v in section.get("views", []):
                if v.get("name") == visual_name:
                    return v
        return None

    def _build_visual_spec(
        self, vpos: VisualPosition, view_meta: dict[str, Any],
    ) -> VisualSpec:
        """Build a VisualSpec from view metadata and position."""
        chart_type = view_meta.get("type", "table")
        pbi_type, type_warnings = map_visual_type(chart_type)

        # Map columns
        columns = view_meta.get("columns", [])
        field_mappings = map_oac_columns_to_roles(columns, pbi_type, self._table_mapping)

        # Conditional formatting
        cond_formats = []
        for cf_meta in view_meta.get("conditionalFormats", []):
            cf = translate_conditional_format(cf_meta)
            if cf:
                cond_formats.append(cf)

        # Sorting
        sort_configs = []
        for sort_meta in view_meta.get("sorts", []):
            sc = translate_sort(sort_meta)
            if sc:
                sort_configs.append(sc)

        return VisualSpec(
            name=_visual_id(),
            visual_type=pbi_type,
            position=vpos,
            field_mappings=field_mappings,
            title=view_meta.get("title", view_meta.get("name", "")),
            conditional_formats=cond_formats,
            sort_configs=sort_configs,
            warnings=type_warnings,
        )

    # ------------------------------------------------------------------
    # Summary report
    # ------------------------------------------------------------------

    def generate_summary_report(self) -> str:
        """Generate a Markdown summary of the report migration."""
        lines = [
            "# Report Migration Summary",
            "",
            f"**Generated at:** {datetime.now(timezone.utc).isoformat()}",
            f"**Agent:** {self.agent_name}",
            "",
        ]

        total_pages = sum(pr.page_count for pr in self._pbir_results)
        total_visuals = sum(pr.visual_count for pr in self._pbir_results)
        total_slicers = sum(pr.slicer_count for pr in self._pbir_results)
        total_files = sum(len(pr.files) for pr in self._pbir_results)

        lines.extend([
            "## Overview",
            "",
            f"- **Reports migrated:** {len(self._reports_generated)}",
            f"- **Total pages:** {total_pages}",
            f"- **Total visuals:** {total_visuals}",
            f"- **Total slicers:** {total_slicers}",
            f"- **Total files generated:** {total_files}",
            "",
        ])

        # Per-report summary
        if self._reports_generated:
            lines.extend([
                "## Reports",
                "",
                "| Report | Pages | Visuals | Slicers | Files |",
                "|---|---|---|---|---|",
            ])
            for i, name in enumerate(self._reports_generated):
                if i < len(self._pbir_results):
                    pr = self._pbir_results[i]
                    lines.append(
                        f"| {name} | {pr.page_count} | {pr.visual_count} | "
                        f"{pr.slicer_count} | {len(pr.files)} |"
                    )
            lines.append("")

        # Review items
        all_review = []
        for pr in self._pbir_results:
            all_review.extend(pr.review_items)
        if all_review:
            lines.extend([
                "## Items Requiring Review",
                "",
                "| Type | Page | Item | Warning |",
                "|---|---|---|---|",
            ])
            for ri in all_review:
                item_name = ri.get("visual") or ri.get("slicer") or ""
                lines.append(
                    f"| {ri.get('type', '')} | {ri.get('page', '')} | "
                    f"{item_name} | {ri.get('warning', '')[:80]} |"
                )
            lines.append("")

        return "\n".join(lines)


def _safe_name(name: str) -> str:
    """Sanitise a report name for filesystem use."""
    return name.replace(" ", "_").replace("/", "_").replace("\\", "_")
