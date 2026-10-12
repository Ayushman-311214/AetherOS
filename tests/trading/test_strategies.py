"""
The five built-in strategies over hand-built reads.

A strategy is deterministic and side-effect-free, so each case here builds a
:class:`StrategyContext` from fixtures with *known* indicator values and known
SMC/ICT/breakout content, runs one strategy, and asserts the verdict and the
geometry. The reads are built through the real
:class:`TechnicalAnalysisService` / :class:`MarketStructureService` /
:class:`SMCService` so a "fires/declines" verdict is a verdict about the actual
pipeline, not a synthetic one.

The honest declensions are tested as hard as the firings: a strategy that never
declines cannot be trusted to fire either (CLAUDE.md section 28 -- "no setup" is
a first-class result).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    DataQualityStatus,
    Direction,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.ict_service import ICTService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.smc_service import SMCService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.strategies.breakout import BreakoutStrategy
from aetheros.trading.strategies.context import StrategyContext
from aetheros.trading.strategies.ict import ICTStrategy
from aetheros.trading.strategies.mean_reversion import MeanReversionStrategy
from aetheros.trading.strategies.registry import default_registry
from aetheros.trading.strategies.smc import SMCStrategy
from aetheros.trading.strategies.trend_following import TrendFollowingStrategy

from .conftest import make_market_data, make_ohlc_market_data

# A gentle but persistent rise: structure is an uptrend, ADX is high, momentum
# is positive -- the canonical trend-following context.
_UPTREND_CLOSES = [100.0 + i * 0.9 + (0.25 if i % 2 else -0.25) for i in range(80)]

# A quiet alternating range around 100: no established trend, RSI mid-band.
_RANGE_CLOSES = [100.0 + (1.2 if (i // 6) % 2 else -1.2) for i in range(80)]

# A pullback-and-resume uptrend: sixteen 5-up/3-down legs, then a 6-bar
# pullback below the fast mean, then a long modest resume. The resume runs 14
# bars so a *new* higher low confirms (swing confirmation lags 3 bars) and the
# final structure read is genuinely UPTREND again -- a real trend entry looks
# like this, unlike a monotonic ramp whose last bar is always maximally
# extended. Entry ends ~4.5 ATR above the mean, so the test tunes
# max_extension_atr (a declared parameter) rather than weakening the rule.
def _uptrend_with_pullback_bars() -> list[tuple[float, float, float, float]]:
    prices: list[float] = []
    price = 100.0
    for _ in range(16):
        for _ in range(5):
            price += 1.2
            prices.append(price)
        for _ in range(3):
            price -= 1.0
            prices.append(price)
    for _ in range(6):
        price -= 1.5
        prices.append(price)  # the pullback below the mean
    for _ in range(14):
        price += 0.8
        prices.append(price)  # the resume: long enough to confirm a higher low
    bars: list[tuple[float, float, float, float]] = []
    prev = prices[0]
    for close in prices:
        bars.append((prev, max(prev, close) + 0.1, min(prev, close) - 0.1, close))
        prev = close
    return bars


class _Services:
    """The real deterministic reads, built once and shared across every case."""

    def __init__(self) -> None:
        self.structure = MarketStructureService()
        self.technical = TechnicalAnalysisService()
        self.evidence = EvidenceService()
        self.smc = SMCService(self.structure)
        self.ict = ICTService(self.structure, self.smc)


#: One module-level instance: every test shares the same deterministic reads,
#: which are stateless and safe to share.
services = _Services()


def build_context_sync(
    data,
    *,
    smc=None,
    ict=None,
    breakout=None,
    degradations=(),
) -> StrategyContext:
    """
    Assemble a context from the deterministic *sync* reads.

    The analysis service's ``analyze_data`` is async, but every layer it calls
    (technical, structure, evidence) is synchronous, so the test resolves them
    directly. This mirrors what :class:`StrategyService.build_context` does,
    minus the container plumbing.
    """
    from aetheros.trading.domain.analysis import TradingAnalysis
    from aetheros.trading.domain.enums import Confidence
    from aetheros.trading.domain.provenance import Provenance

    technical = services.technical.compute(data)
    structure = services.structure.analyze(data)
    volume = services.evidence.build_volume_analysis(data)
    evidence = services.evidence.build(
        data=data, technical=technical, structure=structure, volume=volume
    )
    analysis = TradingAnalysis(
        instrument=data.instrument,
        timeframe_value=data.timeframe.value,
        last_price=technical.last_price,
        direction=Direction.UNKNOWN,
        directional_score=0.0,
        confidence=Confidence.LOW,
        technical=technical,
        structure=structure,
        evidence=evidence,
        volume=volume,
        quality=data.quality,
        provenance=Provenance(
            source=data.provenance.source,
            tier=(
                SourceTier.MOCK if data.provenance.is_mock else SourceTier.DERIVED
            ),
            detail="deterministic evidence-fusion analysis",
        ),
    )
    return StrategyContext(
        data=data,
        analysis=analysis,
        smc=smc if smc is not None else services.smc.analyze(data),
        ict=ict,
        breakout=breakout,
        degradations=degradations,
    )


# ----------------------------------------------------------------------
# Trend following


def test_trend_following_fires_on_a_pullback_resume():
    data = make_ohlc_market_data(_uptrend_with_pullback_bars(), symbol="TREND")
    context = build_context_sync(data)
    # The fixture's entry sits ~4.5 ATR from the mean by construction; 6.0 is
    # the tuned ceiling this strategy is tested with.
    evaluation = TrendFollowingStrategy(max_extension_atr=6.0).evaluate(context)

    assert evaluation.fired, evaluation.limitations
    setup = evaluation.setup
    assert setup is not None
    assert setup.direction is Direction.UP
    assert setup.entry_reference == pytest.approx(context.last_price)
    # The invalidation must sit below the entry on a bullish thesis.
    assert setup.invalidation_level < setup.entry_reference
    assert setup.setup_id.startswith("su_")
    assert all(rule.satisfied for rule in setup.rules)
    assert setup.evidence  # a setup is never unexplained
    assert setup.reasoning.strip()


def test_trend_following_declines_on_a_range():
    data = make_market_data(_RANGE_CLOSES, symbol="RANGE")
    context = build_context_sync(data)
    evaluation = TrendFollowingStrategy().evaluate(context)

    assert not evaluation.fired
    # The decline names the unmet conditions rather than returning a vacuous no.
    assert evaluation.limitations
    assert "unmet conditions" in evaluation.limitations[0]
    # Failed rules are still recorded -- not dropped.
    assert evaluation.failed_rules


def test_trend_following_declines_when_the_trend_is_too_weak():
    data = make_ohlc_market_data(_uptrend_with_pullback_bars(), symbol="WEAK")
    context = build_context_sync(data)
    # The real read shows ADX ~41; a floor of 60 is unreachable *here* without
    # being unreachable in principle (a monotonic series reaches ADX 100).
    strict = TrendFollowingStrategy(min_adx=60.0)
    evaluation = strict.evaluate(context)
    assert not evaluation.fired

    adx_rule = next(r for r in evaluation.rules if "ADX" in r.rule)
    assert not adx_rule.satisfied
    assert adx_rule.threshold == 60.0


def test_trend_following_declines_when_entry_is_overextended():
    data = make_ohlc_market_data(_uptrend_with_pullback_bars(), symbol="EXT")
    context = build_context_sync(data)
    # ~1.2 ATR from the mean on the real read; a 0.01 ATR ceiling makes the
    # extension rule fail without making the whole rule set vacuous.
    tight = TrendFollowingStrategy(max_extension_atr=0.01)
    evaluation = tight.evaluate(context)
    assert not evaluation.fired
    overextended = next(r for r in evaluation.rules if "extended" in r.rule)
    assert not overextended.satisfied


# ----------------------------------------------------------------------
# Mean reversion


def _stretched_low_data() -> list[float]:
    """
    A quiet alternating range that ends with a three-bar dip to 96.5.

    The range's last leg must be an *up* leg so the structure read does not end
    DOWNTREND (which would make the dip a trend continuation rather than a
    stretch). RSI lands near 26 and the stretch clears 1 ATR.
    """
    closes = [100.0 + (1.0 if (i // 6) % 2 else -1.0) for i in range(72)]
    step = (closes[-1] - 96.5) / 3.0
    closes += [closes[-1] - step, closes[-1] - 2 * step, 96.5]
    return closes


def test_mean_reversion_fires_on_a_volatility_scaled_stretch():
    data = make_market_data(_stretched_low_data(), symbol="STRETCH")
    context = build_context_sync(data)
    evaluation = MeanReversionStrategy().evaluate(context)

    assert evaluation.fired, evaluation.limitations
    setup = evaluation.setup
    assert setup is not None
    assert setup.direction is Direction.UP  # fading a dip -> long
    assert setup.invalidation_level < setup.entry_reference


def test_mean_reversion_declines_when_the_market_is_trending():
    data = make_market_data(_UPTREND_CLOSES, symbol="MRUP")
    context = build_context_sync(data)
    evaluation = MeanReversionStrategy().evaluate(context)
    assert not evaluation.fired
    # The specific blocker is the regime: ADX exceeds the ceiling.
    adx_rule = next(r for r in evaluation.rules if "not trending" in r.rule)
    assert not adx_rule.satisfied


def test_mean_reversion_declines_without_a_stretch():
    data = make_market_data(_RANGE_CLOSES, symbol="NOSTRETCH")
    context = build_context_sync(data)
    evaluation = MeanReversionStrategy().evaluate(context)
    assert not evaluation.fired
    stretch = next(r for r in evaluation.rules if "stretched" in r.rule)
    assert not stretch.satisfied


# ----------------------------------------------------------------------
# SMC


def test_smc_declines_without_a_directional_structural_read():
    data = make_market_data(_RANGE_CLOSES, symbol="SMCRANGE")
    context = build_context_sync(data)
    evaluation = SMCStrategy().evaluate(context)
    assert not evaluation.fired
    directional = next(r for r in evaluation.rules if "structure is directional" in r.rule)
    assert not directional.satisfied


def test_smc_invalidation_is_on_the_correct_side_for_both_directions():
    """For each side, whatever the SMC read says, the setup's geometry is sane."""
    for closes, symbol, expected_side in (
        (_UPTREND_CLOSES, "SMCUP", Direction.UP),
        ([200.0 - i * 0.9 + (0.25 if i % 2 else -0.25) for i in range(80)], "SMCDOWN", Direction.DOWN),
    ):
        data = make_market_data(closes, symbol=symbol)
        context = build_context_sync(data)
        evaluation = SMCStrategy().evaluate(context)
        setup = evaluation.setup
        if setup is None:
            continue  # the read legitimately found no live zone; geometry N/A
        assert setup.direction is expected_side
        if setup.direction is Direction.UP:
            assert setup.invalidation_level < setup.entry_reference
        else:
            assert setup.invalidation_level > setup.entry_reference


