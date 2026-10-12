"""
The simulation package's pure pieces (spec Phase 14).

Everything here is deterministic and I/O-free: a replay cursor, an exit rule, a
cost model, an account book, and the report they add up to. The service that
drives them is exercised separately in ``test_simulation_service.py``.

Three properties are the point of the phase, and each is pinned here rather
than left to the service test:

- **no look-ahead.** :meth:`SimulationFeed.visible` is the only view a decision
  gets, and it ends at the cursor.
- **ambiguity resolves against the strategy.** A bar whose range contains both
  the stop and the target closes at the *stop*, labelled ``AMBIGUOUS``.
- **the account is the only ledger.** What a closed round trip returns to cash
  is the initial balance plus the trade's own net P&L -- exactly, not
  approximately. The paper venue's balance is not a second opinion, because it
  has no book for a round trip at all (see ``simulation/account.py``).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from aetheros.trading.domain.enums import (
    DataQualityStatus,
    Direction,
    PositionStatus,
    SourceTier,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.domain.simulation import (
    SimulatedTrade,
    SimulationExitReason,
    SimulationReport,
)
from aetheros.trading.domain.trade import Position
from aetheros.trading.errors import BrokerError
from aetheros.trading.simulation import (
    DEFAULT_CURRENCY,
    DEFAULT_PORTFOLIO_ID,
    FeedPriceSource,
    SimulationFeed,
    VirtualAccount,
    commission_for,
    exit_for,
    slipped_price,
)

from .conftest import make_market_data

_INSTRUMENT = Instrument.parse("SIM")
_START = datetime(2026, 1, 5, tzinfo=UTC)


def _candle(
    index: int = 0,
    *,
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.0,
) -> Candle:
    """A bar with explicit OHLC, so the exit cases are known answers."""
    return Candle(
        timestamp=_START + timedelta(days=index),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1_000.0,
    )


def _position(
    direction: Direction = Direction.UP,
    *,
    entry: float = 100.0,
    stop: float | None = 98.0,
    target: float | None = 104.0,
    quantity: float = 10.0,
) -> Position:
    return Position(
        instrument=_INSTRUMENT,
        direction=direction,
        quantity=quantity,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
    )


def _short_position(*, entry: float = 100.0, stop: float = 102.0, target: float = 96.0):
    return _position(Direction.DOWN, entry=entry, stop=stop, target=target)


def _trade(**overrides) -> SimulatedTrade:
    base = {
        "position_id": f"sim-{_INSTRUMENT.key}-0-1",
        "instrument_key": _INSTRUMENT.key,
        "direction": Direction.UP,
        "quantity": 10.0,
        "entry_price": 100.0,
        "entry_bar": 0,
        "exit_price": 104.0,
        "exit_bar": 3,
        "reason": SimulationExitReason.TARGET,
        "realized_pnl": 40.0,
        "commission_paid": 2.0,
    }
    base.update(overrides)
    return SimulatedTrade(**base)


def _report(**overrides) -> SimulationReport:
    base = {
        "instrument": _INSTRUMENT,
        "timeframe": "1d",
        "strategy_id": "trend_following",
        "bars": 10,
        "warmup": 2,
        "initial_equity": 100_000.0,
        "final_equity": 100_038.0,
        "realized_pnl": 40.0,
        "unrealised_pnl": 0.0,
        "commission_paid": 2.0,
        "max_drawdown": 0.0,
        "sharpe": None,
        "statistics": None,
        "trades": (_trade(),),
        "equity_curve": (100_000.0, 100_038.0),
        "signals_fired": 1,
        "orders_filled": 1,
        "orders_rejected": 0,
        "admissions_refused": 0,
        "entries_skipped": 0,
        "exit_counts": (("target", 1),),
        "assumptions": ("A signal is decided on the close of bar t.",),
        "provenance": Provenance(
            source="test", tier=SourceTier.DERIVED, detail="replayed series"
        ),
        "quality": DataQuality(
            status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0
        ),
        "is_reliable": True,
    }
    base.update(overrides)
    return SimulationReport(**base)


# ----------------------------------------------------------------------
# The replay cursor


def test_a_feed_starts_on_the_first_bar():
    feed = SimulationFeed(make_market_data([100.0, 101.0, 102.0], symbol="SIM"))
    assert len(feed) == 3
    assert feed.cursor == 0
    assert feed.exhausted is False
    assert feed.bar().close == 100.0
    assert feed.price() == 100.0


def test_the_first_decision_cannot_see_the_second_bar():
    """
    The look-ahead guarantee, as a known answer: the second bar's close is
    nothing like the first's, and it is simply not in the window.
    """
    data = make_market_data([100.0, 999.0], symbol="SIM")
    feed = SimulationFeed(data)
    assert [c.close for c in feed.visible().candles] == [100.0]


def test_visible_ends_at_the_cursor_and_grows_by_exactly_one_bar():
    data = make_market_data([100.0, 101.0, 102.0, 103.0], symbol="SIM")
    feed = SimulationFeed(data)
    for index in range(len(data.candles)):
        feed.seek(index)
        visible = feed.visible()
        assert visible.candles == data.candles[: index + 1]
        assert len(visible.candles) == index + 1
        assert visible.candles[-1] is data.candles[index]


def test_advancing_walks_the_series_and_stops_at_the_end():
    feed = SimulationFeed(make_market_data([100.0, 101.0, 102.0], symbol="SIM"))
    assert feed.advance() is True
    assert feed.cursor == 1
    assert feed.advance() is True
    assert feed.cursor == 2
    assert feed.exhausted is True
    # An exhausted feed is an honest end of data: it does not wrap or hold.
    assert feed.advance() is False
    assert feed.cursor == 2
    assert feed.bar().close == 102.0


def test_seeking_outside_the_series_is_refused():
    feed = SimulationFeed(make_market_data([100.0, 101.0], symbol="SIM"))
    for index in (-1, 2):
        with pytest.raises(ValueError, match="Cannot seek to bar"):
            feed.seek(index)


def test_a_series_with_no_bars_is_refused():
    with pytest.raises(ValueError, match="at least one candle"):
        SimulationFeed(replace(make_market_data([100.0], symbol="SIM"), candles=()))


def test_an_unusable_replayed_close_is_a_broker_error():
    """A bar that cannot be priced is an outage, not a fill at zero."""
    data = make_market_data([100.0, 101.0], symbol="SIM")
    unpriced = _candle(1, open_=0.0, high=1.0, low=0.0, close=0.0)
    feed = SimulationFeed(replace(data, candles=(data.candles[0], unpriced)))
    feed.seek(1)
    with pytest.raises(BrokerError, match="not usable"):
        feed.price()


@pytest.mark.asyncio
async def test_the_feed_source_prices_the_bar_under_the_cursor():
    feed = SimulationFeed(make_market_data([100.0, 101.0, 102.0], symbol="SIM"))
    source = FeedPriceSource(feed)
    assert source.feed is feed
    assert await source.price(_INSTRUMENT.key) == 100.0
    feed.advance()
    assert await source.price(_INSTRUMENT.key) == 101.0


@pytest.mark.asyncio
async def test_the_feed_source_refuses_another_instrument():
    """A venue wired to the wrong feed must fail loudly, not fill silently."""
    feed = SimulationFeed(make_market_data([100.0, 101.0], symbol="SIM"))
    with pytest.raises(BrokerError, match="replays"):
        await FeedPriceSource(feed).price("OTHER")


# ----------------------------------------------------------------------
# The exit rule


def test_a_long_takes_profit_when_the_bar_reaches_its_target():
    decision = exit_for(_position(), _candle(high=105.0, low=99.0, close=104.5))
    assert decision == (104.0, SimulationExitReason.TARGET)


def test_a_long_is_stopped_when_the_bar_reaches_its_stop():
    decision = exit_for(_position(), _candle(high=100.5, low=97.5, close=98.0))
    assert decision == (98.0, SimulationExitReason.STOP)


def test_touching_a_level_exactly_is_touching_it():
    assert exit_for(_position(), _candle(low=98.0)) == (
        98.0,
        SimulationExitReason.STOP,
    )
    assert exit_for(_position(), _candle(high=104.0)) == (
        104.0,
        SimulationExitReason.TARGET,
    )


def test_a_bar_containing_both_levels_closes_at_the_stop():
    """
    The pessimistic rule, as a known answer: the true order of events inside a
    bar is unknowable from bar data, so the run never gets to assume it was
    the good one.
    """
    decision = exit_for(_position(), _candle(high=105.0, low=97.0))
    assert decision == (98.0, SimulationExitReason.AMBIGUOUS)


def test_a_bar_touching_neither_level_leaves_the_position_open():
    assert exit_for(_position(), _candle(high=101.0, low=99.0)) is None


def test_a_short_is_the_mirror_of_a_long():
    assert exit_for(_short_position(), _candle(high=102.5)) == (
        102.0,
        SimulationExitReason.STOP,
    )
    assert exit_for(_short_position(), _candle(high=101.0, low=95.5, close=96.0)) == (
        96.0,
        SimulationExitReason.TARGET,
    )
    assert exit_for(_short_position(), _candle(high=103.0, low=95.0)) == (
        102.0,
        SimulationExitReason.AMBIGUOUS,
    )
    assert exit_for(_short_position(), _candle(high=101.0, low=99.0)) is None


def test_a_position_with_no_levels_has_no_exit_rule():
    """No stop and no target is "no rule applies", not an invented price."""
    bare = _position(stop=None, target=None)
    assert exit_for(bare, _candle(high=140.0, low=60.0)) is None


def test_a_position_with_only_a_stop_can_still_be_stopped():
    only_stop = _position(target=None)
    assert exit_for(only_stop, _candle(high=140.0, low=97.0)) == (
        98.0,
        SimulationExitReason.STOP,
    )
    assert exit_for(only_stop, _candle(high=140.0, low=99.0)) is None


# ----------------------------------------------------------------------
# Costs


def test_slippage_always_moves_against_the_order():
    """A buyer pays more and a seller receives less -- never the reverse."""
    assert slipped_price(100.0, buying=True, slippage_bps=10.0) == pytest.approx(
        100.10
    )
    assert slipped_price(100.0, buying=False, slippage_bps=10.0) == pytest.approx(
        99.90
    )


def test_zero_slippage_leaves_the_ideal_price_alone():
    assert slipped_price(123.45, buying=True, slippage_bps=0.0) == 123.45
    assert slipped_price(123.45, buying=False, slippage_bps=0.0) == 123.45


@pytest.mark.parametrize("price", [0.0, -1.0, float("inf"), float("nan")])
def test_an_unusable_fill_price_is_refused(price):
    with pytest.raises(ValueError, match="finite and positive"):
        slipped_price(price, buying=True, slippage_bps=0.0)


@pytest.mark.parametrize("bps", [-1.0, float("inf"), float("nan")])
def test_unusable_slippage_is_refused(bps):
    with pytest.raises(ValueError, match="Slippage cannot be negative"):
        slipped_price(100.0, buying=True, slippage_bps=bps)


def test_commission_is_basis_points_of_notional():
    assert commission_for(10_000.0, commission_bps=10.0) == pytest.approx(10.0)
    assert commission_for(10_000.0, commission_bps=1.0) == pytest.approx(1.0)


def test_a_free_commission_is_zero_and_named_as_such():
    assert commission_for(10_000.0, commission_bps=0.0) == 0.0


def test_commission_charges_the_size_of_the_trade_not_its_side():
    """A short's notional is signed; its cost is not."""
    assert commission_for(-25_000.0, commission_bps=4.0) == pytest.approx(10.0)


