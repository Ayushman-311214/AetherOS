"""
Monitoring service -- one bounded "Observe Result -> Evaluate" sweep.

Runs a single, deterministic monitoring pass over the recorded predictions (spec
sections 16, 29): it resolves the outstanding predictions against the freshest
market data, summarises them into an aggregate track record, announces a
:class:`~aetheros.trading.events.MonitoringSweepCompleted` event, and returns a
:class:`~aetheros.trading.domain.monitoring.MonitoringReport`.

It composes the existing primitives (reuse, not duplication -- section 22):
:class:`PredictionTrackRecordService` resolves the recorded predictions and
:class:`PredictionPerformanceService` aggregates them. It adds the bounded
"sweep" framing a scheduler can call repeatedly plus the event announcement.

Two boundaries are deliberate and structural (spec sections 15, 28, 29):

* **One pass, not a background loop.** ``run_once`` is a single bounded sweep. The
  actual continuously-running, self-scheduling autonomous loop -- and the durable
  outcome store that would let performance *accumulate* across sweeps rather than
  recompute fresh each time -- remain deferred to the Memory/state layer. This
  service stores nothing new; it recomputes from the prediction store each call.
* **Honesty inherited wholesale.** PENDING/UNRESOLVABLE outcomes are surfaced, a
  resolution that cannot be fetched is skipped (never faked), and a thin or MOCK
  sample is reported but never announced as an earned track record.
"""

from __future__ import annotations

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import PredictionOutcomeStatus
from ..domain.monitoring import MonitoringReport
from ..events import MonitoringSweepCompleted
from .outcome_store import OutcomeStore
from .performance_service import PredictionPerformanceService
from .track_record_service import PredictionTrackRecordService

logger = get_logger("trading.monitoring")


class MonitoringService:
    """Runs one bounded monitoring sweep over the recorded predictions."""

    def __init__(
        self,
        track_record: PredictionTrackRecordService,
        performance: PredictionPerformanceService,
        *,
        outcome_store: OutcomeStore | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._track_record = track_record
        self._performance = performance
        self._outcome_store = outcome_store
        self._event_bus = event_bus

    async def run_once(
        self,
        *,
        instrument_key: str | None = None,
        limit: int | None = None,
    ) -> MonitoringReport:
        outcomes = await self._track_record.resolve_all(
            instrument_key=instrument_key, limit=limit
        )
        performance = await self._performance.summarize(outcomes)

        resolved = sum(
            1 for o in outcomes if o.status is PredictionOutcomeStatus.RESOLVED
        )
        pending = sum(
            1 for o in outcomes if o.status is PredictionOutcomeStatus.PENDING
        )
        unresolvable = sum(
            1 for o in outcomes if o.status is PredictionOutcomeStatus.UNRESOLVABLE
        )

        # Durable accumulation (opt-in): persist each outcome so sweeps build a
        # lasting record instead of recomputing from zero. A store failure is
        # logged and swallowed -- it can never sink a sweep that resolved honestly.
        if self._outcome_store is not None:
            await self._persist(outcomes)

        report = MonitoringReport(
            swept=len(outcomes),
            resolved=resolved,
            pending=pending,
            unresolvable=unresolvable,
            outcomes=outcomes,
            performance=performance,
            instrument_key=instrument_key,
        )
        await self._emit(report)
        return report

    # ------------------------------------------------------------------

    async def _persist(self, outcomes) -> None:
        for outcome in outcomes:
            try:
                await self._outcome_store.record(outcome)
            except Exception:
                logger.exception(
                    "Failed to persist a monitoring outcome; continuing"
                )

    async def _emit(self, report: MonitoringReport) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                MonitoringSweepCompleted(
                    swept=report.swept,
                    resolved=report.resolved,
                    pending=report.pending,
                    unresolvable=report.unresolvable,
                    scored=report.performance.scored,
                    directional_accuracy=report.performance.directional_accuracy,
                    is_reliable=report.performance.is_reliable,
                    is_mock=report.performance.is_mock,
                )
            )
        except Exception:
            logger.exception("Failed to publish MonitoringSweepCompleted")
