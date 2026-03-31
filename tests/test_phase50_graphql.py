"""Tests for Phase 50: GraphQL API & Federation.

Covers:
- GraphQL type definitions and schema construction
- Query resolvers (health, migrations, migration by ID)
- Mutation resolvers (createMigration, cancelMigration)
- Subscription generators (migrationLogs, migrationEvents)
- Field-level authorization (require_permission, check_field_permission)
- Query complexity / depth limiting
- DataLoader N+1 prevention
- REST + GraphQL coexistence on FastAPI
"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


def _strawberry_available() -> bool:
    try:
        import strawberry  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# DataLoader tests (no strawberry dependency)
# ---------------------------------------------------------------------------


class TestDataLoaderContext(unittest.TestCase):
    """DataLoaderContext — per-request caching for N+1 prevention."""

    def _make_store(self):
        from src.api.app import MigrationCreateRequest, MigrationStore, InventoryItemResponse
        store = MigrationStore()
        req = MigrationCreateRequest(name="test-migration", source_type="oac")
        rec = store.create(req)
        rec.add_log("INFO", "Test log entry", agent_id="discovery")
        rec.add_log("WARNING", "Second log", agent_id="schema")
        rec.inventory_items = [
            InventoryItemResponse(
                id="item-1", asset_type="ANALYSIS", name="Sales Report",
                source_path="/oac/analyses/sales", complexity="Medium",
                migration_status="not-started",
            ),
            InventoryItemResponse(
                id="item-2", asset_type="DASHBOARD", name="Main Dashboard",
                source_path="/oac/dashboards/main", complexity="High",
                migration_status="not-started",
            ),
        ]
        return store, rec

    def test_migration_loader_caches(self):
        from src.api.dataloaders import MigrationLoader
        store, rec = self._make_store()
        loader = MigrationLoader(store)
        r1 = loader.load(rec.id)
        r2 = loader.load(rec.id)
        self.assertIs(r1, r2)

    def test_migration_loader_returns_none_for_missing(self):
        from src.api.dataloaders import MigrationLoader
        store, _ = self._make_store()
        loader = MigrationLoader(store)
        self.assertIsNone(loader.load("nonexistent-id"))

    def test_migration_loader_load_many(self):
        from src.api.dataloaders import MigrationLoader
        store, rec = self._make_store()
        loader = MigrationLoader(store)
        results = loader.load_many([rec.id, "missing"])
        self.assertEqual(len(results), 2)
        self.assertIsNotNone(results[0])
        self.assertIsNone(results[1])

    def test_migration_loader_clear_specific(self):
        from src.api.dataloaders import MigrationLoader
        store, rec = self._make_store()
        loader = MigrationLoader(store)
        loader.load(rec.id)
        self.assertIn(rec.id, loader._cache)
        loader.clear(rec.id)
        self.assertNotIn(rec.id, loader._cache)

    def test_migration_loader_clear_all(self):
        from src.api.dataloaders import MigrationLoader
        store, rec = self._make_store()
        loader = MigrationLoader(store)
        loader.load(rec.id)
        loader.clear()
        self.assertEqual(len(loader._cache), 0)

    def test_inventory_loader(self):
        from src.api.dataloaders import InventoryLoader
        store, rec = self._make_store()
        loader = InventoryLoader(store)
        items = loader.load(rec.id)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].name, "Sales Report")

    def test_inventory_loader_missing(self):
        from src.api.dataloaders import InventoryLoader
        store, _ = self._make_store()
        loader = InventoryLoader(store)
        self.assertEqual(loader.load("nonexistent"), [])

    def test_log_loader(self):
        from src.api.dataloaders import LogLoader
        store, rec = self._make_store()
        loader = LogLoader(store)
        logs = loader.load(rec.id)
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].level, "INFO")

    def test_log_loader_missing(self):
        from src.api.dataloaders import LogLoader
        store, _ = self._make_store()
        loader = LogLoader(store)
        self.assertEqual(loader.load("nonexistent"), [])

    def test_dataloader_context_creates_all_loaders(self):
        from src.api.dataloaders import DataLoaderContext
        store, _ = self._make_store()
        ctx = DataLoaderContext(store)
        self.assertIsNotNone(ctx.migrations)
        self.assertIsNotNone(ctx.inventory)
        self.assertIsNotNone(ctx.logs)

    def test_inventory_loader_caches(self):
        from src.api.dataloaders import InventoryLoader
        store, rec = self._make_store()
        loader = InventoryLoader(store)
        r1 = loader.load(rec.id)
        r2 = loader.load(rec.id)
        self.assertIs(r1, r2)

    def test_log_loader_caches(self):
        from src.api.dataloaders import LogLoader
        store, rec = self._make_store()
        loader = LogLoader(store)
        r1 = loader.load(rec.id)
        r2 = loader.load(rec.id)
        self.assertIs(r1, r2)


# ---------------------------------------------------------------------------
# Query complexity / depth limiting
# ---------------------------------------------------------------------------


class TestQueryComplexity(unittest.TestCase):
    """Query complexity and depth validation."""

    def test_max_query_depth_constant(self):
        from src.api.graphql_schema import MAX_QUERY_DEPTH
        self.assertEqual(MAX_QUERY_DEPTH, 10)

    def test_max_query_complexity_constant(self):
        from src.api.graphql_schema import MAX_QUERY_COMPLEXITY
        self.assertEqual(MAX_QUERY_COMPLEXITY, 500)

    def test_measure_depth_flat_node(self):
        from src.api.graphql_schema import _measure_depth
        node = MagicMock()
        node.selection_set = None
        self.assertEqual(_measure_depth(node), 0)

    def test_measure_depth_nested(self):
        from src.api.graphql_schema import _measure_depth
        leaf = MagicMock()
        leaf.selection_set = None
        mid = MagicMock()
        mid.selection_set.selections = [leaf]
        root = MagicMock()
        root.selection_set.selections = [mid]
        self.assertEqual(_measure_depth(root), 2)

    def test_measure_complexity_single(self):
        from src.api.graphql_schema import _measure_complexity
        node = MagicMock()
        node.selection_set = None
        self.assertEqual(_measure_complexity(node), 1)

    def test_measure_complexity_nested(self):
        from src.api.graphql_schema import _measure_complexity
        leaf = MagicMock()
        leaf.selection_set = None
        mid = MagicMock()
        mid.selection_set.selections = [leaf]
        root = MagicMock()
        root.selection_set.selections = [mid, mid]
        result = _measure_complexity(root)
        self.assertGreater(result, 1)

    def test_validate_no_field_nodes(self):
        from src.api.graphql_schema import validate_query_limits
        info = MagicMock(spec=[])
        validate_query_limits(info)  # should not raise

    def test_validate_excessive_depth_raises(self):
        from src.api.graphql_schema import validate_query_limits, QueryComplexityError, MAX_QUERY_DEPTH

        def build_chain(depth):
            if depth == 0:
                node = MagicMock()
                node.selection_set = None
                return node
            child = build_chain(depth - 1)
            parent = MagicMock()
            parent.selection_set.selections = [child]
            return parent

        deep_node = build_chain(MAX_QUERY_DEPTH + 2)
        info = MagicMock()
        info.field_nodes = [deep_node]
        with self.assertRaises(QueryComplexityError) as ctx:
            validate_query_limits(info)
        self.assertIn("depth", str(ctx.exception))

    def test_error_attributes(self):
        from src.api.graphql_schema import QueryComplexityError
        err = QueryComplexityError("too complex", depth=15, complexity=600)
        self.assertEqual(err.depth, 15)
        self.assertEqual(err.complexity, 600)


# ---------------------------------------------------------------------------
# Field-level authorization
# ---------------------------------------------------------------------------


class TestFieldAuthorization(unittest.TestCase):
    """Field-level authorization utilities."""

    def test_no_claims_allows(self):
        from src.api.graphql_schema import check_field_permission
        info = MagicMock()
        info.context = {}
        self.assertTrue(check_field_permission(info, "migration:read"))

    def test_admin_allowed(self):
        from src.api.graphql_schema import check_field_permission
        from src.api.auth import TokenClaims, PlatformRole
        claims = TokenClaims(sub="user1", roles=[PlatformRole.ADMIN])
        info = MagicMock()
        info.context = {"claims": claims}
        self.assertTrue(check_field_permission(info, "migration:read"))

    def test_viewer_denied_create(self):
        from src.api.graphql_schema import check_field_permission
        from src.api.auth import TokenClaims, PlatformRole
        claims = TokenClaims(sub="user1", roles=[PlatformRole.VIEWER])
        info = MagicMock()
        info.context = {"claims": claims}
        self.assertFalse(check_field_permission(info, "migration:create"))

    def test_require_permission_raises(self):
        from src.api.graphql_schema import require_permission
        from src.api.auth import TokenClaims, PlatformRole
        claims = TokenClaims(sub="user1", roles=[PlatformRole.VIEWER])
        info = MagicMock()
        info.context = {"claims": claims}
        with self.assertRaises(PermissionError):
            require_permission(info, "migration:create")

    def test_require_permission_passes(self):
        from src.api.graphql_schema import require_permission
        from src.api.auth import TokenClaims, PlatformRole
        claims = TokenClaims(sub="user1", roles=[PlatformRole.OPERATOR])
        info = MagicMock()
        info.context = {"claims": claims}
        require_permission(info, "migration:create")  # no raise

    def test_context_as_object(self):
        from src.api.graphql_schema import check_field_permission
        from src.api.auth import TokenClaims, PlatformRole
        claims = TokenClaims(sub="user1", roles=[PlatformRole.ADMIN])
        ctx_obj = MagicMock()
        ctx_obj.claims = claims
        info = MagicMock()
        info.context = ctx_obj
        self.assertTrue(check_field_permission(info, "migration:read"))


# ---------------------------------------------------------------------------
# Schema availability
# ---------------------------------------------------------------------------


class TestSchemaAvailability(unittest.TestCase):

    def test_strawberry_available_flag(self):
        from src.api.graphql_schema import strawberry_available
        result = strawberry_available()
        self.assertIsInstance(result, bool)
        if _strawberry_available():
            self.assertTrue(result)

    @unittest.skipUnless(_strawberry_available(), "strawberry not installed")
    def test_get_schema_returns_schema(self):
        from src.api.graphql_schema import get_schema
        schema = get_schema()
        self.assertIsNotNone(schema)
        self.assertTrue(hasattr(schema, "execute_sync"))

    @unittest.skipUnless(_strawberry_available(), "strawberry not installed")
    def test_get_schema_is_singleton(self):
        from src.api.graphql_schema import get_schema
        s1 = get_schema()
        s2 = get_schema()
        self.assertIs(s1, s2)

    def test_get_schema_raises_when_unavailable(self):
        from src.api import graphql_schema as mod
        old = mod._SCHEMA
        mod._SCHEMA = None
        try:
            with self.assertRaises(RuntimeError):
                mod.get_schema()
        finally:
            mod._SCHEMA = old


# ---------------------------------------------------------------------------
# GraphQL Query resolver tests
# ---------------------------------------------------------------------------


@unittest.skipUnless(_strawberry_available(), "strawberry not installed")
class TestQueryResolvers(unittest.TestCase):

    def _make_store_with_data(self):
        from src.api.app import MigrationCreateRequest, MigrationStore, InventoryItemResponse
        store = MigrationStore()
        req1 = MigrationCreateRequest(name="alpha", source_type="oac")
        rec1 = store.create(req1)
        rec1.add_log("INFO", "Started", agent_id="discovery")
        rec1.inventory_items = [
            InventoryItemResponse(
                id="inv-1", asset_type="ANALYSIS", name="Report A",
                source_path="/a", complexity="Low", migration_status="done",
            ),
        ]
        req2 = MigrationCreateRequest(name="beta", source_type="tableau")
        rec2 = store.create(req2)
        return store, rec1, rec2

    def _make_info(self, context=None):
        info = MagicMock()
        info.context = context or {}
        info.field_nodes = []
        return info

    def test_query_health(self):
        from src.api.graphql_schema import Query
        q = Query()
        info = self._make_info()
        health = q.health(info)
        self.assertEqual(health.status, "healthy")
        self.assertEqual(health.version, "5.0.0")

    def test_query_migrations_list(self):
        from src.api.graphql_schema import Query
        from src.api import app as app_mod
        store, _, _ = self._make_store_with_data()
        old = app_mod._store
        app_mod._store = store
        try:
            q = Query()
            migrations = q.migrations(self._make_info())
            self.assertEqual(len(migrations), 2)
            names = {m.name for m in migrations}
            self.assertIn("alpha", names)
            self.assertIn("beta", names)
        finally:
            app_mod._store = old

    def test_query_migration_by_id_with_loader(self):
        from src.api.graphql_schema import Query
        from src.api.dataloaders import DataLoaderContext
        from src.api import app as app_mod
        store, rec1, _ = self._make_store_with_data()
        old = app_mod._store
        app_mod._store = store
        try:
            q = Query()
            loaders = DataLoaderContext(store)
            migration = q.migration(self._make_info({"loaders": loaders}), id=rec1.id)
            self.assertIsNotNone(migration)
            self.assertEqual(migration.name, "alpha")
        finally:
            app_mod._store = old

    def test_query_migration_by_id_without_loader(self):
        from src.api.graphql_schema import Query
        from src.api import app as app_mod
        store, rec1, _ = self._make_store_with_data()
        old = app_mod._store
        app_mod._store = store
        try:
            q = Query()
            migration = q.migration(self._make_info(), id=rec1.id)
            self.assertIsNotNone(migration)
            self.assertEqual(migration.name, "alpha")
        finally:
            app_mod._store = old

    def test_query_migration_not_found(self):
        from src.api.graphql_schema import Query
        from src.api import app as app_mod
        store, _, _ = self._make_store_with_data()
        old = app_mod._store
        app_mod._store = store
        try:
            q = Query()
            self.assertIsNone(q.migration(self._make_info(), id="nonexistent"))
        finally:
            app_mod._store = old


# ---------------------------------------------------------------------------
# Mutation resolver tests
# ---------------------------------------------------------------------------


@unittest.skipUnless(_strawberry_available(), "strawberry not installed")
class TestMutationResolvers(unittest.TestCase):

    def _make_info(self, context=None):
        info = MagicMock()
        info.context = context or {}
        info.field_nodes = []
        return info

    def test_create_migration(self):
        from src.api.graphql_schema import Mutation, MigrationCreateInput, GQLMigrationMode
        from src.api import app as app_mod
        from src.api.app import MigrationStore
        store = MigrationStore()
        old = app_mod._store
        app_mod._store = store
        try:
            m = Mutation()
            inp = MigrationCreateInput(
                name="new-mig", source_type="obiee",
                mode=GQLMigrationMode.INCREMENTAL, wave=2, dry_run=True,
            )
            result = m.create_migration(self._make_info(), input=inp)
            self.assertEqual(result.name, "new-mig")
            self.assertEqual(result.source_type, "obiee")
            self.assertEqual(result.mode, "incremental")
            self.assertEqual(len(store.list_all()), 1)
        finally:
            app_mod._store = old

    def test_cancel_migration(self):
        from src.api.graphql_schema import Mutation
        from src.api import app as app_mod
        from src.api.app import MigrationCreateRequest, MigrationStore
        store = MigrationStore()
        rec = store.create(MigrationCreateRequest(name="cancel-me"))
        rec.status = "running"
        old = app_mod._store
        app_mod._store = store
        try:
            m = Mutation()
            cancel = m.cancel_migration(self._make_info(), migration_id=rec.id)
            self.assertTrue(cancel.cancelled)
            self.assertEqual(rec.status, "cancelled")
        finally:
            app_mod._store = old

    def test_cancel_already_completed(self):
        from src.api.graphql_schema import Mutation
        from src.api import app as app_mod
        from src.api.app import MigrationCreateRequest, MigrationStore
        store = MigrationStore()
        rec = store.create(MigrationCreateRequest(name="done"))
        rec.status = "completed"
        old = app_mod._store
        app_mod._store = store
        try:
            m = Mutation()
            cancel = m.cancel_migration(self._make_info(), migration_id=rec.id)
            self.assertFalse(cancel.cancelled)
            self.assertIn("already completed", cancel.message)
        finally:
            app_mod._store = old

    def test_cancel_not_found(self):
        from src.api.graphql_schema import Mutation
        from src.api import app as app_mod
        from src.api.app import MigrationStore
        old = app_mod._store
        app_mod._store = MigrationStore()
        try:
            m = Mutation()
            cancel = m.cancel_migration(self._make_info(), migration_id="nope")
            self.assertFalse(cancel.cancelled)
            self.assertIn("not found", cancel.message)
        finally:
            app_mod._store = old


# ---------------------------------------------------------------------------
# Subscription tests
# ---------------------------------------------------------------------------


@unittest.skipUnless(_strawberry_available(), "strawberry not installed")
class TestSubscriptions(unittest.TestCase):

    def _make_info(self):
        info = MagicMock()
        info.context = {}
        return info

    def test_subscription_migration_logs(self):
        from src.api.graphql_schema import Subscription
        from src.api import app as app_mod
        from src.api.app import MigrationCreateRequest, MigrationStore

        store = MigrationStore()
        rec = store.create(MigrationCreateRequest(name="sub-test"))
        rec.add_log("INFO", "Started", agent_id="discovery")
        rec.status = "completed"

        old = app_mod._store
        app_mod._store = store
        try:
            s = Subscription()

            async def collect():
                entries = []
                async for entry in s.migration_logs(self._make_info(), migration_id=rec.id):
                    entries.append(entry)
                return entries

            loop = asyncio.new_event_loop()
            try:
                entries = loop.run_until_complete(collect())
            finally:
                loop.close()
            self.assertGreater(len(entries), 0)
            self.assertEqual(entries[0].message, "Started")
        finally:
            app_mod._store = old

    def test_subscription_logs_not_found(self):
        from src.api.graphql_schema import Subscription
        from src.api import app as app_mod
        from src.api.app import MigrationStore

        old = app_mod._store
        app_mod._store = MigrationStore()
        try:
            s = Subscription()

            async def collect():
                entries = []
                async for entry in s.migration_logs(self._make_info(), migration_id="missing"):
                    entries.append(entry)
                return entries

            loop = asyncio.new_event_loop()
            try:
                entries = loop.run_until_complete(collect())
            finally:
                loop.close()
            self.assertEqual(len(entries), 0)
        finally:
            app_mod._store = old

    def test_subscription_events_not_found(self):
        from src.api.graphql_schema import Subscription
        from src.api import app as app_mod
        from src.api.app import MigrationStore

        old = app_mod._store
        app_mod._store = MigrationStore()
        try:
            s = Subscription()

            async def collect():
                entries = []
                async for entry in s.migration_events(self._make_info(), migration_id="missing"):
                    entries.append(entry)
                return entries

            loop = asyncio.new_event_loop()
            try:
                entries = loop.run_until_complete(collect())
            finally:
                loop.close()
            self.assertEqual(len(entries), 0)
        finally:
            app_mod._store = old


# ---------------------------------------------------------------------------
# Migration type field resolver tests
# ---------------------------------------------------------------------------


@unittest.skipUnless(_strawberry_available(), "strawberry not installed")
class TestMigrationTypeResolvers(unittest.TestCase):

    def test_inventory_field(self):
        from src.api.graphql_schema import Migration
        from src.api.dataloaders import DataLoaderContext
        from src.api import app as app_mod
        from src.api.app import MigrationCreateRequest, MigrationStore, InventoryItemResponse

        store = MigrationStore()
        rec = store.create(MigrationCreateRequest(name="test"))
        rec.inventory_items = [
            InventoryItemResponse(
                id="i1", asset_type="ANALYSIS", name="A",
                source_path="/a", complexity="Low", migration_status="done",
            ),
        ]
        old = app_mod._store
        app_mod._store = store
        try:
            loaders = DataLoaderContext(store)
            info = MagicMock()
            info.context = {"loaders": loaders}
            mig = Migration(
                id=rec.id, name="test", status="running", mode="full",
                source_type="oac", created_at=rec.created_at,
                started_at=None, completed_at=None, progress_pct=0.0,
                total_items=1, succeeded_items=0, failed_items=0, error=None,
            )
            items = mig.inventory(info)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].name, "A")
        finally:
            app_mod._store = old

    def test_logs_field_with_limit(self):
        from src.api.graphql_schema import Migration
        from src.api.dataloaders import DataLoaderContext
        from src.api import app as app_mod
        from src.api.app import MigrationCreateRequest, MigrationStore

        store = MigrationStore()
        rec = store.create(MigrationCreateRequest(name="test"))
        for i in range(10):
            rec.add_log("INFO", f"Log entry {i}")
        old = app_mod._store
        app_mod._store = store
        try:
            loaders = DataLoaderContext(store)
            info = MagicMock()
            info.context = {"loaders": loaders}
            mig = Migration(
                id=rec.id, name="test", status="running", mode="full",
                source_type="oac", created_at=rec.created_at,
                started_at=None, completed_at=None, progress_pct=0.0,
                total_items=0, succeeded_items=0, failed_items=0, error=None,
            )
            logs = mig.logs(info, limit=3)
            self.assertEqual(len(logs), 3)
        finally:
            app_mod._store = old

    def test_agents_field(self):
        from src.api.graphql_schema import Migration
        from src.api.dataloaders import DataLoaderContext
        from src.api import app as app_mod
        from src.api.app import AgentStatusResponse, MigrationCreateRequest, MigrationStore

        store = MigrationStore()
        rec = store.create(MigrationCreateRequest(name="test"))
        rec.agents["discovery"] = AgentStatusResponse(
            agent_id="discovery", state="running", items_processed=5,
        )
        old = app_mod._store
        app_mod._store = store
        try:
            loaders = DataLoaderContext(store)
            info = MagicMock()
            info.context = {"loaders": loaders}
            mig = Migration(
                id=rec.id, name="test", status="running", mode="full",
                source_type="oac", created_at=rec.created_at,
                started_at=None, completed_at=None, progress_pct=0.0,
                total_items=0, succeeded_items=0, failed_items=0, error=None,
            )
            agents = mig.agents(info)
            self.assertEqual(len(agents), 1)
            self.assertEqual(agents[0].agent_id, "discovery")
        finally:
            app_mod._store = old

    def test_fields_no_loader_return_empty(self):
        from src.api.graphql_schema import Migration
        info = MagicMock()
        info.context = {}
        mig = Migration(
            id="x", name="test", status="running", mode="full",
            source_type="oac", created_at=datetime.now(timezone.utc),
            started_at=None, completed_at=None, progress_pct=0.0,
            total_items=0, succeeded_items=0, failed_items=0, error=None,
        )
        self.assertEqual(mig.inventory(info), [])
        self.assertEqual(mig.logs(info), [])
        self.assertEqual(mig.agents(info), [])


# ---------------------------------------------------------------------------
# REST + GraphQL coexistence
# ---------------------------------------------------------------------------


@unittest.skipUnless(_strawberry_available(), "strawberry not installed")
class TestRESTGraphQLCoexistence(unittest.TestCase):

    def test_create_app_has_graphql_route(self):
        try:
            from fastapi import FastAPI  # noqa: F401
        except ImportError:
            self.skipTest("FastAPI not installed")

        from src.api.app import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        self.assertIn("/health", routes)
        self.assertIn("/migrations", routes)
        self.assertIn("/graphql", routes)


# ---------------------------------------------------------------------------
# Schema execution (integration-level)
# ---------------------------------------------------------------------------


@unittest.skipUnless(_strawberry_available(), "strawberry not installed")
class TestSchemaExecution(unittest.TestCase):

    def test_health_query(self):
        from src.api.graphql_schema import get_schema
        schema = get_schema()
        result = schema.execute_sync(
            "{ health { status version migrationsActive } }",
            context_value={},
        )
        self.assertIsNone(result.errors)
        self.assertEqual(result.data["health"]["status"], "healthy")
        self.assertEqual(result.data["health"]["version"], "5.0.0")

    def test_create_mutation(self):
        from src.api.graphql_schema import get_schema
        from src.api import app as app_mod
        from src.api.app import MigrationStore
        store = MigrationStore()
        old = app_mod._store
        app_mod._store = store
        try:
            schema = get_schema()
            mutation = """
            mutation {
                createMigration(input: {
                    name: "gql-test"
                    sourceType: "oac"
                    mode: FULL
                    dryRun: false
                }) {
                    id name status mode
                }
            }
            """
            resp = schema.execute_sync(mutation, context_value={})
            self.assertIsNone(resp.errors)
            self.assertEqual(resp.data["createMigration"]["name"], "gql-test")
            self.assertEqual(resp.data["createMigration"]["mode"], "full")
            self.assertEqual(len(store.list_all()), 1)
        finally:
            app_mod._store = old

    def test_migrations_query(self):
        from src.api.graphql_schema import get_schema
        from src.api.dataloaders import DataLoaderContext
        from src.api import app as app_mod
        from src.api.app import MigrationCreateRequest, MigrationStore

        store = MigrationStore()
        store.create(MigrationCreateRequest(name="m1", source_type="oac"))
        store.create(MigrationCreateRequest(name="m2", source_type="tableau"))

        old = app_mod._store
        app_mod._store = store
        try:
            schema = get_schema()
            loaders = DataLoaderContext(store)
            resp = schema.execute_sync(
                "{ migrations { id name sourceType status } }",
                context_value={"loaders": loaders},
            )
            self.assertIsNone(resp.errors)
            self.assertEqual(len(resp.data["migrations"]), 2)
        finally:
            app_mod._store = old

    def test_cancel_mutation(self):
        from src.api.graphql_schema import get_schema
        from src.api import app as app_mod
        from src.api.app import MigrationCreateRequest, MigrationStore

        store = MigrationStore()
        rec = store.create(MigrationCreateRequest(name="cancel-me"))
        rec.status = "running"

        old = app_mod._store
        app_mod._store = store
        try:
            schema = get_schema()
            resp = schema.execute_sync(
                f'mutation {{ cancelMigration(migrationId: "{rec.id}") {{ migrationId cancelled message }} }}',
                context_value={},
            )
            self.assertIsNone(resp.errors)
            self.assertTrue(resp.data["cancelMigration"]["cancelled"])
        finally:
            app_mod._store = old

    def test_auth_denied_on_mutation(self):
        from src.api.graphql_schema import get_schema
        from src.api import app as app_mod
        from src.api.app import MigrationStore
        from src.api.auth import TokenClaims, PlatformRole

        old = app_mod._store
        app_mod._store = MigrationStore()
        try:
            schema = get_schema()
            claims = TokenClaims(sub="viewer", roles=[PlatformRole.VIEWER])
            resp = schema.execute_sync(
                'mutation { createMigration(input: { name: "should-fail" }) { id name } }',
                context_value={"claims": claims},
            )
            self.assertIsNotNone(resp.errors)
            self.assertGreater(len(resp.errors), 0)
        finally:
            app_mod._store = old

    def test_migration_by_id_query(self):
        from src.api.graphql_schema import get_schema
        from src.api.dataloaders import DataLoaderContext
        from src.api import app as app_mod
        from src.api.app import MigrationCreateRequest, MigrationStore

        store = MigrationStore()
        rec = store.create(MigrationCreateRequest(name="lookup"))
        old = app_mod._store
        app_mod._store = store
        try:
            schema = get_schema()
            loaders = DataLoaderContext(store)
            resp = schema.execute_sync(
                f'{{ migration(id: "{rec.id}") {{ id name status }} }}',
                context_value={"loaders": loaders},
            )
            self.assertIsNone(resp.errors)
            self.assertEqual(resp.data["migration"]["name"], "lookup")
        finally:
            app_mod._store = old


# ---------------------------------------------------------------------------
# GQL type field shapes
# ---------------------------------------------------------------------------


@unittest.skipUnless(_strawberry_available(), "strawberry not installed")
class TestGQLTypeShapes(unittest.TestCase):

    def test_health_status(self):
        from src.api.graphql_schema import HealthStatus
        h = HealthStatus(status="ok", version="1.0", uptime_seconds=10.0, migrations_active=0)
        self.assertEqual(h.status, "ok")

    def test_cancel_result(self):
        from src.api.graphql_schema import CancelResult
        c = CancelResult(migration_id="abc", cancelled=True, message="done")
        self.assertTrue(c.cancelled)

    def test_inventory_item(self):
        from src.api.graphql_schema import InventoryItem
        item = InventoryItem(
            id="x", asset_type="ANALYSIS", name="N",
            source_path="/p", complexity="Low", migration_status="done",
        )
        self.assertEqual(item.asset_type, "ANALYSIS")

    def test_log_entry(self):
        from src.api.graphql_schema import LogEntry
        le = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level="INFO", agent_id="etl", message="hi",
        )
        self.assertEqual(le.level, "INFO")

    def test_agent_status(self):
        from src.api.graphql_schema import AgentStatus
        a = AgentStatus(
            agent_id="discovery", state="running",
            items_processed=5, items_failed=1,
            started_at=None, completed_at=None,
        )
        self.assertEqual(a.agent_id, "discovery")

    def test_migration_mode_enum(self):
        from src.api.graphql_schema import GQLMigrationMode
        self.assertEqual(GQLMigrationMode.FULL.value, "full")
        self.assertEqual(GQLMigrationMode.INCREMENTAL.value, "incremental")


if __name__ == "__main__":
    unittest.main()
