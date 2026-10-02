"""
Aggregate analysis value objects.

VolumeAnalysis is a small structured read of recent volume behaviour.

TradingAnalysis is the top-level *deterministic* product of the numerical
core: it ties together the instrument, the technical snapshot, the market
structure, the collected evidence and an overall directional lean -- with an
explicit data-quality read and a list of limitations. It is deliberately NOT a
prediction with calibrated probabilities (that belongs to the later quant /
calibration layers); it is the evidence-grounded situation report those layers
consume. Nothing here requires an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction
from .evidence import Evidence
from .instrument import Instrument
from .provenance import DataQuality, Provenance
from .structure import MarketStructure
from .technical import TechnicalSnapshot


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class VolumeAnalysis:
    last_volume: float
    average_volume: float
    relative_volume: float  # last / average
    trend: str  # "rising" | "falling" | "flat"
    observation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_volume": self.last_volume,
            "average_volume": self.average_volume,
            "relative_volume": self.relative_volume,
            "trend": self.trend,
            "observation": self.observation,
        }


@dataclass(frozen=True, slots=True)
class TradingAnalysis:
    """Deterministic, evidence-grounded situation report for one instrument."""

    instrument: Instrument
    timeframe_value: str
    last_price: float
    direction: Direction
    directional_score: float  # net signed lean in [-1, 1], derived
    confidence: Confidence
    technical: TechnicalSnapshot
    structure: MarketStructure
    evidence: tuple[Evidence, ...]
    volume: VolumeAnalysis | None
    quality: DataQuality
    provenance: Provenance
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def is_actionable(self) -> bool:
        """
        Whether this analysis rests on data solid enough to act on.

        Mock or unusable data, or an outright UNKNOWN direction, is never
        actionable -- the honest answer there is "insufficient evidence".
        """
        return (
            self.quality.usable
            and not self.provenance.is_mock
            and self.direction is not Direction.UNKNOWN
            and bool(self.evidence)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe_value,
            "last_price": self.last_price,
            "direction": self.direction.value,
            "directional_score": self.directional_score,
            "confidence": self.confidence.value,
            "is_actionable": self.is_actionable,
            "technical": self.technical.to_dict(),
            "structure": self.structure.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "volume": self.volume.to_dict() if self.volume else None,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
