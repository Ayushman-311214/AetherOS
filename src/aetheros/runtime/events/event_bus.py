from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from core.logging import get_logger
from runtime.events.events import Event

logger = get_logger("event_bus")

EventHandler = Callable[[Event], Any | Awaitable[Any]]


class EventBus:
    """
    Central event bus for AetherOS.

    Features:
    - Sync + Async handlers
    - Multiple subscribers
    - Exception isolation
    - Thread-safe registration
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    # ==========================================================
    # Subscribe
    # ==========================================================

    async def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> None:
        """
        Register an event handler.
        """

        async with self._lock:

            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

                logger.debug(
                    f"Subscribed '{handler.__name__}' "
                    f"to '{event_type.__name__}'"
                )

    # ==========================================================
    # Unsubscribe
    # ==========================================================

    async def unsubscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> None:

        async with self._lock:

            if handler in self._subscribers[event_type]:

                self._subscribers[event_type].remove(handler)

                logger.debug(
                    f"Unsubscribed '{handler.__name__}' "
                    f"from '{event_type.__name__}'"
                )

    # ==========================================================
    # Publish
    # ==========================================================

    async def publish(self, event: Event) -> None:
        """
        Publish an event.

        Every subscriber receives the event.
        """

        handlers = list(self._subscribers.get(type(event), []))

        if not handlers:
            logger.debug(f"No subscribers for {event.name}")
            return

        logger.info(
            f"Publishing {event.name} "
            f"to {len(handlers)} subscriber(s)"
        )

        for handler in handlers:

            try:

                if inspect.iscoroutinefunction(handler):

                    await handler(event)

                else:

                    handler(event)

            except Exception:

                logger.exception(
                    f"Handler '{handler.__name__}' "
                    f"failed while processing {event.name}"
                )

    # ==========================================================
    # Utilities
    # ==========================================================

    async def clear(self) -> None:

        async with self._lock:
            self._subscribers.clear()

    def listeners(
        self,
        event_type: type[Event],
    ) -> list[EventHandler]:

        return list(self._subscribers.get(event_type, []))

    def listener_count(
        self,
        event_type: type[Event],
    ) -> int:

        return len(self._subscribers.get(event_type, []))

    def event_types(self) -> list[type[Event]]:
        return list(self._subscribers.keys())