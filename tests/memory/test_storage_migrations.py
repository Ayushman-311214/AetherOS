"""
Phase 2 persistence & migration acceptance tests.

These exercise the storage-layer behaviours the Phase 2 contract requires that
the existing ``test_memory_storage.py`` did not cover: fresh installation,
upgrade from an older schema version, transaction rollback, constraint / foreign
-key cascade enforcement, repeated (idempotent) migration invocation, concurrent
cross-connection access with the bounded busy timeout, close/reopen and restart
persistence, native backup/recovery, and proof that representative records
survive a migration without loss.

Every test uses an isolated temporary database (``tmp_path``) or ``:memory:`` --
never a real user database.
"""

from __future__ import annotations

import sqlite3
import threading

import pytest

from aetheros.core.errors.memory_error import MemoryStorageError
from aetheros.memory.domain import (
    Memory,
    MemorySource,
    MemoryType,
    SourceType,
    Veracity,
)
from aetheros.memory.storage import LATEST_VERSION, MemoryRepository, SQLiteDatabase
from aetheros.memory.storage.schema import MIGRATIONS


# ----------------------------------------------------------------------
# Fresh installation
# ----------------------------------------------------------------------


def test_fresh_install_creates_latest_schema(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "fresh.db")
    db.connect()
    try:
        assert db.schema_version() == LATEST_VERSION
        # Every table named in the migrations is present.
        rows = db.query_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        names = {r["name"] for r in rows}
        for expected in (
            "memory_items",
            "memory_embeddings",
            "memory_links",
            "memory_tags",
            "memory_entities",
            "entities",
            "relationships",
            "memory_access",
            "schema_migrations",
        ):
            assert expected in names
    finally:
        db.close()


def test_fresh_install_sets_pragmas(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "pragmas.db", busy_timeout_ms=1234)
    db.connect()
    try:
        assert db.query_one("PRAGMA foreign_keys")[0] == 1
        assert db.query_one("PRAGMA busy_timeout")[0] == 1234
        assert str(db.query_one("PRAGMA journal_mode")[0]).lower() == "wal"
    finally:
        db.close()


# ----------------------------------------------------------------------
# Upgrade from a supported older schema
# ----------------------------------------------------------------------


def test_upgrade_from_empty_schema_applies_all_migrations(tmp_path) -> None:
    """A DB that predates ``schema_migrations`` (version 0) upgrades cleanly."""
    path = tmp_path / "old.db"
    # Simulate an older install: a bare file with no schema at all (version 0).
    raw = sqlite3.connect(str(path))
    raw.execute("CREATE TABLE unrelated (x INTEGER)")  # pre-existing foreign table
    raw.commit()
    raw.close()

    db = SQLiteDatabase(path)
    db.connect()
    try:
        assert db.schema_version() == LATEST_VERSION
        # The pre-existing table is untouched (non-destructive upgrade).
        assert db.query_one("SELECT COUNT(*) AS n FROM unrelated")["n"] == 0
    finally:
        db.close()