@pytest.mark.parametrize("bps", [-1.0, float("nan")])
def test_a_negative_commission_rate_is_refused(bps):
    with pytest.raises(ValueError, match="Commission cannot be negative"):
        commission_for(1_000.0, commission_bps=bps)


def test_an_unusable_notional_is_refused():
    with pytest.raises(ValueError, match="finite notional"):
        commission_for(float("inf"), commission_bps=1.0)


# ----------------------------------------------------------------------
# The virtual account


def test_a_new_account_holds_its_balance_and_nothing_else():
    account = VirtualAccount(_INSTRUMENT, initial_balance=50_000.0)
    assert account.cash == 50_000.0
    assert account.initial_balance == 50_000.0
    assert account.is_open is False
    assert account.position is None
    assert account.closed_trades == ()
    assert account.realized_pnl == 0.0
    assert account.commission_paid == 0.0
    assert account.equity(100.0) == 50_000.0
    assert account.unrealised_pnl(100.0) == 0.0
    assert account.open_exposure(100.0) == 0.0


@pytest.mark.parametrize("balance", [0.0, -1.0, float("inf")])
def test_a_non_positive_starting_balance_is_refused(balance):
    with pytest.raises(ValueError, match="positive starting balance"):
        VirtualAccount(_INSTRUMENT, initial_balance=balance)


