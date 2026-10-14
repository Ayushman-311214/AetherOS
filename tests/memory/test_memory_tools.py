"""
Memory tool tests (spec Phase 19/24).

The tools resolve the MemoryManager from the process-wide DI container at call
time. These tests register a throwaway in-memory manager there, exercise the
tools, and always deregister it so nothing leaks into the rest of the suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from aetheros.core.container import container
from aetheros.memory.config import MemoryConfig
from aetheros.memory.services.manager import MemoryManager
from aetheros.memory import tools as memory_tools


@pytest_asyncio.fixture
async def wired_manager():
    mgr = MemoryManager(MemoryConfig.for_memory_db(Path(":memory:"), embedding_dim=64))
    await mgr.initialize()
    container.register_singleton(MemoryManager, lambda: mgr)
    try:
        yield mgr
    finally:
        container.remove(MemoryManager)
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_remember_and_recall_tools(wired_manager) -> None:
    stored = await memory_tools.remember(
        "User prefers the Brave browser.", tags=["preference"], importance="high"
    )
    assert stored["ok"] is True
    recalled = await memory_tools.recall("which browser?")
    assert recalled["ok"] is True
    assert recalled["count"] >= 1
    assert recalled["results"][0]["why"]  # explainable (Rule 6)


@pytest.mark.asyncio
async def test_get_update_forget_tools(wired_manager) -> None:
    stored = await memory_tools.remember("a note to edit")
    mid = stored["memory_id"]

    got = await memory_tools.get_memory(mid)
    assert got["ok"] and got["memory"]["id"] == mid

    updated = await memory_tools.update_memory(mid, content="edited note")
    assert updated["ok"] and updated["version"] == 2

    forgotten = await memory_tools.forget_memory(mid, hard=True)
    assert forgotten["ok"]
    assert (await memory_tools.get_memory(mid))["ok"] is False


@pytest.mark.asyncio
async def test_status_and_list_tools(wired_manager) -> None:
    await memory_tools.remember("fact one")
    status = await memory_tools.memory_status()
    assert status["ok"] and status["stats"]["total"] >= 1
    listing = await memory_tools.list_memories(limit=10)
    assert listing["ok"] and listing["count"] >= 1


@pytest.mark.asyncio
async def test_tools_report_disabled_when_not_registered() -> None:
    # No manager registered -> every tool returns the disabled sentinel.
    assert not container.has(MemoryManager)
    result = await memory_tools.recall("anything")
    assert result == {
        "ok": False,
        "error": "MEMORY_DISABLED",
        "detail": "Memory is off. Set ENABLE_MEMORY=true to use it.",
    }


def test_memory_tools_registered_in_registry() -> None:
    from aetheros.tools.registry import tool_registry

    names = tool_registry.names()
    for expected in ("remember", "recall", "get_memory", "forget_memory", "memory_status"):
        assert expected in names
    assert "memory" in tool_registry.categories()
