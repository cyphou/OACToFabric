"""Configuration loader — read TOML config with environment overlay.

Supports a base ``migration.toml`` merged with an optional per-environment
overlay (``dev.toml``, ``test.toml``, ``prod.toml``).  Environment
variables prefixed ``OAC_`` / ``FABRIC_`` / ``AZURE_`` override any file
setting via the Pydantic ``Settings`` class in ``src.core.config``.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_DIR = Path("config")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ScopeConfig:
    """Migration scope parsed from TOML."""

    include_paths: list[str] = field(default_factory=list)
    exclude_paths: list[str] = field(default_factory=list)
    asset_types: list[str] = field(default_factory=list)
    wave: int | None = None


@dataclass
class OrchestratorSettings:
    """Orchestrator tunables parsed from TOML."""

    max_retries: int = 3
    retry_backoff_seconds: list[int] = field(default_factory=lambda: [60, 300, 900])
    parallel_agents_per_wave: int = 3
    max_items_per_wave: int = 50
    validate_after_each_wave: bool = True
    auto_advance_waves: bool = False
    notification_channels: list[str] = field(default_factory=lambda: ["log"])


@dataclass
class LLMSettings:
    """LLM settings parsed from TOML."""

    enabled: bool = False
    model: str = "gpt-4"
    max_tokens: int = 2048
    temperature: float = 0.1
    max_retries: int = 3
    token_budget_per_run: int = 500_000
    cache_enabled: bool = True


@dataclass
class MigrationConfig:
    """Complete migration configuration."""

    environment: str = "dev"
    output_dir: str = "output"
    log_level: str = "INFO"
    scope: ScopeConfig = field(default_factory=ScopeConfig)
    orchestrator: OrchestratorSettings = field(default_factory=OrchestratorSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *overlay* into *base* (overlay wins on conflict)."""
    merged = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file and return the parsed dict."""
    with path.open("rb") as f:
        return tomllib.load(f)


def load_config(
    config_path: Path | str | None = None,
    environment: str | None = None,
    *,
    config_dir: Path | str | None = None,
) -> MigrationConfig:
    """Load migration configuration.

    Resolution order
    ----------------
    1. Base file (``config/migration.toml`` or *config_path*).
    2. Environment overlay (``config/<env>.toml``) — merged on top.
    3. Environment variables override individual values (via Pydantic
       ``Settings`` in config.py — handled separately at caller's level).

    Parameters
    ----------
    config_path
        Explicit path to the base TOML config.  If *None*, falls back
        to ``<config_dir>/migration.toml``.
    environment
        Environment name (``dev``, ``test``, ``prod``).  If *None*,
        read from ``[migration].environment`` in the base config.
    config_dir
        Directory containing config files.  Defaults to ``config/``.
    """
    cdir = Path(config_dir) if config_dir else _DEFAULT_CONFIG_DIR

    # --- 1. Base file ---
    base_path = Path(config_path) if config_path else cdir / "migration.toml"
    if base_path.exists():
        raw = load_toml(base_path)
        logger.info("Loaded base config from %s", base_path)
    else:
        raw = {}
        logger.warning("Base config not found at %s — using defaults", base_path)

    # --- 2. Environment overlay ---
    env = environment or raw.get("migration", {}).get("environment", "dev")
    overlay_path = cdir / f"{env}.toml"
    if overlay_path.exists():
        overlay = load_toml(overlay_path)
        raw = _deep_merge(raw, overlay)
        logger.info("Applied environment overlay from %s", overlay_path)

    return _parse_config(raw, env)


def _parse_config(raw: dict[str, Any], environment: str) -> MigrationConfig:
    """Convert raw TOML dict into a typed ``MigrationConfig``."""
    mig = raw.get("migration", {})
    scope_raw = raw.get("scope", {})
    orch_raw = raw.get("orchestrator", {})
    llm_raw = raw.get("llm", {})

    scope = ScopeConfig(
        include_paths=scope_raw.get("include_paths", []),
        exclude_paths=scope_raw.get("exclude_paths", []),
        asset_types=scope_raw.get("asset_types", []),
        wave=scope_raw.get("wave"),
    )

    orch = OrchestratorSettings(
        max_retries=orch_raw.get("max_retries", 3),
        retry_backoff_seconds=orch_raw.get("retry_backoff_seconds", [60, 300, 900]),
        parallel_agents_per_wave=orch_raw.get("parallel_agents_per_wave", 3),
        max_items_per_wave=orch_raw.get("max_items_per_wave", 50),
        validate_after_each_wave=orch_raw.get("validate_after_each_wave", True),
        auto_advance_waves=orch_raw.get("auto_advance_waves", False),
        notification_channels=orch_raw.get("notification_channels", ["log"]),
    )

    llm = LLMSettings(
        enabled=llm_raw.get("enabled", False),
        model=llm_raw.get("model", "gpt-4"),
        max_tokens=llm_raw.get("max_tokens", 2048),
        temperature=llm_raw.get("temperature", 0.1),
        max_retries=llm_raw.get("max_retries", 3),
        token_budget_per_run=llm_raw.get("token_budget_per_run", 500_000),
        cache_enabled=llm_raw.get("cache_enabled", True),
    )

    return MigrationConfig(
        environment=environment,
        output_dir=mig.get("output_dir", "output"),
        log_level=mig.get("log_level", "INFO"),
        scope=scope,
        orchestrator=orch,
        llm=llm,
        extra={k: v for k, v in raw.items() if k not in ("migration", "scope", "orchestrator", "llm")},
    )
