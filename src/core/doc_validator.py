"""Documentation validator and project hygiene utilities.

Provides:
- ``DocValidator`` — scan docs for stale references, broken links, outdated versions.
- ``ChangelogGenerator`` — auto-generate changelog entries from structured commit metadata.
- ``ProjectHealthCheck`` — verify README, CHANGELOG, .env.example, CONTRIBUTING alignment.
- ``CIWorkflowGenerator`` — generate GitHub Actions YAML for lint, test, build.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Doc validation
# ---------------------------------------------------------------------------


class DocIssueType(str, Enum):
    """Types of documentation issues."""
    STALE_VERSION = "stale_version"
    BROKEN_LINK = "broken_link"
    MISSING_SECTION = "missing_section"
    OUTDATED_REFERENCE = "outdated_reference"
    MISSING_FILE = "missing_file"


@dataclass
class DocIssue:
    """A single documentation issue."""
    file_path: str
    issue_type: DocIssueType
    description: str
    line_number: int = 0
    severity: str = "warning"  # warning, error
    suggestion: str = ""


@dataclass
class DocValidationReport:
    """Result of a documentation validation scan."""
    issues: list[DocIssue] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"Doc Validation [{status}]: "
            f"{len(self.issues)} issues "
            f"({self.error_count} errors, {self.warning_count} warnings) "
            f"across {self.files_scanned} files"
        )

    def by_type(self, issue_type: DocIssueType) -> list[DocIssue]:
        return [i for i in self.issues if i.issue_type == issue_type]


class DocValidator:
    """Scan documentation files for quality issues."""

    VERSION_PATTERN = re.compile(r"v(\d+\.\d+\.\d+)")
    LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    HEADING_PATTERN = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)

    def __init__(self, current_version: str = "3.0.0") -> None:
        self.current_version = current_version

    def validate_content(
        self,
        content: str,
        file_path: str = "document.md",
        *,
        expected_sections: list[str] | None = None,
        min_version: str = "2.0.0",
    ) -> list[DocIssue]:
        """Validate a single document's content."""
        issues: list[DocIssue] = []

        # Check for stale versions
        issues.extend(self._check_versions(content, file_path, min_version))

        # Check for broken links
        issues.extend(self._check_links(content, file_path))

        # Check for expected sections
        if expected_sections:
            issues.extend(self._check_sections(content, file_path, expected_sections))

        return issues

    def validate_files(
        self,
        file_contents: dict[str, str],
        expected_files: list[str] | None = None,
    ) -> DocValidationReport:
        """Validate multiple documentation files."""
        report = DocValidationReport(files_scanned=len(file_contents))

        for path, content in file_contents.items():
            issues = self.validate_content(content, path)
            report.issues.extend(issues)

        # Check for missing expected files
        if expected_files:
            existing = set(file_contents.keys())
            for ef in expected_files:
                if ef not in existing:
                    report.issues.append(DocIssue(
                        file_path=ef,
                        issue_type=DocIssueType.MISSING_FILE,
                        description=f"Expected file not found: {ef}",
                        severity="error",
                    ))

        return report

    def _check_versions(
        self, content: str, file_path: str, min_version: str,
    ) -> list[DocIssue]:
        """Check for version references older than min_version."""
        issues: list[DocIssue] = []
        for i, line in enumerate(content.splitlines(), 1):
            for match in self.VERSION_PATTERN.finditer(line):
                ver = match.group(1)
                if self._version_lt(ver, min_version):
                    issues.append(DocIssue(
                        file_path=file_path,
                        issue_type=DocIssueType.STALE_VERSION,
                        description=f"Version {ver} is older than {min_version}",
                        line_number=i,
                        severity="warning",
                        suggestion=f"Update to v{self.current_version}",
                    ))
        return issues

    def _check_links(self, content: str, file_path: str) -> list[DocIssue]:
        """Check for potentially broken links."""
        issues: list[DocIssue] = []
        for i, line in enumerate(content.splitlines(), 1):
            for match in self.LINK_PATTERN.finditer(line):
                link_text = match.group(1)
                link_target = match.group(2)
                # Flag obviously broken patterns
                if link_target.startswith("http") and " " in link_target:
                    issues.append(DocIssue(
                        file_path=file_path,
                        issue_type=DocIssueType.BROKEN_LINK,
                        description=f"URL contains spaces: {link_target}",
                        line_number=i,
                        severity="error",
                    ))
                if link_target.endswith(".md") and "../../../" in link_target:
                    issues.append(DocIssue(
                        file_path=file_path,
                        issue_type=DocIssueType.BROKEN_LINK,
                        description=f"Deeply nested relative link: {link_target}",
                        line_number=i,
                        severity="warning",
                    ))
        return issues

    def _check_sections(
        self, content: str, file_path: str, expected: list[str],
    ) -> list[DocIssue]:
        """Check that expected sections are present."""
        issues: list[DocIssue] = []
        headings = [m.group(1).strip().lower() for m in self.HEADING_PATTERN.finditer(content)]
        for section in expected:
            if section.lower() not in headings:
                issues.append(DocIssue(
                    file_path=file_path,
                    issue_type=DocIssueType.MISSING_SECTION,
                    description=f"Missing expected section: {section}",
                    severity="warning",
                    suggestion=f"Add a section titled '{section}'",
                ))
        return issues

    @staticmethod
    def _version_lt(a: str, b: str) -> bool:
        """Return True if version a < version b."""
        try:
            a_parts = [int(x) for x in a.split(".")]
            b_parts = [int(x) for x in b.split(".")]
            return a_parts < b_parts
        except (ValueError, AttributeError):
            return False


