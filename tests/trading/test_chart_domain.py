"""
Chart domain value objects: Timeframe monthly bar, annotations, chart data
projection and chart state (Phase 3).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aetheros.trading.domain.chart import (
    ChartAnnotation,
    ChartAnnotationKind,
    ChartData,
    ChartPoint,
    ChartState,
)
from aetheros.trading.domain.enums import Timeframe
from aetheros.trading.domain.instrument import Instrument

UTC_TZ = UTC


def _ts(minutes: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC_TZ) + timedelta(minutes=minutes)


def _point(minutes: int, close: float = 100.0) -> ChartPoint:
    return ChartPoint(
        timestamp=_ts(minutes),
        open=close - 1.0,
        high=close + 1.0,
        low=close - 2.0,
        close=close,
        volume=1000.0,
    )


# ==============================================================
# Timeframe: the monthly bar
# ==============================================================


class TestTimeframeMonthly:
    def test_parse_exact_case_distinguishes_month_from_minute(self):
        assert Timeframe.parse("1M") is Timeframe.MN
        assert Timeframe.parse("1m") is Timeframe.M1

    def test_parse_case_insensitive_fallback(self):
        # Lowercase "1d" and mixed "1D" both resolve to the daily bar.
        assert Timeframe.parse("1d") is Timeframe.D1
        assert Timeframe.parse("1D") is Timeframe.D1

    def test_monthly_seconds_use_30_day_convention(self):
        assert Timeframe.MN.seconds == 30 * 86400

    def test_labels_are_human_readable(self):
        assert Timeframe.MN.label == "1 Month"
        assert Timeframe.M1.label == "1 Minute"

    def test_unknown_timeframe_still_raises(self):
        with pytest.raises(ValueError, match="Unknown timeframe"):
            Timeframe.parse("7x")


# ==============================================================
# ChartAnnotation
# ==============================================================


class TestChartAnnotation:
    def test_hline_roundtrip(self):
        annotation = ChartAnnotation(kind="hline", price=104.5, label="R1")
        payload = annotation.to_dict()
        assert payload["kind"] == "hline"
        assert payload["price"] == 104.5
        assert payload["label"] == "R1"

    def test_hline_requires_price(self):
        with pytest.raises(ValueError, match="hline.*price"):
            ChartAnnotation(kind="hline")

    def test_vline_requires_timestamp(self):
        with pytest.raises(ValueError, match="vline.*timestamp"):
            ChartAnnotation(kind="vline")
        ok = ChartAnnotation(kind="vline", timestamp=_ts(30))
        assert ok.to_dict()["timestamp"] is not None

    def test_trendline_requires_two_distinct_points(self):
        with pytest.raises(ValueError, match="two timestamps"):
            ChartAnnotation(kind="trendline", timestamp=_ts(0), price=100.0)
        with pytest.raises(ValueError, match="differ in time"):
            ChartAnnotation(
                kind="trendline",
                timestamp=_ts(10),
                timestamp2=_ts(10),
                price=100.0,
                price2=110.0,
            )

    def test_zone_requires_ordered_prices(self):
        with pytest.raises(ValueError, match="above"):
            ChartAnnotation(kind="zone", price=110.0, price2=100.0)
        ok = ChartAnnotation(kind="zone", price=100.0, price2=110.0)
        assert ok.price2 == 110.0

    def test_marker_requires_price_and_timestamp(self):
        with pytest.raises(ValueError, match="marker.*price"):
            ChartAnnotation(kind="marker", timestamp=_ts(5))
        with pytest.raises(ValueError, match="marker.*timestamp"):
            ChartAnnotation(kind="marker", price=100.0)
        ok = ChartAnnotation(kind="marker", timestamp=_ts(5), price=100.0)
        assert ok.kind == ChartAnnotationKind.MARKER

    def test_note_requires_timestamp_only(self):
        ok = ChartAnnotation(kind="note", timestamp=_ts(5), note="FOMC")
        assert ok.note == "FOMC"

    def test_unknown_kind_rejected(self):
        with pytest.raises(ValueError, match="Unknown annotation kind"):
            ChartAnnotation(kind="scribble", price=1.0)

    def test_non_finite_price_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            ChartAnnotation(kind="hline", price=float("nan"))

    def test_kind_constants_available(self):
        for kind in (
            ChartAnnotationKind.HLINE,
            ChartAnnotationKind.VLINE,
            ChartAnnotationKind.TRENDLINE,
            ChartAnnotationKind.ZONE,
            ChartAnnotationKind.MARKER,
            ChartAnnotationKind.NOTE,
        ):
            assert isinstance(kind, str)


# ==============================================================
# ChartData
# ==============================================================


class TestChartData:
    def test_ranges_from_points(self):
        data = ChartData(
            instrument=Instrument("TEST"),
            timeframe=Timeframe.D1,
            points=(_point(0, 100.0), _point(1, 105.0), _point(2, 110.0)),
        )
        assert data.time_start == _ts(0)
        assert data.time_end == _ts(2)
        assert data.price_high == pytest.approx(111.0)
        assert data.price_low == pytest.approx(98.0)

    def test_empty_points_rejected(self):
        with pytest.raises(ValueError, match="at least one point"):
            ChartData(
                instrument=Instrument("TEST"),
                timeframe=Timeframe.D1,
                points=(),
            )

    def test_non_increasing_time_rejected(self):
        with pytest.raises(ValueError, match="strictly increasing"):
            ChartData(
                instrument=Instrument("TEST"),
                timeframe=Timeframe.D1,
                points=(_point(5), _point(5)),
            )

    def test_point_ohlc_consistency_validated(self):
        with pytest.raises(ValueError, match="high"):
            ChartPoint(
                timestamp=_ts(0), open=100.0, high=90.0, low=95.0, close=100.0, volume=1.0
            )

    def test_point_negative_volume_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            ChartPoint(
                timestamp=_ts(0), open=100.0, high=101.0, low=99.0, close=100.0, volume=-1.0
            )

    def test_to_dict_includes_tail_not_full_series_by_default(self):
        points = tuple(_point(i, 100.0 + i) for i in range(50))
        data = ChartData(
            instrument=Instrument("TEST"),
            timeframe=Timeframe.D1,
            points=points,
        )
        payload = data.to_dict()
        assert payload["point_count"] == 50
        assert len(payload["recent_points"]) == 20
        full = data.to_dict(include_points=True)
        assert len(full["points"]) == 50


# ==============================================================
# ChartState
# ==============================================================


class TestChartState:
    def _state(self, start_min: int = 0, end_min: int = 60) -> ChartState:
        return ChartState(
            instrument=Instrument("TEST"),
            timeframe=Timeframe.D1,
            visible_start=_ts(start_min),
            visible_end=_ts(end_min),
        )

    def test_valid_state_roundtrip(self):
        state = self._state()
        payload = state.to_dict()
        assert payload["timeframe"] == "1d"
        assert payload["annotations"] == []

    def test_reversed_window_rejected(self):
        with pytest.raises(ValueError, match="precede"):
            self._state(start_min=60, end_min=0)

    def test_naive_timestamps_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            ChartState(
                instrument=Instrument("TEST"),
                timeframe=Timeframe.D1,
                visible_start=datetime(2025, 1, 1),
                visible_end=datetime(2025, 1, 2),
            )

    def test_annotations_carried(self):
        annotation = ChartAnnotation(kind="hline", price=100.0)
        state = ChartState(
            instrument=Instrument("TEST"),
            timeframe=Timeframe.D1,
            visible_start=_ts(0),
            visible_end=_ts(60),
            annotations=(annotation,),
        )
        assert state.annotations[0].price == 100.0
