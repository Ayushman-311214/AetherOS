"""
Alert router (spec Phase 23).

The decoupling point: ``Alert -> AlertRouter -> DeliveryProvider``. The router
takes a finished :class:`Alert` and fans it out to the registered providers
for the channels the alert named, returning one :class:`DeliveryResult` per
channel attempted. It owns no notion of *why* an alert exists (that is the
rules layer) and no notion of *how* any channel sends (that is a provider) --
so trading logic can raise alerts, and delivery mechanisms can be added or
swapped, without either knowing about the other.

Guarantees, all structural:

* **One result per requested channel, always.** A channel the alert named but
  that has no registered provider yields ``delivered=False`` with the reason
  "no provider registered" -- an unroutable alert is reported, never dropped.
* **A dead channel never blocks the others.** Each provider is awaited inside
  its own guard; a provider that raises is turned into a failed result and the
  remaining channels are still attempted.
* **No default fan-out.** An alert that named no channels is delivered to the
  router's configured default channel if one exists, else returned as routed
  nowhere -- the router never invents a destination.
"""

from __future__ import annotations

from ...core.logging import get_logger
from .domain import Alert, DeliveryChannel
from .providers import DeliveryProvider, DeliveryResult

logger = get_logger("trading.alerts")


class AlertRouter:
    """Fans an alert out to the delivery providers for its channels."""

    def __init__(
        self,
        *,
        default_channel: DeliveryChannel | None = DeliveryChannel.DESKTOP,
    ) -> None:
        self._providers: dict[DeliveryChannel, DeliveryProvider] = {}
        self._default_channel = default_channel

    def register(self, provider: DeliveryProvider) -> None:
        """
        Register ``provider`` for its declared channel.

        One provider per channel: registering a second replaces the first, so
        wiring is last-wins and never silently doubles delivery.
        """
        self._providers[provider.channel] = provider

    @property
    def channels(self) -> tuple[DeliveryChannel, ...]:
        return tuple(self._providers)

    async def route(self, alert: Alert) -> tuple[DeliveryResult, ...]:
        """
        Deliver ``alert`` to each of its channels, one result per channel.

        Falls back to the configured default channel when the alert named
        none. Returns an empty tuple only when the alert named no channels and
        there is no default -- an explicit "routed nowhere", not a silent drop.
        """
        targets = alert.channels or self._fallback_channels()
        if not targets:
            logger.debug(
                "Alert %s named no channels and no default is set; routed nowhere.",
                alert.alert_id,
            )
            return ()

        results: list[DeliveryResult] = []
        for channel in targets:
            provider = self._providers.get(channel)
            if provider is None:
                results.append(
                    DeliveryResult(
                        channel=channel,
                        delivered=False,
                        detail="no provider registered for this channel",
                        provider="",
                    )
                )
                continue
            results.append(await self._deliver(provider, alert))
        return tuple(results)

    # ------------------------------------------------------------------

    def _fallback_channels(self) -> tuple[DeliveryChannel, ...]:
        if self._default_channel is None:
            return ()
        return (self._default_channel,)

    async def _deliver(
        self, provider: DeliveryProvider, alert: Alert
    ) -> DeliveryResult:
        try:
            return await provider.deliver(alert)
        except Exception as exc:  # noqa: BLE001 -- one dead channel must not stop others
            logger.exception(
                "Delivery provider '%s' failed for alert %s",
                provider.name,
                alert.alert_id,
            )
            return DeliveryResult(
                channel=provider.channel,
                delivered=False,
                detail=f"provider raised: {exc}",
                provider=provider.name,
            )
