"""
Momentum-divergence detection service.

Detects *regular divergence* between price and the RSI oscillator: a lower price
low against a higher RSI low (bullish divergence -- a weakening downtrend), or a
higher price high against a lower RSI high (bearish divergence -- a weakening
uptrend). This is a well-defined, textbook technical read (CLAUDE.md section 5),
computed deterministically from the RSI in ``indicators/core.py`` (reuse, not a
re-implemented oscillator -- section 22).

It follows the RegimeService / AnomalyService shape: the service operates purely
on one ``MarketData`` object it is handed (no LLM, no I/O), so it is trivially
unit-testable with crafted candles, and identical inputs always yield the
identical read.

The read is honest (sections 5, 28): mock, unusable or too-thin data, or fewer
than two comparable pivots, yields ``Direction.UNKNOWN`` with the reason in
``limitations`` and no fabricated signal; a clean series with no divergence is a
determinate reliable SIDEWAYS "no divergence" read. When a divergence is present
it emits a single ``EvidenceType.MOMENTUM`` :class:`Evidence` item.

This increment is deliberately standalone: the service and its tool stand beside
the existing pipeline and are not fused into the orchestrator, so no existing
behaviour changes.
"""

from __future__ import annotations

import numpy as np

from ...config.settings import Settings
from ..domain.divergence import DivergenceAnalysis
from ..domain.enums import Assertion, Confidence, Direction, EvidenceType
from ..domain.evidence import Evidence
from ..domain.market_data import MarketData
from ..indicators import core as ind

_EPS = 1e-12

# RSI-point gap between the two compared pivots that maps to a full-weight
# (weight 1.0) evidence claim; larger is clamped. A 20-point oscillator
# divergence is treated as a strong one. Scales the *weight* of one evidence
# item -- never a probability.
_FULL_WEIGHT_RSI_GAP = 20.0


