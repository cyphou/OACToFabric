"""GraphQL schema for the OAC-to-Fabric migration platform.

Built with Strawberry GraphQL and integrated alongside the existing
REST + WebSocket API on FastAPI.

Features:
- Full query API mirroring REST endpoints
- Mutations for migration lifecycle
- Real-time subscriptions via WebSocket transport
- Field-level authorization via require_permission()
- Query complexity/depth limiting
- DataLoader pattern for N+1 prevention
"""

from __future__ import annotations

import asyncio
import enum
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Query complexity / depth validation
# ---------------------------------------------------------------------------


MAX_QUERY_DEPTH = 10
MAX_QUERY_COMPLEXITY = 500


class QueryComplexityError(Exception):
    """Raised when a query exceeds complexity or depth limits."""

    def __init__(self, message: str, depth: int = 0, complexity: int = 0) -> None:
        self.depth = depth
        self.complexity = complexity
        super().__init__(message)


def _measure_depth(node: Any, current: int = 0) -> int:
    """Recursively measure the depth of a GraphQL selection set."""
    if not hasattr(node, "selection_set") or node.selection_set is None:
        return current
    max_child = current
    for selection in node.selection_set.selections:
        child_depth = _measure_depth(selection, current + 1)
        if child_depth > max_child:
            max_child = child_depth
    return max_child


def _measure_complexity(node: Any, multiplier: int = 1) -> int:
    """Estimate query complexity based on field count x nesting multiplier."""
    if not hasattr(node, "selection_set") or node.selection_set is None:
        return multiplier
    total = 0
    for selection in node.selection_set.selections:
        total += _measure_complexity(selection, multiplier * 1)
        total += multiplier
    return total


def validate_query_limits(info: Any) -> None:
    """Validate that the query does not exceed depth/complexity limits."""
    if not hasattr(info, "field_nodes"):
        return
    for node in info.field_nodes:
        depth = _measure_depth(node)
        if depth > MAX_QUERY_DEPTH:
            raise QueryComplexityError(
                f"Query depth {depth} exceeds maximum allowed depth of {MAX_QUERY_DEPTH}",
                depth=depth,
            )
        complexity = _measure_complexity(node)
        if complexity > MAX_QUERY_COMPLEXITY:
            raise QueryComplexityError(
                f"Query complexity {complexity} exceeds maximum of {MAX_QUERY_COMPLEXITY}",
                complexity=complexity,
            )


# ---------------------------------------------------------------------------
# Field-level authorization
# ---------------------------------------------------------------------------


def check_field_permission(info: Any, permission: str) -> bool:
    """Check if the current user has the required permission."""
    context = info.context
    claims = context.get("claims") if isinstance(context, dict) else getattr(context, "claims", None)
    if claims is None:
        return True
    return claims.has_permission(permission)


def require_permission(info: Any, permission: str) -> None:
    """Raise PermissionError if the user lacks the required permission."""
    if not check_field_permission(info, permission):
        raise PermissionError(f"Missing required permission: {permission}")


# ---------------------------------------------------------------------------
# Strawberry types — module-level (required by strawberry's type resolver)
# ---------------------------------------------------------------------------

