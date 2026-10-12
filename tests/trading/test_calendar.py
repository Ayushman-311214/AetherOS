"""
Deterministic event / economic-calendar tests (spec sections 5, 9, 21, 28).

Three layers, each pinned to the honesty rules:
- ``MockCalendarProvider`` is reproducible and loudly stamped ``SourceTier.MOCK``,
  filters by horizon, and returns its events soonest-first;
- ``EventCalendarService`` fuses provider events into an auditable
  ``EventCalendar`` that can never present a MOCK calendar as reliable, treats an
  empty calendar as an honest "no scheduled events" result (not a failure), and
  publishes a ``MarketEventsDetected`` event;
- the macro taxonomy names *which* of the spec's six releases an ``ECONOMIC``
  event is (CPI, FOMC, NFP, interest rates, GDP, employment) -- a label, never an
  impact, and ``UNKNOWN`` rather than a guess when the title names none of them.

A scheduled event is sourced calendar data, never a claim about what price will
do; nothing here fabricates events or an event's market impact.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.calendar.macro import classify
from aetheros.trading.domain.enums import DataQualityStatus, SourceTier
from aetheros.trading.domain.event_calendar import (
    EventImpact,
    EventType,
    MacroEventKind,
    MarketEvent,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.errors import CalendarError
from aetheros.trading.events import MarketEventsDetected
from aetheros.trading.providers.calendar_base import CalendarProvider
from aetheros.trading.providers.mock_calendar_provider import MockCalendarProvider
from aetheros.trading.services.calendar_service import EventCalendarService


def _event(
    *,
    days: float,
    impact: EventImpact = EventImpact.MEDIUM,
    event_type: EventType = EventType.EARNINGS,
    tier: SourceTier = SourceTier.SECONDARY,
    title: str | None = None,
) -> MarketEvent:
    """A controllable, clearly-synthetic event stamped a non-mock tier."""
    return MarketEvent(
        instrument_key="AAPL",
        event_type=event_type,
        title=title or f"AAPL scheduled event in {days}d",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=days),
        impact=impact,
        provenance=Provenance(
            source="fake-cal", tier=tier, detail="synthetic test event"
        ),
    )


class FakeCalendarProvider(CalendarProvider):
    """Hands back exactly the events built by the test; non-mock so it can be reliable."""

    name = "fake-cal"
    tier = SourceTier.SECONDARY

    def __init__(self, events: tuple[MarketEvent, ...]) -> None:
        self._events = events

    async def get_events(self, instrument, *, horizon_days) -> tuple[MarketEvent, ...]:
        return self._events


def _service(provider: CalendarProvider, *, event_bus=None) -> EventCalendarService:
    return EventCalendarService(provider, get_settings(), event_bus=event_bus)


# ----------------------------------------------------------------------
# MockCalendarProvider
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic():
    provider = MockCalendarProvider()
    inst = Instrument.parse("AAPL")
    first = await provider.get_events(inst, horizon_days=30)
    second = await provider.get_events(inst, horizon_days=30)
    assert [e.id for e in first] == [e.id for e in second]
    assert [e.title for e in first] == [e.title for e in second]


@pytest.mark.asyncio
async def test_mock_provider_is_labelled_mock():
    provider = MockCalendarProvider()
    assert provider.tier is SourceTier.MOCK
    assert provider.is_mock is True
    events = await provider.get_events(Instrument.parse("AAPL"), horizon_days=30)
    assert events
    assert all(e.provenance.tier is SourceTier.MOCK for e in events)


@pytest.mark.asyncio
async def test_mock_provider_rejects_non_positive_horizon():
    with pytest.raises(ValueError):
        await MockCalendarProvider().get_events(
            Instrument.parse("AAPL"), horizon_days=0
        )


@pytest.mark.asyncio
async def test_mock_provider_filters_by_horizon():
    inst = Instrument.parse("AAPL")
    short = await MockCalendarProvider().get_events(inst, horizon_days=7)
    longer = await MockCalendarProvider().get_events(inst, horizon_days=30)
    # A longer horizon can only reveal more (or equal) events, never fewer.
    assert len(short) <= len(longer)
    # Every returned event genuinely falls within its requested horizon.
    now = datetime.now(timezone.utc)
    assert all(e.scheduled_at <= now + timedelta(days=7, seconds=5) for e in short)


@pytest.mark.asyncio
async def test_mock_provider_returns_events_soonest_first():
    events = await MockCalendarProvider().get_events(
        Instrument.parse("AAPL"), horizon_days=30
    )
    times = [e.scheduled_at for e in events]
    assert times == sorted(times)


@pytest.mark.asyncio
async def test_mock_provider_short_horizon_has_high_impact():
    # The catalog guarantees at least one HIGH-impact event inside the default
    # 7-day horizon, so the event-risk path is always exercised on mock.
    events = await MockCalendarProvider().get_events(
        Instrument.parse("AAPL"), horizon_days=7
    )
    assert any(e.is_high_impact for e in events)


# ----------------------------------------------------------------------
# EventCalendarService aggregation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_returns_calendar_with_events():
    events = (_event(days=3), _event(days=5, impact=EventImpact.HIGH))
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")
    assert calendar.event_count == 2
    assert calendar.instrument.key == Instrument.parse("AAPL").key


@pytest.mark.asyncio
async def test_service_sorts_events_soonest_first():
    # Provider hands them back out of order; the service must reorder defensively.
    events = (_event(days=9), _event(days=2), _event(days=5))
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")
    times = [e.scheduled_at for e in calendar.events]
    assert times == sorted(times)
    assert calendar.next_event is not None
    assert calendar.next_event.scheduled_at == min(times)


@pytest.mark.asyncio
async def test_service_flags_high_impact():
    events = (_event(days=3, impact=EventImpact.LOW), _event(days=5, impact=EventImpact.HIGH))
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")
    assert calendar.has_high_impact is True


@pytest.mark.asyncio
async def test_service_no_high_impact_when_none_present():
    events = (_event(days=3, impact=EventImpact.LOW), _event(days=5, impact=EventImpact.MEDIUM))
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")
    assert calendar.has_high_impact is False


@pytest.mark.asyncio
async def test_service_non_mock_feed_is_reliable():
    events = (_event(days=3),)
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")
    assert calendar.is_reliable is True
    assert calendar.provenance.tier is SourceTier.SECONDARY


@pytest.mark.asyncio
async def test_service_empty_calendar_is_honest_not_a_failure():
    calendar = await _service(FakeCalendarProvider(())).get_events("AAPL")
    # An empty calendar is a legitimate "no scheduled event risk" result: usable
    # quality, zero events, and NOT a failure.
    assert calendar.event_count == 0
    assert calendar.next_event is None
    assert calendar.quality.status is DataQualityStatus.OK
    assert calendar.is_reliable is True
    assert any("no scheduled events" in lim.lower() for lim in calendar.limitations)


@pytest.mark.asyncio
async def test_service_mock_feed_is_never_reliable():
    calendar = await _service(MockCalendarProvider()).get_events("AAPL", horizon_days=30)
    assert calendar.is_reliable is False
    assert calendar.provenance.tier is SourceTier.MOCK
    assert any("MOCK" in lim for lim in calendar.limitations)


@pytest.mark.asyncio
async def test_service_uses_default_horizon():
    settings = get_settings()
    calendar = await _service(FakeCalendarProvider(())).get_events("AAPL")
    assert calendar.horizon_days == settings.TRADING_EVENT_HORIZON_DAYS


@pytest.mark.asyncio
async def test_service_rejects_empty_symbol():
    with pytest.raises(CalendarError):
        await _service(FakeCalendarProvider(())).get_events("")


@pytest.mark.asyncio
async def test_service_rejects_non_positive_horizon():
    with pytest.raises(CalendarError):
        await _service(FakeCalendarProvider(())).get_events("AAPL", horizon_days=0)


@pytest.mark.asyncio
async def test_service_wraps_provider_failure_as_calendar_error():
    class BrokenProvider(CalendarProvider):
        name = "broken"
        tier = SourceTier.SECONDARY

        async def get_events(self, instrument, *, horizon_days):
            raise RuntimeError("provider blew up")

    with pytest.raises(CalendarError):
        await _service(BrokenProvider()).get_events("AAPL")


@pytest.mark.asyncio
async def test_service_publishes_event():
    received: list[MarketEventsDetected] = []
    bus = EventBus()
    await bus.subscribe(MarketEventsDetected, lambda e: received.append(e))

    events = (_event(days=3, impact=EventImpact.HIGH),)
    await _service(FakeCalendarProvider(events), event_bus=bus).get_events("AAPL")

    assert len(received) == 1
    assert received[0].instrument_key == Instrument.parse("AAPL").key
    assert received[0].event_count == 1
    assert received[0].has_high_impact is True
    assert received[0].next_event_type == EventType.EARNINGS.value


@pytest.mark.asyncio
async def test_service_to_dict_shape_is_mock():
    calendar = await _service(MockCalendarProvider()).get_events("AAPL", horizon_days=30)
    data = calendar.to_dict()
    assert data["provenance"]["tier"] == SourceTier.MOCK.value
    assert data["is_reliable"] is False
    assert "has_high_impact" in data
    assert isinstance(data["events"], list)
    if data["events"]:
        assert "days_until" in data["events"][0]


# ----------------------------------------------------------------------
# Macro taxonomy
#
# The spec's economic calendar tracks six named releases. These pin that each
# one is *named*, that the two genuinely ambiguous pairs resolve to the
# specific kind, and that a title naming none of them is honestly UNKNOWN
# rather than mapped to the nearest guess.
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("US CPI y/y", MacroEventKind.CPI),
        ("FOMC Statement", MacroEventKind.FOMC),
        ("US Non-Farm Payrolls", MacroEventKind.NFP),
        ("Interest Rate Decision", MacroEventKind.INTEREST_RATE),
        ("GDP Growth Rate q/q", MacroEventKind.GDP),
        ("Unemployment Rate", MacroEventKind.EMPLOYMENT),
    ],
)
def test_classify_names_each_of_the_spec_categories(title, expected):
    assert classify(title).kind is expected


def test_nfp_outranks_the_broader_employment_kind():
    """
    "Non-Farm Employment Change" carries the broader kind's word too. Payrolls
    are the specific release, so the specific kind must win -- otherwise the two
    NFP kinds would be indistinguishable and the ordering would be decorative.
    """
    read = classify("Non-Farm Employment Change")
    assert read.kind is MacroEventKind.NFP
    assert "employment" in read.matched_terms or "non farm employment" in (
        read.matched_terms
    )


def test_fomc_outranks_the_generic_rate_decision():
    """A Fed decision is the specific case of a rate decision, not a generic one."""
    assert classify("FOMC Interest Rate Decision").kind is MacroEventKind.FOMC
    assert classify("BoE Interest Rate Decision").kind is (
        MacroEventKind.INTEREST_RATE
    )


def test_inflation_language_maps_to_cpi_even_when_the_fed_is_named():
    assert classify("Fed's preferred inflation gauge").kind is MacroEventKind.CPI


def test_case_and_punctuation_do_not_change_the_read():
    assert classify("us NON-FARM payrolls").kind is MacroEventKind.NFP
    assert classify("u.s. cpi, y/y").kind is MacroEventKind.CPI
    assert classify("FOMC  statement.").kind is MacroEventKind.FOMC


def test_a_term_matches_only_at_a_word_boundary():
    """``gdpr`` must not read as ``gdp``: a near-miss is worse than UNKNOWN."""
    assert classify("GDPR compliance update").kind is MacroEventKind.UNKNOWN


def test_text_naming_no_known_release_is_unknown():
    read = classify("US Retail Sales m/m")
    assert read.kind is MacroEventKind.UNKNOWN
    assert read.matched_terms == ()


@pytest.mark.parametrize("text", ["", "   ", "!!!", "\n\t"])
def test_empty_text_is_unknown_with_no_terms(text):
    read = classify(text)
    assert read.kind is MacroEventKind.UNKNOWN
    assert read.matched_terms == ()


def test_classify_is_deterministic():
    first = classify("US CPI y/y")
    second = classify("US CPI y/y")
    assert first == second


def test_the_read_reports_the_terms_it_matched():
    """Every classification must be explainable by the text that produced it."""
    read = classify("US Consumer Price Index")
    assert read.kind is MacroEventKind.CPI
    assert "consumer price index" in read.matched_terms


@pytest.mark.asyncio
async def test_service_names_the_macro_release_and_keeps_it_in_the_payload():
    events = (
        _event(
            days=3,
            event_type=EventType.ECONOMIC,
            impact=EventImpact.HIGH,
            title="US CPI y/y",
        ),
    )
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")

    assert calendar.events[0].macro_kind is MacroEventKind.CPI
    # The tool returns calendar.to_dict(), so this is the agent-visible path.
    assert calendar.to_dict()["events"][0]["macro_kind"] == "cpi"


@pytest.mark.asyncio
async def test_service_leaves_a_non_macro_event_unnamed():
    """An earnings date already *is* its type; a second label would say nothing."""
    events = (_event(days=3, event_type=EventType.EARNINGS),)
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")

    assert calendar.events[0].macro_kind is None
    assert calendar.to_dict()["events"][0]["macro_kind"] is None


@pytest.mark.asyncio
async def test_the_classification_never_touches_the_providers_impact():
    """
    The taxonomy names a release; it does not grade it. A source that rated its
    own CPI print LOW keeps that rating.
    """
    events = (
        _event(
            days=3,
            event_type=EventType.ECONOMIC,
            impact=EventImpact.LOW,
            title="US CPI y/y",
        ),
    )
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")

    assert calendar.events[0].macro_kind is MacroEventKind.CPI
    assert calendar.events[0].impact is EventImpact.LOW
    assert calendar.has_high_impact is False


@pytest.mark.asyncio
async def test_next_high_impact_is_not_merely_the_soonest_event():
    """
    The bug this property exists to prevent: a soft dividend on day 1 and a
    high-impact CPI on day 3. ``next_event`` is the dividend, so anything
    warning about the risk must not name it.
    """
    events = (
        _event(days=1, event_type=EventType.DIVIDEND, impact=EventImpact.LOW),
        _event(
            days=3,
            event_type=EventType.ECONOMIC,
            impact=EventImpact.HIGH,
            title="US CPI y/y",
        ),
    )
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")

    assert calendar.next_event is not None
    assert calendar.next_event.event_type is EventType.DIVIDEND
    assert calendar.next_high_impact is not None
    assert calendar.next_high_impact.macro_kind is MacroEventKind.CPI


@pytest.mark.asyncio
async def test_a_calendar_with_no_high_impact_event_has_none_to_name():
    events = (_event(days=3, impact=EventImpact.LOW),)
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")
    assert calendar.next_high_impact is None


@pytest.mark.asyncio
async def test_the_high_impact_limitation_names_the_release():
    events = (
        _event(
            days=3,
            event_type=EventType.ECONOMIC,
            impact=EventImpact.HIGH,
            title="US CPI y/y",
        ),
    )
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")

    assert any("high-impact CPI release" in lim for lim in calendar.limitations)


@pytest.mark.asyncio
async def test_an_unnamed_release_keeps_the_generic_wording():
    """
    Coverage is deliberately partial: a release the taxonomy does not name is
    still warned about, just without a name it does not have.
    """
    events = (
        _event(
            days=3,
            event_type=EventType.ECONOMIC,
            impact=EventImpact.HIGH,
            title="US Retail Sales m/m",
        ),
    )
    calendar = await _service(FakeCalendarProvider(events)).get_events("AAPL")

    assert calendar.events[0].macro_kind is MacroEventKind.UNKNOWN
    assert any(
        "A high-impact event falls within" in lim for lim in calendar.limitations
    )


@pytest.mark.asyncio
async def test_the_published_event_carries_the_release_that_carries_the_risk():
    received: list[MarketEventsDetected] = []
    bus = EventBus()
    await bus.subscribe(MarketEventsDetected, lambda e: received.append(e))

    events = (
        _event(days=1, event_type=EventType.DIVIDEND, impact=EventImpact.LOW),
        _event(
            days=3,
            event_type=EventType.ECONOMIC,
            impact=EventImpact.HIGH,
            title="US CPI y/y",
        ),
    )
    await _service(FakeCalendarProvider(events), event_bus=bus).get_events("AAPL")

    assert len(received) == 1
    assert received[0].next_high_impact_kind == "cpi"


@pytest.mark.asyncio
async def test_a_non_macro_event_publishes_no_release_kind():
    received: list[MarketEventsDetected] = []
    bus = EventBus()
    await bus.subscribe(MarketEventsDetected, lambda e: received.append(e))

    events = (_event(days=3, impact=EventImpact.HIGH),)  # EARNINGS by default
    await _service(FakeCalendarProvider(events), event_bus=bus).get_events("AAPL")

    assert received[0].next_high_impact_kind == ""
