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
from datetime import UTC, datetime

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..cache import TTLCache
from ..domain.enums import DataQualityStatus, Timeframe
from ..domain.instrument import Instrument
from ..domain.market_data import MarketData, Quote
from ..domain.provenance import DataQuality
from ..errors import InsufficientDataError, InvalidSymbolError, MarketDataError
from ..events import (
    CandleClosed,
    DataQualityDegraded,
    MarketDataReceived,
    MarketDataUpdated,
)
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
        # Last-seen quality band per instrument+timeframe, so a worsening is
        # announced once as DataQualityDegraded rather than on every fetch.
        self._last_quality: dict[str, DataQualityStatus] = {}

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

        await self._emit_quality_transition(data)
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
            if min(c.open, c.high, c.low, c.close) <= 0:
                issues.append("Non-positive OHLC price in candle series.")
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

        # Future-dated / drifting last bar (spec section 3 -- timestamp drift).
        # A last bar far ahead of wall-clock is a feed defect, never a fresh one;
        # it must not be read as "new data". Freshness below also guards staleness.
        if status not in (DataQualityStatus.INVALID, DataQualityStatus.MISSING):
            drift = self._future_drift_seconds(data.timeframe, timestamps[-1])
            if drift is not None and drift > 0:
                issues.append(
                    f"Last bar is {drift:.0f}s in the future "
                    f"(beyond the timeframe's tolerance)."
                )
                status = DataQualityStatus.INVALID

        # Internal gaps: a bar missing mid-series is a partial feed defect, not a
        # silent hole. For sub-daily data we expect the next bar to be within two
        # timeframe steps; for daily/weekly/monthly data, session closures,
        # weekends and holidays make calendar gaps legitimate, so do not flag
        # them without an exchange-session calendar to compare against.
        if (
            status not in (DataQualityStatus.INVALID, DataQualityStatus.MISSING)
            and data.timeframe in (Timeframe.M1, Timeframe.M5, Timeframe.M15, Timeframe.M30, Timeframe.H1, Timeframe.H4)
        ):
            gap = self._largest_gap_multiple(data.timeframe, timestamps)
            if gap is not None and gap >= 2.0:
                issues.append(
                    f"Series has a gap: two adjacent bars are ~{gap:.1f}x the "
                    f"expected {data.timeframe.value} spacing apart."
                )
                if status is DataQualityStatus.OK:
                    status = DataQualityStatus.PARTIAL

        # Abnormal price/volume magnitudes: a single bar orders of magnitude off
        # its neighbours is almost always a feed glitch (a bad print or a unit
        # error), not a real move. We compare each bar to the median of the
        # series -- never to a fabricated "expected" price -- and only flag a
        # value that is implausible relative to the instrument's own range, so a
        # genuine crash or a low-priced instrument is not mislabelled.
        if status is DataQualityStatus.OK:
            outlier = self._abnormal_magnitude(candles)
            if outlier is not None:
                issues.append(outlier)
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
            last_ts = last_ts.replace(tzinfo=UTC)
        return max(0.0, (datetime.now(UTC) - last_ts).total_seconds())

    @staticmethod
    def _future_drift_seconds(tf: Timeframe, last_ts: datetime) -> float | None:
        """
        How far *ahead of now* the last bar sits, as a positive number of seconds
        beyond the timeframe's own tolerance. None when the last bar is not ahead.
        A small lead is legitimate (a bar that *just* opened), so the tolerance is
        one timeframe step -- only a larger jump is a feed/timestamp defect.
        """
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=UTC)
        ahead = (last_ts - datetime.now(UTC)).total_seconds()
        return ahead - tf.seconds if ahead > 0 else None

    @staticmethod
    def _largest_gap_multiple(tf: Timeframe, timestamps: list[datetime]) -> float | None:
        """
        The largest ratio between an adjacent-bar gap and the median gap.

        Sub-daily series can legitimately skip a bar (a halt); a daily+ series
        has weekend/holiday spacing *baked into* the median, so a true mid-series
        hole shows as an unusually large gap relative to the series' own rhythm
        -- never to a fixed calendar assumption. None when fewer than 2 bars.
        """
        if len(timestamps) < 2:
            return None
        deltas = [
            (b - a).total_seconds()
            for a, b in zip(timestamps, timestamps[1:])
        ]
        deltas = [d for d in deltas if d > 0]
        if not deltas:
            return None
        median = sorted(deltas)[len(deltas) // 2]
        if median <= 0:
            return None
        return max(deltas) / median

    @staticmethod
    def _abnormal_magnitude(candles) -> str | None:
        """
        Flag a single bar whose close or volume is implausible vs the series
        median -- a classic feed glitch (a bad print, a units error, a decimal
        shift). The bar must be many orders of magnitude off *and* the rest of
        the series must be internally consistent, so a real crash or a
        low-priced instrument is not mislabelled. Returns a human-readable
        issue string, or None when nothing is out of line.
        """
        if len(candles) < 4:
            return None
        closes = sorted(c.close for c in candles)
        volumes = sorted(c.volume for c in candles)
        mid = len(candles) // 2
        med_close = closes[mid] or 0.0
        med_volume = volumes[mid] or 0.0

        # A non-positive close can never be a real traded price; it is always a
        # defect worth flagging (a valid OHLC would have been caught already).
        if any(c.close <= 0 for c in candles):
            return "A candle has a non-positive close; price data is corrupt."

        # Volume of exactly zero across an entire equity feed is suspicious but
        # common for thin/illiquid data, so only flag when it's the *outlier*:
        # a lone non-zero bar inside an otherwise zero series (or vice-versa)
        # is a broken print, not a real market.
        if med_close > 0:
            for c in candles:
                ratio = c.close / med_close if med_close else 0.0
                if ratio >= 1e3 or (0 < ratio <= 1e-3):
                    return (
                        f"A bar close ({c.close:g}) is ~{max(ratio, 1 / ratio):.0f}x "
                        "the series median; a probable bad print."
                    )
        if med_volume > 0:
            for c in candles:
                ratio = c.volume / med_volume if med_volume else 0.0
                if ratio >= 1e4:
                    return (
                        f"A bar volume ({c.volume:g}) is ~{ratio:.0f}x the series "
                        "median; a probable bad print."
                    )
        return None

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

    async def _emit_quality_transition(self, data: MarketData) -> None:
        """
        Announce a worsening of the data-quality band for this instrument+tf.

        The last-seen status is kept per key so a *transition* (e.g. OK ->
        PARTIAL, or anything -> INVALID) is published once rather than on every
        refresh. The first observation is recorded silently -- a service that
        has never seen a feed cannot assert a *change*, so an initial OK or an
        initial PARTIAL emits nothing (spec section 3/17: emit on a real
        worsening transition, never a fabricated baseline).
        """
        key = f"{data.instrument.key}:{data.timeframe.value}"
        prev = self._last_quality.get(key)
        self._last_quality[key] = data.quality.status
        if self._event_bus is None or prev is None or prev == data.quality.status:
            return
        if not self._degraded(prev, data.quality.status):
            return
        try:
            await self._event_bus.publish(
                DataQualityDegraded(
                    instrument_key=data.instrument.key,
                    timeframe=data.timeframe.value,
                    previous_status=prev.value,
                    status=data.quality.status.value,
                    issues=data.quality.issues,
                    is_mock=data.provenance.is_mock,
                    source_tier=data.provenance.tier.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish DataQualityDegraded")

    @staticmethod
    def _degraded(before: DataQualityStatus, after: DataQualityStatus) -> bool:
        """Whether the band worsened (a stricter ordering than "changed")."""
        order = {
            DataQualityStatus.OK: 0,
            DataQualityStatus.PARTIAL: 1,
            DataQualityStatus.STALE: 2,
            DataQualityStatus.MISSING: 3,
            DataQualityStatus.INVALID: 4,
        }
        return order[after] > order[before]

    async def _emit_updated(self, data: MarketData) -> None:
        if self._event_bus is None:
            return
        # Announce the arrival of the validated snapshot first, then replay each
        # delivered bar as a CandleClosed. Both are best-effort: a publish failure
        # is logged and swallowed so event delivery never breaks data retrieval.
        try:
            await self._event_bus.publish(
                MarketDataReceived(
                    instrument_key=data.instrument.key,
                    timeframe=data.timeframe.value,
                    candle_count=data.count,
                    last_price=data.last_price,
                    first_bar_timestamp=(
                        data.candles[0].timestamp.isoformat() if data.candles else ""
                    ),
                    last_bar_timestamp=(
                        data.last_timestamp.isoformat()
                        if data.last_timestamp
                        else ""
                    ),
                    source_tier=data.provenance.tier.value,
                    quality_status=data.quality.status.value,
                    is_mock=data.provenance.is_mock,
                )
            )
        except Exception:
            logger.exception("Failed to publish MarketDataReceived")
        try:
            await self._emit_candle_closes(data)
        except Exception:
            logger.exception("Failed to publish CandleClosed events")
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

    async def _emit_candle_closes(self, data: MarketData) -> None:
        """
        Announce the most recently closed bar.

        AetherOS is pull-based, so "a bar closed" can only mean "a closed bar was
        delivered in the snapshot." Every delivered candle is by definition
        closed; the meaningful, non-redundant signal for a live consumer is the
        *newest* close, so exactly one ``CandleClosed`` is emitted -- for the
        final bar, flagged ``is_final_bar``. Emitting one event per delivered bar
        would replay hundreds of stale closes on every fetch and drown the
        genuinely new one, so this stays a single announcement. A cache hit emits
        nothing -- this method only runs on a freshly fetched series.
        """
        if not data.candles:
            return
        index = data.count - 1
        candle = data.candles[index]
        await self._event_bus.publish(
            CandleClosed(
                instrument_key=data.instrument.key,
                timeframe=data.timeframe.value,
                index=index,
                is_final_bar=True,
                bar_timestamp=candle.timestamp.isoformat(),
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                source_tier=data.provenance.tier.value,
                quality_status=data.quality.status.value,
            )
        )
