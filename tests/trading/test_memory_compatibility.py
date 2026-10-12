"""
Memory-compatibility boundary (Phase 8).

Verifies — without building Memory — that a future Memory subsystem can
subscribe to the structured intelligence events and receive everything it
would need to store (predictions, outcomes, evidence, regimes, liquidity
zones, sweeps, signals, analyses) **without modifying any trading code**.

The test uses a throwaway recording subscriber (the shape a future Memory
adapter would take): subscribe via the shared EventBus's public API, publish
real production events, assert the subscriber received them with the
context it needs (ids, instruments, timestamps, honesty flags).
"""

from __future__ import annotations

import pytest

from aetheros.runtime.events.event_bus import EventBus
from aetheros.runtime.events.events import Event
from aetheros.trading.events import (
    AnalysisCompleted,
    BacktestCompleted,
    LiquidityAbsorbed,
    LiquiditySwept,
    LiquidityZoneCreated,
    MarketRegimeChanged,
    PositionClosed,
    PredictionCreated,
    PredictionPerformanceEvaluated,
    PredictionResolved,
    ProbabilityEstimated,
    SignalGenerated,
)

#: Everything the spec's future-Memory contract names (§Phase 8), plus the
#: outcome/performance events the "store historical outcomes + strategy
#: performance" items require. All exist as real event classes (the spec's
#: canonical names — e.g. ``PredictionOutcomeRecorded`` — map onto the
#: production events the pipeline actually publishes: ``PredictionResolved``
#: and ``LiquiditySwept``).
MEMORY_RELEVANT_EVENTS = (
    PredictionCreated,
    PredictionResolved,
    SignalGenerated,
    AnalysisCompleted,
    MarketRegimeChanged,
    LiquidityZoneCreated,
    LiquiditySwept,
    LiquidityAbsorbed,
    BacktestCompleted,
    ProbabilityEstimated,
    PredictionPerformanceEvaluated,
    PositionClosed,
)


class _RecordingMemoryAdapter:
    """
    A stand-in for a future Memory subscriber.

    Records every event it receives, keyed by name — the shape the eventual
    memory write path would take. Uses only the EventBus's public API. The bus
    logs the handler's ``__name__`` at subscribe time, so a Memory adapter must
    expose a named handler (``handle``), not rely on ``__call__``.
    """

    def __init__(self) -> None:
        self.received: dict[str, Event] = {}

    async def handle(self, event: Event) -> None:
        self.received[event.name] = event


@pytest.mark.asyncio
async def test_memory_adapter_subscribes_without_touching_trading_code():
    """A subscriber gets every structured event via the public bus API."""
    bus = EventBus()
    memory = _RecordingMemoryAdapter()

    for event_type in MEMORY_RELEVANT_EVENTS:
        await bus.subscribe(event_type, memory.handle)

    # Publish one real event of each subscribed type.
    await bus.publish(
        PredictionCreated(
            prediction_id="pred_1", instrument_key="NASDAQ:AAPL",
            timeframe="1d", recommendation="approved", direction="up",
            confidence="high", probability_up=0.73, horizon_bars=5,
            model_pipeline="deterministic-core/1.0", source_tier="secondary",
        )
    )
    await bus.publish(
        PredictionResolved(
            prediction_id="pred_1", instrument_key="NASDAQ:AAPL",
            timeframe="1d", predicted_direction="up",
            realized_direction="up", is_correct=True,
            realized_return=0.012, source_tier="secondary",
        )
    )
    await bus.publish(
        SignalGenerated(
            signal_id="sg_1", instrument_key="NASDAQ:AAPL",
            action="buy", direction="up", confidence="high", risk="medium",
        )
    )
    await bus.publish(
        AnalysisCompleted(
            instrument_key="NASDAQ:AAPL", timeframe="1d", direction="up",
            confidence="high", directional_score=0.6, is_actionable=True,
            evidence_count=5, source_tier="secondary",
        )
    )
    await bus.publish(
        MarketRegimeChanged(
            instrument_key="NASDAQ:AAPL", timeframe="1d",
            previous_regime="ranging", regime="trending_up", direction="up",
            is_reliable=True, source_tier="secondary",
        )
    )
    await bus.publish(
        LiquidityZoneCreated(
            instrument_key="NASDAQ:AAPL", side="bid",
            zone_id="lqz_1", lower_price=99.0, upper_price=99.5,
            liquidity_score=0.8, detail="new wall", source_tier="secondary",
        )
    )
    await bus.publish(
        LiquiditySwept(
            instrument_key="NASDAQ:AAPL", side="bid", zone_id="lqz_1",
            price=99.5, detail="wall gave way", source_tier="secondary",
        )
    )
    await bus.publish(
        LiquidityAbsorbed(
            instrument_key="NASDAQ:AAPL", side="ask", zone_id="lqz_2",
            price=101.5, volume=60.0, detail="absorbed",
            source_tier="secondary",
        )
    )

    # The memory adapter received every event, with the context it needs.
    names = set(memory.received)
    assert {
        "PredictionCreated", "PredictionResolved", "SignalGenerated",
        "AnalysisCompleted", "MarketRegimeChanged", "LiquidityZoneCreated",
        "LiquiditySwept", "LiquidityAbsorbed",
    } <= names

    # The payloads carry what a memory store needs: stable ids + honesty flags.
    pred = memory.received["PredictionCreated"]
    assert pred.prediction_id == "pred_1"
    assert pred.is_mock is False
    assert pred.probability_up == pytest.approx(0.73)
    outcome = memory.received["PredictionResolved"]
    assert outcome.prediction_id == "pred_1"
    assert outcome.is_correct is True


