"""
Strategy service: build the shared read, evaluate strategies, compare them,
and optimize their parameters (spec Phase 7).

This is the assembly point the strategy package deliberately lacks. A strategy
takes a :class:`StrategyContext` and nothing else -- it fetches no data, runs no
indicator and detects no structure -- so *something* has to do that work once
per instrument/timeframe, and this is it. Building the context here rather than
inside the strategies is what makes a comparison meaningful: every strategy in a
panel interprets the same numbers, so a disagreement is a disagreement about
reading rather than about inputs.

The four responsibilities map onto the four public methods:

- :meth:`build_context` -- assemble the analysis / SMC / ICT / breakout reads.
- :meth:`evaluate` -- run one named strategy over an already-built context.
- :meth:`compare` -- run a panel and report their consensus, *and* their
  disagreement.
- :meth:`optimize` -- a deterministic grid search scored by the existing
  walk-forward :class:`BacktestService`.

Nothing here produces a probability, a signal or an order. A setup says "this
side, read at this price, void below this level"; sizing it, pricing it and
deciding whether to act on it are the risk engine's and the later signal
layer's jobs (CLAUDE.md section 9's required path). No event is published: the
sibling detection services (SMC, ICT, breakout) do not publish either, and a
comparison is an intermediate reading, not a state change anything else in the
system consumes -- the report layer's own event is the one that matters.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from ...core.logging import get_logger
from ..domain.enums import Direction, OptimizationObjective
from ..domain.market_data import MarketData
from ..domain.strategy import (
    ParameterSearch,
    StrategyComparison,
    StrategyEvaluation,
    StrategySetup,
)
from ..errors import InsufficientDataError, StrategyError
from ..strategies.base import TradingStrategy
from ..strategies.context import StrategyContext
from ..strategies.optimization import ParameterGrid, ParameterOptimizer
from ..strategies.registry import StrategyRegistry, default_registry
from .analysis_service import AnalysisService
from .backtest_service import BacktestService
from .breakout_service import BreakoutService
from .ict_service import ICTService
from .market_structure_service import MarketStructureService
from .smc_service import SMCService

logger = get_logger("trading.strategy")

#: Bars below which a context is not worth assembling. Matches the SMC and ICT
#: services' own floors -- asking for less would only produce two failures
#: dressed up as one.
DEFAULT_MIN_BARS = 20

_Read = TypeVar("_Read")


class StrategyService:
    """Deterministic strategy evaluation, comparison and tuning."""

    def __init__(
        self,
        analysis: AnalysisService,
        structure: MarketStructureService | None = None,
        smc: SMCService | None = None,
        ict: ICTService | None = None,
        breakout: BreakoutService | None = None,
        *,
        registry: StrategyRegistry | None = None,
        backtest: BacktestService | None = None,
        min_bars: int = DEFAULT_MIN_BARS,
    ) -> None:
        if min_bars < 5:
            raise ValueError("min_bars must be at least 5.")

        # The structure service is shared, not rebuilt, so the SMC and ICT
        # reads cannot disagree about where the swings are.
        self._structure = structure or MarketStructureService()
        self._smc = smc or SMCService(self._structure)
        self._ict = ict or ICTService(self._structure, self._smc)
        self._breakout = breakout
        self._analysis = analysis
        self._registry = registry or default_registry()
        self._optimizer = ParameterOptimizer(backtest) if backtest else None
        self._min_bars = min_bars

    @property
    def registry(self) -> StrategyRegistry:
        return self._registry

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    async def build_context(self, data: MarketData) -> StrategyContext:
        """
        Assemble the one read every strategy in a panel interprets.

        The technical and structural analysis comes from
        :class:`AnalysisService`, which is the system's existing deterministic
        core -- re-running its maths here would be a second, divergent
        definition of the same indicators. The SMC read is required; ICT and
        breakout are optional by design, and when one of them cannot be built
        the reason is recorded as a *degradation* rather than left as a bare
        ``None``, because "the engine found nothing" and "the engine could not
        run" are different facts and the strategies report them differently.

        Raises :class:`InsufficientDataError` when there is not enough history
        to build the required reads at all.
        """
        count = len(data.candles)
        if count < self._min_bars:
            raise InsufficientDataError(
                f"Need at least {self._min_bars} candles for a strategy context, "
                f"got {count}.",
                context={"instrument": data.instrument.key, "bars": count},
            )

        # emit=False: a context is built once per call (and once per bar during
        # an optimization sweep), so publishing AnalysisCompleted for each would
        # flood the bus with intermediate work that is not itself a result.
        analysis = await self._analysis.analyze_data(data, emit=False)
        smc = self._smc.analyze(data)

        degradations: list[str] = []
        ict = self._optional("ICT", self._ict.analyze, data, degradations)
        if self._breakout is None:
            degradations.append(
                "No breakout service is configured, so the breakout read and "
                "any strategy that needs it are unavailable."
            )
            breakout = None
        else:
            breakout = self._optional(
                "breakout", self._breakout.analyze, data, degradations
            )

        return StrategyContext(
            data=data,
            analysis=analysis,
            smc=smc,
            ict=ict,
            breakout=breakout,
            degradations=tuple(degradations),
        )

    @staticmethod
    def _optional(
        label: str,
        build: Callable[[MarketData], _Read],
        data: MarketData,
        degradations: list[str],
    ) -> _Read | None:
        """
        Build an optional read, degrading to ``None`` on insufficient history.

        Only :class:`InsufficientDataError` is absorbed -- a documented,
        expected absence on a short window. Any other failure is a bug in the
        read and propagates rather than being silently converted into "there
        was nothing here".
        """
        try:
            return build(data)
        except InsufficientDataError as exc:
            degradations.append(
                f"The {label} read could not be built for this window: {exc.message}. "
                f"Strategies that need it will report that they could not run."
            )
            return None

    # ------------------------------------------------------------------
    # Evaluate / compare
    # ------------------------------------------------------------------

    def evaluate(self, context: StrategyContext, strategy_id: str) -> StrategyEvaluation:
        """
        Run one named strategy over an already-built context.

        Synchronous and side-effect-free: everything expensive happened in
        :meth:`build_context`, which is exactly why a panel can be evaluated
        against one shared read.
        """
        return self._registry.require(strategy_id).evaluate(context)

    async def compare(
        self,
        data: MarketData,
        *,
        strategy_ids: Sequence[str] | None = None,
    ) -> StrategyComparison:
        """
        Evaluate a panel of strategies over one context and compare the results.

        ``strategy_ids`` defaults to everything registered. The consensus is
        UNKNOWN when the firing strategies split, and every strategy that took
        the losing side -- or, on a tie, any side at all -- is listed as
        dissenting. Averaging a 3-2 split into a single direction would hide
        precisely the disagreement a comparison exists to surface.
        """
        context = await self.build_context(data)
        strategies = self._panel(strategy_ids)
        evaluations = tuple(strategy.evaluate(context) for strategy in strategies)

        bullish = sum(1 for item in evaluations if item.direction is Direction.UP)
        bearish = sum(1 for item in evaluations if item.direction is Direction.DOWN)
        if bullish > bearish:
            consensus = Direction.UP
        elif bearish > bullish:
            consensus = Direction.DOWN
        else:
            consensus = Direction.UNKNOWN

        firing = bullish + bearish
        limitations = list(context.degradations)
        if consensus is Direction.UNKNOWN:
            agreement = None
            dissenting = tuple(item.strategy_id for item in evaluations if item.fired)
            if firing == 0:
                limitations.append(
                    "No registered strategy produced a setup on this context; "
                    "the comparison is the system's insufficient-evidence result."
                )
            else:
                limitations.append(
                    f"The firing strategies split {bullish}-{bearish}; no "
                    "consensus direction is reported."
                )
        else:
            agreeing = bullish if consensus is Direction.UP else bearish
            agreement = round(agreeing / firing, 6)
            dissenting = tuple(
                item.strategy_id
                for item in evaluations
                if item.fired and item.direction is not consensus
            )

        return StrategyComparison(
            instrument_key=data.instrument.key,
            timeframe=data.timeframe.value,
            evaluations=evaluations,
            consensus=consensus,
            agreement=agreement,
            bullish=bullish,
            bearish=bearish,
            dissenting=dissenting,
            provenance=context.provenance,
            limitations=tuple(limitations),
        )

    def _panel(self, strategy_ids: Sequence[str] | None) -> tuple[TradingStrategy, ...]:
        if strategy_ids is None:
            strategies = self._registry.all()
        else:
            strategies = tuple(
                self._registry.require(strategy_id) for strategy_id in strategy_ids
            )
        if not strategies:
            raise StrategyError(
                "No strategies are registered to evaluate.",
                hint="Register strategies on the service's registry first.",
            )
        return strategies

    # ------------------------------------------------------------------
    # Optimize
    # ------------------------------------------------------------------

    async def optimize(
        self,
        data: MarketData,
        strategy_id: str,
        grid: ParameterGrid,
        *,
        objective: OptimizationObjective = OptimizationObjective.DIRECTIONAL_ACCURACY,
        horizon: int | None = None,
        warmup: int | None = None,
    ) -> ParameterSearch:
        """
        Grid-search one strategy's parameters over a walk-forward backtest.

        Every bar re-runs :meth:`build_context` on the window up to that bar, so
        the search is honest but not cheap -- the cost is one full analysis per
        bar per combination, and that is the price of not evaluating a parameter
        set on data it could not have seen.
        """
        if self._optimizer is None:
            raise StrategyError(
                "Parameter optimization needs a backtester, and none was injected.",
                hint="Construct StrategyService with a BacktestService to "
                "optimize strategy parameters.",
            )
        strategy = self._registry.require(strategy_id)
        logger.debug(
            "Optimizing strategy '%s' over %d combinations",
            strategy_id,
            grid.size(),
        )
        return await self._optimizer.search(
            strategy,
            data,
            self.build_context,
            grid,
            objective=objective,
            horizon=horizon,
            warmup=warmup,
        )

    # ------------------------------------------------------------------

    def setups(self, evaluations: Sequence[StrategyEvaluation]) -> tuple[StrategySetup, ...]:
        """The setups among a set of evaluations, in the order given."""
        return tuple(item.setup for item in evaluations if item.setup is not None)
