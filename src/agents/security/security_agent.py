"""Security & Governance Migration Agent — Agent 06.

Migrates OAC security model (application roles, row-level security,
object-level permissions) to Power BI RLS / OLS and Fabric workspace
role assignments.

Lifecycle:
  1. Discover: load security roles, init blocks from Lakehouse inventory
  2. Plan: map roles, identify lookup tables needed
  3. Execute: generate TMDL roles, OLS, lookup DDL, assignment scripts
  4. Validate: check generated artefacts for completeness
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

from .ols_generator import (
    OLSGenerationResult,
    OLSRoleDefinition,
    convert_all_object_permissions,
    generate_security_matrix,
    render_ols_tmdl,
)
from .rls_converter import (
    SecurityLookupTable,
    analyse_init_blocks,
    generate_lookup_table_ddl,
    generate_rls_test_plan,
    render_roles_tmdl,
    render_test_plan_markdown,
)
from .role_mapper import (
    FabricRoleAssignment,
    OACRole,
    RLSRoleDefinition,
    RoleMappingResult,
    generate_role_assignment_script,
    map_roles,
    parse_oac_role,
)

logger = logging.getLogger(__name__)


class SecurityMigrationAgent(MigrationAgent):
    """Agent 06 — Security & Governance Migration (OAC → Fabric/PBI)."""

    def __init__(
        self,
        lakehouse_client: Any | None = None,
        table_mapping: dict[str, str] | None = None,
        workspace_id: str = "<WORKSPACE_ID>",
        output_dir: str | Path = "output/security",
    ) -> None:
        super().__init__(
            agent_id="agent-06",
            agent_name="Security & Governance Migration Agent",
        )
        self._lakehouse = lakehouse_client
        self._table_mapping = table_mapping or {}
        self._workspace_id = workspace_id
        self._output_dir = Path(output_dir)

        # Internal state
        self._oac_roles: list[OACRole] = []
        self._role_mapping: RoleMappingResult | None = None
        self._ols_result: OLSGenerationResult | None = None
        self._lookup_tables: list[SecurityLookupTable] = []
        self._init_blocks: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # MigrationAgent interface
    # ------------------------------------------------------------------

    async def discover(self, scope: MigrationScope) -> Inventory:
        """Load security roles and init blocks from inventory."""
        items: list[InventoryItem] = []

        if self._lakehouse is not None:
            for asset_type_val in (
                AssetType.SECURITY_ROLE.value,
                AssetType.INIT_BLOCK.value,
            ):
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
            logger.warning(
                "No Lakehouse client — using scope include_paths for discovery"
            )
            for path in scope.include_paths:
                name = path.strip("/").split("/")[-1]
                items.append(
                    InventoryItem(
                        id=f"security__{name.lower().replace(' ', '_')}",
                        asset_type=AssetType.SECURITY_ROLE,
                        source_path=path,
                        name=name,
                        metadata={},
                    )
                )

        # Apply scope exclusions
        if scope.exclude_paths:
            items = [
                i
                for i in items
                if not any(i.source_path.startswith(ex) for ex in scope.exclude_paths)
            ]

        inventory = Inventory(items=items)
        logger.info(
            "Security agent discovered %d items (%d roles, %d init blocks)",
            inventory.count,
            len(inventory.by_type(AssetType.SECURITY_ROLE)),
            len(inventory.by_type(AssetType.INIT_BLOCK)),
        )
        return inventory

    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """Build migration plan for security artefacts."""
        # Parse OAC roles from inventory
        self._oac_roles = []
        self._init_blocks = []

        for item in inventory.items:
            if item.asset_type == AssetType.SECURITY_ROLE:
                role_meta = dict(item.metadata)
                role_meta.setdefault("name", item.name)
                self._oac_roles.append(parse_oac_role(role_meta))
            elif item.asset_type == AssetType.INIT_BLOCK:
                self._init_blocks.append(dict(item.metadata))

        plan = MigrationPlan(agent_id=self.agent_id, items=inventory.items)
        plan.estimated_duration_minutes = max(1, len(self._oac_roles) * 2)
        logger.info(
            "Plan: %d roles, %d init blocks to process",
            len(self._oac_roles),
            len(self._init_blocks),
        )
        return plan

    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Generate security artefacts (TMDL roles, OLS, scripts)."""
        result = MigrationResult(agent_id=self.agent_id, total=len(plan.items))
        self._output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Analyse init blocks → lookup tables
            self._lookup_tables = analyse_init_blocks(self._init_blocks)

            # 2. Map OAC roles → workspace + RLS roles
            self._role_mapping = map_roles(self._oac_roles)

            # 3. Convert OLS permissions
            roles_with_perms = [
                {"name": r.name, "object_permissions": r.object_permissions}
                for r in self._oac_roles
                if r.object_permissions
            ]
            self._ols_result = convert_all_object_permissions(
                roles_with_perms, self._table_mapping
            )

            # 4. Write artefacts
            self._write_rls_tmdl()
            self._write_ols_tmdl()
            self._write_lookup_ddl()
            self._write_role_assignment_script()
            self._write_test_plan()
            self._write_security_matrix()

            # Summary
            summary_path = self._output_dir / "security_migration_summary.md"
            summary_path.write_text(
                self.generate_summary_report(), encoding="utf-8"
            )

            result.succeeded = len(plan.items)
            result.completed_at = datetime.now(timezone.utc)

        except Exception as exc:
            logger.exception("Security migration failed")
            result.failed = len(plan.items)
            result.errors.append({"error": str(exc)})
            result.completed_at = datetime.now(timezone.utc)

        logger.info(
            "Security agent: %d succeeded, %d failed",
            result.succeeded,
            result.failed,
        )
        return result

    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Validate generated security artefacts."""
        report = ValidationReport(agent_id=self.agent_id)

        # Check 1: execution succeeded
        report.total_checks += 1
        if result.failed == 0:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "execution_success", "status": "FAIL"})

        # Check 2: roles.tmdl file exists
        report.total_checks += 1
        roles_file = self._output_dir / "roles.tmdl"
        if roles_file.exists() and roles_file.stat().st_size > 10:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "roles_tmdl_exists", "status": "FAIL"})

        # Check 3: workspace assignment script exists
        report.total_checks += 1
        script_file = self._output_dir / "workspace_role_assignments.ps1"
        if script_file.exists():
            report.passed += 1
        else:
            report.failed += 1
            report.details.append(
                {"check": "assignment_script_exists", "status": "FAIL"}
            )

        # Check 4: all OAC roles mapped
        report.total_checks += 1
        if self._role_mapping and len(
            self._role_mapping.workspace_assignments
        ) == len(self._oac_roles):
            report.passed += 1
        else:
            report.failed += 1
            report.details.append(
                {"check": "all_roles_mapped", "status": "FAIL"}
            )

        # Check 5: review items (warning, not failure)
        report.total_checks += 1
        review_count = 0
        if self._role_mapping:
            review_count += len(self._role_mapping.review_items)
        if self._ols_result:
            review_count += len(self._ols_result.review_items)
        if review_count == 0:
            report.passed += 1
        else:
            report.warnings += 1
            report.details.append({
                "check": "review_items",
                "status": "WARN",
                "count": review_count,
            })

        # Check 6: test plan generated
        report.total_checks += 1
        test_plan_file = self._output_dir / "rls_test_plan.md"
        if test_plan_file.exists():
            report.passed += 1
        else:
            report.failed += 1
            report.details.append(
                {"check": "test_plan_exists", "status": "FAIL"}
            )

        return report

    # ------------------------------------------------------------------
    # Internal file writers
    # ------------------------------------------------------------------

    def _write_rls_tmdl(self) -> None:
        """Write roles.tmdl with RLS role definitions."""
        if self._role_mapping is None:
            return
        content = render_roles_tmdl(
            self._role_mapping.rls_roles, self._lookup_tables
        )
        (self._output_dir / "roles.tmdl").write_text(content, encoding="utf-8")
        logger.info("Wrote roles.tmdl with %d RLS roles", len(self._role_mapping.rls_roles))

    def _write_ols_tmdl(self) -> None:
        """Write ols.tmdl with Object-Level Security definitions."""
        if self._ols_result is None:
            return
        content = render_ols_tmdl(self._ols_result.ols_roles)
        (self._output_dir / "ols.tmdl").write_text(content, encoding="utf-8")
        logger.info("Wrote ols.tmdl with %d OLS roles", len(self._ols_result.ols_roles))

    def _write_lookup_ddl(self) -> None:
        """Write security lookup table DDL."""
        for lt in self._lookup_tables:
            ddl = generate_lookup_table_ddl(lt)
            (self._output_dir / f"{lt.table_name}.sql").write_text(
                ddl, encoding="utf-8"
            )
            logger.info("Wrote DDL for %s", lt.table_name)

    def _write_role_assignment_script(self) -> None:
        """Write PowerShell workspace role assignment script."""
        if self._role_mapping is None:
            return
        script = generate_role_assignment_script(
            self._role_mapping.workspace_assignments,
            workspace_id=self._workspace_id,
        )
        (self._output_dir / "workspace_role_assignments.ps1").write_text(
            script, encoding="utf-8"
        )

    def _write_test_plan(self) -> None:
        """Write RLS validation test plan."""
        if self._role_mapping is None:
            return
        test_cases = generate_rls_test_plan(self._role_mapping.rls_roles)
        md = render_test_plan_markdown(test_cases)
        (self._output_dir / "rls_test_plan.md").write_text(md, encoding="utf-8")

    def _write_security_matrix(self) -> None:
        """Write OLS security matrix."""
        if self._ols_result is None:
            return
        md = generate_security_matrix(self._ols_result.ols_roles)
        (self._output_dir / "security_matrix.md").write_text(md, encoding="utf-8")

    # ------------------------------------------------------------------
    # Summary report
    # ------------------------------------------------------------------

    def generate_summary_report(self) -> str:
        """Generate a Markdown summary of the security migration."""
        lines = [
            "# Security Migration Summary",
            "",
            f"**Generated at:** {datetime.now(timezone.utc).isoformat()}",
            f"**Agent:** {self.agent_name}",
            "",
        ]

        rls_count = len(self._role_mapping.rls_roles) if self._role_mapping else 0
        ws_count = (
            len(self._role_mapping.workspace_assignments)
            if self._role_mapping
            else 0
        )
        ols_count = len(self._ols_result.ols_roles) if self._ols_result else 0
        lookup_count = len(self._lookup_tables)

        lines.extend([
            "## Overview",
            "",
            f"- **OAC roles processed:** {len(self._oac_roles)}",
            f"- **Workspace role assignments:** {ws_count}",
            f"- **RLS roles generated:** {rls_count}",
            f"- **OLS roles generated:** {ols_count}",
            f"- **Security lookup tables:** {lookup_count}",
            "",
        ])

        # Workspace roles
        if self._role_mapping and self._role_mapping.workspace_assignments:
            lines.extend([
                "## Workspace Role Assignments",
                "",
                "| OAC Role | Fabric Role | AAD Group | Users |",
                "|---|---|---|---|",
            ])
            for a in self._role_mapping.workspace_assignments:
                users = ", ".join(a.users[:3])
                if len(a.users) > 3:
                    users += f" (+{len(a.users) - 3} more)"
                lines.append(
                    f"| {a.source_oac_role} | {a.workspace_role.value} | "
                    f"{a.aad_group} | {users} |"
                )
            lines.append("")

        # RLS roles
        if self._role_mapping and self._role_mapping.rls_roles:
            lines.extend([
                "## RLS Roles",
                "",
                "| Role | Tables | Review Required |",
                "|---|---|---|",
            ])
            for r in self._role_mapping.rls_roles:
                tables = ", ".join(tp.table_name for tp in r.table_permissions)
                lines.append(
                    f"| {r.role_name} | {tables} | "
                    f"{'Yes' if r.requires_review else 'No'} |"
                )
            lines.append("")

        # OLS roles
        if self._ols_result and self._ols_result.ols_roles:
            lines.extend([
                "## OLS Roles",
                "",
                "| Role | Hidden Columns | Hidden Tables | Review |",
                "|---|---|---|---|",
            ])
            for r in self._ols_result.ols_roles:
                lines.append(
                    f"| {r.role_name} | {len(r.column_permissions)} | "
                    f"{len(r.table_permissions)} | "
                    f"{'Yes' if r.requires_review else 'No'} |"
                )
            lines.append("")

        # Warnings
        all_warnings: list[str] = []
        if self._role_mapping:
            all_warnings.extend(self._role_mapping.warnings)
        if self._ols_result:
            all_warnings.extend(self._ols_result.warnings)
        if all_warnings:
            lines.extend([
                "## Warnings",
                "",
            ])
            for w in all_warnings:
                lines.append(f"- {w}")
            lines.append("")

        return "\n".join(lines)
