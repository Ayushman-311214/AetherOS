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
