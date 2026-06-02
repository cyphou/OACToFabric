#!/usr/bin/env python3
"""Generate a focused migration execution pack for priority tracks.

Tracks covered:
1. Essbase migration (semantic + writeback)
2. OAC reports on top of Exadata
3. OAC reports on top of Essbase

Outputs markdown runbooks and a command book in one folder.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _track_essbase_core(bso_prep_dir: str) -> str:
    return "\n".join(
        [
            "# Track 1 — Essbase Migration (Core)",
            "",
            "## Goal",
            "",
            "Migrate Essbase cubes to Fabric semantic + writeback stack with validation and cutover.",
            "",
            "## Scope",
            "",
            "- Outline parsing, calc translation, TMDL generation",
            "- BSO writeback backend for Longview/Smart View replacement path",
            "- UAT and cutover readiness",
            "",
            "## Execute",
            "",
            "1. Run Essbase connector/bridge tests:",
            "",
            "```powershell",
            "pytest tests/test_essbase_connector.py tests/test_essbase_semantic_bridge.py -q",
            "```",
            "",
            "2. Generate BSO writeback package:",
            "",
            "```powershell",
            "py -3 scripts/prepare_bso_writeback.py --outline examples/essbase_samples/longview_budget_writeback.xml --enable-allocation --enable-currency",
            "```",
            "",
            "3. Review artifacts:",
            "",
            f"- {bso_prep_dir}/warehouse_ddl.sql",
            f"- {bso_prep_dir}/stored_procedures.sql",
            f"- {bso_prep_dir}/calc_notebook.py",
            f"- {bso_prep_dir}/tds_connection.json",
            f"- {bso_prep_dir}/cutover_checklist.md",
            "",
            "## Exit Criteria",
            "",
            "- UAT notebook passes",
            "- Writeback round-trip passes",
            "- Cutover checklist approved",
        ]
    )


def _track_oac_exadata() -> str:
    return "\n".join(
        [
            "# Track 2 — OAC Reports on Exadata",
            "",
            "## Goal",
            "",
            "Migrate OAC reporting and semantic layer fed by Exadata to Fabric Warehouse + Power BI.",
            "",
            "## Scope",
            "",
            "- OAC inventory and report extraction",
            "- Oracle/Exadata schema and ETL migration",
            "- OAC report to PBIR conversion",
            "",
            "## Execute",
            "",
            "1. Discovery and planning:",
            "",
            "```powershell",
            "oac-migrate discover --config config/migration.toml --output-dir output/focus_oac_exadata",
            "oac-migrate plan --config config/migration.toml --output-dir output/focus_oac_exadata",
            "```",
            "",
            "2. Run schema and ETL migration phases:",
            "",
            "```powershell",
            "python -m src.cli.main migrate --agents 02-schema --config config/migration.toml",
            "python -m src.cli.main migrate --agents 03-etl --config config/migration.toml",
            "```",
            "",
            "3. Run semantic and report phases:",
            "",
            "```powershell",
            "python -m src.cli.main migrate --agents 04-semantic --config config/migration.toml",
            "python -m src.cli.main migrate --agents 05-report --config config/migration.toml",
            "```",
            "",
            "4. Validate:",
            "",
            "```powershell",
            "oac-migrate validate --config config/migration.toml --output-dir output/focus_oac_exadata",
            "```",
            "",
            "## Exit Criteria",
            "",
            "- Exadata-backed subject areas present in semantic model",
            "- Priority OAC dashboards converted and validated",
            "- Validation report has no critical mismatches",
        ]
    )


def _track_oac_on_essbase() -> str:
    return "\n".join(
        [
            "# Track 3 — OAC on Top of Essbase",
            "",
            "## Goal",
            "",
            "Migrate OAC reports that depend on Essbase cubes while preserving planning/writeback capabilities.",
            "",
            "## Scope",
            "",
            "- Essbase cube semantic migration",
            "- OAC report conversion referencing migrated semantics",
            "- Longview/BSO writeback backend replacement",
            "",
            "## Execute",
            "",
            "1. Migrate Essbase core first (Track 1).",
            "",
            "2. Run OAC report migration phases:",
            "",
            "```powershell",
            "python -m src.cli.main migrate --agents 05-report --config config/migration.toml",
            "python -m src.cli.main migrate --agents 06-security --config config/migration.toml",
            "```",
            "",
            "3. Validate parity against OAC on Essbase:",
            "",
            "```powershell",
            "python -m src.cli.main migrate --agents 07-validation --config config/migration.toml",
            "```",
            "",
            "## Key Controls",
            "",
            "- Track low-confidence Essbase calc translations (<0.7)",
            "- Prioritize Scenario/Period/Entity totals parity",
            "- Validate RLS equivalence for Essbase filters",
            "",
            "## Exit Criteria",
            "",
            "- OAC dashboards over Essbase have validated Power BI equivalents",
            "- Security roles and totals validated",
            "- Writeback path operational in Fabric",
        ]
    )


def _command_book() -> str:
    return "\n".join(
        [
            "# Focus Command Book",
            "",
            "## Full Test Gate",
            "",
            "```powershell",
            "pytest tests/ --tb=short -q",
            "```",
            "",
            "## Essbase + Writeback",
            "",
            "```powershell",
            "pytest tests/test_essbase_connector.py tests/test_essbase_semantic_bridge.py tests/test_writeback_generator.py tests/test_longview_migration.py -q",
            "py -3 scripts/prepare_bso_writeback.py --outline examples/essbase_samples/longview_budget_writeback.xml --enable-allocation --enable-currency",
            "```",
            "",
            "## OAC Discovery/Plan",
            "",
            "```powershell",
            "oac-migrate discover --config config/migration.toml --output-dir output/focus_run",
            "oac-migrate plan --config config/migration.toml --output-dir output/focus_run",
            "```",
            "",
            "## OAC Migration Phases",
            "",
            "```powershell",
            "python -m src.cli.main migrate --agents 02-schema --config config/migration.toml",
            "python -m src.cli.main migrate --agents 03-etl --config config/migration.toml",
            "python -m src.cli.main migrate --agents 04-semantic --config config/migration.toml",
            "python -m src.cli.main migrate --agents 05-report --config config/migration.toml",
            "python -m src.cli.main migrate --agents 06-security --config config/migration.toml",
            "python -m src.cli.main migrate --agents 07-validation --config config/migration.toml",
            "```",
        ]
    )


def _readiness_checklist() -> str:
    return "\n".join(
        [
            "# Focus Readiness Checklist",
            "",
            "## Essbase",
            "",
            "- [ ] Outline parsed and dimensions verified",
            "- [ ] Calc translation review queue triaged",
            "- [ ] BSO writeback package generated",
            "- [ ] UAT notebook passed",
            "",
            "## OAC on Exadata",
            "",
            "- [ ] Exadata source schemas discovered",
            "- [ ] Schema and ETL artifacts generated",
            "- [ ] Priority OAC reports migrated",
            "- [ ] Validation report approved",
            "",
            "## OAC on Essbase",
            "",
            "- [ ] Essbase semantic model baseline complete",
            "- [ ] OAC report parity checks complete",
            "- [ ] Security/RLS parity complete",
            "- [ ] Cutover checklist approved",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare focused migration track pack")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/focus_tracks"),
        help="Directory for generated focus-track runbooks",
    )
    parser.add_argument(
        "--bso-prep-dir",
        default="output/etl/bso_writeback_prep",
        help="Path shown in runbooks for BSO prep artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    _write(out / "01_essbase_core_plan.md", _track_essbase_core(args.bso_prep_dir))
    _write(out / "02_oac_on_exadata_plan.md", _track_oac_exadata())
    _write(out / "03_oac_on_essbase_plan.md", _track_oac_on_essbase())
    _write(out / "command_book.md", _command_book())
    _write(out / "readiness_checklist.md", _readiness_checklist())

    print(f"Generated focus track pack in: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
