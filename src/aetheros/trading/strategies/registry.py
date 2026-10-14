"""
Strategy registry -- "build strategies" and "load strategies" (spec Phase 7).

The registry is the single place a strategy is named, so the rest of the system
never hard-codes a strategy class. The service looks strategies up by id, the
comparison layer enumerates whatever is registered, and a caller may register
their own without touching any of the built-in modules -- the same extension
shape as :class:`~aetheros.trading.indicators.registry.IndicatorRegistry`.

Registered strategies are held as *instances*, not classes, because a strategy's
parameters are part of what it is: "the breakout strategy requiring volume
confirmation" and "the breakout strategy that does not" are two different
readings, and the optimizer relies on being able to register and evaluate them
side by side.

Strategies are stateless, so one instance is safely shared. The registry still
returns them by id rather than mutating anything, and a duplicate id is rejected
rather than silently overwriting -- two strategies answering to one name would
make every result that names an id ambiguous.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..domain.enums import StrategyCategory
from .base import TradingStrategy
from .breakout import BreakoutStrategy
from .ict import ICTStrategy
from .mean_reversion import MeanReversionStrategy
from .smc import SMCStrategy
from .trend_following import TrendFollowingStrategy


class StrategyRegistry:
    """Strategy id -> strategy instance, with duplicate-id protection."""

    def __init__(self, strategies: tuple[TradingStrategy, ...] = ()) -> None:
        self._strategies: dict[str, TradingStrategy] = {}
        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy: TradingStrategy) -> None:
        """Add ``strategy`` under its own id."""
        key = strategy.strategy_id.strip().lower()
        if not key:
            raise ValueError("A strategy must declare a non-empty strategy_id.")
        if not strategy.name.strip():
            raise ValueError(f"Strategy '{key}' must declare a name.")
        if not strategy.description.strip():
            raise ValueError(f"Strategy '{key}' must declare a description.")
        if key in self._strategies:
            raise ValueError(
                f"Strategy '{key}' is already registered. Unregister it first."
            )
        self._strategies[key] = strategy

    def unregister(self, strategy_id: str) -> None:
        """Remove a strategy; absent ids are ignored, like ``dict.pop``."""
        self._strategies.pop(strategy_id.strip().lower(), None)

    def get(self, strategy_id: str) -> TradingStrategy | None:
        """The strategy with this id, or None."""
        return self._strategies.get(strategy_id.strip().lower())

    def require(self, strategy_id: str) -> TradingStrategy:
        """
        The strategy with this id, or a ValueError naming what is registered.

        Used where a missing strategy is a caller error rather than an expected
        absence -- an optimizer asked to tune a strategy that does not exist
        should say so, not return an empty search.
        """
        strategy = self.get(strategy_id)
        if strategy is None:
            raise ValueError(
                f"Unknown strategy '{strategy_id}'. Registered: "
                f"{', '.join(self.ids()) or 'none'}."
            )
        return strategy

    def ids(self) -> tuple[str, ...]:
        """Registered ids, sorted."""
        return tuple(sorted(self._strategies))

    def all(self) -> tuple[TradingStrategy, ...]:
        """Every registered strategy, in id order."""
        return tuple(self._strategies[key] for key in sorted(self._strategies))

    def by_category(self, category: StrategyCategory) -> tuple[TradingStrategy, ...]:
        """Every registered strategy in one category, in id order."""
        return tuple(
            strategy for strategy in self.all() if strategy.category is category
        )

    def clear(self) -> None:
        self._strategies.clear()

    def __contains__(self, strategy_id: str) -> bool:
        return strategy_id.strip().lower() in self._strategies

    def __len__(self) -> int:
        return len(self._strategies)

    def __iter__(self) -> Iterator[TradingStrategy]:
        return iter(self.all())


def default_registry() -> StrategyRegistry:
    """
    A registry holding the strategies defined in this package.

    One instance per call, so a caller may register, unregister or reconfigure
    without affecting any other caller -- the module deliberately exposes a
    factory rather than a singleton, because unlike indicators there is no
    single process-wide interpretation that would make a shared instance
    meaningful.
    """
    return StrategyRegistry(
        (
            TrendFollowingStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
            SMCStrategy(),
            ICTStrategy(),
        )
    )
