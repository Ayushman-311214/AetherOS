"""
Statistical-anomaly value object.

An :class:`AnomalyAnalysis` is the deterministic read of *whether the most
recent bar is a statistical outlier* against the instrument's own recent
history -- an unusually large return, an unusual volume, or an unusual overnight
gap, each measured as a z-score versus a trailing baseline. It is not a
prediction and carries no calibrated probability; it is situational context that
later layers (a critic check, the composed report) can consume, and it populates
the previously-unpopulated ``EvidenceType.ANOMALY`` line (CLAUDE.md sections 5,
9, 27).

Like every trading value object it carries its own provenance, data-quality read
and limitations, and it is honest about ignorance: mock, unusable or too-thin
data produces ``Direction.UNKNOWN`` with ``is_reliable`` False and no fabricated
z-scores, and a quiet tape with no outlier is a *determinate* reliable
"no anomaly" read rather than an invented event (sections 2, 28, 61).
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
class AnomalyAnalysis:
    """Deterministic last-bar statistical-outlier read for one instrument."""

    instrument: Instrument
    timeframe_value: str
    lookback: int  # trailing baseline bars actually used
    is_anomalous: bool
    return_z: float | None  # z-score of the last simple return, or None
    volume_z: float | None  # z-score of the last volume, or None
    gap_z: float | None  # z-score of the last overnight gap, or None
    last_return: float | None  # last simple return, for narration
    direction: Direction
    confidence: Confidence
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
        reliable -- the honest answer there is "anomaly undetermined". A
        determinate "no anomaly" (SIDEWAYS) read on usable, non-mock data *is*
        reliable: measuring a quiet tape is a real result.
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
            "is_anomalous": self.is_anomalous,
            "return_z": self.return_z,
            "volume_z": self.volume_z,
            "gap_z": self.gap_z,
            "last_return": self.last_return,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "is_reliable": self.is_reliable,
            "observation": self.observation,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
