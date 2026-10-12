"""
ICT detector tests (spec Phase 6).

One section per concept, each a known-answer case over a hand-built,
timestamped candle sequence: the session or window the detector is given is
computed by the real session catalogue, so the time half is exercised too.

The negative cases matter as much as the positive ones -- the spec forbids
hardcoded outcomes and fabricated signals, so several tests assert that a
detector reports **nothing** (or an explicit limitation) when the condition it
claims to measure is absent: a change of character with no displacement, a
Judas swing with no sweep, a session that does not show the Power-of-Three
shape.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from aetheros.trading.domain.enums import (
    Confidence,
    Direction,
    KillZoneName,
    LiquidityEventKind,
    LiquidityPoolKind,
    SessionModelKind,
    SessionName,
    SMCZoneKind,
    StructureBreakType,
    Timeframe,
    TrendState,
)
from aetheros.trading.domain.smc import (
    DealingRange,
    LiquidityEvent,
    SMCAnalysis,
    SMCZone,
    StructureBreak,
)
from aetheros.trading.ict.daily_bias import detect_daily_bias
from aetheros.trading.ict.judas_swing import detect_judas_swings
from aetheros.trading.ict.kill_zones import detect_kill_zones
from aetheros.trading.ict.liquidity_pools import detect_liquidity_pools
from aetheros.trading.ict.market_structure_shift import (
    detect_market_structure_shifts,
)
from aetheros.trading.ict.ote import detect_ote
from aetheros.trading.ict.power_of_three import detect_power_of_three
from aetheros.trading.ict.session_models import detect_session_models
from aetheros.trading.ict.sessions import DayBucket, SessionCatalogue

from .conftest import local_time, make_ohlc_market_data

H1 = Timeframe.H1
INTERVAL = timedelta(seconds=H1.seconds)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def _context(ohlc, start: datetime, *, timeframe: Timeframe = H1):
    """Data plus the session context every time-based detector reads."""
    data = make_ohlc_market_data(ohlc, timeframe=timeframe, start=start)
    catalogue = SessionCatalogue()
    interval = timedelta(seconds=timeframe.seconds)
    return (
        data,
        catalogue,
        catalogue.session_windows(data.candles, interval=interval),
        catalogue.bucket_by_local_date(data.candles),
    )


def _session_bars(
    open_: float, high: float, low: float, close: float, count: int = 6
) -> list[tuple[float, float, float, float]]:
    """
    ``count`` bars whose session aggregate is exactly the given OHLC.

    The session high is placed on the second bar and the low on the third, so
    the aggregate the session layer computes is the one the test names --
    rather than something that has to be read back off a random walk.
    """
    mid = (high + low) / 2.0
    bars: list[tuple[float, float, float, float]] = []
    for i in range(count):
        o = open_ if i == 0 else mid
        c = close if i == count - 1 else mid
        if i == 1:
            h, l = high, max(min(o, c) - 0.01, low)
        elif i == 2:
            h, l = min(max(o, c) + 0.01, high), low
        else:
            h, l = min(max(o, c) + 0.01, high), max(min(o, c) - 0.01, low)
        bars.append((o, h, l, c))
    return bars


def _two_sessions(
    asia: tuple[float, float, float, float],
    london: tuple[float, float, float, float],
):
    """A 12-hour series: the Asian session then the London session."""
    data = make_ohlc_market_data(
        _session_bars(*asia) + _session_bars(*london),
        timeframe=H1,
        start=local_time(2026, 1, 14, 20),
    )
    catalogue = SessionCatalogue()
    windows = catalogue.session_windows(data.candles, interval=INTERVAL)
    buckets = catalogue.bucket_by_local_date(data.candles)
    return data, catalogue, windows, buckets


def _kill_zone_ohlc() -> list[tuple[float, float, float, float]]:
    """
    One full trading day from the Asian open, with known session extremes.

    Asia 99.5-101.5, London 100.2-102.5 (its opening hour taking Asia's high),
    New York 99.8-101.7.
    """
    return [
        # Asia -- 20:00 to 01:00
        (100.0, 100.5, 99.5, 100.2),
        (100.2, 100.8, 100.0, 100.6),
        (100.6, 101.2, 100.4, 101.0),
        (101.0, 101.5, 100.8, 101.2),
        (101.2, 101.3, 100.5, 100.7),
        (100.7, 100.9, 100.1, 100.3),
        # London -- 02:00 to 07:00
        (100.3, 101.0, 100.2, 100.9),
        (100.9, 102.0, 100.8, 101.9),
        (101.9, 102.5, 101.7, 102.2),
        (102.2, 102.3, 101.5, 101.7),
        (101.7, 101.8, 101.0, 101.2),
        (101.2, 101.4, 100.9, 101.1),
        # New York -- 08:00 to 16:00
        (101.1, 101.6, 101.0, 101.5),
        (101.5, 101.7, 101.2, 101.3),
        (101.3, 101.5, 100.8, 100.9),
        (100.9, 101.2, 100.4, 100.6),
        (100.6, 100.8, 100.0, 100.2),
        (100.2, 100.4, 99.8, 100.0),
        (100.0, 100.3, 99.9, 100.1),
        (100.1, 100.4, 100.0, 100.2),
        (100.2, 100.5, 100.1, 100.3),
        # 17:00 to 19:00 -- in no session
        (100.3, 100.4, 100.2, 100.3),
        (100.3, 100.4, 100.2, 100.3),
        (100.3, 100.4, 100.2, 100.3),
    ]


def _kill_zone_context():
    return _context(_kill_zone_ohlc(), local_time(2026, 1, 14, 20))


# ----------------------------------------------------------------------
# 1. Daily bias
# ----------------------------------------------------------------------


def _bucket(
    day: int, *, low: float, high: float, close: float, count: int = 10
) -> DayBucket:
    return DayBucket(
        local_date=date(2026, 1, day),
        open=close,
        high=high,
        low=low,
        close=close,
        candle_count=count,
        first_index=0,
        last_index=count - 1,
    )


def _two_days(*, low: float = 100.0, high: float = 110.0, close: float = 105.0):
    return [
        _bucket(14, low=low, high=high, close=close),
        _bucket(15, low=100.0, high=120.0, close=112.0),
    ]


def test_bias_is_bullish_above_the_prior_day_high() -> None:
    bias, limits = detect_daily_bias(
        _two_days(), last_price=112.0, timeframe="1d"
    )
    assert limits == ()
    assert bias is not None
    assert bias.direction is Direction.UP
    assert bias.confidence is Confidence.HIGH
    assert bias.prior_day_date == date(2026, 1, 14)
    assert bias.prior_day_high == 110.0
    assert bias.prior_day_low == 100.0
    assert bias.price_ratio == pytest.approx(1.2)
    assert bias.position == "premium"


def test_bias_is_bearish_below_the_prior_day_low() -> None:
    bias, limits = detect_daily_bias(
        _two_days(), last_price=95.0, timeframe="1d"
    )
    assert limits == ()
    assert bias is not None
    assert bias.direction is Direction.DOWN
    assert bias.confidence is Confidence.HIGH
    assert bias.price_ratio == pytest.approx(-0.5)
    assert bias.position == "discount"


def test_inside_the_prior_range_the_daily_trend_decides() -> None:
    bias, _ = detect_daily_bias(
        _two_days(),
        last_price=106.0,
        timeframe="1d",
        trend=TrendState.UPTREND,
    )
    assert bias is not None
    assert bias.direction is Direction.UP
    assert bias.confidence is Confidence.MEDIUM
    assert bias.position == "premium"


def test_inside_the_prior_range_with_no_trend_is_sideways() -> None:
    bias, _ = detect_daily_bias(
        _two_days(), last_price=105.0, timeframe="1d"
    )
    assert bias is not None
    assert bias.direction is Direction.SIDEWAYS
    assert bias.confidence is Confidence.LOW
    assert bias.position == "equilibrium"


def test_a_single_day_yields_no_bias_and_says_so() -> None:
    bias, limits = detect_daily_bias(
        _two_days()[:1], last_price=112.0, timeframe="1d"
    )
    assert bias is None
    assert len(limits) == 1
    assert "prior day" in limits[0]


def test_a_prior_day_with_no_range_yields_no_bias() -> None:
    flat = _bucket(14, low=105.0, high=105.0, close=105.0)
    bias, limits = detect_daily_bias(
        [flat, _bucket(15, low=100.0, high=120.0, close=112.0)],
        last_price=112.0,
        timeframe="1d",
    )
    assert bias is None
    assert len(limits) == 1
    assert "no range" in limits[0]


def test_bias_from_real_candles() -> None:
    """End to end: a rising series is read as an above-prior-high day."""
    ohlc = []
    price = 100.0
    for _ in range(48):
        open_ = price
        close = price + 0.1
        ohlc.append((open_, close + 0.05, open_ - 0.05, close))
        price = close
    data, _, _, buckets = _context(ohlc, local_time(2026, 1, 14, 20))

    assert len(buckets) == 3  # 14th, 15th and 16th exchange-local
    bias, limits = detect_daily_bias(
        buckets, last_price=float(data.last_price), timeframe="1h"
    )
    assert limits == ()
    assert bias is not None
    assert bias.direction is Direction.UP
    assert bias.prior_day_date == date(2026, 1, 15)
    assert float(data.last_price) > bias.prior_day_high


# ----------------------------------------------------------------------
# 2. Market structure shift
# ----------------------------------------------------------------------


def _mss_data():
    """40 hourly bars, calm except for one violently displaced bar at index 30."""
    ohlc = []
    price = 100.0
    for i in range(40):
        open_ = price
        if i == 30:
            close = open_ - 5.0
            ohlc.append((open_, open_ + 0.1, close - 0.1, close))
        else:
            close = open_ - 0.1
            ohlc.append((open_, open_ + 0.5, open_ - 0.5, close))
        price = close
    return make_ohlc_market_data(
        ohlc, timeframe=H1, start=local_time(2026, 1, 15, 0)
    )


def _mss_analysis(data, *, kind=StructureBreakType.CHOCH, with_gap: bool = False):
    """The SMC half, hand-built so the displacement rule is what is under test."""
    bar = data.candles[30]
    structure_break = StructureBreak(
        kind=kind,
        direction=Direction.DOWN,
        index=30,
        timestamp=bar.timestamp,
        timeframe="1h",
        broken_level=98.0,
        broken_index=10,
        break_price=float(bar.close),
        trend_before=TrendState.UPTREND,
        confidence=Confidence.MEDIUM,
    )
    zones: tuple[SMCZone, ...] = ()
    if with_gap:
        gap_bar = data.candles[25]
        zones = (
            SMCZone(
                kind=SMCZoneKind.FAIR_VALUE_GAP,
                direction=Direction.DOWN,
                top=99.0,
                bottom=98.0,
                index=25,
                timestamp=gap_bar.timestamp,
                timeframe="1h",
                confidence=Confidence.MEDIUM,
            ),
        )
    return (
        SMCAnalysis(
            instrument_key="TEST",
            timeframe="1h",
            last_price=float(bar.close),
            trend=TrendState.DOWNTREND,
            breaks=(structure_break,),
            zones=zones,
        ),
        structure_break,
    )


def test_displaced_change_of_character_is_reported() -> None:
    data = _mss_data()
    analysis, structure_break = _mss_analysis(data)

    shifts = detect_market_structure_shifts(analysis, data)
    assert len(shifts) == 1
    shift = shifts[0]
    assert shift.direction is Direction.DOWN
    assert shift.prior_trend is TrendState.UPTREND
    assert shift.index == 30
    assert shift.broken_level == structure_break.broken_level
    assert shift.displacement > 1.5
    assert shift.left_fair_value_gap is False
    assert shift.confidence is Confidence.MEDIUM
    assert shift.evidence


def test_change_of_character_without_displacement_is_not_a_shift() -> None:
    """The rule this detector exists for: a drift through a level is not an MSS."""
    data = _mss_data()
    analysis, _ = _mss_analysis(data)

    assert detect_market_structure_shifts(analysis, data) != ()
    # With the body multiple set beyond any candle's body, and no gap, nothing
    # about this break qualifies as displacement.
    assert (
        detect_market_structure_shifts(
            analysis, data, displacement_body_multiple=1_000_000.0
        )
        == ()
    )


def test_a_fair_value_gap_alone_confirms_the_shift() -> None:
    data = _mss_data()
    analysis, _ = _mss_analysis(data, with_gap=True)

    shifts = detect_market_structure_shifts(
        analysis, data, displacement_body_multiple=1_000_000.0
    )
    assert len(shifts) == 1
    assert shifts[0].left_fair_value_gap is True
    assert shifts[0].confidence is Confidence.MEDIUM


def test_gap_and_body_together_are_high_confidence() -> None:
    data = _mss_data()
    analysis, _ = _mss_analysis(data, with_gap=True)

    shifts = detect_market_structure_shifts(analysis, data)
    assert len(shifts) == 1
    assert shifts[0].left_fair_value_gap is True
    assert shifts[0].confidence is Confidence.HIGH


def test_a_break_with_the_trend_is_a_continuation_not_a_shift() -> None:
    data = _mss_data()
    analysis, _ = _mss_analysis(data, kind=StructureBreakType.BOS)
    assert detect_market_structure_shifts(analysis, data) == ()


def test_shift_is_attributed_to_its_session_when_a_catalogue_is_given() -> None:
    data = _mss_data()
    analysis, _ = _mss_analysis(data)
    shifts = detect_market_structure_shifts(
        analysis, data, catalogue=SessionCatalogue()
    )
    assert len(shifts) == 1
    # 00:00 + 30 hours = 06:00 New York, inside the London session.
    assert shifts[0].session is SessionName.LONDON


def test_non_positive_displacement_multiple_is_rejected() -> None:
    data = _mss_data()
    analysis, _ = _mss_analysis(data)
    with pytest.raises(ValueError, match="must be positive"):
        detect_market_structure_shifts(
            analysis, data, displacement_body_multiple=0.0
        )


# ----------------------------------------------------------------------
# 3. Kill zones
# ----------------------------------------------------------------------


def _kill_zones():
    data, catalogue, windows, _ = _kill_zone_context()
    return detect_kill_zones(
        data.candles, windows, interval=INTERVAL, timeframe="1h", catalogue=catalogue
    )


def test_every_present_kill_zone_is_measured() -> None:
    windows, limits = _kill_zones()
    assert limits == ()

    by_name = {window.name: window for window in windows}
    assert set(by_name) == {
        KillZoneName.ASIA,
        KillZoneName.LONDON_OPEN,
        KillZoneName.NY_AM,
        KillZoneName.LONDON_CLOSE,
        KillZoneName.NY_PM,
    }

    # The Asian kill zone carried the whole Asian session's range.
    asia = by_name[KillZoneName.ASIA]
    assert asia.start_at == local_time(2026, 1, 14, 20)
    assert asia.end_at == local_time(2026, 1, 15, 0)
    assert asia.candle_count == 4
    assert (asia.high, asia.low) == (101.5, 99.5)
    assert asia.range_share == pytest.approx(1.0)
    assert asia.swept_level is None

    # London's opening hour took the Asian high.
    london_open = by_name[KillZoneName.LONDON_OPEN]
    assert london_open.start_at == local_time(2026, 1, 15, 2)
    assert london_open.candle_count == 3
    assert (london_open.high, london_open.low) == (102.5, 100.2)
    assert london_open.range_share == pytest.approx(1.0)
    assert london_open.swept_level == pytest.approx(101.5)
    assert london_open.swept_direction is Direction.UP
    assert london_open.confidence is Confidence.HIGH

    # New York AM: 09:00 and 10:00 of a 1.9-point session.
    ny_am = by_name[KillZoneName.NY_AM]
    assert ny_am.start_at == local_time(2026, 1, 15, 9)
    assert ny_am.candle_count == 2
    assert (ny_am.high, ny_am.low) == (101.7, 100.8)
    assert ny_am.range_share == pytest.approx(0.9 / 1.9)
    assert ny_am.swept_level is None


def test_kill_zone_windows_are_chronological() -> None:
    windows, _ = _kill_zones()
    starts = [window.start_at for window in windows]
    assert starts == sorted(starts)


def test_new_york_pm_takes_the_london_low() -> None:
    windows, _ = _kill_zones()
    ny_pm = next(w for w in windows if w.name is KillZoneName.NY_PM)
    assert ny_pm.swept_level == pytest.approx(100.2)
    assert ny_pm.swept_direction is Direction.DOWN


def test_absent_kill_zones_are_reported_as_limitations() -> None:
    """A zone with no bars is absent -- never an empty window."""
    ohlc = [
        (100.0, 100.5, 99.5, 100.2),
        (100.2, 100.4, 100.0, 100.3),
        (100.3, 100.5, 100.1, 100.4),
    ]
    data, catalogue, windows, _ = _context(ohlc, local_time(2026, 1, 15, 12))
    zones, limits = detect_kill_zones(
        data.candles, windows, interval=INTERVAL, timeframe="1h", catalogue=catalogue
    )

    assert len(zones) == 1
    assert zones[0].name is KillZoneName.NY_PM
    assert len(limits) == 1
    for absent in ("asia", "london_open", "ny_am", "london_close"):
        assert absent in limits[0]


# ----------------------------------------------------------------------
# 4. Optimal trade entry
# ----------------------------------------------------------------------


def _ote_candles():
    ohlc = []
    for i in range(30):
        if i == 21:
            ohlc.append((109.0, 109.5, 107.5, 108.0))
        else:
            ohlc.append((109.0, 109.5, 109.0, 109.2))
    return make_ohlc_market_data(
        ohlc, timeframe=H1, start=local_time(2026, 1, 15, 0)
    )


def _range(low_index: int, high_index: int) -> DealingRange:
    return DealingRange(
        high=110.0,
        low=100.0,
        equilibrium=105.0,
        position="premium",
        price_ratio=0.9,
        high_index=high_index,
        low_index=low_index,
    )


def test_bullish_ote_band_is_the_618_to_79_retracement() -> None:
    candles = _ote_candles().candles
    zone, limits = detect_ote(
        _range(5, 20), candles, last_price=107.0, timeframe="1h"
    )
    assert limits == ()
    assert zone is not None
    assert zone.direction is Direction.UP
    assert zone.band_bottom == pytest.approx(106.18)
    assert zone.band_top == pytest.approx(107.9)
    assert zone.in_zone is True
    assert zone.confidence is Confidence.HIGH
    assert zone.index == 20
    # Price retraced to 107.5, i.e. 0.25 of the leg.
    assert zone.retracement_ratio == pytest.approx(0.25)


def test_a_bullish_band_that_price_never_reached_is_reported_as_such() -> None:
    candles = _ote_candles().candles
    zone, _ = detect_ote(_range(5, 20), candles, last_price=104.0, timeframe="1h")
    assert zone is not None
    assert zone.in_zone is False
    assert zone.confidence is Confidence.MEDIUM
    assert zone.retracement_ratio == pytest.approx(0.25)


def test_bearish_ote_band_is_mirrored_off_the_leg_high() -> None:
    candles = _ote_candles().candles
    zone, _ = detect_ote(_range(20, 5), candles, last_price=103.0, timeframe="1h")
    assert zone is not None
    assert zone.direction is Direction.DOWN
    assert zone.band_bottom == pytest.approx(102.1)
    assert zone.band_top == pytest.approx(103.82)
    assert zone.in_zone is True


def test_no_dealing_range_means_no_ote_band() -> None:
    candles = _ote_candles().candles
    zone, limits = detect_ote(None, candles, last_price=107.0, timeframe="1h")
    assert zone is None
    assert len(limits) == 1
    assert "dealing range" in limits[0]


def test_invalid_ote_ratios_are_rejected() -> None:
    candles = _ote_candles().candles
    with pytest.raises(ValueError, match="OTE ratios"):
        detect_ote(
            _range(5, 20),
            candles,
            last_price=107.0,
            timeframe="1h",
            low_ratio=0.8,
            high_ratio=0.7,
        )


# ----------------------------------------------------------------------
# 5. Liquidity pools
# ----------------------------------------------------------------------


def _pools(events=()):
    data, catalogue, windows, buckets = _kill_zone_context()
    pools = detect_liquidity_pools(
        events,
        windows,
        buckets,
        data.candles,
        timeframe="1h",
        catalogue=catalogue,
    )
    return pools, data


def test_session_extremes_become_liquidity_pools() -> None:
    pools, _ = _pools()
    by_kind = {}
    for pool in pools:
        by_kind.setdefault(pool.kind, []).append(pool)

    assert len(by_kind[LiquidityPoolKind.SESSION_HIGH]) == 3
    assert len(by_kind[LiquidityPoolKind.SESSION_LOW]) == 3

    asia_high = next(
        p for p in by_kind[LiquidityPoolKind.SESSION_HIGH] if p.level == 101.5
    )
    # Buy-side liquidity rests above a high.
    assert asia_high.direction is Direction.UP
    assert asia_high.session is SessionName.ASIA
    # Asia's high formed at bar 3; the first bar after it to trade through the
    # level is London's 102.0 print at bar 7.
    assert asia_high.index == 3
    assert asia_high.taken is True
    assert asia_high.taken_index == 7

    london_high = next(
        p for p in by_kind[LiquidityPoolKind.SESSION_HIGH] if p.level == 102.5
    )
    assert london_high.taken is False
    assert london_high.taken_index is None


def test_sell_side_pools_rest_below_lows() -> None:
    pools, _ = _pools()
    asia_low = next(
        p
        for p in pools
        if p.kind is LiquidityPoolKind.SESSION_LOW and p.level == 99.5
    )
    assert asia_low.direction is Direction.DOWN
    assert asia_low.taken is False

    london_low = next(
        p
        for p in pools
        if p.kind is LiquidityPoolKind.SESSION_LOW and p.level == 100.2
    )
    # London's low formed at bar 6; New York traded through it at bar 16, whose
    # 100.0 low is the first print below 100.2.
    assert london_low.taken is True
    assert london_low.taken_index == 16


def test_prior_day_extremes_are_reported() -> None:
    pools, _ = _pools()
    prior_high = next(
        p for p in pools if p.kind is LiquidityPoolKind.PRIOR_DAY_HIGH
    )
    prior_low = next(p for p in pools if p.kind is LiquidityPoolKind.PRIOR_DAY_LOW)
    assert (prior_high.level, prior_low.level) == (101.5, 99.5)
    assert prior_high.confidence is Confidence.HIGH


def test_equal_highs_from_the_smc_read_are_reused() -> None:
    data = _kill_zone_context()[0]
    event = LiquidityEvent(
        kind=LiquidityEventKind.EQUAL_HIGHS,
        direction=Direction.UP,
        level=105.0,
        extreme=105.1,
        index=10,
        timestamp=data.candles[10].timestamp,
        timeframe="1h",
        confidence=Confidence.MEDIUM,
    )
    pools, _ = _pools([event])
    equal = next(p for p in pools if p.kind is LiquidityPoolKind.EQUAL_HIGHS)
    assert equal.level == 105.0
    assert equal.index == 10
    assert equal.direction is Direction.UP
    # Nothing in the window ever traded above 105.
    assert equal.taken is False


def test_unmapped_liquidity_events_are_ignored() -> None:
    data = _kill_zone_context()[0]
    sweep = LiquidityEvent(
        kind=LiquidityEventKind.SWEEP,
        direction=Direction.UP,
        level=101.5,
        extreme=101.6,
        index=3,
        timestamp=data.candles[3].timestamp,
        timeframe="1h",
        confidence=Confidence.MEDIUM,
    )
    with_sweep, _ = _pools([sweep])
    without, _ = _pools()
    assert len(with_sweep) == len(without)


def test_a_pool_is_never_taken_by_the_bar_that_forms_it() -> None:
    """Strict inequality: the forming bar's own extreme does not count."""
    pools, _ = _pools()
    london_high = next(
        p
        for p in pools
        if p.kind is LiquidityPoolKind.SESSION_HIGH and p.level == 102.5
    )
    assert london_high.index == 8
    assert london_high.taken is False


# ----------------------------------------------------------------------
# 6. Judas swing
# ----------------------------------------------------------------------


def _judas_ohlc(*, close_above_open: bool = False):
    """Asia then London, London's opening hour taking Asia's high."""
    asia = [
        (100.0, 100.5, 99.5, 100.2),
        (100.2, 100.8, 100.0, 100.6),
        (100.6, 100.9, 100.3, 100.5),
        (100.5, 101.0, 100.2, 100.8),
        (100.8, 100.9, 100.1, 100.3),
        (100.3, 100.6, 99.8, 100.0),
    ]
    london = [
        (100.5, 102.0, 100.4, 101.8),  # opening hour: takes Asia's 101.0
        (101.8, 102.2, 101.5, 101.6),
        (101.6, 101.7, 100.5, 100.7),
        (100.7, 100.9, 99.8, 100.0),
        (100.0, 100.2, 99.0, 99.2),
        (99.2, 102.5 if close_above_open else 99.5, 98.5, 101.5 if close_above_open else 98.8),
    ]
    return asia + london, asia, london


def _judas(*, close_above_open: bool = False, minutes: int = 60):
    ohlc, _, _ = _judas_ohlc(close_above_open=close_above_open)
    data, _, windows, _ = _context(ohlc, local_time(2026, 1, 14, 20))
    return detect_judas_swings(
        windows, data.candles, timeframe="1h", opening_window_minutes=minutes
    )


def test_a_sweep_of_the_prior_high_that_reverses_is_a_bearish_judas_swing() -> None:
    swings, limits = _judas()
    assert limits == ()
    assert len(swings) == 1
    swing = swings[0]
    assert swing.session is SessionName.LONDON
    # The reversal is down, however bullish the sweep looked.
    assert swing.direction is Direction.DOWN
    assert swing.swept_level == pytest.approx(101.0)
    assert swing.sweep_extreme == pytest.approx(102.0)
    assert swing.sweep_index == 6
    assert swing.session_open == pytest.approx(100.5)
    assert swing.reversal_price == pytest.approx(98.8)
    assert swing.reversal_index == 11
    assert swing.timestamp == local_time(2026, 1, 15, 7)
    assert swing.confidence is Confidence.HIGH


def test_no_reversal_means_no_judas_swing() -> None:
    """The level was taken, but the session never closed back through its open."""
    swings, _ = _judas(close_above_open=True)
    assert swings == ()


def test_no_sweep_of_the_prior_session_means_no_judas_swing() -> None:
    data, _, windows, _ = _kill_zone_context()
    swings, limits = detect_judas_swings(windows, data.candles, timeframe="1h")
    assert swings == ()
    assert limits == ()


def test_a_single_session_cannot_produce_a_judas_swing() -> None:
    ohlc, _, _ = _judas_ohlc()
    data, _, windows, _ = _context(ohlc[:6], local_time(2026, 1, 14, 20))
    swings, limits = detect_judas_swings(windows, data.candles, timeframe="1h")
    assert swings == ()
    assert len(limits) == 1
    assert "prior session" in limits[0]


def test_the_opening_window_is_a_real_parameter() -> None:
    """A wider opening window reads a different extreme as the sweep."""
    hour, _ = _judas(minutes=60)
    five_hours, _ = _judas(minutes=300)

    assert len(hour) == 1 and len(five_hours) == 1
    assert (hour[0].sweep_index, hour[0].sweep_extreme) == (6, pytest.approx(102.0))
    # 02:00-06:00 includes the 03:00 bar, whose 102.2 high is the wider extreme.
    assert five_hours[0].sweep_index == 7
    assert five_hours[0].sweep_extreme == pytest.approx(102.2)
    # The level taken and the reversal are unchanged: only the measurement moved.
    assert five_hours[0].swept_level == pytest.approx(101.0)
    assert five_hours[0].reversal_price == pytest.approx(98.8)


# ----------------------------------------------------------------------
# 7. Power of Three
# ----------------------------------------------------------------------


def _power_of_three_ohlc() -> list[tuple[float, float, float, float]]:
    """Nine New York hours: a quiet open, a false push down, an expansion up."""
    return [
        (100.0, 100.3, 99.90, 100.2),  # accumulation
        (100.2, 100.5, 100.00, 100.1),
        (100.1, 100.4, 99.95, 100.3),
        (100.3, 100.4, 99.50, 99.8),  # manipulation: runs below the range
        (99.8, 99.9, 98.80, 99.0),
        (99.0, 99.3, 98.90, 99.2),
        (99.2, 100.0, 99.10, 99.9),  # distribution: expands up
        (99.9, 101.0, 99.80, 100.9),
        (100.9, 102.0, 100.80, 101.8),
    ]


def _pot(ohlc=None, **kwargs):
    data, _, windows, _ = _context(
        _power_of_three_ohlc() if ohlc is None else ohlc,
        local_time(2026, 1, 15, 8),
    )
    return detect_power_of_three(
        windows, data.candles, interval=INTERVAL, timeframe="1h", **kwargs
    )


def test_a_textbook_session_is_decomposed_into_three_measured_phases() -> None:
    results, limits = _pot()
    assert limits == ()
    assert len(results) == 1
    three = results[0]

    assert three.session is SessionName.NEW_YORK
    assert three.direction is Direction.UP
    assert three.manipulation_side is Direction.DOWN
    assert three.session_open == pytest.approx(100.0)
    assert three.session_close == pytest.approx(101.8)
    assert three.confidence is Confidence.HIGH

    # The session ranged 98.8-102.0, so 3.2.
    assert three.accumulation.high == pytest.approx(100.5)
    assert three.accumulation.low == pytest.approx(99.9)
    assert three.accumulation.range_share == pytest.approx(0.6 / 3.2)
    assert three.accumulation.candle_count == 3

    assert three.manipulation.low == pytest.approx(98.8)
    assert three.manipulation.range_share == pytest.approx(1.6 / 3.2)

    assert three.distribution.high == pytest.approx(102.0)
    assert three.distribution.range_share == pytest.approx(2.9 / 3.2)

    # Phase boundaries are the session's exact thirds.
    assert three.accumulation.start_at == local_time(2026, 1, 15, 8)
    assert three.manipulation.start_at == local_time(2026, 1, 15, 11)
    assert three.distribution.start_at == local_time(2026, 1, 15, 14)
    assert three.end_at == local_time(2026, 1, 15, 17)


def test_a_wide_accumulation_third_disqualifies_the_session() -> None:
    results, limits = _pot(accumulation_max_share=0.1)
    assert results == ()
    assert any("accumulation/manipulation" in limit for limit in limits)


def test_manipulation_on_the_same_side_as_the_close_is_not_a_power_of_three() -> None:
    """A session that only runs up is a trend, not accumulation/manipulation/distribution."""
    ohlc = [
        (100.0, 100.2, 99.90, 100.1),
        (100.1, 100.3, 100.00, 100.2),
        (100.2, 100.4, 100.10, 100.3),
        (100.3, 101.0, 100.20, 100.9),  # middle third runs UP, same as the close
        (100.9, 101.5, 100.80, 101.4),
        (101.4, 101.8, 101.30, 101.7),
        (101.7, 102.0, 101.60, 101.9),
        (101.9, 102.2, 101.80, 102.1),
        (102.1, 102.4, 102.00, 102.3),
    ]
    results, _ = _pot(ohlc)
    assert results == ()


def test_too_few_bars_to_split_is_reported_honestly() -> None:
    ohlc = [
        (100.0, 100.5, 99.5, 100.2),
        (100.2, 100.6, 100.0, 100.4),
    ]
    results, limits = _pot(ohlc)
    assert results == ()
    assert any("too few bars" in limit for limit in limits)


def test_invalid_accumulation_share_is_rejected() -> None:
    with pytest.raises(ValueError, match="accumulation_max_share"):
        _pot(accumulation_max_share=0.0)


# ----------------------------------------------------------------------
# 8. Session models
# ----------------------------------------------------------------------


def test_a_session_that_sweeps_and_gives_back_is_sweep_and_reverse() -> None:
    _, _, windows, _ = _two_sessions(
        (100.0, 103.0, 99.0, 102.0),   # Asia closes up
        (101.0, 103.5, 100.0, 101.5),  # London takes 103 and closes back inside
    )
    models, limits = detect_session_models(windows, timeframe="1h")
    assert limits == ()
    assert len(models) == 1
    model = models[0]
    assert model.session is SessionName.LONDON
    assert model.previous_session is SessionName.ASIA
    assert model.kind is SessionModelKind.SWEEP_AND_REVERSE
    assert model.direction is Direction.DOWN
    assert model.level_taken == pytest.approx(103.0)
    assert model.confidence is Confidence.HIGH


def test_a_session_wider_than_its_predecessor_has_expanded() -> None:
    _, _, windows, _ = _two_sessions(
        (99.5, 100.5, 99.5, 100.4),   # Asia ranges 1.0
        (100.0, 103.0, 100.0, 102.8),  # London ranges 3.0 and closes up
    )
    models, _ = detect_session_models(windows, timeframe="1h")
    assert len(models) == 1
    assert models[0].kind is SessionModelKind.EXPANSION
    assert models[0].direction is Direction.UP
    assert models[0].level_taken is None


def test_a_session_much_narrower_than_its_predecessor_is_consolidating() -> None:
    _, _, windows, _ = _two_sessions(
        (100.0, 103.0, 99.0, 102.0),   # Asia ranges 4.0
        (100.5, 102.2, 100.4, 102.0),  # London ranges 1.8, closes up
    )
    models, _ = detect_session_models(windows, timeframe="1h")
    assert len(models) == 1
    assert models[0].kind is SessionModelKind.CONSOLIDATION
    assert models[0].level_taken is None


def test_a_session_closing_against_its_predecessor_is_a_reversal() -> None:
    _, _, windows, _ = _two_sessions(
        (100.0, 103.0, 99.0, 102.0),   # Asia ranges 4.0 and closes up
        (102.0, 102.5, 99.5, 100.8),   # London ranges 3.0 and closes down
    )
    models, _ = detect_session_models(windows, timeframe="1h")
    assert len(models) == 1
    assert models[0].kind is SessionModelKind.REVERSAL
    assert models[0].direction is Direction.DOWN
    assert models[0].level_taken is None


def test_a_session_continuing_its_predecessor_is_continuation() -> None:
    _, _, windows, _ = _two_sessions(
        (100.0, 103.0, 99.0, 102.0),   # Asia ranges 4.0, closes up
        (100.5, 102.5, 100.0, 102.0),  # London ranges 2.5, closes up, no sweep
    )
    models, _ = detect_session_models(windows, timeframe="1h")
    assert len(models) == 1
    assert models[0].kind is SessionModelKind.CONTINUATION
    assert models[0].direction is Direction.UP


def test_the_kill_zone_day_models_london_against_asia_and_new_york_against_london() -> None:
    data, _, windows, _ = _kill_zone_context()
    models, limits = detect_session_models(windows, timeframe="1h")
    assert limits == ()
    assert [model.session for model in models] == [
        SessionName.LONDON,
        SessionName.NEW_YORK,
    ]
    # London takes Asia's high (101.5) and closes back below it.
    assert models[0].kind is SessionModelKind.SWEEP_AND_REVERSE
    assert models[0].level_taken == pytest.approx(101.5)
    # New York takes London's low (100.2) and closes back above it.
    assert models[1].kind is SessionModelKind.SWEEP_AND_REVERSE
    assert models[1].level_taken == pytest.approx(100.2)


def test_a_single_session_has_no_model() -> None:
    data, _, windows, _ = _context(
        _session_bars(100.0, 103.0, 99.0, 102.0),
        local_time(2026, 1, 14, 20),
    )
    models, limits = detect_session_models(windows, timeframe="1h")
    assert models == ()
    assert len(limits) == 1
    assert "two sessions" in limits[0]


def test_a_session_with_no_range_is_undefined() -> None:
    """A flat session has nothing to compare, and is labelled UNDEFINED."""
    flat = [(100.0, 100.0, 100.0, 100.0)] * 6
    data = make_ohlc_market_data(
        _session_bars(100.0, 103.0, 99.0, 102.0) + flat,
        timeframe=H1,
        start=local_time(2026, 1, 14, 20),
    )
    windows = SessionCatalogue().session_windows(data.candles, interval=INTERVAL)
    models, _ = detect_session_models(windows, timeframe="1h")

    assert len(models) == 1
    assert models[0].session is SessionName.LONDON
    assert models[0].kind is SessionModelKind.UNDEFINED
    assert models[0].direction is Direction.UNKNOWN
    assert models[0].confidence is Confidence.LOW


def test_the_detectors_are_deterministic() -> None:
    """The same candles always yield the same label."""
    _, _, windows, _ = _two_sessions(
        (100.0, 103.0, 99.0, 102.0),
        (100.5, 102.5, 100.0, 102.0),
    )
    first, _ = detect_session_models(windows, timeframe="1h")
    second, _ = detect_session_models(windows, timeframe="1h")
    assert first == second
