"""
Microstructure service.

The pull-based counterpart to the candle pipeline's "data arrived" events: it
fetches a live order-book depth snapshot and the recent executed-trade prints
through the injected :class:`MarketDataProvider` (never a hard-coded source) and
announces them on the shared event bus as ``OrderBookUpdated`` /
``TradeReceived``.

Honesty is structural here, exactly as in the candle service:

* It asks the provider's own capability flags first -- a source that cannot
  serve books or trades gets an honest typed ``MarketDataError`` refusal, never
  fabricated levels or prints (the provider's ``supports_order_book`` /
  ``supports_trades`` contract exists precisely so an unsupported call is a
  loud error, not an empty guess).
* ``is_mock`` is surfaced on every emitted event, so a synthetic book or print
  can never read downstream as a real one (CLAUDE.md sections 9, 28).
* Every publish is best-effort: a subscriber or bus failure is logged and
  swallowed so event delivery never breaks the underlying fetch.
"""

from __future__ import annotations

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.instrument import Instrument
from ..domain.order_book import OrderBook
from ..errors import InvalidSymbolError, MarketDataError, ProviderError
from ..events import OrderBookUpdated, TradeReceived
from ..providers.base import MarketDataProvider

logger = get_logger("trading.microstructure")


class MicrostructureService:
    """Fetches order-book / trade-tick data and announces it on the bus."""

    def __init__(
        self,
        provider: MarketDataProvider,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._provider = provider
        self._event_bus = event_bus

    @staticmethod
    def _coerce_instrument(symbol: str | Instrument) -> Instrument:
        if isinstance(symbol, Instrument):
            return symbol
        try:
            return Instrument.parse(symbol)
        except ValueError as exc:
            raise InvalidSymbolError(
                f"Cannot resolve instrument '{symbol}' for microstructure.",
                context={"symbol": symbol},
                cause=exc,
            ) from exc

    async def get_order_book(
        self, symbol: str | Instrument, *, depth: int = 10
    ) -> OrderBook:
        """
        Fetch the current depth snapshot and publish ``OrderBookUpdated``.

        Raises a typed error when the provider cannot serve books; an empty
        book is the provider's honest answer and is passed through untouched.
        """
        instrument = self._coerce_instrument(symbol)
        if not self._provider.supports_order_book:
            raise ProviderError(
                f"Provider '{self._provider.name}' does not provide "
                f"order-book data.",
                context={
                    "provider": self._provider.name,
                    "instrument": instrument.key,
                },
            )
        try:
            book = await self._provider.get_order_book(instrument, depth=depth)
        except (MarketDataError, InvalidSymbolError):
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Provider '{self._provider.name}' failed to return an order "
                f"book for {instrument.key}.",
                context={"symbol": instrument.symbol},
                cause=exc,
            ) from exc

        await self._emit_order_book(book)
        return book

    async def get_recent_trades(
        self, symbol: str | Instrument, *, limit: int = 50
    ) -> int:
        """
        Fetch recent executed-trade prints and publish one ``TradeReceived``
        event per print. Returns the number of prints announced.

        Raises a typed error when the provider cannot serve trades; an empty
        result is the provider's honest "no prints" and emits nothing.
        """
        instrument = self._coerce_instrument(symbol)
        if not self._provider.supports_trades:
            raise ProviderError(
                f"Provider '{self._provider.name}' does not provide "
                f"trade-tick data.",
                context={
                    "provider": self._provider.name,
                    "instrument": instrument.key,
                },
            )
        try:
            ticks = await self._provider.get_recent_trades(
                instrument, limit=limit
            )
        except (MarketDataError, InvalidSymbolError):
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Provider '{self._provider.name}' failed to return trades "
                f"for {instrument.key}.",
                context={"symbol": instrument.symbol},
                cause=exc,
            ) from exc

        await self._emit_trades(ticks)
        return len(ticks)

    # ------------------------------------------------------------------
    # Events (best-effort; delivery must never break the fetch)
    # ------------------------------------------------------------------

    async def _emit_order_book(self, book: OrderBook) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                OrderBookUpdated(
                    instrument_key=book.instrument.key,
                    bid_levels=len(book.bids),
                    ask_levels=len(book.asks),
                    best_bid=book.best_bid,
                    best_ask=book.best_ask,
                    mid_price=book.mid_price,
                    spread=book.spread,
                    book_timestamp=book.timestamp.isoformat(),
                    source_tier=book.provenance.tier.value,
                    is_mock=book.provenance.is_mock,
                )
            )
        except Exception:
            logger.exception("Failed to publish OrderBookUpdated")

    async def _emit_trades(self, ticks) -> None:
        if self._event_bus is None:
            return
        for tick in ticks:
            try:
                provenance = tick.provenance
                await self._event_bus.publish(
                    TradeReceived(
                        instrument_key=tick.instrument.key,
                        price=tick.price,
                        amount=tick.amount,
                        side=tick.side.value,
                        trade_timestamp=tick.timestamp.isoformat(),
                        tick_id=tick.tick_id or "",
                        source_tier=(
                            provenance.tier.value if provenance else ""
                        ),
                        is_mock=provenance.is_mock if provenance else False,
                    )
                )
            except Exception:
                logger.exception("Failed to publish TradeReceived")
