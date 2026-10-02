"""
CriticService: deterministic go/no-go validation of a proposed signal.

The critic never restates a signal -- it challenges it. These tests pin the
spec's core honesty rule (CLAUDE.md sections 5, 28, 61): the critic prefers
INSUFFICIENT_EVIDENCE over a fabricated APPROVE when the input is not sound
(mock/unusable data, no directional side, or no reliable evidence), REJECTs a
judged-but-wanting case (evidence conflicts with the fused direction, thin
risk/reward, or no measured edge over the historical baseline), and only
APPROVEs when every hard check passes. Every verdict is a fixed function of the
inputs -- no LLM, no fabrication. When a calibrated probability estimate is
supplied, a *reliable* one that contradicts the fused direction is the one place
the deterministic core lets the quant layer veto a signal; an unreliable one
only WARNs and an absent one is SKIPPED.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.domain.analysis import TradingAnalysis
from aetheros.trading.domain.anomaly import AnomalyAnalysis
from aetheros.trading.domain.historical_analogue import HistoricalAnalogueAnalysis
from aetheros.trading.domain.macro import MacroContext
from aetheros.trading.domain.multi_timeframe import MultiTimeframeAnalysis
from aetheros.trading.domain.backtest import BacktestResult
from aetheros.trading.domain.breakout import BreakoutAnalysis
from aetheros.trading.domain.divergence import DivergenceAnalysis
from aetheros.trading.domain.enums import (
    Assertion,
    CheckStatus,
    Confidence,
    CriticVerdict,
    DataQualityStatus,
    Direction,
    EvidenceType,
    MarketPosture,
    MarketRegime,
    RiskBand,
    TimeframeAlignment,
    SourceTier,
    Timeframe,
    TrendState,
)
from aetheros.trading.domain.evidence import Evidence
from aetheros.trading.domain.event_calendar import (
    EventCalendar,
    EventImpact,
    EventType,
    MarketEvent,
)
from aetheros.trading.domain.fundamentals import (
    FundamentalAnalysis,
    FundamentalFactor,
    FundamentalSnapshot,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.news import NewsAnalysis
from aetheros.trading.domain.probability import (
    CalibrationMetrics,
    ProbabilityEstimate,
)
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.domain.regime import RegimeAnalysis
from aetheros.trading.domain.risk import RiskAssessment
from aetheros.trading.domain.structure import MarketStructure
from aetheros.trading.domain.technical import TechnicalSnapshot
from aetheros.trading.events import SignalCritiqued
from aetheros.trading.services.critic_service import CriticService

import pytest

_INSTR = Instrument.parse("TEST")


def _prov(tier: SourceTier = SourceTier.PRIMARY) -> Provenance:
    return Provenance(source="test", tier=tier, detail="critic fixture")


def _quality(status: DataQualityStatus = DataQualityStatus.OK) -> DataQuality:
    return DataQuality(status=status, issues=(), freshness_seconds=0.0)


def _svc(event_bus: EventBus | None = None) -> CriticService:
    return CriticService(get_settings(), event_bus=event_bus)


def _evidence(
    direction: Direction,
    weight: float = 0.8,
    *,
    detail: str,
    assertion: Assertion = Assertion.CALCULATED,
    tier: SourceTier = SourceTier.PRIMARY,
    status: DataQualityStatus = DataQualityStatus.OK,
) -> Evidence:
    return Evidence(
        instrument_key=_INSTR.key,
        type=EvidenceType.TECHNICAL,
        assertion=assertion,
        direction=direction,
        detail=detail,
        weight=weight,
        confidence=Confidence.MEDIUM,
        provenance=_prov(tier),
        quality=_quality(status),
    )


def _technical() -> TechnicalSnapshot:
    return TechnicalSnapshot(
        timeframe=Timeframe.D1, last_price=100.0, bars=200, provenance=_prov()
    )


def _structure() -> MarketStructure:
    return MarketStructure(
        trend=TrendState.UPTREND,
        trend_strength=0.6,
        swings=(),
        supports=(),
        resistances=(),
        signals=(),
        higher_highs=True,
        higher_lows=True,
        lower_highs=False,
        lower_lows=False,
    )


def _analysis(
    direction: Direction,
    evidence: tuple[Evidence, ...] = (),
    *,
    tier: SourceTier = SourceTier.PRIMARY,
    status: DataQualityStatus = DataQualityStatus.OK,
    limitations: tuple[str, ...] = (),
) -> TradingAnalysis:
    score = 0.5 if direction is Direction.UP else -0.5 if direction is Direction.DOWN else 0.0
    return TradingAnalysis(
        instrument=_INSTR,
        timeframe_value="1d",
        last_price=100.0,
        direction=direction,
        directional_score=score,
        confidence=Confidence.MEDIUM,
        technical=_technical(),
        structure=_structure(),
        evidence=tuple(evidence),
        volume=None,
        quality=_quality(status),
        provenance=_prov(tier),
        limitations=tuple(limitations),
    )


def _risk(rr: float | None, *, direction: Direction = Direction.UP) -> RiskAssessment:
    return RiskAssessment(
        instrument=_INSTR,
        direction=direction,
        entry=100.0,
        stop_loss=98.0,
        stop_method="atr",
        target=(100.0 + rr * 2.0) if rr is not None else None,
        target_method="structural",
        targets=(),
        risk_per_unit=2.0,
        reward_per_unit=(rr * 2.0) if rr is not None else None,
        risk_reward_ratio=rr,
        stop_distance_pct=0.02,
        atr=2.0,
        atr_pct=0.02,
        volatility_risk=RiskBand.MEDIUM,
        overall_risk=RiskBand.MEDIUM,
        account_equity=None,
        risk_pct=None,
        risk_amount=None,
        position_size=None,
        position_notional=None,
        invalidation="close below 98",
        rationale=(),
        quality=_quality(),
        provenance=_prov(),
        is_actionable=True,
    )


def _backtest(
    *, accuracy: float | None, base_rate: float | None, is_reliable: bool = True
) -> BacktestResult:
    hits = int(round(accuracy * 100)) if accuracy is not None else 0
    return BacktestResult(
        instrument=_INSTR,
        timeframe="1d",
        horizon=5,
        warmup=50,
        total_bars=200,
        evaluated=100,
        directional_calls=100,
        hits=hits,
        directional_accuracy=accuracy,
        up_calls=100,
        up_hits=hits,
        up_accuracy=accuracy,
        down_calls=0,
        down_hits=0,
        down_accuracy=None,
        coverage=1.0,
        base_rate_up=base_rate,
        avg_return_per_trade=0.01,
        cumulative_return=1.0,
        max_drawdown=0.1,
        sharpe=0.5,
        quality=_quality(),
        provenance=_prov(),
        is_reliable=is_reliable,
    )


def _probability(
    direction: Direction,
    *,
    p_up: float = 0.7,
    is_reliable: bool = True,
    limitations: tuple[str, ...] = (),
    tier: SourceTier = SourceTier.DERIVED,
) -> ProbabilityEstimate:
    return ProbabilityEstimate(
        instrument=_INSTR,
        timeframe_value="1d",
        horizon=5,
        model_name="logistic_momentum",
        model_version="1.0.0",
        calibration_method="platt",
        feature_names=("rsi_14_centered", "momentum_10"),
        raw_p_up=p_up,
        p_up=p_up,
        p_down=round(1.0 - p_up, 6),
        direction=direction,
        confidence=Confidence.MEDIUM,
        is_reliable=is_reliable,
        provenance=_prov(tier),
        quality=_quality(),
        train_metrics=None,
        holdout_metrics=CalibrationMetrics(
            brier=0.20,
            log_loss=0.55,
            accuracy=0.60,
            ece=0.05,
            base_rate=0.5,
            sample_size=50,
        ),
        baseline_brier=0.25,
        limitations=limitations,
    )


def _news(
    direction: Direction,
    *,
    is_reliable: bool = True,
    tier: SourceTier = SourceTier.SECONDARY,
    sentiment_score: float = 0.4,
    item_count: int = 4,
    limitations: tuple[str, ...] = (),
) -> NewsAnalysis:
    return NewsAnalysis(
        instrument=_INSTR,
        items=(),  # the critic reads only the aggregate fields, not per-item
        direction=direction,
        sentiment_score=sentiment_score,
        positive_count=item_count if direction is Direction.UP else 0,
        negative_count=item_count if direction is Direction.DOWN else 0,
        neutral_count=item_count if direction in (Direction.SIDEWAYS, Direction.UNKNOWN) else 0,
        confidence=Confidence.MEDIUM,
        evidence=(),
        provenance=_prov(tier),
        quality=_quality(),
        is_reliable=is_reliable,
        limitations=limitations,
    )


def _calendar(
    *,
    has_high_impact: bool,
    is_reliable: bool = True,
    tier: SourceTier = SourceTier.SECONDARY,
    horizon_days: int = 7,
    limitations: tuple[str, ...] = (),
    with_event: bool = True,
) -> EventCalendar:
    """A controllable event calendar built directly for critic unit tests."""
    ref = datetime.now(timezone.utc)
    events: tuple[MarketEvent, ...] = ()
    if with_event:
        events = (
            MarketEvent(
                instrument_key=_INSTR.key,
                event_type=EventType.EARNINGS,
                title="TEST earnings",
                scheduled_at=ref + timedelta(days=3),
                impact=EventImpact.HIGH if has_high_impact else EventImpact.LOW,
                provenance=_prov(tier),
            ),
        )
    return EventCalendar(
        instrument=_INSTR,
        events=events,
        horizon_days=horizon_days,
        reference_time=ref,
        has_high_impact=has_high_impact,
        provenance=_prov(tier),
        quality=_quality(),
        is_reliable=is_reliable,
        limitations=limitations,
    )


def _fundamentals(
    direction: Direction,
    *,
    is_reliable: bool = True,
    tier: SourceTier = SourceTier.SECONDARY,
    health_score: float = 0.4,
    scored: int = 6,
    limitations: tuple[str, ...] = (),
) -> FundamentalAnalysis:
    """A controllable fundamental read built directly for critic unit tests."""
    snapshot = FundamentalSnapshot(
        instrument_key=_INSTR.key,
        provenance=_prov(tier),
        net_margin=0.2,
    )
    factors = tuple(
        FundamentalFactor(
            metric=f"m{i}",
            value=0.1,
            direction=direction,
            score=health_score,
            detail="fixture factor",
        )
        for i in range(scored)
    )
    return FundamentalAnalysis(
        instrument=_INSTR,
        snapshot=snapshot,
        direction=direction,
        health_score=health_score,
        confidence=Confidence.MEDIUM,
        factors=factors,
        evidence=(),
        provenance=_prov(tier),
        quality=_quality(),
        is_reliable=is_reliable,
        limitations=limitations,
    )


def _regime(
    regime: MarketRegime,
    *,
    is_reliable: bool = True,
    adx: float | None = 30.0,
    atr_pct: float | None = 0.01,
    limitations: tuple[str, ...] = (),
) -> RegimeAnalysis:
    """A controllable market-regime read built directly for critic unit tests.

    Reliability follows the RegimeAnalysis contract: a MOCK tier (or an UNKNOWN
    regime) is never reliable, anything else on OK data is.
    """
    tier = SourceTier.DERIVED if is_reliable else SourceTier.MOCK
    return RegimeAnalysis(
        instrument=_INSTR,
        timeframe_value="1d",
        regime=regime,
        adx=adx,
        trend_strength=(adx / 100.0) if adx is not None else None,
        atr_pct=atr_pct,
        realized_volatility=0.01,
        confidence=Confidence.MEDIUM,
        quality=_quality(),
        provenance=_prov(tier),
        observation="fixture regime",
        limitations=limitations,
    )


def _anomaly(
    direction: Direction,
    *,
    is_anomalous: bool = True,
    is_reliable: bool = True,
    lookback: int = 60,
    limitations: tuple[str, ...] = (),
) -> AnomalyAnalysis:
    """A controllable statistical-anomaly read built directly for critic tests.

    Reliability follows the AnomalyAnalysis contract: a MOCK tier (or an UNKNOWN
    direction) is never reliable, anything else on OK data is.
    """
    tier = SourceTier.DERIVED if is_reliable else SourceTier.MOCK
    return AnomalyAnalysis(
        instrument=_INSTR,
        timeframe_value="1d",
        lookback=lookback,
        is_anomalous=is_anomalous,
        return_z=3.5 if is_anomalous else 0.4,
        volume_z=1.0,
        gap_z=0.2,
        last_return=0.05 if direction is Direction.UP else -0.05,
        direction=direction,
        confidence=Confidence.MEDIUM,
        quality=_quality(),
        provenance=_prov(tier),
        observation="fixture anomaly",
        limitations=limitations,
    )


def _historical(
    direction: Direction,
    *,
    up_rate: float = 0.8,
    is_reliable: bool = True,
    neighbors: int = 25,
    limitations: tuple[str, ...] = (),
) -> HistoricalAnalogueAnalysis:
    """A controllable historical-analogue read built directly for critic tests.

    Reliability follows the HistoricalAnalogueAnalysis contract: a MOCK tier (or
    an UNKNOWN direction) is never reliable, anything else on OK data is.
    """
    tier = SourceTier.DERIVED if is_reliable else SourceTier.MOCK
    return HistoricalAnalogueAnalysis(
        instrument=_INSTR,
        timeframe_value="1d",
        horizon=5,
        sample_size=200,
        neighbors=neighbors,
        direction=direction,
        confidence=Confidence.MEDIUM,
        up_rate=up_rate,
        mean_forward_return=0.03 if direction is Direction.UP else -0.03,
        mean_distance=0.5,
        quality=_quality(),
        provenance=_prov(tier),
        observation="fixture analogue",
        limitations=limitations,
    )


def _macro(
    posture: MarketPosture,
    *,
    regime: MarketRegime = MarketRegime.TRENDING_UP,
    is_reliable: bool = True,
    limitations: tuple[str, ...] = (),
) -> MacroContext:
    """A controllable broad-market macro-context read for critic unit tests.

    Reliability follows the MacroContext contract: a MOCK tier (or an UNKNOWN
    posture) is never reliable, anything else on OK data is.
    """
    tier = SourceTier.DERIVED if is_reliable else SourceTier.MOCK
    return MacroContext(
        benchmark=Instrument.parse("SPY"),
        timeframe_value="1d",
        posture=posture,
        regime=regime,
        confidence=Confidence.MEDIUM,
        quality=_quality(),
        provenance=_prov(tier),
        observation="fixture macro",
        limitations=limitations,
    )


def _mtf(
    alignment: TimeframeAlignment,
    *,
    base_direction: Direction = Direction.UP,
    higher_direction: Direction = Direction.UP,
    is_reliable: bool = True,
    limitations: tuple[str, ...] = (),
) -> MultiTimeframeAnalysis:
    """A controllable multi-timeframe read built directly for critic unit tests.

    Reliability follows the MultiTimeframeAnalysis contract: a MOCK tier (or an
    UNKNOWN higher direction) is never reliable, anything else on OK data is.
    """
    tier = SourceTier.DERIVED if is_reliable else SourceTier.MOCK
    return MultiTimeframeAnalysis(
        instrument=_INSTR,
        base_timeframe="1d",
        higher_timeframe="1w",
        base_direction=base_direction,
        higher_direction=higher_direction,
        alignment=alignment,
        confidence=Confidence.MEDIUM,
        quality=_quality(),
        provenance=_prov(tier),
        higher_quality=_quality(),
        higher_provenance=_prov(tier),
        observation="fixture multi-timeframe",
        limitations=limitations,
    )


def _divergence(
    direction: Direction,
    *,
    has_divergence: bool = True,
    is_reliable: bool = True,
    limitations: tuple[str, ...] = (),
) -> DivergenceAnalysis:
    """A controllable momentum-divergence read for critic unit tests.

    Reliability follows the DivergenceAnalysis contract: a MOCK tier (or an
    UNKNOWN direction) is never reliable, anything else on OK data is.
    """
    tier = SourceTier.DERIVED if is_reliable else SourceTier.MOCK
    return DivergenceAnalysis(
        instrument=_INSTR,
        timeframe_value="1d",
        oscillator="rsi_14",
        has_divergence=has_divergence,
        direction=direction,
        confidence=Confidence.MEDIUM,
        price_change_pct=-0.03 if direction is Direction.UP else 0.03,
        oscillator_change=8.0 if direction is Direction.UP else -8.0,
        pivot_count=4,
        quality=_quality(),
        provenance=_prov(tier),
        observation="fixture divergence",
        limitations=limitations,
    )


def _breakout(
    direction: Direction,
    *,
    has_breakout: bool = True,
    volume_confirmed: bool = True,
    is_reliable: bool = True,
    limitations: tuple[str, ...] = (),
) -> BreakoutAnalysis:
    """A controllable channel-breakout read for critic unit tests.

    Reliability follows the BreakoutAnalysis contract: a MOCK tier (or an UNKNOWN
    direction) is never reliable, anything else on OK data is.
    """
    tier = SourceTier.DERIVED if is_reliable else SourceTier.MOCK
    return BreakoutAnalysis(
        instrument=_INSTR,
        timeframe_value="1d",
        lookback=20,
        has_breakout=has_breakout,
        direction=direction,
        confidence=Confidence.MEDIUM,
        channel_high=110.0,
        channel_low=90.0,
        last_close=112.0 if direction is Direction.UP else 88.0,
        volume_ratio=2.0 if volume_confirmed else 1.0,
        volume_confirmed=volume_confirmed,
        quality=_quality(),
        provenance=_prov(tier),
        observation="fixture breakout",
        limitations=limitations,
    )


def _status(report, name: str) -> CheckStatus:
    for check in report.checks:
        if check.name == name:
            return check.status
    raise AssertionError(f"no check named {name!r}")


def _sound_up_evidence() -> tuple[Evidence, ...]:
    return (
        _evidence(Direction.UP, 0.8, detail="price above sma50"),
        _evidence(Direction.UP, 0.7, detail="rising macd histogram"),
    )


# --- APPROVE: a sound, directional, corroborated case with good R:R ----------


@pytest.mark.asyncio
async def test_approves_sound_directional_case():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))

    assert report.verdict is CriticVerdict.APPROVE
    assert report.approved is True
    assert report.failed_checks == ()
    assert _status(report, "data_quality") is CheckStatus.PASS
    assert _status(report, "data_source") is CheckStatus.PASS
    assert _status(report, "direction_defined") is CheckStatus.PASS
    assert _status(report, "evidence_sufficiency") is CheckStatus.PASS
    assert _status(report, "signal_conflict") is CheckStatus.PASS
    assert _status(report, "risk_reward") is CheckStatus.PASS


@pytest.mark.asyncio
async def test_approves_with_historical_edge():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        backtest=_backtest(accuracy=0.6, base_rate=0.5),
    )
    assert report.verdict is CriticVerdict.APPROVE
    assert _status(report, "historical_reliability") is CheckStatus.PASS


@pytest.mark.asyncio
async def test_unreliable_backtest_warns_not_rejects():
    # A mock/thin backtest cannot confirm an edge -- WARN, never a hard FAIL.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        backtest=_backtest(accuracy=0.9, base_rate=0.5, is_reliable=False),
    )
    assert _status(report, "historical_reliability") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


# --- REJECT: judged, and found wanting ---------------------------------------


@pytest.mark.asyncio
async def test_rejects_conflicting_evidence():
    # Most of the directional weight opposes the fused UP call.
    analysis = _analysis(
        Direction.UP,
        (
            _evidence(Direction.UP, 0.3, detail="weak up momentum"),
            _evidence(Direction.DOWN, 0.8, detail="bearish divergence"),
            _evidence(Direction.DOWN, 0.8, detail="price below vwap"),
        ),
    )
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert report.verdict is CriticVerdict.REJECT
    assert _status(report, "signal_conflict") is CheckStatus.FAIL
    assert any("signal_conflict" in r for r in report.reasons)


@pytest.mark.asyncio
async def test_rejects_thin_risk_reward():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(1.0))  # below min reward
    assert report.verdict is CriticVerdict.REJECT
    assert _status(report, "risk_reward") is CheckStatus.FAIL
    assert any("risk_reward" in r for r in report.reasons)


@pytest.mark.asyncio
async def test_rejects_no_historical_edge():
    # A reliable backtest whose accuracy does not beat the naive up-rate baseline.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        backtest=_backtest(accuracy=0.5, base_rate=0.55),
    )
    assert report.verdict is CriticVerdict.REJECT
    assert _status(report, "historical_reliability") is CheckStatus.FAIL


# --- INSUFFICIENT_EVIDENCE: not enough sound input to judge at all -----------


@pytest.mark.asyncio
async def test_insufficient_on_mock_data():
    analysis = _analysis(
        Direction.UP,
        (_evidence(Direction.UP, 0.8, detail="mock up", tier=SourceTier.MOCK),),
        tier=SourceTier.MOCK,
        limitations=("Analysis rests on synthetic MOCK data.",),
    )
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert report.verdict is CriticVerdict.INSUFFICIENT_EVIDENCE
    assert report.approved is False
    assert _status(report, "data_source") is CheckStatus.FAIL


@pytest.mark.asyncio
async def test_insufficient_on_unknown_direction():
    analysis = _analysis(
        Direction.UNKNOWN,
        (_evidence(Direction.UP, 0.8, detail="lonely up hint"),),
    )
    report = await _svc().critique(analysis, risk=None)
    assert report.verdict is CriticVerdict.INSUFFICIENT_EVIDENCE
    assert _status(report, "direction_defined") is CheckStatus.FAIL


@pytest.mark.asyncio
async def test_insufficient_on_sideways_direction():
    analysis = _analysis(
        Direction.SIDEWAYS,
        (_evidence(Direction.UP, 0.6, detail="mild up"),),
    )
    report = await _svc().critique(analysis)
    assert report.verdict is CriticVerdict.INSUFFICIENT_EVIDENCE
    # SIDEWAYS is defined-but-not-tradable: WARN, not a hard FAIL.
    assert _status(report, "direction_defined") is CheckStatus.WARN


@pytest.mark.asyncio
async def test_insufficient_on_no_reliable_evidence():
    # INFERRED evidence is not reliable, so nothing corroborates the call.
    analysis = _analysis(
        Direction.UP,
        (_evidence(Direction.UP, 0.8, detail="inferred", assertion=Assertion.INFERRED),),
    )
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert report.verdict is CriticVerdict.INSUFFICIENT_EVIDENCE
    assert _status(report, "evidence_sufficiency") is CheckStatus.FAIL


# --- Probability calibration: a validated quant model can corroborate or veto -


@pytest.mark.asyncio
async def test_reliable_probability_agreeing_passes():
    # A calibrated model that agrees with the fused UP call PASSes the check.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        probability=_probability(Direction.UP, p_up=0.72),
    )
    assert _status(report, "probability_calibration") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_probability_contradicting_rejects():
    # The only place the deterministic core lets a *validated* probability veto
    # a signal: a reliable model pointing DOWN against a fused UP call is a hard
    # FAIL, which folds into REJECT (spec sections 5, 6, 28).
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        probability=_probability(Direction.DOWN, p_up=0.28),
    )
    assert _status(report, "probability_calibration") is CheckStatus.FAIL
    assert report.verdict is CriticVerdict.REJECT
    assert any("probability_calibration" in r for r in report.reasons)


@pytest.mark.asyncio
async def test_unreliable_probability_warns_not_rejects():
    # An unreliable/mock estimate cannot confirm an edge -- WARN, never a FAIL,
    # so it never flips an otherwise-sound APPROVE.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        probability=_probability(
            Direction.DOWN,
            p_up=0.28,
            is_reliable=False,
            limitations=("no out-of-sample edge over the naive baseline",),
        ),
    )
    assert _status(report, "probability_calibration") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_noncommittal_probability_warns():
    # Reliable but inside the dead-band around 0.5: it neither confirms nor
    # contradicts, so it WARNs rather than PASSing or FAILing.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        probability=_probability(Direction.SIDEWAYS, p_up=0.51),
    )
    assert _status(report, "probability_calibration") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_absent_probability_is_skipped():
    # No estimate supplied: the check is honestly SKIPPED, never silently passed.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "probability_calibration") is CheckStatus.SKIPPED


# --- News sentiment: soft, advisory corroboration that never vetoes ----------


@pytest.mark.asyncio
async def test_reliable_news_agreeing_passes():
    # A reliable read that agrees with the fused UP call PASSes the check.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), news=_news(Direction.UP)
    )
    assert _status(report, "news_sentiment") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_news_opposing_warns_never_rejects():
    # News is soft, advisory context: even a reliable read pointing DOWN against
    # a fused UP call only WARNs -- it never single-handedly rejects a signal.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), news=_news(Direction.DOWN, sentiment_score=-0.4)
    )
    assert _status(report, "news_sentiment") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_unreliable_news_warns_not_rejects():
    # A mock/thin read cannot confirm a catalyst -- WARN, never a FAIL.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        news=_news(
            Direction.DOWN,
            is_reliable=False,
            tier=SourceTier.MOCK,
            limitations=("News sentiment rests on synthetic MOCK headlines.",),
        ),
    )
    assert _status(report, "news_sentiment") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_noncommittal_news_warns():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), news=_news(Direction.SIDEWAYS, sentiment_score=0.0)
    )
    assert _status(report, "news_sentiment") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_absent_news_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "news_sentiment") is CheckStatus.SKIPPED


# --- Event risk: a reliable high-impact calendar can veto; mock never does ----


@pytest.mark.asyncio
async def test_reliable_high_impact_calendar_rejects():
    # The event_risk check is the calendar counterpart to the probability veto:
    # a reliable calendar carrying a high-impact event inside the horizon is a
    # hard FAIL, which folds into REJECT (spec section 5's earnings example).
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        calendar=_calendar(has_high_impact=True),
    )
    assert _status(report, "event_risk") is CheckStatus.FAIL
    assert report.verdict is CriticVerdict.REJECT
    assert any("event_risk" in r for r in report.reasons)


@pytest.mark.asyncio
async def test_reliable_calendar_no_high_impact_passes():
    # A reliable calendar with no high-impact event in the horizon clears the
    # check and does not stand in the way of an otherwise-sound APPROVE.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        calendar=_calendar(has_high_impact=False),
    )
    assert _status(report, "event_risk") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_unreliable_calendar_warns_not_rejects():
    # A MOCK/unreliable calendar cannot confirm or rule out event risk -- WARN,
    # never a FAIL, so a synthetic calendar never vetoes a real signal.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        calendar=_calendar(
            has_high_impact=True,
            is_reliable=False,
            tier=SourceTier.MOCK,
            limitations=("Event calendar rests on synthetic MOCK entries.",),
        ),
    )
    assert _status(report, "event_risk") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_calendar_skipped_when_not_directional():
    # Nothing to guard when there is no tradable side: the check SKIPs even with
    # a reliable high-impact calendar present.
    analysis = _analysis(
        Direction.SIDEWAYS, (_evidence(Direction.UP, 0.6, detail="mild up"),)
    )
    report = await _svc().critique(
        analysis, risk=_risk(2.0), calendar=_calendar(has_high_impact=True)
    )
    assert _status(report, "event_risk") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_absent_calendar_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "event_risk") is CheckStatus.SKIPPED


# --- Fundamentals: soft, longer-horizon corroboration that never vetoes -------


@pytest.mark.asyncio
async def test_reliable_fundamentals_agreeing_passes():
    # A reliable fundamental read agreeing with the fused UP call PASSes.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), fundamentals=_fundamentals(Direction.UP)
    )
    assert _status(report, "fundamentals") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_fundamentals_opposing_warns_never_rejects():
    # Fundamentals sit on a longer horizon than a short-term technical call, so
    # even a reliable read pointing DOWN against a fused UP call only WARNs -- it
    # never single-handedly rejects the near-term signal.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        fundamentals=_fundamentals(Direction.DOWN, health_score=-0.4),
    )
    assert _status(report, "fundamentals") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_unreliable_fundamentals_warns_not_rejects():
    # A mock/thin read cannot confirm a real fundamental picture -- WARN, never
    # a FAIL, so it never flips an otherwise-sound APPROVE.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        fundamentals=_fundamentals(
            Direction.DOWN,
            is_reliable=False,
            tier=SourceTier.MOCK,
            limitations=("Fundamentals rest on synthetic MOCK financials.",),
        ),
    )
    assert _status(report, "fundamentals") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_noncommittal_fundamentals_warns():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        fundamentals=_fundamentals(Direction.SIDEWAYS, health_score=0.02),
    )
    assert _status(report, "fundamentals") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_absent_fundamentals_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "fundamentals") is CheckStatus.SKIPPED


# --- Market regime: soft, situational corroboration that never vetoes --------


@pytest.mark.asyncio
async def test_reliable_trending_regime_aligned_passes():
    # A reliable up-trending regime aligned with the fused UP call PASSes.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), regime=_regime(MarketRegime.TRENDING_UP)
    )
    assert _status(report, "market_regime") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_countertrend_regime_warns_never_rejects():
    # A reliable down-trending regime against a fused UP call is a counter-trend
    # caution: it WARNs but never single-handedly rejects the signal.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), regime=_regime(MarketRegime.TRENDING_DOWN)
    )
    assert _status(report, "market_regime") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_ranging_regime_warns():
    # A directional call in a range-bound tape is a caution, not a veto.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), regime=_regime(MarketRegime.RANGING, adx=15.0)
    )
    assert _status(report, "market_regime") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_volatile_regime_warns():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), regime=_regime(MarketRegime.VOLATILE, atr_pct=0.08)
    )
    assert _status(report, "market_regime") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_unreliable_regime_warns_not_rejects():
    # A MOCK/unreliable regime cannot confirm the market context -- WARN, never a
    # FAIL, so a synthetic regime never vetoes a real signal.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        regime=_regime(
            MarketRegime.TRENDING_DOWN,
            is_reliable=False,
            limitations=("Regime derived from MOCK data.",),
        ),
    )
    assert _status(report, "market_regime") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_unknown_regime_is_skipped():
    # An undetermined regime carries nothing to weigh the signal against.
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), regime=_regime(MarketRegime.UNKNOWN, adx=None)
    )
    assert _status(report, "market_regime") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_regime_skipped_when_not_directional():
    analysis = _analysis(
        Direction.SIDEWAYS, (_evidence(Direction.UP, 0.6, detail="mild up"),)
    )
    report = await _svc().critique(
        analysis, risk=_risk(2.0), regime=_regime(MarketRegime.TRENDING_UP)
    )
    assert _status(report, "market_regime") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_absent_regime_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "market_regime") is CheckStatus.SKIPPED


# --- Honesty about what this build cannot yet check ---------------------------


@pytest.mark.asyncio
async def test_reliable_agreeing_anomaly_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), anomaly=_anomaly(Direction.UP)
    )
    assert _status(report, "anomaly") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_opposing_anomaly_warns_never_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), anomaly=_anomaly(Direction.DOWN)
    )
    # An unusual move against the call is a caution, never a veto.
    assert _status(report, "anomaly") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_quiet_tape_anomaly_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        anomaly=_anomaly(Direction.SIDEWAYS, is_anomalous=False),
    )
    # No anomaly on a reliable read is a clean, expected state -> PASS.
    assert _status(report, "anomaly") is CheckStatus.PASS


@pytest.mark.asyncio
async def test_volume_only_anomaly_warns():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        anomaly=_anomaly(Direction.SIDEWAYS, is_anomalous=True),
    )
    # A non-directional (volume-only) spike neither confirms nor contradicts.
    assert _status(report, "anomaly") is CheckStatus.WARN


@pytest.mark.asyncio
async def test_unreliable_anomaly_warns_not_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        anomaly=_anomaly(Direction.UP, is_reliable=False, limitations=("MOCK",)),
    )
    assert _status(report, "anomaly") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_absent_anomaly_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "anomaly") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_reliable_agreeing_historical_analogue_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), historical_analogue=_historical(Direction.UP)
    )
    assert _status(report, "historical_analogue") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_opposing_historical_analogue_warns_never_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        historical_analogue=_historical(Direction.DOWN, up_rate=0.2),
    )
    # A contrary past tendency is a caution, never a veto.
    assert _status(report, "historical_analogue") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_inconclusive_historical_analogue_warns():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        historical_analogue=_historical(Direction.SIDEWAYS, up_rate=0.5),
    )
    assert _status(report, "historical_analogue") is CheckStatus.WARN


@pytest.mark.asyncio
async def test_unreliable_historical_analogue_warns_not_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        historical_analogue=_historical(
            Direction.UP, is_reliable=False, limitations=("MOCK",)
        ),
    )
    assert _status(report, "historical_analogue") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_absent_historical_analogue_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "historical_analogue") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_reliable_agreeing_macro_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), macro=_macro(MarketPosture.RISK_ON)
    )
    assert _status(report, "macro_context") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_reliable_opposing_macro_warns_never_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        macro=_macro(MarketPosture.RISK_OFF, regime=MarketRegime.TRENDING_DOWN),
    )
    # A risk-off tape against a bullish call is a caution, never a veto.
    assert _status(report, "macro_context") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_neutral_macro_warns():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        macro=_macro(MarketPosture.NEUTRAL, regime=MarketRegime.RANGING),
    )
    assert _status(report, "macro_context") is CheckStatus.WARN


@pytest.mark.asyncio
async def test_unreliable_macro_warns_not_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        macro=_macro(MarketPosture.RISK_ON, is_reliable=False, limitations=("MOCK",)),
    )
    assert _status(report, "macro_context") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_absent_macro_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "macro_context") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_confirmed_multi_timeframe_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), multi_timeframe=_mtf(TimeframeAlignment.CONFIRMED)
    )
    assert _status(report, "multi_timeframe") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_conflicting_multi_timeframe_warns_never_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        multi_timeframe=_mtf(
            TimeframeAlignment.CONFLICT, higher_direction=Direction.DOWN
        ),
    )
    # A counter-trend call is a caution, never a veto.
    assert _status(report, "multi_timeframe") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_neutral_multi_timeframe_warns():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        multi_timeframe=_mtf(
            TimeframeAlignment.NEUTRAL, higher_direction=Direction.SIDEWAYS
        ),
    )
    assert _status(report, "multi_timeframe") is CheckStatus.WARN


@pytest.mark.asyncio
async def test_unreliable_multi_timeframe_warns_not_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        multi_timeframe=_mtf(
            TimeframeAlignment.CONFIRMED, is_reliable=False, limitations=("MOCK",)
        ),
    )
    assert _status(report, "multi_timeframe") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_unknown_multi_timeframe_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        multi_timeframe=_mtf(
            TimeframeAlignment.UNKNOWN, higher_direction=Direction.UNKNOWN
        ),
    )
    assert _status(report, "multi_timeframe") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_absent_multi_timeframe_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "multi_timeframe") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_agreeing_divergence_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), divergence=_divergence(Direction.UP)
    )
    assert _status(report, "divergence") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_opposing_divergence_warns_never_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), divergence=_divergence(Direction.DOWN)
    )
    assert _status(report, "divergence") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_no_divergence_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        divergence=_divergence(Direction.SIDEWAYS, has_divergence=False),
    )
    assert _status(report, "divergence") is CheckStatus.PASS


@pytest.mark.asyncio
async def test_unreliable_divergence_warns_not_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        divergence=_divergence(Direction.UP, is_reliable=False, limitations=("MOCK",)),
    )
    assert _status(report, "divergence") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_absent_divergence_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "divergence") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_agreeing_breakout_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), breakout=_breakout(Direction.UP)
    )
    assert _status(report, "breakout") is CheckStatus.PASS
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_opposing_breakout_warns_never_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis, risk=_risk(2.0), breakout=_breakout(Direction.DOWN)
    )
    assert _status(report, "breakout") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_no_breakout_passes():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        breakout=_breakout(Direction.SIDEWAYS, has_breakout=False),
    )
    assert _status(report, "breakout") is CheckStatus.PASS


@pytest.mark.asyncio
async def test_unreliable_breakout_warns_not_rejects():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(
        analysis,
        risk=_risk(2.0),
        breakout=_breakout(Direction.UP, is_reliable=False, limitations=("MOCK",)),
    )
    assert _status(report, "breakout") is CheckStatus.WARN
    assert report.verdict is CriticVerdict.APPROVE


@pytest.mark.asyncio
async def test_absent_breakout_is_skipped():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))
    assert _status(report, "breakout") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_undoable_checks_are_skipped_not_passed():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc().critique(analysis, risk=_risk(2.0))  # no backtest supplied
    assert _status(report, "probability_calibration") is CheckStatus.SKIPPED
    assert _status(report, "event_risk") is CheckStatus.SKIPPED
    assert _status(report, "historical_reliability") is CheckStatus.SKIPPED
    assert _status(report, "fundamentals") is CheckStatus.SKIPPED
    assert _status(report, "market_regime") is CheckStatus.SKIPPED
    assert _status(report, "relative_strength") is CheckStatus.SKIPPED
    assert _status(report, "anomaly") is CheckStatus.SKIPPED
    assert _status(report, "historical_analogue") is CheckStatus.SKIPPED
    assert _status(report, "macro_context") is CheckStatus.SKIPPED
    assert _status(report, "multi_timeframe") is CheckStatus.SKIPPED
    assert _status(report, "divergence") is CheckStatus.SKIPPED
    assert _status(report, "breakout") is CheckStatus.SKIPPED


@pytest.mark.asyncio
async def test_deterministic():
    analysis = _analysis(Direction.UP, _sound_up_evidence())
    r1 = await _svc().critique(analysis, risk=_risk(2.0))
    r2 = await _svc().critique(analysis, risk=_risk(2.0))
    assert r1.verdict == r2.verdict
    assert [(c.name, c.status) for c in r1.checks] == [
        (c.name, c.status) for c in r2.checks
    ]


@pytest.mark.asyncio
async def test_publishes_signal_critiqued():
    received: list[SignalCritiqued] = []
    bus = EventBus()
    await bus.subscribe(SignalCritiqued, lambda e: received.append(e))

    analysis = _analysis(Direction.UP, _sound_up_evidence())
    report = await _svc(bus).critique(analysis, risk=_risk(2.0))

    assert len(received) == 1
    evt = received[0]
    assert evt.verdict == report.verdict.value
    assert evt.approved == report.approved
    assert evt.direction == "up"
    assert evt.check_count == len(report.checks)
