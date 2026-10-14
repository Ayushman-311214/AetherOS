"""
Honest write-result types (spec Phase 4 -- "distinguish succeeded, skipped,
failed, unavailable and genuinely durable pending results").

The legacy verbs (``remember`` / ``remember_memory``) return a :class:`Memory`
and raise on failure; they are unchanged. :class:`WriteResult` is the explicit,
result-based alternative returned by :meth:`MemoryManager.store`, so a caller can
tell a durable write apart from a policy skip, an idempotent no-op, an operational
failure, or a disabled subsystem -- without a returned object being mistaken for
proof of persistence (CLAUDE.md Rule: "Never return success for a write that did
not persist.").
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..domain.memory import Memory


class WriteStatus(str, Enum):
    """The five truthful outcomes of an attempted durable write."""

    STORED = "stored"          # durably persisted to the authoritative store
    SKIPPED = "skipped"        # intentionally not written (policy / idempotent hit)
    FAILED = "failed"          # attempted and failed; nothing persisted
    UNAVAILABLE = "unavailable"  # subsystem disabled or not initialized
    PENDING = "pending"        # accepted but durable persistence not yet confirmed


@dataclass(frozen=True, slots=True)
class WriteResult:
    """Outcome of a :meth:`MemoryManager.store` call."""

    status: WriteStatus
    memory: Memory | None = None
    memory_id: str | None = None
    reason: str | None = None

    @property
    def ok(self) -> bool:
        """True when the write was accepted (stored or deliberately skipped)."""
        return self.status in (WriteStatus.STORED, WriteStatus.SKIPPED)

    @property
    def persisted(self) -> bool:
        """True only when the row is durably in the authoritative store."""
        return self.status is WriteStatus.STORED

    # -- factories (keep call sites terse and consistent) ---------------

    @classmethod
    def stored(cls, memory: Memory) -> "WriteResult":
        return cls(WriteStatus.STORED, memory=memory, memory_id=memory.id)

    @classmethod
    def skipped(cls, memory: Memory, reason: str) -> "WriteResult":
        return cls(WriteStatus.SKIPPED, memory=memory, memory_id=memory.id, reason=reason)

    @classmethod
    def failed(cls, reason: str, *, memory: Memory | None = None) -> "WriteResult":
        return cls(
            WriteStatus.FAILED,
            memory=memory,
            memory_id=memory.id if memory else None,
            reason=reason,
        )

    @classmethod
    def unavailable(cls, reason: str) -> "WriteResult":
        return cls(WriteStatus.UNAVAILABLE, reason=reason)
