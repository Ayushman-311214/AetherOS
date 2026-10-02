"""
Deterministic technical-indicator maths.

Pure functions over numpy arrays -- no I/O, no state, no LLM, fully
reproducible. Each series function returns an array the *same length* as its
input, left-padded with ``np.nan`` for the warm-up period, so results align
one-to-one with the candle series and the caller can simply take the last
finite value.

These are the calculators the spec insists live in analytical modules rather
than in a prompt (CLAUDE.md sections 5, 22). They intentionally do NOT decide
anything -- interpretation is the structure/evidence layers' job.
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-12


def _as_float_array(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError("Indicator inputs must be one-dimensional.")
    return arr


def _nan_prefix(length: int) -> np.ndarray:
    return np.full(length, np.nan, dtype=float)


def sma(values: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average. NaN for the first ``period - 1`` positions."""
    arr = _as_float_array(values)
    if period <= 0:
        raise ValueError("period must be positive.")
    n = arr.size
    out = _nan_prefix(n)
    if n < period:
        return out
    cumsum = np.cumsum(np.insert(arr, 0, 0.0))
    windows = (cumsum[period:] - cumsum[:-period]) / period
    out[period - 1 :] = windows
    return out


def ema(values: np.ndarray, period: int) -> np.ndarray:
    """
    Exponential moving average, seeded with the SMA of the first ``period``
    values so the result is deterministic and independent of history length.
    """
    arr = _as_float_array(values)
    if period <= 0:
        raise ValueError("period must be positive.")
    n = arr.size
    out = _nan_prefix(n)
    if n < period:
        return out
    alpha = 2.0 / (period + 1.0)
    seed = arr[:period].mean()
    out[period - 1] = seed
    prev = seed
    for i in range(period, n):
        prev = alpha * arr[i] + (1.0 - alpha) * prev
        out[i] = prev
    return out


def rsi(values: np.ndarray, period: int = 14) -> np.ndarray:
    """Wilder's RSI in [0, 100]. NaN until ``period`` deltas are available."""
    arr = _as_float_array(values)
    if period <= 0:
        raise ValueError("period must be positive.")
    n = arr.size
    out = _nan_prefix(n)
    if n <= period:
        return out
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()

    def _rsi_from(ag: float, al: float) -> float:
        if al < _EPS:
            return 100.0 if ag > _EPS else 50.0
        rs = ag / al
        return 100.0 - (100.0 / (1.0 + rs))

    out[period] = _rsi_from(avg_gain, avg_loss)
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i] = _rsi_from(avg_gain, avg_loss)
    return out


