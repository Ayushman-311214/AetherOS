"""
Probability calibration (Platt scaling) and honest calibration metrics.

A raw model probability is not necessarily *calibrated*: when the model says
0.7, do events actually happen ~70% of the time? Platt scaling fits a 1-D
logistic map ``sigmoid(a*score + b)`` on a held-out slice to correct that, and
the metrics here measure whether it worked -- Brier score, log-loss, accuracy
and Expected Calibration Error (ECE), plus the reliability bins ECE is built
from. These are the measures the spec names (CLAUDE.md section 6); reporting
them, rather than a bare probability, is what keeps a prediction auditable.

All pure numpy, deterministic, no sklearn/scipy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

_EPS = 1e-12
_Z_CLAMP = 30.0


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -_Z_CLAMP, _Z_CLAMP)
    return 1.0 / (1.0 + np.exp(-z))


def _clip01(p: np.ndarray) -> np.ndarray:
    return np.clip(p, _EPS, 1.0 - _EPS)


class PlattScaler:
    """Deterministic 1-D logistic calibrator: p_cal = sigmoid(a * score + b)."""

    def __init__(self, *, learning_rate: float = 0.1, iterations: int = 500) -> None:
        if learning_rate <= 0.0:
            raise ValueError("learning_rate must be positive.")
        if iterations < 1:
            raise ValueError("iterations must be >= 1.")
        self._lr = float(learning_rate)
        self._iters = int(iterations)
        self._a: float = 1.0
        self._b: float = 0.0
        self._fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    @property
    def coefficients(self) -> tuple[float, float]:
        return (self._a, self._b)

    def fit(self, scores: np.ndarray, y: np.ndarray) -> "PlattScaler":
        s = np.asarray(scores, dtype=float).ravel()
        t = np.asarray(y, dtype=float).ravel()
        if s.shape != t.shape:
            raise ValueError("scores and y must have the same shape.")
        if s.size == 0:
            raise ValueError("cannot fit Platt scaler on an empty sample.")
        # Standardise the scores for a stable, scale-independent fit; fold the
        # standardisation back into (a, b) so transform() works on raw scores.
        mean = float(s.mean())
        std = float(s.std())
        std = std if std > _EPS else 1.0
        z = (s - mean) / std

        a, b = 0.0, 0.0
        n = z.size
        for _ in range(self._iters):
            p = _sigmoid(a * z + b)
            err = p - t
            grad_a = float((err * z).mean())
            grad_b = float(err.mean())
            a -= self._lr * grad_a
            b -= self._lr * grad_b
        # Map back to raw-score space: a*z + b = (a/std)*s + (b - a*mean/std).
        self._a = a / std
        self._b = b - a * mean / std
        self._fitted = True
        return self

    def transform(self, scores: np.ndarray) -> np.ndarray:
        s = np.asarray(scores, dtype=float)
        return _sigmoid(self._a * s + self._b)


def brier_score(p: np.ndarray, y: np.ndarray) -> float:
    """Mean squared error between probability and outcome; lower is better."""
    p = np.asarray(p, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if p.size == 0:
        return float("nan")
    return float(np.mean((p - y) ** 2))


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    """Binary cross-entropy; lower is better."""
    p = _clip01(np.asarray(p, dtype=float).ravel())
    y = np.asarray(y, dtype=float).ravel()
    if p.size == 0:
        return float("nan")
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def accuracy(p: np.ndarray, y: np.ndarray, *, threshold: float = 0.5) -> float:
    """Share of rows whose thresholded prediction matches the outcome."""
    p = np.asarray(p, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if p.size == 0:
        return float("nan")
    return float(np.mean((p >= threshold).astype(float) == y))


def reliability_bins(
    p: np.ndarray, y: np.ndarray, *, bins: int = 10
) -> list[dict[str, float]]:
    """
    Group predictions into equal-width probability bins and, per non-empty bin,
    report the mean predicted probability vs the observed frequency. This is the
    raw material of a reliability diagram and of ECE.
    """
    p = np.asarray(p, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    out: list[dict[str, float]] = []
    if p.size == 0:
        return out
    edges = np.linspace(0.0, 1.0, bins + 1)
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        # Last bin is closed on the right so p == 1.0 is counted.
        mask = (p >= lo) & (p < hi) if i < bins - 1 else (p >= lo) & (p <= hi)
        count = int(mask.sum())
        if count == 0:
            continue
        out.append(
            {
                "lower": round(float(lo), 6),
                "upper": round(float(hi), 6),
                "count": count,
                "mean_predicted": round(float(p[mask].mean()), 6),
                "observed_frequency": round(float(y[mask].mean()), 6),
            }
        )
    return out


def expected_calibration_error(
    p: np.ndarray, y: np.ndarray, *, bins: int = 10
) -> float:
    """
    ECE: the sample-weighted average gap between predicted probability and
    observed frequency across bins. 0 is perfectly calibrated.
    """
    p = np.asarray(p, dtype=float).ravel()
    if p.size == 0:
        return float("nan")
    total = p.size
    ece = 0.0
    for b in reliability_bins(p, y, bins=bins):
        weight = b["count"] / total
        ece += weight * abs(b["mean_predicted"] - b["observed_frequency"])
    return float(ece)


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """A numeric bundle of calibration measures over one evaluation slice."""

    brier: float
    log_loss: float
    accuracy: float
    ece: float
    base_rate: float
    sample_size: int
    bins: tuple[dict[str, float], ...] = ()

    @classmethod
    def evaluate(
        cls, p: np.ndarray, y: np.ndarray, *, bins: int = 10
    ) -> "CalibrationReport":
        y_arr = np.asarray(y, dtype=float).ravel()
        return cls(
            brier=round(brier_score(p, y_arr), 6),
            log_loss=round(log_loss(p, y_arr), 6),
            accuracy=round(accuracy(p, y_arr), 6),
            ece=round(expected_calibration_error(p, y_arr, bins=bins), 6),
            base_rate=round(float(y_arr.mean()) if y_arr.size else float("nan"), 6),
            sample_size=int(y_arr.size),
            bins=tuple(reliability_bins(p, y_arr, bins=bins)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brier": self.brier,
            "log_loss": self.log_loss,
            "accuracy": self.accuracy,
            "ece": self.ece,
            "base_rate": self.base_rate,
            "sample_size": self.sample_size,
            "reliability_bins": [dict(b) for b in self.bins],
        }
