"""
Shared fixtures for the memory test suite.

Every fixture builds against an in-memory SQLite database so the suite is fast,
isolated and leaves nothing on disk. ``:memory:`` survives for the lifetime of
the single connection the SQLiteDatabase holds, which is exactly one test here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest
import pytest_asyncio

from aetheros.memory.config import MemoryConfig
from aetheros.memory.domain import (
    Memory,
    MemoryImportance,
    MemorySource,
    MemoryType,
    SourceType,
    Veracity,
)
from aetheros.memory.storage import MemoryRepository, SQLiteDatabase


@pytest.fixture
def memory_config() -> MemoryConfig:
    from pathlib import Path

    return MemoryConfig.for_memory_db(Path(":memory:"), embedding_dim=64)


@pytest_asyncio.fixture
async def database() -> AsyncIterator[SQLiteDatabase]:
    db = SQLiteDatabase(":memory:")
    db.connect()
    try:
        yield db
    finally:
        db.close()


@pytest_asyncio.fixture
async def repository(database: SQLiteDatabase) -> MemoryRepository:
    return MemoryRepository(database)


@pytest_asyncio.fixture
async def manager(memory_config) -> "AsyncIterator":
    from aetheros.memory.services.manager import MemoryManager

    mgr = MemoryManager(memory_config)
    await mgr.initialize()
    try:
        yield mgr
    finally:
        await mgr.shutdown()


@pytest.fixture
def make_memory() -> Callable[..., Memory]:
    def _make(
        content: str = "User prefers the Brave browser.",
        *,
        memory_type: MemoryType = MemoryType.PREFERENCE,
        veracity: Veracity = Veracity.USER_INPUT,
        confidence: float = 0.8,
        importance: MemoryImportance = MemoryImportance.NORMAL,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        metadata: dict | None = None,
    ) -> Memory:
        return Memory(
            content=content,
            memory_type=memory_type,
            veracity=veracity,
            confidence=confidence,
            importance=importance,
            source=MemorySource(source_type=SourceType.USER, origin="test"),
            tags=tags or ["preference", "browser"],
            entities=entities or ["Brave"],
            metadata=metadata or {},
        )

    return _make
