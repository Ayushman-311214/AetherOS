"""
Working (short-term) memory (spec Phase 8).

A bounded, in-process scratchpad for the active session: the current task, plan,
entities, recent observations, tool calls and decisions. It is intentionally
*not* persisted row-by-row -- it is the live context window. Capacity is capped
(MEMORY_MAX_WORKING_CONTEXT) so it never grows without bound; when full it evicts
the least-important, oldest item, and :meth:`promote` writes the items worth
keeping into long-term memory before they are lost.
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..domain.enums import (
    MemoryImportance,
    MemoryScope,
    MemoryType,
    SourceType,
    Veracity,
)
from ..domain.memory import Memory, MemorySource
from .._clock import utcnow


@dataclass(slots=True)
class WorkingItem:
    """One entry in the working set."""

    kind: str
    content: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    data: dict[str, Any] = field(default_factory=dict)
    importance: MemoryImportance = MemoryImportance.NORMAL
    created_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "content": self.content,
            "data": dict(self.data),
            "importance": int(self.importance),
            "created_at": self.created_at.isoformat(),
        }


class WorkingMemory:
    """Bounded live context for one session (spec Phase 8)."""

    def __init__(self, *, capacity: int = 50, session_id: str | None = None) -> None:
        self._capacity = max(1, capacity)
        self.session_id = session_id or uuid.uuid4().hex
        self._items: deque[WorkingItem] = deque()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add(
        self,
        kind: str,
        content: str,
        *,
        data: dict[str, Any] | None = None,
        importance: MemoryImportance = MemoryImportance.NORMAL,
    ) -> WorkingItem:
        item = WorkingItem(
            kind=kind, content=content, data=data or {}, importance=importance
        )
        self._items.append(item)
        self._enforce_capacity()
        return item

    def update(self, item_id: str, *, content: str | None = None, **data: Any) -> bool:
        for item in self._items:
            if item.id == item_id:
                if content is not None:
                    item.content = content
                item.data.update(data)
                return True
        return False

    def remove(self, item_id: str) -> bool:
        for item in list(self._items):
            if item.id == item_id:
                self._items.remove(item)
                return True
        return False

    def clear(self) -> None:
        self._items.clear()

    def _enforce_capacity(self) -> None:
        while len(self._items) > self._capacity:
            # Evict the lowest-importance item among the oldest half, so recent
            # and important context survives (spec Phase 8 -- bounded window).
            oldest = list(self._items)[: max(1, len(self._items) // 2)]
            victim = min(oldest, key=lambda it: (int(it.importance), it.created_at))
            self._items.remove(victim)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def items(self, *, kind: str | None = None) -> list[WorkingItem]:
        if kind is None:
            return list(self._items)
        return [it for it in self._items if it.kind == kind]

    def __len__(self) -> int:
        return len(self._items)

    def summarize(self) -> str:
        """A compact textual summary of the working set (for context assembly)."""
        if not self._items:
            return "Working memory is empty."
        lines = [f"Working memory ({len(self._items)} items):"]
        for item in self._items:
            lines.append(f"- [{item.kind}] {item.content}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Promotion to long-term (spec Phase 8 -- promote_to_long_term)
    # ------------------------------------------------------------------

    def to_memories(
        self, *, min_importance: MemoryImportance = MemoryImportance.HIGH
    ) -> list[Memory]:
        """Project the keep-worthy working items into long-term Memory records."""
        out: list[Memory] = []
        for item in self._items:
            if int(item.importance) < int(min_importance):
                continue
            out.append(
                Memory(
                    content=item.content,
                    memory_type=MemoryType.SEMANTIC,
                    veracity=Veracity.OBSERVATION,
                    data=dict(item.data),
                    source=MemorySource(
                        source_type=SourceType.SYSTEM, origin="working_memory"
                    ),
                    importance=item.importance,
                    scope=MemoryScope.LONG_TERM,
                    tags=["promoted", item.kind],
                    metadata={"session_id": self.session_id},
                )
            )
        return out
