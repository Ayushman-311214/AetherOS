"""
Channel-breakout detection service.

Detects a Donchian-style breakout: the latest close pushing above the prior
``lookback``-bar highest high (bullish breakout) or below the prior-bar lowest
low (bearish breakdown), with optional above-average-volume confirmation. This
is a classic, well-defined price-action read (CLAUDE.md section 5), computed
deterministically from the OHLCV series.

It follows the RegimeService / AnomalyService shape: the service operates purely
on one ``MarketData`` object it is handed (no LLM, no I/O), so it is trivially
unit-testable with crafted candles, and identical inputs always yield the
identical read.

The read is honest (sections 5, 28): mock, unusable or too-thin data yields
``Direction.UNKNOWN`` with the reason in ``limitations`` and no fabricated
signal; a close inside the channel is a determinate reliable SIDEWAYS "no
breakout" read. When a breakout is present it emits a single
``EvidenceType.MARKET_STRUCTURE`` :class:`Evidence` item, weighted up when the
breakout is confirmed by volume.

This increment is deliberately standalone: the service and its tool stand beside
the existing pipeline and are not fused into the orchestrator, so no existing
behaviour changes.
"""

from __future__ import annotations

import numpy as np

from ...config.settings import Settings
from ..domain.breakout import BreakoutAnalysis
from ..domain.enums import Assertion, Confidence, Direction, EvidenceType
from ..domain.evidence import Evidence
from ..domain.market_data import MarketData

_EPS = 1e-12

# Fractional distance beyond the channel edge that maps to a full-weight
# (weight 1.0) evidence claim before the volume adjustment; larger is clamped. A
# 3% push beyond the channel is treated as a decisive break. Scales the *weight*
# of one evidence item -- never a probability.
_FULL_WEIGHT_BREAK = 0.03


class BreakoutService:
    """Deterministic channel-breakout read over candles."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def analyze(self, data: MarketData) -> BreakoutAnalysis:
        window = self._settings.TRADING_BREAKOUT_LOOKBACK
        min_bars = self._settings.TRADING_BREAKOUT_MIN_BARS
        vol_mult = self._settings.TRADING_BREAKOUT_VOL_MULT

        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append(
                "Data is MOCK; breakout is illustrative, not a real market read."
            )
        if not data.quality.ok:
            limitations.extend(data.quality.issues)

        # Need the latest bar plus a full channel of prior bars behind it.
        if not data.quality.usable or data.count < min_bars or data.count < window + 1:
            if data.count < max(min_bars, window + 1):
                limitations.append(
                    f"Only {data.count} bars; need at least "
                    f"{max(min_bars, window + 1)} for a breakout read."
                )
            return self._unknown(data, window, tuple(limitations))

        highs = data.highs()
        lows = data.lows()
        closes = data.closes()
        volumes = data.volumes()

        # Channel = the `window` bars *before* the latest one, so the latest close
        # breaking it is a genuine new extreme rather than trivially its own high.
        channel_high = float(np.max(highs[-(window + 1) : -1]))
        channel_low = float(np.min(lows[-(window + 1) : -1]))
        last_close = float(closes[-1])

        avg_vol = float(np.mean(volumes[-(window + 1) : -1]))
        last_vol = float(volumes[-1])
        volume_ratio = last_vol / avg_vol if avg_vol > _EPS else None
        volume_confirmed = volume_ratio is not None and volume_ratio >= vol_mult

        if last_close > channel_high:
            direction = Direction.UP
            edge = channel_high
        elif last_close < channel_low:
            direction = Direction.DOWN
            edge = channel_low
        else:
            return BreakoutAnalysis(
                instrument=data.instrument,
                timeframe_value=data.timeframe.value,
                lookback=window,
                has_breakout=False,
                direction=Direction.SIDEWAYS,
                confidence=Confidence.LOW,
                channel_high=round(channel_high, 6),
                channel_low=round(channel_low, 6),
                last_close=round(last_close, 6),
                volume_ratio=round(volume_ratio, 6) if volume_ratio is not None else None,
                volume_confirmed=False,
                quality=data.quality,
                provenance=data.provenance,
                evidence=None,
                observation=(
                    f"No breakout: last close {last_close:.2f} sits inside the "
                    f"{window}-bar channel [{channel_low:.2f}, {channel_high:.2f}]."
                ),
                limitations=tuple(limitations),
            )

        # Distance beyond the broken edge, as a fraction, scaled by volume.
        break_frac = abs(last_close - edge) / abs(edge) if abs(edge) > _EPS else 0.0
        base = min(1.0, break_frac / _FULL_WEIGHT_BREAK)
        weight = base if volume_confirmed else base * 0.5
        confidence = Confidence.from_score(weight)
        observation = self._describe(
            direction, last_close, channel_high, channel_low, window,
            volume_ratio, volume_confirmed,
        )
        evidence = self._evidence(
            data, direction, weight, confidence, channel_high, channel_low,
            volume_ratio, volume_confirmed, window, observation,
        )

        return BreakoutAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            lookback=window,
            has_breakout=True,
            direction=direction,
            confidence=confidence,
            channel_high=round(channel_high, 6),
            channel_low=round(channel_low, 6),
            last_close=round(last_close, 6),
            volume_ratio=round(volume_ratio, 6) if volume_ratio is not None else None,
            volume_confirmed=volume_confirmed,
            quality=data.quality,
            provenance=data.provenance,
            evidence=evidence,
            observation=observation,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _describe(
        direction: Direction,
        last_close: float,
        channel_high: float,
        channel_low: float,
        window: int,
        volume_ratio: float | None,
        volume_confirmed: bool,
    ) -> str:
        edge = channel_high if direction is Direction.UP else channel_low
        kind = "breakout above" if direction is Direction.UP else "breakdown below"
        vol = (
            f"on {volume_ratio:.1f}x average volume"
            if volume_confirmed and volume_ratio is not None
            else "without volume confirmation"
        )
        return (
            f"Channel {kind} the {window}-bar extreme {edge:.2f} "
            f"(last close {last_close:.2f}) {vol}."
        )

    def _evidence(
        self,
        data: MarketData,
        direction: Direction,
        weight: float,
        confidence: Confidence,
        channel_high: float,
        channel_low: float,
        volume_ratio: float | None,
        volume_confirmed: bool,
        window: int,
        detail: str,
    ) -> Evidence:
        return Evidence(
            instrument_key=data.instrument.key,
            type=EvidenceType.MARKET_STRUCTURE,
            assertion=Assertion.DETECTED,
            direction=direction,
            detail=detail,
            weight=weight,
            confidence=confidence,
            provenance=data.provenance,
            quality=data.quality,
            data={
                "channel_high": round(channel_high, 6),
                "channel_low": round(channel_low, 6),
                "volume_ratio": round(volume_ratio, 6) if volume_ratio is not None else None,
                "volume_confirmed": volume_confirmed,
                "lookback": window,
            },
        )

    @staticmethod
    def _unknown(
        data: MarketData,
        window: int,
        limitations: tuple[str, ...],
    ) -> BreakoutAnalysis:
        return BreakoutAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            lookback=window,
            has_breakout=False,
            direction=Direction.UNKNOWN,
            confidence=Confidence.LOW,
            channel_high=None,
            channel_low=None,
            last_close=None,
            volume_ratio=None,
            volume_confirmed=False,
            quality=data.quality,
            provenance=data.provenance,
            evidence=None,
            observation="Breakout undetermined: insufficient or unusable data.",
            limitations=limitations,
        )
