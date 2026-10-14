"""
Market-regime service.

Classifies the *character* of the market for one instrument -- trending, ranging
or volatile -- from deterministic indicator maths (ADX for trend strength, ATR
as a fraction of price for realised volatility). No LLM and no I/O beyond the
candle series it is handed; identical candles always yield the identical regime
(CLAUDE.md sections 5, 22).

The read is honest about its own reliability: mock, unusable or too-thin data
produces ``MarketRegime.UNKNOWN`` (or, for mock, a labelled-but-unreliable read)
with the reason recorded in ``limitations`` rather than a fabricated regime
(sections 9, 28). When an EventBus is wired it emits a ``MarketRegimeDetected``
event; a publish failure is logged and swallowed so it never sinks the read.
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import Confidence, MarketRegime
from ..domain.market_data import MarketData
from ..domain.regime import RegimeAnalysis
from ..events import MarketRegimeDetected
from ..indicators.core import adx as adx_indicator
from ..indicators.core import atr as atr_indicator
from ..indicators.core import last_finite, volatility

logger = get_logger("trading.regime")


class RegimeService:
    """Deterministic trending / ranging / volatile classification over candles."""

    def __init__(
        self, settings: Settings, *, event_bus: EventBus | None = None
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus

    async def detect(self, data: MarketData) -> RegimeAnalysis:
        result = self._detect(data)
        await self._emit(result)
        return result

    # ------------------------------------------------------------------

    def _detect(self, data: MarketData) -> RegimeAnalysis:
        period = self._settings.TRADING_REGIME_PERIOD
        min_bars = self._settings.TRADING_REGIME_MIN_BARS
        adx_trend = self._settings.TRADING_REGIME_ADX_TREND
        vol_high = self._settings.TRADING_REGIME_VOL_HIGH_PCT

        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append(
                "Regime derived from MOCK data; classification is illustrative, "
                "not a real market read."
            )
        if not data.quality.ok:
            limitations.extend(data.quality.issues)

        n = len(data.candles)
        # Guard: without usable, sufficiently long data no honest regime exists.
        if not data.quality.usable or n < min_bars:
            if n < min_bars:
                limitations.append(
                    f"Only {n} candles; need at least {min_bars} for a regime read."
                )
            return self._unknown(data, limitations)

        closes = data.closes()
        highs = data.highs()
        lows = data.lows()

        adx_val = last_finite(adx_indicator(highs, lows, closes, period=period))
        atr_val = last_finite(atr_indicator(highs, lows, closes, period=period))
        last_price = float(closes[-1])
        realized = last_finite(volatility(closes, period=min(period, n - 1)))

        if adx_val is None or atr_val is None or last_price <= 0:
            limitations.append(
                "Trend-strength / volatility indicators did not warm up on this "
                "series; regime undetermined."
            )
            return self._unknown(data, limitations)

        atr_pct = atr_val / last_price
        trend_strength = min(1.0, adx_val / 100.0)
        regime, confidence, observation = self._classify(
            adx_val=adx_val,
            atr_pct=atr_pct,
            closes=closes,
            adx_trend=adx_trend,
            vol_high=vol_high,
            period=period,
        )

        return RegimeAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            regime=regime,
            adx=round(adx_val, 3),
            trend_strength=round(trend_strength, 3),
            atr_pct=round(atr_pct, 6),
            realized_volatility=(
                round(realized, 6) if realized is not None else None
            ),
            confidence=confidence,
            quality=data.quality,
            provenance=data.provenance,
            observation=observation,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _classify(
        *,
        adx_val: float,
        atr_pct: float,
        closes,
        adx_trend: float,
        vol_high: float,
        period: int,
    ) -> tuple[MarketRegime, Confidence, str]:
        # Volatility dominates: a whipsawing tape is VOLATILE regardless of ADX,
        # because directional signals are least reliable there.
        if atr_pct >= vol_high:
            return (
                MarketRegime.VOLATILE,
                Confidence.from_score(min(1.0, atr_pct / (vol_high * 2.0))),
                (
                    f"ATR is {atr_pct * 100:.2f}% of price (>= "
                    f"{vol_high * 100:.2f}% threshold): high-volatility regime."
                ),
            )
        if adx_val >= adx_trend:
            # Direction from a short vs long mean of closes -- the same slope
            # confirmation the structure layer uses.
            size = closes.size
            short = float(closes[-min(size, period):].mean())
            long = float(closes[-min(size, period * 2):].mean())
            up = short >= long
            regime = (
                MarketRegime.TRENDING_UP if up else MarketRegime.TRENDING_DOWN
            )
            return (
                regime,
                Confidence.from_score(min(1.0, adx_val / 50.0)),
                (
                    f"ADX {adx_val:.1f} (>= {adx_trend:.0f}) with "
                    f"{'rising' if up else 'falling'} price: "
                    f"{'up' if up else 'down'}-trending regime."
                ),
            )
        return (
            MarketRegime.RANGING,
            Confidence.LOW,
            (
                f"ADX {adx_val:.1f} (< {adx_trend:.0f}) and ATR "
                f"{atr_pct * 100:.2f}% of price: range-bound / choppy regime."
            ),
        )

    def _unknown(
        self, data: MarketData, limitations: list[str]
    ) -> RegimeAnalysis:
        return RegimeAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            regime=MarketRegime.UNKNOWN,
            adx=None,
            trend_strength=None,
            atr_pct=None,
            realized_volatility=None,
            confidence=Confidence.LOW,
            quality=data.quality,
            provenance=data.provenance,
            observation="Regime undetermined: insufficient or unusable data.",
            limitations=tuple(limitations),
        )

    async def _emit(self, result: RegimeAnalysis) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                MarketRegimeDetected(
                    instrument_key=result.instrument.key,
                    timeframe=result.timeframe_value,
                    regime=result.regime.value,
                    adx=result.adx,
                    atr_pct=result.atr_pct,
                    trend_strength=result.trend_strength,
                    is_reliable=result.is_reliable,
                    source_tier=result.provenance.tier.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish MarketRegimeDetected")
