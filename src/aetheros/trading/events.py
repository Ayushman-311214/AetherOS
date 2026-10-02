"""
Trading-domain events.

Published on the shared EventBus so other subsystems (logging, monitoring,
future memory) can react to trading activity without the trading services
depending on them (CLAUDE.md section 16). Payloads are kept to plain,
already-serialised dicts so the events stay decoupled from the domain objects'
internal shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..runtime.events.events import Event


@dataclass(frozen=True, slots=True)
class MarketDataUpdated(Event):
    """Fresh (or refreshed) market data became available for an instrument."""

    instrument_key: str = ""
    timeframe: str = ""
    candle_count: int = 0
    last_price: float | None = None
    source_tier: str = ""
    quality_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "candle_count": self.candle_count,
            "last_price": self.last_price,
            "source_tier": self.source_tier,
            "quality_status": self.quality_status,
        }


@dataclass(frozen=True, slots=True)
class AnalysisCompleted(Event):
    """A deterministic TradingAnalysis was produced for an instrument."""

    instrument_key: str = ""
    timeframe: str = ""
    direction: str = ""
    confidence: str = ""
    directional_score: float = 0.0
    is_actionable: bool = False
    evidence_count: int = 0
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "confidence": self.confidence,
            "directional_score": self.directional_score,
            "is_actionable": self.is_actionable,
            "evidence_count": self.evidence_count,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class RiskAssessed(Event):
    """A deterministic risk plan was produced for a directional trade idea."""

    instrument_key: str = ""
    direction: str = ""
    entry: float | None = None
    stop_loss: float | None = None
    risk_reward_ratio: float | None = None
    overall_risk: str = ""
    is_actionable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "direction": self.direction,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "risk_reward_ratio": self.risk_reward_ratio,
            "overall_risk": self.overall_risk,
            "is_actionable": self.is_actionable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class BacktestCompleted(Event):
    """A deterministic walk-forward backtest of a signal was completed."""

    instrument_key: str = ""
    timeframe: str = ""
    horizon: int = 0
    evaluated: int = 0
    directional_accuracy: float | None = None
    base_rate_up: float | None = None
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "evaluated": self.evaluated,
            "directional_accuracy": self.directional_accuracy,
            "base_rate_up": self.base_rate_up,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class SignalCritiqued(Event):
    """The critic returned a go/no-go verdict on a proposed signal."""

    instrument_key: str = ""
    direction: str = ""
    verdict: str = ""
    approved: bool = False
    check_count: int = 0
    failed_checks: int = 0
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "direction": self.direction,
            "verdict": self.verdict,
            "approved": self.approved,
            "check_count": self.check_count,
            "failed_checks": self.failed_checks,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class ProbabilityEstimated(Event):
    """A calibrated directional probability was estimated for an instrument."""

    instrument_key: str = ""
    timeframe: str = ""
    horizon: int = 0
    direction: str = ""
    p_up: float | None = None
    holdout_brier: float | None = None
    baseline_brier: float | None = None
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "direction": self.direction,
            "p_up": self.p_up,
            "holdout_brier": self.holdout_brier,
            "baseline_brier": self.baseline_brier,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class NewsSentimentAnalyzed(Event):
    """A deterministic news-sentiment read was produced for an instrument."""

    instrument_key: str = ""
    direction: str = ""
    sentiment_score: float = 0.0
    confidence: str = ""
    item_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "direction": self.direction,
            "sentiment_score": self.sentiment_score,
            "confidence": self.confidence,
            "item_count": self.item_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class MarketEventsDetected(Event):
    """A deterministic event-calendar lookup was produced for an instrument."""

    instrument_key: str = ""
    horizon_days: int = 0
    event_count: int = 0
    has_high_impact: bool = False
    next_event_type: str = ""
    next_event_days: float | None = None
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "horizon_days": self.horizon_days,
            "event_count": self.event_count,
            "has_high_impact": self.has_high_impact,
            "next_event_type": self.next_event_type,
            "next_event_days": self.next_event_days,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class FundamentalsAnalyzed(Event):
    """A deterministic fundamental read was produced for an instrument."""

    instrument_key: str = ""
    direction: str = ""
    health_score: float = 0.0
    confidence: str = ""
    scored_metric_count: int = 0
    reported_metric_count: int = 0
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "direction": self.direction,
            "health_score": self.health_score,
            "confidence": self.confidence,
            "scored_metric_count": self.scored_metric_count,
            "reported_metric_count": self.reported_metric_count,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class MarketRegimeDetected(Event):
    """
    A deterministic market-regime classification was produced for an instrument.

    Named "detected", not "changed": this build keeps no prior-regime memory to
    diff against, so it honestly reports the regime it read *now* rather than
    claiming a transition it cannot verify. A ``MarketRegimeChanged`` transition
    event awaits the deferred memory/state layer (CLAUDE.md sections 15, 16, 28).
    """

    instrument_key: str = ""
    timeframe: str = ""
    regime: str = ""
    adx: float | None = None
    atr_pct: float | None = None
    trend_strength: float | None = None
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "regime": self.regime,
            "adx": self.adx,
            "atr_pct": self.atr_pct,
            "trend_strength": self.trend_strength,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class TradingReportGenerated(Event):
    """A composed, deterministic trading report was assembled for an instrument."""

    instrument_key: str = ""
    timeframe: str = ""
    recommendation: str = ""
    direction: str = ""
    confidence: str = ""
    verdict: str = ""
    is_actionable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "recommendation": self.recommendation,
            "direction": self.direction,
            "confidence": self.confidence,
            "verdict": self.verdict,
            "is_actionable": self.is_actionable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class PredictionCreated(Event):
    """
    A trading report was produced and captured as an auditable section-8
    prediction contract (spec sections 8, 16, 19, 28).

    Announced whenever the orchestrator finishes a report -- including a NO_TRADE
    decision, which is a genuine, auditable "we chose not to act" and is recorded
    verbatim, never upgraded into a confident call. ``probability_up`` is present
    only when the report surfaced a *reliable* calibrated estimate; a MOCK or thin
    read leaves it ``None`` (the event never invents a number the report refused
    to state). ``is_mock`` marks a prediction resting on synthetic data, which can
    never later read as a real track record.
    """

    prediction_id: str = ""
    instrument_key: str = ""
    timeframe: str = ""
    recommendation: str = ""
    direction: str = ""
    confidence: str = ""
    is_actionable: bool = False
    probability_up: float | None = None
    horizon_bars: int = 0
    model_pipeline: str = ""
    source_tier: str = ""
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "prediction_id": self.prediction_id,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "recommendation": self.recommendation,
            "direction": self.direction,
            "confidence": self.confidence,
            "is_actionable": self.is_actionable,
            "probability_up": self.probability_up,
            "horizon_bars": self.horizon_bars,
            "model_pipeline": self.model_pipeline,
            "source_tier": self.source_tier,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class PredictionResolved(Event):
    """
    A past prediction was checked against the market that unfolded after it.

    Published only when a prediction genuinely RESOLVED -- its horizon elapsed in
    the available data and the realised move was measured. A prediction still
    within its horizon (PENDING) or one whose entry bar cannot be located
    (UNRESOLVABLE) is not announced as an outcome, because there is nothing yet
    to report honestly (spec sections 6, 16, 29). ``is_correct`` is ``None`` for
    a resolved but non-directional call, which has no directional bet to score.
    """

    prediction_id: str = ""
    instrument_key: str = ""
    timeframe: str = ""
    predicted_direction: str = ""
    realized_direction: str = ""
    is_correct: bool | None = None
    realized_return: float | None = None
    brier_contribution: float | None = None
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "prediction_id": self.prediction_id,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "predicted_direction": self.predicted_direction,
            "realized_direction": self.realized_direction,
            "is_correct": self.is_correct,
            "realized_return": self.realized_return,
            "brier_contribution": self.brier_contribution,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class PredictionPerformanceEvaluated(Event):
    """
    An aggregate performance/calibration read was produced over a batch of
    already-resolved prediction outcomes -- the "Evaluate" step of the autonomous
    loop (spec sections 6, 29).

    ``is_reliable`` is ``False`` whenever the scored sample is thinner than the
    configured minimum or any contributing outcome was resolved on MOCK data: an
    aggregate is never announced as a track record it has not earned (sections 6,
    9, 28). ``directional_accuracy``, ``brier`` and ``ece`` may be ``None`` when
    no scored (respectively, no calibrated-probability) outcomes were available.
    """

    sample_size: int = 0
    resolved: int = 0
    scored: int = 0
    directional_accuracy: float | None = None
    coverage: float | None = None
    brier: float | None = None
    ece: float | None = None
    probability_sample_size: int = 0
    is_reliable: bool = False
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "sample_size": self.sample_size,
            "resolved": self.resolved,
            "scored": self.scored,
            "directional_accuracy": self.directional_accuracy,
            "coverage": self.coverage,
            "brier": self.brier,
            "ece": self.ece,
            "probability_sample_size": self.probability_sample_size,
            "is_reliable": self.is_reliable,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class MonitoringSweepCompleted(Event):
    """
    One monitoring sweep over the recorded predictions completed -- the bounded,
    repeatable "Observe Result -> Evaluate" pass of the autonomous loop (spec
    sections 16, 29). It resolves the outstanding predictions against the freshest
    market data and reports how the batch broke down, plus the aggregate.

    This is a single pass, not a running background loop: a scheduler may call it
    repeatedly, but the sweep itself is bounded and deterministic. ``is_reliable``
    follows the aggregate's own gate -- a sweep over a thin or MOCK sample is
    reported, never announced as an earned track record (sections 6, 28).
    """

    swept: int = 0
    resolved: int = 0
    pending: int = 0
    unresolvable: int = 0
    scored: int = 0
    directional_accuracy: float | None = None
    is_reliable: bool = False
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "swept": self.swept,
            "resolved": self.resolved,
            "pending": self.pending,
            "unresolvable": self.unresolvable,
            "scored": self.scored,
            "directional_accuracy": self.directional_accuracy,
            "is_reliable": self.is_reliable,
            "is_mock": self.is_mock,
        }
