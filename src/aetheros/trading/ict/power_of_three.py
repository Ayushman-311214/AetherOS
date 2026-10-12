"""
Power of Three (spec Phase 6).

ICT's Power of Three -- accumulation, manipulation, distribution -- is the claim
that a session moves in three acts: it builds a position quietly, runs a false
move to take the other side's liquidity, then expands in the real direction into
the close. This detector decomposes a session into its three time thirds and
then *measures* each act rather than assuming it:

- **accumulation** is the opening third, and it qualifies as accumulation only
  if its range is a small share of the session's -- a quiet open, not just an
  early one;
- **manipulation** is the middle third, and it qualifies only if it carries an
  extreme on the **opposite** side to the direction the session ultimately
  closed -- the false move, identified by which side it took;
- **distribution** is the closing third, and it should carry the expansion: its
  range share must be at least the accumulation third's.

A session that does not show that shape is **not reported**. Returned shares
make the shape checkable; they are not decorative.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

from ..domain.enums import AMDPhase, Confidence, Direction
from ..domain.ict import AMDPhaseWindow, PowerOfThree, SessionWindow
from ..domain.market_data import Candle

#: The opening third must be at most this share of the session's range to count
#: as accumulation rather than simply "the first part of the day".
DEFAULT_ACCUMULATION_MAX_SHARE = 0.35


def _phase_window(
    phase: AMDPhase,
    candles: Sequence[Candle],
    indices: Sequence[int],
    interval: timedelta,
    session_range: float,
) -> AMDPhaseWindow:
    bars = [candles[index] for index in indices]
    high = max(bar.high for bar in bars)
    low = min(bar.low for bar in bars)
    return AMDPhaseWindow(
        phase=phase,
        start_at=bars[0].timestamp,
        end_at=bars[-1].timestamp + interval,
        open=bars[0].open,
        high=high,
        low=low,
        close=bars[-1].close,
        candle_count=len(bars),
        range_share=(high - low) / session_range,
    )


def _manipulation_side(
    accumulation: AMDPhaseWindow, manipulation: AMDPhaseWindow
) -> Direction:
    """
    Which side the middle third ran, read from what it took out.

    Below the accumulation low is sell-side taken (a move DOWN); above its high
    is buy-side taken (a move UP). When it takes both, the larger excursion is
    the one that matters; when it takes neither, the side is UNDEFINED rather
    than guessed.
    """
    below = accumulation.low - manipulation.low
    above = manipulation.high - accumulation.high
    if below > 0 and above > 0:
        return Direction.DOWN if below >= above else Direction.UP
    if below > 0:
        return Direction.DOWN
    if above > 0:
        return Direction.UP
    return Direction.UNKNOWN


def _opposite(direction: Direction) -> Direction:
    """The side a false move must run if the session is to close ``direction``."""
    if direction is Direction.UP:
        return Direction.DOWN
    if direction is Direction.DOWN:
        return Direction.UP
    return Direction.UNKNOWN


def detect_power_of_three(
    session_windows: Sequence[SessionWindow],
    candles: Sequence[Candle],
    *,
    interval: timedelta,
    timeframe: str,
    accumulation_max_share: float = DEFAULT_ACCUMULATION_MAX_SHARE,
) -> tuple[tuple[PowerOfThree, ...], tuple[str, ...]]:
    """
    Every session that shows a measurable accumulation/manipulation/distribution
    shape, with its three phases.
    """
    if not 0.0 < accumulation_max_share < 1.0:
        raise ValueError("accumulation_max_share must lie strictly within 0 and 1.")

    results: list[PowerOfThree] = []
    limitations: list[str] = []

    for window in session_windows:
        if window.range <= 0:
            limitations.append(
                f"The {window.session.value} session at "
                f"{window.start_at.isoformat()} has no range; it cannot be "
                f"decomposed into three phases."
            )
            continue

        span = window.end_at - window.start_at
        first_cut = window.start_at + span / 3
        second_cut = window.start_at + span * 2 / 3

        groups: list[list[int]] = [[], [], []]
        for index in range(window.first_index, window.last_index + 1):
            timestamp = candles[index].timestamp
            if timestamp < first_cut:
                groups[0].append(index)
            elif timestamp < second_cut:
                groups[1].append(index)
            else:
                groups[2].append(index)

        if not all(groups):
            limitations.append(
                f"The {window.session.value} session at "
                f"{window.start_at.isoformat()} has too few bars to split into "
                f"three non-empty phases."
            )
            continue

        phases = tuple(
            _phase_window(phase, candles, indices, interval, window.range)
            for phase, indices in zip(
                (AMDPhase.ACCUMULATION, AMDPhase.MANIPULATION, AMDPhase.DISTRIBUTION),
                groups,
                strict=False,
            )
        )
        accumulation, manipulation, distribution = phases

        if accumulation.range_share > accumulation_max_share:
            continue

        if window.close > window.open:
            direction = Direction.UP
        elif window.close < window.open:
            direction = Direction.DOWN
        else:
            direction = Direction.SIDEWAYS

        side = _manipulation_side(accumulation, manipulation)
        # The false move must be on the opposite side to the realised direction.
        if direction is Direction.SIDEWAYS or side is not _opposite(direction):
            continue
        if distribution.range_share < accumulation.range_share:
            continue

        results.append(
            PowerOfThree(
                session=window.session,
                start_at=window.start_at,
                end_at=window.end_at,
                direction=direction,
                manipulation_side=side,
                phases=phases,
                session_open=window.open,
                session_close=window.close,
                timeframe=timeframe,
                confidence=(
                    Confidence.HIGH
                    if distribution.range_share >= 0.5
                    else Confidence.MEDIUM
                ),
                evidence=(
                    f"Accumulation held {accumulation.range_share:.1%} of the "
                    f"session range over {accumulation.candle_count} bars.",
                    f"Manipulation ran {side.value}, taking "
                    f"{'the low' if side is Direction.DOWN else 'the high'} beyond "
                    f"the accumulation range.",
                    f"Distribution carried {distribution.range_share:.1%} of the "
                    f"range and the session closed {direction.value}.",
                ),
            )
        )

    if session_windows and not results:
        limitations.append(
            "No session showed a measurable accumulation/manipulation/"
            "distribution shape; none is reported rather than forcing one."
        )

    return tuple(results), tuple(limitations)
