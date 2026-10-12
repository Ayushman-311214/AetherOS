"""
Walk-forward splitter and pooling tests (spec Phase 13, "walk-forward testing").

Two things are being pinned here, and they are different in kind:

- **the window arithmetic** -- exactly which bars land in which fold, for both a
  rolling and an anchored schedule, and that the embargo really does hold the
  training window back from the test window. A splitter that is off by one bar
  leaks, and leaks silently.
- **the honesty of the report** -- that a run with too few folds, synthetic data
  or too thin a sample says so and is not reliable, and that pooling
  concatenates the folds' trades in time order instead of averaging per-fold
  figures (which would get a path-dependent drawdown wrong).
"""

from __future__ import annotations

import pytest

from aetheros.trading.backtesting.walk_forward import (
    WalkForwardSplitter,
    pool_out_of_sample_returns,
    selection_stability,
    summarise_folds,
)
from aetheros.trading.domain.backtest import FoldWindow, WalkForwardFold
from aetheros.trading.domain.enums import (
    DataQualityStatus,
    OptimizationObjective,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.provenance import DataQuality, Provenance

from .conftest import make_backtest_result, make_market_data


# ----------------------------------------------------------------------
# builders
# ----------------------------------------------------------------------


def _fold(
    index: int,
    *,
    train_bars: int = 4,
    test_bars: int = 2,
    embargo: int = 1,
    oos_returns: tuple[float, ...] | None = (0.05, 0.05),
    selection: tuple[tuple[str, object], ...] = (),
    reliable: bool = True,
    mock: bool = False,
) -> WalkForwardFold:
    """One fold, with train immediately before test and the embargo between."""
    train_start = index * (train_bars + embargo + test_bars)
    train_end = train_start + train_bars
    test_start = train_end + embargo
    window = FoldWindow(
        index=index,
        train_start=train_start,
        train_end=train_end,
        test_start=test_start,
        test_end=test_start + test_bars,
    )
    tier = SourceTier.MOCK if mock else SourceTier.DERIVED
    in_sample = make_backtest_result((0.05, 0.05), reliable=reliable, tier=tier)
    out_of_sample = (
        None
        if oos_returns is None
        else make_backtest_result(oos_returns, reliable=reliable, tier=tier)
    )
    return WalkForwardFold(
        window=window,
        selection=selection,
        in_sample=in_sample,
        out_of_sample=out_of_sample,
    )


def _report(
    folds: list[WalkForwardFold],
    *,
    min_sample: int = 1,
    min_folds: int = 2,
    quality: DataQuality | None = None,
    mock: bool = False,
):
    return summarise_folds(
        folds,
        instrument=Instrument.parse("TEST"),
        timeframe=Timeframe.D1.value,
        horizon=1,
        warmup=0,
        embargo_bars=1,
        objective=OptimizationObjective.DIRECTIONAL_ACCURACY,
        quality=quality
        or DataQuality(status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0),
        provenance=Provenance(
            source="test",
            tier=SourceTier.MOCK if mock else SourceTier.DERIVED,
            detail="unit test",
        ),
        min_sample=min_sample,
        min_folds=min_folds,
    )


# ----------------------------------------------------------------------
# the splitter
# ----------------------------------------------------------------------


def test_a_rolling_schedule_walks_the_series_one_test_window_at_a_time():
    splitter = WalkForwardSplitter(train_bars=4, test_bars=2, embargo_bars=1)
    windows = splitter.folds(12)

    assert [(w.train_start, w.train_end) for w in windows] == [
        (0, 4),
        (2, 6),
        (4, 8),
    ]
    assert [(w.test_start, w.test_end) for w in windows] == [(5, 7), (7, 9), (9, 11)]
    assert [w.index for w in windows] == [0, 1, 2]
    assert all(w.embargo_bars == 1 for w in windows)
    assert splitter.step == 2
    assert splitter.span_bars == 7


def test_the_embargo_keeps_the_training_window_out_of_the_test_window():
    # train_bars + embargo is the last training bar, so the test window starts
    # exactly `embargo` bars after the training window ends -- never before it.
    splitter = WalkForwardSplitter(train_bars=5, test_bars=3, embargo_bars=2)
    for window in splitter.folds(40):
        assert window.test_start == window.train_end + 2
        assert window.embargo_bars == 2


def test_an_anchored_schedule_grows_the_training_window_from_one_start():
    splitter = WalkForwardSplitter(
        train_bars=4, test_bars=2, embargo_bars=1, anchored=True
    )
    windows = splitter.folds(12)

    assert [w.train_start for w in windows] == [0, 0, 0]
    assert [w.train_end for w in windows] == [4, 6, 8]
    assert [(w.test_start, w.test_end) for w in windows] == [(5, 7), (7, 9), (9, 11)]


def test_a_warmup_holds_the_first_fold_back():
    splitter = WalkForwardSplitter(train_bars=4, test_bars=2)
    windows = splitter.folds(10, warmup=2)

    assert [(w.train_start, w.test_end) for w in windows] == [(2, 8), (4, 10)]


def test_a_series_too_short_for_a_fold_yields_no_folds():
    splitter = WalkForwardSplitter(train_bars=4, test_bars=2, embargo_bars=1)
    # A span of 7 bars does not fit in 5, and an empty tuple -- not a
    # half-window -- is the honest answer.
    assert splitter.folds(5) == ()
    assert splitter.folds(0) == ()
    assert splitter.folds(10, warmup=10) == ()


def test_a_splitter_rejects_an_unusable_schedule():
    with pytest.raises(ValueError):
        WalkForwardSplitter(train_bars=0, test_bars=2)
    with pytest.raises(ValueError):
        WalkForwardSplitter(train_bars=4, test_bars=0)
    with pytest.raises(ValueError):
        WalkForwardSplitter(train_bars=4, test_bars=2, embargo_bars=-1)
    with pytest.raises(ValueError):
        WalkForwardSplitter(train_bars=4, test_bars=2, step_bars=0)


def test_an_overlapping_step_is_honoured_when_asked_for():
    # A step below the test window deliberately re-scores bars; the caller who
    # sets it has traded fold independence for fold count and gets what it asked
    # for rather than a silent correction.
    splitter = WalkForwardSplitter(train_bars=4, test_bars=4, step_bars=2)
    windows = splitter.folds(20)
    assert splitter.step == 2
    assert windows[0].test_start == 4
    assert windows[1].test_start == 6


# ----------------------------------------------------------------------
# MarketData.window -- the slicing primitive the folds are built from
# ----------------------------------------------------------------------


def test_a_window_is_half_open_and_carries_the_series_provenance():
    data = make_market_data([100.0 + i for i in range(10)])
    window = data.window(2, 5)

    assert window.count == 3
    assert window.candles == data.candles[2:5]
    assert window.provenance == data.provenance
    assert window.quality == data.quality


def test_a_window_that_runs_off_the_series_fails_loudly():
    data = make_market_data([100.0 + i for i in range(10)])

    assert data.window(0).count == 10
    assert data.window(10, 10).count == 0
    with pytest.raises(ValueError):
        data.window(-1)
    with pytest.raises(ValueError):
        data.window(0, 11)
    with pytest.raises(ValueError):
        data.window(5, 4)


# ----------------------------------------------------------------------
# pooling
# ----------------------------------------------------------------------


def test_pooled_returns_are_concatenated_in_fold_order():
    folds = [
        _fold(0, oos_returns=(0.02, -0.01)),
        _fold(1, oos_returns=(0.03,)),
    ]
    assert pool_out_of_sample_returns(folds) == [0.02, -0.01, 0.03]


def test_an_unevaluated_fold_contributes_nothing_to_the_pool():
    folds = [
        _fold(0, oos_returns=(0.02,)),
        _fold(1, oos_returns=None),
    ]
    assert pool_out_of_sample_returns(folds) == [0.02]


def test_the_pooled_drawdown_is_the_path_of_the_whole_run():
    # Fold A: +0.10, +0.10. Fold B: -0.05, -0.05. The pooled equity path peaks at
    # 0.20 and falls to 0.10, so the run's drawdown is 0.10 -- not the 0.05 mean
    # of the two folds' own drawdowns (0.0 and 0.10).
    folds = [
        _fold(0, oos_returns=(0.10, 0.10)),
        _fold(1, oos_returns=(-0.05, -0.05)),
    ]
    report = _report(folds)

    assert report.oos_statistics is not None
    assert report.oos_statistics.trades == 4
    assert report.oos_statistics.max_drawdown == pytest.approx(0.10)
    assert report.oos_statistics.cumulative_return == pytest.approx(0.10)


# ----------------------------------------------------------------------
# the honesty gate
# ----------------------------------------------------------------------


def test_a_report_over_enough_reliable_folds_is_reliable():
    report = _report([_fold(0), _fold(1)], min_sample=1, min_folds=2)
    assert report.is_reliable is True
    assert report.limitations == ()
    assert report.evaluated_folds == 2


def test_one_fold_is_not_evidence_of_generalisation():
    report = _report([_fold(0)], min_folds=2)
    assert report.is_reliable is False
    assert any("fold(s) were measured" in line for line in report.limitations)


def test_mock_data_is_never_a_reliable_edge():
    report = _report([_fold(0, mock=True), _fold(1, mock=True)], mock=True)
    assert report.is_reliable is False
    assert any("MOCK" in line for line in report.limitations)


def test_a_thin_pooled_sample_is_reported_as_thin():
    report = _report([_fold(0), _fold(1)], min_sample=10)
    assert report.is_reliable is False
    assert any("pooled out-of-sample directional calls" in line for line in report.limitations)


def test_unusable_data_is_named_in_the_limitations():
    # STALE data is still usable -- it is degraded, and the backtester records
    # that in its own limitations -- but INVALID data cannot be analysed at all,
    # so a walk-forward run over it must be unreliable and say which it was.
    quality = DataQuality(
        status=DataQualityStatus.INVALID,
        issues=("the last bar's high is below its low",),
        freshness_seconds=0.0,
    )
    report = _report([_fold(0), _fold(1)], quality=quality)
    assert report.is_reliable is False
    assert any("invalid" in line for line in report.limitations)


def test_a_run_with_no_folds_says_why_rather_than_inventing_one():
    report = _report([])
    assert report.is_reliable is False
    assert report.evaluated_folds == 0
    assert report.oos_statistics is None
    assert any("No fold fitted the series" in line for line in report.limitations)
    assert any("out-of-sample measurement" in line for line in report.limitations)


def test_the_generalisation_gap_is_in_sample_minus_out_of_sample():
    # Both folds' in-sample results score 1.0 (two winning trades); the pooled
    # out-of-sample accuracy is 2/4 = 0.5, so the gap is 0.5 -- the fit showing.
    folds = [
        _fold(0, oos_returns=(0.10, -0.10)),
        _fold(1, oos_returns=(0.10, -0.10)),
    ]
    report = _report(folds)

    assert report.in_sample_accuracy_mean == pytest.approx(1.0)
    assert report.oos_directional_accuracy == pytest.approx(0.5)
    assert report.generalisation_gap == pytest.approx(0.5)


# ----------------------------------------------------------------------
# selection stability
# ----------------------------------------------------------------------


def test_selection_stability_is_the_share_of_folds_that_agreed():
    agreed = (("period", 14),)
    other = (("period", 20),)
    folds = [
        _fold(0, selection=agreed),
        _fold(1, selection=agreed),
        _fold(2, selection=other),
    ]
    assert selection_stability(folds) == pytest.approx(2 / 3)


def test_a_search_that_never_selected_anything_has_no_stability():
    # Carrying the configured defaults forward is not a selection, so a run that
    # only ever did that has no stability to report -- rather than a perfect 1.0
    # for having "agreed" with itself.
    folds = [_fold(0), _fold(1)]
    assert selection_stability(folds) is None
    report = _report(folds)
    assert report.selection_stability is None


def test_a_reselected_default_does_not_count_as_agreement():
    folds = [
        _fold(0, selection=(("period", 14),)),
        _fold(1, selection=()),
    ]
    assert selection_stability(folds) == pytest.approx(1.0)


# ----------------------------------------------------------------------
# the folds themselves
# ----------------------------------------------------------------------


def test_a_fold_measured_out_of_sample_must_carry_its_in_sample_measurement():
    window = FoldWindow(index=0, train_start=0, train_end=4, test_start=5, test_end=7)
    with pytest.raises(ValueError):
        WalkForwardFold(window=window, out_of_sample=make_backtest_result((0.01,)))


def test_a_fold_window_cannot_start_its_test_before_training_ends():
    with pytest.raises(ValueError):
        FoldWindow(index=0, train_start=0, train_end=5, test_start=4, test_end=6)
    with pytest.raises(ValueError):
        FoldWindow(index=0, train_start=3, train_end=3, test_start=3, test_end=5)


def test_a_report_serialises_its_folds_and_headline_numbers():
    report = _report([_fold(0), _fold(1)])
    payload = report.to_dict()

    assert payload["horizon"] == 1
    assert payload["evaluated_folds"] == 2
    assert len(payload["folds"]) == 2
    assert payload["folds"][0]["window"]["test_start"] == 5
    assert payload["is_reliable"] is True
    assert isinstance(payload["created_at"], str)
