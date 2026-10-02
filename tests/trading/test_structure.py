"""
MarketStructureService: swings, levels, trend and structural signals.
"""

from __future__ import annotations

import math

import pytest

from aetheros.trading.domain.enums import TrendState
from aetheros.trading.errors import InsufficientDataError
from aetheros.trading.services.market_structure_service import (
    MarketStructureService,
)

from .conftest import make_market_data


def test_uptrend_detected(uptrend_data):
    structure = MarketStructureService().analyze(uptrend_data)
    assert structure.trend is TrendState.UPTREND
    assert 0.0 <= structure.trend_strength <= 1.0


def test_downtrend_detected(downtrend_data):
    structure = MarketStructureService().analyze(downtrend_data)
    assert structure.trend is TrendState.DOWNTREND


def test_swings_have_evidence():
    # A monotonic series has no interior pivots by definition, so use a series
    # that genuinely oscillates: swing detection is only meaningful there.
    closes = [100.0 + 0.2 * i + 6.0 * math.sin(i / 4.0) for i in range(120)]
    data = make_market_data(closes, symbol="OSC")
    structure = MarketStructureService().analyze(data)
    assert len(structure.swings) > 0
    for s in structure.swings:
        assert s.kind in ("high", "low")
        assert s.price > 0


def test_levels_ranked_by_proximity(uptrend_data):
    structure = MarketStructureService().analyze(uptrend_data)
    last_price = uptrend_data.closes()[-1]
    for levels in (structure.supports, structure.resistances):
        distances = [abs(lvl.price - last_price) for lvl in levels]
        assert distances == sorted(distances)


def test_insufficient_bars_raises():
    data = make_market_data([100.0, 101.0, 102.0])  # < min_bars
    with pytest.raises(InsufficientDataError):
        MarketStructureService().analyze(data)


def test_signals_carry_reference_price(uptrend_data):
    structure = MarketStructureService().analyze(uptrend_data)
    for sig in structure.signals:
        assert sig.reference_price > 0
        assert sig.observation  # non-empty human-readable reason


def test_structure_is_deterministic(uptrend_data):
    a = MarketStructureService().analyze(uptrend_data)
    b = MarketStructureService().analyze(uptrend_data)
    assert a.to_dict() == b.to_dict()


def test_pattern_flags_consistent(uptrend_data):
    structure = MarketStructureService().analyze(uptrend_data)
    # An uptrend should not simultaneously be flagged lower-highs+lower-lows.
    assert not (structure.lower_highs and structure.lower_lows)
