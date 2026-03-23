"""Phase 28 — Plugin & Extensibility Architecture.

Tests cover:
- PluginHook enum values
- PluginManifest validation (name, version format)
- PluginBase on_hook passthrough
- TranslationRule pattern matching and apply
- TranslationRuleSet priority ordering and from_dicts
- AgentPlugin interface
- ConnectorPlugin interface
- PluginManager register/unregister/list/get
- PluginManager hook execution
- PluginManager translation rule integration
- Custom agent and connector plugin tracking
"""

from __future__ import annotations

import pytest

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


# ===================================================================
# PluginHook
# ===================================================================


class TestPluginHook:
    """Tests for plugin hook enum."""

    def test_hook_values(self):
        assert PluginHook.PRE_DISCOVER.value == "pre_discover"
        assert PluginHook.POST_DEPLOY.value == "post_deploy"
        assert PluginHook.PRE_VALIDATE.value == "pre_validate"

    def test_all_hooks(self):
        assert len(PluginHook) == 8


# ===================================================================
# PluginManifest
# ===================================================================


class TestPluginManifest:
    """Tests for plugin manifest."""

    def test_valid_manifest(self):
        m = PluginManifest(name="my-plugin", version="1.0.0", description="Test")
        assert m.is_valid is True
        assert m.validate() == []

    def test_missing_name(self):
        m = PluginManifest(name="", version="1.0.0")
        assert m.is_valid is False
        assert any("name" in e.lower() for e in m.validate())

    def test_missing_version(self):
        m = PluginManifest(name="test", version="")
        assert m.is_valid is False

    def test_invalid_version_format(self):
        m = PluginManifest(name="test", version="abc")
        assert m.is_valid is False
        assert any("version" in e.lower() for e in m.validate())

    def test_valid_version_with_suffix(self):
        m = PluginManifest(name="test", version="1.2.3-beta")
        assert m.is_valid is True

    def test_manifest_with_hooks(self):
        m = PluginManifest(
            name="test",
            version="1.0.0",
            hooks=[PluginHook.PRE_DISCOVER, PluginHook.POST_DISCOVER],
        )
        assert len(m.hooks) == 2

    def test_manifest_defaults(self):
        m = PluginManifest(name="test")
        assert m.enabled is True
        assert m.hooks == []
        assert m.dependencies == {}


# ===================================================================
# PluginBase
# ===================================================================


class TestPluginBase:
    """Tests for plugin base class."""

    def test_name_and_version(self):
        manifest = PluginManifest(name="demo", version="2.0.0")
        plugin = PluginBase(manifest)
        assert plugin.name == "demo"
        assert plugin.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_on_hook_passthrough(self):
        manifest = PluginManifest(name="demo", version="1.0.0")
        plugin = PluginBase(manifest)
        ctx = {"key": "value"}
        result = await plugin.on_hook(PluginHook.PRE_DISCOVER, ctx)
        assert result == ctx


# ===================================================================
# TranslationRule
# ===================================================================


class TestTranslationRule:
    """Tests for translation rule."""

    def test_matching_rule(self):
        rule = TranslationRule(
            name="count_star",
            oac_pattern=r"COUNT\(\*\)",
            dax_template="COUNTROWS()",
        )
        result = rule.apply("SELECT COUNT(*) FROM sales")
        assert result is not None
        assert "COUNTROWS()" in result

    def test_no_match(self):
        rule = TranslationRule(
            name="count_star",
            oac_pattern=r"COUNT\(\*\)",
            dax_template="COUNTROWS()",
        )
        result = rule.apply("SUM(amount)")
        assert result is None

    def test_case_insensitive(self):
        rule = TranslationRule(
            name="lower_test",
            oac_pattern=r"count\(\*\)",
            dax_template="COUNTROWS()",
        )
        result = rule.apply("COUNT(*)")
        assert result is not None

    def test_priority(self):
        r1 = TranslationRule(name="a", oac_pattern="x", dax_template="y", priority=10)
        r2 = TranslationRule(name="b", oac_pattern="x", dax_template="z", priority=50)
        assert r1.priority < r2.priority


# ===================================================================
# TranslationRuleSet
# ===================================================================


class TestTranslationRuleSet:
    """Tests for translation rule set."""

    def test_add_rule_sorted(self):
        rs = TranslationRuleSet()
        rs.add_rule(TranslationRule("b", r"b", "B", priority=50))
        rs.add_rule(TranslationRule("a", r"a", "A", priority=10))
        assert rs.rules[0].name == "a"
        assert rs.rules[1].name == "b"

    def test_apply_first_match(self):
        rs = TranslationRuleSet()
        rs.add_rule(TranslationRule("hi_priority", r"SUM", "DAX_SUM", priority=10))
        rs.add_rule(TranslationRule("lo_priority", r"SUM", "OTHER_SUM", priority=50))
        result, name = rs.apply_first_match("SUM(amount)")
        assert name == "hi_priority"
        assert "DAX_SUM" in result

    def test_no_match_returns_none(self):
        rs = TranslationRuleSet()
        rs.add_rule(TranslationRule("x", r"NOPE", "Y"))
        result, name = rs.apply_first_match("SUM(amount)")
        assert result is None
        assert name == ""

    def test_from_dicts(self):
        dicts = [
            {"name": "rule1", "oac_pattern": r"SUM", "dax_template": "SUM_DAX", "priority": 20},
            {"name": "rule2", "oac_pattern": r"AVG", "dax_template": "AVERAGE", "priority": 10},
        ]
        rs = TranslationRuleSet.from_dicts(dicts, source="test.yaml")
        assert len(rs.rules) == 2
        assert rs.rules[0].name == "rule2"  # lower priority number = higher priority
        assert rs.source == "test.yaml"

    def test_from_dicts_defaults(self):
        dicts = [{"oac_pattern": r"X", "dax_template": "Y"}]
        rs = TranslationRuleSet.from_dicts(dicts)
        assert rs.rules[0].name == "unnamed"
        assert rs.rules[0].priority == 100


