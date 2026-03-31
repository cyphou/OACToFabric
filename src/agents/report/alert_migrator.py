"""Alert Migrator — OAC Agents/Alerts → Fabric Data Activator triggers.

Parses OAC agent definitions (condition-based alerts with thresholds,
schedules, and delivery channels) and generates Fabric Data Activator
Reflex trigger configurations.

Handles:
  - Threshold conditions (>, <, ==, between, top-N, bottom-N)
  - Schedule mapping (OAC cron → Data Activator evaluation frequency)
  - Delivery channels (email, dashboard notification → Teams, email, Power Automate)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAC Agent / Alert data types
# ---------------------------------------------------------------------------


@dataclass
class OACAlertCondition:
    """A condition in an OAC agent alert."""

    measure: str
    operator: str           # gt, lt, eq, gte, lte, between, topN, bottomN
    threshold: float | None = None
    threshold_high: float | None = None  # for 'between'
    top_n: int | None = None             # for topN/bottomN


@dataclass
class OACAlertSchedule:
    """Schedule for OAC agent execution."""

    frequency: str = "daily"      # daily, weekly, monthly, hourly, custom
    cron_expression: str = ""     # raw OAC cron
    time_of_day: str = "08:00"
    day_of_week: str | None = None
    day_of_month: int | None = None


@dataclass
class OACAlertDelivery:
    """Delivery configuration for OAC agent alert."""

    channel: str = "email"        # email, dashboard, sms, custom
    recipients: list[str] = field(default_factory=list)
    subject: str = ""
    message_template: str = ""


@dataclass
class OACAgentDefinition:
    """Complete OAC agent/alert definition."""

    name: str
    description: str = ""
    subject_area: str = ""
    conditions: list[OACAlertCondition] = field(default_factory=list)
    schedule: OACAlertSchedule = field(default_factory=OACAlertSchedule)
    delivery: OACAlertDelivery = field(default_factory=OACAlertDelivery)
    enabled: bool = True
    priority: str = "normal"      # low, normal, high, critical


# ---------------------------------------------------------------------------
# Data Activator trigger types
# ---------------------------------------------------------------------------


@dataclass
class ActivatorCondition:
    """A Data Activator trigger condition."""

    property_name: str
    operator: str           # GreaterThan, LessThan, Equals, Between, TopN, BottomN
    threshold: float | None = None
    threshold_high: float | None = None
    top_n: int | None = None


@dataclass
class ActivatorAction:
    """An action to perform when trigger fires."""

    action_type: str        # Email, Teams, PowerAutomate
    recipients: list[str] = field(default_factory=list)
    subject: str = ""
    body_template: str = ""


@dataclass
class ActivatorTrigger:
    """Fabric Data Activator Reflex trigger definition."""

    name: str
    description: str = ""
    object_type: str = ""        # maps to semantic model table
    conditions: list[ActivatorCondition] = field(default_factory=list)
    actions: list[ActivatorAction] = field(default_factory=list)
    evaluation_frequency: str = "PT1H"  # ISO 8601 duration
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to Data Activator JSON configuration."""
        return {
            "name": self.name,
            "description": self.description,
            "objectType": self.object_type,
            "conditions": [
                {
                    "property": c.property_name,
                    "operator": c.operator,
                    "threshold": c.threshold,
                    "thresholdHigh": c.threshold_high,
                    "topN": c.top_n,
                }
                for c in self.conditions
            ],
            "actions": [
                {
                    "type": a.action_type,
                    "recipients": a.recipients,
                    "subject": a.subject,
                    "bodyTemplate": a.body_template,
                }
                for a in self.actions
            ],
            "evaluationFrequency": self.evaluation_frequency,
            "enabled": self.enabled,
        }


@dataclass
class AlertMigrationResult:
    """Result of migrating OAC alerts to Data Activator."""

    triggers: list[ActivatorTrigger] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Operator mapping
# ---------------------------------------------------------------------------

_OPERATOR_MAP: dict[str, str] = {
    "gt": "GreaterThan",
    ">": "GreaterThan",
    "gte": "GreaterThanOrEqual",
    ">=": "GreaterThanOrEqual",
    "lt": "LessThan",
    "<": "LessThan",
    "lte": "LessThanOrEqual",
    "<=": "LessThanOrEqual",
    "eq": "Equals",
    "=": "Equals",
    "==": "Equals",
    "between": "Between",
    "topn": "TopN",
    "top-n": "TopN",
    "bottomn": "BottomN",
    "bottom-n": "BottomN",
}

