"""
Probability service -- deterministic calibrated directional probability.

Given a market-data series it estimates P(up) over the next ``horizon`` bars by:

1. building a look-ahead-safe feature matrix + forward labels (``quant.features``);
2. splitting the labelled rows *time-ordered* (never shuffled) into train /
   calibration / holdout slices, so the reported edge is genuinely out-of-sample
   and free of data leakage (spec sections 7, 21);
3. fitting a deterministic logistic model on train, Platt-calibrating it on the
   calibration slice, and measuring Brier / log-loss / accuracy / ECE on holdout;
4. scoring the final bar's features to produce the live estimate.

Honesty gates decide ``is_reliable``: mock or unusable data, splits below the
configured minimums, or a model that fails to beat the naive base-rate baseline
on the holdout all yield ``is_reliable = False`` with an explicit limitation. The
number is still returned so the reason is visible, but downstream layers must not
surface an unreliable estimate as a signal -- "insufficient evidence" beats a
fabricated edge (spec sections 2, 3, 28, 61).
"""

from __future__ import annotations

import numpy as np

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import Confidence, Direction, SourceTier
from ..domain.market_data import MarketData
from ..domain.probability import CalibrationMetrics, ProbabilityEstimate
from ..domain.provenance import Provenance
from ..errors import ProbabilityError
from ..events import ProbabilityEstimated
from ..quant.calibration import CalibrationReport, PlattScaler, brier_score
from ..quant.features import build_features
from ..quant.model import LogisticRegression

logger = get_logger("trading.probability")

MODEL_NAME = "logistic_momentum"
MODEL_VERSION = "1.0.0"
CALIBRATION_METHOD = "platt"

# Minimum rows to even attempt a fit, independent of the reliability minimums.
_FIT_FLOOR_TRAIN = 20
_FIT_FLOOR_SLICE = 5


