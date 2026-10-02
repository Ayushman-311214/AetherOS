"""
Deterministic logistic regression in pure numpy.

A small, fully reproducible binary classifier: zero-initialised weights, a fixed
L2 penalty, a fixed learning rate and a fixed iteration budget, trained by batch
gradient descent. Features are standardised using statistics learned *only* from
the training rows (the mean/std are stored and reapplied at predict time), so no
information from the calibration or holdout slices leaks into the fit -- the
look-ahead / data-leakage guarantee the spec demands (CLAUDE.md sections 7, 21).

There is deliberately no sklearn/scipy dependency: the maths is simple enough to
own outright, and owning it keeps the result bit-for-bit deterministic across
environments, which is what makes the backtested edge auditable.
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-12
# Clamp the logit argument so exp() cannot overflow on extreme standardised inputs.
_Z_CLAMP = 30.0


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -_Z_CLAMP, _Z_CLAMP)
    return 1.0 / (1.0 + np.exp(-z))


class LogisticRegression:
    """A deterministic L2-regularised logistic classifier (batch gradient descent)."""

    def __init__(
        self,
        *,
        l2: float = 1.0,
        learning_rate: float = 0.1,
        iterations: int = 500,
    ) -> None:
        if l2 < 0.0:
            raise ValueError("l2 must be non-negative.")
        if learning_rate <= 0.0:
            raise ValueError("learning_rate must be positive.")
        if iterations < 1:
            raise ValueError("iterations must be >= 1.")
        self._l2 = float(l2)
        self._lr = float(learning_rate)
        self._iters = int(iterations)
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None
        self._weights: np.ndarray | None = None
        self._bias: float = 0.0

    @property
    def is_fitted(self) -> bool:
        return self._weights is not None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegression":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim != 2:
            raise ValueError("X must be a 2-D feature matrix.")
        if y.ndim != 1 or y.shape[0] != X.shape[0]:
            raise ValueError("y must be a 1-D vector aligned with X rows.")

        # Standardise on the TRAINING rows only; store for predict time.
        self._mean = X.mean(axis=0)
        std = X.std(axis=0)
        self._std = np.where(std < _EPS, 1.0, std)  # guard constant columns
        Xs = (X - self._mean) / self._std

        n, d = Xs.shape
        w = np.zeros(d, dtype=float)
        b = 0.0
        for _ in range(self._iters):
            p = _sigmoid(Xs @ w + b)
            err = p - y
            grad_w = (Xs.T @ err) / n + self._l2 * w / n
            grad_b = float(err.mean())
            w -= self._lr * grad_w
            b -= self._lr * grad_b
        self._weights = w
        self._bias = b
        return self

    def _standardise(self, X: np.ndarray) -> np.ndarray:
        assert self._mean is not None and self._std is not None
        return (np.asarray(X, dtype=float) - self._mean) / self._std

    def decision_scores(self, X: np.ndarray) -> np.ndarray:
        """Raw logits (w·x + b) -- the natural input to Platt calibration."""
        if self._weights is None:
            raise RuntimeError("Model is not fitted.")
        Xs = self._standardise(X)
        if Xs.ndim == 1:
            Xs = Xs.reshape(1, -1)
        return Xs @ self._weights + self._bias

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """P(y=1) for each row of X."""
        return _sigmoid(self.decision_scores(X))
