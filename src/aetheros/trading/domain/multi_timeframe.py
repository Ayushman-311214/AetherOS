"""
Multi-timeframe confirmation value object.

A :class:`MultiTimeframeAnalysis` reads how an instrument's base-timeframe
directional lean sits against its higher-timeframe trend (CLAUDE.md section 5):
a call in the direction of the higher-timeframe trend is CONFIRMED and stronger;
one against it is a CONFLICT (a counter-trend call carries more risk); a
higher timeframe with no trend is NEUTRAL. It is not a prediction and carries no
calibrated probability; it is situational context, and the higher-timeframe
trend it surfaces is evidence-grade.

Like every trading value object it carries its own provenance and data-quality
read and is honest about ignorance: mock, unusable or too-thin data on *either*
timeframe yields ``TimeframeAlignment.UNKNOWN`` with ``is_reliable`` False and no
fabricated alignment (sections 5, 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction, TimeframeAlignment
from .evidence import Evidence
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MultiTimeframeAnalysis:
    """Deterministic base-vs-higher-timeframe confirmation read."""

    instrument: Instrument
    base_timeframe: str
    higher_timeframe: str
    base_direction: Direction
    higher_direction: Direction
    alignment: TimeframeAlignment
    confidence: Confidence
    quality: DataQuality  # base-timeframe data quality
    provenance: Provenance  # base-timeframe provenance
    higher_quality: DataQuality
    higher_provenance: Provenance
    evidence: Evidence | None = None
    observation: str = ""
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def direction(self) -> Direction:
        """The read's headline direction is the higher-timeframe trend (context)."""
        return self.higher_direction

    @property
    def is_reliable(self) -> bool:
        """
        Whether this read rests on data solid enough to lean on.

        Both timeframes must be usable and non-mock, and the higher timeframe
        must have a determinate direction -- otherwise the honest answer is
        "alignment undetermined".
        """
        return (
            self.quality.usable
            and self.higher_quality.usable
            and not self.provenance.is_mock
            and not self.higher_provenance.is_mock
            and self.higher_direction is not Direction.UNKNOWN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "base_timeframe": self.base_timeframe,
            "higher_timeframe": self.higher_timeframe,
            "base_direction": self.base_direction.value,
            "higher_direction": self.higher_direction.value,
            "alignment": self.alignment.value,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "is_reliable": self.is_reliable,
            "observation": self.observation,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "higher_quality": self.higher_quality.to_dict(),
            "higher_provenance": self.higher_provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
