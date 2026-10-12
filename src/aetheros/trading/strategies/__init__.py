"""
The strategy engine (spec Phase 7).

Strategies *interpret* reads that already exist -- analysis, structure, SMC, ICT,
breakout -- into an auditable directional setup. They fetch no data, compute no
indicators, detect no structure, and place no stop, target or size; that
geometry belongs to the risk engine. The boundary is what keeps a strategy a
statement about the market rather than a second, quietly competing execution
path.

The package holds five things:

- :class:`StrategyContext` -- the shared read every strategy in a comparison
  interprets, so a disagreement is about reading, not about inputs.
- :class:`TradingStrategy` / :class:`RuleBasedStrategy` -- the contract, and the
  rules-plus-builder implementation of it that the five built-ins use.
- The five built-in strategies: :class:`TrendFollowingStrategy`,
  :class:`MeanReversionStrategy`, :class:`BreakoutStrategy`,
  :class:`SMCStrategy`, :class:`ICTStrategy`.
- :class:`StrategyRegistry` / :func:`default_registry` -- "build strategies" and
  "load strategies": a strategy is named in exactly one place.
- :class:`ParameterOptimizer` -- "optimize parameters": a deterministic grid
  search scored by the *existing* walk-forward backtester, so a parameter set
  can never be selected by rules the deployed engine would not apply.

Comparing strategies lives one level up, in
:class:`~aetheros.trading.services.strategy_service.StrategyService`, because it
needs the reads this package deliberately does not fetch.
"""

from __future__ import annotations

from .base import (
    CONFIDENCE_WEIGHTS,
    STRONG_CLAIM_WEIGHT,
    SUPPORTING_WEIGHT,
    WEAK_CLAIM_WEIGHT,
    RuleBasedStrategy,
    TradingStrategy,
)
from .breakout import BreakoutStrategy
from .context import StrategyContext
from .ict import ICTStrategy
from .levels import (
    STRUCTURAL,
    VOLATILITY,
    atr_level,
    invalidation_source,
    nearest_swing_level,
    structural_invalidation,
)
from .mean_reversion import MeanReversionStrategy
from .optimization import ContextBuilder, ParameterGrid, ParameterOptimizer
from .registry import StrategyRegistry, default_registry
from .smc import SMCStrategy
from .trend_following import TrendFollowingStrategy

__all__ = [
    "CONFIDENCE_WEIGHTS",
    "STRONG_CLAIM_WEIGHT",
    "STRUCTURAL",
    "SUPPORTING_WEIGHT",
    "VOLATILITY",
    "WEAK_CLAIM_WEIGHT",
    "BreakoutStrategy",
    "ContextBuilder",
    "ICTStrategy",
    "MeanReversionStrategy",
    "ParameterGrid",
    "ParameterOptimizer",
    "RuleBasedStrategy",
    "SMCStrategy",
    "StrategyContext",
    "StrategyRegistry",
    "TradingStrategy",
    "TrendFollowingStrategy",
    "atr_level",
    "default_registry",
    "invalidation_source",
    "nearest_swing_level",
    "structural_invalidation",
]
