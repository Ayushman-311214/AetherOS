"""
Prediction-outcome value object (spec sections 6, 15, 16, 29).

A :class:`PredictionOutcome` is the auditable answer to the question the spec
insists AetherOS keep asking -- "was the previous prediction correct?" -- for a
single :class:`~aetheros.trading.domain.prediction.PredictionRecord` checked
against the market that unfolded after it. It is what the "Observe Result ->
Evaluate" step of the autonomous loop (section 29) produces, and the raw
material a later Memory/monitoring layer will aggregate into calibration and
performance metrics (sections 6, 15).

Two honesty rules are structural here:

* **Never a fabricated verdict.** A prediction whose horizon has not yet elapsed
  in the available data is ``PENDING`` and one whose entry bar cannot be located
  is ``UNRESOLVABLE`` -- neither is scored as a hit or a miss. Only a genuinely
  ``RESOLVED`` outcome carries ``is_correct``, and even then a non-directional
  call (SIDEWAYS/UNKNOWN, or a NO_TRADE report) has no directional bet to score,
  so ``is_correct`` stays ``None`` (sections 2, 28, 61).
* **A mock resolution is not a track record.** Resolving a prediction on
  synthetic data validates the scoring machinery, not a real forecasting edge;
  such an outcome is flagged ``is_reliable = False`` with an explicit
  limitation, so it can never later read as evidence the system predicts well
  (sections 9, 15, 28).

The outcome computes nothing beyond the arithmetic of the realised move; every
field traces to the record it judged and the candles it read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Direction, PredictionOutcomeStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class PredictionOutcome:
    """The auditable result of checking one prediction against later market data."""

    prediction_id: str
    instrument_key: str
    timeframe: str
    status: PredictionOutcomeStatus

    predicted_direction: Direction
    # Populated only for a RESOLVED outcome; None while PENDING/UNRESOLVABLE.
    realized_direction: Direction | None = None
    # True/False only for a RESOLVED *directional* prediction; None otherwise
    # (a non-directional call has no directional bet to score).
    is_correct: bool | None = None

    entry_timestamp: datetime | None = None
    exit_timestamp: datetime | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    realized_return: float | None = None
    horizon_bars: int = 0
    bars_elapsed: int = 0

    # Per-prediction calibration error, present only when the record carried a
    # reliable calibrated P(up): the Brier contribution (p_up - y)^2 with
    # y = 1 if the realised move was up else 0.
    predicted_p_up: float | None = None
    brier_contribution: float | None = None

    is_reliable: bool = False
    is_mock: bool = False
    limitations: tuple[str, ...] = ()
    resolved_at: datetime = field(default_factory=_utcnow)
    reason: str = ""

    @property
    def is_resolved(self) -> bool:
        return self.status is PredictionOutcomeStatus.RESOLVED

    @property
    def is_scored(self) -> bool:
        """A resolved, directional outcome that was actually graded hit/miss."""
        return self.is_correct is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "status": self.status.value,
            "predicted_direction": self.predicted_direction.value,
            "realized_direction": (
                self.realized_direction.value
                if self.realized_direction is not None
                else None
            ),
            "is_correct": self.is_correct,
            "entry_timestamp": (
                self.entry_timestamp.isoformat() if self.entry_timestamp else None
            ),
            "exit_timestamp": (
                self.exit_timestamp.isoformat() if self.exit_timestamp else None
            ),
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "realized_return": self.realized_return,
            "horizon_bars": self.horizon_bars,
            "bars_elapsed": self.bars_elapsed,
            # A probability outcome is an estimate checked against one draw, never
            # a guarantee that was kept or broken (spec sections 3, 28).
            "predicted_p_up": self.predicted_p_up,
            "brier_contribution": self.brier_contribution,
            "is_reliable": self.is_reliable,
            "is_mock": self.is_mock,
            "limitations": list(self.limitations),
            "resolved_at": self.resolved_at.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PredictionOutcome":
        """
        Rebuild an outcome from its :meth:`to_dict` form (durable read-back).

        The inverse of :meth:`to_dict`, so a durable outcome store serialises with
        the former and reconstructs with this without loss. Enums and ISO
        timestamps are parsed back; absent optionals stay ``None``.
        """

        def _dt(value: Any) -> datetime | None:
            if value is None:
                return None
            return value if isinstance(value, datetime) else datetime.fromisoformat(value)

        realized = data.get("realized_direction")
        return cls(
            prediction_id=data["prediction_id"],
            instrument_key=data["instrument_key"],
            timeframe=data["timeframe"],
            status=PredictionOutcomeStatus(data["status"]),
            predicted_direction=Direction(data["predicted_direction"]),
            realized_direction=Direction(realized) if realized is not None else None,
            is_correct=data.get("is_correct"),
            entry_timestamp=_dt(data.get("entry_timestamp")),
            exit_timestamp=_dt(data.get("exit_timestamp")),
            entry_price=data.get("entry_price"),
            exit_price=data.get("exit_price"),
            realized_return=data.get("realized_return"),
            horizon_bars=data.get("horizon_bars", 0),
            bars_elapsed=data.get("bars_elapsed", 0),
            predicted_p_up=data.get("predicted_p_up"),
            brier_contribution=data.get("brier_contribution"),
            is_reliable=data.get("is_reliable", False),
            is_mock=data.get("is_mock", False),
            limitations=tuple(data.get("limitations", ())),
            resolved_at=_dt(data.get("resolved_at")) or _utcnow(),
            reason=data.get("reason", ""),
        )
