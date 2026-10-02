"""
Deterministic mock event-calendar provider.

This exists so the whole event-risk path can be exercised end-to-end -- in tests
and in a no-credentials dev run -- WITHOUT a real calendar feed, while never
letting a synthetic event masquerade as a real scheduled one (spec sections 2,
28, 53, 61).

Honesty guarantees:
- every event is stamped ``SourceTier.MOCK`` and ``is_mock`` is True,
- the returned set is a deterministic slice of a fixed catalog, scheduled at
  seeded day-offsets keyed by the instrument symbol, so the same symbol always
  yields the same calendar (reproducible tests) but the events are clearly
  labelled synthetic,
- it never claims to be a real vendor and must never be used as evidence of an
  actual, real-world scheduled event.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from ..domain.enums import SourceTier
from ..domain.event_calendar import EventImpact, EventType, MarketEvent
from ..domain.instrument import Instrument
from ..domain.provenance import Provenance
from .calendar_base import CalendarProvider

_MOCK_SOURCE = "mock-calendar"

# A fixed catalog of (type, title-template, impact, base day-offset). The base
# offsets are staggered so a short horizon returns only the soonest events and a
# longer horizon reveals more -- exercising the horizon filter honestly.
_CATALOG: tuple[tuple[EventType, str, EventImpact, int], ...] = (
    (EventType.EARNINGS, "{sym} quarterly earnings release", EventImpact.HIGH, 3),
    (EventType.ECONOMIC, "Macro rate decision relevant to {sym}", EventImpact.HIGH, 5),
    (EventType.DIVIDEND, "{sym} ex-dividend date", EventImpact.MEDIUM, 8),
    (EventType.GUIDANCE, "{sym} management guidance update", EventImpact.MEDIUM, 12),
    (EventType.MEETING, "{sym} annual shareholder meeting", EventImpact.LOW, 18),
    (
        EventType.CORPORATE_ACTION,
        "{sym} share buyback program update",
        EventImpact.LOW,
        25,
    ),
)


def _seed_for(symbol: str) -> int:
    digest = hashlib.sha1(symbol.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


class MockCalendarProvider(CalendarProvider):
    """A reproducible, clearly-labelled synthetic event-calendar source."""

    name = "mock"
    tier = SourceTier.MOCK

    async def get_events(
        self,
        instrument: Instrument,
        *,
        horizon_days: int,
    ) -> tuple[MarketEvent, ...]:
        if horizon_days <= 0:
            raise ValueError("horizon_days must be positive.")

        seed = _seed_for(instrument.symbol)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        provenance = Provenance(
            source=_MOCK_SOURCE,
            tier=SourceTier.MOCK,
            detail="deterministic synthetic event catalog",
        )

        events: list[MarketEvent] = []
        for i, (event_type, template, impact, base) in enumerate(_CATALOG):
            # A small, deterministic per-event jitter (0..2 days) keyed by the
            # symbol, so different instruments have different -- but stable --
            # calendars. The earnings/macro base offsets stay <= a 7-day horizon.
            jitter = (seed >> (i * 2)) % 3
            offset = base + jitter
            if offset > horizon_days:
                continue
            events.append(
                MarketEvent(
                    instrument_key=instrument.key,
                    event_type=event_type,
                    title=template.format(sym=instrument.symbol),
                    scheduled_at=now + timedelta(days=offset),
                    impact=impact,
                    provenance=provenance,
                    detail="Synthetic scheduled event (MOCK); not a real calendar entry.",
                )
            )

        events.sort(key=lambda e: e.scheduled_at)
        return tuple(events)
