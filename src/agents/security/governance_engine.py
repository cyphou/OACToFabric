"""Governance engine — naming conventions, PII detection, sensitivity labels, audit trail.

Ported from T2P's GovernanceEngine — enforces or warns about naming
conventions, detects PII columns, maps roles to sensitivity labels,
and produces an audit trail of governance findings.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_GOVERNANCE_CONFIG: dict[str, Any] = {
    "mode": "warn",     # "warn" = log warnings, "enforce" = fail on violation
    "naming": {
        "measure_prefix": "m_",
        "column_style": "snake_case",     # snake_case | PascalCase | camelCase
        "table_style": "PascalCase",
        "max_name_length": 128,
    },
    "pii_detection": True,
    "sensitivity_mapping": {
        "Administrator": "Highly Confidential",
        "PowerUser": "Confidential",
        "Viewer": "General",
        "Public": "Public",
    },
    "audit_trail": True,
}


# ---------------------------------------------------------------------------
# PII patterns (15 regex patterns)
# ---------------------------------------------------------------------------

_PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("email", re.compile(r"\bemail\b", re.IGNORECASE), "email"),
    ("ssn", re.compile(r"\bssn\b|social[_.\s]?security", re.IGNORECASE), "ssn"),
    ("phone", re.compile(r"\bphone\b|\bmobile\b|\bcell\b", re.IGNORECASE), "phone"),
    ("name_personal", re.compile(r"\b(?:first|last|full)[_.\s]?name\b", re.IGNORECASE), "name"),
    ("credit_card", re.compile(r"\bcredit[_.\s]?card\b|\bpan\b|\bcard[_.\s]?number\b", re.IGNORECASE), "creditCard"),
    ("address", re.compile(r"\baddress\b|\bstreet\b|\bzip\b|\bpostal\b", re.IGNORECASE), "address"),
    ("date_of_birth", re.compile(r"\bdob\b|\bbirth[_.\s]?date\b|\bdate[_.\s]?of[_.\s]?birth\b", re.IGNORECASE), "dob"),
    ("national_id", re.compile(r"\bnational[_.\s]?id\b|\bpassport\b|\bdriver[_.\s]?licen[sc]e\b", re.IGNORECASE), "nationalId"),
    ("ip_address", re.compile(r"\bip[_.\s]?addr\b|\bip[_.\s]?address\b", re.IGNORECASE), "ipAddress"),
    ("medical_record", re.compile(r"\bmrn\b|\bmedical[_.\s]?record\b|\bicd\b", re.IGNORECASE), "medicalRecord"),
    ("bank_account", re.compile(r"\baccount[_.\s]?number\b|\brouting[_.\s]?number\b|\biban\b", re.IGNORECASE), "bankAccount"),
    ("salary", re.compile(r"\bsalary\b|\bwage\b|\bcompensation\b|\bincome\b", re.IGNORECASE), "salary"),
    ("gender", re.compile(r"\bgender\b|\bsex\b", re.IGNORECASE), "gender"),
    ("ethnicity", re.compile(r"\bethnicity\b|\brace\b", re.IGNORECASE), "ethnicity"),
    ("religion", re.compile(r"\breligion\b|\bfaith\b", re.IGNORECASE), "religion"),
]


# ---------------------------------------------------------------------------
# Credential redaction (10 patterns)
# ---------------------------------------------------------------------------

_CREDENTIAL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(password\s*=\s*)([^\s;,\"']+)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(Bearer\s+)([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(client[_.]?secret\s*=\s*)([^\s;,\"']+)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(api[_.]?key\s*=\s*)([^\s;,\"']+)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(access[_.]?token\s*=\s*)([^\s;,\"']+)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(secret\s*=\s*)([^\s;,\"']+)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(conn(?:ection)?[_.]?string\s*=\s*[\"'])([^\"']+)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(SharedAccessKey=)([A-Za-z0-9+/=]+)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(AccountKey=)([A-Za-z0-9+/=]+)", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(sig=)([A-Za-z0-9%+/=]+)", re.IGNORECASE), r"\1***REDACTED***"),
]


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------


@dataclass
class GovernanceFinding:
    """A single governance finding."""

    category: str       # naming | pii | credential | sensitivity
    severity: str       # info | warning | error
    message: str
    location: str = ""  # table.column or file path
    auto_fixed: bool = False


@dataclass
class GovernanceReport:
    """Aggregate governance report."""

    findings: list[GovernanceFinding] = field(default_factory=list)
    mode: str = "warn"
    pii_columns: list[dict[str, str]] = field(default_factory=list)

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)

    @property
    def by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.category] = counts.get(f.category, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Naming convention checks
# ---------------------------------------------------------------------------

_STYLE_CHECKS: dict[str, re.Pattern[str]] = {
    "snake_case": re.compile(r"^[a-z][a-z0-9_]*$"),
    "PascalCase": re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
    "camelCase": re.compile(r"^[a-z][a-zA-Z0-9]*$"),
}


def check_naming(
    name: str,
    name_type: str,     # "table" | "column" | "measure"
    config: dict[str, Any] | None = None,
) -> list[GovernanceFinding]:
    """Check a name against naming conventions."""
    cfg = config or DEFAULT_GOVERNANCE_CONFIG["naming"]
    findings: list[GovernanceFinding] = []

    max_len = cfg.get("max_name_length", 128)
    if len(name) > max_len:
        findings.append(GovernanceFinding(
            category="naming",
            severity="warning",
            message=f"{name_type} name '{name}' exceeds max length ({len(name)} > {max_len})",
            location=name,
        ))

    if name_type == "measure":
        prefix = cfg.get("measure_prefix", "")
        if prefix and not name.startswith(prefix):
            findings.append(GovernanceFinding(
                category="naming",
                severity="info",
                message=f"Measure '{name}' missing prefix '{prefix}'",
                location=name,
            ))

    style_key = f"{name_type}_style"
    expected_style = cfg.get(style_key, "")
    if expected_style and expected_style in _STYLE_CHECKS:
        pattern = _STYLE_CHECKS[expected_style]
        if not pattern.match(name):
            findings.append(GovernanceFinding(
                category="naming",
                severity="info",
                message=f"{name_type} '{name}' does not match {expected_style} convention",
                location=name,
            ))

    return findings


# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------


def detect_pii(column_name: str) -> list[GovernanceFinding]:
    """Scan a column name for PII indicators.

    Returns governance findings for any detected PII categories.
    """
    findings: list[GovernanceFinding] = []

    for pii_name, pattern, pii_type in _PII_PATTERNS:
        if pattern.search(column_name):
            findings.append(GovernanceFinding(
                category="pii",
                severity="warning",
                message=f"Potential PII detected: {pii_name} (type: {pii_type})",
                location=column_name,
            ))

    return findings


def scan_tables_for_pii(
    tables: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Scan all tables for PII columns.

    Returns list of dicts with 'table', 'column', 'pii_type' keys.
    """
    pii_columns: list[dict[str, str]] = []

    for table in tables:
        table_name = table.get("name", "")
        for col in table.get("columns", []):
            col_name = col.get("name", "")
            for pii_name, pattern, pii_type in _PII_PATTERNS:
                if pattern.search(col_name):
                    pii_columns.append({
                        "table": table_name,
                        "column": col_name,
                        "pii_type": pii_type,
                    })

    if pii_columns:
        logger.warning("PII scan: %d potential PII columns detected", len(pii_columns))

    return pii_columns


