"""Incremental Crawler — detect OAC changes since last discovery run.

Compares current OAC catalog state against the previous inventory
snapshot to produce a delta of added, modified, and removed assets.

Enables re-running only the affected migration agents instead of
a full re-migration, dramatically reducing subsequent run times.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Change detection types
# ---------------------------------------------------------------------------


@dataclass
class AssetFingerprint:
    """Fingerprint of an OAC asset for change detection."""

    asset_id: str
    asset_type: str
    name: str
    hash: str                # SHA-256 of canonical representation
    last_modified: str = ""  # ISO 8601 timestamp from OAC
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeRecord:
    """A single change detected between inventory snapshots."""

    asset_id: str
    asset_type: str
    name: str
    change_type: str        # added, modified, removed
    old_hash: str = ""
    new_hash: str = ""
    details: str = ""


@dataclass
class IncrementalResult:
    """Result of incremental discovery."""

    added: list[ChangeRecord] = field(default_factory=list)
    modified: list[ChangeRecord] = field(default_factory=list)
    removed: list[ChangeRecord] = field(default_factory=list)
    unchanged_count: int = 0
    snapshot_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.modified) + len(self.removed)

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0

    def summary(self) -> str:
        return (
            f"Incremental scan: {len(self.added)} added, "
            f"{len(self.modified)} modified, {len(self.removed)} removed, "
            f"{self.unchanged_count} unchanged"
        )

    def affected_asset_ids(self) -> list[str]:
        """Return IDs of all changed assets (for selective re-migration)."""
        ids: list[str] = []
        for c in self.added:
            ids.append(c.asset_id)
        for c in self.modified:
            ids.append(c.asset_id)
        return ids

    def affected_types(self) -> set[str]:
        """Return set of asset types that have changes."""
        types: set[str] = set()
        for c in self.added + self.modified + self.removed:
            types.add(c.asset_type)
        return types


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------


def compute_fingerprint(
    asset_id: str,
    asset_type: str,
    name: str,
    content: str | dict[str, Any],
    last_modified: str = "",
) -> AssetFingerprint:
    """Compute a fingerprint for an OAC asset.

    Parameters
    ----------
    asset_id : str
        Unique asset identifier.
    asset_type : str
        Asset type (table, analysis, dashboard, etc.).
    name : str
        Asset display name.
    content : str | dict
        Asset content (XML, JSON, or dict) for hashing.
    last_modified : str
        Last modified timestamp from OAC.

    Returns
    -------
    AssetFingerprint
        Fingerprint with content hash.
    """
    if isinstance(content, dict):
        canonical = json.dumps(content, sort_keys=True, default=str)
    else:
        canonical = content

    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return AssetFingerprint(
        asset_id=asset_id,
        asset_type=asset_type,
        name=name,
        hash=content_hash,
        last_modified=last_modified,
    )


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------


def detect_changes(
    previous: list[AssetFingerprint],
    current: list[AssetFingerprint],
) -> IncrementalResult:
    """Detect changes between two inventory snapshots.

    Parameters
    ----------
    previous : list[AssetFingerprint]
        Fingerprints from previous discovery run.
    current : list[AssetFingerprint]
        Fingerprints from current discovery run.

    Returns
    -------
    IncrementalResult
        Detected changes (added, modified, removed).
    """
    prev_map = {fp.asset_id: fp for fp in previous}
    curr_map = {fp.asset_id: fp for fp in current}

    result = IncrementalResult()

    # Added and modified
    for asset_id, curr_fp in curr_map.items():
        if asset_id not in prev_map:
            result.added.append(ChangeRecord(
                asset_id=asset_id,
                asset_type=curr_fp.asset_type,
                name=curr_fp.name,
                change_type="added",
                new_hash=curr_fp.hash,
            ))
        elif prev_map[asset_id].hash != curr_fp.hash:
            result.modified.append(ChangeRecord(
                asset_id=asset_id,
                asset_type=curr_fp.asset_type,
                name=curr_fp.name,
                change_type="modified",
                old_hash=prev_map[asset_id].hash,
                new_hash=curr_fp.hash,
            ))
        else:
            result.unchanged_count += 1

    # Removed
    for asset_id, prev_fp in prev_map.items():
        if asset_id not in curr_map:
            result.removed.append(ChangeRecord(
                asset_id=asset_id,
                asset_type=prev_fp.asset_type,
                name=prev_fp.name,
                change_type="removed",
                old_hash=prev_fp.hash,
            ))

    logger.info(result.summary())
    return result


# ---------------------------------------------------------------------------
# Snapshot persistence helpers
# ---------------------------------------------------------------------------


def fingerprints_to_json(fingerprints: list[AssetFingerprint]) -> str:
    """Serialize fingerprints to JSON for persistence."""
    return json.dumps(
        [
            {
                "asset_id": fp.asset_id,
                "asset_type": fp.asset_type,
                "name": fp.name,
                "hash": fp.hash,
                "last_modified": fp.last_modified,
            }
            for fp in fingerprints
        ],
        indent=2,
    )


def fingerprints_from_json(json_text: str) -> list[AssetFingerprint]:
    """Deserialize fingerprints from JSON."""
    data = json.loads(json_text)
    return [
        AssetFingerprint(
            asset_id=item["asset_id"],
            asset_type=item["asset_type"],
            name=item["name"],
            hash=item["hash"],
            last_modified=item.get("last_modified", ""),
        )
        for item in data
    ]
