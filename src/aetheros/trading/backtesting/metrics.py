"""
Performance metrics for the backtesting engine (spec Phase 13 metrics).

The spec names five metrics: **Win Rate, Profit Factor, Sharpe Ratio, Max
Drawdown, Expectancy**. They are computed here, once, as pure functions over a
sequence of *signed per-trade returns*, and everything else in the engine --
:class:`~aetheros.trading.services.backtest_service.BacktestService`, the
walk-forward report, the comparison -- reads them from this module rather than
re-deriving them. Two definitions live here that would otherwise be duplicated
and could then drift apart:

- **what a trade earned** (:func:`directional_returns`): a long call earns the
  realised forward return, a short call earns its negation, and a call that
  never traded earns nothing because it is absent, not zero.
- **what "undefined" means** (:func:`trade_statistics`): every ratio is ``None``
  when it cannot be computed rather than a convenient zero or an ``inf``.

The two curve statistics are deliberately *not* per-trade ratios and are
documented as such: the Sharpe here is a per-trade mean over standard deviation,
not an annualised figure, and the drawdown is measured on the additive equity
curve of the returned trades. Both say what they are so neither is read as
something it is not.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from ..domain.backtest import TradeOutcome, TradeStatistics
from ..domain.enums import Direction

#: Decimal places for ratios (win rate, profit factor, Sharpe).
_RATIO_PLACES = 6

#: Tolerance under which a returns sample's variance is treated as exactly
#: zero dispersion. Squared-difference summation over a constant series leaves
#: a residue of order machine-epsilon (1e-33 and below for typical return
#: magnitudes); a real per-trade spread is many orders larger, so this floor
#: separates "flat" from "tiny but genuine" without ever rejecting the latter.
_VARIANCE_EPS = 1e-24

#: Decimal places for return figures (sums, averages, drawdown).
_RETURN_PLACES = 8


def directional_returns(outcomes: Iterable[TradeOutcome]) -> list[float]:
    """
    Signed per-trade returns for the directional calls among ``outcomes``.

    A long call earns the realised forward return; a short call earns its
    negation. A non-directional call never traded, so it is *skipped* rather
    than counted as a zero-return trade -- an absent call is not a breakeven,
    and counting it as one would quietly deflate the win rate and dilute the
    expectancy of every backtest that mostly declines to trade.
    """
    returns: list[float] = []
    for outcome in outcomes:
        if outcome.predicted is Direction.UP:
            returns.append(outcome.forward_return)
        elif outcome.predicted is Direction.DOWN:
            returns.append(-outcome.forward_return)
    return returns


def max_drawdown(returns: Sequence[float]) -> float:
    """
    Largest peak-to-trough drop on the additive equity curve (>= 0).

    Path-dependent by nature: it is the worst the running sum ever fell below
    its own high-water mark, so it must be measured on a continuous sequence of
    trades rather than averaged from shorter runs.
    """
    equity = 0.0
    peak = 0.0
    worst = 0.0
    for r in returns:
        equity += r
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return round(-worst, _RETURN_PLACES)


def sharpe_ratio(returns: Sequence[float]) -> float | None:
    """
    Per-trade mean over standard deviation. **Not annualised.**

    None for fewer than two trades (a single trade has no dispersion) and for a
    sample with no dispersion at all -- a ratio with a zero denominator is
    undefined, and reporting a large number there would read as a triumph.
    """
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    std = variance**0.5
    # A constant series leaves a residue of order machine-epsilon after the
    # squared-difference sum, not an exact zero -- so "no dispersion" is a
    # tolerance, not an equality. Guarding on the variance keeps a genuinely
    # tiny-but-real spread computable while a flat series still reads as
    # undefined rather than an astronomically large ratio.
    if math.isclose(variance, 0.0, abs_tol=_VARIANCE_EPS):
        return None
    return round(mean / std, _RATIO_PLACES)


def trade_statistics(returns: Sequence[float]) -> TradeStatistics:
    """
    The full metric record for one set of signed trade returns.

    Profitable trades are wins, losing trades are losses, and the exactly-flat
    ones are breakevens -- a distinction no other metric makes, and the reason a
    win rate is not the same number as a directional hit rate.

    An empty sample yields an all-``None`` record rather than a zeroed one: "no
    trades were taken" and "trades were taken and made nothing" are different
    findings and must not be reported identically.
    """
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    breakevens = len(returns) - len(wins) - len(losses)
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    return TradeStatistics(
        trades=len(returns),
        wins=len(wins),
        losses=len(losses),
        breakevens=breakevens,
        win_rate=(
            round(len(wins) / len(returns), _RATIO_PLACES) if len(returns) else None
        ),
        gross_profit=round(gross_profit, _RETURN_PLACES),
        gross_loss=round(gross_loss, _RETURN_PLACES),
        # No losing trade means no finite profit factor. The number everyone
        # wants here is "infinite", which is not a measurement.
        profit_factor=(
            round(gross_profit / gross_loss, _RATIO_PLACES) if gross_loss > 0 else None
        ),
        average_win=(
            round(gross_profit / len(wins), _RETURN_PLACES) if wins else None
        ),
        average_loss=(
            round(sum(losses) / len(losses), _RETURN_PLACES) if losses else None
        ),
        # Expectancy is the mean signed return: the average amount one trade of
        # this strategy made, which is what "expectancy" means when the sizes
        # are equal. Position sizing belongs to the risk engine, not here.
        expectancy=(
            round(sum(returns) / len(returns), _RETURN_PLACES) if returns else None
        ),
        cumulative_return=(round(sum(returns), _RETURN_PLACES) if returns else None),
        max_drawdown=max_drawdown(returns) if returns else None,
        sharpe=sharpe_ratio(returns),
    )
