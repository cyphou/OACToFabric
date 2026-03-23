"""Resilience utilities — edge-case handling for production migrations.

Covers:
- **Unicode normalization**: Sanitize OAC asset names with special chars.
- **Circular dependency detection**: Detect and break cycles in data models.
- **Concurrent run locking**: Prevent multiple migration runs from colliding.
- **Rate-limit backoff**: Adaptive backoff for Fabric/OAC API throttling.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unicode / special character normalization
# ---------------------------------------------------------------------------


def normalize_name(name: str, *, max_length: int = 128) -> str:
    """Normalize an OAC asset name for Fabric/PBI compatibility.

    1. Unicode NFC normalization.
    2. Replace non-ASCII chars with closest ASCII equivalent.
    3. Replace special chars with underscores.
    4. Collapse multiple underscores.
    5. Truncate to *max_length*.
    """
    if not name:
        return ""

    # NFC normalization
    normalized = unicodedata.normalize("NFC", name)

    # Transliterate to ASCII (best-effort)
    ascii_name = unicodedata.normalize("NFKD", normalized)
    ascii_name = ascii_name.encode("ascii", "ignore").decode("ascii")

    # Replace non-alphanumeric chars (except underscore, hyphen, dot)
    clean = re.sub(r"[^\w\-.]", "_", ascii_name)

    # Collapse multiple underscores
    clean = re.sub(r"_+", "_", clean)

    # Strip leading/trailing underscores
    clean = clean.strip("_")

    # Truncate
    if len(clean) > max_length:
        clean = clean[:max_length].rstrip("_")

    return clean or "unnamed"


def sanitize_identifier(name: str) -> str:
    """Convert a name into a valid SQL/DAX identifier.

    - Must start with a letter or underscore.
    - Only alphanumeric + underscore allowed.
    - Reserved words get a trailing underscore.
    """
    clean = normalize_name(name)
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", clean)

    if clean and not clean[0].isalpha() and clean[0] != "_":
        clean = "_" + clean

    # Avoid SQL reserved words (representative subset)
    _reserved = {
        "select", "from", "where", "table", "create", "drop",
        "insert", "update", "delete", "index", "order", "group",
        "having", "join", "on", "and", "or", "not", "null",
        "true", "false", "as", "is", "in", "like", "between",
    }
    if clean.lower() in _reserved:
        clean = clean + "_"

    return clean or "_unnamed"


# ---------------------------------------------------------------------------
# Circular dependency detection
# ---------------------------------------------------------------------------


def detect_cycles(
    edges: list[tuple[str, str]],
) -> list[list[str]]:
    """Detect all cycles in a directed graph.

    Parameters
    ----------
    edges
        List of (source, target) tuples representing dependencies.

    Returns
    -------
    list[list[str]]
        Each inner list is a cycle: [A, B, C, A] means A→B→C→A.
        Returns empty list if no cycles exist.
    """
    # Build adjacency list
    adj: dict[str, list[str]] = {}
    all_nodes: set[str] = set()
    for src, tgt in edges:
        adj.setdefault(src, []).append(tgt)
        all_nodes.add(src)
        all_nodes.add(tgt)

    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def _dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                _dfs(neighbor)
            elif neighbor in rec_stack:
                # Found a cycle — extract it
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.discard(node)

    for node in sorted(all_nodes):
        if node not in visited:
            _dfs(node)

    return cycles


def break_cycles(
    edges: list[tuple[str, str]],
    priority: dict[str, int] | None = None,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Break cycles by removing the lowest-priority edge in each cycle.

    Parameters
    ----------
    edges
        All directed edges.
    priority
        Node priority map (higher = more important to keep edges for).

    Returns
    -------
    (kept_edges, removed_edges)
    """
    pri = priority or {}
    removed: list[tuple[str, str]] = []
    working = list(edges)

    while True:
        cycles = detect_cycles(working)
        if not cycles:
            break

        # Take the first cycle, remove the edge with lowest-priority target
        cycle = cycles[0]
        # cycle = [A, B, C, A] — edges are (A,B), (B,C), (C,A)
        cycle_edges = [
            (cycle[i], cycle[i + 1]) for i in range(len(cycle) - 1)
        ]

        # Remove edge with lowest-priority source node
        edge_to_remove = min(
            cycle_edges,
            key=lambda e: pri.get(e[0], 0),
        )
        working.remove(edge_to_remove)
        removed.append(edge_to_remove)
        logger.warning(
            "Breaking cycle: removed edge %s → %s",
            edge_to_remove[0],
            edge_to_remove[1],
        )

    return working, removed


