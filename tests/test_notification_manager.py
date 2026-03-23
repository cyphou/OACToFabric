"""Tests for notification manager — rules, dispatch, history."""

from __future__ import annotations

import pytest

from src.agents.orchestrator.notification_manager import (
    Channel,
    Notification,
    NotificationManager,
    NotificationRule,
    Severity,
    render_notification_log,
)


# ---------------------------------------------------------------------------
# NotificationManager
# ---------------------------------------------------------------------------


class TestNotificationManager:
    def test_default_channels(self):
        mgr = NotificationManager()
        # Only LOG is enabled by default
        notifs = mgr.notify("wave_started", "W1", "started")
        assert len(notifs) == 1
        assert notifs[0].channel == Channel.LOG

    def test_enabled_channels_filter(self):
        mgr = NotificationManager(
            enabled_channels=[Channel.LOG, Channel.TEAMS]
        )
        notifs = mgr.notify("wave_started", "W1", "started")
        # wave_started rule → LOG + TEAMS
        assert len(notifs) == 2
        channels = {n.channel for n in notifs}
        assert Channel.LOG in channels
        assert Channel.TEAMS in channels

    def test_email_channel(self):
        mgr = NotificationManager(
            enabled_channels=[Channel.LOG, Channel.TEAMS, Channel.EMAIL]
        )
        notifs = mgr.notify("wave_completed", "W1", "done")
        channels = {n.channel for n in notifs}
        assert Channel.EMAIL in channels

    def test_no_matching_rule(self):
        mgr = NotificationManager()
        notifs = mgr.notify("unknown_event", "Title", "msg")
        # Falls back to INFO/LOG
        assert len(notifs) == 1
        assert notifs[0].severity == Severity.INFO

    def test_severity_override(self):
        mgr = NotificationManager()
        notifs = mgr.notify(
            "wave_started", "W1", "msg", severity=Severity.CRITICAL
        )
        assert notifs[0].severity == Severity.CRITICAL

    def test_history(self):
        mgr = NotificationManager()
        mgr.notify("wave_started", "W1", "started")
        mgr.notify("wave_completed", "W1", "done")
        assert len(mgr.history) == 2

    def test_clear_history(self):
        mgr = NotificationManager()
        mgr.notify("wave_started", "W1", "msg")
        mgr.clear_history()
        assert len(mgr.history) == 0

    def test_agent_id_and_wave_id(self):
        mgr = NotificationManager()
        notifs = mgr.notify(
            "agent_completed", "Done", "msg",
            agent_id="02-schema", wave_id="wave1",
        )
        assert notifs[0].agent_id == "02-schema"
        assert notifs[0].wave_id == "wave1"

    def test_metadata(self):
        mgr = NotificationManager()
        notifs = mgr.notify(
            "agent_completed", "Done", "msg",
            metadata={"key": "val"},
        )
        assert notifs[0].metadata == {"key": "val"}


# ---------------------------------------------------------------------------
# Custom rules
# ---------------------------------------------------------------------------


class TestCustomRules:
    def test_custom_rule(self):
        rules = [
            NotificationRule(
                "custom_event",
                Severity.HIGH,
                [Channel.LOG, Channel.PAGERDUTY],
            ),
        ]
        mgr = NotificationManager(
            rules=rules,
            enabled_channels=[Channel.LOG, Channel.PAGERDUTY],
        )
        notifs = mgr.notify("custom_event", "Alert", "msg")
        assert len(notifs) == 2
        assert notifs[0].severity == Severity.HIGH

    def test_partial_match(self):
        rules = [
            NotificationRule("wave", Severity.INFO, [Channel.LOG]),
        ]
        mgr = NotificationManager(rules=rules)
        notifs = mgr.notify("wave_started", "W1", "msg")
        assert len(notifs) == 1  # "wave" is in "wave_started"


# ---------------------------------------------------------------------------
# Notification data class
# ---------------------------------------------------------------------------


class TestNotification:
    def test_defaults(self):
        n = Notification(title="T", message="M")
        assert n.severity == Severity.INFO
        assert n.channel == Channel.LOG
        assert n.agent_id == ""


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class TestRenderNotificationLog:
    def test_renders(self):
        history = [
            Notification(
                title="Wave 1 started", message="5 items",
                severity=Severity.INFO, channel=Channel.LOG,
                agent_id="", wave_id="1",
            ),
            Notification(
                title="Agent 02 failed", message="timeout",
                severity=Severity.HIGH, channel=Channel.TEAMS,
                agent_id="02-schema", wave_id="1",
            ),
        ]
        md = render_notification_log(history)
        assert "Notification Log" in md
        assert "Wave 1 started" in md
        assert "Agent 02 failed" in md
        assert "HIGH" in md

    def test_empty(self):
        md = render_notification_log([])
        assert "Notification Log" in md
