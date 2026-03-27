"""TMDL self-healing — 17 auto-repair patterns.

Automatically detects and repairs common TMDL structural issues
that would cause deployment failures:

 1. Duplicate table names → rename with suffix
 2. Broken column refs → hide + annotation
 3. Orphan measures → reassign to first table
 4. Empty names → remove
 5. Circular relationships → Union-Find deactivate
 6. M query errors → try/otherwise wrapping
 7. Missing sort-by columns → remove sortByColumn property
 8. Invalid format strings → replace with DAX-safe default
 9. Duplicate measure names across tables → rename with table prefix
10. Missing relationship columns → remove relationship
11. Invalid partition mode → default to import
12. Duplicate column names within table → rename with suffix
13. Expression syntax brackets → normalise [col] refs
14. Missing display folder → add default "Migrated"
15. Unicode BOM in content → strip
16. Trailing whitespace in names → trim
17. Unreferenced hidden tables → annotate for review
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
# Pattern 7: Missing sort-by columns
# ---------------------------------------------------------------------------

def _fix_missing_sort_by(files: dict[str, str]) -> list[RepairAction]:
    """Remove sortByColumn references pointing to non-existent columns."""
    repairs: list[RepairAction] = []
    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        all_cols = {m.group(1).strip() for m in re.finditer(r"^\s+column\s+'?([^'=\n]+)'?", content, re.MULTILINE)}
        for m in re.finditer(r"sortByColumn:\s+'?([^'\n]+)'?", content):
            ref = m.group(1).strip()
            if ref not in all_cols:
                files[path] = content.replace(m.group(0), f"/// @migration: sortByColumn '{ref}' removed (not found)")
                content = files[path]
                repairs.append(RepairAction(
                    pattern="missing_sort_by",
                    severity="warning",
                    description=f"Removed sortByColumn '{ref}' (column not found)",
                    file_path=path,
                    action_taken="removed invalid sortByColumn",
                ))
    return repairs


# ---------------------------------------------------------------------------
# Pattern 8: Invalid format strings
# ---------------------------------------------------------------------------

_INVALID_FORMAT_CHARS = re.compile(r"[{}<>\\]")

def _fix_invalid_format_strings(files: dict[str, str]) -> list[RepairAction]:
    """Replace format strings containing invalid characters with safe defaults."""
    repairs: list[RepairAction] = []
    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        for m in re.finditer(r"formatString:\s+'([^'\n]+)'", content):
            fmt = m.group(1)
            if _INVALID_FORMAT_CHARS.search(fmt):
                safe_fmt = "0.00"
                files[path] = content.replace(m.group(0), f"formatString: '{safe_fmt}'")
                content = files[path]
                repairs.append(RepairAction(
                    pattern="invalid_format",
                    severity="info",
                    description=f"Replaced invalid format '{fmt}' with '{safe_fmt}'",
                    file_path=path,
                    action_taken="replaced format string",
                ))
    return repairs


# ---------------------------------------------------------------------------
# Pattern 9: Duplicate measure names across tables
# ---------------------------------------------------------------------------

def _fix_duplicate_measures(files: dict[str, str]) -> list[RepairAction]:
    """Detect measures with identical names across different tables and rename."""
    repairs: list[RepairAction] = []
    measure_locations: dict[str, list[str]] = {}  # measure_name → [file_paths]

    for path, content in files.items():
        if not path.startswith("definition/tables/"):
            continue
        for m in re.finditer(r"^\s+measure\s+'([^']+)'", content, re.MULTILINE):
            measure_locations.setdefault(m.group(1), []).append(path)

    for name, paths in measure_locations.items():
        if len(paths) <= 1:
            continue
        for i, path in enumerate(paths[1:], 2):
            content = files[path]
            # Extract table name for prefix
            tbl_match = re.match(r"^table\s+'?([^'\n]+)'?", content)
            prefix = tbl_match.group(1).strip() if tbl_match else f"T{i}"
            new_name = f"{prefix}_{name}"
            files[path] = content.replace(f"measure '{name}'", f"measure '{new_name}'", 1)
            repairs.append(RepairAction(
                pattern="duplicate_measure",
                severity="warning",
                description=f"Renamed duplicate measure '{name}' to '{new_name}'",
                file_path=path,
                action_taken=f"rename: {name} → {new_name}",
            ))
    return repairs


# ---------------------------------------------------------------------------
# Pattern 10: Missing relationship columns
# ---------------------------------------------------------------------------

def _fix_missing_rel_columns(files: dict[str, str]) -> list[RepairAction]:
    """Remove relationships referencing columns that don't exist in their tables."""
    repairs: list[RepairAction] = []
    if "definition/relationships.tmdl" not in files:
        return repairs

    # Collect all table→columns
    table_columns: dict[str, set[str]] = {}
    for path, content in files.items():
        if not path.startswith("definition/tables/"):
            continue
        tbl_m = re.match(r"^table\s+'?([^'\n]+)'?", content)
        if tbl_m:
            tbl_name = tbl_m.group(1).strip()
            cols = {m.group(1).strip() for m in re.finditer(r"^\s+column\s+'?([^'=\n]+)'?", content, re.MULTILINE)}
            table_columns[tbl_name] = cols

    content = files["definition/relationships.tmdl"]
    rel_blocks = re.split(r"(?=^relationship\s)", content, flags=re.MULTILINE)
    kept: list[str] = []
    for block in rel_blocks:
        if not block.strip():
            continue
        from_tbl = re.search(r"fromTable:\s+'?([^'\n]+)'?", block)
        from_col = re.search(r"fromColumn:\s+'?([^'\n]+)'?", block)
        to_tbl = re.search(r"toTable:\s+'?([^'\n]+)'?", block)
        to_col = re.search(r"toColumn:\s+'?([^'\n]+)'?", block)
        if from_tbl and from_col and to_tbl and to_col:
            ft, fc = from_tbl.group(1).strip(), from_col.group(1).strip()
            tt, tc = to_tbl.group(1).strip(), to_col.group(1).strip()
            if ft in table_columns and fc not in table_columns[ft]:
                repairs.append(RepairAction(
                    pattern="missing_rel_column",
                    severity="error",
                    description=f"Removed relationship: {ft}[{fc}] not found",
                    action_taken="removed relationship",
                ))
                continue
            if tt in table_columns and tc not in table_columns[tt]:
                repairs.append(RepairAction(
                    pattern="missing_rel_column",
                    severity="error",
                    description=f"Removed relationship: {tt}[{tc}] not found",
                    action_taken="removed relationship",
                ))
                continue
        kept.append(block)
    files["definition/relationships.tmdl"] = "\n".join(kept)
    return repairs


