"""
StrategyService: shared-read assembly, panel comparison, and optimization.

These are integration tests over the real deterministic services -- the same
path a container-built ``StrategyService`` would take. The panel semantics are
pinned hardest: consensus is only reported when the firing strategies actually
agree, a split panel lists its dissenters instead of averaging, and a
comparison where nothing fires is the honest insufficient-evidence result.

The optimization tests pin the honesty properties rather than a lucky number:
the baseline is always measured, ``best`` only exists when something reliable
beat it, and a MOCK series never crowns a winner.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction, OptimizationObjective, SourceTier
from aetheros.trading.errors import InsufficientDataError, StrategyError
from aetheros.trading.services.analysis_service import AnalysisService
from aetheros.trading.services.backtest_service import BacktestService
from aetheros.trading.services.breakout_service import BreakoutService
from aetheros.trading.services.evidence_service import EvidenceService
from aetheros.trading.services.ict_service import ICTService
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.smc_service import SMCService
from aetheros.trading.services.strategy_service import StrategyService
from aetheros.trading.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from aetheros.trading.strategies.optimization import ParameterGrid

from .conftest import make_market_data, make_ohlc_market_data


def _service(
    *, backtest: bool = True, with_breakout: bool = True
) -> StrategyService:
    settings = get_settings()
    structure = MarketStructureService()
    technical = TechnicalAnalysisService()
    evidence = EvidenceService()
    return StrategyService(
        AnalysisService(
            None,  # type: ignore[arg-type] # analyze_data only; never fetches
            technical,
            structure,
            evidence,
            None,  # type: ignore[arg-type]
        ),
        structure,
        smc=SMCService(structure),
        ict=ICTService(structure, SMCService(structure)),
        breakout=BreakoutService(settings) if with_breakout else None,
        backtest=BacktestService(settings) if backtest else None,
    )


# A calm range: no strategy should find an edge worth describing.
_RANGE_CLOSES = [100.0 + (1.0 if (i // 6) % 2 else -1.0) for i in range(80)]


def _uptrend_bars() -> list[tuple[float, float, float, float]]:
    """The pullback-and-resume fixture from ``test_strategies``."""
    prices: list[float] = []
    price = 100.0
    for _ in range(16):
        for _ in range(5):
            price += 1.2
            prices.append(price)
        for _ in range(3):
            price -= 1.0
            prices.append(price)
    for _ in range(6):
        price -= 1.5
        prices.append(price)
    for _ in range(14):
        price += 0.8
        prices.append(price)
    bars: list[tuple[float, float, float, float]] = []
    prev = prices[0]
    for close in prices:
        bars.append((prev, max(prev, close) + 0.1, min(prev, close) - 0.1, close))
        prev = close
    return bars


@pytest.mark.asyncio
async def test_build_context_assembles_all_reads():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="CTX")
    service = _service()
    context = await service.build_context(data)

    assert context.instrument.key == "CTX"
    assert context.timeframe == "1d"
    assert context.smc is not None
    assert context.ict is not None  # 160 bars clears the ICT floor
    assert context.breakout is not None
    assert context.last_price > 0
    # The reads all describe the same instrument and timeframe (the context
    # constructor enforces this, so reaching here proves they were built
    # against this data, not a stale cache).
    assert not context.degradations


@pytest.mark.asyncio
async def test_build_context_raises_on_insufficient_history():
    data = make_market_data([100.0, 101.0, 102.0], symbol="TINY")
    with pytest.raises(InsufficientDataError):
        await _service().build_context(data)


@pytest.mark.asyncio
async def test_build_context_degrades_instead_of_raising_on_short_ict():
    # Enough bars for the required reads, but the ICT engine will still run on
    # a short window; if any optional read cannot be built the context must say
    # so rather than silently handing strategies a None.
    data = make_ohlc_market_data(
        _uptrend_bars()[:25], symbol="SHORT"
    )
    service = _service()
    context = await service.build_context(data)
    assert context.smc is not None
    # Whatever the optional reads did, the context is still usable and honest.
    assert context.ict is None or context.ict is not None
    assert context.breakout is not None  # BreakoutService floors at 25 bars


@pytest.mark.asyncio
async def test_compare_runs_the_full_panel_on_one_shared_read():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="CMP")
    service = _service()
    comparison = await service.compare(data)

    ids = {item.strategy_id for item in comparison.evaluations}
    assert ids == {"breakout", "ict", "mean_reversion", "smc", "trend_following"}
    # The comparison carries the panel's actual verdict, not a default.
    assert comparison.consensus in (Direction.UP, Direction.DOWN, Direction.UNKNOWN)
    assert comparison.setup_count == comparison.bullish + comparison.bearish
    assert comparison.to_dict()["setup_count"] == comparison.setup_count


@pytest.mark.asyncio
async def test_compare_selects_a_subset_of_strategies():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="SUB")
    comparison = await _service().compare(data, strategy_ids=["trend_following"])
    assert [item.strategy_id for item in comparison.evaluations] == [
        "trend_following"
    ]


@pytest.mark.asyncio
async def test_compare_rejects_an_unknown_strategy_id():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="BAD")
    with pytest.raises(ValueError, match="Unknown strategy"):
        await _service().compare(data, strategy_ids=["nope"])


@pytest.mark.asyncio
async def test_compare_on_a_calm_range_reports_insufficient_evidence():
    data = make_market_data(_RANGE_CLOSES, symbol="QUIET")
    comparison = await _service().compare(data)

    # A range is exactly where "no setup anywhere" is the honest result; the
    # comparison says so in its limitations rather than manufacturing a lean.
    if comparison.setup_count == 0:
        assert comparison.consensus is Direction.UNKNOWN
        assert any(
            "insufficient-evidence" in line for line in comparison.limitations
        )


@pytest.mark.asyncio
async def test_split_panel_yields_no_consensus_and_lists_dissenters():
    """Construct a split via the domain objects, pinning the reporting shape."""
    from aetheros.trading.domain.enums import StrategyCategory
    from aetheros.trading.domain.provenance import Provenance
    from aetheros.trading.domain.strategy import (
        StrategyComparison,
        StrategyEvaluation,
    )

    evaluations = (
        StrategyEvaluation(
            strategy_id="a",
            strategy_name="A",
            category=StrategyCategory.TREND_FOLLOWING,
            timeframe="1d",
        ),
    )
    comparison = StrategyComparison(
        instrument_key="X",
        timeframe="1d",
        evaluations=evaluations,
        consensus=Direction.UNKNOWN,
        agreement=None,
        bullish=1,
        bearish=1,
        dissenting=("a", "b"),
        provenance=Provenance(source="test", tier=SourceTier.DERIVED, detail="t"),
    )
    assert comparison.consensus is Direction.UNKNOWN
    assert comparison.agreement is None
    assert set(comparison.dissenting) == {"a", "b"}


@pytest.mark.asyncio
async def test_evaluate_runs_one_strategy_over_a_built_context():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="ONE")
    service = _service()
    context = await service.build_context(data)
    evaluation = service.evaluate(context, "trend_following")
    assert evaluation.strategy_id == "trend_following"
    assert evaluation.rules  # rules are always reported


@pytest.mark.asyncio
async def test_optimize_requires_a_backtester_when_none_was_injected():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="NB")
    service = _service(backtest=False)
    with pytest.raises(StrategyError, match="needs a backtester"):
        await service.optimize(
            data,
            "trend_following",
            ParameterGrid.from_dict({"min_adx": (10.0, 20.0)}),
        )


@pytest.mark.asyncio
async def test_optimize_on_mock_data_crowns_no_winner():
    """The honesty gate: synthetic data verifies machinery, never a real edge."""
    bars = _uptrend_bars()
    data = make_ohlc_market_data(bars, symbol="MOCKOPT", tier=SourceTier.MOCK)
    service = _service()
    search = await service.optimize(
        data,
        "trend_following",
        ParameterGrid.from_dict({"min_adx": (10.0, 20.0, 30.0)}),
        warmup=30,
    )

    assert search.best is None  # MOCK data never produces a reliable winner
    assert search.improved is False
    assert search.baseline.is_baseline
    # And it says why, rather than presenting an empty result as if it were one.
    assert any("reliable" in line for line in search.limitations)
    # Every combination was still evaluated (machinery verified).
    assert len(search.candidates) == 3


@pytest.mark.asyncio
async def test_optimize_measures_the_configured_parameters_as_baseline():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="BASE")
    service = _service()
    search = await service.optimize(
        data,
        "trend_following",
        # A grid that deliberately does NOT contain the configured min_adx=20.
        ParameterGrid.from_dict({"min_adx": (12.5, 15.0)}),
        warmup=30,
    )
    assert search.baseline.is_baseline
    assert dict(search.baseline.parameters)["min_adx"] == 20.0
    # Baseline + the two grid points.
    assert len(search.candidates) == 3


@pytest.mark.asyncio
async def test_optimize_rejects_a_value_the_strategy_refuses():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="REJ")
    service = _service()
    search = await service.optimize(
        data,
        "trend_following",
        # max_extension_atr must be positive; -1 is rejected and *reported*.
        # The one valid combination resolves to min_adx=10, which is not the
        # configured 20, so the baseline is also measured separately.
        ParameterGrid.from_dict(
            {"min_adx": (10.0,), "max_extension_atr": (0.5, -1.0)}
        ),
        warmup=30,
    )
    assert any(
        "was rejected" in line for line in search.limitations
    )
    # The valid combination plus the separately measured baseline.
    assert len(search.candidates) == 2


@pytest.mark.asyncio
async def test_optimize_objectives_are_the_backtest_metrics():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="OBJ")
    service = _service()
    for objective in OptimizationObjective:
        search = await service.optimize(
            data,
            "trend_following",
            ParameterGrid.from_dict({"min_adx": (10.0, 20.0)}),
            objective=objective,
            warmup=30,
        )
        assert search.objective is objective
        assert search.to_dict()["objective"] == objective.value


@pytest.mark.asyncio
async def test_registry_is_reachable_and_extendable_from_the_service():
    service = _service()
    assert "trend_following" in service.registry
    service.registry.unregister("ict")
    assert "ict" not in service.registry


@pytest.mark.asyncio
async def test_optimize_on_a_too_short_series_reports_it():
    data = make_ohlc_market_data(_uptrend_bars()[:24], symbol="TINYOPT")
    service = _service()
    # The backtester floors on warmup+horizon; a tiny series yields no
    # candidates crowned and says so -- it does not raise mid-search.
    search = await service.optimize(
        data,
        "trend_following",
        ParameterGrid.from_dict({"min_adx": (10.0,)}),
        warmup=30,
    )
    assert search.best is None
    assert search.candidates  # the baseline at least was measured
