"""
Event / economic-calendar value objects (spec sections 5, 9, 26).

The calendar layer answers one honest question the critic must eventually ask
(section 5): *is there a major scheduled event within the prediction horizon?*
Earnings, ex-dividend dates, guidance updates and macro releases all raise the
risk that a signal derived from price/structure is invalidated by information the
model never saw. Its value objects follow the same discipline as the rest of the
domain:

- a :class:`MarketEvent` is a single *scheduled* event as a provider reported it,
  content-addressed so the same event dedupes across polls and never carries a
  fabricated identity;
- an :class:`EventCalendar` is the aggregate over one instrument and one horizon:
  the events that fall inside it, whether any is high-impact, and -- like every
  other analysis object -- an explicit ``is_reliable`` flag plus ``limitations``
  that say plainly when the calendar should NOT be trusted (mock data especially).

A scheduled event is sourced data, never a prediction (section 15): nothing here
asserts what an event will *do* to price, only that it is on the calendar, and a
MOCK calendar can never masquerade as a real one (sections 2, 28, 61).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    """Category of a scheduled market event. Inherits ``str`` for JSON output."""

    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    GUIDANCE = "guidance"
    ECONOMIC = "economic"  # macro releases: rate decisions, CPI, jobs
    CORPORATE_ACTION = "corporate_action"  # split, buyback, M&A
    MEETING = "meeting"  # shareholder / analyst meeting
    OTHER = "other"
    UNKNOWN = "unknown"


class EventImpact(str, Enum):
    """How disruptive an event is expected to be. A label, never a probability."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


def _stable_id(
    *, instrument_key: str, event_type: str, title: str, scheduled_at: datetime
) -> str:
    """
    Content-addressed id for one event.

    Keyed on the scheduled *date* (not the exact time) so the same event
    re-fetched with a slightly different timestamp is recognised as one event
    rather than a brand-new one each poll.
    """
    day = scheduled_at.date().isoformat()
    payload = "|".join(
        (instrument_key, event_type.strip().lower(), title.strip().lower(), day)
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"evt_{digest[:16]}"


@dataclass(frozen=True, slots=True)
class MarketEvent:
    """A single scheduled event as a provider reported it (no interpretation)."""

    instrument_key: str
    event_type: EventType
    title: str
    scheduled_at: datetime
    impact: EventImpact
    provenance: Provenance
    detail: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                _stable_id(
                    instrument_key=self.instrument_key,
                    event_type=self.event_type.value,
                    title=self.title,
                    scheduled_at=self.scheduled_at,
                ),
            )

    @property
    def is_high_impact(self) -> bool:
        return self.impact is EventImpact.HIGH

    def days_until(self, reference: datetime) -> float:
        """Signed days from ``reference`` to the event (negative = already past)."""
        return round((self.scheduled_at - reference).total_seconds() / 86400.0, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instrument_key": self.instrument_key,
            "event_type": self.event_type.value,
            "title": self.title,
            "scheduled_at": self.scheduled_at.isoformat(),
            "impact": self.impact.value,
            "detail": self.detail,
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class EventCalendar:
    """Scheduled events for an instrument within a horizon, with its audit trail."""

    instrument: Instrument
    events: tuple[MarketEvent, ...]  # sorted soonest-first, all within the horizon
    horizon_days: int
    reference_time: datetime
    has_high_impact: bool
    provenance: Provenance
    quality: DataQuality
    is_reliable: bool
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def next_event(self) -> MarketEvent | None:
        """The soonest scheduled event in the horizon, if any."""
        return self.events[0] if self.events else None

    def to_dict(self) -> dict[str, Any]:
        ref = self.reference_time
        nxt = self.next_event
        return {
            "instrument": self.instrument.to_dict(),
            "horizon_days": self.horizon_days,
            "reference_time": ref.isoformat(),
            # A scheduled event is sourced fact, not a claim about price
            # (spec sections 3, 15, 28).
            "has_high_impact": self.has_high_impact,
            "event_count": self.event_count,
            "next_event": (
                {**nxt.to_dict(), "days_until": nxt.days_until(ref)}
                if nxt is not None
                else None
            ),
            "events": [
                {**e.to_dict(), "days_until": e.days_until(ref)} for e in self.events
            ],
            "is_reliable": self.is_reliable,
            "limitations": list(self.limitations),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
            "created_at": self.created_at.isoformat(),
        }
