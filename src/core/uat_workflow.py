"""UAT workflow — session management, comparison specs, sign-off tracking.

Provides:
- ``UATStatus`` / ``UATSession`` — track a UAT session lifecycle.
- ``ComparisonSpec`` — define what to compare between OAC and Fabric/PBI.
- ``ComparisonResult`` — structured comparison outcome.
- ``DefectSeverity`` / ``Defect`` / ``DefectLog`` — track UAT defects.
- ``SignOffStatus`` / ``SignOffRecord`` / ``SignOffTracker`` — manage sign-offs.
- ``UATWorkflow`` — orchestrate a full UAT workflow.
- ``UATReport`` — generate UAT summary reports.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


class UATStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SIGNED_OFF = "signed_off"
    REJECTED = "rejected"


@dataclass
class UATSession:
    """A single UAT testing session."""
    session_id: str = ""
    name: str = ""
    description: str = ""
    wave: str = ""
    status: UATStatus = UATStatus.DRAFT
    created_at: str = ""
    updated_at: str = ""
    assigned_to: list[str] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)  # asset names in scope
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def transition(self, new_status: UATStatus) -> None:
        """Transition session to a new status with validation."""
        allowed: dict[UATStatus, set[UATStatus]] = {
            UATStatus.DRAFT: {UATStatus.IN_PROGRESS},
            UATStatus.IN_PROGRESS: {UATStatus.BLOCKED, UATStatus.COMPLETED, UATStatus.REJECTED},
            UATStatus.BLOCKED: {UATStatus.IN_PROGRESS, UATStatus.REJECTED},
            UATStatus.COMPLETED: {UATStatus.SIGNED_OFF, UATStatus.REJECTED, UATStatus.IN_PROGRESS},
            UATStatus.REJECTED: {UATStatus.IN_PROGRESS},
            UATStatus.SIGNED_OFF: set(),
        }
        if new_status not in allowed.get(self.status, set()):
            raise ValueError(f"Cannot transition from {self.status.value} to {new_status.value}")
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Comparison specs
# ---------------------------------------------------------------------------


class ComparisonType(str, Enum):
    DATA_MATCH = "data_match"        # row-level data comparison
    VISUAL_MATCH = "visual_match"    # screenshot comparison
    METRIC_MATCH = "metric_match"    # KPI/measure value comparison
    SCHEMA_MATCH = "schema_match"    # column/type comparison
    SECURITY_MATCH = "security_match"  # RLS result comparison


@dataclass
class ComparisonSpec:
    """Defines what to compare between source and target."""
    spec_id: str = ""
    name: str = ""
    comparison_type: ComparisonType = ComparisonType.DATA_MATCH
    source_ref: str = ""       # OAC asset reference
    target_ref: str = ""       # Fabric/PBI asset reference
    tolerance: float = 0.0     # acceptable difference (0 = exact)
    filters: dict[str, str] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.spec_id:
            self.spec_id = uuid.uuid4().hex[:10]


class ComparisonOutcome(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    PARTIAL = "partial"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ComparisonResult:
    """Result of running a comparison spec."""
    spec_id: str = ""
    outcome: ComparisonOutcome = ComparisonOutcome.SKIPPED
    source_value: Any = None
    target_value: Any = None
    difference: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    executed_at: str = ""
    error_message: str = ""

    def __post_init__(self) -> None:
        if not self.executed_at:
            self.executed_at = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Defect tracking
# ---------------------------------------------------------------------------


class DefectSeverity(str, Enum):
    COSMETIC = "cosmetic"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
    BLOCKER = "blocker"


class DefectStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    VERIFIED = "verified"
    WONT_FIX = "wont_fix"
    DEFERRED = "deferred"


@dataclass
class Defect:
    """A UAT defect / issue."""
    defect_id: str = ""
    session_id: str = ""
    title: str = ""
    description: str = ""
    severity: DefectSeverity = DefectSeverity.MINOR
    status: DefectStatus = DefectStatus.OPEN
    asset_name: str = ""
    comparison_spec_id: str = ""
    reported_by: str = ""
    assigned_to: str = ""
    created_at: str = ""
    resolved_at: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.defect_id:
            self.defect_id = f"DEF-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def resolve(self, status: DefectStatus = DefectStatus.FIXED) -> None:
        self.status = status
        self.resolved_at = datetime.now(timezone.utc).isoformat()


class DefectLog:
    """Manage a collection of defects for a UAT session."""

    def __init__(self) -> None:
        self._defects: list[Defect] = []

    def add(self, defect: Defect) -> None:
        self._defects.append(defect)

    def create(self, **kwargs: Any) -> Defect:
        d = Defect(**kwargs)
        self._defects.append(d)
        return d

    @property
    def all_defects(self) -> list[Defect]:
        return list(self._defects)

    def by_severity(self, severity: DefectSeverity) -> list[Defect]:
        return [d for d in self._defects if d.severity == severity]

    def by_status(self, status: DefectStatus) -> list[Defect]:
        return [d for d in self._defects if d.status == status]

    def by_session(self, session_id: str) -> list[Defect]:
        return [d for d in self._defects if d.session_id == session_id]

    @property
    def open_count(self) -> int:
        return len(self.by_status(DefectStatus.OPEN))

    @property
    def blocker_count(self) -> int:
        return len(self.by_severity(DefectSeverity.BLOCKER)) + len(self.by_severity(DefectSeverity.CRITICAL))

    @property
    def total_count(self) -> int:
        return len(self._defects)

    def summary(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for d in self._defects:
            result[d.severity.value] = result.get(d.severity.value, 0) + 1
        return result


# ---------------------------------------------------------------------------
# Sign-off tracking
# ---------------------------------------------------------------------------


class SignOffStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"


@dataclass
class SignOffRecord:
    """A sign-off decision by a stakeholder."""
    record_id: str = ""
    session_id: str = ""
    approver: str = ""
    status: SignOffStatus = SignOffStatus.PENDING
    conditions: list[str] = field(default_factory=list)
    comments: str = ""
    signed_at: str = ""

    def __post_init__(self) -> None:
        if not self.record_id:
            self.record_id = uuid.uuid4().hex[:10]

    def approve(self, comments: str = "") -> None:
        self.status = SignOffStatus.APPROVED
        self.comments = comments
        self.signed_at = datetime.now(timezone.utc).isoformat()

    def reject(self, comments: str = "") -> None:
        self.status = SignOffStatus.REJECTED
        self.comments = comments
        self.signed_at = datetime.now(timezone.utc).isoformat()

    def approve_conditional(self, conditions: list[str], comments: str = "") -> None:
        self.status = SignOffStatus.CONDITIONAL
        self.conditions = conditions
        self.comments = comments
        self.signed_at = datetime.now(timezone.utc).isoformat()


class SignOffTracker:
    """Track sign-offs for UAT sessions."""

    def __init__(self) -> None:
        self._records: list[SignOffRecord] = []

    def add(self, record: SignOffRecord) -> None:
        self._records.append(record)

    def create(self, **kwargs: Any) -> SignOffRecord:
        r = SignOffRecord(**kwargs)
        self._records.append(r)
        return r

    def by_session(self, session_id: str) -> list[SignOffRecord]:
        return [r for r in self._records if r.session_id == session_id]

    def is_fully_approved(self, session_id: str) -> bool:
        records = self.by_session(session_id)
        if not records:
            return False
        return all(r.status in (SignOffStatus.APPROVED, SignOffStatus.CONDITIONAL) for r in records)

    def has_rejection(self, session_id: str) -> bool:
        return any(r.status == SignOffStatus.REJECTED for r in self.by_session(session_id))

    @property
    def all_records(self) -> list[SignOffRecord]:
        return list(self._records)

    @property
    def pending_count(self) -> int:
        return sum(1 for r in self._records if r.status == SignOffStatus.PENDING)


# ---------------------------------------------------------------------------
# UAT Workflow
# ---------------------------------------------------------------------------


class UATWorkflow:
    """Orchestrate a full UAT workflow."""

    def __init__(self) -> None:
        self._sessions: dict[str, UATSession] = {}
        self._specs: dict[str, list[ComparisonSpec]] = {}  # session_id → specs
        self._results: dict[str, list[ComparisonResult]] = {}  # session_id → results
        self.defect_log = DefectLog()
        self.sign_off_tracker = SignOffTracker()

    def create_session(self, **kwargs: Any) -> UATSession:
        session = UATSession(**kwargs)
        self._sessions[session.session_id] = session
        self._specs[session.session_id] = []
        self._results[session.session_id] = []
        return session

    def get_session(self, session_id: str) -> UATSession | None:
        return self._sessions.get(session_id)

    @property
    def all_sessions(self) -> list[UATSession]:
        return list(self._sessions.values())

    def add_comparison(self, session_id: str, spec: ComparisonSpec) -> None:
        if session_id not in self._specs:
            raise ValueError(f"Session {session_id} not found")
        self._specs[session_id].append(spec)

    def get_comparisons(self, session_id: str) -> list[ComparisonSpec]:
        return self._specs.get(session_id, [])

    def record_result(self, session_id: str, result: ComparisonResult) -> None:
        if session_id not in self._results:
            raise ValueError(f"Session {session_id} not found")
        self._results[session_id].append(result)

    def get_results(self, session_id: str) -> list[ComparisonResult]:
        return self._results.get(session_id, [])

    def start_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.transition(UATStatus.IN_PROGRESS)

    def complete_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.transition(UATStatus.COMPLETED)

    def sign_off_session(self, session_id: str, approver: str, comments: str = "") -> SignOffRecord:
        record = self.sign_off_tracker.create(
            session_id=session_id, approver=approver,
        )
        record.approve(comments)

        # Check if fully approved
        session = self._sessions.get(session_id)
        if session and self.sign_off_tracker.is_fully_approved(session_id):
            if session.status == UATStatus.COMPLETED:
                session.transition(UATStatus.SIGNED_OFF)

        return record

    def session_progress(self, session_id: str) -> dict[str, Any]:
        """Get progress for a session."""
        specs = self._specs.get(session_id, [])
        results = self._results.get(session_id, [])
        defects = self.defect_log.by_session(session_id)

        completed_specs = {r.spec_id for r in results}
        matches = sum(1 for r in results if r.outcome == ComparisonOutcome.MATCH)
        mismatches = sum(1 for r in results if r.outcome == ComparisonOutcome.MISMATCH)

        return {
            "total_specs": len(specs),
            "completed_specs": len(completed_specs),
            "remaining_specs": len(specs) - len(completed_specs),
            "matches": matches,
            "mismatches": mismatches,
            "defects": len(defects),
            "blockers": sum(1 for d in defects if d.severity in (DefectSeverity.BLOCKER, DefectSeverity.CRITICAL)),
            "progress_pct": (len(completed_specs) / len(specs) * 100.0) if specs else 0.0,
        }


# ---------------------------------------------------------------------------
# UAT Report
# ---------------------------------------------------------------------------


class UATReport:
    """Generate UAT summary reports."""

    def __init__(self, workflow: UATWorkflow) -> None:
        self._workflow = workflow

    def generate_session_report(self, session_id: str) -> str:
        """Generate markdown report for a single UAT session."""
        session = self._workflow.get_session(session_id)
        if not session:
            return f"Session {session_id} not found."

        lines = [f"# UAT Report — {session.name}\n"]
        lines.append(f"**Session ID**: {session.session_id}")
        lines.append(f"**Status**: {session.status.value}")
        lines.append(f"**Wave**: {session.wave}")
        lines.append(f"**Created**: {session.created_at}")
        lines.append("")

        # Progress
        progress = self._workflow.session_progress(session_id)
        lines.append("## Progress\n")
        lines.append(f"- Specs: {progress['completed_specs']}/{progress['total_specs']}")
        lines.append(f"- Matches: {progress['matches']}")
        lines.append(f"- Mismatches: {progress['mismatches']}")
        lines.append(f"- Progress: {progress['progress_pct']:.0f}%")
        lines.append("")

        # Defects
        defects = self._workflow.defect_log.by_session(session_id)
        if defects:
            lines.append("## Defects\n")
            lines.append(f"Total: {len(defects)}, Blockers: {progress['blockers']}")
            lines.append("")
            for d in defects:
                lines.append(f"- **{d.defect_id}** [{d.severity.value}] {d.title} — {d.status.value}")
            lines.append("")

        # Sign-offs
        sign_offs = self._workflow.sign_off_tracker.by_session(session_id)
        if sign_offs:
            lines.append("## Sign-offs\n")
            for s in sign_offs:
                lines.append(f"- {s.approver}: {s.status.value}")
                if s.conditions:
                    for c in s.conditions:
                        lines.append(f"  - Condition: {c}")
            lines.append("")

        return "\n".join(lines)

    def generate_summary(self) -> str:
        """Generate a summary across all UAT sessions."""
        sessions = self._workflow.all_sessions
        lines = ["# UAT Summary Report\n"]
        lines.append(f"**Total sessions**: {len(sessions)}")
        by_status: dict[str, int] = {}
        for s in sessions:
            by_status[s.status.value] = by_status.get(s.status.value, 0) + 1
        for status, count in by_status.items():
            lines.append(f"- {status}: {count}")
        lines.append(f"\n**Total defects**: {self._workflow.defect_log.total_count}")
        lines.append(f"**Open defects**: {self._workflow.defect_log.open_count}")
        lines.append(f"**Pending sign-offs**: {self._workflow.sign_off_tracker.pending_count}")
        return "\n".join(lines)
