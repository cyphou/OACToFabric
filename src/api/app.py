"""FastAPI Web API for the OAC-to-Fabric migration platform.

Exposes the migration engine as a REST + WebSocket service:
- ``POST /migrations`` — start a new migration
- ``GET  /migrations/{id}`` — migration status
- ``GET  /migrations/{id}/inventory`` — discovered assets
- ``GET  /migrations/{id}/logs`` — SSE log stream
- ``POST /migrations/{id}/cancel`` — graceful shutdown
- ``WS   /ws/migrations/{id}`` — real-time WebSocket event feed
- ``GET  /health`` — readiness/liveness probe
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class MigrationMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class MigrationCreateRequest(BaseModel):
    """Payload for ``POST /migrations``."""

    name: str = Field(description="Human-readable migration name")
    source_type: str = Field(default="oac", description="Source platform (oac, obiee, tableau, …)")
    config: dict[str, Any] = Field(default_factory=dict, description="Migration config dict")
    mode: MigrationMode = MigrationMode.FULL
    wave: int | None = None
    dry_run: bool = False


class AgentStatusResponse(BaseModel):
    agent_id: str
    state: str = "idle"
    items_processed: int = 0
    items_failed: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None


class MigrationStatusResponse(BaseModel):
    """Response for ``GET /migrations/{id}``."""

    id: str
    name: str
    status: str = "pending"
    mode: str = "full"
    source_type: str = "oac"
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress_pct: float = 0.0
    agents: list[AgentStatusResponse] = Field(default_factory=list)
    total_items: int = 0
    succeeded_items: int = 0
    failed_items: int = 0
    error: str | None = None


class InventoryItemResponse(BaseModel):
    id: str
    asset_type: str
    name: str
    source_path: str
    complexity: str = "Low"
    migration_status: str = "not-started"


class InventoryResponse(BaseModel):
    migration_id: str
    total: int
    items: list[InventoryItemResponse] = Field(default_factory=list)


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    agent_id: str = ""
    message: str


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "2.0.0"
    uptime_seconds: float = 0.0
    migrations_active: int = 0


class CancelResponse(BaseModel):
    migration_id: str
    cancelled: bool
    message: str = ""


# ---------------------------------------------------------------------------
# Migration store (in-memory)
# ---------------------------------------------------------------------------


class MigrationRecord:
    """In-memory record of a migration run."""

    def __init__(self, req: MigrationCreateRequest) -> None:
        self.id: str = uuid.uuid4().hex[:12]
        self.name: str = req.name
        self.source_type: str = req.source_type
        self.mode: str = req.mode.value
        self.config: dict[str, Any] = req.config
        self.wave: int | None = req.wave
        self.dry_run: bool = req.dry_run
        self.status: str = "pending"
        self.created_at: datetime = datetime.now(timezone.utc)
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.progress_pct: float = 0.0
        self.agents: dict[str, AgentStatusResponse] = {}
        self.total_items: int = 0
        self.succeeded_items: int = 0
        self.failed_items: int = 0
        self.error: str | None = None
        self.logs: list[LogEntry] = []
        self.inventory_items: list[InventoryItemResponse] = []
        self._cancel_event: asyncio.Event = asyncio.Event()
        self._ws_subscribers: list[asyncio.Queue] = []

    def to_status(self) -> MigrationStatusResponse:
        return MigrationStatusResponse(
            id=self.id,
            name=self.name,
            status=self.status,
            mode=self.mode,
            source_type=self.source_type,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            progress_pct=self.progress_pct,
            agents=list(self.agents.values()),
            total_items=self.total_items,
            succeeded_items=self.succeeded_items,
            failed_items=self.failed_items,
            error=self.error,
        )

    def add_log(self, level: str, message: str, agent_id: str = "") -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            agent_id=agent_id,
            message=message,
        )
        self.logs.append(entry)
        return entry

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Push an event to all WebSocket subscribers."""
        for q in self._ws_subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._ws_subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._ws_subscribers:
            self._ws_subscribers.remove(q)


class MigrationStore:
    """In-memory migration store."""

    def __init__(self) -> None:
        self._migrations: dict[str, MigrationRecord] = {}
        self._start_time: datetime = datetime.now(timezone.utc)

    def create(self, req: MigrationCreateRequest) -> MigrationRecord:
        rec = MigrationRecord(req)
        self._migrations[rec.id] = rec
        return rec

    def get(self, migration_id: str) -> MigrationRecord | None:
        return self._migrations.get(migration_id)

    def list_all(self) -> list[MigrationRecord]:
        return list(self._migrations.values())

    @property
    def active_count(self) -> int:
        return sum(1 for m in self._migrations.values() if m.status in ("pending", "running"))

    @property
    def uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()


