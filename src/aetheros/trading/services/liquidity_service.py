"""
Liquidity-analysis service.

Composes the existing indicator primitives into the spec's missing
"liquidity analysis" read: participation (relative volume from
``volume_ma``), the volume-at-price profile (POC + 70% value area from
``volume_profile``), a spread proxy (ATR as a fraction of price) and price's
distance to the point of control. Everything is deterministic maths over a
candle series the caller hands in -- no I/O, no LLM, no new indicator
implementations (reuse, not duplication, CLAUDE.md section 22).

Honesty rules (sections 5, 28): each input an indicator cannot compute stays
``None`` with a limitation recorded; unusable data yields UNKNOWN reads, never
a fabricated "high participation".
"""

from __future__ import annotations

from ...core.logging import get_logger
from .. import indicators as ind
from ..domain.enums import DataQualityStatus, SourceTier
from ..domain.liquidity import LiquidityAnalysis
from ..domain.market_data import MarketData
from ..domain.provenance import Provenance

logger = get_logger("trading.liquidity")

# Relative-volume bands for the participation label.
_HIGH_PARTICIPATION = 1.5
_LOW_PARTICIPATION = 0.75

# Value-area share above which the volume is called "concentrated".
_CONCENTRATED_SHARE = 0.85


class LiquidityService:
    """Deterministic liquidity read over a MarketData window."""

    def __init__(self, *, period: int = 20, profile_bins: int = 20) -> None:
        if period <= 0:
            raise ValueError("period must be positive.")
        if profile_bins <= 1:
            raise ValueError("profile_bins must be greater than 1.")
        self._period = period
        self._profile_bins = profile_bins

    def analyze(self, data: MarketData) -> LiquidityAnalysis:
        closes = data.closes()
        highs = data.highs()
        lows = data.lows()
        volumes = data.volumes()
        last_price = data.last_price

        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append("Read is based on synthetic MOCK data.")
        if data.quality.status in (
            DataQualityStatus.MISSING,
            DataQualityStatus.INVALID,
        ):
            limitations.append(
                f"Underlying data quality is '{data.quality.status.value}'."
            )

        # ---- Participation (relative volume) ----
        relative_volume: float | None = None
        participation = "unknown"
        vol_ma = ind.last_finite(ind.volume_ma(volumes, self._period))
        if vol_ma is not None and vol_ma > 0 and closes.size:
            relative_volume = round(float(volumes[-1]) / vol_ma, 4)
            if relative_volume >= _HIGH_PARTICIPATION:
                participation = "high"
            elif relative_volume <= _LOW_PARTICIPATION:
                participation = "low"
            else:
                participation = "average"
        else:
            limitations.append(
                "Not enough bars for a volume baseline; participation unknown."
            )

        # ---- Volume profile ----
        profile = ind.volume_profile(closes, volumes, self._profile_bins)
        poc = value_area_low = value_area_high = value_area_share = None
        concentration = "unknown"
        if profile is not None:
            poc = profile.poc
            value_area_low = profile.value_area_low
            value_area_high = profile.value_area_high
            in_area = sum(
                v
                for v, (lo, hi) in zip(
                    profile.bin_volumes,
                    zip(profile.bin_edges[:-1], profile.bin_edges[1:], strict=True),
                    strict=True,
                )
                if lo >= value_area_low and hi <= value_area_high
            )
            value_area_share = round(
                in_area / profile.total_volume, 4
            ) if profile.total_volume > 0 else None
            if value_area_share is not None:
                concentration = (
                    "concentrated"
                    if value_area_share >= _CONCENTRATED_SHARE
                    else "distributed"
                )
        else:
            limitations.append(
                "Not enough distinct price points for a volume profile."
            )

        # ---- Spread proxy ----
        atr_value = ind.last_finite(
            ind.atr(highs, lows, closes, self._period)
        )
        spread_proxy_pct = (
            round(atr_value / last_price * 100.0, 4)
            if atr_value is not None and last_price
            else None
        )
        if spread_proxy_pct is None:
            limitations.append("ATR unavailable; spread proxy unknown.")

        # ---- Price vs POC ----
        price_vs_poc_pct = (
            round((last_price - poc) / poc * 100.0, 4)
            if poc is not None and poc > 0
            else None
        )

        observation = self._observation(
            participation,
            concentration,
            price_vs_poc_pct,
        )

        return LiquidityAnalysis(
            last_price=last_price,
            participation=participation,
            relative_volume=relative_volume,
            poc=poc,
            value_area_low=value_area_low,
            value_area_high=value_area_high,
            value_area_share=value_area_share,
            concentration=concentration,
            spread_proxy_pct=spread_proxy_pct,
            price_vs_poc_pct=price_vs_poc_pct,
            observation=observation,
            provenance=Provenance(
                source=data.provenance.source,
                tier=(
                    SourceTier.MOCK
                    if data.provenance.is_mock
                    else SourceTier.DERIVED
                ),
                detail="deterministic liquidity analysis",
            ),
            limitations=tuple(limitations),
        )

    @staticmethod
    def _observation(
        participation: str,
        concentration: str,
        price_vs_poc_pct: float | None,
    ) -> str:
        parts: list[str] = []
        if participation != "unknown":
            parts.append(f"{participation} participation")
        if concentration != "unknown":
            parts.append(f"{concentration} volume around the value area")
        if price_vs_poc_pct is not None:
            side = "above" if price_vs_poc_pct > 0 else "below"
            parts.append(f"price {abs(price_vs_poc_pct):.2f}% {side} the POC")
        if not parts:
            return "Insufficient data for a liquidity read."
        return "; ".join(parts[:3]) + "."
