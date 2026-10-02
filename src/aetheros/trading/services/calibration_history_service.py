"""
Calibration-history service -- "has our probability model actually been calibrated?"

The honest first rung of learning from history (CLAUDE.md sections 6, 29): it
reads the accumulated resolved outcomes from the :class:`OutcomeStore`, pairs
each reliably-probabilistic prediction's P(up) with the realised up/down it was
checked against, and measures how well the two agreed -- realised Brier vs a
base-rate baseline, ECE, a reliability curve, and an over-/under-confidence read.
When (and only when) the live track record is large enough to trust, it also
*proposes* a secondary recalibration map fit on that history.

It reuses the quant calibration code (``quant/calibration.py`` -- PlattScaler,
CalibrationReport, brier_score; section 22, not a re-implementation) and is pure
measurement: it never modifies the live probability pipeline. Applying any
proposed correction to future estimates is a separate, explicitly-gated step.

Look-ahead safety (section 7) is structural: the correction is fit on *past*
predictions whose outcomes are now known; nothing about a future estimate enters
it. Overfit safety is the ``TRADING_CALIB_MIN_SAMPLE`` gate -- a thin live sample
proposes no correction. MOCK-sourced outcomes are excluded entirely, so a
synthetic track record can never drive a correction.
"""

from __future__ import annotations

import numpy as np

from ...config.settings import Settings
from ..domain.calibration_audit import CalibrationAudit, CalibrationCorrection
from ..domain.outcome import PredictionOutcome
from ..quant.calibration import CalibrationReport, PlattScaler, brier_score
from .outcome_store import OutcomeStore


