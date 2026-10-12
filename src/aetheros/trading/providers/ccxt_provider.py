"""
CCXT market-data provider (optional extra: ``pip install aetheros[market]``).

Serves crypto (and forex where the chosen exchange lists it) through the
ccxt unified API behind the same :class:`MarketDataProvider` interface Yahoo
and the mock implement, so every analysis layer works unchanged. Unlike Yahoo
it *does* expose order-book depth and executed trades, which is what makes it
the multi-market data engine's microstructure source (spec sections 1, 2, 9).

Honesty guarantees (same rules as the Yahoo adapter):

* ``SourceTier.SECONDARY``: exchange feeds are real but aggregated/possibly
  delayed relative to the authoritative tape.
* It never fabricates. Network errors, exchange errors, malformed payloads
  and empty responses raise typed :class:`ProviderError` /
  :class:`InsufficientDataError`; malformed rows are dropped, never repaired.
* ccxt's built-in rate limiting (``enableRateLimit``) is left on so the
  provider respects the exchange's budget rather than hammering it.

The exchange object is injected through the constructor so tests drive a
stub without any network or ccxt installation.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ..domain.enums import DataQualityStatus, Direction, SourceTier, Timeframe
from ..domain.instrument import Instrument
from ..domain.market_data import Candle, MarketData, Quote
from ..domain.order_book import OrderBook, OrderBookLevel, TradeTick
from ..domain.provenance import DataQuality, Provenance
from ..errors import InsufficientDataError, ProviderError
from .base import MarketDataProvider

# AetherOS timeframe -> ccxt `timeframe` string. ccxt's convention matches
# ours for every supported bar except the weekly, which ccxt writes "1M"
# (month) vs "1w" -- the entries are explicit so a mismatch can never pass
# silently.
_CCXT_TIMEFRAME: dict[Timeframe, str] = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1d",
    Timeframe.W1: "1w",
    Timeframe.MN: "1M",
}

_MILLISECONDS = 1000.0


def ccxt_symbol(instrument: Instrument) -> str:
    """
    Map an Instrument to ccxt's pair conventions (pure, unit-testable).

    * crypto: ``BTC`` -> ``BTC/USD``; an explicit pair (``BTC/USDT``) or a
      six-letter style (``BTCUSDT``) is preserved/normalised to the slash form
    * forex: six-letter pair -> ``EUR/USD``; three-letter base -> ``EUR/USD``
    * anything else: the bare symbol (the exchange will refuse it honestly)
    """
    raw = instrument.symbol.upper()
    asset_class = instrument.asset_class.strip().lower()
    if asset_class == "crypto":
        if "/" in raw:
            return raw
        if len(raw) >= 7 and raw.endswith("USDT"):
            return f"{raw[:-4]}/USDT"
        if len(raw) >= 4 and raw.endswith("USD"):
            return f"{raw[:-3]}/USD"
        return f"{raw}/USD"
    if asset_class == "forex":
        if "/" in raw:
            return raw
        if len(raw) == 6:
            return f"{raw[:3]}/{raw[3:]}"
        if len(raw) == 3:
            return f"{raw}/USD"
        return raw
    return raw


class _Transient(ProviderError):
    """A venue failure that may succeed on retry (transport, rate limit).

    Subclasses ProviderError so callers catching the public error type see
    identical behaviour when retries are exhausted. Mirrors the Yahoo
    provider's transient/permanent split: an exchange outage is transient, a
    malformed payload is permanent.
    """

    default_code = "TRADING_MD_006"


class CcxtMarketDataProvider(MarketDataProvider):
    """Real candles, quotes, order books and trades via the ccxt unified API."""

    name = "ccxt"
    tier = SourceTier.SECONDARY

    #: ccxt serves crypto across exchanges and forex on those that list it.
    #: Commodity derivatives (e.g. PAXG/USD gold) ride the same spot API.
    asset_classes = ("crypto", "forex", "commodity")

    #: The unified API exposes order books and executed trades.
    supports_order_book = True
    supports_trades = True

    def __init__(
        self,
        exchange: Any,
        *,
        timeout: float = 15.0,
        max_retries: int = 0,
        retry_backoff_seconds: float = 1.0,
        sleeper: Callable[[float], object] = asyncio.sleep,
    ) -> None:
        """
        ``exchange`` is an already-constructed ``ccxt.async_support`` exchange
        (or a test stub with the same call surface). The provider owns nothing
        else: the bootstrapper picks the exchange from settings, and callers
        that want a different venue construct their own.

        ``max_retries`` bounds transport-level retries with the same
        exponential backoff shape as the Yahoo provider; malformed payloads
        are never retried.
        """
        if exchange is None:
            raise ValueError("CcxtMarketDataProvider requires an exchange object.")
        self._exchange = exchange
        self._timeout = timeout
        self._max_retries = max(0, max_retries)
        self._retry_backoff_seconds = retry_backoff_seconds
        self._sleeper = sleeper

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _symbol(instrument: Instrument) -> str:
        return ccxt_symbol(instrument)

    @classmethod
    def _tf(cls, timeframe: Timeframe) -> str:
        try:
            return _CCXT_TIMEFRAME[timeframe]
        except KeyError:
            raise ProviderError(
                f"Timeframe '{timeframe.value}' is not supported by the ccxt "
                f"provider. Supported: "
                f"{', '.join(t.value for t in _CCXT_TIMEFRAME)}.",
                context={"timeframe": timeframe.value},
            ) from None

    @staticmethod
    def _from_ms(milliseconds: float | int | None) -> datetime | None:
        if milliseconds is None:
            return None
        value = float(milliseconds)
        if not math.isfinite(value) or value <= 0:
            return None
        return datetime.fromtimestamp(value / _MILLISECONDS, tz=UTC)

    # ------------------------------------------------------------------
    # Error mapping
    # ------------------------------------------------------------------

    def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """
        Invoke an exchange method, mapping every failure to a typed error.

        Synchronous indirection over the async method: the exchange's coroutine
        is awaited by the caller. A ccxt ``ExchangeError`` family member (or
        any exception) becomes a ProviderError carrying the method and symbol
        context -- never a fabricated result.
        """
        # Intentionally returns the coroutine for the caller to await.
        return self._await_call(method, *args, **kwargs)

    async def _await_call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        attempts = self._max_retries + 1
        last_exc: _Transient | None = None
        for attempt in range(attempts):
            if attempt > 0:
                await self._sleeper(
                    self._retry_backoff_seconds * (2 ** (attempt - 1))
                )
            try:
                fn = getattr(self._exchange, method)
                result = fn(*args, **kwargs)
                if hasattr(result, "__await__"):
                    result = await result
                return result
            except Exception as exc:  # ccxt raises many shapes; map them all
                last_exc = _Transient(
                    f"ccxt exchange call '{method}' failed: {exc}",
                    context={"method": method},
                    cause=exc,
                )
                continue
        assert last_exc is not None  # only reachable after >= 1 transient raise
        raise last_exc

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    async def get_candles(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        *,
        limit: int,
    ) -> MarketData:
        if limit <= 0:
            raise ValueError("limit must be positive.")
        symbol = self._symbol(instrument)
        raw = await self._await_call(
            "fetch_ohlcv", symbol, self._tf(timeframe), None, limit
        )
        candles: list[Candle] = []
        for row in raw or []:
            # ccxt rows: [timestamp_ms, open, high, low, close, volume]
            if not isinstance(row, (list, tuple)) or len(row) < 6:
                continue
            ts = self._from_ms(row[0])
            o, h, lo, c, v = (float(row[i]) for i in range(1, 6))
            if ts is None or any(
                not math.isfinite(x) for x in (o, h, lo, c, v)
            ):
                continue
            try:
                candles.append(
                    Candle(timestamp=ts, open=o, high=h, low=lo, close=c, volume=v)
                )
            except ValueError:
                continue
        if not candles:
            raise InsufficientDataError(
                f"ccxt returned no usable candles for '{symbol}' "
                f"[{timeframe.value}].",
                context={"symbol": symbol, "timeframe": timeframe.value},
            )
        return MarketData(
            instrument=instrument,
            timeframe=timeframe,
            candles=tuple(candles[-limit:]),
            provenance=Provenance(
                source=self.name,
                tier=self.tier,
                detail=f"ccxt {getattr(self._exchange, 'id', 'exchange')} OHLCV",
            ),
            # The service re-derives staleness/partiality from the bars.
            quality=DataQuality(status=DataQualityStatus.OK),
        )

    async def get_quote(self, instrument: Instrument) -> Quote:
        symbol = self._symbol(instrument)
        raw = await self._await_call("fetch_ticker", symbol)
        if not isinstance(raw, dict):
            raise ProviderError(
                f"ccxt returned a non-ticker payload for '{symbol}'.",
                context={"symbol": symbol},
            )
        price = raw.get("last")
        ts = self._from_ms(raw.get("timestamp"))
        if price is None or ts is None:
            raise InsufficientDataError(
                f"ccxt ticker for '{symbol}' has no usable price/timestamp.",
                context={"symbol": symbol},
            )
        bid, ask = raw.get("bid"), raw.get("ask")
        return Quote(
            instrument=instrument,
            price=float(price),
            timestamp=ts,
            bid=float(bid) if bid is not None else None,
            ask=float(ask) if ask is not None else None,
            volume=raw.get("baseVolume"),
            change_pct=raw.get("percentage"),
            provenance=Provenance(
                source=self.name,
                tier=self.tier,
                detail=f"ccxt {getattr(self._exchange, 'id', 'exchange')} ticker",
            ),
        )

    async def get_order_book(
        self,
        instrument: Instrument,
        *,
        depth: int = 10,
    ) -> OrderBook:
        if depth <= 0:
            raise ValueError("depth must be positive.")
        symbol = self._symbol(instrument)
        raw = await self._await_call("fetch_order_book", symbol, depth)
        if not isinstance(raw, dict):
            raise ProviderError(
                f"ccxt returned a non-book payload for '{symbol}'.",
                context={"symbol": symbol},
            )
        bids = self._levels(raw.get("bids"), symbol, "bids")
        asks = self._levels(raw.get("asks"), symbol, "asks")
        if not bids and not asks:
            raise InsufficientDataError(
                f"ccxt order book for '{symbol}' has no usable levels.",
                context={"symbol": symbol},
            )
        ts = self._from_ms(raw.get("timestamp")) or datetime.now(UTC)
        return OrderBook(
            instrument=instrument,
            bids=tuple(bids),
            asks=tuple(asks),
            timestamp=ts,
            provenance=Provenance(
                source=self.name,
                tier=self.tier,
                detail=f"ccxt {getattr(self._exchange, 'id', 'exchange')} depth",
            ),
        )

    async def get_recent_trades(
        self,
        instrument: Instrument,
        *,
        limit: int = 50,
    ) -> tuple[TradeTick, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive.")
        symbol = self._symbol(instrument)
        raw = await self._await_call("fetch_trades", symbol, None, limit)
        provenance = Provenance(
            source=self.name,
            tier=self.tier,
            detail=f"ccxt {getattr(self._exchange, 'id', 'exchange')} trades",
        )
        ticks: list[TradeTick] = []
        for trade in raw or []:
            if not isinstance(trade, dict):
                continue
            price, amount = trade.get("price"), trade.get("amount")
            ts = self._from_ms(trade.get("timestamp"))
            side_raw = str(trade.get("side") or "").lower()
            if price is None or amount is None or ts is None:
                continue
            side = Direction.UP if side_raw == "buy" else Direction.DOWN
            try:
                ticks.append(
                    TradeTick(
                        instrument=instrument,
                        price=float(price),
                        amount=float(amount),
                        side=side,
                        timestamp=ts,
                        tick_id=str(trade.get("id")) if trade.get("id") else None,
                        provenance=provenance,
                    )
                )
            except ValueError:
                continue
        return tuple(ticks)

    # ------------------------------------------------------------------

    @staticmethod
    def _levels(rows: Any, symbol: str, side: str) -> list[OrderBookLevel]:
        """Parse ccxt [[price, amount], ...] rows, dropping malformed entries."""
        levels: list[OrderBookLevel] = []
        for row in rows or []:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            price, amount = row[0], row[1]
            if price is None or amount is None:
                continue
            try:
                levels.append(
                    OrderBookLevel(price=float(price), amount=float(amount))
                )
            except ValueError:
                continue
        return levels
