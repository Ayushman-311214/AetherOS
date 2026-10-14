"""
Signal lifecycle state machine (spec Phase 2).

The lifecycle is the explicit, validated trail a signal walks:
CREATED → VALIDATING → APPROVED/INVALIDATED → ACTIVE →
EXECUTED/PARTIALLY_FILLED → CLOSED → EVALUATED. These tests pin the three
properties that make it honest rather than a log line:

- **legal moves advance**, and the trail records every step with its reason;
- **illegal moves are refused loudly** -- a signal cannot be EVALUATED before
  EXECUTED, cannot be APPROVED after EXECUTED, and can never leave a terminal
  state;
- **the first state is CREATED**, never a fabricated shortcut into a later one.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.lifecycle import (
    LifecycleTransition,
    SignalLifecycle,
    SignalState,
    allowed,
)
from aetheros.trading.errors import LifecycleError
from aetheros.trading.production import SignalLifecycleService


def _new(signal_id: str = "sg_test") -> SignalLifecycle:
    return SignalLifecycle.create(signal_id)


def test_a_lifecycle_starts_in_created():
    record = _new()
    assert record.state is SignalState.CREATED
    assert record.transitions == ()
    assert not record.is_terminal


def test_created_validates_to_validating():
    record = _new().transition(SignalState.VALIDATING, reason="panel judged it")
    assert record.state is SignalState.VALIDATING
    assert len(record.transitions) == 1
    assert record.transitions[0].from_state is SignalState.CREATED
    assert record.transitions[0].to_state is SignalState.VALIDATING


def test_the_happy_path_walks_to_evaluated():
    record = (
        _new()
        .transition(SignalState.VALIDATING, reason="gates ran")
        .transition(SignalState.APPROVED, reason="critic approved")
        .transition(SignalState.EXECUTED, reason="order filled")
        .transition(SignalState.CLOSED, reason="position unwound")
        .transition(SignalState.EVALUATED, reason="prediction resolved")
    )
    assert record.state is SignalState.EVALUATED
    assert record.is_terminal
    assert [t.to_state for t in record.transitions] == [
        SignalState.VALIDATING,
        SignalState.APPROVED,
        SignalState.EXECUTED,
        SignalState.CLOSED,
        SignalState.EVALUATED,
    ]


@pytest.mark.parametrize(
    "to_state",
    [SignalState.APPROVED, SignalState.EXECUTED, SignalState.CLOSED],
)
def test_an_invalidated_signal_cannot_re_enter(to_state):
    record = (
        _new()
        .transition(SignalState.VALIDATING, reason="gates ran")
        .transition(SignalState.INVALIDATED, reason="critic rejected")
    )
    with pytest.raises(LifecycleError, match="Illegal lifecycle transition"):
        record.transition(to_state, reason="illegal")


def test_a_created_signal_can_fill_directly():
    # A market order can create-and-fill in one step; CREATED -> EXECUTED is legal.
    record = _new().transition(SignalState.EXECUTED, reason="market fill")
    assert record.state is SignalState.EXECUTED


def test_an_executed_signal_cannot_be_approved_afterward():
    record = _new().transition(SignalState.EXECUTED, reason="market fill")
    with pytest.raises(LifecycleError):
        record.transition(SignalState.APPROVED, reason="too late")


def test_a_created_signal_cannot_be_evaluated():
    with pytest.raises(LifecycleError):
        _new().transition(SignalState.EVALUATED, reason="never traded")


def test_evaluated_is_terminal():
    record = _new().transition(SignalState.EXECUTED, reason="filled").transition(
        SignalState.EVALUATED, reason="scored"
    )
    assert record.is_terminal
    with pytest.raises(LifecycleError):
        record.transition(SignalState.CLOSED, reason="cannot leave terminal")


def test_allowed_is_the_single_source_of_truth():
    assert allowed(SignalState.CREATED, SignalState.VALIDATING)
    assert not allowed(SignalState.CREATED, SignalState.EVALUATED)
    assert not allowed(SignalState.EVALUATED, SignalState.CLOSED)


# ----------------------------------------------------------------------
# The service: tracking, observability, and best-effort advance


def test_the_service_opens_and_advances_a_signal():
    service = SignalLifecycleService()
    record = service.open("sg_1", instrument_key="TEST")
    assert record.state is SignalState.CREATED
    updated = service.advance(
        "sg_1", SignalState.VALIDATING, reason="gates ran", instrument_key="TEST"
    )
    assert updated.state is SignalState.VALIDATING
    assert service.state_of("sg_1") is SignalState.VALIDATING


def test_the_service_try_advance_swallows_an_illegal_move():
    service = SignalLifecycleService()
    service.open("sg_1", instrument_key="TEST")
    # CREATED -> EVALUATED is illegal; try_advance must not record it.
    result = service.try_advance(
        "sg_1", SignalState.EVALUATED, reason="bad move", instrument_key="TEST"
    )
    assert result is None
    assert service.state_of("sg_1") is SignalState.CREATED


def test_the_service_advance_raises_on_an_illegal_move():
    service = SignalLifecycleService()
    service.open("sg_1")
    with pytest.raises(LifecycleError):
        service.advance("sg_1", SignalState.EVALUATED, reason="bad")


def test_an_unknown_signal_returns_no_state():
    service = SignalLifecycleService()
    assert service.get("never_seen") is None
    assert service.state_of("never_seen") is None
