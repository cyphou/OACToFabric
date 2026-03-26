"""OAC function leak detector for generated DAX.

Scans generated DAX expressions for un-translated OAC/Oracle functions
that would cause deployment failures — provides regex-based detection
with auto-fix suggestions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Leak patterns: (compiled_regex, description, auto_fix_suggestion)
# ---------------------------------------------------------------------------

_OAC_FUNCTION_LEAK_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\bNVL\s*\(", re.IGNORECASE), "NVL (Oracle null-coalesce)", "COALESCE"),
    (re.compile(r"\bNVL2\s*\(", re.IGNORECASE), "NVL2 (Oracle conditional null)", "IF(ISBLANK(...), else, then)"),
    (re.compile(r"\bDECODE\s*\(", re.IGNORECASE), "DECODE (Oracle case expression)", "SWITCH"),
    (re.compile(r"\bSYSDATE\b", re.IGNORECASE), "SYSDATE (Oracle current date)", "TODAY()"),
    (re.compile(r"\bSYSTIMESTAMP\b", re.IGNORECASE), "SYSTIMESTAMP (Oracle current timestamp)", "NOW()"),
    (re.compile(r"\bROWNUM\b", re.IGNORECASE), "ROWNUM (Oracle row numbering)", "RANKX or ROW_NUMBER via ADDCOLUMNS"),
    (re.compile(r"\bSUBSTR\s*\(", re.IGNORECASE), "SUBSTR (Oracle substring)", "MID"),
    (re.compile(r"\bINSTR\s*\(", re.IGNORECASE), "INSTR (Oracle string position)", "SEARCH or FIND"),
    (re.compile(r"\bTRUNC\s*\(", re.IGNORECASE), "TRUNC (Oracle truncate)", "TRUNC → INT or ROUNDDOWN"),
    (re.compile(r"\bTO_CHAR\s*\(", re.IGNORECASE), "TO_CHAR (Oracle format)", "FORMAT"),
    (re.compile(r"\bTO_DATE\s*\(", re.IGNORECASE), "TO_DATE (Oracle parse date)", "DATEVALUE"),
    (re.compile(r"\bTO_NUMBER\s*\(", re.IGNORECASE), "TO_NUMBER (Oracle parse number)", "VALUE"),
    (re.compile(r"\bVALUEOF\s*\(\s*NQ_SESSION\.", re.IGNORECASE), "VALUEOF(NQ_SESSION.*) (OAC session variable)", "USERPRINCIPALNAME() or custom RLS"),
    (re.compile(r"\bEVALUATE_PREDICATE\b", re.IGNORECASE), "EVALUATE_PREDICATE (OAC)", "DAX filter expression"),
    (re.compile(r"\bPRESENTATION_VARIABLE\b", re.IGNORECASE), "PRESENTATION_VARIABLE (OAC)", "What-If parameter or slicer"),
    (re.compile(r"\bREPOSITORY_VARIABLE\b", re.IGNORECASE), "REPOSITORY_VARIABLE (OAC)", "Configuration table lookup"),
    (re.compile(r"\bSESSION_VARIABLE\b", re.IGNORECASE), "SESSION_VARIABLE (OAC)", "USERPRINCIPALNAME()"),
    (re.compile(r"\bFROM\s+DUAL\b", re.IGNORECASE), "FROM DUAL (Oracle dummy table)", "Remove — not needed in DAX"),
    (re.compile(r"\(\+\)", re.IGNORECASE), "(+) (Oracle outer join syntax)", "Use relationship or NATURALLEFTOUTERJOIN"),
    (re.compile(r"\bLISTAGG\s*\(", re.IGNORECASE), "LISTAGG (Oracle aggregation)", "CONCATENATEX"),
    (re.compile(r"\bROWID\b", re.IGNORECASE), "ROWID (Oracle physical row ID)", "Remove — not applicable in DAX"),
    (re.compile(r"\bCONNECT\s+BY\b", re.IGNORECASE), "CONNECT BY (Oracle hierarchical query)", "PATH/PATHCONTAINS pattern"),
]


# ---------------------------------------------------------------------------
# Auto-fix map (simple replacements)
# ---------------------------------------------------------------------------

_AUTO_FIX_MAP: dict[str, tuple[re.Pattern[str], str]] = {
    "NVL": (re.compile(r"\bNVL\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)", re.IGNORECASE), r"COALESCE(\1, \2)"),
    "SYSDATE": (re.compile(r"\bSYSDATE\b", re.IGNORECASE), "TODAY()"),
    "SYSTIMESTAMP": (re.compile(r"\bSYSTIMESTAMP\b", re.IGNORECASE), "NOW()"),
    "FROM DUAL": (re.compile(r"\bFROM\s+DUAL\b", re.IGNORECASE), ""),
    "ROWID": (re.compile(r"\bROWID\b", re.IGNORECASE), ""),
}


# ---------------------------------------------------------------------------
# Leak detection result
# ---------------------------------------------------------------------------


@dataclass
class LeakDetection:
    """A single detected OAC/Oracle function leak in DAX."""

    function_name: str
    description: str
    suggestion: str
    measure_name: str = ""
    table_name: str = ""
    match_text: str = ""
    auto_fixable: bool = False


@dataclass
class LeakDetectorResult:
    """Result of scanning a TMDL file set for function leaks."""

    leaks: list[LeakDetection] = field(default_factory=list)
    auto_fixed: int = 0
    total_measures_scanned: int = 0

    @property
    def leak_count(self) -> int:
        return len(self.leaks)

    @property
    def has_leaks(self) -> bool:
        return bool(self.leaks)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_dax_for_leaks(
    dax: str,
    measure_name: str = "",
    table_name: str = "",
) -> list[LeakDetection]:
    """Scan a single DAX expression for OAC/Oracle function leaks."""
    leaks: list[LeakDetection] = []

    for pattern, description, suggestion in _OAC_FUNCTION_LEAK_PATTERNS:
        match = pattern.search(dax)
        if match:
            func_name = description.split("(")[0].strip()
            leaks.append(LeakDetection(
                function_name=func_name,
                description=description,
                suggestion=suggestion,
                measure_name=measure_name,
                table_name=table_name,
                match_text=match.group(0),
                auto_fixable=func_name in _AUTO_FIX_MAP,
            ))

    return leaks


def auto_fix_dax(dax: str) -> tuple[str, int]:
    """Auto-fix known OAC/Oracle function leaks in DAX.

    Returns (fixed_dax, fix_count).
    """
    fixed = dax
    fix_count = 0

    for name, (pattern, replacement) in _AUTO_FIX_MAP.items():
        new = pattern.sub(replacement, fixed)
        if new != fixed:
            fix_count += 1
            fixed = new

    return fixed, fix_count


def scan_tmdl_files(files: dict[str, str]) -> LeakDetectorResult:
    """Scan all TMDL table files for OAC function leaks.

    Parameters
    ----------
    files
        Dict of relative_path → content (from TMDLGenerationResult.files).

    Returns
    -------
    LeakDetectorResult
        All detected leaks with auto-fix suggestion.
    """
    all_leaks: list[LeakDetection] = []
    auto_fixed = 0
    total_measures = 0

    for path, content in files.items():
        if not path.startswith("definition/tables/"):
            continue

        # Extract table name
        table_match = re.match(r"^table\s+'?([^'\n]+)", content)
        table_name = table_match.group(1).strip() if table_match else path

        # Find all measures and calculated columns with expressions
        for m in re.finditer(
            r"(?:measure|column)\s+'([^']+)'\s*=\s*(.+?)(?=\n\s+\w|\Z)",
            content,
            re.DOTALL,
        ):
            measure_name = m.group(1)
            dax_expr = m.group(2).strip()
            total_measures += 1

            leaks = scan_dax_for_leaks(dax_expr, measure_name, table_name)
            all_leaks.extend(leaks)
            auto_fixed += sum(1 for l in leaks if l.auto_fixable)

    result = LeakDetectorResult(
        leaks=all_leaks,
        auto_fixed=auto_fixed,
        total_measures_scanned=total_measures,
    )

    if all_leaks:
        logger.warning(
            "Leak detector: %d OAC function leaks found in %d measures (%d auto-fixable)",
            result.leak_count, total_measures, auto_fixed,
        )
    else:
        logger.info("Leak detector: no OAC function leaks found")

    return result
