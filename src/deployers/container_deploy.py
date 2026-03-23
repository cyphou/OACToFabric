"""Containerization and cloud deployment configuration.

Provides:
- ``ContainerConfig`` — Docker image build configuration.
- ``ComposeConfig`` — Docker Compose service definitions.
- ``AzureDeployConfig`` — Azure Container Apps IaC configuration.
- ``HelmValues`` — Kubernetes Helm chart values.
- ``generate_dockerfile()`` — Generate a production Dockerfile.
- ``generate_compose()`` — Generate a docker-compose.yml.
- ``generate_bicep()`` — Generate Azure Bicep template.
- ``SmokeTestRunner`` — Post-deployment smoke test runner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Docker configuration
# ---------------------------------------------------------------------------


@dataclass
class ContainerConfig:
    """Docker container build configuration."""

    base_image: str = "python:3.11-slim"
    app_port: int = 8000
    workdir: str = "/app"
    user: str = "appuser"
    healthcheck_path: str = "/health"
    env_vars: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=lambda: {
        "org.opencontainers.image.title": "oac2fabric-api",
        "org.opencontainers.image.version": "2.0.0",
    })

    def validate(self) -> list[str]:
        """Return list of validation errors (empty if valid)."""
        errors = []
        if not self.base_image:
            errors.append("base_image is required")
        if self.app_port < 1 or self.app_port > 65535:
            errors.append(f"Invalid port: {self.app_port}")
        if not self.workdir.startswith("/"):
            errors.append("workdir must be an absolute path")
        return errors


def generate_dockerfile(config: ContainerConfig | None = None) -> str:
    """Generate a multi-stage production Dockerfile."""
    cfg = config or ContainerConfig()

    return f"""# ---- Build stage ----
FROM {cfg.base_image} AS builder

WORKDIR {cfg.workdir}

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir --upgrade pip \\
    && pip install --no-cache-dir .

# ---- Runtime stage ----
FROM {cfg.base_image}

RUN groupadd -r {cfg.user} && useradd -r -g {cfg.user} {cfg.user}

WORKDIR {cfg.workdir}

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder {cfg.workdir} {cfg.workdir}

USER {cfg.user}

EXPOSE {cfg.app_port}

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{cfg.app_port}{cfg.healthcheck_path}')"

CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "{cfg.app_port}"]
"""


# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------


@dataclass
class ComposeService:
    """A service in Docker Compose."""

    name: str
    image: str = ""
    build_context: str = "."
    dockerfile: str = "Dockerfile"
    ports: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    healthcheck_cmd: str = ""
    volumes: list[str] = field(default_factory=list)


@dataclass
class ComposeConfig:
    """Docker Compose configuration."""

    services: list[ComposeService] = field(default_factory=list)
    version: str = "3.9"

    @staticmethod
    def default() -> "ComposeConfig":
        """Return a default compose config for API + dashboard."""
        return ComposeConfig(
            services=[
                ComposeService(
                    name="api",
                    build_context=".",
                    dockerfile="Dockerfile",
                    ports=["8000:8000"],
                    environment={"LOG_LEVEL": "INFO"},
                    healthcheck_cmd="curl -f http://localhost:8000/health || exit 1",
                ),
                ComposeService(
                    name="dashboard",
                    build_context="./dashboard",
                    dockerfile="Dockerfile",
                    ports=["3000:80"],
                    depends_on=["api"],
                ),
            ]
        )


def generate_compose(config: ComposeConfig | None = None) -> str:
    """Generate docker-compose.yml content."""
    cfg = config or ComposeConfig.default()

    lines = [f"version: '{cfg.version}'", "", "services:"]

    for svc in cfg.services:
        lines.append(f"  {svc.name}:")
        if svc.image:
            lines.append(f"    image: {svc.image}")
        else:
            lines.append("    build:")
            lines.append(f"      context: {svc.build_context}")
            lines.append(f"      dockerfile: {svc.dockerfile}")
        if svc.ports:
            lines.append("    ports:")
            for p in svc.ports:
                lines.append(f'      - "{p}"')
        if svc.environment:
            lines.append("    environment:")
            for k, v in svc.environment.items():
                lines.append(f"      {k}: {v}")
        if svc.depends_on:
            lines.append("    depends_on:")
            for dep in svc.depends_on:
                lines.append(f"      - {dep}")
        if svc.healthcheck_cmd:
            lines.append("    healthcheck:")
            lines.append(f'      test: ["{svc.healthcheck_cmd}"]')
            lines.append("      interval: 30s")
            lines.append("      timeout: 10s")
            lines.append("      retries: 3")
        if svc.volumes:
            lines.append("    volumes:")
            for v in svc.volumes:
                lines.append(f"      - {v}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Azure Container Apps (Bicep)
# ---------------------------------------------------------------------------


@dataclass
class AzureDeployConfig:
    """Azure Container Apps deployment configuration."""

    resource_group: str = "rg-oac2fabric"
    location: str = "eastus"
    env_name: str = "oac2fabric-env"
    api_app_name: str = "oac2fabric-api"
    dashboard_app_name: str = "oac2fabric-dashboard"
    acr_name: str = "oac2fabricacr"
    api_image: str = "oac2fabricacr.azurecr.io/api:latest"
    dashboard_image: str = "oac2fabricacr.azurecr.io/dashboard:latest"
    min_replicas: int = 1
    max_replicas: int = 5
    cpu: float = 0.5
    memory: str = "1Gi"
    keyvault_name: str = ""
    app_insights_connection: str = ""
    managed_identity: bool = True

    def validate(self) -> list[str]:
        errors = []
        if not self.resource_group:
            errors.append("resource_group is required")
        if not self.location:
            errors.append("location is required")
        if self.min_replicas < 0:
            errors.append("min_replicas must be >= 0")
        if self.max_replicas < self.min_replicas:
            errors.append("max_replicas must be >= min_replicas")
        return errors


def generate_bicep(config: AzureDeployConfig | None = None) -> str:
    """Generate Azure Bicep template for Container Apps deployment."""
    cfg = config or AzureDeployConfig()

    return f"""// OAC-to-Fabric Migration Platform — Azure Container Apps
