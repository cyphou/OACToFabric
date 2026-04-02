"""Human-in-the-Loop escalation — confidence routing and review UI — Phase 75.

Provides a structured escalation system where low-confidence LLM outputs,
unresolvable conflicts, and self-healing failures route to a human review
queue with full context for fast decision-making.

Components:
- ``EscalationQueue`` — priority queue of items needing human review.
- ``ReviewItem`` — a single escalation with context and suggested actions.
- ``FeedbackCollector`` — captures human decisions to improve future runs.

Usage::

    queue = EscalationQueue()
    queue.escalate(ReviewItem(
        asset_id="table_123",
        reason="DAX translation confidence 0.45 — below threshold",
        suggested_actions=["approve_as_is", "edit_manually", "skip"],
    ))
    pending = queue.get_pending()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    VALIDATION_FAILURE = "validation_failure"
    CONFLICT_UNRESOLVED = "conflict_unresolved"
    HEALING_FAILED = "healing_failed"
    SECURITY_REVIEW = "security_review"
    DATA_QUALITY = "data_quality"
    UNKNOWN_PATTERN = "unknown_pattern"


class ReviewAction(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"
    SKIP = "skip"
    RETRY = "retry"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


@dataclass
class ReviewItem:
    """A single item requiring human review."""

    item_id: str = ""
    asset_id: str = ""
    agent_id: str = ""
    reason: EscalationReason = EscalationReason.LOW_CONFIDENCE
    description: str = ""
    severity: str = "medium"  # low / medium / high / critical
    context: dict[str, Any] = field(default_factory=dict)
    suggested_actions: list[ReviewAction] = field(default_factory=list)
    source_expression: str = ""
    generated_output: str = ""
    confidence: float = 0.0
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer: str = ""
    resolution_action: ReviewAction | None = None
    resolution_notes: str = ""
    created_at: float = 0.0
    resolved_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        if not self.item_id:
            self.item_id = f"review_{self.asset_id}_{int(self.created_at * 1000)}"
        if not self.suggested_actions:
            self.suggested_actions = [ReviewAction.APPROVE, ReviewAction.EDIT, ReviewAction.SKIP]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.item_id,
            "asset_id": self.asset_id,
            "agent_id": self.agent_id,
            "reason": self.reason.value,
            "severity": self.severity,
            "description": self.description,
            "confidence": self.confidence,
            "status": self.status.value,
            "actions": [a.value for a in self.suggested_actions],
            "resolution": self.resolution_action.value if self.resolution_action else None,
        }


# ---------------------------------------------------------------------------
# Escalation queue
# ---------------------------------------------------------------------------


class EscalationQueue:
    """Priority queue for human review items.

    Items are sorted by severity (critical first) and then by creation time.
    """

    def __init__(self) -> None:
        self._items: list[ReviewItem] = []
        self._index: dict[str, ReviewItem] = {}

    def escalate(self, item: ReviewItem) -> str:
        """Add an item to the escalation queue.

        Returns the item ID.
        """
        self._items.append(item)
        self._index[item.item_id] = item

        logger.info(
            "Escalated %s: %s [%s] — %s",
            item.item_id,
            item.reason.value,
            item.severity,
            item.description[:100],
        )
        return item.item_id

    def get_pending(
        self,
        severity: str | None = None,
        reason: EscalationReason | None = None,
        agent_id: str | None = None,
    ) -> list[ReviewItem]:
        """Get pending review items, optionally filtered."""
        items = [i for i in self._items if i.status == ReviewStatus.PENDING]

        if severity:
            items = [i for i in items if i.severity == severity]
        if reason:
            items = [i for i in items if i.reason == reason]
        if agent_id:
            items = [i for i in items if i.agent_id == agent_id]

        # Sort by severity then time
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda i: (severity_order.get(i.severity, 99), i.created_at))

        return items

    def resolve(
        self,
        item_id: str,
        action: ReviewAction,
        reviewer: str = "",
        notes: str = "",
    ) -> bool:
        """Resolve a review item with a human decision."""
        item = self._index.get(item_id)
        if not item:
            return False

        item.status = ReviewStatus.RESOLVED
        item.resolution_action = action
        item.reviewer = reviewer
        item.resolution_notes = notes
        item.resolved_at = time.time()

        logger.info(
            "Resolved %s: action=%s by=%s",
            item_id, action.value, reviewer or "system",
        )
        return True

    def defer(self, item_id: str) -> bool:
        """Defer an item for later review."""
        item = self._index.get(item_id)
        if not item:
            return False
        item.status = ReviewStatus.DEFERRED
        return True

    def get_item(self, item_id: str) -> ReviewItem | None:
        return self._index.get(item_id)

    @property
    def total_items(self) -> int:
        return len(self._items)

    @property
    def pending_count(self) -> int:
        return sum(1 for i in self._items if i.status == ReviewStatus.PENDING)

    @property
    def resolved_count(self) -> int:
        return sum(1 for i in self._items if i.status == ReviewStatus.RESOLVED)

    def get_stats(self) -> dict[str, int]:
        """Get queue statistics."""
        stats: dict[str, int] = {}
        for item in self._items:
            stats[item.status.value] = stats.get(item.status.value, 0) + 1
        return stats


# ---------------------------------------------------------------------------
# Feedback collector
# ---------------------------------------------------------------------------


@dataclass
class FeedbackEntry:
    """A human feedback entry for training improvement."""

    item_id: str
    action_taken: ReviewAction
    source_expression: str = ""
    approved_output: str = ""
    notes: str = ""
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "action": self.action_taken.value,
            "source": self.source_expression[:200],
            "output": self.approved_output[:200],
            "notes": self.notes,
        }


class FeedbackCollector:
    """Collects human feedback to improve future translations.

    Approved translations can be added to the translation cache.
    Rejected patterns help train better prompts.

    Parameters
    ----------
    agent_memory
        Optional agent memory for persisting feedback.
    translation_cache
        Optional translation cache for storing approved translations.
    """

    def __init__(
        self,
        agent_memory: Any = None,
        translation_cache: Any = None,
    ) -> None:
        self._memory = agent_memory
        self._cache = translation_cache
        self._entries: list[FeedbackEntry] = []

    def record(
        self,
        item: ReviewItem,
        action: ReviewAction,
        approved_output: str = "",
        notes: str = "",
    ) -> FeedbackEntry:
        """Record human feedback for a review item."""
        entry = FeedbackEntry(
            item_id=item.item_id,
            action_taken=action,
            source_expression=item.source_expression,
            approved_output=approved_output or item.generated_output,
            notes=notes,
        )
        self._entries.append(entry)

        # If approved, add to translation cache
        if action == ReviewAction.APPROVE and self._cache and item.source_expression:
            self._cache.store(
                item.source_expression,
                approved_output or item.generated_output,
                confidence=1.0,  # Human-approved = max confidence
            )

        # Persist to memory
        if self._memory:
            self._memory.store(
                "human_feedback",
                key=item.item_id,
                value=entry.to_dict(),
                confidence=1.0,
            )

        logger.info(
            "Feedback recorded: %s → %s",
            item.item_id, action.value,
        )
        return entry

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    @property
    def approval_rate(self) -> float:
        if not self._entries:
            return 0.0
        approved = sum(1 for e in self._entries if e.action_taken == ReviewAction.APPROVE)
        return approved / len(self._entries)

    def get_approved(self) -> list[FeedbackEntry]:
        """Get all approved feedback entries (useful for training)."""
        return [e for e in self._entries if e.action_taken == ReviewAction.APPROVE]

    def get_rejected(self) -> list[FeedbackEntry]:
        """Get all rejected feedback entries (useful for negative examples)."""
        return [e for e in self._entries if e.action_taken == ReviewAction.REJECT]
