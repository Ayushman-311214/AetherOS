from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(slots=True, frozen=True)
class Transcript:
    """
    Result of a speech-recognition request.
    """

    text: str
    language: str | None = None
    confidence: float | None = None
    duration: float = 0.0

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


class SpeechToText(ABC):
    """
    Abstract base class for all speech-recognition providers.

    Implementations must be replaceable: AetherOS depends on this
    interface, never on a concrete engine.
    """

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider name, e.g. "faster-whisper".
        """
        ...

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """
        Sample rate, in Hz, the provider expects audio in.
        """
        ...

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @abstractmethod
    async def initialize(self) -> None:
        """
        Load models and acquire resources.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Release model and resources.
        """
        ...

    # ==========================================================
    # Transcription
    # ==========================================================

    @abstractmethod
    async def transcribe(
        self,
        audio: np.ndarray,
        *,
        sample_rate: int | None = None,
        language: str | None = None,
    ) -> Transcript:
        """
        Transcribe mono float32 PCM audio in the range [-1, 1].

        Must not block the event loop.
        """
        ...


__all__ = [
    "SpeechToText",
    "Transcript",
]
