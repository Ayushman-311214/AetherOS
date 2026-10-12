"""
Liquidity pools (spec Phase 6).

A liquidity pool is resting liquidity: a price level where orders are known to
sit, and therefore a level price is drawn toward. ICT reads them at three kinds
of place, and this detector reports all three rather than only the fashionable
one:

- **equal highs / equal lows** -- clusters of confirmed swings at effectively
  the same price. This half is *reused outright* from :class:`SMCService`, which
  already clusters swings within tolerance and reports them as
  ``LiquidityEventKind.EQUAL_HIGHS`` / ``EQUAL_LOWS``; no clustering is
  re-implemented here;
- **session extremes** -- each session's high and low, measured from the session
  windows the time engine already built;
- **prior-day extremes** -- the completed day's high and low, from the same
  local-day buckets the daily bias reads.

``direction`` names the *side the liquidity rests on*, following ICT's standard
vocabulary: UP means buy-side liquidity resting above a high (the stops of
shorts), DOWN means sell-side resting below a low. This is a location, not a
forecast -- and it is deliberately the opposite sense from
``LiquidityEvent.direction``, which describes the reaction to a pool *being
taken*. Both are stated on the object so neither can be misread.

``taken`` is a measurement: price has since traded through the level. A pool
that has not been taken is still resting.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.enums import Confidence, Direction, LiquidityEventKind, LiquidityPoolKind
from ..domain.ict import LiquidityPool, SessionWindow
from ..domain.market_data import Candle
from ..domain.smc import LiquidityEvent
from .sessions import DayBucket, SessionCatalogue

#: LiquidityEvent kinds reused from the SMC layer, mapped to the side the
#: liquidity rests on: equal highs hold buy-side liquidity above them, equal
#: lows sell-side below.
_EQUAL_KINDS = {
    LiquidityEventKind.EQUAL_HIGHS: (LiquidityPoolKind.EQUAL_HIGHS, Direction.UP),
    LiquidityEventKind.EQUAL_LOWS: (LiquidityPoolKind.EQUAL_LOWS, Direction.DOWN),
}


def _extreme_index(
    candles: Sequence[Candle], first: int, last: int, *, high: bool
) -> int:
    """The index of the highest (or lowest) bar within ``[first, last]``."""
    best = first
    for index in range(first, last + 1):
        bar = candles[index]
        if high:
            if bar.high > candles[best].high:
                best = index
        elif bar.low < candles[best].low:
            best = index
    return best


def _resolve_taken(
    candles: Sequence[Candle], index: int, level: float, *, above: bool
) -> int | None:
    """
    The first bar after ``index`` that traded through ``level``, or None.

    Strict inequality, so a bar that *forms* the level at its own extreme does
    not count as having taken it.
    """
    for position in range(index + 1, len(candles)):
        bar = candles[position]
        if (bar.high > level) if above else (bar.low < level):
            return position
    return None


def detect_liquidity_pools(
    liquidity: Sequence[LiquidityEvent],
    session_windows: Sequence[SessionWindow],
    buckets: Sequence[DayBucket],
    candles: Sequence[Candle],
    *,
    timeframe: str,
    catalogue: SessionCatalogue | None = None,
) -> tuple[LiquidityPool, ...]:
    """Every resting or taken liquidity pool visible in this window."""
    pools: list[LiquidityPool] = []

    def add(
        *,
        kind: LiquidityPoolKind,
        direction: Direction,
        level: float,
        index: int,
        evidence: list[str],
        confidence: Confidence = Confidence.MEDIUM,
    ) -> None:
        taken_index = _resolve_taken(
            candles, index, level, above=direction is Direction.UP
        )
        session = (
            catalogue.session_for(candles[index].timestamp)
            if catalogue is not None
            else None
        )
        pool_evidence = list(evidence)
        if taken_index is not None:
            pool_evidence.append(
                f"Price has since traded through it at bar {taken_index}."
            )
        pools.append(
            LiquidityPool(
                kind=kind,
                direction=direction,
                level=level,
                index=index,
                timestamp=candles[index].timestamp,
                timeframe=timeframe,
                taken=taken_index is not None,
                taken_index=taken_index,
                session=session.name if session else None,
                confidence=confidence,
                evidence=tuple(pool_evidence),
            )
        )

    # 1. Equal highs/lows, reused from the SMC read.
    for event in liquidity:
        mapped = _EQUAL_KINDS.get(event.kind)
        if mapped is None:
            continue
        kind, direction = mapped
        add(
            kind=kind,
            direction=direction,
            level=event.level,
            index=event.index,
            evidence=[
                f"{event.kind.value} clustered at {event.level:.4f}.",
                *event.evidence,
            ],
            confidence=event.confidence,
        )

    # 2. Session extremes.
    session_sides = (
        (True, LiquidityPoolKind.SESSION_HIGH),
        (False, LiquidityPoolKind.SESSION_LOW),
    )
    for window in session_windows:
        for high, side in session_sides:
            index = _extreme_index(
                candles, window.first_index, window.last_index, high=high
            )
            level = window.high if high else window.low
            add(
                kind=side,
                direction=Direction.UP if high else Direction.DOWN,
                level=level,
                index=index,
                evidence=[
                    f"The {window.session.value} session "
                    f"({'high' if high else 'low'}) is {level:.4f}.",
                ],
                confidence=Confidence.MEDIUM,
            )

    # 3. Prior-day extremes -- the completed day, as the bias reads it.
    day_sides = (
        (True, LiquidityPoolKind.PRIOR_DAY_HIGH),
        (False, LiquidityPoolKind.PRIOR_DAY_LOW),
    )
    if len(buckets) >= 2:
        prior = buckets[-2]
        for high, side in day_sides:
            index = _extreme_index(
                candles, prior.first_index, prior.last_index, high=high
            )
            level = prior.high if high else prior.low
            add(
                kind=side,
                direction=Direction.UP if high else Direction.DOWN,
                level=level,
                index=index,
                evidence=[
                    f"The prior day ({prior.local_date.isoformat()}) "
                    f"{'high' if high else 'low'} is {level:.4f}.",
                ],
                confidence=Confidence.HIGH,
            )

    return tuple(pools)
