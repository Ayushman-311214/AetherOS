"""
MarketDataService: caching, validation, freshness and honest error typing.

This is the layer the spec cares most about (CLAUDE.md sections 9, 47): it must
never present stale data as current, never pass structurally-broken bars
downstream, and must translate provider failure into typed errors.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import DataQualityStatus, Timeframe
from aetheros.trading.errors import InvalidSymbolError, MarketDataError
from aetheros.trading.events import MarketDataUpdated
from aetheros.trading.services.market_data_service import MarketDataService
from aetheros.runtime.events.event_bus import EventBus

from .conftest import FakeProvider, make_invalid_market_data, make_market_data


def _service(provider, event_bus=None):
    return MarketDataService(provider, get_settings(), event_bus=event_bus)


@pytest.mark.asyncio
async def test_fresh_series_is_ok():
    data = make_market_data([100.0 + i for i in range(120)])
    svc = _service(FakeProvider(data))
    out = await svc.get_candles("AAPL", "1d", limit=120)
    assert out.quality.status is DataQualityStatus.OK


@pytest.mark.asyncio
async def test_results_are_cached():
    data = make_market_data([100.0 + i for i in range(60)])
    provider = FakeProvider(data)
    svc = _service(provider)
    await svc.get_candles("AAPL", "1d", limit=60)
    await svc.get_candles("AAPL", "1d", limit=60)
    # Second identical request served from cache -> provider hit once.
    assert provider.candle_calls == 1


@pytest.mark.asyncio
async def test_partial_series_is_flagged():
    data = make_market_data([100.0 + i for i in range(50)])
    svc = _service(FakeProvider(data))
    out = await svc.get_candles("AAPL", "1d", limit=100)  # asked 100, got 50
    assert out.quality.status is DataQualityStatus.PARTIAL
    assert any("received 50" in issue for issue in out.quality.issues)


@pytest.mark.asyncio
async def test_stale_series_is_flagged():
    old_end = datetime.now(timezone.utc) - timedelta(days=10)
    data = make_market_data(
        [100.0 + i for i in range(120)], timeframe=Timeframe.D1, end=old_end
    )
    svc = _service(FakeProvider(data))
    out = await svc.get_candles("AAPL", "1d", limit=120)
    assert out.quality.status is DataQualityStatus.STALE
    assert not out.quality.ok


@pytest.mark.asyncio
async def test_structurally_broken_series_is_invalid():
    data = make_invalid_market_data()
    svc = _service(FakeProvider(data))
    out = await svc.get_candles("AAPL", "1d", limit=len(data.candles))
    assert out.quality.status is DataQualityStatus.INVALID
    assert not out.quality.usable


@pytest.mark.asyncio
async def test_invalid_symbol_raises():
    svc = _service(FakeProvider(make_market_data([1.0, 2.0, 3.0])))
    with pytest.raises(InvalidSymbolError):
        await svc.get_candles("", "1d", limit=10)


@pytest.mark.asyncio
async def test_unknown_timeframe_raises():
    svc = _service(FakeProvider(make_market_data([1.0, 2.0, 3.0])))
    with pytest.raises(MarketDataError):
        await svc.get_candles("AAPL", "bogus", limit=10)


@pytest.mark.asyncio
async def test_non_positive_limit_raises():
    svc = _service(FakeProvider(make_market_data([1.0, 2.0, 3.0])))
    with pytest.raises(MarketDataError):
        await svc.get_candles("AAPL", "1d", limit=0)


@pytest.mark.asyncio
async def test_provider_failure_becomes_market_data_error():
    class Broken(FakeProvider):
        async def get_candles(self, instrument, timeframe, *, limit):
            raise RuntimeError("socket exploded")

    svc = _service(Broken(make_market_data([1.0, 2.0, 3.0])))
    with pytest.raises(MarketDataError):
        await svc.get_candles("AAPL", "1d", limit=10)


@pytest.mark.asyncio
async def test_publishes_market_data_updated():
    received: list[MarketDataUpdated] = []
    bus = EventBus()
    await bus.subscribe(MarketDataUpdated, lambda e: received.append(e))

    data = make_market_data([100.0 + i for i in range(30)])
    svc = _service(FakeProvider(data), event_bus=bus)
    await svc.get_candles("AAPL", "1d", limit=30)

    assert len(received) == 1
    assert received[0].candle_count == 30
