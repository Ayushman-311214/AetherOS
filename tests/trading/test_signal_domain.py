"""
Signal-layer value objects: validation and serialisation.

The guards that keep the signal layer honest at the model level: a candidate
must be directional, must share its side with its signal and its risk
geometry, must carry the critic's verdict, and must be content-addressed so
an audit trail can de-duplicate re-derivations. An evaluation with zero fired
candidates is a valid, first-class result.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from aetheros.trading.domain.critique import CriticCheck, CriticReport
from aetheros.trading.domain.enums import (
    CheckStatus,
    Confidence,
    CriticVerdict,
    Direction,
    RiskBand,
    StrategyCategory,
    TradeAction,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.signal import SignalCandidate, SignalEvaluation
from aetheros.trading.domain.strategy import StrategyRuleMatch, StrategySetup
from aetheros.trading.domain.trade import TradeSignal

from .test_critic import _analysis, _prov, _quality, _risk

CATEGORY = StrategyCategory.TREND_FOLLOWING
_INSTR = Instrument.parse("TEST")

#: Sentinel distinguishing "no signal argument given" (build one) from
#: "explicitly declined" (keep None). Without it a signal=None default would
#: be rebuilt into a fired signal and every declined-candidate test would lie.
_DEFAULT = object()


def _setup(direction: Direction = Direction.UP) -> StrategySetup:
    analysis = _analysis(direction)
    return StrategySetup(
        instrument=analysis.instrument,
        strategy_id="trend_following",
        strategy_name="Trend Following",
        category=CATEGORY,
        timeframe="1d",
        direction=direction,
        confidence=Confidence.MEDIUM,
        entry_reference=analysis.last_price,
        invalidation_level=(
            analysis.last_price - 2.0
            if direction is Direction.UP
            else analysis.last_price + 2.0
        ),
        rules=(
            StrategyRuleMatch(
                rule="structure is directional",
                satisfied=True,
                detail="Structure reads 'uptrend'.",
            ),
        ),
        evidence=(),
        reasoning="Structure is up and momentum agrees.",
        quality=analysis.quality,
        provenance=analysis.provenance,
    )


def _signal(direction: Direction = Direction.UP) -> TradeSignal:
    entry = 100.0
    stop = 98.0 if direction is Direction.UP else 102.0
    target = 104.0 if direction is Direction.UP else 96.0
    return TradeSignal(
        instrument=_INSTR,
        action=TradeAction.BUY if direction is Direction.UP else TradeAction.SELL,
        direction=direction,
        confidence=Confidence.MEDIUM,
        risk=RiskBand.MEDIUM,
        reasoning="A fully judged proposal.",
        evidence=(),
        entry=entry,
        stop_loss=stop,
        take_profit=target,
        strategy_id="trend_following",
    )


def _critique(verdict: CriticVerdict = CriticVerdict.APPROVE) -> CriticReport:
    return CriticReport(
        instrument=_INSTR,
        direction=Direction.UP,
        verdict=verdict,
        checks=(
            CriticCheck(
                name="data_source",
                status=CheckStatus.PASS,
                detail="Data is real and fresh.",
            ),
        ),
        reasons=("The evidence is sufficient and agrees.",),
        quality=_quality(),
        provenance=_prov(),
    )


def make_candidate(
    *,
    direction: Direction = Direction.UP,
    signal: TradeSignal | None | object = _DEFAULT,
    verdict: CriticVerdict = CriticVerdict.APPROVE,
    rr: float | None = 2.0,
) -> SignalCandidate:
    if signal is _DEFAULT:
        signal = _signal(direction)
    return SignalCandidate(
        strategy_id="trend_following",
        strategy_name="Trend Following",
        category=CATEGORY,
        timeframe="1d",
        direction=direction,
        signal=signal,  # type: ignore[arg-type]
        risk=_risk(rr, direction=direction),
        critique=_critique(verdict),
    )


# ----------------------------------------------------------------------
# SignalCandidate


def test_candidate_must_be_directional():
    for direction in (Direction.SIDEWAYS, Direction.UNKNOWN):
        # The TradeSignal guard fires first on the nested signal; the test
        # passes None so the *candidate's own* guard is the one exercised.
        with pytest.raises(ValueError, match="must be directional"):
            make_candidate(direction=direction, signal=None)


def test_candidate_rejects_a_signal_on_the_other_side():
    with pytest.raises(ValueError, match="share its side"):
        make_candidate(direction=Direction.UP, signal=_signal(Direction.DOWN))


def test_candidate_rejects_a_signal_from_another_strategy():
    stranger = replace(_signal(), strategy_id="mean_reversion")
    with pytest.raises(ValueError, match="come from that strategy"):
        make_candidate(signal=stranger)


def test_candidate_rejects_risk_geometry_on_the_other_side():
    with pytest.raises(ValueError, match="share its side"):
        SignalCandidate(
            strategy_id="trend_following",
            strategy_name="Trend Following",
            category=CATEGORY,
            timeframe="1d",
            direction=Direction.UP,
            signal=_signal(Direction.UP),
            risk=_risk(2.0, direction=Direction.DOWN),
            critique=_critique(),
        )


def test_candidate_id_is_content_addressed_and_stable():
    first = make_candidate()
    second = make_candidate()
    assert first.candidate_id == second.candidate_id
    assert first.candidate_id.startswith("sg_")

    # A candidate that did not fire has a different id: "no proposal" is a
    # different fact from "proposal at 100 with stop 98".
    declined = make_candidate(signal=None)
    assert declined.candidate_id != first.candidate_id


def test_a_declined_candidate_is_first_class():
    declined = make_candidate(signal=None, verdict=CriticVerdict.REJECT)
    assert not declined.fired
    assert declined.risk_band is RiskBand.MEDIUM
    # The candidate still carries its full judgement trail.
    assert declined.critique.verdict is CriticVerdict.REJECT


def test_candidate_to_dict_exposes_the_full_trail():
    payload = make_candidate().to_dict()
    assert payload["fired"] is True
    assert payload["direction"] == "up"
    assert payload["signal"]["action"] == "buy"
    assert payload["risk"]["direction"] == "up"
    assert payload["critique"]["verdict"] == "approve"
    assert payload["rejections"] == []


# ----------------------------------------------------------------------
# SignalEvaluation


def test_evaluation_with_zero_candidates_is_the_honest_result():
    evaluation = SignalEvaluation(
        instrument_key="TEST",
        timeframe="1d",
        limitations=("No strategy produced a setup.",),
    )
    assert evaluation.signal_count == 0
    assert evaluation.consensus is Direction.UNKNOWN
    assert evaluation.fired_strategies == ()


def test_evaluation_consensus_requires_agreement():
    up = make_candidate(direction=Direction.UP)
    down = make_candidate(direction=Direction.DOWN)
    mixed = SignalEvaluation(
        instrument_key="TEST",
        timeframe="1d",
        candidates=(up, down),
        signals=(_signal(Direction.UP), _signal(Direction.DOWN)),
    )
    assert mixed.consensus is Direction.UNKNOWN  # disagreement is not averaged

    agreed = SignalEvaluation(
        instrument_key="TEST",
        timeframe="1d",
        candidates=(up,),
        signals=(_signal(Direction.UP),),
    )
    assert agreed.consensus is Direction.UP


def test_evaluation_validates_its_signals_match_its_candidates():
    # Two candidates, one fired -- the signals tuple must mirror exactly the
    # fired subset, in order.
    with pytest.raises(ValueError, match="exactly its fired candidates"):
        SignalEvaluation(
            instrument_key="TEST",
            timeframe="1d",
            candidates=(make_candidate(), make_candidate(signal=None)),
            signals=(),  # one candidate fired, so this is inconsistent
        )


def test_evaluation_validates_instrument_of_candidates():
    other = make_candidate()
    with pytest.raises(ValueError, match="describe its instrument"):
        SignalEvaluation(
            instrument_key="OTHER",
            timeframe="1d",
            candidates=(other,),
            signals=(_signal(),),
        )
