"""Task Flow Generator — OAC action links → Fabric Translytical Task Flows.

Converts OAC action links and navigation actions (drill-down, drill-through,
URL links, linked analyses) into Fabric Task Flow JSON definitions.

Task Flows in Fabric enable multi-step guided workflows that combine
data exploration with action execution.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAC action link types
# ---------------------------------------------------------------------------


@dataclass
class OACActionLink:
    """An OAC action link (navigate, drill, URL, invoke agent)."""

    name: str
    action_type: str        # navigate, drillDown, drillThrough, url, invokeAgent
    target: str = ""        # target analysis path, URL, or agent name
    parameters: dict[str, str] = field(default_factory=dict)
    source_column: str = ""
    source_analysis: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# Fabric Task Flow types
# ---------------------------------------------------------------------------


@dataclass
class TaskFlowStep:
    """A single step in a Fabric Task Flow."""

    step_id: str
    step_type: str          # OpenReport, RunQuery, SendNotification, NavigateToPage, ApplyFilter
    display_name: str = ""
    target_artifact: str = ""
    parameters: dict[str, str] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.step_id,
            "type": self.step_type,
            "displayName": self.display_name,
            "targetArtifact": self.target_artifact,
            "parameters": self.parameters,
            "dependsOn": self.depends_on,
        }


@dataclass
class TaskFlowDefinition:
    """A Fabric Task Flow definition."""

    name: str
    description: str = ""
    steps: list[TaskFlowStep] = field(default_factory=list)
    entry_point: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "displayName": self.name,
            "description": self.description,
            "entryPoint": self.entry_point or (self.steps[0].step_id if self.steps else ""),
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class TaskFlowGenerationResult:
    """Result of task flow generation."""

    task_flows: list[TaskFlowDefinition] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unmapped_actions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Action type → step type mapping
# ---------------------------------------------------------------------------

_ACTION_TO_STEP_TYPE: dict[str, str] = {
    "navigate": "OpenReport",
    "drilldown": "NavigateToPage",
    "drillthrough": "ApplyFilter",
    "url": "OpenUrl",
    "invokeagent": "SendNotification",
    "executereport": "OpenReport",
    "refresh": "RunQuery",
}


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------


def _generate_step_id(index: int) -> str:
    """Generate a deterministic step ID."""
    return f"step_{index:03d}"


def map_action_to_step(
    action: OACActionLink,
    step_index: int,
    previous_step_id: str | None = None,
) -> TaskFlowStep:
    """Map a single OAC action link to a Task Flow step.

    Parameters
    ----------
    action : OACActionLink
        OAC action link definition.
    step_index : int
        Step sequence number.
    previous_step_id : str | None
        Previous step ID for dependency chaining.

    Returns
    -------
    TaskFlowStep
        Fabric Task Flow step.
    """
    step_type = _ACTION_TO_STEP_TYPE.get(
        action.action_type.lower().replace("_", "").replace("-", ""),
        "OpenReport",
    )

    step_id = _generate_step_id(step_index)
    depends = [previous_step_id] if previous_step_id else []

    params = dict(action.parameters)
    if action.source_column:
        params["sourceColumn"] = action.source_column

    return TaskFlowStep(
        step_id=step_id,
        step_type=step_type,
        display_name=action.name or f"Step {step_index + 1}",
        target_artifact=action.target,
        parameters=params,
        depends_on=depends,
    )


def generate_task_flow(
    name: str,
    actions: list[OACActionLink],
    description: str = "",
) -> TaskFlowDefinition:
    """Generate a Fabric Task Flow from a sequence of OAC action links.

    Parameters
    ----------
    name : str
        Task Flow name.
    actions : list[OACActionLink]
        OAC action links to convert.
    description : str
        Task Flow description.

    Returns
    -------
    TaskFlowDefinition
        Generated Task Flow.
    """
    steps: list[TaskFlowStep] = []
    prev_id: str | None = None

    for i, action in enumerate(actions):
        step = map_action_to_step(action, i, prev_id)
        steps.append(step)
        prev_id = step.step_id

    return TaskFlowDefinition(
        name=name,
        description=description or f"Migrated from OAC actions — {len(steps)} steps",
        steps=steps,
    )


def generate_all_task_flows(
    action_groups: dict[str, list[OACActionLink]],
) -> TaskFlowGenerationResult:
    """Generate Task Flows from grouped OAC action links.

    Parameters
    ----------
    action_groups : dict[str, list[OACActionLink]]
        OAC actions grouped by source analysis name.

    Returns
    -------
    TaskFlowGenerationResult
        All generated task flows.
    """
    result = TaskFlowGenerationResult()

    for group_name, actions in action_groups.items():
        if not actions:
            continue

        unmapped = [
            a for a in actions
            if a.action_type.lower().replace("_", "").replace("-", "")
            not in _ACTION_TO_STEP_TYPE
        ]
        for u in unmapped:
            result.unmapped_actions.append(f"{group_name}/{u.name}: {u.action_type}")
            result.warnings.append(
                f"Unmapped action type '{u.action_type}' in '{group_name}/{u.name}'"
            )

        mappable = [a for a in actions if a not in unmapped]
        if mappable:
            tf = generate_task_flow(group_name, mappable)
            result.task_flows.append(tf)

    logger.info(
        "Generated %d task flows from %d action groups (%d unmapped)",
        len(result.task_flows),
        len(action_groups),
        len(result.unmapped_actions),
    )
    return result
