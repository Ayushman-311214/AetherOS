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

from dataclasses import replace
from datetime import UTC, datetime

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..calendar.macro import classify
from ..domain.enums import DataQualityStatus
from ..domain.event_calendar import (
    EventCalendar,
    EventType,
    MacroEventKind,
    MarketEvent,
)
from ..domain.instrument import Instrument
from ..domain.provenance import DataQuality, Provenance
from ..errors import CalendarError
from ..events import MarketEventsDetected, NewsImpactDetected
from ..providers.calendar_base import CalendarProvider

logger = get_logger("trading.calendar")

_MOCK_LIMITATION = (
    "Event calendar rests on synthetic MOCK entries (SourceTier.MOCK) — not a "
    "real earnings/economic calendar. The events are illustrative only and are "
    "not reliable."
)


def _release_label(event: MarketEvent) -> str:
    """
    How to name ``event`` inside a warning: ``"CPI release"``, else ``"event"``.

    An unnamed macro release (``UNKNOWN``) deliberately falls back to the generic
    word rather than dressing a non-answer up as a name.
    """
    kind = event.macro_kind
    if kind is not None and kind is not MacroEventKind.UNKNOWN:
        return f"{kind.value.replace('_', ' ').upper()} release"
    return "event"


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
        # Ids of high-impact events already announced as NewsImpactDetected, so
        # a repeated lookup re-announces a *new* event, never the same page twice.
        self._announced: set[str] = set()

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
        reference = datetime.now(UTC)
        is_mock = self._provider.is_mock
        tier = self._provider.tier

        # Defensive: keep events soonest-first regardless of provider ordering.
        # Classification happens here rather than in a provider so that *every*
        # provider is named for free -- the mock today, and a real macro feed the
        # day one lands behind the same CalendarProvider ABC.
        ordered = tuple(
            sorted(
                (self._classify(event) for event in events),
                key=lambda e: e.scheduled_at,
            )
        )
        next_high_impact = next((e for e in ordered if e.is_high_impact), None)
        has_high_impact = next_high_impact is not None

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
            is_mock=is_mock,
            count=len(ordered),
            next_high_impact=next_high_impact,
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
    def _classify(event: MarketEvent) -> MarketEvent:
        """
        Name the macro release an ``ECONOMIC`` event refers to.

        Only ``ECONOMIC`` events are classified: an earnings date or a dividend
        already *is* its type and gains nothing from a second label. The impact
        the provider reported is deliberately left untouched -- this taxonomy
        names a release, and filling in a canonical impact where the source said
        ``UNKNOWN`` would be inventing sourced data rather than labelling it.
        """
        if event.event_type is not EventType.ECONOMIC:
            return event
        read = classify(f"{event.title} {event.detail}".strip())
        return replace(event, macro_kind=read.kind)

    @staticmethod
    def _build_limitations(
        *,
        is_mock: bool,
        count: int,
        next_high_impact: MarketEvent | None,
    ) -> tuple[str, ...]:
        limitations: list[str] = []
        if is_mock:
            limitations.append(_MOCK_LIMITATION)
        if count == 0 and not is_mock:
            limitations.append(
                "No scheduled events were found in the horizon; event risk "
                "appears low, but a gap in coverage cannot be ruled out."
            )
        if next_high_impact is not None and not is_mock:
            # Name the release that actually carries the risk. ``next_event``
            # would be the wrong one whenever a softer event sits sooner.
            limitations.append(
                f"A high-impact {_release_label(next_high_impact)} falls within "
                "the prediction horizon; a price-derived signal may be "
                "invalidated by its outcome."
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
        risk = calendar.next_high_impact
        kind = risk.macro_kind if risk is not None else None
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
                    next_high_impact_kind=(
                        kind.value
                        if kind is not None and kind is not MacroEventKind.UNKNOWN
                        else ""
                    ),
                    is_reliable=calendar.is_reliable,
                    source_tier=calendar.provenance.tier.value,
                )
            )
        except Exception:  # event delivery must never break the lookup
            logger.exception("Failed to publish MarketEventsDetected")

        # Announce each genuinely high-impact event once, as its own pageable
        # item rather than buried inside the batch. Mock data is excluded so a
        # synthetic entry can never trigger a real alert.
        if not calendar.is_reliable:
            return
        for event in calendar.events:
            if not event.is_high_impact or event.id in self._announced:
                continue
            self._announced.add(event.id)
            try:
                await self._event_bus.publish(
                    NewsImpactDetected(
                        instrument_key=calendar.instrument.key,
                        kind=self._kind_label(event),
                        title=event.title,
                        scheduled_at=event.scheduled_at.isoformat(),
                        direction="unknown",
                        is_reliable=True,
                        source_tier=calendar.provenance.tier.value,
                    )
                )
            except Exception:
                logger.exception("Failed to publish NewsImpactDetected")

    @staticmethod
    def _kind_label(event: MarketEvent) -> str:
        """The news-impact kind for one event, honest about what it is."""
        if event.event_type is EventType.ECONOMIC:
            kind = event.macro_kind
            if kind is not None and kind is not MacroEventKind.UNKNOWN:
                return kind.value
            return "economic_release"
        return event.event_type.value
