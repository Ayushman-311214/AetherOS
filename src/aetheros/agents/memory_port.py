"""
The memory port the agent depends on (spec Phase 20B).

Dependency inversion: the agent must be able to recall and record memory without
knowing SQLite, vectors, graphs or embeddings exist. So the agent package owns
this *port* -- a small abstraction plus a null-object default -- and the memory
package implements it. ``AgentCore`` holds an :class:`AgentMemory`; when memory
is disabled it holds a :class:`NullAgentMemory`, so there is no scattered
``if ENABLE_MEMORY`` in the loop (spec Phase 20K) and a missing memory subsystem
is simply a no-op collaborator.

The data the port exposes to the agent (:class:`MemoryContext` /
:class:`MemoryItemView`) is deliberately plain -- it carries no memory-domain
types -- so nothing in the agent takes a dependency on the memory package.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .state import AgentState


@dataclass(frozen=True, slots=True)
class MemoryItemView:
    """A single recalled memory, flattened to plain fields for the agent."""

    id: str
    memory_type: str
    content: str
    confidence: float
    score: float
    reasons: tuple[str, ...] = ()

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.memory_type,
            "confidence": round(self.confidence, 3),
            "score": round(self.score, 3),
            "why": list(self.reasons),
        }


@dataclass(slots=True)
class MemoryContext:
    """
    Structured, bounded memory handed to the planner (spec Phase 20D).

    Carries the ranked items plus retrieval metadata. ``error`` is set (and
    ``items`` left empty) when recall failed -- the agent treats that as "no
    memory", never as a reason to abort the run (spec Phase 20L).
    """

    query: str = ""
    items: list[MemoryItemView] = field(default_factory=list)
    latency_ms: float = 0.0
    truncated: bool = False
    error: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.items

    def by_type(self, memory_type: str) -> list[MemoryItemView]:
        return [i for i in self.items if i.memory_type == memory_type]

    def to_observation_lines(self, *, max_chars: int) -> list[str]:
        """
        Render the recalled memory as bounded advisory lines for the prompt.

        The framing is explicit (spec Phase 20E/20R, Test 9): memory is historical
        guidance, and current observations / vision take precedence -- the planner
        must never blindly replay a stale coordinate. The total text is capped at
        ``max_chars`` so recall cannot pollute the context (Rule 7 / Phase 20N).
        """
        if not self.items:
            return []

        header = (
            "Relevant memory (historical guidance only — verify against the "
            "current screen/state; current observations and vision take "
            "precedence over any remembered value such as coordinates):"
        )
        lines = [header]
        used = len(header)
        for item in self.items:
            line = (
                f"- [{item.memory_type}] {item.content} "
                f"(confidence {item.confidence:.2f})"
            )
            if used + len(line) > max_chars:
                break
            lines.append(line)
            used += len(line)
        return lines

    def describe(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "count": len(self.items),
            "latency_ms": round(self.latency_ms, 2),
            "truncated": self.truncated,
            "error": self.error,
            "items": [i.describe() for i in self.items],
        }


class AgentMemory(ABC):
    """What the agent needs from memory: recall before planning, record after."""

    @abstractmethod
    async def recall(
        self,
        goal: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> MemoryContext:
        """Return the relevant, bounded, ranked memory for ``goal``."""
        ...

    @abstractmethod
    async def record_run(self, state: AgentState) -> None:
        """Record an episode (and failure/recovery) from a finished run."""
        ...


class NullAgentMemory(AgentMemory):
    """The no-op memory used when the subsystem is disabled (spec Phase 20K)."""

    async def recall(
        self,
        goal: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> MemoryContext:
        return MemoryContext(query=goal)

    async def record_run(self, state: AgentState) -> None:
        return None


__all__ = [
    "AgentMemory",
    "NullAgentMemory",
    "MemoryContext",
    "MemoryItemView",
]
