"""Incremental merge engine for safe re-migration.

Ported from T2P's IncrementalMerger — preserves user customizations
when re-running migration on previously-generated artifacts.

Strategy:
  - Added files (in incoming, not in existing) → add
  - Removed files (in existing, not in incoming) → keep if user-owned
  - Modified files → preserve user-editable JSON keys
  - Unchanged files → keep from existing
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Files owned by the user that should never be overwritten
USER_OWNED_FILES: frozenset[str] = frozenset({
    "staticResources",
    "custom_measures",
    "custom_visuals",
    "user_theme.json",
    "custom_dax.tmdl",
})

# JSON keys that users may have manually edited
USER_EDITABLE_KEYS: frozenset[str] = frozenset({
    "displayName",
    "title",
    "description",
    "subtitle",
    "tooltip",
})


# ---------------------------------------------------------------------------
# Merge result
# ---------------------------------------------------------------------------


@dataclass
class MergeAction:
    """A single merge action."""

    path: str
    action: str     # added | removed_kept | removed_deleted | modified | unchanged
    reason: str = ""


@dataclass
class MergeResult:
    """Result of an incremental merge operation."""

    actions: list[MergeAction] = field(default_factory=list)
    added: int = 0
    modified: int = 0
    unchanged: int = 0
    kept: int = 0       # User-owned files that were kept despite being removed
    deleted: int = 0

    @property
    def total(self) -> int:
        return self.added + self.modified + self.unchanged + self.kept + self.deleted


# ---------------------------------------------------------------------------
# Merge engine
# ---------------------------------------------------------------------------


def _is_user_owned(path: str) -> bool:
    """Check if a file path is user-owned and should not be overwritten."""
    name = Path(path).name
    stem = Path(path).stem
    return name in USER_OWNED_FILES or stem in USER_OWNED_FILES


def _merge_json_preserving_user_keys(
    existing_content: str,
    incoming_content: str,
) -> str:
    """Merge two JSON files, preserving user-editable keys from existing."""
    try:
        existing = json.loads(existing_content)
        incoming = json.loads(incoming_content)
    except (json.JSONDecodeError, TypeError):
        return incoming_content

    if not isinstance(existing, dict) or not isinstance(incoming, dict):
        return incoming_content

    # Preserve user-editable keys from existing
    merged = dict(incoming)
    for key in USER_EDITABLE_KEYS:
        if key in existing and existing[key] != incoming.get(key):
            merged[key] = existing[key]

    return json.dumps(merged, indent=2)


def merge_artifacts(
    existing_files: dict[str, str],
    incoming_files: dict[str, str],
) -> tuple[dict[str, str], MergeResult]:
    """Merge incoming migration artifacts with existing user-modified artifacts.

    Parameters
    ----------
    existing_files
        Dict of relative_path → content from previous migration run.
    incoming_files
        Dict of relative_path → content from current migration run.

    Returns
    -------
    (merged_files, merge_result)
        The merged file dict and a MergeResult summary.
    """
    result = MergeResult()
    merged: dict[str, str] = {}

    all_paths = set(existing_files) | set(incoming_files)

    for path in sorted(all_paths):
        in_existing = path in existing_files
        in_incoming = path in incoming_files

        if in_incoming and not in_existing:
            # New file from migration — add it
            merged[path] = incoming_files[path]
            result.added += 1
            result.actions.append(MergeAction(path, "added"))

        elif in_existing and not in_incoming:
            # File removed from migration output
            if _is_user_owned(path):
                merged[path] = existing_files[path]
                result.kept += 1
                result.actions.append(MergeAction(path, "removed_kept", "User-owned file"))
            else:
                result.deleted += 1
                result.actions.append(MergeAction(path, "removed_deleted"))

        elif in_existing and in_incoming:
            if existing_files[path] == incoming_files[path]:
                # Unchanged
                merged[path] = existing_files[path]
                result.unchanged += 1
                result.actions.append(MergeAction(path, "unchanged"))
            else:
                # Modified — merge preserving user keys for JSON files
                if path.endswith(".json"):
                    merged[path] = _merge_json_preserving_user_keys(
                        existing_files[path],
                        incoming_files[path],
                    )
                else:
                    merged[path] = incoming_files[path]
                result.modified += 1
                result.actions.append(MergeAction(path, "modified"))

    logger.info(
        "Merge complete: %d added, %d modified, %d unchanged, %d kept, %d deleted",
        result.added, result.modified, result.unchanged, result.kept, result.deleted,
    )

    return merged, result
