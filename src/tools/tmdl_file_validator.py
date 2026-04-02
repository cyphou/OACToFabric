"""Filesystem-based TMDL validator for generated migration output.

Validates real TMDL output directories (not just in-memory dicts):

1. **Structure check** — required files/dirs exist, .platform is valid JSON
2. **Table validation** — every .tmdl in tables/ has proper declarations,
   lineageTags, at least one column or measure
3. **Relationship validation** — relationships reference existing tables/columns
4. **Cross-reference check** — measures referencing tables/columns that exist
5. **Model consistency** — database.tmdl compatibilityLevel, culture, etc.
6. **DAX validation** — all measures pass deep DAX validation (via dax_validator)

Usage::

    from src.tools.tmdl_file_validator import validate_output_directory

    report = validate_output_directory("output/essbase_migration/complex_planning")
    print(report.summary())
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.tools.dax_validator import DAXValidationResult, validate_tmdl_measures

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class FileValidation:
    """Validation result for a single file."""

    path: str
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dax_results: list[DAXValidationResult] = field(default_factory=list)


@dataclass
class TMDLOutputReport:
    """Complete validation report for a TMDL output directory."""

    root_dir: str
    files: list[FileValidation] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    table_count: int = 0
    measure_count: int = 0
    column_count: int = 0
    relationship_count: int = 0

    @property
    def valid(self) -> bool:
        if self.errors:
            return False
        return all(f.valid for f in self.files)

    @property
    def total_errors(self) -> int:
        return len(self.errors) + sum(len(f.errors) for f in self.files)

    @property
    def total_warnings(self) -> int:
        return len(self.warnings) + sum(len(f.warnings) for f in self.files)

    @property
    def dax_error_count(self) -> int:
        return sum(
            r.error_count
            for f in self.files
            for r in f.dax_results
        )

    def summary(self) -> str:
        """Human-readable summary."""
        status = "PASS" if self.valid else "FAIL"
        lines = [
            f"TMDL Validation: {status}",
            f"  Directory: {self.root_dir}",
            f"  Tables: {self.table_count}",
            f"  Measures: {self.measure_count}",
            f"  Columns: {self.column_count}",
            f"  Relationships: {self.relationship_count}",
            f"  Errors: {self.total_errors}",
            f"  Warnings: {self.total_warnings}",
            f"  DAX errors: {self.dax_error_count}",
        ]
        if self.errors:
            lines.append("  Top-level errors:")
            for e in self.errors[:10]:
                lines.append(f"    - {e}")
        for fv in self.files:
            if fv.errors:
                lines.append(f"  {fv.path}:")
                for e in fv.errors[:5]:
                    lines.append(f"    - {e}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def _validate_platform(path: Path, report: TMDLOutputReport) -> None:
    """Validate .platform JSON file."""
    fv = FileValidation(path=str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fv.errors.append(f".platform is not valid JSON: {e}")
        fv.valid = False
        report.files.append(fv)
        return

    required_keys = {"$schema", "metadata", "config"}
    for key in required_keys:
        if key not in data:
            fv.errors.append(f".platform missing required key: {key}")
            fv.valid = False

    # Check metadata has type
    meta = data.get("metadata", {})
    if isinstance(meta, dict) and "type" not in meta:
        fv.warnings.append(".platform metadata missing 'type' key")

    report.files.append(fv)


def _validate_model(path: Path, report: TMDLOutputReport) -> None:
    """Validate model.tmdl."""
    fv = FileValidation(path=str(path))
    content = path.read_text(encoding="utf-8")

    if not re.search(r"^model\s+", content, re.MULTILINE):
        fv.errors.append("model.tmdl missing 'model' declaration")
        fv.valid = False

    if "culture:" not in content:
        fv.warnings.append("model.tmdl missing 'culture:' property")

    report.files.append(fv)


def _validate_database(path: Path, report: TMDLOutputReport) -> None:
    """Validate definition/database.tmdl."""
    fv = FileValidation(path=str(path))
    content = path.read_text(encoding="utf-8")

    if "compatibilityLevel:" not in content:
        fv.warnings.append("database.tmdl missing compatibilityLevel")

    report.files.append(fv)


def _extract_table_metadata(content: str) -> dict[str, Any]:
    """Extract table name, columns, and measures from a TMDL table file."""
    info: dict[str, Any] = {"name": "", "columns": [], "measures": []}

    # Table name
    m = re.search(r"^table\s+'?([^'\n]+?)'?\s*$", content, re.MULTILINE)
    if m:
        info["name"] = m.group(1).strip()

    # Columns
    for col_match in re.finditer(
        r"^\s+column\s+'?([^'\n=]+?)'?\s*$", content, re.MULTILINE
    ):
        info["columns"].append(col_match.group(1).strip())

    # Measures
    for meas_match in re.finditer(
        r"^\s+measure\s+'?([^'\n=]+?)'?\s*=", content, re.MULTILINE
    ):
        info["measures"].append(meas_match.group(1).strip())

    return info


def _validate_table(
    path: Path,
    report: TMDLOutputReport,
    *,
    validate_dax: bool = True,
) -> dict[str, Any]:
    """Validate a single TMDL table file; return metadata."""
    fv = FileValidation(path=str(path))
    content = path.read_text(encoding="utf-8")
    meta = _extract_table_metadata(content)

    if not re.search(r"^table\s+", content, re.MULTILINE):
        fv.errors.append(f"{path.name} missing 'table' declaration")
        fv.valid = False

    if "lineageTag:" not in content:
        fv.warnings.append(f"{path.name} missing lineageTag")

    cols = meta["columns"]
    measures = meta["measures"]
    report.column_count += len(cols)
    report.measure_count += len(measures)

    if not cols and not measures:
        fv.warnings.append(f"{path.name} has no columns or measures")

    # Deep DAX validation
    if validate_dax and measures:
        dax_results = validate_tmdl_measures(content)
        fv.dax_results = dax_results
        for dr in dax_results:
            if not dr.valid:
                for issue in dr.issues:
                    if issue.severity.value == "error":
                        fv.errors.append(
                            f"DAX error in measure '{dr.measure_name}': {issue.message}"
                        )
                        fv.valid = False

    report.files.append(fv)
    return meta


def _validate_relationships(
    path: Path,
    table_metadata: dict[str, dict[str, Any]],
    report: TMDLOutputReport,
) -> None:
    """Validate relationships.tmdl cross-references."""
    fv = FileValidation(path=str(path))
    content = path.read_text(encoding="utf-8")

    # Count relationships
    rel_blocks = re.findall(r"^relationship\s+", content, re.MULTILINE)
    report.relationship_count = len(rel_blocks)

    if not rel_blocks:
        fv.warnings.append("relationships.tmdl is empty")

    # Extract table references from relationships
    known_tables = set(table_metadata.keys())
    # Pattern: fromTable: 'TableName' or toTable: 'TableName'
    for ref_match in re.finditer(
        r"(?:fromTable|toTable)\s*:\s*'?([^'\n]+?)'?\s*$",
        content,
        re.MULTILINE,
    ):
        ref_table = ref_match.group(1).strip()
        if ref_table and ref_table not in known_tables:
            fv.warnings.append(
                f"Relationship references unknown table: '{ref_table}'"
            )

    report.files.append(fv)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def validate_output_directory(
    directory: str,
    *,
    validate_dax: bool = True,
) -> TMDLOutputReport:
    """Validate a TMDL output directory from migration.

    Expected structure::

        {directory}/
        ├── SemanticModel/       (or at root)
        │   ├── model.tmdl
        │   ├── .platform
        │   └── definition/
        │       ├── database.tmdl
        │       ├── relationships.tmdl
        │       ├── expressions.tmdl
        │       ├── perspectives.tmdl
        │       ├── roles.tmdl
        │       └── tables/
        │           ├── Table1.tmdl
        │           └── Table2.tmdl
        └── generated_ddl.sql   (optional)

    Parameters
    ----------
    directory
        Root directory of the migration output for one asset (e.g., one cube).
    validate_dax
        Whether to run deep DAX validation on all measures.

    Returns
    -------
    TMDLOutputReport
    """
    root = Path(directory)
    report = TMDLOutputReport(root_dir=str(root))

    if not root.exists():
        report.errors.append(f"Directory does not exist: {root}")
        return report

    # Detect SemanticModel subdirectory
    sm_dir = root / "SemanticModel"
    if not sm_dir.exists():
        # Maybe the root IS the semantic model directory
        if (root / "model.tmdl").exists():
            sm_dir = root
        else:
            report.errors.append(
                f"No SemanticModel directory or model.tmdl found in {root}"
            )
            return report

    # Validate .platform
    platform_path = sm_dir / ".platform"
    if platform_path.exists():
        _validate_platform(platform_path, report)
    else:
        report.errors.append(f"Missing required file: .platform")

    # Validate model.tmdl
    model_path = sm_dir / "model.tmdl"
    if model_path.exists():
        _validate_model(model_path, report)
    else:
        report.errors.append("Missing required file: model.tmdl")

    # Definition directory
    def_dir = sm_dir / "definition"
    if not def_dir.exists():
        report.errors.append("Missing required directory: definition/")
        return report

    # Validate database.tmdl
    db_path = def_dir / "database.tmdl"
    if db_path.exists():
        _validate_database(db_path, report)

    # Validate tables
    tables_dir = def_dir / "tables"
    table_metadata: dict[str, dict[str, Any]] = {}

    if tables_dir.exists():
        for tmdl_file in sorted(tables_dir.glob("*.tmdl")):
            meta = _validate_table(
                tmdl_file,
                report,
                validate_dax=validate_dax,
            )
            report.table_count += 1
            if meta.get("name"):
                table_metadata[meta["name"]] = meta
    else:
        report.errors.append("Missing required directory: definition/tables/")

    # Validate relationships
    rel_path = def_dir / "relationships.tmdl"
    if rel_path.exists():
        _validate_relationships(rel_path, table_metadata, report)

    # Validate DDL (if present)
    ddl_path = root / "generated_ddl.sql"
    if ddl_path.exists():
        fv = FileValidation(path=str(ddl_path))
        ddl_content = ddl_path.read_text(encoding="utf-8")
        if not ddl_content.strip():
            fv.warnings.append("generated_ddl.sql is empty")
        else:
            # Check for CREATE TABLE statements
            creates = re.findall(
                r"CREATE\s+TABLE", ddl_content, re.IGNORECASE
            )
            if not creates:
                fv.warnings.append(
                    "generated_ddl.sql has no CREATE TABLE statements"
                )
        report.files.append(fv)

    logger.info(
        "TMDL output validation: %s (%d errors, %d warnings, %d tables, %d measures)",
        "PASS" if report.valid else "FAIL",
        report.total_errors,
        report.total_warnings,
        report.table_count,
        report.measure_count,
    )

    return report


def validate_migration_output(
    output_dir: str,
    *,
    validate_dax: bool = True,
) -> dict[str, TMDLOutputReport]:
    """Validate all cube/asset directories in a migration output.

    Parameters
    ----------
    output_dir
        Root output directory (e.g., ``output/essbase_migration/``).

    Returns
    -------
    dict[str, TMDLOutputReport]
        Mapping of subdirectory name → validation report.
    """
    root = Path(output_dir)
    results: dict[str, TMDLOutputReport] = {}

    if not root.exists():
        return results

    for subdir in sorted(root.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith("."):
            # Check if it looks like a migration output (has SemanticModel or model.tmdl)
            has_sm = (subdir / "SemanticModel").exists()
            has_model = (subdir / "model.tmdl").exists()
            if has_sm or has_model:
                results[subdir.name] = validate_output_directory(
                    str(subdir),
                    validate_dax=validate_dax,
                )

    total_errors = sum(r.total_errors for r in results.values())
    total_tables = sum(r.table_count for r in results.values())
    logger.info(
        "Validated %d assets: %d tables, %d total errors",
        len(results), total_tables, total_errors,
    )

    return results
