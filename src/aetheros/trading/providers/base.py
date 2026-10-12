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
from ..domain.order_book import OrderBook, TradeTick
from ..errors import ProviderError


class MarketDataProvider(ABC):
    """Interface every market-data source implements."""

    #: Human-readable source label used in Provenance.
    name: str = "unknown"

    #: The best tier this provider can honestly claim for its data.
    tier: SourceTier = SourceTier.UNVERIFIED

    #: Asset classes this provider can serve. Used by callers to route an
    #: instrument to a provider that actually lists it (multi-market support)
    #: rather than sending every symbol to every feed.
    asset_classes: tuple[str, ...] = ("equity",)

    #: Whether this provider can return order-book depth snapshots.
    supports_order_book: bool = False

    #: Whether this provider can return recent executed trades (ticks).
    supports_trades: bool = False

    @property
    def is_mock(self) -> bool:
        return self.tier is SourceTier.MOCK

    def supports_asset_class(self, asset_class: str) -> bool:
        """Whether the provider serves an asset class (case-insensitive)."""
        wanted = asset_class.strip().lower()
        return any(wanted == served.lower() for served in self.asset_classes)

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

    async def get_order_book(
        self,
        instrument: Instrument,
        *,
        depth: int = 10,
    ) -> OrderBook:
        """
        Return the current depth snapshot for the instrument.

        The default is an honest refusal: a provider that cannot serve books
        says so with a typed error rather than fabricating levels. Only
        providers that set ``supports_order_book = True`` override this.
        """
        raise ProviderError(
            f"Provider '{self.name}' does not provide order-book data.",
            context={"provider": self.name, "instrument": instrument.key},
        )

    async def get_recent_trades(
        self,
        instrument: Instrument,
        *,
        limit: int = 50,
    ) -> tuple[TradeTick, ...]:
        """
        Return up to ``limit`` most-recent executed trades for the instrument.

        The default is an honest refusal, exactly as for order books: only
        providers that set ``supports_trades = True`` override this.
        """
        raise ProviderError(
            f"Provider '{self.name}' does not provide trade-tick data.",
            context={"provider": self.name, "instrument": instrument.key},
        )
