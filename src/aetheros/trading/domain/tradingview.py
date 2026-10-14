"""
TradingView chart value objects (spec Phase 18).

The identity and state of one TradingView chart *as the adapter sees it*: what
was requested (symbol, timeframe, URL), what the page reports about itself
(title, URL after navigation), and what vision read off the rendered frame.
Nothing here drives a browser or analyses a market -- those live in
``browser/``, ``desktop/``, ``vision/`` and ``trading/`` proper. These objects
are the stable shape the adapter hands back so Trading Intelligence can
consume chart state without touching automation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(UTC)


#: TradingView's chart host. Centralised so the URL convention lives in one
#: place rather than scattered across call sites.
TRADINGVIEW_BASE_URL = "https://www.tradingview.com/chart/"

#: Symbol slug separator TradingView uses in chart URLs (EXCHANGE:SYMBOL).
SYMBOL_SEPARATOR = ":"


def chart_url(symbol: str, exchange: str | None = None) -> str:
    """
    Build the TradingView chart URL for an instrument.

    Pure and unit-testable: no browser, no network. The slug is
    ``EXCHANGE:SYMBOL`` when an exchange is known, else the bare symbol --
    TradingView resolves either.
    """
    slug = symbol.strip().upper()
    if not slug:
        raise ValueError("A TradingView chart needs a non-empty symbol.")
    if exchange and exchange.strip():
        slug = f"{exchange.strip().upper()}{SYMBOL_SEPARATOR}{slug}"
    return f"{TRADINGVIEW_BASE_URL}?symbol={slug}"


@dataclass(frozen=True, slots=True)
class TradingViewChartState:
    """
    What one TradingView chart looks like right now.

    ``requested_*`` is what the caller asked for; ``page_*`` is what the
    browser reports after navigation (title/URL -- the observable proof the
    right chart loaded); ``visible_*`` is what vision read off the frame
    (symbol/timeframe/price text where found, else ``None`` -- never guessed).
    ``captured_at`` stamps the frame; ``limitations`` records what could not
    be determined.
    """

    requested_symbol: str
    requested_timeframe: str
    page_url: str = ""
    page_title: str = ""
    visible_symbol: str | None = None
    visible_timeframe: str | None = None
    visible_price: str | None = None
    captured_at: datetime = field(default_factory=_utcnow)
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_symbol": self.requested_symbol,
            "requested_timeframe": self.requested_timeframe,
            "page_url": self.page_url,
            "page_title": self.page_title,
            "visible_symbol": self.visible_symbol,
            "visible_timeframe": self.visible_timeframe,
            "visible_price": self.visible_price,
            "captured_at": self.captured_at.isoformat(),
            "limitations": list(self.limitations),
        }
