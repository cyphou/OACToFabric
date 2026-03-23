"""Plugin & extensibility architecture.

Provides:
- ``PluginManifest`` — plugin metadata from ``plugin.toml``.
- ``PluginHook`` — lifecycle hook points.
- ``PluginManager`` — discover, load, validate, and execute plugins.
- ``TranslationPlugin`` — interface for custom OAC→DAX rules.
- ``TranslationRuleSet`` — YAML-based custom translation rules.
- ``AgentPlugin`` — interface for registering custom agents.
- ``ConnectorPlugin`` — interface for custom source connectors.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plugin hooks
# ---------------------------------------------------------------------------


class PluginHook(str, Enum):
    """Lifecycle hook points where plugins can inject behavior."""

    PRE_DISCOVER = "pre_discover"
    POST_DISCOVER = "post_discover"
    PRE_TRANSLATE = "pre_translate"
    POST_TRANSLATE = "post_translate"
    PRE_DEPLOY = "pre_deploy"
    POST_DEPLOY = "post_deploy"
    PRE_VALIDATE = "pre_validate"
    POST_VALIDATE = "post_validate"


# ---------------------------------------------------------------------------
# Plugin manifest
# ---------------------------------------------------------------------------


@dataclass
class PluginManifest:
    """Plugin metadata — typically loaded from ``plugin.toml``."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    hooks: list[PluginHook] = field(default_factory=list)
    entry_point: str = ""
    dependencies: dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def validate(self) -> list[str]:
        """Return validation errors (empty if valid)."""
        errors = []
        if not self.name:
            errors.append("Plugin name is required")
        if not self.version:
            errors.append("Plugin version is required")
        if not re.match(r"^\d+\.\d+\.\d+", self.version):
            errors.append(f"Invalid version format: {self.version}")
        return errors

    @property
    def is_valid(self) -> bool:
        return len(self.validate()) == 0


# ---------------------------------------------------------------------------
# Plugin base class
# ---------------------------------------------------------------------------


class PluginBase:
    """Base class for all plugins."""

    def __init__(self, manifest: PluginManifest) -> None:
        self.manifest = manifest

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    async def on_hook(self, hook: PluginHook, context: dict[str, Any]) -> dict[str, Any]:
        """Called when a lifecycle hook fires.

        Override in subclass to inject behavior.
        Returns the (possibly modified) context dict.
        """
        return context


# ---------------------------------------------------------------------------
# Translation plugin — custom OAC→DAX rules
# ---------------------------------------------------------------------------


@dataclass
class TranslationRule:
    """A single custom translation rule."""

    name: str
    oac_pattern: str  # regex pattern matching OAC expression
    dax_template: str  # DAX replacement template
    priority: int = 100  # lower = higher priority (overrides built-in)
    description: str = ""

    @property
    def compiled_pattern(self) -> re.Pattern:
        return re.compile(self.oac_pattern, re.IGNORECASE)

    def apply(self, expression: str) -> str | None:
        """Apply this rule to an expression. Returns result or None if no match."""
        m = self.compiled_pattern.search(expression)
        if m:
            try:
                return self.compiled_pattern.sub(self.dax_template, expression)
            except re.error:
                return None
        return None


@dataclass
class TranslationRuleSet:
    """A set of custom translation rules (loaded from YAML)."""

    rules: list[TranslationRule] = field(default_factory=list)
    source: str = ""  # file path or plugin name

    def add_rule(self, rule: TranslationRule) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def apply_first_match(self, expression: str) -> tuple[str | None, str]:
        """Apply the first matching rule. Returns (result, rule_name) or (None, "")."""
        for rule in self.rules:
            result = rule.apply(expression)
            if result is not None:
                return result, rule.name
        return None, ""

    @staticmethod
    def from_dicts(rule_dicts: list[dict[str, Any]], source: str = "") -> "TranslationRuleSet":
        """Create a rule set from a list of dicts (parsed from YAML)."""
        rules = []
        for d in rule_dicts:
            rules.append(TranslationRule(
                name=d.get("name", "unnamed"),
                oac_pattern=d["oac_pattern"],
                dax_template=d["dax_template"],
                priority=d.get("priority", 100),
                description=d.get("description", ""),
            ))
        ts = TranslationRuleSet(rules=rules, source=source)
        ts.rules.sort(key=lambda r: r.priority)
        return ts


