"""
Deterministic mock market-data provider.

This exists so the entire numerical trading core can be exercised end-to-end --
in tests and in a no-credentials dev run -- WITHOUT a real data feed, while
never letting synthetic numbers masquerade as real ones (spec sections 53, 61).

Honesty guarantees:
- every result is stamped ``SourceTier.MOCK`` and ``is_mock`` is True,
- the DataQuality carries an explicit "synthetic mock data" issue that
  propagates all the way to the final analysis and report,
- the series is a seeded geometric random walk keyed by the instrument symbol,
  so the same symbol always yields the same candles (reproducible tests), but
  it is clearly labelled as fabricated for demonstration only.

It is NOT a market simulator and must never be used as evidence of real market
behaviour.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import numpy as np

from ..domain.enums import DataQualityStatus, SourceTier, Timeframe
from ..domain.instrument import Instrument
from ..domain.market_data import Candle, MarketData, Quote
from ..domain.provenance import DataQuality, Provenance
from .base import MarketDataProvider

_MOCK_ISSUE = "Synthetic mock data (SourceTier.MOCK) — not real market data."


def _seed_for(symbol: str) -> int:
    digest = hashlib.sha1(symbol.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


class MockMarketDataProvider(MarketDataProvider):
    """A reproducible, clearly-labelled synthetic data source."""

    name = "mock"
    tier = SourceTier.MOCK

    def __init__(self, *, base_price: float = 100.0, daily_vol: float = 0.015) -> None:
        if base_price <= 0:
            raise ValueError("base_price must be positive.")
        self._base_price = base_price
        self._daily_vol = daily_vol

    def _generate(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        limit: int,
    ) -> list[Candle]:
        rng = np.random.default_rng(_seed_for(instrument.symbol))
        # Scale per-bar volatility off the timeframe so shorter bars move less.
        scale = (timeframe.seconds / Timeframe.D1.seconds) ** 0.5
        vol = self._daily_vol * scale
        # Symbol-dependent starting price for variety, still deterministic.
        start = self._base_price * (0.5 + (_seed_for(instrument.symbol) % 1000) / 1000.0)

        log_returns = rng.normal(loc=0.0, scale=vol, size=limit)
        prices = start * np.exp(np.cumsum(log_returns))

        now = datetime.now(timezone.utc).replace(microsecond=0)
        step = timedelta(seconds=timeframe.seconds)

        candles: list[Candle] = []
        prev_close = start
        for i in range(limit):
            close = float(prices[i])
            open_ = float(prev_close)
            hi = max(open_, close) * (1.0 + abs(rng.normal(0.0, vol * 0.5)))
            lo = min(open_, close) * (1.0 - abs(rng.normal(0.0, vol * 0.5)))
            volume = float(abs(rng.normal(1_000_000, 250_000)))
            ts = now - step * (limit - 1 - i)
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
            prev_close = close
        return candles

    async def get_candles(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        *,
        limit: int,
    ) -> MarketData:
        if limit <= 0:
            raise ValueError("limit must be positive.")
        candles = self._generate(instrument, timeframe, limit)
        provenance = Provenance(
            source=self.name,
            tier=SourceTier.MOCK,
            detail="deterministic seeded random walk",
        )
        quality = DataQuality(
            status=DataQualityStatus.OK,
            issues=(_MOCK_ISSUE,),
            freshness_seconds=0.0,
        )
        return MarketData(
            instrument=instrument,
            timeframe=timeframe,
            candles=tuple(candles),
            provenance=provenance,
            quality=quality,
        )

    async def get_quote(self, instrument: Instrument) -> Quote:
        # Reuse the last generated daily candle so quote and candles agree.
        data = await self.get_candles(instrument, Timeframe.D1, limit=2)
        last = data.candles[-1]
        prev = data.candles[-2]
        change_pct = (
            (last.close / prev.close - 1.0) * 100.0 if prev.close else None
        )
        return Quote(
            instrument=instrument,
            price=last.close,
            timestamp=last.timestamp,
            provenance=Provenance(
                source=self.name,
                tier=SourceTier.MOCK,
                detail="deterministic seeded random walk",
            ),
            volume=last.volume,
            change_pct=change_pct,
        )
