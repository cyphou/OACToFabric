"""Phase 24 — Containerization & Cloud Deployment.

Tests cover:
- ContainerConfig defaults and validation
- Dockerfile generation (multi-stage, non-root user, healthcheck)
- ComposeService and ComposeConfig defaults
- Docker Compose YAML generation
- AzureDeployConfig validation (replicas, names, resource group)
- Bicep template generation
- HelmValues and to_values_dict
- SmokeTestResult and SmokeTestRunner
"""

from __future__ import annotations

import pytest

from src.deployers.container_deploy import (
    AzureDeployConfig,
    ComposeConfig,
    ComposeService,
    ContainerConfig,
    HelmValues,
    SmokeTestResult,
    SmokeTestRunner,
    generate_bicep,
    generate_compose,
    generate_dockerfile,
)


# ===================================================================
# ContainerConfig
# ===================================================================


class TestContainerConfig:
    """Tests for container configuration."""

    def test_defaults(self):
        cfg = ContainerConfig()
        assert cfg.base_image == "python:3.11-slim"
        assert cfg.app_port == 8000
        assert cfg.workdir == "/app"
        assert cfg.user == "appuser"

    def test_custom_values(self):
        cfg = ContainerConfig(base_image="python:3.12", app_port=9000, user="myuser")
        assert cfg.base_image == "python:3.12"
        assert cfg.app_port == 9000

    def test_validate_passes(self):
        cfg = ContainerConfig()
        errors = cfg.validate()
        assert errors == []

    def test_validate_invalid_port(self):
        cfg = ContainerConfig(app_port=0)
        errors = cfg.validate()
        assert any("port" in e.lower() for e in errors)

    def test_validate_empty_image(self):
        cfg = ContainerConfig(base_image="")
        errors = cfg.validate()
        assert any("image" in e.lower() for e in errors)


# ===================================================================
# Dockerfile generation
# ===================================================================


class TestGenerateDockerfile:
    """Tests for Dockerfile generation."""

    def test_dockerfile_contains_from(self):
        cfg = ContainerConfig()
        df = generate_dockerfile(cfg)
        assert "FROM" in df

    def test_dockerfile_multistage(self):
        cfg = ContainerConfig()
        df = generate_dockerfile(cfg)
        # Should have at least 2 FROM statements (builder + runtime)
        assert df.count("FROM") >= 2

    def test_dockerfile_non_root_user(self):
        cfg = ContainerConfig(user="appuser")
        df = generate_dockerfile(cfg)
        assert "appuser" in df

    def test_dockerfile_healthcheck(self):
        cfg = ContainerConfig(healthcheck_path="/health")
        df = generate_dockerfile(cfg)
        assert "HEALTHCHECK" in df

    def test_dockerfile_custom_port(self):
        cfg = ContainerConfig(app_port=9000)
        df = generate_dockerfile(cfg)
        assert "9000" in df


# ===================================================================
# Docker Compose
# ===================================================================


class TestComposeConfig:
    """Tests for Docker Compose configuration."""

    def test_compose_service(self):
        svc = ComposeService(name="api", image="oac2fabric:latest", ports=["8000:8000"])
        assert svc.name == "api"
        assert "8000:8000" in svc.ports

    def test_default_config(self):
        cfg = ComposeConfig.default()
        assert len(cfg.services) >= 1
        names = [s.name for s in cfg.services]
        assert "api" in names

    def test_generate_compose_yaml(self):
        cfg = ComposeConfig.default()
        yaml_text = generate_compose(cfg)
        assert "services:" in yaml_text
        assert "api" in yaml_text


# ===================================================================
# Azure deploy config
# ===================================================================


class TestAzureDeployConfig:
    """Tests for Azure Container Apps configuration."""

    def test_defaults(self):
        cfg = AzureDeployConfig(resource_group="rg-test", location="eastus")
        assert cfg.resource_group == "rg-test"
        assert cfg.min_replicas >= 1

    def test_validate_passes(self):
        cfg = AzureDeployConfig(resource_group="rg-test", location="eastus")
        errors = cfg.validate()
        assert errors == []

    def test_validate_empty_rg(self):
        cfg = AzureDeployConfig(resource_group="", location="eastus")
        errors = cfg.validate()
        assert len(errors) > 0

    def test_validate_replicas_range(self):
        cfg = AzureDeployConfig(resource_group="rg", location="eastus", max_replicas=0, min_replicas=2)
        errors = cfg.validate()
        assert any("replica" in e.lower() for e in errors)


# ===================================================================
# Bicep generation
# ===================================================================


class TestGenerateBicep:
    """Tests for Bicep template generation."""

    def test_bicep_contains_resource(self):
        cfg = AzureDeployConfig(resource_group="rg-test", location="eastus")
        bicep = generate_bicep(cfg)
        assert "resource" in bicep
        assert "Microsoft.App" in bicep

    def test_bicep_contains_location(self):
        cfg = AzureDeployConfig(resource_group="rg-test", location="westeurope")
        bicep = generate_bicep(cfg)
        assert "westeurope" in bicep


# ===================================================================
# Helm values
# ===================================================================


class TestHelmValues:
    """Tests for Helm chart values."""

    def test_defaults(self):
        hv = HelmValues()
        assert hv.chart_name == "oac2fabric"
        assert hv.namespace == "oac2fabric"

    def test_to_values_dict(self):
        hv = HelmValues(api_replicas=2, dashboard_replicas=1)
        d = hv.to_values_dict()
        assert d["api"]["replicas"] == 2
        assert d["dashboard"]["replicas"] == 1

    def test_custom_namespace(self):
        hv = HelmValues(namespace="custom-ns")
        assert hv.namespace == "custom-ns"


# ===================================================================
# Smoke tests
# ===================================================================


class TestSmokeTestRunner:
    """Tests for smoke test infrastructure."""

    def test_smoke_result_model(self):
        r = SmokeTestResult(name="health", passed=True, status_code=200)
        assert r.passed is True
        assert r.status_code == 200

    def test_smoke_result_failure(self):
        r = SmokeTestResult(name="check", passed=False, error="timeout")
        assert r.passed is False
        assert r.error == "timeout"

    def test_runner_all_passed_empty(self):
        runner = SmokeTestRunner()
        # all_passed is a property; empty _results → all([]) → True
        assert runner.all_passed is True

    def test_runner_all_passed_mixed(self):
        runner = SmokeTestRunner()
        runner._results = [
            SmokeTestResult(name="a", passed=True),
            SmokeTestResult(name="b", passed=False),
        ]
        assert runner.all_passed is False

    def test_runner_all_passed_all_ok(self):
        runner = SmokeTestRunner()
        runner._results = [
            SmokeTestResult(name="a", passed=True),
            SmokeTestResult(name="b", passed=True),
        ]
        assert runner.all_passed is True
