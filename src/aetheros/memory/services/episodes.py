"""
Episode lifecycle recorder (Phase 10 -- episodic memory foundation).

An explicit, restart-safe lifecycle over the durable ``Episode`` rows that
:class:`ManagerAgentMemory` has been writing single-shot since Phase 20:

.. code-block:: text

    start_episode  ->  record_action / record_observation  ->  finalize_episode
         |                         |                                |
         v                         v                                v
    incomplete row          chronological appends              outcome + ended_at
    (outcome UNKNOWN)       (deduplicated, redacted)           (idempotent)

Design notes (contract compliance):

* **No second bus.** The recorder calls the existing :class:`MemoryManager`
  verbs (``store`` / ``update`` / ``get`` / ``link``); every persisted change
  flows through :class:`MemoryWriter`, so the existing ``MemoryStored`` event
  contract announces it. No new event classes, no new bus.
* **Restart-safe by construction.** The recorder holds no in-memory episode
  state; every mutation is a read-modify-write against the authoritative
  SQLite store, so a restart simply resumes from the stored rows. Incomplete
  episodes (``ended_at`` is ``None``) are listed by :meth:`list_incomplete`.
* **No duplicate episodes.** ``start_episode`` persists through
  :meth:`MemoryManager.store` with the episode id as the idempotency key, so a
  retried start is a safe no-op. ``finalize_episode`` is idempotent: repeating
  it with the same outcome writes nothing; a *different* outcome updates the
  single row in place (historical predictions themselves stay immutable --
  only the episode wrapper is edited, Rule: outcomes are linked records).
* **Duplicate / late / out-of-order appends.** An action (or observation) is
  deduplicated on its ``(name, started_at)`` identity, so a redelivered event
  cannot double-record a step. Appends are re-sorted chronologically on every
  write and every read, so late arrivals slot into place instead of rewriting
  history. Appending to a finalized episode is allowed (late evidence) but
  never moves ``ended_at`` or the recorded outcome.
* **Summaries stay attributable.** The stored ``content`` is always rebuilt
  from the stored action list via :meth:`Episode.summary`; the recorder never
  invents steps and never caches a stale summary string.
* **Redaction before persistence.** Tool arguments pass through
  :func:`redact_keys` (forbidden keys become ``[redacted]``); free-text
  fields (goal, summaries, errors, lessons, provenance, environment) pass
  through :func:`redact_text` for secret-span scrubbing. The write-path
  validator additionally enforces the content policy on the way in.
* **Bounded.** Actions per episode are capped by
  ``MemoryConfig.episode_max_actions`` (oldest dropped first, counted in row
  metadata -- never silently); listing methods take an explicit ``limit`` and
  page internally instead of loading the whole table.
* **Concurrency.** Mutations use the manager's optimistic version guard with
  a bounded retry loop, so two writers appending to one episode converge
  instead of losing steps.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ...core.errors.memory_error import (
    MemoryConflictError,
    MemoryNotFoundError,
    MemoryStorageError,
)
from ...core.logging import get_logger
from ...core.observability.redaction import redact_keys, safe_preview
from .._clock import utcnow
from ..domain.content_policy import redact_text
from ..domain.enums import MemoryStatus, MemoryType, OutcomeStatus
from ..domain.episode import ActionRecord, Episode, EpisodeObservation
from ..domain.memory import Memory, new_id
from ..storage.repository import MemoryRepository
from .results import WriteStatus

if TYPE_CHECKING:
    from .manager import MemoryManager

logger = get_logger("memory.episodes")

_EPISODE_DATA_KEY = "episode"
_FAILURE_LINKS_KEY = "failure_links"

# Bounded optimistic-concurrency retries for a contested episode row.
_MUTATE_ATTEMPTS = 3


class EpisodeRecorder:
    """Explicit episode lifecycle over durable episodic memories.

    Constructed once by :class:`MemoryManager` (see the ``episodes``
    accessor); holds no episode state itself, only the manager handle, the
    resolved config values and the clock.
    """

    def __init__(
        self,
        manager: MemoryManager,
        repository: MemoryRepository,
        *,
        max_actions: int = 200,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._manager = manager
        self._repo = repository
        self._max_actions = max(1, int(max_actions))
        self._clock = clock

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    async def start_episode(
        self,
        goal: str,
        *,
        episode_id: str | None = None,
        task_id: str | None = None,
        session_id: str | None = None,
        environment: dict[str, Any] | None = None,
        relevant_memories: list[str] | None = None,
        provenance: dict[str, Any] | None = None,
        started_at: datetime | None = None,
    ) -> Episode:
        """Persist a new incomplete episode and return it.

        The row is written with outcome ``UNKNOWN`` and no ``ended_at``; it
        becomes attributable history only at :meth:`finalize_episode`.
        Repeating a start with the same ``episode_id`` returns the existing
        episode without duplicating it.

        Honest outcomes: a genuinely stored or idempotent-hit start returns
        the stored episode; a disabled/uninitialized subsystem or a
        policy-declined write returns the episode unsaved (mirroring
        :meth:`MemoryManager.remember_memory` -- recognisable because no row
        exists for its id); a storage/embedding failure raises
        :class:`MemoryStorageError` rather than masquerading as success.
        """
        goal_clean, goal_kinds = redact_text(goal)
        env = redact_keys(environment)
        prov = redact_keys(provenance)
        if goal_kinds:
            prov = {**prov, "redacted_secret_kinds": sorted(set(goal_kinds))}

        episode = Episode(
            id=episode_id or new_id(),
            goal=goal_clean,
            task_id=task_id,
            session_id=session_id,
            environment=env,
            relevant_memories=list(relevant_memories or []),
            provenance=prov,
            started_at=started_at or self._clock(),
        )
        memory = episode.to_memory()
        result = await self._manager.store(memory, idempotency_key=episode.id)

        if result.status is WriteStatus.STORED:
            await self._link_relevant_memories(episode)
            stored = self._row_to_episode(result.memory)
            return stored if stored is not None else episode
        if result.status is WriteStatus.SKIPPED and "already stored" in (
            result.reason or ""
        ):
            # Idempotent hit: the start was already recorded -- return what is
            # stored rather than the fresh (empty) object.
            stored = self._row_to_episode(result.memory)
            if stored is not None:
                return stored
            raise MemoryConflictError(
                f"Episode id {episode.id!r} is already stored but not as a "
                "live episode (it may have been forgotten).",
                hint="Start again with a new episode id.",
            )
        if result.status is WriteStatus.FAILED:
            raise MemoryStorageError(
                f"Episode start {episode.id!r} was attempted but not persisted: "
                f"{result.reason or 'unknown storage failure'}.",
                hint="Check the database and the embedding provider, then retry.",
            )
        # UNAVAILABLE (disabled / not started) or policy-declined SKIPPED:
        # honest no-op, return the unsaved episode like remember_memory does.
        logger.debug("start_episode not persisted: %s", result.reason)
        return episode

    async def _link_relevant_memories(self, episode: Episode) -> None:
        """Link the episode to each relevant memory that actually exists.

        Missing ids are skipped with a warning -- an episode must never fail
        to start because a cited memory is gone. Uses the same ``references``
        link contract retrieval expansion already understands.
        """
        for memory_id in episode.relevant_memories:
            try:
                target = await self._manager.get(memory_id)
            except Exception as exc:  # noqa: BLE001 - defensive, never block start
                logger.warning("Relevant-memory lookup failed: %s", exc)
                target = None
            if target is None or target.status is MemoryStatus.DELETED:
                logger.warning("Relevant memory %r missing; link skipped.", memory_id)
                continue
            await self._manager.link(
                episode.id,
                memory_id,
                link_type="references",
                metadata={"kind": "episode_evidence"},
            )

    # ------------------------------------------------------------------
    # Append (actions / observations)
    # ------------------------------------------------------------------

    async def record_action(
        self,
        episode_id: str,
        name: str,
        *,
        status: OutcomeStatus = OutcomeStatus.UNKNOWN,
        arguments: dict[str, Any] | None = None,
        result_summary: str = "",
        error: str | None = None,
        duration_ms: float | None = None,
        started_at: datetime | None = None,
    ) -> Episode:
        """Append one tool call / agent step to a live episode.

        ``arguments`` are redacted (forbidden keys) and the summary/error are
        secret-scrubbed before persistence. A redelivered event -- same name
        and timestamp -- is a no-op returning the episode unchanged.
        """
        when = started_at or self._clock()
        summary_clean, _ = redact_text(safe_preview(result_summary))
        error_clean: str | None = None
        if error:
            error_clean, _ = redact_text(safe_preview(error))
        action = ActionRecord(
            name=name,
            arguments=redact_keys(arguments),
            status=status,
            result_summary=summary_clean,
            error=error_clean,
            duration_ms=duration_ms,
            started_at=when,
        )

        def _append(episode: Episode, _row: Memory) -> bool:
            key = (action.name, action.started_at.isoformat())
            for existing in episode.actions:
                if (existing.name, existing.started_at.isoformat()) == key:
                    return False  # duplicate delivery -- no write
            episode.actions.append(action)
            return True

        updated, _ = await self._mutate(episode_id, _append)
        return updated

    async def record_observation(
        self,
        episode_id: str,
        key: str,
        content: str,
        *,
        observed_at: datetime | None = None,
    ) -> Episode:
        """Append one timestamped observation to a live episode.

        Observations are point-in-time notes (market state, screen state);
        unlike working-memory current-observations they are historical record,
        so repeats accumulate rather than replace -- except exact redeliveries
        (same key and timestamp), which are a no-op.
        """
        when = observed_at or self._clock()
        content_clean, _ = redact_text(safe_preview(content))
        observation = EpisodeObservation(
            key=key, content=content_clean, observed_at=when
        )

        def _append(episode: Episode, _row: Memory) -> bool:
            stamp = observation.observed_at.isoformat()
            for existing in episode.observations:
                if (existing.key, existing.observed_at.isoformat()) == (key, stamp):
                    return False
            episode.observations.append(observation)
            return True

        updated, _ = await self._mutate(episode_id, _append)
        return updated

    # ------------------------------------------------------------------
    # Failure / recovery links
    # ------------------------------------------------------------------

    async def attach_failure(self, episode_id: str, failure_id: str) -> None:
        """Link an existing failure memory to its episode (idempotent).

        Uses the same ``derived_from`` / ``failure_in_episode`` link contract
        the agent integration writes, so retrieval expansion sees one shape.
        Attachment is recorded on the episode row itself, making a repeated
        attach a no-op -- the graph link is only created when the row
        actually changed, so repeats never duplicate link rows.
        """
        row = await self._manager.get(episode_id)
        if self._row_to_episode(row) is None:
            raise MemoryNotFoundError(f"No live episode with id {episode_id!r}.")
        failure = await self._manager.get(failure_id)
        if failure is None or failure.status is MemoryStatus.DELETED:
            raise MemoryNotFoundError(f"No live failure memory {failure_id!r}.")

        def _attach(episode: Episode, row: Memory) -> bool:
            attached = list(row.data.get(_FAILURE_LINKS_KEY, []))
            if failure_id in attached:
                return False
            attached.append(failure_id)
            row.data[_FAILURE_LINKS_KEY] = attached
            return True

        _, did_write = await self._mutate(episode_id, _attach)
        if not did_write:
            return  # already attached -- no duplicate link row
        await self._manager.link(
            failure_id,
            episode_id,
            link_type="derived_from",
            metadata={"kind": "failure_in_episode"},
        )

    async def episode_failures(self, episode_id: str) -> list[Memory]:
        """Failure memories attached to an episode (missing ones skipped)."""
        row = await self._manager.get(episode_id)
        if self._row_to_episode(row) is None:
            raise MemoryNotFoundError(f"No live episode with id {episode_id!r}.")
        assert row is not None
        out: list[Memory] = []
        for failure_id in row.data.get(_FAILURE_LINKS_KEY, []):
            failure = await self._manager.get(failure_id)
            if failure is not None and failure.status is not MemoryStatus.DELETED:
                out.append(failure)
        return out

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    async def finalize_episode(
        self,
        episode_id: str,
        status: OutcomeStatus,
        *,
        detail: str = "",
        metrics: dict[str, Any] | None = None,
        lessons: list[str] | None = None,
    ) -> Episode:
        """Close an episode with its outcome (idempotent).

        Repeating a finalization with the same status writes nothing.
        Finalizing with a *different* status updates the single row in place
        -- never a second episode row. New lessons are appended without
        duplicating exact repeats; the summary is rebuilt from stored steps.
        """
        detail_clean, _ = redact_text(safe_preview(detail))
        lesson_list = [
            redact_text(safe_preview(lesson))[0] for lesson in (lessons or [])
        ]
        metrics_clean = redact_keys(metrics)

        def _finalize(episode: Episode, _row: Memory) -> bool:
            if episode.ended_at is not None and episode.outcome.status is status:
                return False  # repeated finalization -- no write
            episode.outcome.status = status
            episode.outcome.detail = detail_clean
            episode.outcome.metrics = metrics_clean
            for lesson in lesson_list:
                if lesson and lesson not in episode.lessons:
                    episode.lessons.append(lesson)
            episode.ended_at = self._clock()
            return True

        updated, _ = await self._mutate(episode_id, _finalize)
        return updated

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def get_episode(self, episode_id: str) -> Episode | None:
        """Rebuild one episode from its stored row (chronological).

        Returns ``None`` for a missing id, a non-episode row, a soft-deleted
        row, or a row whose payload no longer parses -- never raises for a
        read.
        """
        try:
            row = await self._manager.get(episode_id)
        except Exception as exc:  # noqa: BLE001 - reads degrade to "no episode"
            logger.warning("get_episode read failed: %s", exc)
            return None
        return self._row_to_episode(row)

    async def list_episodes(
        self,
        *,
        task_id: str | None = None,
        session_id: str | None = None,
        status: OutcomeStatus | None = None,
        include_incomplete: bool = True,
        limit: int = 100,
    ) -> list[Episode]:
        """Episodes in scope, newest first, bounded by ``limit``.

        ``task_id`` / ``session_id`` scope the query (scope isolation: one
        session's episodes never appear in another's listing); ``status``
        filters on the recorded outcome; incomplete episodes are included
        unless ``include_incomplete`` is ``False``.
        """
        bound = max(1, int(limit))
        candidates: list[Memory] = []
        if task_id is not None:
            candidates = await self._repo.find_by_metadata("task_id", task_id)
        elif session_id is not None:
            candidates = await self._repo.find_by_metadata("session_id", session_id)
        else:
            candidates = await self._repo.list_by(
                memory_type=MemoryType.EPISODIC.value, limit=bound * 2
            )
        episodes: list[Episode] = []
        for row in candidates:
            episode = self._row_to_episode(row)
            if episode is None:
                continue
            if session_id is not None and task_id is not None:
                if episode.session_id != session_id:
                    continue
            if status is not None and episode.outcome.status is not status:
                continue
            if not include_incomplete and episode.ended_at is None:
                continue
            episodes.append(episode)
        episodes.sort(key=lambda e: e.started_at.isoformat(), reverse=True)
        return episodes[:bound]

    async def list_incomplete(self, *, limit: int = 100) -> list[Episode]:
        """Episodes started but never finalized (interrupted work to resume).

        Pages the episodic rows in bounded batches so recovery never loads
        the whole table.
        """
        bound = max(1, int(limit))
        found: list[Episode] = []
        offset = 0
        for _ in range(10):  # hard page bound: at most 1000 rows scanned
            batch = await self._repo.list_by(
                memory_type=MemoryType.EPISODIC.value, limit=100, offset=offset
            )
            if not batch:
                break
            offset += len(batch)
            for row in batch:
                episode = self._row_to_episode(row)
                if episode is not None and episode.ended_at is None:
                    found.append(episode)
                    if len(found) >= bound:
                        return found
        return found

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _row_to_episode(self, row: Memory | None) -> Episode | None:
        """Rebuild an episode from a stored row, or ``None`` if not usable."""
        if row is None:
            return None
        if row.memory_type is not MemoryType.EPISODIC:
            return None
        if row.status is MemoryStatus.DELETED:
            return None
        payload = row.data.get(_EPISODE_DATA_KEY)
        if not isinstance(payload, dict):
            return None
        try:
            episode = Episode.from_dict(payload)
        except Exception as exc:  # noqa: BLE001 - corrupt payload reads as absent
            logger.warning("Unparseable episode payload for %r: %s", row.id, exc)
            return None
        episode.actions.sort(key=lambda a: a.started_at.isoformat())
        episode.observations.sort(key=lambda o: o.observed_at.isoformat())
        return episode

    async def _mutate(
        self,
        episode_id: str,
        mutate: Callable[[Episode, Memory], bool],
    ) -> tuple[Episode, bool]:
        """Read-modify-write one episode row with bounded version retries.

        ``mutate`` edits the rebuilt episode in place and returns ``True`` when
        a write is needed (``False`` = idempotent no-op, no version bump, no
        re-index). Actions/observations are re-sorted and capped before every
        write; the content summary is always rebuilt from the stored steps.
        Returns the episode and whether a write happened.
        """
        last_conflict: MemoryConflictError | None = None
        for _ in range(_MUTATE_ATTEMPTS):
            row = await self._manager.get(episode_id)
            episode = self._row_to_episode(row)
            if episode is None:
                raise MemoryNotFoundError(
                    f"No live episode with id {episode_id!r}.",
                    hint="Start the episode first, or check for a typo/forgotten id.",
                )
            assert row is not None
            if not mutate(episode, row):
                return episode, False
            dropped = self._cap_actions(episode)
            metadata = {
                k: v
                for k, v in {
                    "episode_id": episode.id,
                    "task_id": episode.task_id,
                    "session_id": episode.session_id,
                }.items()
                if v is not None
            }
            if dropped:
                metadata["truncated_actions"] = (
                    int(row.metadata.get("truncated_actions", 0)) + dropped
                )
            data = dict(row.data)
            data[_EPISODE_DATA_KEY] = episode.to_dict()
            try:
                updated = await self._manager.update(
                    episode_id,
                    expected_version=row.version,
                    content=episode.summary(),
                    data=data,
                    metadata=metadata,
                )
            except MemoryConflictError as exc:
                last_conflict = exc
                continue
            rebuilt = self._row_to_episode(updated)
            if rebuilt is None:  # pragma: no cover - defensive
                raise MemoryStorageError(
                    f"Episode {episode_id!r} unreadable right after its own update."
                )
            return rebuilt, True
        raise last_conflict or MemoryConflictError(
            f"Episode {episode_id!r} is under contention; retry the append."
        )

    def _cap_actions(self, episode: Episode) -> int:
        """Enforce the per-episode action bound; return how many were dropped."""
        overflow = len(episode.actions) - self._max_actions
        if overflow <= 0:
            return 0
        episode.actions.sort(key=lambda a: a.started_at.isoformat())
        del episode.actions[:overflow]
        return overflow
