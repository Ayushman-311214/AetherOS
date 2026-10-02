"""
Event / economic-calendar service.

Fetches scheduled events through an injected :class:`CalendarProvider` and fuses
them into a single auditable :class:`EventCalendar` for one instrument and one
horizon: the events inside the window, whether any is high-impact, and -- like
every other analysis object -- an honest ``is_reliable`` gate plus
``limitations`` (spec sections 5, 9, 26).

The honesty discipline of the rest of the domain holds here: a scheduled event
is sourced data, never a claim about what price will do (section 15); a MOCK
calendar can never masquerade as a real one (sections 2, 28, 61); and the
service performs no LLM call and invents no events -- an empty calendar is a
legitimate "no scheduled event risk" result, distinct from a failure.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import DataQualityStatus
from ..domain.event_calendar import EventCalendar, MarketEvent
from ..domain.instrument import Instrument
from ..domain.provenance import DataQuality, Provenance
from ..errors import CalendarError
from ..events import MarketEventsDetected
from ..providers.calendar_base import CalendarProvider

logger = get_logger("trading.calendar")

_MOCK_LIMITATION = (
    "Event calendar rests on synthetic MOCK entries (SourceTier.MOCK) — not a "
    "real earnings/economic calendar. The events are illustrative only and are "
    "not reliable."
)


class EventCalendarService:
    """Deterministic scheduled-event lookup for one instrument and horizon."""

    def __init__(
        self,
        provider: CalendarProvider,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._event_bus = event_bus

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def is_mock(self) -> bool:
        return self._provider.is_mock

    async def get_events(
        self,
        symbol: str | Instrument,
        *,
        horizon_days: int | None = None,
    ) -> EventCalendar:
        instrument = self._coerce_instrument(symbol)
        horizon = self._coerce_horizon(horizon_days)

        try:
            events = await self._provider.get_events(
                instrument, horizon_days=horizon
            )
        except CalendarError:
            raise
        except Exception as exc:  # provider misbehaved -> typed, honest error
            raise CalendarError(
                f"Calendar provider '{self._provider.name}' failed for "
                f"{instrument.key}.",
                context={"symbol": instrument.symbol},
                cause=exc,
            ) from exc

        calendar = self._build(instrument, events, horizon)
        await self._emit(calendar)
        return calendar

    # ------------------------------------------------------------------
    # Aggregation (pure, deterministic)
    # ------------------------------------------------------------------

    def _build(
        self,
        instrument: Instrument,
        events: tuple[MarketEvent, ...],
        horizon: int,
    ) -> EventCalendar:
        reference = datetime.now(timezone.utc)
        is_mock = self._provider.is_mock
        tier = self._provider.tier

        # Defensive: keep events soonest-first regardless of provider ordering.
        ordered = tuple(sorted(events, key=lambda e: e.scheduled_at))
        has_high_impact = any(e.is_high_impact for e in ordered)

        provenance = Provenance(
            source=self._provider.name,
            tier=tier,
            detail="scheduled event lookup within the prediction horizon",
        )

        # An empty calendar is an honest, usable result ("no scheduled events" =
        # no event risk), so quality is OK even with zero events; only a MOCK
        # feed carries an explicit synthetic-data issue that propagates onward.
        issues: list[str] = []
        if is_mock:
            issues.append(_MOCK_LIMITATION)
        quality = DataQuality(
            status=DataQualityStatus.OK, issues=tuple(issues), freshness_seconds=0.0
        )

        is_reliable = quality.usable and not is_mock
        limitations = self._build_limitations(
            is_mock=is_mock, count=len(ordered), has_high_impact=has_high_impact
        )

        return EventCalendar(
            instrument=instrument,
            events=ordered,
            horizon_days=horizon,
            reference_time=reference,
            has_high_impact=has_high_impact,
            provenance=provenance,
            quality=quality,
            is_reliable=is_reliable,
            limitations=limitations,
        )

    @staticmethod
    def _build_limitations(
        *, is_mock: bool, count: int, has_high_impact: bool
    ) -> tuple[str, ...]:
        limitations: list[str] = []
        if is_mock:
            limitations.append(_MOCK_LIMITATION)
        if count == 0 and not is_mock:
            limitations.append(
                "No scheduled events were found in the horizon; event risk "
                "appears low, but a gap in coverage cannot be ruled out."
            )
        if has_high_impact and not is_mock:
            limitations.append(
                "A high-impact event falls within the prediction horizon; a "
                "price-derived signal may be invalidated by its outcome."
            )
        return tuple(limitations)

    # ------------------------------------------------------------------
    # Coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_instrument(symbol: str | Instrument) -> Instrument:
        if isinstance(symbol, Instrument):
            return symbol
        try:
            return Instrument.parse(symbol)
        except ValueError as exc:
            raise CalendarError(str(exc), context={"symbol": symbol}) from exc

    def _coerce_horizon(self, horizon_days: int | None) -> int:
        default = self._settings.TRADING_EVENT_HORIZON_DAYS
        if horizon_days is None:
            return default
        if horizon_days <= 0:
            raise CalendarError(
                "horizon_days must be a positive integer.",
                context={"horizon_days": horizon_days},
            )
        return horizon_days

    async def _emit(self, calendar: EventCalendar) -> None:
        if self._event_bus is None:
            return
        nxt = calendar.next_event
        try:
            await self._event_bus.publish(
                MarketEventsDetected(
                    instrument_key=calendar.instrument.key,
                    horizon_days=calendar.horizon_days,
                    event_count=calendar.event_count,
                    has_high_impact=calendar.has_high_impact,
                    next_event_type=(nxt.event_type.value if nxt else ""),
                    next_event_days=(
                        nxt.days_until(calendar.reference_time) if nxt else None
                    ),
                    is_reliable=calendar.is_reliable,
                    source_tier=calendar.provenance.tier.value,
                )
            )
        except Exception:  # event delivery must never break the lookup
            logger.exception("Failed to publish MarketEventsDetected")
