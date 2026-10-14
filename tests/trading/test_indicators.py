"""
Deterministic numerical tests for the indicator maths.

These are the reproducible, known-answer cases the spec requires for a
quantitative system (CLAUDE.md section 21). Where a hand-check is easy (SMA of
a constant, RSI of a monotonic series) the expected value is asserted exactly;
elsewhere the invariants that must hold (alignment, warm-up NaNs, bounds) are
asserted.
"""

from __future__ import annotations

import numpy as np
import pytest

from aetheros.trading.indicators import core as ind


def test_sma_constant_series_equals_constant():
    values = np.full(10, 5.0)
    out = ind.sma(values, 3)
    # First two positions are warm-up NaNs.
    assert np.isnan(out[0]) and np.isnan(out[1])
    assert np.allclose(out[2:], 5.0)
    assert out.size == values.size


def test_sma_known_window():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    out = ind.sma(values, 3)
    assert out[2] == pytest.approx(2.0)  # (1+2+3)/3
    assert out[3] == pytest.approx(3.0)
    assert out[4] == pytest.approx(4.0)


def test_sma_insufficient_data_all_nan():
    out = ind.sma(np.array([1.0, 2.0]), 5)
    assert out.size == 2
    assert np.all(np.isnan(out))


def test_ema_matches_manual_recursion():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    period = 3
    out = ind.ema(values, period)
    alpha = 2.0 / (period + 1.0)
    seed = values[:period].mean()  # 2.0
    expected3 = alpha * 4.0 + (1 - alpha) * seed
    expected4 = alpha * 5.0 + (1 - alpha) * expected3
    assert out[period - 1] == pytest.approx(seed)
    assert out[3] == pytest.approx(expected3)
    assert out[4] == pytest.approx(expected4)


def test_rsi_all_gains_saturates_high():
    values = np.arange(1.0, 30.0)  # strictly increasing
    out = ind.rsi(values, 14)
    last = ind.last_finite(out)
    assert last is not None
    assert last > 99.0  # no losses -> RSI near 100


def test_rsi_all_losses_saturates_low():
    values = np.arange(30.0, 1.0, -1.0)  # strictly decreasing
    out = ind.rsi(values, 14)
    last = ind.last_finite(out)
    assert last is not None
    assert last < 1.0


def test_rsi_within_bounds():
    rng = np.random.default_rng(42)
    values = 100 + np.cumsum(rng.normal(0, 1, 200))
    out = ind.rsi(values, 14)
    finite = out[np.isfinite(out)]
    assert np.all((finite >= 0.0) & (finite <= 100.0))


def test_macd_alignment_and_histogram():
    rng = np.random.default_rng(1)
    values = 100 + np.cumsum(rng.normal(0, 1, 100))
    macd_line, signal_line, hist = ind.macd(values)
    assert macd_line.size == signal_line.size == hist.size == values.size
    finite = np.isfinite(macd_line) & np.isfinite(signal_line)
    assert np.allclose(hist[finite], (macd_line - signal_line)[finite])


def test_macd_requires_fast_lt_slow():
    with pytest.raises(ValueError):
        ind.macd(np.arange(50.0), fast=26, slow=12)


def test_atr_positive_and_aligned():
    rng = np.random.default_rng(2)
    close = 100 + np.cumsum(rng.normal(0, 1, 60))
    high = close + np.abs(rng.normal(0, 0.5, 60))
    low = close - np.abs(rng.normal(0, 0.5, 60))
    out = ind.atr(high, low, close, 14)
    assert out.size == close.size
    finite = out[np.isfinite(out)]
    assert np.all(finite >= 0.0)


def test_bollinger_ordering():
    rng = np.random.default_rng(3)
    values = 100 + np.cumsum(rng.normal(0, 1, 60))
    mid, upper, lower = ind.bollinger(values, 20)
    finite = np.isfinite(mid) & np.isfinite(upper) & np.isfinite(lower)
    assert np.all(upper[finite] >= mid[finite])
    assert np.all(mid[finite] >= lower[finite])


def test_vwap_between_low_and_high_extremes():
    high = np.array([10.0, 11.0, 12.0])
    low = np.array([8.0, 9.0, 10.0])
    close = np.array([9.0, 10.0, 11.0])
    volume = np.array([100.0, 100.0, 100.0])
    out = ind.vwap(high, low, close, volume)
    assert out.size == 3
    last = ind.last_finite(out)
    assert low.min() <= last <= high.max()


def test_adx_within_bounds_when_computable():
    rng = np.random.default_rng(4)
    close = 100 + np.cumsum(rng.normal(0, 1, 100))
    high = close + np.abs(rng.normal(0, 0.5, 100))
    low = close - np.abs(rng.normal(0, 0.5, 100))
    out = ind.adx(high, low, close, 14)
    finite = out[np.isfinite(out)]
    if finite.size:
        assert np.all((finite >= 0.0) & (finite <= 100.0))


def test_returns_first_is_nan():
    out = ind.returns(np.array([100.0, 110.0, 99.0]))
    assert np.isnan(out[0])
    assert out[1] == pytest.approx(0.10)
    assert out[2] == pytest.approx(-0.10)


def test_last_finite_none_when_all_nan():
    assert ind.last_finite(np.array([np.nan, np.nan])) is None


def test_zscore_zero_for_constant():
    out = ind.zscore(np.full(30, 7.0), 20)
    finite = out[np.isfinite(out)]
    assert np.allclose(finite, 0.0)


def test_indicators_are_deterministic():
    values = np.linspace(1, 100, 100)
    assert np.allclose(
        np.nan_to_num(ind.rsi(values, 14)),
        np.nan_to_num(ind.rsi(values, 14)),
    )


