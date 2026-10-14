"""
Session and kill-zone time engine (spec Phase 6).

ICT is a time-based framework, so this module is the foundation the rest of the
ICT engine stands on: it answers *which session and which kill zone a timestamp
belongs to*, and aggregates candles into the exchange-local days that the daily
bias is read from.

Everything here is pure: no I/O, no LLM, no market data of its own. A
:class:`SessionCatalogue` is a table of window *definitions* plus lookups over
them, which means session logic is testable from timestamps alone, without a
single candle -- the acceptance criterion the spec sets for it.

Two conventions are fixed here and documented rather than assumed:

**Sessions are a partition, kill zones overlap.** The default catalogue divides
the 24-hour trading day into the three desk-active blocks (Asia, London, New
York) expressed in New York local time, the convention ICT quotes. Kill zones
are narrower sub-windows and *do* overlap -- the New York AM and London Close
zones share an hour -- so zone lookups return tuples. Both lookups return tuples
so a custom catalogue with overlapping sessions is handled without a code path
that only works for the default table.

**A candle belongs to the session containing its open.** A bar stamped *t*
covers [*t*, *t* + interval), so membership is decided by *t* alone. Window
bounds are the first bar's open and the last bar's close, which is why building
a window needs the bar interval.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..domain.enums import KillZoneName, SessionName
from ..domain.ict import KillZone, SessionWindow, TradingSession
from ..domain.market_data import Candle

#: ICT's kill zones are conventionally quoted in New York local time, so that is
#: the default reference. It is a constructor argument everywhere, never baked
#: in, so a non-US instrument can be read in its own exchange's clock.
DEFAULT_EXCHANGE_TIMEZONE = "America/New_York"

# Session windows, in New York local time. The three blocks partition the
# trading day from the Asian open through the New York close; the remaining
# 17:00-20:00 window belongs to no session and is reported as such rather than
# silently folded into one.
_DEFAULT_SESSIONS: tuple[TradingSession, ...] = (
    TradingSession(
        name=SessionName.ASIA,
        start=time(20, 0),
        end=time(2, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="Asian Session",
    ),
    TradingSession(
        name=SessionName.LONDON,
        start=time(2, 0),
        end=time(8, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="London Session",
    ),
    TradingSession(
        name=SessionName.NEW_YORK,
        start=time(8, 0),
        end=time(17, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="New York Session",
    ),
)

# Kill zones, in New York local time. NY AM and London Close deliberately
# overlap between 10:00 and 11:00 -- that overlap is real, and lookups return
# both rather than picking one arbitrarily.
_DEFAULT_KILL_ZONES: tuple[KillZone, ...] = (
    KillZone(
        name=KillZoneName.ASIA,
        session=SessionName.ASIA,
        start=time(20, 0),
        end=time(0, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="Asian Kill Zone",
    ),
    KillZone(
        name=KillZoneName.LONDON_OPEN,
        session=SessionName.LONDON,
        start=time(2, 0),
        end=time(5, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="London Open Kill Zone",
    ),
    KillZone(
        name=KillZoneName.NY_AM,
        session=SessionName.NEW_YORK,
        start=time(8, 30),
        end=time(11, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="New York AM Kill Zone",
    ),
    KillZone(
        name=KillZoneName.LONDON_CLOSE,
        session=SessionName.NEW_YORK,
        start=time(10, 0),
        end=time(12, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="London Close Kill Zone",
    ),
    KillZone(
        name=KillZoneName.NY_PM,
        session=SessionName.NEW_YORK,
        start=time(13, 30),
        end=time(16, 0),
        timezone=DEFAULT_EXCHANGE_TIMEZONE,
        label="New York PM Kill Zone",
    ),
)


@dataclass(frozen=True, slots=True)
class DayBucket:
    """
    One exchange-local calendar day of price, aggregated from finer bars.

    This is the daily read the bias detector works from: the day's open (its
    first bar's open) and close (its last bar's close), the extremes price
    reached, and the bar range that produced them so a caller can trace the
    bucket back to the candles.
    """

    local_date: date
    open: float
    high: float
    low: float
    close: float
    candle_count: int
    first_index: int
    last_index: int

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError("A day high cannot be below its low.")
        if not (self.low <= self.open <= self.high):
            raise ValueError("A day open must lie within its range.")
        if not (self.low <= self.close <= self.high):
            raise ValueError("A day close must lie within its range.")
        if self.candle_count < 1:
            raise ValueError("A day bucket must contain at least one bar.")

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_date": self.local_date.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "range": self.range,
            "candle_count": self.candle_count,
            "first_index": self.first_index,
            "last_index": self.last_index,
        }


class SessionCatalogue:
    """
    A table of session and kill-zone definitions, plus lookups over them.

    The default table is the conventional ICT one in New York local time; pass
    ``sessions``/``kill_zones`` to read a different market's clock, or a
    different ``timezone`` to move the whole table.
    """

    def __init__(
        self,
        *,
        timezone: str = DEFAULT_EXCHANGE_TIMEZONE,
        sessions: Sequence[TradingSession] | None = None,
        kill_zones: Sequence[KillZone] | None = None,
    ) -> None:
        try:
            self._tzinfo = ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown timezone '{timezone}'.") from exc
        self._timezone = timezone
        self._sessions = tuple(sessions) if sessions is not None else _DEFAULT_SESSIONS
        self._kill_zones = (
            tuple(kill_zones) if kill_zones is not None else _DEFAULT_KILL_ZONES
        )
        if not self._sessions:
            raise ValueError("A session catalogue must define at least one session.")

    @property
    def timezone(self) -> str:
        return self._timezone

    @property
    def sessions(self) -> tuple[TradingSession, ...]:
        return self._sessions

    @property
    def kill_zones(self) -> tuple[KillZone, ...]:
        return self._kill_zones

    # ------------------------------------------------------------------
    # Point lookups (pure time -- no candles needed)
    # ------------------------------------------------------------------

    def local_date(self, timestamp: datetime) -> date:
        """The exchange-local calendar date of ``timestamp``."""
        return timestamp.astimezone(self._tzinfo).date()

    def sessions_for(self, timestamp: datetime) -> tuple[TradingSession, ...]:
        """Every session containing ``timestamp``, in catalogue order."""
        return tuple(s for s in self._sessions if s.contains(timestamp))

    def session_for(self, timestamp: datetime) -> TradingSession | None:
        """
        The first session containing ``timestamp``, or None.

        With the default (partitioning) table this is unambiguous. A custom
        table with overlapping sessions resolves to the earliest in catalogue
        order, deterministically, which is all the soft session *attribution*
        on a detection needs; use :meth:`sessions_for` to see every match.
        """
        for session in self._sessions:
            if session.contains(timestamp):
                return session
        return None

    def kill_zones_for(self, timestamp: datetime) -> tuple[KillZone, ...]:
        """Every kill zone containing ``timestamp`` (zones may overlap)."""
        return tuple(z for z in self._kill_zones if z.contains(timestamp))

    def kill_zone_for(self, timestamp: datetime) -> KillZone | None:
        """The first kill zone containing ``timestamp``, or None."""
        for zone in self._kill_zones:
            if zone.contains(timestamp):
                return zone
        return None

    # ------------------------------------------------------------------
    # Aggregation over candles
    # ------------------------------------------------------------------

    def occurrence_groups(
        self,
        candles: Sequence[Candle],
        window: TradingSession | KillZone,
    ) -> tuple[tuple[int, ...], ...]:
        """
        Group candle indices into one run per occurrence of ``window``.

        Each run is a single local day's instance of the window, so a session
        that wraps midnight (Asia) yields one group per session *day* rather
        than splitting at 00:00. Groups come back chronological, and a window
        with no bars in it contributes no group -- absence is reported by the
        caller, never as an empty window here.
        """
        buckets: dict[date, list[int]] = {}
        for index, candle in enumerate(candles):
            if not window.contains(candle.timestamp):
                continue
            local = candle.timestamp.astimezone(window.tzinfo)
            day = local.date()
            if window.wraps_midnight and local.time() < window.end:
                # After midnight, still part of the previous day's occurrence.
                day -= timedelta(days=1)
            buckets.setdefault(day, []).append(index)
        return tuple(tuple(buckets[day]) for day in sorted(buckets))

    def session_windows(
        self,
        candles: Sequence[Candle],
        *,
        interval: timedelta,
    ) -> tuple[SessionWindow, ...]:
        """
        Every session occurrence present in ``candles``, chronological.

        ``interval`` is the bar length, needed because a window's close is the
        *last bar's close* rather than its open timestamp.
        """
        windows: list[SessionWindow] = []
        for session in self._sessions:
            for indices in self.occurrence_groups(candles, session):
                windows.append(
                    self._build_session_window(candles, session, indices, interval)
                )
        windows.sort(key=lambda window: window.start_at)
        return tuple(windows)

    def bucket_by_local_date(
        self, candles: Sequence[Candle]
    ) -> tuple[DayBucket, ...]:
        """Aggregate ``candles`` into exchange-local calendar days, chronological."""
        buckets: dict[date, list[int]] = {}
        for index, candle in enumerate(candles):
            buckets.setdefault(self.local_date(candle.timestamp), []).append(index)
        return tuple(
            self._build_day_bucket(candles, day, indices)
            for day, indices in sorted(buckets.items())
        )

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_session_window(
        candles: Sequence[Candle],
        session: TradingSession,
        indices: Sequence[int],
        interval: timedelta,
    ) -> SessionWindow:
        bars = [candles[index] for index in indices]
        return SessionWindow(
            session=session.name,
            start_at=bars[0].timestamp,
            end_at=bars[-1].timestamp + interval,
            open=bars[0].open,
            high=max(bar.high for bar in bars),
            low=min(bar.low for bar in bars),
            close=bars[-1].close,
            candle_count=len(bars),
            first_index=indices[0],
            last_index=indices[-1],
        )

    @staticmethod
    def _build_day_bucket(
        candles: Sequence[Candle],
        day: date,
        indices: Sequence[int],
    ) -> DayBucket:
        bars = [candles[index] for index in indices]
        return DayBucket(
            local_date=day,
            open=bars[0].open,
            high=max(bar.high for bar in bars),
            low=min(bar.low for bar in bars),
            close=bars[-1].close,
            candle_count=len(bars),
            first_index=indices[0],
            last_index=indices[-1],
        )
