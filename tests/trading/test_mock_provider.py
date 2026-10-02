"""
Mock market-data provider: reproducibility and honesty.

The mock exists so the whole trading core can run without a real feed, but the
spec's absolute rule is that synthetic data must never look real. These tests
pin both properties: the series is deterministic per symbol, and every result
is stamped SourceTier.MOCK with an explicit synthetic-data issue.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import SourceTier, Timeframe
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.providers.mock_provider import MockMarketDataProvider


@pytest.mark.asyncio
async def test_candles_are_deterministic_per_symbol():
    provider = MockMarketDataProvider()
    inst = Instrument.parse("AAPL")
    a = await provider.get_candles(inst, Timeframe.D1, limit=50)
    b = await provider.get_candles(inst, Timeframe.D1, limit=50)
    assert [c.close for c in a.candles] == [c.close for c in b.candles]


@pytest.mark.asyncio
async def test_different_symbols_differ():
    provider = MockMarketDataProvider()
    a = await provider.get_candles(Instrument.parse("AAPL"), Timeframe.D1, limit=50)
    b = await provider.get_candles(Instrument.parse("MSFT"), Timeframe.D1, limit=50)
    assert [c.close for c in a.candles] != [c.close for c in b.candles]


@pytest.mark.asyncio
async def test_result_is_labelled_mock():
    provider = MockMarketDataProvider()
    assert provider.is_mock
    data = await provider.get_candles(Instrument.parse("AAPL"), Timeframe.D1, limit=20)
    assert data.provenance.tier is SourceTier.MOCK
    assert data.provenance.is_mock
    assert any("mock" in issue.lower() for issue in data.quality.issues)


@pytest.mark.asyncio
async def test_candle_count_matches_limit():
    provider = MockMarketDataProvider()
    data = await provider.get_candles(Instrument.parse("AAPL"), Timeframe.H1, limit=37)
    assert len(data.candles) == 37


@pytest.mark.asyncio
async def test_ohlc_are_internally_consistent():
    provider = MockMarketDataProvider()
    data = await provider.get_candles(Instrument.parse("AAPL"), Timeframe.D1, limit=100)
    for c in data.candles:
        assert c.high >= c.open and c.high >= c.close and c.high >= c.low
        assert c.low <= c.open and c.low <= c.close
        assert c.volume >= 0


@pytest.mark.asyncio
async def test_timestamps_strictly_increasing():
    provider = MockMarketDataProvider()
    data = await provider.get_candles(Instrument.parse("AAPL"), Timeframe.D1, limit=50)
    ts = [c.timestamp for c in data.candles]
    assert all(b > a for a, b in zip(ts, ts[1:]))


@pytest.mark.asyncio
async def test_quote_is_mock():
    provider = MockMarketDataProvider()
    quote = await provider.get_quote(Instrument.parse("AAPL"))
    assert quote.provenance.tier is SourceTier.MOCK
    assert quote.price > 0


@pytest.mark.asyncio
async def test_zero_limit_rejected():
    provider = MockMarketDataProvider()
    with pytest.raises(ValueError):
        await provider.get_candles(Instrument.parse("AAPL"), Timeframe.D1, limit=0)
