"""
Session/time engine tests (spec Phase 6).

The spec requires session/time logic to be *testable* and driven by real
market/session/time information. These tests exercise it from timestamps alone
-- no candles, no provider -- because that is exactly the property being
claimed: the time layer is a pure function of wall-clock time.

Timestamps are written in the exchange's own clock (``local_time``) or in UTC,
never in a fixed offset, so a wrong handling of daylight saving shows up as a
failure rather than as a fixture that quietly assumes EST all year.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from aetheros.trading.domain.enums import KillZoneName, SessionName, Timeframe
from aetheros.trading.domain.ict import KillZone, TradingSession
from aetheros.trading.ict.sessions import (
    DEFAULT_EXCHANGE_TIMEZONE,
    SessionCatalogue,
)

from .conftest import local_time, make_ohlc_market_data

DAY = date(2026, 1, 15)
NY = ZoneInfo(DEFAULT_EXCHANGE_TIMEZONE)


def _catalogue() -> SessionCatalogue:
    return SessionCatalogue()


# ----------------------------------------------------------------------
# Point lookups: instant -> session
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("utc_hour", "expected"),
    [
        (1, SessionName.ASIA),  # 20:00 the previous local day
        (4, SessionName.ASIA),  # 23:00 -- still the same Asian session
        (6, SessionName.ASIA),  # 01:00 -- past local midnight but inside the wrap
        (8, SessionName.LONDON),  # 03:00
        (12, SessionName.LONDON),  # 07:00
        (13, SessionName.NEW_YORK),  # 08:00 -- New York opens (start inclusive)
        (21, SessionName.NEW_YORK),  # 16:00
        (23, None),  # 18:00 -- between the New York close and the Asian open
    ],
)
def test_utc_instant_maps_to_the_expected_session(
    utc_hour: int, expected: SessionName | None
) -> None:
    catalogue = _catalogue()
    timestamp = datetime(2026, 1, 15, utc_hour, 0, tzinfo=timezone.utc)
    session = catalogue.session_for(timestamp)
    assert (session.name if session else None) is expected


def test_asian_session_wraps_local_midnight() -> None:
    asia = next(s for s in _catalogue().sessions if s.name is SessionName.ASIA)
    assert asia.wraps_midnight is True
    # 23:00 and 01:00 local are the same session day; 12:00 local is not in it.
    assert asia.contains(local_time(2026, 1, 15, 23)) is True
    assert asia.contains(local_time(2026, 1, 16, 1)) is True
    assert asia.contains(local_time(2026, 1, 16, 12)) is False


def test_session_boundaries_are_half_open() -> None:
    """A window includes its start instant and excludes its end instant."""
    catalogue = _catalogue()
    # 02:00 local is London's first minute and no longer Asia's.
    assert catalogue.session_for(local_time(2026, 1, 15, 2)).name is SessionName.LONDON
    assert catalogue.session_for(local_time(2026, 1, 15, 1, 59)).name is SessionName.ASIA
    # 08:00 local is New York's first minute and no longer London's.
    assert (
        catalogue.session_for(local_time(2026, 1, 15, 8)).name is SessionName.NEW_YORK
    )
    assert (
        catalogue.session_for(local_time(2026, 1, 15, 7, 59)).name is SessionName.LONDON
    )


def test_the_default_table_partitions_the_trading_day() -> None:
    """Every quarter-hour of the 24-hour trading day belongs to at most one session."""
    catalogue = _catalogue()
    unassigned: list[datetime] = []
    for offset in range(0, 24 * 60, 15):
        timestamp = local_time(2026, 1, 15, 20) + timedelta(minutes=offset)
        matches = catalogue.sessions_for(timestamp)
        if not matches:
            unassigned.append(timestamp)
        assert len(matches) <= 1, f"{timestamp} fell into two sessions"
    # Only the 17:00-20:00 gap is unassigned; nothing before it is.
    assert unassigned, "expected the 17:00-20:00 gap to belong to no session"
    assert all(ts.astimezone(NY).hour >= 17 for ts in unassigned)


# ----------------------------------------------------------------------
# Point lookups: instant -> kill zone
# ----------------------------------------------------------------------


def test_kill_zones_nest_inside_their_declared_session() -> None:
    """Every zone is a sub-window of the session it names."""
    catalogue = _catalogue()
    for zone in catalogue.kill_zones:
        start, end = zone.window_on(DAY)
        midpoint = start + (end - start) / 2
        session = catalogue.session_for(midpoint)
        assert session is not None, f"{zone.name} has no containing session"
        assert session.name is zone.session


def test_overlapping_kill_zones_are_both_reported() -> None:
    """New York AM and London Close genuinely share 10:00-11:00 local."""
    catalogue = _catalogue()
    both = catalogue.kill_zones_for(local_time(2026, 1, 15, 10, 30))
    assert [zone.name for zone in both] == [
        KillZoneName.NY_AM,
        KillZoneName.LONDON_CLOSE,
    ]


def test_kill_zone_lookup_outside_every_zone_is_none() -> None:
    catalogue = _catalogue()
    # 06:00 local is London but before the New York AM zone and after London Open.
    assert catalogue.kill_zone_for(local_time(2026, 1, 15, 6)) is None
    assert catalogue.kill_zones_for(local_time(2026, 1, 15, 18)) == ()


def test_kill_zone_windows_are_half_open() -> None:
    catalogue = _catalogue()
    assert (
        catalogue.kill_zone_for(local_time(2026, 1, 15, 8, 30)).name
        is KillZoneName.NY_AM
    )
    # 08:29 local is inside no zone: London Open ended at 05:00.
    assert catalogue.kill_zone_for(local_time(2026, 1, 15, 8, 29)) is None
    # 11:00 local is the New York AM zone's exclusive end.
    assert KillZoneName.NY_AM not in {
        zone.name for zone in catalogue.kill_zones_for(local_time(2026, 1, 15, 11))
    }


# ----------------------------------------------------------------------
# Daylight saving
# ----------------------------------------------------------------------


def test_dst_moves_the_same_utc_instant_between_sessions() -> None:
    """
    The same UTC clock time lands in a different local session in January and
    July, because the session table is defined in exchange-local wall clock.

    12:30 UTC is 07:30 EST (London) in January and 08:30 EDT (New York) in July.
    """
    catalogue = _catalogue()
    winter = datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)
    summer = datetime(2026, 7, 15, 12, 30, tzinfo=timezone.utc)

    assert catalogue.session_for(winter).name is SessionName.LONDON
    assert catalogue.session_for(summer).name is SessionName.NEW_YORK

    # The kill zones differ too: 08:30 EDT is inside the New York AM zone,
    # while 07:30 EST is inside no zone at all.
    assert catalogue.kill_zone_for(winter) is None
    assert catalogue.kill_zone_for(summer).name is KillZoneName.NY_AM


def test_dst_shifts_the_local_clock_by_exactly_one_hour() -> None:
    """A sanity check that the zone database, not a fixed offset, is in play."""
    catalogue = _catalogue()
    winter = catalogue.local_date(datetime(2026, 1, 15, 12, tzinfo=timezone.utc))
    summer = catalogue.local_date(datetime(2026, 7, 15, 12, tzinfo=timezone.utc))
    assert winter == date(2026, 1, 15)
    assert summer == date(2026, 7, 15)
    # 12:00 UTC is 07:00 EST but 08:00 EDT.
    assert datetime(2026, 1, 15, 12, tzinfo=timezone.utc).astimezone(NY).hour == 7
    assert datetime(2026, 7, 15, 12, tzinfo=timezone.utc).astimezone(NY).hour == 8


# ----------------------------------------------------------------------
# Catalogue construction
# ----------------------------------------------------------------------


def test_custom_session_table_overrides_the_default() -> None:
    """A caller may redefine the windows without touching the engine."""
    custom = TradingSession(
        name=SessionName.LONDON,
        start=time(3, 0),
        end=time(11, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="Custom London",
    )
    catalogue = SessionCatalogue(sessions=[custom], kill_zones=[])

    session = catalogue.session_for(local_time(2026, 1, 15, 3, 30))
    assert session is not None and session.name is SessionName.LONDON
    # 20:00 local would be Asia under the default table, and is nothing here.
    assert catalogue.session_for(local_time(2026, 1, 15, 20)) is None
    assert catalogue.kill_zones == ()
    assert catalogue.kill_zone_for(local_time(2026, 1, 15, 3, 30)) is None


def test_custom_timezone_moves_the_whole_table() -> None:
    """Reading an instrument in Tokyo's clock re-anchors the local day."""
    tokyo = SessionCatalogue(timezone="Asia/Tokyo")
    timestamp = datetime(2026, 1, 15, 1, 0, tzinfo=timezone.utc)  # 10:00 JST
    assert tokyo.local_date(timestamp) == date(2026, 1, 15)
    assert _catalogue().local_date(timestamp) == date(2026, 1, 14)  # 20:00 EST


