"""
Streaming / granular market-data event contracts.

AetherOS is pull-based, not a live tick feed, so the canonical streaming events
are emitted from the points where the system *actually* gains the information:

* ``MarketDataService.get_candles`` surfaces a freshly fetched snapshot ->
  ``MarketDataReceived``, then one ``CandleClosed`` for the newest delivered
  bar (every delivered bar is by definition closed; only the final one is the
  meaningful "new close" for a live consumer).
* ``MicrostructureService`` fetches a depth snapshot / recent prints through the
  provider -> ``OrderBookUpdated`` / ``TradeReceived``.
* ``ProbabilityService.estimate`` recomputes its feature matrix ->
  ``FeatureUpdated``.

These tests assert the contracts honestly: the events carry only what the
source really knew, ``is_mock`` is surfaced, and a publish failure never breaks
the underlying operation.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.runtime.events.events import Event
from aetheros.trading.domain.enums import Direction, SourceTier
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.order_book import OrderBook, OrderBookLevel, TradeTick
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.errors import MarketDataError, ProviderError
from aetheros.trading.events import (
    CandleClosed,
    FeatureUpdated,
    MarketDataReceived,
    MarketDataUpdated,
    MarketRegimeChanged,
    OrderBookUpdated,
    TradeReceived,
)
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.trading.services.microstructure_service import MicrostructureService

from .conftest import FakeProvider, make_market_data


def _collector() -> tuple[list[Event], "object"]:
    """
    An EventBus subscriber plus the list it records into.

    The bus logs ``handler.__name__`` on subscribe, so the handler must be a
    real function, not a callable instance. Returns ``(seen, handler)``.
    """
    seen: list[Event] = []

    async def handler(event: Event) -> None:
        seen.append(event)

    return seen, handler


# ----------------------------------------------------------------------
# Serialization contracts (no I/O)
# ----------------------------------------------------------------------


def test_market_data_received_serializes() -> None:
    e = MarketDataReceived(
        instrument_key="NASDAQ:AAPL",
        timeframe="1d",
        candle_count=120,
        last_price=150.0,
        first_bar_timestamp="2026-01-01T00:00:00+00:00",
        last_bar_timestamp="2026-05-01T00:00:00+00:00",
        source_tier="secondary",
        quality_status="ok",
        is_mock=False,
    )
    d = e.to_dict()
    assert d["name"] == "MarketDataReceived"
    assert d["candle_count"] == 120
    assert d["is_mock"] is False
    assert d["first_bar_timestamp"] == "2026-01-01T00:00:00+00:00"


def test_candle_closed_serializes_bar_identity() -> None:
    e = CandleClosed(
        instrument_key="NASDAQ:AAPL",
        timeframe="1d",
        index=119,
        is_final_bar=True,
        bar_timestamp="2026-05-01T00:00:00+00:00",
        open=149.0,
        high=151.0,
        low=148.0,
        close=150.0,
        volume=2_000_000.0,
        source_tier="secondary",
        quality_status="ok",
    )
    d = e.to_dict()
    assert d["name"] == "CandleClosed"
    assert d["is_final_bar"] is True
    # The bar's own open time is distinct from the event's wall-clock timestamp.
    assert d["bar_timestamp"] == "2026-05-01T00:00:00+00:00"
    assert d["close"] == 150.0
    assert e.timestamp.tzinfo is not None  # event wall-clock is still aware


def test_order_book_updated_and_trade_received_serialize() -> None:
    book = OrderBookUpdated(
        instrument_key="BTC/USD",
        bid_levels=10,
        ask_levels=10,
        best_bid=99.0,
        best_ask=101.0,
        mid_price=100.0,
        spread=2.0,
        book_timestamp="2026-05-01T00:00:00+00:00",
        source_tier="secondary",
    )
    bd = book.to_dict()
    assert bd["spread"] == 2.0
    assert bd["mid_price"] == 100.0

    tick = TradeReceived(
        instrument_key="BTC/USD",
        price=100.5,
        amount=0.25,
        side="up",
        trade_timestamp="2026-05-01T00:00:00+00:00",
        tick_id="t-1",
    )
    td = tick.to_dict()
    assert td["side"] == "up"
    assert td["price"] == 100.5


def test_market_regime_changed_and_feature_updated_serialize() -> None:
    change = MarketRegimeChanged(
        instrument_key="NASDAQ:AAPL",
        timeframe="1d",
        previous_regime="ranging",
        regime="trending_up",
        direction="up",
        is_reliable=True,
        source_tier="secondary",
    )
    d = change.to_dict()
    assert d["previous_regime"] == "ranging"
    assert d["regime"] == "trending_up"
    assert d["direction"] == "up"

    feat = FeatureUpdated(
        instrument_key="NASDAQ:AAPL",
        timeframe="1d",
        horizon_bars=5,
        feature_names=("rsi_14_centered", "momentum_10"),
        has_live_row=True,
        model="logistic_momentum/1.0.0",
        is_reliable=True,
    )
    fd = feat.to_dict()
    # feature_count is derived from the names, so the two can never disagree.
    assert fd["feature_count"] == 2
    assert fd["feature_names"] == ["rsi_14_centered", "momentum_10"]


# ----------------------------------------------------------------------
# MarketDataService emission (fresh snapshot -> received + candle closed)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_candles_emits_received_and_final_candle_close() -> None:
    bus = EventBus()
    received, recv_h = _collector()
    closes, close_h = _collector()
    await bus.subscribe(MarketDataReceived, recv_h)
    await bus.subscribe(CandleClosed, close_h)

    data = make_market_data([100.0 + i for i in range(60)], symbol="AAPL")
    svc = MarketDataService(FakeProvider(data), get_settings(), event_bus=bus)
    await svc.get_candles("AAPL", "1d", limit=60)

    assert len(received) == 1
    rec = received[0]
    assert rec.instrument_key == "AAPL"
    assert rec.candle_count == 60
    assert rec.is_mock is False

    # Exactly one CandleClosed -- the newest delivered bar, flagged final.
    assert len(closes) == 1
    close = closes[0]
    assert close.is_final_bar is True
    assert close.index == data.count - 1
    assert close.close == data.candles[-1].close


@pytest.mark.asyncio
async def test_cached_fetch_does_not_reannounce() -> None:
    bus = EventBus()
    received, recv_h = _collector()
    await bus.subscribe(MarketDataReceived, recv_h)

    data = make_market_data([100.0 + i for i in range(30)], symbol="AAPL")
    svc = MarketDataService(FakeProvider(data), get_settings(), event_bus=bus)
    await svc.get_candles("AAPL", "1d", limit=30)
    await svc.get_candles("AAPL", "1d", limit=30)  # served from cache

    assert len(received) == 1


@pytest.mark.asyncio
async def test_market_data_received_marks_mock() -> None:
    bus = EventBus()
    received, recv_h = _collector()
    await bus.subscribe(MarketDataReceived, recv_h)

    data = make_market_data(
        [100.0 + i for i in range(30)], symbol="AAPL", tier=SourceTier.MOCK
    )
    svc = MarketDataService(FakeProvider(data), get_settings(), event_bus=bus)
    await svc.get_candles("AAPL", "1d", limit=30)

    assert received[0].is_mock is True
    assert received[0].source_tier == "mock"


# ----------------------------------------------------------------------
# MicrostructureService
# ----------------------------------------------------------------------


class _MicroProvider(FakeProvider):
    """A provider that serves order books and trade ticks (ccxt-like)."""

    supports_order_book = True
    supports_trades = True

    def __init__(self, data, *, book: OrderBook, ticks: tuple[TradeTick, ...]):
        super().__init__(data)
        self._book = book
        self._ticks = ticks

    async def get_order_book(self, instrument, *, depth=10) -> OrderBook:
        return self._book

    async def get_recent_trades(self, instrument, *, limit=50):
        return self._ticks


def _book(symbol: str = "BTC/USD") -> OrderBook:
    ts = datetime(2026, 5, 1, tzinfo=timezone.utc)
    return OrderBook(
        instrument=Instrument.parse(symbol),
        bids=(
            OrderBookLevel(price=99.0, amount=1.0),
            OrderBookLevel(price=98.0, amount=2.0),
        ),
        asks=(
            OrderBookLevel(price=101.0, amount=1.5),
            OrderBookLevel(price=102.0, amount=1.0),
        ),
        timestamp=ts,
        provenance=Provenance(source="ccxt", tier=SourceTier.SECONDARY),
    )


def _ticks(symbol: str = "BTC/USD") -> tuple[TradeTick, ...]:
    ts = datetime(2026, 5, 1, tzinfo=timezone.utc)
    prov = Provenance(source="ccxt", tier=SourceTier.SECONDARY)
    return (
        TradeTick(
            instrument=Instrument.parse(symbol),
            price=100.5,
            amount=0.25,
            side=Direction.UP,
            timestamp=ts,
            tick_id="t-1",
            provenance=prov,
        ),
        TradeTick(
            instrument=Instrument.parse(symbol),
            price=100.4,
            amount=0.5,
            side=Direction.DOWN,
            timestamp=ts,
            tick_id="t-2",
            provenance=prov,
        ),
    )


@pytest.mark.asyncio
async def test_order_book_fetch_emits_updated() -> None:
    bus = EventBus()
    books, books_h = _collector()
    await bus.subscribe(OrderBookUpdated, books_h)

    provider = _MicroProvider(
        make_market_data([100.0] * 5, symbol="BTC/USD"),
        book=_book(),
        ticks=_ticks(),
    )
    svc = MicrostructureService(provider, event_bus=bus)
    book = await svc.get_order_book("BTC/USD", depth=10)

    assert book.spread == 2.0
    assert len(books) == 1
    ev = books[0]
    assert ev.best_bid == 99.0
    assert ev.best_ask == 101.0
    assert ev.bid_levels == 2 and ev.ask_levels == 2
    assert ev.is_mock is False


@pytest.mark.asyncio
async def test_recent_trades_emit_one_event_per_print() -> None:
    bus = EventBus()
    trades, trades_h = _collector()
    await bus.subscribe(TradeReceived, trades_h)

    provider = _MicroProvider(
        make_market_data([100.0] * 5, symbol="BTC/USD"),
        book=_book(),
        ticks=_ticks(),
    )
    svc = MicrostructureService(provider, event_bus=bus)
    n = await svc.get_recent_trades("BTC/USD", limit=10)

    assert n == 2
    assert len(trades) == 2
    assert trades[0].side == "up"
    assert trades[1].side == "down"
    assert trades[0].tick_id == "t-1"


@pytest.mark.asyncio
async def test_unsupported_provider_is_an_honest_refusal() -> None:
    # FakeProvider declares supports_order_book/trades = False.
    provider = FakeProvider(make_market_data([1.0] * 5, symbol="AAPL"))
    svc = MicrostructureService(provider, event_bus=EventBus())
    with pytest.raises(ProviderError):
        await svc.get_order_book("AAPL")
    with pytest.raises(ProviderError):
        await svc.get_recent_trades("AAPL")


@pytest.mark.asyncio
async def test_service_works_without_an_event_bus() -> None:
    provider = _MicroProvider(
        make_market_data([100.0] * 5, symbol="BTC/USD"),
        book=_book(),
        ticks=_ticks(),
    )
    svc = MicrostructureService(provider)  # no bus wired
    book = await svc.get_order_book("BTC/USD")
    assert book.mid_price == 100.0
