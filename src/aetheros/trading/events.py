"""
Trading-domain events.

Published on the shared EventBus so other subsystems (logging, monitoring,
future memory) can react to trading activity without the trading services
depending on them (CLAUDE.md section 16). Payloads are kept to plain,
already-serialised dicts so the events stay decoupled from the domain objects'
internal shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..runtime.events.events import Event


@dataclass(frozen=True, slots=True)
class MarketOpened(Event):
    """A market session opened for an instrument or venue."""

    market: str = ""
    instrument_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "market": self.market,
            "instrument_key": self.instrument_key,
        }


@dataclass(frozen=True, slots=True)
class MarketDataReceived(Event):
    """
    A fresh market-data snapshot arrived and passed validation.

    This is the pull-based system's analogue of "data received on the wire": it
    fires when :meth:`MarketDataService.get_candles` returns a newly fetched
    series, before any per-bar ``CandleClosed`` events are replayed. It carries
    only the snapshot's own shape -- instrument, timeframe, bar count, the last
    bar's identity -- never a fabricated live-stream detail. ``is_mock`` is
    surfaced so a subscriber downstream can never mistake synthetic data for a
    real feed (CLAUDE.md section 9).
    """

    instrument_key: str = ""
    timeframe: str = ""
    candle_count: int = 0
    last_price: float | None = None
    first_bar_timestamp: str = ""
    last_bar_timestamp: str = ""
    source_tier: str = ""
    quality_status: str = ""
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "candle_count": self.candle_count,
            "last_price": self.last_price,
            "first_bar_timestamp": self.first_bar_timestamp,
            "last_bar_timestamp": self.last_bar_timestamp,
            "source_tier": self.source_tier,
            "quality_status": self.quality_status,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class CandleClosed(Event):
    """
    A single completed (closed) OHLCV bar became part of an instrument's series.

    AetherOS is pull-based: it fetches a *snapshot* of bars rather than a live
    tick stream. A candle in a delivered snapshot is by definition closed -- the
    provider only hands over bars whose period has elapsed -- so every bar the
    service surfaces is announced here as ``CandleClosed``. There is deliberately
    no ``CandleUpdated``: this build does not track a still-forming bar, and
    inventing one would pretend a granularity the data does not have (see the
    module docstring and docs/trading-intelligence/03-event-contracts.md).

    ``is_final_bar`` marks the last candle of the delivered series -- the bar a
    downstream subscriber usually acts on -- so a replaying consumer can emit the
    whole series yet a live one can filter to the newest close.
    """

    instrument_key: str = ""
    timeframe: str = ""
    index: int = 0
    is_final_bar: bool = False
    bar_timestamp: str = ""  # the candle's own open time (UTC, ISO) -- not the event's
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    source_tier: str = ""
    quality_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),  # event wall-clock time
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "index": self.index,
            "is_final_bar": self.is_final_bar,
            "bar_timestamp": self.bar_timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "source_tier": self.source_tier,
            "quality_status": self.quality_status,
        }


@dataclass(frozen=True, slots=True)
class OrderBookUpdated(Event):
    """
    An order-book (depth) snapshot became available for an instrument.

    Mirrors the pull-based design: it carries the *top* of the delivered book
    (best bid/ask, mid, spread, level counts) so a subscriber can react to
    microstructure without re-serialising every level. ``depth`` is the number
    of levels per side actually delivered -- the event reports what the source
    provided, never pads to a nominal depth (CLAUDE.md section 9).
    """

    instrument_key: str = ""
    bid_levels: int = 0
    ask_levels: int = 0
    best_bid: float | None = None
    best_ask: float | None = None
    mid_price: float | None = None
    spread: float | None = None
    book_timestamp: str = ""
    source_tier: str = ""
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "bid_levels": self.bid_levels,
            "ask_levels": self.ask_levels,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "mid_price": self.mid_price,
            "spread": self.spread,
            "book_timestamp": self.book_timestamp,
            "source_tier": self.source_tier,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class TradeReceived(Event):
    """
    A single executed trade print was reported for an instrument.

    Carries the print itself (price, amount, aggressor side) plus provenance.
    ``side`` is the aggressor: ``up`` = buyer-initiated, ``down`` = seller-initiated
    (matching ``TradeTick.side``). An event is only as honest as its source --
    ``is_mock`` keeps a synthetic print from reading as a real one.
    """

    instrument_key: str = ""
    price: float = 0.0
    amount: float = 0.0
    side: str = ""
    trade_timestamp: str = ""
    tick_id: str = ""
    source_tier: str = ""
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "price": self.price,
            "amount": self.amount,
            "side": self.side,
            "trade_timestamp": self.trade_timestamp,
            "tick_id": self.tick_id,
            "source_tier": self.source_tier,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class SignalGenerated(Event):
    """An evidence-backed proposed trade action was generated."""

    signal_id: str = ""
    instrument_key: str = ""
    action: str = ""
    direction: str = ""
    confidence: str = ""
    risk: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "signal_id": self.signal_id,
            "instrument_key": self.instrument_key,
            "action": self.action,
            "direction": self.direction,
            "confidence": self.confidence,
            "risk": self.risk,
        }


@dataclass(frozen=True, slots=True)
class OrderSubmitted(Event):
    """An order was submitted to an execution provider."""

    order_id: str = ""
    instrument_key: str = ""
    direction: str = ""
    order_type: str = ""
    quantity: float = 0.0
    provider: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "order_id": self.order_id,
            "instrument_key": self.instrument_key,
            "direction": self.direction,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "provider": self.provider,
        }


@dataclass(frozen=True, slots=True)
class OrderFilled(Event):
    """An order received a fill, fully or partially."""

    order_id: str = ""
    instrument_key: str = ""
    filled_quantity: float = 0.0
    fill_price: float = 0.0
    fully_filled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "order_id": self.order_id,
            "instrument_key": self.instrument_key,
            "filled_quantity": self.filled_quantity,
            "fill_price": self.fill_price,
            "fully_filled": self.fully_filled,
        }


@dataclass(frozen=True, slots=True)
class PositionClosed(Event):
    """A position was closed and its realised result recorded."""

    position_id: str = ""
    instrument_key: str = ""
    exit_price: float = 0.0
    realized_pnl: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "position_id": self.position_id,
            "instrument_key": self.instrument_key,
            "exit_price": self.exit_price,
            "realized_pnl": self.realized_pnl,
        }


@dataclass(frozen=True, slots=True)
class RiskLimitReached(Event):
    """A configured risk boundary was reached or breached."""

    limit_name: str = ""
    observed_value: float = 0.0
    limit_value: float = 0.0
    instrument_key: str | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "limit_name": self.limit_name,
            "observed_value": self.observed_value,
            "limit_value": self.limit_value,
            "instrument_key": self.instrument_key,
            "reason": self.reason,
        }


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
    # The soonest *high-impact* event's macro release, when it is a named one
    # ("cpi", "fomc", ...). Empty for an unnamed macro release or a non-macro
    # event, where next_event_type already says what it is. Present so a
    # subscriber watching for event risk can tell a CPI print from a PMI
    # without re-classifying the title itself.
    next_high_impact_kind: str = ""
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
            "next_high_impact_kind": self.next_high_impact_kind,
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


@dataclass(frozen=True, slots=True)
class MarketRegimeChanged(Event):
    """
    The prevailing market regime for an instrument *transitioned* between states.

    This is distinct from ``MarketRegimeDetected`` (which reports the regime read
    *now*, with no memory of the last). A ``MarketRegimeChanged`` asserts a real
    before->after transition and so carries both the previous and the new regime.
    It is only honest to publish when a prior regime for the same
    instrument+timeframe was genuinely recorded -- the producer that publishes
    this must hold (or be given) that previous state; the detector itself stays
    stateless and publishes ``MarketRegimeDetected``. ``is_reliable`` follows the
    new read's own gate (CLAUDE.md sections 5, 28).
    """

    instrument_key: str = ""
    timeframe: str = ""
    previous_regime: str = ""
    regime: str = ""
    direction: str = ""  # directional bias of the NEW regime (never a probability)
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "previous_regime": self.previous_regime,
            "regime": self.regime,
            "direction": self.direction,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class VolatilityChanged(Event):
    """
    The *realised* volatility character of an instrument changed bands.

    Distinct from ``MarketRegimeChanged`` (which is the broader character of the
    market: trend+volatility+the 6-state tracker). ``VolatilityChanged`` is the
    narrower, more actionable signal the spec's event vocabulary reserves (spec
    section 17): realised volatility crossing a band boundary -- calm -> normal
    -> elevated -- so a subscriber can re-check sizing/exposure without
    re-reading the regime. It is emitted only on a *genuine* band transition,
    never on a within-band wobble, and only when the producer holds a prior
    volatility read to diff against (the stateless detector alone cannot assert
    a change). ``previous_band`` is the settled prior band; ``band`` is the new
    one. ``is_reliable`` follows the read's own gate so a mock or thin read
    never announces a real shift (CLAUDE.md sections 5, 28).
    """

    instrument_key: str = ""
    timeframe: str = ""
    previous_band: str = ""
    band: str = ""
    atr_pct: float | None = None  # realised volatility as a fraction of price
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "previous_band": self.previous_band,
            "band": self.band,
            "atr_pct": self.atr_pct,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class LiquidityChanged(Event):
    """
    The resting-liquidity picture for an instrument changed materially.

    The liquidity tracker already publishes the *granular* zone lifecycle events
    (``LiquidityZoneCreated`` / ``LiquiditySwept`` / ``LiquidityAbsorbed`` / ...).
    This is the section-17 roll-up: the net resting-liquidity picture shifted --
    e.g. resting supply grew/shrank past a threshold, or a tracked zone was
    consumed/created so the available liquidity at price changed -- announced as
    a single state change rather than as ten micro-events. ``previous_state`` /
    ``state`` carry a compact descriptor ("deeper"/"thinner"/"swept"/"stable")
    rather than the full zone model so a subscriber can react to the *change*,
    not re-derive it. Only emitted on a real state transition the tracker
    measured, never on a flicker (CLAUDE.md sections 5, 28).
    """

    instrument_key: str = ""
    timeframe: str = ""
    previous_state: str = ""
    state: str = ""
    detail: str = ""
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "previous_state": self.previous_state,
            "state": self.state,
            "detail": self.detail,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class SignalInvalidated(Event):
    """
    A previously-fired (or pending) signal / prediction was invalidated.

    A signal's ``invalidation`` field names the condition under which its thesis
    no longer holds (e.g. "close below the structural stop"). When the market
    later shows that condition met -- the predicted entry was breached, the
    predicted direction is now contradicted by realised price, or the data the
    signal rested on went stale -- the signal is *invalidated*, not silently
    left standing. This event is that announcement. ``signal_id`` /
    ``prediction_id`` identify the cancelled call so a subscriber can reconcile
    the audit trail; ``reason`` names the invalidation condition that fired
    (spec sections 15, 17, 28). Never emitted for a signal that simply resolved
    (that is ``PredictionResolved``) -- only for one whose *basis* broke before
    horizon.
    """

    instrument_key: str = ""
    timeframe: str = ""
    signal_id: str = ""
    prediction_id: str = ""
    reason: str = ""
    invalidation: str = ""
    is_mock: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "signal_id": self.signal_id,
            "prediction_id": self.prediction_id,
            "reason": self.reason,
            "invalidation": self.invalidation,
            "is_mock": self.is_mock,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class DataQualityDegraded(Event):
    """
    The market-data quality for an instrument degraded below usable.

    ``MarketDataService`` already downgrades a series to STALE / PARTIAL /
    MISSING / INVALID and carries it in ``DataQuality``. This event announces
    the *transition into a worse quality band* -- e.g. a previously-OK feed
    returning PARTIAL or STALE data, or a feed that degraded to INVALID -- so
    a downstream consumer (signal gating, execution admission, monitoring) can
    *react* to the degradation instead of only seeing it embedded in the next
    read. ``previous_status`` / ``status`` carry the band names; ``issues`` is
    the human-readable reason. Only emitted on a genuine worsening transition,
    never on a transient blip or a fetch that was already bad (spec section 3 /
    17's "BAD_DATA must be able to block signals").
    """

    instrument_key: str = ""
    timeframe: str = ""
    previous_status: str = ""
    status: str = ""
    issues: tuple[str, ...] = ()
    is_mock: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "previous_status": self.previous_status,
            "status": self.status,
            "issues": list(self.issues),
            "is_mock": self.is_mock,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class NewsImpactDetected(Event):
    """
    A high-impact news item or scheduled event was detected for an instrument.

    ``NewsSentimentAnalyzed`` reports the aggregate sentiment read;
    ``MarketEventsDetected`` reports the calendar lookup. This event is the
    narrower *actionable* announcement the spec's vocabulary reserves (section
    17): a single high-impact item (an ``EventImpact.HIGH`` calendar event, or a
    headline whose scoring produced a strong catalyst) that a desk would page
    on, surfaced as one event rather than buried in a batch. ``kind`` names the
    class ("economic_release", "earnings", "dividend", "headline"); ``title``
    is the item; ``direction`` is the directional lean of the news (never a
    probability). Only emitted for a genuinely high-impact item on a
    non-mock read (CLAUDE.md sections 5, 28).
    """

    instrument_key: str = ""
    kind: str = ""
    title: str = ""
    scheduled_at: str = ""
    direction: str = ""
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "kind": self.kind,
            "title": self.title,
            "scheduled_at": self.scheduled_at,
            "direction": self.direction,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


@dataclass(frozen=True, slots=True)
class RiskStateChanged(Event):
    """
    The account-level risk state crossed a threshold (the section-17 event).

    ``RiskAssessed`` reports a *per-trade* risk plan; ``RiskLimitReached``
    reports a limit breach. ``RiskStateChanged`` is the state-transition
    announcement: the account's aggregate risk posture moved into a new band --
    e.g. daily realised loss approaching / breaching the configured limit, or
    open exposure crossing the cap -- so a subscriber can stop new entries
    *before* a hard breach, not only after. ``kind`` names which state
    ("daily_loss", "max_exposure"); ``previous_state`` / ``state`` carry
    "within" / "approaching" / "breached"; ``utilisation`` is the fraction of
    the configured limit consumed. Only emitted on a genuine band transition,
    fail-closed (an unknown input reads as a state change, not silence).
    """

    kind: str = ""
    previous_state: str = ""
    state: str = ""
    utilisation: float | None = None
    detail: str = ""
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "kind": self.kind,
            "previous_state": self.previous_state,
            "state": self.state,
            "utilisation": self.utilisation,
            "detail": self.detail,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class FeatureUpdated(Event):
    """
    A feature vector for the quant layer was recomputed for an instrument.

    Carries the *shape and provenance* of the recomputation -- which model fed on
    it, how many causal features, whether a live (unlabelled) row existed --
    rather than the raw matrix (which is large and already reproducible from the
    candles). ``is_reliable`` mirrors the producing estimate's edge gate so a
    subscriber can never read a mock/no-edge feature set as a real signal input
    (CLAUDE.md sections 6, 9).
    """

    instrument_key: str = ""
    timeframe: str = ""
    horizon_bars: int = 0
    feature_names: tuple[str, ...] = ()
    has_live_row: bool = False
    model: str = ""
    is_reliable: bool = False
    source_tier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "horizon_bars": self.horizon_bars,
            "feature_count": len(self.feature_names),
            "feature_names": list(self.feature_names),
            "has_live_row": self.has_live_row,
            "model": self.model,
            "is_reliable": self.is_reliable,
            "source_tier": self.source_tier,
        }


# ======================================================================
# Liquidity-intelligence events (Phase 2, order-book / tape microstructure)
#
# These are distinct named Event subclasses so a subscriber can register for
# exactly the change it cares about. They share a payload shape -- instrument,
# side, the zone band it concerns, the supporting numbers and the honesty flag
# -- carried on a common base so a consumer can read any of them uniformly.
# ======================================================================

#: Canonical liquidity event kinds (the class names are the event names).
LIQUIDITY_APPEARED = "LiquidityAppeared"
LIQUIDITY_REMOVED = "LiquidityRemoved"
LIQUIDITY_REPLENISHED = "LiquidityReplenished"
LIQUIDITY_CONSUMED = "LiquidityConsumed"
LIQUIDITY_SWEPT = "LiquiditySwept"
LIQUIDITY_ABSORBED = "LiquidityAbsorbed"
LIQUIDITY_IMBALANCE_CHANGED = "LiquidityImbalanceChanged"
LIQUIDITY_ZONE_CREATED = "LiquidityZoneCreated"
LIQUIDITY_ZONE_WEAKENED = "LiquidityZoneWeakened"
LIQUIDITY_ZONE_INVALIDATED = "LiquidityZoneInvalidated"


@dataclass(frozen=True, slots=True)
class LiquidityEvent(Event):
    """
    Base payload for order-book / tape liquidity changes (Phase 2).

    ``zone_id`` is the content-addressed id of the ``LiquidityZone`` the change
    belongs to (empty for whole-book reads like an imbalance flip). ``side`` is
    ``"bid"`` / ``"ask"`` / ``"none"``; the numeric context (price, volume,
    liquidity/persistence scores) is kept flat so a dashboard, a logger, a
    future Memory adapter or a backtester can read it without deserialising a
    nested zone. ``is_mock`` is surfaced so synthetic liquidity is never read as
    a real wall (CLAUDE.md sections 9, 28).
    """

    instrument_key: str = ""
    side: str = ""
    zone_id: str = ""
    lower_price: float | None = None
    upper_price: float | None = None
    price: float | None = None
    volume: float | None = None
    liquidity_score: float | None = None
    persistence_score: float | None = None
    detail: str = ""
    source_tier: str = ""
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "instrument_key": self.instrument_key,
            "side": self.side,
            "zone_id": self.zone_id,
            "lower_price": self.lower_price,
            "upper_price": self.upper_price,
            "price": self.price,
            "volume": self.volume,
            "liquidity_score": self.liquidity_score,
            "persistence_score": self.persistence_score,
            "detail": self.detail,
            "source_tier": self.source_tier,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True, slots=True)
class LiquidityAppeared(LiquidityEvent):
    """New resting liquidity showed at a band."""


@dataclass(frozen=True, slots=True)
class LiquidityRemoved(LiquidityEvent):
    """Resting liquidity was pulled from a band (not consumed by the tape)."""


@dataclass(frozen=True, slots=True)
class LiquidityReplenished(LiquidityEvent):
    """Resting liquidity reappeared at a band after being consumed."""


@dataclass(frozen=True, slots=True)
class LiquidityConsumed(LiquidityEvent):
    """Executed flow ate into a zone's resting liquidity."""


