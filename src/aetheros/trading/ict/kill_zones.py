"""
Kill zones (spec Phase 6).

A kill zone is the narrow window in which ICT expects a session's directional
move to originate. Detecting one is only half the job: the useful question is
whether the move *actually* happened there, so each window is measured rather
than merely labelled --

- ``range_share``: the zone's range as a fraction of its session's whole range,
  which is what "the move originated in the kill zone" means numerically;
- ``swept_level``: the prior session's extreme the zone took out, when it took
  one. A kill zone that opens by taking the previous session's high or low is
  doing the thing kill zones are named for.

A kill zone with no bars inside it is **absent**, not an empty window: it is
skipped and a limitation is returned, so nothing is fabricated to fill the gap.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from ..domain.enums import Confidence, Direction, KillZoneName
from ..domain.ict import KillZoneWindow, SessionWindow
from ..domain.market_data import Candle
from .sessions import SessionCatalogue


def _preceding_session(
    windows: Sequence[SessionWindow], start_at: datetime
) -> SessionWindow | None:
    """The last session window that closed at or before ``start_at``."""
    preceding = [window for window in windows if window.end_at <= start_at]
    return max(preceding, key=lambda window: window.end_at, default=None)


def _containing_session(
    windows: Sequence[SessionWindow], session_name, start_at: datetime
) -> SessionWindow | None:
    """
    The window of the zone's own session that contains ``start_at``.

    Half-open containment (``start_at < window.end_at``), matching the session
    layer's documented convention that a bar stamped *t* covers [*t*, *t* +
    interval). The inclusive form would attribute a bar opening exactly at a
    window's close to the *previous* session -- on daily bars that pairs a
    kill-zone with a different day's session window and can yield a range
    share above 1, which is exactly the artifact this guard exists to prevent.
    """
    for window in windows:
        if (
            window.session is session_name
            and window.start_at <= start_at < window.end_at
        ):
            return window
    return None


def detect_kill_zones(
    candles: Sequence[Candle],
    session_windows: Sequence[SessionWindow],
    *,
    interval: timedelta,
    timeframe: str,
    catalogue: SessionCatalogue,
) -> tuple[tuple[KillZoneWindow, ...], tuple[str, ...]]:
    """
    Every kill-zone occurrence present in the data, with what price did in it.

    Returns ``(windows, limitations)``; a zone whose session window is missing
    (or has no range to measure against) is reported as a limitation rather than
    being given an invented ``range_share``.
    """
    windows: list[KillZoneWindow] = []
    limitations: list[str] = []
    empty: list[KillZoneName] = []

    for zone in catalogue.kill_zones:
        groups = catalogue.occurrence_groups(candles, zone)
        if not groups:
            empty.append(zone.name)
            continue

        for indices in groups:
            bars = [candles[index] for index in indices]
            start_at = bars[0].timestamp
            high = max(bar.high for bar in bars)
            low = min(bar.low for bar in bars)

            session = _containing_session(session_windows, zone.session, start_at)
            if session is None or session.range <= 0:
                limitations.append(
                    f"The {zone.label or zone.name.value} occurrence at "
                    f"{start_at.isoformat()} has no session range to measure "
                    f"against; it is reported without a range share."
                )
                continue

            range_share = (high - low) / session.range

            swept_level: float | None = None
            swept_direction: Direction | None = None
            prior = _preceding_session(session_windows, start_at)
            if prior is not None:
                if high > prior.high:
                    swept_level, swept_direction = prior.high, Direction.UP
                elif low < prior.low:
                    swept_level, swept_direction = prior.low, Direction.DOWN

            evidence = [
                f"{zone.label or zone.name.value} ran {low:.4f}-{high:.4f} "
                f"({len(bars)} bars), {range_share:.1%} of the "
                f"{zone.session.value} session's range.",
            ]
            if swept_level is not None:
                side = "high" if swept_direction is Direction.UP else "low"
                evidence.append(
                    f"It took the prior session's {side} at {swept_level:.4f}."
                )

            windows.append(
                KillZoneWindow(
                    name=zone.name,
                    session=zone.session,
                    start_at=start_at,
                    end_at=bars[-1].timestamp + interval,
                    open=bars[0].open,
                    high=high,
                    low=low,
                    close=bars[-1].close,
                    candle_count=len(bars),
                    range_share=range_share,
                    timeframe=timeframe,
                    first_index=indices[0],
                    last_index=indices[-1],
                    swept_level=swept_level,
                    swept_direction=swept_direction,
                    confidence=(
                        Confidence.HIGH
                        if swept_level is not None
                        else Confidence.MEDIUM
                    ),
                    evidence=tuple(evidence),
                )
            )

    if empty:
        limitations.append(
            "No bars fell inside these kill zones in this window, so they are "
            f"absent rather than empty: {', '.join(z.value for z in empty)}."
        )

    windows.sort(key=lambda window: window.start_at)
    return tuple(windows), tuple(limitations)
