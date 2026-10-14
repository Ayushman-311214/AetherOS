"""
The enriched outcome evaluator.

Measures a prediction's *path* through the candles that unfolded after it --
not just whether the endpoint agreed, but how the move behaved along the way.
Pure arithmetic over a candle window; it never fits or infers.

The measured quantities:

* **Excursions** -- ``max_favorable_excursion`` and ``max_adverse_excursion``,
  the furthest the move ran for and against the predicted direction, read off
  the bar highs/lows (the honest intra-bar extremes, since a bar's range is
  where price actually traded).
* **Target / invalidation hits** -- whether price *traded through* the stated
  target or invalidation level during the window. ``None`` when the prediction
  stated no such level -- the honest "nothing to check against".
* **Time to outcome** -- the bars to the first level hit, or the horizon when
  nothing was hit.

Honesty is structural: an unusable window or an unlocatable entry yields
UNRESOLVABLE; a horizon not yet elapsed yields PENDING; the hit flags are only
ever ``True`` when the level was genuinely crossed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ..domain.enums import Direction
from ..domain.market_data import Candle, MarketData
from .outcome import EnrichedOutcome


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class PredictionLike:
    """
    The minimal contract an evaluator needs to score a prediction.

    Adapts any of the system's prediction shapes (``PredictionRecord``, a
    ``SignalAssessment``, or a test fixture) into the fields the path
    measurement reads: id, instrument, timeframe, direction, created_at,
    horizon, entry, target, invalidation, is_mock.
    """

    prediction_id: str
    instrument_key: str
    timeframe: str
    direction: Direction
    created_at: datetime
    horizon_bars: int
    entry: float | None = None
    target: float | None = None
    invalidation_price: float | None = None
    is_mock: bool = False
    probability_up: float | None = None


class OutcomeEvaluator:
    """Deterministic path evaluator over a candle window."""

    def evaluate(
        self,
        prediction: PredictionLike,
        data: MarketData,
    ) -> EnrichedOutcome:
        """
        Measure ``prediction`` against ``data`` (the candles that unfolded).

        Honest statuses:
        * ``unresolvable`` -- unusable/empty data, wrong instrument/timeframe,
          or the entry bar could not be located.
        * ``pending`` -- the horizon has not yet elapsed in the window.
        * ``resolved`` -- the move over the horizon was measured, with its path.
        """
        if data is None or not data.quality.usable or data.count == 0:
            return self._unresolvable(
                prediction, "Unusable or empty market data."
            )
        if data.instrument.key != prediction.instrument_key:
            return self._unresolvable(
                prediction,
                f"Instrument mismatch: prediction is for "
                f"'{prediction.instrument_key}', data is "
                f"'{data.instrument.key}'.",
            )
        if data.timeframe.value != prediction.timeframe:
            return self._unresolvable(
                prediction,
                f"Timeframe mismatch: prediction is "
                f"'{prediction.timeframe}', data is '{data.timeframe.value}'.",
            )

        entry_index = self._locate_entry(prediction, data)
        if entry_index is None:
            return self._unresolvable(
                prediction,
                "No candle at or before the prediction timestamp.",
            )

        entry = data.candles[entry_index]
        entry_price = entry.close
        exit_index = entry_index + prediction.horizon_bars
        last_index = data.count - 1
        bars_elapsed = max(0, last_index - entry_index)

        # PENDING: horizon not elapsed yet -- too early to judge honestly.
        if exit_index > last_index:
            return EnrichedOutcome(
                prediction_id=prediction.prediction_id,
                instrument_key=prediction.instrument_key,
                timeframe=prediction.timeframe,
                direction=prediction.direction,
                status="pending",
                entry_price=entry_price,
                entry_timestamp=_ensure_utc(entry.timestamp),
                horizon_bars=prediction.horizon_bars,
                bars_elapsed=bars_elapsed,
                is_reliable=False,
                is_mock=prediction.is_mock or data.provenance.is_mock,
                reason=(
                    f"Horizon of {prediction.horizon_bars} bars has not "
                    f"elapsed; {bars_elapsed} available."
                ),
            )

        exit_price = data.candles[exit_index].close
        path = data.candles[entry_index : exit_index + 1]
        realized_return = (
            (exit_price - entry_price) / entry_price if entry_price else 0.0
        )
        realized_direction = self._realized_direction(realized_return)

        # Excursions + level hits over the path.
        mfe, mae = self._excursions(
            path, entry_price, prediction.direction
        )
        target_hit, invalidation_hit, t_outcome = self._hits(
            path,
            entry_index,
            entry_price,
            prediction.direction,
            prediction.target,
            prediction.invalidation_price,
        )

        is_correct: bool | None = None
        if prediction.direction in (Direction.UP, Direction.DOWN):
            is_correct = prediction.direction is realized_direction

        return EnrichedOutcome(
            prediction_id=prediction.prediction_id,
            instrument_key=prediction.instrument_key,
            timeframe=prediction.timeframe,
            direction=prediction.direction,
            status="resolved",
            entry_price=entry_price,
            exit_price=exit_price,
            entry_timestamp=_ensure_utc(entry.timestamp),
            outcome_timestamp=_ensure_utc(
                data.candles[
                    min(exit_index, entry_index + (t_outcome or 0))
                ].timestamp
            ),
            realized_return=round(realized_return, 6),
            realized_direction=realized_direction,
            is_correct=is_correct,
            horizon_bars=prediction.horizon_bars,
            bars_elapsed=prediction.horizon_bars,
            max_favorable_excursion=round(mfe, 6),
            max_adverse_excursion=round(mae, 6),
            target_hit=target_hit,
            invalidation_hit=invalidation_hit,
            target=prediction.target,
            invalidation_price=prediction.invalidation_price,
            time_to_outcome=t_outcome,
            is_reliable=not (prediction.is_mock or data.provenance.is_mock),
            is_mock=prediction.is_mock or data.provenance.is_mock,
            reason="Path measured over the stated horizon.",
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _locate_entry(prediction, data: MarketData) -> int | None:
        created = _ensure_utc(prediction.created_at)
        idx = None
        for i, c in enumerate(data.candles):
            if _ensure_utc(c.timestamp) <= created:
                idx = i
            else:
                break
        return idx

    @staticmethod
    def _realized_direction(ret: float) -> Direction:
        band = 0.001
        if ret > band:
            return Direction.UP
        if ret < -band:
            return Direction.DOWN
        return Direction.SIDEWAYS

    @staticmethod
    def _excursions(
        path: tuple[Candle, ...], entry: float, direction: Direction
    ) -> tuple[float, float]:
        """
        Max favorable / adverse excursion, signed in the predicted direction.

        Measured from the bar highs/lows across the path -- the honest extremes
        price actually traded to. ``favorable`` is the furthest the move ran in
        the predicted direction; ``adverse`` the furthest against it.
        """
        if direction is Direction.UP:
            favorable = max((c.high - entry) for c in path)
            adverse = min((c.low - entry) for c in path)
        elif direction is Direction.DOWN:
            favorable = max((entry - c.low) for c in path)
            adverse = min((entry - c.high) for c in path)
        else:
            favorable = max((c.high - entry) for c in path)
            adverse = min((c.low - entry) for c in path)
        if entry <= 0:
            return 0.0, 0.0
        return favorable / entry, adverse / entry

    @staticmethod
    def _hits(
        path: tuple[Candle, ...],
        entry_index: int,
        entry: float,
        direction: Direction,
        target: float | None,
        invalidation: float | None,
    ) -> tuple[bool | None, bool | None, int | None]:
        """
        Whether price traded through the stated target / invalidation, and the
        bar offset to the first hit.

        For an UP prediction a target above entry is hit when a bar's high
        reaches it, an invalidation below entry when a bar's low crosses it;
        DOWN mirrors. ``None`` where no level was stated. ``time_to_outcome``
        is the first bar where *either* level was reached.
        """
        target_hit = None if target is None else False
        inv_hit = None if invalidation is None else False
        first_hit: int | None = None
        for i, c in enumerate(path):
            if direction is Direction.UP:
                if target is not None and not target_hit and c.high >= target:
                    target_hit = True
                if (
                    invalidation is not None
                    and not inv_hit
                    and c.low <= invalidation
                ):
                    inv_hit = True
            elif direction is Direction.DOWN:
                if target is not None and not target_hit and c.low <= target:
                    target_hit = True
                if (
                    invalidation is not None
                    and not inv_hit
                    and c.high >= invalidation
                ):
                    inv_hit = True
            if first_hit is None and (target_hit or inv_hit):
                first_hit = i
        return target_hit, inv_hit, first_hit

    def _unresolvable(self, prediction, reason: str) -> EnrichedOutcome:
        return EnrichedOutcome(
            prediction_id=prediction.prediction_id,
            instrument_key=prediction.instrument_key,
            timeframe=prediction.timeframe,
            direction=prediction.direction,
            status="unresolvable",
            horizon_bars=prediction.horizon_bars,
            is_reliable=False,
            is_mock=prediction.is_mock,
            reason=reason,
        )
