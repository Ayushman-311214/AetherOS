"""Market-data & news provider abstractions and implementations."""

from __future__ import annotations

from .base import MarketDataProvider
from .fundamentals_base import FundamentalsProvider
from .mock_fundamentals_provider import MockFundamentalsProvider
from .mock_news_provider import MockNewsProvider
from .mock_provider import MockMarketDataProvider
from .news_base import NewsProvider
from .yahoo_provider import YahooMarketDataProvider

__all__ = [
    "MarketDataProvider",
    "MockMarketDataProvider",
    "YahooMarketDataProvider",
    "NewsProvider",
    "MockNewsProvider",
    "FundamentalsProvider",
    "MockFundamentalsProvider",
]


def ccxt_provider_available() -> bool:
    """Whether the optional ccxt dependency is importable (no import cost)."""
    import importlib.util

    return importlib.util.find_spec("ccxt") is not None
