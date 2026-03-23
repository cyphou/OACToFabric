"""Checkpoint manager — persist and resume migration progress.

Writes a JSON checkpoint file after each completed wave/agent so that
a migration run can be resumed from the last successful point after
a failure or interruption.

Checkpoint format::

    {
        "run_id": "abc123",
        "started_at": "2025-01-15T10:00:00Z",
        "updated_at": "2025-01-15T10:30:00Z",
        "completed_waves": [1, 2],
        "completed_agents": {
            "1": ["01-discovery", "02-schema"],
            "2": ["03-etl", "04-semantic"]
        },
        "current_wave": 3,
        "status": "in_progress"
    }
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CHECKPOINT_FILENAME = ".checkpoint.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Checkpoint:
    """Serializable migration checkpoint."""

    run_id: str = ""
    started_at: str = ""
    updated_at: str = ""
    completed_waves: list[int] = field(default_factory=list)
    completed_agents: dict[str, list[str]] = field(default_factory=dict)
    current_wave: int = 0
    status: str = "not_started"
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_wave_complete(self, wave_id: int) -> bool:
        """Check if a wave has been fully completed."""
        return wave_id in self.completed_waves

    def is_agent_complete(self, wave_id: int, agent_id: str) -> bool:
        """Check if a specific agent in a wave has been completed."""
        return agent_id in self.completed_agents.get(str(wave_id), [])

    def pending_agents(self, wave_id: int, all_agents: list[str]) -> list[str]:
        """Return agents in a wave that haven't completed yet."""
        done = set(self.completed_agents.get(str(wave_id), []))
        return [a for a in all_agents if a not in done]


# ---------------------------------------------------------------------------
# Checkpoint Manager
# ---------------------------------------------------------------------------


class CheckpointManager:
    """Manage migration checkpoint persistence.

    Usage::

        mgr = CheckpointManager(output_dir=Path("output/run_001"))
        mgr.start("run-123")

        # After each agent completes
        mgr.mark_agent_complete(wave_id=1, agent_id="01-discovery")

        # After an entire wave completes
        mgr.mark_wave_complete(wave_id=1)

        # On resume
        cp = mgr.load()
        if cp and cp.is_wave_complete(1):
            # Skip wave 1
            ...
    """

    def __init__(self, output_dir: Path | str) -> None:
        self._dir = Path(output_dir)
        self._path = self._dir / _CHECKPOINT_FILENAME
        self._checkpoint: Checkpoint | None = None

    @property
    def checkpoint(self) -> Checkpoint | None:
        return self._checkpoint

    @property
    def path(self) -> Path:
        return self._path

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, run_id: str) -> Checkpoint:
        """Initialize a new checkpoint for a migration run."""
        now = datetime.now(timezone.utc).isoformat()
        self._checkpoint = Checkpoint(
            run_id=run_id,
            started_at=now,
            updated_at=now,
            status="in_progress",
        )
        self._save()
        logger.info("Checkpoint started: %s → %s", run_id, self._path)
        return self._checkpoint

    def load(self) -> Checkpoint | None:
        """Load an existing checkpoint from disk. Returns None if not found."""
        if not self._path.exists():
            logger.debug("No checkpoint found at %s", self._path)
            return None

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._checkpoint = Checkpoint(**raw)
            logger.info(
                "Checkpoint loaded: run=%s, wave=%d, status=%s",
                self._checkpoint.run_id,
                self._checkpoint.current_wave,
                self._checkpoint.status,
            )
            return self._checkpoint
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error("Failed to load checkpoint: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Progress tracking
    # ------------------------------------------------------------------

    def mark_agent_complete(self, wave_id: int, agent_id: str) -> None:
        """Mark an agent as completed within a wave."""
        if not self._checkpoint:
            raise RuntimeError("Checkpoint not started — call start() first")

        wave_key = str(wave_id)
        if wave_key not in self._checkpoint.completed_agents:
            self._checkpoint.completed_agents[wave_key] = []

        if agent_id not in self._checkpoint.completed_agents[wave_key]:
            self._checkpoint.completed_agents[wave_key].append(agent_id)

        self._checkpoint.current_wave = wave_id
        self._save()
        logger.debug("Agent %s marked complete in wave %d", agent_id, wave_id)

    def mark_wave_complete(self, wave_id: int) -> None:
        """Mark an entire wave as completed."""
        if not self._checkpoint:
            raise RuntimeError("Checkpoint not started — call start() first")

        if wave_id not in self._checkpoint.completed_waves:
            self._checkpoint.completed_waves.append(wave_id)
            self._checkpoint.completed_waves.sort()

        self._checkpoint.current_wave = wave_id
        self._save()
        logger.info("Wave %d marked complete", wave_id)

    def mark_finished(self, status: str = "succeeded") -> None:
        """Mark the entire migration run as finished."""
        if not self._checkpoint:
            raise RuntimeError("Checkpoint not started — call start() first")

        self._checkpoint.status = status
        self._save()
        logger.info("Migration finished: %s", status)

    def mark_failed(self, error: str = "") -> None:
        """Mark the migration as failed."""
        if not self._checkpoint:
            raise RuntimeError("Checkpoint not started — call start() first")

        self._checkpoint.status = "failed"
        if error:
            self._checkpoint.metadata["last_error"] = error[:500]
        self._save()
        logger.error("Migration failed: %s", error)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def can_resume(self) -> bool:
        """Check if a checkpoint exists and can be resumed."""
        cp = self.load()
        return cp is not None and cp.status == "in_progress"

    def resume_wave(self) -> int:
        """Return the wave ID to resume from (0 if starting fresh)."""
        if not self._checkpoint:
            return 0
        # Resume from the last incomplete wave
        if self._checkpoint.completed_waves:
            return max(self._checkpoint.completed_waves) + 1
        return self._checkpoint.current_wave or 1

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Write checkpoint to disk."""
        if not self._checkpoint:
            return
        self._checkpoint.updated_at = datetime.now(timezone.utc).isoformat()
        self._dir.mkdir(parents=True, exist_ok=True)
        data = asdict(self._checkpoint)
        self._path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

    def delete(self) -> None:
        """Remove the checkpoint file."""
        if self._path.exists():
            self._path.unlink()
            logger.info("Checkpoint deleted: %s", self._path)
        self._checkpoint = None
