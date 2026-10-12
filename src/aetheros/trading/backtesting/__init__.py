"""
The backtesting engine (spec Phase 13).

Four responsibilities, and this package holds the three that are pure:

- **Historical testing** -- :class:`~aetheros.trading.services.backtest_service.BacktestService`,
  which already existed and is where a signal is scored bar by bar.
- **Performance metrics** -- :mod:`~aetheros.trading.backtesting.metrics`:
  Win Rate, Profit Factor, Sharpe, Max Drawdown, Expectancy, defined once.
- **Walk-forward testing** -- :mod:`~aetheros.trading.backtesting.walk_forward`:
  the splitter and the pooling of out-of-sample folds.
- **Strategy comparison** -- :mod:`~aetheros.trading.backtesting.comparison`:
  ranking several backtests of one question.

Everything here is a pure function or a frozen value object over already-loaded
bars: no I/O, no LLM, no provider, and -- deliberately -- no import of
``services`` or ``strategies``. Orchestration lives in
``services/walk_forward_service.py``, because a service importing this package
while this package imported that service would be a cycle, and keeping the
arithmetic independent of its caller is worth more than the import it saves.
"""

from __future__ import annotations

from . import comparison, metrics, walk_forward
from .comparison import (
    COMPARABLE_METRICS,
    DEFAULT_COMPARISON_METRIC,
    compare_backtests,
    metric_value,
)
from .metrics import (
    directional_returns,
    max_drawdown,
    sharpe_ratio,
    trade_statistics,
)
from .walk_forward import (
    DEFAULT_MIN_FOLDS,
    WalkForwardSplitter,
    pool_out_of_sample_returns,
    selection_stability,
    summarise_folds,
)

__all__ = [
    "COMPARABLE_METRICS",
    "DEFAULT_COMPARISON_METRIC",
    "DEFAULT_MIN_FOLDS",
    "WalkForwardSplitter",
    "comparison",
    "compare_backtests",
    "directional_returns",
    "max_drawdown",
    "metric_value",
    "metrics",
    "pool_out_of_sample_returns",
    "selection_stability",
    "sharpe_ratio",
    "summarise_folds",
    "trade_statistics",
    "walk_forward",
]