# ---------------------------------------------------------------------------
# Agent plugin
# ---------------------------------------------------------------------------


class AgentPlugin(PluginBase):
    """Plugin that registers a custom agent in the DAG."""

    async def create_agent(self, config: dict[str, Any]) -> Any:
        """Create and return the custom agent instance.

        Override in subclass.
        """
        raise NotImplementedError("Subclass must implement create_agent()")

    def agent_id(self) -> str:
        """Return the agent ID for DAG registration."""
        return f"plugin-{self.name}"

    def depends_on(self) -> list[str]:
        """Return list of agent IDs this agent depends on."""
        return []


# ---------------------------------------------------------------------------
# Connector plugin
# ---------------------------------------------------------------------------


class ConnectorPlugin(PluginBase):
    """Plugin that registers a custom source connector."""

    def platform_name(self) -> str:
        """Return the platform identifier (e.g. 'sap_bw')."""
        return self.name

    async def create_connector(self, config: dict[str, Any]) -> Any:
        """Create and return the custom connector instance.

        Override in subclass.
        """
        raise NotImplementedError("Subclass must implement create_connector()")


# ---------------------------------------------------------------------------
# Plugin manager
# ---------------------------------------------------------------------------


class PluginManager:
    """Discover, load, validate, and manage plugins.

    Plugins are discovered from a ``plugins/`` directory. Each plugin
    is a Python module with a ``PluginManifest`` and one or more
    plugin classes (TranslationPlugin, AgentPlugin, ConnectorPlugin).
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginBase] = {}
        self._hooks: dict[PluginHook, list[PluginBase]] = {h: [] for h in PluginHook}
        self._translation_rules: TranslationRuleSet = TranslationRuleSet()
        self._custom_agents: list[AgentPlugin] = []
        self._custom_connectors: list[ConnectorPlugin] = []

    def register(self, plugin: PluginBase) -> list[str]:
        """Register a plugin. Returns validation errors (empty if success)."""
        errors = plugin.manifest.validate()
        if errors:
            logger.warning("Plugin '%s' validation failed: %s", plugin.name, errors)
            return errors

        self._plugins[plugin.name] = plugin

        for hook in plugin.manifest.hooks:
            self._hooks[hook].append(plugin)

        if isinstance(plugin, AgentPlugin):
            self._custom_agents.append(plugin)
        elif isinstance(plugin, ConnectorPlugin):
            self._custom_connectors.append(plugin)

        logger.info("Plugin registered: %s v%s", plugin.name, plugin.version)
        return []

    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name."""
        plugin = self._plugins.pop(name, None)
        if not plugin:
            return False

        for hook_list in self._hooks.values():
            if plugin in hook_list:
                hook_list.remove(plugin)

        if plugin in self._custom_agents:
            self._custom_agents.remove(plugin)
        if plugin in self._custom_connectors:
            self._custom_connectors.remove(plugin)

        return True

    def get(self, name: str) -> PluginBase | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginManifest]:
        return [p.manifest for p in self._plugins.values()]

    async def execute_hook(
        self,
        hook: PluginHook,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute all registered plugins for a lifecycle hook."""
        for plugin in self._hooks.get(hook, []):
            if plugin.manifest.enabled:
                try:
                    context = await plugin.on_hook(hook, context)
                except Exception as exc:
                    logger.error("Plugin '%s' hook '%s' failed: %s", plugin.name, hook.value, exc)
        return context

    def add_translation_rules(self, rules: TranslationRuleSet) -> None:
        """Add custom translation rules from a plugin or YAML file."""
        for rule in rules.rules:
            self._translation_rules.add_rule(rule)
        logger.info("Added %d custom translation rules from %s", len(rules.rules), rules.source)

    def translate(self, expression: str) -> tuple[str | None, str]:
        """Apply custom translation rules (before built-in rules).

        Returns (translated_expression, rule_name) or (None, "") if no match.
        """
        return self._translation_rules.apply_first_match(expression)

    @property
    def custom_agents(self) -> list[AgentPlugin]:
        return list(self._custom_agents)

    @property
    def custom_connectors(self) -> list[ConnectorPlugin]:
        return list(self._custom_connectors)

    @property
    def translation_rule_count(self) -> int:
        return len(self._translation_rules.rules)

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)