def test_negative_period_raises():
    with pytest.raises(ValueError):
        ind.sma(np.arange(10.0), 0)


# ==============================================================
# SuperTrend
# ==============================================================


def test_supertrend_uptrend_direction_and_line():
    closes = np.array([100.0 + i * 0.5 for i in range(60)])
    highs = closes + 1.0
    lows = closes - 1.0
    line, direction, stop = ind.supertrend(highs, lows, closes, 10, 3.0)

    assert direction[-1] == 1.0
    # In an up-trend the line tracks close and the stop sits below it.
    assert line[-1] == pytest.approx(closes[-1])
    assert stop[-1] < closes[-1]
    # Alignment and warm-up NaNs.
    assert line.size == direction.size == stop.size == closes.size
    assert np.all(np.isnan(direction[:9]))


def test_supertrend_downtrend_direction_and_line():
    closes = np.array([200.0 - i * 0.5 for i in range(60)])
    highs = closes + 1.0
    lows = closes - 1.0
    line, direction, stop = ind.supertrend(highs, lows, closes, 10, 3.0)

    assert direction[-1] == -1.0
    # In a down-trend the line is the upper band, above close.
    assert line[-1] > closes[-1]
    assert stop[-1] > closes[-1]


def test_supertrend_flips_on_reversal():
    # Rise steadily, then fall hard enough to cross the trailing stop.
    rise = [100.0 + i * 0.8 for i in range(40)]
    fall = [rise[-1] - i * 3.0 for i in range(1, 20)]
    closes = np.array(rise + fall)
    highs = closes + 1.0
    lows = closes - 1.0
    _, direction, _ = ind.supertrend(highs, lows, closes, 10, 3.0)

    assert direction[40] == 1.0  # still up at the peak
    assert direction[-1] == -1.0  # flipped after the reversal
    # Direction is only ever +/-1 where finite.
    finite = direction[np.isfinite(direction)]
    assert np.all(np.isin(finite, (1.0, -1.0)))


def test_supertrend_direction_is_sticky():
    # A one-bar dip that does not breach the band must NOT flip the trend.
    closes = np.array([100.0 + i * 0.8 for i in range(50)])
    closes[25] -= 1.0  # small pullback inside the band
    highs = closes + 1.0
    lows = closes - 1.0
    _, direction, _ = ind.supertrend(highs, lows, closes, 10, 3.0)
    assert direction[-1] == 1.0


def test_supertrend_rejects_bad_arguments():
    closes = np.arange(50.0)
    with pytest.raises(ValueError):
        ind.supertrend(closes, closes, closes, 0)
    with pytest.raises(ValueError):
        ind.supertrend(closes, closes, closes, 10, 0.0)
    with pytest.raises(ValueError):
        ind.supertrend(closes, closes[:-1], closes, 10)


def test_supertrend_insufficient_bars_all_nan():
    closes = np.arange(5.0)
    line, direction, stop = ind.supertrend(closes + 1, closes - 1, closes, 10)
    assert np.all(np.isnan(direction))


# ==============================================================
# Volume Profile
# ==============================================================


def test_volume_profile_poc_on_known_dataset():
    # Two price clusters: 100 (light) and 110 (heavy). POC must be in the 110
    # cluster's bin.
    closes = np.array([100.0] * 10 + [110.0] * 30)
    volumes = np.array([1.0] * 10 + [5.0] * 30)
    profile = ind.volume_profile(closes, volumes, bins=10)
    assert profile is not None
    assert profile.total_volume == pytest.approx(160.0)
    assert 109.0 <= profile.poc <= 111.0
    # Bins sum to the total.
    assert sum(profile.bin_volumes) == pytest.approx(profile.total_volume)
    assert len(profile.bin_edges) == 11
    assert len(profile.bin_volumes) == 10


def test_volume_profile_value_area_contains_poc_and_covers_target():
    rng = np.random.default_rng(7)
    closes = 100 + rng.normal(0, 5, 300)
    volumes = np.abs(rng.normal(1000, 200, 300))
    profile = ind.volume_profile(closes, volumes, bins=20)
    assert profile is not None
    # The value area brackets the POC.
    assert profile.value_area_low <= profile.poc <= profile.value_area_high
    # The covered share meets or exceeds the 70% target (bar the rounding of
    # bin edges: the area is built from whole bins, so it is >= 70%).
    share = 0.0
    for vol, lo in zip(
        profile.bin_volumes, profile.bin_edges[:-1], strict=True
    ):
        if profile.value_area_low <= lo <= profile.value_area_high:
            share += vol
    assert share / profile.total_volume >= 0.70


def test_volume_profile_none_when_no_price_range():
    closes = np.full(10, 100.0)
    volumes = np.full(10, 5.0)
    assert ind.volume_profile(closes, volumes, bins=5) is None


def test_volume_profile_excludes_nan_inputs():
    closes = np.array([100.0, 101.0, np.nan, 102.0, 103.0])
    volumes = np.array([1.0, 1.0, 1.0, np.nan, 1.0])
    profile = ind.volume_profile(closes, volumes, bins=5)
    assert profile is not None
    # Only three usable bars -> total 3.0, not 5.0.
    assert profile.total_volume == pytest.approx(3.0)


def test_volume_profile_rejects_bad_arguments():
    closes = np.arange(10.0)
    with pytest.raises(ValueError):
        ind.volume_profile(closes, closes, bins=1)
    with pytest.raises(ValueError):
        ind.volume_profile(closes, closes, bins=5, value_area_pct=0.0)
    with pytest.raises(ValueError):
        ind.volume_profile(closes, closes[:-1], bins=5)
