"""
Evidence service.

Translates the deterministic technical snapshot, market structure and volume
behaviour into discrete, sourced, weighted :class:`Evidence` items -- the
atomic claims the decision layers reason over. Each item records what was
observed, the direction it leans, how strongly (weight), and inherits the
provenance/quality of the underlying data so a mock or stale input can never be
laundered into a confident real signal (spec sections 8, 15, 61).

This layer interprets numbers into claims; it does not fuse them into a single
verdict (that is the analysis service's job) and it never invents a claim that
the inputs do not support.
"""

from __future__ import annotations

from ...core.logging import get_logger
from ..domain.analysis import VolumeAnalysis
from ..domain.enums import Assertion, Confidence, Direction, EvidenceType
from ..domain.evidence import Evidence
from ..domain.market_data import MarketData
from ..domain.provenance import DataQuality, Provenance
from ..domain.structure import MarketStructure
from ..domain.technical import TechnicalSnapshot

logger = get_logger("trading.evidence")


class EvidenceService:
    """Builds Evidence items from computed technical/structure/volume reads."""

    def build(
        self,
        *,
        data: MarketData,
        technical: TechnicalSnapshot,
        structure: MarketStructure,
        volume: VolumeAnalysis | None,
    ) -> tuple[Evidence, ...]:
        key = data.instrument.key
        prov = data.provenance
        quality = data.quality
        items: list[Evidence] = []

        def add(
            etype: EvidenceType,
            assertion: Assertion,
            direction: Direction,
            detail: str,
            weight: float,
            extra: dict | None = None,
        ) -> None:
            items.append(
                Evidence(
                    instrument_key=key,
                    type=etype,
                    assertion=assertion,
                    direction=direction,
                    detail=detail,
                    weight=weight,
                    confidence=Confidence.from_score(weight),
                    provenance=prov,
                    quality=quality,
                    data=extra or {},
                )
            )

        price = technical.last_price

        # ---- Moving-average relationship -> trend evidence ----
        if technical.sma_fast is not None and technical.sma_slow is not None:
            if technical.sma_fast > technical.sma_slow:
                add(
                    EvidenceType.TREND,
                    Assertion.CALCULATED,
                    Direction.UP,
                    f"Fast SMA ({technical.sma_fast:.2f}) is above slow SMA "
                    f"({technical.sma_slow:.2f}).",
                    0.6,
                )
            elif technical.sma_fast < technical.sma_slow:
                add(
                    EvidenceType.TREND,
                    Assertion.CALCULATED,
                    Direction.DOWN,
                    f"Fast SMA ({technical.sma_fast:.2f}) is below slow SMA "
                    f"({technical.sma_slow:.2f}).",
                    0.6,
                )

        # ---- Price vs slow MA ----
        if technical.sma_slow is not None:
            if price > technical.sma_slow:
                add(
                    EvidenceType.TECHNICAL,
                    Assertion.CALCULATED,
                    Direction.UP,
                    f"Price ({price:.2f}) is above the slow SMA "
                    f"({technical.sma_slow:.2f}).",
                    0.5,
                )
            elif price < technical.sma_slow:
                add(
                    EvidenceType.TECHNICAL,
                    Assertion.CALCULATED,
                    Direction.DOWN,
                    f"Price ({price:.2f}) is below the slow SMA "
                    f"({technical.sma_slow:.2f}).",
                    0.5,
                )

        # ---- RSI momentum ----
        if technical.rsi is not None:
            rsi = technical.rsi
            if rsi >= 70:
                add(
                    EvidenceType.MOMENTUM,
                    Assertion.CALCULATED,
                    Direction.DOWN,
                    f"RSI {rsi:.1f} is overbought (>= 70).",
                    0.5,
                    {"rsi": rsi},
                )
            elif rsi <= 30:
                add(
                    EvidenceType.MOMENTUM,
                    Assertion.CALCULATED,
                    Direction.UP,
                    f"RSI {rsi:.1f} is oversold (<= 30).",
                    0.5,
                    {"rsi": rsi},
                )
            elif rsi > 55:
                add(
                    EvidenceType.MOMENTUM,
                    Assertion.CALCULATED,
                    Direction.UP,
                    f"RSI {rsi:.1f} shows bullish momentum (> 55).",
                    0.35,
                    {"rsi": rsi},
                )
            elif rsi < 45:
                add(
                    EvidenceType.MOMENTUM,
                    Assertion.CALCULATED,
                    Direction.DOWN,
                    f"RSI {rsi:.1f} shows bearish momentum (< 45).",
                    0.35,
                    {"rsi": rsi},
                )

        # ---- MACD histogram ----
        if technical.macd is not None:
            hist = technical.macd.histogram
            if hist > 0:
                add(
                    EvidenceType.MOMENTUM,
                    Assertion.CALCULATED,
                    Direction.UP,
                    f"MACD histogram is positive ({hist:.4f}).",
                    0.45,
                )
            elif hist < 0:
                add(
                    EvidenceType.MOMENTUM,
                    Assertion.CALCULATED,
                    Direction.DOWN,
                    f"MACD histogram is negative ({hist:.4f}).",
                    0.45,
                )

        # ---- Bollinger stretch ----
        if technical.bollinger is not None:
            if price > technical.bollinger.upper:
                add(
                    EvidenceType.VOLATILITY,
                    Assertion.CALCULATED,
                    Direction.DOWN,
                    f"Price ({price:.2f}) is above the upper Bollinger band "
                    f"({technical.bollinger.upper:.2f}); stretched.",
                    0.3,
                )
            elif price < technical.bollinger.lower:
                add(
                    EvidenceType.VOLATILITY,
                    Assertion.CALCULATED,
                    Direction.UP,
                    f"Price ({price:.2f}) is below the lower Bollinger band "
                    f"({technical.bollinger.lower:.2f}); stretched.",
                    0.3,
                )

        # ---- Structure signals ----
        for sig in structure.signals:
            weight = {
                Confidence.HIGH: 0.7,
                Confidence.MEDIUM: 0.5,
                Confidence.LOW: 0.3,
            }[sig.confidence]
            add(
                EvidenceType.MARKET_STRUCTURE,
                Assertion.DETECTED,
                sig.direction,
                sig.observation,
                weight,
                {"signal_type": sig.type.value, "reference_price": sig.reference_price},
            )

        # ---- Structural trend pattern ----
        if structure.higher_highs and structure.higher_lows:
            add(
                EvidenceType.MARKET_STRUCTURE,
                Assertion.DETECTED,
                Direction.UP,
                "Structure shows higher highs and higher lows.",
                0.6,
            )
        elif structure.lower_highs and structure.lower_lows:
            add(
                EvidenceType.MARKET_STRUCTURE,
                Assertion.DETECTED,
                Direction.DOWN,
                "Structure shows lower highs and lower lows.",
                0.6,
            )

        # ---- Volume confirmation ----
        if volume is not None and volume.relative_volume >= 1.5:
            add(
                EvidenceType.VOLUME,
                Assertion.OBSERVED,
                Direction.UNKNOWN,
                f"Volume is {volume.relative_volume:.1f}x its average "
                f"({volume.trend}); moves are being confirmed by participation.",
                0.3,
                {"relative_volume": volume.relative_volume},
            )

        return tuple(items)

    # ------------------------------------------------------------------

    @staticmethod
    def build_volume_analysis(data: MarketData, *, period: int = 20) -> VolumeAnalysis | None:
        volumes = data.volumes()
        if volumes.size == 0:
            return None
        last = float(volumes[-1])
        window = volumes[-min(volumes.size, period):]
        avg = float(window.mean()) if window.size else 0.0
        rel = last / avg if avg > 0 else 0.0

        # Trend of volume: compare the last third vs the first third of window.
        if window.size >= 3:
            third = max(1, window.size // 3)
            early = float(window[:third].mean())
            late = float(window[-third:].mean())
            if late > early * 1.1:
                trend = "rising"
            elif late < early * 0.9:
                trend = "falling"
            else:
                trend = "flat"
        else:
            trend = "flat"

        observation = (
            f"Last volume {last:,.0f} vs {period}-bar average {avg:,.0f} "
            f"({rel:.2f}x, {trend})."
        )
        return VolumeAnalysis(
            last_volume=last,
            average_volume=avg,
            relative_volume=rel,
            trend=trend,
            observation=observation,
        )
