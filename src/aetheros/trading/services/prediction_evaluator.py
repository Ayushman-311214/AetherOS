"""
Prediction evaluator -- deterministic "was the previous prediction correct?".

This is the scoring half of the autonomous loop's "Observe Result -> Evaluate"
step (spec sections 6, 16, 29): given a stored
:class:`~aetheros.trading.domain.prediction.PredictionRecord` and the
:class:`~aetheros.trading.domain.market_data.MarketData` that unfolded after it,
it produces the auditable
:class:`~aetheros.trading.domain.outcome.PredictionOutcome`.

The evaluator computes nothing beyond the arithmetic of the realised move; it
locates the entry bar the prediction was made against, walks ``horizon_bars``
forward to the exit bar, and reads the return off the candles. It never fits,
guesses or infers -- every field traces to the record it judged and the candles
it read.

Three honesty rules are structural (spec sections 2, 3, 15, 28, 61):

* **Never a fabricated verdict.** If the entry bar cannot be located or the data
  is unusable the outcome is ``UNRESOLVABLE``; if the horizon has not yet elapsed
  in the available candles it is ``PENDING``. Neither is scored as a hit or a
  miss, and neither is announced as a resolved outcome.
* **Only a directional bet is graded.** A non-directional call (SIDEWAYS /
  UNKNOWN) has nothing to be right or wrong about, so ``is_correct`` stays
  ``None`` even when the move is fully measured.
* **A mock resolution is not a track record.** Resolving against synthetic MOCK
  data validates the scoring machinery, not a forecasting edge; such an outcome
  is flagged ``is_reliable = False`` with an explicit limitation.

The realised *direction* is graded three-way through a small configurable flat
band (a near-flat move is SIDEWAYS, not a directional hit), while the binary
up/down label behind a probability's Brier contribution always uses the raw sign
of the return -- exactly the label the probability model was trained against.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import Direction, PredictionOutcomeStatus
from ..domain.market_data import MarketData
from ..domain.outcome import PredictionOutcome
from ..domain.prediction import PredictionRecord
from ..errors import PredictionError
from ..events import PredictionResolved
from .market_data_service import MarketDataService

logger = get_logger("trading.evaluator")


def _ensure_utc(dt: datetime) -> datetime:
    """Treat a naive timestamp as UTC so comparisons never raise or mislead."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PredictionEvaluator:
    """Deterministic scorer of a past prediction against later market data."""

    def __init__(
        self,
        settings: Settings,
        *,
        market_data: MarketDataService | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._settings = settings
        self._market_data = market_data
        self._event_bus = event_bus

    async def resolve(
        self, record: PredictionRecord, data: MarketData
    ) -> PredictionOutcome:
        """
        Score ``record`` against ``data`` (candles observed after the prediction).

        Raises :class:`PredictionError` if the data is for a different instrument
        or timeframe than the prediction -- resolving a call against the wrong
        series would be a silent, dishonest mismatch, not a valid outcome.
        """
        if record is None:
            raise PredictionError("Cannot resolve a missing prediction record.")
        if data is None:
            raise PredictionError(
                "Cannot resolve a prediction against missing market data."
            )
        if data.instrument.key != record.instrument_key:
            raise PredictionError(
                "Market data instrument does not match the prediction.",
                context={
                    "prediction_instrument": record.instrument_key,
                    "data_instrument": data.instrument.key,
                },
            )
        if data.timeframe.value != record.timeframe:
            raise PredictionError(
                "Market data timeframe does not match the prediction.",
                context={
                    "prediction_timeframe": record.timeframe,
                    "data_timeframe": data.timeframe.value,
                },
            )

        outcome = self._resolve(record, data)
        if outcome.is_resolved:
            await self._emit(outcome)
        return outcome

    async def resolve_latest(self, record: PredictionRecord) -> PredictionOutcome:
        """
        Fetch the freshest candles for the prediction's instrument, then resolve.

        A convenience for the monitoring loop; it requires a wired
        :class:`MarketDataService`. The fetched data may still leave the outcome
        PENDING (horizon not yet elapsed) -- that is the honest answer, not a
        failure.
        """
        if self._market_data is None:
            raise PredictionError(
                "resolve_latest requires a MarketDataService; none is wired.",
                context={"prediction_id": record.id},
            )
        data = await self._market_data.get_candles(
            record.instrument_key, record.timeframe
        )
        return await self.resolve(record, data)

    # ------------------------------------------------------------------

    def _resolve(
        self, record: PredictionRecord, data: MarketData
    ) -> PredictionOutcome:
        predicted = Direction(record.direction)
        is_mock = record.is_mock or data.provenance.is_mock
        limitations: list[str] = []
        if is_mock:
            limitations.append(
                "Prediction resolved against synthetic MOCK data; it validates "
                "the scoring machinery, not a real forecasting track record."
            )

        # Unusable data (MISSING/INVALID) or an empty series cannot be scored.
        if not data.quality.usable or data.count == 0:
            limitations.append(
                f"Data quality is '{data.quality.status.value}'; the prediction "
                "cannot be resolved against it."
            )
            return self._unresolvable(
                record,
                predicted,
                is_mock,
                limitations,
                reason="Market data is unusable or empty.",
            )

        entry_index = self._locate_entry(record, data)
        if entry_index is None:
            return self._unresolvable(
                record,
                predicted,
                is_mock,
                limitations,
                reason=(
                    "No candle at or before the prediction timestamp; the entry "
                    "bar cannot be located in the supplied data."
                ),
            )

        entry_candle = data.candles[entry_index]
        exit_index = entry_index + record.horizon_bars
        last_index = data.count - 1

        # The horizon has not yet elapsed in the data we hold -- too early to judge.
        if exit_index > last_index:
            return PredictionOutcome(
                prediction_id=record.id,
                instrument_key=record.instrument_key,
                timeframe=record.timeframe,
                status=PredictionOutcomeStatus.PENDING,
                predicted_direction=predicted,
                entry_timestamp=_ensure_utc(entry_candle.timestamp),
                entry_price=entry_candle.close,
                horizon_bars=record.horizon_bars,
                bars_elapsed=last_index - entry_index,
                is_reliable=False,
                is_mock=is_mock,
                limitations=tuple(limitations),
                reason=(
                    f"Horizon of {record.horizon_bars} bars has not elapsed; only "
                    f"{last_index - entry_index} bar(s) available after entry."
                ),
            )

        exit_candle = data.candles[exit_index]
        entry_price = entry_candle.close
        exit_price = exit_candle.close
        realized_return = (
            (exit_price - entry_price) / entry_price if entry_price else 0.0
        )
        realized_direction = self._realized_direction(realized_return)

        # Only a directional call has a bet to grade; SIDEWAYS/UNKNOWN do not.
        is_correct: bool | None = None
        if predicted in (Direction.UP, Direction.DOWN):
            is_correct = predicted is realized_direction

        # Brier contribution only when the record carried a reliable P(up); the
        # binary label uses the raw sign of the move, matching the model's target.
        predicted_p_up: float | None = None
        brier_contribution: float | None = None
        if record.probability_reliable and record.probability_up is not None:
            predicted_p_up = record.probability_up
            y = 1.0 if realized_return > 0.0 else 0.0
            brier_contribution = (record.probability_up - y) ** 2

        return PredictionOutcome(
            prediction_id=record.id,
            instrument_key=record.instrument_key,
            timeframe=record.timeframe,
            status=PredictionOutcomeStatus.RESOLVED,
            predicted_direction=predicted,
            realized_direction=realized_direction,
            is_correct=is_correct,
            entry_timestamp=_ensure_utc(entry_candle.timestamp),
            exit_timestamp=_ensure_utc(exit_candle.timestamp),
            entry_price=entry_price,
            exit_price=exit_price,
            realized_return=realized_return,
            horizon_bars=record.horizon_bars,
            bars_elapsed=record.horizon_bars,
            predicted_p_up=predicted_p_up,
            brier_contribution=brier_contribution,
            is_reliable=not is_mock,
            is_mock=is_mock,
            limitations=tuple(limitations),
            reason="Realised move measured over the stated horizon.",
        )

    def _locate_entry(
        self, record: PredictionRecord, data: MarketData
    ) -> int | None:
        """
        Index of the last candle whose open time is at or before the prediction.

        This is the bar the prediction was made against; the exit is measured
        ``horizon_bars`` forward from it. Returns ``None`` if every candle in the
        series opens after the prediction was made.
        """
        created = _ensure_utc(record.created_at)
        entry_index: int | None = None
        for i, candle in enumerate(data.candles):
            if _ensure_utc(candle.timestamp) <= created:
                entry_index = i
            else:
                break
        return entry_index

    def _realized_direction(self, realized_return: float) -> Direction:
        band = self._settings.TRADING_EVAL_FLAT_BAND
        if realized_return > band:
            return Direction.UP
        if realized_return < -band:
            return Direction.DOWN
        return Direction.SIDEWAYS

    def _unresolvable(
        self,
        record: PredictionRecord,
        predicted: Direction,
        is_mock: bool,
        limitations: list[str],
        *,
        reason: str,
    ) -> PredictionOutcome:
        return PredictionOutcome(
            prediction_id=record.id,
            instrument_key=record.instrument_key,
            timeframe=record.timeframe,
            status=PredictionOutcomeStatus.UNRESOLVABLE,
            predicted_direction=predicted,
            horizon_bars=record.horizon_bars,
            is_reliable=False,
            is_mock=is_mock,
            limitations=tuple(limitations),
            reason=reason,
        )

    async def _emit(self, outcome: PredictionOutcome) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                PredictionResolved(
                    prediction_id=outcome.prediction_id,
                    instrument_key=outcome.instrument_key,
                    timeframe=outcome.timeframe,
                    predicted_direction=outcome.predicted_direction.value,
                    realized_direction=(
                        outcome.realized_direction.value
                        if outcome.realized_direction is not None
                        else ""
                    ),
                    is_correct=outcome.is_correct,
                    realized_return=outcome.realized_return,
                    brier_contribution=outcome.brier_contribution,
                    is_reliable=outcome.is_reliable,
                    source_tier="mock" if outcome.is_mock else "derived",
                )
            )
        except Exception:
            logger.exception("Failed to publish PredictionResolved")
