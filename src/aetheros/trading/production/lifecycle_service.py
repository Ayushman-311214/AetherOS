"""
Signal-lifecycle service (spec Phase 2 -- lifecycle observability).

Keeps a :class:`~aetheros.trading.domain.lifecycle.SignalLifecycle` record per
signal and advances it through the validated state machine as the pipeline
moves: signal engine → critic/risk gates → execution → evaluation. This is the
single place the sequence lives, so a caller can always ask *"what state is
this signal in, and how did it get there?"* and get the audited trail rather
than reconstructing it from scattered events.

Two rules keep it honest:

* **Advance is validated.** :meth:`advance` goes through
  :meth:`SignalLifecycle.transition`, so an illegal move raises
  :class:`LifecycleError` -- it is never recorded and never silently skipped.
  A convenience :meth:`try_advance` swallows the error into a log line for the
  "best-effort" call sites (a simulation that does not drive a full book)
  without ever letting an illegal state persist.
* **Transitions are observable.** Every accepted advance publishes
  :class:`SignalStateChanged`, and an INVALIDATED signal additionally
  publishes the already-declared :class:`SignalInvalidated` -- so the Phase 1
  event contract gets its real producer here.

The service holds only the lifecycle records (a dict by signal id); it keeps
no market data and makes no judgement about whether a signal *should* advance
-- the callers decide that, and the state machine decides whether the move
they ask for is legal.
"""

from __future__ import annotations

import asyncio

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.lifecycle import SignalLifecycle, SignalState
from ..errors import LifecycleError
from ..events import SignalInvalidated, SignalStateChanged

logger = get_logger("trading.lifecycle")


class SignalLifecycleService:
    """Tracks and validates each signal's lifecycle, emitting transitions."""

    def __init__(self, *, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus
        self._records: dict[str, SignalLifecycle] = {}

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, signal_id: str) -> SignalLifecycle | None:
        """The lifecycle record for a signal, or None if never opened."""
        return self._records.get(signal_id)

    def state_of(self, signal_id: str) -> SignalState | None:
        """The current state of a signal, or None if untracked."""
        record = self._records.get(signal_id)
        return record.state if record is not None else None

    def all(self) -> tuple[SignalLifecycle, ...]:
        """Every tracked lifecycle record."""
        return tuple(self._records.values())

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def open(
        self, signal_id: str, *, instrument_key: str = "", reason: str = "signal generated"
    ) -> SignalLifecycle:
        """
        Open a lifecycle for a signal in CREATED (idempotent).

        Re-opening an already-tracked signal returns the existing record -- a
        signal does not re-create itself; it continues the trail it already has.
        """
        existing = self._records.get(signal_id)
        if existing is not None:
            return existing
        record = SignalLifecycle.create(signal_id, reason=reason)
        self._records[signal_id] = record
        self._emit(record, None, SignalState.CREATED, reason, instrument_key)
        return record

    def advance(
        self,
        signal_id: str,
        to_state: SignalState,
        *,
        reason: str,
        instrument_key: str = "",
    ) -> SignalLifecycle:
        """
        Advance a signal one validated step; raises LifecycleError if illegal.

        The signal is opened in CREATED first if it is not already tracked, so
        a caller can advance a signal it only just learned about without a
        separate open step.
        """
        record = self._records.get(signal_id)
        if record is None:
            record = self.open(
                signal_id, instrument_key=instrument_key, reason=reason
            )
        from_state = record.state
        updated = record.transition(to_state, reason=reason)
        self._records[signal_id] = updated
        self._emit(updated, from_state, to_state, reason, instrument_key)
        if to_state is SignalState.INVALIDATED:
            self._emit_invalidated(updated, reason, instrument_key)
        return updated

    def try_advance(
        self,
        signal_id: str,
        to_state: SignalState,
        *,
        reason: str,
        instrument_key: str = "",
    ) -> SignalLifecycle | None:
        """
        Best-effort advance: logs and returns None on an illegal move.

        For call sites that should not hard-fail on a lifecycle edge case (a
        replay that does not drive the full state machine), this keeps the
        record honest without propagating -- the illegal move is logged, never
        recorded.
        """
        try:
            return self.advance(
                signal_id, to_state, reason=reason, instrument_key=instrument_key
            )
        except LifecycleError as exc:
            logger.warning("Lifecycle advance refused for %s: %s", signal_id, exc)
            return None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _emit(
        self,
        record: SignalLifecycle,
        from_state: SignalState | None,
        to_state: SignalState,
        reason: str,
        instrument_key: str,
    ) -> None:
        if self._event_bus is None:
            return
        try:
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    SignalStateChanged(
                        signal_id=record.signal_id,
                        instrument_key=instrument_key,
                        from_state=from_state.value if from_state else "",
                        to_state=to_state.value,
                        reason=reason,
                    )
                )
            )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("Failed to publish SignalStateChanged")

    def _emit_invalidated(
        self, record: SignalLifecycle, reason: str, instrument_key: str
    ) -> None:
        if self._event_bus is None:
            return
        try:
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    SignalInvalidated(
                        signal_id=record.signal_id,
                        instrument_key=instrument_key,
                        reason=reason,
                        source_tier="derived",
                    )
                )
            )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("Failed to publish SignalInvalidated")
