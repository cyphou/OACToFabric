"""Activator Config — Fabric Data Activator Reflex deployment configuration.

Generates the JSON payload required to create and configure a Data Activator
Reflex item in a Fabric workspace, including object streams, triggers,
and action bindings.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .alert_migrator import ActivatorTrigger

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reflex configuration types
# ---------------------------------------------------------------------------


@dataclass
class ObjectStream:
    """A Data Activator object stream connected to a semantic model."""

    name: str
    semantic_model_id: str = ""
    table_name: str = ""
    key_column: str = ""
    timestamp_column: str = ""
    properties: list[str] = field(default_factory=list)


@dataclass
class ReflexConfig:
    """Complete Data Activator Reflex configuration."""

    reflex_name: str
    workspace_id: str = ""
    description: str = ""
    object_streams: list[ObjectStream] = field(default_factory=list)
    triggers: list[ActivatorTrigger] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to Fabric REST API payload format."""
        return {
            "displayName": self.reflex_name,
            "description": self.description,
            "type": "Reflex",
            "definition": {
                "parts": [
                    {
                        "path": "reflex.json",
                        "payload": json.dumps({
                            "objectStreams": [
                                {
                                    "name": s.name,
                                    "dataSource": {
                                        "type": "SemanticModel",
                                        "semanticModelId": s.semantic_model_id,
                                        "table": s.table_name,
                                    },
                                    "keyColumn": s.key_column,
                                    "timestampColumn": s.timestamp_column,
                                    "properties": s.properties,
                                }
                                for s in self.object_streams
                            ],
                            "triggers": [t.to_dict() for t in self.triggers],
                        }),
                        "payloadType": "InlineBase64",
                    }
                ]
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------


def generate_reflex_config(
    name: str,
    triggers: list[ActivatorTrigger],
    semantic_model_id: str = "",
    workspace_id: str = "",
    table_name: str = "",
    key_column: str = "Id",
    timestamp_column: str = "Date",
) -> ReflexConfig:
    """Generate a Data Activator Reflex configuration from migrated triggers.

    Parameters
    ----------
    name : str
        Reflex display name.
    triggers : list[ActivatorTrigger]
        Migrated triggers from ``alert_migrator``.
    semantic_model_id : str
        Target semantic model ID in Fabric.
    workspace_id : str
        Target workspace ID.
    table_name : str
        Default table name for object streams.
    key_column : str
        Key column for object identification.
    timestamp_column : str
        Timestamp column for event ordering.

    Returns
    -------
    ReflexConfig
        Complete Reflex configuration ready for deployment.
    """
    # Build object streams from trigger object types
    streams: list[ObjectStream] = []
    seen_types: set[str] = set()

    for trigger in triggers:
        obj_type = trigger.object_type or table_name or "DefaultObject"
        if obj_type in seen_types:
            continue
        seen_types.add(obj_type)

        # Collect all properties referenced in conditions
        props: list[str] = []
        for cond in trigger.conditions:
            if cond.property_name and cond.property_name not in props:
                props.append(cond.property_name)

        streams.append(ObjectStream(
            name=obj_type,
            semantic_model_id=semantic_model_id,
            table_name=obj_type,
            key_column=key_column,
            timestamp_column=timestamp_column,
            properties=props,
        ))

    config = ReflexConfig(
        reflex_name=name,
        workspace_id=workspace_id,
        description=f"Migrated from OAC alerts — {len(triggers)} triggers",
        object_streams=streams,
        triggers=list(triggers),
    )

    logger.info(
        "Generated Reflex config '%s': %d streams, %d triggers",
        name,
        len(streams),
        len(triggers),
    )
    return config
