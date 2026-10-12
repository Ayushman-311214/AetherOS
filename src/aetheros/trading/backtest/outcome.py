"""
Enriched prediction outcomes (Phase 6).

The :class:`PredictionOutcome` the existing evaluator produces measures the
*endpoint* of a prediction's horizon -- entry price, exit price, realised
return, hit/miss. Phase 6 asks for the *path*: how far the move ran against
the prediction before it resolved (max adverse excursion), how far it ran for
it (max favorable excursion), whether the stated target or invalidation was
reached along the way, and how long it took. :class:`EnrichedOutcome` carries
exactly those fields.

Everything is measured, never inferred: the excursions are the realised
high/low extremes over the path, the hit flags are whether price *traded
through* the stated levels, and ``time_to_outcome`` is the bar count to the
first hit (or the horizon when nothing hit). A prediction with no target or
invalidation keeps the honest ``None``/``False`` rather than a fabricated
answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..domain.enums import Direction


@dataclass(frozen=True, slots=True)
class EnrichedOutcome:
    """
    A prediction's outcome with the realised path measured, not just the end.

    ``prediction_id`` links back to the recorded call; ``direction`` is the
    predicted side; ``entry_price``/``exit_price`` are the bar closes bounding
    the measured window. Excursions are measured relative to ``entry_price``,
    signed so *favorable* is positive and *adverse* negative in the predicted
    direction.
    """

    prediction_id: str
    instrument_key: str
    timeframe: str
    direction: Direction
    status: str                     # "resolved" | "pending" | "unresolvable"

    entry_price: float | None = None
    exit_price: float | None = None
    entry_timestamp: datetime | None = None
    outcome_timestamp: datetime | None = None

    realized_return: float | None = None
    realized_direction: Direction | None = None
    is_correct: bool | None = None
    horizon_bars: int = 0
    bars_elapsed: int = 0

    # The path, signed in the predicted direction.
    max_favorable_excursion: float | None = None   # furthest the move ran FOR it
    max_adverse_excursion: float | None = None     # furthest it ran AGAINST it

    # Did the stated levels get reached along the way?
    target_hit: bool | None = None        # None when no target was stated
    invalidation_hit: bool | None = None  # None when no invalidation was stated
    target: float | None = None
    invalidation_price: float | None = None

    # How long to the first hit (bars), or the horizon if nothing hit.
    time_to_outcome: int | None = None

    # Honesty flags.
    is_reliable: bool = False
    is_mock: bool = False
    limitations: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "status": self.status,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_timestamp": (
                self.entry_timestamp.isoformat() if self.entry_timestamp else None
            ),
            "outcome_timestamp": (
                self.outcome_timestamp.isoformat()
                if self.outcome_timestamp
                else None
            ),
            "realized_return": self.realized_return,
            "realized_direction": (
                self.realized_direction.value
                if self.realized_direction is not None
                else None
            ),
            "is_correct": self.is_correct,
            "horizon_bars": self.horizon_bars,
            "bars_elapsed": self.bars_elapsed,
            "max_favorable_excursion": self.max_favorable_excursion,
            "max_adverse_excursion": self.max_adverse_excursion,
            "target_hit": self.target_hit,
            "invalidation_hit": self.invalidation_hit,
            "target": self.target,
            "invalidation_price": self.invalidation_price,
            "time_to_outcome": self.time_to_outcome,
            "is_reliable": self.is_reliable,
            "is_mock": self.is_mock,
            "limitations": list(self.limitations),
            "reason": self.reason,
        }
