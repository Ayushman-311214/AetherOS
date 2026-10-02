"""
Yahoo Finance market-data provider.

The first *real* market-data source in AetherOS. It reads OHLCV candles and
quotes from Yahoo's public chart endpoint over HTTPS, behind the same
:class:`MarketDataProvider` interface the mock uses, so the analysis, risk,
backtest, critic and orchestration layers work unchanged -- but now on real
prices rather than a synthetic random walk (spec sections 1, 9, 30: reliable
market data is priority #1). Because the data is real and non-mock
(``SourceTier.SECONDARY``), an analysis built on it can finally be *actionable*.

Honesty guarantees (spec sections 9, 20, 53, 61):

* It is ``SourceTier.SECONDARY``, never PRIMARY: Yahoo is a free, aggregated,
  possibly-delayed feed, not the authoritative exchange tape, and the tier says
  so. It is never ``MOCK`` -- these are real numbers.
* It **never fabricates**. Any failure -- network error, non-200 response, an
  error object in the payload, or a response with no usable bars -- raises a
  typed :class:`ProviderError` / :class:`InsufficientDataError`. It does not
  fall back to synthetic data or a previous result.
* It does not stamp freshness/validity optimistically: it returns the bars as
  read and lets :class:`MarketDataService` re-derive DataQuality (staleness,
  partiality, OHLC sanity) independently.

Timeframes: Yahoo supports 1m/5m/15m/30m/1h/1d/1wk. AetherOS's 4h bar has no
native Yahoo interval, so it is rejected with a clear error rather than being
silently resampled.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from ..domain.enums import DataQualityStatus, SourceTier, Timeframe
from ..domain.instrument import Instrument
from ..domain.market_data import Candle, MarketData, Quote
from ..domain.provenance import DataQuality, Provenance
from ..errors import InsufficientDataError, ProviderError
from .base import MarketDataProvider

_DEFAULT_BASE_URL = "https://query1.finance.yahoo.com"

# A browser-like User-Agent: the public endpoint rejects some default clients.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# AetherOS timeframe -> Yahoo `interval`. 4h has no native Yahoo interval and is
# deliberately absent: we reject it rather than fabricate it by resampling.
_YAHOO_INTERVAL: dict[Timeframe, str] = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.D1: "1d",
    Timeframe.W1: "1wk",
}

# Extra lookback factor when requesting `period1..period2`, to cover non-trading
# time (weekends/holidays for daily+, overnight gaps for intraday) so we still
# get close to `limit` real bars back. Over-fetching is safe: we trim to the
# most-recent `limit`.
_LOOKBACK_FACTOR: dict[Timeframe, float] = {
    Timeframe.M1: 3.0,
    Timeframe.M5: 3.0,
    Timeframe.M15: 3.0,
    Timeframe.M30: 3.0,
    Timeframe.H1: 3.0,
    Timeframe.D1: 2.0,
    Timeframe.W1: 1.6,
}

# Exchange -> Yahoo symbol suffix. US exchanges use the bare ticker; others take
# a suffix (RELIANCE + NSE -> RELIANCE.NS). An unknown exchange falls back to the
# bare symbol rather than guessing a suffix that would query the wrong listing.
_EXCHANGE_SUFFIX: dict[str, str] = {
    "NSE": ".NS",
    "BSE": ".BO",
    "NASDAQ": "",
    "NYSE": "",
    "AMEX": "",
    "ARCA": "",
    "LSE": ".L",
    "TSX": ".TO",
    "HKEX": ".HK",
    "FRA": ".F",
}


class YahooMarketDataProvider(MarketDataProvider):
    """Real OHLCV candles and quotes from Yahoo's public chart endpoint."""

    name = "yahoo"
    tier = SourceTier.SECONDARY

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ) -> None:
        # An injected client (owned by the caller) makes this provider testable
        # with httpx.MockTransport and lets a host share one connection pool. If
        # none is given we open and close a client per request.
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Symbol / timeframe mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _yahoo_symbol(instrument: Instrument) -> str:
        suffix = ""
        if instrument.exchange:
            suffix = _EXCHANGE_SUFFIX.get(instrument.exchange, "")
        return f"{instrument.symbol}{suffix}"

    @classmethod
    def _interval(cls, timeframe: Timeframe) -> str:
        try:
            return _YAHOO_INTERVAL[timeframe]
        except KeyError:
            raise ProviderError(
                f"Timeframe '{timeframe.value}' is not supported by the Yahoo "
                f"provider (no native interval). Supported: "
                f"{', '.join(t.value for t in _YAHOO_INTERVAL)}.",
                context={"timeframe": timeframe.value},
            ) from None

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def _fetch_chart(self, symbol: str, params: dict[str, object]) -> dict:
        url = f"{self._base_url}/v8/finance/chart/{symbol}"
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.get(url, params=params, headers=_HEADERS)
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Yahoo request failed for '{symbol}': {exc}",
                context={"symbol": symbol},
                cause=exc,
            ) from exc
        finally:
            if self._client is None:
                await client.aclose()

        if resp.status_code != 200:
            raise ProviderError(
                f"Yahoo returned HTTP {resp.status_code} for '{symbol}'.",
                context={"symbol": symbol, "status": resp.status_code},
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ProviderError(
                f"Yahoo returned a non-JSON response for '{symbol}'.",
                context={"symbol": symbol},
                cause=exc,
            ) from exc

        chart = payload.get("chart") if isinstance(payload, dict) else None
        if not isinstance(chart, dict):
            raise ProviderError(
                f"Unexpected Yahoo payload shape for '{symbol}'.",
                context={"symbol": symbol},
            )
        error = chart.get("error")
        if error:
            desc = error.get("description") if isinstance(error, dict) else error
            raise ProviderError(
                f"Yahoo reported an error for '{symbol}': {desc}",
                context={"symbol": symbol},
            )
        results = chart.get("result")
        if not results:
            raise InsufficientDataError(
                f"Yahoo returned no chart data for '{symbol}'.",
                context={"symbol": symbol},
            )
        print("Yahoo chart result for -----------> ", symbol, ":", results[0])
        return results[0]

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_candles(result: dict) -> list[Candle]:
        """
        Build candles from a Yahoo chart result, dropping any bar with a null
        OHLC field (Yahoo commonly emits a trailing all-null bar for the current
        in-progress period). Never invents a value to fill a gap.
        """
        timestamps = result.get("timestamp") or []
        quote_blocks = (result.get("indicators") or {}).get("quote") or [{}]
        quote = quote_blocks[0] if quote_blocks else {}
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        candles: list[Candle] = []
        for i, ts in enumerate(timestamps):
            try:
                o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            except IndexError:
                break
            if None in (o, h, l, c) or ts is None:
                continue
            v = volumes[i] if i < len(volumes) and volumes[i] is not None else 0.0
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(int(ts), tz=timezone.utc),
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v),
                )
            )
        candles.sort(key=lambda cd: cd.timestamp)
        return candles

    @staticmethod
    def _detail(result: dict) -> str:
        meta = result.get("meta") or {}
        exchange = meta.get("exchangeName") or "?"
        currency = meta.get("currency") or "?"
        return f"Yahoo Finance chart ({exchange}, {currency})"

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
        interval = self._interval(timeframe)
        symbol = self._yahoo_symbol(instrument)

        now = int(time.time())
        factor = _LOOKBACK_FACTOR.get(timeframe, 2.0)
        span = int(timeframe.seconds * limit * factor)
        params: dict[str, object] = {
            "interval": interval,
            "period1": now - span,
            "period2": now,
            "includePrePost": "false",
            "events": "div,splits",
        }

        result = await self._fetch_chart(symbol, params)
        candles = self._parse_candles(result)
        if not candles:
            raise InsufficientDataError(
                f"Yahoo returned no usable candles for '{symbol}' "
                f"[{timeframe.value}].",
                context={"symbol": symbol, "timeframe": timeframe.value},
            )
        # Trim to the most-recent `limit` bars (we deliberately over-fetched).
        candles = candles[-limit:]

        return MarketData(
            instrument=instrument,
            timeframe=timeframe,
            candles=tuple(candles),
            provenance=Provenance(
                source=self.name,
                tier=self.tier,
                detail=self._detail(result),
            ),
            # Report the read as OK; MarketDataService independently re-derives
            # staleness, partiality and OHLC sanity from the actual bars.
            quality=DataQuality(status=DataQualityStatus.OK),
        )

    async def get_quote(self, instrument: Instrument) -> Quote:
        # Reuse the daily series so the quote and candles are mutually consistent
        # and share one code path. The last close is the latest available price.
        data = await self.get_candles(instrument, Timeframe.D1, limit=2)
        last = data.candles[-1]
        prev = data.candles[-2] if len(data.candles) >= 2 else None
        change_pct = (
            (last.close / prev.close - 1.0) * 100.0
            if prev is not None and prev.close
            else None
        )
        return Quote(
            instrument=instrument,
            price=last.close,
            timestamp=last.timestamp,
            provenance=Provenance(
                source=self.name,
                tier=self.tier,
                detail="Yahoo Finance latest close",
            ),
            volume=last.volume,
            change_pct=change_pct,
        )


