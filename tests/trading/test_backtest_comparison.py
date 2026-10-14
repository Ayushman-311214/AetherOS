"""
Backtest comparison tests (spec Phase 13, "strategy comparison").

The rules being pinned are mostly *refusals*, because that is where a comparison
goes wrong. Ranking ``{label: result}`` on one metric is arithmetic; the value of
the module is that it will not rank backtests measured on different questions,
will not treat an undefined metric as a zero score, and will not crown a winner
that is unreliable or merely tied.
"""

from __future__ import annotations

import pytest

from aetheros.trading.backtesting.comparison import (
    COMPARABLE_METRICS,
    compare_backtests,
    metric_value,
)
from aetheros.trading.domain.enums import SourceTier, Timeframe
from aetheros.trading.errors import BacktestError

from .conftest import make_backtest_result


# ----------------------------------------------------------------------
# ranking
# ----------------------------------------------------------------------


def test_a_higher_is_better_metric_ranks_the_best_first():
    comparison = compare_backtests(
        {
            "momentum": make_backtest_result((0.03, 0.03, 0.03)),
            "meanrev": make_backtest_result((0.05, -0.05, 0.05, -0.05)),
            "breakout": make_backtest_result((0.01, -0.02, -0.02, -0.02)),
        },
        metric="directional_accuracy",
    )

    assert comparison.best == "momentum"
    assert comparison.is_conclusive is True
    assert [entry.label for entry in comparison.ranked] == [
        "momentum",
        "meanrev",
        "breakout",
    ]
    assert [entry.rank for entry in comparison.ranked] == [1, 2, 3]


def test_a_lower_is_better_metric_ranks_the_smallest_drawdown_first():
    # max_drawdown is the one comparable metric where less is more, and a run
    # that fell 5% beats one that fell 20%.
    comparison = compare_backtests(
        {
            "shallow": make_backtest_result((0.10, -0.05, 0.10, -0.05)),
            "deep": make_backtest_result((0.10, -0.20, 0.10, -0.20)),
        },
        metric="max_drawdown",
    )

    assert comparison.higher_is_better is False
    assert comparison.best == "shallow"
    assert comparison.ranked[0].value < comparison.ranked[1].value


def test_identical_values_share_a_rank_and_leave_no_winner():
    comparison = compare_backtests(
        {
            "a": make_backtest_result((0.03, 0.03, 0.03)),
            "b": make_backtest_result((0.03, 0.03, 0.03)),
        },
        metric="directional_accuracy",
    )

    assert comparison.best is None
    assert comparison.tied == ("a", "b")
    assert comparison.is_conclusive is False
    assert [entry.rank for entry in comparison.ranked] == [1, 1]
    assert any("Tied" in line for line in comparison.limitations)


def test_a_leader_whose_own_backtest_is_unreliable_wins_nothing():
    comparison = compare_backtests(
        {
            "lucky": make_backtest_result((0.09, 0.09, 0.09), reliable=False),
            "honest": make_backtest_result((0.02, 0.02, -0.01)),
        },
        metric="directional_accuracy",
    )

    assert comparison.ranked[0].label == "lucky"
    assert comparison.best is None
    assert comparison.is_conclusive is False
    assert any("unreliable" in line for line in comparison.limitations)


def test_a_leader_with_no_runner_up_is_not_conclusive():
    # Only one entry had a defined value, so nothing was beaten.
    comparison = compare_backtests(
        {
            "measured": make_backtest_result((0.05, -0.05, 0.05, -0.05)),
            "silent": make_backtest_result(),
        },
        metric="directional_accuracy",
    )

    assert comparison.best == "measured"
    assert comparison.is_conclusive is False
    assert comparison.limitations


