"""
Aggregate prediction-performance value object (spec sections 6, 9, 28, 29).

Where a :class:`~aetheros.trading.domain.outcome.PredictionOutcome` answers "was
*this* prediction correct?", a :class:`PredictionPerformance` answers the next
question the spec insists on -- "is the system actually any good?" -- over a
batch of already-resolved outcomes. It is the "Evaluate" rung of the autonomous
loop (section 29) and the bundle of measures section 6 names: directional
accuracy, coverage, and (when the predictions carried calibrated probabilities)
Brier score and Expected Calibration Error via the shared quant calibration code.

Two honesty rules are structural here, exactly as for the outcomes it summarises:

* **Only resolved, graded outcomes count.** PENDING and UNRESOLVABLE outcomes
  are tallied for transparency but never enter accuracy or calibration -- a
  prediction that could not be judged is not evidence for or against the system.
* **A thin or mock sample is not a track record.** Fewer than the configured
  minimum of scored predictions, or any outcome resolved on MOCK data, yields
  ``is_reliable = False`` with an explicit limitation, so an aggregate can never
  read as proof of an edge it has not earned (sections 6, 9, 28).

The object computes nothing beyond counting and the calibration arithmetic; every
field traces to the outcomes it was handed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..quant.calibration import CalibrationReport


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class PredictionPerformance:
    """An auditable aggregate of many resolved predictions' outcomes."""

    sample_size: int
    resolved: int
    pending: int
    unresolvable: int

    # Directional grading (only RESOLVED, directional outcomes are scored).
    scored: int
    hits: int
    misses: int
    directional_accuracy: float | None = None
    coverage: float | None = None  # scored / resolved
    mean_realized_return: float | None = None

    # Probability calibration over predictions that carried a reliable P(up).
    probability_sample_size: int = 0
    calibration: CalibrationReport | None = None

    is_reliable: bool = False
    is_mock: bool = False
    limitations: tuple[str, ...] = ()
    generated_at: datetime = field(default_factory=_utcnow)

    @property
    def is_calibrated_sample(self) -> bool:
        """Whether any calibrated-probability predictions were available to grade."""
        return self.calibration is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_size": self.sample_size,
            "counts": {
                "resolved": self.resolved,
                "pending": self.pending,
                "unresolvable": self.unresolvable,
                "scored": self.scored,
                "hits": self.hits,
                "misses": self.misses,
            },
            "directional_accuracy": self.directional_accuracy,
            "coverage": self.coverage,
            "mean_realized_return": self.mean_realized_return,
            "probability_sample_size": self.probability_sample_size,
            # A calibration bundle is an out-of-sample measurement, never a
            # promise the next prediction will land (spec sections 3, 28).
            "calibration": (
                self.calibration.to_dict() if self.calibration is not None else None
            ),
            "is_reliable": self.is_reliable,
            "is_mock": self.is_mock,
            "limitations": list(self.limitations),
            "generated_at": self.generated_at.isoformat(),
        }
