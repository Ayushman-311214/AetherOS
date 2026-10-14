"""
Exit rules and transaction costs for a replayed session (spec Phase 14).

Both functions here are pure: a position and a bar in, a decision out. That is
deliberate -- the exit rule is the part of a simulation most likely to be
quietly tuned until the result looks good, so it is kept to a fixed, testable
rule set with the uncomfortable cases resolved *against* the strategy.

The rules, in full:

- A position is tested against each bar's high and low from the bar **after**
  the one that opened it. A stop that a bar's own range also contains would
  otherwise close the position on the very bar that created it, which is not a
  trade anyone could have taken.
- If one bar's range contains both the stop and the target, the true order of
  events inside that bar is unknowable from daily data. The position closes at
  the **stop** and is labelled ``AMBIGUOUS``: an unorderable bar never gets to
  flatter the result.
- Stops and targets are the signal's own geometry. Nothing here trails a stop,
  scales out or adds to a position -- those are the position manager's
  business, and inventing them here would mean the simulator had an exit
  policy the strategies were never tested against.
"""

from __future__ import annotations

import math

from ..domain.enums import Direction
from ..domain.market_data import Candle
from ..domain.simulation import SimulationExitReason
from ..domain.trade import Position

#: Basis points in a whole unit (1% == 100 bps).
_BPS = 10_000.0


def exit_for(
    position: Position,
    candle: Candle,
) -> tuple[float, SimulationExitReason] | None:
    """
    Whether ``candle`` closes ``position``, and at what price and reason.

    Returns ``None`` when the bar's range touches neither level -- including
    when the position has no stop or no target, which is exactly the "no exit
    rule applies" answer rather than an exit at some invented price.
    """
    is_long = position.direction is Direction.UP
    stop = position.stop_loss
    target = position.take_profit

    # A long is stopped when the low reaches its stop and takes profit when the
    # high reaches its target; a short is the mirror of both.
    stop_hit = stop is not None and (
        candle.low <= stop if is_long else candle.high >= stop
    )
    target_hit = target is not None and (
        candle.high >= target if is_long else candle.low <= target
    )

    if stop_hit and target_hit:
        assert stop is not None
        return stop, SimulationExitReason.AMBIGUOUS
    if stop_hit:
        assert stop is not None
        return stop, SimulationExitReason.STOP
    if target_hit:
        assert target is not None
        return target, SimulationExitReason.TARGET
    return None


def slipped_price(price: float, *, buying: bool, slippage_bps: float) -> float:
    """
    ``price`` moved against the order by ``slippage_bps``.

    Slippage is always adverse: a buyer pays more and a seller receives less.
    Modelling it as symmetric noise around the mid would let a simulation
    profit from its own liquidity assumptions, which is the failure mode §7
    names.
    """
    if not math.isfinite(price) or price <= 0:
        raise ValueError("A fill price must be finite and positive.")
    if not math.isfinite(slippage_bps) or slippage_bps < 0:
        raise ValueError("Slippage cannot be negative.")
    drift = slippage_bps / _BPS
    return price * (1.0 + drift) if buying else price * (1.0 - drift)


def commission_for(notional: float, *, commission_bps: float) -> float:
    """
    The commission on ``notional`` at ``commission_bps``.

    Charged on both legs of a round trip by the caller, because a venue that
    only charged one side would not be a venue.
    """
    if not math.isfinite(notional):
        raise ValueError("A commission needs a finite notional.")
    if not math.isfinite(commission_bps) or commission_bps < 0:
        raise ValueError("Commission cannot be negative.")
    return abs(notional) * commission_bps / _BPS
