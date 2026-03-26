"""TMDL self-healing — 6 auto-repair patterns.

Ported from T2P — automatically detects and repairs common TMDL
structural issues that would cause deployment failures:

1. Duplicate table names → rename with suffix
2. Broken column refs → hide + annotation
3. Orphan measures → reassign to first table
4. Empty names → remove
5. Circular relationships → Union-Find deactivate
6. M query errors → try/otherwise wrapping
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Repair record
# ---------------------------------------------------------------------------


@dataclass
class RepairAction:
    """A single self-healing repair action taken."""

    pattern: str        # duplicate_table | broken_ref | orphan_measure | empty_name | circular_rel | m_error
    severity: str       # info | warning | error
    description: str
    file_path: str = ""
    action_taken: str = ""


@dataclass
class SelfHealingResult:
    """Result of running all self-healing patterns."""

    repairs: list[RepairAction] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)  # Updated files

    @property
    def repair_count(self) -> int:
        return len(self.repairs)

    @property
    def by_pattern(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.repairs:
            counts[r.pattern] = counts.get(r.pattern, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Union-Find for cycle detection
# ---------------------------------------------------------------------------


class _UnionFind:
    """Union-Find data structure for detecting relationship cycles."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: str, y: str) -> bool:
        """Union two sets. Returns False if they were already in the same set (cycle)."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1
        return True


# ---------------------------------------------------------------------------
# Pattern 1: Duplicate table names
# ---------------------------------------------------------------------------

def _fix_duplicate_tables(files: dict[str, str]) -> list[RepairAction]:
    """Detect and rename duplicate table names."""
    repairs: list[RepairAction] = []
    table_names: dict[str, list[str]] = {}  # name → [file_paths]

    for path, content in files.items():
        if not path.startswith("definition/tables/"):
            continue
        m = re.match(r"^table\s+'?([^'\n]+)'?", content)
        if m:
            name = m.group(1).strip()
            table_names.setdefault(name, []).append(path)

    for name, paths in table_names.items():
        if len(paths) <= 1:
            continue
        for i, path in enumerate(paths[1:], 2):
            old_name = name
            new_name = f"{name}_{i}"
            content = files[path]
            files[path] = content.replace(f"table '{old_name}'", f"table '{new_name}'", 1)
            files[path] = files[path].replace(f"table {old_name}", f"table {new_name}", 1)
            repairs.append(RepairAction(
                pattern="duplicate_table",
                severity="warning",
                description=f"Renamed duplicate table '{old_name}' to '{new_name}'",
                file_path=path,
                action_taken=f"rename: {old_name} → {new_name}",
            ))

    return repairs


# ---------------------------------------------------------------------------
# Pattern 2: Broken column references
# ---------------------------------------------------------------------------

def _fix_broken_refs(files: dict[str, str]) -> list[RepairAction]:
    """Detect calculated columns/measures referencing non-existent columns and hide them."""
    repairs: list[RepairAction] = []

    # Collect all column names from all tables
    all_columns: set[str] = set()
    for path, content in files.items():
        if not path.startswith("definition/tables/"):
            continue
        for m in re.finditer(r"^\s+column\s+'?([^'=\n]+)'?", content, re.MULTILINE):
            all_columns.add(m.group(1).strip())

    # Check expressions for references to non-existent columns
    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        for m in re.finditer(r"\[([^\]]+)\]", content):
            ref = m.group(1)
            if ref not in all_columns and not re.match(r"^(Date|Value|Fields|Y|X|Category)$", ref):
                # Mark the containing measure/column as hidden
                if "isHidden" not in content:
                    files[path] = content + "\n        /// @migration: broken-ref-auto-hidden\n"
                    repairs.append(RepairAction(
                        pattern="broken_ref",
                        severity="warning",
                        description=f"Potential broken ref [{ref}] detected",
                        file_path=path,
                        action_taken="annotated for review",
                    ))
                break  # One repair per file

    return repairs


# ---------------------------------------------------------------------------
# Pattern 3: Orphan measures (measures without a table)
# ---------------------------------------------------------------------------

def _fix_orphan_measures(files: dict[str, str]) -> list[RepairAction]:
    """Detect standalone measures not assigned to any table and reassign."""
    repairs: list[RepairAction] = []

    # This pattern applies if we find measure definitions outside table files
    first_table_path: str | None = None
    for path in files:
        if path.startswith("definition/tables/"):
            first_table_path = path
            break

    if not first_table_path:
        return repairs

    for path, content in list(files.items()):
        if path.startswith("definition/tables/"):
            continue
        # Check for orphan measure definitions
        orphan_measures = re.findall(r"^\s*measure\s+'([^']+)'", content, re.MULTILINE)
        if orphan_measures:
            # Append to first table
            files[first_table_path] += "\n" + content
            del files[path]
            for m_name in orphan_measures:
                repairs.append(RepairAction(
                    pattern="orphan_measure",
                    severity="info",
                    description=f"Reassigned orphan measure '{m_name}' to first table",
                    file_path=first_table_path,
                    action_taken=f"moved from {path}",
                ))

    return repairs


# ---------------------------------------------------------------------------
# Pattern 4: Empty names
# ---------------------------------------------------------------------------

def _fix_empty_names(files: dict[str, str]) -> list[RepairAction]:
    """Remove table/column/measure definitions with empty names."""
    repairs: list[RepairAction] = []

    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue

        # Detect empty column/measure names
        empty_pattern = re.compile(r"^\s+(?:column|measure)\s+''\s*=?", re.MULTILINE)
        if empty_pattern.search(content):
            files[path] = empty_pattern.sub("", content)
            repairs.append(RepairAction(
                pattern="empty_name",
                severity="warning",
                description="Removed definition with empty name",
                file_path=path,
                action_taken="removed empty-name definition",
            ))

    return repairs


# ---------------------------------------------------------------------------
# Pattern 5: Circular relationships (Union-Find)
# ---------------------------------------------------------------------------

def _fix_circular_relationships(files: dict[str, str]) -> list[RepairAction]:
    """Detect and deactivate relationships that form cycles."""
    repairs: list[RepairAction] = []

    if "definition/relationships.tmdl" not in files:
        return repairs

    content = files["definition/relationships.tmdl"]
    uf = _UnionFind()

    # Parse relationships
    rel_blocks = re.split(r"(?=^relationship\s)", content, flags=re.MULTILINE)
    new_blocks: list[str] = []

    for block in rel_blocks:
        if not block.strip():
            continue

        from_m = re.search(r"fromTable:\s+'?([^'\n]+)'?", block)
        to_m = re.search(r"toTable:\s+'?([^'\n]+)'?", block)

        if from_m and to_m:
            from_t = from_m.group(1).strip()
            to_t = to_m.group(1).strip()

            if not uf.union(from_t, to_t):
                # Cycle detected — deactivate
                if "isActive: false" not in block:
                    block = block.rstrip() + "\n    isActive: false\n"
                    repairs.append(RepairAction(
                        pattern="circular_rel",
                        severity="error",
                        description=f"Circular relationship detected: {from_t} ↔ {to_t}",
                        action_taken="deactivated relationship",
                    ))

        new_blocks.append(block)

    files["definition/relationships.tmdl"] = "\n".join(new_blocks)
    return repairs


# ---------------------------------------------------------------------------
# Pattern 6: M query errors (try/otherwise)
# ---------------------------------------------------------------------------

def _fix_m_query_errors(files: dict[str, str]) -> list[RepairAction]:
    """Wrap M query partition expressions with try/otherwise for resilience."""
    repairs: list[RepairAction] = []

    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue

        # Find M query partition blocks
        partition_match = re.search(
            r"(partition\s+'[^']+'\s*=\s*m\s+mode:\s*import\s+source\s+)(let\s+.+?\n\s+\S+)",
            content,
            re.DOTALL,
        )
        if partition_match:
            m_expr = partition_match.group(2)
            # Check if already wrapped
            if "try" not in m_expr and "otherwise" not in m_expr:
                # Find the final 'in' block
                in_match = re.search(r"\n(\s+in\s*\n\s+\S+)$", m_expr)
                if in_match:
                    final_expr = in_match.group(1).strip()
                    # Wrap: try (original) otherwise #table({})
                    wrapped = m_expr.replace(
                        final_expr,
                        f"in\n                try {final_expr.replace('in', '').strip()} otherwise #table({{}})",
                    )
                    files[path] = content.replace(m_expr, wrapped)
                    repairs.append(RepairAction(
                        pattern="m_error",
                        severity="info",
                        description="Wrapped M query with try/otherwise",
                        file_path=path,
                        action_taken="added try/otherwise fallback",
                    ))

    return repairs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def self_heal(files: dict[str, str]) -> SelfHealingResult:
    """Run all 6 self-healing patterns on a TMDL file set.

    Parameters
    ----------
    files
        Dict of relative_path → TMDL content from generation.

    Returns
    -------
    SelfHealingResult
        Updated files and list of repairs applied.
    """
    all_repairs: list[RepairAction] = []

    # Run patterns in order
    all_repairs.extend(_fix_duplicate_tables(files))
    all_repairs.extend(_fix_broken_refs(files))
    all_repairs.extend(_fix_orphan_measures(files))
    all_repairs.extend(_fix_empty_names(files))
    all_repairs.extend(_fix_circular_relationships(files))
    all_repairs.extend(_fix_m_query_errors(files))

    result = SelfHealingResult(repairs=all_repairs, files=files)

    if all_repairs:
        logger.info(
            "Self-healing: %d repairs applied — %s",
            result.repair_count,
            result.by_pattern,
        )
    else:
        logger.info("Self-healing: no repairs needed")

    return result
