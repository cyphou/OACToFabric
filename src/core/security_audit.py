"""Security audit module — credential leak detection and hardening checks.

Provides:
- ``CredentialScanner`` — scans files, logs, and data for credential leaks.
- ``audit_config`` — verify a migration config dict has no plaintext secrets.
- ``audit_log_output`` — verify log lines don't contain sensitive values.
- ``AuditReport`` — structured output from a security scan.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audit finding severity
# ---------------------------------------------------------------------------


class FindingSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditFinding:
    """A single security audit finding."""

    file_path: str
    line_number: int
    pattern_name: str
    severity: FindingSeverity
    description: str
    snippet: str = ""  # redacted excerpt


@dataclass
class AuditReport:
    """Result of a security audit scan."""

    findings: list[AuditFinding] = field(default_factory=list)
    files_scanned: int = 0
    lines_scanned: int = 0

    @property
    def high_count(self) -> int:
        return sum(
            1
            for f in self.findings
            if f.severity in (FindingSeverity.HIGH, FindingSeverity.CRITICAL)
        )

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.LOW)

    @property
    def passed(self) -> bool:
        return self.high_count == 0

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"Security Audit [{status}]: "
            f"{len(self.findings)} findings "
            f"(critical+high={self.high_count}, medium={self.medium_count}, "
            f"low={self.low_count}) "
            f"across {self.files_scanned} files, {self.lines_scanned} lines"
        )


# ---------------------------------------------------------------------------
# Credential patterns
# ---------------------------------------------------------------------------

_CREDENTIAL_PATTERNS: list[tuple[str, re.Pattern[str], FindingSeverity]] = [
    (
        "hardcoded_password",
        re.compile(
            r"""(?:password|passwd|pwd)\s*[=:]\s*["'][^"']{4,}["']""",
            re.IGNORECASE,
        ),
        FindingSeverity.HIGH,
    ),
    (
        "hardcoded_api_key",
        re.compile(
            r"""(?:api[_-]?key|apikey)\s*[=:]\s*["'][A-Za-z0-9+/=]{16,}["']""",
            re.IGNORECASE,
        ),
        FindingSeverity.HIGH,
    ),
    (
        "hardcoded_connection_string",
        re.compile(
            r"""(?:connection[_-]?string|conn[_-]?str)\s*[=:]\s*["'][^"']{20,}["']""",
            re.IGNORECASE,
        ),
        FindingSeverity.HIGH,
    ),
    (
        "hardcoded_secret",
        re.compile(
            r"""(?:secret|client[_-]?secret)\s*[=:]\s*["'][^"']{8,}["']""",
            re.IGNORECASE,
        ),
        FindingSeverity.HIGH,
    ),
    (
        "bearer_token",
        re.compile(
            r"\bBearer\s+[A-Za-z0-9\-._~+/]+={0,2}\b",
            re.IGNORECASE,
        ),
        FindingSeverity.CRITICAL,
    ),
    (
        "private_key_header",
        re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
        FindingSeverity.CRITICAL,
    ),
    (
        "aws_access_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        FindingSeverity.HIGH,
    ),
    (
        "azure_storage_key",
        re.compile(
            r"""(?:AccountKey|account_key)\s*[=:]\s*["']?[A-Za-z0-9+/=]{44,88}["']?""",
            re.IGNORECASE,
        ),
        FindingSeverity.HIGH,
    ),
    (
        "generic_token_assignment",
        re.compile(
            r"""(?:token|access_token)\s*[=:]\s*["'][A-Za-z0-9\-._]{20,}["']""",
            re.IGNORECASE,
        ),
        FindingSeverity.MEDIUM,
    ),
]

# File extensions to skip
_SKIP_EXTENSIONS = {".pyc", ".pyo", ".exe", ".dll", ".so", ".bin", ".zip", ".gz", ".tar"}
_SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules", ".mypy_cache"}


# ---------------------------------------------------------------------------
# Credential Scanner
# ---------------------------------------------------------------------------


