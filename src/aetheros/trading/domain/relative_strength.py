"""
Relative-strength (sector/benchmark) value object.

A ``RelativeStrengthAnalysis`` is the deterministic read of *how one instrument
has performed relative to a benchmark* over a fixed lookback window -- the
"Positive sector strength" line the spec's example reports cite (CLAUDE.md
sections 2, 27). It is the natural populator of ``EvidenceType.MARKET_CONTEXT``:
a computed comparison of two return series, not a prediction and carrying no
calibrated probability. Later layers (the report's evidence list, a future
critic check) consume it as situational context.

Like every trading value object it carries its own provenance, data-quality read
and limitations for *both* series, and it is honest about ignorance: mock,
unusable or too-thin data on *either* side produces ``Direction.UNKNOWN`` with
``is_reliable`` False rather than a fabricated lean (sections 9, 15, 28). A
benchmark drawn from MOCK data can never make the read reliable, even when the
instrument's own data is real.
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
class RelativeStrengthAnalysis:
    """Deterministic relative-strength read of one instrument vs a benchmark."""

    instrument: Instrument
    benchmark_key: str
    timeframe_value: str
    lookback: int  # bars actually compared (<= requested, aligned to both series)
    instrument_return: float | None  # simple return over the window, or None
    benchmark_return: float | None
    relative_return: float | None  # instrument_return - benchmark_return (excess)
    direction: Direction  # UP=outperforming, DOWN=underperforming, SIDEWAYS=in-line
    confidence: Confidence
    quality: DataQuality  # the instrument series' quality (the primary subject)
    provenance: Provenance  # the instrument series' provenance
    benchmark_quality: DataQuality  # kept so a weak/mock benchmark is visible
    benchmark_provenance: Provenance
    evidence: Evidence | None = None  # MARKET_CONTEXT claim, only on a real read
    observation: str = ""
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def is_reliable(self) -> bool:
        """
        Whether this relative-strength read rests on data solid enough to lean on.

        Requires *both* series to be usable and non-mock and a determinate
        direction. A mock or unusable benchmark, or an UNKNOWN direction, is
        never reliable -- the honest answer there is "relative strength
        undetermined".
        """
        return (
            self.quality.usable
            and self.benchmark_quality.usable
            and not self.provenance.is_mock
            and not self.benchmark_provenance.is_mock
            and self.direction is not Direction.UNKNOWN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "benchmark": self.benchmark_key,
            "timeframe": self.timeframe_value,
            "lookback": self.lookback,
            "instrument_return": self.instrument_return,
            "benchmark_return": self.benchmark_return,
            "relative_return": self.relative_return,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "is_reliable": self.is_reliable,
            "observation": self.observation,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "benchmark_quality": self.benchmark_quality.to_dict(),
            "benchmark_provenance": self.benchmark_provenance.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
