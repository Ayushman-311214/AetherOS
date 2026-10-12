"""
Phase 4 write-path hardening tests.

Covers the additive honesty/safety features layered onto the existing write
path: the five-state :class:`WriteResult`, idempotent ``store``, disabled-mode
degradation, the optimistic-concurrency guard on ``update``, and the
vector-projection verify/repair seam. These exercise the real SQLite store and
the real (hashing) embedder via the ``manager`` fixture -- no mocks.
"""

from __future__ import annotations

import dataclasses

import pytest

from aetheros.core.errors.memory_error import MemoryConflictError
from aetheros.memory.domain import MemoryImportance
from aetheros.memory.services.results import WriteResult, WriteStatus


def _memory(make_memory, **kw):
    return make_memory(**kw)


# --------------------------------------------------------------------------
# WriteResult -- explicit five-state outcome
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_returns_stored(manager, make_memory) -> None:
    result = await manager.store(_memory(make_memory, content="VWAP is a volume line."))
    assert isinstance(result, WriteResult)
    assert result.status is WriteStatus.STORED
    assert result.persisted
    assert result.ok
    assert await manager.get(result.memory_id) is not None


@pytest.mark.asyncio
async def test_store_skips_on_policy(manager, make_memory) -> None:
    trivial = _memory(
        make_memory,
        content="noise",
        importance=MemoryImportance.TRIVIAL,
        confidence=0.1,
    )
    result = await manager.store(trivial)
    assert result.status is WriteStatus.SKIPPED
    assert not result.persisted
    assert result.ok  # a deliberate skip is still an accepted outcome
    assert await manager.get(trivial.id) is None  # nothing persisted


@pytest.mark.asyncio
async def test_store_is_idempotent_by_id(manager, make_memory) -> None:
    m = _memory(make_memory, content="RSI measures momentum.")
    first = await manager.store(m)
    assert first.status is WriteStatus.STORED
    # Re-submitting the same object (same id) must not create a duplicate.
    second = await manager.store(m)
    assert second.status is WriteStatus.SKIPPED
    assert "already stored" in (second.reason or "")
    assert await manager._repo.count() == 1


@pytest.mark.asyncio
async def test_store_is_idempotent_by_key(manager, make_memory) -> None:
    a = _memory(make_memory, content="MACD crossover up.")
    b = _memory(make_memory, content="MACD crossover up (retry).")
    first = await manager.store(a, idempotency_key="signal-123")
    second = await manager.store(b, idempotency_key="signal-123")
    assert first.status is WriteStatus.STORED
    assert second.status is WriteStatus.SKIPPED
    assert second.memory_id == first.memory_id
    assert await manager._repo.count() == 1


@pytest.mark.asyncio
async def test_store_reports_failure_without_persisting(manager, make_memory) -> None:
    # Force the embedding step to fail; the result must be FAILED, never STORED.
    async def _boom(*_a, **_k):
        raise RuntimeError("embedder down")

    manager._writer._vectors.index = _boom  # type: ignore[assignment]
    m = _memory(make_memory, content="will fail to embed")
    result = await manager.store(m)
    assert result.status is WriteStatus.FAILED
    assert not result.persisted
    assert "embedder down" in (result.reason or "")


# --------------------------------------------------------------------------
# Disabled mode -- never pretend to persist, never raise on recall
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_store_is_unavailable(manager, make_memory) -> None:
    manager._config = dataclasses.replace(manager._config, enabled=False)
    result = await manager.store(_memory(make_memory, content="ignored"))
    assert result.status is WriteStatus.UNAVAILABLE
    assert not result.ok


@pytest.mark.asyncio
async def test_disabled_retrieve_degrades_to_empty(manager, make_memory) -> None:
    await manager.store(_memory(make_memory, content="brave browser note"))
    manager._config = dataclasses.replace(manager._config, enabled=False)
    assert await manager.retrieve("brave browser") == []


# --------------------------------------------------------------------------
# Optimistic concurrency guard on update
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_guarded_update_succeeds_on_matching_version(manager) -> None:
    m = await manager.remember("old", importance=MemoryImportance.HIGH)
    updated = await manager.update(
        m.id, expected_version=m.version, content="new"
    )
    assert updated.content == "new"
    assert updated.version == m.version + 1


@pytest.mark.asyncio
async def test_guarded_update_rejects_stale_version(manager) -> None:
    m = await manager.remember("old", importance=MemoryImportance.HIGH)
    # A concurrent writer bumps the version first.
    await manager.update(m.id, content="winner")
    # Our write still thinks the row is at the original version -> conflict.
    with pytest.raises(MemoryConflictError):
        await manager.update(m.id, expected_version=m.version, content="loser")
    # The winner's content survived; the loser never persisted.
    assert (await manager.get(m.id)).content == "winner"


@pytest.mark.asyncio
async def test_unguarded_update_is_last_writer_wins(manager) -> None:
    m = await manager.remember("old", importance=MemoryImportance.HIGH)
    updated = await manager.update(m.id, content="new")  # no expected_version
    assert updated.content == "new"


# --------------------------------------------------------------------------
# Projection consistency / repair seam
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_projection_consistent_after_normal_writes(manager, make_memory) -> None:
    await manager.store(_memory(make_memory, content="a"))
    await manager.store(_memory(make_memory, content="b"))
    report = await manager.verify_projection()
    assert report["consistent"]
    assert report["missing"] == []
    assert report["orphan"] == []


@pytest.mark.asyncio
async def test_repair_reindexes_missing_vector(manager, make_memory) -> None:
    result = await manager.store(_memory(make_memory, content="needs a vector"))
    # Simulate a lost projection row (authoritative store still has the memory).
    await manager._vectors.delete(result.memory_id)
    before = await manager.verify_projection()
    assert result.memory_id in before["missing"]
    assert not before["consistent"]

    repaired = await manager.repair_projection()
    assert repaired["reindexed"] == 1
    after = await manager.verify_projection()
    assert after["consistent"]


@pytest.mark.asyncio
async def test_repair_removes_orphan_vector(manager, make_memory) -> None:
    await manager.store(_memory(make_memory, content="legit"))
    # A vector whose authoritative row is absent (legacy/corrupted drift). The
    # FK CASCADE normally prevents this, so we insert past the FK to simulate it;
    # repair must still remove it, since an orphan vector leaks content that has
    # no backing memory.
    conn = manager._db._require()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "INSERT INTO memory_embeddings (memory_id, dim, vector, model, created_at) "
        "VALUES (?,?,?,?,?)",
        ("ghost-id", 1, b"\x00\x00\x00\x00", "hashing", "2026-01-01T00:00:00Z"),
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    before = await manager.verify_projection()
    assert "ghost-id" in before["orphan"]
    assert not before["consistent"]

    repaired = await manager.repair_projection()
    assert repaired["removed"] == 1
    assert (await manager.verify_projection())["consistent"]


@pytest.mark.asyncio
async def test_repair_is_idempotent(manager, make_memory) -> None:
    await manager.store(_memory(make_memory, content="stable"))
    first = await manager.repair_projection()
    assert first == {"reindexed": 0, "removed": 0}