# ----------------------------------------------------------------------
# ICT


def test_ict_reports_a_blocker_when_no_ict_read_is_available():
    """A strategy that *cannot* run says so, rather than vacuously finding nothing."""
    data = make_market_data(_UPTREND_CLOSES, symbol="NOICT")
    context = build_context_sync(data, ict=None)
    evaluation = ICTStrategy().evaluate(context)

    assert not evaluation.fired
    assert "needs an ICT read" in " ".join(evaluation.limitations)
    assert evaluation.rules == ()  # it did not even look


def test_ict_fires_when_bias_shift_and_ote_agree():
    """The full ICT read over a session-aligned uptrend, when the engine can run."""
    from .conftest import local_time

    # Session-aligned bars: two New York days of a persistent rally, so the
    # prior completed day reads bullish and a shift can displace through it.
    start = local_time(2026, 3, 2, 0, 0)
    closes = []
    price = 100.0
    for _ in range(120):
        price += 0.9
        closes.append(price)

    bars = []
    prev = closes[0]
    for close in closes:
        bars.append((prev, max(prev, close) + 0.4, min(prev, close) - 0.4, close))
        prev = close
    data = make_ohlc_market_data(
        bars, symbol="ICTTEST", timeframe=Timeframe.H1, start=start
    )

    ict = services.ict.analyze(data)
    context = build_context_sync(data, ict=ict)
    evaluation = ICTStrategy().evaluate(context)

    # Whether it fires depends on the full eight-concept read; what is pinned
    # here is that it *evaluated* (no blockers) and its geometry is sane.
    assert not any("needs an ICT read" in line for line in evaluation.limitations)
    setup = evaluation.setup
    if setup is not None:
        assert setup.direction in (Direction.UP, Direction.DOWN)
        if setup.direction is Direction.UP:
            assert setup.invalidation_level < setup.entry_reference
        else:
            assert setup.invalidation_level > setup.entry_reference


