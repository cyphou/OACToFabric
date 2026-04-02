"""Fabric deployment dry-run validator.

Simulates a full deployment without writing to any target system:

1. **Artifact validation** — checks that all files exist, are well-formed,
   and pass structural validation before deployment.
2. **Dependency checking** — verifies artifact dependencies (e.g., semantic
   model references tables that will be created by DDL).
3. **Naming validation** — ensures all artifact names comply with Fabric
   naming rules (length, characters, uniqueness).
4. **Capacity estimation** — estimates storage and compute requirements.
5. **Deployment manifest** — produces a detailed manifest of what *would*
   be deployed, in what order, with estimated impact.

Usage::

    from src.tools.fabric_dry_run import DeploymentDryRun

    dry_run = DeploymentDryRun(output_dir="output/essbase_migration")
    manifest = dry_run.validate()
    print(manifest.summary())
    if manifest.has_blockers:
        for b in manifest.blockers:
            print(f"  BLOCKER: {b}")
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fabric naming rules
# ---------------------------------------------------------------------------

# Max lengths for Fabric item names
_MAX_NAME_LENGTHS: dict[str, int] = {
    "lakehouse": 256,
    "warehouse": 256,
    "pipeline": 256,
    "notebook": 256,
    "semantic_model": 256,
    "report": 256,
    "dataflow": 256,
    "table": 128,
    "column": 128,
}

# Invalid characters for Fabric item names
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Reserved names
_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


def validate_fabric_name(
    name: str,
    item_type: str = "table",
) -> list[str]:
    """Validate a name against Fabric naming rules. Returns list of errors."""
    errors: list[str] = []

    if not name:
        errors.append("Name is empty")
        return errors

    if not name.strip():
        errors.append("Name is whitespace only")
        return errors

    max_len = _MAX_NAME_LENGTHS.get(item_type, 256)
    if len(name) > max_len:
        errors.append(f"Name '{name}' exceeds max length {max_len} (got {len(name)})")

    if _INVALID_CHARS.search(name):
        errors.append(f"Name '{name}' contains invalid characters")

    if name.upper() in _RESERVED_NAMES:
        errors.append(f"Name '{name}' is a reserved name")

    if name.startswith(" ") or name.endswith(" "):
        errors.append(f"Name '{name}' has leading/trailing spaces")

    if name.endswith("."):
        errors.append(f"Name '{name}' ends with a period")

    return errors


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class DeploymentAction(str):
    """Type of deployment action."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class ArtifactManifestEntry:
    """A single artifact that would be deployed."""

    artifact_type: str  # table, semantic_model, report, pipeline, etc.
    artifact_name: str
    action: str = "CREATE"
    source_path: str = ""
    dependencies: list[str] = field(default_factory=list)
    estimated_size_kb: int = 0
    naming_errors: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.naming_errors and not self.validation_errors


