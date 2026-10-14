from __future__ import annotations

from .base_error import BaseError, ErrorContext


class VoiceError(BaseError):
    """
    Base exception for all voice-subsystem errors.

    Examples:
        - Microphone unavailable
        - Invalid audio device
        - Speech recognition failed
        - Speech synthesis failed
        - Audio playback failed
    """

    ERROR_PREFIX = "VOICE"

    def __init__(
        self,
        *,
        code: str,
        message: str,
        hint: str | None = None,
        context: ErrorContext | None = None,
        cause: Exception | None = None,
    ) -> None:

        if not code.startswith(self.ERROR_PREFIX):
            code = f"{self.ERROR_PREFIX}_{code}"

        if context is None:
            context = ErrorContext(module="voice")

        super().__init__(
            code=code,
            message=message,
            hint=hint,
            context=context,
            cause=cause,
        )


class AudioDeviceError(VoiceError):
    """
    The requested audio device is missing or cannot be opened.
    """


class MicrophoneUnavailableError(AudioDeviceError):
    """
    Microphone capture could not be started.

    AetherOS must remain usable without a microphone, so callers
    are expected to degrade to text input rather than abort.
    """


class SpeechToTextError(VoiceError):
    """
    Transcription failed, or the STT model could not be loaded.
    """


class TextToSpeechError(VoiceError):
    """
    Speech synthesis or audio playback failed.
    """


class WakeWordError(VoiceError):
    """
    The wake-word engine failed to initialize or detect.
    """


__all__ = [
    "AudioDeviceError",
    "MicrophoneUnavailableError",
    "SpeechToTextError",
    "TextToSpeechError",
    "VoiceError",
    "WakeWordError",
]
