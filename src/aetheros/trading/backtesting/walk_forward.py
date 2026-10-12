"""
Walk-forward testing (spec Phase 13, "Walk-forward testing").

The engine's existing backtester measures one fixed configuration over the whole
series. That answers "how would this have done?" but never "how will choosing a
configuration have done?" -- and the difference is the whole point of
walk-forward testing. Fitting parameters on a series and then reporting the fit
is the classic way a backtest lies, so this module splits the series into
consecutive folds and keeps the two halves apart:

::

    fold 0:  [---- train ----][embargo][-- test --]
    fold 1:      [---- train ----][embargo][-- test --]
    fold 2:          [---- train ----][embargo][-- test --]

A configuration is *chosen* on each training window and then measured on a test
window it has never seen; only the pooled test-window figures are evidence, and
the report records the in-sample average beside them so the gap between the two
is visible rather than hidden.

**Why an embargo.** A training bar's label is the return ``horizon`` bars ahead
of it, so a training bar sitting within ``horizon`` of the test window carries a
label that reaches into data the fold is supposed to have never seen. Streaming
straight from train into test would leak exactly there, which is why
:class:`WalkForwardSplitter` takes an embargo and why the service defaults it to
the horizon rather than zero.

A fold that could not be evaluated is recorded as such with its reason; a run
with too few folds to be walk-forward evidence says so and is not reliable,
never quietly promoted to one.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from ..domain.backtest import (
    FoldWindow,
    TradeStatistics,
    WalkForwardFold,
    WalkForwardReport,
)
from ..domain.enums import OptimizationObjective
from ..domain.instrument import Instrument
from ..domain.provenance import DataQuality, Provenance
from .metrics import trade_statistics

#: Fewer folds than this is not walk-forward evidence: one fold cannot show
#: whether a configuration generalises, only whether it fitted once.
DEFAULT_MIN_FOLDS = 2


@dataclass(frozen=True, slots=True)
class WalkForwardSplitter:
    """
    A rolling/anchored train-test splitter for one bar series.

    ``train_bars`` and ``test_bars`` fix the two window lengths; ``step_bars``
    (default: one test window) advances the whole schedule, so the default walks
    through the series without scoring the same test bar twice. ``anchored``
    switches from a fixed-length training window to an expanding one that always
    starts at the same bar -- rolling adapts to recent behaviour, anchored
    accumulates history, and they answer different questions.

    ``step_bars`` smaller than ``test_bars`` deliberately overlaps the test
    windows; that is allowed because it trades independence for fold count, and
    the caller who sets it has asked for that.
    """

    train_bars: int
    test_bars: int
    embargo_bars: int = 0
    anchored: bool = False
    step_bars: int | None = None

    def __post_init__(self) -> None:
        if self.train_bars < 1:
            raise ValueError("A walk-forward splitter needs at least one train bar.")
        if self.test_bars < 1:
            raise ValueError("A walk-forward splitter needs at least one test bar.")
        if self.embargo_bars < 0:
            raise ValueError("A walk-forward embargo cannot be negative.")
        if self.step_bars is not None and self.step_bars < 1:
            raise ValueError("A walk-forward step must be at least one bar.")

    @property
    def step(self) -> int:
        """Bars the schedule advances per fold (one test window by default)."""
        return self.step_bars if self.step_bars is not None else self.test_bars

    @property
    def span_bars(self) -> int:
        """Bars a single non-anchored fold consumes: train + embargo + test."""
        return self.train_bars + self.embargo_bars + self.test_bars

    def folds(self, n_bars: int, *, warmup: int = 0) -> tuple[FoldWindow, ...]:
        """
        Every fold this schedule fits in a series of ``n_bars`` bars.

        ``warmup`` is the number of leading bars nothing may be trusted from, so
        the first fold starts after it. An empty result is the honest answer for
        a series too short for even one fold -- the caller reports that rather
        than evaluating a fold that does not exist.
        """
        if n_bars < 0:
            raise ValueError("A bar count cannot be negative.")
        if warmup < 0:
            raise ValueError("A warmup cannot be negative.")
        if warmup >= n_bars:
            return ()

        windows: list[FoldWindow] = []
        if self.anchored:
            # Expanding history: the training window always starts at the first
            # trusted bar and grows a step at a time.
            train_end = warmup + self.train_bars
            while train_end + self.embargo_bars + self.test_bars <= n_bars:
                test_start = train_end + self.embargo_bars
                windows.append(
                    FoldWindow(
                        index=len(windows),
                        train_start=warmup,
                        train_end=train_end,
                        test_start=test_start,
                        test_end=test_start + self.test_bars,
                    )
                )
                train_end += self.step
            return tuple(windows)

        train_start = warmup
        while train_start + self.span_bars <= n_bars:
            train_end = train_start + self.train_bars
            test_start = train_end + self.embargo_bars
            windows.append(
                FoldWindow(
                    index=len(windows),
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_start + self.test_bars,
                )
            )
            train_start += self.step
        return tuple(windows)


def pool_out_of_sample_returns(folds: Sequence[WalkForwardFold]) -> list[float]:
    """
    Every fold's out-of-sample trade returns, in fold order.

    The folds are chronological and their test windows do not overlap (at the
    default step), so concatenating them gives one continuous out-of-sample
    equity path -- which is what makes a pooled drawdown and Sharpe meaningful
    rather than an average of unrelated curves.
    """
    pooled: list[float] = []
    for fold in folds:
        if fold.out_of_sample is not None:
            pooled.extend(fold.out_of_sample.returns)
    return pooled


def _weighted_mean(values: Sequence[tuple[float | None, int]]) -> float | None:
    """A ratio pooled across folds, weighted by the bars each was measured on."""
    total = sum(weight for _, weight in values)
    if total <= 0:
        return None
    weighted = sum(value * weight for value, weight in values if value is not None)
    return round(weighted / total, 6)


def selection_stability(folds: Sequence[WalkForwardFold]) -> float | None:
    """
    How often the fold winner was the same parameter set, as a share.

    A search whose "best" parameters change every fold has found noise rather
    than a configuration, and this is the number that shows it. Folds that
    fitted nothing (the strategy's own defaults were carried forward) are
    excluded: carrying defaults is not a selection, and counting it as one would
    inflate the stability of a run that never selected anything.
    """
    selections = [
        tuple((key, repr(value)) for key, value in fold.selection)
        for fold in folds
        if fold.selection
    ]
    if not selections:
        return None
    most_common = Counter(selections).most_common(1)[0][1]
    return round(most_common / len(selections), 6)


def summarise_folds(
    folds: Sequence[WalkForwardFold],
    *,
    instrument: Instrument,
    timeframe: str,
    horizon: int,
    warmup: int,
    embargo_bars: int,
    objective: OptimizationObjective,
    quality: DataQuality,
    provenance: Provenance,
    min_sample: int,
    min_folds: int = DEFAULT_MIN_FOLDS,
) -> WalkForwardReport:
    """
    Aggregate folds into one report, pooling only the out-of-sample results.

    The honesty gate is structural rather than decorative: a run is reliable
    only when it has enough *evaluated* folds, on non-synthetic usable data,
    with enough pooled out-of-sample calls to mean anything. Each failed
    condition adds its own named limitation, so an unreliable report says
    exactly which thing about it was insufficient instead of leaving the reader
    to guess.
    """
    limitations: list[str] = []
    evaluated = [fold for fold in folds if fold.out_of_sample is not None]

    if not folds:
        limitations.append(
            "No fold fitted the series: it is too short for the configured "
            f"train({instrument.key}) + embargo + test windows."
        )
    if not evaluated:
        limitations.append(
            "No fold produced an out-of-sample measurement, so there is "
            "nothing to generalise from."
        )
    if provenance.is_mock:
        limitations.append(
            "Walk-forward ran on synthetic MOCK data; the folds verify the "
            "engine, not a real market edge."
        )
    if not quality.ok:
        limitations.append(
            f"Data quality is '{quality.status.value}': "
            + "; ".join(quality.issues)
        )
    if len(evaluated) < min_folds:
        limitations.append(
            f"Only {len(evaluated)} fold(s) were measured (< {min_folds}); a "
            "walk-forward conclusion needs more than one fold."
        )

    pooled = pool_out_of_sample_returns(folds)
    statistics: TradeStatistics | None = trade_statistics(pooled) if pooled else None

    directional_calls = sum(
        fold.out_of_sample.directional_calls
        for fold in evaluated
        if fold.out_of_sample is not None
    )
    hits = sum(
        fold.out_of_sample.hits
        for fold in evaluated
        if fold.out_of_sample is not None
    )
    accuracy = (
        round(hits / directional_calls, 6) if directional_calls > 0 else None
    )
    base_rate = _weighted_mean(
        [
            (fold.out_of_sample.base_rate_up, fold.out_of_sample.evaluated)
            for fold in evaluated
            if fold.out_of_sample is not None
        ]
    )
    in_sample_mean = _weighted_mean(
        [
            (fold.in_sample.directional_accuracy, fold.in_sample.directional_calls)
            for fold in evaluated
            if fold.in_sample is not None
            and fold.in_sample.directional_accuracy is not None
        ]
    )

    if directional_calls == 0 and evaluated:
        limitations.append(
            "No out-of-sample directional calls were made; accuracy is undefined."
        )
    if directional_calls < min_sample and directional_calls > 0:
        limitations.append(
            f"Only {directional_calls} pooled out-of-sample directional calls "
            f"(< {min_sample}); the sample is too small to be reliable."
        )

    is_reliable = (
        quality.usable
        and not provenance.is_mock
        and len(evaluated) >= min_folds
        and directional_calls >= min_sample
    )

    return WalkForwardReport(
        instrument=instrument,
        timeframe=timeframe,
        horizon=horizon,
        warmup=warmup,
        embargo_bars=embargo_bars,
        objective=objective,
        folds=tuple(folds),
        oos_statistics=statistics,
        oos_directional_calls=directional_calls,
        oos_directional_accuracy=accuracy,
        oos_base_rate_up=base_rate,
        in_sample_accuracy_mean=in_sample_mean,
        selection_stability=selection_stability(folds),
        quality=quality,
        provenance=provenance,
        is_reliable=is_reliable,
        limitations=tuple(limitations),
    )