def test_unknown_timezone_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown timezone"):
        SessionCatalogue(timezone="Mars/Olympus_Mons")


def test_catalogue_must_define_at_least_one_session() -> None:
    with pytest.raises(ValueError, match="at least one session"):
        SessionCatalogue(sessions=[])


def test_session_and_zone_windows_must_be_non_zero_length() -> None:
    with pytest.raises(ValueError, match="non-zero length"):
        TradingSession(
            name=SessionName.ASIA,
            start=time(2, 0),
            end=time(2, 0),
            timezone=DEFAULT_EXCHANGE_TIMEZONE,
        )
    with pytest.raises(ValueError, match="non-zero length"):
        KillZone(
            name=KillZoneName.NY_AM,
            session=SessionName.NEW_YORK,
            start=time(8, 30),
            end=time(8, 30),
            timezone=DEFAULT_EXCHANGE_TIMEZONE,
        )


# ----------------------------------------------------------------------
# Aggregation over candles
# ----------------------------------------------------------------------


def _session_day() -> list[tuple[float, float, float, float]]:
    """32 quarter-hour bars from 20:00 local to 04:00 the next morning."""
    return [
        (100.0 + i, 100.5 + i, 99.5 + i, 100.25 + i)
        for i in range(32)
    ]


def _session_day_data():
    return make_ohlc_market_data(
        _session_day(),
        timeframe=Timeframe.M15,
        start=local_time(2026, 1, 15, 20),
    )


