#!/usr/bin/env python3
"""Run a live OAC pilot migration against a scoped subset.

Usage
-----
::

    python scripts/run_pilot.py --config config/migration.toml \\
        --scope "/shared/pilot" --output-dir output/pilot

The pilot:
1. Runs each agent in sequence on the given scope.
2. Captures timing, throughput, and error metrics.
3. Generates a ``PilotReport`` JSON + summary.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
import uuid
from pathlib import Path

# Ensure repo root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.pilot_report import (
    AgentVerdict,
    PerformanceProfile,
    PilotAgentResult,
    PilotDefect,
    PilotReportBuilder,
)

logger = logging.getLogger("pilot")

# Default agent execution order
AGENT_ORDER = [
    ("01", "Discovery"),
    ("02", "Schema"),
    ("03", "ETL"),
    ("04", "Semantic Model"),
    ("05", "Report"),
    ("06", "Security"),
    ("07", "Validation"),
]


async def _run_agent_stub(agent_id: str, agent_name: str, scope_path: str) -> PilotAgentResult:
    """Simulate an agent run.  Replace with real agent invocation."""
    start = time.monotonic()
    logger.info("Running %s (%s) on scope %s …", agent_name, agent_id, scope_path)

    # In production: import the agent, call discover/plan/execute/validate.
    # Here we produce a stub result for pilot-harness validation.
    await asyncio.sleep(0)  # yield control
    elapsed_ms = int((time.monotonic() - start) * 1000)

    return PilotAgentResult(
        agent_id=agent_id,
        agent_name=agent_name,
        verdict=AgentVerdict.OK,
        items_processed=0,
        duration_ms=elapsed_ms,
    )


async def run_pilot(scope_path: str, output_dir: str) -> int:
    """Execute the pilot and write the report."""
    pilot_id = f"pilot-{uuid.uuid4().hex[:8]}"
    builder = PilotReportBuilder(pilot_id, scope_description=f"Scope: {scope_path}")
    t0 = time.monotonic()

    for agent_id, agent_name in AGENT_ORDER:
        try:
            result = await _run_agent_stub(agent_id, agent_name, scope_path)
            builder.add_agent_result(result)
        except Exception as exc:  # noqa: BLE001
            builder.add_agent_result(
                PilotAgentResult(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    verdict=AgentVerdict.FAILED,
                    errors=[str(exc)],
                )
            )
            builder.add_defect(
                PilotDefect(
                    defect_id=f"DEF-{uuid.uuid4().hex[:6]}",
                    agent_id=agent_id,
                    severity="high",
                    title=f"{agent_name} failed",
                    description=str(exc),
                )
            )

    total_ms = int((time.monotonic() - t0) * 1000)
    builder.set_performance(PerformanceProfile(total_duration_ms=total_ms))

    report = builder.build()

    # Write output
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / f"{pilot_id}.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2, default=str))
    logger.info("Report written to %s", report_path)

    summary_path = out / f"{pilot_id}_summary.txt"
    summary_path.write_text(report.summary())

    print(report.summary())
    return 0 if report.outcome.value != "failed" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a live OAC pilot migration")
    parser.add_argument("--scope", default="/shared/pilot", help="OAC catalog path to pilot")
    parser.add_argument("--output-dir", default="output/pilot", help="Directory for pilot report")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    rc = asyncio.run(run_pilot(args.scope, args.output_dir))
    sys.exit(rc)


if __name__ == "__main__":
    main()
