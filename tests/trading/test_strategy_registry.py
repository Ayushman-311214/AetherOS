"""
Strategy registry and parameter grid.

The registry is the single place a strategy is *named*, so these tests pin the
things that would make a result ambiguous: a duplicate id, an unnamed strategy,
a lookup that silently returns nothing. The grid is the explicit, finite search
space the optimizer enumerates -- a dropped or duplicated axis would make a
search report on a space it never explored, so the product is asserted exactly.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import StrategyCategory
from aetheros.trading.strategies.base import RuleBasedStrategy
from aetheros.trading.strategies.breakout import BreakoutStrategy
from aetheros.trading.strategies.ict import ICTStrategy
from aetheros.trading.strategies.mean_reversion import MeanReversionStrategy
from aetheros.trading.strategies.optimization import ParameterGrid
from aetheros.trading.strategies.registry import StrategyRegistry, default_registry
from aetheros.trading.strategies.smc import SMCStrategy
from aetheros.trading.strategies.trend_following import TrendFollowingStrategy

EXPECTED_IDS = ("breakout", "ict", "mean_reversion", "smc", "trend_following")


class _Nameless(RuleBasedStrategy):
    """A strategy that declares no id/name/description -- the registry must refuse it."""

    strategy_id = ""
    name = ""
    description = ""

    def rules(self, context):  # pragma: no cover - never evaluated
        return ()

    def build(self, context, rules):  # pragma: no cover - never evaluated
        return None


class _NoName(TrendFollowingStrategy):
    name = ""


class _NoDescription(TrendFollowingStrategy):
    description = ""


# ----------------------------------------------------------------------
# Registry


def test_default_registry_holds_the_five_built_in_strategies():
    registry = default_registry()
    assert registry.ids() == EXPECTED_IDS
    assert len(registry) == 5
    assert [strategy.strategy_id for strategy in registry] == list(EXPECTED_IDS)


def test_default_registry_is_a_factory_not_a_singleton():
    first = default_registry()
    first.unregister("ict")
    assert default_registry().get("ict") is not None


def test_registry_lookup_is_case_insensitive():
    registry = default_registry()
    assert registry.get(" SMC ") is not None
    assert "ICT" in registry


def test_get_returns_none_for_an_unknown_id_but_require_raises():
    registry = default_registry()
    assert registry.get("nope") is None
    with pytest.raises(ValueError, match="Unknown strategy 'nope'") as excinfo:
        registry.require("nope")
    # The message names what *is* registered, so the caller can correct itself.
    assert "trend_following" in str(excinfo.value)


def test_register_rejects_a_duplicate_id():
    registry = StrategyRegistry((TrendFollowingStrategy(),))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(TrendFollowingStrategy())


def test_register_rejects_a_strategy_with_no_id_name_or_description():
    registry = StrategyRegistry()
    with pytest.raises(ValueError, match="non-empty strategy_id"):
        registry.register(_Nameless())
    with pytest.raises(ValueError, match="must declare a name"):
        registry.register(_NoName())
    with pytest.raises(ValueError, match="must declare a description"):
        registry.register(_NoDescription())


def test_unregister_is_idempotent():
    registry = default_registry()
    registry.unregister("smc")
    registry.unregister("smc")
    assert registry.get("smc") is None


def test_by_category_filters_in_id_order():
    registry = default_registry()
    assert [s.strategy_id for s in registry.by_category(StrategyCategory.ICT)] == ["ict"]
    assert registry.by_category(StrategyCategory.CUSTOM) == ()


def test_registry_accepts_a_caller_supplied_strategy():
    registry = StrategyRegistry()
    registry.register(SMCStrategy())
    assert registry.ids() == ("smc",)


# ----------------------------------------------------------------------
# Parameter grid


def test_grid_enumerates_the_cartesian_product_in_declaration_order():
    grid = ParameterGrid.from_dict({"a": (1, 2), "b": (10,)})
    assert grid.names == ("a", "b")
    assert grid.size() == 2
    assert grid.combinations() == (
        (("a", 1), ("b", 10)),
        (("a", 2), ("b", 10)),
    )


def test_grid_of_one_axis_is_that_axis():
    grid = ParameterGrid.from_dict({"min_adx": (15.0, 20.0, 25.0)})
    assert grid.size() == 3
    assert [dict(combo) for combo in grid.combinations()] == [
        {"min_adx": 15.0},
        {"min_adx": 20.0},
        {"min_adx": 25.0},
    ]


def test_grid_with_no_axes_is_a_single_empty_combination():
    """An empty grid means "evaluate the strategy as configured", not "nothing"."""
    grid = ParameterGrid(axes=())
    assert grid.size() == 1
    assert grid.combinations() == ((),)


def test_grid_rejects_an_axis_with_no_values():
    with pytest.raises(ValueError, match="has no values to try"):
        ParameterGrid.from_dict({"min_adx": ()})


def test_grid_rejects_duplicate_or_blank_axis_names():
    with pytest.raises(ValueError, match="must be unique"):
        ParameterGrid(axes=(("a", (1,)), ("a", (2,))))
    with pytest.raises(ValueError, match="must have a name"):
        ParameterGrid(axes=(("  ", (1,)),))


def test_grid_serialises_its_axes_and_size():
    payload = ParameterGrid.from_dict({"a": (1, 2), "b": (3,)}).to_dict()
    assert payload == {"axes": {"a": [1, 2], "b": [3]}, "size": 2}


# ----------------------------------------------------------------------
# Strategy metadata


def test_built_in_strategies_declare_distinct_ids_and_categories():
    strategies = [
        TrendFollowingStrategy(),
        MeanReversionStrategy(),
        BreakoutStrategy(),
        SMCStrategy(),
        ICTStrategy(),
    ]
    ids = [strategy.strategy_id for strategy in strategies]
    assert len(ids) == len(set(ids))
    assert [strategy.category for strategy in strategies] == [
        StrategyCategory.TREND_FOLLOWING,
        StrategyCategory.MEAN_REVERSION,
        StrategyCategory.BREAKOUT,
        StrategyCategory.SMC,
        StrategyCategory.ICT,
    ]
    for strategy in strategies:
        assert strategy.name.strip()
        assert strategy.description.strip()


def test_parameters_are_the_thresholds_the_strategy_actually_applies():
    """Parameters must be tunable thresholds, never indicator periods.

    The technical snapshot is computed with the system's configured periods, so
    a strategy exposing ``sma_period`` would be reporting a parameter it never
    applied. Every declared parameter is therefore a threshold or a tolerance.
    """
    forbidden = {"sma_period", "ema_period", "rsi_period", "atr_period", "lookback"}
    for strategy in default_registry():
        names = {name for name, _ in strategy.parameters}
        assert not (names & forbidden), f"{strategy.strategy_id} exposes {names & forbidden}"


def test_with_parameters_copies_and_rejects_unknown_names():
    strategy = TrendFollowingStrategy()
    tuned = strategy.with_parameters(min_adx=30.0)
    assert tuned.min_adx == 30.0
    assert strategy.min_adx == 20.0  # the original is untouched (frozen)
    with pytest.raises(ValueError, match="Unknown parameter"):
        strategy.with_parameters(nonsense=1.0)


def test_with_parameters_enforces_the_strategy_s_own_validation():
    with pytest.raises(ValueError, match="max_extension_atr must be positive"):
        BreakoutStrategy().with_parameters(max_extension_atr=-1.0)
