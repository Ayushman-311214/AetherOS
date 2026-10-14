"""
Memory-domain events (spec Phase 16/22).

Published on the shared EventBus so other subsystems (observability, the HUD,
future learning loops) can react to memory activity without the memory services
depending on them (CLAUDE.md section 16). Payloads are plain already-serialised
values, mirroring the trading events' convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..runtime.events.events import Event


@dataclass(frozen=True, slots=True)
class MemoryStored(Event):
    """A memory was written (created or updated)."""

    memory_id: str = ""
    memory_type: str = ""
    veracity: str = ""
    confidence: float = 0.0
    source_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "veracity": self.veracity,
            "confidence": self.confidence,
            "source_type": self.source_type,
        }


@dataclass(frozen=True, slots=True)
class MemoryRetrieved(Event):
    """A retrieval returned a ranked set of memories."""

    query: str = ""
    result_count: int = 0
    top_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "query": self.query,
            "result_count": self.result_count,
            "top_score": self.top_score,
        }


@dataclass(frozen=True, slots=True)
class MemoryConsolidated(Event):
    """A consolidation pass merged/promoted/archived memories."""

    merged: int = 0
    archived: int = 0
    promoted: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "merged": self.merged,
            "archived": self.archived,
            "promoted": self.promoted,
        }


@dataclass(frozen=True, slots=True)
class MemoryForgotten(Event):
    """A memory was forgotten (soft-deleted or hard-deleted) by the user."""

    memory_id: str = ""
    hard: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "memory_id": self.memory_id,
            "hard": self.hard,
        }
