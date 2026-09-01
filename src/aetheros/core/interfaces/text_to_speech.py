from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

#: Called with a normalized amplitude in [0, 1] while audio plays.
#:
#: Used to drive HUD animation. Implementations that cannot measure
#: amplitude simply never call it.
AmplitudeCallback = Callable[[float], None]


class TextToSpeech(ABC):
    """
    Abstract base class for all speech-synthesis providers.

    Implementations must be replaceable and cancellable.
    """

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider name, e.g. "edge-tts".
        """
        ...

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @abstractmethod
    async def initialize(self) -> None:
        """
        Acquire synthesis resources.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Release synthesis and playback resources.
        """
        ...

    # ==========================================================
    # Synthesis
    # ==========================================================

    @abstractmethod
    async def speak(
        self,
        text: str,
        *,
        on_amplitude: AmplitudeCallback | None = None,
    ) -> None:
        """
        Synthesize and play `text`, returning when playback ends.

        Must not block the event loop, and must raise
        asyncio.CancelledError promptly when cancelled.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop playback immediately.

        Safe to call when nothing is playing.
        """
        ...

    # ==========================================================
    # State
    # ==========================================================

    @property
    @abstractmethod
    def is_speaking(self) -> bool:
        """
        Whether audio is currently playing.
        """
        ...


__all__ = [
    "AmplitudeCallback",
    "TextToSpeech",
]
