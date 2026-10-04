"""
Trading-memory records (spec Phase 16).

Memory does **not** reproduce the Trading Intelligence domain -- it stores the
*history* of what that subsystem produced and how those calls turned out, so the
system can later answer "what happened last time a similar setup occurred?" and
"where have we historically been poorly calibrated?".

Two hard rules from the project spec shape these records:

* **Provenance is preserved** -- every record keeps the model/version and data
  version it came from (section 8, Rule 8).
* **History is immutable** -- a :class:`PredictionMemory` is never rewritten
  once its outcome is known (section 16, Rule 4). The realised result is a
  *separate* :class:`PredictionOutcomeMemory` that references it, so the
  original call stands untouched for audit.

The payloads are plain dicts rather than trading-domain objects, keeping the
memory layer decoupled from the trading package's internal shapes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import MemoryImportance, MemoryType, SourceType, Veracity
from .memory import Memory, MemorySource


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class PredictionMemory:
    """
    An audit record of one produced prediction (spec section 8 contract).

    Immutable by convention: once written it is not edited. A later outcome is
    attached as a separate :class:`PredictionOutcomeMemory`.
    """

    instrument: str
    direction: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeframe: str = ""
    horizon: str = ""
    prob_up: float | None = None
    prob_sideways: float | None = None
    prob_down: float | None = None
    confidence: str = ""
    risk_reward: float | None = None
    invalidation: str = ""
    regime: str = ""
    evidence: list[str] = field(default_factory=list)
    model: str = ""
    model_version: str = ""
    data_version: str = ""
    source_tier: str = ""
    predicted_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instrument": self.instrument,
            "direction": self.direction,
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "prob_up": self.prob_up,
            "prob_sideways": self.prob_sideways,
            "prob_down": self.prob_down,
            "confidence": self.confidence,
            "risk_reward": self.risk_reward,
            "invalidation": self.invalidation,
            "regime": self.regime,
            "evidence": list(self.evidence),
            "model": self.model,
            "model_version": self.model_version,
            "data_version": self.data_version,
            "source_tier": self.source_tier,
            "predicted_at": self.predicted_at.isoformat(),
        }

    def to_memory(self) -> Memory:
        prob = f"{self.prob_up:.0%}" if self.prob_up is not None else "n/a"
        return Memory(
            id=self.id,
            content=(
                f"Prediction {self.direction} on {self.instrument} "
                f"({self.timeframe}, horizon {self.horizon}): P(up)={prob}."
            ),
            memory_type=MemoryType.TRADING,
            # A prediction is a PREDICTION, never a FACT (CLAUDE.md section 15).
            veracity=Veracity.PREDICTION,
            data={"prediction": self.to_dict()},
            source=MemorySource(
                source_type=SourceType.PREDICTION,
                origin=self.model or "trading",
                reference=self.model_version or None,
                detail={"source_tier": self.source_tier},
            ),
            confidence=0.5,  # the record is certain; the *claim* is probabilistic
            importance=MemoryImportance.HIGH,
            tags=["trading", "prediction", self.instrument.lower(), self.direction.lower()],
            entities=[self.instrument],
            metadata={
                "instrument_id": self.instrument,
                "timeframe": self.timeframe,
                "model_version": self.model_version,
                "data_version": self.data_version,
            },
        )


@dataclass(slots=True)
class PredictionOutcomeMemory:
    """
    The realised outcome of a past prediction (spec section 16, Phase 13).

    References the original :class:`PredictionMemory` by id and carries the
    calibration signal (Brier contribution) the learning layer aggregates.
    This is an OBSERVATION of what actually happened -- it is appended, and it
    never mutates the original prediction.
    """

    prediction_id: str
    instrument: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    realized_direction: str = ""
    correct: bool | None = None
    realized_return: float | None = None
    brier: float | None = None
    predicted_prob_up: float | None = None
    notes: str = ""
    resolved_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "instrument": self.instrument,
            "realized_direction": self.realized_direction,
            "correct": self.correct,
            "realized_return": self.realized_return,
            "brier": self.brier,
            "predicted_prob_up": self.predicted_prob_up,
            "notes": self.notes,
            "resolved_at": self.resolved_at.isoformat(),
        }

    def to_memory(self) -> Memory:
        verdict = (
            "correct" if self.correct else "incorrect" if self.correct is not None else "unresolved"
        )
        return Memory(
            id=self.id,
            content=(
                f"Outcome for prediction {self.prediction_id} on {self.instrument}: "
                f"{self.realized_direction or 'n/a'} ({verdict})."
            ),
            memory_type=MemoryType.TRADING,
            veracity=Veracity.OBSERVATION,
            data={"outcome": self.to_dict()},
            source=MemorySource(
                source_type=SourceType.OBSERVATION,
                origin="prediction_evaluator",
                reference=self.prediction_id,
            ),
            confidence=0.95,
            importance=MemoryImportance.HIGH,
            tags=["trading", "outcome", self.instrument.lower(), verdict],
            entities=[self.instrument],
            metadata={"instrument_id": self.instrument, "prediction_id": self.prediction_id},
        )
