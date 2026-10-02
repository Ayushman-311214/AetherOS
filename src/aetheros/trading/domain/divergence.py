"""
Momentum-divergence value object.

A :class:`DivergenceAnalysis` is the deterministic read of *regular divergence*
between price and a momentum oscillator (RSI): price making a lower low while
the oscillator makes a higher low is classic bullish divergence (a weakening
downtrend), and price making a higher high while the oscillator makes a lower
high is bearish divergence (a weakening uptrend). It is a well-defined technical
read (CLAUDE.md section 5, momentum/price action), not a prediction and carrying
no calibrated probability; it populates ``EvidenceType.MOMENTUM`` as a divergence
signal.

Like every trading value object it carries its own provenance and data-quality
read and is honest about ignorance: mock, unusable or too-thin data, or too few
pivots to compare, yields ``Direction.UNKNOWN`` with ``is_reliable`` False and no
fabricated signal; a clean series with no divergence is a determinate reliable
"no divergence" (SIDEWAYS) read (sections 5, 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction
from .evidence import Evidence
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class DivergenceAnalysis:
    """Deterministic price-vs-oscillator regular-divergence read."""

    instrument: Instrument
    timeframe_value: str
    oscillator: str  # the oscillator used, e.g. "rsi_14"
    has_divergence: bool
    direction: Direction  # UP = bullish divergence, DOWN = bearish, SIDEWAYS = none
    confidence: Confidence
    price_change_pct: float | None  # price move between the two compared pivots
    oscillator_change: float | None  # oscillator move between the same two pivots
    pivot_count: int  # pivots found on the relevant side
    quality: DataQuality
    provenance: Provenance
    evidence: Evidence | None = None
    observation: str = ""
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def is_reliable(self) -> bool:
        """
        Whether this read rests on data solid enough to lean on.

        Mock or unusable data, or an UNKNOWN read (too few pivots to judge), is
        never reliable. A determinate "no divergence" (SIDEWAYS) read on usable,
        non-mock data *is* reliable: finding no divergence is a real result.
        """
        return (
            self.quality.usable
            and not self.provenance.is_mock
            and self.direction is not Direction.UNKNOWN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe_value,
            "oscillator": self.oscillator,
            "has_divergence": self.has_divergence,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "price_change_pct": self.price_change_pct,
            "oscillator_change": self.oscillator_change,
            "pivot_count": self.pivot_count,
            "is_reliable": self.is_reliable,
            "observation": self.observation,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
