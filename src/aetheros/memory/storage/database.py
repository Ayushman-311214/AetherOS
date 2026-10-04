"""
SQLite connection management and migration runner (spec Phase 2).

A thin, synchronous wrapper around a single :mod:`sqlite3` connection, guarded by
a re-entrant lock. The connection is opened with ``check_same_thread=False`` so
the async repository can drive it from an :func:`asyncio.to_thread` worker, and
the lock serialises access -- SQLite's own connection object is not safe for
concurrent use even then.

Why one shared connection rather than a pool: the memory DB is low-contention
(an interactive agent, not a web service), WAL mode gives us concurrent readers
anyway, and a single connection is what lets a ``:memory:`` database survive for
the lifetime of a test. The async surface (not raw threads everywhere) is in the
repository, which owns the ``to_thread`` boundary.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from ...core.errors.memory_error import MemoryStorageError
from ...core.logging import get_logger
from .schema import MIGRATIONS

logger = get_logger("memory.storage")


class SQLiteDatabase:
    """Owns the SQLite connection and keeps the schema migrated."""

    def __init__(self, path: str | Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the connection (idempotent) and bring the schema up to date."""
        with self._lock:
            if self._conn is not None:
                return

            path = self._path
            is_memory = str(path) == ":memory:"
            if not is_memory:
                p = Path(path)
                p.parent.mkdir(parents=True, exist_ok=True)
                path = str(p)
            else:
                path = ":memory:"

            try:
                conn = sqlite3.connect(path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                # WAL is a file-only feature; harmless to skip for :memory:.
                if not is_memory:
                    conn.execute("PRAGMA journal_mode = WAL")
                self._conn = conn
            except sqlite3.Error as exc:  # pragma: no cover - construction failure
                raise MemoryStorageError(
                    f"Could not open the memory database at {path!r}.",
                    hint="Check the path is writable and DATA_DIR exists.",
                    cause=exc,
                ) from exc

            self._run_migrations()

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def _require(self) -> sqlite3.Connection:
        if self._conn is None:
            raise MemoryStorageError(
                "The memory database is not connected.",
                hint="Call connect() (the MemoryManager does this on initialize).",
            )
        return self._conn

    # ------------------------------------------------------------------
    # Migrations
    # ------------------------------------------------------------------

    def _run_migrations(self) -> None:
        conn = self._require()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations"
        ).fetchone()
        current = int(row["v"]) if row else 0

        for version, statements in MIGRATIONS:
            if version <= current:
                continue
            try:
                for stmt in statements:
                    conn.execute(stmt)
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (version,),
                )
                conn.commit()
                logger.bind(version=version).info("Applied memory migration.")
            except sqlite3.Error as exc:
                conn.rollback()
                raise MemoryStorageError(
                    f"Memory migration {version} failed.",
                    cause=exc,
                ) from exc

    def schema_version(self) -> int:
        with self._lock:
            conn = self._require()
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations"
            ).fetchone()
            return int(row["v"]) if row else 0

    # ------------------------------------------------------------------
    # Query helpers (synchronous; the repository owns the async boundary)
    # ------------------------------------------------------------------

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        with self._lock:
            conn = self._require()
            try:
                conn.execute(sql, params)
                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                raise MemoryStorageError("Memory write failed.", cause=exc) from exc

    def execute_many(self, sql: str, rows: Iterable[Sequence[Any]]) -> None:
        with self._lock:
            conn = self._require()
            try:
                conn.executemany(sql, list(rows))
                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                raise MemoryStorageError("Memory batch write failed.", cause=exc) from exc

    def execute_script(self, statements: Iterable[tuple[str, Sequence[Any]]]) -> None:
        """Run several (sql, params) statements in one committed transaction."""
        with self._lock:
            conn = self._require()
            try:
                for sql, params in statements:
                    conn.execute(sql, params)
                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                raise MemoryStorageError("Memory transaction failed.", cause=exc) from exc

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        with self._lock:
            conn = self._require()
            try:
                return conn.execute(sql, params).fetchone()
            except sqlite3.Error as exc:
                raise MemoryStorageError("Memory read failed.", cause=exc) from exc

    def query_all(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            conn = self._require()
            try:
                return list(conn.execute(sql, params).fetchall())
            except sqlite3.Error as exc:
                raise MemoryStorageError("Memory read failed.", cause=exc) from exc
