"""
DivergenceService: deterministic price-vs-RSI regular-divergence detection.

Two layers of test. The pivot finder and the divergence classifier are pure
functions, pinned directly on controlled arrays (price + a hand-set oscillator)
so the CONFIRMED bullish/bearish rules are exact and not at the mercy of RSI on a
synthetic series. The integration cases run the full service on crafted candles
and assert the honesty contract (CLAUDE.md sections 5, 28): mock data is never
reliable, too-thin data is UNKNOWN with no fabricated numbers, and a clean series
yields a determinate reliable "no divergence" read.
"""

from __future__ import annotations

import math

import numpy as np

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Assertion, Direction, EvidenceType, SourceTier
from aetheros.trading.services.divergence_service import DivergenceService

from .conftest import make_market_data

_CLEAN_UP = [100.0 + i * 0.5 + (0.2 if i % 2 else -0.2) for i in range(120)]
# A clearly oscillating series so confirmed pivots exist on both sides.
_WAVY = [100.0 + 10.0 * math.sin(i / 3.0) + i * 0.1 for i in range(150)]


def _service() -> DivergenceService:
    return DivergenceService(get_settings())


# ---- pivot finder (pure) ----


def test_pivots_find_strict_local_extrema():
    # Indices:        0    1    2    3    4    5    6
    prices = np.array([5.0, 3.0, 5.0, 7.0, 4.0, 6.0, 8.0])
    lows = DivergenceService._pivots(prices, 1, low=True)
    highs = DivergenceService._pivots(prices, 1, low=False)
    # idx 1 (3.0) and idx 4 (4.0) are strict local minima; idx 3 (7.0) a maximum.
    assert 1 in lows and 4 in lows
    assert 3 in highs


# ---- divergence classifier (pure) ----


def test_regular_bullish_divergence_is_detected():
    # Two pivot lows: older at idx 1 (price 10, rsi 30), newer at idx 4
    # (price 8 = lower low, rsi 40 = higher low) -> bullish divergence.
    closes = np.array([12.0, 10.0, 12.0, 11.0, 8.0, 11.0])
    rsi = np.array([np.nan, 30.0, np.nan, np.nan, 40.0, np.nan])
    result = DivergenceService._regular(closes, rsi, [1, 4], low=True)
    assert result is not None
    direction, price_change, rsi_change = result
    assert direction is Direction.UP
    assert price_change < 0 and rsi_change > 0


def test_regular_bearish_divergence_is_detected():
    # Two pivot highs: older idx 1 (price 10, rsi 70), newer idx 4
    # (price 12 = higher high, rsi 60 = lower high) -> bearish divergence.
    closes = np.array([8.0, 10.0, 8.0, 9.0, 12.0, 9.0])
    rsi = np.array([np.nan, 70.0, np.nan, np.nan, 60.0, np.nan])
    result = DivergenceService._regular(closes, rsi, [1, 4], low=False)
    assert result is not None
    direction, _, rsi_change = result
    assert direction is Direction.DOWN
    assert rsi_change < 0


def test_no_divergence_when_price_and_oscillator_agree():
    # Lower price low AND lower RSI low -> trend confirmed, NOT a divergence.
    closes = np.array([12.0, 10.0, 12.0, 11.0, 8.0, 11.0])
    rsi = np.array([np.nan, 30.0, np.nan, np.nan, 20.0, np.nan])
    assert DivergenceService._regular(closes, rsi, [1, 4], low=True) is None


def test_fewer_than_two_pivots_is_none():
    closes = np.array([1.0, 2.0, 3.0])
    rsi = np.array([50.0, 50.0, 50.0])
    assert DivergenceService._regular(closes, rsi, [1], low=True) is None


# ---- integration (honesty) ----


def test_mock_data_is_never_reliable():
    a = _service().analyze(
        make_market_data(_CLEAN_UP, symbol="MOCKX", tier=SourceTier.MOCK)
    )
    assert a.is_reliable is False
    assert any("MOCK" in lim for lim in a.limitations)


def test_thin_data_is_unknown_not_fabricated():
    a = _service().analyze(make_market_data([100.0 + i for i in range(15)], symbol="THIN"))
    assert a.direction is Direction.UNKNOWN
    assert a.is_reliable is False
    assert a.has_divergence is False
    assert a.price_change_pct is None
    assert a.evidence is None


def test_clean_series_reads_determinate_direction():
    # An oscillating series has confirmed pivots, so the read is determinate and
    # reliable (a divergence or an honest "no divergence"), never UNKNOWN.
    a = _service().analyze(make_market_data(_WAVY, symbol="WAVY"))
    assert a.direction is not Direction.UNKNOWN
    assert a.is_reliable is True
    assert a.pivot_count >= 2
    # If a divergence fired it carries typed MOMENTUM/DETECTED evidence.
    if a.has_divergence:
        assert a.evidence is not None
        assert a.evidence.type is EvidenceType.MOMENTUM
        assert a.evidence.assertion is Assertion.DETECTED


def test_is_deterministic():
    md = make_market_data(_WAVY, symbol="WAVY")
    a = _service().analyze(md).to_dict()
    b = _service().analyze(md).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    if a.get("evidence"):
        a["evidence"].pop("created_at", None)
        b["evidence"].pop("created_at", None)
    assert a == b
