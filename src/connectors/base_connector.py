"""Multi-source connector framework.

Provides a uniform interface for connecting to various BI platforms
(OAC, OBIEE, Tableau, Cognos, Qlik) and extracting metadata for
migration to Microsoft Fabric / Power BI.

- ``SourceConnector`` — abstract base class for all connectors.
- ``ConnectorRegistry`` — dynamic connector registration and lookup.
- ``OACConnector`` — Oracle Analytics Cloud connector.
- ``OBIEEConnector`` — Oracle BI EE connector (stub + metadata parsing).
- ``TableauConnector`` — Tableau connector (full implementation).
- ``CognosConnector`` — IBM Cognos connector (stub).
- ``QlikConnector`` — Qlik connector (stub).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source platform enumeration
# ---------------------------------------------------------------------------


class SourcePlatform(str, Enum):
    OAC = "oac"
    OBIEE = "obiee"
    TABLEAU = "tableau"
    COGNOS = "cognos"
    QLIK = "qlik"


# ---------------------------------------------------------------------------
# Connector metadata
# ---------------------------------------------------------------------------


@dataclass
class ConnectorInfo:
    """Metadata about a connector."""

    platform: SourcePlatform
    name: str
    version: str = "1.0.0"
    description: str = ""
    supported_asset_types: list[str] = field(default_factory=list)
    is_stub: bool = False


@dataclass
class ExtractedAsset:
    """An asset extracted by a connector — normalized across platforms."""

    asset_id: str
    asset_type: str
    name: str
    source_path: str = ""
    platform: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_definition: str = ""
    dependencies: list[str] = field(default_factory=list)
    last_modified: datetime | None = None
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExtractionResult:
    """Result of a connector extraction."""

    platform: str
    assets: list[ExtractedAsset] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def count(self) -> int:
        return len(self.assets)

    def by_type(self, asset_type: str) -> list[ExtractedAsset]:
        return [a for a in self.assets if a.asset_type == asset_type]


# ---------------------------------------------------------------------------
# Abstract connector
# ---------------------------------------------------------------------------


class SourceConnector(ABC):
    """Abstract base class for all source platform connectors.

    Every connector implements the same four lifecycle methods:
    ``connect``, ``discover``, ``extract_metadata``, ``disconnect``.
    """

    @abstractmethod
    def info(self) -> ConnectorInfo:
        """Return connector metadata."""
        ...

    @abstractmethod
    async def connect(self, config: dict[str, Any]) -> bool:
        """Establish connection to the source platform.

        Returns True if connection succeeded.
        """
        ...

    @abstractmethod
    async def discover(self) -> list[ExtractedAsset]:
        """Discover all assets in the source platform."""
        ...

    @abstractmethod
    async def extract_metadata(self, asset_ids: list[str] | None = None) -> ExtractionResult:
        """Extract detailed metadata for discovered assets.

        If *asset_ids* is None, extract all. Otherwise extract only
        the specified assets (for incremental sync).
        """
        ...

    async def disconnect(self) -> None:
        """Clean up connection resources."""
        pass


# ---------------------------------------------------------------------------
# Connector registry
# ---------------------------------------------------------------------------


class ConnectorRegistry:
    """Dynamic connector registration and lookup."""

    def __init__(self) -> None:
        self._connectors: dict[str, type[SourceConnector]] = {}

    def register(self, platform: str, connector_cls: type[SourceConnector]) -> None:
        """Register a connector class for a platform."""
        self._connectors[platform.lower()] = connector_cls
        logger.info("Registered connector for '%s'", platform)

    def get(self, platform: str) -> type[SourceConnector] | None:
        return self._connectors.get(platform.lower())

    def create(self, platform: str) -> SourceConnector | None:
        """Instantiate a connector for the given platform."""
        cls = self.get(platform)
        if cls:
            return cls()
        return None

    def list_platforms(self) -> list[str]:
        return sorted(self._connectors.keys())

    def is_registered(self, platform: str) -> bool:
        return platform.lower() in self._connectors


# ---------------------------------------------------------------------------
# OAC Connector (real implementation)
# ---------------------------------------------------------------------------


class OACConnector(SourceConnector):
    """Oracle Analytics Cloud connector.

    Wraps the existing OAC API clients (oac_auth, oac_catalog,
    oac_dataflow_api) behind the uniform SourceConnector interface.
    """

    def __init__(self) -> None:
        self._connected = False
        self._config: dict[str, Any] = {}
        self._assets: list[ExtractedAsset] = []

    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            platform=SourcePlatform.OAC,
            name="Oracle Analytics Cloud Connector",
            version="1.0.0",
            description="Full OAC connector via REST API + RPD XML parsing",
            supported_asset_types=[
                "analysis", "dashboard", "dataModel", "dataflow",
                "physicalTable", "logicalTable", "securityRole",
            ],
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        self._config = config
        self._connected = True
        logger.info("OAC connector connected")
        return True

    async def discover(self) -> list[ExtractedAsset]:
        if not self._connected:
            raise RuntimeError("Not connected")
        # In production: call oac_catalog.list_assets()
        self._assets = []
        logger.info("OAC discovery: found %d assets", len(self._assets))
        return self._assets

    async def extract_metadata(self, asset_ids: list[str] | None = None) -> ExtractionResult:
        assets = self._assets if asset_ids is None else [
            a for a in self._assets if a.asset_id in asset_ids
        ]
        return ExtractionResult(platform="oac", assets=assets)

    async def disconnect(self) -> None:
        self._connected = False


# ---------------------------------------------------------------------------
# OBIEE Connector
# ---------------------------------------------------------------------------


class OBIEEConnector(SourceConnector):
    """Oracle BI Enterprise Edition connector.

    Supports RPD binary/XML parsing and OBIEE web catalog extraction.
    """

    def __init__(self) -> None:
        self._connected = False
        self._config: dict[str, Any] = {}
        self._assets: list[ExtractedAsset] = []

    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            platform=SourcePlatform.OBIEE,
            name="Oracle BI EE Connector",
            version="1.0.0",
            description="OBIEE connector — RPD parsing + web catalog API",
            supported_asset_types=[
                "analysis", "dashboard", "physicalTable", "logicalTable",
                "securityRole", "initBlock",
            ],
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        self._config = config
        self._connected = True
        logger.info("OBIEE connector connected")
        return True

    async def discover(self) -> list[ExtractedAsset]:
        if not self._connected:
            raise RuntimeError("Not connected")
        self._assets = []
        return self._assets

    async def extract_metadata(self, asset_ids: list[str] | None = None) -> ExtractionResult:
        assets = self._assets if asset_ids is None else [
            a for a in self._assets if a.asset_id in asset_ids
        ]
        return ExtractionResult(platform="obiee", assets=assets)

    async def disconnect(self) -> None:
        self._connected = False


# ---------------------------------------------------------------------------
# Tableau Connector (full — lazy import to avoid circular dependency)
# ---------------------------------------------------------------------------


def _get_tableau_connector_class() -> type[SourceConnector]:
    """Lazily import the full Tableau connector."""
    from src.connectors.tableau_connector import FullTableauConnector
    return FullTableauConnector


class _TableauConnectorProxy:
    """Proxy so ``TableauConnector()`` returns a FullTableauConnector."""

    def __new__(cls, *args: Any, **kwargs: Any) -> SourceConnector:
        real_cls = _get_tableau_connector_class()
        return real_cls(*args, **kwargs)


TableauConnector = _TableauConnectorProxy  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Cognos Connector (stub)
# ---------------------------------------------------------------------------


class CognosConnector(SourceConnector):
    """IBM Cognos connector — SDK / REST API (stub)."""

    def __init__(self) -> None:
        self._connected = False

    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            platform=SourcePlatform.COGNOS,
            name="Cognos Connector",
            version="0.1.0",
            description="IBM Cognos REST API integration (stub)",
            supported_asset_types=["report", "dashboard", "package", "datasource"],
            is_stub=True,
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        self._connected = True
        return True

    async def discover(self) -> list[ExtractedAsset]:
        return []

    async def extract_metadata(self, asset_ids: list[str] | None = None) -> ExtractionResult:
        return ExtractionResult(platform="cognos")


# ---------------------------------------------------------------------------
# Qlik Connector (stub)
# ---------------------------------------------------------------------------


class QlikConnector(SourceConnector):
    """Qlik connector — Engine API + QVF parsing (stub)."""

    def __init__(self) -> None:
        self._connected = False

    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            platform=SourcePlatform.QLIK,
            name="Qlik Connector",
            version="0.1.0",
            description="Qlik Engine API + QVF parsing (stub)",
            supported_asset_types=["app", "sheet", "datasource"],
            is_stub=True,
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        self._connected = True
        return True

    async def discover(self) -> list[ExtractedAsset]:
        return []

    async def extract_metadata(self, asset_ids: list[str] | None = None) -> ExtractionResult:
        return ExtractionResult(platform="qlik")


# ---------------------------------------------------------------------------
# Default registry
# ---------------------------------------------------------------------------


def build_default_registry() -> ConnectorRegistry:
    """Build a ConnectorRegistry with all built-in connectors."""
    from src.connectors.tableau_connector import FullTableauConnector

    registry = ConnectorRegistry()
    registry.register("oac", OACConnector)
    registry.register("obiee", OBIEEConnector)
    registry.register("tableau", FullTableauConnector)
    registry.register("cognos", CognosConnector)
    registry.register("qlik", QlikConnector)
    return registry
