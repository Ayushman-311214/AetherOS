"""
Deterministic parameter search (spec Phase 7).

"Optimize parameters" is the strategy-engine responsibility that most easily
becomes dishonest, so this module is built around three constraints:

**It reuses the existing backtester.** Scoring is
:meth:`BacktestService.run` -- the same walk-forward, look-ahead-safe engine the
rest of the system is validated with. There is no second backtester here, so a
parameter set cannot be selected by rules the deployed engine would not apply.
Each bar is still evaluated on ``candles[: t + 1]`` only, which means the
strategy genuinely cannot see the bar it is scored against.

**The grid is explicit and finite.** The caller names the axes and the values.
There is no gradient, no search heuristic and no randomness, so re-running a
search reproduces it exactly (CLAUDE.md section 31: reproducible results).

**No reliable winner is a valid result.** :attr:`ParameterSearch.best` is None
when no candidate cleared the reliability gate -- a mock series, or too few
directional calls to mean anything. Crowning the luckiest parameter set on a
thin sample is precisely the overfitting the spec forbids, so the honest answer
is that the search found nothing trustworthy. The strategy's *configured*
defaults are always evaluated as a baseline, so a winner has something real to
have beaten.
"""

from __future__ import annotations

import itertools
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..domain.backtest import BacktestResult
from ..domain.enums import Direction, OptimizationObjective, SourceTier
from ..domain.market_data import MarketData
from ..domain.provenance import Provenance
from ..domain.strategy import ParameterCandidate, ParameterSearch
from ..errors import InsufficientDataError
from .base import TradingStrategy
from .context import StrategyContext

if TYPE_CHECKING:  # imported for typing only: a runtime import here is circular
    from ..services.backtest_service import BacktestService, SignalFn

#: Builds the shared read for one window. Supplied by the caller (the strategy
#: service) so the optimizer owns no analysis logic of its own.
ContextBuilder = Callable[[MarketData], Awaitable[StrategyContext]]

_OBJECTIVES: dict[OptimizationObjective, str] = {
    OptimizationObjective.DIRECTIONAL_ACCURACY: "directional_accuracy",
    OptimizationObjective.CUMULATIVE_RETURN: "cumulative_return",
    OptimizationObjective.SHARPE: "sharpe",
}


@dataclass(frozen=True, slots=True)
class ParameterGrid:
    """
    A finite, explicitly enumerated set of parameter combinations.

    ``axes`` pairs each parameter name with the values to try, in declaration
    order; the search space is their Cartesian product. An axis with no values
    is rejected rather than treated as "skip this parameter", because a silently
    dropped axis would make a search report a result for a space it never
    explored.
    """

    axes: tuple[tuple[str, tuple[Any, ...]], ...]

    def __post_init__(self) -> None:
        names = [name for name, _ in self.axes]
        if len(names) != len(set(names)):
            raise ValueError("Parameter axis names must be unique.")
        for name, values in self.axes:
            if not name.strip():
                raise ValueError("A parameter axis must have a name.")
            if not values:
                raise ValueError(f"Parameter axis '{name}' has no values to try.")

    @classmethod
    def from_dict(cls, mapping: Mapping[str, Sequence[Any]]) -> ParameterGrid:
        """Build a grid from an ordered mapping of name -> values."""
        return cls(
            axes=tuple((name, tuple(values)) for name, values in mapping.items())
        )

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.axes)

    def size(self) -> int:
        """How many combinations the grid enumerates."""
        total = 1
        for _, values in self.axes:
            total *= len(values)
        return total

    def combinations(self) -> tuple[tuple[tuple[str, Any], ...], ...]:
        """Every combination, as ordered name/value pairs, in a stable order."""
        if not self.axes:
            return ((),)
        values = [values for _, values in self.axes]
        names = self.names
        return tuple(
            tuple(zip(names, combination, strict=True))
            for combination in itertools.product(*values)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "axes": {name: list(values) for name, values in self.axes},
            "size": self.size(),
        }


def strategy_signal(
    strategy: TradingStrategy, build_context: ContextBuilder
) -> SignalFn:
    """
    A backtest signal that runs one strategy over each past-only window.

    A window too short to analyse is a bar the strategy could not have traded, so
    it makes no call rather than raising: the backtester already treats a
    non-directional call as "did not trade", which is exactly the honest reading.
    Any *other* failure propagates -- a strategy that crashes is a bug, not an
    absence of signal.

    Public because the walk-forward service has to run the *same* signal over an
    out-of-sample window: a second, separately written version of this adapter
    could drift from the one the parameter search scored, and then the folds
    would be measuring a different strategy from the one that was chosen.
    """

    async def signal(window: MarketData) -> Direction:
        try:
            context = await build_context(window)
        except InsufficientDataError:
            return Direction.UNKNOWN
        return strategy.evaluate(context).direction

    return signal


