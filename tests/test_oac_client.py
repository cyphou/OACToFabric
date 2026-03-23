"""Tests for OAC REST API client — mock HTTP responses."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.agents.discovery.oac_client import OACClient, _make_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_token_response():
    return {
        "access_token": "test-token-123",
        "expires_in": 3600,
        "token_type": "Bearer",
    }


@pytest.fixture
def mock_catalog_response():
    return {
        "items": [
            {
                "name": "Revenue Analysis",
                "path": "/shared/Sales/Revenue Analysis",
                "type": "analysis",
                "owner": "admin",
                "lastModified": "2025-01-15T10:30:00Z",
                "columns": ["Revenue", "Region", "Product"],
                "filters": ["Year = 2024"],
                "prompts": ["Region Prompt"],
                "subjectAreas": ["Sales - Revenue"],
            },
            {
                "name": "Cost Dashboard",
                "path": "/shared/Finance/Cost Dashboard",
                "type": "dashboard",
                "owner": "finance_user",
                "lastModified": "2025-02-01T08:00:00Z",
                "pages": ["Overview", "Details"],
                "embeddedContent": [
                    {"path": "/shared/Finance/Cost Breakdown"},
                ],
            },
        ]
    }


@pytest.fixture
def mock_connections_response():
    return {
        "items": [
            {
                "name": "OracleDB_Prod",
                "type": "Oracle",
                "host": "db.example.com",
                "port": 1521,
                "database": "PROD",
                "owner": "admin",
            }
        ]
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMakeId:
    def test_basic(self):
        assert _make_id("analysis", "/shared/Sales/Report") == "analysis__shared__sales__report"

    def test_spaces(self):
        assert _make_id("dashboard", "/shared/My Report") == "dashboard__shared__my_report"


class TestOACClientParsing:
    def test_parse_catalog_item_analysis(self, mock_catalog_response):
        raw = mock_catalog_response["items"][0]
        from src.core.models import AssetType
        item = OACClient._parse_catalog_item(raw, AssetType.ANALYSIS)

        assert item.name == "Revenue Analysis"
        assert item.asset_type == AssetType.ANALYSIS
        assert item.source_path == "/shared/Sales/Revenue Analysis"
        assert item.owner == "admin"
        assert "Revenue" in item.metadata.get("columns", [])
        assert len(item.dependencies) >= 1  # subject area dep

    def test_parse_catalog_item_dashboard_with_embedded(self, mock_catalog_response):
        raw = mock_catalog_response["items"][1]
        from src.core.models import AssetType
        item = OACClient._parse_catalog_item(raw, AssetType.DASHBOARD)

        assert item.name == "Cost Dashboard"
        assert item.asset_type == AssetType.DASHBOARD
        assert len(item.metadata.get("pages", [])) == 2
        # Should have embedding dep
        embed_deps = [d for d in item.dependencies if d.dependency_type == "embeds_analysis"]
        assert len(embed_deps) == 1


class TestOACClientInit:
    def test_defaults(self):
        client = OACClient(
            base_url="https://example.com",
            client_id="id",
            client_secret="secret",
            token_url="https://auth.example.com/token",
        )
        assert client._base_url == "https://example.com"
        assert client._client_id == "id"
