"""
Shared builders for trading tests.

These construct MarketData with *controlled* shapes (a clean uptrend, a
downtrend, a stale series) so the structure/technical/evidence tests assert
against known behaviour rather than the mock provider's random walk. All data
here is clearly synthetic and used only for deterministic assertions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.trading.domain.enums import (
    DataQualityStatus,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData, Quote
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.providers.base import MarketDataProvider


def _provenance(tier: SourceTier = SourceTier.PRIMARY) -> Provenance:
    return Provenance(source="test", tier=tier, detail="synthetic test fixture")


def make_market_data(
    closes: list[float],
    *,
    symbol: str = "TEST",
    timeframe: Timeframe = Timeframe.D1,
    tier: SourceTier = SourceTier.PRIMARY,
    end: datetime | None = None,
    quality: DataQuality | None = None,
    volume: float = 1_000_000.0,
) -> MarketData:
    """Build a MarketData from a close series with plausible OHLC/volume."""
    end = end or datetime.now(timezone.utc).replace(microsecond=0)
    step = timedelta(seconds=timeframe.seconds)
    n = len(closes)
    candles: list[Candle] = []
    prev = closes[0]
    for i, close in enumerate(closes):
        open_ = prev
        hi = max(open_, close) + 0.5
        lo = min(open_, close) - 0.5
        ts = end - step * (n - 1 - i)
        candles.append(
            Candle(
                timestamp=ts,
                open=open_,
                high=hi,
                low=lo,
                close=close,
                volume=volume,
            )
        )
        prev = close
    return MarketData(
        instrument=Instrument.parse(symbol),
        timeframe=timeframe,
        candles=tuple(candles),
        provenance=_provenance(tier),
        quality=quality
        or DataQuality(status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0),
    )


@pytest.fixture
def uptrend_data() -> MarketData:
    # Steadily rising series with mild noise, enough bars for every indicator.
    closes = [100.0 + i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]
    return make_market_data(closes, symbol="UP")


@pytest.fixture
def downtrend_data() -> MarketData:
    closes = [200.0 - i * 0.8 + (0.3 if i % 2 else -0.3) for i in range(120)]
    return make_market_data(closes, symbol="DOWN")


@pytest.fixture
def flat_data() -> MarketData:
    closes = [100.0 + (0.2 if i % 2 else -0.2) for i in range(120)]
    return make_market_data(closes, symbol="FLAT")


def make_invalid_market_data(*, symbol: str = "BAD") -> MarketData:
    """A series with a structurally impossible candle (high below low)."""
    data = make_market_data([100.0 + i for i in range(30)], symbol=symbol)
    bad = data.candles[-1]
    broken = Candle(
        timestamp=bad.timestamp,
        open=bad.open,
        high=1.0,  # high below low -> INVALID
        low=100.0,
        close=bad.close,
        volume=bad.volume,
    )
    return MarketData(
        instrument=data.instrument,
        timeframe=data.timeframe,
        candles=data.candles[:-1] + (broken,),
        provenance=data.provenance,
        quality=data.quality,
    )


class FakeProvider(MarketDataProvider):
    """
    A controllable, clearly-synthetic provider for service tests.

    Unlike the mock provider it is stamped PRIMARY so quality-assessment tests
    are not dominated by the mock penalty; it simply hands back whatever
    MarketData/Quote the test built and counts how often it was called (so
    cache behaviour is observable).
    """

    name = "fake"
    tier = SourceTier.PRIMARY

    def __init__(self, data: MarketData, *, quote: Quote | None = None) -> None:
        self._data = data
        self._quote = quote
        self.candle_calls = 0
        self.quote_calls = 0

    async def get_candles(self, instrument, timeframe, *, limit) -> MarketData:
        self.candle_calls += 1
        return self._data

    async def get_quote(self, instrument) -> Quote:
        self.quote_calls += 1
        if self._quote is None:
            raise NotImplementedError("FakeProvider was not given a quote.")
        return self._quote