# ---------------------------------------------------------------------------
# Changelog generator
# ---------------------------------------------------------------------------


@dataclass
class ChangelogEntry:
    """A single changelog entry."""
    version: str
    date: str
    category: str  # Added, Changed, Fixed, Removed
    description: str
    phase: int | None = None


class ChangelogGenerator:
    """Generate changelog entries from structured metadata."""

    CATEGORIES = ["Added", "Changed", "Fixed", "Removed", "Security"]

    def generate_entries(
        self,
        features: list[dict[str, Any]],
        version: str = "2.0.0",
        date: str = "",
    ) -> list[ChangelogEntry]:
        """Generate changelog entries from feature descriptors."""
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entries: list[ChangelogEntry] = []
        for feat in features:
            entries.append(ChangelogEntry(
                version=version,
                date=date,
                category=feat.get("category", "Added"),
                description=feat.get("description", ""),
                phase=feat.get("phase"),
            ))
        return entries

    def format_markdown(
        self,
        entries: list[ChangelogEntry],
        version: str = "2.0.0",
        date: str = "",
    ) -> str:
        """Format changelog entries as Markdown."""
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        lines = [f"## [{version}] — {date}", ""]

        # Group by category
        by_category: dict[str, list[ChangelogEntry]] = {}
        for entry in entries:
            by_category.setdefault(entry.category, []).append(entry)

        for cat in self.CATEGORIES:
            cat_entries = by_category.get(cat, [])
            if cat_entries:
                lines.append(f"### {cat}")
                for e in cat_entries:
                    phase_tag = f" (Phase {e.phase})" if e.phase else ""
                    lines.append(f"- {e.description}{phase_tag}")
                lines.append("")

        return "\n".join(lines)

    def generate_v2_changelog(self) -> str:
        """Generate the v1.1–v2.0 changelog entries."""
        features = [
            {"category": "Added", "description": "FastAPI Web API with REST + WebSocket endpoints", "phase": 23},
            {"category": "Added", "description": "Real-time migration monitoring via WebSocket", "phase": 23},
            {"category": "Added", "description": "Docker, Docker Compose, and Helm chart support", "phase": 24},
            {"category": "Added", "description": "Azure Container Apps deployment module", "phase": 24},
            {"category": "Added", "description": "Incremental/delta migration with change detection", "phase": 25},
            {"category": "Added", "description": "Sync journal and conflict resolution policies", "phase": 25},
            {"category": "Added", "description": "Multi-source connector framework (OAC, OBIEE, Tableau/Cognos/Qlik stubs)", "phase": 26},
            {"category": "Added", "description": "GPT-4o visual validation with screenshot comparison + SSIM", "phase": 27},
            {"category": "Added", "description": "Plugin architecture for translation rules, agents, and connectors", "phase": 28},
            {"category": "Added", "description": "Multi-tenant SaaS with RBAC, metering, and rate limiting", "phase": 29},
            {"category": "Added", "description": "Migration rollback engine with artifact versioning", "phase": 30},
        ]
        return self.format_markdown(
            self.generate_entries(features, "2.0.0"),
            version="2.0.0",
        )


# ---------------------------------------------------------------------------
# Project health check
# ---------------------------------------------------------------------------


@dataclass
class HealthCheckResult:
    """Result of a project health check."""
    checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(self.checks.values()) if self.checks else False

    @property
    def pass_count(self) -> int:
        return sum(1 for v in self.checks.values() if v)

    @property
    def fail_count(self) -> int:
        return sum(1 for v in self.checks.values() if not v)

    def summary(self) -> str:
        total = len(self.checks)
        status = "PASS" if self.passed else "FAIL"
        return f"Health Check [{status}]: {self.pass_count}/{total} checks passed"


