"""
CcxtMarketDataProvider: candles, quotes, order books and trades through a stub.

Fully deterministic and network-free: the exchange object is injected as a
plain stub with the ccxt call surface (fetch_ohlcv / fetch_ticker /
fetch_order_book / fetch_trades), so the provider's mapping and honesty rules
are pinned without requiring the ccxt package at all.
"""

from __future__ import annotations

from typing import Any

import pytest

from aetheros.trading.domain.enums import Direction, SourceTier, Timeframe
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.errors import InsufficientDataError, ProviderError
from aetheros.trading.providers.ccxt_provider import (
    CcxtMarketDataProvider,
    ccxt_symbol,
)

BTC = Instrument("BTC", asset_class="crypto")
EURUSD = Instrument("EURUSD", asset_class="forex")

_MS = 1_735_689_600_000  # 2025-01-01T00:00:00Z in ms


class StubExchange:
    """A minimal async ccxt exchange double."""

    id = "stub"

    def __init__(
        self,
        *,
        ohlcv: list | None = None,
        ticker: dict | None = None,
        book: dict | None = None,
        trades: list | None = None,
        raise_on: str | None = None,
    ) -> None:
        self._ohlcv = ohlcv or []
        self._ticker = ticker
        self._book = book
        self._trades = trades or []
        self._raise_on = raise_on
        self.calls: list[tuple[str, tuple, dict]] = []

    async def fetch_ohlcv(self, symbol, timeframe=None, since=None, limit=None):
        self.calls.append(("fetch_ohlcv", (symbol, timeframe, since, limit), {}))
        if self._raise_on == "fetch_ohlcv":
            raise RuntimeError("exchange unreachable")
        return self._ohlcv

    async def fetch_ticker(self, symbol):
        self.calls.append(("fetch_ticker", (symbol,), {}))
        if self._raise_on == "fetch_ticker":
            raise RuntimeError("exchange unreachable")
        if self._ticker is None:
            return {}
        return self._ticker

    async def fetch_order_book(self, symbol, limit=None):
        self.calls.append(("fetch_order_book", (symbol, limit), {}))
        if self._raise_on == "fetch_order_book":
            raise RuntimeError("exchange unreachable")
        if self._book is None:
            return {}
        return self._book

    async def fetch_trades(self, symbol, since=None, limit=None):
        self.calls.append(("fetch_trades", (symbol, since, limit), {}))
        if self._raise_on == "fetch_trades":
            raise RuntimeError("exchange unreachable")
        return self._trades


# ==============================================================
# Symbol mapping
# ==============================================================


@pytest.mark.parametrize(
    ("instrument", "expected"),
    [
        (Instrument("BTC", asset_class="crypto"), "BTC/USD"),
        (Instrument("BTCUSDT", asset_class="crypto"), "BTC/USDT"),
        (Instrument("ETH/USDT", asset_class="crypto"), "ETH/USDT"),
        (Instrument("EURUSD", asset_class="forex"), "EUR/USD"),
        (Instrument("EUR", asset_class="forex"), "EUR/USD"),
        (Instrument("AAPL"), "AAPL"),  # non-ccxt asset class: bare symbol
    ],
)
def test_ccxt_symbol_maps_asset_classes(instrument, expected):
    assert ccxt_symbol(instrument) == expected


# ==============================================================
# Capability flags
# ==============================================================


def test_capability_flags_and_asset_classes():
    provider = CcxtMarketDataProvider(StubExchange())
    assert provider.supports_order_book is True
    assert provider.supports_trades is True
    assert provider.supports_asset_class("crypto")
    assert provider.supports_asset_class("FOREX")
    assert provider.supports_asset_class("commodity")
    assert not provider.supports_asset_class("equity")
    assert provider.tier is SourceTier.SECONDARY
    assert provider.is_mock is False


