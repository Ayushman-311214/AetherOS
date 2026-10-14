"""
YahooMarketDataProvider: the first real market-data adapter.

These tests are fully deterministic and never touch the network: they drive the
provider through an ``httpx.MockTransport`` that returns canned Yahoo chart
payloads (or failures). They pin the two things that matter for a real provider
under the spec's honesty rules (CLAUDE.md sections 9, 20, 53, 61): it parses a
real payload into correctly-shaped, non-mock ``SourceTier.SECONDARY`` candles,
and on any failure -- HTTP error, error payload, or no usable bars -- it raises
a typed error rather than fabricating data.
"""

from __future__ import annotations

import time

import httpx
import pytest

from aetheros.trading.domain.enums import SourceTier, Timeframe
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.errors import InsufficientDataError, ProviderError
from aetheros.trading.providers.yahoo_provider import (
    YahooMarketDataProvider,
    yahoo_symbol,
)


def _chart_payload(
    *,
    opens,
    highs,
    lows,
    closes,
    volumes,
    start: int | None = None,
    step: int = 86400,
    error=None,
    result_empty: bool = False,
):
    """Build a Yahoo /v8/finance/chart-shaped JSON payload."""
    if error is not None:
        return {"chart": {"result": None, "error": error}}
    if result_empty:
        return {"chart": {"result": [], "error": None}}
    n = len(closes)
    base = start if start is not None else int(time.time()) - step * n
    timestamps = [base + step * i for i in range(n)]
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "exchangeName": "NMS",
                        "currency": "USD",
                        "symbol": "TEST",
                    },
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": opens,
                                "high": highs,
                                "low": lows,
                                "close": closes,
                                "volume": volumes,
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


def _provider(handler, **kwargs) -> YahooMarketDataProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    # Instant awaitable sleeper: retry backoff must never slow the suite.
    async def sleeper(seconds: float) -> None:
        return None

    kwargs.setdefault("sleeper", sleeper)
    return YahooMarketDataProvider(client=client, **kwargs)


def _ok_handler(payload, *, capture: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(request)
        return httpx.Response(200, json=payload)

    return handler


@pytest.mark.asyncio
async def test_parses_real_payload_into_secondary_candles():
    payload = _chart_payload(
        opens=[10.0, 11.0, 12.0],
        highs=[10.5, 11.5, 12.5],
        lows=[9.5, 10.5, 11.5],
        closes=[10.2, 11.2, 12.2],
        volumes=[1000, 1100, 1200],
    )
    provider = _provider(_ok_handler(payload))
    data = await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=300)

    assert data.count == 3
    assert data.provenance.tier is SourceTier.SECONDARY
    assert data.provenance.source == "yahoo"
    assert provider.is_mock is False
    assert data.candles[-1].close == pytest.approx(12.2)
    # Ascending timestamps, as every downstream layer assumes.
    ts = [c.timestamp for c in data.candles]
    assert ts == sorted(ts)


@pytest.mark.asyncio
async def test_drops_null_trailing_bar():
    # Yahoo emits a trailing all-null bar for the in-progress period.
    payload = _chart_payload(
        opens=[10.0, 11.0, None],
        highs=[10.5, 11.5, None],
        lows=[9.5, 10.5, None],
        closes=[10.2, 11.2, None],
        volumes=[1000, 1100, None],
    )
    provider = _provider(_ok_handler(payload))
    data = await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=300)
    assert data.count == 2  # the null bar is dropped, not filled


@pytest.mark.asyncio
async def test_trims_to_requested_limit():
    payload = _chart_payload(
        opens=[1.0, 2.0, 3.0, 4.0, 5.0],
        highs=[1.0, 2.0, 3.0, 4.0, 5.0],
        lows=[1.0, 2.0, 3.0, 4.0, 5.0],
        closes=[1.0, 2.0, 3.0, 4.0, 5.0],
        volumes=[1, 2, 3, 4, 5],
    )
    provider = _provider(_ok_handler(payload))
    data = await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=2)
    assert data.count == 2
    # Keeps the MOST RECENT bars.
    assert [c.close for c in data.candles] == [4.0, 5.0]