def test_a_long_pays_for_itself_and_for_the_commission():
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    position = account.open(
        direction=Direction.UP,
        quantity=10.0,
        price=100.0,
        commission=5.0,
        bar_index=3,
        timestamp=_START,
        stop_loss=98.0,
        take_profit=104.0,
    )
    assert account.cash == pytest.approx(10_000.0 - 1_000.0 - 5.0)
    assert account.is_open is True
    assert position.status is PositionStatus.OPEN
    assert account.position is position
    assert account.commission_paid == 5.0


def test_a_short_is_paid_for_itself_and_pays_the_commission():
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    account.open(
        direction=Direction.DOWN,
        quantity=10.0,
        price=100.0,
        commission=5.0,
        bar_index=0,
        timestamp=_START,
    )
    assert account.cash == pytest.approx(10_000.0 + 1_000.0 - 5.0)
    # The proceeds are in cash, but the obligation is not: at the entry price
    # the account is down exactly its commission.
    assert account.equity(100.0) == pytest.approx(9_995.0)


def test_a_second_position_is_refused():
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    account.open(
        direction=Direction.UP,
        quantity=1.0,
        price=100.0,
        commission=0.0,
        bar_index=0,
        timestamp=_START,
    )
    with pytest.raises(ValueError, match="already holds a position"):
        account.open(
            direction=Direction.UP,
            quantity=1.0,
            price=100.0,
            commission=0.0,
            bar_index=1,
            timestamp=_START,
        )


