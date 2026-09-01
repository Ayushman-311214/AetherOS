from __future__ import annotations

import asyncio

from ...core.interfaces.text_to_speech import (
    AmplitudeCallback,
    TextToSpeech,
)
from ...core.logging.logging import get_logger


class NullTTS(TextToSpeech):
    """
    Speech synthesis that produces no sound.

    Selected when the user disables spoken output, and when every real
    provider fails to initialize. The text response still reaches the
    CLI and the HUD, so AetherOS stays usable.
    """

    def __init__(
        self,
        *,
        reason: str = "Speech synthesis is disabled.",
    ) -> None:

        self._reason = reason
        self._logger = get_logger("voice.tts.null")

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return "null"

    @property
    def reason(self) -> str:
        return self._reason

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def initialize(self) -> None:
        self._logger.info(f"Speech synthesis disabled: {self._reason}")

    async def shutdown(self) -> None:
        return None

    # ==========================================================
    # Synthesis
    # ==========================================================

    async def speak(
        self,
        text: str,
        *,
        on_amplitude: AmplitudeCallback | None = None,
    ) -> None:
        return None

    async def stop(self) -> None:
        return None

    # ==========================================================
    # State
    # ==========================================================

    @property
    def is_speaking(self) -> bool:
        return False


class RecordingTTS(TextToSpeech):
    """
    Records what would have been spoken.

    The test double for speech output: it takes a configurable amount
    of simulated time, emits a synthetic amplitude envelope so HUD
    animation can be exercised, and honours cancellation.
    """

    def __init__(
        self,
        *,
        duration: float = 0.0,
    ) -> None:

        self._duration = duration

        self.spoken: list[str] = []
        self.stopped = 0
        self.initialized = False

        self._speaking = False

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return "recording"

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.initialized = False

    # ==========================================================
    # Synthesis
    # ==========================================================

    async def speak(
        self,
        text: str,
        *,
        on_amplitude: AmplitudeCallback | None = None,
    ) -> None:

        self.spoken.append(text)

        self._speaking = True

        try:
            if on_amplitude is not None:
                on_amplitude(0.6)

            if self._duration > 0:
                await asyncio.sleep(self._duration)

        finally:
            self._speaking = False

            if on_amplitude is not None:
                on_amplitude(0.0)

    async def stop(self) -> None:
        self.stopped += 1

    # ==========================================================
    # State
    # ==========================================================

    @property
    def is_speaking(self) -> bool:
        return self._speaking


__all__ = [
    "NullTTS",
    "RecordingTTS",
]
