"""
Historical-analogue value object.

A :class:`HistoricalAnalogueAnalysis` is the deterministic read of *what has
tended to happen after the setup looked like it does now* -- it finds the K past
bars whose causal feature vector most resembles the latest bar's, and reports
how those analogues resolved over a fixed forward horizon (their up-rate and
mean forward return). It is not a prediction and carries no calibrated
probability; it is situational, evidence-grade context that later layers (a
critic check, the composed report) can consume, and it populates the
previously-unpopulated ``EvidenceType.HISTORICAL`` line (CLAUDE.md sections 1, 7,
15, 27).

The read is look-ahead-safe by construction: analogues are only past bars whose
forward outcome is *fully realised*, and the latest bar's features are causal
(section 7/21). It is honest about ignorance: mock, unusable or too-thin history
yields ``Direction.UNKNOWN`` with ``is_reliable`` False and no fabricated
numbers, and an inconclusive analogue set (an up-rate near 50/50) is a
determinate reliable SIDEWAYS read (sections 2, 28, 61).
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
class HistoricalAnalogueAnalysis:
    """Deterministic nearest-analogue forward-outcome read for one instrument."""

    instrument: Instrument
    timeframe_value: str
    horizon: int  # forward bars each analogue's outcome was measured over
    sample_size: int  # labelled analogue rows available
    neighbors: int  # K nearest actually averaged
    direction: Direction
    confidence: Confidence
    up_rate: float | None  # fraction of the K analogues that rose over the horizon
    mean_forward_return: float | None  # mean realised forward return of the K
    mean_distance: float | None  # mean feature-space distance of the K (lower = closer)
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

        Mock or unusable data, or an UNKNOWN read (too little history to judge),
        is never reliable -- the honest answer there is "no analogue read". A
        determinate SIDEWAYS ("inconclusive") read on usable, non-mock data *is*
        reliable: measuring an even split is a real result.
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
            "horizon": self.horizon,
            "sample_size": self.sample_size,
            "neighbors": self.neighbors,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "up_rate": self.up_rate,
            "mean_forward_return": self.mean_forward_return,
            "mean_distance": self.mean_distance,
            "is_reliable": self.is_reliable,
            "observation": self.observation,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
