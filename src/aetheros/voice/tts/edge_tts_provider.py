from __future__ import annotations

import asyncio

from ...core.errors.voice_error import TextToSpeechError
from ...core.interfaces.text_to_speech import (
    AmplitudeCallback,
    TextToSpeech,
)
from ...core.logging.logging import get_logger
from ..audio import AudioPlayer
from ..config import VoiceConfig
from .decode import decode_mp3


class EdgeTTS(TextToSpeech):
    """
    Neural speech synthesis via Microsoft Edge's read-aloud voices.

    Chosen because it is free, needs no API key, and sounds far better
    than an offline formant synthesizer. It does require an internet
    connection, so `SapiTTS` is the offline fallback.

    Audio arrives as MP3, is decoded to PCM, and is played through the
    shared AudioPlayer so that real amplitude data drives the HUD.
    """

    def __init__(
        self,
        config: VoiceConfig,
        player: AudioPlayer,
    ) -> None:

        self._config = config
        self._player = player
        self._logger = get_logger("voice.tts.edge")

        self._speaking = False
        self._cancelled = False

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return "edge-tts"

    @property
    def voice(self) -> str:
        return self._config.tts_voice

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def initialize(self) -> None:
        """
        Verify the library is importable.

        No connection is made here: a network check at startup would
        slow every launch, and synthesis failures are handled per-turn.
        """

        try:
            import edge_tts  # noqa: F401

        except Exception as exc:
            raise TextToSpeechError(
                code="001",
                message="edge-tts is not installed.",
                hint="Install it with: pip install edge-tts",
                cause=exc,
            ) from exc

        self._logger.info(
            f"Speech synthesis ready (edge-tts, voice={self._config.tts_voice})."
        )

    async def shutdown(self) -> None:
        await self.stop()

    # ==========================================================
    # Synthesis
    # ==========================================================

    async def speak(
        self,
        text: str,
        *,
        on_amplitude: AmplitudeCallback | None = None,
    ) -> None:
        """
        Synthesize and play `text`.
        """

        spoken = text.strip()

        if not spoken:
            return

        self._cancelled = False
        self._speaking = True

        try:
            audio = await self._synthesize(spoken)

            if self._cancelled:
                return

            samples, rate = decode_mp3(audio)

            if samples.size == 0:
                self._logger.warning("Synthesis produced no audio.")
                return

            await self._player.play(
                samples,
                rate,
                on_level=on_amplitude,
            )

        finally:
            self._speaking = False

    async def stop(self) -> None:
        self._cancelled = True

        await self._player.stop()

    # ==========================================================
    # State
    # ==========================================================

    @property
    def is_speaking(self) -> bool:
        return self._speaking or self._player.is_playing

    # ==========================================================
    # Internals
    # ==========================================================

    async def _synthesize(self, text: str) -> bytes:
        """
        Fetch MP3 audio for `text`.
        """

        import edge_tts

        try:
            communicate = edge_tts.Communicate(
                text,
                voice=self._config.tts_voice,
                rate=self._config.tts_rate,
                volume=self._config.tts_volume,
                pitch=self._config.tts_pitch,
            )

            buffer = bytearray()

            async for chunk in communicate.stream():

                if self._cancelled:
                    break

                if chunk.get("type") == "audio":
                    buffer.extend(chunk.get("data", b""))

            return bytes(buffer)

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            raise TextToSpeechError(
                code="002",
                message="Speech synthesis request failed.",
                hint=(
                    "edge-tts needs internet access. Set "
                    "AETHEROS_TTS_PROVIDER=sapi to synthesize offline."
                ),
                cause=exc,
            ) from exc


__all__ = ["EdgeTTS"]
