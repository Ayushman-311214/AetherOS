"""
Memory tools exposed through the ToolRegistry (spec Phase 19).

Thin, schema-friendly wrappers over the :class:`MemoryManager`, following the
same convention as every other AetherOS tool: the function is registered by the
``@tool`` decorator at import time and resolves its service from the DI
container at call time (CLAUDE.md section 11 -- never bypass the registry). Each
tool returns a plain, predictable dict so it serialises cleanly into a tool
result and the LLM never sees a raw domain object.

If memory is disabled (ENABLE_MEMORY=false) the manager is not registered; every
tool then returns a clear ``{"ok": False, "error": "MEMORY_DISABLED"}`` rather
than raising, so an agent is told the capability is off instead of crashing.
"""

from __future__ import annotations

from typing import Any

from ..core.container import container
from ..tools.tool import tool
from .domain.enums import (
    MemoryImportance,
    MemoryType,
    SourceType,
    Veracity,
)


def _manager():
    from .services.manager import MemoryManager

    if not container.has(MemoryManager):
        return None
    return container.resolve(MemoryManager)


def _disabled() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "MEMORY_DISABLED",
        "detail": "Memory is off. Set ENABLE_MEMORY=true to use it.",
    }


@tool(category="memory", description="Store a new memory (a fact, note or observation).")
async def remember(
    content: str,
    memory_type: str = "semantic",
    tags: list[str] | None = None,
    importance: str = "normal",
) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    try:
        mtype = MemoryType(memory_type.lower())
    except ValueError:
        mtype = MemoryType.SEMANTIC
    importance_map = {
        "trivial": MemoryImportance.TRIVIAL,
        "low": MemoryImportance.LOW,
        "normal": MemoryImportance.NORMAL,
        "high": MemoryImportance.HIGH,
        "critical": MemoryImportance.CRITICAL,
    }
    memory = await mgr.remember(
        content=content,
        memory_type=mtype,
        veracity=Veracity.OBSERVATION,
        source_type=SourceType.USER,
        origin="remember_tool",
        importance=importance_map.get(importance.lower(), MemoryImportance.NORMAL),
        tags=tags or [],
    )
    return {"ok": True, "memory_id": memory.id, "memory_type": memory.memory_type.value}


@tool(category="memory", description="Search memory for relevant items and why they matched.")
async def recall(query: str, limit: int = 5) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    results = await mgr.retrieve(query, limit=limit)
    return {
        "ok": True,
        "count": len(results),
        "results": [
            {
                "id": r.memory.id,
                "content": r.memory.content,
                "type": r.memory.memory_type.value,
                "confidence": round(r.memory.confidence, 3),
                "score": round(r.score, 3),
                "why": r.explanation.reasons,
            }
            for r in results
        ],
    }


@tool(category="memory", description="Fetch one memory by its id.")
async def get_memory(memory_id: str) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    memory = await mgr.get(memory_id)
    if memory is None:
        return {"ok": False, "error": "NOT_FOUND", "memory_id": memory_id}
    return {"ok": True, "memory": memory.to_dict()}


@tool(category="memory", description="Update a stored memory's content or confidence.")
async def update_memory(
    memory_id: str,
    content: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    changes: dict[str, Any] = {}
    if content is not None:
        changes["content"] = content
    if confidence is not None:
        changes["confidence"] = confidence
    if not changes:
        return {"ok": False, "error": "NO_CHANGES"}
    try:
        memory = await mgr.update(memory_id, **changes)
    except Exception as exc:  # MemoryNotFoundError and friends
        return {"ok": False, "error": "UPDATE_FAILED", "detail": str(exc)}
    return {"ok": True, "memory_id": memory.id, "version": memory.version}


@tool(category="memory", description="Forget a memory. Soft by default; hard=true deletes it permanently.")
async def forget_memory(memory_id: str, hard: bool = False) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    ok = await mgr.forget(memory_id, hard=hard)
    return {"ok": ok, "memory_id": memory_id, "hard": hard}


@tool(category="memory", description="List stored memories, optionally filtered by type.")
async def list_memories(memory_type: str | None = None, limit: int = 20) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    memories = await mgr._repo.list_by(memory_type=memory_type, limit=limit)
    return {
        "ok": True,
        "count": len(memories),
        "memories": [
            {
                "id": m.id,
                "type": m.memory_type.value,
                "content": m.content,
                "confidence": round(m.confidence, 3),
                "status": m.status.value,
            }
            for m in memories
        ],
    }


@tool(category="memory", description="Find entities related to a given one in the knowledge graph.")
async def find_related_memory(entity: str, max_hops: int = 2) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    related = await mgr.related_entities(entity, max_hops=max_hops)
    return {
        "ok": True,
        "entity": entity,
        "related": [{"name": e.name, "type": e.entity_type} for e in related],
    }


@tool(category="memory", description="Report memory subsystem statistics.")
async def memory_status() -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    return {"ok": True, "stats": await mgr.stats()}