# ===================================================================
# AgentPlugin
# ===================================================================


class TestAgentPlugin:
    """Tests for agent plugin interface."""

    def test_agent_id(self):
        manifest = PluginManifest(name="custom-agent", version="1.0.0")
        plugin = AgentPlugin(manifest)
        assert plugin.agent_id() == "plugin-custom-agent"

    def test_depends_on_default(self):
        manifest = PluginManifest(name="custom-agent", version="1.0.0")
        plugin = AgentPlugin(manifest)
        assert plugin.depends_on() == []

    @pytest.mark.asyncio
    async def test_create_agent_raises(self):
        manifest = PluginManifest(name="custom-agent", version="1.0.0")
        plugin = AgentPlugin(manifest)
        with pytest.raises(NotImplementedError):
            await plugin.create_agent({})


# ===================================================================
# ConnectorPlugin
# ===================================================================


class TestConnectorPlugin:
    """Tests for connector plugin interface."""

    def test_platform_name(self):
        manifest = PluginManifest(name="sap-bw", version="1.0.0")
        plugin = ConnectorPlugin(manifest)
        assert plugin.platform_name() == "sap-bw"

    @pytest.mark.asyncio
    async def test_create_connector_raises(self):
        manifest = PluginManifest(name="sap-bw", version="1.0.0")
        plugin = ConnectorPlugin(manifest)
        with pytest.raises(NotImplementedError):
            await plugin.create_connector({})


# ===================================================================
# PluginManager
# ===================================================================


class TestPluginManager:
    """Tests for plugin manager."""

    def _make_plugin(self, name: str = "test", hooks: list | None = None) -> PluginBase:
        manifest = PluginManifest(
            name=name,
            version="1.0.0",
            hooks=hooks or [],
        )
        return PluginBase(manifest)

    def test_register_valid(self):
        mgr = PluginManager()
        plugin = self._make_plugin("my-plugin")
        errors = mgr.register(plugin)
        assert errors == []
        assert mgr.plugin_count == 1

    def test_register_invalid(self):
        mgr = PluginManager()
        manifest = PluginManifest(name="", version="bad")
        plugin = PluginBase(manifest)
        errors = mgr.register(plugin)
        assert len(errors) > 0
        assert mgr.plugin_count == 0

    def test_get_plugin(self):
        mgr = PluginManager()
        p = self._make_plugin("demo")
        mgr.register(p)
        assert mgr.get("demo") is p
        assert mgr.get("nonexistent") is None

    def test_unregister(self):
        mgr = PluginManager()
        mgr.register(self._make_plugin("demo"))
        assert mgr.unregister("demo") is True
        assert mgr.plugin_count == 0
        assert mgr.unregister("demo") is False

    def test_list_plugins(self):
        mgr = PluginManager()
        mgr.register(self._make_plugin("a"))
        mgr.register(self._make_plugin("b"))
        manifests = mgr.list_plugins()
        assert len(manifests) == 2

    @pytest.mark.asyncio
    async def test_execute_hook(self):
        mgr = PluginManager()

        class ModifyPlugin(PluginBase):
            async def on_hook(self, hook, context):
                context["modified"] = True
                return context

        manifest = PluginManifest(
            name="modifier",
            version="1.0.0",
            hooks=[PluginHook.PRE_DISCOVER],
        )
        mgr.register(ModifyPlugin(manifest))
        ctx = await mgr.execute_hook(PluginHook.PRE_DISCOVER, {"modified": False})
        assert ctx["modified"] is True

    @pytest.mark.asyncio
    async def test_execute_hook_disabled_plugin(self):
        mgr = PluginManager()

        class ModifyPlugin(PluginBase):
            async def on_hook(self, hook, context):
                context["modified"] = True
                return context

        manifest = PluginManifest(
            name="disabled",
            version="1.0.0",
            hooks=[PluginHook.PRE_DISCOVER],
            enabled=False,
        )
        mgr.register(ModifyPlugin(manifest))
        ctx = await mgr.execute_hook(PluginHook.PRE_DISCOVER, {"modified": False})
        assert ctx["modified"] is False

    def test_translation_rules(self):
        mgr = PluginManager()
        rules = TranslationRuleSet(rules=[
            TranslationRule("sum_rule", r"SUM", "DAX_SUM"),
        ], source="test")
        mgr.add_translation_rules(rules)
        assert mgr.translation_rule_count == 1
        result, name = mgr.translate("SUM(amount)")
        assert "DAX_SUM" in result

    def test_translate_no_match(self):
        mgr = PluginManager()
        result, name = mgr.translate("AVG(x)")
        assert result is None
        assert name == ""

    def test_custom_agents_tracked(self):
        mgr = PluginManager()
        manifest = PluginManifest(name="agent-x", version="1.0.0")
        mgr.register(AgentPlugin(manifest))
        assert len(mgr.custom_agents) == 1

    def test_custom_connectors_tracked(self):
        mgr = PluginManager()
        manifest = PluginManifest(name="conn-x", version="1.0.0")
        mgr.register(ConnectorPlugin(manifest))
        assert len(mgr.custom_connectors) == 1