def test_a_candle_belongs_to_the_session_containing_its_open() -> None:
    """
    The documented labelling rule: a bar stamped *t* is in the session
    containing *t*, even though the bar itself spans into the next one.
    """
    data = _session_day_data()
    catalogue = _catalogue()
    first = data.candles[0]
    last = data.candles[-1]
    assert first.timestamp == local_time(2026, 1, 15, 20)
    assert catalogue.session_for(first.timestamp).name is SessionName.ASIA
    # The final bar opens at 03:45 and closes at 04:00 -- London's, not Asia's.
    assert last.timestamp == local_time(2026, 1, 16, 3, 45)
    assert catalogue.session_for(last.timestamp).name is SessionName.LONDON


def test_occurrence_groups_keep_a_wrapping_session_together() -> None:
    """Asia's 20:00-02:00 occurrence is one group, not two split at midnight."""
    data = _session_day_data()
    asia = next(s for s in _catalogue().sessions if s.name is SessionName.ASIA)
    groups = _catalogue().occurrence_groups(data.candles, asia)

    assert len(groups) == 1
    assert groups[0] == tuple(range(24))  # 20:00-01:45 inclusive


def test_session_windows_measure_the_bars_that_fell_inside() -> None:
    data = _session_day_data()
    windows = _catalogue().session_windows(
        data.candles, interval=timedelta(seconds=Timeframe.M15.seconds)
    )

    assert [window.session for window in windows] == [
        SessionName.ASIA,
        SessionName.LONDON,
    ]
    asia, london = windows

    # Asia: the first 24 bars, closing at 02:00 (last open + interval).
    assert asia.start_at == local_time(2026, 1, 15, 20)
    assert asia.end_at == local_time(2026, 1, 16, 2)
    assert asia.candle_count == 24
    assert asia.first_index == 0
    assert asia.last_index == 23
    assert asia.open == 100.0
    assert asia.close == 100.25 + 23
    assert asia.high == 100.5 + 23
    assert asia.low == 99.5

    # London: the eight bars from 02:00, nothing more.
    assert london.start_at == local_time(2026, 1, 16, 2)
    assert london.end_at == local_time(2026, 1, 16, 4)
    assert london.candle_count == 8
    assert london.first_index == 24
    assert london.last_index == 31


def test_session_windows_are_chronological_across_sessions() -> None:
    data = _session_day_data()
    windows = _catalogue().session_windows(
        data.candles, interval=timedelta(seconds=Timeframe.M15.seconds)
    )
    starts = [window.start_at for window in windows]
    assert starts == sorted(starts)


def test_bucket_by_local_date_splits_on_local_midnight() -> None:
    data = _session_day_data()
    buckets = _catalogue().bucket_by_local_date(data.candles)

    assert [bucket.local_date for bucket in buckets] == [
        date(2026, 1, 15),
        date(2026, 1, 16),
    ]
    first, second = buckets
    # 20:00-23:45 local is still 15 January; 00:00 onwards is the 16th.
    assert first.candle_count == 16
    assert first.open == 100.0
    assert first.close == 100.25 + 15
    assert second.candle_count == 16
    assert second.open == 100.0 + 16


def test_day_bucket_range_and_midpoint_are_measured() -> None:
    data = _session_day_data()
    first = _catalogue().bucket_by_local_date(data.candles)[0]
    assert first.range == pytest.approx(first.high - first.low)
    assert first.midpoint == pytest.approx((first.high + first.low) / 2)
    assert first.to_dict()["candle_count"] == 16
