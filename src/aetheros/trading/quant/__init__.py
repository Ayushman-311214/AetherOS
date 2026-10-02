"""
Quantitative primitives for the Trading Intelligence core.

Pure-numpy, dependency-light building blocks for probability estimation:
causal feature construction, a deterministic logistic model, and probability
calibration with honest calibration metrics. Nothing here does I/O, touches an
LLM, or fabricates data -- these are the calculators the spec (CLAUDE.md
sections 5, 6, 7, 22) insists live in analytical modules.
"""

from __future__ import annotations

from .calibration import (
    CalibrationReport,
    PlattScaler,
    accuracy,
    brier_score,
    expected_calibration_error,
    log_loss,
    reliability_bins,
)
from .features import FeatureMatrix, build_features
from .model import LogisticRegression

__all__ = [
    "CalibrationReport",
    "PlattScaler",
    "accuracy",
    "brier_score",
    "expected_calibration_error",
    "log_loss",
    "reliability_bins",
    "FeatureMatrix",
    "build_features",
    "LogisticRegression",
]
