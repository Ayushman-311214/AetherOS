"""
Causal feature construction for probability estimation.

Turns an OHLCV series into a feature matrix whose row ``t`` depends *only* on
candles up to and including ``t`` -- every input indicator is causal (see
``indicators/core.py``), so nothing about bar ``t`` can encode the future. The
label for row ``t`` is the sign of the realised return ``horizon`` bars later
(``1`` if ``close[t+h] > close[t]`` else ``0``); it is computed here from the
full series and is the *target*, never a feature. This split -- causal features
vs. a forward label the model never sees as an input -- is the structural
guarantee against look-ahead bias the spec requires (CLAUDE.md sections 7, 21).

Rows are emitted only where every feature is finite (past the indicator warm-up)
and a full ``horizon`` of future bars exists to label against. A separate
``latest`` row (the feature vector at the final bar, which has no label yet) is
what the live estimate is scored on.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..indicators import core as ind

_EPS = 1e-12

FEATURE_NAMES: tuple[str, ...] = (
    "rsi_14_centered",
    "momentum_10",
    "sma_gap_20",
    "trend_10_30",
    "zscore_20",
    "volatility_20",
    "macd_hist_norm",
    "volume_ratio",
)


def _momentum(values: np.ndarray, period: int) -> np.ndarray:
    """close[t]/close[t-period] - 1, NaN for the first ``period`` positions."""
    arr = np.asarray(values, dtype=float)
    n = arr.size
    out = np.full(n, np.nan, dtype=float)
    if n <= period:
        return out
    with np.errstate(divide="ignore", invalid="ignore"):
        prev = arr[:-period]
        out[period:] = np.where(np.abs(prev) > _EPS, arr[period:] / prev - 1.0, np.nan)
    return out


def _feature_columns(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
) -> np.ndarray:
    """Stack the causal feature columns into an (n, n_features) matrix."""
    n = closes.size

    rsi_c = ind.rsi(closes, 14) - 50.0
    mom = _momentum(closes, 10)

    sma20 = ind.sma(closes, 20)
    with np.errstate(divide="ignore", invalid="ignore"):
        sma_gap = np.where(np.abs(sma20) > _EPS, (closes - sma20) / sma20, np.nan)

    sma10 = ind.sma(closes, 10)
    sma30 = ind.sma(closes, 30)
    with np.errstate(divide="ignore", invalid="ignore"):
        trend = np.where(np.abs(sma30) > _EPS, (sma10 - sma30) / sma30, np.nan)

    z = ind.zscore(closes, 20)
    vol = ind.volatility(closes, 20)

    _, _, hist = ind.macd(closes)
    with np.errstate(divide="ignore", invalid="ignore"):
        macd_norm = np.where(np.abs(closes) > _EPS, hist / closes, np.nan)

    vol_ma = ind.volume_ma(volumes, 20)
    with np.errstate(divide="ignore", invalid="ignore"):
        vol_ratio = np.where(np.abs(vol_ma) > _EPS, volumes / vol_ma - 1.0, np.nan)

    columns = [rsi_c, mom, sma_gap, trend, z, vol, macd_norm, vol_ratio]
    return np.column_stack([c[:n] for c in columns])


@dataclass(frozen=True, slots=True)
class FeatureMatrix:
    """Look-ahead-safe features + forward labels for a single series."""

    feature_names: tuple[str, ...]
    X: np.ndarray  # (rows, n_features), aligned to `indices`
    y: np.ndarray  # (rows,), binary up-label horizon bars ahead
    indices: np.ndarray  # candle index each row was built from
    horizon: int
    latest: np.ndarray | None  # feature row at the final bar (no label), or None
    latest_index: int | None

    @property
    def rows(self) -> int:
        return int(self.X.shape[0])


def build_features(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    *,
    horizon: int,
) -> FeatureMatrix:
    if horizon < 1:
        raise ValueError("horizon must be >= 1.")
    closes = np.asarray(closes, dtype=float)
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    volumes = np.asarray(volumes, dtype=float)
    n = closes.size

    feats = _feature_columns(closes, highs, lows, volumes)
    finite_rows = np.all(np.isfinite(feats), axis=1)

    # Labelled rows: features finite AND a full horizon of future bars exists.
    rows_idx: list[int] = []
    labels: list[float] = []
    for t in range(n):
        if not finite_rows[t]:
            continue
        j = t + horizon
        if j >= n:
            continue
        entry = closes[t]
        if not np.isfinite(entry) or abs(entry) <= _EPS:
            continue
        exit_price = closes[j]
        if not np.isfinite(exit_price):
            continue
        labels.append(1.0 if exit_price > entry else 0.0)
        rows_idx.append(t)

    if rows_idx:
        X = feats[np.asarray(rows_idx, dtype=int)]
        y = np.asarray(labels, dtype=float)
        indices = np.asarray(rows_idx, dtype=int)
    else:
        X = np.empty((0, feats.shape[1]), dtype=float)
        y = np.empty((0,), dtype=float)
        indices = np.empty((0,), dtype=int)

    latest = None
    latest_index = None
    if n > 0 and finite_rows[n - 1]:
        latest = feats[n - 1]
        latest_index = n - 1

    return FeatureMatrix(
        feature_names=FEATURE_NAMES,
        X=X,
        y=y,
        indices=indices,
        horizon=horizon,
        latest=latest,
        latest_index=latest_index,
    )
