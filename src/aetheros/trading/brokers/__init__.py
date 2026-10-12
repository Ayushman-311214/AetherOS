"""
The broker package (spec Phase 9).

:class:`BrokerProvider` is the common interface every venue implements;
:class:`PaperTradingProvider` is the reference implementation -- real market
prices against virtual money, per the spec's paper-trading definition. Live
venue connectors (Interactive Brokers, Binance, Bybit, Alpaca, MetaTrader)
are later phases behind the same interface.

:class:`PriceSource` is where a venue reads the price it fills at, so the same
paper venue can serve the live tape (its default) or a replayed historical bar
during a simulation without a second venue implementation existing.
"""

from __future__ import annotations

from .base import BrokerProvider
from .paper_provider import (
    DEFAULT_INITIAL_BALANCE,
    PaperTradingProvider,
)
from .price_source import LiveCandlePriceSource, PriceSource

__all__ = [
    "DEFAULT_INITIAL_BALANCE",
    "BrokerProvider",
    "LiveCandlePriceSource",
    "PaperTradingProvider",
    "PriceSource",
]
