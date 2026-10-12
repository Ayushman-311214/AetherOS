"""
Where a setup is wrong (spec Phase 7).

A strategy says *which side* and *why*; this module answers the one remaining
geometric question it is allowed to answer: the level at which the thesis is
void. That is deliberately the only price a setup carries. Entry, stop, target,
size and the risk/reward ratio are :class:`RiskService`'s deterministic output
from the same analysis, and a strategy that computed them itself would be a
second risk engine quietly disagreeing with the first.

Structure is preferred to volatility, because a structural level is a fact about
this market's price action while an ATR band is a statement about typical
movement. The fallback exists so a setup is not lost merely because the swing
detector has not confirmed a pivot yet -- but it is always reported as what it
is, an ATR-derived level rather than a structural one, through
:func:`invalidation_source`.

Returns None rather than a guess. A strategy with no defensible invalidation
level has no setup, and saying so is the honest outcome (CLAUDE.md section 28).
"""

from __future__ import annotations

from ..domain.enums import Direction
from .context import StrategyContext

#: Source label for a level taken from a confirmed swing point.
STRUCTURAL = "structural"
#: Source label for a level taken from an ATR band, i.e. not a market level.
VOLATILITY = "volatility"


def nearest_swing_level(
    context: StrategyContext, direction: Direction
) -> float | None:
    """
    The closest confirmed swing on the side that would invalidate the thesis.

    For a bullish setup that is the highest confirmed swing *low* below the
    current price -- the nearest structural support whose failure means the leg
    justifying the trade is gone. Bearish is the mirror image. None means
    structure has confirmed no swing on that side, which is a real answer rather
    than a zero.
    """
    entry = context.last_price
    swings = context.analysis.structure.swings
    if direction is Direction.UP:
        below = [s.price for s in swings if s.kind == "low" and s.price < entry]
        return max(below) if below else None
    if direction is Direction.DOWN:
        above = [s.price for s in swings if s.kind == "high" and s.price > entry]
        return min(above) if above else None
    return None


def atr_level(
    context: StrategyContext, direction: Direction, *, multiple: float
) -> float | None:
    """
    A volatility band ``multiple`` ATRs behind the entry, or None without an ATR.

    This is not a market level and is never presented as one; it is the honest
    fallback for a setup whose structural reference has not been confirmed yet.
    """
    if multiple <= 0:
        raise ValueError("An ATR multiple must be positive.")
    atr = context.atr
    if atr is None or atr <= 0:
        return None
    entry = context.last_price
    if direction is Direction.UP:
        return entry - multiple * atr
    if direction is Direction.DOWN:
        return entry + multiple * atr
    return None


def structural_invalidation(
    context: StrategyContext, direction: Direction, *, atr_multiple: float
) -> float | None:
    """
    The invalidation level for a setup: the nearest structure, else an ATR band.

    Always on the correct side of the current price, so a caller can pass the
    result straight to :class:`StrategySetup` without a second side check.
    """
    level = nearest_swing_level(context, direction)
    if level is None:
        level = atr_level(context, direction, multiple=atr_multiple)
    if level is None or level <= 0:
        return None
    return round(level, 8)


def invalidation_source(context: StrategyContext, direction: Direction) -> str:
    """
    Which source an invalidation level for ``direction`` would come from here.

    Call this alongside :func:`structural_invalidation` when the level needs to
    be *described*: a volatility band presented as a structural level would
    misrepresent a statement about typical movement as a fact about this market.
    """
    return (
        STRUCTURAL
        if nearest_swing_level(context, direction) is not None
        else VOLATILITY
    )
