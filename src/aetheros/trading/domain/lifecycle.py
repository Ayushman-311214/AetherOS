"""
Signal-lifecycle value objects (spec Phase 2 -- the explicit signal lifecycle).

A fired :class:`~aetheros.trading.domain.trade.TradeSignal` is not a static
fact: it is *created* by the signal engine, *validated* through the critic and
risk gates, may be *approved* into an executable plan, become *active* once a
resting order is working, be *invalidated* by its own invalidation condition
or by a gate that stopped it, reach a venue and *execute* (possibly only
*partially filled*), *close* when the position is unwound, and finally be
*evaluated* when the prediction it embodies is scored against what actually
happened.

Phase 1 emitted this trail implicitly -- a ``SignalGenerated`` event fired,
an ``OrderSubmitted`` event fired, a ``PredictionResolved`` event fired -- but
no single object *owned* the sequence, so "what state is this signal in?" had
no answer and an illegal jump (a signal that skipped validation and went
straight to filled) could not be told apart from an honest one. This module
makes the lifecycle a first-class, validated record:

* :class:`SignalState` -- the nine states the spec enumerates, in order.
* :func:`allowed` -- the fixed transition table; only moves it names are legal.
* :class:`SignalLifecycle` -- an immutable record of where one signal is and
  every audited step that took it there. :meth:`SignalLifecycle.transition`
  validates the move against the table and either returns a new record one
  state further along, or raises :class:`LifecycleError` naming the illegal
  jump. A transition is never silently dropped and never silently allowed --
  that is the difference between a lifecycle and a log line.

The record computes nothing about the market; it only enforces that the trail
of states a signal claims is one the spec permits. Every transition is carried
as a :class:`LifecycleTransition` (from, to, reason, timestamp) so the record
is self-auditing end to end.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ..errors import LifecycleError


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SignalState(str, Enum):
    """
    The nine lifecycle states a signal can occupy (spec Phase 2).

    The order is meaningful -- it is the spec's required path -- but the enum
    itself imposes none of it; legality lives in :data:`_TRANSITIONS` so the
    set of allowed moves is a single auditable table rather than scattered
    conditionals.
    """

    CREATED = "created"
    VALIDATING = "validating"
    APPROVED = "approved"
    ACTIVE = "active"
    INVALIDATED = "invalidated"
    EXECUTED = "executed"
    PARTIALLY_FILLED = "partially_filled"
    CLOSED = "closed"
    EVALUATED = "evaluated"

    @property
    def is_terminal(self) -> bool:
        """Whether the lifecycle can move no further from this state."""
        return not _TRANSITIONS.get(self)


# The single source of truth for which transitions are legal. A state absent
# from the table is terminal. The table is deliberately permissive about the
# "any state -> INVALIDATED" jump (a signal can be invalidated from any live
# state, because an invalidation condition is external to the sequence) and
# about skipping ahead on a fast fill (CREATED -> EXECUTED is legal, because a
# market order can create-and-fill in one step), but it forbids the jumps that
# would be dishonest: a signal cannot be EVALUATED before it EXECUTED, cannot
# be APPROVED after it EXECUTED, and can never leave a terminal state.
_TRANSITIONS: dict[SignalState, frozenset[SignalState]] = {
    SignalState.CREATED: frozenset(
        {
            SignalState.VALIDATING,
            SignalState.INVALIDATED,
            SignalState.EXECUTED,
        }
    ),
    SignalState.VALIDATING: frozenset(
        {
            SignalState.APPROVED,
            SignalState.INVALIDATED,
        }
    ),
    SignalState.APPROVED: frozenset(
        {
            SignalState.ACTIVE,
            SignalState.EXECUTED,
            SignalState.INVALIDATED,
        }
    ),
    SignalState.ACTIVE: frozenset(
        {
            SignalState.PARTIALLY_FILLED,
            SignalState.EXECUTED,
            SignalState.INVALIDATED,
            SignalState.CLOSED,
        }
    ),
    SignalState.PARTIALLY_FILLED: frozenset(
        {
            SignalState.EXECUTED,
            SignalState.CLOSED,
            SignalState.INVALIDATED,
        }
    ),
    SignalState.EXECUTED: frozenset(
        {
            SignalState.PARTIALLY_FILLED,
            SignalState.CLOSED,
            SignalState.INVALIDATED,
            SignalState.EVALUATED,
        }
    ),
    SignalState.INVALIDATED: frozenset(
        {
            SignalState.EVALUATED,
        }
    ),
    SignalState.CLOSED: frozenset(
        {
            SignalState.EVALUATED,
        }
    ),
    SignalState.EVALUATED: frozenset(),
}


def allowed(from_state: SignalState, to_state: SignalState) -> bool:
    """Whether a transition between two states is legal."""
    return to_state in _TRANSITIONS.get(from_state, frozenset())


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    """One audited step in a signal's lifecycle."""

    from_state: SignalState
    to_state: SignalState
    reason: str
    at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("A lifecycle transition must name its reason.")
        if self.at.tzinfo is None or self.at.utcoffset() is None:
            raise ValueError("A lifecycle transition timestamp must be aware.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_state.value,
            "to": self.to_state.value,
            "reason": self.reason,
            "at": self.at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SignalLifecycle:
    """
    The immutable, audited lifecycle record of one signal.

    ``transitions`` is the ordered history of legal moves; ``state`` is the
    current head. A record is always built in ``CREATED`` (see
    :meth:`create`) and only ever advances through :meth:`transition`, which
    validates the move. Because the record is frozen, an audit can hold one
    and trust that its history cannot be edited after the fact.
    """

    signal_id: str
    state: SignalState
    transitions: tuple[LifecycleTransition, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.signal_id.strip():
            raise ValueError("A lifecycle record requires a signal id.")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("A lifecycle created_at must be aware.")

    @classmethod
    def create(cls, signal_id: str, *, reason: str = "signal generated") -> "SignalLifecycle":
        """
        Open a lifecycle in CREATED.

        A lifecycle begins the moment the signal exists -- the very first state
        is the honest one, never a fabricated "already validating" shortcut.
        """
        return cls(signal_id=signal_id, state=SignalState.CREATED)

    @property
    def is_terminal(self) -> bool:
        """Whether this record can advance no further."""
        return self.state.is_terminal

    def transition(
        self,
        to_state: SignalState,
        *,
        reason: str,
        at: datetime | None = None,
    ) -> "SignalLifecycle":
        """
        Advance the lifecycle one state, validating the move.

        Returns a new record one step further along; the original is
        untouched. Raises :class:`LifecycleError` naming the illegal jump when
        the move is not in the transition table -- an illegal move is a loud,
        typed error, never a silently-ignored or silently-permitted one.
        """
        if not allowed(self.state, to_state):
            raise LifecycleError(
                f"Illegal lifecycle transition for signal '{self.signal_id}': "
                f"{self.state.value} -> {to_state.value}. Allowed next states: "
                f"{sorted(s.value for s in _TRANSITIONS.get(self.state, ())) or 'none'}.",
                context={
                    "signal_id": self.signal_id,
                    "from_state": self.state.value,
                    "to_state": to_state.value,
                },
            )
        step = LifecycleTransition(
            from_state=self.state,
            to_state=to_state,
            reason=reason,
            at=at if at is not None else _utcnow(),
        )
        return SignalLifecycle(
            signal_id=self.signal_id,
            state=to_state,
            transitions=self.transitions + (step,),
            created_at=self.created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "state": self.state.value,
            "is_terminal": self.is_terminal,
            "transitions": [t.to_dict() for t in self.transitions],
            "created_at": self.created_at.isoformat(),
        }
