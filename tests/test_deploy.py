"""Tests for deployment script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.deploy import (
    _discover_artifacts,
    _generate_deployment_manifest,
    main,
)


class TestDiscoverArtifacts:
    def test_empty_dir(self, tmp_path: Path):
        artifacts = _discover_artifacts(tmp_path)
        assert all(len(v) == 0 for v in artifacts.values())

    def test_finds_sql_files(self, tmp_path: Path):
        (tmp_path / "schema").mkdir()
        (tmp_path / "schema" / "create_sales.sql").write_text("CREATE TABLE sales (id INT)")
        artifacts = _discover_artifacts(tmp_path)
        assert len(artifacts["ddl"]) == 1

    def test_finds_pipeline_json(self, tmp_path: Path):
        (tmp_path / "pipelines").mkdir()
        (tmp_path / "pipelines" / "load.pipeline.json").write_text("{}")
        artifacts = _discover_artifacts(tmp_path)
        assert len(artifacts["pipelines"]) == 1

    def test_finds_tmdl_files(self, tmp_path: Path):
        (tmp_path / "model").mkdir()
        (tmp_path / "model" / "sales.tmdl").write_text("table Sales")
        artifacts = _discover_artifacts(tmp_path)
        assert len(artifacts["tmdl"]) == 1

    def test_nonexistent_dir(self, tmp_path: Path):
        artifacts = _discover_artifacts(tmp_path / "nope")
        assert all(len(v) == 0 for v in artifacts.values())


class TestGenerateManifest:
    def test_manifest_structure(self):
        artifacts = {
            "ddl": [Path("a.sql"), Path("b.sql")],
            "pipelines": [Path("p.pipeline.json")],
            "notebooks": [],
            "tmdl": [],
            "reports": [],
        }
        manifest = _generate_deployment_manifest(artifacts, "dev", "ws-123")
        assert manifest["environment"] == "dev"
        assert manifest["total_artifacts"] == 3
        assert manifest["breakdown"]["ddl"] == 2


class TestMain:
    def test_dry_run_no_artifacts(self, tmp_path: Path):
        rc = main(["--env", "dev", "--artifacts", str(tmp_path), "--dry-run"])
        assert rc == 0

    def test_dry_run_with_artifacts(self, tmp_path: Path):
        (tmp_path / "test.sql").write_text("SELECT 1")
        rc = main([
            "--env", "dev",
            "--artifacts", str(tmp_path),
            "--workspace-id", "ws-test",
            "--dry-run",
        ])
        assert rc == 0
