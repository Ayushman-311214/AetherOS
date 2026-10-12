"""
Walk-forward service (spec Phase 13 -- historical and walk-forward testing).

The engine's :class:`~aetheros.trading.services.backtest_service.BacktestService`
scores *one fixed configuration* over a series; the strategy layer's
:class:`~aetheros.trading.strategies.optimization.ParameterOptimizer` picks the
best configuration *on* a series. Neither answers the question that decides
whether a strategy is worth running: **if the system had re-chosen its parameters
at each point in history, using only what it knew then, how would the choices have
done on the data that followed?**

This service answers exactly that, and nothing else:

::

    for each fold:   [---- train ----][embargo][-- test --]

        choose parameters  ->  ParameterOptimizer.search(train)
        measure them       ->  BacktestService.run(test)     <- the only evidence

The orchestration lives here rather than in ``trading/backtesting`` because that
package must stay importable by this service without importing it back: the
arithmetic is pure, the wiring is not.

Three properties are deliberate and load-bearing:

**The embargo is the horizon, not zero.** A training bar is labelled with the
return ``horizon`` bars ahead of it, so the last ``horizon`` training bars carry
labels drawn from the test window. Streaming train straight into test would leak
there and nowhere else, which is the one leak a walk-forward run exists to
prevent.

**Nothing fitted means the defaults, and a named limitation.** When no parameter
combination clears the search's reliability gate, the fold carries the
strategy's configured parameters forward and says so. Silently skipping the fold
would hide a strategy the system cannot tune; silently keeping the in-sample
winner would be the overfit the split exists to avoid.

**Pooled, not averaged.** Each fold's out-of-sample trades are concatenated in
time order before the drawdown and Sharpe are computed, because those two are
path-dependent: an average of per-fold drawdowns is not the drawdown of the run.
"""

from __future__ import annotations

from typing import Any

from ...config.settings import Settings
from ...core.logging import get_logger
from ..backtesting.walk_forward import WalkForwardSplitter, summarise_folds
from ..domain.backtest import (
    BacktestResult,
    FoldWindow,
    WalkForwardFold,
    WalkForwardReport,
)
from ..domain.enums import OptimizationObjective, SourceTier
from ..domain.market_data import MarketData
from ..domain.provenance import Provenance
from ..errors import StrategyError
from ..strategies.base import TradingStrategy
from ..strategies.optimization import ParameterGrid, ParameterOptimizer, strategy_signal
from .backtest_service import BacktestService
from .strategy_service import StrategyService

logger = get_logger("trading.walk_forward")