def macd(
    values: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (macd_line, signal_line, histogram), each input-aligned."""
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError("MACD periods must be positive.")
    if fast >= slow:
        raise ValueError("MACD fast period must be shorter than slow period.")
    arr = _as_float_array(values)
    ema_fast = ema(arr, fast)
    ema_slow = ema(arr, slow)
    macd_line = ema_fast - ema_slow
    # Signal line is an EMA of the finite part of the macd line.
    finite = np.isfinite(macd_line)
    signal_line = _nan_prefix(arr.size)
    if finite.any():
        start = int(np.argmax(finite))
        sub = macd_line[start:]
        sub_signal = ema(np.nan_to_num(sub, nan=0.0), signal)
        signal_line[start:] = sub_signal
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    h = _as_float_array(high)
    l = _as_float_array(low)
    c = _as_float_array(close)
    if not (h.size == l.size == c.size):
        raise ValueError("high/low/close must be the same length.")
    n = h.size
    tr = _nan_prefix(n)
    if n == 0:
        return tr
    tr[0] = h[0] - l[0]
    prev_close = c[:-1]
    tr[1:] = np.maximum.reduce(
        [h[1:] - l[1:], np.abs(h[1:] - prev_close), np.abs(l[1:] - prev_close)]
    )
    return tr


def atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """Average True Range (Wilder's smoothing)."""
    if period <= 0:
        raise ValueError("period must be positive.")
    tr = true_range(high, low, close)
    n = tr.size
    out = _nan_prefix(n)
    if n < period:
        return out
    first = np.nanmean(tr[:period])
    out[period - 1] = first
    prev = first
    for i in range(period, n):
        prev = (prev * (period - 1) + tr[i]) / period
        out[i] = prev
    return out


def bollinger(
    values: np.ndarray,
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (middle, upper, lower) Bollinger bands."""
    arr = _as_float_array(values)
    if period <= 0:
        raise ValueError("period must be positive.")
    n = arr.size
    middle = sma(arr, period)
    upper = _nan_prefix(n)
    lower = _nan_prefix(n)
    if n < period:
        return middle, upper, lower
    # Rolling population std over each window.
    for i in range(period - 1, n):
        window = arr[i - period + 1 : i + 1]
        std = window.std()
        upper[i] = middle[i] + num_std * std
        lower[i] = middle[i] - num_std * std
    return middle, upper, lower


def vwap(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
) -> np.ndarray:
    """
    Cumulative volume-weighted average price over the supplied series.

    Note: this is a running VWAP across the whole array (no session reset);
    session-anchored VWAP is a later concern once intraday sessions exist.
    """
    h = _as_float_array(high)
    l = _as_float_array(low)
    c = _as_float_array(close)
    v = _as_float_array(volume)
    if not (h.size == l.size == c.size == v.size):
        raise ValueError("high/low/close/volume must be the same length.")
    n = h.size
    out = _nan_prefix(n)
    if n == 0:
        return out
    typical = (h + l + c) / 3.0
    cum_pv = np.cumsum(typical * v)
    cum_v = np.cumsum(v)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(cum_v > _EPS, cum_pv / cum_v, np.nan)
    return out


def adx(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """Average Directional Index in [0, 100] (Wilder)."""
    h = _as_float_array(high)
    l = _as_float_array(low)
    c = _as_float_array(close)
    if not (h.size == l.size == c.size):
        raise ValueError("high/low/close must be the same length.")
    n = h.size
    out = _nan_prefix(n)
    if n < 2 * period:
        return out

    up_move = h[1:] - h[:-1]
    down_move = l[:-1] - l[1:]
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = true_range(h, l, c)[1:]  # align with the diffed dm arrays

    def _wilder_smooth(x: np.ndarray) -> np.ndarray:
        smoothed = np.full(x.size, np.nan, dtype=float)
        if x.size < period:
            return smoothed
        prev = x[:period].sum()
        smoothed[period - 1] = prev
        for i in range(period, x.size):
            prev = prev - (prev / period) + x[i]
            smoothed[i] = prev
        return smoothed

    tr_s = _wilder_smooth(tr)
    plus_s = _wilder_smooth(plus_dm)
    minus_s = _wilder_smooth(minus_dm)

    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = 100.0 * (plus_s / tr_s)
        minus_di = 100.0 * (minus_s / tr_s)
        dx = 100.0 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

    # dx is indexed against the diffed arrays (offset by 1 from candles).
    finite = np.where(np.isfinite(dx))[0]
    if finite.size == 0:
        return out
    first = int(finite[0])
    if dx.size - first < period:
        return out
    adx_line = np.full(dx.size, np.nan, dtype=float)
    seed = np.nanmean(dx[first : first + period])
    idx = first + period - 1
    adx_line[idx] = seed
    prev = seed
    for i in range(idx + 1, dx.size):
        if np.isfinite(dx[i]):
            prev = (prev * (period - 1) + dx[i]) / period
            adx_line[i] = prev
    # shift back by one to align with the original candle indices
    out[1:] = adx_line
    return out


def returns(values: np.ndarray) -> np.ndarray:
    """Simple period-over-period returns; first element is NaN."""
    arr = _as_float_array(values)
    n = arr.size
    out = _nan_prefix(n)
    if n < 2:
        return out
    with np.errstate(divide="ignore", invalid="ignore"):
        out[1:] = np.where(arr[:-1] != 0.0, arr[1:] / arr[:-1] - 1.0, np.nan)
    return out


def volatility(values: np.ndarray, period: int = 20) -> np.ndarray:
    """Rolling standard deviation of simple returns (annualisation-free)."""
    arr = _as_float_array(values)
    if period <= 0:
        raise ValueError("period must be positive.")
    rets = returns(arr)
    n = rets.size
    out = _nan_prefix(n)
    for i in range(period, n):
        window = rets[i - period + 1 : i + 1]
        if np.all(np.isfinite(window)):
            out[i] = window.std()
    return out


def volume_ma(volume: np.ndarray, period: int = 20) -> np.ndarray:
    """Simple moving average of volume."""
    return sma(volume, period)


def zscore(values: np.ndarray, period: int = 20) -> np.ndarray:
    """Rolling z-score of the series (how many std devs from its mean)."""
    arr = _as_float_array(values)
    if period <= 0:
        raise ValueError("period must be positive.")
    n = arr.size
    out = _nan_prefix(n)
    for i in range(period - 1, n):
        window = arr[i - period + 1 : i + 1]
        mean = window.mean()
        std = window.std()
        out[i] = (arr[i] - mean) / std if std > _EPS else 0.0
    return out


def last_finite(values: np.ndarray) -> float | None:
    """Return the last non-NaN value of a series, or None if there is none."""
    arr = np.asarray(values, dtype=float)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None
    return float(finite[-1])