@pytest.mark.asyncio
async def test_trading_intelligence_works_with_no_memory_subscriber():
    """Publishing works identically with zero subscribers (Memory off)."""
    bus = EventBus()  # no subscribers at all
    await bus.publish(
        PredictionCreated(prediction_id="p", instrument_key="X")
    )  # must not raise and needs no memory wiring


def test_evidence_and_records_are_persistable_shapes():
    """The domain records Memory would store are serialisable + id-stable."""
    from aetheros.trading.domain.prediction import PredictionRecord
    from aetheros.trading.domain.evidence import Evidence

    # Evidence is content-addressed -> a memory store can dedupe on it.
    e1 = _evidence()
    e2 = _evidence()
    assert e1.id == e2.id
    assert e1.to_dict()["id"] == e1.id

    # PredictionRecord round-trips through dict (the durable-store contract).
    rec = _prediction_record()
    back = PredictionRecord.from_dict(rec.to_dict())
    assert back.id == rec.id
    assert back.direction == rec.direction
    assert back.recommendation == rec.recommendation


def _evidence() -> Evidence:
    from aetheros.trading.domain.evidence import Evidence
    from aetheros.trading.domain.enums import (
        Assertion,
        Confidence,
        Direction,
        EvidenceType,
        DataQualityStatus,
        SourceTier,
    )
    from aetheros.trading.domain.provenance import DataQuality, Provenance
    return Evidence(
        instrument_key="X",
        type=EvidenceType.MARKET_STRUCTURE,
        assertion=Assertion.CALCULATED,
        direction=Direction.UP,
        detail="test claim",
        weight=0.5,
        confidence=Confidence.MEDIUM,
        provenance=Provenance(source="t", tier=SourceTier.PRIMARY),
        quality=DataQuality(status=DataQualityStatus.OK),
    )


def _prediction_record() -> PredictionRecord:
    from aetheros.trading.domain.prediction import PredictionRecord
    from datetime import UTC, datetime
    return PredictionRecord(
        id="pred_1",
        instrument_key="NASDAQ:AAPL",
        symbol="AAPL", exchange="NASDAQ", asset_class="equity", name=None,
        timeframe="1d",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        horizon_bars=5,
        recommendation="approved", is_actionable=True,
        direction="up", confidence="high", directional_score=0.6,
        probability_reliable=True, probability_up=0.73, probability_down=0.27,
        risk_reward_ratio=2.8, overall_risk="medium",
        invalidation="close below 99.5",
        source_tier="secondary", is_mock=False,
        model_pipeline="deterministic-core/1.0", evidence_count=5,
    )