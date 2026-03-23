"""Phase 26 — Multi-Source Connector Framework.

Tests cover:
- SourcePlatform enum values
- ConnectorInfo construction and is_stub
- ExtractedAsset fields
- ExtractionResult properties (success, count, by_type)
- ConnectorRegistry register/get/create/list
- OACConnector info and lifecycle
- OBIEEConnector info and lifecycle
- Stub connectors (Tableau, Cognos, Qlik)
- build_default_registry helper
"""

from __future__ import annotations

import pytest

from src.connectors.base_connector import (
    CognosConnector,
    ConnectorInfo,
    ConnectorRegistry,
    ExtractedAsset,
    ExtractionResult,
    OACConnector,
    OBIEEConnector,
    QlikConnector,
    SourcePlatform,
    TableauConnector,
    build_default_registry,
)


# ===================================================================
# SourcePlatform
# ===================================================================


class TestSourcePlatform:
    """Tests for source platform enum."""

    def test_platform_values(self):
        assert SourcePlatform.OAC.value == "oac"
        assert SourcePlatform.OBIEE.value == "obiee"
        assert SourcePlatform.TABLEAU.value == "tableau"
        assert SourcePlatform.COGNOS.value == "cognos"
        assert SourcePlatform.QLIK.value == "qlik"
        assert SourcePlatform.ESSBASE.value == "essbase"

    def test_all_platforms(self):
        assert len(SourcePlatform) == 6


# ===================================================================
# ConnectorInfo
# ===================================================================


class TestConnectorInfo:
    """Tests for connector info."""

    def test_full_connector_info(self):
        info = ConnectorInfo(
            platform=SourcePlatform.OAC,
            name="OAC Connector",
            version="1.0.0",
            description="Oracle Analytics Cloud connector",
            supported_asset_types=["analysis", "dashboard"],
            is_stub=False,
        )
        assert info.platform == SourcePlatform.OAC
        assert info.is_stub is False
        assert len(info.supported_asset_types) == 2

    def test_stub_connector_info(self):
        info = ConnectorInfo(
            platform=SourcePlatform.TABLEAU,
            name="Tableau Stub",
            version="0.1.0",
            is_stub=True,
        )
        assert info.is_stub is True


# ===================================================================
# ExtractedAsset
# ===================================================================


class TestExtractedAsset:
    """Tests for extracted asset."""

    def test_asset_fields(self):
        asset = ExtractedAsset(
            asset_id="a1",
            asset_type="analysis",
            name="Sales Report",
            source_path="/shared/Sales",
            platform="oac",
            metadata={"owner": "admin"},
            dependencies=["a2", "a3"],
        )
        assert asset.asset_id == "a1"
        assert asset.platform == "oac"
        assert len(asset.dependencies) == 2

    def test_asset_defaults(self):
        asset = ExtractedAsset(
            asset_id="x",
            asset_type="dashboard",
            name="d1",
            source_path="/",
            platform="obiee",
        )
        assert asset.metadata == {}
        assert asset.dependencies == []


# ===================================================================
# ExtractionResult
# ===================================================================


class TestExtractionResult:
    """Tests for extraction result."""

    def test_empty_result(self):
        r = ExtractionResult(platform="oac", assets=[], errors=[])
        assert r.success is True
        assert r.count == 0

    def test_result_with_assets(self):
        assets = [
            ExtractedAsset("a1", "analysis", "r1", "/", "oac"),
            ExtractedAsset("a2", "dashboard", "d1", "/", "oac"),
            ExtractedAsset("a3", "analysis", "r2", "/", "oac"),
        ]
        r = ExtractionResult(platform="oac", assets=assets, errors=[])
        assert r.count == 3
        assert r.success is True
        assert len(r.by_type("analysis")) == 2
        assert len(r.by_type("dashboard")) == 1

    def test_result_with_errors(self):
        r = ExtractionResult(
            platform="oac",
            assets=[],
            errors=["connection timeout"],
        )
        assert r.success is False


# ===================================================================
# ConnectorRegistry
# ===================================================================


class TestConnectorRegistry:
    """Tests for connector registry."""

    def test_register_and_get(self):
        registry = ConnectorRegistry()
        registry.register("oac", OACConnector)
        assert registry.is_registered("oac") is True
        cls = registry.get("oac")
        assert cls is OACConnector

    def test_get_unregistered(self):
        registry = ConnectorRegistry()
        assert registry.get("tableau") is None

    def test_create_instance(self):
        registry = ConnectorRegistry()
        registry.register("oac", OACConnector)
        connector = registry.create("oac")
        assert connector is not None
        assert isinstance(connector, OACConnector)

    def test_create_unregistered(self):
        registry = ConnectorRegistry()
        assert registry.create("qlik") is None

    def test_list_platforms(self):
        registry = ConnectorRegistry()
        registry.register("oac", OACConnector)
        registry.register("obiee", OBIEEConnector)
        platforms = registry.list_platforms()
        assert "oac" in platforms
        assert "obiee" in platforms
        assert len(platforms) == 2


# ===================================================================
# Concrete connectors — info
# ===================================================================


class TestOACConnector:
    """Tests for OAC connector."""

    def test_info(self):
        c = OACConnector()
        info = c.info()
        assert info.platform == SourcePlatform.OAC
        assert info.is_stub is False
        assert "Oracle" in info.name and "Analytics" in info.name

    def test_info_has_asset_types(self):
        c = OACConnector()
        info = c.info()
        assert len(info.supported_asset_types) > 0


class TestOBIEEConnector:
    """Tests for OBIEE connector."""

    def test_info(self):
        c = OBIEEConnector()
        info = c.info()
        assert info.platform == SourcePlatform.OBIEE
        assert "Oracle" in info.name and "BI" in info.name


class TestTableauConnector:
    """Tests for Tableau connector (now full implementation)."""

    def test_is_not_stub(self):
        c = TableauConnector()
        assert c.info().is_stub is False
        assert c.info().platform == SourcePlatform.TABLEAU


class TestCognosConnector:
    """Tests for Cognos stub connector."""

    def test_is_stub(self):
        c = CognosConnector()
        assert c.info().is_stub is True
        assert c.info().platform == SourcePlatform.COGNOS


class TestQlikConnector:
    """Tests for Qlik stub connector."""

    def test_is_stub(self):
        c = QlikConnector()
        assert c.info().is_stub is True
        assert c.info().platform == SourcePlatform.QLIK


# ===================================================================
# build_default_registry
# ===================================================================


class TestBuildDefaultRegistry:
    """Tests for the default registry builder."""

    def test_all_platforms_registered(self):
        registry = build_default_registry()
        for platform in SourcePlatform:
            assert registry.is_registered(platform.value), f"{platform} not registered"

    def test_can_create_all(self):
        registry = build_default_registry()
        for platform in SourcePlatform:
            connector = registry.create(platform.value)
            assert connector is not None, f"Cannot create {platform}"

    def test_registry_count(self):
        registry = build_default_registry()
        assert len(registry.list_platforms()) == 6