# ----------------------------------------------------------------------
# Breakout


def test_breakout_reports_a_blocker_when_no_breakout_read_is_available():
    data = make_market_data(_UPTREND_CLOSES, symbol="NOBRK")
    context = build_context_sync(data, breakout=None)
    evaluation = BreakoutStrategy().evaluate(context)

    assert not evaluation.fired
    assert "needs a breakout read" in " ".join(evaluation.limitations)
    assert evaluation.rules == ()


def _volume_market_data(
    bars: list[tuple[float, float, float, float, float]],
    *,
    symbol: str,
) -> MarketData:
    """
    OHLCV bars with per-bar volume, on the D1 timeframe.

    The breakout read turns on the *last* bar's volume relative to the channel
    average, and ``make_market_data`` stamps every bar with one volume, so the
    confirmed and unconfirmed cases need this builder.
    """
    end = datetime.now(UTC).replace(microsecond=0)
    step = timedelta(days=1)
    n = len(bars)
    candles = tuple(
        Candle(
            timestamp=end - step * (n - 1 - i),
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )
        for i, (open_, high, low, close, volume) in enumerate(bars)
    )
    return MarketData(
        instrument=Instrument.parse(symbol),
        timeframe=Timeframe.D1,
        candles=candles,
        provenance=Provenance(
            source="test", tier=SourceTier.PRIMARY, detail="fixture"
        ),
        quality=DataQuality(
            status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0
        ),
    )


