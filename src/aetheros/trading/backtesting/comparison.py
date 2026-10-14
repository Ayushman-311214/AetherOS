"""
Backtest comparison (spec Phase 13, "Strategy comparison").

Ranks several backtests of the *same* question against one named metric. The
restriction is the substance of the module: comparing a 5-day horizon against a
1-day one, or two different instruments, produces a number that looks like a
result and means nothing, so :func:`compare_backtests` refuses the comparison
outright rather than qualifying it.

Two honesty rules shape the output:

- a metric that is undefined for a candidate (no losing trade means no profit
  factor; one trade has no Sharpe) leaves that candidate **unranked**, and the
  limitations say so -- it is not quietly treated as zero, which would let a
  strategy win by having no measurable result;
- a winner is crowned only when it is a *reliable* backtest that strictly beat
  the runner-up. A tie, a synthetic-data leader, or a leader the engine itself
  flagged as unreliable yields ``best = None`` with the reason attached.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..domain.backtest import BacktestComparison, BacktestComparisonEntry
from ..domain.backtest import BacktestResult as Result
from ..errors import BacktestError

#: The metrics that may be compared, mapped to whether a higher value is the
#: better outcome. Every one is either a plain accuracy/return ratio (higher is
#: better) or a drawdown (lower is better); there is no third case, which is why
#: the flag is a bool rather than a direction enum.
COMPARABLE_METRICS: dict[str, bool] = {
    "directional_accuracy": True,
    "win_rate": True,
    "profit_factor": True,
    "expectancy": True,
    "sharpe": True,
    "cumulative_return": True,
    "max_drawdown": False,
}

DEFAULT_COMPARISON_METRIC = "directional_accuracy"


def metric_value(result: Result, metric: str) -> float | None:
    """
    The named metric's value for one backtest, or ``None`` when undefined.

    Two metrics live on the trade statistics rather than the result itself
    (win rate, profit factor, expectancy), so they read through
    ``result.statistics`` and are undefined for a result that carries none --
    which is exactly the "no measurable result" case the caller must not treat
    as a score.
    """
    if metric == "directional_accuracy":
        return result.directional_accuracy
    if metric == "sharpe":
        return result.sharpe
    if metric == "cumulative_return":
        return result.cumulative_return
    if metric == "max_drawdown":
        return result.max_drawdown
    if result.statistics is None:
        return None
    if metric == "win_rate":
        return result.statistics.win_rate
    if metric == "profit_factor":
        return result.statistics.profit_factor
    if metric == "expectancy":
        return result.statistics.expectancy
    raise ValueError(f"Unknown comparison metric '{metric}'.")


def _assert_comparable(results: Mapping[str, Result]) -> None:
    """Reject a comparison whose candidates were not measured on one question."""
    baseline_label, baseline = next(iter(results.items()))
    for label, result in results.items():
        if result.instrument.key != baseline.instrument.key:
            raise BacktestError(
                f"Backtests are not comparable: '{baseline_label}' is "
                f"{baseline.instrument.key} but '{label}' is "
                f"{result.instrument.key}."
            )
        if result.timeframe != baseline.timeframe:
            raise BacktestError(
                f"Backtests are not comparable: '{baseline_label}' ran on "
                f"{baseline.timeframe} but '{label}' ran on {result.timeframe}."
            )
        if result.horizon != baseline.horizon:
            raise BacktestError(
                f"Backtests are not comparable: '{baseline_label}' used a "
                f"{baseline.horizon}-bar horizon but '{label}' used "
                f"{result.horizon}."
            )
        if result.warmup != baseline.warmup:
            raise BacktestError(
                f"Backtests are not comparable: '{baseline_label}' used a "
                f"{baseline.warmup}-bar warmup but '{label}' used "
                f"{result.warmup}."
            )


def compare_backtests(
    results: Mapping[str, Result],
    *,
    metric: str = DEFAULT_COMPARISON_METRIC,
) -> BacktestComparison:
    """
    Rank ``{label: result}`` against one metric of a single shared question.

    Ranking is competition-style: an entry's rank is one more than the number of
    entries that strictly beat it, so equal values share a rank and the next
    rank is skipped. Only entries the metric is defined for are ranked.
    """
    if metric not in COMPARABLE_METRICS:
        raise ValueError(
            f"Unknown comparison metric '{metric}'. Known metrics: "
            + ", ".join(sorted(COMPARABLE_METRICS))
            + "."
        )
    if len(results) < 2:
        raise ValueError("A comparison needs at least two backtests to compare.")
    _assert_comparable(results)

    higher_is_better = COMPARABLE_METRICS[metric]
    candidates = [
        (label, result, metric_value(result, metric)) for label, result in results.items()
    ]

    entries: list[BacktestComparisonEntry] = []
    for label, result, value in candidates:
        if value is None:
            entries.append(
                BacktestComparisonEntry(
                    label=label, result=result, value=None, rank=None
                )
            )
            continue
        better = sum(
            1
            for _, _, other in candidates
            if other is not None
            and (
                other > value
                if higher_is_better
                else other < value  # the lower the drawdown, the better
            )
        )
        entries.append(
            BacktestComparisonEntry(
                label=label, result=result, value=value, rank=better + 1
            )
        )

    ranked = tuple(
        sorted(
            (entry for entry in entries if entry.rank is not None),
            key=lambda entry: entry.rank if entry.rank is not None else 0,
        )
    )
    leaders = tuple(entry.label for entry in ranked if entry.rank == 1)

    limitations: list[str] = []
    unranked = tuple(entry.label for entry in entries if entry.rank is None)
    if unranked:
        limitations.append(
            f"'{metric}' is undefined for "
            + ", ".join(f"'{label}'" for label in unranked)
            + ", so they were not ranked."
        )
    mock_labels = tuple(
        entry.label for entry in entries if entry.result.provenance.is_mock
    )
    if mock_labels:
        limitations.append(
            "Measured on synthetic MOCK data: "
            + ", ".join(f"'{label}'" for label in mock_labels)
            + ". A ranking among synthetic results is not market evidence."
        )

    best: str | None = None
    tied: tuple[str, ...] = ()
    if len(leaders) == 1:
        leader = ranked[0]
        if leader.result.is_reliable:
            best = leader.label
        else:
            limitations.append(
                f"'{leader.label}' leads on {metric} but its own backtest is "
                "flagged unreliable, so no winner is declared."
            )
    elif len(leaders) > 1:
        tied = leaders
        limitations.append(
            "Tied on "
            f"{metric}: "
            + ", ".join(f"'{label}'" for label in leaders)
            + ". No winner is declared."
        )
    else:
        limitations.append(
            f"No backtest had a defined value for '{metric}', so the "
            "comparison is empty."
        )

    # A winner is conclusive only if it strictly beat a runner-up *and* is
    # reliable; a leader with nothing behind it has not been shown to be better
    # than anything.
    is_conclusive = best is not None and len(ranked) >= 2

    return BacktestComparison(
        metric=metric,
        higher_is_better=higher_is_better,
        entries=tuple(entries),
        best=best,
        tied=tied,
        is_conclusive=is_conclusive,
        limitations=tuple(limitations),
    )