class DivergenceService:
    """Deterministic price-vs-RSI regular-divergence read over candles."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def analyze(self, data: MarketData) -> DivergenceAnalysis:
        window = self._settings.TRADING_DIV_PIVOT_WINDOW
        min_bars = self._settings.TRADING_DIV_MIN_BARS
        rsi_period = self._settings.TRADING_DIV_RSI_PERIOD
        osc_name = f"rsi_{rsi_period}"

        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append(
                "Data is MOCK; divergence is illustrative, not a real market read."
            )
        if not data.quality.ok:
            limitations.extend(data.quality.issues)

        if not data.quality.usable or data.count < min_bars:
            if data.count < min_bars:
                limitations.append(
                    f"Only {data.count} bars; need at least {min_bars} for a "
                    "divergence read."
                )
            return self._unknown(data, osc_name, 0, tuple(limitations))

        closes = data.closes()
        rsi = ind.rsi(closes, rsi_period)

        lows = self._pivots(closes, window, low=True)
        highs = self._pivots(closes, window, low=False)
        # Only pivots where the oscillator has warmed up are comparable.
        lows = [i for i in lows if np.isfinite(rsi[i])]
        highs = [i for i in highs if np.isfinite(rsi[i])]

        bull = self._regular(closes, rsi, lows, low=True)
        bear = self._regular(closes, rsi, highs, low=False)

        pivot_count = len(lows) + len(highs)
        if lows == [] and highs == []:
            # Not even one usable pivot on either side -> can't judge.
            limitations.append(
                "No confirmed price pivots with a warmed-up oscillator; divergence "
                "undetermined."
            )
            return self._unknown(data, osc_name, pivot_count, tuple(limitations))

        chosen = self._choose(bull, bear)
        if chosen is None:
            # Pivots exist but neither side diverges -> a real "no divergence".
            return DivergenceAnalysis(
                instrument=data.instrument,
                timeframe_value=data.timeframe.value,
                oscillator=osc_name,
                has_divergence=False,
                direction=Direction.SIDEWAYS,
                confidence=Confidence.LOW,
                price_change_pct=None,
                oscillator_change=None,
                pivot_count=pivot_count,
                quality=data.quality,
                provenance=data.provenance,
                evidence=None,
                observation=(
                    f"No regular divergence between price and {osc_name} over the "
                    "most recent pivots."
                ),
                limitations=tuple(limitations),
            )

        direction, price_change, osc_change = chosen
        weight = min(1.0, abs(osc_change) / _FULL_WEIGHT_RSI_GAP)
        confidence = Confidence.from_score(weight)
        observation = self._describe(direction, price_change, osc_change, osc_name)
        evidence = self._evidence(
            data, direction, weight, confidence, price_change, osc_change, osc_name,
            observation,
        )

        return DivergenceAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            oscillator=osc_name,
            has_divergence=True,
            direction=direction,
            confidence=confidence,
            price_change_pct=round(price_change, 6),
            oscillator_change=round(osc_change, 6),
            pivot_count=pivot_count,
            quality=data.quality,
            provenance=data.provenance,
            evidence=evidence,
            observation=observation,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _pivots(values: np.ndarray, window: int, *, low: bool) -> list[int]:
        """Indices that are a strict local min (low) / max (high) over +/-window.

        Returns pivots in ascending index order. The edges (first/last ``window``
        bars) cannot be confirmed and are excluded.
        """
        n = values.size
        out: list[int] = []
        for i in range(window, n - window):
            seg = values[i - window : i + window + 1]
            center = values[i]
            if low:
                if center == seg.min() and np.sum(seg == center) == 1:
                    out.append(i)
            else:
                if center == seg.max() and np.sum(seg == center) == 1:
                    out.append(i)
        return out

    @staticmethod
    def _regular(
        closes: np.ndarray,
        rsi: np.ndarray,
        pivots: list[int],
        *,
        low: bool,
    ) -> tuple[Direction, float, float] | None:
        """Classify regular divergence over the two most recent pivots.

        For lows (bullish): price lower-low but RSI higher-low.
        For highs (bearish): price higher-high but RSI lower-high.
        Returns (direction, price_change_pct, rsi_change) or None if no
        divergence (or fewer than two pivots).
        """
        if len(pivots) < 2:
            return None
        p1, p2 = pivots[-2], pivots[-1]  # older, newer
        price1, price2 = float(closes[p1]), float(closes[p2])
        rsi1, rsi2 = float(rsi[p1]), float(rsi[p2])
        if abs(price1) <= _EPS:
            return None
        price_change = price2 / price1 - 1.0
        rsi_change = rsi2 - rsi1

        if low:
            # bullish: lower price low, higher RSI low
            if price2 < price1 and rsi2 > rsi1:
                return Direction.UP, price_change, rsi_change
        else:
            # bearish: higher price high, lower RSI high
            if price2 > price1 and rsi2 < rsi1:
                return Direction.DOWN, price_change, rsi_change
        return None

    @staticmethod
    def _choose(
        bull: tuple[Direction, float, float] | None,
        bear: tuple[Direction, float, float] | None,
    ) -> tuple[Direction, float, float] | None:
        """Pick the stronger of a detected bullish/bearish divergence.

        If both fired, the one with the larger absolute oscillator divergence
        wins (a deterministic tie-break); otherwise whichever fired, or None.
        """
        if bull is not None and bear is not None:
            return bull if abs(bull[2]) >= abs(bear[2]) else bear
        return bull or bear

    @staticmethod
    def _describe(
        direction: Direction,
        price_change: float,
        osc_change: float,
        osc_name: str,
    ) -> str:
        kind = "Bullish" if direction is Direction.UP else "Bearish"
        extreme = "low" if direction is Direction.UP else "high"
        return (
            f"{kind} regular divergence: price made a "
            f"{'lower' if direction is Direction.UP else 'higher'} {extreme} "
            f"({price_change * 100:+.2f}%) while {osc_name} moved "
            f"{osc_change:+.1f} the other way."
        )

    def _evidence(
        self,
        data: MarketData,
        direction: Direction,
        weight: float,
        confidence: Confidence,
        price_change: float,
        osc_change: float,
        osc_name: str,
        detail: str,
    ) -> Evidence:
        return Evidence(
            instrument_key=data.instrument.key,
            type=EvidenceType.MOMENTUM,
            assertion=Assertion.DETECTED,
            direction=direction,
            detail=detail,
            weight=weight,
            confidence=confidence,
            provenance=data.provenance,
            quality=data.quality,
            data={
                "divergence": "bullish" if direction is Direction.UP else "bearish",
                "oscillator": osc_name,
                "price_change_pct": round(price_change, 6),
                "oscillator_change": round(osc_change, 6),
            },
        )

    @staticmethod
    def _unknown(
        data: MarketData,
        osc_name: str,
        pivot_count: int,
        limitations: tuple[str, ...],
    ) -> DivergenceAnalysis:
        return DivergenceAnalysis(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            oscillator=osc_name,
            has_divergence=False,
            direction=Direction.UNKNOWN,
            confidence=Confidence.LOW,
            price_change_pct=None,
            oscillator_change=None,
            pivot_count=pivot_count,
            quality=data.quality,
            provenance=data.provenance,
            evidence=None,
            observation="Divergence undetermined: insufficient or unusable data.",
            limitations=limitations,
        )