class CalibrationHistoryService:
    """Measures realised calibration over the accumulated outcome history."""

    def __init__(self, settings: Settings, *, outcome_store: OutcomeStore) -> None:
        self._settings = settings
        self._outcome_store = outcome_store

    async def audit(
        self,
        *,
        instrument_key: str | None = None,
        limit: int | None = None,
    ) -> CalibrationAudit:
        min_sample = self._settings.TRADING_CALIB_MIN_SAMPLE
        band = self._settings.TRADING_CALIB_BIAS_BAND

        outcomes = await self._outcome_store.list_outcomes(
            instrument_key=instrument_key, limit=limit
        )
        usable = [o for o in outcomes if self._usable(o)]

        if not usable:
            return self._empty(instrument_key)

        p = np.array([float(o.predicted_p_up) for o in usable], dtype=float)
        # Binary up-label from the raw sign of the realised move, matching the
        # model's own training label (independent of any SIDEWAYS dead-band).
        y = np.array(
            [1.0 if float(o.realized_return) > 0.0 else 0.0 for o in usable],
            dtype=float,
        )

        report = CalibrationReport.evaluate(p, y)
        base_rate = float(y.mean())
        baseline_brier = round(brier_score(np.full_like(y, base_rate), y), 6)
        mean_predicted = round(float(p.mean()), 6)

        trustworthy = len(usable) >= min_sample
        bias = self._bias(mean_predicted, base_rate, band, trustworthy)
        proposed = self._propose_correction(p, y) if trustworthy else None
        beats_baseline = report.brier < baseline_brier

        limitations: list[str] = []
        if not trustworthy:
            limitations.append(
                f"Only {len(usable)} reliably-probabilistic outcomes; need "
                f">= {min_sample} before a recalibration correction is proposed "
                "(a thinner live sample would overfit)."
            )

        observation = self._describe(
            len(usable), mean_predicted, base_rate, bias, beats_baseline, trustworthy
        )

        return CalibrationAudit(
            instrument_key=instrument_key,
            sample_size=len(usable),
            brier=report.brier,
            baseline_brier=baseline_brier,
            ece=report.ece,
            mean_predicted=mean_predicted,
            realized_up_rate=round(base_rate, 6),
            bias=bias,
            reliability_bins=report.bins,
            proposed_correction=proposed,
            beats_baseline=beats_baseline,
            is_reliable=trustworthy,
            observation=observation,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    async def derive_correction(
        self,
        *,
        instrument_key: str | None = None,
        limit: int | None = None,
    ) -> CalibrationCorrection:
        """Fit a recalibration map on history and validate it out-of-sample.

        Time-orders the usable outcomes (oldest first), fits a Platt correction on
        the earlier portion, and only trusts it if, on the held-out most-recent
        tail, the corrected Brier beats the uncorrected one and the whole sample
        clears the floor. A correction that fails either gate is returned with
        ``trusted = False`` and leaves probabilities unchanged -- never a
        manufactured edge (spec sections 6, 7, 28).
        """
        min_sample = self._settings.TRADING_CALIB_MIN_SAMPLE
        holdout_fraction = self._settings.TRADING_CALIB_HOLDOUT_FRACTION

        outcomes = await self._outcome_store.list_outcomes(
            instrument_key=instrument_key, limit=limit
        )
        usable = [o for o in outcomes if self._usable(o)]
        # Oldest-first so the HOLDOUT is the most recent tail (a realistic online
        # check: fit on the past, validate on what came after).
        usable.sort(key=lambda o: o.resolved_at)
        n = len(usable)

        if n < min_sample:
            return CalibrationCorrection(
                a=1.0, b=0.0, trusted=False, sample_size=n, holdout_size=0,
                holdout_brier_before=None, holdout_brier_after=None,
                reason=f"only {n} outcomes; need >= {min_sample} to derive a correction.",
            )

        p = np.array([float(o.predicted_p_up) for o in usable], dtype=float)
        y = np.array(
            [1.0 if float(o.realized_return) > 0.0 else 0.0 for o in usable],
            dtype=float,
        )
        hold = max(1, int(round(n * holdout_fraction)))
        train_end = n - hold
        if train_end < 2 or hold < 1:
            return CalibrationCorrection(
                a=1.0, b=0.0, trusted=False, sample_size=n, holdout_size=hold,
                holdout_brier_before=None, holdout_brier_after=None,
                reason="not enough history to form a train/holdout split.",
            )

        p_train, y_train = p[:train_end], y[:train_end]
        p_hold, y_hold = p[train_end:], y[train_end:]
        if float(y_train.min()) == float(y_train.max()):
            return CalibrationCorrection(
                a=1.0, b=0.0, trusted=False, sample_size=n, holdout_size=hold,
                holdout_brier_before=None, holdout_brier_after=None,
                reason="training outcomes are all one class; no correction fittable.",
            )

        scaler = PlattScaler().fit(p_train, y_train)
        a, b = scaler.coefficients
        before = round(brier_score(p_hold, y_hold), 6)
        after = round(brier_score(scaler.transform(p_hold), y_hold), 6)
        trusted = after < before

        return CalibrationCorrection(
            a=round(a, 6),
            b=round(b, 6),
            trusted=trusted,
            sample_size=n,
            holdout_size=hold,
            holdout_brier_before=before,
            holdout_brier_after=after,
            reason=(
                "validated: corrected holdout Brier beats uncorrected."
                if trusted
                else "rejected: correction did not improve the holdout Brier."
            ),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _usable(o: PredictionOutcome) -> bool:
        """A resolved, non-mock, reliable outcome carrying a calibrated P(up)."""
        return (
            o.is_resolved
            and o.predicted_p_up is not None
            and o.realized_return is not None
            and o.is_reliable
            and not o.is_mock
        )

    @staticmethod
    def _bias(
        mean_predicted: float, base_rate: float, band: float, trustworthy: bool
    ) -> str:
        if not trustworthy:
            return "unknown"
        gap = mean_predicted - base_rate
        if gap > band:
            return "overconfident"
        if gap < -band:
            return "underconfident"
        return "well_calibrated"

    @staticmethod
    def _propose_correction(p: np.ndarray, y: np.ndarray) -> tuple[float, float] | None:
        """Fit a secondary Platt map p_corrected = sigmoid(a*p + b) on history.

        Returns the raw-space coefficients, or None if the sample is degenerate
        (all-one-class) so a fit would be meaningless rather than fabricated.
        """
        if float(y.min()) == float(y.max()):
            return None
        scaler = PlattScaler().fit(p, y)
        a, b = scaler.coefficients
        return (round(a, 6), round(b, 6))

    @staticmethod
    def _describe(
        n: int,
        mean_predicted: float,
        base_rate: float,
        bias: str,
        beats_baseline: bool,
        trustworthy: bool,
    ) -> str:
        if not trustworthy:
            return (
                f"Realised calibration measured over {n} outcome(s), but the live "
                "sample is too thin to propose a correction yet."
            )
        edge = "beats" if beats_baseline else "does not beat"
        return (
            f"Over {n} resolved predictions the model averaged P(up)="
            f"{mean_predicted:.0%} against a {base_rate:.0%} realised up-rate "
            f"('{bias}'); its Brier {edge} the base-rate baseline."
        )

    @staticmethod
    def _empty(instrument_key: str | None) -> CalibrationAudit:
        return CalibrationAudit(
            instrument_key=instrument_key,
            sample_size=0,
            brier=None,
            baseline_brier=None,
            ece=None,
            mean_predicted=None,
            realized_up_rate=None,
            bias="unknown",
            reliability_bins=(),
            proposed_correction=None,
            beats_baseline=False,
            is_reliable=False,
            observation=(
                "No reliably-probabilistic resolved outcomes yet; realised "
                "calibration cannot be measured."
            ),
            limitations=(
                "No resolved predictions carrying a reliable calibrated P(up) have "
                "accumulated; run monitoring sweeps over real-data predictions first.",
            ),
        )
