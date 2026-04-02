"""CLI entry point for the OAC-to-Fabric migration framework.

Commands
--------
- ``oac-migrate discover``      — Run discovery only (Agent 01).
- ``oac-migrate plan``          — Generate a wave plan without executing.
- ``oac-migrate migrate``       — Full orchestrated migration.
- ``oac-migrate validate``      — Run validation suite standalone (Agent 07).
- ``oac-migrate status``        — Show migration progress from Lakehouse.
- ``oac-migrate marketplace``   — Plugin marketplace (list / install / publish).
- ``oac-migrate analytics``     — Export migration analytics dashboard data.
- ``oac-migrate optimize``      — AI-assisted schema optimization.
- ``oac-migrate tune``          — Performance auto-tuning analysis.
- ``oac-migrate validate-dax``  — Deep DAX syntax validation (src/tools).
- ``oac-migrate validate-tmdl`` — TMDL file-system validation (src/tools).
- ``oac-migrate reconcile``     — Data reconciliation between snapshots.
- ``oac-migrate dry-run``       — Fabric deployment dry-run.

Usage
-----
::

    python -m src.cli.main migrate --config config/migration.toml --output-dir output
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from src.cli.config_loader import MigrationConfig, load_config
from src.core.models import MigrationScope

logger = logging.getLogger("oac_migrate")


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _setup_logging(level: str = "INFO") -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s  %(levelname)-8s  [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Scope builder
# ---------------------------------------------------------------------------


def _build_scope(cfg: MigrationConfig, wave: int | None = None) -> MigrationScope:
    """Build a ``MigrationScope`` from config + CLI overrides."""
    from src.core.models import AssetType

    asset_types = []
    for at in cfg.scope.asset_types:
        try:
            asset_types.append(AssetType(at))
        except ValueError:
            logger.warning("Unknown asset type '%s' — skipping", at)

    return MigrationScope(
        include_paths=cfg.scope.include_paths,
        exclude_paths=cfg.scope.exclude_paths,
        asset_types=asset_types,
        wave=wave or cfg.scope.wave,
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


async def cmd_discover(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Run discovery only and write inventory."""
    from src.agents.orchestrator.orchestrator_agent import (
        OrchestratorAgent,
        OrchestratorConfig,
    )

    scope = _build_scope(cfg, wave=args.wave)
    orch_cfg = OrchestratorConfig(output_dir=args.output_dir or cfg.output_dir)
    orch = OrchestratorAgent(config=orch_cfg)

    inventory = await orch._load_inventory(scope)
    out = Path(orch_cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    lines = ["# Discovery Inventory", "", f"**Items:** {inventory.count}", ""]
    lines.append("| ID | Type | Name | Path |")
    lines.append("|---|---|---|---|")
    for item in inventory.items:
        lines.append(f"| {item.id} | {item.asset_type.value} | {item.name} | {item.source_path} |")

    report = "\n".join(lines)
    (out / "discovery_inventory.md").write_text(report, encoding="utf-8")
    print(f"Inventory written to {out / 'discovery_inventory.md'} ({inventory.count} items)")
    return 0


async def cmd_plan(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Generate wave plan without executing."""
    from src.agents.orchestrator.wave_planner import plan_waves, render_wave_plan

    scope = _build_scope(cfg, wave=args.wave)
    # Build inventory from scope
    from src.agents.orchestrator.orchestrator_agent import OrchestratorAgent, OrchestratorConfig

    orch = OrchestratorAgent(config=OrchestratorConfig(output_dir=args.output_dir or cfg.output_dir))
    inventory = await orch._load_inventory(scope)

    wave_plan = plan_waves(inventory, max_items_per_wave=cfg.orchestrator.max_items_per_wave)
    md = render_wave_plan(wave_plan)

    out = Path(args.output_dir or cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "wave_plan.md").write_text(md, encoding="utf-8")
    print(f"Wave plan written to {out / 'wave_plan.md'} ({wave_plan.wave_count} waves, {wave_plan.total_items} items)")
    return 0


async def cmd_migrate(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Run full orchestrated migration."""
    from src.agents.orchestrator.notification_manager import Channel
    from src.agents.orchestrator.orchestrator_agent import (
        OrchestratorAgent,
        OrchestratorConfig,
    )
    from src.core.agent_registry import build_default_registry
    from src.core.runner_factory import AgentDependencies, RunnerFactory
    from src.core.state_coordinator import StateCoordinator

    scope = _build_scope(cfg, wave=args.wave)

    channels = [Channel(c) for c in cfg.orchestrator.notification_channels]
    orch_cfg = OrchestratorConfig(
        max_retries=cfg.orchestrator.max_retries,
        retry_backoff_seconds=cfg.orchestrator.retry_backoff_seconds,
        parallel_agents_per_wave=cfg.orchestrator.parallel_agents_per_wave,
        max_items_per_wave=cfg.orchestrator.max_items_per_wave,
        validate_after_each_wave=cfg.orchestrator.validate_after_each_wave,
        auto_advance_waves=cfg.orchestrator.auto_advance_waves,
        notification_channels=channels,
        output_dir=args.output_dir or cfg.output_dir,
    )

    # --- Build real agent runner from registry + config ---
    registry = build_default_registry()

    # Filter agents if --agents flag specified
    agent_ids = None
    if hasattr(args, "agents") and args.agents:
        agent_ids = [a.strip() for a in args.agents.split(",")]
        logger.info("Restricting migration to agents: %s", agent_ids)

    deps = AgentDependencies(
        rpd_xml_path=getattr(getattr(cfg, "source", None), "rpd_xml_path", ""),
        oracle_schema=getattr(getattr(cfg, "source", None), "oracle_schema", "OACS"),
        workspace_id=getattr(cfg, "fabric_workspace_id", ""),
        lakehouse_name=getattr(cfg, "fabric_lakehouse_name", "oac_migration"),
        output_base=args.output_dir or cfg.output_dir,
    )
    state_coord = StateCoordinator()  # in-memory for now
    factory = RunnerFactory(
        registry=registry,
        deps=deps,
        state_coordinator=state_coord,
    )
    runner = factory.create_runner()

    # Handle --resume: skip agents that already completed
    if hasattr(args, "resume") and args.resume:
        completed = state_coord.get_completed_agents()
        if completed:
            logger.info("Resuming — skipping completed agents: %s", completed)
            print(f"[RESUME] Skipping completed agents: {completed}")

    if args.dry_run:
        print("[DRY-RUN] Would run migration with scope:")
        print(f"  Paths:  {scope.include_paths}")
        print(f"  Types:  {[a.value for a in scope.asset_types]}")
        print(f"  Wave:   {scope.wave}")
        print(f"  Output: {orch_cfg.output_dir}")
        print(f"  Agents: {agent_ids or registry.list()}")
        print(f"  Resume: {getattr(args, 'resume', False)}")
        return 0

    orch = OrchestratorAgent(config=orch_cfg, agent_runner=runner)
    summary = await orch.run_migration(scope)

    print(f"\nMigration {summary.overall_status}")
    print(f"  Agents run:  {summary.total_agents_run}")
    print(f"  Succeeded:   {summary.total_succeeded}")
    print(f"  Failed:      {summary.total_failed}")
    return 0 if summary.all_passed else 1


async def cmd_validate(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Run validation suite standalone."""
    from src.agents.orchestrator.orchestrator_agent import (
        OrchestratorAgent,
        OrchestratorConfig,
    )
    from src.agents.orchestrator.dag_engine import NodeStatus

    scope = _build_scope(cfg, wave=args.wave)
    orch_cfg = OrchestratorConfig(output_dir=args.output_dir or cfg.output_dir)
    orch = OrchestratorAgent(config=orch_cfg)

    result = await orch._execute_agent("07-validation", scope)
    status = "PASSED" if result.status == NodeStatus.SUCCEEDED else "FAILED"
    print(f"Validation {status}")
    if result.error:
        print(f"  Error: {result.error}")
    return 0 if result.status == NodeStatus.SUCCEEDED else 1


async def cmd_status(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Show migration progress."""
    out = Path(args.output_dir or cfg.output_dir)
    summary_path = out / "orchestrator" / "migration_summary.md"

    if summary_path.exists():
        print(summary_path.read_text(encoding="utf-8"))
    else:
        print(f"No migration summary found at {summary_path}")
        print("Run 'migrate' first to generate a summary.")
    return 0


async def cmd_marketplace(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Plugin marketplace operations."""
    from src.plugins.marketplace import (
        cmd_plugin_install,
        cmd_plugin_list,
        cmd_plugin_publish,
    )

    action = args.action
    if action == "list":
        return cmd_plugin_list(args)
    elif action == "install":
        return cmd_plugin_install(args)
    elif action == "publish":
        return cmd_plugin_publish(args)
    else:
        print(f"Unknown marketplace action: {action}")
        return 1


async def cmd_analytics(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Export migration analytics dashboard data."""
    from src.plugins.analytics_dashboard import (
        DashboardDataExporter,
        MetricsCollector,
        PBITTemplateGenerator,
    )

    out = Path(args.output_dir or cfg.output_dir) / "analytics"
    out.mkdir(parents=True, exist_ok=True)

    collector = MetricsCollector(migration_id="current")
    metrics = collector.create_snapshot()

    exporter = DashboardDataExporter(metrics)
    fmt = getattr(args, "format", "json")
    if fmt == "csv":
        exporter.export_agent_csv(out / "agents.csv")
        exporter.export_wave_csv(out / "waves.csv")
    elif fmt == "powerbi":
        gen = PBITTemplateGenerator(metrics)
        gen.save_manifest(out / "dashboard_manifest.json")
    else:
        exporter.export_json(out / "metrics.json")

    print(f"Analytics exported to {out} (format: {fmt})")
    return 0


async def cmd_optimize(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Run AI-assisted schema optimization."""
    from src.core.schema_optimizer import SchemaOptimizer, SchemaProfile

    out = Path(args.output_dir or cfg.output_dir) / "optimization"
    out.mkdir(parents=True, exist_ok=True)

    optimizer = SchemaOptimizer()
    # Build a minimal schema profile for demonstration
    profile = SchemaProfile(
        total_tables=0, total_columns=0, total_size_gb=0.0,
        fact_tables=[], dim_tables=[],
    )
    report = optimizer.analyze(profile)

    import json
    (out / "schema_recommendations.json").write_text(
        json.dumps(
            {"recommendations": [r.__dict__ for r in report.recommendations],
             "summary": report.summary},
            indent=2, default=str,
        ),
        encoding="utf-8",
    )
    print(f"Schema optimization report: {len(report.recommendations)} recommendations → {out}")
    return 0


async def cmd_tune(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Run performance auto-tuning analysis."""
    from src.core.perf_auto_tuner import PerformanceAutoTuner

    out = Path(args.output_dir or cfg.output_dir) / "tuning"
    out.mkdir(parents=True, exist_ok=True)

    tuner = PerformanceAutoTuner()
    report = tuner.tune(queries=[], measures=[], tables=[])

    import json
    (out / "perf_tuning_report.json").write_text(
        json.dumps(
            {"dax_optimizations": len(report.dax_optimizations),
             "aggregation_tables": len(report.aggregation_tables),
             "composite_patterns": len(report.composite_patterns),
             "summary": report.summary},
            indent=2, default=str,
        ),
        encoding="utf-8",
    )
    print(f"Performance tuning report → {out}")
    return 0


# ---------------------------------------------------------------------------
# Tool commands (src/tools/)
# ---------------------------------------------------------------------------


async def cmd_validate_dax(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Validate DAX expressions in a TMDL directory."""
    from src.tools.dax_validator import validate_tmdl_directory, validate_dax_deep

    target = getattr(args, "path", None) or args.output_dir or cfg.output_dir

    target_path = Path(target)
    if target_path.is_dir():
        results = validate_tmdl_directory(str(target_path))
        total_errors = sum(r.error_count for r in results)
        total_warnings = sum(r.warning_count for r in results)
        print(f"DAX Validation: {len(results)} measures checked")
        print(f"  Errors:   {total_errors}")
        print(f"  Warnings: {total_warnings}")
        for r in results:
            if r.issues:
                for issue in r.issues:
                    severity = issue.severity.value.upper()
                    print(f"  [{severity}] {r.measure_name}: {issue.code} — {issue.message}")
        return 1 if total_errors > 0 else 0
    else:
        # Single expression
        expr = target_path.read_text(encoding="utf-8") if target_path.is_file() else target
        result = validate_dax_deep(expr)
        for issue in result.issues:
            print(f"  [{issue.severity.value.upper()}] {issue.code}: {issue.message}")
        return 1 if result.error_count > 0 else 0


async def cmd_validate_tmdl(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Validate TMDL file structure."""
    from src.tools.tmdl_file_validator import validate_tmdl_output

    target = getattr(args, "path", None) or args.output_dir or cfg.output_dir

    report = validate_tmdl_output(target)
    print(f"TMDL Validation: {report.total_checks} checks")
    print(f"  Passed:   {report.passed}")
    print(f"  Failed:   {report.failed}")
    for finding in report.findings:
        if finding.get("severity") == "error":
            print(f"  [ERROR] {finding.get('check')}: {finding.get('message')}")
    return 0 if report.all_passed else 1


async def cmd_reconcile(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Run data reconciliation between source and target snapshots."""
    from src.tools.reconciliation_cli import (
        OfflineReconciler,
        generate_markdown_report,
    )
    import json as json_mod

    source_path = getattr(args, "source", None)
    target_path = getattr(args, "target", None)

    if not source_path or not target_path:
        print("Error: --source and --target snapshot JSON files are required")
        return 1

    source_data = json_mod.loads(Path(source_path).read_text(encoding="utf-8"))
    target_data = json_mod.loads(Path(target_path).read_text(encoding="utf-8"))

    recon = OfflineReconciler(source_data, target_data)
    report = recon.run()

    md = generate_markdown_report(report)
    out = Path(args.output_dir or cfg.output_dir) / "reconciliation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "reconciliation_report.md").write_text(md, encoding="utf-8")
    print(f"Reconciliation: {report.total_checks} checks, {report.passed} passed, {report.failed} failed")
    print(f"  Report → {out / 'reconciliation_report.md'}")
    return 0 if report.all_passed else 1


async def cmd_dry_run(cfg: MigrationConfig, args: argparse.Namespace) -> int:
    """Run Fabric deployment dry-run."""
    from src.tools.fabric_dry_run import DeploymentDryRun, export_manifest_json

    target = getattr(args, "path", None) or args.output_dir or cfg.output_dir

    dry_run = DeploymentDryRun(output_dir=target)
    manifest = dry_run.scan()

    out = Path(args.output_dir or cfg.output_dir) / "dry_run"
    out.mkdir(parents=True, exist_ok=True)

    manifest_json = export_manifest_json(manifest)
    (out / "deployment_manifest.json").write_text(manifest_json, encoding="utf-8")

    print(f"Dry-Run: {manifest.total_artifacts} artifacts scanned")
    print(f"  Valid:   {manifest.valid_count}")
    print(f"  Issues:  {manifest.issue_count}")
    print(f"  Manifest → {out / 'deployment_manifest.json'}")
    return 0 if manifest.issue_count == 0 else 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oac-migrate",
        description="OAC → Microsoft Fabric & Power BI migration CLI",
    )
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="Path to migration TOML config (default: config/migration.toml)",
    )
    parser.add_argument(
        "--env", "-e",
        default=None,
        help="Environment name for config overlay (dev/test/prod)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Output directory for reports",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-error output",
    )

    sub = parser.add_subparsers(dest="command", help="Migration commands")

    # --- discover ---
    p_discover = sub.add_parser("discover", help="Run discovery and output inventory")
    p_discover.add_argument("--wave", type=int, default=None)

    # --- plan ---
    p_plan = sub.add_parser("plan", help="Generate wave plan without executing")
    p_plan.add_argument("--wave", type=int, default=None)

    # --- migrate ---
    p_migrate = sub.add_parser("migrate", help="Run full orchestrated migration")
    p_migrate.add_argument("--wave", type=int, default=None)
    p_migrate.add_argument("--dry-run", action="store_true", help="Preview without executing")
    p_migrate.add_argument(
        "--agents",
        default=None,
        help="Comma-separated agent IDs to run (e.g. '01-discovery,02-schema')",
    )
    p_migrate.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint (skip completed agents)",
    )

    # --- validate ---
    p_validate = sub.add_parser("validate", help="Run validation suite")
    p_validate.add_argument("--wave", type=int, default=None)

    # --- status ---
    sub.add_parser("status", help="Show migration progress")

    # --- marketplace ---
    p_mp = sub.add_parser("marketplace", help="Plugin marketplace: list / install / publish")
    p_mp.add_argument("action", choices=["list", "install", "publish"],
                       help="Marketplace operation")
    p_mp.add_argument("--name", default=None, help="Plugin name (for install/publish)")
    p_mp.add_argument("--registry", default=None, help="Path to registry JSON")
    p_mp.add_argument("--tag", default=None, help="Filter by tag (for list)")

    # --- analytics ---
    p_an = sub.add_parser("analytics", help="Export migration analytics dashboard data")
    p_an.add_argument("--format", choices=["json", "csv", "powerbi"], default="json",
                       help="Export format (default: json)")

    # --- optimize ---
    p_opt = sub.add_parser("optimize", help="AI-assisted schema optimization")
    p_opt.add_argument("--lakehouse", default=None, help="Target Fabric Lakehouse name")

    # --- tune ---
    p_tune = sub.add_parser("tune", help="Performance auto-tuning analysis")
    p_tune.add_argument("--lakehouse", default=None, help="Target Fabric Lakehouse name")

    # --- validate-dax ---
    p_vdax = sub.add_parser("validate-dax", help="Deep DAX syntax validation")
    p_vdax.add_argument("path", nargs="?", default=None, help="TMDL directory or DAX file/expression")

    # --- validate-tmdl ---
    p_vtmdl = sub.add_parser("validate-tmdl", help="TMDL file-system structure validation")
    p_vtmdl.add_argument("path", nargs="?", default=None, help="TMDL output directory")

    # --- reconcile ---
    p_recon = sub.add_parser("reconcile", help="Data reconciliation between snapshots")
    p_recon.add_argument("--source", required=True, help="Source snapshot JSON file")
    p_recon.add_argument("--target", required=True, help="Target snapshot JSON file")

    # --- dry-run ---
    p_dry = sub.add_parser("dry-run", help="Fabric deployment dry-run")
    p_dry.add_argument("path", nargs="?", default=None, help="Output directory to scan")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_COMMANDS: dict[str, Any] = {
    "discover": cmd_discover,
    "plan": cmd_plan,
    "migrate": cmd_migrate,
    "validate": cmd_validate,
    "status": cmd_status,
    "marketplace": cmd_marketplace,
    "analytics": cmd_analytics,
    "optimize": cmd_optimize,
    "tune": cmd_tune,
    "validate-dax": cmd_validate_dax,
    "validate-tmdl": cmd_validate_tmdl,
    "reconcile": cmd_reconcile,
    "dry-run": cmd_dry_run,
}


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Logging
    level = "DEBUG" if args.verbose else ("WARNING" if args.quiet else "INFO")
    _setup_logging(level)

    # Config
    cfg = load_config(
        config_path=args.config,
        environment=args.env,
    )
    if args.verbose:
        cfg.log_level = "DEBUG"

    handler = _COMMANDS.get(args.command)
    if not handler:
        parser.print_help()
        return 1

    return asyncio.run(handler(cfg, args))


if __name__ == "__main__":
    sys.exit(main())
