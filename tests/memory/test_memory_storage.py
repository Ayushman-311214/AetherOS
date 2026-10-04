"""
Storage-layer tests (spec Phase 2/4 + Phase 24 unit tests).

Prove the schema migrates, a Memory round-trips losslessly through SQLite,
provenance survives, side-table filtering works, and access accounting + links
behave.
"""

from __future__ import annotations

import pytest

from aetheros.memory.domain import (
    Memory,
    MemoryQuery,
    MemoryType,
    SourceType,
    Veracity,
)
from aetheros.memory.storage import LATEST_VERSION, MemoryRepository, SQLiteDatabase


def test_schema_migrates_to_latest(database: SQLiteDatabase) -> None:
    assert database.schema_version() == LATEST_VERSION
    assert database.is_connected


def test_connect_is_idempotent() -> None:
    db = SQLiteDatabase(":memory:")
    db.connect()
    db.connect()  # must not raise or re-migrate
    assert db.schema_version() == LATEST_VERSION
    db.close()


@pytest.mark.asyncio
async def test_add_and_get_round_trip(repository: MemoryRepository, make_memory) -> None:
    original = make_memory(metadata={"session_id": "s1", "task_id": "t1"})
    await repository.add(original)

    fetched = await repository.get(original.id)
    assert fetched is not None
    assert fetched.id == original.id
    assert fetched.content == original.content
    assert fetched.memory_type is MemoryType.PREFERENCE
    assert fetched.veracity is Veracity.USER_INPUT
    # Provenance preserved (Rule 8).
    assert fetched.source.source_type is SourceType.USER
    assert fetched.source.origin == "test"
    assert fetched.tags == original.tags
    assert fetched.entities == original.entities
    assert fetched.metadata["session_id"] == "s1"


@pytest.mark.asyncio
async def test_get_missing_returns_none(repository: MemoryRepository) -> None:
    assert await repository.get("does-not-exist") is None


@pytest.mark.asyncio
async def test_delete_removes_memory(repository: MemoryRepository, make_memory) -> None:
    m = make_memory()
    await repository.add(m)
    assert await repository.exists(m.id)
    await repository.delete(m.id)
    assert not await repository.exists(m.id)


@pytest.mark.asyncio
async def test_count_excludes_deleted(repository: MemoryRepository, make_memory) -> None:
    from aetheros.memory.domain import MemoryStatus

    live = make_memory(content="live memory")
    gone = make_memory(content="deleted memory")
    gone.status = MemoryStatus.DELETED
    await repository.add_many([live, gone])

    assert await repository.count() == 1
    assert await repository.count(include_deleted=True) == 2


@pytest.mark.asyncio
async def test_candidates_filter_by_type_and_tag(
    repository: MemoryRepository, make_memory
) -> None:
    pref = make_memory(content="prefers brave", tags=["preference", "browser"])
    other = make_memory(
        content="some episode",
        memory_type=MemoryType.EPISODIC,
        veracity=Veracity.OBSERVATION,
        tags=["episode"],
        entities=["TradingView"],
    )
    await repository.add_many([pref, other])

    q = MemoryQuery(memory_types=[MemoryType.PREFERENCE], tags=["browser"])
    hits = await repository.candidates(q)
    assert [m.id for m in hits] == [pref.id]


@pytest.mark.asyncio
async def test_candidates_filter_by_context_column(
    repository: MemoryRepository, make_memory
) -> None:
    a = make_memory(content="in session 1", metadata={"session_id": "s1"})
    b = make_memory(content="in session 2", metadata={"session_id": "s2"})
    await repository.add_many([a, b])

    q = MemoryQuery(context={"session_id": "s1"})
    hits = await repository.candidates(q)
    assert [m.id for m in hits] == [a.id]


@pytest.mark.asyncio
async def test_record_access_bumps_counter(
    repository: MemoryRepository, make_memory
) -> None:
    m = make_memory()
    await repository.add(m)
    await repository.record_access(m.id, context={"query": "browser"})
    await repository.record_access(m.id)

    fetched = await repository.get(m.id)
    assert fetched is not None
    assert fetched.access_count == 2
    assert fetched.last_accessed_at is not None


@pytest.mark.asyncio
async def test_type_distribution(repository: MemoryRepository, make_memory) -> None:
    await repository.add_many(
        [
            make_memory(content="pref a"),
            make_memory(content="pref b"),
            make_memory(
                content="ep",
                memory_type=MemoryType.EPISODIC,
                veracity=Veracity.OBSERVATION,
            ),
        ]
    )
    dist = await repository.type_distribution()
    assert dist["preference"] == 2
    assert dist["episodic"] == 1


@pytest.mark.asyncio
async def test_links_round_trip(repository: MemoryRepository, make_memory) -> None:
    a = make_memory(content="failure: fixed coordinates")
    b = make_memory(content="recovery: vision grounding")
    await repository.add_many([a, b])
    await repository.add_link(
        {
            "id": "link1",
            "from_id": a.id,
            "to_id": b.id,
            "link_type": "has_outcome",
            "weight": 1.0,
            "metadata": {},
        }
    )
    neighbours = await repository.linked_ids(a.id)
    assert neighbours == [(b.id, "has_outcome", 1.0)]


def test_memory_rejects_blank_content() -> None:
    with pytest.raises(ValueError):
        Memory(content="   ")