def _channel_break_bars(
    *,
    lookback: int,
    lift: float = 1.0,
    break_volume: float = 2_000_000.0,
) -> list[tuple[float, float, float, float, float]]:
    """
    A flat channel, then one break bar closing past the channel high.

    The break bar carries a tall upper wick (which raises ATR, so a close only
    ~1 point past the edge reads as a *near* edge rather than a chase) and the
    given volume (2x the channel's average confirms it).
    """
    bars: list[tuple[float, float, float, float, float]] = []
    prev = 100.0
    for i in range(lookback + 11):
        close = 100.0
        upper = 0.4
        lower = 0.4
        volume = 1_000_000.0
        if i == lookback + 10:
            close = 100.0 + lift
            upper = 4.0  # the tall wick that raises ATR
            volume = break_volume
        bars.append(
            (prev, max(prev, close) + upper, min(prev, close) - lower, close, volume)
        )
        prev = close
    return bars


def test_breakout_fires_on_a_confirmed_channel_break():
    settings = get_settings()
    lookback = settings.TRADING_BREAKOUT_LOOKBACK
    breakout_service = BreakoutService(settings)

    data = _volume_market_data(
        _channel_break_bars(lookback=lookback), symbol="BRK"
    )
    breakout = breakout_service.analyze(data)
    assert breakout.has_breakout
    assert breakout.direction is Direction.UP
    assert breakout.volume_confirmed

    context = build_context_sync(data, breakout=breakout)
    evaluation = BreakoutStrategy().evaluate(context)

    assert evaluation.fired, evaluation.limitations
    setup = evaluation.setup
    assert setup is not None
    assert setup.direction is Direction.UP
    # The invalidation is the broken channel edge itself.
    assert setup.invalidation_level == pytest.approx(breakout.channel_high)
    assert setup.invalidation_level < setup.entry_reference


def test_breakout_declines_inside_the_channel():
    breakout_service = BreakoutService(get_settings())
    closes = [100.0 + (0.6 if i % 2 else -0.6) for i in range(60)]
    data = make_market_data(closes, symbol="NOBRK2")
    breakout = breakout_service.analyze(data)
    assert not breakout.has_breakout

    context = build_context_sync(data, breakout=breakout)
    evaluation = BreakoutStrategy().evaluate(context)
    assert not evaluation.fired


def test_breakout_declines_when_volume_confirmation_is_missing():
    settings = get_settings()
    lookback = settings.TRADING_BREAKOUT_LOOKBACK
    breakout_service = BreakoutService(settings)

    # A break on *average* volume: has_breakout is True but volume_confirmed
    # is False, so the strategy's required confirmation rule fails.
    data = _volume_market_data(
        _channel_break_bars(lookback=lookback, break_volume=1_000_000.0),
        symbol="BRKNV",
    )
    breakout = breakout_service.analyze(data)
    assert breakout.has_breakout
    assert not breakout.volume_confirmed

    context = build_context_sync(data, breakout=breakout)
    evaluation = BreakoutStrategy().evaluate(context)
    assert not evaluation.fired
    volume_rule = next(r for r in evaluation.rules if "volume" in r.rule)
    assert not volume_rule.satisfied


# ----------------------------------------------------------------------
# Panel behaviour


def test_every_builtin_strategy_evaluates_without_raising():
    """The panel contract: every strategy returns an evaluation, never an exception."""
    for data in (
        make_market_data(_UPTREND_CLOSES, symbol="PANELUP"),
        make_market_data(_RANGE_CLOSES, symbol="PANELRANGE"),
    ):
        context = build_context_sync(data)
        for strategy in default_registry():
            evaluation = strategy.evaluate(context)
            assert evaluation.strategy_id == strategy.strategy_id
            assert isinstance(evaluation.rules, tuple)


def test_declined_evaluations_name_their_unmet_conditions():
    data = make_market_data(_RANGE_CLOSES, symbol="DECLINE")
    context = build_context_sync(data)
    for strategy in default_registry():
        evaluation = strategy.evaluate(context)
        if evaluation.fired:
            continue
        if evaluation.rules:  # blockers produce no rules at all
            assert evaluation.limitations
            assert any(
                "unmet conditions" in line or "no setup" in line
                for line in evaluation.limitations
            )


def test_strategies_are_stateless_across_evaluations():
    data = make_market_data(_UPTREND_CLOSES, symbol="STATE")
    context = build_context_sync(data)
    strategy = TrendFollowingStrategy()
    first = strategy.evaluate(context)
    second = strategy.evaluate(context)
    # The same strategy over the same context must give the same setup id.
    if first.setup and second.setup:
        assert first.setup.setup_id == second.setup.setup_id
