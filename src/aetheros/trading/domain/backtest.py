"""
Backtest value objects.

A :class:`BacktestResult` is the deterministic product of a walk-forward
evaluation: at each historical bar a signal is computed from *only* the bars up
to and including that bar, and its call is scored against the realised forward
return ``horizon`` bars later. Nothing here is fitted, guessed, or produced by
an LLM -- it is honest, reproducible measurement (spec sections 6, 7, 21).

Crucially, a backtest on synthetic (MOCK) data proves nothing about a real
market edge, so such a result carries ``is_reliable = False`` no matter how good
the numbers look. The metrics here are for a *categorical* directional signal
(accuracy vs. an empirical base rate, plus trade-return statistics); calibrated
probabilistic metrics (Brier score, ROC-AUC, expected calibration error) belong
to the later probability layer and are deliberately absent, not silently faked.

The walk-forward layer (spec Phase 13, "Walk-forward testing") adds
:class:`FoldWindow`, :class:`WalkForwardFold` and :class:`WalkForwardReport`: a
series is split into consecutive train/test folds, a configuration is *chosen*
on each train window and then measured on the test window it has never seen.
The point of the split is that the in-sample number and the out-of-sample number
are recorded separately and are never allowed to be confused -- an in-sample
score is a selection artefact, and only the pooled out-of-sample figures are
evidence. :class:`BacktestComparison` is the "Strategy comparison" half: it
ranks several backtests of the same instrument, horizon and warmup against one
named metric, and refuses to crown a winner it cannot stand behind.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import Direction, OptimizationObjective
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class TradeOutcome:
    """One walk-forward prediction scored against its realised forward return."""

    index: int
    timestamp: datetime
    predicted: Direction
    entry_price: float
    exit_price: float
    forward_return: float
    realized: Direction
    correct: bool | None  # None when the prediction had no directional call

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "predicted": self.predicted.value,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "forward_return": self.forward_return,
            "realized": self.realized.value,
            "correct": self.correct,
        }


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Deterministic, reproducible walk-forward evaluation of a signal."""

    instrument: Instrument
    timeframe: str
    horizon: int
    warmup: int

    total_bars: int
    evaluated: int  # bars with a resolvable forward window

    directional_calls: int  # UP/DOWN predictions among the evaluated bars
    hits: int
    directional_accuracy: float | None

    up_calls: int
    up_hits: int
    up_accuracy: float | None
    down_calls: int
    down_hits: int
    down_accuracy: float | None

    coverage: float | None  # directional_calls / evaluated
    base_rate_up: float | None  # empirical P(forward move up) -- the naive baseline

    avg_return_per_trade: float | None  # signed per directional call
    cumulative_return: float | None  # additive equity curve of signed returns
    max_drawdown: float | None
    sharpe: float | None  # per-trade mean/std, NOT annualised

    quality: DataQuality
    provenance: Provenance
    is_reliable: bool
    statistics: TradeStatistics | None = None
    #: Signed per-trade returns, in evaluation order -- the raw material the
    #: statistics are computed from. Kept because the walk-forward layer has to
    #: *pool* several folds' trades into one sample, and a pooled drawdown or
    #: Sharpe cannot be reconstructed from already-summarised numbers. It is
    #: deliberately absent from :meth:`to_dict`: a tool result is read by an
    #: LLM, and shipping one float per historical call would drown it.
    returns: tuple[float, ...] = ()
    limitations: tuple[str, ...] = ()
    sample: tuple[TradeOutcome, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "warmup": self.warmup,
            "total_bars": self.total_bars,
            "evaluated": self.evaluated,
            "directional_calls": self.directional_calls,
            "hits": self.hits,
            "directional_accuracy": self.directional_accuracy,
            "up_calls": self.up_calls,
            "up_hits": self.up_hits,
            "up_accuracy": self.up_accuracy,
            "down_calls": self.down_calls,
            "down_hits": self.down_hits,
            "down_accuracy": self.down_accuracy,
            "coverage": self.coverage,
            "base_rate_up": self.base_rate_up,
            "avg_return_per_trade": self.avg_return_per_trade,
            "cumulative_return": self.cumulative_return,
            "max_drawdown": self.max_drawdown,
            "sharpe": self.sharpe,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "is_reliable": self.is_reliable,
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "limitations": list(self.limitations),
            "sample": [o.to_dict() for o in self.sample],
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class TradeStatistics:
    """
    Trade-return statistics (spec Phase 13 metrics).

    Win Rate, Profit Factor and Expectancy are measured here, alongside the
    Sharpe and maximum drawdown the engine already reported, so one object is
    the whole performance record of a set of trades.

    Everything is computed from *signed* per-trade returns -- a long call earns
    the forward return, a short call earns its negation -- so a **win** means
    the trade made money, which is deliberately not the same as a directionally
    *correct* call: a correct call on a flat move makes nothing and counts as a
    breakeven, not a win.

    Every ratio is ``None`` when it is undefined rather than zero or infinite.
    A sample with no losing trade has no finite profit factor, and reporting
    ``inf`` there would invite exactly the overconfidence the spec's honesty
    rules forbid.
    """

    trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate: float | None

    gross_profit: float
    gross_loss: float  # positive magnitude of the summed losing trades
    profit_factor: float | None

    average_win: float | None
    average_loss: float | None  # negative, as the trades were
    expectancy: float | None  # mean signed return per trade

    cumulative_return: float | None
    max_drawdown: float | None
    sharpe: float | None

    def __post_init__(self) -> None:
        if self.trades < 0:
            raise ValueError("A trade count cannot be negative.")
        for label, value in (
            ("wins", self.wins),
            ("losses", self.losses),
            ("breakevens", self.breakevens),
        ):
            if value < 0:
                raise ValueError(f"A trade statistics {label} count cannot be negative.")
        if self.wins + self.losses + self.breakevens != self.trades:
            raise ValueError(
                "A trade statistics record's wins, losses and breakevens must "
                "sum to its trade count."
            )
        for label, value in (
            ("gross_profit", self.gross_profit),
            ("gross_loss", self.gross_loss),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{label} must be a finite non-negative number.")
        for label, value in (
            ("win_rate", self.win_rate),
            ("profit_factor", self.profit_factor),
            ("average_win", self.average_win),
            ("average_loss", self.average_loss),
            ("expectancy", self.expectancy),
            ("cumulative_return", self.cumulative_return),
            ("max_drawdown", self.max_drawdown),
            ("sharpe", self.sharpe),
        ):
            if value is not None and not math.isfinite(value):
                raise ValueError(f"A trade statistics {label} must be finite.")
        if self.win_rate is not None and not 0.0 <= self.win_rate <= 1.0:
            raise ValueError("A win rate must be a fraction between 0 and 1.")
        if self.max_drawdown is not None and self.max_drawdown < 0:
            raise ValueError("A maximum drawdown is reported as a magnitude (>= 0).")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "breakevens": self.breakevens,
            "win_rate": self.win_rate,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "expectancy": self.expectancy,
            "cumulative_return": self.cumulative_return,
            "max_drawdown": self.max_drawdown,
            "sharpe": self.sharpe,
        }


@dataclass(frozen=True, slots=True)
class FoldWindow:
    """
    One walk-forward fold's bar ranges, half-open at both ends:
    ``[train_start, train_end)`` and ``[test_start, test_end)``.

    ``test_start`` is at least ``train_end``; the gap between them is the
    *embargo*, and it is not cosmetic. A training bar's label is the return
    ``horizon`` bars ahead of it, so a training bar within ``horizon`` of the
    test window carries a label that reaches into data the fold is supposed to
    have never seen. The embargo is what keeps the two apart, which is why
    :class:`~aetheros.trading.backtesting.walk_forward.WalkForwardSplitter`
    takes it and why the service defaults it to the horizon.
    """

    index: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("A fold index cannot be negative.")
        if self.train_start < 0:
            raise ValueError("A fold cannot start before the first bar.")
        if self.train_end <= self.train_start:
            raise ValueError("A fold's training window must span at least one bar.")
        if self.test_end <= self.test_start:
            raise ValueError("A fold's test window must span at least one bar.")
        if self.test_start < self.train_end:
            raise ValueError(
                "A fold's test window cannot start before its training window ends."
            )

    @property
    def embargo_bars(self) -> int:
        """Bars between the training and test windows (>= 0)."""
        return self.test_start - self.train_end

    @property
    def train_bars(self) -> int:
        return self.train_end - self.train_start

    @property
    def test_bars(self) -> int:
        return self.test_end - self.test_start

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "embargo_bars": self.embargo_bars,
            "train_bars": self.train_bars,
            "test_bars": self.test_bars,
        }


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    """
    One fold's outcome: what was chosen in-sample, and what it then did.

    ``selection`` holds the parameters chosen on the training window; an empty
    selection means nothing was fitted and the strategy's configured defaults
    were carried forward (an honest no-fit fold, not a silent one).
    ``in_sample`` and ``out_of_sample`` are kept apart on purpose: the
    in-sample figure is a *selection artefact* and must never be read as
    performance.
    """

    window: FoldWindow
    selection: tuple[tuple[str, Any], ...] = ()
    in_sample: BacktestResult | None = None
    out_of_sample: BacktestResult | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        keys = [key for key, _ in self.selection]
        if any(not key.strip() for key in keys) or len(keys) != len(set(keys)):
            raise ValueError("Selection keys must be non-empty and unique.")
        if self.out_of_sample is not None and self.in_sample is None:
            raise ValueError(
                "A fold measured out-of-sample must also carry the in-sample "
                "measurement its configuration was chosen from."
            )

    @property
    def evaluated(self) -> bool:
        """Whether the fold produced an out-of-sample measurement."""
        return self.out_of_sample is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "window": self.window.to_dict(),
            "selection": dict(self.selection),
            "in_sample": self.in_sample.to_dict() if self.in_sample else None,
            "out_of_sample": (
                self.out_of_sample.to_dict() if self.out_of_sample else None
            ),
            "evaluated": self.evaluated,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class WalkForwardReport:
    """
    A whole walk-forward run: every fold, plus the pooled out-of-sample result.

    The headline numbers are the **out-of-sample** ones. ``in_sample_accuracy_mean``
    is recorded so the gap between the two is visible -- a configuration that
    looks excellent in-sample and poor out-of-sample has been *fitted*, and
    that is the single most important thing a walk-forward run exists to expose.
    ``selection_stability`` is the share of folds whose winning parameter set
    was the most frequently chosen one; a search whose winner changes every fold
    has found noise, not a configuration.
    """

    instrument: Instrument
    timeframe: str
    horizon: int
    warmup: int
    embargo_bars: int
    objective: OptimizationObjective
    folds: tuple[WalkForwardFold, ...]

    oos_statistics: TradeStatistics | None
    oos_directional_calls: int
    oos_directional_accuracy: float | None
    oos_base_rate_up: float | None

    in_sample_accuracy_mean: float | None
    selection_stability: float | None

    quality: DataQuality
    provenance: Provenance
    is_reliable: bool
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if self.horizon < 1:
            raise ValueError("A walk-forward report needs a positive horizon.")
        if self.warmup < 0:
            raise ValueError("A walk-forward report's warmup cannot be negative.")
        if self.embargo_bars < 0:
            raise ValueError("A walk-forward report's embargo cannot be negative.")
        for index, fold in enumerate(self.folds):
            if fold.window.index != index:
                raise ValueError(
                    "A walk-forward report's folds must be indexed from zero in "
                    "the order they ran."
                )
        if self.oos_directional_calls < 0:
            raise ValueError("An out-of-sample call count cannot be negative.")
        for label, value in (
            ("oos_directional_accuracy", self.oos_directional_accuracy),
            ("oos_base_rate_up", self.oos_base_rate_up),
            ("in_sample_accuracy_mean", self.in_sample_accuracy_mean),
            ("selection_stability", self.selection_stability),
        ):
            if value is not None and not math.isfinite(value):
                raise ValueError(f"A walk-forward report's {label} must be finite.")

    @property
    def evaluated_folds(self) -> int:
        """How many folds produced an out-of-sample measurement."""
        return sum(1 for fold in self.folds if fold.evaluated)

    @property
    def generalisation_gap(self) -> float | None:
        """
        In-sample accuracy minus out-of-sample accuracy (positive is fitted).

        None when either side is undefined: the gap is only meaningful when
        both numbers were actually measured.
        """
        if self.in_sample_accuracy_mean is None or self.oos_directional_accuracy is None:
            return None
        return round(self.in_sample_accuracy_mean - self.oos_directional_accuracy, 6)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "warmup": self.warmup,
            "embargo_bars": self.embargo_bars,
            "objective": self.objective.value,
            "folds": [fold.to_dict() for fold in self.folds],
            "evaluated_folds": self.evaluated_folds,
            "oos_statistics": (
                self.oos_statistics.to_dict() if self.oos_statistics else None
            ),
            "oos_directional_calls": self.oos_directional_calls,
            "oos_directional_accuracy": self.oos_directional_accuracy,
            "oos_base_rate_up": self.oos_base_rate_up,
            "in_sample_accuracy_mean": self.in_sample_accuracy_mean,
            "generalisation_gap": self.generalisation_gap,
            "selection_stability": self.selection_stability,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "is_reliable": self.is_reliable,
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class BacktestComparisonEntry:
    """One backtest in a comparison, with its standing under the ranked metric."""

    label: str
    result: BacktestResult
    value: float | None
    rank: int | None = None  # 1-based; None when the metric is undefined here

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("A comparison entry needs a label.")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("A comparison entry's value must be finite.")
        if self.rank is not None and self.rank < 1:
            raise ValueError("A comparison rank starts at 1.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "rank": self.rank,
            "is_reliable": self.result.is_reliable,
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class BacktestComparison:
    """
    Several backtests of the same instrument ranked by one named metric.

    ``best`` is None -- not "the top of the list" -- whenever a winner cannot be
    stood behind: no entry is reliable, the top two are tied, or the winner's
    edge over the runner-up is not a strict improvement. A comparison that
    crowned the luckiest of two synthetic backtests would be manufacturing
    exactly the false confidence the spec forbids.
    """

    metric: str
    higher_is_better: bool
    entries: tuple[BacktestComparisonEntry, ...]
    best: str | None = None
    tied: tuple[str, ...] = ()
    is_conclusive: bool = False
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.metric.strip():
            raise ValueError("A comparison must name the metric it ranked.")
        if len(self.entries) < 2:
            raise ValueError("A comparison requires at least two backtests.")
        labels = [entry.label for entry in self.entries]
        if len(labels) != len(set(labels)):
            raise ValueError("Comparison entry labels must be unique.")
        if self.best is not None and self.best not in labels:
            raise ValueError("A comparison's winner must be one of its entries.")

    @property
    def ranked(self) -> tuple[BacktestComparisonEntry, ...]:
        """The entries the metric could be read for, best first."""
        ranked = [entry for entry in self.entries if entry.rank is not None]
        return tuple(
            sorted(ranked, key=lambda entry: entry.rank if entry.rank else 0)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "higher_is_better": self.higher_is_better,
            "entries": [entry.to_dict() for entry in self.entries],
            "best": self.best,
            "tied": list(self.tied),
            "is_conclusive": self.is_conclusive,
            "limitations": list(self.limitations),
        }
