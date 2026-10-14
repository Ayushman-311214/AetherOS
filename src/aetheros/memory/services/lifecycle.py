"""
Memory lifecycle / decay / retention (spec Phase 14).

A memory's *status* is derived from its age, confidence and TTL; its *scope*,
*importance*, *type* and *veracity* can veto transitions. The sweep never
deletes -- it demotes along a documented chain so nothing is silently lost.

Allowed transitions (all reversible except DELETED-by-user):

.. code-block:: text

    ACTIVE --> STALE --> DECAYED --> ARCHIVED
      |          |           |            ^
      v          v           v            | reactivation
    LOW_CONFIDENCE (parallel flag: confidence < 0.25, any neglect state)
      .          .           .         (explicit reactivate() verb,
      .          .           .          or automatic re-evaluation when
      EXPIRED (TTL passed; evaluated before the neglect chain)  fresh access
      .          .           .          restores recency)
      .          .           .
    DELETED (user forget() only -- decay never deletes)

Thresholds are half-life multiples of the configured ``decay_halflife_days``
(``recency = 0.5 ** (age_days / halflife)``): STALE below 1/8 (3 half-lives
untouched), DECAYED below 1/64 (6 half-lives), ARCHIVED below 1/512
(9 half-lives). With the default 30-day half-life that is ~90 / ~180 /
~270 days. EPHEMERAL scope archives outright at the STALE point (it was
born short-lived).

What the dimensions mean (kept strictly separate):

* *confidence* (Phase 13) is evidence-derived trust; the lifecycle only
  *reads* it (LOW_CONFIDENCE flag). Decay never writes confidence.
* *freshness/recency* drives the neglect chain; it is NOT a second
  confidence penalty -- an old row keeps its confidence, only its status
  (and hence its recall visibility) changes.
* *importance* exempts: CRITICAL rows never auto-archive (they can still go
  STALE/DECAYED/EXPIRED-by-explicit-TTL, so neglect is visible, but the
  archive step requires a human).
* *trading history* is protected: TRADING type and PREDICTION veracity skip
  the neglect chain entirely (ordinary decay must not destroy them); an
  explicitly-set TTL still expires them, and the confidence flag still
  applies. PERMANENT scope vetoes everything (always ACTIVE).

Projection propagation: the authoritative SQLite row is the source of
truth and its status takes effect immediately for recall (the retriever
filters on status). Derived projections follow on the same pass --
recallable rows (ACTIVE/LOW_CONFIDENCE/STALE/DECAYED) are re-indexed (the
store's INSERT OR REPLACE otherwise drops their vector via FK cascade),
non-recallable rows (ARCHIVED/EXPIRED) have their vectors deleted so no
bypassed filter can leak them. ``verify/repair_projection`` agree: only
recallable rows require vectors.

Reactivation: STALE/DECAYED rows reactivate automatically -- any access
refreshes recency, and the next pass re-evaluates them to ACTIVE (evaluate
is a pure function of current state). ARCHIVED/EXPIRED rows need the
explicit ``manager.reactivate()`` verb (which re-indexes the vector).
DELETED rows are never reactivated by lifecycle (that's explicit user
restore territory, out of scope here).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime
from typing import Any

from ...core.logging import get_logger
from .._clock import utcnow
from ..config import MemoryConfig
from ..domain.enums import (
    RECALLABLE_STATUSES,
    MemoryImportance,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    Veracity,
)
from ..domain.memory import Memory

logger = get_logger("memory.lifecycle")

# Neglect-chain thresholds as half-life multiples: recency < 0.5**N.
_STALE_HALFLIVES = 3  # recency < 1/8
_DECAYED_HALFLIVES = 6  # recency < 1/64
_ARCHIVE_HALFLIVES = 9  # recency < 1/512

# NOTE: the recallable-status set lives in domain.enums as
# RECALLABLE_STATUSES (shared by lifecycle, retriever, repository SQL and
# projection checks).

# Trading history: ordinary decay must not destroy it.
_HISTORY_TYPES = frozenset({MemoryType.TRADING})


class MemoryLifecycle:
    """Decide and apply lifecycle status transitions."""

    def __init__(
        self,
        config: MemoryConfig,
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._config = config
        self._clock = clock

    def recency(self, memory: Memory, *, now: datetime) -> float:
        reference = memory.last_accessed_at or memory.updated_at or memory.created_at
        age_days = max(0.0, (now - reference).total_seconds() / 86400.0)
        return float(math.pow(0.5, age_days / self._config.decay_halflife_days))

    def evaluate(self, memory: Memory, *, now: datetime | None = None) -> MemoryStatus:
        """The status a memory *should* have, without mutating it.

        Pure function of the row + ``now``: re-running over the same store
        is a fixed point (idempotent), and any access that refreshes
        recency automatically restores STALE/DECAYED rows to ACTIVE on the
        next pass (reactivation without a special case).
        """
        now = now or self._clock()

        if memory.scope is MemoryScope.PERMANENT:
            # Permanent memories are always active regardless of age/confidence.
            return MemoryStatus.ACTIVE

        if memory.status is MemoryStatus.DELETED:
            # User action only. Decay never touches deleted rows.
            return MemoryStatus.DELETED

        if memory.is_expired(now=now):
            return MemoryStatus.EXPIRED

        if memory.confidence < 0.25:
            return MemoryStatus.LOW_CONFIDENCE

        if self._is_history_protected(memory):
            # Protected trading history skips the neglect chain: ordinary
            # decay must not destroy it. (TTL-expiry above still applies to
            # an explicitly-set TTL; the confidence flag above still applies
            # as evidence, not age.)
            return MemoryStatus.ACTIVE

        recency = self.recency(memory, now=now)
        if recency < 0.5**_ARCHIVE_HALFLIVES:
            if memory.scope is MemoryScope.EPHEMERAL:
                return MemoryStatus.ARCHIVED
            if memory.importance is MemoryImportance.CRITICAL:
                # Critical rows never auto-archive: neglect stays visible
                # as DECAYED, but the archive step requires a human.
                return MemoryStatus.DECAYED
            return MemoryStatus.ARCHIVED
        if recency < 0.5**_DECAYED_HALFLIVES:
            return MemoryStatus.DECAYED
        # Below ~1/8 of original recency weight (3 half-lives untouched) a
        # non-permanent memory is stale; an EPHEMERAL one archives outright.
        if recency < 0.5**_STALE_HALFLIVES:
            if memory.scope is MemoryScope.EPHEMERAL:
                return MemoryStatus.ARCHIVED
            return MemoryStatus.STALE

        return MemoryStatus.ACTIVE

    @staticmethod
    def _is_history_protected(memory: Memory) -> bool:
        return (
            memory.memory_type in _HISTORY_TYPES
            or memory.veracity is Veracity.PREDICTION
        )

    async def decay_pass(
        self,
        repository: Any,
        vector_index: Any = None,
        *,
        now: datetime | None = None,
        batch_size: int = 500,
        max_batches: int = 0,
    ) -> dict[str, int]:
        """
        Re-evaluate statuses in bounded batches and persist transitions.

        Each transition is version-guarded (a concurrent edit wins; the
        transition is skipped and counted, never clobbered) and propagated
        to the vector projection on the same pass (re-index recallable
        rows, delete vectors of newly non-recallable rows). Returns counts
        by target status plus ``skipped_conflict`` and ``batches`` for
        observability (spec Phase 22). A no-op when decay is disabled in
        config. Idempotent: a second pass over the same store transitions
        nothing (evaluate is a fixed point), and an interrupted pass simply
        resumes from the rows it didn't reach.
        """
        if not self._config.decay_enabled:
            return {}
        if not self._config.enabled:
            return {}

        moment = now or self._clock()
        batch_size = max(1, int(batch_size))
        max_batches = max(0, int(max_batches))
        transitions: dict[str, int] = {}
        batches = 0
        offset = 0
        while True:
            if max_batches and batches >= max_batches:
                break
            batch = await repository.list_by(limit=batch_size, offset=offset)
            if not batch:
                break
            batches += 1
            for memory in batch:
                outcome = await self._transition_one(
                    repository, vector_index, memory, moment
                )
                if outcome is not None:
                    transitions[outcome] = transitions.get(outcome, 0) + 1
            if len(batch) < batch_size:
                break
            offset += len(batch)
        if batches:
            transitions["batches"] = batches
        return transitions

    async def _transition_one(
        self, repository: Any, vector_index: Any, memory: Memory, now: datetime
    ) -> str | None:
        """Evaluate + persist one row. Returns the target status or None."""
        wanted = self.evaluate(memory, now=now)
        if wanted is memory.status:
            return None
        expected_version = memory.version
        memory.status = wanted
        memory.updated_at = now
        memory.version += 1
        won = await repository.update_guarded(memory, expected_version)
        if not won:
            # A concurrent edit won the race: its write stands, our
            # transition is skipped (never clobbered). The next pass will
            # re-evaluate against the fresh row.
            return "skipped_conflict"
        await self._propagate(vector_index, memory)
        return wanted.value

    async def _propagate(self, vector_index: Any, memory: Memory) -> None:
        """Follow a transition into the vector projection.

        Recallable rows are re-embedded (the store's INSERT OR REPLACE
        drops their vector via FK cascade); newly non-recallable rows have
        their vectors deleted so no bypassed filter can leak them. A
        missing index (embedded/test use) simply skips propagation -- the
        authoritative status already governs recall.
        """
        if vector_index is None:
            return
        try:
            if memory.status in RECALLABLE_STATUSES:
                from .writer import MemoryWriter

                await vector_index.index(
                    memory.id, MemoryWriter._embedding_text(memory)
                )
            else:
                await vector_index.delete(memory.id)
        except Exception as exc:
            # Projection follows best-effort; repair_projection reconciles
            # anything missed. The authoritative status already governs.
            # Logged (never silent): a systematic failure here would
            # otherwise masquerade as a healthy pass.
            logger.bind(memory_id=memory.id, error=str(exc)).warning(
                "Vector propagation failed; repair_projection will reconcile."
            )