@pytest.mark.asyncio
async def test_get_quote_returns_change_pct():
    payload = _chart_payload(
        opens=[10.0, 11.0],
        highs=[10.5, 11.5],
        lows=[9.5, 10.5],
        closes=[10.0, 11.0],
        volumes=[1000, 1100],
    )
    provider = _provider(_ok_handler(payload))
    quote = await provider.get_quote(Instrument("AAPL"))
    assert quote.price == pytest.approx(11.0)
    assert quote.change_pct == pytest.approx(10.0)  # 11/10 - 1
    assert quote.provenance.tier is SourceTier.SECONDARY


@pytest.mark.asyncio
async def test_maps_exchange_to_yahoo_suffix():
    captured: list[httpx.Request] = []
    payload = _chart_payload(
        opens=[1.0], highs=[1.0], lows=[1.0], closes=[1.0], volumes=[1]
    )
    provider = _provider(_ok_handler(payload, capture=captured))
    await provider.get_candles(
        Instrument("RELIANCE", exchange="NSE"), Timeframe.D1, limit=1
    )
    assert captured, "no request captured"
    assert "RELIANCE.NS" in str(captured[0].url)


@pytest.mark.asyncio
async def test_unsupported_timeframe_is_rejected_not_fabricated():
    # 4h has no native Yahoo interval; the provider must refuse, not resample.
    provider = _provider(_ok_handler({}))
    with pytest.raises(ProviderError):
        await provider.get_candles(Instrument("AAPL"), Timeframe.H4, limit=100)


@pytest.mark.asyncio
async def test_http_error_becomes_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    provider = _provider(handler)
    with pytest.raises(ProviderError):
        await provider.get_candles(Instrument("NOPE"), Timeframe.D1, limit=100)


@pytest.mark.asyncio
async def test_error_payload_becomes_provider_error():
    payload = _chart_payload(
        opens=[], highs=[], lows=[], closes=[], volumes=[],
        error={"code": "Not Found", "description": "No data found for symbol"},
    )
    provider = _provider(_ok_handler(payload))
    with pytest.raises(ProviderError):
        await provider.get_candles(Instrument("NOPE"), Timeframe.D1, limit=100)


@pytest.mark.asyncio
async def test_empty_result_becomes_insufficient_data():
    payload = _chart_payload(
        opens=[], highs=[], lows=[], closes=[], volumes=[], result_empty=True
    )
    provider = _provider(_ok_handler(payload))
    with pytest.raises(InsufficientDataError):
        await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=100)


@pytest.mark.asyncio
async def test_all_null_bars_become_insufficient_data():
    payload = _chart_payload(
        opens=[None, None],
        highs=[None, None],
        lows=[None, None],
        closes=[None, None],
        volumes=[None, None],
    )
    provider = _provider(_ok_handler(payload))
    with pytest.raises(InsufficientDataError):
        await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=100)


@pytest.mark.asyncio
async def test_network_error_becomes_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(handler)
    with pytest.raises(ProviderError):
        await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=100)


# ==============================================================
# Retry policy (Phase 2)
# ==============================================================


def _single_bar_payload() -> dict:
    return _chart_payload(
        opens=[1.0], highs=[1.0], lows=[1.0], closes=[1.0], volumes=[1]
    )


@pytest.mark.asyncio
async def test_rate_limited_then_success_is_retried():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json=_single_bar_payload())

    provider = _provider(handler, max_retries=2)
    data = await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=1)
    assert data.count == 1
    assert len(calls) == 2  # one failure, one retry


@pytest.mark.asyncio
async def test_server_error_exhausts_retries_and_raises_typed():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503, text="service unavailable")

    provider = _provider(handler, max_retries=1)
    with pytest.raises(ProviderError):
        await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=1)
    assert len(calls) == 2  # initial + 1 retry


@pytest.mark.asyncio
async def test_client_error_is_not_retried():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(404, text="not found")

    provider = _provider(handler, max_retries=3)
    with pytest.raises(ProviderError):
        await provider.get_candles(Instrument("NOPE"), Timeframe.D1, limit=1)
    assert len(calls) == 1  # permanent error: fail fast


