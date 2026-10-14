"""
SimulationService: the real pipeline replayed over real-shaped bars.

These tests build the same wiring the bootstrapper does -- analysis, structure,
SMC/ICT, strategies, risk, critic, signals, portfolio sizing, risk limits --
and drive it through :class:`SimulationService`, so what is exercised is the
actual §9 chain and not a stand-in for it.

What is pinned here, in order of importance:

- **the honesty gate.** A MOCK series comes back ``is_reliable is False`` with
  the reason stated. This test is the point of the phase and is not relaxed to
  make a run look good.
- **no look-ahead.** Changing the final bar cannot change a decision taken
  before it. That is asserted against the trades themselves, not the code.
- **the venue's money.** The venue is capitalised from the account's cash, so
  its affordability check means something and a run does not run out of
  bookkeeping money partway through.
- **a thin or synthetic series is a result, not an error.** §28's "not enough
  evidence" is a valid answer, and it is asserted as one.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.brokers import PaperTradingProvider, PriceSource
from aetheros.trading.brokers.base import BrokerProvider
from aetheros.trading.domain.enums import Direction
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData
from aetheros.trading.domain.simulation import SimulationExitReason
from aetheros.trading.providers.base import MarketDataProvider
from aetheros.trading.providers.mock_provider import MockMarketDataProvider
from aetheros.trading.risk.limits_service import RiskLimitsService
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.critic_service import CriticService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.ict_service import ICTService
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.portfolio_service import PortfolioRiskService
from aetheros.trading.services.risk_service import RiskService
from aetheros.trading.services.signal_service import SignalService
from aetheros.trading.services.simulation_service import (
    SimulationService,
    _paper_venue,
)
from aetheros.trading.services.smc_service import SMCService
from aetheros.trading.services.strategy_service import StrategyService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.simulation import (
    FeedPriceSource,
    SimulationFeed,
    VirtualAccount,
)

from .conftest import FakeProvider, make_market_data

#: A shipped strategy id, so this suite exercises the real panel rather than a
#: test-only strategy that might fire where the real ones would not.
STRATEGY = "trend_following"

_SYMBOL = "SIM"
_BARS = 300
_START = datetime(2026, 1, 5, tzinfo=UTC)


def _closes(count: int = _BARS) -> list[float]:
    """A long, mildly noisy uptrend -- enough shape for the panel to read."""
    return [100.0 + i * 0.6 + (0.4 if i % 3 else -0.4) for i in range(count)]


@dataclass(frozen=True)
class _Harness:
    """The wired pipeline, plus the venues it happened to build."""

    service: SimulationService
    market_data: MarketDataService
    venues: list[BrokerProvider]
    balances: list[float]


def _harness(provider: MarketDataProvider, *, record_venues: bool = False) -> _Harness:
    """
    The pipeline the live path uses, wired by hand.

    ``record_venues`` swaps in a factory that builds the *same* paper venue but
    keeps a reference, so a test can see exactly what the simulation
    capitalised and when. Without it the service runs on its own default.
    """
    settings = get_settings()
    market_data = MarketDataService(provider, settings)
    structure = MarketStructureService()
    analysis = AnalysisService(
        market_data,
        TechnicalAnalysisService(),
        structure,
        EvidenceService(),
        settings,
    )
    smc = SMCService(structure)
    ict = ICTService(structure, smc)
    strategy = StrategyService(
        analysis,
        structure,
        smc=smc,
        ict=ict,
        breakout=BreakoutService(settings),
        backtest=BacktestService(settings),
    )
    signals = SignalService(
        strategy,
        RiskService(settings),
        CriticService(settings),
        market_data,
        settings,
    )

    venues: list[BrokerProvider] = []
    balances: list[float] = []
    factory = None
    if record_venues:

        def factory(source: PriceSource, balance: float) -> BrokerProvider:
            balances.append(balance)
            venue = _paper_venue(source, balance)
            venues.append(venue)
            return venue

    service = SimulationService(
        signals,
        PortfolioRiskService(settings),
        RiskLimitsService(settings),
        settings,
        venue_factory=factory,
    )
    return _Harness(
        service=service,
        market_data=market_data,
        venues=venues,
        balances=balances,
    )


@pytest.fixture
def harness() -> _Harness:
    return _harness(FakeProvider(make_market_data(_closes(), symbol=_SYMBOL)))


@pytest.fixture
def recorded() -> _Harness:
    return _harness(
        FakeProvider(make_market_data(_closes(), symbol=_SYMBOL)), record_venues=True
    )


@pytest.fixture
def mock_harness() -> _Harness:
    return _harness(MockMarketDataProvider())


async def _series(harness: _Harness, *, symbol: str = _SYMBOL) -> MarketData:
    """The series as the pipeline itself would fetch it."""
    return await harness.market_data.get_candles(symbol, "1d", limit=_BARS)


def _short_series() -> MarketData:
    """Ten bars: fewer than the strategy layer will read anything from."""
    return make_market_data([100.0 + i for i in range(10)], symbol=_SYMBOL)


# ----------------------------------------------------------------------
# The honesty gate


@pytest.mark.asyncio
async def test_a_mock_series_is_never_reliable(mock_harness):
    """
    The phase's central test. Synthetic data exercises the machinery; it is
    not evidence about an edge, and the report has to say so.
    """
    data = await mock_harness.market_data.get_candles("AAPL", "1d", limit=_BARS)
    report = await mock_harness.service.run(data, STRATEGY)

    assert report.is_reliable is False
    assert report.provenance.is_mock is True
    assert any("MOCK" in line for line in report.limitations)


@pytest.mark.asyncio
async def test_a_mock_run_takes_no_trade_and_does_not_pretend_otherwise(
    mock_harness,
):
    """
    Synthetic data is non-actionable at the gate, so nothing can fire -- and
    the counters say why rather than the trade list being quietly blank.
    """
    data = await mock_harness.market_data.get_candles("AAPL", "1d", limit=_BARS)
    report = await mock_harness.service.run(data, STRATEGY)

    assert report.trade_count == 0
    assert report.signals_fired == 0
    assert report.orders_filled == 0
    assert report.entries_skipped == 0
    assert any("No trade was taken" in line for line in report.limitations)


@pytest.mark.asyncio
async def test_a_series_too_short_to_read_is_a_result_not_an_error(harness):
    """§28: "not enough evidence" is a valid answer, and it is a reported one."""
    report = await harness.service.run(_short_series(), STRATEGY)

    assert report.trade_count == 0
    assert report.is_reliable is False
    assert len(report.limitations) == 1
    assert "produced no result at all" in report.limitations[0]
    # Nothing was evaluated, so there is no equity to report either.
    assert report.warmup == report.bars
    assert report.equity_curve == ()


@pytest.mark.asyncio
async def test_an_explicit_warmup_outside_the_series_is_refused(harness):
    """A caller bug, not a thin series: clamped silently it would hide itself."""
    data = await _series(harness)
    for warmup in (-1, len(data.candles)):
        with pytest.raises(ValueError, match="inside the series"):
            await harness.service.run(data, STRATEGY, warmup=warmup)


@pytest.mark.asyncio
async def test_a_negative_cost_is_refused(harness):
    data = await _series(harness)
    with pytest.raises(ValueError, match="costs cannot be negative"):
        await harness.service.run(data, STRATEGY, commission_bps=-1.0)
    with pytest.raises(ValueError, match="costs cannot be negative"):
        await harness.service.run(data, STRATEGY, slippage_bps=-1.0)


# ----------------------------------------------------------------------
# What was replayed


@pytest.mark.asyncio
async def test_the_report_describes_the_series_it_replayed(harness):
    data = await _series(harness)
    report = await harness.service.run(data, STRATEGY)

    assert report.instrument.key == data.instrument.key
    assert report.strategy_id == STRATEGY
    assert report.timeframe == data.timeframe.value
    assert report.bars == len(data.candles)
    assert report.initial_equity == get_settings().TRADING_SIM_INITIAL_BALANCE
    assert report.warmup > 0
    # One mark per evaluated bar: the warmup bars are the ones not marked.
    assert len(report.equity_curve) == report.bars - report.warmup


@pytest.mark.asyncio
async def test_the_fill_model_is_named_in_every_report(harness):
    """§7: transaction assumptions are stated, never left implicit."""
    report = await harness.service.run(await _series(harness), STRATEGY)
    assumptions = " ".join(report.assumptions)

    assert "no intrabar entry is modelled" in assumptions
    assert "from bar t+1 onward" in assumptions
    assert "recorded as 'ambiguous'" in assumptions
    assert "no trailing stop, no partial exit and no scaling in" in assumptions
    assert "Nothing is opened on the final bar" in assumptions


@pytest.mark.asyncio
async def test_the_default_cost_model_is_named_rather_than_assumed_away(harness):
    """Zero costs are the quiet way a backtest flatters itself, so they are said."""
    report = await harness.service.run(await _series(harness), STRATEGY)
    assumptions = " ".join(report.assumptions)

    assert "zero: no trading cost is modelled" in assumptions
    assert "zero: every fill is at the ideal price" in assumptions


@pytest.mark.asyncio
async def test_a_charged_cost_model_is_reported_with_its_numbers(harness):
    report = await harness.service.run(
        await _series(harness), STRATEGY, commission_bps=12.0, slippage_bps=3.0
    )
    assumptions = " ".join(report.assumptions)

    assert "Commission is 12 bps" in assumptions
    assert "Slippage is 3 bps" in assumptions
    assert "zero:" not in assumptions


# ----------------------------------------------------------------------
# The trades


@pytest.mark.asyncio
async def test_the_report_reconciles_its_own_counters(harness):
    """Whatever the run did, the counters and the trade list must agree."""
    report = await harness.service.run(await _series(harness), STRATEGY)

    assert set(report.exit_breakdown) == {
        "target",
        "stop",
        "ambiguous",
        "forced_end",
    }
    assert sum(report.exit_breakdown.values()) == report.trade_count
    assert report.orders_filled >= report.trade_count
    for trade in report.trades:
        # Every trade happened after the warmup, inside the series, and was
        # resolved after the bar that opened it.
        assert trade.entry_bar >= report.warmup
        assert trade.entry_bar < trade.exit_bar <= report.bars
        assert trade.instrument_key == report.instrument.key
        assert trade.direction in (Direction.UP, Direction.DOWN)
        assert trade.quantity > 0
        assert trade.entry_price > 0
        assert trade.exit_price > 0
        assert trade.reason.value in report.exit_breakdown


@pytest.mark.asyncio
async def test_a_run_either_carries_its_trades_or_names_why_it_took_none(harness):
    """
    Both outcomes are honest answers, so both are asserted: a run that traded
    carries each trade's own arithmetic, and a run that did not names the
    counters that explain the emptiness rather than reporting a bare zero.
    """
    report = await harness.service.run(await _series(harness), STRATEGY)

    if report.trades:
        for trade in report.trades:
            assert trade.notional == pytest.approx(trade.quantity * trade.entry_price)
            assert trade.net_pnl == pytest.approx(
                trade.realized_pnl - trade.commission_paid
            )
        assert report.realized_pnl == pytest.approx(
            sum(trade.realized_pnl for trade in report.trades)
        )
        assert report.commission_paid == pytest.approx(
            sum(trade.commission_paid for trade in report.trades)
        )
    else:
        assert report.is_reliable is False
        assert any(
            "No trade was taken" in line and "suppressed by the one-position" in line
            for line in report.limitations
        )


@pytest.mark.asyncio
async def test_a_position_the_series_ended_on_is_flagged_not_hidden(harness):
    """
    A forced exit is the data ending, not a rule firing, so it is both counted
    on the trade and named among the reasons the run is unreliable.
    """
    report = await harness.service.run(await _series(harness), STRATEGY)
    forced = [trade for trade in report.trades if trade.forced]

    assert report.exit_breakdown["forced_end"] == len(forced)
    assert all(
        trade.reason is SimulationExitReason.FORCED_END for trade in forced
    )
    if forced:
        assert report.is_reliable is False
        assert any(
            "series ended with a position open" in line
            for line in report.limitations
        )


# ----------------------------------------------------------------------
# Determinism and look-ahead


@pytest.mark.asyncio
async def test_two_identical_runs_agree(harness):
    """A simulation is reproducible, or it is not evidence of anything."""
    data = await _series(harness)
    first = await harness.service.run(data, STRATEGY)
    second = await harness.service.run(data, STRATEGY)

    def _stable(report) -> dict:
        payload = report.to_dict()
        payload.pop("created_at")
        return payload

    assert _stable(first) == _stable(second)


@pytest.mark.asyncio
async def test_a_decision_never_sees_the_bar_after_it(harness):
    """
    The look-ahead test, asserted against behaviour rather than code: replace
    the final bar with a wild one, and every trade that had already resolved
    must come out byte-identical, because no decision on those bars could have
    read it.
    """
    data = await _series(harness)
    last = data.candles[-1]
    previous = data.candles[-2].close
    wild = Candle(
        timestamp=last.timestamp,
        open=previous,
        high=previous * 2.0,
        low=previous * 0.5,
        close=previous * 1.9,
        volume=last.volume,
    )
    rewritten = replace(data, candles=data.candles[:-1] + (wild,))

    baseline = await harness.service.run(data, STRATEGY)
    disturbed = await harness.service.run(rewritten, STRATEGY)

    def _settled(report) -> list[dict]:
        return [
            trade.to_dict()
            for trade in report.trades
            if trade.exit_bar < report.bars - 1
        ]

    assert _settled(baseline) == _settled(disturbed)
    # The comparison is only meaningful if bars were actually evaluated.
    assert baseline.equity_curve


# ----------------------------------------------------------------------
# The venue's money


def _account(balance: float = 10_000.0) -> VirtualAccount:
    return VirtualAccount(Instrument.parse(_SYMBOL), initial_balance=balance)


def _price_source() -> FeedPriceSource:
    return FeedPriceSource(SimulationFeed(make_market_data([100.0], symbol=_SYMBOL)))


def test_a_venue_is_capitalised_with_the_cash_the_account_holds(recorded):
    """
    The venue's affordability check has to mean something, so it is handed the
    account's cash at the moment of the order -- not a run-long balance that
    only ever falls, which would refuse to trade while the account was still
    perfectly solvent.
    """
    settings = get_settings()
    account = _account()
    source = _price_source()

    assert recorded.service._engine_for(source, account, settings) is not None
    assert recorded.balances == [10_000.0]

    # A losing round trip lowers what the next venue is capitalised with,
    # because the account is the book that survives one.
    account.open(
        direction=Direction.UP,
        quantity=10.0,
        price=100.0,
        commission=5.0,
        bar_index=0,
        timestamp=_START,
    )
    account.close(
        price=95.0,
        reason=SimulationExitReason.STOP,
        commission=6.0,
        bar_index=4,
        timestamp=_START,
    )

    assert account.cash == pytest.approx(9_939.0)
    assert recorded.service._engine_for(source, account, settings) is not None
    assert recorded.balances == [10_000.0, pytest.approx(9_939.0)]
    assert len(recorded.venues) == 2


def test_an_account_with_no_cash_builds_no_venue(recorded):
    """
    A venue needs a positive balance and there is no honest way to build one
    from no money, so the run records the refusal instead of inventing cash.
    """
    account = _account(balance=1_000.0)
    account.open(
        direction=Direction.UP,
        quantity=10.0,
        price=100.0,
        commission=0.0,
        bar_index=0,
        timestamp=_START,
    )

    assert account.cash == 0.0
    assert recorded.service._engine_for(_price_source(), account, get_settings()) is None
    assert recorded.venues == []


def test_the_default_venue_is_the_real_paper_provider():
    """The injected default fills at a paper venue, never at a live one."""
    venue = _paper_venue(_price_source(), 1_000.0)
    assert isinstance(venue, PaperTradingProvider)
    assert venue.balance == 1_000.0


def test_the_service_takes_no_event_bus():
    """
    A deliberate absence, pinned as one: a replayed fill is history being
    re-read, so giving this service a bus would let a live subscriber react to
    an order that never happened.
    """
    assert "event_bus" not in inspect.signature(SimulationService.__init__).parameters