# ---------------------------------------------------------------------------
# Credential redaction
# ---------------------------------------------------------------------------


def redact_credentials(text: str) -> tuple[str, int]:
    """Redact credentials from text (connection strings, tokens, passwords).

    Returns (redacted_text, count_of_redactions).
    """
    result = text
    count = 0

    for pattern, replacement in _CREDENTIAL_PATTERNS:
        new_result = pattern.sub(replacement, result)
        if new_result != result:
            count += 1
            result = new_result

    return result, count


# ---------------------------------------------------------------------------
# Sensitivity label mapping
# ---------------------------------------------------------------------------


def map_sensitivity_label(
    role_name: str,
    config: dict[str, str] | None = None,
) -> str:
    """Map an OAC role name to a Purview sensitivity label.

    Returns the sensitivity label string.
    """
    label_map = config or DEFAULT_GOVERNANCE_CONFIG.get("sensitivity_mapping", {})
    return label_map.get(role_name, "General")


# ---------------------------------------------------------------------------
# Full governance scan
# ---------------------------------------------------------------------------


def run_governance_scan(
    tables: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> GovernanceReport:
    """Run a full governance scan on table definitions.

    Checks naming conventions, PII, and produces a report.

    Parameters
    ----------
    tables
        List of table dicts with 'name' and 'columns' keys.
    config
        Governance config dict (defaults to DEFAULT_GOVERNANCE_CONFIG).
    """
    cfg = config or DEFAULT_GOVERNANCE_CONFIG
    naming_cfg = cfg.get("naming", DEFAULT_GOVERNANCE_CONFIG["naming"])
    report = GovernanceReport(mode=cfg.get("mode", "warn"))

    for table in tables:
        table_name = table.get("name", "")

        # Check table naming
        report.findings.extend(check_naming(table_name, "table", naming_cfg))

        for col in table.get("columns", []):
            col_name = col.get("name", "")

            # Check column naming
            report.findings.extend(check_naming(col_name, "column", naming_cfg))

            # PII detection
            if cfg.get("pii_detection", True):
                report.findings.extend(detect_pii(col_name))

        # Check measure naming
        for measure in table.get("measures", []):
            m_name = measure.get("name", "") if isinstance(measure, dict) else str(measure)
            report.findings.extend(check_naming(m_name, "measure", naming_cfg))

    # PII column inventory
    if cfg.get("pii_detection", True):
        report.pii_columns = scan_tables_for_pii(tables)

    logger.info(
        "Governance scan: %d findings (%s)",
        report.finding_count, report.by_category,
    )

    return report
