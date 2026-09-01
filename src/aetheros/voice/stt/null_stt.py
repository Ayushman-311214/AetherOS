from __future__ import annotations

import numpy as np

from ...core.interfaces.speech_to_text import SpeechToText, Transcript
from ...core.logging.logging import get_logger


class NullSTT(SpeechToText):
    """
    Speech recognition that never recognizes anything.

    Used when the user has disabled the microphone, when no capture
    device exists, and in tests. Keeping this behind the same
    interface means the pipeline needs no "is STT available" branches.
    """

    def __init__(
        self,
        *,
        reason: str = "Speech recognition is disabled.",
        sample_rate: int = 16_000,
    ) -> None:

        self._reason = reason
        self._sample_rate = sample_rate

        self._logger = get_logger("voice.stt.null")

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return "null"

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def reason(self) -> str:
        return self._reason

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def initialize(self) -> None:
        self._logger.info(f"Speech recognition disabled: {self._reason}")

    async def shutdown(self) -> None:
        return None

    # ==========================================================
    # Transcription
    # ==========================================================

    async def transcribe(
        self,
        audio: np.ndarray,
        *,
        sample_rate: int | None = None,
        language: str | None = None,
    ) -> Transcript:

        return Transcript(text="", language=language)


class ScriptedSTT(SpeechToText):
    """
    Returns queued phrases in order.

    This is the test double that lets the whole voice pipeline be
    exercised without a microphone, and it also backs the CLI's
    "voice say <text>" command for manual end-to-end checks.
    """

    def __init__(
        self,
        phrases: list[str] | None = None,
        *,
        sample_rate: int = 16_000,
    ) -> None:

        self._phrases: list[str] = list(phrases or [])
        self._sample_rate = sample_rate

        self.initialized = False
        self.calls = 0

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return "scripted"

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    # ==========================================================
    # Scripting
    # ==========================================================

    def queue(self, text: str) -> None:
        self._phrases.append(text)

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.initialized = False

    # ==========================================================
    # Transcription
    # ==========================================================

    async def transcribe(
        self,
        audio: np.ndarray,
        *,
        sample_rate: int | None = None,
        language: str | None = None,
    ) -> Transcript:

        self.calls += 1

        text = self._phrases.pop(0) if self._phrases else ""

        return Transcript(
            text=text,
            language=language or "en",
            confidence=1.0,
        )


__all__ = [
    "NullSTT",
    "ScriptedSTT",
]
