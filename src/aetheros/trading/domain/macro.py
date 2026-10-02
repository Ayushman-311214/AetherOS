"""
Broad-market macro-context value object.

A :class:`MacroContext` is the deterministic read of *what the overall market is
doing* -- risk-on, risk-off or neutral -- derived from a market benchmark's own
regime (CLAUDE.md sections 2, 5, 27). It is the context a single-name signal sits
inside: a bullish name in a risk-off tape is riskier than the same name in a
risk-on one. It is not a prediction and carries no calibrated probability; it is
situational, evidence-grade context that later layers can consume, and it
populates the previously-unpopulated ``EvidenceType.MACRO`` line.

Like every trading value object it carries its own provenance, data-quality read
and limitations, and it is honest about ignorance: mock, unusable or too-thin
benchmark data produces ``MarketPosture.UNKNOWN`` with ``is_reliable`` False and
no fabricated posture (sections 5, 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction, MarketPosture, MarketRegime
from .evidence import Evidence
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MacroContext:
    """Deterministic broad-market risk-posture read from a benchmark."""

    benchmark: Instrument
    timeframe_value: str
    posture: MarketPosture
    regime: MarketRegime  # the benchmark regime the posture was derived from
    confidence: Confidence
    quality: DataQuality
    provenance: Provenance
    evidence: Evidence | None = None
    observation: str = ""
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def direction(self) -> Direction:
        """Directional bias implied by the posture (SIDEWAYS for neutral)."""
        return self.posture.direction

    @property
    def is_reliable(self) -> bool:
        """
        Whether this read rests on data solid enough to lean on.

        Mock or unusable benchmark data, or an UNKNOWN posture, is never
        reliable -- the honest answer there is "market context undetermined".
        """
        return (
            self.quality.usable
            and not self.provenance.is_mock
            and self.posture is not MarketPosture.UNKNOWN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark.to_dict(),
            "timeframe": self.timeframe_value,
            "posture": self.posture.value,
            "regime": self.regime.value,
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
