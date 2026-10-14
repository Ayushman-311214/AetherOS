"""
The replay cursor (spec Phase 14, "live market simulation").

A simulation is a series of bars played back one at a time. Everything else in
this package is accounting; this module is the clock, and it exists as a
separate object because the *only* way to guarantee a simulated decision could
not see the future is to make the visible slice a property of the cursor
rather than a convention the loop is trusted to honour.

:meth:`SimulationFeed.visible` returns ``data.window(0, cursor + 1)`` -- the bar
under the cursor and every bar before it, never one after. That reuses
:meth:`MarketData.window`, the single place in this codebase where the
past-only guarantee is defined, so a replayed session and a walk-forward fold
cannot disagree about what "up to here" means.

:class:`FeedPriceSource` adapts the same cursor to the broker layer's
:class:`PriceSource` port, which is what lets the *real* paper venue fill a
replayed bar.
"""

from __future__ import annotations

import math

from ..domain.market_data import Candle, MarketData
from ..errors import BrokerError


class SimulationFeed:
    """
    A past-only cursor over one instrument's series.

    The cursor starts at the first bar and never runs past the last: an
    exhausted feed is an honest end of data, so :meth:`advance` reports it
    rather than wrapping or holding.
    """

    def __init__(self, data: MarketData) -> None:
        if not data.candles:
            raise ValueError(
                "A simulation feed needs at least one candle to replay."
            )
        self._data = data
        self._cursor = 0

    @property
    def data(self) -> MarketData:
        """The full series being replayed."""
        return self._data

    @property
    def cursor(self) -> int:
        """The index of the bar currently under the cursor."""
        return self._cursor

    def __len__(self) -> int:
        return len(self._data.candles)

    @property
    def exhausted(self) -> bool:
        """Whether the cursor sits on the final bar."""
        return self._cursor >= len(self) - 1

    def bar(self) -> Candle:
        """The bar under the cursor."""
        return self._data.candles[self._cursor]

    def seek(self, index: int) -> None:
        """
        Place the cursor at ``index``.

        The warmup seek: an index the series does not contain is an error
        rather than a clamp, because a caller that asked to start past the end
        has a bug, and silently starting somewhere else would hide it.
        """
        if index < 0 or index >= len(self):
            raise ValueError(
                f"Cannot seek to bar {index} of a {len(self)}-bar series."
            )
        self._cursor = index

    def price(self) -> float:
        """
        The price a decision taken now would fill at: this bar's close.

        The close is the honest choice for a bar-by-bar replay -- the bar is
        over when the decision is made, so the close is the last price that is
        genuinely known. Entering at the *next* bar's open would be the same
        thing with one more bar of hindsight baked in.
        """
        price = float(self.bar().close)
        if not math.isfinite(price) or price <= 0:
            raise BrokerError(
                f"The replayed price for '{self._data.instrument.key}' at bar "
                f"{self._cursor} is not usable.",
                context={"instrument": self._data.instrument.key, "price": price},
            )
        return price

    def visible(self) -> MarketData:
        """
        The series as it stood at the end of the current bar -- nothing more.

        This is the look-ahead guarantee, stated once: half-open ``[0, cursor+1)``
        through the same slicing primitive the backtester uses.
        """
        return self._data.window(0, self._cursor + 1)

    def advance(self) -> bool:
        """Move to the next bar; False when the cursor was already at the end."""
        if self.exhausted:
            return False
        self._cursor += 1
        return True


class FeedPriceSource:
    """
    A broker :class:`~aetheros.trading.brokers.price_source.PriceSource` backed
    by a replay cursor.

    Injecting this into the paper venue is what lets the *real* venue fill a
    simulated session: the §9 chain (execution engine → broker) is untouched,
    and the only thing that changes is where the venue reads its price. The
    instrument is checked rather than assumed -- a venue wired to the wrong
    feed must fail loudly instead of quietly filling one instrument at
    another's price.
    """

    def __init__(self, feed: SimulationFeed) -> None:
        self._feed = feed

    @property
    def feed(self) -> SimulationFeed:
        return self._feed

    async def price(self, instrument_key: str) -> float:
        expected = self._feed.data.instrument.key
        if instrument_key != expected:
            raise BrokerError(
                f"This simulated feed replays '{expected}', not "
                f"'{instrument_key}'.",
                context={"instrument": instrument_key, "feed": expected},
            )
        return self._feed.price()