class WalkForwardService:
    """
    Rolling/anchored walk-forward evaluation of one strategy's parameter search.

    Holds the three collaborators it orchestrates and no state between runs:
    the backtester that measures, the optimizer that chooses, and the strategy
    service that supplies the registry and the context builder. The splitter is
    injectable so a run can be reproduced later with the exact window schedule
    that produced it.
    """

    def __init__(
        self,
        backtest: BacktestService,
        strategies: StrategyService,
        settings: Settings,
        *,
        optimizer: ParameterOptimizer | None = None,
        splitter: WalkForwardSplitter | None = None,
    ) -> None:
        self._backtest = backtest
        self._strategies = strategies
        self._settings = settings
        self._optimizer = optimizer or ParameterOptimizer(backtest)
        self._default_splitter = splitter

    # ------------------------------------------------------------------

    def splitter(
        self,
        horizon: int,
        *,
        train_bars: int | None = None,
        test_bars: int | None = None,
        anchored: bool = False,
        step_bars: int | None = None,
        embargo_bars: int | None = None,
        override: WalkForwardSplitter | None = None,
    ) -> WalkForwardSplitter:
        """
        The window schedule a run will use, from settings or explicit overrides.

        The embargo defaults to ``horizon`` rather than the splitter's own zero:
        see the module docstring. A caller who deliberately wants a different
        embargo can pass one, but has to say so.
        """
        if override is not None:
            return override
        if self._default_splitter is not None:
            return self._default_splitter
        s = self._settings
        return WalkForwardSplitter(
            train_bars=(
                train_bars if train_bars is not None else s.TRADING_WF_TRAIN_BARS
            ),
            test_bars=test_bars if test_bars is not None else s.TRADING_WF_TEST_BARS,
            embargo_bars=horizon if embargo_bars is None else embargo_bars,
            anchored=anchored,
            step_bars=step_bars,
        )

    async def run(
        self,
        data: MarketData,
        strategy_id: str,
        grid: ParameterGrid,
        *,
        objective: OptimizationObjective = OptimizationObjective.DIRECTIONAL_ACCURACY,
        horizon: int | None = None,
        warmup: int | None = None,
        anchored: bool = False,
        step_bars: int | None = None,
        train_bars: int | None = None,
        test_bars: int | None = None,
        embargo_bars: int | None = None,
        splitter: WalkForwardSplitter | None = None,
        min_sample: int | None = None,
        min_folds: int | None = None,
    ) -> WalkForwardReport:
        """
        Choose on each training window, measure on the test window that follows.

        Returns a report whether or not the run was conclusive: a series too
        short for a single fold, or folds too thin to mean anything, produce a
        report whose ``is_reliable`` is False and whose limitations name the
        reason. An honest "not enough evidence" is a result here, not an error.
        """
        s = self._settings
        h = horizon if horizon is not None else s.TRADING_BACKTEST_HORIZON
        w = warmup if warmup is not None else s.TRADING_BACKTEST_WARMUP
        min_n = min_sample if min_sample is not None else s.TRADING_BACKTEST_MIN_SAMPLE
        folds_floor = min_folds if min_folds is not None else s.TRADING_WF_MIN_FOLDS

        strategy = self._strategies.registry.get(strategy_id)
        if strategy is None:
            raise StrategyError(
                f"Unknown strategy '{strategy_id}'. Registered: "
                f"{', '.join(self._strategies.registry.ids()) or 'none'}.",
                hint="Run list_strategies to see the registered strategies.",
            )

        schedule = self.splitter(
            h,
            train_bars=train_bars,
            test_bars=test_bars,
            anchored=anchored,
            step_bars=step_bars,
            embargo_bars=embargo_bars,
            override=splitter,
        )
        windows = schedule.folds(len(data.candles), warmup=w)

        logger.debug(
            "Walk-forward '%s': %d fold(s) over %d bars (train=%d test=%d embargo=%d)",
            strategy_id,
            len(windows),
            len(data.candles),
            schedule.train_bars,
            schedule.test_bars,
            schedule.embargo_bars,
        )

        folds: list[WalkForwardFold] = []
        for window in windows:
            folds.append(
                await self._run_fold(
                    strategy,
                    data,
                    window,
                    grid=grid,
                    objective=objective,
                    horizon=h,
                )
            )

        return summarise_folds(
            folds,
            instrument=data.instrument,
            timeframe=data.timeframe.value,
            horizon=h,
            warmup=w,
            embargo_bars=schedule.embargo_bars,
            objective=objective,
            quality=data.quality,
            provenance=Provenance(
                source=data.provenance.source,
                tier=SourceTier.MOCK if data.provenance.is_mock else SourceTier.DERIVED,
                detail="deterministic walk-forward parameter selection",
            ),
            min_sample=min_n,
            min_folds=folds_floor,
        )

    # ------------------------------------------------------------------

    async def _run_fold(
        self,
        strategy: TradingStrategy,
        data: MarketData,
        window: FoldWindow,
        *,
        grid: ParameterGrid,
        objective: OptimizationObjective,
        horizon: int,
    ) -> WalkForwardFold:
        """
        Fit on one fold's train window, then score the fit on its test window.

        The train and test slices come from :meth:`MarketData.window`, so neither
        can extend past the fold by accident. Both runs use ``warmup=0``: the
        fold's window *is* the trusted history, and a bar the strategy cannot yet
        analyse makes no call rather than raising, which the backtester already
        reads as "did not trade".
        """
        train = data.window(window.train_start, window.train_end)
        test = data.window(window.test_start, window.test_end)

        limitations: list[str] = []
        search = await self._optimizer.search(
            strategy,
            train,
            self._strategies.build_context,
            grid,
            objective=objective,
            horizon=horizon,
            warmup=0,
        )

        selection: tuple[tuple[str, Any], ...] = ()
        if search.best is not None:
            selection = search.best.parameters
        else:
            # A fold that could not be tuned keeps the strategy's configured
            # parameters and says so. Dropping the fold would hide a strategy the
            # system cannot tune; keeping the in-sample winner would be exactly
            # the overfit the split exists to prevent.
            limitations.append(
                f"Fold {window.index}: no parameter combination was reliable, so "
                "the strategy's configured parameters were carried forward and "
                "the fold selected nothing."
            )
        limitations.extend(search.limitations)

        variant = strategy.with_parameters(**dict(selection)) if selection else strategy
        signal = strategy_signal(variant, self._strategies.build_context)

        in_sample = await self._backtest.run(train, signal, horizon=horizon, warmup=0)
        measured = await self._backtest.run(test, signal, horizon=horizon, warmup=0)

        out_of_sample: BacktestResult | None = measured
        if measured.evaluated == 0:
            # The test window produced no scoreable bar at all -- the strategy
            # could not analyse it, or the data was unusable. That is an
            # *unevaluated* fold, and counting it as one would let a run of empty
            # folds clear the "enough folds" gate without measuring anything.
            limitations.append(
                f"Fold {window.index}: the test window produced no scoreable bar, "
                "so the fold has no out-of-sample measurement."
            )
            out_of_sample = None

        if in_sample.directional_calls == 0:
            limitations.append(
                f"Fold {window.index}: the training window produced no directional "
                "calls, so the in-sample figure is not a selection signal."
            )

        return WalkForwardFold(
            window=window,
            selection=selection,
            in_sample=in_sample,
            out_of_sample=out_of_sample,
            limitations=tuple(limitations),
        )
