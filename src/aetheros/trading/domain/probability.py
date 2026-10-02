"""
Probability-estimate value objects (spec sections 3, 6, 8).

:class:`ProbabilityEstimate` is the auditable output of the quant probability
layer: a calibrated P(up)/P(down) for a defined instrument, timeframe and
horizon, tagged with the model, the calibration method, the out-of-sample
metrics that justify trusting it, and -- crucially -- an ``is_reliable`` flag
and ``limitations`` that say plainly when it should NOT be trusted. A number
that fails its own honesty gates is still returned (so the reason is visible),
but ``is_reliable`` is ``False`` and downstream layers must not surface it as a
signal. This is the spec's central rule made structural: a probability is an
estimate under stated conditions, never a guarantee, and "insufficient
evidence" is preferred over a fabricated edge (sections 2, 3, 28, 61).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Confidence, Direction
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class CalibrationMetrics:
    """Out-of-sample calibration/accuracy measures over one evaluation slice."""

    brier: float
    log_loss: float
    accuracy: float
    ece: float
    base_rate: float
    sample_size: int
    reliability_bins: tuple[dict[str, float], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "brier": self.brier,
            "log_loss": self.log_loss,
            "accuracy": self.accuracy,
            "ece": self.ece,
            "base_rate": self.base_rate,
            "sample_size": self.sample_size,
            "reliability_bins": [dict(b) for b in self.reliability_bins],
        }


@dataclass(frozen=True, slots=True)
class ProbabilityEstimate:
    """A calibrated directional probability with its full audit trail."""

    instrument: Instrument
    timeframe_value: str
    horizon: int
    model_name: str
    model_version: str
    calibration_method: str
    feature_names: tuple[str, ...]
    raw_p_up: float
    p_up: float
    p_down: float
    direction: Direction
    confidence: Confidence
    is_reliable: bool
    provenance: Provenance
    quality: DataQuality
    train_metrics: CalibrationMetrics | None = None
    holdout_metrics: CalibrationMetrics | None = None
    baseline_brier: float | None = None
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe_value,
            "horizon": self.horizon,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            # Probabilities are estimates under the stated conditions, never
            # guarantees (spec sections 3, 28).
            "probability": {
                "up": self.p_up,
                "down": self.p_down,
            },
            "raw_probability_up": self.raw_p_up,
            "is_reliable": self.is_reliable,
            "model": {
                "name": self.model_name,
                "version": self.model_version,
                "calibration": self.calibration_method,
                "features": list(self.feature_names),
            },
            "baseline_brier": self.baseline_brier,
            "train_metrics": self.train_metrics.to_dict() if self.train_metrics else None,
            "holdout_metrics": (
                self.holdout_metrics.to_dict() if self.holdout_metrics else None
            ),
            "limitations": list(self.limitations),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
            "created_at": self.created_at.isoformat(),
        }
