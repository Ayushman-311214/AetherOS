"""
Backtesting / prediction tracking / outcomes / calibration (Phase 6).

Covers historical replay, no-lookahead, determinism, prediction creation,
outcome recording, metrics, and liquidity-specific rates. Deterministic
synthetic fixtures only -- the production assess function is a stub that reads
the same real components the live path would (it is NOT a fake analysis engine;
the pipeline drives whatever production assess_fn it's given).

NOTE: named ``test_backtest_pipeline`` (not ``test_backtest``) so it does not
collide with the existing ``BacktestService`` suite.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.trading.backtest.evaluator import OutcomeEvaluator, PredictionLike
from aetheros.trading.backtest.metrics import evaluate, MIN_SAMPLE
from aetheros.trading.backtest.pipeline import BacktestPipeline
from aetheros.trading.backtest.outcome import EnrichedOutcome
from aetheros.trading.domain.enums import (
    DataQualityStatus,
    Direction,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData
from aetheros.trading.domain.provenance import DataQuality, Provenance

_INST = Instrument.parse("TEST")
_PROV = Provenance(source="t", tier=SourceTier.PRIMARY)
_T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _mk(closes, *, symbol="TEST", tf=Timeframe.D1, tier=SourceTier.PRIMARY):
    candles = []
    for i, c in enumerate(closes):
        o = closes[max(0, i - 1)]
        hi = max(o, c) + 0.4
        lo = min(o, c) - 0.4
        candles.append(
            Candle(
                timestamp=_T0 + timedelta(seconds=tf.seconds) * i,
                open=o, high=hi, low=lo, close=c, volume=1e6,
            )
        )
    return MarketData(
        instrument=Instrument.parse(symbol), timeframe=tf,
        candles=tuple(candles),
        provenance=Provenance(source="t", tier=tier),
        quality=DataQuality(status=DataQualityStatus.OK),
    )


_UP = [100.0 + 0.8 * i for i in range(120)]
_DOWN = [200.0 - 0.8 * i for i in range(120)]


def _assess_up(window):
    """A trivially-bullish assess fn (used to test the pipeline mechanics)."""
    class _A:
        direction = Direction.UP
        entry = window.last_price
        targets = (window.last_price * 1.02,)
        invalidation_price = window.last_price * 0.99
        probability_up = 0.7
    return _A()


def _assess_down(window):
    class _A:
        direction = Direction.DOWN
        entry = window.last_price
        targets = (window.last_price * 0.98,)
        invalidation_price = window.last_price * 1.01
        probability_up = 0.3
    return _A()


# ----------------------------------------------------------------------
# Enriched outcome evaluator
# ----------------------------------------------------------------------


def _pred(direction=Direction.UP, created=None, target=None, inv=None, idx=50):
    created = created or _T0 + timedelta(seconds=86400) * idx
    return PredictionLike(
        prediction_id="bt_test",
        instrument_key="TEST",
        timeframe="1d",
        direction=direction,
        created_at=created,
        horizon_bars=5,
        entry=100.0,
        target=target,
        invalidation_price=inv,
    )


def test_evaluator_resolves_correct_call():
    ev = OutcomeEvaluator()
    data = _mk(_UP)
    out = ev.evaluate(_pred(Direction.UP), data)
    assert out.status == "resolved"
    assert out.is_correct is True
    assert out.realized_return is not None and out.realized_return > 0


def test_evaluator_pending_when_horizon_not_elapsed():
    ev = OutcomeEvaluator()
    data = _mk(_UP)
    created = data.last_timestamp
    out = ev.evaluate(_pred(Direction.UP, created=created), data)
    assert out.status == "pending"


def test_evaluator_unresolvable_on_wrong_instrument():
    ev = OutcomeEvaluator()
    out = ev.evaluate(_pred(), _mk(_UP, symbol="OTHER"))
    assert out.status == "unresolvable"


def test_evaluator_excursions_measured():
    ev = OutcomeEvaluator()
    data = _mk(_UP)
    out = ev.evaluate(_pred(Direction.UP), data)
    assert out.max_favorable_excursion > 0
    assert out.max_adverse_excursion <= 0


def test_evaluator_target_and_invalidation_hits():
    ev = OutcomeEvaluator()
    data = _mk(_UP)
    out = ev.evaluate(_pred(Direction.UP, target=102.0, inv=95.0), data)
    assert out.target_hit is True
    assert out.invalidation_hit is False
    assert out.time_to_outcome is not None


def test_evaluator_none_when_no_levels_stated():
    ev = OutcomeEvaluator()
    out = ev.evaluate(_pred(Direction.UP), _mk(_UP))
    assert out.target_hit is None
    assert out.invalidation_hit is None


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------


def _outcome(correct, ret=0.01, mfe=0.02, mae=-0.01, target=None, t_hit=None,
             inv=None, i_hit=None, lim=()):
    return EnrichedOutcome(
        prediction_id="x", instrument_key="TEST", timeframe="1d",
        direction=Direction.UP, status="resolved",
        realized_return=ret, is_correct=correct,
        max_favorable_excursion=mfe, max_adverse_excursion=mae,
        target=target, target_hit=t_hit,
        invalidation_price=inv, invalidation_hit=i_hit,
        horizon_bars=5, bars_elapsed=5, limitations=lim,
    )


def test_metrics_accuracy_and_rates():
    outcomes = [_outcome(True) for _ in range(7)] + [_outcome(False) for _ in range(3)]
    m = evaluate(outcomes, min_sample=3)
    assert m.accuracy == pytest.approx(0.7)
    assert m.win_rate == pytest.approx(0.7)
    assert m.loss_rate == pytest.approx(0.3)
    assert m.false_signal_rate == pytest.approx(0.3)
    assert m.is_reliable is True


def test_metrics_expected_return_and_excursions():
    m = evaluate([_outcome(True, ret=0.02, mfe=0.03, mae=-0.01)] * 12, min_sample=5)
    assert m.expected_return == pytest.approx(0.02)
    assert m.mean_mfe == pytest.approx(0.03)
    assert m.mean_mae == pytest.approx(-0.01)


def test_metrics_level_rates():
    outcomes = (
        [_outcome(True, target=102, t_hit=True, inv=95, i_hit=False)] * 6
        + [_outcome(False, target=102, t_hit=False, inv=95, i_hit=True)] * 6
    )
    m = evaluate(outcomes, min_sample=5)
    assert m.target_hit_rate == pytest.approx(0.5)
    assert m.invalidation_hit_rate == pytest.approx(0.5)


def test_metrics_thin_sample_not_reliable():
    m = evaluate([_outcome(True), _outcome(False)], min_sample=10)
    assert m.is_reliable is False
    assert any("minimum" in lim for lim in m.limitations)


def test_metrics_mock_never_reliable():
    outcomes = [
        EnrichedOutcome(
            prediction_id="x", instrument_key="T", timeframe="1d",
            direction=Direction.UP, status="resolved",
            realized_return=0.01, is_correct=True, is_mock=True,
            horizon_bars=5, bars_elapsed=5,
        )
        for _ in range(15)
    ]
    m = evaluate(outcomes, min_sample=5)
    assert m.is_mock is True
    assert m.is_reliable is False


def test_metrics_liquidity_rates():
    outcomes = (
        [_outcome(True, lim=("sweep:rejection",)) for _ in range(4)]
        + [_outcome(True, lim=("sweep:acceptance",)) for _ in range(4)]
        + [_outcome(True, lim=("absorbed",)) for _ in range(4)]
    )
    m = evaluate(outcomes, min_sample=5)
    # 8 outcomes carry sweep context: 4 rejections, 4 acceptances.
    assert m.sweep_reversal_rate == pytest.approx(4 / 8)
    assert m.sweep_continuation_rate == pytest.approx(4 / 8)
    assert m.absorption_success_rate == pytest.approx(1.0)


# ----------------------------------------------------------------------
# Pipeline: replay + no-look-ahead + determinism
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_replays_and_evaluates():
    pipe = BacktestPipeline(_assess_up, horizon=5, warmup=40, step=10)
    r = await pipe.run(_mk(_UP))
    assert len(r.predictions) > 0
    assert len(r.predictions) == len(r.outcomes)
    assert r.metrics.scored > 0


@pytest.mark.asyncio
async def test_pipeline_no_lookahead_each_step_only_sees_past():
    """
    A step's prediction must not depend on a bar after it.

    Spy on what the assess fn was handed: each window's ``count`` equals the
    step's index + 1 and its ``last_price`` is that bar's close -- never a
    later bar. If the pipeline leaked the future, the window would contain
    bars beyond the step.
    """
    seen = {}

    def spy(window):
        seen[window.count] = window.last_price
        return _assess_up(window)

    pipe = BacktestPipeline(spy, horizon=5, warmup=40, step=10)
    await pipe.run(_mk(_UP))
    # Every window the assess fn saw ended exactly at its step's bar index.
    for count, price in seen.items():
        assert price == pytest.approx(_UP[count - 1], rel=1e-3)


@pytest.mark.asyncio
async def test_pipeline_deterministic():
    pipe = BacktestPipeline(_assess_up, horizon=5, warmup=40, step=10)
    data = _mk(_UP)
    r1 = await pipe.run(data)
    r2 = await pipe.run(data)
    assert [p.prediction_id for p in r1.predictions] == [
        p.prediction_id for p in r2.predictions
    ]
    assert r1.metrics.to_dict() == r2.metrics.to_dict()


@pytest.mark.asyncio
async def test_pipeline_prediction_timestamps_are_window_last_bar():
    pipe = BacktestPipeline(_assess_up, horizon=5, warmup=40, step=10)
    data = _mk(_UP)
    r = await pipe.run(data)
    bar_times = {c.timestamp for c in data.candles}
    for p in r.predictions:
        assert p.created_at in bar_times


# ----------------------------------------------------------------------
# Calibration (uses the existing quant layer)
# ----------------------------------------------------------------------


def test_calibration_report_available_for_probability_predictions():
    from aetheros.trading.quant.calibration import CalibrationReport
    import numpy as np
    p = np.array([0.9, 0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.5, 0.5])
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0, 1, 0])
    rep = CalibrationReport.evaluate(p, y, bins=5)
    assert rep.brier is not None
    assert rep.ece is not None
    assert rep.accuracy is not None
    assert rep.sample_size == 10
    assert len(rep.bins) > 0
