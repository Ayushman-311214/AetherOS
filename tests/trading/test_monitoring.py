"""
The monitoring service: one bounded "Observe Result -> Evaluate" sweep.

These pin the sweep's composition and honesty (spec sections 16, 28, 29): it
resolves the recorded predictions, partitions them into resolved / pending /
unresolvable, summarises the resolved batch, and announces exactly one
MonitoringSweepCompleted event. The evaluator is faked (as in the track-record
tests) so these isolate the sweep composition from candle arithmetic; a thin or
MOCK sample is reported but never announced as a reliable track record, and the
sweep is a single pass -- it is not a background loop.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction, PredictionOutcomeStatus
from aetheros.trading.domain.outcome import PredictionOutcome
from aetheros.trading.domain.prediction import PredictionRecord
from aetheros.trading.events import MonitoringSweepCompleted
from aetheros.trading.services.monitoring_service import MonitoringService
from aetheros.trading.services.outcome_store import InMemoryOutcomeStore
from aetheros.trading.services.performance_service import (
    PredictionPerformanceService,
)
from aetheros.trading.services.prediction_store import InMemoryPredictionStore
from aetheros.trading.services.track_record_service import (
    PredictionTrackRecordService,
)


class _Bus:
    def __init__(self) -> None:
        self.events: list = []

    async def publish(self, event) -> None:
        self.events.append(event)


def _record(pid: str, instrument_key: str = "AAPL") -> PredictionRecord:
    return PredictionRecord(
        id=pid,
        instrument_key=instrument_key,
        symbol=instrument_key,
        exchange=None,
        asset_class="equity",
        name=None,
        timeframe="1d",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        horizon_bars=5,
        recommendation="buy",
        is_actionable=True,
        direction=Direction.UP.value,
        confidence="high",
        directional_score=0.6,
        probability_reliable=False,
        probability_up=None,
        probability_down=None,
        risk_reward_ratio=2.0,
        overall_risk="medium",
        invalidation="",
        source_tier="derived",
        is_mock=False,
        model_pipeline="deterministic-v1",
        evidence_count=4,
        limitations=(),
    )


def _outcome(pid: str, status: PredictionOutcomeStatus, *, is_correct=None) -> PredictionOutcome:
    return PredictionOutcome(
        prediction_id=pid,
        instrument_key="AAPL",
        timeframe="1d",
        status=status,
        predicted_direction=Direction.UP,
        realized_direction=Direction.UP if status is PredictionOutcomeStatus.RESOLVED else Direction.UNKNOWN,
        is_correct=is_correct,
        realized_return=0.02 if status is PredictionOutcomeStatus.RESOLVED else None,
        horizon_bars=5,
        bars_elapsed=5 if status is PredictionOutcomeStatus.RESOLVED else 1,
        is_reliable=status is PredictionOutcomeStatus.RESOLVED,
        is_mock=False,
    )


class _FakeEvaluator:
    def __init__(self, outcomes: dict[str, PredictionOutcome]) -> None:
        self._outcomes = outcomes

    async def resolve_latest(self, record: PredictionRecord) -> PredictionOutcome:
        return self._outcomes[record.id]


async def _service_with(outcomes: dict[str, PredictionOutcome], *, bus: _Bus | None = None, outcome_store=None):
    settings = get_settings()
    store = InMemoryPredictionStore()
    for pid in outcomes:
        await store.record(_record(pid))
    perf = PredictionPerformanceService(settings)
    track = PredictionTrackRecordService(store, _FakeEvaluator(outcomes), perf)  # type: ignore[arg-type]
    return MonitoringService(track, perf, outcome_store=outcome_store, event_bus=bus)


@pytest.mark.asyncio
async def test_sweep_partitions_outcomes_by_status():
    outcomes = {
        "p_res": _outcome("p_res", PredictionOutcomeStatus.RESOLVED, is_correct=True),
        "p_pend": _outcome("p_pend", PredictionOutcomeStatus.PENDING),
        "p_unres": _outcome("p_unres", PredictionOutcomeStatus.UNRESOLVABLE),
    }
    service = await _service_with(outcomes)
    report = await service.run_once()

    assert report.swept == 3
    assert report.resolved == 1
    assert report.pending == 1
    assert report.unresolvable == 1
    assert report.performance.sample_size == 3


@pytest.mark.asyncio
async def test_sweep_emits_exactly_one_event():
    bus = _Bus()
    outcomes = {"p1": _outcome("p1", PredictionOutcomeStatus.RESOLVED, is_correct=True)}
    service = await _service_with(outcomes, bus=bus)
    await service.run_once()

    assert len(bus.events) == 1
    evt = bus.events[0]
    assert isinstance(evt, MonitoringSweepCompleted)
    assert evt.swept == 1
    assert evt.resolved == 1


@pytest.mark.asyncio
async def test_empty_history_is_a_valid_quiet_sweep():
    service = await _service_with({})
    report = await service.run_once()

    assert report.swept == 0
    assert report.resolved == 0
    assert report.performance.is_reliable is False  # nothing to measure yet


@pytest.mark.asyncio
async def test_thin_sample_is_reported_but_not_reliable():
    outcomes = {"p1": _outcome("p1", PredictionOutcomeStatus.RESOLVED, is_correct=True)}
    service = await _service_with(outcomes)
    report = await service.run_once()

    # One resolved outcome is below the reliability floor -> reported, not reliable.
    assert report.resolved == 1
    assert report.performance.is_reliable is False


@pytest.mark.asyncio
async def test_report_to_dict_shape_is_complete():
    outcomes = {"p1": _outcome("p1", PredictionOutcomeStatus.RESOLVED, is_correct=True)}
    service = await _service_with(outcomes)
    payload = (await service.run_once()).to_dict()

    for key in (
        "swept",
        "resolved",
        "pending",
        "unresolvable",
        "outcomes",
        "performance",
    ):
        assert key in payload, f"missing monitoring key: {key}"


@pytest.mark.asyncio
async def test_sweep_persists_outcomes_to_the_outcome_store():
    outcome_store = InMemoryOutcomeStore()
    outcomes = {
        "p1": _outcome("p1", PredictionOutcomeStatus.RESOLVED, is_correct=True),
        "p2": _outcome("p2", PredictionOutcomeStatus.PENDING),
    }
    service = await _service_with(outcomes, outcome_store=outcome_store)
    await service.run_once()

    # Both swept outcomes are accumulated durably; a second sweep upserts, not
    # duplicates (the store is keyed on prediction_id).
    assert len(outcome_store) == 2
    await service.run_once()
    assert len(outcome_store) == 2
