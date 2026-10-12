"""
ChartService: build/slice/annotate/synchronize over MarketData (Phase 3).

Deterministic and I/O-free: every test drives the pure chart operations on
synthetic series from the shared trading fixtures.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aetheros.trading.domain.chart import ChartAnnotation, ChartState
from aetheros.trading.domain.enums import Timeframe
from aetheros.trading.errors import InsufficientDataError
from aetheros.trading.services.chart_service import ChartService

from .conftest import make_market_data

UTC_TZ = UTC


def _series(closes, *, symbol="TEST", start=None):
    start = start or datetime(2025, 1, 1, tzinfo=UTC_TZ)
    end = start + timedelta(days=len(closes) - 1)
    return make_market_data(closes, symbol=symbol, end=end)


def _ts(day: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC_TZ) + timedelta(days=day)


# ==============================================================
# build_chart
# ==============================================================


class TestBuildChart:
    def test_projects_candles_to_points_with_ranges(self):
        closes = [100.0 + i for i in range(30)]
        data = _series(closes)
        chart = ChartService().build_chart(data)

        assert chart.instrument.symbol == "TEST"
        assert chart.timeframe is Timeframe.D1
        assert chart.points[0].close == pytest.approx(closes[0])
        assert chart.points[-1].close == pytest.approx(closes[-1])
        assert chart.provenance is not None
        # Price range from the fixture's high/low padding (+0.5 / -0.5).
        assert chart.price_high == pytest.approx(max(closes) + 0.5)
        assert chart.price_low == pytest.approx(min(closes) - 0.5)

    def test_empty_series_rejected(self):
        with pytest.raises(InsufficientDataError):
            ChartService().build_chart(_empty())


def _empty():
    from aetheros.trading.domain.enums import DataQualityStatus, SourceTier
    from aetheros.trading.domain.instrument import Instrument
    from aetheros.trading.domain.market_data import MarketData
    from aetheros.trading.domain.provenance import DataQuality, Provenance

    return MarketData(
        instrument=Instrument.parse("EMPTY"),
        timeframe=Timeframe.D1,
        candles=(),
        provenance=Provenance(source="test", tier=SourceTier.PRIMARY),
        quality=DataQuality(status=DataQualityStatus.OK),
    )


# ==============================================================
# slice_chart
# ==============================================================


class TestSliceChart:
    def test_slice_keeps_only_window_bars(self):
        closes = [100.0 + i for i in range(30)]
        data = _series(closes)
        chart = ChartService().slice_chart(data, _ts(10), _ts(19))
        assert chart.points[0].timestamp == _ts(10)
        assert chart.points[-1].timestamp == _ts(19)
        assert len(chart.points) == 10

    def test_slice_window_without_bars_raises(self):
        closes = [100.0 + i for i in range(30)]
        data = _series(closes)
        with pytest.raises(InsufficientDataError):
            ChartService().slice_chart(data, _ts(100), _ts(200))

    def test_slice_inclusive_on_both_ends(self):
        closes = [100.0 + i for i in range(30)]
        data = _series(closes)
        chart = ChartService().slice_chart(data, _ts(5), _ts(5))
        assert len(chart.points) == 1


# ==============================================================
# add_annotation
# ==============================================================


class TestAddAnnotation:
    def test_derives_new_state_immutably(self):
        closes = [100.0 + i for i in range(30)]
        data = _series(closes)
        service = ChartService()
        chart = service.build_chart(data)
        initial = ChartState(
            instrument=chart.instrument,
            timeframe=chart.timeframe,
            visible_start=chart.time_start,
            visible_end=chart.time_end,
        )
        annotation = ChartAnnotation(kind="hline", price=110.0, label="R1")
        updated = service.add_annotation(initial, annotation)

        assert initial.annotations == ()  # the original is untouched
        assert updated.annotations == (annotation,)
        assert updated.updated_at >= initial.updated_at


# ==============================================================
# synchronize
# ==============================================================


class TestSynchronize:
    def test_overlapping_series_trimmed_to_common_window(self):
        a = _series([100.0 + i for i in range(30)], symbol="A")  # days 0..29
        b = _series(
            [200.0 + i for i in range(30)],
            symbol="B",
            start=_ts(10),
        )  # days 10..39
        result = ChartService().synchronize({"A": a, "B": b})

        assert result["A"]["synced"] is True
        assert result["B"]["synced"] is True
        # Common window = intersection of the two ranges: days 10..29.
        assert result["A"]["chart"].points[0].timestamp == _ts(10)
        assert result["A"]["chart"].points[-1].timestamp == _ts(29)
        assert result["B"]["chart"].points[0].timestamp == _ts(10)
        assert result["B"]["chart"].points[-1].timestamp == _ts(29)
        window = result["A"]["window"]
        assert window["start"] == _ts(10).isoformat()
        assert window["end"] == _ts(29).isoformat()

    def test_disjoint_series_reported_not_fabricated(self):
        a = _series([100.0 + i for i in range(10)], symbol="A")  # days 0..9
        b = _series(
            [200.0 + i for i in range(10)],
            symbol="B",
            start=_ts(100),
        )  # days 100..109
        result = ChartService().synchronize({"A": a, "B": b})

        # No shared bars in the common window: both report unsynced honestly.
        assert result["A"]["synced"] is False
        assert result["B"]["synced"] is False
        assert result["A"]["chart"] is None
        assert result["B"]["chart"] is None
        assert result["B"]["limitation"] is not None

    def test_empty_series_is_excluded_with_limitation(self):
        a = _series([100.0 + i for i in range(10)], symbol="A")
        result = ChartService().synchronize({"A": a, "EMPTY": _empty()})
        assert result["A"]["synced"] is True
        assert result["EMPTY"]["synced"] is False
        assert result["EMPTY"]["limitation"] == "empty series"

    def test_no_series_returns_empty_mapping(self):
        assert ChartService().synchronize({}) == {}

    def test_single_series_syncs_to_itself(self):
        a = _series([100.0 + i for i in range(10)], symbol="A")
        result = ChartService().synchronize({"A": a})
        assert result["A"]["synced"] is True
        assert result["A"]["chart"].points[-1].close == pytest.approx(109.0)
