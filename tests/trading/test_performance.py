"""
The deterministic prediction-performance aggregator (spec sections 6, 9, 28, 29).

These pin the "is the system any good?" summariser at its honesty boundary: over
a batch of already-resolved outcomes it counts hits/misses, reports directional
accuracy and coverage, and (reusing the shared quant calibration code) a Brier
score and ECE over the calibrated-probability outcomes. Only RESOLVED, directional
outcomes are scored; PENDING/UNRESOLVABLE are tallied but never graded; a sample
thinner than TRADING_PERF_MIN_SAMPLE or tainted by MOCK data is never reported as
a reliable track record; an empty batch is a valid summary, not an error.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction, PredictionOutcomeStatus
from aetheros.trading.domain.outcome import PredictionOutcome
from aetheros.trading.errors import PredictionError
from aetheros.trading.events import PredictionPerformanceEvaluated
from aetheros.trading.services.performance_service import (
    PredictionPerformanceService,
)


# --------------------------------------------------------------------------- #
# Fixtures / helpers                                                           #
# --------------------------------------------------------------------------- #


class _Bus:
    """A minimal event bus that records what the service publishes."""

    def __init__(self) -> None:
        self.events: list = []

    async def publish(self, event) -> None:
        self.events.append(event)


def _resolved(
    *,
    is_correct: bool | None = True,
    predicted: Direction = Direction.UP,
    realized: Direction = Direction.UP,
    realized_return: float | None = 0.02,
    predicted_p_up: float | None = None,
    is_mock: bool = False,
) -> PredictionOutcome:
    return PredictionOutcome(
        prediction_id="pred_x",
        instrument_key="AAPL",
        timeframe="1d",
        status=PredictionOutcomeStatus.RESOLVED,
        predicted_direction=predicted,
        realized_direction=realized,
        is_correct=is_correct,
        realized_return=realized_return,
        horizon_bars=2,
        bars_elapsed=2,
        predicted_p_up=predicted_p_up,
        brier_contribution=(
            None
            if predicted_p_up is None or realized_return is None
            else (predicted_p_up - (1.0 if realized_return > 0.0 else 0.0)) ** 2
        ),
        is_reliable=not is_mock,
        is_mock=is_mock,
    )


def _pending() -> PredictionOutcome:
    return PredictionOutcome(
        prediction_id="pred_p",
        instrument_key="AAPL",
        timeframe="1d",
        status=PredictionOutcomeStatus.PENDING,
        predicted_direction=Direction.UP,
        horizon_bars=2,
        bars_elapsed=1,
    )


def _unresolvable() -> PredictionOutcome:
    return PredictionOutcome(
        prediction_id="pred_u",
        instrument_key="AAPL",
        timeframe="1d",
        status=PredictionOutcomeStatus.UNRESOLVABLE,
        predicted_direction=Direction.UP,
        horizon_bars=2,
    )


def _service(bus: _Bus | None = None) -> PredictionPerformanceService:
    return PredictionPerformanceService(get_settings(), event_bus=bus)


def _min_sample() -> int:
    return get_settings().TRADING_PERF_MIN_SAMPLE


# --------------------------------------------------------------------------- #
# Counting / directional accuracy                                              #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_directional_accuracy_and_coverage_are_hand_computable():
    # 3 hits, 1 miss, 1 non-directional (SIDEWAYS -> not scored) = 5 resolved.
    outcomes = [
        _resolved(is_correct=True),
        _resolved(is_correct=True),
        _resolved(is_correct=True),
        _resolved(is_correct=False, realized=Direction.DOWN, realized_return=-0.02),
        _resolved(
            is_correct=None,
            predicted=Direction.SIDEWAYS,
            realized=Direction.SIDEWAYS,
            realized_return=0.0,
        ),
    ]
    perf = await _service().summarize(outcomes)

    assert perf.sample_size == 5
    assert perf.resolved == 5
    assert perf.scored == 4  # the SIDEWAYS call has no directional bet
    assert perf.hits == 3
    assert perf.misses == 1
    assert perf.directional_accuracy == pytest.approx(0.75)
    assert perf.coverage == pytest.approx(4 / 5)  # scored / resolved


@pytest.mark.asyncio
async def test_pending_and_unresolvable_are_tallied_but_never_scored():
    outcomes = [_resolved(is_correct=True), _pending(), _unresolvable()]
    perf = await _service().summarize(outcomes)

    assert perf.sample_size == 3
    assert perf.resolved == 1
    assert perf.pending == 1
    assert perf.unresolvable == 1
    assert perf.scored == 1
    assert perf.hits == 1
    # Coverage is over resolved only; the pending/unresolvable never enter it.
    assert perf.coverage == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_mean_realized_return_averages_resolved_moves():
    outcomes = [
        _resolved(realized_return=0.02),
        _resolved(realized_return=-0.04, is_correct=False, realized=Direction.DOWN),
    ]
    perf = await _service().summarize(outcomes)
    assert perf.mean_realized_return == pytest.approx(-0.01)


# --------------------------------------------------------------------------- #
# Calibration bundle                                                           #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_calibration_brier_is_hand_computable():
    # Two calibrated predictions: p=0.8 vs up (y=1) -> 0.04; p=0.3 vs down (y=0)
    # -> 0.09. Mean Brier = 0.065. A third resolved outcome without a probability
    # must not enter the calibration sample.
    outcomes = [
        _resolved(predicted_p_up=0.8, realized_return=0.02),
        _resolved(
            predicted_p_up=0.3,
            realized_return=-0.02,
            is_correct=False,
            predicted=Direction.DOWN,
            realized=Direction.DOWN,
        ),
        _resolved(predicted_p_up=None, realized_return=0.02),
    ]
    perf = await _service().summarize(outcomes)

    assert perf.probability_sample_size == 2
    assert perf.is_calibrated_sample is True
    assert perf.calibration is not None
    assert perf.calibration.brier == pytest.approx(0.065)
    assert perf.calibration.sample_size == 2


@pytest.mark.asyncio
async def test_no_calibration_when_no_probabilities_present():
    perf = await _service().summarize([_resolved(predicted_p_up=None)])
    assert perf.probability_sample_size == 0
    assert perf.calibration is None
    assert perf.is_calibrated_sample is False


# --------------------------------------------------------------------------- #
# Honesty: empty / thin / mock samples                                          #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_empty_batch_is_a_valid_insufficient_summary_not_an_error():
    perf = await _service().summarize([])
    assert perf.sample_size == 0
    assert perf.resolved == 0
    assert perf.scored == 0
    assert perf.directional_accuracy is None
    assert perf.coverage is None
    assert perf.is_reliable is False
    assert any("nothing to measure" in lim for lim in perf.limitations)


@pytest.mark.asyncio
async def test_none_input_raises():
    with pytest.raises(PredictionError):
        await _service().summarize(None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_below_min_sample_is_reported_but_not_reliable():
    # A single perfect hit is still not a track record.
    perf = await _service().summarize([_resolved(is_correct=True)])
    assert perf.scored == 1
    assert perf.directional_accuracy == pytest.approx(1.0)
    assert perf.is_reliable is False
    assert any("below the configured minimum" in lim for lim in perf.limitations)


@pytest.mark.asyncio
async def test_at_min_sample_on_real_data_is_reliable():
    perf = await _service().summarize(
        [_resolved(is_correct=True) for _ in range(_min_sample())]
    )
    assert perf.scored == _min_sample()
    assert perf.is_mock is False
    assert perf.is_reliable is True
    assert perf.limitations == ()


@pytest.mark.asyncio
async def test_mock_sample_is_never_reliable_even_when_large():
    perf = await _service().summarize(
        [_resolved(is_correct=True, is_mock=True) for _ in range(_min_sample())]
    )
    assert perf.scored == _min_sample()
    assert perf.is_mock is True
    assert perf.is_reliable is False
    assert any("MOCK" in lim for lim in perf.limitations)


@pytest.mark.asyncio
async def test_all_pending_reports_no_measurable_performance():
    perf = await _service().summarize([_pending(), _pending()])
    assert perf.resolved == 0
    assert perf.scored == 0
    assert perf.is_reliable is False
    assert any("No outcomes were resolved" in lim for lim in perf.limitations)


# --------------------------------------------------------------------------- #
# Events / determinism / serialisation                                          #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_event_emitted_for_non_empty_batch_only():
    bus = _Bus()
    svc = _service(bus)

    await svc.summarize([])  # empty -> no event
    assert bus.events == []

    await svc.summarize([_resolved(predicted_p_up=0.8, realized_return=0.02)])
    assert len(bus.events) == 1
    published = bus.events[0]
    assert isinstance(published, PredictionPerformanceEvaluated)
    assert published.scored == 1
    assert published.brier == pytest.approx(0.04)
    assert published.is_reliable is False


@pytest.mark.asyncio
async def test_summary_is_deterministic():
    outcomes = [
        _resolved(is_correct=True, predicted_p_up=0.7),
        _resolved(is_correct=False, realized=Direction.DOWN, realized_return=-0.02),
    ]
    a = await _service().summarize(outcomes)
    b = await _service().summarize(outcomes)

    da, db = a.to_dict(), b.to_dict()
    da.pop("generated_at")
    db.pop("generated_at")
    assert da == db


@pytest.mark.asyncio
async def test_to_dict_shape_is_complete():
    perf = await _service().summarize(
        [_resolved(is_correct=True, predicted_p_up=0.8, realized_return=0.02)]
    )
    d = perf.to_dict()

    expected_keys = {
        "sample_size",
        "counts",
        "directional_accuracy",
        "coverage",
        "mean_realized_return",
        "probability_sample_size",
        "calibration",
        "is_reliable",
        "is_mock",
        "limitations",
        "generated_at",
    }
    assert set(d) == expected_keys
    assert set(d["counts"]) == {
        "resolved",
        "pending",
        "unresolvable",
        "scored",
        "hits",
        "misses",
    }
    assert d["calibration"]["brier"] == pytest.approx(0.04)
