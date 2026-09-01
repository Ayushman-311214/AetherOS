from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .events import Event

# Stores all decorated handlers
_SUBSCRIBERS: list[tuple[type[Event], Callable[..., Any]]] = []


def subscribe(event_type: type[Event]):
    """
    Decorator used to register an event handler.

    Example:
        @subscribe(ScreenCaptured)
        async def run_ocr(event):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _SUBSCRIBERS.append((event_type, func))
        return func

    return decorator


def get_subscribers() -> list[tuple[type[Event], Callable[..., Any]]]:
    """
    Returns all registered subscribers.
    """
    return list(_SUBSCRIBERS)


def clear_subscribers() -> None:
    """
    Removes every registered subscriber.

    Mainly useful for testing.
    """
    _SUBSCRIBERS.clear()