def test_a_position_id_names_the_bar_and_the_sequence():
    """Deterministic ids: two runs of the same replay name the same trades."""
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    position = account.open(
        direction=Direction.UP,
        quantity=1.0,
        price=100.0,
        commission=0.0,
        bar_index=7,
        timestamp=_START,
    )
    assert position.position_id == f"sim-{_INSTRUMENT.key}-7-1"


def test_marking_a_long_adds_its_market_value_to_cash():
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    account.open(
        direction=Direction.UP,
        quantity=10.0,
        price=100.0,
        commission=0.0,
        bar_index=0,
        timestamp=_START,
    )
    assert account.unrealised_pnl(110.0) == pytest.approx(100.0)
    assert account.open_exposure(110.0) == pytest.approx(1_100.0)
    # 9,000 cash + 10 shares worth 110 -- the whole market value, not the gain.
    assert account.equity(110.0) == pytest.approx(10_100.0)


def test_marking_a_short_subtracts_its_market_value():
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    account.open(
        direction=Direction.DOWN,
        quantity=10.0,
        price=100.0,
        commission=0.0,
        bar_index=0,
        timestamp=_START,
    )
    assert account.unrealised_pnl(90.0) == pytest.approx(100.0)
    assert account.equity(90.0) == pytest.approx(11_000.0 - 900.0)


def _round_trip(
    direction: Direction = Direction.UP,
    *,
    entry: float = 100.0,
    exit_price: float = 110.0,
    entry_commission: float = 5.0,
    exit_commission: float = 6.0,
) -> tuple[VirtualAccount, SimulatedTrade]:
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    account.open(
        direction=direction,
        quantity=10.0,
        price=entry,
        commission=entry_commission,
        bar_index=0,
        timestamp=_START,
    )
    trade = account.close(
        price=exit_price,
        reason=SimulationExitReason.TARGET,
        commission=exit_commission,
        bar_index=4,
        timestamp=_START + timedelta(days=4),
    )
    return account, trade


