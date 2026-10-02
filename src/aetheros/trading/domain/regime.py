"""
Market-regime value object.

A ``RegimeAnalysis`` is the deterministic read of *what character the market is
in* -- trending, ranging or volatile -- derived purely from ADX (trend strength)
and ATR-as-a-fraction-of-price (realised volatility). It is not a prediction and
carries no calibrated probability; it is situational context that later layers
(the critic's "is the regime compatible?" check, the composed report) consume.

Like every trading value object it carries its own provenance, data-quality read
and limitations, and it is honest about ignorance: mock, unusable or too-thin
data produces ``MarketRegime.UNKNOWN`` with ``is_reliable`` False rather than a
fabricated regime (CLAUDE.md sections 5, 8, 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction, MarketRegime
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class RegimeAnalysis:
    """Deterministic market-regime classification for one instrument."""

    instrument: Instrument
    timeframe_value: str
    regime: MarketRegime
    adx: float | None  # raw ADX in 0..100, or None if it did not warm up
    trend_strength: float | None  # ADX normalised to 0..1, derived
    atr_pct: float | None  # ATR as a fraction of the last price
    realized_volatility: float | None  # rolling std of simple returns
    confidence: Confidence
    quality: DataQuality
    provenance: Provenance
    observation: str = ""
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def direction(self) -> Direction:
        """Directional bias implied by the regime (SIDEWAYS for a range)."""
        return self.regime.direction

    @property
    def is_reliable(self) -> bool:
        """
        Whether this regime read rests on data solid enough to lean on.

        Mock or unusable data, or an UNKNOWN regime, is never reliable -- the
        honest answer there is "regime undetermined".
        """
        return (
            self.quality.usable
            and not self.provenance.is_mock
            and self.regime is not MarketRegime.UNKNOWN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe_value,
            "regime": self.regime.value,
            "direction": self.direction.value,
            "adx": self.adx,
            "trend_strength": self.trend_strength,
            "atr_pct": self.atr_pct,
            "realized_volatility": self.realized_volatility,
            "confidence": self.confidence.value,
            "is_reliable": self.is_reliable,
            "observation": self.observation,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
