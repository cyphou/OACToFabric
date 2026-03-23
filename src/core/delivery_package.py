"""Customer delivery package — asset catalogs, change docs, handover checklists.

Provides:
- ``DeliveryAsset`` / ``AssetCatalog`` — catalog of all delivered artifacts.
- ``ChangeDocGenerator`` — generate change documentation from migration metadata.
- ``TrainingContentGen`` — generate training material skeletons.
- ``KnownIssueTracker`` — track known issues and workarounds.
- ``HandoverChecklist`` — customer handover readiness checklist.
- ``DeliveryPackage`` — composite delivery package.
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
# Asset catalog
# ---------------------------------------------------------------------------


class DeliveryAssetType(str, Enum):
    SEMANTIC_MODEL = "semantic_model"
    REPORT = "report"
    DASHBOARD = "dashboard"
    PIPELINE = "pipeline"
    NOTEBOOK = "notebook"
    LAKEHOUSE_TABLE = "lakehouse_table"
    RLS_ROLE = "rls_role"
    DATAFLOW = "dataflow"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    MIGRATED = "migrated"
    VALIDATED = "validated"
    DELIVERED = "delivered"
    DEFERRED = "deferred"
    EXCLUDED = "excluded"


@dataclass
class DeliveryAsset:
    """A single artifact in the delivery package."""
    asset_id: str = ""
    name: str = ""
    asset_type: DeliveryAssetType = DeliveryAssetType.OTHER
    source_ref: str = ""        # OAC reference
    target_ref: str = ""        # Fabric/PBI reference
    status: DeliveryStatus = DeliveryStatus.PENDING
    version: str = "1.0"
    owner: str = ""
    notes: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.asset_id:
            self.asset_id = uuid.uuid4().hex[:10]


class AssetCatalog:
    """Catalog of all delivered artifacts."""

    def __init__(self) -> None:
        self._assets: dict[str, DeliveryAsset] = {}

    def add(self, asset: DeliveryAsset) -> None:
        self._assets[asset.asset_id] = asset

    def create(self, **kwargs: Any) -> DeliveryAsset:
        a = DeliveryAsset(**kwargs)
        self._assets[a.asset_id] = a
        return a

    def get(self, asset_id: str) -> DeliveryAsset | None:
        return self._assets.get(asset_id)

    def remove(self, asset_id: str) -> bool:
        if asset_id in self._assets:
            del self._assets[asset_id]
            return True
        return False

    @property
    def all_assets(self) -> list[DeliveryAsset]:
        return list(self._assets.values())

    def by_type(self, asset_type: DeliveryAssetType) -> list[DeliveryAsset]:
        return [a for a in self._assets.values() if a.asset_type == asset_type]

    def by_status(self, status: DeliveryStatus) -> list[DeliveryAsset]:
        return [a for a in self._assets.values() if a.status == status]

    @property
    def total_count(self) -> int:
        return len(self._assets)

    @property
    def delivered_count(self) -> int:
        return len(self.by_status(DeliveryStatus.DELIVERED))

    @property
    def pending_count(self) -> int:
        return len(self.by_status(DeliveryStatus.PENDING))

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for a in self._assets.values():
            by_type[a.asset_type.value] = by_type.get(a.asset_type.value, 0) + 1
            by_status[a.status.value] = by_status.get(a.status.value, 0) + 1
        return {
            "total": self.total_count,
            "by_type": by_type,
            "by_status": by_status,
        }

    def search(self, query: str) -> list[DeliveryAsset]:
        """Search assets by name (case-insensitive)."""
        q = query.lower()
        return [a for a in self._assets.values() if q in a.name.lower()]


# ---------------------------------------------------------------------------
# Change documentation
# ---------------------------------------------------------------------------


@dataclass
class ChangeEntry:
    """A single change in the migration."""
    source_name: str = ""
    target_name: str = ""
    change_type: str = ""  # "created", "modified", "removed", "renamed"
    description: str = ""
    impact: str = ""  # "none", "low", "medium", "high"
    category: str = ""


class ChangeDocGenerator:
    """Generate change documentation from migration metadata."""

    def __init__(self) -> None:
        self._entries: list[ChangeEntry] = []

    def add(self, entry: ChangeEntry) -> None:
        self._entries.append(entry)

    def add_from_mapping(self, source: str, target: str, change_type: str = "created",
                          description: str = "", impact: str = "low", category: str = "") -> ChangeEntry:
        e = ChangeEntry(source_name=source, target_name=target, change_type=change_type,
                         description=description, impact=impact, category=category)
        self._entries.append(e)
        return e

    @property
    def all_entries(self) -> list[ChangeEntry]:
        return list(self._entries)

    @property
    def total_changes(self) -> int:
        return len(self._entries)

    def by_category(self, category: str) -> list[ChangeEntry]:
        return [e for e in self._entries if e.category == category]

    def by_impact(self, impact: str) -> list[ChangeEntry]:
        return [e for e in self._entries if e.impact == impact]

    def generate_markdown(self) -> str:
        """Generate change documentation in markdown."""
        lines = ["# Migration Change Document\n"]
        lines.append(f"**Total changes**: {self.total_changes}")
        lines.append(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

        # Group by category
        categories: dict[str, list[ChangeEntry]] = {}
        for e in self._entries:
            cat = e.category or "uncategorized"
            categories.setdefault(cat, []).append(e)

        for cat, entries in sorted(categories.items()):
            lines.append(f"## {cat.title()}\n")
            lines.append("| Source | Target | Type | Impact | Description |")
            lines.append("|--------|--------|------|--------|-------------|")
            for e in entries:
                lines.append(f"| {e.source_name} | {e.target_name} | {e.change_type} | {e.impact} | {e.description} |")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Training content
# ---------------------------------------------------------------------------


@dataclass
class TrainingModule:
    """A single training module."""
    module_id: str = ""
    title: str = ""
    description: str = ""
    duration_minutes: int = 30
    audience: str = ""  # "end_user", "admin", "developer"
    topics: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.module_id:
            self.module_id = uuid.uuid4().hex[:8]


class TrainingContentGen:
    """Generate training material skeletons based on delivered assets."""

    def __init__(self) -> None:
        self._modules: list[TrainingModule] = []

    def generate_from_catalog(self, catalog: AssetCatalog) -> list[TrainingModule]:
        """Generate training modules based on delivered asset types."""
        self._modules.clear()
        asset_types = {a.asset_type for a in catalog.all_assets}

        if DeliveryAssetType.REPORT in asset_types or DeliveryAssetType.DASHBOARD in asset_types:
            self._modules.append(TrainingModule(
                title="Power BI Report Navigation",
                description="How to navigate and interact with migrated Power BI reports",
                duration_minutes=45,
                audience="end_user",
                topics=["Report navigation", "Slicer usage", "Bookmarks", "Export options"],
            ))

        if DeliveryAssetType.SEMANTIC_MODEL in asset_types:
            self._modules.append(TrainingModule(
                title="Semantic Model Overview",
                description="Understanding the Power BI semantic model structure",
                duration_minutes=60,
                audience="developer",
                topics=["Tables & relationships", "Measures (DAX)", "Hierarchies", "Data refresh"],
            ))

        if DeliveryAssetType.RLS_ROLE in asset_types:
            self._modules.append(TrainingModule(
                title="Row-Level Security",
                description="How RLS is configured and tested in Power BI",
                duration_minutes=30,
                audience="admin",
                topics=["RLS roles", "Testing as user", "Dynamic RLS patterns"],
            ))

        if DeliveryAssetType.PIPELINE in asset_types or DeliveryAssetType.DATAFLOW in asset_types:
            self._modules.append(TrainingModule(
                title="Data Pipeline Operations",
                description="Monitoring and managing Fabric data pipelines",
                duration_minutes=45,
                audience="admin",
                topics=["Pipeline monitoring", "Refresh schedules", "Failure handling", "Alerting"],
            ))

        if DeliveryAssetType.LAKEHOUSE_TABLE in asset_types:
            self._modules.append(TrainingModule(
                title="Fabric Lakehouse Basics",
                description="Working with Lakehouse tables in Microsoft Fabric",
                duration_minutes=30,
                audience="developer",
                topics=["OneLake structure", "Delta tables", "SQL analytics endpoint", "Notebooks"],
            ))

        return list(self._modules)

    @property
    def all_modules(self) -> list[TrainingModule]:
        return list(self._modules)

    def generate_outline_markdown(self) -> str:
        """Generate a markdown outline of all training modules."""
        lines = ["# Training Plan\n"]
        for i, m in enumerate(self._modules, 1):
            lines.append(f"## Module {i}: {m.title}\n")
            lines.append(f"- **Duration**: {m.duration_minutes} minutes")
            lines.append(f"- **Audience**: {m.audience}")
            lines.append(f"- **Description**: {m.description}")
            if m.prerequisites:
                lines.append(f"- **Prerequisites**: {', '.join(m.prerequisites)}")
            lines.append("\n**Topics:**\n")
            for t in m.topics:
                lines.append(f"  1. {t}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Known issues
# ---------------------------------------------------------------------------


@dataclass
class KnownIssue:
    """A known issue with a workaround."""
    issue_id: str = ""
    title: str = ""
    description: str = ""
    affected_assets: list[str] = field(default_factory=list)
    workaround: str = ""
    resolution_eta: str = ""
    severity: str = "low"  # low, medium, high

    def __post_init__(self) -> None:
        if not self.issue_id:
            self.issue_id = f"KI-{uuid.uuid4().hex[:6]}"


class KnownIssueTracker:
    """Track known issues and workarounds for delivery."""

    def __init__(self) -> None:
        self._issues: list[KnownIssue] = []

    def add(self, issue: KnownIssue) -> None:
        self._issues.append(issue)

    def create(self, **kwargs: Any) -> KnownIssue:
        ki = KnownIssue(**kwargs)
        self._issues.append(ki)
        return ki

    @property
    def all_issues(self) -> list[KnownIssue]:
        return list(self._issues)

    @property
    def total_count(self) -> int:
        return len(self._issues)

    def by_severity(self, severity: str) -> list[KnownIssue]:
        return [i for i in self._issues if i.severity == severity]

    def for_asset(self, asset_name: str) -> list[KnownIssue]:
        return [i for i in self._issues if asset_name in i.affected_assets]

    def generate_markdown(self) -> str:
        lines = ["# Known Issues\n"]
        if not self._issues:
            lines.append("No known issues at this time.")
            return "\n".join(lines)

        lines.append(f"**Total**: {self.total_count}\n")
        for ki in self._issues:
            lines.append(f"### {ki.issue_id}: {ki.title}\n")
            lines.append(f"- **Severity**: {ki.severity}")
            lines.append(f"- **Description**: {ki.description}")
            if ki.affected_assets:
                lines.append(f"- **Affected**: {', '.join(ki.affected_assets)}")
            if ki.workaround:
                lines.append(f"- **Workaround**: {ki.workaround}")
            if ki.resolution_eta:
                lines.append(f"- **Resolution ETA**: {ki.resolution_eta}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Handover checklist
# ---------------------------------------------------------------------------


class ChecklistItemStatus(str, Enum):
    TODO = "todo"
    DONE = "done"
    NA = "not_applicable"


@dataclass
class ChecklistItem:
    """A single item in the handover checklist."""
    item_id: str = ""
    category: str = ""
    description: str = ""
    status: ChecklistItemStatus = ChecklistItemStatus.TODO
    notes: str = ""
    owner: str = ""

    def __post_init__(self) -> None:
        if not self.item_id:
            self.item_id = uuid.uuid4().hex[:8]

    def complete(self, notes: str = "") -> None:
        self.status = ChecklistItemStatus.DONE
        if notes:
            self.notes = notes

    def skip(self, reason: str = "") -> None:
        self.status = ChecklistItemStatus.NA
        if reason:
            self.notes = reason


class HandoverChecklist:
    """Customer handover readiness checklist."""

    # Standard checklist template
    STANDARD_ITEMS: list[dict[str, str]] = [
        {"category": "Data", "description": "All source data migrated and validated"},
        {"category": "Data", "description": "Data refresh schedules configured"},
        {"category": "Data", "description": "Incremental refresh configured (if needed)"},
        {"category": "Model", "description": "Semantic model deployed and tested"},
        {"category": "Model", "description": "All DAX measures verified against source"},
        {"category": "Model", "description": "Relationships validated"},
        {"category": "Reports", "description": "All reports migrated and visually validated"},
        {"category": "Reports", "description": "Slicers and filters working correctly"},
        {"category": "Reports", "description": "Report permissions configured"},
        {"category": "Security", "description": "Row-level security configured and tested"},
        {"category": "Security", "description": "Workspace roles assigned"},
        {"category": "Security", "description": "Sensitivity labels applied"},
        {"category": "Ops", "description": "Monitoring and alerting configured"},
        {"category": "Ops", "description": "Failure notification set up"},
        {"category": "Ops", "description": "Runbook documentation provided"},
        {"category": "Delivery", "description": "Training completed"},
        {"category": "Delivery", "description": "Change documentation delivered"},
        {"category": "Delivery", "description": "Known issues documented"},
        {"category": "Delivery", "description": "UAT sign-off obtained"},
        {"category": "Delivery", "description": "Go-live date confirmed"},
    ]

    def __init__(self, include_standard: bool = True) -> None:
        self._items: list[ChecklistItem] = []
        if include_standard:
            for item_def in self.STANDARD_ITEMS:
                self._items.append(ChecklistItem(
                    category=item_def["category"],
                    description=item_def["description"],
                ))

    def add(self, item: ChecklistItem) -> None:
        self._items.append(item)

    def create(self, **kwargs: Any) -> ChecklistItem:
        ci = ChecklistItem(**kwargs)
        self._items.append(ci)
        return ci

    @property
    def all_items(self) -> list[ChecklistItem]:
        return list(self._items)

    @property
    def total_count(self) -> int:
        return len(self._items)

    @property
    def done_count(self) -> int:
        return sum(1 for i in self._items if i.status == ChecklistItemStatus.DONE)

    @property
    def remaining_count(self) -> int:
        return sum(1 for i in self._items if i.status == ChecklistItemStatus.TODO)

    @property
    def progress_pct(self) -> float:
        applicable = sum(1 for i in self._items if i.status != ChecklistItemStatus.NA)
        if applicable == 0:
            return 100.0
        return (self.done_count / applicable) * 100.0

    def by_category(self, category: str) -> list[ChecklistItem]:
        return [i for i in self._items if i.category == category]

    @property
    def is_complete(self) -> bool:
        return all(i.status in (ChecklistItemStatus.DONE, ChecklistItemStatus.NA) for i in self._items)

    def generate_markdown(self) -> str:
        lines = ["# Handover Checklist\n"]
        lines.append(f"**Progress**: {self.done_count}/{self.total_count} ({self.progress_pct:.0f}%)\n")

        categories: dict[str, list[ChecklistItem]] = {}
        for item in self._items:
            categories.setdefault(item.category, []).append(item)

        for cat, items in sorted(categories.items()):
            lines.append(f"## {cat}\n")
            for item in items:
                check = "x" if item.status == ChecklistItemStatus.DONE else (" " if item.status == ChecklistItemStatus.TODO else "-")
                lines.append(f"- [{check}] {item.description}")
                if item.notes:
                    lines.append(f"  - Note: {item.notes}")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Delivery package
# ---------------------------------------------------------------------------


@dataclass
class DeliveryPackage:
    """Composite delivery package for a customer migration."""
    package_id: str = ""
    customer_name: str = ""
    project_name: str = ""
    version: str = "1.0"
    created_at: str = ""

    catalog: AssetCatalog = field(default_factory=AssetCatalog)
    change_doc: ChangeDocGenerator = field(default_factory=ChangeDocGenerator)
    training: TrainingContentGen = field(default_factory=TrainingContentGen)
    known_issues: KnownIssueTracker = field(default_factory=KnownIssueTracker)
    checklist: HandoverChecklist = field(default_factory=lambda: HandoverChecklist(include_standard=True))

    def __post_init__(self) -> None:
        if not self.package_id:
            self.package_id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def generate_index_markdown(self) -> str:
        """Generate a package index / table of contents."""
        lines = [f"# Delivery Package — {self.project_name}\n"]
        lines.append(f"**Customer**: {self.customer_name}")
        lines.append(f"**Version**: {self.version}")
        lines.append(f"**Package ID**: {self.package_id}")
        lines.append(f"**Created**: {self.created_at}")
        lines.append("")

        # Summary
        cat_summary = self.catalog.summary()
        lines.append("## Asset Summary\n")
        lines.append(f"- Total assets: {cat_summary['total']}")
        for atype, count in cat_summary.get("by_type", {}).items():
            lines.append(f"  - {atype}: {count}")
        lines.append("")

        lines.append("## Package Contents\n")
        lines.append("1. Asset Catalog")
        lines.append(f"2. Change Documentation ({self.change_doc.total_changes} changes)")
        lines.append(f"3. Training Plan ({len(self.training.all_modules)} modules)")
        lines.append(f"4. Known Issues ({self.known_issues.total_count} issues)")
        lines.append(f"5. Handover Checklist ({self.checklist.progress_pct:.0f}% complete)")
        lines.append("")

        return "\n".join(lines)

    @property
    def is_ready(self) -> bool:
        """Check if the delivery package is ready for handover."""
        return (
            self.catalog.total_count > 0
            and self.checklist.is_complete
            and self.catalog.pending_count == 0
        )