# ---------------------------------------------------------------------------
# Concurrent run locking
# ---------------------------------------------------------------------------


class MigrationLock:
    """File-based migration lock to prevent concurrent runs.

    Uses a lock file in the output directory.  The lock contains
    metadata about the owning run for diagnostics.
    """

    _LOCK_FILENAME = ".migration.lock"

    def __init__(self, output_dir: Path | str) -> None:
        self._dir = Path(output_dir)
        self._lock_path = self._dir / self._LOCK_FILENAME
        self._acquired = False

    @property
    def is_locked(self) -> bool:
        """Check if a lock file exists."""
        return self._lock_path.exists()

    def acquire(
        self,
        run_id: str,
        *,
        force: bool = False,
    ) -> bool:
        """Acquire the migration lock.

        Returns True if lock was acquired, False if already held.
        Pass ``force=True`` to break an existing lock.
        """
        if self._lock_path.exists() and not force:
            existing = self._read_lock()
            logger.error(
                "Migration lock held by run '%s' (since %s). "
                "Use --force to override.",
                existing.get("run_id", "unknown"),
                existing.get("acquired_at", "unknown"),
            )
            return False

        self._dir.mkdir(parents=True, exist_ok=True)
        lock_data = {
            "run_id": run_id,
            "acquired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pid": _safe_pid(),
        }
        self._lock_path.write_text(
            json.dumps(lock_data, indent=2), encoding="utf-8"
        )
        self._acquired = True
        logger.info("Migration lock acquired: %s", run_id)
        return True

    def release(self) -> None:
        """Release the migration lock."""
        if self._lock_path.exists():
            self._lock_path.unlink()
            logger.info("Migration lock released")
        self._acquired = False

    def _read_lock(self) -> dict[str, Any]:
        try:
            return json.loads(
                self._lock_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            return {}

    def __enter__(self) -> MigrationLock:
        return self

    def __exit__(self, *args: Any) -> None:
        if self._acquired:
            self.release()


def _safe_pid() -> int:
    """Get current PID safely."""
    import os
    return os.getpid()


# ---------------------------------------------------------------------------
# Adaptive rate-limit backoff
# ---------------------------------------------------------------------------


class AdaptiveBackoff:
    """Adaptive exponential backoff for API rate limiting.

    Tracks consecutive failures and adjusts delay accordingly.
    Successful calls reset the backoff counter.
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: float = 0.1,
    ) -> None:
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self._consecutive_failures = 0
        self._total_retries = 0

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def total_retries(self) -> int:
        return self._total_retries

    def next_delay(self) -> float:
        """Calculate the next backoff delay in seconds."""
        delay = self.base_delay * (self.multiplier ** self._consecutive_failures)
        delay = min(delay, self.max_delay)
        return delay

    def record_failure(self) -> float:
        """Record a failure and return the recommended delay."""
        self._consecutive_failures += 1
        self._total_retries += 1
        delay = self.next_delay()
        logger.debug(
            "Backoff: failure #%d, next delay=%.1fs",
            self._consecutive_failures,
            delay,
        )
        return delay

    def record_success(self) -> None:
        """Record a success — reset the consecutive failure counter."""
        self._consecutive_failures = 0

    def reset(self) -> None:
        """Full reset of all counters."""
        self._consecutive_failures = 0
        self._total_retries = 0