@dataclass
class DeploymentManifest:
    """Complete deployment dry-run manifest."""

    output_dir: str
    artifacts: list[ArtifactManifestEntry] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    deployment_order: list[str] = field(default_factory=list)
    estimated_total_size_kb: int = 0
    estimated_ru_cost: float = 0.0

    @property
    def valid(self) -> bool:
        if self.blockers:
            return False
        if not self.artifacts:
            return True
        return all(a.valid for a in self.artifacts)

    @property
    def has_blockers(self) -> bool:
        return bool(self.blockers)

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)

    @property
    def valid_count(self) -> int:
        return sum(1 for a in self.artifacts if a.valid)

    @property
    def invalid_count(self) -> int:
        return sum(1 for a in self.artifacts if not a.valid)

    def summary(self) -> str:
        """Human-readable deployment summary."""
        status = "BLOCKED" if self.has_blockers else "READY"
        lines = [
            f"Deployment Dry-Run: {status}",
            f"  Output directory: {self.output_dir}",
            f"  Total artifacts: {self.artifact_count}",
            f"  Valid: {self.valid_count}",
            f"  Invalid: {self.invalid_count}",
            f"  Estimated size: {self.estimated_total_size_kb:,} KB",
            "",
        ]

        if self.blockers:
            lines.append("BLOCKERS:")
            for b in self.blockers:
                lines.append(f"  ❌ {b}")
            lines.append("")

        if self.warnings:
            lines.append("WARNINGS:")
            for w in self.warnings[:10]:
                lines.append(f"  ⚠️ {w}")
            lines.append("")

        lines.append("DEPLOYMENT ORDER:")
        for i, step in enumerate(self.deployment_order, 1):
            lines.append(f"  {i}. {step}")
        lines.append("")

        lines.append("ARTIFACTS:")
        for a in self.artifacts:
            icon = "✅" if a.valid else "❌"
            lines.append(f"  {icon} [{a.artifact_type}] {a.artifact_name} ({a.action})")
            for e in a.naming_errors:
                lines.append(f"      Naming: {e}")
            for e in a.validation_errors:
                lines.append(f"      Error: {e}")
            for w in a.validation_warnings:
                lines.append(f"      Warn: {w}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dry-run validator
# ---------------------------------------------------------------------------


class DeploymentDryRun:
    """Simulate Fabric deployment and validate all artifacts.

    Parameters
    ----------
    output_dir
        Root directory of migration output (e.g., ``output/essbase_migration``).
    workspace_name
        Target Fabric workspace name (for naming validation).
    """

    def __init__(
        self,
        output_dir: str,
        *,
        workspace_name: str = "MigrationWorkspace",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.workspace_name = workspace_name

    def validate(self) -> DeploymentManifest:
        """Run full deployment dry-run validation.

        Returns
        -------
        DeploymentManifest
            Complete manifest of what would be deployed.
        """
        manifest = DeploymentManifest(output_dir=str(self.output_dir))

        if not self.output_dir.exists():
            manifest.blockers.append(f"Output directory does not exist: {self.output_dir}")
            return manifest

        # Scan for deployable assets
        all_tables: set[str] = set()
        all_semantic_models: list[str] = []

        for subdir in sorted(self.output_dir.iterdir()):
            if not subdir.is_dir() or subdir.name.startswith("."):
                continue

            # Check for SemanticModel
            sm_dir = subdir / "SemanticModel"
            if sm_dir.exists():
                self._validate_semantic_model(subdir, sm_dir, manifest)
                all_semantic_models.append(subdir.name)

                # Extract table names from TMDL
                tables_dir = sm_dir / "definition" / "tables"
                if tables_dir.exists():
                    for tmdl_file in tables_dir.glob("*.tmdl"):
                        table_name = tmdl_file.stem
                        all_tables.add(table_name)

            # Check for DDL
            ddl_path = subdir / "generated_ddl.sql"
            if ddl_path.exists():
                self._validate_ddl(subdir, ddl_path, manifest, all_tables)

        # Build deployment order
        manifest.deployment_order = self._compute_deployment_order(manifest)

        # Check cross-dependencies
        self._check_cross_dependencies(manifest, all_tables)

        # Estimate sizes
        manifest.estimated_total_size_kb = sum(
            a.estimated_size_kb for a in manifest.artifacts
        )

        logger.info(
            "Dry-run: %d artifacts, %d blockers, %d warnings",
            manifest.artifact_count,
            len(manifest.blockers),
            len(manifest.warnings),
        )

        return manifest

    def _validate_semantic_model(
        self,
        asset_dir: Path,
        sm_dir: Path,
        manifest: DeploymentManifest,
    ) -> None:
        """Validate a semantic model for deployment."""
        entry = ArtifactManifestEntry(
            artifact_type="semantic_model",
            artifact_name=asset_dir.name,
            source_path=str(sm_dir),
        )

        # Naming validation
        entry.naming_errors = validate_fabric_name(asset_dir.name, "semantic_model")

        # Required files
        model_path = sm_dir / "model.tmdl"
        platform_path = sm_dir / ".platform"

        if not model_path.exists():
            entry.validation_errors.append("Missing model.tmdl")
        else:
            content = model_path.read_text(encoding="utf-8")
            if not re.search(r"^model\s+", content, re.MULTILINE):
                entry.validation_errors.append("model.tmdl missing 'model' declaration")
            entry.estimated_size_kb += len(content) // 1024 + 1

        if not platform_path.exists():
            entry.validation_errors.append("Missing .platform")
        else:
            try:
                platform_data = json.loads(platform_path.read_text(encoding="utf-8"))
                for key in ("$schema", "metadata", "config"):
                    if key not in platform_data:
                        entry.validation_errors.append(f".platform missing key: {key}")
            except json.JSONDecodeError:
                entry.validation_errors.append(".platform is not valid JSON")

        # Tables directory
        tables_dir = sm_dir / "definition" / "tables"
        if tables_dir.exists():
            table_names: set[str] = set()
            for tmdl_file in tables_dir.glob("*.tmdl"):
                content = tmdl_file.read_text(encoding="utf-8")
                entry.estimated_size_kb += len(content) // 1024 + 1

                # Extract table name and check for duplicates
                m = re.search(r"^table\s+'?([^'\n]+)", content, re.MULTILINE)
                if m:
                    tname = m.group(1).strip()
                    if tname in table_names:
                        entry.validation_errors.append(f"Duplicate table name: '{tname}'")
                    table_names.add(tname)

                    # Validate table name
                    name_errors = validate_fabric_name(tname, "table")
                    for ne in name_errors:
                        entry.validation_warnings.append(f"Table '{tname}': {ne}")
                else:
                    entry.validation_warnings.append(f"{tmdl_file.name} missing table declaration")

            entry.dependencies = [f"table:{n}" for n in sorted(table_names)]
        else:
            entry.validation_warnings.append("No tables directory found")

        if entry.validation_errors:
            manifest.blockers.append(
                f"Semantic model '{asset_dir.name}' has validation errors"
            )

        manifest.artifacts.append(entry)

    def _validate_ddl(
        self,
        asset_dir: Path,
        ddl_path: Path,
        manifest: DeploymentManifest,
        expected_tables: set[str],
    ) -> None:
        """Validate DDL file for deployment."""
        content = ddl_path.read_text(encoding="utf-8")

        # Extract CREATE TABLE names
        creates = re.findall(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)",
            content,
            re.IGNORECASE,
        )

        for table_name in creates:
            clean_name = table_name.strip("`'\"")
            entry = ArtifactManifestEntry(
                artifact_type="lakehouse_table",
                artifact_name=clean_name,
                source_path=str(ddl_path),
                estimated_size_kb=len(content) // max(len(creates), 1) // 1024 + 1,
            )
            entry.naming_errors = validate_fabric_name(clean_name, "table")
            manifest.artifacts.append(entry)

        if not creates:
            manifest.warnings.append(
                f"DDL file {ddl_path.name} in {asset_dir.name} has no CREATE TABLE statements"
            )

    def _compute_deployment_order(
        self,
        manifest: DeploymentManifest,
    ) -> list[str]:
        """Compute deployment order based on artifact types."""
        order: list[str] = []

        # 1. Lakehouse tables first (DDL)
        tables = [a for a in manifest.artifacts if a.artifact_type == "lakehouse_table"]
        if tables:
            order.append(f"1. Create {len(tables)} Lakehouse tables (DDL)")

        # 2. Data loading (pipelines/notebooks)
        pipelines = [a for a in manifest.artifacts if a.artifact_type == "pipeline"]
        if pipelines:
            order.append(f"2. Deploy {len(pipelines)} data pipelines")

        # 3. Semantic models
        models = [a for a in manifest.artifacts if a.artifact_type == "semantic_model"]
        if models:
            order.append(f"3. Deploy {len(models)} semantic model(s)")

        # 4. Reports
        reports = [a for a in manifest.artifacts if a.artifact_type == "report"]
        if reports:
            order.append(f"4. Deploy {len(reports)} report(s)")

        if not order:
            order.append("No deployable artifacts found")

        return order

    def _check_cross_dependencies(
        self,
        manifest: DeploymentManifest,
        available_tables: set[str],
    ) -> None:
        """Check that semantic model table references match DDL tables."""
        ddl_tables = {
            a.artifact_name
            for a in manifest.artifacts
            if a.artifact_type == "lakehouse_table"
        }

        for artifact in manifest.artifacts:
            if artifact.artifact_type != "semantic_model":
                continue

            for dep in artifact.dependencies:
                if dep.startswith("table:"):
                    table_name = dep[len("table:"):]
                    # Check if there's a corresponding DDL table
                    # (case-insensitive match)
                    ddl_match = any(
                        t.lower() == table_name.lower()
                        for t in ddl_tables
                    )
                    if not ddl_match and ddl_tables:
                        manifest.warnings.append(
                            f"Semantic model '{artifact.artifact_name}' references "
                            f"table '{table_name}' not found in DDL"
                        )


# ---------------------------------------------------------------------------
# JSON manifest output
# ---------------------------------------------------------------------------


def export_manifest_json(manifest: DeploymentManifest) -> str:
    """Export deployment manifest as JSON."""
    data = {
        "output_dir": manifest.output_dir,
        "status": "BLOCKED" if manifest.has_blockers else "READY",
        "artifact_count": manifest.artifact_count,
        "valid": manifest.valid_count,
        "invalid": manifest.invalid_count,
        "estimated_size_kb": manifest.estimated_total_size_kb,
        "blockers": manifest.blockers,
        "warnings": manifest.warnings,
        "deployment_order": manifest.deployment_order,
        "artifacts": [
            {
                "type": a.artifact_type,
                "name": a.artifact_name,
                "action": a.action,
                "source": a.source_path,
                "valid": a.valid,
                "naming_errors": a.naming_errors,
                "validation_errors": a.validation_errors,
                "warnings": a.validation_warnings,
                "estimated_size_kb": a.estimated_size_kb,
            }
            for a in manifest.artifacts
        ],
    }
    return json.dumps(data, indent=2)
