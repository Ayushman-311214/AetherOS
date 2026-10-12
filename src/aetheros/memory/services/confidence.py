"""
Confidence and evidence updates (Phase 13).

Stored-fact confidence is a claim about *how much the system trusts a
stored memory* -- it is NOT a forecast probability (which lives on the
prediction row's own fields and stays 0.5-confident as a record), NOT
retrieval relevance (the scorer's blended, per-query signal), and NOT a
procedure success rate (the Wilson-shrunk count ratio on ``Procedure``).
Each of those has its own scale and semantics; this module moves only the
stored-fact number, and refuses rows where that number is conventionally
fixed (predictions, trading history) or where the row itself is history
(episodes, failures, procedures).

Update rules (all deterministic, all bounded, all recorded):

* ``confirm`` -- an independent source corroborates the memory: +0.05,
  capped at 0.95. Independence is keyed by ``source``: the same source
  confirming twice is a duplicate observation, not a second confirmation,
  and is a no-op. Seen sources live in
  ``metadata["confirmation_sources"]``.
* ``correct`` -- an explicit user correction of a user-governed row
  (USER_INPUT veracity, PREFERENCE type, or explicit user fact):
  content/fields replaced, confidence set to 0.9, correction recorded.
  Refuses prediction-veracity rows, TRADING rows, episodes, failures and
  procedures -- user corrections govern applicable user facts, they never
  rewrite immutable market predictions or fabricate external truth.
* ``record_reuse`` -- a verified reuse of the memory succeeded (+0.03,
  cap 0.9) or failed (-0.05, floor 0.1). For reusable knowledge
  (procedures, semantic know-how); predictions use linked outcomes, not
  reuse.
* ``record_outcome`` -- an observed outcome bears on a stored fact:
  confirmed correct +0.05 (cap 0.95), shown wrong -0.10 (floor 0.1).
  Refuses PREDICTION-veracity rows: a forecast's outcome is a separate
  linked record (Rule: historical predictions immutable), never an edit.
* ``apply_contradiction`` -- a ``contradicts`` link now names this row:
  -0.05 (floor 0.2, so contradiction dents but never destroys; archival
  is consolidation's job, not confidence's). Records which row
  contradicted it.

What NEVER moves confidence (pinned by tests):

* retrieval (``record_access`` / ``retrieve`` touch access counts only);
* mere ageing (freshness lives in the scorer's recency signal and the
  lifecycle's status transitions -- decaying confidence by age as well
  would double-penalise old memories);
* embedding similarity, consolidation merges beyond the legacy +0.02
  (left in place, documented as a limitation below).

Bounds: absolute [0, 1] enforced by the domain clamp; update rules float
between floor 0.1 and cap 0.95 so no single update can max out or erase a
memory. The lifecycle's LOW_CONFIDENCE threshold (0.25) is a consumer of
this number, not a setter.

Evidence history: every applied rule appends
``{at, rule, delta, before, after, source?}`` to
``metadata["confidence_history"]`` (cap 20, oldest dropped). The history
is the audit trail: *why* a number moved is always recoverable.

Limitations (documented, not hidden): these scores are bounded heuristics,
NOT calibrated probabilities -- no calibration is measured here, so never
present them as such. Two pre-existing ad-hoc nudges (consolidator merge
+0.02, graph upsert +0.05) predate this module, stay capped, and do not
write history entries; the updater is the documented path for everything
new.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...core.errors.memory_error import (
    MemoryConflictError,
    MemoryNotFoundError,
    MemoryStorageError,
    MemoryValidationError,
)
from ...core.logging import get_logger
from .._clock import utcnow
from ..domain.enums import MemoryStatus, MemoryType, Veracity
from ..domain.memory import Memory

if TYPE_CHECKING:
    from .manager import MemoryManager

logger = get_logger("memory.confidence")

_HISTORY_KEY = "confidence_history"
_SOURCES_KEY = "confirmation_sources"

# Update-rule bounds. The domain clamp holds the absolute [0, 1]; these
# keep any single rule from maxing out or erasing a memory.
_FLOOR = 0.1
_CAP = 0.95
_REUSE_CAP = 0.9
_CONTRADICTION_FLOOR = 0.2
_HISTORY_CAP = 20

# Bounded optimistic-concurrency retries for a contested row.
_MUTATE_ATTEMPTS = 3

# Rows whose confidence is conventionally fixed or whose content is
# history: the updater refuses them rather than silently misusing the
# number. TRADING type covers market predictions/outcomes; PREDICTION
# veracity covers forecasts wherever they live.
_PROTECTED_TYPES = frozenset(
    {
        MemoryType.EPISODIC,
        MemoryType.FAILURE,
        MemoryType.TRADING,
        MemoryType.PROCEDURAL,
    }
)


class ConfidenceUpdateResult:
    """Outcome of one update rule: the row before/after + whether it wrote."""

    __slots__ = ("memory", "applied", "reason")

    def __init__(self, memory: Memory, *, applied: bool, reason: str) -> None:
        self.memory = memory
        self.applied = applied
        self.reason = reason


class ConfidenceUpdater:
    """Documented, bounded confidence updates over durable memories.

    Constructed once by :class:`MemoryManager` (see the ``confidence``
    accessor); holds no row state itself. Every mutation is a version-
    guarded read-modify-write through the existing ``update`` verb, so the
    existing ``MemoryStored`` event contract announces it. No new bus.
    """

    def __init__(self, manager: MemoryManager) -> None:
        self._manager = manager

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    async def confirm(
        self, memory_id: str, *, source: str = "user"
    ) -> ConfidenceUpdateResult:
        """Record an independent confirmation (+0.05, cap 0.95).

        Independence is keyed by ``source``: a source that already confirmed
        this memory is a duplicate observation, not new evidence, and the
        call is a no-op (applied=False). Refuses protected rows.
        """
        source_key = (source or "").strip().lower() or "unknown"
        row = await self._live_row(memory_id)
        self._refuse_protected(row, rule="confirm")
        seen = list(row.metadata.get(_SOURCES_KEY, []))
        if source_key in seen:
            return ConfidenceUpdateResult(
                row, applied=False, reason=f"source {source_key!r} already counted"
            )
        seen.append(source_key)
        return await self._apply(
            row,
            delta=min(0.05, _CAP - row.confidence),
            rule="confirm",
            source=source_key,
            extra_metadata={_SOURCES_KEY: seen},
        )

    async def correct(
        self,
        memory_id: str,
        *,
        content: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> ConfidenceUpdateResult:
        """Apply an explicit user correction (confidence := 0.9).

        Governs user facts only: USER_INPUT veracity or PREFERENCE type.
        Refuses prediction-veracity rows, TRADING rows, episodes, failures
        and procedures -- corrections never rewrite immutable history or
        fabricate external truth. At least one of ``content``/``fields``
        must change something, else the call is a no-op.
        """
        row = await self._live_row(memory_id)
        # User-governed rows: PREFERENCE type (any non-prediction veracity),
        # USER_INPUT veracity, or USER-sourced rows on unprotected,
        # non-trading types (a user can correct what the user said --
        # veracity labels truth-status, source labels authorship).
        # Everything else is refused: predictions and trading rows are
        # immutable history, and episodes / failures / procedures evolve by
        # their own evidence -- corrections never rewrite them or fabricate
        # external truth.
        from ..domain.enums import SourceType

        is_preference = (
            row.memory_type is MemoryType.PREFERENCE
            and row.veracity is not Veracity.PREDICTION
        )
        is_user_fact = (
            row.veracity is Veracity.USER_INPUT
            and row.memory_type not in _PROTECTED_TYPES
            and row.memory_type is not MemoryType.TRADING
        )
        is_user_authored = (
            row.source.source_type is SourceType.USER
            and row.memory_type not in _PROTECTED_TYPES
            and row.memory_type is not MemoryType.TRADING
            and row.veracity is not Veracity.PREDICTION
        )
        if not (is_preference or is_user_fact or is_user_authored):
            raise MemoryValidationError(
                f"correct() governs user facts/preferences; row {memory_id!r} "
                f"is {row.memory_type.value} / {row.veracity.value}.",
                hint="User corrections never rewrite immutable history or "
                "fabricate external truth; link a new memory instead.",
            )
        changes: dict[str, Any] = {}
        if content is not None and content.strip() and content != row.content:
            changes["content"] = content
        if fields:
            merged = dict(row.metadata)
            merged.update(fields)
            if merged != row.metadata:
                changes["metadata"] = merged
        if not changes:
            return ConfidenceUpdateResult(
                row, applied=False, reason="nothing changed"
            )
        # A user correction sets (not nudges) confidence: the user looked at
        # this fact and fixed it, so it is trusted -- but not certain.
        before = row.confidence
        return await self._apply(
            row,
            set_to=0.9,
            rule="correct",
            _before=before,
            _extra_changes=changes,
        )

    async def record_reuse(
        self, memory_id: str, *, succeeded: bool
    ) -> ConfidenceUpdateResult:
        """Record a verified reuse (+0.03 success / -0.05 failure).

        For reusable knowledge. Refuses prediction-veracity and TRADING
        rows (forecasts are graded by linked outcomes, not by reuse) and
        history rows (episodes/failures/procedures evolve by their own
        evidence counts, not by this number).
        """
        row = await self._live_row(memory_id)
        self._refuse_protected(row, rule="record_reuse")
        if row.veracity is Veracity.PREDICTION or (
            row.memory_type is MemoryType.TRADING
        ):
            raise MemoryValidationError(
                f"record_reuse() refuses {row.memory_type.value} / "
                f"{row.veracity.value} rows: forecasts are graded by linked "
                "outcomes, not by reuse.",
                hint="Store a realised outcome as a separate linked record.",
            )
        if succeeded:
            return await self._apply(
                row,
                delta=min(0.03, _REUSE_CAP - row.confidence),
                rule="reuse_succeeded",
            )
        return await self._apply(
            row,
            delta=-min(0.05, row.confidence - _FLOOR),
            rule="reuse_failed",
        )

    async def record_outcome(
        self, memory_id: str, *, correct: bool
    ) -> ConfidenceUpdateResult:
        """Record an observed outcome bearing on a stored fact.

        Confirmed correct: +0.05 (cap 0.95). Shown wrong: -0.10 (floor
        0.1). Refuses PREDICTION-veracity rows outright -- a forecast's
        outcome is a separate linked record, never an edit (Rule: historical
        predictions immutable).
        """
        row = await self._live_row(memory_id)
        if row.veracity is Veracity.PREDICTION or (
            row.memory_type is MemoryType.TRADING
        ):
            raise MemoryValidationError(
                f"record_outcome() refuses {row.memory_type.value} / "
                f"{row.veracity.value} rows: forecast outcomes are separate "
                "linked records, never edits.",
                hint="Use remember_prediction_outcome() for forecasts.",
            )
        self._refuse_protected(row, rule="record_outcome")
        if correct:
            return await self._apply(
                row,
                delta=min(0.05, _CAP - row.confidence),
                rule="outcome_confirmed",
            )
        return await self._apply(
            row,
            delta=-min(0.10, row.confidence - _FLOOR),
            rule="outcome_refuted",
        )

    async def apply_contradiction(
        self, memory_id: str, *, contradicted_by: str
    ) -> ConfidenceUpdateResult:
        """Dent confidence for a recorded contradiction (-0.05, floor 0.2).

        The floor keeps contradiction as a dent, never destruction: archival
        is consolidation's job. Records which row contradicted this one, so
        the history names its evidence. Idempotent per contradictor: the
        same pair denting twice is a duplicate, not new evidence.
        """
        row = await self._live_row(memory_id)
        self._refuse_protected(row, rule="apply_contradiction")
        seen = list(row.metadata.get("contradicted_by", []))
        if contradicted_by in seen:
            return ConfidenceUpdateResult(
                row, applied=False, reason="contradictor already counted"
            )
        seen.append(contradicted_by)
        return await self._apply(
            row,
            delta=-min(0.05, row.confidence - _CONTRADICTION_FLOOR),
            rule="contradiction",
            source=contradicted_by,
            extra_metadata={"contradicted_by": seen},
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    async def history(self, memory_id: str) -> list[dict[str, Any]]:
        """The recorded evidence history for a row (oldest first)."""
        row = await self._live_row(memory_id)
        entries = row.metadata.get(_HISTORY_KEY, [])
        return [dict(e) for e in entries] if isinstance(entries, list) else []

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _live_row(self, memory_id: str) -> Memory:
        row = await self._manager.get(memory_id)
        if row is None or row.status is MemoryStatus.DELETED:
            raise MemoryNotFoundError(f"No live memory with id {memory_id!r}.")
        return row

    def _refuse_protected(self, row: Memory, *, rule: str) -> None:
        if row.memory_type in _PROTECTED_TYPES:
            raise MemoryValidationError(
                f"{rule}() refuses {row.memory_type.value} rows: that "
                "confidence is conventionally fixed or the row is history.",
                hint="Confidence updates apply to stored facts, not to "
                "episodes, failures, trading history or procedures.",
            )

    async def _apply(
        self,
        row: Memory,
        *,
        delta: float = 0.0,
        set_to: float | None = None,
        rule: str,
        source: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
        _before: float | None = None,
        _extra_changes: dict[str, Any] | None = None,
    ) -> ConfidenceUpdateResult:
        """Version-guarded write with history append. Returns the outcome."""
        before = _before if _before is not None else row.confidence
        target = set_to if set_to is not None else before + delta
        target = max(0.0, min(1.0, target))
        if abs(target - before) < 1e-12 and not _extra_changes:
            return ConfidenceUpdateResult(row, applied=False, reason="at bound")
        last_conflict: MemoryConflictError | None = None
        for _ in range(_MUTATE_ATTEMPTS):
            fresh = await self._manager.get(row.id)
            if fresh is None or fresh.status is MemoryStatus.DELETED:
                raise MemoryNotFoundError(f"No live memory with id {row.id!r}.")
            entry: dict[str, Any] = {
                "at": utcnow().isoformat(),
                "rule": rule,
                "delta": round(target - fresh.confidence, 6),
                "before": fresh.confidence,
                "after": target,
            }
            if source is not None:
                entry["source"] = source
            history = list(fresh.metadata.get(_HISTORY_KEY, []))
            history.append(entry)
            del history[: max(0, len(history) - _HISTORY_CAP)]
            metadata = dict(fresh.metadata)
            metadata[_HISTORY_KEY] = history
            if extra_metadata:
                metadata.update(extra_metadata)
            if _extra_changes and "metadata" in _extra_changes:
                merged = dict(_extra_changes["metadata"])
                merged[_HISTORY_KEY] = history
                if extra_metadata:
                    merged.update(extra_metadata)
                metadata = merged
            try:
                if _extra_changes and "content" in _extra_changes:
                    updated = await self._manager.update(
                        row.id,
                        expected_version=fresh.version,
                        content=_extra_changes["content"],
                        confidence=target,
                        metadata=metadata,
                    )
                else:
                    updated = await self._manager.update(
                        row.id,
                        expected_version=fresh.version,
                        confidence=target,
                        metadata=metadata,
                    )
            except MemoryConflictError as exc:
                last_conflict = exc
                continue
            return ConfidenceUpdateResult(updated, applied=True, reason=rule)
        raise last_conflict or MemoryStorageError(
            f"Confidence update on {row.id!r} is under contention; retry."
        )