def test_upgrade_is_incremental(tmp_path) -> None:
    """Only migrations newer than the recorded version are applied."""
    path = tmp_path / "partial.db"
    raw = sqlite3.connect(str(path))
    raw.execute(
        "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, "
        "applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    # Pretend version 1 is already applied by creating its core table + marker.
    raw.execute("CREATE TABLE memory_items (id TEXT PRIMARY KEY)")
    # Migration 2 adds partial indexes on relationships, so a faithful v1 DB
    # must already have that table for the incremental upgrade to apply.
    raw.execute(
        "CREATE TABLE relationships (id TEXT PRIMARY KEY, source_id TEXT, "
        "target_id TEXT, relation TEXT, valid_to TEXT)"
    )
    raw.execute("INSERT INTO schema_migrations (version) VALUES (1)")
    raw.commit()
    raw.close()

    db = SQLiteDatabase(path)
    db.connect()  # must not try to re-run migration 1 (would error on CREATE)
    try:
        assert db.schema_version() == LATEST_VERSION
    finally:
        db.close()


# ----------------------------------------------------------------------
# Repeated migration invocation (idempotence)
# ----------------------------------------------------------------------


def test_repeated_connect_does_not_remigrate(tmp_path) -> None:
    path = tmp_path / "idem.db"
    db = SQLiteDatabase(path)
    db.connect()
    first = db.schema_version()
    db.close()

    db2 = SQLiteDatabase(path)
    db2.connect()
    try:
        assert db2.schema_version() == first == LATEST_VERSION
        # schema_migrations has exactly one row per defined migration, no dupes.
        n = db2.query_one("SELECT COUNT(*) AS n FROM schema_migrations")["n"]
        assert n == len(MIGRATIONS)
    finally:
        db2.close()


def test_connect_idempotent_in_process(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "twice.db")
    db.connect()
    db.connect()  # second call is a no-op
    try:
        assert db.schema_version() == LATEST_VERSION
    finally:
        db.close()


# ----------------------------------------------------------------------
# Transaction rollback
# ----------------------------------------------------------------------


def test_execute_script_rolls_back_atomically(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "rollback.db")
    db.connect()
    try:
        # First statement is valid, second references a non-existent table, so
        # the whole script must roll back and leave no partial state.
        with pytest.raises(MemoryStorageError):
            db.execute_script(
                [
                    (
                        "INSERT INTO memory_items (id, memory_type, veracity, "
                        "content, created_at, updated_at) VALUES "
                        "('x','semantic','observation','c','t','t')",
                        (),
                    ),
                    ("INSERT INTO does_not_exist (a) VALUES (1)", ()),
                ]
            )
        row = db.query_one("SELECT COUNT(*) AS n FROM memory_items")
        assert row["n"] == 0  # first insert was rolled back
    finally:
        db.close()


def test_failed_migration_rolls_back(tmp_path, monkeypatch) -> None:
    """A broken migration must roll back and surface MemoryStorageError."""
    path = tmp_path / "badmig.db"
    broken = list(MIGRATIONS) + [(LATEST_VERSION + 1, ("CREATE TABLE bad(",))]
    monkeypatch.setattr(
        "aetheros.memory.storage.database.MIGRATIONS", broken, raising=True
    )
    db = SQLiteDatabase(path)
    with pytest.raises(MemoryStorageError):
        db.connect()
    # The good migrations before the broken one committed; the broken one did not.
    try:
        assert db.schema_version() == LATEST_VERSION
        assert db.query_one(
            "SELECT COUNT(*) AS n FROM sqlite_master "
            "WHERE type='table' AND name='bad'"
        )["n"] == 0
    finally:
        db.close()


# ----------------------------------------------------------------------
# Constraints / foreign-key cascade
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hard_delete_cascades_side_tables(tmp_path, make_memory) -> None:
    db = SQLiteDatabase(tmp_path / "cascade.db")
    db.connect()
    repo = MemoryRepository(db)
    try:
        m = make_memory(tags=["alpha", "beta"], entities=["RELIANCE"])
        await repo.add(m)
        assert db.query_one(
            "SELECT COUNT(*) AS n FROM memory_tags WHERE memory_id=?", (m.id,)
        )["n"] == 2
        assert db.query_one(
            "SELECT COUNT(*) AS n FROM memory_entities WHERE memory_id=?", (m.id,)
        )["n"] == 1

        await repo.delete(m.id)  # hard delete the parent row

        # ON DELETE CASCADE removed the dependent side-table rows.
        assert db.query_one(
            "SELECT COUNT(*) AS n FROM memory_tags WHERE memory_id=?", (m.id,)
        )["n"] == 0
        assert db.query_one(
            "SELECT COUNT(*) AS n FROM memory_entities WHERE memory_id=?", (m.id,)
        )["n"] == 0
    finally:
        db.close()


def test_primary_key_constraint_enforced(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "pk.db")
    db.connect()
    try:
        # Parent row must exist first (memory_tags has an FK to memory_items).
        db.execute(
            "INSERT INTO memory_items (id, memory_type, veracity, content, "
            "created_at, updated_at) VALUES "
            "('m1','semantic','observation','c','t','t')"
        )
        ins = "INSERT INTO memory_tags (memory_id, tag) VALUES ('m1','t1')"
        db.execute(ins)
        with pytest.raises(MemoryStorageError):
            db.execute(ins)  # duplicate composite PK
    finally:
        db.close()


# ----------------------------------------------------------------------
# Close / reopen, restart persistence, records survive migration
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_records_persist_across_close_reopen(tmp_path, make_memory) -> None:
    path = tmp_path / "persist.db"

    db = SQLiteDatabase(path)
    db.connect()
    repo = MemoryRepository(db)
    m = make_memory(
        content="RELIANCE closed above its 200-day average.",
        metadata={"session_id": "s1", "instrument_id": "RELIANCE"},
    )
    await repo.add(m)
    db.close()

    # Simulate a process restart: a brand-new object over the same file.
    db2 = SQLiteDatabase(path)
    db2.connect()
    repo2 = MemoryRepository(db2)
    try:
        fetched = await repo2.get(m.id)
        assert fetched is not None
        assert fetched.content == m.content
        # Provenance + scope columns survived the round trip to disk.
        assert fetched.source.source_type is SourceType.USER
        assert fetched.metadata["instrument_id"] == "RELIANCE"
        assert fetched.version == m.version
    finally:
        db2.close()


@pytest.mark.asyncio
async def test_representative_records_survive_remigration(tmp_path) -> None:
    """
    Write representative records, then reopen (which re-runs the migration
    runner). All records and their fields must survive without loss.
    """
    path = tmp_path / "survive.db"
    db = SQLiteDatabase(path)
    db.connect()
    repo = MemoryRepository(db)

    samples = [
        Memory(
            content="User prefers Brave browser.",
            memory_type=MemoryType.PREFERENCE,
            veracity=Veracity.USER_INPUT,
            source=MemorySource(source_type=SourceType.USER, origin="cli"),
            tags=["preference"],
            entities=["Brave"],
        ),
        Memory(
            content="TradingView showed a bullish engulfing candle.",
            memory_type=MemoryType.EPISODIC,
            veracity=Veracity.OBSERVATION,
            source=MemorySource(source_type=SourceType.VISION, origin="screenshot"),
            entities=["TradingView"],
            metadata={"session_id": "s9"},
        ),
    ]
    await repo.add_many(samples)
    before = await repo.count()
    db.close()

    # Reopen -> migration runner executes again; nothing should be dropped.
    db2 = SQLiteDatabase(path)
    db2.connect()
    try:
        assert db2.schema_version() == LATEST_VERSION
        repo2 = MemoryRepository(db2)
        assert await repo2.count() == before == len(samples)
        for original in samples:
            got = await repo2.get(original.id)
            assert got is not None
            assert got.content == original.content
            assert got.veracity is original.veracity
            assert got.source.source_type is original.source.source_type
    finally:
        db2.close()


# ----------------------------------------------------------------------
# Concurrent access (cross-connection) with the bounded busy timeout
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_writers_two_connections(tmp_path, make_memory) -> None:
    """
    Two independent SQLiteDatabase objects (separate connections) over one WAL
    file both write; the bounded busy_timeout lets the second wait rather than
    fail. Measured behaviour: all writes land, no 'database is locked' error.
    """
    path = tmp_path / "concurrent.db"
    db_a = SQLiteDatabase(path, busy_timeout_ms=5000)
    db_b = SQLiteDatabase(path, busy_timeout_ms=5000)
    db_a.connect()
    db_b.connect()
    repo_a = MemoryRepository(db_a)
    repo_b = MemoryRepository(db_b)
    try:
        errors: list[Exception] = []

        def write(repo: MemoryRepository, n: int) -> None:
            import asyncio

            async def _go() -> None:
                for i in range(n):
                    await repo.add(make_memory(content=f"c{i}"))

            try:
                asyncio.run(_go())
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        t1 = threading.Thread(target=write, args=(repo_a, 15))
        t2 = threading.Thread(target=write, args=(repo_b, 15))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert errors == [], f"concurrent writes raised: {errors}"
        # Reader connection sees the committed total from both writers.
        assert await repo_a.count() == 30
    finally:
        db_a.close()
        db_b.close()


# ----------------------------------------------------------------------
# Backup / recovery
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backup_then_recover(tmp_path, make_memory) -> None:
    live = tmp_path / "live.db"
    backup = tmp_path / "backups" / "snapshot.db"

    db = SQLiteDatabase(live)
    db.connect()
    repo = MemoryRepository(db)
    m = make_memory(content="snapshot me")
    await repo.add(m)

    out = db.backup(backup)
    assert out == backup
    assert backup.exists()
    db.close()

    # "Recover": open the backup as if it had replaced the live file.
    restored = SQLiteDatabase(backup)
    restored.connect()
    try:
        repo_r = MemoryRepository(restored)
        got = await repo_r.get(m.id)
        assert got is not None and got.content == "snapshot me"
        assert restored.schema_version() == LATEST_VERSION
    finally:
        restored.close()


def test_backup_rejects_memory_destination() -> None:
    db = SQLiteDatabase(":memory:")
    db.connect()
    try:
        with pytest.raises(MemoryStorageError):
            db.backup(":memory:")
    finally:
        db.close()
