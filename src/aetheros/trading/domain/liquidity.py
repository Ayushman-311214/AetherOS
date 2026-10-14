"""
Liquidity-analysis value objects.

A liquidity read characterises *where the traded volume sits* relative to
price: the volume profile's point of control and value area, participation
(relative volume), the volatility spread proxy (ATR as a fraction of price),
and price's distance to the POC. It is situational context -- never a
directional prediction -- and honest about gaps: any input the underlying
indicators could not compute stays ``None`` rather than being fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .provenance import Provenance


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class LiquidityAnalysis:
    """Deterministic liquidity read for one instrument/timeframe."""

    last_price: float
    participation: str  # "high" | "average" | "low" | "unknown"
    relative_volume: float | None
    poc: float | None
    value_area_low: float | None
    value_area_high: float | None
    value_area_share: float | None  # share of volume inside the value area
    concentration: str  # "concentrated" | "distributed" | "unknown"
    spread_proxy_pct: float | None  # ATR / price * 100
    price_vs_poc_pct: float | None  # distance of price to POC, %
    observation: str
    provenance: Provenance
    limitations: tuple[str, ...] = ()
    computed_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_price": self.last_price,
            "participation": self.participation,
            "relative_volume": self.relative_volume,
            "poc": self.poc,
            "value_area_low": self.value_area_low,
            "value_area_high": self.value_area_high,
            "value_area_share": self.value_area_share,
            "concentration": self.concentration,
            "spread_proxy_pct": self.spread_proxy_pct,
            "price_vs_poc_pct": self.price_vs_poc_pct,
            "observation": self.observation,
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "computed_at": self.computed_at.isoformat(),
        }