class ParameterOptimizer:
    """
    Deterministic grid search over a strategy's parameters.

    Holds only a :class:`BacktestService`; the strategy, the data and the
    context builder are supplied per search, so one optimizer instance serves
    every strategy without holding state between runs.
    """

    def __init__(self, backtest: BacktestService) -> None:
        self._backtest = backtest

    async def search(
        self,
        strategy: TradingStrategy,
        data: MarketData,
        build_context: ContextBuilder,
        grid: ParameterGrid,
        *,
        objective: OptimizationObjective = OptimizationObjective.DIRECTIONAL_ACCURACY,
        horizon: int | None = None,
        warmup: int | None = None,
    ) -> ParameterSearch:
        """
        Evaluate every combination in ``grid`` and report the reliable winner.

        A grid names only the axes to vary, so a combination that resolves to
        the strategy's configured parameters *is* the baseline -- it is scored
        once and marked as such, rather than measured twice. When no
        combination resolves to the baseline, it is run separately so
        :attr:`ParameterSearch.baseline` is always the configuration the system
        would actually have run.
        """
        baseline_parameters = strategy.parameters
        combinations = grid.combinations()

        limitations: list[str] = []
        candidates: list[ParameterCandidate] = []
        for parameters in combinations:
            try:
                variant = strategy.with_parameters(**dict(parameters))
            except (TypeError, ValueError) as exc:
                # A grid value the strategy rejects is reported, never dropped
                # silently -- the search result must account for every point.
                limitations.append(
                    f"Combination {dict(parameters)} was rejected by "
                    f"{strategy.strategy_id}: {exc}"
                )
                continue
            candidates.append(
                await self._score(
                    variant,
                    data,
                    build_context,
                    objective,
                    horizon=horizon,
                    warmup=warmup,
                    is_baseline=variant.parameters == baseline_parameters,
                )
            )

        if not any(candidate.is_baseline for candidate in candidates):
            candidates.append(
                await self._score(
                    strategy,
                    data,
                    build_context,
                    objective,
                    horizon=horizon,
                    warmup=warmup,
                    is_baseline=True,
                )
            )

        baseline = next(
            (c for c in candidates if c.is_baseline),
            ParameterCandidate(
                strategy_id=strategy.strategy_id,
                parameters=baseline_parameters,
                score=None,
                directional_accuracy=None,
                cumulative_return=None,
                max_drawdown=None,
                sharpe=None,
                directional_calls=0,
                is_reliable=False,
                is_baseline=True,
            ),
        )

        reliable = [c for c in candidates if c.is_reliable and c.score is not None]
        best = max(reliable, key=lambda c: c.score or float("-inf")) if reliable else None
        if best is None:
            limitations.append(
                "No parameter combination produced a reliable result: the sample "
                "was too thin, the data synthetic, or the objective could not be "
                "measured. No 'best' parameters are reported."
            )
        if len(candidates) < grid.size():
            limitations.append(
                f"Only {len(candidates)} of {grid.size()} configured combinations "
                "could be evaluated."
            )

        return ParameterSearch(
            strategy_id=strategy.strategy_id,
            objective=objective,
            baseline=baseline,
            candidates=tuple(candidates),
            best=best,
            provenance=Provenance(
                source=data.provenance.source,
                tier=(
                    SourceTier.MOCK
                    if data.provenance.is_mock
                    else SourceTier.DERIVED
                ),
                detail="deterministic grid search over a walk-forward backtest",
            ),
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    async def _score(
        self,
        strategy: TradingStrategy,
        data: MarketData,
        build_context: ContextBuilder,
        objective: OptimizationObjective,
        *,
        horizon: int | None,
        warmup: int | None,
        is_baseline: bool,
    ) -> ParameterCandidate:
        result = await self._backtest.run(
            data,
            self._signal(strategy, build_context),
            horizon=horizon,
            warmup=warmup,
        )
        score = self._score_of(result, objective)
        return ParameterCandidate(
            strategy_id=strategy.strategy_id,
            parameters=strategy.parameters,
            score=score,
            directional_accuracy=result.directional_accuracy,
            cumulative_return=result.cumulative_return,
            max_drawdown=result.max_drawdown,
            sharpe=result.sharpe,
            directional_calls=result.directional_calls,
            is_reliable=result.is_reliable and score is not None,
            is_baseline=is_baseline,
        )

    @staticmethod
    def _signal(strategy: TradingStrategy, build_context: ContextBuilder) -> SignalFn:
        """Alias of :func:`strategy_signal`, kept for existing callers."""
        return strategy_signal(strategy, build_context)

    @staticmethod
    def _score_of(
        result: BacktestResult, objective: OptimizationObjective
    ) -> float | None:
        """
        The measured value of the chosen objective, or None when unmeasurable.

        None is returned rather than 0.0: a search that could not measure its
        own objective must not rank an unmeasurable candidate as a zero score,
        which would make it beat every negative one.
        """
        return getattr(result, _OBJECTIVES[objective])
