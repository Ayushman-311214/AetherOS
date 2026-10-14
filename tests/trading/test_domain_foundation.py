from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from aetheros.runtime.events.event_bus import EventBus
from aetheros.runtime.events.events import Event
from aetheros.trading.domain.enums import (
    Confidence,
    Direction,
    OrderStatus,
    OrderType,
    PositionStatus,
    RiskBand,
    StrategyCategory,
    TradeAction,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle
from aetheros.trading.domain.trade import (
    Order,
    Portfolio,
    Position,
    RiskProfile,
    Strategy,
    TradeSignal,
)
from aetheros.trading.events import (
    MarketOpened,
    OrderFilled,
    OrderSubmitted,
    PositionClosed,
    RiskLimitReached,
    SignalGenerated,
)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument.parse("NASDAQ:AAPL")


def test_candle_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Candle(datetime(2025, 1, 1), 10, 11, 9, 10, 1)


def test_candle_requires_finite_consistent_ohlcv() -> None:
    timestamp = datetime(2025, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="high"):
        Candle(timestamp, 10, 9, 8, 10, 1)
    with pytest.raises(ValueError, match="finite"):
        Candle(timestamp, 10, float("nan"), 8, 9, 1)
    with pytest.raises(ValueError, match="non-negative"):
        Candle(timestamp, 10, 11, 9, 10, -1)


def test_candle_normalizes_aware_timestamp_to_utc() -> None:
    timestamp = datetime(2025, 1, 1, 12, tzinfo=timezone(timedelta(hours=2)))
    candle = Candle(timestamp, 10, 11, 9, 10, 1)
    assert candle.timestamp == datetime(2025, 1, 1, 10, tzinfo=UTC)


def test_instrument_rejects_empty_symbol() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        Instrument("   ")
    with pytest.raises(ValueError, match="must not be empty"):
        Instrument.parse("  ")


def test_quote_rejects_impossible_price_and_naive_timestamp(
    instrument,
) -> None:
    from aetheros.trading.domain.enums import SourceTier
    from aetheros.trading.domain.market_data import Quote
    from aetheros.trading.domain.provenance import Provenance

    provenance = Provenance(source="test", tier=SourceTier.PRIMARY)
    aware = datetime(2025, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="positive"):
        Quote(instrument, 0.0, aware, provenance)
    with pytest.raises(ValueError, match="positive"):
        Quote(instrument, -5.0, aware, provenance)
    with pytest.raises(ValueError, match="timezone-aware"):
        Quote(instrument, 100.0, datetime(2025, 1, 1), provenance)
    with pytest.raises(ValueError, match="non-negative"):
        Quote(instrument, 100.0, aware, provenance, volume=-1.0)


def test_trade_signal_requires_executable_geometry_for_entries(instrument) -> None:
    with pytest.raises(ValueError, match="entry price"):
        TradeSignal(
            instrument,
            TradeAction.BUY,
            Direction.UP,
            Confidence.HIGH,
            RiskBand.LOW,
            "trend continuation",
            (),
        )
    signal = TradeSignal(
        instrument,
        TradeAction.BUY,
        Direction.UP,
        Confidence.MEDIUM,
        RiskBand.LOW,
        "price above support",
        (),
        entry=100,
        stop_loss=95,
        take_profit=110,
    )
    assert signal.to_dict()["instrument"]["symbol"] == "AAPL"
    with pytest.raises(FrozenInstanceError):
        signal.entry = 101


def test_order_validates_type_fill_and_direction(instrument) -> None:
    with pytest.raises(ValueError, match="limit_price"):
        Order(instrument, Direction.UP, 2, OrderType.LIMIT)
    with pytest.raises(ValueError, match="full quantity"):
        Order(
            instrument,
            Direction.UP,
            2,
            OrderType.MARKET,
            status=OrderStatus.FILLED,
            filled_quantity=1,
            average_fill_price=100,
        )
    partial = Order(
        instrument,
        Direction.DOWN,
        2,
        OrderType.MARKET,
        status=OrderStatus.PARTIALLY_FILLED,
        filled_quantity=1,
        average_fill_price=100,
    )
    assert partial.to_dict()["status"] == "partially_filled"


def test_position_requires_consistent_open_closed_state(instrument) -> None:
    with pytest.raises(ValueError, match="exit fields"):
        Position(
            instrument,
            Direction.UP,
            2,
            100,
            status=PositionStatus.OPEN,
            exit_price=105,
        )
    closed = Position(
        instrument,
        Direction.DOWN,
        2,
        100,
        status=PositionStatus.CLOSED,
        exit_price=90,
        opened_at=datetime(2025, 1, 1, tzinfo=UTC),
        closed_at=datetime(2025, 1, 2, tzinfo=UTC),
    )
    assert closed.realized_pnl == pytest.approx(20)
    with pytest.raises(ValueError, match="closed_at"):
        Position(
            instrument,
            Direction.UP,
            1,
            100,
            status=PositionStatus.CLOSED,
            exit_price=101,
        )


def test_strategy_and_risk_profile_reject_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="description"):
        Strategy("momentum", "Momentum", StrategyCategory.TREND_FOLLOWING, " ")
    with pytest.raises(ValueError, match="unique"):
        Strategy(
            "momentum",
            "Momentum",
            StrategyCategory.TREND_FOLLOWING,
            "trend setup",
            parameters=(("period", 20), ("period", 50)),
        )
    with pytest.raises(ValueError, match="max_daily_loss_pct"):
        RiskProfile(1.0, 0.0, 50.0, 1.5)
    assert RiskProfile(1.0, 3.0, 50.0, 1.5).to_dict()["min_risk_reward"] == 1.5


def test_portfolio_rejects_invalid_account_state(instrument) -> None:
    with pytest.raises(ValueError, match="margin_used"):
        Portfolio("acct-1", "USD", 500, 1000, margin_used=1001)
    position = Position(instrument, Direction.UP, 1, 100)
    portfolio = Portfolio("acct-1", "USD", 900, 1000, positions=(position,))
    assert portfolio.to_dict()["positions"][0]["position_id"] == position.position_id


@pytest.mark.asyncio
async def test_trading_events_use_shared_event_bus_and_serialize() -> None:
    events: list[Event] = []
    bus = EventBus()

    async def receive(event: Event) -> None:
        events.append(event)

    event_types = (
        MarketOpened,
        SignalGenerated,
        OrderSubmitted,
        OrderFilled,
        PositionClosed,
        RiskLimitReached,
    )
    for event_type in event_types:
        await bus.subscribe(event_type, receive)

    instances = [
        MarketOpened(market="NASDAQ"),
        SignalGenerated(signal_id="sig-1", instrument_key="NASDAQ:AAPL"),
        OrderSubmitted(order_id="ord-1", instrument_key="NASDAQ:AAPL"),
        OrderFilled(order_id="ord-1", instrument_key="NASDAQ:AAPL", filled_quantity=1, fill_price=100),
        PositionClosed(position_id="pos-1", instrument_key="NASDAQ:AAPL", exit_price=101),
        RiskLimitReached(limit_name="daily_loss", observed_value=3.1, limit_value=3.0),
    ]

    for event in instances:
        assert isinstance(event, Event)
        assert event.to_dict()["name"] == type(event).__name__
        await bus.publish(event)

    assert events == instances
    assert len({event.event_id for event in events}) == len(event_types)
    assert all(event.timestamp.tzinfo is not None for event in events)