class CredentialScanner:
    """Scan source files for hardcoded credentials.

    Parameters
    ----------
    extra_patterns : list
        Additional ``(name, regex, severity)`` tuples to check.
    skip_extensions : set
        File extensions to skip.
    """

    def __init__(
        self,
        extra_patterns: list[tuple[str, re.Pattern[str], FindingSeverity]] | None = None,
        skip_extensions: set[str] | None = None,
    ) -> None:
        self._patterns = list(_CREDENTIAL_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)
        self._skip_exts = skip_extensions or _SKIP_EXTENSIONS

    def scan_file(self, file_path: str | Path) -> list[AuditFinding]:
        """Scan a single file for credential patterns."""
        path = Path(file_path)
        if path.suffix in self._skip_exts:
            return []

        findings: list[AuditFinding] = []
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return []

        for line_num, line in enumerate(text.splitlines(), 1):
            for pattern_name, regex, severity in self._patterns:
                if regex.search(line):
                    # Redact the actual secret in the snippet
                    snippet = line.strip()[:120]
                    findings.append(
                        AuditFinding(
                            file_path=str(path),
                            line_number=line_num,
                            pattern_name=pattern_name,
                            severity=severity,
                            description=f"Potential {pattern_name} detected",
                            snippet=snippet,
                        )
                    )

        return findings

    def scan_directory(self, directory: str | Path) -> AuditReport:
        """Recursively scan a directory for credential leaks."""
        root = Path(directory)
        report = AuditReport()

        for path in root.rglob("*"):
            if path.is_dir():
                continue
            if any(skip in path.parts for skip in _SKIP_DIRS):
                continue
            if path.suffix in self._skip_exts:
                continue

            report.files_scanned += 1
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                report.lines_scanned += len(lines)
            except (OSError, UnicodeDecodeError):
                continue

            file_findings = self.scan_file(path)
            report.findings.extend(file_findings)

        return report

    def scan_text(self, text: str, source: str = "<inline>") -> list[AuditFinding]:
        """Scan raw text (e.g. log output) for credential patterns."""
        findings: list[AuditFinding] = []
        for line_num, line in enumerate(text.splitlines(), 1):
            for pattern_name, regex, severity in self._patterns:
                if regex.search(line):
                    findings.append(
                        AuditFinding(
                            file_path=source,
                            line_number=line_num,
                            pattern_name=pattern_name,
                            severity=severity,
                            description=f"Potential {pattern_name} in text",
                            snippet=line.strip()[:120],
                        )
                    )
        return findings


# ---------------------------------------------------------------------------
# Config audit
# ---------------------------------------------------------------------------


def audit_config(config: dict[str, Any]) -> list[AuditFinding]:
    """Check a config dict for plaintext secrets.

    Examines all string values in the config (recursively) for patterns
    that look like credentials.
    """
    findings: list[AuditFinding] = []
    scanner = CredentialScanner()

    def _walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                _walk(val, f"{path}.{key}" if path else key)
        elif isinstance(obj, (list, tuple)):
            for i, val in enumerate(obj):
                _walk(val, f"{path}[{i}]")
        elif isinstance(obj, str):
            # Check if the key name suggests a secret
            key_lower = path.rsplit(".", 1)[-1].lower() if path else ""
            secret_key_words = {
                "password",
                "secret",
                "key",
                "token",
                "credential",
                "connection_string",
            }
            if any(w in key_lower for w in secret_key_words) and len(obj) > 4:
                # This is likely a plaintext secret
                findings.append(
                    AuditFinding(
                        file_path="<config>",
                        line_number=0,
                        pattern_name="config_plaintext_secret",
                        severity=FindingSeverity.HIGH,
                        description=f"Plaintext secret in config key: {path}",
                        snippet=f"{path} = ***redacted***",
                    )
                )

    _walk(config)
    return findings


def audit_log_output(log_text: str) -> list[AuditFinding]:
    """Scan log output for leaked credentials."""
    scanner = CredentialScanner()
    return scanner.scan_text(log_text, source="<log-output>")
