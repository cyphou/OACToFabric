"""Notification manager — emit migration events to configured channels.

Supports pluggable notification backends.  The default implementation
logs to the Python logger; integrations with Microsoft Teams, email,
and PagerDuty are represented as stubs that downstream deployments can
fill in.

Severity levels
---------------
- **INFO**: Routine progress (wave started, agent completed).
- **WARN**: Non-blocking issues (retry scheduled, degraded performance).
- **HIGH**: Blocking failure requiring attention.
- **CRITICAL**: Migration halted / data integrity risk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Channel(str, Enum):
    LOG = "log"
    TEAMS = "teams"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"


@dataclass
class Notification:
    """A single notification event."""

    title: str
    message: str
    severity: Severity = Severity.INFO
    channel: Channel = Channel.LOG
    agent_id: str = ""
    wave_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------


@dataclass
class NotificationRule:
    """Maps an event pattern to a severity + channel + recipients list."""

    event_pattern: str  # simple string match on event type
    severity: Severity = Severity.INFO
    channels: list[Channel] = field(default_factory=lambda: [Channel.LOG])
    recipients: list[str] = field(default_factory=list)


_DEFAULT_RULES: list[NotificationRule] = [
    NotificationRule("wave_started", Severity.INFO, [Channel.LOG, Channel.TEAMS]),
    NotificationRule("wave_completed", Severity.INFO, [Channel.LOG, Channel.TEAMS, Channel.EMAIL]),
    NotificationRule("agent_completed", Severity.INFO, [Channel.LOG]),
    NotificationRule("agent_failed_first", Severity.WARN, [Channel.LOG, Channel.TEAMS]),
    NotificationRule("agent_failed_max", Severity.HIGH, [Channel.LOG, Channel.TEAMS, Channel.EMAIL]),
    NotificationRule("validation_failure_high", Severity.HIGH, [Channel.LOG, Channel.TEAMS, Channel.EMAIL]),
    NotificationRule("migration_complete", Severity.INFO, [Channel.LOG, Channel.TEAMS, Channel.EMAIL]),
    NotificationRule("migration_halted", Severity.CRITICAL, [Channel.LOG, Channel.TEAMS, Channel.EMAIL, Channel.PAGERDUTY]),
]


# ---------------------------------------------------------------------------
# Notification manager
# ---------------------------------------------------------------------------


class NotificationManager:
    """Dispatch notifications via configured rules & channels."""

    def __init__(
        self,
        rules: list[NotificationRule] | None = None,
        enabled_channels: list[Channel] | None = None,
        *,
        teams_webhook_url: str = "",
        email_connection_string: str = "",
        email_sender: str = "",
        email_recipients: list[str] | None = None,
        pagerduty_routing_key: str = "",
    ) -> None:
        self._rules = rules or list(_DEFAULT_RULES)
        self._enabled = set(enabled_channels or [Channel.LOG])
        self._history: list[Notification] = []
        self._teams_webhook_url = teams_webhook_url
        self._email_connection_string = email_connection_string
        self._email_sender = email_sender
        self._email_recipients = email_recipients or []
        self._pagerduty_routing_key = pagerduty_routing_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notify(
        self,
        event_type: str,
        title: str,
        message: str,
        *,
        agent_id: str = "",
        wave_id: str = "",
        severity: Severity | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[Notification]:
        """Emit a notification for *event_type*.

        The severity and channels are determined by the first matching
        rule.  If no rule matches, a default INFO/LOG notification is
        sent.

        Returns the list of notifications dispatched (one per channel).
        """
        rule = self._match_rule(event_type)
        sev = severity or (rule.severity if rule else Severity.INFO)
        channels = (rule.channels if rule else [Channel.LOG])

        dispatched: list[Notification] = []
        for ch in channels:
            if ch not in self._enabled:
                continue
            notif = Notification(
                title=title,
                message=message,
                severity=sev,
                channel=ch,
                agent_id=agent_id,
                wave_id=wave_id,
                metadata=metadata or {},
            )
            self._dispatch(notif)
            dispatched.append(notif)
            self._history.append(notif)

        return dispatched

    @property
    def history(self) -> list[Notification]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    # ------------------------------------------------------------------
    # Rule matching
    # ------------------------------------------------------------------

    def _match_rule(self, event_type: str) -> NotificationRule | None:
        for rule in self._rules:
            if rule.event_pattern in event_type:
                return rule
        return None

    # ------------------------------------------------------------------
    # Channel dispatch (pluggable stubs)
    # ------------------------------------------------------------------

    def _dispatch(self, notification: Notification) -> None:
        """Route notification to the appropriate channel backend."""
        if notification.channel == Channel.LOG:
            self._send_log(notification)
        elif notification.channel == Channel.TEAMS:
            self._send_teams(notification)
        elif notification.channel == Channel.EMAIL:
            self._send_email(notification)
        elif notification.channel == Channel.PAGERDUTY:
            self._send_pagerduty(notification)

    def _send_log(self, n: Notification) -> None:
        log_fn = {
            Severity.INFO: logger.info,
            Severity.WARN: logger.warning,
            Severity.HIGH: logger.error,
            Severity.CRITICAL: logger.critical,
        }.get(n.severity, logger.info)
        log_fn("[%s] %s — %s", n.severity.value, n.title, n.message)

    def _send_teams(self, n: Notification) -> None:
        """Send a Microsoft Teams notification via Incoming Webhook."""
        if not self._teams_webhook_url:
            logger.debug("Teams webhook URL not configured — skipping")
            return
        import httpx

        severity_colors = {
            Severity.INFO: "0076D7",
            Severity.WARN: "FFA500",
            Severity.HIGH: "FF0000",
            Severity.CRITICAL: "8B0000",
        }
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": severity_colors.get(n.severity, "0076D7"),
            "summary": n.title,
            "sections": [
                {
                    "activityTitle": f"[{n.severity.value}] {n.title}",
                    "facts": [
                        {"name": "Message", "value": n.message},
                        {"name": "Agent", "value": n.agent_id or "—"},
                        {"name": "Wave", "value": n.wave_id or "—"},
                        {"name": "Timestamp", "value": n.timestamp.isoformat()},
                    ],
                    "markdown": True,
                }
            ],
        }
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(self._teams_webhook_url, json=card)
                resp.raise_for_status()
            logger.info("Teams notification sent: %s", n.title)
        except Exception:
            logger.exception("Failed to send Teams notification: %s", n.title)

    def _send_email(self, n: Notification) -> None:
        """Send an email notification via Azure Communication Services."""
        if not self._email_connection_string or not self._email_recipients:
            logger.debug("Email not configured — skipping")
            return
        try:
            from azure.communication.email import EmailClient

            client = EmailClient.from_connection_string(self._email_connection_string)
            message = {
                "senderAddress": self._email_sender or "DoNotReply@migration.local",
                "recipients": {
                    "to": [{"address": addr} for addr in self._email_recipients]
                },
                "content": {
                    "subject": f"[{n.severity.value}] {n.title}",
                    "plainText": (
                        f"{n.message}\n\n"
                        f"Agent: {n.agent_id or '—'}\n"
                        f"Wave: {n.wave_id or '—'}\n"
                        f"Timestamp: {n.timestamp.isoformat()}"
                    ),
                },
            }
            poller = client.begin_send(message)
            poller.result()
            logger.info("Email notification sent: %s", n.title)
        except ImportError:
            logger.warning("azure-communication-email not installed — skipping email")
        except Exception:
            logger.exception("Failed to send email notification: %s", n.title)

    def _send_pagerduty(self, n: Notification) -> None:
        """Send a PagerDuty alert via Events API v2."""
        if not self._pagerduty_routing_key:
            logger.debug("PagerDuty routing key not configured — skipping")
            return
        import httpx

        severity_map = {
            Severity.INFO: "info",
            Severity.WARN: "warning",
            Severity.HIGH: "error",
            Severity.CRITICAL: "critical",
        }
        payload = {
            "routing_key": self._pagerduty_routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"[{n.severity.value}] {n.title}: {n.message}",
                "severity": severity_map.get(n.severity, "error"),
                "source": "oac-to-fabric-migration",
                "component": n.agent_id or "orchestrator",
                "group": n.wave_id or "migration",
                "custom_details": {
                    "message": n.message,
                    "agent_id": n.agent_id,
                    "wave_id": n.wave_id,
                    "timestamp": n.timestamp.isoformat(),
                    **(n.metadata or {}),
                },
            },
        }
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    "https://events.pagerduty.com/v2/enqueue", json=payload
                )
                resp.raise_for_status()
            logger.info("PagerDuty alert sent: %s", n.title)
        except Exception:
            logger.exception("Failed to send PagerDuty alert: %s", n.title)


# ---------------------------------------------------------------------------
# Event report rendering
# ---------------------------------------------------------------------------


def render_notification_log(history: list[Notification]) -> str:
    """Render notification history as a Markdown table."""
    lines = [
        "# Notification Log",
        "",
        "| Timestamp | Severity | Channel | Title | Agent | Wave |",
        "|---|---|---|---|---|---|",
    ]
    for n in history:
        ts = n.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(
            f"| {ts} | {n.severity.value} | {n.channel.value} | "
            f"{n.title} | {n.agent_id or '—'} | {n.wave_id or '—'} |"
        )
    lines.append("")
    return "\n".join(lines)
