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

Three times are distinguished on every record (Phase 16):

* ``event_time`` -- when the market event happened (the bar/candle time, the
  moment the regime held, the prediction's horizon target);
* ``ingested_at`` -- when this row was written to memory;
* ``evaluation_time`` -- when an outcome was resolved (outcomes only).

As-of retrieval filters on ``event_time``: asking "what did we know at T?"
sees only rows whose event predates T, so future outcomes can never leak
into historical backtests. ``ingested_at``/``evaluation_time`` answer the
companion questions "when did we record it?" and "when was it resolved?".

No record here computes trading results: probabilities, Brier scores,
returns and calibration numbers arrive caller-computed from the trading
subsystem and are stored verbatim (never invented, never recomputed).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import MemoryImportance, MemoryType, SourceType, Veracity
from .memory import Memory, MemorySource


def _utcnow() -> datetime:
    return datetime.now(UTC)


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


def _trading_memory(
    *,
    id: str,
    content: str,
    payload_key: str,
    payload: dict[str, Any],
    instrument: str,
    timeframe: str,
    event_time: datetime | None,
    tags: list[str],
    entities: list[str],
    metadata: dict[str, Any],
    confidence: float = 0.8,
) -> Memory:
    """Shared TRADING/OBSERVATION projection for history rows (Phase 16).

    Every row carries ``instrument_id`` + ``timeframe`` + ``event_time``
    metadata so as-of retrieval can filter without opening payloads.
    """
    meta = {
        "instrument_id": instrument,
        "timeframe": timeframe,
        **{k: v for k, v in metadata.items() if v is not None},
    }
    if event_time is not None:
        meta["event_time"] = event_time.isoformat()
    return Memory(
        id=id,
        content=content,
        memory_type=MemoryType.TRADING,
        veracity=Veracity.OBSERVATION,
        data={payload_key: payload},
        source=MemorySource(
            source_type=SourceType.OBSERVATION,
            origin="trading_history",
            detail={"kind": payload_key},
        ),
        confidence=confidence,
        importance=MemoryImportance.HIGH,
        tags=["trading", payload_key, *tags],
        entities=entities or [instrument],
        metadata=meta,
    )


@dataclass(slots=True)
class MarketRegimeMemory:
    """A remembered market-regime reading (from RegimeAnalysis, as plain data).

    A situational observation, not a forecast: what character the market was
    in at ``event_time`` (the bar time the read rests on), with the inputs
    that produced it (ADX/ATR) kept as evidence, not recomputed.
    """

    instrument: str
    regime: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeframe: str = ""
    venue: str | None = None
    direction: str = ""
    adx: float | None = None
    atr_pct: float | None = None
    reliable: bool = True
    source_tier: str = ""
    model_version: str = ""
    data_version: str = ""
    event_time: datetime | None = None
    ingested_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instrument": self.instrument,
            "regime": self.regime,
            "timeframe": self.timeframe,
            "venue": self.venue,
            "direction": self.direction,
            "adx": self.adx,
            "atr_pct": self.atr_pct,
            "reliable": self.reliable,
            "source_tier": self.source_tier,
            "model_version": self.model_version,
            "data_version": self.data_version,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "ingested_at": self.ingested_at.isoformat(),
        }

    def to_memory(self) -> Memory:
        return _trading_memory(
            id=self.id,
            content=(
                f"Regime on {self.instrument} ({self.timeframe}): {self.regime}."
            ),
            payload_key="regime",
            payload=self.to_dict(),
            instrument=self.instrument,
            timeframe=self.timeframe,
            event_time=self.event_time,
            tags=[self.regime.lower(), "reliable" if self.reliable else "unreliable"],
            entities=[self.instrument],
            metadata={
                "venue": self.venue,
                "model_version": self.model_version,
                "data_version": self.data_version,
            },
        )


@dataclass(slots=True)
class AnalysisSnapshotMemory:
    """A remembered historical analysis (from TradingAnalysis, as plain data).

    Direction, score, evidence references and limitations verbatim from the
    producing call. The ``as_of`` event time is when the analysed state held.
    """

    instrument: str
    direction: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeframe: str = ""
    venue: str | None = None
    last_price: float | None = None
    directional_score: float | None = None
    confidence_label: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    actionable: bool = False
    source_tier: str = ""
    model_version: str = ""
    data_version: str = ""
    event_time: datetime | None = None
    ingested_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instrument": self.instrument,
            "direction": self.direction,
            "timeframe": self.timeframe,
            "venue": self.venue,
            "last_price": self.last_price,
            "directional_score": self.directional_score,
            "confidence_label": self.confidence_label,
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "actionable": self.actionable,
            "source_tier": self.source_tier,
            "model_version": self.model_version,
            "data_version": self.data_version,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "ingested_at": self.ingested_at.isoformat(),
        }

    def to_memory(self) -> Memory:
        return _trading_memory(
            id=self.id,
            content=(
                f"Analysis on {self.instrument} ({self.timeframe}): "
                f"{self.direction}."
            ),
            payload_key="analysis",
            payload=self.to_dict(),
            instrument=self.instrument,
            timeframe=self.timeframe,
            event_time=self.event_time,
            tags=[self.direction.lower()],
            entities=[self.instrument],
            metadata={
                "venue": self.venue,
                "model_version": self.model_version,
                "data_version": self.data_version,
            },
        )


