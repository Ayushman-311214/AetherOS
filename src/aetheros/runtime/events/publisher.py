from __future__ import annotations

from runtime.events.event_bus import EventBus
from runtime.events.events import Event

_event_bus: EventBus | None = None


def set_event_bus(event_bus: EventBus) -> None:
    """
    Set the global EventBus instance.

    This should be called once during application bootstrap.
    """
    global _event_bus
    _event_bus = event_bus


def get_event_bus() -> EventBus:
    """
    Returns the configured EventBus.

    Raises:
        RuntimeError: If EventBus has not been initialized.
    """
    if _event_bus is None:
        raise RuntimeError(
            "EventBus has not been initialized. "
            "Call set_event_bus() during bootstrap."
        )

    return _event_bus


async def publish(event: Event) -> None:
    """
    Publish an event using the global EventBus.
    """
    await get_event_bus().publish(event)