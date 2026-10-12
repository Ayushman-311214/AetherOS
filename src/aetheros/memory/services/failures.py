"""
Failure and recovery memory recorder (Phase 11).

An explicit, restart-safe lifecycle over the durable ``FailureRecord`` rows
that :class:`ManagerAgentMemory` has been writing single-shot since Phase 20:

.. code-block:: text

    record_failure -> record_attempt [x N] -> resolve / confirm_cause
         |                |                      |
         v                v                      v
    open row        attempt log grows      recovered flag / confirmed cause
    (OBSERVATION)   (bounded, redacted)    (single row, idempotent)

Design notes (contract compliance):

* **No second bus.** The recorder calls the existing :class:`MemoryManager`
  verbs (``store`` / ``update`` / ``get`` / ``link``); every persisted change
  flows through :class:`MemoryWriter`, so the existing ``MemoryStored`` event
  contract announces it. No new event classes, no new bus. The verified
  existing failure/recovery integration -- the agent's deterministic failure
  ids and the ``derived_from`` / ``failure_in_episode`` link contract -- is
  reused unchanged, so agent-written rows read back through this recorder.
* **Observed facts vs inferred causes.** ``observed_symptoms`` are facts.
  ``suspected_cause`` is an unverified hypothesis and is quarantined: it is
  stored in the payload (so it is not lost) but excluded from the searchable
  summary until :meth:`confirm_cause` is called explicitly. An unverified
  suspected cause must never read as a confirmed fact in retrieval.
* **No automatic procedure revision.** :meth:`link_alternative` records a
  ``recovered_by`` edge from the failure to the successful alternative (a
  procedure or any memory) with source evidence, but never edits the
  procedure itself. Procedure evolution (a later phase) consumes the
  evidence contract documented below; this phase only gathers it.
* **Bound and redact error payloads.** Error text, symptoms, attempt details
  and context pass through forbidden-key redaction + secret-span scrubbing
  and length bounding before persistence. A huge traceback becomes a bounded
  preview; a credential in an exception message, URL, request body or tool
  output never reaches the row.
* **Restart-safe by construction.** The recorder holds no in-memory failure
  state; every mutation is a read-modify-write against the authoritative
  SQLite store. Open failures (no successful recovery) are listed by
  :meth:`list_open`.
* **Duplicate-safe.** ``record_failure`` persists through
  :meth:`MemoryManager.store` with the failure id as the idempotency key, so
  a redelivered failure is a safe no-op. A repeated identical attempt appends
  nothing. Links are created once (row-recorded attachment, like episodes).

Evidence contract for later procedure evolution (consumed, not built, here):

* A failure row carries ``failure_type``, observed ``error`` + ``symptoms``,
  the failing ``action``, the ordered ``attempts`` log (each with action,
  status, detail, timestamp), ``successful_recovery`` when one worked, and
  ``recovered_by`` links to the alternative that actually succeeded (with
  ``evidence`` metadata naming the source: the episode id and the successful
  step). A later phase can mine "failures of type T with successful recovery
  R" into procedure fallbacks -- from these rows and links alone, without
  re-deriving anything.
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
from ..domain.memory import Memory, new_id
from ..domain.preference import FailureRecord, RecoveryAttempt
from ..storage.repository import MemoryRepository
from .results import WriteStatus

if TYPE_CHECKING:
    from .manager import MemoryManager

logger = get_logger("memory.failures")

_FAILURE_DATA_KEY = "failure"

# Bounded optimistic-concurrency retries for a contested failure row.
_MUTATE_ATTEMPTS = 3

# Hard cap on recorded attempts per failure: an unbounded retry loop must not
# produce an unbounded row. Oldest attempts are dropped first and counted.
_MAX_ATTEMPTS = 50


class FailureRecorder:
    """Explicit failure/recovery lifecycle over durable failure memories.

    Constructed once by :class:`MemoryManager` (see the ``failures``
    accessor); holds no failure state itself, only the manager handle, the
    repository handle and the clock.
    """

    def __init__(
        self,
        manager: MemoryManager,
        repository: MemoryRepository,
        *,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._manager = manager
        self._repo = repository
        self._clock = clock

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    async def record_failure(
        self,
        failure_type: str,
        error: str,
        *,
        failure_id: str | None = None,
        action: str = "",
        arguments: dict[str, Any] | None = None,
        observed_symptoms: list[str] | None = None,
        suspected_cause: str = "",
        context: dict[str, Any] | None = None,
        environment: dict[str, Any] | None = None,
        episode_id: str | None = None,
        procedure_id: str | None = None,
    ) -> FailureRecord:
        """Persist a new open failure and return it.

        ``arguments`` are the failing call's argument *names* (never values --
        values may be passwords); everything free-text is secret-scrubbed and
        bounded before persistence. Repeating a record with the same
        ``failure_id`` returns the stored failure without duplicating it.
        When the subsystem is disabled (or not initialized) the record is
        returned unsaved -- recognisable because no row exists for its id.
        A storage failure raises :class:`MemoryStorageError`, never a phantom
        success.
        """
        error_clean, _ = redact_text(safe_preview(error))
        symptoms = [
            redact_text(safe_preview(s))[0] for s in (observed_symptoms or [])
        ]
        cause_clean, _ = redact_text(safe_preview(suspected_cause))
        ctx = redact_keys(context)
        if arguments:
            # Names only -- the caller passes {"argument_names": [...]} or a
            # bare names mapping; any forbidden key is still redacted.
            ctx = {**ctx, "failing_call": redact_keys(arguments)}
        env = redact_keys(environment)

        record = FailureRecord(
            id=failure_id or new_id(),
            failure_type=failure_type,
            error=error_clean,
            action=action,
            context=ctx,
            environment=env,
            observed_symptoms=symptoms,
            suspected_cause=cause_clean,
            episode_id=episode_id,
            procedure_id=procedure_id,
        )
        memory = record.to_memory()
        result = await self._manager.store(memory, idempotency_key=record.id)

        if result.status is WriteStatus.STORED:
            await self._link_context(record)
            stored = self._row_to_failure(result.memory)
            return stored if stored is not None else record
        if result.status is WriteStatus.SKIPPED and "already stored" in (
            result.reason or ""
        ):
            stored = self._row_to_failure(result.memory)
            if stored is not None:
                return stored
            raise MemoryConflictError(
                f"Failure id {record.id!r} is already stored but not as a "
                "live failure (it may have been forgotten).",
                hint="Record again with a new failure id.",
            )
        if result.status is WriteStatus.FAILED:
            raise MemoryStorageError(
                f"Failure record {record.id!r} was attempted but not persisted: "
                f"{result.reason or 'unknown storage failure'}.",
                hint="Check the database and the embedding provider, then retry.",
            )
        logger.debug("record_failure not persisted: %s", result.reason)
        return record

    async def _link_context(self, record: FailureRecord) -> None:
        """Link the failure to its episode/procedure where they exist.

        Missing targets are skipped with a warning -- a failure must never
        fail to record because a cited row is gone. Late links (targets that
        appear afterwards) are handled by :meth:`link_episode` /
        :meth:`link_procedure`.
        """
        if record.episode_id is not None:
            await self._link_if_live(
                record.id,
                record.episode_id,
                link_type="derived_from",
                metadata={"kind": "failure_in_episode"},
            )
        if record.procedure_id is not None:
            await self._link_if_live(
                record.id,
                record.procedure_id,
                link_type="observed_in",
                metadata={"kind": "failure_in_procedure"},
            )

    async def _link_if_live(
        self,
        from_id: str,
        to_id: str,
        *,
        link_type: str,
        metadata: dict[str, Any],
    ) -> bool:
        """Create a link only when the target row is live. Never raises."""
        try:
            target = await self._manager.get(to_id)
        except Exception as exc:  # noqa: BLE001 - defensive, never block record
            logger.warning("Link-target lookup failed: %s", exc)
            return False
        if target is None or target.status is MemoryStatus.DELETED:
            logger.warning("Link target %r missing; link skipped.", to_id)
            return False
        await self._manager.link(
            from_id, to_id, link_type=link_type, metadata=metadata
        )
        return True

    async def link_episode(self, failure_id: str, episode_id: str) -> None:
        """Attach a late-arriving episode link (idempotent, never raises
        for a missing target -- it logs and skips)."""
        row = await self._manager.get(failure_id)
        record = self._row_to_failure(row)
        if record is None:
            raise MemoryNotFoundError(f"No live failure with id {failure_id!r}.")

        def _attach(record: FailureRecord, row: Memory) -> bool:
            if record.episode_id == episode_id:
                return False
            record.episode_id = episode_id
            return True

        _, did_write = await self._mutate(failure_id, _attach)
        if not did_write:
            return  # already attached -- no duplicate link row
        await self._link_if_live(
            failure_id,
            episode_id,
            link_type="derived_from",
            metadata={"kind": "failure_in_episode"},
        )

    async def link_procedure(self, failure_id: str, procedure_id: str) -> None:
        """Attach a late-arriving procedure link (idempotent, same shape)."""
        row = await self._manager.get(failure_id)
        record = self._row_to_failure(row)
        if record is None:
            raise MemoryNotFoundError(f"No live failure with id {failure_id!r}.")

        def _attach(record: FailureRecord, row: Memory) -> bool:
            if record.procedure_id == procedure_id:
                return False
            record.procedure_id = procedure_id
            return True

        _, did_write = await self._mutate(failure_id, _attach)
        if not did_write:
            return  # already attached -- no duplicate link row
        await self._link_if_live(
            failure_id,
            procedure_id,
            link_type="observed_in",
            metadata={"kind": "failure_in_procedure"},
        )

    # ------------------------------------------------------------------
    # Attempts
    # ------------------------------------------------------------------

    async def record_attempt(
        self,
        failure_id: str,
        action: str,
        *,
        status: OutcomeStatus = OutcomeStatus.UNKNOWN,
        detail: str = "",
    ) -> FailureRecord:
        """Append one recovery attempt to an open failure.

        Attempt details are scrubbed and bounded before persistence. An exact
        redelivery (same action + status + detail) appends nothing. Attempts
        are capped at ``_MAX_ATTEMPTS`` (oldest dropped first, counted in row
        metadata -- never silently).
        """
        detail_clean, _ = redact_text(safe_preview(detail))
        attempt = RecoveryAttempt(
            action=action,
            status=status,
            detail=detail_clean,
            attempted_at=self._clock(),
        )

        def _append(record: FailureRecord, _row: Memory) -> bool:
            for existing in record.attempts:
                if (
                    existing.action == attempt.action
                    and existing.status is attempt.status
                    and existing.detail == attempt.detail
                ):
                    return False  # duplicate delivery -- no write
            record.attempts.append(attempt)
            if not record.attempted_recovery:
                record.attempted_recovery = action
            return True

        updated, _ = await self._mutate(failure_id, _append)
        return updated

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    async def resolve(
        self,
        failure_id: str,
        recovery: str,
        *,
        status: OutcomeStatus = OutcomeStatus.SUCCESS,
        detail: str = "",
    ) -> FailureRecord:
        """Mark a failure recovered (or explicitly unrecovered).

        The recovery name is appended to the attempt log as well, so the
        successful alternative is attributable to a recorded step. Repeating
        a resolution with the same recovery writes nothing. This never edits
        any procedure -- it only records what worked, with evidence.
        """
        recovery_clean, _ = redact_text(safe_preview(recovery))
        detail_clean, _ = redact_text(safe_preview(detail))

        def _resolve(record: FailureRecord, _row: Memory) -> bool:
            if record.successful_recovery == recovery_clean and (
                not recovery_clean or record.recovery_status is status
            ):
                return False  # repeated resolution -- no write
            record.successful_recovery = recovery_clean
            record.recovery_status = status
            if recovery_clean and not any(
                a.action == recovery_clean for a in record.attempts
            ):
                record.attempts.append(
                    RecoveryAttempt(
                        action=recovery_clean,
                        status=status,
                        detail=detail_clean,
                        attempted_at=self._clock(),
                    )
                )
            return True

        updated, _ = await self._mutate(failure_id, _resolve)
        return updated

    async def confirm_cause(self, failure_id: str, cause: str) -> FailureRecord:
        """Promote a suspected cause to confirmed (explicit, attributable).

        Until this call, the suspicion is quarantined out of the searchable
        summary. The confirmed text is scrubbed before persistence like every
        other free-text field.
        """
        cause_clean, _ = redact_text(safe_preview(cause))

        def _confirm(record: FailureRecord, _row: Memory) -> bool:
            if record.cause_confirmed and record.suspected_cause == cause_clean:
                return False
            record.suspected_cause = cause_clean
            record.cause_confirmed = True
            return True

        updated, _ = await self._mutate(failure_id, _confirm)
        return updated

    # ------------------------------------------------------------------
    # Alternatives (evidence links, never procedure edits)
    # ------------------------------------------------------------------

    async def link_alternative(
        self,
        failure_id: str,
        alternative_id: str,
        *,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """Link the successful alternative to a failure (idempotent).

        The alternative may be a procedure or any memory (e.g. the episode
        step that worked). ``evidence`` names the source -- episode id,
        successful step -- so later procedure evolution can cite it. The link
        is recorded on the failure row, making repeats a no-op instead of
        duplicate link rows. The alternative itself is never modified.
        """
        row = await self._manager.get(failure_id)
        if self._row_to_failure(row) is None:
            raise MemoryNotFoundError(f"No live failure with id {failure_id!r}.")
        target = await self._manager.get(alternative_id)
        if target is None or target.status is MemoryStatus.DELETED:
            raise MemoryNotFoundError(
                f"No live alternative memory {alternative_id!r}."
            )

        key = f"recovered_by:{alternative_id}"

        def _attach(record: FailureRecord, row: Memory) -> bool:
            attached = list(row.data.get("alternative_links", []))
            if key in attached:
                return False
            attached.append(key)
            row.data["alternative_links"] = attached
            return True

        _, did_write = await self._mutate(failure_id, _attach)
        if not did_write:
            return
        await self._manager.link(
            failure_id,
            alternative_id,
            link_type="recovered_by",
            metadata={
                "kind": "failure_recovered_by_alternative",
                "evidence": redact_keys(evidence),
            },
        )

    async def failure_alternatives(self, failure_id: str) -> list[Memory]:
        """Alternative memories linked to a failure (missing ones skipped)."""
        row = await self._manager.get(failure_id)
        if self._row_to_failure(row) is None:
            raise MemoryNotFoundError(f"No live failure with id {failure_id!r}.")
        assert row is not None
        out: list[Memory] = []
        for key in row.data.get("alternative_links", []):
            _, _, alternative_id = key.partition(":")
            if not alternative_id:
                continue
            alternative = await self._manager.get(alternative_id)
            if alternative is not None and alternative.status is not MemoryStatus.DELETED:
                out.append(alternative)
        return out

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def get_failure(self, failure_id: str) -> FailureRecord | None:
        """Rebuild one failure from its stored row.

        Returns ``None`` for a missing id, a non-failure row, a soft-deleted
        row, or a row whose payload no longer parses -- never raises for a
        read.
        """
        try:
            row = await self._manager.get(failure_id)
        except Exception as exc:  # noqa: BLE001 - reads degrade to "no failure"
            logger.warning("get_failure read failed: %s", exc)
            return None
        return self._row_to_failure(row)

    async def list_failures(
        self,
        *,
        failure_type: str | None = None,
        recovered: bool | None = None,
        episode_id: str | None = None,
        include_resolved: bool = True,
        limit: int = 100,
    ) -> list[FailureRecord]:
        """Failures in scope, newest first, bounded by ``limit``.

        ``failure_type`` filters on the error category; ``recovered``
        filters on whether a successful recovery is recorded; ``episode_id``
        scopes to one episode's failures. Resolved failures are included
        unless ``include_resolved`` is ``False`` (historical retrieval keeps
        them by default -- a past fix is evidence, not clutter).
        """
        bound = max(1, int(limit))
        candidates = await self._repo.list_by(
            memory_type=MemoryType.FAILURE.value, limit=bound * 2
        )
        out: list[FailureRecord] = []
        for row in candidates:
            record = self._row_to_failure(row)
            if record is None:
                continue
            if failure_type is not None and record.failure_type != failure_type:
                continue
            if recovered is not None and record.recovered is not recovered:
                continue
            if episode_id is not None and record.episode_id != episode_id:
                continue
            if not include_resolved and record.recovered:
                continue
            out.append(record)
        out.sort(key=lambda r: r.created_at.isoformat(), reverse=True)
        return out[:bound]

    async def list_open(self, *, limit: int = 100) -> list[FailureRecord]:
        """Failures with no successful recovery recorded (work to resume).

        Pages the failure rows in bounded batches so recovery never loads
        the whole table.
        """
        bound = max(1, int(limit))
        found: list[FailureRecord] = []
        offset = 0
        for _ in range(10):  # hard page bound: at most 1000 rows scanned
            batch = await self._repo.list_by(
                memory_type=MemoryType.FAILURE.value, limit=100, offset=offset
            )
            if not batch:
                break
            offset += len(batch)
            for row in batch:
                record = self._row_to_failure(row)
                if record is not None and not record.recovered:
                    found.append(record)
                    if len(found) >= bound:
                        return found
        return found

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _row_to_failure(self, row: Memory | None) -> FailureRecord | None:
        """Rebuild a failure from a stored row, or ``None`` if not usable."""
        if row is None:
            return None
        if row.memory_type is not MemoryType.FAILURE:
            return None
        if row.status is MemoryStatus.DELETED:
            return None
        payload = row.data.get(_FAILURE_DATA_KEY)
        if not isinstance(payload, dict):
            return None
        try:
            return FailureRecord.from_dict(payload)
        except Exception as exc:  # noqa: BLE001 - corrupt payload reads as absent
            logger.warning("Unparseable failure payload for %r: %s", row.id, exc)
            return None

    async def _mutate(
        self,
        failure_id: str,
        mutate: Callable[[FailureRecord, Memory], bool],
    ) -> tuple[FailureRecord, bool]:
        """Read-modify-write one failure row with bounded version retries.

        ``mutate`` edits the rebuilt record in place and returns ``True``
        when a write is needed (``False`` = idempotent no-op, no version
        bump, no re-index). The attempt log is capped before every write; the
        content summary is always rebuilt from the stored record (suspected
        causes stay quarantined until confirmed). Returns the record and
        whether a write happened.
        """
        last_conflict: MemoryConflictError | None = None
        for _ in range(_MUTATE_ATTEMPTS):
            row = await self._manager.get(failure_id)
            record = self._row_to_failure(row)
            if record is None:
                raise MemoryNotFoundError(
                    f"No live failure with id {failure_id!r}.",
                    hint="Record the failure first, or check for a typo/forgotten id.",
                )
            assert row is not None
            if not mutate(record, row):
                return record, False
            dropped = self._cap_attempts(record)
            data = dict(row.data)
            data[_FAILURE_DATA_KEY] = record.to_dict()
            metadata = dict(row.metadata)
            if dropped:
                metadata["truncated_attempts"] = (
                    int(row.metadata.get("truncated_attempts", 0)) + dropped
                )
            # Keep the episode/procedure scope columns in sync with the record
            # (late links arrive after the initial write).
            if record.episode_id is not None:
                metadata["episode_id"] = record.episode_id
            # Recompute the derived presentation fields from the updated
            # record (same rules as FailureRecord.to_memory): a recovered
            # failure must read recovered in tags, confidence and
            # importance -- never keep a stale "open" tag after resolve().
            projected = record.to_memory()
            try:
                updated = await self._manager.update(
                    failure_id,
                    expected_version=row.version,
                    content=projected.content,
                    confidence=projected.confidence,
                    importance=projected.importance,
                    tags=projected.tags,
                    data=data,
                    metadata=metadata,
                )
            except MemoryConflictError as exc:
                last_conflict = exc
                continue
            rebuilt = self._row_to_failure(updated)
            if rebuilt is None:  # pragma: no cover - defensive
                raise MemoryStorageError(
                    f"Failure {failure_id!r} unreadable right after its own update."
                )
            return rebuilt, True
        raise last_conflict or MemoryConflictError(
            f"Failure {failure_id!r} is under contention; retry the append."
        )

    def _cap_attempts(self, record: FailureRecord) -> int:
        """Enforce the per-failure attempt bound; return how many were dropped."""
        overflow = len(record.attempts) - _MAX_ATTEMPTS
        if overflow <= 0:
            return 0
        del record.attempts[:overflow]
        return overflow
