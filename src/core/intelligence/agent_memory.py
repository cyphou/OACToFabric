"""Agent memory — persistent per-agent memory for cross-task learning.

Each agent accumulates decisions, patterns, and error resolutions across
migration runs.  Memory is stored in-process (dict-backed) and can be
flushed to a Lakehouse Delta table for durability.

Entry types:
- ``decision``  — a translation or mapping choice made by the agent.
- ``pattern``   — a recurring pattern detected (e.g. common OAC idiom).
- ``error``     — an error and its resolution.
- ``context``   — free-form context shared across tasks.

Usage::

    memory = AgentMemory("04-semantic")
    memory.store("decision", key="SUM_Sales", value="SUM(Sales[Amount])", confidence=0.95)
    entries = memory.recall("decision", query="Sales")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Memory entry
# ---------------------------------------------------------------------------


@dataclass
class MemoryEntry:
    """A single memory entry."""

    entry_type: str  # decision, pattern, error, context
    key: str
    value: Any
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 0  # 0 = no expiry
    access_count: int = 0

    @property
    def expired(self) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_type": self.entry_type,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds,
            "access_count": self.access_count,
        }


# ---------------------------------------------------------------------------
# Agent memory store
# ---------------------------------------------------------------------------


class AgentMemory:
    """Per-agent persistent memory.

    Parameters
    ----------
    agent_id
        The owning agent's identifier.
    default_ttl
        Default time-to-live in seconds for new entries (0 = no expiry).
    max_entries
        Maximum entries before oldest are evicted.
    """

    def __init__(
        self,
        agent_id: str,
        *,
        default_ttl: float = 0,
        max_entries: int = 50_000,
    ) -> None:
        self.agent_id = agent_id
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._entries: dict[str, MemoryEntry] = {}  # key → entry

    # ---- store ----

    def store(
        self,
        entry_type: str,
        key: str,
        value: Any,
        *,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
        ttl_seconds: float | None = None,
    ) -> MemoryEntry:
        """Store or update a memory entry."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl

        entry = MemoryEntry(
            entry_type=entry_type,
            key=key,
            value=value,
            confidence=confidence,
            metadata=metadata or {},
            ttl_seconds=ttl,
        )
        self._entries[key] = entry

        # Evict if over capacity
        if len(self._entries) > self._max_entries:
            self._evict_oldest()

        logger.debug(
            "[%s] Stored %s: '%s' (confidence=%.2f)",
            self.agent_id, entry_type, key, confidence,
        )
        return entry

    # ---- recall ----

    def recall(
        self,
        entry_type: str | None = None,
        *,
        query: str = "",
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """Recall memory entries, optionally filtered.

        Parameters
        ----------
        entry_type
            Filter by entry type (decision, pattern, error, context).
        query
            Substring match against the key.
        min_confidence
            Minimum confidence threshold.
        limit
            Maximum entries to return.
        """
        results: list[MemoryEntry] = []
        for entry in self._entries.values():
            if entry.expired:
                continue
            if entry_type and entry.entry_type != entry_type:
                continue
            if min_confidence > 0 and entry.confidence < min_confidence:
                continue
            if query and query.lower() not in entry.key.lower():
                continue
            entry.access_count += 1
            results.append(entry)

        # Sort by confidence descending, then by recency
        results.sort(key=lambda e: (-e.confidence, -e.created_at))
        return results[:limit]

    def get(self, key: str) -> MemoryEntry | None:
        """Get a single entry by exact key.  Returns None if expired or missing."""
        entry = self._entries.get(key)
        if entry is None or entry.expired:
            return None
        entry.access_count += 1
        return entry

    def has(self, key: str) -> bool:
        entry = self._entries.get(key)
        return entry is not None and not entry.expired

    # ---- management ----

    def forget(self, key: str) -> bool:
        """Remove a specific entry."""
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def clear(self, entry_type: str | None = None) -> int:
        """Clear entries, optionally filtered by type.  Returns count removed."""
        if entry_type is None:
            count = len(self._entries)
            self._entries.clear()
            return count

        to_remove = [
            k for k, v in self._entries.items()
            if v.entry_type == entry_type
        ]
        for k in to_remove:
            del self._entries[k]
        return len(to_remove)

    def prune_expired(self) -> int:
        """Remove all expired entries.  Returns count removed."""
        expired = [k for k, v in self._entries.items() if v.expired]
        for k in expired:
            del self._entries[k]
        return len(expired)

    def _evict_oldest(self) -> None:
        """Evict the oldest entry (by created_at) to stay under max_entries."""
        if not self._entries:
            return
        oldest_key = min(self._entries, key=lambda k: self._entries[k].created_at)
        del self._entries[oldest_key]

    # ---- bulk export/import ----

    def export_all(self) -> list[dict[str, Any]]:
        """Export all non-expired entries as dicts (for Delta table persistence)."""
        return [
            {"agent_id": self.agent_id, **e.to_dict()}
            for e in self._entries.values()
            if not e.expired
        ]

    def import_entries(self, rows: list[dict[str, Any]]) -> int:
        """Import entries from dicts (e.g. loaded from Delta table)."""
        count = 0
        for row in rows:
            entry = MemoryEntry(
                entry_type=row.get("entry_type", "context"),
                key=row["key"],
                value=row["value"],
                confidence=row.get("confidence", 1.0),
                metadata=row.get("metadata", {}),
                created_at=row.get("created_at", time.time()),
                ttl_seconds=row.get("ttl_seconds", 0),
                access_count=row.get("access_count", 0),
            )
            if not entry.expired:
                self._entries[entry.key] = entry
                count += 1
        return count

    # ---- properties ----

    @property
    def size(self) -> int:
        return len(self._entries)

    def count_by_type(self) -> dict[str, int]:
        """Count entries grouped by type."""
        counts: dict[str, int] = {}
        for e in self._entries.values():
            if not e.expired:
                counts[e.entry_type] = counts.get(e.entry_type, 0) + 1
        return counts