# ---------------------------------------------------------------------------
# Pattern 11: Invalid partition mode
# ---------------------------------------------------------------------------

def _fix_invalid_partition_mode(files: dict[str, str]) -> list[RepairAction]:
    """Replace unrecognised partition mode values with 'import'."""
    repairs: list[RepairAction] = []
    valid_modes = {"import", "directQuery", "dual", "directLake"}
    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        for m in re.finditer(r"mode:\s*(\w+)", content):
            mode = m.group(1)
            if mode not in valid_modes:
                files[path] = content.replace(m.group(0), "mode: import")
                content = files[path]
                repairs.append(RepairAction(
                    pattern="invalid_partition_mode",
                    severity="warning",
                    description=f"Replaced invalid mode '{mode}' with 'import'",
                    file_path=path,
                    action_taken="defaulted to import mode",
                ))
    return repairs


# ---------------------------------------------------------------------------
# Pattern 12: Duplicate column names within a table
# ---------------------------------------------------------------------------

def _fix_duplicate_columns(files: dict[str, str]) -> list[RepairAction]:
    """Rename duplicate column names within the same table."""
    repairs: list[RepairAction] = []
    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        col_names: dict[str, int] = {}
        for m in re.finditer(r"(column\s+'([^']+)')", content):
            name = m.group(2)
            col_names[name] = col_names.get(name, 0) + 1
            if col_names[name] > 1:
                new_name = f"{name}_{col_names[name]}"
                # Replace only this occurrence (use count from end)
                files[path] = files[path].replace(
                    f"column '{name}'", f"column '{new_name}'", 1
                )
                repairs.append(RepairAction(
                    pattern="duplicate_column",
                    severity="warning",
                    description=f"Renamed duplicate column '{name}' to '{new_name}'",
                    file_path=path,
                    action_taken=f"rename: {name} → {new_name}",
                ))
    return repairs


# ---------------------------------------------------------------------------
# Pattern 13: Expression syntax — normalise bracket references
# ---------------------------------------------------------------------------

def _fix_expression_brackets(files: dict[str, str]) -> list[RepairAction]:
    """Normalise unquoted column references in expressions to [col] form."""
    repairs: list[RepairAction] = []
    # OAC expressions sometimes use "Table.Column" instead of 'Table'[Column]
    dot_ref = re.compile(r"(?<!')(\b[A-Z]\w+)\.(\w+)\b(?!\])")
    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        if dot_ref.search(content):
            new_content = dot_ref.sub(r"'\1'[\2]", content)
            if new_content != content:
                files[path] = new_content
                repairs.append(RepairAction(
                    pattern="expression_brackets",
                    severity="info",
                    description="Normalised Table.Column refs to 'Table'[Column]",
                    file_path=path,
                    action_taken="bracket normalisation",
                ))
    return repairs


# ---------------------------------------------------------------------------
# Pattern 14: Missing display folder for migrated measures
# ---------------------------------------------------------------------------