// Generated by oac2fabric deployment module

param location string = '{cfg.location}'
param environmentName string = '{cfg.env_name}'
param apiAppName string = '{cfg.api_app_name}'
param dashboardAppName string = '{cfg.dashboard_app_name}'
param apiImage string = '{cfg.api_image}'
param dashboardImage string = '{cfg.dashboard_image}'

resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {{
  name: environmentName
  location: location
  properties: {{
    appLogsConfiguration: {{
      destination: 'log-analytics'
    }}
  }}
}}

resource apiApp 'Microsoft.App/containerApps@2023-05-01' = {{
  name: apiAppName
  location: location
  identity: {{
    type: 'SystemAssigned'
  }}
  properties: {{
    managedEnvironmentId: containerAppEnv.id
    configuration: {{
      ingress: {{
        external: true
        targetPort: 8000
        transport: 'http'
      }}
    }}
    template: {{
      containers: [
        {{
          name: 'api'
          image: apiImage
          resources: {{
            cpu: json('{cfg.cpu}')
            memory: '{cfg.memory}'
          }}
        }}
      ]
      scale: {{
        minReplicas: {cfg.min_replicas}
        maxReplicas: {cfg.max_replicas}
      }}
    }}
  }}
}}

resource dashboardApp 'Microsoft.App/containerApps@2023-05-01' = {{
  name: dashboardAppName
  location: location
  properties: {{
    managedEnvironmentId: containerAppEnv.id
    configuration: {{
      ingress: {{
        external: true
        targetPort: 80
        transport: 'http'
      }}
    }}
    template: {{
      containers: [
        {{
          name: 'dashboard'
          image: dashboardImage
          resources: {{
            cpu: json('0.25')
            memory: '0.5Gi'
          }}
        }}
      ]
      scale: {{
        minReplicas: 1
        maxReplicas: 3
      }}
    }}
  }}
}}

output apiUrl string = 'https://${{apiApp.properties.configuration.ingress.fqdn}}'
output dashboardUrl string = 'https://${{dashboardApp.properties.configuration.ingress.fqdn}}'
"""


# ---------------------------------------------------------------------------
# Helm chart values
# ---------------------------------------------------------------------------


@dataclass
class HelmValues:
    """Kubernetes Helm chart values."""

    chart_name: str = "oac2fabric"
    namespace: str = "oac2fabric"
    api_image: str = "ghcr.io/oac2fabric/api:2.0"
    dashboard_image: str = "ghcr.io/oac2fabric/dashboard:2.0"
    api_replicas: int = 2
    dashboard_replicas: int = 1
    api_port: int = 8000
    dashboard_port: int = 80
    ingress_enabled: bool = True
    ingress_host: str = "oac2fabric.example.com"
    tls_enabled: bool = True
    resource_limits_cpu: str = "500m"
    resource_limits_memory: str = "512Mi"

    def to_values_dict(self) -> dict[str, Any]:
        return {
            "api": {
                "image": self.api_image,
                "replicas": self.api_replicas,
                "port": self.api_port,
                "resources": {
                    "limits": {"cpu": self.resource_limits_cpu, "memory": self.resource_limits_memory}
                },
            },
            "dashboard": {
                "image": self.dashboard_image,
                "replicas": self.dashboard_replicas,
                "port": self.dashboard_port,
            },
            "ingress": {
                "enabled": self.ingress_enabled,
                "host": self.ingress_host,
                "tls": self.tls_enabled,
            },
        }


# ---------------------------------------------------------------------------
# Smoke test runner
# ---------------------------------------------------------------------------


@dataclass
class SmokeTestResult:
    """Result of a post-deployment smoke test."""

    name: str
    passed: bool
    status_code: int | None = None
    response_time_ms: float = 0.0
    error: str = ""


class SmokeTestRunner:
    """Run post-deployment smoke tests against a live API.

    In-process testing (no actual HTTP calls) when ``base_url`` is
    ``"mock://"``.  Real HTTP via ``httpx`` otherwise.
    """

    def __init__(self, base_url: str = "mock://") -> None:
        self.base_url = base_url.rstrip("/")
        self._results: list[SmokeTestResult] = []

    async def check_health(self) -> SmokeTestResult:
        result = SmokeTestResult(name="health_check", passed=True, status_code=200, response_time_ms=1.0)
        if self.base_url == "mock://":
            self._results.append(result)
            return result
        # pragma: no cover — real HTTP
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/health", timeout=10.0)
                result.status_code = r.status_code
                result.passed = r.status_code == 200
        except Exception as exc:
            result.passed = False
            result.error = str(exc)
        self._results.append(result)
        return result

    async def check_migrations_list(self) -> SmokeTestResult:
        result = SmokeTestResult(name="migrations_list", passed=True, status_code=200, response_time_ms=1.0)
        if self.base_url == "mock://":
            self._results.append(result)
            return result
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/migrations", timeout=10.0)
                result.status_code = r.status_code
                result.passed = r.status_code == 200
        except Exception as exc:
            result.passed = False
            result.error = str(exc)
        self._results.append(result)
        return result

    async def run_all(self) -> list[SmokeTestResult]:
        """Run all smoke tests and return results."""
        self._results.clear()
        await self.check_health()
        await self.check_migrations_list()
        return list(self._results)

    @property
    def results(self) -> list[SmokeTestResult]:
        return list(self._results)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self._results)
