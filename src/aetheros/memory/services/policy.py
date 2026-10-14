"""
Memory policy engine (spec Phase 21).

Decides what to remember and for how long, so the rest of the system does not
have to. It classifies a memory into a retention :class:`MemoryScope`, sets a
TTL for the time-bounded scopes, and can veto trivial writes to keep the store
(and later the LLM context, Rule 7) from filling with noise. Deterministic and
side-effect-free apart from stamping the memory it is handed.
"""

from __future__ import annotations

from datetime import timedelta

from ..domain.enums import (
    MemoryImportance,
    MemoryScope,
    MemoryType,
    Veracity,
)
from ..domain.memory import Memory
from .._clock import utcnow

# TTLs for the time-bounded scopes. LONG_TERM and PERMANENT have no TTL.
_SCOPE_TTL = {
    MemoryScope.EPHEMERAL: timedelta(hours=6),
    MemoryScope.SESSION: timedelta(days=1),
    MemoryScope.TASK: timedelta(days=7),
}


class MemoryPolicyEngine:
    """Classify retention and gate trivial writes."""

    def classify(self, memory: Memory) -> MemoryScope:
        # An explicit scope set by the caller wins (the policy never downgrades a
        # deliberate choice).
        if memory.scope is not MemoryScope.LONG_TERM:
            return memory.scope

        # Durable kinds: preferences, procedures, trading history and facts are
        # long-term; a confirmed critical memory is permanent.
        if memory.importance is MemoryImportance.CRITICAL:
            return MemoryScope.PERMANENT

        if memory.memory_type in (
            MemoryType.PREFERENCE,
            MemoryType.PROCEDURAL,
            MemoryType.TRADING,
        ):
            return MemoryScope.LONG_TERM

        if memory.veracity is Veracity.FACT:
            return MemoryScope.LONG_TERM

        # Working memory is session-scoped; episodic/failure default to task.
        if memory.memory_type is MemoryType.WORKING:
            return MemoryScope.SESSION
        if memory.memory_type in (MemoryType.EPISODIC, MemoryType.FAILURE):
            return MemoryScope.TASK

        return MemoryScope.LONG_TERM

    def should_remember(self, memory: Memory) -> bool:
        """Reject trivial, low-confidence ephemeral chatter (Rule 7)."""
        if memory.importance is MemoryImportance.TRIVIAL and memory.confidence < 0.3:
            return False
        return True

    def apply(self, memory: Memory) -> Memory:
        """Stamp scope + expiry on a memory according to policy."""
        scope = self.classify(memory)
        memory.scope = scope
        ttl = _SCOPE_TTL.get(scope)
        if ttl is not None and memory.expires_at is None:
            memory.expires_at = utcnow() + ttl
        return memory
