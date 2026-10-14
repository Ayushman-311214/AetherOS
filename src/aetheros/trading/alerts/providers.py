"""
Alert delivery providers (spec Phase 23).

A :class:`DeliveryProvider` is the narrow seam between an :class:`Alert` and
the outside world: given an alert, deliver it, and report whether it went.
The router (``router.py``) holds providers behind this interface and never
knows which concrete one it is talking to -- the decoupling the phase's
acceptance criterion demands.

Only two providers ship here, and neither sends anything over a network:

* :class:`LogDeliveryProvider` writes the alert to the structured log. It is
  the always-safe default -- no credentials, no I/O that can fail a desk's
  pipeline -- and it maps to the DESKTOP channel conceptually (the local
  machine) without pretending to raise an OS notification it cannot.
* :class:`CollectingDeliveryProvider` keeps delivered alerts in memory. It
  exists for tests and for a caller that wants to pull recent alerts (a TUI
  panel), not to notify anyone.

Email, Mobile, Discord and Telegram are named by :class:`DeliveryChannel` and
routed to by channel, but their network providers are deliberately deferred:
each needs a credential and an outbound integration that must not be stubbed
with a fake that silently drops messages. A channel with no registered
provider is reported as *undelivered with a reason*, never as a success.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ...core.logging import get_logger
from .domain import Alert, DeliveryChannel

logger = get_logger("trading.alerts")


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """What one provider did with one alert."""

    channel: DeliveryChannel
    delivered: bool
    detail: str
    provider: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel.value,
            "delivered": self.delivered,
            "detail": self.detail,
            "provider": self.provider,
        }


class DeliveryProvider(ABC):
    """One channel's delivery mechanism. Stateless from the router's view."""

    #: The channel this provider serves.
    channel: DeliveryChannel

    @property
    @abstractmethod
    def name(self) -> str:
        """A short, stable provider name for logs and audit."""

    @abstractmethod
    async def deliver(self, alert: Alert) -> DeliveryResult:
        """
        Deliver ``alert`` on this provider's channel.

        Must never raise for an ordinary delivery failure: a provider that
        cannot send reports ``delivered=False`` with a reason, so one dead
        channel never stops the router from trying the others.
        """


class LogDeliveryProvider(DeliveryProvider):
    """
    Delivers an alert by writing it to the structured log.

    The dependency-free default: always available, never a network call, and
    honest about being a log line rather than an OS toast.
    """

    channel = DeliveryChannel.DESKTOP

    @property
    def name(self) -> str:
        return "log"

    async def deliver(self, alert: Alert) -> DeliveryResult:
        logger.info(
            "ALERT [%s/%s] %s: %s",
            alert.kind.value,
            alert.severity.value,
            alert.title,
            alert.body,
            extra={"alert_id": alert.alert_id, "instrument": alert.instrument_key},
        )
        return DeliveryResult(
            channel=self.channel,
            delivered=True,
            detail="written to structured log",
            provider=self.name,
        )


class CollectingDeliveryProvider(DeliveryProvider):
    """
    Keeps delivered alerts in memory instead of sending them.

    For tests and for a local reader (a TUI alerts panel) that wants to pull
    what fired. It notifies no one and makes no I/O.
    """

    def __init__(self, channel: DeliveryChannel = DeliveryChannel.DESKTOP) -> None:
        self.channel = channel
        self._alerts: list[Alert] = []

    @property
    def name(self) -> str:
        return "collecting"

    @property
    def alerts(self) -> tuple[Alert, ...]:
        return tuple(self._alerts)

    async def deliver(self, alert: Alert) -> DeliveryResult:
        self._alerts.append(alert)
        return DeliveryResult(
            channel=self.channel,
            delivered=True,
            detail="collected in memory",
            provider=self.name,
        )