# Singleton store
_store = MigrationStore()


def get_store() -> MigrationStore:
    return _store


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------


def create_app() -> Any:
    """Create and configure the FastAPI application.

    Returns the app object. Import FastAPI lazily so the module can be
    imported/tested without the ``fastapi`` package installed.
    """
    try:
        from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import StreamingResponse
    except ImportError:  # pragma: no cover
        raise RuntimeError("FastAPI not installed. Run: pip install fastapi uvicorn")

    app = FastAPI(
        title="OAC-to-Fabric Migration Platform",
        version="2.0.0",
        description="REST + WebSocket API for Oracle Analytics Cloud migration to Microsoft Fabric & Power BI",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- GraphQL (Strawberry) ----
    try:
        from strawberry.fastapi import GraphQLRouter
        from src.api.graphql_schema import get_schema
        from src.api.dataloaders import DataLoaderContext

        def _get_context() -> dict:
            return {"loaders": DataLoaderContext(get_store())}

        graphql_app = GraphQLRouter(get_schema(), context_getter=_get_context)
        app.include_router(graphql_app, prefix="/graphql", tags=["graphql"])
        logger.info("GraphQL endpoint mounted at /graphql")
    except ImportError:
        logger.info("Strawberry not installed — GraphQL endpoint disabled")
    except Exception as exc:
        logger.warning("Failed to mount GraphQL endpoint: %s", exc)

    store = get_store()

    # ---- Health ----
    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    async def health():
        return HealthResponse(
            status="healthy",
            version="2.0.0",
            uptime_seconds=round(store.uptime_seconds, 1),
            migrations_active=store.active_count,
        )

    # ---- Migrations CRUD ----
    @app.post("/migrations", response_model=MigrationStatusResponse, status_code=201, tags=["migrations"])
    async def create_migration(req: MigrationCreateRequest):
        rec = store.create(req)
        rec.add_log("INFO", f"Migration '{rec.name}' created ({rec.mode} mode)")
        return rec.to_status()

    @app.get("/migrations", response_model=list[MigrationStatusResponse], tags=["migrations"])
    async def list_migrations():
        return [r.to_status() for r in store.list_all()]

    @app.get("/migrations/{migration_id}", response_model=MigrationStatusResponse, tags=["migrations"])
    async def get_migration(migration_id: str):
        rec = store.get(migration_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Migration not found")
        return rec.to_status()

    @app.get("/migrations/{migration_id}/inventory", response_model=InventoryResponse, tags=["migrations"])
    async def get_inventory(migration_id: str):
        rec = store.get(migration_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Migration not found")
        return InventoryResponse(
            migration_id=migration_id,
            total=len(rec.inventory_items),
            items=rec.inventory_items,
        )

    @app.get("/migrations/{migration_id}/logs", tags=["migrations"])
    async def get_logs(migration_id: str):
        rec = store.get(migration_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Migration not found")

        async def event_stream():
            for entry in rec.logs:
                yield f"data: {entry.model_dump_json()}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/migrations/{migration_id}/cancel", response_model=CancelResponse, tags=["migrations"])
    async def cancel_migration(migration_id: str):
        rec = store.get(migration_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Migration not found")
        if rec.status in ("completed", "cancelled", "failed"):
            return CancelResponse(
                migration_id=migration_id,
                cancelled=False,
                message=f"Migration already {rec.status}",
            )
        rec._cancel_event.set()
        rec.status = "cancelled"
        rec.completed_at = datetime.now(timezone.utc)
        rec.add_log("WARNING", "Migration cancelled by user")
        return CancelResponse(migration_id=migration_id, cancelled=True, message="Cancellation requested")

    # ---- WebSocket ----
    @app.websocket("/ws/migrations/{migration_id}")
    async def ws_migration(websocket: WebSocket, migration_id: str):
        rec = store.get(migration_id)
        if not rec:
            await websocket.close(code=4004, reason="Migration not found")
            return

        await websocket.accept()
        queue = rec.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    await websocket.send_json(event)
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_json({"type": "ping"})
        except WebSocketDisconnect:
            pass
        finally:
            rec.unsubscribe(queue)

    return app
