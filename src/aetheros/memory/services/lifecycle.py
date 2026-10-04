"""
Memory lifecycle / decay (spec Phase 14).

Pure, deterministic status evaluation plus a sweep that applies it. A memory's
*status* is derived from its age, confidence and TTL; its *scope* can veto
expiry (PERMANENT memories never expire, spec Phase 14). The sweep never deletes
-- it demotes (ACTIVE -> STALE/LOW_CONFIDENCE -> ARCHIVED/EXPIRED) so nothing is
silently lost and a later access can revive a STALE memory.
"""

from __future__ import annotations

import math
from datetime import datetime

from ..config import MemoryConfig
from ..domain.enums import MemoryScope, MemoryStatus
from ..domain.memory import Memory
from .._clock import utcnow


class MemoryLifecycle:
    """Decide and apply lifecycle status transitions."""

    def __init__(self, config: MemoryConfig) -> None:
        self._config = config

    def recency(self, memory: Memory, *, now: datetime) -> float:
        reference = memory.last_accessed_at or memory.updated_at or memory.created_at
        age_days = max(0.0, (now - reference).total_seconds() / 86400.0)
        return float(math.pow(0.5, age_days / self._config.decay_halflife_days))

    def evaluate(self, memory: Memory, *, now: datetime | None = None) -> MemoryStatus:
        """The status a memory *should* have, without mutating it."""
        now = now or utcnow()

        if memory.scope is MemoryScope.PERMANENT:
            # Permanent memories are always active regardless of age/confidence.
            return MemoryStatus.ACTIVE

        if memory.is_expired(now=now):
            return MemoryStatus.EXPIRED

        if memory.confidence < 0.25:
            return MemoryStatus.LOW_CONFIDENCE

        recency = self.recency(memory, now=now)
        # Below ~1/8 of original recency weight (3 half-lives untouched) a
        # non-permanent memory is stale; an EPHEMERAL one archives outright.
        if recency < 0.125:
            if memory.scope is MemoryScope.EPHEMERAL:
                return MemoryStatus.ARCHIVED
            return MemoryStatus.STALE

        return MemoryStatus.ACTIVE

    async def decay_pass(self, repository) -> dict[str, int]:
        """
        Re-evaluate every memory's status and persist any transitions.

        Returns a count of transitions by target status for observability
        (spec Phase 22). A no-op when decay is disabled in config.
        """
        if not self._config.decay_enabled:
            return {}

        now = utcnow()
        transitions: dict[str, int] = {}
        for memory in await repository.iter_all():
            new_status = self.evaluate(memory, now=now)
            if new_status is not memory.status:
                memory.status = new_status
                memory.updated_at = now
                await repository.update(memory)
                transitions[new_status.value] = transitions.get(new_status.value, 0) + 1
        return transitions
