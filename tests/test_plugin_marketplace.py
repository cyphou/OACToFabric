"""Tests for the plugin marketplace (Phase 42).

Covers:
- PluginRegistryEntry model
- PluginRegistry — publish, search, list, save/load
- PluginInstaller — install/uninstall lifecycle
- VisualMappingOverridePlugin — override hooks
- DataQualityPlugin — null ratio, row count, hooks
- CLI helpers — list, install, publish
- load_builtin_plugins convenience
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.plugins.marketplace import (
    DataQualityIssue,
    DataQualityPlugin,
    DataQualityReport,
    InstallResult,
    PluginInstaller,
    PluginRegistry,
    PluginRegistryEntry,
    VisualMappingOverridePlugin,
    cmd_plugin_install,
    cmd_plugin_list,
    cmd_plugin_publish,
    load_builtin_plugins,
)
from src.plugins.plugin_manager import (
    PluginBase,
    PluginHook,
    PluginManager,
    PluginManifest,
    TranslationRule,
    TranslationRuleSet,
)


# ===================================================================
# PluginRegistryEntry
# ===================================================================


class TestPluginRegistryEntry:
    def test_defaults(self):
        e = PluginRegistryEntry(name="my-plugin")
        assert e.version == "0.1.0"
        assert e.plugin_type == "translation"
        assert e.downloads == 0

    def test_to_dict(self):
        e = PluginRegistryEntry(name="x", version="1.0.0", tags=["dax"])
        d = e.to_dict()
        assert d["name"] == "x"
        assert d["tags"] == ["dax"]

    def test_from_dict(self):
        d = {"name": "x", "version": "2.0.0", "author": "Alice"}
        e = PluginRegistryEntry.from_dict(d)
        assert e.name == "x"
        assert e.version == "2.0.0"
        assert e.author == "Alice"

    def test_from_dict_ignores_extra(self):
        d = {"name": "x", "unknown_field": 42}
        e = PluginRegistryEntry.from_dict(d)
        assert e.name == "x"

    def test_round_trip(self):
        e = PluginRegistryEntry(name="rt", version="3.0.0", tags=["test"])
        e2 = PluginRegistryEntry.from_dict(e.to_dict())
        assert e.name == e2.name
        assert e.version == e2.version


# ===================================================================
# PluginRegistry
# ===================================================================


class TestPluginRegistry:
    def test_empty_registry(self):
        r = PluginRegistry()
        assert r.count == 0
        assert r.list_all() == []

    def test_publish_and_get(self):
        r = PluginRegistry()
        entry = PluginRegistryEntry(name="test-plugin", version="1.0.0")
        r.publish(entry)
        assert r.count == 1
        assert r.get("test-plugin") is not None

    def test_unpublish(self):
        r = PluginRegistry()
        r.publish(PluginRegistryEntry(name="x"))
        assert r.unpublish("x")
        assert r.count == 0

    def test_unpublish_missing(self):
        r = PluginRegistry()
        assert not r.unpublish("nonexistent")

    def test_search_by_name(self):
        r = PluginRegistry()
        r.publish(PluginRegistryEntry(name="dax-helper", description="DAX tools"))
        r.publish(PluginRegistryEntry(name="visual-plugin", description="Visual overrides"))
        results = r.search("dax")
        assert len(results) == 1
        assert results[0].name == "dax-helper"

    def test_search_by_description(self):
        r = PluginRegistry()
        r.publish(PluginRegistryEntry(name="plugin-a", description="Quality checks"))
        results = r.search("quality")
        assert len(results) == 1

    def test_search_by_tags(self):
        r = PluginRegistry()
        r.publish(PluginRegistryEntry(name="a", tags=["dax", "migration"]))
        r.publish(PluginRegistryEntry(name="b", tags=["visual"]))
        results = r.search(tags=["dax"])
        assert len(results) == 1
        assert results[0].name == "a"

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.json"
            r = PluginRegistry(index_path=path)
            r.publish(PluginRegistryEntry(name="p1", version="1.0.0"))
            r.publish(PluginRegistryEntry(name="p2", version="2.0.0"))

            r2 = PluginRegistry(index_path=path)
            assert r2.count == 2
            assert r2.get("p1").version == "1.0.0"


# ===================================================================
# PluginInstaller
# ===================================================================


class TestPluginInstaller:
    def _make_installer(self, tmpdir: str):
        reg = PluginRegistry()
        mgr = PluginManager()
        return PluginInstaller(plugin_dir=tmpdir, registry=reg, manager=mgr), reg, mgr

    def test_install_from_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            installer, reg, mgr = self._make_installer(tmpdir)
            entry = PluginRegistryEntry(name="test-inst", version="1.0.0")
            result = installer.install_from_entry(entry)
            assert result.success
            assert installer.installed_count == 1

    def test_install_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            installer, _, _ = self._make_installer(tmpdir)
            entry = PluginRegistryEntry(name="dir-test", version="1.0.0")
            installer.install_from_entry(entry)
            assert (Path(tmpdir) / "dir-test" / "plugin.json").exists()

    def test_install_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            installer, _, mgr = self._make_installer(tmpdir)
            manifest = PluginManifest(name="from-manifest", version="1.0.0")
            plugin = PluginBase(manifest)
            result = installer.install_from_manifest(manifest, plugin)
            assert result.success
            assert mgr.plugin_count == 1

    def test_install_bad_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            installer, _, _ = self._make_installer(tmpdir)
            bad = PluginManifest(name="", version="1.0.0")  # name required
            plugin = PluginBase(bad)
            result = installer.install_from_manifest(bad, plugin)
            assert not result.success

    def test_uninstall(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            installer, _, mgr = self._make_installer(tmpdir)
            manifest = PluginManifest(name="removeme", version="1.0.0")
            plugin = PluginBase(manifest)
            installer.install_from_manifest(manifest, plugin)
            result = installer.uninstall("removeme")
            assert result.success
            assert installer.installed_count == 0


# ===================================================================
# VisualMappingOverridePlugin
# ===================================================================


class TestVisualMappingOverridePlugin:
    def test_manifest(self):
        p = VisualMappingOverridePlugin()
        assert p.name == "visual-mapping-overrides"
        assert p.manifest.is_valid

    def test_set_and_get_override(self):
        p = VisualMappingOverridePlugin()
        p.set_override("pivot_table", "matrix")
        assert p.get_override("pivot_table") == "matrix"

    def test_case_insensitive(self):
        p = VisualMappingOverridePlugin()
        p.set_override("Bar_Chart", "stackedBarChart")
        assert p.get_override("bar_chart") == "stackedBarChart"

    def test_list_overrides(self):
        p = VisualMappingOverridePlugin()
        p.set_override("a", "A")
        p.set_override("b", "B")
        assert len(p.list_overrides()) == 2

    @pytest.mark.asyncio
    async def test_hook_applies_overrides(self):
        p = VisualMappingOverridePlugin()
        p.set_override("pivot_table", "matrix")
        ctx = {"visuals": [{"oac_type": "pivot_table", "pbi_type": "table"}]}
        result = await p.on_hook(PluginHook.POST_TRANSLATE, ctx)
        assert result["visuals"][0]["pbi_type"] == "matrix"

    @pytest.mark.asyncio
    async def test_hook_no_match(self):
        p = VisualMappingOverridePlugin()
        ctx = {"visuals": [{"oac_type": "bar", "pbi_type": "bar"}]}
        result = await p.on_hook(PluginHook.POST_TRANSLATE, ctx)
        assert result["visuals"][0]["pbi_type"] == "bar"


# ===================================================================
# DataQualityPlugin
# ===================================================================


class TestDataQualityPlugin:
    def test_manifest(self):
        p = DataQualityPlugin()
        assert p.name == "data-quality-checks"
        assert p.manifest.is_valid

    def test_null_ratio_ok(self):
        p = DataQualityPlugin(null_threshold=0.5)
        issue = p.check_null_ratio("t1", "c1", 10, 100)
        assert issue is None

    def test_null_ratio_warning(self):
        p = DataQualityPlugin(null_threshold=0.5)
        issue = p.check_null_ratio("t1", "c1", 60, 100)
        assert issue is not None
        assert issue.severity == "warning"

    def test_null_ratio_error(self):
        p = DataQualityPlugin(null_threshold=0.5)
        issue = p.check_null_ratio("t1", "c1", 90, 100)
        assert issue is not None
        assert issue.severity == "error"

    def test_null_ratio_zero_total(self):
        p = DataQualityPlugin()
        assert p.check_null_ratio("t1", "c1", 0, 0) is None

    def test_row_count_ok(self):
        p = DataQualityPlugin()
        issue = p.check_row_count_variance("t1", 1000, 1000)
        assert issue is None

    def test_row_count_warning(self):
        p = DataQualityPlugin()
        issue = p.check_row_count_variance("t1", 1000, 970)
        assert issue is not None
        assert issue.severity == "warning"

    def test_row_count_error(self):
        p = DataQualityPlugin()
        issue = p.check_row_count_variance("t1", 1000, 900)
        assert issue is not None
        assert issue.severity == "error"

    def test_run_checks(self):
        p = DataQualityPlugin(null_threshold=0.3)
        stats = [
            {
                "table": "Sales",
                "source_row_count": 1000,
                "target_row_count": 995,
                "columns": [
                    {"name": "ID", "null_count": 0, "total_count": 1000},
                    {"name": "Notes", "null_count": 500, "total_count": 1000},
                ],
            }
        ]
        report = p.run_checks(stats)
        assert report.tables_checked == 1
        assert report.columns_checked == 2
        assert report.issue_count >= 1  # Notes null ratio

    def test_run_checks_all_pass(self):
        p = DataQualityPlugin()
        stats = [{"table": "T", "source_row_count": 10, "target_row_count": 10, "columns": []}]
        report = p.run_checks(stats)
        assert report.passed

    def test_add_rule(self):
        p = DataQualityPlugin()
        p.add_rule("Sales", "Revenue", "outlier", 3.0)
        assert len(p._rules) == 1

    @pytest.mark.asyncio
    async def test_pre_validate_hook(self):
        p = DataQualityPlugin()
        ctx = {}
        result = await p.on_hook(PluginHook.PRE_VALIDATE, ctx)
        assert result["data_quality_plugin_active"]

    @pytest.mark.asyncio
    async def test_post_validate_hook(self):
        p = DataQualityPlugin(null_threshold=0.1)
        ctx = {
            "table_stats": [{
                "table": "X",
                "source_row_count": 100,
                "target_row_count": 100,
                "columns": [{"name": "A", "null_count": 50, "total_count": 100}],
            }]
        }
        result = await p.on_hook(PluginHook.POST_VALIDATE, ctx)
        assert "data_quality_report" in result
        assert result["data_quality_report"]["issue_count"] >= 1


class TestDataQualityReport:
    def test_report_empty(self):
        r = DataQualityReport()
        assert r.issue_count == 0
        assert r.error_count == 0
        assert r.passed

    def test_report_with_issues(self):
        issues = [
            DataQualityIssue(table="T", issue_type="null_ratio", severity="warning"),
            DataQualityIssue(table="T", issue_type="row_count", severity="error"),
        ]
        r = DataQualityReport(
            issues=issues,
            passed=not any(i.severity == "error" for i in issues),
        )
        assert r.issue_count == 2
        assert r.error_count == 1
        assert r.warning_count == 1
        assert not r.passed  # has error


# ===================================================================
# CLI helpers
# ===================================================================


class TestCLIHelpers:
    def test_cmd_plugin_list_empty(self):
        reg = PluginRegistry()
        mgr = PluginManager()
        output = cmd_plugin_list(reg, mgr)
        assert "No plugins found" in output

    def test_cmd_plugin_list_with_installed(self):
        reg = PluginRegistry()
        mgr = PluginManager()
        mgr.register(PluginBase(PluginManifest(name="foo", version="1.0.0", description="A foo")))
        output = cmd_plugin_list(reg, mgr)
        assert "foo" in output
        assert "Installed Plugins" in output

    def test_cmd_plugin_list_with_registry(self):
        reg = PluginRegistry()
        reg.publish(PluginRegistryEntry(name="bar", version="2.0.0", description="B"))
        mgr = PluginManager()
        output = cmd_plugin_list(reg, mgr)
        assert "bar" in output
        assert "Available Plugins" in output

    def test_cmd_plugin_install_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = PluginRegistry()
            mgr = PluginManager()
            installer = PluginInstaller(tmpdir, reg, mgr)
            reg.publish(PluginRegistryEntry(name="to-install", version="1.0.0"))
            result = cmd_plugin_install("to-install", reg, installer)
            assert result.success

    def test_cmd_plugin_install_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = PluginRegistry()
            mgr = PluginManager()
            installer = PluginInstaller(tmpdir, reg, mgr)
            result = cmd_plugin_install("missing", reg, installer)
            assert not result.success

    def test_cmd_plugin_publish(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "plugin.json"
            manifest_path.write_text(json.dumps({
                "name": "published-plugin",
                "version": "1.0.0",
                "description": "Test publish",
            }))
            reg = PluginRegistry()
            entry = cmd_plugin_publish(manifest_path, reg)
            assert entry is not None
            assert entry.name == "published-plugin"
            assert reg.count == 1

    def test_cmd_plugin_publish_missing_file(self):
        reg = PluginRegistry()
        entry = cmd_plugin_publish("/nonexistent/path/plugin.json", reg)
        assert entry is None


# ===================================================================
# Load built-in plugins
# ===================================================================


class TestLoadBuiltinPlugins:
    def test_loads_two_plugins(self):
        mgr = PluginManager()
        loaded = load_builtin_plugins(mgr)
        assert len(loaded) == 2
        assert "visual-mapping-overrides" in loaded
        assert "data-quality-checks" in loaded
        assert mgr.plugin_count == 2

    def test_idempotent_names(self):
        mgr = PluginManager()
        load_builtin_plugins(mgr)
        names = [p.name for p in mgr.list_plugins()]
        assert "visual-mapping-overrides" in names
        assert "data-quality-checks" in names
