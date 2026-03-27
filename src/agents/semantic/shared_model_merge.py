"""Shared semantic model merge engine.

Enables multiple Power BI reports to share a single semantic model,
avoiding redundant table definitions and ensuring consistency.

Workflow:
1. Fingerprint all tables in each TMDL model (hash column names + types)
2. Identify overlapping/identical tables using Jaccard similarity
3. Produce one shared semantic model with all unique tables
4. Generate thin report references (byPath) pointing to the shared model
5. Output merge manifest with decisions and confidence scores
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------


@dataclass
class TableFingerprint:
    """Fingerprint for a single TMDL table."""

    table_name: str
    source_model: str
    columns: list[str]  # sorted column names
    column_types: dict[str, str]  # column_name → data type
    measures: list[str]
    row_hash: str = ""

    @property
    def fingerprint(self) -> str:
        """Content-based hash of the table structure."""
        sig = "|".join(sorted(self.columns))
        return hashlib.sha256(sig.encode()).hexdigest()[:16]


@dataclass
class MergeCandidate:
    """A pair of tables that may be merged."""

    table_a: TableFingerprint
    table_b: TableFingerprint
    jaccard_score: float
    decision: str = ""  # "merge" | "keep_both" | "review"
    confidence: float = 0.0


@dataclass
class MergeResult:
    """Result of merging multiple semantic models."""

    shared_tables: list[dict[str, Any]] = field(default_factory=list)
    thin_references: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[MergeCandidate] = field(default_factory=list)
    merge_decisions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def merged_count(self) -> int:
        return sum(1 for d in self.merge_decisions if d.get("decision") == "merge")

    @property
    def kept_count(self) -> int:
        return sum(1 for d in self.merge_decisions if d.get("decision") == "keep_both")


# ---------------------------------------------------------------------------
# Fingerprint extraction from TMDL content
# ---------------------------------------------------------------------------


def extract_table_fingerprint(
    table_name: str,
    tmdl_content: str,
    source_model: str = "",
) -> TableFingerprint:
    """Extract a fingerprint from TMDL table content."""
    columns: list[str] = []
    column_types: dict[str, str] = {}
    measures: list[str] = []

    for m in re.finditer(
        r"^\s+column\s+'([^']+)'\s*(?:=\s*)?(?:.*?dataType:\s*(\w+))?",
        tmdl_content,
        re.MULTILINE,
    ):
        col_name = m.group(1).strip()
        col_type = m.group(2) or "string"
        columns.append(col_name)
        column_types[col_name] = col_type

    for m in re.finditer(r"^\s+measure\s+'([^']+)'", tmdl_content, re.MULTILINE):
        measures.append(m.group(1).strip())

    return TableFingerprint(
        table_name=table_name,
        source_model=source_model,
        columns=sorted(columns),
        column_types=column_types,
        measures=sorted(measures),
    )


# ---------------------------------------------------------------------------
# Jaccard similarity
# ---------------------------------------------------------------------------


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


# ---------------------------------------------------------------------------
# Merge engine
# ---------------------------------------------------------------------------


def find_merge_candidates(
    fingerprints: list[TableFingerprint],
    threshold: float = 0.7,
) -> list[MergeCandidate]:
    """Find pairs of tables that are candidates for merging.

    Parameters
    ----------
    fingerprints
        All table fingerprints across all models.
    threshold
        Minimum Jaccard score to consider a merge.
    """
    candidates: list[MergeCandidate] = []
    seen_pairs: set[tuple[str, str]] = set()

    for i, fp_a in enumerate(fingerprints):
        for fp_b in fingerprints[i + 1:]:
            if fp_a.source_model == fp_b.source_model:
                continue  # Skip same-model comparisons
            pair_key = tuple(sorted([fp_a.fingerprint, fp_b.fingerprint]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            score = jaccard_similarity(
                set(fp_a.columns), set(fp_b.columns)
            )
            if score >= threshold:
                decision = "merge" if score >= 0.9 else "review"
                candidates.append(MergeCandidate(
                    table_a=fp_a,
                    table_b=fp_b,
                    jaccard_score=score,
                    decision=decision,
                    confidence=score,
                ))

    candidates.sort(key=lambda c: c.jaccard_score, reverse=True)
    return candidates


def merge_semantic_models(
    models: dict[str, dict[str, str]],
    threshold: float = 0.7,
) -> MergeResult:
    """Merge multiple TMDL semantic models into a shared model.

    Parameters
    ----------
    models
        Dict of model_name → { relative_path → tmdl_content }.
    threshold
        Minimum Jaccard score for auto-merge.

    Returns
    -------
    MergeResult
        Shared tables, thin references, and merge decisions.
    """
    result = MergeResult()

    # Step 1: Extract fingerprints from all models
    all_fingerprints: list[TableFingerprint] = []
    for model_name, files in models.items():
        for path, content in files.items():
            if not path.startswith("definition/tables/"):
                continue
            tbl_m = re.match(r"^table\s+'?([^'\n]+)'?", content)
            if tbl_m:
                fp = extract_table_fingerprint(
                    tbl_m.group(1).strip(), content, model_name
                )
                all_fingerprints.append(fp)

    # Step 2: Find merge candidates
    candidates = find_merge_candidates(all_fingerprints, threshold)
    result.candidates = candidates

    # Step 3: Build shared table set
    merged_tables: dict[str, TableFingerprint] = {}  # fingerprint_hash → fp
    for fp in all_fingerprints:
        if fp.fingerprint not in merged_tables:
            merged_tables[fp.fingerprint] = fp

    # Apply merge decisions
    merged_fingerprints: set[str] = set()
    for candidate in candidates:
        if candidate.decision == "merge":
            merged_fingerprints.add(candidate.table_b.fingerprint)
            # Keep table_a, drop table_b
            result.merge_decisions.append({
                "decision": "merge",
                "kept": candidate.table_a.table_name,
                "merged": candidate.table_b.table_name,
                "source_kept": candidate.table_a.source_model,
                "source_merged": candidate.table_b.source_model,
                "jaccard": candidate.jaccard_score,
                "confidence": candidate.confidence,
            })
        else:
            result.merge_decisions.append({
                "decision": "keep_both",
                "table_a": candidate.table_a.table_name,
                "table_b": candidate.table_b.table_name,
                "jaccard": candidate.jaccard_score,
                "reason": "below auto-merge threshold" if candidate.jaccard_score < 0.9 else "manual review",
            })

    # Step 4: Build shared tables list
    for fp_hash, fp in merged_tables.items():
        if fp_hash not in merged_fingerprints:
            result.shared_tables.append({
                "table_name": fp.table_name,
                "source_model": fp.source_model,
                "columns": fp.columns,
                "measures": fp.measures,
                "fingerprint": fp_hash,
            })

    # Step 5: Generate thin references
    for model_name in models:
        result.thin_references.append({
            "report_name": model_name,
            "semantic_model_ref": {
                "byPath": f"../{model_name}_SharedModel",
            },
        })

    logger.info(
        "Semantic model merge: %d shared tables, %d merged, %d kept separate",
        len(result.shared_tables),
        result.merged_count,
        result.kept_count,
    )
    return result


def generate_merge_manifest(result: MergeResult) -> str:
    """Generate a JSON merge manifest from merge results."""
    manifest = {
        "merge_summary": {
            "shared_tables": len(result.shared_tables),
            "merged_count": result.merged_count,
            "kept_separate": result.kept_count,
            "total_candidates": len(result.candidates),
        },
        "shared_tables": result.shared_tables,
        "thin_references": result.thin_references,
        "merge_decisions": result.merge_decisions,
    }
    return json.dumps(manifest, indent=2, default=str)
