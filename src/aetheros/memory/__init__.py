"""
AetherOS Memory subsystem (CLAUDE.md section 15; implementation spec Phases 0-29).

A structured, retrievable, confidence- and time-aware memory layer: working,
episodic, semantic, procedural, preference, failure and trading memory over a
SQLite store, a swappable embedding/vector index and a knowledge graph, surfaced
through a hybrid, explainable retrieval pipeline and the ToolRegistry.

The public entry point is :class:`~aetheros.memory.services.manager.MemoryManager`;
the bootstrapper constructs and registers it when ``ENABLE_MEMORY`` is set.
"""

from __future__ import annotations

from .config import MemoryConfig

__all__ = ["MemoryConfig", "MemoryManager", "SQLiteMemoryProvider"]


def __getattr__(name: str):
    # Lazy re-export so `from aetheros.memory import MemoryManager` works without
    # importing the (numpy/networkx-heavy) service layer at package import time.
    if name == "MemoryManager":
        from .services.manager import MemoryManager

        return MemoryManager
    if name == "SQLiteMemoryProvider":
        from .services.provider import SQLiteMemoryProvider

        return SQLiteMemoryProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
