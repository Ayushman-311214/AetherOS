"""
The signal assessment -- the engine's full, explainable output.

A :class:`SignalAssessment` is what the engine produces for one instrument:
the direction the evidence leans, the honestly-separated scores (raw / model /
probability / confidence), the risk geometry (R:R, invalidation, targets,
expected move), the evidence and the *contradicting* evidence, and every
limitation. It is a probabilistic assessment, never a claim of certainty --
and it deliberately mirrors the spec's representation example
(direction/probability/confidence/expected_move/RR/invalidation) without ever
hard-coding an output.

Two fields carry the engine's core honesty contract:

* ``supporting`` / ``contradicting`` -- the evidence is split and *both* sides
  are carried, so a signal under disagreement shows it instead of hiding it.
* ``is_actionable`` / ``limitations`` -- an actionable signal needs reliable,
  agreeing, non-contradicted evidence AND actionable risk geometry; a thin or
  contradictory read is reported as such, not cleaned up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..domain.enums import Confidence, Direction, RiskBand
from ..domain.evidence import Evidence
from ..domain.instrument import Instrument
from .evidence import MissingSource
from .scoring import ScoreBreakdown


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SignalAssessment:
    """
    An evidence-based probabilistic signal for one instrument.

    ``direction`` is the leaned side (SIDEWAYS/UNKNOWN when there is no honest
    edge); ``probability_up`` is the calibrated estimate, ``None`` when not
    reliable -- the raw/model scores are separate and never masquerade as it.
    """

    instrument: Instrument
    timeframe: str

    # Direction and the four honestly-separated quantities.
    direction: Direction
    probability_up: float | None
    confidence: Confidence
    scores: ScoreBreakdown

    # The trade context (risk geometry) -- populated only when a directional,
    # actionable read exists. All Optional: no false precision.
    expected_move: str                # "up" | "down" | "sideways" | "unknown"
    time_horizon: str                 # the timeframe the read was made on
    risk_reward_ratio: float | None
    entry: float | None
    invalidation: str
    targets: tuple[float, ...]
    risk_band: RiskBand

    # The full evidence ledger -- both sides carried.
    supporting: tuple[Evidence, ...]
    contradicting: tuple[Evidence, ...]
    risk_factors: tuple[str, ...]

    # Missing-data accounting -- explicit, never assumed neutral.
    missing_sources: tuple[MissingSource, ...]
    coverage: float

    # Meta: actionable only when reliable + agreeing + actionable risk.
    is_actionable: bool
    is_mock: bool
    limitations: tuple[str, ...] = ()
    generated_at: datetime = field(default_factory=_utcnow)
    model: str = "deterministic-evidence/1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "probability": (
                {"up": self.probability_up, "down": 1.0 - self.probability_up}
                if self.probability_up is not None
                else None
            ),
            "confidence": self.confidence.value,
            "scores": self.scores.to_dict(),
            "expected_move": self.expected_move,
            "time_horizon": self.time_horizon,
            "risk_reward_ratio": self.risk_reward_ratio,
            "entry": self.entry,
            "invalidation": self.invalidation,
            "targets": list(self.targets),
            "risk_band": self.risk_band.value,
            "supporting": [e.to_dict() for e in self.supporting],
            "contradicting": [e.to_dict() for e in self.contradicting],
            "risk_factors": list(self.risk_factors),
            "missing_sources": [m.to_dict() for m in self.missing_sources],
            "coverage": self.coverage,
            "is_actionable": self.is_actionable,
            "is_mock": self.is_mock,
            "limitations": list(self.limitations),
            "model": self.model,
            "generated_at": self.generated_at.isoformat(),
        }
