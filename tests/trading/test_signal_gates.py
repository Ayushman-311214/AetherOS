"""
The signal gates: every path to a fired or declined candidate.

The gate sequence is the entire intelligence of the signal layer, so each
gate gets a fired-case and a rejected-case, and the composed reasoning is
asserted to name its actual inputs (side, geometry, verdict) rather than
surviving empty inputs. Fixtures reuse the critic-test builders so the risk
geometry and critique verdicts are the same objects the real pipeline
produces.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from aetheros.trading.domain.enums import (
    Confidence,
    CriticVerdict,
    Direction,
    TradeAction,
)
from aetheros.trading.signals.gates import evaluate_candidate

from .test_critic import _risk as _bullish_risk
from .test_signal_domain import _critique, _setup

_MIN_REWARD = 1.5


def _sided_risk(direction: Direction, rr: float | None = 2.0):
    """
    Risk geometry on the correct side of its entry for either direction.

    The critic-test builder is hardcoded bullish (stop below entry); a SELL
    candidate needs the mirror, and this helper flips stop/target while
    keeping the same ratio and actionability.
    """
    risk = _bullish_risk(rr, direction=Direction.UP)
    if direction is Direction.UP:
        return replace(risk, direction=Direction.UP)
    # Bearish mirror: entry 100, stop above, target below, same distances.
    return replace(
        risk,
        direction=Direction.DOWN,
        stop_loss=102.0,
        target=(100.0 - (rr * 2.0)) if rr is not None else None,
        reward_per_unit=(rr * 2.0) if rr is not None else None,
    )


def _run(
    *,
    setup_direction: Direction = Direction.UP,
    risk_direction: Direction = Direction.UP,
    verdict: CriticVerdict = CriticVerdict.APPROVE,
    rr: float | None = 2.0,
    actionable: bool = True,
):
    setup = _setup(setup_direction)
    risk = _sided_risk(risk_direction, rr)
    if not actionable:
        risk = replace(risk, is_actionable=False)
    critique = _critique(verdict)
    return evaluate_candidate(setup, risk, critique, min_reward=_MIN_REWARD)


# ----------------------------------------------------------------------
# The fired path


def test_a_fully_judged_candidate_becomes_a_signal():
    signal, rejections = _run()
    assert signal is not None
    assert rejections == ()
    assert signal.action is TradeAction.BUY
    assert signal.direction is Direction.UP
    assert signal.entry == 100.0
    assert signal.stop_loss == 98.0
    assert signal.take_profit is not None
    assert signal.strategy_id == "trend_following"


def test_a_bearish_candidate_becomes_a_sell_signal():
    signal, _ = _run(setup_direction=Direction.DOWN, risk_direction=Direction.DOWN)
    assert signal is not None
    assert signal.action is TradeAction.SELL
    assert signal.direction is Direction.DOWN


def test_the_signal_carries_composed_reasoning_from_its_inputs():
    signal, _ = _run()
    assert signal is not None
    # The reasoning names the side, the geometry and the verdict -- the parts
    # that actually produced it.
    assert "long" in signal.reasoning or "short" in signal.reasoning
    assert "100.0000" in signal.reasoning
    assert "stop" in signal.reasoning
    assert "critic" in signal.reasoning.lower()


def test_the_signal_carries_the_setups_evidence_and_confidence():
    signal, _ = _run()
    assert signal is not None
    assert signal.confidence is Confidence.MEDIUM
    assert signal.evidence == _setup().evidence


# ----------------------------------------------------------------------
# Each gate, rejected


def test_side_disagreement_is_rejected_as_a_wiring_error():
    signal, rejections = _run(setup_direction=Direction.UP, risk_direction=Direction.DOWN)
    assert signal is None
    assert len(rejections) == 1
    assert "side" in rejections[0]


def test_unactionable_risk_never_proposes():
    signal, rejections = _run(actionable=False)
    assert signal is None
    assert "actionable" in rejections[0]


@pytest.mark.parametrize(
    "verdict", [CriticVerdict.REJECT, CriticVerdict.INSUFFICIENT_EVIDENCE]
)
def test_the_signal_engine_never_overrules_the_critic(verdict):
    signal, rejections = _run(verdict=verdict)
    assert signal is None
    assert "critic" in rejections[0]
    assert verdict.value in rejections[0]


def test_a_missing_ratio_is_an_honest_decline():
    signal, rejections = _run(rr=None)
    assert signal is None
    assert "risk_reward" in rejections[0]
    assert "no measurable" in rejections[0]


def test_a_thin_ratio_is_rejected_with_its_numbers():
    signal, rejections = _run(rr=1.0)
    assert signal is None
    assert "risk_reward" in rejections[0]
    # The rejection cites the actual numbers so it can be checked by hand.
    assert "1.00" in rejections[0]
    assert f"{_MIN_REWARD:.2f}" in rejections[0]


def test_the_ratio_floor_is_inclusive():
    """A ratio exactly at the minimum passes: '>= minimum', not '>'."""
    signal, _ = _run(rr=_MIN_REWARD)
    assert signal is not None


# ----------------------------------------------------------------------
# Geometry sanity on the fired path


def test_fired_geometry_respects_the_buy_side_invariants():
    """The TradeSignal model itself enforces this; the gates must not bypass it."""
    signal, _ = _run()
    assert signal is not None
    assert signal.stop_loss < signal.entry
    assert signal.take_profit > signal.entry
