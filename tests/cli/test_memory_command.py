"""
The ``memory`` CLI command (spec Phase 28).

Drives the command handler directly against a throwaway in-memory
MemoryManager wired into the DI container, and always deregisters it so the
process-wide container is left clean. Also pins the honest "NOT ENABLED"
rendering when memory is off.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from aetheros.cli.commands import CommandRegistry
from aetheros.core.container import container
from aetheros.memory.config import MemoryConfig
from aetheros.memory.services.manager import MemoryManager


@pytest_asyncio.fixture
async def commands_with_memory():
    mgr = MemoryManager(MemoryConfig.for_memory_db(Path(":memory:"), embedding_dim=64))
    await mgr.initialize()
    container.register_singleton(MemoryManager, lambda: mgr)
    try:
        yield CommandRegistry(), mgr
    finally:
        container.remove(MemoryManager)
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_memory_reports_not_enabled_when_absent() -> None:
    container.remove(MemoryManager)
    out = await CommandRegistry()._memory_command([])
    assert "NOT ENABLED" in out


@pytest.mark.asyncio
async def test_memory_stats(commands_with_memory) -> None:
    commands, mgr = commands_with_memory
    await mgr.remember("User prefers Brave.", tags=["preference"])
    out = await commands._memory_command(["stats"])
    assert "Total memories : 1" in out
    assert "Embedder" in out


@pytest.mark.asyncio
async def test_memory_search_and_show(commands_with_memory) -> None:
    commands, mgr = commands_with_memory
    m = await mgr.remember("User prefers the Brave browser.", tags=["preference"])

    search_out = await commands._memory_command(["search", "browser"])
    assert "Brave" in search_out
    assert "why:" in search_out

    show_out = await commands._memory_command(["show", m.id])
    assert m.id in show_out
    assert "confidence" in show_out


@pytest.mark.asyncio
async def test_memory_forget(commands_with_memory) -> None:
    commands, mgr = commands_with_memory
    m = await mgr.remember("a disposable note")
    out = await commands._memory_command(["forget", m.id, "hard"])
    assert "hard-deleted" in out
    assert await mgr.get(m.id) is None
