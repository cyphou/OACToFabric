"""Tests for CLI entry point."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.cli.main import build_parser, main, _build_scope, _setup_logging
from src.cli.config_loader import MigrationConfig, ScopeConfig


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_parser_commands(self):
        parser = build_parser()
        for cmd in ("discover", "plan", "migrate", "validate", "status"):
            args = parser.parse_args([cmd])
            assert args.command == cmd

    def test_global_flags(self):
        parser = build_parser()
        args = parser.parse_args(["--verbose", "--config", "c.toml", "migrate"])
        assert args.verbose is True
        assert args.config == "c.toml"

    def test_migrate_dry_run(self):
        parser = build_parser()
        args = parser.parse_args(["migrate", "--dry-run"])
        assert args.dry_run is True

    def test_discover_wave(self):
        parser = build_parser()
        args = parser.parse_args(["discover", "--wave", "3"])
        assert args.wave == 3

    def test_no_command_shows_help(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None


# ---------------------------------------------------------------------------
# Build scope
# ---------------------------------------------------------------------------


class TestBuildScope:
    def test_builds_scope_from_config(self):
        cfg = MigrationConfig(
            scope=ScopeConfig(
                include_paths=["/foo"],
                exclude_paths=["/bar"],
                asset_types=["analysis", "dashboard"],
                wave=1,
            )
        )
        scope = _build_scope(cfg)
        assert scope.include_paths == ["/foo"]
        assert scope.exclude_paths == ["/bar"]
        assert len(scope.asset_types) == 2
        assert scope.wave == 1

    def test_wave_override(self):
        cfg = MigrationConfig(scope=ScopeConfig(wave=1))
        scope = _build_scope(cfg, wave=5)
        assert scope.wave == 5

    def test_unknown_type_skipped(self):
        cfg = MigrationConfig(
            scope=ScopeConfig(asset_types=["analysis", "not_a_type"])
        )
        scope = _build_scope(cfg)
        assert len(scope.asset_types) == 1


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


class TestMain:
    def test_no_command_returns_zero(self):
        rc = main([])
        assert rc == 0

    def test_status_no_summary(self, tmp_path: Path):
        rc = main(["--output-dir", str(tmp_path), "status"])
        assert rc == 0

    def test_status_with_summary(self, tmp_path: Path):
        (tmp_path / "orchestrator").mkdir()
        (tmp_path / "orchestrator" / "migration_summary.md").write_text("# Summary")
        rc = main(["--output-dir", str(tmp_path), "status"])
        assert rc == 0

    def test_migrate_dry_run(self, tmp_path: Path):
        config_path = tmp_path / "m.toml"
        config_path.write_text(textwrap.dedent("""\
            [migration]
            environment = "dev"
        """))
        rc = main([
            "--config", str(config_path),
            "--output-dir", str(tmp_path),
            "migrate", "--dry-run",
        ])
        assert rc == 0


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def test_setup_logging_default(self):
        _setup_logging("INFO")

    def test_setup_logging_debug(self):
        _setup_logging("DEBUG")