try:
    import strawberry

    @strawberry.enum
    class GQLMigrationMode(enum.Enum):
        FULL = "full"
        INCREMENTAL = "incremental"

    @strawberry.type
    class AgentStatus:
        agent_id: str
        state: str
        items_processed: int
        items_failed: int
        started_at: Optional[datetime]
        completed_at: Optional[datetime]

    @strawberry.type
    class InventoryItem:
        id: str
        asset_type: str
        name: str
        source_path: str
        complexity: str
        migration_status: str

    @strawberry.type
    class LogEntry:
        timestamp: datetime
        level: str
        agent_id: str
        message: str

    @strawberry.type
    class HealthStatus:
        status: str
        version: str
        uptime_seconds: float
        migrations_active: int

    @strawberry.type
    class CancelResult:
        migration_id: str
        cancelled: bool
        message: str

    @strawberry.input
    class MigrationCreateInput:
        name: str
        source_type: str = "oac"
        mode: GQLMigrationMode = GQLMigrationMode.FULL
        wave: Optional[int] = None
        dry_run: bool = False

    @strawberry.type
    class Migration:
        id: str
        name: str
        status: str
        mode: str
        source_type: str
        created_at: datetime
        started_at: Optional[datetime]
        completed_at: Optional[datetime]
        progress_pct: float
        total_items: int
        succeeded_items: int
        failed_items: int
        error: Optional[str]

        @strawberry.field
        def agents(self, info: strawberry.types.Info) -> list[AgentStatus]:
            require_permission(info, "migration:read")
            ctx = info.context
            loader = ctx.get("loaders") if isinstance(ctx, dict) else getattr(ctx, "loaders", None)
            if loader:
                rec = loader.migrations.load(self.id)
                if rec:
                    return [
                        AgentStatus(
                            agent_id=a.agent_id, state=a.state,
                            items_processed=a.items_processed,
                            items_failed=a.items_failed,
                            started_at=a.started_at,
                            completed_at=a.completed_at,
                        )
                        for a in rec.agents.values()
                    ]
            return []

        @strawberry.field
        def inventory(self, info: strawberry.types.Info) -> list[InventoryItem]:
            require_permission(info, "migration:read")
            ctx = info.context
            loader = ctx.get("loaders") if isinstance(ctx, dict) else getattr(ctx, "loaders", None)
            if loader:
                items = loader.inventory.load(self.id)
                return [
                    InventoryItem(
                        id=i.id, asset_type=i.asset_type, name=i.name,
                        source_path=i.source_path, complexity=i.complexity,
                        migration_status=i.migration_status,
                    )
                    for i in items
                ]
            return []

        @strawberry.field
        def logs(self, info: strawberry.types.Info, limit: int = 100) -> list[LogEntry]:
            require_permission(info, "migration:read")
            ctx = info.context
            loader = ctx.get("loaders") if isinstance(ctx, dict) else getattr(ctx, "loaders", None)
            if loader:
                entries = loader.logs.load(self.id)
                return [
                    LogEntry(
                        timestamp=e.timestamp, level=e.level,
                        agent_id=e.agent_id, message=e.message,
                    )
                    for e in entries[:limit]
                ]
            return []

    def _record_to_gql(rec) -> Migration:
        return Migration(
            id=rec.id, name=rec.name, status=rec.status,
            mode=rec.mode, source_type=rec.source_type,
            created_at=rec.created_at, started_at=rec.started_at,
            completed_at=rec.completed_at, progress_pct=rec.progress_pct,
            total_items=rec.total_items, succeeded_items=rec.succeeded_items,
            failed_items=rec.failed_items, error=rec.error,
        )

    @strawberry.type
    class Query:
        @strawberry.field
        def health(self, info: strawberry.types.Info) -> HealthStatus:
            from src.api.app import get_store
            store = get_store()
            return HealthStatus(
                status="healthy", version="5.0.0",
                uptime_seconds=round(store.uptime_seconds, 1),
                migrations_active=store.active_count,
            )

        @strawberry.field
        def migrations(self, info: strawberry.types.Info) -> list[Migration]:
            require_permission(info, "migration:read")
            validate_query_limits(info)
            from src.api.app import get_store
            store = get_store()
            return [_record_to_gql(r) for r in store.list_all()]

        @strawberry.field
        def migration(self, info: strawberry.types.Info, id: str) -> Optional[Migration]:
            require_permission(info, "migration:read")
            validate_query_limits(info)
            ctx = info.context
            loader = ctx.get("loaders") if isinstance(ctx, dict) else getattr(ctx, "loaders", None)
            if loader:
                rec = loader.migrations.load(id)
            else:
                from src.api.app import get_store
                store = get_store()
                rec = store.get(id)
            if rec is None:
                return None
            return _record_to_gql(rec)

    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def create_migration(self, info: strawberry.types.Info, input: MigrationCreateInput) -> Migration:
            require_permission(info, "migration:create")
            from src.api.app import MigrationCreateRequest, MigrationMode, get_store
            store = get_store()
            req = MigrationCreateRequest(
                name=input.name, source_type=input.source_type,
                mode=MigrationMode(input.mode.value),
                wave=input.wave, dry_run=input.dry_run,
            )
            rec = store.create(req)
            rec.add_log("INFO", f"Migration '{rec.name}' created via GraphQL ({rec.mode} mode)")
            return _record_to_gql(rec)

        @strawberry.mutation
        def cancel_migration(self, info: strawberry.types.Info, migration_id: str) -> CancelResult:
            require_permission(info, "migration:cancel")
            from src.api.app import get_store
            store = get_store()
            rec = store.get(migration_id)
            if rec is None:
                return CancelResult(
                    migration_id=migration_id, cancelled=False,
                    message="Migration not found",
                )
            if rec.status in ("completed", "cancelled", "failed"):
                return CancelResult(
                    migration_id=migration_id, cancelled=False,
                    message=f"Migration already {rec.status}",
                )
            rec._cancel_event.set()
            rec.status = "cancelled"
            rec.completed_at = datetime.now(timezone.utc)
            rec.add_log("WARNING", "Migration cancelled via GraphQL")
            return CancelResult(
                migration_id=migration_id, cancelled=True,
                message="Cancellation requested",
            )

    @strawberry.type
    class Subscription:
        @strawberry.subscription
        async def migration_logs(
            self, info: strawberry.types.Info, migration_id: str
        ) -> AsyncGenerator[LogEntry, None]:
            from src.api.app import get_store
            store = get_store()
            rec = store.get(migration_id)
            if rec is None:
                return

            for entry in rec.logs:
                yield LogEntry(
                    timestamp=entry.timestamp, level=entry.level,
                    agent_id=entry.agent_id, message=entry.message,
                )

            last_count = len(rec.logs)
            while rec.status not in ("completed", "cancelled", "failed"):
                await asyncio.sleep(1.0)
                current = rec.logs[last_count:]
                for entry in current:
                    yield LogEntry(
                        timestamp=entry.timestamp, level=entry.level,
                        agent_id=entry.agent_id, message=entry.message,
                    )
                last_count = len(rec.logs)

        @strawberry.subscription
        async def migration_events(
            self, info: strawberry.types.Info, migration_id: str
        ) -> AsyncGenerator[str, None]:
            from src.api.app import get_store
            import json
            store = get_store()
            rec = store.get(migration_id)
            if rec is None:
                return

            queue = rec.subscribe()
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield json.dumps(event)
                    except asyncio.TimeoutError:
                        yield '{"type": "ping"}'
            finally:
                rec.unsubscribe(queue)

    _SCHEMA = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        subscription=Subscription,
    )

    _STRAWBERRY_AVAILABLE = True

except ImportError:
    _STRAWBERRY_AVAILABLE = False
    _SCHEMA = None

    # Placeholder classes so code can reference names without strawberry
    class GQLMigrationMode(enum.Enum):  # type: ignore[no-redef]
        FULL = "full"
        INCREMENTAL = "incremental"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def strawberry_available() -> bool:
    """Check if strawberry-graphql is installed."""
    return _STRAWBERRY_AVAILABLE


def get_schema():
    """Get the Strawberry schema (raises if strawberry not installed)."""
    if _SCHEMA is None:
        raise RuntimeError(
            "Strawberry GraphQL not installed. Run: pip install strawberry-graphql[fastapi]"
        )
    return _SCHEMA