@pytest.mark.asyncio
async def test_transport_error_is_retried_then_raises():
    sleep_calls: list[float] = []

    async def sleeper(seconds: float) -> None:
        sleep_calls.append(seconds)

    class FlakyExchange(StubExchange):
        def __init__(self) -> None:
            super().__init__(ohlcv=[])
            self.attempts = 0

        async def fetch_ohlcv(self, symbol, timeframe=None, since=None, limit=None):
            self.attempts += 1
            raise RuntimeError("exchange unreachable")

    exchange = FlakyExchange()
    provider = CcxtMarketDataProvider(
        exchange, max_retries=1, retry_backoff_seconds=1.0, sleeper=sleeper
    )
    with pytest.raises(ProviderError, match="fetch_ohlcv"):
        await provider.get_candles(BTC, Timeframe.D1, limit=1)
    assert exchange.attempts == 2  # initial + 1 retry
    assert sleep_calls == [1.0]  # exponential backoff: base * 2^0


@pytest.mark.asyncio
async def test_no_retries_by_default():
    class FailingExchange(StubExchange):
        def __init__(self) -> None:
            super().__init__(ohlcv=[])
            self.attempts = 0

        async def fetch_ohlcv(self, symbol, timeframe=None, since=None, limit=None):
            self.attempts += 1
            raise RuntimeError("exchange unreachable")

    exchange = FailingExchange()
    provider = CcxtMarketDataProvider(exchange)  # max_retries=0 default
    with pytest.raises(ProviderError):
        await provider.get_candles(BTC, Timeframe.D1, limit=1)
    assert exchange.attempts == 1  # fail fast, no retry


def test_none_exchange_rejected():
    with pytest.raises(ValueError):
        CcxtMarketDataProvider(None)


# ==============================================================
# Candles
# ==============================================================


@pytest.mark.asyncio
async def test_parses_ohlcv_into_candles():
    ohlcv = [
        [_MS, 100.0, 110.0, 95.0, 105.0, 12.5],
        [_MS + 86_400_000, 105.0, 108.0, 103.0, 107.0, 9.0],
    ]
    provider = CcxtMarketDataProvider(StubExchange(ohlcv=ohlcv))
    data = await provider.get_candles(BTC, Timeframe.D1, limit=10)

    assert data.count == 2
    assert data.provenance.tier is SourceTier.SECONDARY
    assert data.provenance.source == "ccxt"
    assert data.candles[-1].close == pytest.approx(107.0)
    # The exchange must see the mapped symbol and the ccxt timeframe.
    method, args, _ = provider._exchange.calls[0]
    assert method == "fetch_ohlcv"
    assert args[0] == "BTC/USD"
    assert args[1] == "1d"


@pytest.mark.asyncio
async def test_malformed_ohlcv_rows_are_dropped_not_repaired():
    ohlcv = [
        [_MS, 100.0, 110.0, 95.0, 105.0, 12.5],  # good
        "not-a-row",  # wrong shape entirely
        [_MS, float("nan"), 110.0, 95.0, 105.0, 1.0],  # non-finite
        [None, 100.0, 110.0, 95.0, 105.0, 1.0],  # no timestamp
        [_MS, 200.0, 190.0, 195.0, 205.0, 1.0],  # inconsistent OHLC
    ]
    provider = CcxtMarketDataProvider(StubExchange(ohlcv=ohlcv))
    data = await provider.get_candles(BTC, Timeframe.D1, limit=10)
    assert data.count == 1


@pytest.mark.asyncio
async def test_no_usable_candles_raises_insufficient_data():
    provider = CcxtMarketDataProvider(StubExchange(ohlcv=[]))
    with pytest.raises(InsufficientDataError):
        await provider.get_candles(BTC, Timeframe.D1, limit=10)


@pytest.mark.asyncio
async def test_exchange_failure_maps_to_provider_error():
    provider = CcxtMarketDataProvider(StubExchange(raise_on="fetch_ohlcv"))
    with pytest.raises(ProviderError, match="fetch_ohlcv"):
        await provider.get_candles(BTC, Timeframe.D1, limit=10)


@pytest.mark.asyncio
async def test_non_positive_limit_rejected():
    provider = CcxtMarketDataProvider(StubExchange())
    with pytest.raises(ValueError):
        await provider.get_candles(BTC, Timeframe.D1, limit=0)


# ==============================================================
# Quote
# ==============================================================


