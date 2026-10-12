"""
Session models (spec Phase 6).

Where the other detectors describe one window in isolation, this one describes
the **relationship between consecutive sessions** -- the recurring shapes ICT
names, such as London sweeping the Asian range and reversing, or New York
continuing London's move.

Every label is earned by a measurement against the previous session: a level
actually taken, a range actually larger or smaller, a close actually on the far
side. The precedence is fixed and ordered, so the same data always yields the
same label:

1. a level of the previous session taken and then given back -> SWEEP_AND_REVERSE;
2. a range materially smaller than the previous session -> CONSOLIDATION;
3. a range materially larger -> EXPANSION;
4. a close against the previous session's direction -> REVERSAL;
5. otherwise -> CONTINUATION.

A session with no predecessor, or with no range on either side of the
comparison, is **UNDEFINED** -- never forced into a pattern.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.enums import Confidence, Direction, SessionModelKind
from ..domain.ict import SessionModel, SessionWindow

#: A session ranging at most this share of its predecessor is consolidating.
CONSOLIDATION_RANGE_SHARE = 0.6

#: A session ranging at least this multiple of its predecessor has expanded.
EXPANSION_RANGE_MULTIPLE = 1.5


def _close_direction(window: SessionWindow) -> Direction:
    if window.close > window.open:
        return Direction.UP
    if window.close < window.open:
        return Direction.DOWN
    return Direction.SIDEWAYS


def _sweep_and_reverse(
    window: SessionWindow, previous: SessionWindow
) -> tuple[float | None, Direction]:
    """
    A previous-session level taken and then handed back, if that happened.

    Returns the level and the direction of the reversal; ``(None, UNKNOWN)``
    when no level was taken or the session did not give it back. Taking a level
    without reversing is expansion, and belongs to a different label.
    """
    if window.high > previous.high and window.close < previous.high:
        return previous.high, Direction.DOWN
    if window.low < previous.low and window.close > previous.low:
        return previous.low, Direction.UP
    return None, Direction.UNKNOWN


def detect_session_models(
    session_windows: Sequence[SessionWindow],
    *,
    timeframe: str,
) -> tuple[tuple[SessionModel, ...], tuple[str, ...]]:
    """One model per session after the first, describing it against its predecessor."""
    models: list[SessionModel] = []
    limitations: list[str] = []

    if len(session_windows) < 2:
        limitations.append(
            "Fewer than two sessions in this window; there is no session-to-"
            "session relationship to model."
        )
        return (), tuple(limitations)

    for previous, window in zip(session_windows, session_windows[1:], strict=False):
        level_taken, sweep_direction = _sweep_and_reverse(window, previous)
        previous_close = _close_direction(previous)
        window_close = _close_direction(window)

        if previous.range <= 0 or window.range <= 0:
            kind = SessionModelKind.UNDEFINED
            direction = Direction.UNKNOWN
            evidence = ["One of the two sessions has no range to compare."]
            confidence = Confidence.LOW
        elif level_taken is not None:
            kind = SessionModelKind.SWEEP_AND_REVERSE
            direction = sweep_direction
            evidence = [
                f"{window.session.value} took {previous.session.value}'s "
                f"{'high' if sweep_direction is Direction.DOWN else 'low'} at "
                f"{level_taken:.4f} and closed back inside.",
                f"It closed {window.close:.4f} against a "
                f"{previous.session.value} range of "
                f"{previous.low:.4f}-{previous.high:.4f}.",
            ]
            confidence = Confidence.HIGH
        elif window.range <= previous.range * CONSOLIDATION_RANGE_SHARE:
            kind = SessionModelKind.CONSOLIDATION
            direction = window_close
            evidence = [
                f"{window.session.value} ranged {window.range:.4f}, "
                f"{window.range / previous.range:.1%} of "
                f"{previous.session.value}'s {previous.range:.4f}.",
            ]
            confidence = Confidence.MEDIUM
        elif window.range >= previous.range * EXPANSION_RANGE_MULTIPLE:
            kind = SessionModelKind.EXPANSION
            direction = window_close
            evidence = [
                f"{window.session.value} ranged {window.range:.4f}, "
                f"{window.range / previous.range:.1%} of "
                f"{previous.session.value}'s {previous.range:.4f}.",
            ]
            confidence = Confidence.MEDIUM
        elif (
            window_close is not previous_close
            and window_close is not Direction.SIDEWAYS
            and previous_close is not Direction.SIDEWAYS
        ):
            kind = SessionModelKind.REVERSAL
            direction = window_close
            evidence = [
                f"{previous.session.value} closed {previous_close.value} and "
                f"{window.session.value} closed {direction.value}.",
            ]
            confidence = Confidence.MEDIUM
        else:
            kind = SessionModelKind.CONTINUATION
            direction = window_close
            evidence = [
                f"{window.session.value} closed {direction.value}, the same "
                f"direction as {previous.session.value}.",
            ]
            confidence = Confidence.MEDIUM

        models.append(
            SessionModel(
                session=window.session,
                previous_session=previous.session,
                kind=kind,
                direction=direction,
                level_taken=level_taken,
                timestamp=window.end_at,
                timeframe=timeframe,
                confidence=confidence,
                evidence=tuple(evidence),
            )
        )

    return tuple(models), tuple(limitations)
