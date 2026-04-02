"""Handoff protocol — structured inter-agent communication — Phase 73.

Replaces implicit data-passing via Delta table reads with a formal typed
message bus so agents can negotiate, share context, raise issues, and resolve
cross-domain conflicts.

Message types:
- ARTIFACT_READY — agent finished, artifact available for downstream.
- DEPENDENCY_REQUEST — agent needs data from another agent.
- CONFLICT — incompatible decisions (e.g. storage mode disagreement).
- CONTEXT_SHARE — background info for downstream agents.
- ESCALATION — unresolvable issue requiring human intervention.

Usage::

    bus = MessageBus()
    bus.send(HandoffMessage(
        sender_agent="02-schema",
        receiver_agent="04-semantic",
        message_type=MessageType.ARTIFACT_READY,
        payload={"tables": ["Fact_Sales", "Dim_Product"]},
    ))
    messages = bus.receive("04-semantic")
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------


class MessageType(str, Enum):
    ARTIFACT_READY = "artifact_ready"
    DEPENDENCY_REQUEST = "dependency_request"
    CONFLICT = "conflict"
    CONTEXT_SHARE = "context_share"
    ESCALATION = "escalation"
    ACKNOWLEDGMENT = "acknowledgment"


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"


@dataclass
class HandoffMessage:
    """A typed message between agents."""

    sender_agent: str
    receiver_agent: str
    message_type: MessageType
    payload: dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    requires_response: bool = False
    message_id: str = ""
    correlation_id: str = ""  # Links related messages
    status: MessageStatus = MessageStatus.PENDING
    timestamp: float = 0.0
    summary: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.message_id:
            self.message_id = f"msg_{self.sender_agent}_{int(self.timestamp * 1000)}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.message_id,
            "sender": self.sender_agent,
            "receiver": self.receiver_agent,
            "type": self.message_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "summary": self.summary,
            "requires_response": self.requires_response,
            "correlation_id": self.correlation_id,
            "payload_keys": list(self.payload.keys()),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Message bus
# ---------------------------------------------------------------------------


class MessageBus:
    """In-memory message bus for agent communication.

    In production, backed by the Lakehouse ``handoff_messages`` Delta table.
    The in-memory implementation supports development and testing.
    """

    def __init__(self) -> None:
        self._inbox: dict[str, list[HandoffMessage]] = defaultdict(list)
        self._all_messages: list[HandoffMessage] = []
        self._message_index: dict[str, HandoffMessage] = {}

    def send(self, message: HandoffMessage) -> str:
        """Send a message to the receiver agent's inbox.

        Returns the message ID.
        """
        self._inbox[message.receiver_agent].append(message)
        self._all_messages.append(message)
        self._message_index[message.message_id] = message
        message.status = MessageStatus.DELIVERED

        logger.info(
            "Message %s: %s → %s [%s] %s",
            message.message_id,
            message.sender_agent,
            message.receiver_agent,
            message.message_type.value,
            message.summary or "(no summary)",
        )
        return message.message_id

    def receive(
        self,
        agent_id: str,
        message_type: MessageType | None = None,
        priority: MessagePriority | None = None,
    ) -> list[HandoffMessage]:
        """Receive messages for an agent, optionally filtered.

        Messages are returned in priority order (critical first).
        """
        inbox = self._inbox.get(agent_id, [])
        messages = [m for m in inbox if m.status == MessageStatus.DELIVERED]

        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        if priority:
            messages = [m for m in messages if m.priority == priority]

        # Sort by priority (critical > high > normal > low)
        priority_order = {
            MessagePriority.CRITICAL: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 3,
        }
        messages.sort(key=lambda m: (priority_order.get(m.priority, 99), m.timestamp))

        return messages

    def acknowledge(self, message_id: str) -> bool:
        """Acknowledge receipt of a message."""
        msg = self._message_index.get(message_id)
        if msg:
            msg.status = MessageStatus.ACKNOWLEDGED
            return True
        return False

    def resolve(self, message_id: str, resolution_payload: dict[str, Any] | None = None) -> bool:
        """Mark a message as resolved."""
        msg = self._message_index.get(message_id)
        if msg:
            msg.status = MessageStatus.RESOLVED
            if resolution_payload:
                msg.payload["resolution"] = resolution_payload
            return True
        return False

    def get_unresolved(self, agent_id: str | None = None) -> list[HandoffMessage]:
        """Get all unresolved messages, optionally for a specific agent."""
        messages = self._all_messages
        if agent_id:
            messages = [m for m in messages if m.receiver_agent == agent_id]
        return [m for m in messages if m.status not in (MessageStatus.RESOLVED, MessageStatus.EXPIRED)]

    def get_conflicts(self) -> list[HandoffMessage]:
        """Get all unresolved conflict messages."""
        return [
            m for m in self._all_messages
            if m.message_type == MessageType.CONFLICT
            and m.status not in (MessageStatus.RESOLVED, MessageStatus.EXPIRED)
        ]

    def get_escalations(self) -> list[HandoffMessage]:
        """Get all unresolved escalation messages."""
        return [
            m for m in self._all_messages
            if m.message_type == MessageType.ESCALATION
            and m.status not in (MessageStatus.RESOLVED, MessageStatus.EXPIRED)
        ]

    @property
    def total_messages(self) -> int:
        return len(self._all_messages)

    @property
    def pending_count(self) -> int:
        return sum(1 for m in self._all_messages if m.status in (MessageStatus.PENDING, MessageStatus.DELIVERED))

    def get_message(self, message_id: str) -> HandoffMessage | None:
        return self._message_index.get(message_id)

    def get_conversation(self, correlation_id: str) -> list[HandoffMessage]:
        """Get all messages in a conversation thread."""
        return sorted(
            [m for m in self._all_messages if m.correlation_id == correlation_id],
            key=lambda m: m.timestamp,
        )


# ---------------------------------------------------------------------------
# Conflict resolver
# ---------------------------------------------------------------------------


@dataclass
class ConflictResolution:
    """Resolution of a cross-agent conflict."""

    conflict_message_id: str
    resolution: str
    chosen_option: str
    confidence: float = 0.0
    reasoning: str = ""
    requires_human_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_message_id,
            "resolution": self.resolution,
            "chosen_option": self.chosen_option,
            "confidence": self.confidence,
            "requires_human_review": self.requires_human_review,
        }


class ConflictResolver:
    """Resolve cross-agent conflicts using rules and optional LLM.

    Known conflict patterns:
    - Storage mode disagreement (Import vs DirectLake).
    - Naming collision between agents.
    - Incompatible relationship directions.
    - RLS scope overlap.
    """

    def __init__(self, reasoning_loop: Any = None) -> None:
        self._reasoning = reasoning_loop

    def resolve(self, conflict: HandoffMessage) -> ConflictResolution:
        """Attempt rule-based conflict resolution."""
        payload = conflict.payload
        conflict_type = payload.get("conflict_type", "")

        # Rule-based resolutions
        if conflict_type == "storage_mode":
            return self._resolve_storage_mode(conflict)
        if conflict_type == "naming_collision":
            return self._resolve_naming(conflict)
        if conflict_type == "relationship_direction":
            return self._resolve_relationship(conflict)

        # Unknown conflict → escalate
        return ConflictResolution(
            conflict_message_id=conflict.message_id,
            resolution="Unable to resolve automatically — escalating to human review",
            chosen_option="escalate",
            confidence=0.0,
            requires_human_review=True,
        )

    async def resolve_with_llm(self, conflict: HandoffMessage) -> ConflictResolution:
        """Attempt LLM-powered resolution for complex conflicts."""
        # Try rules first
        resolution = self.resolve(conflict)
        if not resolution.requires_human_review:
            return resolution

        if self._reasoning:
            try:
                result = await self._reasoning.run(
                    task="resolve_conflict",
                    source=str(conflict.payload),
                    context={
                        "sender": conflict.sender_agent,
                        "receiver": conflict.receiver_agent,
                        "type": conflict.payload.get("conflict_type", ""),
                    },
                )
                if result.success and result.output:
                    return ConflictResolution(
                        conflict_message_id=conflict.message_id,
                        resolution=str(result.output),
                        chosen_option="llm_recommended",
                        confidence=result.confidence,
                        reasoning=str(result.output),
                        requires_human_review=result.confidence < 0.7,
                    )
            except Exception:
                logger.debug("LLM conflict resolution failed")

        return resolution

    @staticmethod
    def _resolve_storage_mode(conflict: HandoffMessage) -> ConflictResolution:
        """Resolve storage mode conflict — prefer DirectLake when possible."""
        options = conflict.payload.get("options", {})
        has_lakehouse = options.get("has_lakehouse", False)

        if has_lakehouse:
            return ConflictResolution(
                conflict_message_id=conflict.message_id,
                resolution="Use DirectLake mode — Lakehouse data available",
                chosen_option="direct_lake",
                confidence=0.9,
                reasoning="Lakehouse tables exist, DirectLake provides best query performance",
            )
        return ConflictResolution(
            conflict_message_id=conflict.message_id,
            resolution="Use Import mode — no Lakehouse data available",
            chosen_option="import",
            confidence=0.8,
            reasoning="No Lakehouse tables found, Import is the safest default",
        )

    @staticmethod
    def _resolve_naming(conflict: HandoffMessage) -> ConflictResolution:
        """Resolve naming collision — suffix with agent domain."""
        name = conflict.payload.get("name", "unknown")
        agent = conflict.sender_agent
        return ConflictResolution(
            conflict_message_id=conflict.message_id,
            resolution=f"Suffix with source agent: {name}_{agent}",
            chosen_option=f"{name}_{agent}",
            confidence=0.85,
            reasoning="Naming collision resolved by appending source agent identifier",
        )

    @staticmethod
    def _resolve_relationship(conflict: HandoffMessage) -> ConflictResolution:
        """Resolve relationship direction — prefer many-to-one."""
        return ConflictResolution(
            conflict_message_id=conflict.message_id,
            resolution="Use many-to-one relationship direction (standard star schema)",
            chosen_option="many_to_one",
            confidence=0.9,
            reasoning="Many-to-one is the standard Power BI star schema pattern",
        )


# ---------------------------------------------------------------------------
# Context window builder
# ---------------------------------------------------------------------------


class ContextWindow:
    """Aggregates context from upstream agents into a priority-ranked window.

    Ensures the total context fits within LLM token limits by truncating
    lower-priority items first.
    """

    def __init__(self, max_tokens: int = 8000) -> None:
        self._max_tokens = max_tokens
        self._entries: list[tuple[int, str, str]] = []  # (priority, label, content)

    def add(self, label: str, content: str, priority: int = 5) -> None:
        """Add context with priority (1 = highest, 10 = lowest)."""
        self._entries.append((priority, label, content))

    def build(self) -> str:
        """Build the context string within token limits."""
        self._entries.sort(key=lambda e: e[0])

        sections: list[str] = []
        total_chars = 0
        char_limit = self._max_tokens * 4  # Rough char-to-token ratio

        for _priority, label, content in self._entries:
            section = f"### {label}\n{content}\n"
            if total_chars + len(section) > char_limit:
                remaining = char_limit - total_chars
                if remaining > 100:
                    sections.append(f"### {label}\n{content[:remaining]}...\n")
                break
            sections.append(section)
            total_chars += len(section)

        return "\n".join(sections)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