@dataclass(frozen=True, slots=True)
class LiquiditySwept(LiquidityEvent):
    """Price cleared through a zone -- an *acceptance* (the wall gave way)."""


@dataclass(frozen=True, slots=True)
class LiquidityAbsorbed(LiquidityEvent):
    """
    Aggressive flow was absorbed without proportional price response, or price
    swept into a zone and was rejected (the wall held). ``detail`` says which.
    """


@dataclass(frozen=True, slots=True)
class LiquidityImbalanceChanged(LiquidityEvent):
    """The resting bid/ask balance flipped to a one-sided regime."""


@dataclass(frozen=True, slots=True)
class LiquidityZoneCreated(LiquidityEvent):
    """A new resting-liquidity cluster became a tracked zone."""


@dataclass(frozen=True, slots=True)
class LiquidityZoneWeakened(LiquidityEvent):
    """A tracked zone's resting liquidity faded but has not yet dissolved."""


@dataclass(frozen=True, slots=True)
class LiquidityZoneInvalidated(LiquidityEvent):
    """A tracked zone dissolved -- its resting liquidity fell below the floor."""


#: The liquidity event subclasses, keyed by name for the service's dispatch.
LIQUIDITY_EVENT_TYPES: dict[str, type[LiquidityEvent]] = {
    cls.__name__: cls
    for cls in (
        LiquidityAppeared,
        LiquidityRemoved,
        LiquidityReplenished,
        LiquidityConsumed,
        LiquiditySwept,
        LiquidityAbsorbed,
        LiquidityImbalanceChanged,
        LiquidityZoneCreated,
        LiquidityZoneWeakened,
        LiquidityZoneInvalidated,
    )
}


