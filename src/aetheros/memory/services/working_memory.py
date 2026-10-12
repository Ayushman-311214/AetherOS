"""
Working (short-term) memory (spec Phase 9).

A bounded, in-process, *ephemeral* scratchpad for live reasoning. It holds the
transient context of active work -- the current task/goal/plan, the application
and screen in focus, the instrument and timeframe under analysis, recent tool
calls, decisions and, kept deliberately apart, the *current observations* of the
world (screen state, market state).

Design invariants (spec Phase 9):

* **Ephemeral by default.** Nothing here is persisted. It is the live context
  window and is lost on process restart *by design*; only an explicit
  :meth:`promote` (evidence selection) copies chosen items into durable
  long-term memory. We never turn all working state into long-term memory.
* **Session / task scoped.** Every item belongs to a ``session_id`` and may
  belong to a ``task_id``. Sessions are isolated: one session never reads or
  evicts another's items, and completing a task or ending a session purges only
  that scope.
* **Bounded.** Each session is capped at ``capacity`` general items; when full
  the least-important, oldest item is evicted. Current-observation state is
  keyed, so it is naturally bounded by the number of distinct observation keys.
* **Expiring.** Items may carry a TTL; expired items are invisible to reads and
  removed by :meth:`sweep_expired` / on access. A default session TTL can be
  configured; ``0`` means no expiry.
* **Freshness / sequence safe.** Current observations are updated through
  :meth:`observe`, which rejects a *stale* update (an older ``sequence``, or an
  older ``observed_at`` when sequences tie) so a delayed observation can never
  overwrite newer known state.
* **Concurrency safe.** All shared state is guarded by a re-entrant lock, so
  updates arriving from different threads (e.g. desktop automation run via
  ``asyncio.to_thread``) cannot corrupt the structure.

Current observations always represent *now*; they are not historical references.
Historical guidance lives in long-term memory and is retrieved separately -- a
retrieved memory never overrides a current observation (CLAUDE.md: current
verified state overrides historical memory).
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .._clock import utcnow
from ..domain.enums import (
    MemoryImportance,
    MemoryScope,
    MemoryType,
    SourceType,
    Veracity,
)
from ..domain.memory import Memory, MemorySource

_DEFAULT_SESSION = "default"


@dataclass(slots=True)
class WorkingItem:
    """One entry in the working set.

    ``session_id`` / ``task_id`` scope it; ``expires_at`` (if set) bounds its
    life; ``sequence`` / ``observed_at`` order current-observation updates;
    ``is_evidence`` marks it for explicit durable promotion.
    """

    kind: str
    content: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = _DEFAULT_SESSION
    task_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    importance: MemoryImportance = MemoryImportance.NORMAL
    created_at: datetime = field(default_factory=utcnow)
    observed_at: datetime | None = None
    sequence: int | None = None
    expires_at: datetime | None = None
    is_evidence: bool = False

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "content": self.content,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "data": dict(self.data),
            "importance": int(self.importance),
            "created_at": self.created_at.isoformat(),
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "sequence": self.sequence,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_evidence": self.is_evidence,
        }


@dataclass(frozen=True, slots=True)
class ObservationResult:
    """Outcome of an :meth:`WorkingMemory.observe` call.

    ``accepted`` is ``False`` when the update was *stale* (older than the
    current known observation); ``item`` is always the observation now in effect,
    so a caller can read the current truth regardless.
    """

    accepted: bool
    item: WorkingItem
    reason: str | None = None


class WorkingMemory:
    """Bounded, session-scoped, ephemeral live context (spec Phase 9)."""

    def __init__(
        self,
        *,
        capacity: int = 50,
        session_id: str | None = None,
        default_ttl_seconds: float = 0.0,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._capacity = max(1, capacity)
        self._default_ttl = max(0.0, float(default_ttl_seconds))
        self._clock = clock
        self.session_id = session_id or _DEFAULT_SESSION
        # Per-session general items (historical scratch / decisions / tool calls).
        self._sessions: dict[str, deque[WorkingItem]] = {}
        # Per-session current observations, keyed by observation key.
        self._observations: dict[str, dict[str, WorkingItem]] = {}
        # Re-entrant so a public method may call another under the same lock.
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve(self, session_id: str | None) -> str:
        return session_id or self.session_id

    def _expiry_for(self, ttl_seconds: float | None) -> datetime | None:
        ttl = self._default_ttl if ttl_seconds is None else max(0.0, float(ttl_seconds))
        if ttl <= 0.0:
            return None
        return self._clock() + timedelta(seconds=ttl)

    def _bucket(self, session_id: str) -> deque[WorkingItem]:
        return self._sessions.setdefault(session_id, deque())

    def _obs_bucket(self, session_id: str) -> dict[str, WorkingItem]:
        return self._observations.setdefault(session_id, {})

    def _purge_expired_locked(self, now: datetime) -> int:
        removed = 0
        for sid, bucket in list(self._sessions.items()):
            kept = deque(it for it in bucket if not it.is_expired(now))
            removed += len(bucket) - len(kept)
            if kept:
                self._sessions[sid] = kept
            else:
                del self._sessions[sid]
        for sid, obs in list(self._observations.items()):
            live = {k: it for k, it in obs.items() if not it.is_expired(now)}
            removed += len(obs) - len(live)
            if live:
                self._observations[sid] = live
            else:
                del self._observations[sid]
        return removed

    def _enforce_capacity_locked(self, bucket: deque[WorkingItem]) -> None:
        while len(bucket) > self._capacity:
            # Evict the lowest-importance item among the oldest half, so recent
            # and important context survives (bounded window).
            oldest = list(bucket)[: max(1, len(bucket) // 2)]
            victim = min(oldest, key=lambda it: (int(it.importance), it.created_at))
            bucket.remove(victim)

    # ------------------------------------------------------------------
    # General items (historical scratch)
    # ------------------------------------------------------------------

    def add(
        self,
        kind: str,
        content: str,
        *,
        data: dict[str, Any] | None = None,
        importance: MemoryImportance = MemoryImportance.NORMAL,
        session_id: str | None = None,
        task_id: str | None = None,
        ttl_seconds: float | None = None,
        is_evidence: bool = False,
    ) -> WorkingItem:
        sid = self._resolve(session_id)
        item = WorkingItem(
            kind=kind,
            content=content,
            session_id=sid,
            task_id=task_id,
            data=data or {},
            importance=importance,
            expires_at=self._expiry_for(ttl_seconds),
            is_evidence=is_evidence,
        )
        with self._lock:
            bucket = self._bucket(sid)
            bucket.append(item)
            self._enforce_capacity_locked(bucket)
        return item

    def update(
        self,
        item_id: str,
        *,
        content: str | None = None,
        session_id: str | None = None,
        **data: Any,
    ) -> bool:
        sid = self._resolve(session_id)
        now = self._clock()
        with self._lock:
            for item in self._bucket(sid):
                if item.id == item_id and not item.is_expired(now):
                    if content is not None:
                        item.content = content
                    item.data.update(data)
                    return True
        return False

    def remove(self, item_id: str, *, session_id: str | None = None) -> bool:
        sid = self._resolve(session_id)
        with self._lock:
            bucket = self._sessions.get(sid)
            if bucket is None:
                return False
            for item in list(bucket):
                if item.id == item_id:
                    bucket.remove(item)
                    return True
        return False

    def mark_evidence(
        self, item_id: str, *, is_evidence: bool = True, session_id: str | None = None
    ) -> bool:
        """Flag (or unflag) an item for explicit durable promotion."""
        sid = self._resolve(session_id)
        with self._lock:
            for item in self._bucket(sid):
                if item.id == item_id:
                    item.is_evidence = is_evidence
                    return True
            for item in self._obs_bucket(sid).values():
                if item.id == item_id:
                    item.is_evidence = is_evidence
                    return True
        return False

    # ------------------------------------------------------------------
    # Current observations (freshness / sequence controlled)
    # ------------------------------------------------------------------

    def observe(
        self,
        key: str,
        content: str,
        *,
        sequence: int | None = None,
        observed_at: datetime | None = None,
        session_id: str | None = None,
        data: dict[str, Any] | None = None,
        importance: MemoryImportance = MemoryImportance.NORMAL,
        ttl_seconds: float | None = None,
    ) -> ObservationResult:
        """Set the current observation for ``key``, rejecting stale updates.

        A new observation supersedes the existing one only if it is *not older*:
        a higher ``sequence`` wins; when sequences tie (or are both ``None``) a
        later ``observed_at`` wins. A strictly older update is rejected and the
        existing (newer) observation remains in effect -- so a delayed/out-of-
        order observation can never overwrite newer known state.
        """
        sid = self._resolve(session_id)
        when = observed_at or self._clock()
        with self._lock:
            obs = self._obs_bucket(sid)
            existing = obs.get(key)
            if existing is not None and not existing.is_expired(self._clock()):
                if not self._is_newer(sequence, when, existing):
                    return ObservationResult(
                        accepted=False,
                        item=existing,
                        reason="stale: not newer than current observation",
                    )
            item = WorkingItem(
                kind="observation",
                content=content,
                session_id=sid,
                data=data or {},
                importance=importance,
                observed_at=when,
                sequence=sequence,
                expires_at=self._expiry_for(ttl_seconds),
            )
            obs[key] = item
            return ObservationResult(accepted=True, item=item)

    @staticmethod
    def _is_newer(
        sequence: int | None, when: datetime, existing: WorkingItem
    ) -> bool:
        """Is a candidate (sequence, when) newer than the existing observation?"""
        if sequence is not None and existing.sequence is not None:
            if sequence != existing.sequence:
                return sequence > existing.sequence
            # Equal sequence -> fall through to timestamp tie-break.
        elif sequence is not None and existing.sequence is None:
            return True  # a sequenced update is more authoritative than none
        elif sequence is None and existing.sequence is not None:
            return False  # never let an unsequenced update displace a sequenced one
        existing_when = existing.observed_at or existing.created_at
        return when >= existing_when

    def current_observation(
        self, key: str, *, session_id: str | None = None
    ) -> WorkingItem | None:
        sid = self._resolve(session_id)
        now = self._clock()
        with self._lock:
            item = self._obs_bucket(sid).get(key)
            if item is None or item.is_expired(now):
                return None
            return item

    def current_observations(
        self, *, session_id: str | None = None
    ) -> list[WorkingItem]:
        sid = self._resolve(session_id)
        now = self._clock()
        with self._lock:
            return [it for it in self._obs_bucket(sid).values() if not it.is_expired(now)]

    # ------------------------------------------------------------------
    # Cleanup / lifecycle
    # ------------------------------------------------------------------

    def end_session(self, session_id: str | None = None) -> int:
        """Purge every item and observation for a session. Returns count removed."""
        sid = self._resolve(session_id)
        with self._lock:
            removed = len(self._sessions.get(sid, ())) + len(
                self._observations.get(sid, {})
            )
            self._sessions.pop(sid, None)
            self._observations.pop(sid, None)
        return removed

    def complete_task(self, task_id: str, *, session_id: str | None = None) -> int:
        """Purge items tagged with ``task_id`` (within a session). Returns count."""
        sid = self._resolve(session_id)
        with self._lock:
            bucket = self._sessions.get(sid)
            if bucket is None:
                return 0
            kept = deque(it for it in bucket if it.task_id != task_id)
            removed = len(bucket) - len(kept)
            if kept:
                self._sessions[sid] = kept
            else:
                self._sessions.pop(sid, None)
        return removed

    def sweep_expired(self) -> int:
        """Remove all expired items/observations across sessions. Returns count."""
        with self._lock:
            return self._purge_expired_locked(self._clock())

    def clear(self, *, session_id: str | None = None) -> None:
        """Clear one session (if given) or the entire working set."""
        with self._lock:
            if session_id is None:
                self._sessions.clear()
                self._observations.clear()
            else:
                self._sessions.pop(session_id, None)
                self._observations.pop(session_id, None)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def items(
        self, *, kind: str | None = None, session_id: str | None = None
    ) -> list[WorkingItem]:
        sid = self._resolve(session_id)
        now = self._clock()
        with self._lock:
            live = [it for it in self._bucket(sid) if not it.is_expired(now)]
        if kind is None:
            return live
        return [it for it in live if it.kind == kind]

    def sessions(self) -> list[str]:
        with self._lock:
            return sorted(set(self._sessions) | set(self._observations))

    def __len__(self) -> int:
        now = self._clock()
        with self._lock:
            total = 0
            for bucket in self._sessions.values():
                total += sum(1 for it in bucket if not it.is_expired(now))
            for obs in self._observations.values():
                total += sum(1 for it in obs.values() if not it.is_expired(now))
            return total

    def summarize(self, *, session_id: str | None = None) -> str:
        """A compact textual summary of a session's working set."""
        sid = self._resolve(session_id)
        items = self.items(session_id=sid)
        observations = self.current_observations(session_id=sid)
        if not items and not observations:
            return "Working memory is empty."
        lines = [f"Working memory ({len(items) + len(observations)} items):"]
        for item in observations:
            lines.append(f"- [observation] {item.content}")
        for item in items:
            lines.append(f"- [{item.kind}] {item.content}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Promotion to long-term (explicit evidence selection, spec Phase 9)
    # ------------------------------------------------------------------

    def to_memories(
        self,
        *,
        min_importance: MemoryImportance = MemoryImportance.HIGH,
        session_id: str | None = None,
        only_evidence: bool = False,
    ) -> list[Memory]:
        """Project keep-worthy working items into long-term Memory records.

        With ``only_evidence=True`` only items explicitly marked via
        :meth:`mark_evidence` are promoted (explicit selection for durable
        formation); otherwise the importance threshold selects them. Observations
        become ``OBSERVATION`` veracity, general items ``SEMANTIC``.
        """
        sid = self._resolve(session_id)
        now = self._clock()
        out: list[Memory] = []
        with self._lock:
            candidates: list[WorkingItem] = [
                it for it in self._bucket(sid) if not it.is_expired(now)
            ]
            candidates += [
                it for it in self._obs_bucket(sid).values() if not it.is_expired(now)
            ]
        for item in candidates:
            if only_evidence:
                if not item.is_evidence:
                    continue
            elif int(item.importance) < int(min_importance):
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
                    metadata={"session_id": sid},
                )
            )
        return out
