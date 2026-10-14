"""
Trading alerts (spec Phase 23).

A delivery-agnostic alerting layer wired as ``Alert -> AlertRouter ->
DeliveryProvider``. Trading services publish the same events they always have;
the :class:`AlertService` subscribes, turns events into :class:`Alert` objects
through pure rules, and routes them to the registered providers -- so alert
generation never couples to a notification provider, which is this phase's
acceptance criterion.
"""

from .domain import (
    Alert,
    AlertKind,
    AlertSeverity,
    DeliveryChannel,
)
from .providers import (
    CollectingDeliveryProvider,
    DeliveryProvider,
    DeliveryResult,
    LogDeliveryProvider,
)
from .router import AlertRouter
from .service import AlertService

__all__ = [
    "Alert",
    "AlertKind",
    "AlertRouter",
    "AlertService",
    "AlertSeverity",
    "CollectingDeliveryProvider",
    "DeliveryChannel",
    "DeliveryProvider",
    "DeliveryResult",
    "LogDeliveryProvider",
]