class ProjectHealthCheck:
    """Verify project documentation alignment."""

    REQUIRED_FILES = [
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        ".env.example",
        "pyproject.toml",
    ]

    REQUIRED_README_SECTIONS = [
        "Quick Start",
    ]

    def check(self, file_contents: dict[str, str]) -> HealthCheckResult:
        """Run all health checks against the provided file contents."""
        result = HealthCheckResult()

        # Check required files
        for f in self.REQUIRED_FILES:
            exists = f in file_contents and len(file_contents[f]) > 0
            result.checks[f"file_{f}"] = exists
            if not exists:
                result.details[f"file_{f}"] = f"Missing or empty: {f}"

        # Check README content quality
        readme = file_contents.get("README.md", "")
        if readme:
            for section in self.REQUIRED_README_SECTIONS:
                key = f"readme_section_{section}"
                result.checks[key] = section.lower() in readme.lower()
                if not result.checks[key]:
                    result.details[key] = f"README missing section: {section}"

            # Check version references
            result.checks["readme_current_version"] = "v2.0" in readme or "2.0" in readme or "v3.0" in readme
            if not result.checks["readme_current_version"]:
                result.details["readme_current_version"] = "README doesn't reference current version"

        # Check CHANGELOG has v2.0 entry
        changelog = file_contents.get("CHANGELOG.md", "")
        if changelog:
            result.checks["changelog_v2"] = "2.0.0" in changelog or "[2.0" in changelog
            if not result.checks["changelog_v2"]:
                result.details["changelog_v2"] = "CHANGELOG missing v2.0.0 entry"

        # Check .env.example has key vars
        env = file_contents.get(".env.example", "")
        if env:
            required_vars = ["OAC_BASE_URL", "FABRIC_WORKSPACE_ID", "AZURE_OPENAI_ENDPOINT"]
            for var in required_vars:
                key = f"env_{var}"
                result.checks[key] = var in env
                if not result.checks[key]:
                    result.details[key] = f".env.example missing: {var}"

        return result


# ---------------------------------------------------------------------------
# CI Workflow generator
# ---------------------------------------------------------------------------


@dataclass
class CIWorkflowConfig:
    """Configuration for CI workflow generation."""
    python_versions: list[str] = field(default_factory=lambda: ["3.12", "3.13"])
    run_lint: bool = True
    run_tests: bool = True
    run_type_check: bool = False
    test_command: str = "python -m pytest tests/ --tb=short -q"
    install_command: str = "pip install -e '.[dev]'"
    os: str = "ubuntu-latest"


class CIWorkflowGenerator:
    """Generate GitHub Actions YAML workflow configuration."""

    def generate(self, config: CIWorkflowConfig | None = None) -> str:
        """Generate a GitHub Actions CI workflow YAML string."""
        cfg = config or CIWorkflowConfig()

        versions_str = ", ".join(f'"{v}"' for v in cfg.python_versions)

        lines = [
            "name: CI",
            "",
            "on:",
            "  push:",
            "    branches: [main, develop]",
            "  pull_request:",
            "    branches: [main]",
            "",
            "jobs:",
            "  test:",
            f"    runs-on: {cfg.os}",
            "    strategy:",
            "      matrix:",
            f"        python-version: [{versions_str}]",
            "",
            "    steps:",
            "      - uses: actions/checkout@v4",
            "",
            "      - name: Set up Python ${{ matrix.python-version }}",
            "        uses: actions/setup-python@v5",
            "        with:",
            "          python-version: ${{ matrix.python-version }}",
            "",
            "      - name: Install dependencies",
            "        run: |",
            f"          pip install --upgrade pip",
            f"          {cfg.install_command}",
        ]

        if cfg.run_lint:
            lines.extend([
                "",
                "      - name: Lint with ruff",
                "        run: |",
                "          pip install ruff",
                "          ruff check src/ tests/",
            ])

        if cfg.run_type_check:
            lines.extend([
                "",
                "      - name: Type check with mypy",
                "        run: |",
                "          pip install mypy",
                "          mypy src/",
            ])

        if cfg.run_tests:
            lines.extend([
                "",
                "      - name: Run tests",
                f"        run: {cfg.test_command}",
            ])

        lines.append("")
        return "\n".join(lines)

    def generate_config_dict(self, config: CIWorkflowConfig | None = None) -> dict[str, Any]:
        """Generate as a structured dict (for JSON/YAML serialization)."""
        cfg = config or CIWorkflowConfig()
        return {
            "name": "CI",
            "on": {
                "push": {"branches": ["main", "develop"]},
                "pull_request": {"branches": ["main"]},
            },
            "jobs": {
                "test": {
                    "runs-on": cfg.os,
                    "strategy": {
                        "matrix": {"python-version": cfg.python_versions},
                    },
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"name": "Set up Python", "uses": "actions/setup-python@v5"},
                        {"name": "Install dependencies", "run": cfg.install_command},
                        {"name": "Run tests", "run": cfg.test_command},
                    ],
                },
            },
        }