@pytest.mark.asyncio
async def test_quote_from_ticker_with_bid_ask():
    ticker = {
        "last": 107.0,
        "bid": 106.5,
        "ask": 107.5,
        "timestamp": _MS,
        "baseVolume": 1234.0,
        "percentage": 2.5,
    }
    provider = CcxtMarketDataProvider(StubExchange(ticker=ticker))
    quote = await provider.get_quote(BTC)
    assert quote.price == pytest.approx(107.0)
    assert quote.bid == pytest.approx(106.5)
    assert quote.ask == pytest.approx(107.5)
    assert quote.change_pct == pytest.approx(2.5)
    assert quote.provenance.tier is SourceTier.SECONDARY


@pytest.mark.asyncio
async def test_quote_without_price_or_timestamp_raises():
    provider = CcxtMarketDataProvider(StubExchange(ticker={"bid": 100.0}))
    with pytest.raises(InsufficientDataError):
        await provider.get_quote(BTC)


# ==============================================================
# Order book
# ==============================================================


@pytest.mark.asyncio
async def test_order_book_parsed_with_spread():
    book = {
        "timestamp": _MS,
        "bids": [[99.0, 2.0], [98.0, 3.0], [None, 1.0], ["bad", 1.0]],
        "asks": [[101.0, 1.0], [102.0, 4.0]],
    }
    provider = CcxtMarketDataProvider(StubExchange(book=book))
    result = await provider.get_order_book(BTC, depth=5)

    assert len(result.bids) == 2  # malformed levels dropped
    assert len(result.asks) == 2
    assert result.best_bid == pytest.approx(99.0)
    assert result.best_ask == pytest.approx(101.0)
    assert result.spread == pytest.approx(2.0)
    method, args, _ = provider._exchange.calls[0]
    assert method == "fetch_order_book"
    assert args[0] == "BTC/USD"


@pytest.mark.asyncio
async def test_empty_book_raises_insufficient_data():
    provider = CcxtMarketDataProvider(StubExchange(book={"bids": [], "asks": []}))
    with pytest.raises(InsufficientDataError):
        await provider.get_order_book(BTC)


@pytest.mark.asyncio
async def test_non_positive_depth_rejected():
    provider = CcxtMarketDataProvider(StubExchange())
    with pytest.raises(ValueError):
        await provider.get_order_book(BTC, depth=0)


# ==============================================================
# Trades
# ==============================================================


@pytest.mark.asyncio
async def test_recent_trades_parsed_with_sides():
    trades: list[dict[str, Any]] = [
        {"id": "1", "price": 100.0, "amount": 0.5, "side": "buy", "timestamp": _MS},
        {"id": "2", "price": 101.0, "amount": 0.25, "side": "sell", "timestamp": _MS + 1000},
        {"price": None, "amount": 1.0, "side": "buy", "timestamp": _MS},  # dropped
        "garbage",  # dropped
    ]
    provider = CcxtMarketDataProvider(StubExchange(trades=trades))
    ticks = await provider.get_recent_trades(BTC, limit=10)

    assert len(ticks) == 2
    assert ticks[0].side is Direction.UP
    assert ticks[1].side is Direction.DOWN
    assert ticks[0].tick_id == "1"
    assert ticks[0].provenance is not None
    method, args, _ = provider._exchange.calls[0]
    assert method == "fetch_trades"
    assert args[0] == "BTC/USD"


@pytest.mark.asyncio
async def test_non_positive_trade_limit_rejected():
    provider = CcxtMarketDataProvider(StubExchange())
    with pytest.raises(ValueError):
        await provider.get_recent_trades(BTC, limit=0)


# ==============================================================
# Monthly timeframe mapping
# ==============================================================


@pytest.mark.asyncio
async def test_monthly_timeframe_maps_to_ccxt_1M():
    ohlcv = [[_MS, 100.0, 110.0, 95.0, 105.0, 12.5]]
    provider = CcxtMarketDataProvider(StubExchange(ohlcv=ohlcv))
    data = await provider.get_candles(BTC, Timeframe.MN, limit=1)
    assert data.count == 1
    method, args, _ = provider._exchange.calls[0]
    assert args[1] == "1M"
