"""
Fill-price sources for the broker layer (spec Phase 14).

A venue needs exactly one thing from the outside world: the price an order
would fill at. For a live venue that is the current tape; during a replayed
session it is the bar under the cursor. The question is the same, so the seam
is the same, and putting it here is what lets the *paper venue itself* fill a
simulated session -- the §9 chain (execution engine → broker → venue) stays
unbroken, and only the price the venue reads changes.

:class:`LiveCandlePriceSource` is the production answer and is behaviourally
exactly what the paper provider did before this module existed: the last close
of the live daily feed. :class:`PriceSource` is the interface a simulation
implements.

Both honour the same contract: a price that cannot be read raises
:class:`BrokerError` -- the honest venue outage -- rather than returning a
fabricated number.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..domain.enums import Timeframe
from ..domain.market_data import MarketData
from ..errors import BrokerError

if TYPE_CHECKING:
    # Only used for annotations; importing it at runtime pulls in
    # ``services/__init__`` which re-imports the brokers package (a cycle).
    # The instance is only ever stored and called, never re-instantiated.
    from ..services.market_data_service import MarketDataService


@runtime_checkable
class PriceSource(Protocol):
    """
    Where a venue reads the price it would fill at.

    Deliberately narrow: an instrument key in, one positive finite price out.
    A source that cannot answer raises :class:`BrokerError`; it never guesses,
    because a venue that invents a price is not a venue.
    """

    async def price(self, instrument_key: str) -> float:
        """The price to fill at, or a :class:`BrokerError` if unreadable."""
        ...


class LiveCandlePriceSource:
    """
    The live market price, read through the shared :class:`MarketDataService`.

    This is the production fill source and the paper provider's default. It
    reads the most recent daily close -- the same read the analysis pipeline
    performs, so a paper fill and an analysis can never disagree about the
    price because they asked two different places.
    """

    def __init__(self, market_data: MarketDataService) -> None:
        self._market_data = market_data

    async def price(self, instrument_key: str) -> float:
        """
        The live market price for a fill, read off the shared feed.

        Raises :class:`BrokerError` when the feed cannot produce a price --
        the honest venue outage, never a fabricated fill.
        """
        try:
            data: MarketData = await self._market_data.get_candles(
                instrument_key, Timeframe.D1.value, limit=1
            )
        except Exception as exc:
            raise BrokerError(
                f"The market feed is unavailable for '{instrument_key}': {exc}",
                context={"instrument": instrument_key},
            ) from exc
        candles = data.candles
        if not candles:
            raise BrokerError(
                f"No market price is available for '{instrument_key}'.",
                context={"instrument": instrument_key},
            )
        price = float(candles[-1].close)
        if not math.isfinite(price) or price <= 0:
            raise BrokerError(
                f"The market price for '{instrument_key}' is not usable.",
                context={"instrument": instrument_key, "price": price},
            )
        return price
