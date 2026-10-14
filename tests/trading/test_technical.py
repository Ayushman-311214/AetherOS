"""
TechnicalAnalysisService: snapshot computation and honesty about gaps.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import SourceTier, Timeframe
from aetheros.trading.errors import InsufficientDataError
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)

from .conftest import make_market_data


def test_snapshot_has_expected_fields(uptrend_data):
    snap = TechnicalAnalysisService().compute(uptrend_data)
    assert snap.bars == uptrend_data.count
    assert snap.timeframe is Timeframe.D1
    assert snap.last_price == pytest.approx(uptrend_data.closes()[-1])
    # With 120 bars everything should be computable.
    assert snap.sma_fast is not None
    assert snap.sma_slow is not None
    assert snap.rsi is not None
    assert snap.macd is not None
    assert snap.bollinger is not None
    assert snap.atr is not None


def test_uptrend_fast_sma_above_slow(uptrend_data):
    snap = TechnicalAnalysisService().compute(uptrend_data)
    assert snap.sma_fast > snap.sma_slow


def test_downtrend_fast_sma_below_slow(downtrend_data):
    snap = TechnicalAnalysisService().compute(downtrend_data)
    assert snap.sma_fast < snap.sma_slow


def test_insufficient_bars_raises():
    data = make_market_data([100.0])  # single bar
    with pytest.raises(InsufficientDataError):
        TechnicalAnalysisService().compute(data)


def test_missing_indicators_are_none_not_guessed():
    # 15 bars: RSI(14) has one value, but SMA(50) cannot be computed.
    data = make_market_data([100.0 + i for i in range(15)])
    snap = TechnicalAnalysisService().compute(data)
    assert snap.sma_slow is None  # honest gap, not a fabricated number
    assert snap.bars == 15


def test_snapshot_params_recorded(uptrend_data):
    snap = TechnicalAnalysisService().compute(uptrend_data)
    assert snap.params["rsi"] == 14
    assert "sma_fast" in snap.params


def test_mock_tier_propagates(uptrend_data):
    data = make_market_data(
        [100.0 + i for i in range(60)], tier=SourceTier.MOCK
    )
    snap = TechnicalAnalysisService().compute(data)
    assert snap.provenance.tier is SourceTier.MOCK


def test_determinism(uptrend_data):
    a = TechnicalAnalysisService().compute(uptrend_data)
    b = TechnicalAnalysisService().compute(uptrend_data)

    def _stable(snapshot):
        # Strip wall-clock fields; the numeric result is what must be reproducible.
        d = snapshot.to_dict()
        d.pop("computed_at", None)
        prov = dict(d.get("provenance") or {})
        prov.pop("retrieved_at", None)
        d["provenance"] = prov
        return d

    assert _stable(a) == _stable(b)


def test_snapshot_carries_supertrend_and_volume_profile(uptrend_data):
    snap = TechnicalAnalysisService().compute(uptrend_data)
    assert snap.supertrend is not None
    assert snap.supertrend.direction in ("up", "down")
    assert snap.supertrend.stop > 0
    assert snap.volume_profile is not None
    assert snap.volume_profile.value_area_low <= snap.volume_profile.poc
    assert snap.volume_profile.poc <= snap.volume_profile.value_area_high
    assert snap.volume_profile.total_volume > 0


def test_new_indicators_honest_on_thin_series():
    # 12 bars: supertrend(10) is computable and distinct prices give a profile.
    data = make_market_data([100.0 + i * 0.1 for i in range(12)])
    snap = TechnicalAnalysisService().compute(data)
    assert snap.volume_profile is not None
    # 5 bars: below the supertrend warm-up -> None; the volume profile needs
    # only a price range, so it is honestly computable even here (it has no
    # warm-up -- the honest gap for the profile is a price-less series, not a
    # short one).
    thin = make_market_data([100.0, 101.0, 102.0, 103.0, 104.0])
    thin_snap = TechnicalAnalysisService().compute(thin)
    assert thin_snap.supertrend is None
    assert thin_snap.volume_profile is not None
    # A single flat price has no range to bin -> the profile is None.
    flat = make_market_data([100.0] * 5)
    flat_snap = TechnicalAnalysisService().compute(flat)
    assert flat_snap.volume_profile is None


def test_new_params_recorded(uptrend_data):
    snap = TechnicalAnalysisService().compute(uptrend_data)
    assert snap.params["supertrend_period"] == 10
    assert snap.params["volume_profile_bins"] == 20
