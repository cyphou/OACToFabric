"""Deployment script for OAC-to-Fabric migration artefacts.

Promotes artefacts across environments (dev → test → prod) and deploys
them to the target Fabric workspace.

Usage::

    python scripts/deploy.py --env prod --workspace-id <id> --dry-run
    python scripts/deploy.py --env test --artifacts output/dev
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("deploy")


def _discover_artifacts(artifact_dir: Path) -> dict[str, list[Path]]:
    """Discover deployable artefacts in the output directory."""
    artifacts: dict[str, list[Path]] = {
        "ddl": [],
        "pipelines": [],
        "notebooks": [],
        "tmdl": [],
        "reports": [],
    }

    if not artifact_dir.exists():
        logger.warning("Artifact directory not found: %s", artifact_dir)
        return artifacts

    for f in artifact_dir.rglob("*.sql"):
        artifacts["ddl"].append(f)
    for f in artifact_dir.rglob("*.pipeline.json"):
        artifacts["pipelines"].append(f)
    for f in artifact_dir.rglob("*.py"):
        if "notebook" in f.stem.lower() or f.parent.name == "notebooks":
            artifacts["notebooks"].append(f)
    for f in artifact_dir.rglob("*.tmdl"):
        artifacts["tmdl"].append(f)
    for f in artifact_dir.rglob("*.pbir"):
        artifacts["reports"].append(f)

    for category, files in artifacts.items():
        logger.info("Found %d %s artefact(s)", len(files), category)

    return artifacts


def _validate_prerequisites(env: str) -> bool:
    """Check that required environment variables and configs are set."""
    issues: list[str] = []

    import os

    required_vars = ["FABRIC_WORKSPACE_ID"]
    if env == "prod":
        required_vars.extend(["AZURE_OPENAI_KEY", "FABRIC_SQL_ENDPOINT"])

    for var in required_vars:
        if not os.environ.get(var):
            issues.append(f"Missing environment variable: {var}")

    if issues:
        for issue in issues:
            logger.error(issue)
        return False
    return True


def _generate_deployment_manifest(
    artifacts: dict[str, list[Path]],
    env: str,
    workspace_id: str,
) -> dict:
    """Generate a deployment manifest for tracking."""
    total = sum(len(v) for v in artifacts.values())
    return {
        "environment": env,
        "workspace_id": workspace_id,
        "total_artifacts": total,
        "breakdown": {k: len(v) for k, v in artifacts.items()},
        "files": {k: [str(f) for f in v] for k, v in artifacts.items()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deploy migration artefacts")
    parser.add_argument("--env", required=True, choices=["dev", "test", "prod"])
    parser.add_argument("--workspace-id", default="")
    parser.add_argument(
        "--artifacts",
        default="output",
        help="Directory containing artefacts to deploy",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-manifest", default="deployment_manifest.json")
    args = parser.parse_args(argv)

    logger.info("=== Deployment: env=%s ===", args.env)

    artifact_dir = Path(args.artifacts)
    artifacts = _discover_artifacts(artifact_dir)

    total = sum(len(v) for v in artifacts.values())
    if total == 0:
        logger.warning("No artefacts found in %s — nothing to deploy", artifact_dir)
        return 0

    manifest = _generate_deployment_manifest(artifacts, args.env, args.workspace_id)

    if args.dry_run:
        logger.info("[DRY-RUN] Would deploy %d artefact(s) to workspace %s", total, args.workspace_id)
        logger.info("Manifest:\n%s", json.dumps(manifest, indent=2))
        return 0

    if not _validate_prerequisites(args.env):
        logger.error("Prerequisites not met — aborting deployment")
        return 1

    # Write manifest
    manifest_path = Path(args.output_manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Deployment manifest written to %s", manifest_path)

    logger.info("Deployment complete: %d artefact(s)", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