@pytest.mark.asyncio
async def test_transport_error_is_retried_then_raises():
    calls: list[int] = []

    async def sleeper(seconds: float) -> None:
        calls.append(seconds)  # record the backoff the provider chose

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = YahooMarketDataProvider(
        client=client, max_retries=1, retry_backoff_seconds=1.0, sleeper=sleeper
    )
    with pytest.raises(ProviderError):
        await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=1)
    assert calls == [1.0]  # exponential backoff: base * 2^0 on first retry


@pytest.mark.asyncio
async def test_no_retries_by_default():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(502, text="bad gateway")

    provider = _provider(handler)  # max_retries=0 default
    with pytest.raises(ProviderError):
        await provider.get_candles(Instrument("AAPL"), Timeframe.D1, limit=1)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_capability_flags_are_honest():
    provider = _provider(_ok_handler(_single_bar_payload()))
    assert provider.supports_order_book is False
    assert provider.supports_trades is False
    with pytest.raises(ProviderError, match="does not provide order-book"):
        await provider.get_order_book(Instrument("AAPL"))
    with pytest.raises(ProviderError, match="does not provide trade-tick"):
        await provider.get_recent_trades(Instrument("AAPL"))


# ==============================================================
# Multi-market symbol mapping (Phase 2)
# ==============================================================


@pytest.mark.parametrize(
    ("instrument", "expected"),
    [
        (Instrument("AAPL"), "AAPL"),
        (Instrument("RELIANCE", exchange="NSE"), "RELIANCE.NS"),
        (Instrument("UNKNOWN", exchange="ZZZ"), "UNKNOWN"),  # bare fallback
        (Instrument("EURUSD", asset_class="forex"), "EURUSD=X"),
        (Instrument("EUR", asset_class="forex"), "EURUSD=X"),
        (Instrument("BTC", asset_class="crypto"), "BTC-USD"),
        (Instrument("BTC/USDT", asset_class="crypto"), "BTC-USDT"),
        (Instrument("SPY", asset_class="index"), "SPY"),
        (Instrument("GC", asset_class="commodity"), "GC=F"),
        (Instrument("GC=F", asset_class="commodity"), "GC=F"),
    ],
)
def test_yahoo_symbol_maps_every_asset_class(instrument, expected):
    assert yahoo_symbol(instrument) == expected


@pytest.mark.asyncio
async def test_forex_symbol_requests_the_fx_quote_convention():
    captured: list[httpx.Request] = []
    provider = _provider(
        _ok_handler(_single_bar_payload(), capture=captured)
    )
    await provider.get_candles(
        Instrument("EURUSD", asset_class="forex"), Timeframe.D1, limit=1
    )
    assert "EURUSD=X" in str(captured[0].url)


def test_provider_serves_equity_index_forex_crypto_commodity():
    provider = _provider(_ok_handler(_single_bar_payload()))
    assert provider.supports_asset_class("equity")
    assert provider.supports_asset_class("INDEX")
    assert provider.supports_asset_class("forex")
    assert provider.supports_asset_class("crypto")
    assert provider.supports_asset_class("commodity")
    assert not provider.supports_asset_class("option")


@pytest.mark.asyncio
async def test_commodity_symbol_requests_the_futures_convention():
    captured: list[httpx.Request] = []
    provider = _provider(
        _ok_handler(_single_bar_payload(), capture=captured)
    )
    await provider.get_candles(
        Instrument("GC", asset_class="commodity"), Timeframe.D1, limit=1
    )
    assert "GC%3DF" in str(captured[0].url) or "GC=F" in str(captured[0].url)


@pytest.mark.asyncio
async def test_monthly_timeframe_maps_to_yahoo_1mo():
    captured: list[httpx.Request] = []
    payload = _chart_payload(
        opens=[1.0], highs=[1.0], lows=[1.0], closes=[1.0], volumes=[1]
    )
    provider = _provider(_ok_handler(payload, capture=captured))
    data = await provider.get_candles(Instrument("AAPL"), Timeframe.MN, limit=1)
    assert data.count == 1
    assert "interval=1mo" in str(captured[0].url)


@pytest.mark.asyncio
async def test_monthly_timeframe_parses_case_sensitively():
    # Timeframe.parse must not fold "1M" (month) into "1m" (minute).
    assert Timeframe.parse("1M") is Timeframe.MN
