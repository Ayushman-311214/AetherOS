"""
Volume / volume-price-action analysis (Phase 4).

A deterministic read of *what the traded volume is doing* relative to price --
relative volume, expansion/contraction, an estimated buy/sell split where no
aggressor feed exists, the net-flow/delta that implies, and volume-price
divergence. This complements the liquidity layer's *tape* flow (which needs
executed prints) by deriving an honest volume read from OHLCV bars alone -- the
data every timeframe has.

The central honesty rule: candles do not carry aggressor direction, so "buy vs
sell volume" is *estimated* from bar geometry (close location within the bar's
range) and labelled as such -- never presented as a real buy/sell split, and
never as flow that a real tape read would contradict. Where a true aggressor
feed exists it should be preferred; this is the honest bar-level fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np

from ...core.logging import get_logger
from ..domain.enums import Confidence, Direction
from ..domain.market_data import MarketData
from ..indicators import core as ind

logger = get_logger("trading.volume")

#: Relative-volume bands for the participation label.
_HIGH_REL_VOL = 1.5
_LOW_REL_VOL = 0.75

#: |delta_share| above which the estimated net flow reads as one-sided.
_NET_FLOW_BAND = 0.15


@dataclass(frozen=True, slots=True)
class VolumeAnalysis2:
    """
    The deterministic volume/price-action read for one series.

    Distinct from the candle-based ``VolumeAnalysis`` value object used by
    ``AnalysisService`` (a compact last-vs-average read); this is the fuller
    Phase-4 surface -- expansion/contraction, an estimated buy/sell split, net
    flow/delta, and a volume-price divergence flag.
    """

    participation: str              # "high" | "average" | "low" | "unknown"
    relative_volume: float | None   # last volume / baseline volume
    volume_state: str               # "expanding" | "contracting" | "steady" | "unknown"
    volume_ratio: float | None      # last vs prior-baseline mean
    estimated_buy_volume: float     # estimated buy-initiated volume (bar geometry)
    estimated_sell_volume: float    # estimated sell-initiated volume
    net_flow: float                 # (est_buy - est_sell) / total  in [-1,1]
    delta: float                    # signed estimated net volume (buy - sell)
    divergence: str                 # "bullish" | "bearish" | "none"
    direction: Direction
    confidence: Confidence
    observation: str
    limitations: tuple[str, ...] = ()
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "participation": self.participation,
            "relative_volume": self.relative_volume,
            "volume_state": self.volume_state,
            "volume_ratio": self.volume_ratio,
            "estimated_buy_volume": self.estimated_buy_volume,
            "estimated_sell_volume": self.estimated_sell_volume,
            "net_flow": self.net_flow,
            "delta": self.delta,
            "divergence": self.divergence,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "observation": self.observation,
            "limitations": list(self.limitations),
            "computed_at": self.computed_at.isoformat(),
        }


class VolumeActionService:
    """Deterministic volume/price-action read over a candle series."""

    def __init__(self, *, period: int = 20, min_bars: int = 10) -> None:
        if period < 1:
            raise ValueError("period must be >= 1.")
        self._period = period
        self._min_bars = min_bars

    def analyze(self, data: MarketData) -> VolumeAnalysis2:
        candles = data.candles
        n = len(candles)
        if n < self._min_bars:
            return VolumeAnalysis2(
                participation="unknown", relative_volume=None,
                volume_state="unknown", volume_ratio=None,
                estimated_buy_volume=0.0, estimated_sell_volume=0.0,
                net_flow=0.0, delta=0.0, divergence="none",
                direction=Direction.UNKNOWN, confidence=Confidence.LOW,
                observation="Too few bars for a volume read.",
                limitations=(f"Have {n} bars; need >= {self._min_bars}.",),
            )

        closes = data.closes()
        highs = data.highs()
        lows = data.lows()
        volumes = data.volumes()

        # ---- Relative volume / participation ----
        vol_ma = ind.last_finite(ind.volume_ma(volumes, self._period))
        relative = (
            float(volumes[-1] / vol_ma) if vol_ma and vol_ma > 0 else None
        )
        participation = "unknown"
        if relative is not None:
            participation = (
                "high" if relative >= _HIGH_REL_VOL
                else "low" if relative <= _LOW_REL_VOL
                else "average"
            )

        # ---- Expansion / contraction vs prior baseline ----
        if n > self._period:
            baseline = float(volumes[-self._period - 1 : -1].mean())
            ratio = float(volumes[-1] / baseline) if baseline > 0 else None
        else:
            ratio = relative
        if ratio is None:
            volume_state = "unknown"
        elif ratio >= _HIGH_REL_VOL:
            volume_state = "expanding"
        elif ratio <= _LOW_REL_VOL:
            volume_state = "contracting"
        else:
            volume_state = "steady"

        # ---- Estimated buy/sell split (bar geometry) ----
        buy, sell = self._split_volumes(closes, highs, lows, volumes)
        total_est = buy + sell
        delta = buy - sell
        net_flow = delta / total_est if total_est > 0 else 0.0

        # ---- Volume-price divergence ----
        divergence = self._divergence(closes, volumes)

        direction = (
            Direction.UP if net_flow >= _NET_FLOW_BAND
            else Direction.DOWN if net_flow <= -_NET_FLOW_BAND
            else Direction.SIDEWAYS
        )
        confidence = Confidence.from_score(abs(net_flow))

        return VolumeAnalysis2(
            participation=participation,
            relative_volume=round(relative, 4) if relative is not None else None,
            volume_state=volume_state,
            volume_ratio=round(ratio, 4) if ratio is not None else None,
            estimated_buy_volume=round(buy, 4),
            estimated_sell_volume=round(sell, 4),
            net_flow=round(net_flow, 4),
            delta=round(delta, 4),
            divergence=divergence,
            direction=direction,
            confidence=confidence,
            observation=self._observation(
                participation, volume_state, net_flow, divergence
            ),
            limitations=self._limitations(data),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _split_volumes(closes, highs, lows, volumes) -> tuple[float, float]:
        """
        Estimate buy vs sell volume per bar from close-location-in-range (CLV).

        Each bar's volume is split by where the close sat in its high-low
        range: a close near the high attributes most of the bar's volume to
        buyers; near the low, to sellers. This is an *estimate* -- a bar is not
        a tape -- so it is labelled "estimated" and never presented as a real
        aggressor split.
        """
        rng = highs - lows
        # CLV in [-1,1]: +1 closed at high, -1 closed at low; guard zero range.
        with np.errstate(divide="ignore", invalid="ignore"):
            clv = np.where(
                rng > 0,
                ((closes - lows) - (highs - closes)) / rng,
                0.0,
            )
        buy = float((volumes * (1 + clv) / 2).sum())
        sell = float((volumes * (1 - clv) / 2).sum())
        return buy, sell

    @staticmethod
    def _divergence(closes, volumes) -> str:
        """
        Volume-price divergence: is volume confirming or contradicting the move?

        Compare the price slope over the window to the volume slope. Price up
        on falling volume (bearish divergence -- weak backing) or price down on
        falling volume (bullish divergence -- weak selling pressure) is the
        classic read. Returns "bullish" | "bearish" | "none".
        """
        n = closes.size
        window = min(10, n - 1)
        if window < 2:
            return "none"
        p_delta = float(closes[-1] - closes[-1 - window])
        v_delta = float(volumes[-1] - volumes[-window])
        # Classic volume-price divergence: the move is not confirmed by volume.
        # Price rising on *falling* volume -> bearish divergence (weak backing);
        # price falling on *falling* volume -> bullish divergence (sellers
        # losing conviction). Same-sign volume+price is confirmation, not a
        # divergence.
        if p_delta > 0 and v_delta < 0:
            return "bearish"
        if p_delta < 0 and v_delta < 0:
            return "bullish"
        return "none"

    @staticmethod
    def _limitations(data: MarketData) -> tuple[str, ...]:
        lim: list[str] = [
            "Buy/sell split is estimated from bar geometry (close-in-range); "
            "bars carry no aggressor feed."
        ]
        if data.provenance.is_mock:
            lim.append("Read is based on synthetic MOCK data.")
        return tuple(lim)

    @staticmethod
    def _observation(participation, volume_state, net_flow, divergence) -> str:
        parts = []
        if participation != "unknown":
            parts.append(f"{participation} participation")
        parts.append(f"{volume_state} volume")
        if abs(net_flow) >= _NET_FLOW_BAND:
            side = "buy" if net_flow > 0 else "sell"
            parts.append(f"estimated {side}-led flow ({net_flow:+.2f})")
        if divergence != "none":
            parts.append(f"{divergence} volume-price divergence")
        return "; ".join(parts) + "." if parts else "No clear volume read."