def test_a_trade_carries_the_position_models_own_gross_pnl():
    _account, trade = _round_trip()
    # (110 - 100) * 10, the same formula Position.realized_pnl applies.
    assert trade.realized_pnl == pytest.approx(100.0)
    assert trade.notional == pytest.approx(1_000.0)
    # Both legs of the round trip, kept apart from the result.
    assert trade.commission_paid == pytest.approx(11.0)
    assert trade.net_pnl == pytest.approx(89.0)
    assert trade.return_pct == pytest.approx(0.089)


def test_a_short_round_trip_gains_when_the_price_falls():
    _account, trade = _round_trip(Direction.DOWN, exit_price=90.0)
    assert trade.realized_pnl == pytest.approx(100.0)
    assert trade.net_pnl == pytest.approx(89.0)


def test_a_round_trip_returns_cash_to_the_balance_plus_its_net_pnl():
    """
    The account is the only ledger. Whatever the venue's own balance did, this
    is what the money actually did -- and it reconciles to the trade, exactly.
    """
    account, trade = _round_trip()
    assert account.cash == pytest.approx(10_000.0 + trade.net_pnl)
    assert account.position is None
    assert account.is_open is False
    assert account.closed_trades == (trade,)
    assert account.realized_pnl == pytest.approx(trade.realized_pnl)
    assert account.commission_paid == pytest.approx(11.0)
    assert account.equity(110.0) == pytest.approx(account.cash)


def test_a_losing_round_trip_returns_cash_below_the_balance():
    account, trade = _round_trip(exit_price=95.0)
    assert trade.realized_pnl == pytest.approx(-50.0)
    assert account.cash == pytest.approx(10_000.0 + trade.net_pnl)
    assert account.cash < 10_000.0


def test_a_position_cannot_close_on_the_bar_that_opened_it():
    """The t+1 rule, enforced where it cannot be forgotten: the account."""
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    account.open(
        direction=Direction.UP,
        quantity=10.0,
        price=100.0,
        commission=0.0,
        bar_index=3,
        timestamp=_START,
    )
    for bar_index in (3, 2):
        with pytest.raises(ValueError, match="on or before the bar"):
            account.close(
                price=101.0,
                reason=SimulationExitReason.STOP,
                commission=0.0,
                bar_index=bar_index,
                timestamp=_START,
            )
    assert account.is_open is True


def test_closing_a_flat_account_is_refused():
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    with pytest.raises(ValueError, match="no position to close"):
        account.close(
            price=101.0,
            reason=SimulationExitReason.TARGET,
            commission=0.0,
            bar_index=1,
            timestamp=_START,
        )


def test_realised_pnl_is_measured_in_simulated_days():
    """
    A replay of last year's bars must measure last year's days, not the
    afternoon the simulation was run.
    """
    account, trade = _round_trip()
    assert account.realized_on(date(2026, 1, 9)) == pytest.approx(trade.net_pnl)
    assert account.realized_on(date(2026, 1, 8)) == 0.0


def test_the_snapshot_reports_what_the_risk_gate_asks_for():
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    account.open(
        direction=Direction.UP,
        quantity=10.0,
        price=100.0,
        commission=0.0,
        bar_index=0,
        timestamp=_START,
    )
    snapshot = account.snapshot(110.0, captured_at=_START, realized_today=25.0)
    assert snapshot.equity == pytest.approx(10_100.0)
    assert snapshot.realised_pnl_today == 25.0
    assert snapshot.open_exposure_notional == pytest.approx(1_100.0)
    assert snapshot.captured_at == _START


def test_an_unmeasured_realised_pnl_stays_the_documented_unknown():
    """Not zero: the risk gate fails closed on an unknown, and must see one."""
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    snapshot = account.snapshot(100.0, captured_at=_START)
    assert snapshot.realised_pnl_today is None


