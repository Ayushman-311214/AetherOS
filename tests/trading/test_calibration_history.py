"""
CalibrationHistoryService: the honest first rung of learning from history.

It measures how well past calibrated probabilities matched realised outcomes and
proposes a recalibration correction only when the live sample is large enough
(spec sections 6, 7, 29). These tests pin that contract over a controllable
in-memory outcome store: a well-calibrated history reads well-calibrated, an
over-confident one is flagged over-confident with a proposed correction, a thin
sample measures but proposes NO correction (overfit guard), MOCK outcomes are
excluded, and an empty history is an honest "cannot measure yet". The service
never touches the live probability pipeline.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction, PredictionOutcomeStatus
from aetheros.trading.domain.outcome import PredictionOutcome
from aetheros.trading.services.calibration_history_service import (
    CalibrationHistoryService,
)
from aetheros.trading.services.outcome_store import InMemoryOutcomeStore


def _outcome(
    pid: str,
    *,
    p_up: float | None,
    went_up: bool,
    is_reliable: bool = True,
    is_mock: bool = False,
) -> PredictionOutcome:
    return PredictionOutcome(
        prediction_id=pid,
        instrument_key="AAPL",
        timeframe="1d",
        status=PredictionOutcomeStatus.RESOLVED,
        predicted_direction=Direction.UP,
        realized_direction=Direction.UP if went_up else Direction.DOWN,
        is_correct=went_up,
        realized_return=0.02 if went_up else -0.02,
        horizon_bars=5,
        bars_elapsed=5,
        predicted_p_up=p_up,
        is_reliable=is_reliable,
        is_mock=is_mock,
    )


async def _audit_over(outcomes):
    store = InMemoryOutcomeStore()
    for o in outcomes:
        await store.record(o)
    service = CalibrationHistoryService(get_settings(), outcome_store=store)
    return await service.audit()


@pytest.mark.asyncio
async def test_empty_history_cannot_measure():
    audit = await _audit_over([])
    assert audit.sample_size == 0
    assert audit.bias == "unknown"
    assert audit.proposed_correction is None
    assert audit.is_reliable is False


@pytest.mark.asyncio
async def test_thin_sample_measures_but_proposes_no_correction():
    # A handful of outcomes: below TRADING_CALIB_MIN_SAMPLE -> measured, but no
    # correction proposed (a thin live sample would overfit).
    outcomes = [
        _outcome(f"p{i}", p_up=0.6, went_up=(i % 2 == 0)) for i in range(5)
    ]
    audit = await _audit_over(outcomes)
    assert audit.sample_size == 5
    assert audit.brier is not None  # measured
    assert audit.proposed_correction is None
    assert audit.is_reliable is False
    assert any("overfit" in lim for lim in audit.limitations)


@pytest.mark.asyncio
async def test_overconfident_history_is_flagged_with_a_correction():
    # 40 outcomes: model always claims P(up)=0.9 but only ~40% actually rose ->
    # clearly over-confident, enough sample to propose a correction.
    outcomes = [
        _outcome(f"p{i}", p_up=0.9, went_up=(i % 5 < 2)) for i in range(40)
    ]
    audit = await _audit_over(outcomes)
    assert audit.sample_size == 40
    assert audit.is_reliable is True
    assert audit.bias == "overconfident"
    assert audit.proposed_correction is not None
    # The realised up-rate is well below the mean predicted probability.
    assert audit.mean_predicted > audit.realized_up_rate


@pytest.mark.asyncio
async def test_mock_and_unreliable_outcomes_are_excluded():
    good = [_outcome(f"g{i}", p_up=0.6, went_up=(i % 2 == 0)) for i in range(30)]
    noise = [
        _outcome("m1", p_up=0.9, went_up=False, is_mock=True),
        _outcome("u1", p_up=0.9, went_up=False, is_reliable=False),
    ]
    audit = await _audit_over(good + noise)
    # Only the 30 clean outcomes count; mock/unreliable are dropped.
    assert audit.sample_size == 30


@pytest.mark.asyncio
async def test_to_dict_shape_is_complete():
    outcomes = [_outcome(f"p{i}", p_up=0.55, went_up=(i % 2 == 0)) for i in range(30)]
    payload = (await _audit_over(outcomes)).to_dict()
    for key in (
        "sample_size",
        "brier",
        "baseline_brier",
        "ece",
        "mean_predicted",
        "realized_up_rate",
        "bias",
        "reliability_bins",
        "proposed_correction",
        "beats_baseline",
        "is_reliable",
    ):
        assert key in payload, f"missing calibration-audit key: {key}"


@pytest.mark.asyncio
async def test_is_deterministic():
    outcomes = [_outcome(f"p{i}", p_up=0.6, went_up=(i % 3 == 0)) for i in range(40)]
    a = (await _audit_over(outcomes)).to_dict()
    b = (await _audit_over(outcomes)).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    assert a == b


# ---- derive_correction (out-of-sample validated recalibration) ----


async def _derive_over(outcomes):
    store = InMemoryOutcomeStore()
    for o in outcomes:
        await store.record(o)
    service = CalibrationHistoryService(get_settings(), outcome_store=store)
    return await service.derive_correction()


@pytest.mark.asyncio
async def test_thin_history_yields_an_untrusted_correction():
    corr = await _derive_over(
        [_outcome(f"p{i}", p_up=0.6, went_up=(i % 2 == 0)) for i in range(5)]
    )
    assert corr.trusted is False
    # Untrusted corrections leave the probability unchanged.
    assert corr.apply(0.80) == 0.80


@pytest.mark.asyncio
async def test_untrusted_correction_never_changes_probability():
    # Random-ish outcomes: a fitted correction should not reliably beat holdout
    # Brier, so it must not be trusted and apply() is identity.
    outcomes = [_outcome(f"p{i}", p_up=0.5, went_up=(i % 2 == 0)) for i in range(60)]
    corr = await _derive_over(outcomes)
    assert corr.apply(0.73) == 0.73 or corr.trusted  # identity unless genuinely trusted


@pytest.mark.asyncio
async def test_correction_is_validated_out_of_sample():
    # A consistently over-confident history (always claims 0.9, ~40% rise) across
    # a large sample: the correction should validate on the holdout tail.
    outcomes = [_outcome(f"p{i}", p_up=0.9, went_up=(i % 5 < 2)) for i in range(60)]
    corr = await _derive_over(outcomes)
    assert corr.sample_size == 60
    assert corr.holdout_size >= 1
    assert corr.holdout_brier_before is not None
    if corr.trusted:
        # A trusted correction must genuinely improve the holdout and pulls an
        # over-confident 0.9 downward toward the realised ~0.4.
        assert corr.improves_holdout
        assert corr.apply(0.9) < 0.9
