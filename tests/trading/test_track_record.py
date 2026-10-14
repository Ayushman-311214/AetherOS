"""
The prediction track-record service: the on-demand composition of the audit
store, the per-prediction evaluator and the performance aggregator into one
read-only question -- "of the predictions we recorded, how have they actually
done against the market that followed?"

These pin the composition contract (spec sections 6, 16, 28, 29): it pulls the
store's recorded predictions newest-first, resolves each against the freshest
candles, and summarises the outcomes; an instrument filter and a limit flow
through to the store; an empty history is a valid "nothing to measure yet"
summary rather than an error; and a resolution failure for one record is logged
and omitted rather than faked into a hit/miss or allowed to sink the whole query.

The evaluator is faked here on purpose: it is exhaustively exercised in
``test_prediction_evaluator.py``, so these tests isolate the *composition* --
store ordering/filtering in, real aggregation out -- from the candle arithmetic.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Direction,
    PredictionOutcomeStatus,
)
from aetheros.trading.domain.outcome import PredictionOutcome
from aetheros.trading.domain.prediction import PredictionRecord
from aetheros.trading.services.performance_service import (
    PredictionPerformanceService,
)
from aetheros.trading.services.prediction_store import InMemoryPredictionStore
from aetheros.trading.services.track_record_service import (
    PredictionTrackRecordService,
)


def _record(prediction_id: str, instrument_key: str) -> PredictionRecord:
    """A minimal, hand-built recorded prediction with a fixed content id."""
    symbol, _, exchange = instrument_key.partition(":")
    return PredictionRecord(
        id=prediction_id,
        instrument_key=instrument_key,
        symbol=symbol,
        exchange=exchange or "TEST",
        asset_class="equity",
        name=symbol,
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
        invalidation="close below support",
        source_tier="derived",
        is_mock=False,
        model_pipeline="deterministic-v1",
        evidence_count=4,
        limitations=(),
    )


def _resolved(
    prediction_id: str,
    instrument_key: str,
    *,
    is_correct: bool | None,
    realized_return: float = 0.01,
    is_mock: bool = False,
) -> PredictionOutcome:
    """A RESOLVED, optionally-graded outcome for the fake evaluator to hand back."""
    return PredictionOutcome(
        prediction_id=prediction_id,
        instrument_key=instrument_key,
        timeframe="1d",
        status=PredictionOutcomeStatus.RESOLVED,
        predicted_direction=Direction.UP,
        realized_direction=Direction.UP if realized_return > 0 else Direction.DOWN,
        is_correct=is_correct,
        realized_return=realized_return,
        horizon_bars=5,
        bars_elapsed=5,
        is_reliable=not is_mock,
        is_mock=is_mock,
    )


class _FakeEvaluator:
    """Returns a pre-baked outcome per record id; raises for flagged ids."""

    def __init__(
        self,
        outcomes: dict[str, PredictionOutcome],
        *,
        failing_ids: frozenset[str] = frozenset(),
    ) -> None:
        self._outcomes = outcomes
        self._failing_ids = failing_ids
        self.resolved_ids: list[str] = []

    async def resolve_latest(self, record: PredictionRecord) -> PredictionOutcome:
        self.resolved_ids.append(record.id)
        if record.id in self._failing_ids:
            raise RuntimeError("market data provider unavailable")
        return self._outcomes[record.id]


def _service(
    store: InMemoryPredictionStore,
    evaluator: _FakeEvaluator,
) -> PredictionTrackRecordService:
    return PredictionTrackRecordService(
        store,
        evaluator,  # type: ignore[arg-type]  # duck-typed resolve_latest
        PredictionPerformanceService(get_settings()),
    )


AAPL = "AAPL:NASDAQ"
MSFT = "MSFT:NASDAQ"


# --------------------------------------------------------------------------- #
# Composition                                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_evaluate_composes_store_and_evaluator_into_a_summary():
    store = InMemoryPredictionStore()
    records = [
        _record("pred_a", AAPL),
        _record("pred_b", AAPL),
        _record("pred_c", AAPL),
    ]
    for r in records:
        await store.record(r)

    evaluator = _FakeEvaluator(
        {
            "pred_a": _resolved("pred_a", AAPL, is_correct=True),
            "pred_b": _resolved("pred_b", AAPL, is_correct=True),
            "pred_c": _resolved("pred_c", AAPL, is_correct=False),
        }
    )

    perf = await _service(store, evaluator).evaluate()

    # Every recorded prediction was resolved and folded into the aggregate.
    assert perf.sample_size == 3
    assert perf.resolved == 3
    assert perf.scored == 3
    assert perf.hits == 2
    assert perf.misses == 1
    assert perf.directional_accuracy == pytest.approx(2 / 3, abs=1e-6)
    # Three scored outcomes is far below the default minimum -> honest, not reliable.
    assert perf.is_reliable is False


@pytest.mark.asyncio
async def test_resolve_all_preserves_store_newest_first_order():
    store = InMemoryPredictionStore()
    await store.record(_record("pred_old", AAPL))
    await store.record(_record("pred_new", AAPL))

    evaluator = _FakeEvaluator(
        {
            "pred_old": _resolved("pred_old", AAPL, is_correct=True),
            "pred_new": _resolved("pred_new", AAPL, is_correct=False),
        }
    )

    outcomes = await _service(store, evaluator).resolve_all()

    # Newest-first: the store orders pred_new ahead of pred_old.
    assert [o.prediction_id for o in outcomes] == ["pred_new", "pred_old"]


@pytest.mark.asyncio
async def test_evaluate_scopes_to_one_instrument():
    store = InMemoryPredictionStore()
    await store.record(_record("pred_aapl", AAPL))
    await store.record(_record("pred_msft", MSFT))

    evaluator = _FakeEvaluator(
        {
            "pred_aapl": _resolved("pred_aapl", AAPL, is_correct=True),
            "pred_msft": _resolved("pred_msft", MSFT, is_correct=False),
        }
    )
    service = _service(store, evaluator)

    perf = await service.evaluate(instrument_key=AAPL)

    # Only the AAPL prediction was resolved and counted; MSFT was filtered out.
    assert perf.sample_size == 1
    assert evaluator.resolved_ids == ["pred_aapl"]


@pytest.mark.asyncio
async def test_limit_caps_the_records_evaluated():
    store = InMemoryPredictionStore()
    await store.record(_record("pred_1", AAPL))
    await store.record(_record("pred_2", AAPL))
    await store.record(_record("pred_3", AAPL))

    evaluator = _FakeEvaluator(
        {pid: _resolved(pid, AAPL, is_correct=True) for pid in ("pred_1", "pred_2", "pred_3")}
    )

    outcomes = await _service(store, evaluator).resolve_all(limit=1)

    # The limit caps the page at the single newest record.
    assert [o.prediction_id for o in outcomes] == ["pred_3"]


# --------------------------------------------------------------------------- #
# Honesty boundaries                                                           #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_empty_history_is_an_insufficient_summary_not_an_error():
    store = InMemoryPredictionStore()
    evaluator = _FakeEvaluator({})

    perf = await _service(store, evaluator).evaluate()

    # Nothing recorded yet is a valid answer, never a raised error.
    assert perf.sample_size == 0
    assert perf.is_reliable is False
    assert any("nothing to measure" in lim.lower() for lim in perf.limitations)


@pytest.mark.asyncio
async def test_resolution_failure_on_one_record_is_skipped_not_fatal():
    store = InMemoryPredictionStore()
    await store.record(_record("pred_ok", AAPL))
    await store.record(_record("pred_bad", AAPL))

    evaluator = _FakeEvaluator(
        {"pred_ok": _resolved("pred_ok", AAPL, is_correct=True)},
        failing_ids=frozenset({"pred_bad"}),
    )

    perf = await _service(store, evaluator).evaluate()

    # The un-fetchable record is omitted, not fabricated; the query still returns.
    assert evaluator.resolved_ids == ["pred_bad", "pred_ok"]  # both attempted
    assert perf.sample_size == 1
    assert perf.scored == 1
    assert perf.hits == 1


@pytest.mark.asyncio
async def test_mock_resolutions_are_never_a_reliable_track_record():
    store = InMemoryPredictionStore()
    settings = get_settings()
    ids = [f"pred_{i}" for i in range(settings.TRADING_PERF_MIN_SAMPLE)]
    for pid in ids:
        await store.record(_record(pid, AAPL))

    # A full, all-correct sample -- but resolved on synthetic MOCK data.
    evaluator = _FakeEvaluator(
        {pid: _resolved(pid, AAPL, is_correct=True, is_mock=True) for pid in ids}
    )

    perf = await _service(store, evaluator).evaluate()

    assert perf.scored == settings.TRADING_PERF_MIN_SAMPLE
    assert perf.is_mock is True
    # Even at/above the minimum sample, MOCK data can never read as a real edge.
    assert perf.is_reliable is False


@pytest.mark.asyncio
async def test_a_full_clean_sample_reads_as_a_reliable_track_record():
    store = InMemoryPredictionStore()
    settings = get_settings()
    ids = [f"pred_{i}" for i in range(settings.TRADING_PERF_MIN_SAMPLE)]
    for pid in ids:
        await store.record(_record(pid, AAPL))

    evaluator = _FakeEvaluator(
        {pid: _resolved(pid, AAPL, is_correct=True, is_mock=False) for pid in ids}
    )

    perf = await _service(store, evaluator).evaluate()

    # At the configured minimum, non-mock, fully-scored -> a reliable aggregate.
    assert perf.scored == settings.TRADING_PERF_MIN_SAMPLE
    assert perf.is_mock is False
    assert perf.is_reliable is True
    assert perf.directional_accuracy == pytest.approx(1.0, abs=1e-6)