# ---------------------------------------------------------------------------
# Schedule mapping
# ---------------------------------------------------------------------------

_FREQUENCY_TO_ISO: dict[str, str] = {
    "hourly": "PT1H",
    "daily": "PT24H",
    "weekly": "P7D",
    "monthly": "P30D",
    "every_15_min": "PT15M",
    "every_30_min": "PT30M",
    "every_6_hours": "PT6H",
    "every_12_hours": "PT12H",
}


def _map_schedule(schedule: OACAlertSchedule) -> str:
    """Map OAC schedule to ISO 8601 duration for Data Activator."""
    freq = schedule.frequency.lower().replace(" ", "_")
    iso = _FREQUENCY_TO_ISO.get(freq)
    if iso:
        return iso

    # Try to parse cron for common patterns
    if schedule.cron_expression:
        cron = schedule.cron_expression.strip()
        if cron.startswith("0 */"):
            match = re.match(r"0 \*/(\d+)", cron)
            if match:
                hours = int(match.group(1))
                return f"PT{hours}H"

    logger.warning("Unknown schedule frequency '%s' — defaulting to PT24H", freq)
    return "PT24H"


# ---------------------------------------------------------------------------
# Channel mapping
# ---------------------------------------------------------------------------

_CHANNEL_MAP: dict[str, str] = {
    "email": "Email",
    "dashboard": "Teams",
    "sms": "PowerAutomate",
    "custom": "PowerAutomate",
    "teams": "Teams",
    "notification": "Teams",
}


# ---------------------------------------------------------------------------
# Core migration logic
# ---------------------------------------------------------------------------


def _map_condition(oac_cond: OACAlertCondition) -> ActivatorCondition:
    """Map a single OAC alert condition to Activator condition."""
    operator = _OPERATOR_MAP.get(oac_cond.operator.lower(), "GreaterThan")
    return ActivatorCondition(
        property_name=oac_cond.measure,
        operator=operator,
        threshold=oac_cond.threshold,
        threshold_high=oac_cond.threshold_high,
        top_n=oac_cond.top_n,
    )


def _map_delivery(delivery: OACAlertDelivery, alert_name: str) -> ActivatorAction:
    """Map OAC delivery config to Activator action."""
    action_type = _CHANNEL_MAP.get(delivery.channel.lower(), "Email")
    subject = delivery.subject or f"Alert: {alert_name}"
    body = delivery.message_template or (
        f"Alert '{alert_name}' has been triggered. Please review the data."
    )
    return ActivatorAction(
        action_type=action_type,
        recipients=list(delivery.recipients),
        subject=subject,
        body_template=body,
    )


def migrate_alert(agent_def: OACAgentDefinition) -> ActivatorTrigger:
    """Migrate a single OAC agent/alert to Data Activator trigger.

    Parameters
    ----------
    agent_def : OACAgentDefinition
        OAC alert definition.

    Returns
    -------
    ActivatorTrigger
        Fabric Data Activator trigger configuration.
    """
    conditions = [_map_condition(c) for c in agent_def.conditions]
    action = _map_delivery(agent_def.delivery, agent_def.name)
    eval_freq = _map_schedule(agent_def.schedule)

    return ActivatorTrigger(
        name=agent_def.name,
        description=agent_def.description,
        object_type=agent_def.subject_area,
        conditions=conditions,
        actions=[action],
        evaluation_frequency=eval_freq,
        enabled=agent_def.enabled,
    )


def migrate_all_alerts(
    agents: list[OACAgentDefinition],
) -> AlertMigrationResult:
    """Migrate all OAC agents/alerts to Data Activator triggers.

    Parameters
    ----------
    agents : list[OACAgentDefinition]
        OAC agent definitions.

    Returns
    -------
    AlertMigrationResult
        All migrated triggers with warnings.
    """
    result = AlertMigrationResult()

    for agent_def in agents:
        if not agent_def.conditions:
            result.skipped.append(f"{agent_def.name}: no conditions defined")
            result.warnings.append(
                f"Agent '{agent_def.name}' has no conditions — skipped"
            )
            continue

        try:
            trigger = migrate_alert(agent_def)
            result.triggers.append(trigger)
        except Exception:
            logger.exception("Failed to migrate alert '%s'", agent_def.name)
            result.warnings.append(f"Failed to migrate '{agent_def.name}'")
            result.skipped.append(agent_def.name)

    logger.info(
        "Migrated %d/%d alerts to Data Activator triggers (%d skipped)",
        len(result.triggers),
        len(agents),
        len(result.skipped),
    )
    return result
