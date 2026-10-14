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
async def get_memory(
    memory_id: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    try:
        memory = await mgr.controls.inspect(
            memory_id, user_id=user_id, session_id=session_id
        )
    except Exception as exc:
        return {"ok": False, "error": "NOT_FOUND", "memory_id": memory_id,
                "detail": str(exc)}
    return {"ok": True, "memory": memory}


@tool(category="memory", description="Update a stored memory's content or confidence.")
async def update_memory(
    memory_id: str,
    content: str | None = None,
    confidence: float | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    # Content edits go through the user-controls correction path (scope
    # ownership + revision history + immutable-history refusals); raw
    # confidence edits keep the legacy direct path.
    if content is not None:
        try:
            return {
                "ok": True,
                **await mgr.controls.correct(
                    memory_id, content, user_id=user_id, session_id=session_id
                ),
            }
        except Exception as exc:
            return {"ok": False, "error": "UPDATE_FAILED", "detail": str(exc)}
    changes: dict[str, Any] = {}
    if confidence is not None:
        changes["confidence"] = confidence
    if not changes:
        return {"ok": False, "error": "NO_CHANGES"}
    try:
        memory = await mgr.update(memory_id, **changes)
    except Exception as exc:  # MemoryNotFoundError and friends
        return {"ok": False, "error": "UPDATE_FAILED", "detail": str(exc)}
    return {"ok": True, "memory_id": memory.id, "version": memory.version}


@tool(category="memory", description="Correct a user fact or preference (revision history kept).")
async def correct_memory(
    memory_id: str,
    content: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    try:
        return {
            "ok": True,
            **await mgr.controls.correct(
                memory_id, content, user_id=user_id, session_id=session_id
            ),
        }
    except Exception as exc:
        return {"ok": False, "error": "CORRECT_FAILED", "detail": str(exc)}


@tool(category="memory", description="Export memories in scope as full-fidelity dicts (no vectors/internals).")
async def export_memories(
    user_id: str | None = None,
    session_id: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    try:
        return {
            "ok": True,
            **await mgr.controls.export_scope(
                user_id=user_id, session_id=session_id, limit=limit
            ),
        }
    except Exception as exc:
        return {"ok": False, "error": "EXPORT_FAILED", "detail": str(exc)}


@tool(category="memory", description="Forget a memory. Soft by default; hard=true deletes it permanently.")
async def forget_memory(
    memory_id: str,
    hard: bool = False,
    user_id: str | None = None,
    session_id: str | None = None,
    allow_history: bool = False,
) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    try:
        if hard:
            return {
                "ok": True,
                **await mgr.controls.erase(
                    memory_id, user_id=user_id, session_id=session_id,
                    allow_history=allow_history,
                ),
            }
        return {
            "ok": True,
            **await mgr.controls.forget(
                memory_id, user_id=user_id, session_id=session_id,
                allow_history=allow_history,
            ),
        }
    except Exception as exc:
        return {"ok": False, "error": "FORGET_FAILED", "memory_id": memory_id,
                "detail": str(exc)}


@tool(category="memory", description="List stored memories, optionally filtered by type.")
async def list_memories(
    memory_type: str | None = None,
    limit: int = 20,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    mgr = _manager()
    if mgr is None:
        return _disabled()
    from .domain.enums import MemoryType as MT

    mtype = None
    if memory_type:
        try:
            mtype = MT(memory_type.lower())
        except ValueError:
            mtype = None
    rows = await mgr.controls.list_scope(
        user_id=user_id, session_id=session_id, memory_type=mtype, limit=limit
    )
    return {
        "ok": True,
        "count": len(rows),
        "memories": [
            {
                "id": m["id"],
                "type": m["memory_type"],
                "content": m["content"],
                "confidence": round(m["confidence"], 3),
                "status": m["status"],
            }
            for m in rows
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
