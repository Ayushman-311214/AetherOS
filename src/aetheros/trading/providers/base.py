"""
Market-data provider abstraction.

Trading services depend on this interface, never on a concrete source, so a
real broker/exchange/vendor adapter can be swapped in later without touching
the analysis layers (CLAUDE.md sections 10, 23 -- dependency inversion).

A provider's job is narrow and honest:
- return candles / a quote for an instrument and timeframe,
- stamp every result with Provenance (source + SourceTier) and never claim a
  tier it cannot back up,
- raise a typed error (MarketDataError / InsufficientDataError / ...) rather
  than returning fabricated bars when it cannot fulfil a request.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.enums import SourceTier, Timeframe
from ..domain.instrument import Instrument
from ..domain.market_data import MarketData, Quote


class MarketDataProvider(ABC):
    """Interface every market-data source implements."""

    #: Human-readable source label used in Provenance.
    name: str = "unknown"

    #: The best tier this provider can honestly claim for its data.
    tier: SourceTier = SourceTier.UNVERIFIED

    @property
    def is_mock(self) -> bool:
        return self.tier is SourceTier.MOCK

    @abstractmethod
    async def get_candles(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        *,
        limit: int,
    ) -> MarketData:
        """
        Return up to ``limit`` most-recent candles for the instrument.

        Must raise a trading error (never fabricate) if the data cannot be
        retrieved. The returned MarketData carries its own Provenance/quality.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_quote(self, instrument: Instrument) -> Quote:
        """Return the latest price snapshot for the instrument."""
        raise NotImplementedError