class ProbabilityService:
    """Deterministic, calibrated, look-ahead-safe probability estimator."""

    def __init__(self, settings: Settings, *, event_bus: EventBus | None = None) -> None:
        self._settings = settings
        self._event_bus = event_bus

    async def estimate(
        self, data: MarketData, *, horizon: int | None = None
    ) -> ProbabilityEstimate:
        if data is None:
            raise ProbabilityError("Cannot estimate probability from missing data.")
        s = self._settings
        h = horizon if horizon is not None else s.TRADING_PROB_HORIZON

        estimate = self._estimate(data, h)
        await self._emit(estimate)
        return estimate

    # ------------------------------------------------------------------

    def _estimate(self, data: MarketData, h: int) -> ProbabilityEstimate:
        s = self._settings
        limitations: list[str] = []
        is_mock = data.provenance.is_mock
        if is_mock:
            limitations.append(
                "Probability estimated on synthetic MOCK data; it validates the "
                "model machinery, not a real market edge."
            )
        if not data.quality.ok:
            limitations.append(
                f"Data quality is '{data.quality.status.value}': "
                + "; ".join(data.quality.issues)
            )

        provenance = Provenance(
            source=data.provenance.source,
            tier=SourceTier.MOCK if is_mock else SourceTier.DERIVED,
            detail="deterministic logistic probability estimate (Platt-calibrated)",
        )

        fm = build_features(
            data.closes(), data.highs(), data.lows(), data.volumes(), horizon=h
        )

        # Time-ordered split: earliest -> train, middle -> calibration, latest ->
        # holdout. No shuffling, so evaluation is strictly out-of-sample.
        total = fm.rows
        n_train = int(total * 0.6)
        n_cal = int(total * 0.2)
        n_holdout = total - n_train - n_cal

        too_thin = (
            not data.quality.usable
            or fm.latest is None
            or n_train < _FIT_FLOOR_TRAIN
            or n_cal < _FIT_FLOOR_SLICE
            or n_holdout < _FIT_FLOOR_SLICE
        )
        if too_thin:
            reason = (
                "insufficient usable history"
                if fm.latest is not None and data.quality.usable
                else "no usable latest bar or unusable data"
            )
            limitations.append(
                f"Not enough labelled history to fit a probability model "
                f"({reason}): have {total} labelled rows "
                f"(need >= {_FIT_FLOOR_TRAIN}/{_FIT_FLOOR_SLICE}/{_FIT_FLOOR_SLICE} "
                f"for train/calibration/holdout)."
            )
            return self._neutral(data, provenance, h, fm.feature_names, limitations)

        X_train, y_train = fm.X[:n_train], fm.y[:n_train]
        X_cal, y_cal = fm.X[n_train : n_train + n_cal], fm.y[n_train : n_train + n_cal]
        X_hold, y_hold = fm.X[n_train + n_cal :], fm.y[n_train + n_cal :]

        model = LogisticRegression(
            l2=s.TRADING_PROB_L2,
            learning_rate=s.TRADING_PROB_LR,
            iterations=s.TRADING_PROB_ITERS,
        ).fit(X_train, y_train)

        calibrator = PlattScaler(
            learning_rate=s.TRADING_PROB_LR, iterations=s.TRADING_PROB_ITERS
        ).fit(model.decision_scores(X_cal), y_cal)

        # Calibrated probabilities on each slice.
        p_train = calibrator.transform(model.decision_scores(X_train))
        p_hold = calibrator.transform(model.decision_scores(X_hold))

        bins = s.TRADING_PROB_ECE_BINS
        train_report = CalibrationReport.evaluate(p_train, y_train, bins=bins)
        hold_report = CalibrationReport.evaluate(p_hold, y_hold, bins=bins)

        # Naive baseline: predict the training base rate for every holdout row.
        base_rate_train = float(y_train.mean())
        baseline_brier = round(
            brier_score(np.full(y_hold.shape, base_rate_train), y_hold), 6
        )

        # Live estimate from the final bar's features.
        latest = np.asarray(fm.latest, dtype=float).reshape(1, -1)
        raw_score = model.decision_scores(latest)
        raw_p_up = float(model.predict_proba(latest)[0])
        p_up = float(calibrator.transform(raw_score)[0])
        p_up = min(max(p_up, 0.0), 1.0)
        p_down = round(1.0 - p_up, 6)
        p_up = round(p_up, 6)

        # Honesty / edge gate: the calibrated model must beat the naive baseline
        # on Brier AND be better than a coin flip on holdout accuracy.
        beats_baseline = hold_report.brier < baseline_brier
        beats_coin = hold_report.accuracy > 0.5
        edge = beats_baseline and beats_coin
        is_reliable = data.quality.usable and not is_mock and edge

        if not is_mock and not edge:
            limitations.append(
                "Model shows no out-of-sample edge (holdout Brier "
                f"{hold_report.brier} vs baseline {baseline_brier}, accuracy "
                f"{hold_report.accuracy}); probability is not reliable."
            )

        direction = self._direction(p_up, s.TRADING_PROB_DIRECTION_BAND)
        confidence = Confidence.from_score(abs(p_up - 0.5) * 2.0)

        return ProbabilityEstimate(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            horizon=h,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            calibration_method=CALIBRATION_METHOD,
            feature_names=fm.feature_names,
            raw_p_up=round(raw_p_up, 6),
            p_up=p_up,
            p_down=p_down,
            direction=direction,
            confidence=confidence,
            is_reliable=is_reliable,
            provenance=provenance,
            quality=data.quality,
            train_metrics=self._to_metrics(train_report),
            holdout_metrics=self._to_metrics(hold_report),
            baseline_brier=baseline_brier,
            limitations=tuple(limitations),
        )

    def _neutral(
        self,
        data: MarketData,
        provenance: Provenance,
        h: int,
        feature_names: tuple[str, ...],
        limitations: list[str],
    ) -> ProbabilityEstimate:
        """A non-committal 0.5 estimate when no model can honestly be fit."""
        return ProbabilityEstimate(
            instrument=data.instrument,
            timeframe_value=data.timeframe.value,
            horizon=h,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            calibration_method=CALIBRATION_METHOD,
            feature_names=feature_names,
            raw_p_up=0.5,
            p_up=0.5,
            p_down=0.5,
            direction=Direction.UNKNOWN,
            confidence=Confidence.LOW,
            is_reliable=False,
            provenance=provenance,
            quality=data.quality,
            train_metrics=None,
            holdout_metrics=None,
            baseline_brier=None,
            limitations=tuple(limitations),
        )

    @staticmethod
    def _direction(p_up: float, band: float) -> Direction:
        if p_up >= 0.5 + band:
            return Direction.UP
        if p_up <= 0.5 - band:
            return Direction.DOWN
        return Direction.SIDEWAYS

    @staticmethod
    def _to_metrics(report: CalibrationReport) -> CalibrationMetrics:
        return CalibrationMetrics(
            brier=report.brier,
            log_loss=report.log_loss,
            accuracy=report.accuracy,
            ece=report.ece,
            base_rate=report.base_rate,
            sample_size=report.sample_size,
            reliability_bins=report.bins,
        )

    async def _emit(self, estimate: ProbabilityEstimate) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                ProbabilityEstimated(
                    instrument_key=estimate.instrument.key,
                    timeframe=estimate.timeframe_value,
                    horizon=estimate.horizon,
                    direction=estimate.direction.value,
                    p_up=estimate.p_up,
                    holdout_brier=(
                        estimate.holdout_metrics.brier
                        if estimate.holdout_metrics
                        else None
                    ),
                    baseline_brier=estimate.baseline_brier,
                    is_reliable=estimate.is_reliable,
                    source_tier=estimate.provenance.tier.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish ProbabilityEstimated")
