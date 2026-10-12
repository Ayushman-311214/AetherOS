"""
Alert domain objects (spec Phase 23).

An :class:`Alert` is an immutable, content-addressed notice that something a
caller asked to watch for happened. It is deliberately *delivery-agnostic*:
it names the channels it should reach (:class:`DeliveryChannel`) but knows
nothing about how any of them work, so alert generation never couples to a
notification provider (the phase's whole acceptance criterion). The router
and the providers downstream read these fields; they never reach back.

Honesty carries through here as everywhere else: an alert built from an event
that was flagged unreliable (mock or thin data) carries ``is_reliable=False``,
so a desk is never paged by a synthetic number dressed up as a real one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AlertKind(str, Enum):
    """What a trading alert is about (spec Phase 23 list)."""

    PRICE = "price"
    PATTERN = "pattern"
    SIGNAL = "signal"
    NEWS = "news"
    PORTFOLIO = "portfolio"


class AlertSeverity(str, Enum):
    """
    How loudly an alert asks to be heard.

    Ordered low -> high so a router or provider can gate on a floor
    ("deliver CRITICAL to mobile, everything to desktop") without hard-coding
    the set of kinds.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {"info": 0, "warning": 1, "critical": 2}[self.value]


class DeliveryChannel(str, Enum):
    """Where an alert can be delivered (spec Phase 23 delivery list)."""

    DESKTOP = "desktop"
    EMAIL = "email"
    MOBILE = "mobile"
    DISCORD = "discord"
    TELEGRAM = "telegram"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Alert:
    """
    One immutable, delivery-agnostic alert.

    ``id`` is content-addressed over the fields that define *what happened*
    (kind, instrument, title, body, severity, source event) -- deliberately
    not over the timestamp -- so the same condition reported twice is the same
    alert id, and a router can de-duplicate without a clock.
    """

    kind: AlertKind
    severity: AlertSeverity
    title: str
    body: str
    instrument_key: str | None = None
    channels: tuple[DeliveryChannel, ...] = ()
    source_event: str = ""
    is_reliable: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    alert_id: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("An alert needs a non-empty title.")
        if not self.body.strip():
            raise ValueError("An alert needs a non-empty body.")
        if not self.alert_id:
            seed = "|".join(
                (
                    self.kind.value,
                    self.severity.value,
                    self.instrument_key or "",
                    self.title,
                    self.body,
                    self.source_event,
                )
            )
            digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
            object.__setattr__(self, "alert_id", "alert_" + digest)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "kind": self.kind.value,
            "severity": self.severity.value,
            "title": self.title,
            "body": self.body,
            "instrument_key": self.instrument_key,
            "channels": [c.value for c in self.channels],
            "source_event": self.source_event,
            "is_reliable": self.is_reliable,
            "data": dict(self.data),
            "created_at": self.created_at.isoformat(),
        }