# ----------------------------------------------------------------------
# Phase 2 -- production lifecycle events
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SignalStateChanged(Event):
    """A signal advanced one legal step in its lifecycle (spec Phase 2)."""

    signal_id: str = ""
    instrument_key: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "signal_id": self.signal_id,
            "instrument_key": self.instrument_key,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class PositionOpened(Event):
    """A fill opened a new position in the tracked book (spec Phase 2)."""

    position_id: str = ""
    instrument_key: str = ""
    direction: str = ""
    quantity: float = 0.0
    entry_price: float = 0.0
    provider: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "position_id": self.position_id,
            "instrument_key": self.instrument_key,
            "direction": self.direction,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "provider": self.provider,
        }


@dataclass(frozen=True, slots=True)
class KillSwitchTripped(Event):
    """A scoped kill switch halted order admission (spec Phase 2)."""

    scope: str = ""
    target: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "scope": self.scope,
            "target": self.target,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class KillSwitchCleared(Event):
    """A tripped kill switch was explicitly cleared for recovery (spec Phase 2)."""

    scope: str = ""
    target: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "scope": self.scope,
            "target": self.target,
        }


@dataclass(frozen=True, slots=True)
class ReconciliationMismatchDetected(Event):
    """Local and venue state diverged on one leg of the book (spec Phase 2)."""

    kind: str = ""
    detail: str = ""
    order_id: str = ""
    position_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "kind": self.kind,
            "detail": self.detail,
            "order_id": self.order_id,
            "position_id": self.position_id,
        }


@dataclass(frozen=True, slots=True)
class TradingHealthChanged(Event):
    """The aggregate trading-health status moved to a new band (spec Phase 2)."""

    previous_state: str = ""
    state: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "previous_state": self.previous_state,
            "state": self.state,
            "reasons": list(self.reasons),
        }
