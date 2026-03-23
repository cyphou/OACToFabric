"""Validation & Testing Agent — Agent 07.

Orchestrates end-to-end validation across all migration layers:
  - Data reconciliation  (row counts, checksums, aggregates)
  - Semantic model  (DAX measures, relationships, hierarchies)
  - Reports  (visual counts, types, slicers, screenshots)
  - Security  (RLS row counts, OLS visibility, negative tests)

Lifecycle:
  1. Discover: collect migrated artefacts from inventory + mapping rules
  2. Plan: generate validation test cases per layer
  3. Execute: run validation checks (or output test plans for manual run)
  4. Validate: aggregate results, generate validation reports & defects
"""

from __future__ import annotations

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

from .data_reconciliation import (
    CheckStatus,
    ReconciliationReport,
    ReconciliationResult,
    compare_values,
    evaluate_result,
    generate_data_type_checks,
    generate_reconciliation_queries,
    render_reconciliation_report,
)
from .report_validator import (
    ReportCheckStatus,
    ReportValidationReport,
    evaluate_screenshot_diff,
    evaluate_visual_count,
    evaluate_visual_type,
    generate_drillthrough_tests,
    generate_slicer_tests,
    generate_visual_count_tests,
    generate_visual_type_tests,
    render_report_validation_report,
)
from .security_validator import (
    SecurityCheckStatus,
    SecurityValidationReport,
    evaluate_negative_test,
    evaluate_ols_visibility,
    evaluate_rls_row_count,
    generate_cross_role_tests,
    generate_negative_tests,
    generate_ols_visibility_tests,
    generate_rls_data_content_tests,
    generate_rls_row_count_tests,
    render_security_validation_report,
)
from .semantic_validator import (
    SemanticCheckStatus,
    SemanticValidationReport,
    evaluate_semantic_result,
    generate_filter_context_tests,
    generate_hierarchy_tests,
    generate_measure_tests,
    generate_relationship_tests,
    render_semantic_report,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation Agent
# ---------------------------------------------------------------------------


class ValidationAgent(MigrationAgent):
    """Agent 07 — Validation & Testing (end-to-end migration validation)."""

    def __init__(
        self,
        lakehouse_client: Any | None = None,
        output_dir: str | Path = "output/validation",
    ) -> None:
        super().__init__(
            agent_id="agent-07",
            agent_name="Validation & Testing Agent",
        )
        self._lakehouse = lakehouse_client
        self._output_dir = Path(output_dir)

        # Inventory cache
        self._table_inventory: list[dict[str, Any]] = []
        self._measures: list[dict[str, Any]] = []
        self._relationships: list[dict[str, Any]] = []
        self._hierarchies: list[dict[str, Any]] = []
        self._filters: list[dict[str, Any]] = []
        self._oac_reports: list[dict[str, Any]] = []
        self._pbi_reports: list[dict[str, Any]] = []
        self._rls_roles: list[dict[str, Any]] = []
        self._ols_roles: list[dict[str, Any]] = []
        self._type_mapping: dict[str, str] = {}

        # Results
        self._data_report: ReconciliationReport | None = None
        self._semantic_report: SemanticValidationReport | None = None
        self._report_report: ReportValidationReport | None = None
        self._security_report: SecurityValidationReport | None = None

    # ------------------------------------------------------------------
    # MigrationAgent interface
    # ------------------------------------------------------------------

    async def discover(self, scope: MigrationScope) -> Inventory:
        """Collect all migrated artefacts that need validation.

        Loads the migration inventory and mapping rules to determine
        what to validate.
        """
        items: list[InventoryItem] = []

        if self._lakehouse is not None:
            rows = self._lakehouse.read_inventory()
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
            logger.warning(
                "No Lakehouse client — using scope include_paths for discovery"
            )
            for path in scope.include_paths:
                name = path.strip("/").split("/")[-1]
                items.append(
                    InventoryItem(
                        id=f"val__{name.lower().replace(' ', '_')}",
                        asset_type=AssetType.PHYSICAL_TABLE,
                        source_path=path,
                        name=name,
                        metadata={},
                    )
                )

        inventory = Inventory(items=items)
        logger.info("Validation agent discovered %d items", inventory.count)
        return inventory

    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """Generate validation plan from inventory metadata.

        Extracts tables, measures, relationships, hierarchies, reports,
        and security roles from inventory items' metadata to build
        test-case generators.
        """
        self._extract_validation_inputs(inventory)

        plan = MigrationPlan(agent_id=self.agent_id, items=inventory.items)
        plan.estimated_duration_minutes = max(
            5,
            len(self._table_inventory) * 2
            + len(self._measures)
            + len(self._rls_roles) * 3,
        )
        logger.info(
            "Validation plan: %d tables, %d measures, %d relationships, "
            "%d reports, %d security roles",
            len(self._table_inventory),
            len(self._measures),
            len(self._relationships),
            len(self._oac_reports),
            len(self._rls_roles),
        )
        return plan

    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Generate all validation test cases and output test plans.

        In a real deployment, this would execute queries against Oracle
        and Fabric. Here we generate all test cases and write them as
        structured reports for execution.
        """
        result = MigrationResult(agent_id=self.agent_id, total=4)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        succeeded = 0

        try:
            # 1. Data reconciliation
            self._data_report = self._run_data_reconciliation()
            self._write_report(
                "data_reconciliation_report.md",
                render_reconciliation_report(self._data_report),
            )
            self._write_test_queries()
            succeeded += 1
        except Exception as e:
            logger.exception("Data reconciliation failed")
            result.errors.append({"layer": "data", "error": str(e)})

        try:
            # 2. Semantic validation
            self._semantic_report = self._run_semantic_validation()
            self._write_report(
                "semantic_validation_report.md",
                render_semantic_report(self._semantic_report),
            )
            succeeded += 1
        except Exception as e:
            logger.exception("Semantic validation failed")
            result.errors.append({"layer": "semantic", "error": str(e)})

        try:
            # 3. Report validation
            self._report_report = self._run_report_validation()
            self._write_report(
                "report_validation_report.md",
                render_report_validation_report(self._report_report),
            )
            succeeded += 1
        except Exception as e:
            logger.exception("Report validation failed")
            result.errors.append({"layer": "report", "error": str(e)})

        try:
            # 4. Security validation
            self._security_report = self._run_security_validation()
            self._write_report(
                "security_validation_report.md",
                render_security_validation_report(self._security_report),
            )
            succeeded += 1
        except Exception as e:
            logger.exception("Security validation failed")
            result.errors.append({"layer": "security", "error": str(e)})

        # Write combined summary
        self._write_report(
            "validation_summary.md",
            self.generate_summary_report(),
        )

        result.succeeded = succeeded
        result.failed = 4 - succeeded
        result.completed_at = datetime.now(timezone.utc)
        logger.info(
            "Validation agent: %d/4 layers completed",
            succeeded,
        )
        return result

    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Meta-validate: check that validation itself ran correctly."""
        report = ValidationReport(agent_id=self.agent_id)

        # Check 1: all layers executed
        report.total_checks += 1
        if result.succeeded == 4:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "all_layers_executed",
                "status": "FAIL",
                "succeeded": result.succeeded,
            })

        # Check 2: data report exists
        report.total_checks += 1
        data_file = self._output_dir / "data_reconciliation_report.md"
        if data_file.exists():
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "data_report_exists",
                "status": "FAIL",
            })

        # Check 3: semantic report exists
        report.total_checks += 1
        sem_file = self._output_dir / "semantic_validation_report.md"
        if sem_file.exists():
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "semantic_report_exists",
                "status": "FAIL",
            })

        # Check 4: report validation report exists
        report.total_checks += 1
        rpt_file = self._output_dir / "report_validation_report.md"
        if rpt_file.exists():
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "report_validation_report_exists",
                "status": "FAIL",
            })

        # Check 5: security report exists
        report.total_checks += 1
        sec_file = self._output_dir / "security_validation_report.md"
        if sec_file.exists():
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "security_report_exists",
                "status": "FAIL",
            })

        # Check 6: summary report exists
        report.total_checks += 1
        sum_file = self._output_dir / "validation_summary.md"
        if sum_file.exists():
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({
                "check": "summary_report_exists",
                "status": "FAIL",
            })

        return report

    # ------------------------------------------------------------------
    # Internal: extract validation inputs from inventory
    # ------------------------------------------------------------------

    def _extract_validation_inputs(self, inventory: Inventory) -> None:
        """Parse inventory items into validation input structures."""
        for item in inventory.items:
            meta = dict(item.metadata)

            if item.asset_type == AssetType.PHYSICAL_TABLE:
                self._table_inventory.append({
                    "source_name": meta.get("source_name", item.name),
                    "target_name": meta.get("target_name", item.name),
                    "columns": meta.get("columns", []),
                })

            elif item.asset_type == AssetType.DATA_MODEL:
                # Measures, relationships, hierarchies
                self._measures.extend(meta.get("measures", []))
                self._relationships.extend(meta.get("relationships", []))
                self._hierarchies.extend(meta.get("hierarchies", []))
                self._filters.extend(meta.get("filters", []))

            elif item.asset_type in (AssetType.ANALYSIS, AssetType.DASHBOARD):
                self._oac_reports.append(meta)

            elif item.asset_type == AssetType.SECURITY_ROLE:
                rls_data = {
                    "role_name": meta.get("name", item.name),
                    "test_user": meta.get("test_user", f"test_{item.name.lower()}"),
                    "table_permissions": meta.get("rls_filters", []),
                }
                if rls_data["table_permissions"]:
                    self._rls_roles.append(rls_data)

                ols_data = {
                    "role_name": meta.get("name", item.name),
                    "test_user": meta.get("test_user", f"test_{item.name.lower()}"),
                    "hidden_columns": [
                        p for p in meta.get("object_permissions", [])
                        if p.get("type") in ("hideColumn", "hideMeasure")
                    ],
                    "hidden_tables": [
                        p.get("table", "")
                        for p in meta.get("object_permissions", [])
                        if p.get("type") == "hideTable"
                    ],
                }
                if ols_data["hidden_columns"] or ols_data["hidden_tables"]:
                    self._ols_roles.append(ols_data)

    # ------------------------------------------------------------------
    # Internal: layer-specific validation runners
    # ------------------------------------------------------------------

    def _run_data_reconciliation(self) -> ReconciliationReport:
        """Generate data reconciliation test cases and report."""
        report = ReconciliationReport()
        queries = generate_reconciliation_queries(
            self._table_inventory, include_sample=True
        )
        type_checks = generate_data_type_checks(
            self._table_inventory, self._type_mapping
        )

        # In a real deployment, we'd execute queries here.
        # For now, record generated test cases as SKIP (pending execution).
        for q in queries:
            report.add(
                ReconciliationResult(
                    check_type=q.check_type,
                    asset_name=q.asset_name,
                    column_name=q.column_name,
                    status=CheckStatus.SKIP,
                    description=f"[Generated] {q.description}",
                )
            )

        for q in type_checks:
            report.add(
                ReconciliationResult(
                    check_type=q.check_type,
                    asset_name=q.asset_name,
                    column_name=q.column_name,
                    source_value=q.oracle_sql,
                    target_value=q.fabric_sql,
                    status=CheckStatus.SKIP,
                    description=f"[Generated] {q.description}",
                )
            )

        logger.info(
            "Data reconciliation: %d checks generated (pending execution)",
            report.total_checks,
        )
        return report

    def _run_semantic_validation(self) -> SemanticValidationReport:
        """Generate semantic model validation test cases."""
        report = SemanticValidationReport()

        all_tests = (
            generate_measure_tests(self._measures)
            + generate_relationship_tests(self._relationships)
            + generate_hierarchy_tests(self._hierarchies)
            + generate_filter_context_tests(self._filters)
        )

        from .semantic_validator import SemanticCheckResult, SemanticCheckStatus

        for tc in all_tests:
            report.add(
                SemanticCheckResult(
                    check_type=tc.check_type,
                    name=tc.name,
                    status=SemanticCheckStatus.SKIP,
                    description=f"[Generated] {tc.description}",
                )
            )

        logger.info(
            "Semantic validation: %d checks generated (pending execution)",
            report.total_checks,
        )
        return report

    def _run_report_validation(self) -> ReportValidationReport:
        """Generate report validation test cases."""
        report = ReportValidationReport()

        from .report_validator import ReportCheckResult, ReportCheckStatus

        visual_tests = generate_visual_count_tests(
            self._oac_reports, self._pbi_reports
        )
        slicer_tests = generate_slicer_tests([])  # Populated from inventory
        drillthrough_tests = generate_drillthrough_tests([])

        for tc in visual_tests + slicer_tests + drillthrough_tests:
            report.add(
                ReportCheckResult(
                    check_type=tc.check_type,
                    report_name=tc.report_name,
                    page_name=tc.page_name,
                    status=ReportCheckStatus.SKIP,
                    description=f"[Generated] {tc.description}",
                )
            )

        logger.info(
            "Report validation: %d checks generated (pending execution)",
            report.total_checks,
        )
        return report

    def _run_security_validation(self) -> SecurityValidationReport:
        """Generate security validation test cases."""
        report = SecurityValidationReport()

        from .security_validator import SecurityCheckResult, SecurityCheckStatus

        all_tests = (
            generate_rls_row_count_tests(self._rls_roles)
            + generate_rls_data_content_tests(self._rls_roles)
            + generate_ols_visibility_tests(self._ols_roles)
            + generate_cross_role_tests(self._rls_roles)
            + generate_negative_tests(self._rls_roles)
        )

        for tc in all_tests:
            report.add(
                SecurityCheckResult(
                    check_type=tc.check_type,
                    role_name=tc.role_name,
                    test_user=tc.test_user,
                    table_name=tc.table_name,
                    column_name=tc.column_name,
                    status=SecurityCheckStatus.SKIP,
                    description=f"[Generated] {tc.description}",
                )
            )

        logger.info(
            "Security validation: %d checks generated (pending execution)",
            report.total_checks,
        )
        return report

    # ------------------------------------------------------------------
    # Internal: file I/O
    # ------------------------------------------------------------------

    def _write_report(self, filename: str, content: str) -> None:
        (self._output_dir / filename).write_text(content, encoding="utf-8")
        logger.info("Wrote %s", filename)

    def _write_test_queries(self) -> None:
        """Write generated reconciliation queries as an executable SQL file."""
        queries = generate_reconciliation_queries(
            self._table_inventory, include_sample=False
        )
        lines = [
            "-- Data Reconciliation Queries",
            "-- Generated by Agent 07 — Validation Agent",
            f"-- Generated at: {datetime.now(timezone.utc).isoformat()}",
            "",
        ]
        for i, q in enumerate(queries, 1):
            lines.extend([
                f"-- Check {i}: {q.description}",
                f"-- Oracle:",
                f"--   {q.oracle_sql}",
                f"-- Fabric:",
                f"    {q.fabric_sql}",
                "",
            ])
        self._write_report("reconciliation_queries.sql", "\n".join(lines))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def generate_summary_report(self) -> str:
        """Generate a combined validation summary across all layers."""
        lines = [
            "# Validation Summary",
            "",
            f"**Generated at:** {datetime.now(timezone.utc).isoformat()}",
            f"**Agent:** {self.agent_name}",
            "",
            "## Overview",
            "",
        ]

        layers: list[tuple[str, Any]] = [
            ("Data Reconciliation", self._data_report),
            ("Semantic Model", self._semantic_report),
            ("Report", self._report_report),
            ("Security", self._security_report),
        ]

        lines.extend([
            "| Layer | Total | Passed | Failed | Warnings | Skipped | Pass Rate |",
            "|---|---|---|---|---|---|---|",
        ])

        total_all = passed_all = failed_all = 0

        for name, rpt in layers:
            if rpt is None:
                lines.append(f"| {name} | — | — | — | — | — | — |")
                continue

            t = rpt.total_checks
            p = rpt.passed
            f_count = rpt.failed
            w = rpt.warnings
            s = getattr(rpt, "skipped", 0)
            rate = f"{rpt.pass_rate:.1f}%"

            lines.append(
                f"| {name} | {t} | {p} | {f_count} | {w} | {s} | {rate} |"
            )
            total_all += t
            passed_all += p
            failed_all += f_count

        lines.append("")
        overall_rate = (
            f"{(passed_all / total_all * 100):.1f}%"
            if total_all > 0
            else "N/A"
        )
        lines.extend([
            f"**Overall:** {passed_all}/{total_all} checks passed "
            f"({overall_rate}), {failed_all} failed",
            "",
        ])

        # Generated artefacts
        lines.extend([
            "## Generated Artefacts",
            "",
            "| File | Description |",
            "|---|---|",
            "| data_reconciliation_report.md | Data layer validation |",
            "| reconciliation_queries.sql | Executable reconciliation SQL |",
            "| semantic_validation_report.md | Semantic model validation |",
            "| report_validation_report.md | Report / dashboard validation |",
            "| security_validation_report.md | Security (RLS/OLS) validation |",
            "| validation_summary.md | This summary |",
            "",
        ])

        return "\n".join(lines)
