"""
Event / economic-calendar provider abstraction.

The calendar layer depends on this interface, never on a concrete feed, so a
real earnings/economic-calendar vendor or API adapter can be swapped in later
without touching the service layer (CLAUDE.md sections 10, 23 -- dependency
inversion).

A provider's job is narrow and honest:
- return the scheduled :class:`MarketEvent` items for an instrument that fall
  within the requested horizon,
- stamp every event with Provenance (source + SourceTier) and never claim a tier
  it cannot back up,
- raise a typed :class:`CalendarError` rather than fabricating events when it
  cannot fulfil a request. An empty tuple is a legitimate honest result (a clear
  calendar -- no scheduled events), distinct from a failure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.enums import SourceTier
from ..domain.event_calendar import MarketEvent
from ..domain.instrument import Instrument


class CalendarProvider(ABC):
    """Interface every event/economic-calendar source implements."""

    #: Human-readable source label used in Provenance.
    name: str = "unknown"

    #: The best tier this provider can honestly claim for its data.
    tier: SourceTier = SourceTier.UNVERIFIED

    @property
    def is_mock(self) -> bool:
        return self.tier is SourceTier.MOCK

    @abstractmethod
    async def get_events(
        self,
        instrument: Instrument,
        *,
        horizon_days: int,
    ) -> tuple[MarketEvent, ...]:
        """
        Return the scheduled events for the instrument within ``horizon_days``.

        Must raise a :class:`CalendarError` (never fabricate) if the calendar
        cannot be retrieved. Each returned MarketEvent carries its own
        Provenance. An empty tuple is a legitimate honest result (a clear
        calendar), distinct from a failure.
        """
        raise NotImplementedError
