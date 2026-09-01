from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

#: Invoked from the detector's own thread when the wake word fires.
WakeCallback = Callable[[], None]


class VoiceActivator(ABC):
    """
    Abstract activation source for the voice pipeline.

    An activator decides *when* AetherOS should start listening.
    Push-to-talk is the reliable default; a wake-word engine is an
    interchangeable alternative.

    Always-listening is never mandatory: a activator may legitimately
    never fire, and the user must be able to disable it entirely.
    """

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Activator name, e.g. "push-to-talk".
        """
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """
        Whether the activator is currently armed.
        """
        ...

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @abstractmethod
    async def start(self, on_activate: WakeCallback) -> None:
        """
        Arm the activator.

        `on_activate` may be invoked from a foreign thread, so
        implementations must document their threading model and
        callers must marshal back onto the event loop.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Disarm the activator and release any OS hooks.
        """
        ...


__all__ = [
    "VoiceActivator",
    "WakeCallback",
]
