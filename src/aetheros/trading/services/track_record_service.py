"""
Prediction track-record service -- deterministic "how have our recorded
predictions actually done?" (spec sections 6, 16, 28, 29).

This is the read-only capstone over the three primitives built for the
"Observe Result -> Evaluate" rung of the autonomous loop:

* the :class:`~aetheros.trading.services.prediction_store.PredictionStore`
  holds the auditable :class:`~aetheros.trading.domain.prediction.PredictionRecord`
  of every report the orchestrator produced;
* the :class:`~aetheros.trading.services.prediction_evaluator.PredictionEvaluator`
  scores one record against the market that unfolded after it;
* the :class:`~aetheros.trading.services.performance_service.PredictionPerformanceService`
  aggregates a batch of those outcomes into a track record.

On its own each is useless to a caller who just wants the answer. This service
composes them: pull the recorded predictions (optionally for one instrument),
resolve each against the freshest candles, and summarise the outcomes into a
single :class:`~aetheros.trading.domain.performance.PredictionPerformance`.

Two boundaries are deliberate and structural:

* **On-demand, not a loop.** ``evaluate`` is a synchronous query run when a
  caller asks; it is *not* the autonomous, scheduled monitoring loop that would
  run continuously and persist the outcomes it computes. That loop, and the
  durable outcome/learning store it needs, remain deferred to the Memory/state
  layer (spec sections 15, 29). This service stores nothing and learns nothing:
  every call recomputes outcomes fresh from the store's records and current
  market data.
* **A resolution failure is skipped, never faked.** If the market data for one
  recorded prediction cannot be fetched, that record is logged and skipped
  rather than sunk as a hit or a miss or crashing the whole query -- a fetch
  outage is not a prediction outcome. The honesty of the summary is inherited
  wholesale from the evaluator and the aggregator: PENDING/UNRESOLVABLE outcomes
  are surfaced, mock resolutions never read as a real edge, and a thin sample is
  reported but never called reliable.
"""

from __future__ import annotations

from ...core.logging import get_logger
from ..domain.outcome import PredictionOutcome
from ..domain.performance import PredictionPerformance
from .performance_service import PredictionPerformanceService
from .prediction_evaluator import PredictionEvaluator
from .prediction_store import PredictionStore

logger = get_logger("trading.track_record")


class PredictionTrackRecordService:
    """Deterministic, on-demand evaluation of the recorded prediction history."""

    def __init__(
        self,
        store: PredictionStore,
        evaluator: PredictionEvaluator,
        performance: PredictionPerformanceService,
    ) -> None:
        self._store = store
        self._evaluator = evaluator
        self._performance = performance

    async def evaluate(
        self,
        *,
        instrument_key: str | None = None,
        limit: int | None = None,
    ) -> PredictionPerformance:
        """
        Resolve the recorded predictions and summarise them into a track record.

        Optionally scoped to one ``instrument_key`` and capped at ``limit`` most
        recent records. An empty history is not an error -- it yields a valid
        "nothing to measure yet" summary flagged not reliable (spec section 28).
        """
        outcomes = await self.resolve_all(
            instrument_key=instrument_key, limit=limit
        )
        return await self._performance.summarize(outcomes)

    async def resolve_all(
        self,
        *,
        instrument_key: str | None = None,
        limit: int | None = None,
    ) -> tuple[PredictionOutcome, ...]:
        """
        Resolve every recorded prediction against the freshest market data.

        Preserves the store's newest-first ordering. A record whose data cannot
        be fetched (a genuine provider outage, not a PENDING/UNRESOLVABLE verdict)
        is logged and omitted rather than fabricated into an outcome, so the
        resulting sample honestly counts only the predictions that could be
        judged.
        """
        records = await self._store.list_records(
            instrument_key=instrument_key, limit=limit
        )
        outcomes: list[PredictionOutcome] = []
        for record in records:
            try:
                outcome = await self._evaluator.resolve_latest(record)
            except Exception:
                logger.exception(
                    "Failed to resolve a recorded prediction; omitting it from "
                    "the track record (prediction_id=%s)",
                    record.id,
                )
                continue
            outcomes.append(outcome)
        return tuple(outcomes)
