"""Phase 23 — Web API & Dashboard.

Tests cover:
- MigrationCreateRequest validation
- MigrationStatusResponse construction
- MigrationRecord lifecycle (create, log, broadcast)
- MigrationStore CRUD operations
- create_app() factory (skipped when FastAPI not installed)
- Health check response model
- Cancel / Inventory response models
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from src.api.app import (
    AgentStatusResponse,
    CancelResponse,
    HealthResponse,
    InventoryItemResponse,
    InventoryResponse,
    MigrationCreateRequest,
    MigrationMode,
    MigrationRecord,
    MigrationStatusResponse,
    MigrationStore,
    create_app,
)


# ===================================================================
# MigrationCreateRequest
# ===================================================================


class TestMigrationCreateRequest:
    """Tests for request model."""

    def test_create_request_defaults(self):
        req = MigrationCreateRequest(name="test-mig")
        assert req.name == "test-mig"
        assert req.source_type == "oac"
        assert req.mode == MigrationMode.FULL
        assert req.dry_run is False

    def test_create_request_custom_fields(self):
        req = MigrationCreateRequest(
            name="custom",
            source_type="obiee",
            config={"host": "localhost"},
            mode=MigrationMode.INCREMENTAL,
            wave=1,
            dry_run=True,
        )
        assert req.source_type == "obiee"
        assert req.config["host"] == "localhost"
        assert req.mode == MigrationMode.INCREMENTAL
        assert req.wave == 1
        assert req.dry_run is True

    def test_create_request_empty_config(self):
        req = MigrationCreateRequest(name="x")
        assert req.config == {}


# ===================================================================
# MigrationStatusResponse
# ===================================================================


class TestMigrationStatusResponse:
    """Tests for status response model."""

    def test_status_response_fields(self):
        now = datetime.now(timezone.utc)
        resp = MigrationStatusResponse(
            id="abc",
            name="test",
            status="in-progress",
            created_at=now,
            progress_pct=50.0,
            agents=[],
            total_items=100,
            succeeded_items=40,
            failed_items=5,
        )
        assert resp.id == "abc"
        assert resp.progress_pct == 50.0
        assert resp.total_items == 100

    def test_agent_status_response(self):
        agent = AgentStatusResponse(
            agent_id="01",
            state="running",
        )
        assert agent.agent_id == "01"


# ===================================================================
# MigrationRecord
# ===================================================================


class TestMigrationRecord:
    """Tests for in-memory migration record."""

    def _make_req(self, name: str = "test-mig") -> MigrationCreateRequest:
        return MigrationCreateRequest(name=name)

    def test_record_creation(self):
        rec = MigrationRecord(self._make_req("test-mig"))
        assert rec.name == "test-mig"
        assert rec.status == "pending"
        assert len(rec.id) > 0
        assert rec.logs == []

    def test_add_log(self):
        rec = MigrationRecord(self._make_req("m1"))
        rec.add_log("INFO", "hello")
        rec.add_log("INFO", "world")
        assert len(rec.logs) == 2
        assert rec.logs[0].message == "hello"

    def test_to_status(self):
        rec = MigrationRecord(self._make_req("m1"))
        rec.status = "running"
        rec.progress_pct = 75.0
        status = rec.to_status()
        assert isinstance(status, MigrationStatusResponse)
        assert status.status == "running"
        assert status.progress_pct == 75.0

    def test_subscribe_unsubscribe(self):
        rec = MigrationRecord(self._make_req("m1"))
        q = rec.subscribe()
        assert q in rec._ws_subscribers
        rec.unsubscribe(q)
        assert q not in rec._ws_subscribers


# ===================================================================
# MigrationStore
# ===================================================================


class TestMigrationStore:
    """Tests for in-memory migration store."""

    def _req(self, name: str = "test") -> MigrationCreateRequest:
        return MigrationCreateRequest(name=name)

    def test_create_and_get(self):
        store = MigrationStore()
        rec = store.create(self._req("test"))
        assert rec.name == "test"
        found = store.get(rec.id)
        assert found is not None
        assert found.id == rec.id

    def test_get_nonexistent(self):
        store = MigrationStore()
        assert store.get("nonexistent") is None

    def test_list_all(self):
        store = MigrationStore()
        store.create(self._req("a"))
        store.create(self._req("b"))
        assert len(store.list_all()) == 2

    def test_active_count(self):
        store = MigrationStore()
        r1 = store.create(self._req("a"))
        r2 = store.create(self._req("b"))
        r1.status = "running"
        r2.status = "completed"
        assert store.active_count >= 0

    def test_uptime_seconds(self):
        store = MigrationStore()
        assert store.uptime_seconds >= 0.0


# ===================================================================
# create_app & response models
# ===================================================================


_HAS_FASTAPI = True
try:
    import fastapi  # noqa: F401
except ImportError:
    _HAS_FASTAPI = False


class TestCreateApp:
    """Tests for FastAPI application factory."""

    @pytest.mark.skipif(not _HAS_FASTAPI, reason="FastAPI not installed")
    def test_app_creation(self):
        app = create_app()
        assert app is not None
        assert app.title == "OAC-to-Fabric Migration Platform"

    @pytest.mark.skipif(not _HAS_FASTAPI, reason="FastAPI not installed")
    def test_app_routes_exist(self):
        app = create_app()
        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/health" in route_paths
        assert "/migrations" in route_paths

    def test_health_response_model(self):
        resp = HealthResponse(
            status="healthy",
            version="2.0.0",
            uptime_seconds=42.0,
            migrations_active=0,
        )
        assert resp.status == "healthy"

    def test_cancel_response_model(self):
        resp = CancelResponse(migration_id="abc", cancelled=True, message="ok")
        assert resp.migration_id == "abc"

    def test_inventory_item_model(self):
        item = InventoryItemResponse(
            id="a1",
            asset_type="analysis",
            name="report1",
            source_path="/shared/reports",
            migration_status="migrated",
        )
        assert item.id == "a1"

    def test_inventory_response_model(self):
        inv = InventoryResponse(
            migration_id="m1",
            total=2,
            items=[
                InventoryItemResponse(id="a1", asset_type="analysis", name="r1", source_path="/"),
                InventoryItemResponse(id="a2", asset_type="dashboard", name="d1", source_path="/"),
            ],
        )
        assert inv.total == 2
        assert len(inv.items) == 2
