"""
Judas swing (spec Phase 6).

The Judas swing is the false move a session opens with: price runs one way,
takes out a level it was always going to reach, and then reverses. It is the
manipulation leg of the session -- the move that traps the traders who chased
it -- and it is defined by two things this detector measures rather than
assumes:

1. **A named level was taken.** The opening window's extreme must exceed the
   *prior session's* high or low. Taking an arbitrary level is not a Judas
   swing; taking the previous session's liquidity is.
2. **The reversal is confirmed.** The session must close back on the other side
   of its own open. Until that close exists, the move is just a move.

``direction`` is the direction of the **reversal**, which is what the pattern is
traded for. A session that opens, sweeps the prior high and closes below its
open is a bearish Judas swing however bullish the sweep looked.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

from ..domain.enums import Confidence, Direction
from ..domain.ict import JudasSwing, SessionWindow
from ..domain.market_data import Candle

#: ICT's Judas swing is an opening-window phenomenon; an hour covers the
#: London and New York opens, and is configurable for other markets.
DEFAULT_OPENING_WINDOW_MINUTES = 60


def detect_judas_swings(
    session_windows: Sequence[SessionWindow],
    candles: Sequence[Candle],
    *,
    timeframe: str,
    opening_window_minutes: int = DEFAULT_OPENING_WINDOW_MINUTES,
) -> tuple[tuple[JudasSwing, ...], tuple[str, ...]]:
    """
    Every confirmed Judas swing, chronology-respecting.

    A session is only judged against the session that preceded it, so the first
    session in the data is skipped with a limitation -- there is nothing for it
    to have swept.
    """
    if opening_window_minutes <= 0:
        raise ValueError("opening_window_minutes must be positive.")

    swings: list[JudasSwing] = []
    limitations: list[str] = []

    if len(session_windows) < 2:
        limitations.append(
            "Fewer than two sessions in this window; a Judas swing needs a "
            "prior session to take liquidity from."
        )
        return (), tuple(limitations)

    opening = timedelta(minutes=opening_window_minutes)

    for previous, window in zip(session_windows, session_windows[1:], strict=False):
        opening_indices = [
            index
            for index in range(window.first_index, window.last_index + 1)
            if candles[index].timestamp < window.start_at + opening
        ]
        if not opening_indices:
            continue

        high_index = max(opening_indices, key=lambda i: candles[i].high)
        low_index = min(opening_indices, key=lambda i: candles[i].low)

        swept_level: float | None = None
        sweep_extreme = 0.0
        sweep_index = 0
        direction = Direction.UNKNOWN

        if candles[high_index].high > previous.high:
            swept_level = previous.high
            sweep_extreme = candles[high_index].high
            sweep_index = high_index
            direction = Direction.DOWN  # liquidity taken above, reversal down
        elif candles[low_index].low < previous.low:
            swept_level = previous.low
            sweep_extreme = candles[low_index].low
            sweep_index = low_index
            direction = Direction.UP  # liquidity taken below, reversal up

        if swept_level is None:
            continue

        # The reversal must be confirmed by the session closing against the
        # direction the opening move went.
        reversed_ = (
            window.close < window.open
            if direction is Direction.DOWN
            else window.close > window.open
        )
        if not reversed_:
            continue

        side = "high" if direction is Direction.DOWN else "low"
        swings.append(
            JudasSwing(
                session=window.session,
                direction=direction,
                swept_level=swept_level,
                sweep_extreme=sweep_extreme,
                sweep_index=sweep_index,
                session_open=window.open,
                reversal_price=window.close,
                reversal_index=window.last_index,
                timestamp=candles[window.last_index].timestamp,
                timeframe=timeframe,
                confidence=Confidence.HIGH,
                evidence=(
                    f"The {window.session.value} opening "
                    f"({opening_window_minutes} min) took the prior session's "
                    f"{side} at {swept_level:.4f}, reaching {sweep_extreme:.4f}.",
                    f"The session then closed at {window.close:.4f} against its "
                    f"open of {window.open:.4f}, confirming the reversal.",
                ),
            )
        )

    return tuple(swings), tuple(limitations)
