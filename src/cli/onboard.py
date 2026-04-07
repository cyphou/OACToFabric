"""CLI ``onboard`` subcommand — customer onboarding accelerator.

Runs environment scan → prerequisite check → effort estimate in sequence
and writes a combined onboarding report.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def register_onboard_parser(subparsers: Any) -> None:
    """Register the ``onboard`` subcommand on an argparse subparser group."""
    p = subparsers.add_parser("onboard", help="Customer onboarding: scan environment, check prereqs, estimate effort")
    p.add_argument("--customer", default="Customer", help="Customer name for the report")
    p.add_argument("--config-path", default="config/migration.toml", help="Path to migration config file")
    p.add_argument("--output-dir", default="output/onboarding", help="Directory for onboarding report")
    p.add_argument("--team-size", type=int, default=2, help="Number of team members for effort estimate")
    p.add_argument("--hours-per-day", type=float, default=6.0, help="Effective hours per person per day")
    p.set_defaults(func=run_onboard)


def _load_config_dict(config_path: str) -> dict[str, Any]:
    """Load config as a flat dict for the scanner/checker."""
    path = Path(config_path)
    if not path.exists():
        logger.warning("Config file not found: %s — using defaults", path)
        return {"config_path": config_path}
    try:
        if path.suffix == ".toml":
            import tomllib

            with open(path, "rb") as f:
                data = tomllib.load(f)
            # Flatten top-level sections
            flat: dict[str, Any] = {"config_path": config_path}
            for section in data.values():
                if isinstance(section, dict):
                    flat.update(section)
            return flat
        return {"config_path": config_path}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not parse config: %s", exc)
        return {"config_path": config_path}


def run_onboard(args: argparse.Namespace) -> int:
    """Execute the onboarding workflow."""
    from src.core.onboarding.effort_estimator import EffortEstimator
    from src.core.onboarding.env_scanner import EnvironmentScanner
    from src.core.onboarding.prereq_checker import PrerequisiteChecker

    config = _load_config_dict(args.config_path)

    # 1. Environment scan
    print("=" * 60)
    print("1. Environment Scan")
    print("=" * 60)
    scanner = EnvironmentScanner(config)
    env_profile = scanner.scan(customer_name=args.customer)
    print(env_profile.summary())
    print()

    # 2. Prerequisite check
    print("=" * 60)
    print("2. Prerequisite Check")
    print("=" * 60)
    checker = PrerequisiteChecker(config)
    prereq_report = checker.check()
    print(prereq_report.summary())
    print()

    # 3. Effort estimate (with a synthetic inventory profile)
    print("=" * 60)
    print("3. Effort Estimate")
    print("=" * 60)
    estimator = EffortEstimator(team_size=args.team_size, hours_per_day=args.hours_per_day)
    # If no real inventory, produce a placeholder
    sample_profile: list[dict[str, Any]] = config.get("inventory_profile", [])
    if not sample_profile:
        logger.info("No inventory_profile in config — using empty estimate")
    effort = estimator.estimate(sample_profile)
    print(effort.summary())
    print()

    # 4. Write combined report
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "customer": args.customer,
        "environment": env_profile.to_dict(),
        "prerequisites": prereq_report.to_dict(),
        "effort_estimate": effort.to_dict(),
    }
    report_path = out / "onboarding_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"Report written to {report_path}")

    ready = env_profile.all_reachable and prereq_report.ready
    return 0 if ready else 1
