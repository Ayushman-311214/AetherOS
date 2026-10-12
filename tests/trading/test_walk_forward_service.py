"""
WalkForwardService: re-choosing parameters on each fold, then measuring them.

These are integration tests over the real deterministic services -- the same path
a container-built ``WalkForwardService`` takes. What they pin is the structure of
a walk-forward run rather than a lucky number:

- each fold's training window genuinely ends before its test window begins, by
  exactly the embargo, so no training bar's forward label reaches the test data;
- the pooled out-of-sample statistics are the concatenation of the folds' own
  trades, in time order -- not an average of per-fold figures;
- the in-sample number is recorded beside the out-of-sample one instead of
  standing in for it;
- a series too short for a fold, or a MOCK series, yields a report that says so
  and is not reliable.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import OptimizationObjective, SourceTier
from aetheros.trading.errors import StrategyError
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
from aetheros.trading.services.walk_forward_service import WalkForwardService
from aetheros.trading.strategies.optimization import ParameterGrid

from .conftest import make_market_data, make_ohlc_market_data

# One strategy, one grid point (the configured default) -- these tests are about
# the fold machinery, so the search is kept to the single cheapest honest call.
_GRID = ParameterGrid.from_dict({"min_adx": (20.0,)})

# 160 bars, so train(50) + embargo(1) + test(40) fits twice from a 20-bar warmup.
_TRAIN_BARS = 50
_TEST_BARS = 40
_WARMUP = 20


def _service() -> WalkForwardService:
    settings = get_settings()
    structure = MarketStructureService()
    strategies = StrategyService(
        AnalysisService(
            None,  # type: ignore[arg-type] # analyze_data only; never fetches
            TechnicalAnalysisService(),
            structure,
            EvidenceService(),
            None,  # type: ignore[arg-type]
        ),
        structure,
        smc=SMCService(structure),
        ict=ICTService(structure, SMCService(structure)),
        breakout=BreakoutService(settings),
        backtest=BacktestService(settings),
    )
    return WalkForwardService(BacktestService(settings), strategies, settings)


def _uptrend_bars() -> list[tuple[float, float, float, float]]:
    """The pullback-and-resume fixture the strategy tests rely on."""
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
    # The final upswing must carry the series to the documented 160 bars: the
    # runs above reach 134, so this leg adds 26. Two non-anchored folds need
    # warmup(20) + 2*step(40) + train(50) + embargo(1) + test(40) = 151, so 160
    # leaves fold 1's test window ending at bar 151 with room to spare.
    for _ in range(26):
        price += 0.8
        prices.append(price)
    bars: list[tuple[float, float, float, float]] = []
    prev = prices[0]
    for close in prices:
        bars.append((prev, max(prev, close) + 0.1, min(prev, close) - 0.1, close))
        prev = close
    return bars


async def _run(data, **overrides):
    return await _service().run(
        data,
        "trend_following",
        _GRID,
        horizon=1,
        warmup=_WARMUP,
        train_bars=_TRAIN_BARS,
        test_bars=_TEST_BARS,
        **overrides,
    )


# ----------------------------------------------------------------------
# the fold schedule
# ----------------------------------------------------------------------


def test_the_default_embargo_is_the_horizon():
    # A training bar's label is the return `horizon` bars ahead, so anything less
    # than the horizon leaks into the test window.
    service = _service()
    assert service.splitter(1).embargo_bars == 1
    assert service.splitter(5).embargo_bars == 5
    # ...unless the caller deliberately asks for something else.
    assert service.splitter(5, embargo_bars=0).embargo_bars == 0


def test_the_splitter_falls_back_to_the_configured_window_sizes():
    splitter = _service().splitter(1)
    settings = get_settings()
    assert splitter.train_bars == settings.TRADING_WF_TRAIN_BARS
    assert splitter.test_bars == settings.TRADING_WF_TEST_BARS


def test_the_splitters_window_sizes_can_be_overridden_per_run():
    splitter = _service().splitter(3, train_bars=80, test_bars=30, anchored=True)
    assert (splitter.train_bars, splitter.test_bars, splitter.anchored) == (
        80,
        30,
        True,
    )
    assert splitter.embargo_bars == 3


# ----------------------------------------------------------------------
# a real run
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_each_fold_train_window_ends_before_its_test_window_begins():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="WF")
    report = await _run(data)

    assert len(report.folds) == 2
    assert report.embargo_bars == 1
    for fold in report.folds:
        window = fold.window
        # The whole point of the split: the test data was never trained on, and
        # the embargo is exactly the horizon that would otherwise bridge them.
        assert window.test_start == window.train_end + report.embargo_bars
        assert window.test_end <= data.count
        assert window.train_start >= _WARMUP


@pytest.mark.asyncio
async def test_the_pooled_statistics_are_the_folds_concatenated():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="POOL")
    report = await _run(data)

    measured = [f for f in report.folds if f.out_of_sample is not None]
    assert measured, "the fixture should produce at least one measurable fold"

    pooled_returns = [
        r for fold in measured for r in fold.out_of_sample.returns  # type: ignore[union-attr]
    ]
    if report.oos_statistics is None:
        # No fold traded, so there is no sample -- and no statistics invented
        # for one. The two are the same statement, asserted together.
        assert pooled_returns == []
    else:
        assert report.oos_statistics.trades == len(pooled_returns)
        assert report.oos_statistics.trades == sum(
            fold.out_of_sample.statistics.trades  # type: ignore[union-attr]
            for fold in measured
            if fold.out_of_sample.statistics is not None  # type: ignore[union-attr]
        )
    assert report.oos_directional_calls == sum(
        fold.out_of_sample.directional_calls for fold in measured  # type: ignore[union-attr]
    )


@pytest.mark.asyncio
async def test_the_in_sample_number_is_kept_apart_from_the_out_of_sample_one():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="GAP")
    report = await _run(data)

    for fold in report.folds:
        # An in-sample figure is a selection artefact; recording it lets the gap
        # be seen rather than letting it masquerade as performance.
        assert fold.in_sample is not None
    if report.generalisation_gap is not None:
        assert report.generalisation_gap == pytest.approx(
            report.in_sample_accuracy_mean - report.oos_directional_accuracy
        )


@pytest.mark.asyncio
async def test_a_fold_records_what_it_selected_and_why():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="SEL")
    report = await _run(data)

    for fold in report.folds:
        # Either the grid point was accepted (and it *is* the configured
        # default, so the selection is that parameter) or nothing was reliable
        # and the fold says so. There is no silent third case.
        assert fold.selection == (("min_adx", 20.0),) or any(
            "carried forward" in line for line in fold.limitations
        )


@pytest.mark.asyncio
async def test_the_report_serialises_its_folds():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="SER")
    report = await _run(data)
    payload = report.to_dict()

    assert payload["objective"] == OptimizationObjective.DIRECTIONAL_ACCURACY.value
    assert payload["embargo_bars"] == 1
    assert len(payload["folds"]) == len(report.folds)
    assert payload["folds"][0]["window"]["train_end"] <= payload["folds"][0]["window"][
        "test_start"
    ]
    assert isinstance(payload["limitations"], list)


# ----------------------------------------------------------------------
# the honest refusals
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_series_too_short_for_a_fold_reports_no_folds():
    data = make_market_data([100.0 + i for i in range(40)], symbol="SHORT")
    report = await _run(data)

    assert report.folds == ()
    assert report.is_reliable is False
    assert report.oos_statistics is None
    assert any("No fold fitted the series" in line for line in report.limitations)


@pytest.mark.asyncio
async def test_mock_data_never_produces_a_reliable_report():
    data = make_ohlc_market_data(
        _uptrend_bars(), symbol="MOCKWF", tier=SourceTier.MOCK
    )
    report = await _run(data)

    assert report.is_reliable is False
    assert any("MOCK" in line for line in report.limitations)
    # The search crowns no winner on synthetic data, so every fold carries the
    # configured parameters forward and says so.
    assert all(fold.selection == () for fold in report.folds)


@pytest.mark.asyncio
async def test_an_unknown_strategy_is_rejected_with_the_registered_list():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="BADWF")
    with pytest.raises(StrategyError, match="Unknown strategy"):
        await _service().run(data, "does_not_exist", _GRID)


@pytest.mark.asyncio
async def test_an_anchored_schedule_grows_the_training_window():
    data = make_ohlc_market_data(_uptrend_bars(), symbol="ANCH")
    report = await _run(data, anchored=True)

    assert report.folds, "the fixture should fit at least one anchored fold"
    starts = {fold.window.train_start for fold in report.folds}
    ends = [fold.window.train_end for fold in report.folds]
    assert starts == {_WARMUP}
    assert ends == sorted(ends) and len(set(ends)) == len(ends)
