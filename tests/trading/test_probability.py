"""
ProbabilityService: deterministic, calibrated, look-ahead-safe probability.

These tests pin the spec's central honesty rule (sections 2, 3, 6, 7, 28, 61):
a probability must come from a real, out-of-sample-validated model or not be
surfaced at all. So they prove three things end to end -- (1) on a genuinely
learnable series the model finds an edge and is flagged reliable; (2) on MOCK
data, on a thin sample, and on an unpredictable random walk the number is still
returned but flagged NOT reliable with an explicit reason; (3) the feature
construction is look-ahead-safe: a bar's features never change when future bars
are appended. Everything is deterministic -- no shuffling, no live network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.domain.enums import (
    DataQualityStatus,
    Direction,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.events import ProbabilityEstimated
from aetheros.trading.quant.features import build_features
from aetheros.trading.services.probability_service import ProbabilityService

_BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _series(
    closes,
    *,
    tier: SourceTier = SourceTier.SECONDARY,
    status: DataQualityStatus = DataQualityStatus.OK,
) -> MarketData:
    """Build a valid OHLCV series from a list/array of closes."""
    closes = [float(c) for c in closes]
    candles = []
    prev = closes[0]
    for i, close in enumerate(closes):
        open_ = prev
        hi = max(open_, close) * 1.001
        lo = min(open_, close) * 0.999
        candles.append(
            Candle(
                timestamp=_BASE + timedelta(days=i),
                open=open_,
                high=hi,
                low=lo,
                close=close,
                volume=1_000_000.0 + (i % 7) * 10_000.0,
            )
        )
        prev = close
    return MarketData(
        instrument=Instrument.parse("TEST"),
        timeframe=Timeframe.D1,
        candles=tuple(candles),
        provenance=Provenance(source="test", tier=tier, detail="probability fixture"),
        quality=DataQuality(status=status, issues=(), freshness_seconds=0.0),
    )


def _learnable_closes(n: int = 440) -> np.ndarray:
    """A smooth multi-cycle series: recent momentum genuinely predicts the
    next few bars, so an honest model *should* find an out-of-sample edge."""
    t = np.arange(n, dtype=float)
    log_price = 0.4 * np.sin(2.0 * np.pi * t / 40.0) + 0.0004 * t
    return 100.0 * np.exp(log_price)


def _random_walk_closes(n: int = 440, seed: int = 7) -> np.ndarray:
    """An unpredictable walk: forward direction is (by construction) noise, so
    no honest model should claim an out-of-sample edge on it."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 0.01, size=n)
    return 100.0 * np.exp(np.cumsum(steps))


def _svc(event_bus: EventBus | None = None) -> ProbabilityService:
    return ProbabilityService(get_settings(), event_bus=event_bus)


@pytest.mark.asyncio
async def test_learnable_series_has_out_of_sample_edge():
    data = _series(_learnable_closes())
    est = await _svc().estimate(data, horizon=5)

    # A number is produced and is a well-formed probability distribution.
    assert 0.0 < est.p_up < 1.0
    assert est.p_down == pytest.approx(round(1.0 - est.p_up, 6))

    # The out-of-sample slice must actually beat the naive base-rate baseline
    # (both on Brier and on a coin flip) for the estimate to be reliable.
    assert est.holdout_metrics is not None
    assert est.baseline_brier is not None
    assert est.holdout_metrics.brier < est.baseline_brier
    assert est.holdout_metrics.accuracy > 0.5
    assert est.is_reliable is True
    assert est.provenance.tier is SourceTier.DERIVED
    assert est.direction in (Direction.UP, Direction.DOWN, Direction.SIDEWAYS)


@pytest.mark.asyncio
async def test_mock_data_is_never_reliable():
    data = _series(_learnable_closes(), tier=SourceTier.MOCK)
    est = await _svc().estimate(data, horizon=5)

    # The machinery still runs and returns a number so the reason is visible,
    # but synthetic data can never be a reliable, actionable edge.
    assert 0.0 <= est.p_up <= 1.0
    assert est.is_reliable is False
    assert est.provenance.tier is SourceTier.MOCK
    assert any("MOCK" in lim for lim in est.limitations)


@pytest.mark.asyncio
async def test_thin_sample_is_not_reliable_and_neutral():
    # Far too few bars to fit train/calibration/holdout above the floors.
    data = _series(_learnable_closes(n=40))
    est = await _svc().estimate(data, horizon=5)

    assert est.is_reliable is False
    assert est.p_up == pytest.approx(0.5)
    assert est.p_down == pytest.approx(0.5)
    assert est.direction is Direction.UNKNOWN
    assert est.holdout_metrics is None
    assert any("Not enough labelled history" in lim for lim in est.limitations)


@pytest.mark.asyncio
async def test_random_walk_has_no_edge():
    data = _series(_random_walk_closes())
    est = await _svc().estimate(data, horizon=5)

    # Real-tier data, but an unpredictable series: no out-of-sample edge, so the
    # honest outcome is "not reliable" with the reason stated -- never a
    # fabricated probability dressed up as a signal.
    assert est.is_reliable is False
    assert any("no out-of-sample edge" in lim for lim in est.limitations)


def test_features_are_look_ahead_safe():
    """A bar's feature vector must not change when future bars are appended."""
    closes = _learnable_closes(n=300)
    highs = closes * 1.001
    lows = closes * 0.999
    volumes = np.full(closes.size, 1_000_000.0)

    short = build_features(closes[:200], highs[:200], lows[:200], volumes[:200], horizon=5)
    full = build_features(closes, highs, lows, volumes, horizon=5)

    # Pick an index labelled in BOTH matrices and compare its feature row.
    t = 150
    row_short = short.X[short.indices == t]
    row_full = full.X[full.indices == t]
    assert row_short.shape[0] == 1
    assert row_full.shape[0] == 1
    np.testing.assert_allclose(row_short[0], row_full[0], rtol=0, atol=0)


@pytest.mark.asyncio
async def test_estimate_is_deterministic():
    data = _series(_learnable_closes())
    a = await _svc().estimate(data, horizon=5)
    b = await _svc().estimate(data, horizon=5)

    assert a.p_up == b.p_up
    assert a.raw_p_up == b.raw_p_up
    assert a.is_reliable == b.is_reliable
    assert a.baseline_brier == b.baseline_brier
    assert a.holdout_metrics.to_dict() == b.holdout_metrics.to_dict()


@pytest.mark.asyncio
async def test_metrics_are_in_range():
    data = _series(_learnable_closes())
    est = await _svc().estimate(data, horizon=5)

    for metrics in (est.train_metrics, est.holdout_metrics):
        assert metrics is not None
        assert 0.0 <= metrics.brier <= 1.0
        assert 0.0 <= metrics.accuracy <= 1.0
        assert 0.0 <= metrics.ece <= 1.0
        assert metrics.log_loss >= 0.0
        assert 0.0 <= metrics.base_rate <= 1.0
        assert metrics.sample_size > 0


@pytest.mark.asyncio
async def test_publishes_probability_estimated_event():
    received: list[ProbabilityEstimated] = []
    bus = EventBus()
    await bus.subscribe(ProbabilityEstimated, lambda e: received.append(e))

    data = _series(_learnable_closes())
    est = await _svc(bus).estimate(data, horizon=5)

    assert len(received) == 1
    evt = received[0]
    assert evt.instrument_key == est.instrument.key
    assert evt.horizon == est.horizon
    assert evt.p_up == est.p_up
    assert evt.is_reliable == est.is_reliable
    assert evt.baseline_brier == est.baseline_brier
    assert evt.source_tier == est.provenance.tier.value

