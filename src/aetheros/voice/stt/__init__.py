from __future__ import annotations

from ...core.interfaces.speech_to_text import SpeechToText, Transcript
from ...core.logging.logging import get_logger
from ..config import VoiceConfig
from .faster_whisper_stt import FasterWhisperSTT
from .null_stt import NullSTT, ScriptedSTT

logger = get_logger("voice.stt")


#: Provider name -> factory. Adding an engine means adding a row.
_PROVIDERS = {
    "faster-whisper": "faster-whisper",
    "whisper": "faster-whisper",
    "null": "null",
    "none": "null",
    "disabled": "null",
    "scripted": "scripted",
}


def create_stt(config: VoiceConfig) -> SpeechToText:
    """
    Build the configured speech-recognition provider.

    An unknown provider name is a configuration mistake, not a crash:
    it falls back to faster-whisper with a warning.
    """

    requested = config.stt_provider.strip().lower()

    resolved = _PROVIDERS.get(requested)

    if resolved is None:
        logger.warning(
            f"Unknown STT provider '{config.stt_provider}'; using faster-whisper. "
            f"Valid values: {', '.join(sorted(set(_PROVIDERS)))}"
        )

        resolved = "faster-whisper"

    if resolved == "null":
        return NullSTT(
            reason="AETHEROS_STT_PROVIDER is set to 'null'.",
            sample_rate=config.sample_rate,
        )

    if resolved == "scripted":
        return ScriptedSTT(sample_rate=config.sample_rate)

    return FasterWhisperSTT(config)


__all__ = [
    "FasterWhisperSTT",
    "NullSTT",
    "ScriptedSTT",
    "SpeechToText",
    "Transcript",
    "create_stt",
]