def test_a_metric_undefined_for_a_candidate_leaves_it_unranked():
    # `profit_factor` needs a losing trade. A candidate with none has no value
    # for it -- and that must not be read as a zero, which every real score beats.
    comparison = compare_backtests(
        {
            "allwins": make_backtest_result((0.05, 0.05)),
            "mixed": make_backtest_result((0.05, -0.01)),
        },
        metric="profit_factor",
    )

    unranked = [entry for entry in comparison.entries if entry.rank is None]
    assert [entry.label for entry in unranked] == ["allwins"]
    assert unranked[0].value is None
    assert comparison.best == "mixed"
    assert any("undefined" in line for line in comparison.limitations)


def test_a_result_without_statistics_has_no_trade_metric():
    result = make_backtest_result()
    assert result.statistics is None
    assert metric_value(result, "win_rate") is None
    assert metric_value(result, "profit_factor") is None
    assert metric_value(result, "expectancy") is None
    # ...but the result-level metrics are still readable.
    assert metric_value(result, "directional_accuracy") is None
    assert metric_value(result, "max_drawdown") is None


def test_synthetic_data_is_named_in_the_limitations():
    comparison = compare_backtests(
        {
            "a": make_backtest_result(
                (0.05, 0.05, -0.01), tier=SourceTier.MOCK, reliable=False
            ),
            "b": make_backtest_result((0.02, -0.01, -0.01)),
        },
        metric="directional_accuracy",
    )
    assert any("MOCK" in line for line in comparison.limitations)


def test_the_mock_leader_does_not_win_on_synthetic_data():
    comparison = compare_backtests(
        {
            "a": make_backtest_result(
                (0.05, 0.05, 0.05), tier=SourceTier.MOCK, reliable=False
            ),
            "b": make_backtest_result((0.02, -0.01, -0.01)),
        },
        metric="directional_accuracy",
    )
    assert comparison.ranked[0].label == "a"
    assert comparison.best is None


def test_every_comparable_metric_is_readable_from_a_full_result():
    result = make_backtest_result((0.05, -0.01, 0.02, -0.02))
    for metric in COMPARABLE_METRICS:
        assert metric_value(result, metric) is not None
    with pytest.raises(ValueError):
        metric_value(result, "not_a_metric")


# ----------------------------------------------------------------------
# refusals
# ----------------------------------------------------------------------


def test_backtests_of_different_instruments_are_not_comparable():
    with pytest.raises(BacktestError) as excinfo:
        compare_backtests(
            {
                "a": make_backtest_result((0.05, 0.05), symbol="AAA"),
                "b": make_backtest_result((0.05, 0.05), symbol="BBB"),
            }
        )
    assert "AAA" in str(excinfo.value) and "BBB" in str(excinfo.value)


def test_backtests_over_different_horizons_are_not_comparable():
    with pytest.raises(BacktestError):
        compare_backtests(
            {
                "a": make_backtest_result((0.05, 0.05), horizon=1),
                "b": make_backtest_result((0.05, 0.05), horizon=5),
            }
        )


def test_backtests_on_different_timeframes_are_not_comparable():
    with pytest.raises(BacktestError):
        compare_backtests(
            {
                "a": make_backtest_result((0.05, 0.05), timeframe=Timeframe.D1),
                "b": make_backtest_result((0.05, 0.05), timeframe=Timeframe.H1),
            }
        )


def test_backtests_with_different_warmups_are_not_comparable():
    with pytest.raises(BacktestError):
        compare_backtests(
            {
                "a": make_backtest_result((0.05, 0.05), warmup=0),
                "b": make_backtest_result((0.05, 0.05), warmup=50),
            }
        )


def test_an_unknown_metric_is_rejected():
    with pytest.raises(ValueError) as excinfo:
        compare_backtests(
            {
                "a": make_backtest_result((0.05, 0.05)),
                "b": make_backtest_result((0.05, 0.05)),
            },
            metric="vibes",
        )
    assert "vibes" in str(excinfo.value)


def test_a_comparison_needs_at_least_two_candidates():
    with pytest.raises(ValueError):
        compare_backtests({"only": make_backtest_result((0.05, 0.05))})
