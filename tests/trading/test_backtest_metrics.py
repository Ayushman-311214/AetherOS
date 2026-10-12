"""
Known-answer tests for the backtesting metrics (spec Phase 13 metrics).

The spec names five metrics -- Win Rate, Profit Factor, Sharpe Ratio, Max
Drawdown, Expectancy -- and these pin each to an arithmetic answer worked out on
paper. Every test here asserts a *number*, not a shape, because the whole point
of moving the definitions into one module is that the number stops depending on
which caller asked for it.

The two definitions that are easy to get subtly wrong each get their own test:

- a signal that made no call is **absent**, not a zero-return trade, so it
  cannot dilute the win rate (`test_a_non_directional_call_does_not_trade`);
- a directionally *correct* call on a flat move made no money, so it is a
  breakeven rather than a win (`test_a_correct_call_on_a_flat_move_is_a_breakeven`).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.trading.backtesting.metrics import (
    directional_returns,
    max_drawdown,
    sharpe_ratio,
    trade_statistics,
)
from aetheros.trading.domain.backtest import TradeOutcome
from aetheros.trading.domain.enums import Direction

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _outcome(
    predicted: Direction,
    forward_return: float,
    *,
    realized: Direction = Direction.UP,
) -> TradeOutcome:
    return TradeOutcome(
        index=0,
        timestamp=_NOW,
        predicted=predicted,
        entry_price=100.0,
        exit_price=100.0 * (1.0 + forward_return),
        forward_return=forward_return,
        realized=realized,
        correct=predicted is realized,
    )


# ----------------------------------------------------------------------
# what a trade earned
# ----------------------------------------------------------------------


def test_a_long_earns_the_forward_return_and_a_short_earns_its_negation():
    returns = directional_returns(
        [
            _outcome(Direction.UP, 0.04),
            _outcome(Direction.DOWN, 0.04, realized=Direction.DOWN),
        ]
    )
    assert returns == [0.04, -0.04]


def test_a_non_directional_call_does_not_trade():
    # A SIDEWAYS or UNKNOWN call never opened a position, so it earns nothing and
    # is absent from the sample rather than present as a zero.
    returns = directional_returns(
        [
            _outcome(Direction.SIDEWAYS, 0.04),
            _outcome(Direction.UNKNOWN, -0.03),
            _outcome(Direction.UP, 0.02),
        ]
    )
    assert returns == [0.02]


def test_an_empty_signal_yields_no_trades():
    assert directional_returns([]) == []


# ----------------------------------------------------------------------
# win rate, profit factor, expectancy
# ----------------------------------------------------------------------


def test_trade_statistics_matches_the_hand_computed_numbers():
    # 2 wins (0.10, 0.20), 2 losses (-0.05, -0.10), 1 exactly-flat breakeven.
    stats = trade_statistics([0.10, -0.05, 0.0, 0.20, -0.10])

    assert stats.trades == 5
    assert stats.wins == 2
    assert stats.losses == 2
    assert stats.breakevens == 1

    assert stats.win_rate == pytest.approx(0.4)
    assert stats.gross_profit == pytest.approx(0.30)
    assert stats.gross_loss == pytest.approx(0.15)
    assert stats.profit_factor == pytest.approx(2.0)
    assert stats.average_win == pytest.approx(0.15)
    assert stats.average_loss == pytest.approx(-0.075)
    # Expectancy is the mean signed return: 0.15 of profit over 5 trades.
    assert stats.expectancy == pytest.approx(0.03)
    assert stats.cumulative_return == pytest.approx(0.15)


def test_a_correct_call_on_a_flat_move_is_a_breakeven():
    # `correct` is a property of the direction; a win is a property of the money.
    # A flat move makes neither, and counting it as a win would inflate the win
    # rate of any strategy that trades through quiet stretches.
    trade = _outcome(Direction.UP, 0.0, realized=Direction.SIDEWAYS)
    returns = directional_returns([trade])
    stats = trade_statistics(returns)

    assert returns == [0.0]
    assert stats.trades == 1
    assert stats.wins == 0
    assert stats.losses == 0
    assert stats.breakevens == 1
    assert stats.win_rate == pytest.approx(0.0)


def test_no_losing_trade_means_no_finite_profit_factor():
    stats = trade_statistics([0.10, 0.20])
    assert stats.gross_loss == 0.0
    # Not `inf`, and not a made-up large number: the ratio does not exist.
    assert stats.profit_factor is None
    assert stats.win_rate == pytest.approx(1.0)
    assert stats.average_loss is None


def test_an_empty_sample_is_undefined_not_zero():
    # "No trades were taken" and "trades were taken and made nothing" are
    # different findings and must not be reported identically.
    stats = trade_statistics([])

    assert stats.trades == 0
    assert stats.win_rate is None
    assert stats.profit_factor is None
    assert stats.expectancy is None
    assert stats.cumulative_return is None
    assert stats.max_drawdown is None
    assert stats.sharpe is None
    # The two sums are real zeroes -- nothing was won and nothing was lost.
    assert stats.gross_profit == 0.0
    assert stats.gross_loss == 0.0


# ----------------------------------------------------------------------
# the two curve statistics
# ----------------------------------------------------------------------


def test_max_drawdown_is_the_worst_fall_below_the_running_peak():
    # Equity path: 0.10, 0.05, 0.05, 0.25, 0.15. The peak reaches 0.25 at the
    # fourth trade and the fifth gives 0.10 of it back -- the worst excursion.
    assert max_drawdown([0.10, -0.05, 0.0, 0.20, -0.10]) == pytest.approx(0.10)


def test_a_monotonically_rising_curve_has_no_drawdown():
    assert max_drawdown([0.01, 0.02, 0.03]) == 0.0


def test_drawdown_is_path_dependent_not_a_sum():
    # Both orders total +0.10, but spreading the gains out keeps the equity curve
    # close to its peak while banking them early and then giving them back does
    # not. Drawdown is a property of the *path*, which is why the walk-forward
    # report pools its folds in time order instead of averaging per-fold figures.
    clustered = max_drawdown([0.10, 0.10, -0.05, -0.05])
    interleaved = max_drawdown([0.10, -0.05, 0.10, -0.05])
    assert sum([0.10, 0.10, -0.05, -0.05]) == pytest.approx(
        sum([0.10, -0.05, 0.10, -0.05])
    )
    assert clustered == pytest.approx(0.10)
    assert interleaved == pytest.approx(0.05)


def test_sharpe_is_the_per_trade_mean_over_standard_deviation():
    # mean 0.01, population std 0.02 -> 0.5 exactly.
    assert sharpe_ratio([0.03, -0.01]) == pytest.approx(0.5)
    # A symmetric pair has mean zero, so the ratio is exactly zero -- not None.
    assert sharpe_ratio([0.10, -0.10]) == pytest.approx(0.0)


def test_sharpe_is_undefined_without_dispersion():
    # One trade has no spread to divide by; a constant series has a zero
    # denominator. Both are undefined, and neither is "very good".
    assert sharpe_ratio([0.05]) is None
    assert sharpe_ratio([]) is None
    assert sharpe_ratio([0.05, 0.05, 0.05]) is None


def test_metrics_are_exposed_on_the_statistics_record():
    stats = trade_statistics([0.03, -0.01])
    assert stats.sharpe == pytest.approx(0.5)
    assert stats.max_drawdown == pytest.approx(0.01)