def test_the_portfolio_view_carries_the_book_as_it_stands():
    account = VirtualAccount(_INSTRUMENT, initial_balance=10_000.0)
    account.open(
        direction=Direction.UP,
        quantity=10.0,
        price=100.0,
        commission=0.0,
        bar_index=0,
        timestamp=_START,
    )
    portfolio = account.portfolio(110.0, timestamp=_START)
    assert portfolio.portfolio_id == DEFAULT_PORTFOLIO_ID
    assert portfolio.currency == DEFAULT_CURRENCY
    assert portfolio.cash_balance == pytest.approx(account.cash)
    assert portfolio.equity == pytest.approx(account.equity(110.0))
    assert portfolio.positions == (account.position,)


# ----------------------------------------------------------------------
# The trade and the report


def test_a_trade_keeps_its_costs_apart_from_its_result():
    trade = _trade()
    assert trade.net_pnl == pytest.approx(38.0)
    assert trade.notional == pytest.approx(1_000.0)
    assert trade.return_pct == pytest.approx(0.038)
    assert trade.forced is False


def test_a_forced_exit_says_so():
    trade = _trade(reason=SimulationExitReason.FORCED_END)
    assert trade.forced is True


def test_a_trade_cannot_resolve_on_the_bar_that_opened_it():
    with pytest.raises(ValueError, match="exit after the bar that opened it"):
        _trade(exit_bar=0)


def test_a_trade_round_trips_through_its_dict():
    payload = _trade().to_dict()
    assert payload["direction"] == "up"
    assert payload["reason"] == "target"
    assert payload["net_pnl"] == pytest.approx(38.0)
    assert payload["forced"] is False


def test_the_report_exposes_its_headline_numbers():
    report = _report()
    assert report.trade_count == 1
    assert report.total_return == pytest.approx(0.00038)
    assert report.net_returns == pytest.approx((0.038,))


def test_the_exit_breakdown_names_every_reason_including_the_zeroes():
    """A reason with no exits is a fact about the run, not an omission."""
    assert _report().exit_breakdown == {
        "target": 1,
        "stop": 0,
        "ambiguous": 0,
        "forced_end": 0,
    }


def test_a_reliable_report_cannot_carry_a_limitation():
    """
    The phase's central invariant: a caveat means the run is not trustworthy,
    so reporting both would let a flawed run be presented as a clean one.
    """
    with pytest.raises(ValueError, match="cannot carry limitations"):
        _report(limitations=("Only 1 closed trade: a sample this thin.",))


def test_an_unreliable_report_states_why():
    report = _report(is_reliable=False, limitations=("The series is MOCK.",))
    assert report.limitations == ("The series is MOCK.",)


def test_a_report_serialises_everything_a_reader_needs():
    payload = _report().to_dict()
    assert payload["instrument"]["key"] == _INSTRUMENT.key
    assert payload["strategy_id"] == "trend_following"
    assert payload["initial_equity"] == 100_000.0
    assert payload["realized_pnl"] == 40.0
    assert payload["commission_paid"] == 2.0
    assert payload["trade_count"] == 1
    assert payload["trades"][0]["net_pnl"] == pytest.approx(38.0)
    assert payload["equity_curve"] == [100_000.0, 100_038.0]
    assert payload["exits"]["target"] == 1
    assert payload["is_reliable"] is True
    assert payload["limitations"] == []
    assert payload["created_at"]


def test_a_trade_that_exits_past_the_last_bar_is_refused():
    with pytest.raises(ValueError, match="cannot exit past its last bar"):
        _report(bars=2, trades=(_trade(exit_bar=3),))


def test_a_trade_from_another_instrument_is_refused():
    with pytest.raises(ValueError, match="must describe its instrument"):
        _report(trades=(_trade(instrument_key="OTHER"),))


def test_a_negative_commission_in_a_report_is_refused():
    with pytest.raises(ValueError, match="commission cannot be negative"):
        _report(commission_paid=-1.0)


def test_a_warmup_outside_the_series_is_refused():
    with pytest.raises(ValueError, match="warmup must lie within its bars"):
        _report(warmup=11)


def test_a_negative_counter_is_refused():
    with pytest.raises(ValueError, match="orders_rejected cannot be negative"):
        _report(orders_rejected=-1)
