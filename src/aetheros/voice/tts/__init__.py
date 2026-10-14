from __future__ import annotations

from ...core.interfaces.text_to_speech import (
    AmplitudeCallback,
    TextToSpeech,
)
from ...core.logging.logging import get_logger
from ..audio import AudioPlayer
from ..config import VoiceConfig
from .edge_tts_provider import EdgeTTS
from .null_tts import NullTTS, RecordingTTS
from .sapi_tts import SapiTTS

logger = get_logger("voice.tts")


#: Alias -> canonical provider name.
_PROVIDERS = {
    "edge-tts": "edge-tts",
    "edge": "edge-tts",
    "sapi": "sapi",
    "windows": "sapi",
    "null": "null",
    "none": "null",
    "disabled": "null",
    "recording": "recording",
}


def create_tts(
    config: VoiceConfig,
    player: AudioPlayer,
) -> TextToSpeech:
    """
    Build the configured speech-synthesis provider.
    """

    requested = config.tts_provider.strip().lower()

    resolved = _PROVIDERS.get(requested)

    if resolved is None:
        logger.warning(
            f"Unknown TTS provider '{config.tts_provider}'; using edge-tts. Valid "
            f"values: {', '.join(sorted(set(_PROVIDERS)))}"
        )

        resolved = "edge-tts"

    if resolved == "null":
        return NullTTS(
            reason="AETHEROS_TTS_PROVIDER is set to 'null'.",
        )

    if resolved == "recording":
        return RecordingTTS()

    if resolved == "sapi":
        return SapiTTS(config, player)

    return EdgeTTS(config, player)


def fallback_chain(
    config: VoiceConfig,
    player: AudioPlayer,
) -> list[TextToSpeech]:
    """
    Providers to try, in order, when the preferred one fails.

    edge-tts needs the network and SAPI needs Windows, so neither can
    be guaranteed. Silence is always available, which keeps a failed
    voice from taking the text response down with it.
    """

    primary = create_tts(config, player)

    chain: list[TextToSpeech] = [primary]

    if isinstance(primary, EdgeTTS):
        chain.append(SapiTTS(config, player))

    elif isinstance(primary, SapiTTS):
        chain.append(EdgeTTS(config, player))

    if not isinstance(primary, NullTTS):
        chain.append(
            NullTTS(
                reason=(
                    "No speech-synthesis provider could be "
                    "initialized; responses remain text-only."
                ),
            )
        )

    return chain


__all__ = [
    "AmplitudeCallback",
    "EdgeTTS",
    "NullTTS",
    "RecordingTTS",
    "SapiTTS",
    "TextToSpeech",
    "create_tts",
    "fallback_chain",
]
