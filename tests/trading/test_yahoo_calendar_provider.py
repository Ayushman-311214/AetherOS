"""
YahooCalendarProvider: the first real event-calendar adapter.

These tests are fully deterministic and never touch the network: they drive the
provider through an ``httpx.MockTransport`` that returns canned Yahoo
``quoteSummary`` ``calendarEvents`` payloads (or failures). They pin the things
that matter for a real calendar source under the spec's honesty rules (CLAUDE.md
sections 5, 9, 20, 28, 61): it parses a real payload into correctly-shaped,
non-mock ``SourceTier.SECONDARY`` events; earnings is HIGH-impact and dividend
dates are softer; it filters to the forward horizon (past and out-of-range dates
are dropped); an instrument with nothing scheduled is an honest empty tuple
(a clear calendar, not a failure); and any failure raises a typed
:class:`CalendarError` rather than inventing dates.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from aetheros.trading.domain.enums import SourceTier
from aetheros.trading.domain.event_calendar import EventImpact, EventType
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.errors import CalendarError
from aetheros.trading.providers.yahoo_calendar_provider import YahooCalendarProvider


def _ts(days_from_now: float) -> int:
    """A unix timestamp ``days_from_now`` days from now (negative = past)."""
    when = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    return int(when.timestamp())


def _calendar_payload(
    *,
    earnings_date=None,
    ex_dividend_date=None,
    dividend_date=None,
    error=None,
    result_empty: bool = False,
    calendar_events: dict | None = None,
):
    """Build a Yahoo /v10/finance/quoteSummary calendarEvents-shaped payload."""
    if error is not None:
        return {"quoteSummary": {"result": None, "error": error}}
    if result_empty:
        return {"quoteSummary": {"result": [], "error": None}}
    if calendar_events is None:
        calendar_events = {}
        if earnings_date is not None:
            calendar_events["earnings"] = {"earningsDate": earnings_date}
        if ex_dividend_date is not None:
            calendar_events["exDividendDate"] = ex_dividend_date
        if dividend_date is not None:
            calendar_events["dividendDate"] = dividend_date
    return {
        "quoteSummary": {
            "result": [{"calendarEvents": calendar_events}],
            "error": None,
        }
    }


def _provider(handler) -> YahooCalendarProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return YahooCalendarProvider(client=client)


def _ok_handler(payload, *, capture: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(request)
        return httpx.Response(200, json=payload)

    return handler


@pytest.mark.asyncio
async def test_parses_real_payload_into_secondary_events():
    payload = _calendar_payload(
        earnings_date=[{"raw": _ts(5)}],
        ex_dividend_date={"raw": _ts(10)},
        dividend_date={"raw": _ts(20)},
    )
    provider = _provider(_ok_handler(payload))
    events = await provider.get_events(Instrument("AAPL"), horizon_days=30)

    assert len(events) == 3
    # Sorted soonest-first.
    assert [e.scheduled_at for e in events] == sorted(e.scheduled_at for e in events)
    # Every event is real, non-mock, SECONDARY.
    for event in events:
        assert event.provenance.tier is SourceTier.SECONDARY
        assert event.provenance.tier is not SourceTier.MOCK
        assert event.provenance.source == "yahoo"
        assert event.instrument_key == Instrument("AAPL").key

    earnings = next(e for e in events if e.event_type is EventType.EARNINGS)
    assert earnings.impact is EventImpact.HIGH
    dividends = [e for e in events if e.event_type is EventType.DIVIDEND]
    assert {e.impact for e in dividends} == {EventImpact.MEDIUM, EventImpact.LOW}


@pytest.mark.asyncio
async def test_past_events_are_dropped():
    # A past earnings date is not a scheduled *upcoming* event.
    payload = _calendar_payload(
        earnings_date=[{"raw": _ts(-3)}],
        ex_dividend_date={"raw": _ts(4)},
    )
    provider = _provider(_ok_handler(payload))
    events = await provider.get_events(Instrument("AAPL"), horizon_days=30)

    assert len(events) == 1
    assert events[0].event_type is EventType.DIVIDEND


@pytest.mark.asyncio
async def test_events_beyond_horizon_are_dropped():
    payload = _calendar_payload(
        earnings_date=[{"raw": _ts(3)}],
        dividend_date={"raw": _ts(45)},  # beyond a 7-day horizon
    )
    provider = _provider(_ok_handler(payload))
    events = await provider.get_events(Instrument("AAPL"), horizon_days=7)

    assert len(events) == 1
    assert events[0].event_type is EventType.EARNINGS


@pytest.mark.asyncio
async def test_estimated_earnings_range_dedupes_same_date():
    # Yahoo reports an estimated earnings window as a list; two entries that fall
    # on the same calendar day are one scheduled event, not two.
    same_day = _ts(6)
    payload = _calendar_payload(
        earnings_date=[{"raw": same_day}, {"raw": same_day + 3600}],
    )
    provider = _provider(_ok_handler(payload))
    events = await provider.get_events(Instrument("AAPL"), horizon_days=30)
    assert len(events) == 1


@pytest.mark.asyncio
async def test_empty_calendar_is_a_clear_calendar_not_an_error():
    # A result that parses but carries no scheduled dates is a legitimate honest
    # empty calendar (nothing scheduled), distinct from a failure.
    payload = _calendar_payload(calendar_events={})
    provider = _provider(_ok_handler(payload))
    events = await provider.get_events(Instrument("AAPL"), horizon_days=30)
    assert events == ()


@pytest.mark.asyncio
async def test_non_numeric_dates_are_ignored_not_fabricated():
    payload = _calendar_payload(
        earnings_date=[{"raw": None}, {"fmt": "soon"}],
        ex_dividend_date={"raw": "not-a-number"},
    )
    provider = _provider(_ok_handler(payload))
    events = await provider.get_events(Instrument("AAPL"), horizon_days=30)
    assert events == ()


@pytest.mark.asyncio
async def test_maps_exchange_to_yahoo_suffix():
    captured: list[httpx.Request] = []
    payload = _calendar_payload(earnings_date=[{"raw": _ts(5)}])
    provider = _provider(_ok_handler(payload, capture=captured))
    await provider.get_events(Instrument("RELIANCE", exchange="NSE"), horizon_days=30)
    assert captured, "no request captured"
    assert "RELIANCE.NS" in str(captured[0].url)


@pytest.mark.asyncio
async def test_non_positive_horizon_raises_value_error():
    provider = _provider(_ok_handler(_calendar_payload(calendar_events={})))
    with pytest.raises(ValueError):
        await provider.get_events(Instrument("AAPL"), horizon_days=0)


@pytest.mark.asyncio
async def test_http_error_becomes_calendar_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    provider = _provider(handler)
    with pytest.raises(CalendarError):
        await provider.get_events(Instrument("NOPE"), horizon_days=30)


@pytest.mark.asyncio
async def test_error_payload_becomes_calendar_error():
    payload = _calendar_payload(
        error={"code": "Not Found", "description": "No calendar for symbol"},
    )
    provider = _provider(_ok_handler(payload))
    with pytest.raises(CalendarError):
        await provider.get_events(Instrument("NOPE"), horizon_days=30)


@pytest.mark.asyncio
async def test_empty_result_becomes_calendar_error():
    payload = _calendar_payload(result_empty=True)
    provider = _provider(_ok_handler(payload))
    with pytest.raises(CalendarError):
        await provider.get_events(Instrument("AAPL"), horizon_days=30)


@pytest.mark.asyncio
async def test_network_error_becomes_calendar_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(handler)
    with pytest.raises(CalendarError):
        await provider.get_events(Instrument("AAPL"), horizon_days=30)