@dataclass(slots=True)
class StrategyObservationMemory:
    """A remembered strategy evaluation (from StrategyEvaluation, as plain data).

    Whether the strategy fired or found no setup, with the rule matches and
    the setup reference kept verbatim. Never revises procedure behavior --
    that is a later phase's consumer of this evidence.
    """

    strategy_id: str
    instrument: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    strategy_name: str = ""
    timeframe: str = ""
    venue: str | None = None
    fired: bool = False
    rules_matched: list[str] = field(default_factory=list)
    setup_ref: str | None = None
    limitations: list[str] = field(default_factory=list)
    event_time: datetime | None = None
    ingested_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "instrument": self.instrument,
            "strategy_name": self.strategy_name,
            "timeframe": self.timeframe,
            "venue": self.venue,
            "fired": self.fired,
            "rules_matched": list(self.rules_matched),
            "setup_ref": self.setup_ref,
            "limitations": list(self.limitations),
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "ingested_at": self.ingested_at.isoformat(),
        }

    def to_memory(self) -> Memory:
        state = "fired" if self.fired else "no setup"
        return _trading_memory(
            id=self.id,
            content=(
                f"Strategy {self.strategy_id} on {self.instrument} "
                f"({self.timeframe}): {state}."
            ),
            payload_key="strategy_observation",
            payload=self.to_dict(),
            instrument=self.instrument,
            timeframe=self.timeframe,
            event_time=self.event_time,
            tags=[self.strategy_id.lower(), state.replace(" ", "_")],
            entities=[self.instrument],
            metadata={"venue": self.venue},
        )


@dataclass(slots=True)
class CalibrationRecordMemory:
    """A remembered calibration audit (caller-computed numbers, stored verbatim).

    This row never computes calibration itself -- Brier, bias, sample size
    and any proposed correction arrive from the trading calibration service
    and are preserved exactly, so later phases can answer "where have we
    historically been poorly calibrated?".
    """

    scope: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    instrument: str = ""
    timeframe: str = ""
    sample_size: int = 0
    brier: float | None = None
    baseline_brier: float | None = None
    mean_predicted: float | None = None
    realised_rate: float | None = None
    bias: str = ""
    trustworthy: bool = False
    proposed_correction: dict[str, Any] = field(default_factory=dict)
    model_version: str = ""
    data_version: str = ""
    event_time: datetime | None = None
    ingested_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scope": self.scope,
            "instrument": self.instrument,
            "timeframe": self.timeframe,
            "sample_size": self.sample_size,
            "brier": self.brier,
            "baseline_brier": self.baseline_brier,
            "mean_predicted": self.mean_predicted,
            "realised_rate": self.realised_rate,
            "bias": self.bias,
            "trustworthy": self.trustworthy,
            "proposed_correction": dict(self.proposed_correction),
            "model_version": self.model_version,
            "data_version": self.data_version,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "ingested_at": self.ingested_at.isoformat(),
        }

    def to_memory(self) -> Memory:
        return _trading_memory(
            id=self.id,
            content=f"Calibration audit ({self.scope}): {self.bias or 'n/a'}.",
            payload_key="calibration",
            payload=self.to_dict(),
            instrument=self.instrument,
            timeframe=self.timeframe,
            event_time=self.event_time,
            tags=[self.scope.lower()],
            entities=[self.instrument] if self.instrument else [],
            metadata={
                "model_version": self.model_version,
                "data_version": self.data_version,
            },
        )


@dataclass(slots=True)
class ReasoningSummaryMemory:
    """An attributable reasoning summary: what was concluded, from what.

    A summary, never primary evidence: ``source_refs`` names the memory ids
    (predictions, outcomes, analyses, failures) the reasoning drew on, and
    retrieval can expand from the summary to each source. Nothing is
    invented -- uncited claims do not belong here.
    """

    conclusion: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    instrument: str = ""
    timeframe: str = ""
    venue: str | None = None
    source_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    event_time: datetime | None = None
    ingested_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conclusion": self.conclusion,
            "instrument": self.instrument,
            "timeframe": self.timeframe,
            "venue": self.venue,
            "source_refs": list(self.source_refs),
            "limitations": list(self.limitations),
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "ingested_at": self.ingested_at.isoformat(),
        }

    def to_memory(self) -> Memory:
        return _trading_memory(
            id=self.id,
            content=f"Reasoning summary: {self.conclusion}",
            payload_key="reasoning_summary",
            payload=self.to_dict(),
            instrument=self.instrument,
            timeframe=self.timeframe,
            event_time=self.event_time,
            tags=["reasoning"],
            entities=[self.instrument] if self.instrument else [],
            metadata={"venue": self.venue},
        )
