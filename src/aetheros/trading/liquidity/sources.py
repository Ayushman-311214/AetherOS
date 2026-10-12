"""
Canonical market-data source interfaces for the liquidity layer.

The brief asks for ``CandleSource`` / ``TradeSource`` / ``OrderBookSource`` /
``MarketDataSource`` interfaces so a real provider can be plugged in without
hard-coding an exchange. Rather than invent a parallel provider hierarchy, these
are thin, honest *capability interfaces* that sit on top of the existing
:class:`~aetheros.trading.providers.base.MarketDataProvider` ABC -- the provider
already declares ``get_candles`` / ``get_quote`` / ``get_order_book`` /
``get_recent_trades`` and its ``supports_order_book`` / ``supports_trades``
capability flags. A source wraps a provider and exposes exactly one of those
reads as a typed, validated stream the liquidity analyzers consume.

The honesty rule is the same one the provider enforces: a source that cannot
serve a stream raises a typed ``ProviderError`` / ``InsufficientDataError`` --
it never fabricates candles, books or prints, and it never invents an
``is_mock`` the provider did not stamp.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from ..domain.instrument import Instrument
from ..domain.market_data import MarketData
from ..domain.order_book import OrderBook, TradeTick
from ..errors import ProviderError
from ..providers.base import MarketDataProvider

# What a source hands back on each call.
CandleT = TypeVar("CandleT")


class MarketDataSource(ABC):
    """
    A single-instrument market-data read, bound to one provider.

    ``name`` mirrors the provider's source label (for provenance), ``is_mock``
    mirrors its tier. The single abstract method is the read itself; the
    concrete subclasses pin *which* read it is.
    """

    name: str = "unknown"

    @property
    def is_mock(self) -> bool:
        return False


class CandleSource(MarketDataSource):
    """A source that yields a candle series for an instrument/timeframe."""

    @abstractmethod
    async def candles(
        self, instrument: Instrument, timeframe, *, limit: int
    ) -> MarketData:
        raise NotImplementedError


class OrderBookSource(MarketDataSource):
    """A source that yields order-book depth snapshots."""

    @abstractmethod
    async def order_book(self, instrument: Instrument, *, depth: int) -> OrderBook:
        raise NotImplementedError


class TradeSource(MarketDataSource):
    """A source that yields recent executed-trade prints."""

    @abstractmethod
    async def recent_trades(
        self, instrument: Instrument, *, limit: int
    ) -> tuple[TradeTick, ...]:
        raise NotImplementedError


class ProviderSource(CandleSource, OrderBookSource, TradeSource):
    """
    Adapts a :class:`MarketDataProvider` to all three liquidity sources.

    One object, three reads -- the natural way to plug a real provider (Yahoo,
    ccxt, or any future adapter) into the liquidity layer without touching the
    analyzers. A read the provider cannot serve is an honest typed refusal,
    exactly as the provider itself reports it; the source adds nothing and
    fabricates nothing.
    """

    def __init__(self, provider: MarketDataProvider) -> None:
        if provider is None:
            raise ValueError("ProviderSource requires a market-data provider.")
        self._provider = provider
        self.name = provider.name

    @property
    def provider(self) -> MarketDataProvider:
        return self._provider

    @property
    def is_mock(self) -> bool:
        return self._provider.is_mock

    async def candles(
        self, instrument: Instrument, timeframe, *, limit: int
    ) -> MarketData:
        return await self._provider.get_candles(
            instrument, timeframe, limit=limit
        )

    async def order_book(self, instrument: Instrument, *, depth: int) -> OrderBook:
        if not self._provider.supports_order_book:
            raise ProviderError(
                f"Source '{self.name}' does not provide order-book data.",
                context={"source": self.name, "instrument": instrument.key},
            )
        return await self._provider.get_order_book(instrument, depth=depth)

    async def recent_trades(
        self, instrument: Instrument, *, limit: int
    ) -> tuple[TradeTick, ...]:
        if not self._provider.supports_trades:
            raise ProviderError(
                f"Source '{self.name}' does not provide trade-tick data.",
                context={"source": self.name, "instrument": instrument.key},
            )
        return await self._provider.get_recent_trades(instrument, limit=limit)
