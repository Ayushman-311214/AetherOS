"""
Yahoo Finance event-calendar provider.

The first *real* event-calendar source in AetherOS. It reads scheduled corporate
events -- the next earnings date(s), the ex-dividend date and the dividend
payment date -- from Yahoo's public ``quoteSummary`` ``calendarEvents`` module
over HTTPS, behind the same :class:`CalendarProvider` interface the mock uses, so
the critic's event-risk check and the composed report work unchanged -- but now
on real scheduled dates rather than a seeded synthetic catalog (spec sections 5,
9, 30).

Honesty guarantees (spec sections 5, 9, 20, 28, 61):

* It is ``SourceTier.SECONDARY``, never PRIMARY: Yahoo is a free, aggregated
  feed, not the issuer's own filing, and the tier says so. It is never ``MOCK``.
* It **never fabricates**. A network error, a non-200 response, an error object
  in the payload, a non-JSON body or a missing result raises a typed
  :class:`CalendarError`. It does not invent dates.
* A scheduled event is sourced fact, never a claim about what price will do
  (sections 3, 15). Any date Yahoo does not report is simply absent -- no event
  is emitted for it -- and an instrument with no scheduled events in the horizon
  yields an empty tuple, a legitimate honest "clear calendar", not a failure.
* It filters to the forward horizon only: events already in the past are dropped
  (a past earnings date is not a scheduled upcoming event).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from ..domain.enums import SourceTier
from ..domain.event_calendar import EventImpact, EventType, MarketEvent
from ..domain.instrument import Instrument
from ..domain.provenance import Provenance
from ..errors import CalendarError
from .calendar_base import CalendarProvider
from .yahoo_provider import _EXCHANGE_SUFFIX  # single source of truth for suffixes

_DEFAULT_BASE_URL = "https://query1.finance.yahoo.com"

# A browser-like User-Agent: the public endpoint rejects some default clients.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

_MODULES = "calendarEvents"


class YahooCalendarProvider(CalendarProvider):
    """Real scheduled corporate events from Yahoo's public quoteSummary endpoint."""

    name = "yahoo"
    tier = SourceTier.SECONDARY

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ) -> None:
        # An injected client (owned by the caller) makes this provider testable
        # with httpx.MockTransport and lets a host share one connection pool. If
        # none is given we open and close a client per request.
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Symbol mapping (shares the market provider's exchange suffix table)
    # ------------------------------------------------------------------

    @staticmethod
    def _yahoo_symbol(instrument: Instrument) -> str:
        suffix = ""
        if instrument.exchange:
            suffix = _EXCHANGE_SUFFIX.get(instrument.exchange, "")
        return f"{instrument.symbol}{suffix}"

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def _fetch_summary(self, symbol: str) -> dict:
        url = f"{self._base_url}/v10/finance/quoteSummary/{symbol}"
        params: dict[str, object] = {"modules": _MODULES}
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.get(url, params=params, headers=_HEADERS)
        except httpx.HTTPError as exc:
            raise CalendarError(
                f"Yahoo calendar request failed for '{symbol}': {exc}",
                context={"symbol": symbol},
                cause=exc,
            ) from exc
        finally:
            if self._client is None:
                await client.aclose()

        if resp.status_code != 200:
            raise CalendarError(
                f"Yahoo returned HTTP {resp.status_code} for '{symbol}'.",
                context={"symbol": symbol, "status": resp.status_code},
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            raise CalendarError(
                f"Yahoo returned a non-JSON response for '{symbol}'.",
                context={"symbol": symbol},
                cause=exc,
            ) from exc

        summary = payload.get("quoteSummary") if isinstance(payload, dict) else None
        if not isinstance(summary, dict):
            raise CalendarError(
                f"Unexpected Yahoo payload shape for '{symbol}'.",
                context={"symbol": symbol},
            )
        error = summary.get("error")
        if error:
            desc = error.get("description") if isinstance(error, dict) else error
            raise CalendarError(
                f"Yahoo reported an error for '{symbol}': {desc}",
                context={"symbol": symbol},
            )
        results = summary.get("result")
        if not results:
            raise CalendarError(
                f"Yahoo returned no calendar for '{symbol}'.",
                context={"symbol": symbol},
            )
        return results[0]

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamps(value: object) -> list[datetime]:
        """
        Extract unix-timestamp dates from a calendarEvents field.

        Yahoo carries a date as ``{"raw": 1234567890}`` and a date *range* (used
        for an estimated earnings window) as a list of such objects. A missing or
        non-numeric entry contributes nothing -- never a fabricated date.
        """
        items = value if isinstance(value, list) else [value]
        out: list[datetime] = []
        for item in items:
            raw = item.get("raw") if isinstance(item, dict) else item
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                continue
            try:
                out.append(datetime.fromtimestamp(int(raw), tz=timezone.utc))
            except (OverflowError, OSError, ValueError):
                continue
        return out

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    async def get_events(
        self,
        instrument: Instrument,
        *,
        horizon_days: int,
    ) -> tuple[MarketEvent, ...]:
        if horizon_days <= 0:
            raise ValueError("horizon_days must be positive.")

        symbol = self._yahoo_symbol(instrument)
        result = await self._fetch_summary(symbol)
        calendar = result.get("calendarEvents") or {}
        earnings = calendar.get("earnings") or {}

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=horizon_days)
        provenance = Provenance(
            source=self.name,
            tier=self.tier,
            detail="Yahoo Finance calendarEvents",
        )

        # (raw-field, event-type, impact, title, detail) for each scheduled date.
        # Earnings is the canonical high-impact event; dividend dates are softer.
        specs: list[tuple[list[datetime], EventType, EventImpact, str, str]] = [
            (
                self._timestamps(earnings.get("earningsDate")),
                EventType.EARNINGS,
                EventImpact.HIGH,
                f"{instrument.symbol} earnings date",
                "Scheduled/estimated earnings date reported by Yahoo.",
            ),
            (
                self._timestamps(calendar.get("exDividendDate")),
                EventType.DIVIDEND,
                EventImpact.MEDIUM,
                f"{instrument.symbol} ex-dividend date",
                "Ex-dividend date reported by Yahoo.",
            ),
            (
                self._timestamps(calendar.get("dividendDate")),
                EventType.DIVIDEND,
                EventImpact.LOW,
                f"{instrument.symbol} dividend payment date",
                "Dividend payment date reported by Yahoo.",
            ),
        ]

        events: list[MarketEvent] = []
        seen: set[str] = set()
        for dates, event_type, impact, title, detail in specs:
            for when in dates:
                # Forward horizon only: a date already past is not an upcoming
                # scheduled event, and one beyond the horizon is out of scope.
                if when < now or when > cutoff:
                    continue
                event = MarketEvent(
                    instrument_key=instrument.key,
                    event_type=event_type,
                    title=title,
                    scheduled_at=when,
                    impact=impact,
                    provenance=provenance,
                    detail=detail,
                )
                # An estimated earnings range can repeat a date; dedupe by id.
                if event.id in seen:
                    continue
                seen.add(event.id)
                events.append(event)

        events.sort(key=lambda e: e.scheduled_at)
        return tuple(events)
