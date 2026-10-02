"""
Market-data service.

Sits between the analysis layers and a MarketDataProvider. Its responsibilities
are exactly the honest-data concerns the spec insists on (CLAUDE.md sections 9,
24, 47):

- fetch candles/quotes through the injected provider (never a hard-coded one),
- cache results briefly to avoid hammering a source, while tracking each
  entry's age so freshness is real, not assumed,
- validate the returned series (monotonic timestamps, sane OHLC, no NaNs) and
  downgrade DataQuality rather than passing bad bars downstream,
- flag a series as STALE when its last bar is older than the timeframe allows,
  instead of silently presenting old data as current,
- translate provider failures into typed MarketDataError / InsufficientDataError,
- publish MarketDataUpdated so other subsystems can react.

It performs no interpretation -- that is the technical/structure/evidence
services' job.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..cache import TTLCache
from ..domain.enums import DataQualityStatus, Timeframe
from ..domain.instrument import Instrument
from ..domain.market_data import MarketData, Quote
from ..domain.provenance import DataQuality
from ..errors import InsufficientDataError, InvalidSymbolError, MarketDataError
from ..events import MarketDataUpdated
from ..providers.base import MarketDataProvider

logger = get_logger("trading.market_data")


class MarketDataService:
    """Caching, validation and freshness gateway to a market-data provider."""

    def __init__(
        self,
        provider: MarketDataProvider,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._event_bus = event_bus
        self._quote_cache: TTLCache[Quote] = TTLCache(
            default_ttl=settings.TRADING_CACHE_TTL_QUOTE
        )
        self._candle_cache: TTLCache[MarketData] = TTLCache(
            default_ttl=settings.TRADING_CACHE_TTL_CANDLES
        )

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def is_mock(self) -> bool:
        return self._provider.is_mock

    # ------------------------------------------------------------------
    # Candles
    # ------------------------------------------------------------------

    async def get_candles(
        self,
        symbol: str | Instrument,
        timeframe: str | Timeframe | None = None,
        *,
        limit: int | None = None,
    ) -> MarketData:
        instrument = self._coerce_instrument(symbol)
        tf = self._coerce_timeframe(timeframe)
        n = self._coerce_limit(limit)

        cache_key = f"candles:{instrument.key}:{tf.value}:{n}"
        cached = self._candle_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._provider.get_candles(instrument, tf, limit=n)
        except (MarketDataError, InsufficientDataError, InvalidSymbolError):
            raise
        except Exception as exc:  # provider misbehaved -> typed, honest error
            raise MarketDataError(
                f"Provider '{self._provider.name}' failed to return candles "
                f"for {instrument.key} [{tf.value}].",
                context={"symbol": instrument.symbol, "timeframe": tf.value},
                cause=exc,
            ) from exc

        data = self._assess_quality(data, requested=n)
        self._candle_cache.set(cache_key, data)

        await self._emit_updated(data)
        return data

    async def get_quote(self, symbol: str | Instrument) -> Quote:
        instrument = self._coerce_instrument(symbol)
        cache_key = f"quote:{instrument.key}"
        cached = self._quote_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            quote = await self._provider.get_quote(instrument)
        except (MarketDataError, InvalidSymbolError):
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Provider '{self._provider.name}' failed to return a quote "
                f"for {instrument.key}.",
                context={"symbol": instrument.symbol},
                cause=exc,
            ) from exc

        self._quote_cache.set(cache_key, quote)
        return quote

    # ------------------------------------------------------------------
    # Validation & quality
    # ------------------------------------------------------------------

    def _assess_quality(self, data: MarketData, *, requested: int) -> MarketData:
        """
        Re-derive DataQuality from the actual candles.

        The provider supplies an initial read (e.g. MOCK marks itself); this
        layer adds structural validation and freshness independent of the
        provider's own optimism.
        """
        issues: list[str] = list(data.quality.issues)
        status = data.quality.status

        candles = data.candles
        if not candles:
            issues.append("No candles returned.")
            return self._with_quality(
                data, DataQualityStatus.MISSING, issues, freshness=None
            )

        # Structural validation.
        for c in candles:
            values = (c.open, c.high, c.low, c.close, c.volume)
            if any(v is None or math.isnan(v) or math.isinf(v) for v in values):
                issues.append("Non-finite value in candle series.")
                status = DataQualityStatus.INVALID
                break
            if c.high < c.low or c.high < c.open or c.high < c.close:
                issues.append("Inconsistent OHLC (high below other prices).")
                status = DataQualityStatus.INVALID
                break
            if c.low > c.open or c.low > c.close:
                issues.append("Inconsistent OHLC (low above other prices).")
                status = DataQualityStatus.INVALID
                break
            if c.volume < 0:
                issues.append("Negative volume in candle series.")
                status = DataQualityStatus.INVALID
                break

        # Monotonic, strictly increasing timestamps.
        timestamps = [c.timestamp for c in candles]
        if any(b <= a for a, b in zip(timestamps, timestamps[1:])):
            issues.append("Candle timestamps are not strictly increasing.")
            if status not in (DataQualityStatus.INVALID,):
                status = DataQualityStatus.INVALID

        # Partial series.
        if status not in (DataQualityStatus.INVALID,) and len(candles) < requested:
            issues.append(
                f"Requested {requested} candles, received {len(candles)}."
            )
            if status == DataQualityStatus.OK:
                status = DataQualityStatus.PARTIAL

        # Freshness.
        freshness = self._freshness_seconds(data.timeframe, timestamps[-1])
        if status not in (DataQualityStatus.INVALID, DataQualityStatus.MISSING):
            allowed = data.timeframe.seconds * self._settings.TRADING_STALE_MULTIPLIER
            if freshness is not None and freshness > allowed:
                issues.append(
                    f"Last bar is {freshness:.0f}s old "
                    f"(> {allowed:.0f}s allowed for {data.timeframe.value})."
                )
                if status in (DataQualityStatus.OK, DataQualityStatus.PARTIAL):
                    status = DataQualityStatus.STALE

        return self._with_quality(data, status, issues, freshness=freshness)

    @staticmethod
    def _freshness_seconds(tf: Timeframe, last_ts: datetime) -> float | None:
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - last_ts).total_seconds())

    @staticmethod
    def _with_quality(
        data: MarketData,
        status: DataQualityStatus,
        issues: list[str],
        *,
        freshness: float | None,
    ) -> MarketData:
        # De-duplicate issues while preserving order.
        seen: set[str] = set()
        unique = tuple(i for i in issues if not (i in seen or seen.add(i)))
        quality = DataQuality(
            status=status, issues=unique, freshness_seconds=freshness
        )
        # MarketData is frozen; rebuild with the reassessed quality.
        return MarketData(
            instrument=data.instrument,
            timeframe=data.timeframe,
            candles=data.candles,
            provenance=data.provenance,
            quality=quality,
            retrieved_at=data.retrieved_at,
        )

    # ------------------------------------------------------------------
    # Coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_instrument(symbol: str | Instrument) -> Instrument:
        if isinstance(symbol, Instrument):
            return symbol
        try:
            return Instrument.parse(symbol)
        except ValueError as exc:
            raise InvalidSymbolError(str(exc), context={"symbol": symbol}) from exc

    def _coerce_timeframe(self, timeframe: str | Timeframe | None) -> Timeframe:
        if isinstance(timeframe, Timeframe):
            return timeframe
        raw = timeframe or self._settings.TRADING_DEFAULT_TIMEFRAME
        try:
            return Timeframe.parse(raw)
        except ValueError as exc:
            raise MarketDataError(
                str(exc), context={"timeframe": raw}
            ) from exc

    def _coerce_limit(self, limit: int | None) -> int:
        if limit is None:
            return self._settings.TRADING_MAX_CANDLES
        if limit <= 0:
            raise MarketDataError(
                "limit must be a positive integer.", context={"limit": limit}
            )
        return min(limit, self._settings.TRADING_MAX_CANDLES)

    async def _emit_updated(self, data: MarketData) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                MarketDataUpdated(
                    instrument_key=data.instrument.key,
                    timeframe=data.timeframe.value,
                    candle_count=data.count,
                    last_price=data.last_price,
                    source_tier=data.provenance.tier.value,
                    quality_status=data.quality.status.value,
                )
            )
        except Exception:  # event delivery must never break data retrieval
            logger.exception("Failed to publish MarketDataUpdated")
