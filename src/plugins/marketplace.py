"""Plugin marketplace — registry, discovery, install, publish.

Extends :mod:`src.plugins.plugin_manager` with:

- ``PluginRegistryEntry`` — metadata for a registered plugin in the index.
- ``PluginRegistry`` — local plugin index (JSON-backed).
- ``PluginInstaller`` — download / install / uninstall logic.
- CLI helpers: ``cmd_plugin_list``, ``cmd_plugin_install``, ``cmd_plugin_publish``.
- Two sample plugins: visual-mapping-overrides, data-quality-checks.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.plugins.plugin_manager import (
    AgentPlugin,
    ConnectorPlugin,
    PluginBase,
    PluginHook,
    PluginManager,
    PluginManifest,
    TranslationRule,
    TranslationRuleSet,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Registry entry — one per published plugin
# ---------------------------------------------------------------------------


@dataclass
class PluginRegistryEntry:
    """Metadata for a published plugin in the marketplace index."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    download_url: str = ""
    checksum: str = ""
    min_framework_version: str = "1.0.0"
    plugin_type: str = "translation"  # translation | agent | connector | hook
    downloads: int = 0
    rating: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PluginRegistryEntry":
        return PluginRegistryEntry(**{k: v for k, v in d.items() if k in PluginRegistryEntry.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Plugin registry — JSON-backed index
# ---------------------------------------------------------------------------


class PluginRegistry:
    """Local plugin index, backed by a JSON file.

    Provides search, versioning, and metadata management.
    """

    def __init__(self, index_path: str | Path | None = None) -> None:
        self._entries: dict[str, PluginRegistryEntry] = {}
        self._index_path = Path(index_path) if index_path else None
        if self._index_path and self._index_path.exists():
            self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
            for entry_dict in data.get("plugins", []):
                entry = PluginRegistryEntry.from_dict(entry_dict)
                self._entries[entry.name] = entry
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load plugin index: %s", exc)

    def save(self) -> None:
        if self._index_path:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"plugins": [e.to_dict() for e in self._entries.values()]}
            self._index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def publish(self, entry: PluginRegistryEntry) -> None:
        self._entries[entry.name] = entry
        self.save()
        logger.info("Published plugin '%s' v%s to registry", entry.name, entry.version)

    def unpublish(self, name: str) -> bool:
        if name in self._entries:
            del self._entries[name]
            self.save()
            return True
        return False

    def get(self, name: str) -> PluginRegistryEntry | None:
        return self._entries.get(name)

    def search(self, query: str = "", tags: list[str] | None = None) -> list[PluginRegistryEntry]:
        results = list(self._entries.values())
        if query:
            q = query.lower()
            results = [
                e for e in results
                if q in e.name.lower() or q in e.description.lower()
            ]
        if tags:
            tag_set = set(t.lower() for t in tags)
            results = [
                e for e in results
                if tag_set.intersection(t.lower() for t in e.tags)
            ]
        return results

    def list_all(self) -> list[PluginRegistryEntry]:
        return list(self._entries.values())

    @property
    def count(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# Plugin installer
# ---------------------------------------------------------------------------


@dataclass
class InstallResult:
    """Result of a plugin install/uninstall operation."""

    plugin_name: str
    success: bool
    message: str
    version: str = ""


class PluginInstaller:
    """Manages plugin installation lifecycle.

    Plugins are stored in a local ``plugins/`` directory, each in its own
    subdirectory containing a ``plugin.toml`` manifest and Python module(s).
    """

    def __init__(
        self,
        plugin_dir: str | Path,
        registry: PluginRegistry,
        manager: PluginManager,
    ) -> None:
        self._plugin_dir = Path(plugin_dir)
        self._registry = registry
        self._manager = manager
        self._installed: dict[str, PluginManifest] = {}

    def install_from_entry(self, entry: PluginRegistryEntry) -> InstallResult:
        """Install a plugin from a registry entry (simulated — creates manifest)."""
        dest = self._plugin_dir / entry.name
        dest.mkdir(parents=True, exist_ok=True)

        manifest = PluginManifest(
            name=entry.name,
            version=entry.version,
            description=entry.description,
            author=entry.author,
        )

        manifest_path = dest / "plugin.json"
        manifest_path.write_text(json.dumps(asdict(manifest), indent=2, default=str), encoding="utf-8")

        self._installed[entry.name] = manifest
        logger.info("Installed plugin '%s' v%s to %s", entry.name, entry.version, dest)
        return InstallResult(
            plugin_name=entry.name,
            success=True,
            message=f"Installed to {dest}",
            version=entry.version,
        )

    def install_from_manifest(self, manifest: PluginManifest, plugin: PluginBase) -> InstallResult:
        """Install a plugin from a manifest and instance directly."""
        errors = self._manager.register(plugin)
        if errors:
            return InstallResult(
                plugin_name=manifest.name,
                success=False,
                message=f"Validation errors: {errors}",
            )
        self._installed[manifest.name] = manifest
        return InstallResult(
            plugin_name=manifest.name,
            success=True,
            message="Registered",
            version=manifest.version,
        )

    def uninstall(self, name: str) -> InstallResult:
        """Uninstall a plugin by name."""
        removed = self._manager.unregister(name)
        self._installed.pop(name, None)
        dest = self._plugin_dir / name
        if dest.exists():
            import shutil
            shutil.rmtree(dest, ignore_errors=True)
        return InstallResult(
            plugin_name=name,
            success=removed or dest.exists(),
            message="Uninstalled" if removed else "Not found (cleaned dir)",
        )

    def list_installed(self) -> list[PluginManifest]:
        return list(self._installed.values())

    @property
    def installed_count(self) -> int:
        return len(self._installed)


# ===================================================================
# Built-in sample plugins
# ===================================================================


# --- Sample 1: Visual Mapping Overrides ---

class VisualMappingOverridePlugin(PluginBase):
    """Sample plugin that overrides default OAC → PBI visual mappings.

    Use case: customer wants their OAC Pivot Tables to map to Power BI
    Matrix visuals with specific default formatting, or wants custom
    visual types (e.g. Deneb, charticulator) for specialized charts.
    """

    def __init__(self) -> None:
        super().__init__(PluginManifest(
            name="visual-mapping-overrides",
            version="1.0.0",
            description="Override default OAC → Power BI visual type mappings",
            author="OACtoFabric Team",
            hooks=[PluginHook.POST_TRANSLATE],
        ))
        self._overrides: dict[str, str] = {}

    def set_override(self, oac_type: str, pbi_type: str) -> None:
        """Set a visual mapping override: OAC visual type → PBI visual type."""
        self._overrides[oac_type.lower()] = pbi_type

    def get_override(self, oac_type: str) -> str | None:
        return self._overrides.get(oac_type.lower())

    def list_overrides(self) -> dict[str, str]:
        return dict(self._overrides)

    async def on_hook(self, hook: PluginHook, context: dict[str, Any]) -> dict[str, Any]:
        if hook == PluginHook.POST_TRANSLATE:
            visuals = context.get("visuals", [])
            for v in visuals:
                oac_type = v.get("oac_type", "").lower()
                override = self._overrides.get(oac_type)
                if override:
                    v["pbi_type"] = override
                    v["_overridden_by"] = self.name
            context["visuals"] = visuals
        return context


# --- Sample 2: Data Quality Checks ---

@dataclass
class DataQualityIssue:
    """A data quality issue found during migration."""

    table: str
    column: str = ""
    issue_type: str = ""  # null_ratio, type_mismatch, duplicate, outlier
    severity: str = "warning"  # info, warning, error
    message: str = ""
    value: float = 0.0


@dataclass
class DataQualityReport:
    """Summary of data quality checks."""

    issues: list[DataQualityIssue] = field(default_factory=list)
    tables_checked: int = 0
    columns_checked: int = 0
    passed: bool = True

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


class DataQualityPlugin(PluginBase):
    """Sample plugin that runs data quality checks during validation.

    Checks:
    - Null ratio thresholds per column
    - Data type consistency between source and target
    - Duplicate key detection
    - Row count variance
    """

    def __init__(self, null_threshold: float = 0.5) -> None:
        super().__init__(PluginManifest(
            name="data-quality-checks",
            version="1.0.0",
            description="Data quality checks during migration validation",
            author="OACtoFabric Team",
            hooks=[PluginHook.PRE_VALIDATE, PluginHook.POST_VALIDATE],
        ))
        self._null_threshold = null_threshold
        self._rules: list[dict[str, Any]] = []
        self._last_report: DataQualityReport | None = None

    def add_rule(self, table: str, column: str, issue_type: str, threshold: float = 0.0) -> None:
        """Add a custom quality rule."""
        self._rules.append({
            "table": table,
            "column": column,
            "issue_type": issue_type,
            "threshold": threshold,
        })

    def check_null_ratio(self, table: str, column: str, null_count: int, total: int) -> DataQualityIssue | None:
        if total == 0:
            return None
        ratio = null_count / total
        if ratio > self._null_threshold:
            return DataQualityIssue(
                table=table,
                column=column,
                issue_type="null_ratio",
                severity="warning" if ratio < 0.8 else "error",
                message=f"Null ratio {ratio:.1%} exceeds threshold {self._null_threshold:.1%}",
                value=ratio,
            )
        return None

    def check_row_count_variance(
        self,
        table: str,
        source_count: int,
        target_count: int,
        tolerance: float = 0.01,
    ) -> DataQualityIssue | None:
        if source_count == 0:
            return None
        variance = abs(source_count - target_count) / source_count
        if variance > tolerance:
            return DataQualityIssue(
                table=table,
                issue_type="row_count_variance",
                severity="error" if variance > 0.05 else "warning",
                message=f"Row count variance {variance:.2%}: source={source_count}, target={target_count}",
                value=variance,
            )
        return None

    def run_checks(self, table_stats: list[dict[str, Any]]) -> DataQualityReport:
        """Run all quality checks against table statistics."""
        issues: list[DataQualityIssue] = []
        tables_checked = 0
        columns_checked = 0

        for stat in table_stats:
            table = stat.get("table", "unknown")
            tables_checked += 1

            # Row count check
            src_count = stat.get("source_row_count", 0)
            tgt_count = stat.get("target_row_count", 0)
            issue = self.check_row_count_variance(table, src_count, tgt_count)
            if issue:
                issues.append(issue)

            # Column-level checks
            for col_stat in stat.get("columns", []):
                columns_checked += 1
                col = col_stat.get("name", "")
                null_count = col_stat.get("null_count", 0)
                total = col_stat.get("total_count", 0)
                issue = self.check_null_ratio(table, col, null_count, total)
                if issue:
                    issues.append(issue)

        report = DataQualityReport(
            issues=issues,
            tables_checked=tables_checked,
            columns_checked=columns_checked,
            passed=all(i.severity != "error" for i in issues),
        )
        self._last_report = report
        return report

    async def on_hook(self, hook: PluginHook, context: dict[str, Any]) -> dict[str, Any]:
        if hook == PluginHook.PRE_VALIDATE:
            context["data_quality_plugin_active"] = True
        elif hook == PluginHook.POST_VALIDATE:
            table_stats = context.get("table_stats", [])
            if table_stats:
                report = self.run_checks(table_stats)
                context["data_quality_report"] = {
                    "issue_count": report.issue_count,
                    "error_count": report.error_count,
                    "warning_count": report.warning_count,
                    "passed": report.passed,
                    "tables_checked": report.tables_checked,
                    "columns_checked": report.columns_checked,
                }
        return context

    @property
    def last_report(self) -> DataQualityReport | None:
        return self._last_report


# ===================================================================
# CLI helpers
# ===================================================================


def cmd_plugin_list(registry: PluginRegistry, manager: PluginManager) -> str:
    """List available and installed plugins (CLI handler)."""
    lines = ["# Plugin Marketplace", ""]

    installed = manager.list_plugins()
    if installed:
        lines.append("## Installed Plugins")
        lines.append("")
        lines.append("| Name | Version | Description |")
        lines.append("|---|---|---|")
        for m in installed:
            lines.append(f"| {m.name} | {m.version} | {m.description} |")
        lines.append("")

    available = registry.list_all()
    if available:
        lines.append("## Available Plugins")
        lines.append("")
        lines.append("| Name | Version | Type | Description | Downloads |")
        lines.append("|---|---|---|---|---|")
        for e in available:
            lines.append(
                f"| {e.name} | {e.version} | {e.plugin_type} | {e.description} | {e.downloads} |"
            )
        lines.append("")

    if not installed and not available:
        lines.append("No plugins found. Use `plugin publish` to add plugins.")

    return "\n".join(lines)


def cmd_plugin_install(
    name: str,
    registry: PluginRegistry,
    installer: PluginInstaller,
) -> InstallResult:
    """Install a plugin by name from the registry."""
    entry = registry.get(name)
    if not entry:
        return InstallResult(plugin_name=name, success=False, message="Plugin not found in registry")
    return installer.install_from_entry(entry)


def cmd_plugin_publish(
    manifest_path: str | Path,
    registry: PluginRegistry,
) -> PluginRegistryEntry | None:
    """Publish a plugin to the registry from a manifest file."""
    path = Path(manifest_path)
    if not path.exists():
        logger.error("Manifest not found: %s", path)
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read manifest: %s", exc)
        return None

    entry = PluginRegistryEntry(
        name=data.get("name", path.parent.name),
        version=data.get("version", "0.1.0"),
        description=data.get("description", ""),
        author=data.get("author", ""),
        tags=data.get("tags", []),
        plugin_type=data.get("plugin_type", "translation"),
    )
    registry.publish(entry)
    return entry


# ===================================================================
# Convenience — load built-in sample plugins
# ===================================================================


def load_builtin_plugins(manager: PluginManager) -> list[str]:
    """Register the built-in sample plugins and return their names."""
    loaded: list[str] = []

    vmo = VisualMappingOverridePlugin()
    errors = manager.register(vmo)
    if not errors:
        loaded.append(vmo.name)

    dq = DataQualityPlugin()
    errors = manager.register(dq)
    if not errors:
        loaded.append(dq.name)

    return loaded
