"""Schedule converter — Oracle DBMS_SCHEDULER → Fabric triggers.

Converts Oracle scheduled job definitions into Fabric Data Factory
trigger definitions (schedule-based and tumbling-window triggers).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class OracleSchedule:
    """Parsed Oracle scheduled job definition."""

    job_name: str
    job_type: str = "PLSQL_BLOCK"   # PLSQL_BLOCK | STORED_PROCEDURE | CHAIN
    program_name: str = ""
    procedure_name: str = ""
    repeat_interval: str = ""       # Oracle DBMS_SCHEDULER repeat_interval
    start_date: str = ""
    end_date: str = ""
    enabled: bool = True
    job_class: str = "DEFAULT_JOB_CLASS"
    comments: str = ""
    # For job chains
    chain_steps: list[dict[str, str]] = field(default_factory=list)
    # Dependencies on other jobs
    depends_on: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricTrigger:
    """Fabric Data Factory trigger definition."""

    name: str
    trigger_type: str = "ScheduleTrigger"  # ScheduleTrigger | TumblingWindowTrigger
    pipeline_name: str = ""
    recurrence: dict[str, Any] = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    annotations: list[str] = field(default_factory=list)
    requires_review: bool = False
    review_reason: str = ""

    def to_json(self) -> dict[str, Any]:
        """Serialise to Fabric Data Factory trigger JSON format."""
        trigger: dict[str, Any] = {
            "name": self.name,
            "properties": {
                "type": self.trigger_type,
                "description": self.description,
                "annotations": self.annotations or ["auto-generated", "agent-03"],
                "pipelines": [
                    {
                        "pipelineReference": {
                            "referenceName": self.pipeline_name,
                            "type": "PipelineReference",
                        },
                        "parameters": self.parameters,
                    }
                ],
                "typeProperties": {
                    "recurrence": self.recurrence,
                },
            },
        }
        if self.start_time:
            trigger["properties"]["typeProperties"]["recurrence"]["startTime"] = self.start_time
        if self.end_time:
            trigger["properties"]["typeProperties"]["recurrence"]["endTime"] = self.end_time
        return trigger


# ---------------------------------------------------------------------------
# Oracle REPEAT_INTERVAL parser
# ---------------------------------------------------------------------------

# Oracle formats:
#   FREQ=DAILY; BYHOUR=2; BYMINUTE=0; BYSECOND=0
#   FREQ=HOURLY; INTERVAL=4
#   FREQ=WEEKLY; BYDAY=MON,WED,FRI; BYHOUR=6
#   FREQ=MINUTELY; INTERVAL=30
#   FREQ=MONTHLY; BYMONTHDAY=1; BYHOUR=0

_FREQ_MAP = {
    "YEARLY": ("Year", 1),
    "MONTHLY": ("Month", 1),
    "WEEKLY": ("Week", 1),
    "DAILY": ("Day", 1),
    "HOURLY": ("Hour", 1),
    "MINUTELY": ("Minute", 1),
    "SECONDLY": ("Minute", 1),  # Not supported in Fabric — map to Minute
}

_DAY_MAP = {
    "MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday",
    "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday",
}


def parse_repeat_interval(interval_str: str) -> dict[str, Any]:
    """Parse an Oracle DBMS_SCHEDULER repeat_interval string into Fabric recurrence.

    Returns a dict suitable for the Fabric trigger recurrence property.
    """
    if not interval_str:
        return {"frequency": "Day", "interval": 1}

    parts: dict[str, str] = {}
    for token in interval_str.split(";"):
        token = token.strip()
        if "=" in token:
            key, val = token.split("=", 1)
            parts[key.strip().upper()] = val.strip()

    freq = parts.get("FREQ", "DAILY").upper()
    fabric_freq, default_interval = _FREQ_MAP.get(freq, ("Day", 1))
    interval = int(parts.get("INTERVAL", str(default_interval)))

    recurrence: dict[str, Any] = {
        "frequency": fabric_freq,
        "interval": interval,
    }

    # Time of day
    hour = int(parts.get("BYHOUR", "0"))
    minute = int(parts.get("BYMINUTE", "0"))
    if fabric_freq in ("Day", "Week", "Month", "Year"):
        recurrence["schedule"] = {
            "hours": [hour],
            "minutes": [minute],
        }

    # Day of week
    byday = parts.get("BYDAY", "")
    if byday and fabric_freq == "Week":
        days = [_DAY_MAP.get(d.strip().upper()[:3], d.strip()) for d in byday.split(",")]
        recurrence.setdefault("schedule", {})["weekDays"] = days

    # Day of month
    bymonthday = parts.get("BYMONTHDAY", "")
    if bymonthday and fabric_freq == "Month":
        days_of_month = [int(d.strip()) for d in bymonthday.split(",")]
        recurrence.setdefault("schedule", {})["monthDays"] = days_of_month

    return recurrence


# ---------------------------------------------------------------------------
# Conversion engine
# ---------------------------------------------------------------------------


def convert_schedule(
    schedule: OracleSchedule,
    pipeline_name: str | None = None,
) -> FabricTrigger:
    """Convert an Oracle scheduled job to a Fabric Data Factory trigger.

    Parameters
    ----------
    schedule : OracleSchedule
        Parsed Oracle schedule definition.
    pipeline_name : str | None
        Target Fabric pipeline name. If None, derived from the job name.
    """
    p_name = pipeline_name or f"Pipeline_{_safe_name(schedule.job_name)}"

    recurrence = parse_repeat_interval(schedule.repeat_interval)

    trigger = FabricTrigger(
        name=f"Trigger_{_safe_name(schedule.job_name)}",
        trigger_type="ScheduleTrigger",
        pipeline_name=p_name,
        recurrence=recurrence,
        start_time=schedule.start_date,
        end_time=schedule.end_date,
        description=schedule.comments or f"Migrated from Oracle job: {schedule.job_name}",
        annotations=["auto-generated", "schedule-migration", "agent-03"],
    )

    # Job chains become sequential pipelines — flag for review
    if schedule.job_type == "CHAIN" or schedule.chain_steps:
        trigger.requires_review = True
        trigger.review_reason = "Oracle job chain — ensure sequential pipeline activities are configured"

    # Dependencies flag
    if schedule.depends_on:
        trigger.requires_review = True
        trigger.review_reason = (
            f"Job depends on: {', '.join(schedule.depends_on)} — configure pipeline dependencies"
        )

    if not schedule.enabled:
        trigger.annotations.append("disabled")

    logger.info(
        "Converted schedule '%s' → trigger '%s' (%s, interval=%d)",
        schedule.job_name, trigger.name, recurrence.get("frequency"), recurrence.get("interval", 1),
    )
    return trigger


def convert_multiple_schedules(
    schedules: list[OracleSchedule],
    pipeline_mapping: dict[str, str] | None = None,
) -> list[FabricTrigger]:
    """Convert a list of Oracle schedules to Fabric triggers.

    Parameters
    ----------
    pipeline_mapping : dict
        Optional mapping from Oracle job name → Fabric pipeline name.
    """
    pmap = pipeline_mapping or {}
    return [
        convert_schedule(s, pipeline_name=pmap.get(s.job_name))
        for s in schedules
    ]


# ---------------------------------------------------------------------------
# Schedule extraction helpers
# ---------------------------------------------------------------------------


def parse_oracle_job_metadata(raw: dict[str, Any]) -> OracleSchedule:
    """Parse an Oracle DBMS_SCHEDULER job metadata dict.

    Expected keys (from DBA_SCHEDULER_JOBS or similar query):
        job_name, job_type, program_name, repeat_interval,
        start_date, end_date, enabled, job_class, comments
    """
    chain_steps = raw.get("chain_steps", [])
    depends = raw.get("depends_on", raw.get("dependencies", []))
    if isinstance(depends, str):
        depends = [d.strip() for d in depends.split(",") if d.strip()]

    return OracleSchedule(
        job_name=raw.get("job_name", raw.get("JOB_NAME", "unknown")),
        job_type=raw.get("job_type", raw.get("JOB_TYPE", "PLSQL_BLOCK")),
        program_name=raw.get("program_name", raw.get("PROGRAM_NAME", "")),
        procedure_name=raw.get("procedure_name", raw.get("PROCEDURE_NAME", "")),
        repeat_interval=raw.get("repeat_interval", raw.get("REPEAT_INTERVAL", "")),
        start_date=raw.get("start_date", raw.get("START_DATE", "")),
        end_date=raw.get("end_date", raw.get("END_DATE", "")),
        enabled=_parse_bool(raw.get("enabled", raw.get("ENABLED", "TRUE"))),
        job_class=raw.get("job_class", raw.get("JOB_CLASS", "DEFAULT_JOB_CLASS")),
        comments=raw.get("comments", raw.get("COMMENTS", "")),
        chain_steps=chain_steps,
        depends_on=depends,
        metadata=raw,
    )


def parse_multiple_jobs(jobs: list[dict[str, Any]]) -> list[OracleSchedule]:
    """Parse a list of Oracle job metadata dicts."""
    return [parse_oracle_job_metadata(j) for j in jobs]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w]", "_", name.strip()).lower()


def _parse_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().upper() in ("TRUE", "1", "YES", "ENABLED")
