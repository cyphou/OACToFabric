"""Tests for Oracle DBMS_SCHEDULER → Fabric trigger converter."""

from __future__ import annotations

import pytest

from src.agents.etl.schedule_converter import (
    FabricTrigger,
    OracleSchedule,
    convert_multiple_schedules,
    convert_schedule,
    parse_oracle_job_metadata,
    parse_repeat_interval,
)


# ---------------------------------------------------------------------------
# parse_repeat_interval
# ---------------------------------------------------------------------------


class TestParseRepeatInterval:
    def test_daily(self):
        r = parse_repeat_interval("FREQ=DAILY; BYHOUR=2; BYMINUTE=30")
        assert r["frequency"] == "Day"
        assert r["interval"] == 1
        assert r["schedule"]["hours"] == [2]
        assert r["schedule"]["minutes"] == [30]

    def test_hourly(self):
        r = parse_repeat_interval("FREQ=HOURLY; INTERVAL=4")
        assert r["frequency"] == "Hour"
        assert r["interval"] == 4

    def test_weekly_with_days(self):
        r = parse_repeat_interval("FREQ=WEEKLY; BYDAY=MON,WED,FRI; BYHOUR=6")
        assert r["frequency"] == "Week"
        assert "Monday" in r["schedule"]["weekDays"]
        assert "Wednesday" in r["schedule"]["weekDays"]
        assert "Friday" in r["schedule"]["weekDays"]

    def test_monthly_with_day(self):
        r = parse_repeat_interval("FREQ=MONTHLY; BYMONTHDAY=1; BYHOUR=0")
        assert r["frequency"] == "Month"
        assert r["schedule"]["monthDays"] == [1]

    def test_minutely(self):
        r = parse_repeat_interval("FREQ=MINUTELY; INTERVAL=30")
        assert r["frequency"] == "Minute"
        assert r["interval"] == 30

    def test_empty_string(self):
        r = parse_repeat_interval("")
        assert r["frequency"] == "Day"
        assert r["interval"] == 1


# ---------------------------------------------------------------------------
# convert_schedule
# ---------------------------------------------------------------------------


class TestConvertSchedule:
    def test_basic_daily(self):
        schedule = OracleSchedule(
            job_name="DAILY_LOAD",
            repeat_interval="FREQ=DAILY; BYHOUR=3",
            comments="Daily data load",
        )
        trigger = convert_schedule(schedule)
        assert trigger.name == "Trigger_daily_load"
        assert trigger.pipeline_name == "Pipeline_daily_load"
        assert trigger.recurrence["frequency"] == "Day"
        assert trigger.requires_review is False

    def test_custom_pipeline_name(self):
        schedule = OracleSchedule(job_name="JOB_A", repeat_interval="FREQ=HOURLY; INTERVAL=2")
        trigger = convert_schedule(schedule, pipeline_name="My_Pipeline")
        assert trigger.pipeline_name == "My_Pipeline"

    def test_chain_requires_review(self):
        schedule = OracleSchedule(
            job_name="CHAIN_JOB",
            job_type="CHAIN",
            chain_steps=[{"step": "step1"}, {"step": "step2"}],
            repeat_interval="FREQ=DAILY",
        )
        trigger = convert_schedule(schedule)
        assert trigger.requires_review is True
        assert "chain" in trigger.review_reason.lower()

    def test_dependencies_require_review(self):
        schedule = OracleSchedule(
            job_name="DEP_JOB",
            repeat_interval="FREQ=DAILY",
            depends_on=["JOB_A", "JOB_B"],
        )
        trigger = convert_schedule(schedule)
        assert trigger.requires_review is True
        assert "JOB_A" in trigger.review_reason

    def test_disabled_annotated(self):
        schedule = OracleSchedule(
            job_name="DISABLED_JOB",
            repeat_interval="FREQ=DAILY",
            enabled=False,
        )
        trigger = convert_schedule(schedule)
        assert "disabled" in trigger.annotations

    def test_trigger_to_json(self):
        schedule = OracleSchedule(
            job_name="JSON_TEST",
            repeat_interval="FREQ=HOURLY; INTERVAL=1",
            start_date="2025-01-01T00:00:00Z",
        )
        trigger = convert_schedule(schedule)
        j = trigger.to_json()
        assert j["name"] == trigger.name
        assert j["properties"]["type"] == "ScheduleTrigger"
        assert j["properties"]["pipelines"][0]["pipelineReference"]["referenceName"] == trigger.pipeline_name
        assert j["properties"]["typeProperties"]["recurrence"]["startTime"] == "2025-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# parse_oracle_job_metadata
# ---------------------------------------------------------------------------


class TestParseJobMetadata:
    def test_basic_parse(self):
        raw = {
            "job_name": "ETL_NIGHTLY",
            "job_type": "STORED_PROCEDURE",
            "repeat_interval": "FREQ=DAILY; BYHOUR=1",
            "enabled": "TRUE",
            "comments": "Nightly ETL",
        }
        schedule = parse_oracle_job_metadata(raw)
        assert schedule.job_name == "ETL_NIGHTLY"
        assert schedule.job_type == "STORED_PROCEDURE"
        assert schedule.enabled is True

    def test_uppercase_keys(self):
        raw = {"JOB_NAME": "UP_JOB", "REPEAT_INTERVAL": "FREQ=WEEKLY", "ENABLED": "FALSE"}
        schedule = parse_oracle_job_metadata(raw)
        assert schedule.job_name == "UP_JOB"
        assert schedule.enabled is False

    def test_depends_on_csv(self):
        raw = {"job_name": "J", "depends_on": "JOB_A, JOB_B"}
        schedule = parse_oracle_job_metadata(raw)
        assert schedule.depends_on == ["JOB_A", "JOB_B"]


# ---------------------------------------------------------------------------
# Batch conversion
# ---------------------------------------------------------------------------


class TestConvertMultiple:
    def test_converts_list(self):
        schedules = [
            OracleSchedule(job_name="J1", repeat_interval="FREQ=DAILY"),
            OracleSchedule(job_name="J2", repeat_interval="FREQ=HOURLY; INTERVAL=6"),
        ]
        triggers = convert_multiple_schedules(schedules)
        assert len(triggers) == 2

    def test_with_pipeline_mapping(self):
        schedules = [OracleSchedule(job_name="MY_JOB", repeat_interval="FREQ=DAILY")]
        mapping = {"MY_JOB": "CustomPipeline"}
        triggers = convert_multiple_schedules(schedules, pipeline_mapping=mapping)
        assert triggers[0].pipeline_name == "CustomPipeline"
