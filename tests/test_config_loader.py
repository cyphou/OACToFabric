"""Tests for CLI config_loader module."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.cli.config_loader import (
    LLMSettings,
    MigrationConfig,
    OrchestratorSettings,
    ScopeConfig,
    _deep_merge,
    _parse_config,
    load_config,
    load_toml,
)


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_empty_overlay(self):
        base = {"a": 1, "b": {"c": 2}}
        assert _deep_merge(base, {}) == base

    def test_non_overlapping_keys(self):
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_overlapping_scalar(self):
        assert _deep_merge({"a": 1}, {"a": 99})["a"] == 99

    def test_nested_dict_merge(self):
        base = {"x": {"a": 1, "b": 2}}
        overlay = {"x": {"b": 99, "c": 3}}
        result = _deep_merge(base, overlay)
        assert result["x"] == {"a": 1, "b": 99, "c": 3}

    def test_overlay_replaces_non_dict_with_dict(self):
        result = _deep_merge({"x": 1}, {"x": {"a": 2}})
        assert result["x"] == {"a": 2}


# ---------------------------------------------------------------------------
# load_toml
# ---------------------------------------------------------------------------


class TestLoadToml:
    def test_loads_valid_toml(self, tmp_path: Path):
        f = tmp_path / "test.toml"
        f.write_text('[section]\nkey = "value"\n')
        result = load_toml(f)
        assert result == {"section": {"key": "value"}}

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_toml(tmp_path / "nope.toml")


# ---------------------------------------------------------------------------
# _parse_config
# ---------------------------------------------------------------------------


class TestParseConfig:
    def test_defaults_when_empty(self):
        cfg = _parse_config({}, "dev")
        assert cfg.environment == "dev"
        assert cfg.output_dir == "output"
        assert isinstance(cfg.scope, ScopeConfig)
        assert isinstance(cfg.orchestrator, OrchestratorSettings)
        assert isinstance(cfg.llm, LLMSettings)

    def test_reads_all_sections(self):
        raw = {
            "migration": {"output_dir": "/tmp/out", "log_level": "DEBUG"},
            "scope": {"include_paths": ["/a"], "wave": 2},
            "orchestrator": {"max_retries": 9},
            "llm": {"enabled": True, "model": "gpt-4o"},
        }
        cfg = _parse_config(raw, "test")
        assert cfg.output_dir == "/tmp/out"
        assert cfg.log_level == "DEBUG"
        assert cfg.scope.include_paths == ["/a"]
        assert cfg.scope.wave == 2
        assert cfg.orchestrator.max_retries == 9
        assert cfg.llm.enabled is True
        assert cfg.llm.model == "gpt-4o"

    def test_extra_keys_preserved(self):
        raw = {"custom_section": {"foo": "bar"}}
        cfg = _parse_config(raw, "dev")
        assert cfg.extra["custom_section"] == {"foo": "bar"}


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_loads_base_config(self, tmp_path: Path):
        base = tmp_path / "migration.toml"
        base.write_text(textwrap.dedent("""\
            [migration]
            output_dir = "out"
            log_level = "INFO"

            [orchestrator]
            max_retries = 5
        """))
        cfg = load_config(config_path=base, config_dir=tmp_path)
        assert cfg.output_dir == "out"
        assert cfg.orchestrator.max_retries == 5

    def test_merges_environment_overlay(self, tmp_path: Path):
        (tmp_path / "migration.toml").write_text(textwrap.dedent("""\
            [migration]
            environment = "dev"
            output_dir = "base_out"

            [orchestrator]
            max_retries = 3
            parallel_agents_per_wave = 3
        """))
        (tmp_path / "dev.toml").write_text(textwrap.dedent("""\
            [orchestrator]
            max_retries = 1
        """))
        cfg = load_config(config_dir=tmp_path)
        assert cfg.orchestrator.max_retries == 1  # overridden
        assert cfg.orchestrator.parallel_agents_per_wave == 3  # kept from base
        assert cfg.output_dir == "base_out"

    def test_explicit_environment_overrides_file(self, tmp_path: Path):
        (tmp_path / "migration.toml").write_text('[migration]\nenvironment = "dev"\n')
        (tmp_path / "prod.toml").write_text("[migration]\noutput_dir = 'prod_out'\n")
        cfg = load_config(config_dir=tmp_path, environment="prod")
        assert cfg.output_dir == "prod_out"
        assert cfg.environment == "prod"

    def test_missing_base_uses_defaults(self, tmp_path: Path):
        cfg = load_config(config_dir=tmp_path)
        assert cfg.environment == "dev"
        assert cfg.output_dir == "output"

    def test_missing_overlay_ignored(self, tmp_path: Path):
        (tmp_path / "migration.toml").write_text('[migration]\nenvironment = "staging"\n')
        cfg = load_config(config_dir=tmp_path)
        assert cfg.environment == "staging"


# ---------------------------------------------------------------------------
# MigrationConfig properties
# ---------------------------------------------------------------------------


class TestMigrationConfig:
    def test_is_production(self):
        cfg = MigrationConfig(environment="prod")
        assert cfg.is_production is True

    def test_is_not_production(self):
        cfg = MigrationConfig(environment="dev")
        assert cfg.is_production is False
