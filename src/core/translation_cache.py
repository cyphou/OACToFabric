"""Translation cache — deterministic-hit SQLite cache for LLM translations.

Stores prompt→response mappings keyed by SHA-256 hash of
(system_prompt, user_prompt).  Supports TTL-based expiration.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry."""

    key: str
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    created_at: float = 0.0
    ttl_seconds: int = 0  # 0 = never expires

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return time.time() > self.created_at + self.ttl_seconds


@dataclass
class TranslationCache:
    """SQLite-backed translation cache.

    Parameters
    ----------
    db_path
        Path to the SQLite database file.  Use ``:memory:`` for testing.
    default_ttl
        Default TTL in seconds for cache entries (0 = never expire).
    """

    db_path: str = ":memory:"
    default_ttl: int = 0
    _conn: sqlite3.Connection | None = field(default=None, init=False, repr=False)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._create_tables()
        return self._conn

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                key TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                model TEXT DEFAULT '',
                created_at REAL NOT NULL,
                ttl_seconds INTEGER DEFAULT 0
            )
        """)
        self._conn.commit()

    @staticmethod
    def make_key(system_prompt: str, user_prompt: str) -> str:
        raw = f"{system_prompt}||{user_prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, system_prompt: str, user_prompt: str) -> CacheEntry | None:
        """Look up a cached translation.  Returns None on miss or expiry."""
        conn = self._get_conn()
        key = self.make_key(system_prompt, user_prompt)
        row = conn.execute(
            "SELECT key, content, prompt_tokens, completion_tokens, model, created_at, ttl_seconds "
            "FROM translations WHERE key = ?",
            (key,),
        ).fetchone()

        if row is None:
            return None

        entry = CacheEntry(
            key=row[0],
            content=row[1],
            prompt_tokens=row[2],
            completion_tokens=row[3],
            model=row[4],
            created_at=row[5],
            ttl_seconds=row[6],
        )

        if entry.is_expired:
            self.delete(key)
            return None

        return entry

    def put(
        self,
        system_prompt: str,
        user_prompt: str,
        content: str,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: str = "",
        ttl_seconds: int | None = None,
    ) -> str:
        """Store a translation in the cache.  Returns the cache key."""
        conn = self._get_conn()
        key = self.make_key(system_prompt, user_prompt)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        conn.execute(
            """
            INSERT OR REPLACE INTO translations
            (key, content, prompt_tokens, completion_tokens, model, created_at, ttl_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (key, content, prompt_tokens, completion_tokens, model, time.time(), ttl),
        )
        conn.commit()
        return key

    def delete(self, key: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM translations WHERE key = ?", (key,))
        conn.commit()

    def count(self) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM translations").fetchone()
        return row[0] if row else 0

    def clear(self) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM translations")
        conn.commit()

    def cleanup_expired(self) -> int:
        """Remove all expired entries.  Returns count of removed entries."""
        conn = self._get_conn()
        now = time.time()
        cursor = conn.execute(
            "DELETE FROM translations WHERE ttl_seconds > 0 AND (created_at + ttl_seconds) < ?",
            (now,),
        )
        conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
        models = conn.execute(
            "SELECT model, COUNT(*) FROM translations GROUP BY model"
        ).fetchall()
        return {
            "total_entries": total,
            "models": {m: c for m, c in models},
        }
