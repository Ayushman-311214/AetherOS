"""
Prediction-performance aggregator -- deterministic "is the system any good?".

Where the :class:`~aetheros.trading.services.prediction_evaluator.PredictionEvaluator`
scores one prediction, this service answers the next question the spec insists on
(CLAUDE.md sections 6, 9, 28, 29): over a batch of already-resolved
:class:`~aetheros.trading.domain.outcome.PredictionOutcome` objects, how good is
the system -- what is its directional accuracy, its coverage, and (when the
predictions carried calibrated probabilities) its Brier score and Expected
Calibration Error? It is the "Evaluate" rung of the autonomous loop, computed as
a pure function over outcomes the caller already holds.

Design constraints, all structural:

* **Pure aggregation, no I/O.** ``summarize`` fetches nothing and stores nothing;
  it counts the outcomes it was handed and defers the calibration arithmetic to
  the shared quant code (:mod:`aetheros.trading.quant.calibration`) rather than
  re-implementing Brier/ECE (section 22). The durable prediction store and the
  live monitoring loop that would feed it over time remain deferred.
* **Only resolved, graded outcomes count.** PENDING and UNRESOLVABLE outcomes are
  tallied for transparency but never enter accuracy or calibration.
* **A thin or mock sample is not a track record.** Fewer than the configured
  ``TRADING_PERF_MIN_SAMPLE`` scored predictions, or any outcome resolved on MOCK
  data, yields ``is_reliable = False`` with an explicit limitation (sections 6,
  9, 28). An empty or insufficient batch is a valid summary, never an error.
"""

from __future__ import annotations

from collections.abc import Sequence

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.outcome import PredictionOutcome
from ..domain.performance import PredictionPerformance
from ..errors import PredictionError
from ..events import PredictionPerformanceEvaluated
from ..quant.calibration import CalibrationReport

logger = get_logger("trading.performance")


def _round(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


class PredictionPerformanceService:
    """Deterministic aggregator of many resolved prediction outcomes."""

    def __init__(self, settings: Settings, *, event_bus: EventBus | None = None) -> None:
        self._settings = settings
        self._event_bus = event_bus

    async def summarize(
        self, outcomes: Sequence[PredictionOutcome]
    ) -> PredictionPerformance:
        """
        Aggregate ``outcomes`` into an auditable :class:`PredictionPerformance`.

        A ``None`` sequence is a programming error and raises; an empty or
        thin sequence is not -- it yields a valid summary flagged not reliable,
        because "not enough evidence yet" is the honest answer, not a failure
        (spec sections 6, 28).
        """
        if outcomes is None:
            raise PredictionError("Cannot summarize a missing outcome sequence.")

        sample_size = len(outcomes)

        resolved = [o for o in outcomes if o.is_resolved]
        pending = sum(1 for o in outcomes if o.status.value == "pending")
        unresolvable = sum(1 for o in outcomes if o.status.value == "unresolvable")

        # Only RESOLVED, directional outcomes are graded hit/miss.
        scored_outcomes = [o for o in resolved if o.is_scored]
        scored = len(scored_outcomes)
        hits = sum(1 for o in scored_outcomes if o.is_correct)
        misses = scored - hits

        directional_accuracy = _round(hits / scored) if scored else None
        coverage = _round(scored / len(resolved)) if resolved else None

        returns = [
            o.realized_return for o in resolved if o.realized_return is not None
        ]
        mean_realized_return = (
            _round(sum(returns) / len(returns)) if returns else None
        )

        # Calibration only over resolved outcomes that carried a reliable P(up).
        calibrated = [
            o
            for o in resolved
            if o.predicted_p_up is not None and o.realized_return is not None
        ]
        probability_sample_size = len(calibrated)
        calibration: CalibrationReport | None = None
        if calibrated:
            p = [o.predicted_p_up for o in calibrated]
            # The binary label is the raw sign of the realised move, matching the
            # target the probability model was trained against.
            y = [1.0 if o.realized_return > 0.0 else 0.0 for o in calibrated]
            calibration = CalibrationReport.evaluate(p, y, bins=10)

        # A mock resolution never counts as a real edge; if any scored/measured
        # outcome came from synthetic data the whole aggregate is not a record.
        is_mock = any(o.is_mock for o in resolved)

        min_sample = self._settings.TRADING_PERF_MIN_SAMPLE
        is_reliable = scored >= min_sample and not is_mock

        limitations = self._limitations(
            sample_size=sample_size,
            resolved=len(resolved),
            scored=scored,
            min_sample=min_sample,
            is_mock=is_mock,
        )

        performance = PredictionPerformance(
            sample_size=sample_size,
            resolved=len(resolved),
            pending=pending,
            unresolvable=unresolvable,
            scored=scored,
            hits=hits,
            misses=misses,
            directional_accuracy=directional_accuracy,
            coverage=coverage,
            mean_realized_return=mean_realized_return,
            probability_sample_size=probability_sample_size,
            calibration=calibration,
            is_reliable=is_reliable,
            is_mock=is_mock,
            limitations=tuple(limitations),
        )

        if sample_size:
            await self._emit(performance)
        return performance

    # ------------------------------------------------------------------

    def _limitations(
        self,
        *,
        sample_size: int,
        resolved: int,
        scored: int,
        min_sample: int,
        is_mock: bool,
    ) -> list[str]:
        limitations: list[str] = []
        if sample_size == 0:
            limitations.append(
                "No prediction outcomes were supplied; there is nothing to "
                "measure yet."
            )
            return limitations
        if resolved == 0:
            limitations.append(
                "No outcomes were resolved; every prediction is still pending or "
                "could not be resolved, so no performance can be measured."
            )
        if scored == 0:
            limitations.append(
                "No scored (resolved, directional) outcomes; directional accuracy "
                "cannot be measured."
            )
        elif scored < min_sample:
            limitations.append(
                f"Only {scored} scored outcome(s), below the configured minimum "
                f"of {min_sample}; the aggregate is reported but is not a "
                "reliable track record."
            )
        if is_mock:
            limitations.append(
                "Sample includes outcomes resolved on synthetic MOCK data; it "
                "validates the aggregation, not a real forecasting track record."
            )
        return limitations

    async def _emit(self, performance: PredictionPerformance) -> None:
        if self._event_bus is None:
            return
        try:
            calibration = performance.calibration
            await self._event_bus.publish(
                PredictionPerformanceEvaluated(
                    sample_size=performance.sample_size,
                    resolved=performance.resolved,
                    scored=performance.scored,
                    directional_accuracy=performance.directional_accuracy,
                    coverage=performance.coverage,
                    brier=calibration.brier if calibration is not None else None,
                    ece=calibration.ece if calibration is not None else None,
                    probability_sample_size=performance.probability_sample_size,
                    is_reliable=performance.is_reliable,
                    is_mock=performance.is_mock,
                )
            )
        except Exception:
            logger.exception("Failed to publish PredictionPerformanceEvaluated")
