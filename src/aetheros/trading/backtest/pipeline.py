"""
The backtest pipeline (Phase 6).

Replays a historical ``MarketData`` series through the *same* production
components the live path uses, turns each step into an auditable prediction,
and measures the forward outcome. This is the "does the intelligence work?"
loop -- run only over recorded historical data, never a live feed.

The two hard rules, both structural:

* **No look-ahead.** Every step reads only ``data.window(0, i + 1)`` -- the
  single place the codebase's past-only guarantee is defined -- so a step can
  never see a future bar. The same slicing primitive the live replay and the
  walk-forward folds use; there is no second, leakier path.
* **Production components only.** The pipeline composes the real
  ``MarketIntelService`` + ``SignalEngineService`` + the deterministic risk and
  probability services the caller wires in -- the identical analysis objects a
  live run uses, not a separate fake implementation that could drift from
  production.

The prediction timestamp is the *window's last bar*, never the wall clock --
that is what makes a replayed prediction resolve honestly against the bars
that followed rather than against "now".
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from ...core.logging import get_logger
from ..domain.enums import Direction
from ..domain.market_data import MarketData
from .evaluator import OutcomeEvaluator, PredictionLike
from .metrics import BacktestMetrics, evaluate
from .outcome import EnrichedOutcome

logger = get_logger("trading.backtest")


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """The full backtest output: predictions, outcomes, and the metrics."""

    instrument_key: str
    timeframe: str
    horizon_bars: int
    step: int
    predictions: tuple[PredictionLike, ...]
    outcomes: tuple[EnrichedOutcome, ...]
    metrics: BacktestMetrics
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "horizon_bars": self.horizon_bars,
            "step": self.step,
            "prediction_count": len(self.predictions),
            "outcome_count": len(self.outcomes),
            "metrics": self.metrics.to_dict(),
            "is_mock": self.is_mock,
        }


def _prediction_id(instrument_key: str, timeframe: str, index: int, direction: str) -> str:
    """Content-addressed prediction id -- deterministic across replays."""
    digest = hashlib.sha1(
        f"{instrument_key}|{timeframe}|{index}|{direction}".encode()
    ).hexdigest()
    return f"bt_{digest[:16]}"


class BacktestPipeline:
    """
    Walk-forward backtest over a candle series using production components.

    ``assess_fn`` is the only injection the caller must supply: it maps a
    past-only ``MarketData`` window to the production signal read
    (``SignalAssessment`` or a duck-typed equivalent exposing ``direction``,
    ``probability_up``, ``entry``, ``targets``, ``invalidation_price``,
    ``confidence``). Supplying it lets the pipeline drive the real
    ``SignalEngineService.assess`` -- or the full ``MarketIntelService`` +
    signal-engine chain -- without this module hard-coding which composition
    is under test. This is deliberately NOT a fake analysis implementation:
    the caller hands the production assess function.

    The evaluator is the deterministic path evaluator; it needs no injection.
    """

    def __init__(self, assess_fn, *, horizon: int = 5, warmup: int = 40, step: int = 1) -> None:
        if assess_fn is None:
            raise ValueError("BacktestPipeline requires a production assess_fn.")
        if horizon < 1:
            raise ValueError("horizon must be >= 1.")
        if warmup < 1:
            raise ValueError("warmup must be >= 1.")
        if step < 1:
            raise ValueError("step must be >= 1.")
        self._assess = assess_fn
        self._horizon = horizon
        self._warmup = warmup
        self._step = step
        self._evaluator = OutcomeEvaluator()

    async def run(
        self,
        data: MarketData,
        *,
        horizon: int | None = None,
        is_mock: bool | None = None,
    ) -> BacktestResult:
        """
        Replay ``data`` and evaluate every step's prediction against the future.

        Steps walk ``warmup`` .. ``last - horizon`` at ``step`` stride. Each
        step's prediction reads only ``window(0, i+1)``; its outcome is measured
        over the bars after that window -- the strict no-look-ahead contract.
        """
        h = horizon or self._horizon
        mock = data.provenance.is_mock if is_mock is None else is_mock
        n = data.count
        last_entry = n - 1 - h

        predictions: list[PredictionLike] = []
        outcomes: list[EnrichedOutcome] = []

        if last_entry >= self._warmup:
            for i in range(self._warmup, last_entry + 1, self._step):
                window = data.window(0, i + 1)
                prediction = await self._predict(data, window, i, h, mock)
                predictions.append(prediction)
                # The evaluator reads candles at/after the prediction's created_at
                # (the window's last bar) out to the horizon -- no future info
                # reaches the *prediction*, only the *measurement*.
                outcomes.append(
                    self._evaluator.evaluate(prediction, data)
                )

        metrics = evaluate(outcomes)
        return BacktestResult(
            instrument_key=data.instrument.key,
            timeframe=data.timeframe.value,
            horizon_bars=h,
            step=self._step,
            predictions=tuple(predictions),
            outcomes=tuple(outcomes),
            metrics=metrics,
            is_mock=mock,
        )

    async def _predict(
        self,
        data: MarketData,
        window: MarketData,
        index: int,
        horizon: int,
        is_mock: bool,
    ) -> PredictionLike:
        """
        Turn one past-only window into a prediction, timestamped to its last bar.

        ``created_at`` is the window's last candle timestamp -- the bar the
        prediction is made *against* -- never the wall clock, so the evaluator
        resolves it against the genuinely-following bars.
        """
        assessment = await self._maybe_await(self._assess(window))
        direction = getattr(assessment, "direction", Direction.UNKNOWN)
        if not isinstance(direction, Direction):
            direction = Direction(direction) if direction else Direction.UNKNOWN
        created = window.last_timestamp
        return PredictionLike(
            prediction_id=_prediction_id(
                data.instrument.key, data.timeframe.value, index, direction.value
            ),
            instrument_key=data.instrument.key,
            timeframe=data.timeframe.value,
            direction=direction,
            created_at=created,
            horizon_bars=horizon,
            entry=getattr(assessment, "entry", None),
            target=self._first_target(assessment),
            invalidation_price=self._invalidation_price(assessment),
            is_mock=is_mock,
            probability_up=getattr(assessment, "probability_up", None),
        )

    @staticmethod
    def _first_target(assessment) -> float | None:
        """The first stated target, if the assessment carries any."""
        targets = getattr(assessment, "targets", None)
        if targets:
            return targets[0]
        return getattr(assessment, "target", None)

    @staticmethod
    def _invalidation_price(assessment) -> float | None:
        """The invalidation *price* if the assessment exposes one."""
        inv = getattr(assessment, "invalidation_price", None)
        if inv is not None:
            return inv
        # A SignalAssessment carries invalidation as a string; pull a numeric
        # level only when the object exposes one separately.
        return getattr(assessment, "stop_loss", None)

    @staticmethod
    async def _maybe_await(value):
        """Await the assess result if it is a coroutine."""
        import inspect
        if inspect.isawaitable(value):
            return await value
        return value
