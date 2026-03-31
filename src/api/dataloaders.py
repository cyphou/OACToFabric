"""DataLoader implementations for batched N+1 prevention.

Uses the DataLoader pattern to batch and cache lookups within a single
GraphQL request, avoiding the classic N+1 query problem when resolving
nested relationships (e.g. migration → inventory items, migration → logs).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.api.app import MigrationRecord, MigrationStore

logger = logging.getLogger(__name__)


class MigrationLoader:
    """Batch-loads MigrationRecord objects by ID within a single request."""

    def __init__(self, store: "MigrationStore") -> None:
        self._store = store
        self._cache: dict[str, "MigrationRecord | None"] = {}

    def load(self, migration_id: str) -> "MigrationRecord | None":
        if migration_id not in self._cache:
            self._cache[migration_id] = self._store.get(migration_id)
        return self._cache[migration_id]

    def load_many(self, migration_ids: list[str]) -> list["MigrationRecord | None"]:
        return [self.load(mid) for mid in migration_ids]

    def clear(self, migration_id: str | None = None) -> None:
        if migration_id:
            self._cache.pop(migration_id, None)
        else:
            self._cache.clear()


class InventoryLoader:
    """Batch-loads inventory items for a migration."""

    def __init__(self, store: "MigrationStore") -> None:
        self._store = store
        self._cache: dict[str, list] = {}

    def load(self, migration_id: str) -> list:
        if migration_id not in self._cache:
            rec = self._store.get(migration_id)
            self._cache[migration_id] = rec.inventory_items if rec else []
        return self._cache[migration_id]


class LogLoader:
    """Batch-loads log entries for a migration."""

    def __init__(self, store: "MigrationStore") -> None:
        self._store = store
        self._cache: dict[str, list] = {}

    def load(self, migration_id: str) -> list:
        if migration_id not in self._cache:
            rec = self._store.get(migration_id)
            self._cache[migration_id] = rec.logs if rec else []
        return self._cache[migration_id]


class DataLoaderContext:
    """Per-request context holding all DataLoaders.

    Create a new instance for each GraphQL request to ensure
    caching is scoped to a single request lifecycle.
    """

    def __init__(self, store: "MigrationStore") -> None:
        self.migrations = MigrationLoader(store)
        self.inventory = InventoryLoader(store)
        self.logs = LogLoader(store)
