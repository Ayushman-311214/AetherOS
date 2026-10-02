"""
Calibration-audit value object.

A :class:`CalibrationAudit` is the honest first rung of "learn from historical
performance" (CLAUDE.md sections 6, 29): it measures how well the system's *past,
already-made* calibrated probabilities matched the outcomes that actually
unfolded, and -- only when the live track record is large enough to trust --
proposes a recalibration correction derived from that history.

It is pure measurement over the durable outcome record. Crucially it is
look-ahead-safe by construction: the correction is fit on *past* predictions
whose outcomes are now known, to be applied (in a later, explicitly-gated step)
to *future* estimates -- never to the predictions it was fit on. The audit never
modifies the live probability pipeline itself; it reports what the history says
and proposes, with the proposal gated on sample size so a thin or MOCK-sourced
live record can never drive a correction (sections 7, 28).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .provenance import DataQuality  # noqa: F401  (kept for parity; not required)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class CalibrationCorrection:
    """A holdout-validated recalibration map ``p' = sigmoid(a*p + b)``.

    Derived from the accumulated outcome history and validated OUT-OF-SAMPLE on a
    held-out tail before it is ``trusted``: a correction that does not improve the
    holdout Brier, or rests on too thin a sample, is retained for inspection with
    ``trusted = False`` and :meth:`apply` then leaves the probability unchanged --
    so a correction can never manufacture confidence it did not earn (spec
    sections 6, 7, 28).
    """

    a: float
    b: float
    trusted: bool
    sample_size: int
    holdout_size: int
    holdout_brier_before: float | None
    holdout_brier_after: float | None
    reason: str = ""

    @property
    def improves_holdout(self) -> bool:
        return (
            self.holdout_brier_before is not None
            and self.holdout_brier_after is not None
            and self.holdout_brier_after < self.holdout_brier_before
        )

    def apply(self, p_up: float) -> float:
        """Correct a probability -- but only when trusted; otherwise unchanged."""
        if not self.trusted:
            return p_up
        z = self.a * float(p_up) + self.b
        z = max(-30.0, min(30.0, z))
        return 1.0 / (1.0 + math.exp(-z))

    def to_dict(self) -> dict[str, Any]:
        return {
            "a": self.a,
            "b": self.b,
            "trusted": self.trusted,
            "sample_size": self.sample_size,
            "holdout_size": self.holdout_size,
            "holdout_brier_before": self.holdout_brier_before,
            "holdout_brier_after": self.holdout_brier_after,
            "improves_holdout": self.improves_holdout,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class CalibrationAudit:
    """Realised-calibration measurement over the accumulated prediction history."""

    instrument_key: str | None
    sample_size: int  # resolved, reliable, non-mock outcomes carrying a P(up)
    brier: float | None
    baseline_brier: float | None  # Brier of always predicting the base rate
    ece: float | None
    mean_predicted: float | None
    realized_up_rate: float | None  # the base rate the predictions are judged against
    bias: str  # "overconfident" | "underconfident" | "well_calibrated" | "unknown"
    reliability_bins: tuple[dict[str, float], ...]
    # A proposed secondary recalibration map p_corrected = sigmoid(a * p + b),
    # fit on the history. Present only when the sample clears the trust gate; it
    # is a *proposal*, not yet applied to the live pipeline.
    proposed_correction: tuple[float, float] | None
    beats_baseline: bool  # realised Brier better than the base-rate baseline
    is_reliable: bool  # sample large enough + non-mock to lean on
    observation: str = ""
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "sample_size": self.sample_size,
            "brier": self.brier,
            "baseline_brier": self.baseline_brier,
            "ece": self.ece,
            "mean_predicted": self.mean_predicted,
            "realized_up_rate": self.realized_up_rate,
            "bias": self.bias,
            "reliability_bins": [dict(b) for b in self.reliability_bins],
            "proposed_correction": (
                {"a": self.proposed_correction[0], "b": self.proposed_correction[1]}
                if self.proposed_correction is not None
                else None
            ),
            "beats_baseline": self.beats_baseline,
            "is_reliable": self.is_reliable,
            "observation": self.observation,
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
