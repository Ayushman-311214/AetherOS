"""
Alert service (spec Phase 23).

Wires the three halves together without letting them know about each other:
it subscribes to the trading :class:`EventBus`, turns each event into an
:class:`Alert` via the pure rules in :mod:`rules`, and hands the alert to the
:class:`AlertRouter` for delivery. Trading services keep publishing the same
events they always did; none of them import this service, the router or any
provider -- so alert generation and delivery stay fully decoupled from the
logic that triggers them (the phase's acceptance criterion).

The service also exposes :meth:`raise_alert` for callers that build an alert
directly (an armed price watch, Phase 24's API), and keeps the most recent
alerts in a bounded ring so a local reader can pull what fired without a
delivery provider. It is observer-only on the bus: a rule or a delivery that
fails is logged and swallowed, never propagated back into the producer.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Awaitable, Callable

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ...runtime.events.events import Event
from ..events import (
    MarketEventsDetected,
    MarketRegimeDetected,
    NewsSentimentAnalyzed,
    RiskLimitReached,
    SignalGenerated,
)
from . import rules
from .domain import Alert, DeliveryChannel
from .providers import DeliveryResult
from .router import AlertRouter

logger = get_logger("trading.alerts")

# Event type -> the rule that turns it into an alert (or None). Each rule is
# pure; the service only dispatches on exact type, matching the EventBus.
_RULES: dict[type[Event], Callable[..., Alert | None]] = {
    SignalGenerated: rules.signal_alert,
    NewsSentimentAnalyzed: rules.news_alert,
    RiskLimitReached: rules.risk_alert,
    MarketEventsDetected: rules.event_risk_alert,
    MarketRegimeDetected: rules.regime_alert,
}


class AlertService:
    """Subscribes to trading events, generates alerts, routes them for delivery."""

    def __init__(
        self,
        router: AlertRouter,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
        default_channels: tuple[DeliveryChannel, ...] = (),
        history: int = 200,
    ) -> None:
        self._router = router
        self._settings = settings
        self._event_bus = event_bus
        self._default_channels = default_channels
        self._recent: deque[Alert] = deque(maxlen=max(1, history))
        self._subscribed_types: tuple[type[Event], ...] = ()
        self._subscribed = False

    @property
    def router(self) -> AlertRouter:
        return self._router

    def recent(self, limit: int | None = None) -> tuple[Alert, ...]:
        """The most recently generated alerts, newest last."""
        items = tuple(self._recent)
        if limit is not None:
            items = items[-limit:]
        return items

    async def start(self) -> None:
        """Subscribe to each event a rule covers. Idempotent."""
        if self._event_bus is None or self._subscribed:
            return
        try:
            handler = self._on_event
            for event_type in _RULES:
                await self._event_bus.subscribe(event_type, handler)
            self._subscribed_types = tuple(_RULES)
            self._subscribed = True
            logger.debug("Alert service subscribed to %d event type(s).", len(_RULES))
        except Exception:
            logger.exception("Alert service could not subscribe to the event bus.")

    async def stop(self) -> None:
        """Unsubscribe exactly what ``start`` registered."""
        if self._event_bus is None or not self._subscribed:
            return
        for event_type in self._subscribed_types:
            try:
                await self._event_bus.unsubscribe(event_type, self._on_event)
            except Exception:
                logger.debug("Could not unsubscribe alert service from %s.", event_type)
        self._subscribed = False
        self._subscribed_types = ()

    async def raise_alert(self, alert: Alert) -> tuple[DeliveryResult, ...]:
        """
        Route a pre-built alert directly (an armed price watch, the API layer).

        Records it in the recent ring and returns the per-channel results, so a
        caller that armed the watch can see where it went.
        """
        self._recent.append(alert)
        return await self._router.route(alert)

    # ------------------------------------------------------------------

    async def _on_event(self, event: Event) -> None:
        """Observer-only handler: an alert here must never break the producer."""
        try:
            rule = _RULES.get(type(event))
            if rule is None:
                return
            alert = rule(event, channels=self._default_channels)
            if alert is None:
                return
            self._recent.append(alert)
            await self._router.route(alert)
        except Exception:
            logger.exception(
                "Alert generation failed for %s; the producer is unaffected.",
                event.name,
            )


# A convenience alias so a type-hinted caller can resolve the handler shape.
AlertHandler = Callable[[Event], Awaitable[None]]
