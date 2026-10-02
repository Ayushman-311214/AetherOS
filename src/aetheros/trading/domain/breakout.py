"""
Breakout value object.

A :class:`BreakoutAnalysis` is the deterministic read of a *channel breakout*:
the latest close pushing above the prior-N-bar highest high (a bullish breakout)
or below the prior-N-bar lowest low (a bearish breakdown), optionally confirmed
by above-average volume. It is a classic, well-defined price-action read
(CLAUDE.md section 5, "price action"/"volume"), not a prediction and carrying no
calibrated probability; it populates ``EvidenceType.MARKET_STRUCTURE`` as a
breakout signal.

Like every trading value object it carries its own provenance and data-quality
read and is honest about ignorance: mock, unusable or too-thin data yields
``Direction.UNKNOWN`` with ``is_reliable`` False and no fabricated signal; a close
sitting inside the channel is a determinate reliable "no breakout" (SIDEWAYS)
read (sections 5, 28).
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
class BreakoutAnalysis:
    """Deterministic channel-breakout read for one instrument."""

    instrument: Instrument
    timeframe_value: str
    lookback: int  # channel window actually used
    has_breakout: bool
    direction: Direction  # UP = breakout, DOWN = breakdown, SIDEWAYS = inside channel
    confidence: Confidence
    channel_high: float | None
    channel_low: float | None
    last_close: float | None
    volume_ratio: float | None  # last volume / channel average volume
    volume_confirmed: bool
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

        Mock or unusable data, or an UNKNOWN read (too thin to judge), is never
        reliable. A determinate "no breakout" (SIDEWAYS) read on usable, non-mock
        data *is* reliable: a close inside the channel is a real result.
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
            "lookback": self.lookback,
            "has_breakout": self.has_breakout,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "channel_high": self.channel_high,
            "channel_low": self.channel_low,
            "last_close": self.last_close,
            "volume_ratio": self.volume_ratio,
            "volume_confirmed": self.volume_confirmed,
            "is_reliable": self.is_reliable,
            "observation": self.observation,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