def _fix_missing_display_folder(files: dict[str, str]) -> list[RepairAction]:
    """Add displayFolder: 'Migrated' to measures that lack one."""
    repairs: list[RepairAction] = []
    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        # Find measures without displayFolder
        measure_blocks = list(re.finditer(
            r"(measure\s+'[^']+'\s*=\s*[^\n]+(?:\n(?!\s*(?:measure|column|table)\s).*)*)",
            content,
        ))
        for mb in measure_blocks:
            block = mb.group(0)
            if "displayFolder" not in block:
                new_block = block.rstrip() + "\n        displayFolder: 'Migrated'\n"
                files[path] = files[path].replace(block, new_block, 1)
                repairs.append(RepairAction(
                    pattern="missing_display_folder",
                    severity="info",
                    description="Added displayFolder 'Migrated' to measure",
                    file_path=path,
                    action_taken="added displayFolder",
                ))
                break  # One per file to keep it manageable
    return repairs


# ---------------------------------------------------------------------------
# Pattern 15: Unicode BOM in content
# ---------------------------------------------------------------------------

def _fix_unicode_bom(files: dict[str, str]) -> list[RepairAction]:
    """Strip UTF-8 BOM from file content."""
    repairs: list[RepairAction] = []
    for path, content in list(files.items()):
        if content.startswith("\ufeff"):
            files[path] = content.lstrip("\ufeff")
            repairs.append(RepairAction(
                pattern="unicode_bom",
                severity="info",
                description="Stripped Unicode BOM",
                file_path=path,
                action_taken="removed BOM",
            ))
    return repairs


# ---------------------------------------------------------------------------
# Pattern 16: Trailing whitespace in names
# ---------------------------------------------------------------------------

def _fix_trailing_whitespace(files: dict[str, str]) -> list[RepairAction]:
    """Trim trailing whitespace from table/column/measure names."""
    repairs: list[RepairAction] = []
    ws_pat = re.compile(r"((?:table|column|measure)\s+'[^']*\s+')")
    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        for m in ws_pat.finditer(content):
            original = m.group(1)
            # Extract the name portion and trim
            name_m = re.search(r"'([^']*\s+)'", original)
            if name_m:
                trimmed_name = name_m.group(1).strip()
                fixed = original.replace(f"'{name_m.group(1)}'", f"'{trimmed_name}'")
                files[path] = files[path].replace(original, fixed, 1)
                repairs.append(RepairAction(
                    pattern="trailing_whitespace",
                    severity="info",
                    description=f"Trimmed whitespace from name '{name_m.group(1).strip()}'",
                    file_path=path,
                    action_taken="trimmed name",
                ))
    return repairs


# ---------------------------------------------------------------------------
# Pattern 17: Unreferenced hidden tables
# ---------------------------------------------------------------------------

def _fix_unreferenced_hidden(files: dict[str, str]) -> list[RepairAction]:
    """Annotate tables that are hidden and have no incoming relationships."""
    repairs: list[RepairAction] = []
    # Collect referenced tables from relationships
    referenced_tables: set[str] = set()
    if "definition/relationships.tmdl" in files:
        rel_content = files["definition/relationships.tmdl"]
        for m in re.finditer(r"(?:fromTable|toTable):\s+'?([^'\n]+)'?", rel_content):
            referenced_tables.add(m.group(1).strip())

    for path, content in list(files.items()):
        if not path.startswith("definition/tables/"):
            continue
        tbl_m = re.match(r"^table\s+'?([^'\n]+)'?", content)
        if not tbl_m:
            continue
        tbl_name = tbl_m.group(1).strip()
        if "isHidden" in content and tbl_name not in referenced_tables:
            if "@migration: unreferenced-hidden" not in content:
                files[path] = content + "\n    /// @migration: unreferenced-hidden — consider removing\n"
                repairs.append(RepairAction(
                    pattern="unreferenced_hidden",
                    severity="info",
                    description=f"Table '{tbl_name}' is hidden and unreferenced",
                    file_path=path,
                    action_taken="annotated for review",
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

    # Run all 17 patterns in order
    all_repairs.extend(_fix_unicode_bom(files))           # 15 — first: clean encoding
    all_repairs.extend(_fix_trailing_whitespace(files))   # 16
    all_repairs.extend(_fix_empty_names(files))           # 4
    all_repairs.extend(_fix_duplicate_tables(files))      # 1
    all_repairs.extend(_fix_duplicate_columns(files))     # 12
    all_repairs.extend(_fix_duplicate_measures(files))    # 9
    all_repairs.extend(_fix_broken_refs(files))           # 2
    all_repairs.extend(_fix_orphan_measures(files))       # 3
    all_repairs.extend(_fix_missing_sort_by(files))       # 7
    all_repairs.extend(_fix_invalid_format_strings(files))  # 8
    all_repairs.extend(_fix_expression_brackets(files))   # 13
    all_repairs.extend(_fix_invalid_partition_mode(files)) # 11
    all_repairs.extend(_fix_missing_rel_columns(files))   # 10
    all_repairs.extend(_fix_circular_relationships(files)) # 5
    all_repairs.extend(_fix_m_query_errors(files))        # 6
    all_repairs.extend(_fix_missing_display_folder(files)) # 14
    all_repairs.extend(_fix_unreferenced_hidden(files))   # 17

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
