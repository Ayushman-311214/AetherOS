from __future__ import annotations

import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ...core.errors.voice_error import TextToSpeechError
from ...core.interfaces.text_to_speech import (
    AmplitudeCallback,
    TextToSpeech,
)
from ...core.logging.logging import get_logger
from ..audio import AudioPlayer
from ..config import VoiceConfig
from .decode import decode_wav

#: SpFileStream open mode: create for write.
_SSFM_CREATE_FOR_WRITE = 3

#: SpeechVoiceSpeakFlags: purge anything already queued.
_SVSF_PURGE_BEFORE_SPEAK = 2

#: SpeechStreamFormat: 22.05 kHz, 16-bit, mono.
_SAFT_22KHZ_16BIT_MONO = 22


class SapiTTS(TextToSpeech):
    """
    Offline speech synthesis via the Windows Speech API.

    Uses pywin32, which AetherOS already depends on, so this needs no
    new package and no network access. Voice quality is lower than
    edge-tts, which is why it is the fallback rather than the default.

    SAPI renders into a temporary WAV file rather than straight to the
    speakers. That costs a few milliseconds but means playback goes
    through the shared AudioPlayer, so the HUD gets the same real
    amplitude data it gets from the neural voice.

    COM apartments are thread-affine, so every SAPI call is funnelled
    through one owned worker thread that is shut down explicitly.
    """

    def __init__(
        self,
        config: VoiceConfig,
        player: AudioPlayer,
    ) -> None:

        self._config = config
        self._player = player
        self._logger = get_logger("voice.tts.sapi")

        self._executor: ThreadPoolExecutor | None = None
        self._voice: Any = None

        self._speaking = False
        self._cancelled = False

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return "sapi"

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def initialize(self) -> None:
        """
        Create the COM voice object on its dedicated thread.
        """

        if self._voice is not None:
            return

        if os.name != "nt":
            raise TextToSpeechError(
                code="020",
                message="SAPI speech synthesis requires Windows.",
                hint="Use AETHEROS_TTS_PROVIDER=edge-tts instead.",
            )

        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="aetheros-sapi",
        )

        try:
            self._voice = await self._run(self._create_voice)

        except TextToSpeechError:
            self._shutdown_executor()
            raise

        except Exception as exc:
            self._shutdown_executor()

            raise TextToSpeechError(
                code="021",
                message="Could not initialize Windows speech synthesis.",
                cause=exc,
            ) from exc

        self._logger.info("Speech synthesis ready (Windows SAPI).")

    async def shutdown(self) -> None:

        await self.stop()

        if self._voice is not None and self._executor is not None:

            try:
                await self._run(self._release_voice)

            except Exception:
                self._logger.opt(exception=True).debug(
                    "Ignoring error while releasing SAPI voice."
                )

        self._voice = None

        self._shutdown_executor()

    # ==========================================================
    # Synthesis
    # ==========================================================

    async def speak(
        self,
        text: str,
        *,
        on_amplitude: AmplitudeCallback | None = None,
    ) -> None:

        spoken = text.strip()

        if not spoken:
            return

        if self._voice is None:
            await self.initialize()

        self._cancelled = False
        self._speaking = True

        path: str | None = None

        try:
            path = await self._run(self._render, spoken)

            if self._cancelled or path is None:
                return

            with open(path, "rb") as handle:
                data = handle.read()

            samples, rate = decode_wav(data)

            if samples.size == 0:
                self._logger.warning("SAPI produced no audio.")
                return

            await self._player.play(
                samples,
                rate,
                on_level=on_amplitude,
            )

        finally:
            self._speaking = False

            if path:
                try:
                    os.unlink(path)

                except OSError:
                    self._logger.debug(f"Could not delete temporary audio file: {path}")

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
    # Worker Thread
    # ==========================================================

    async def _run(self, function: Any, *args: Any) -> Any:
        """
        Execute `function` on the owned COM thread.
        """

        executor = self._executor

        if executor is None:
            raise TextToSpeechError(
                code="022",
                message="Speech synthesis has been shut down.",
            )

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(executor, function, *args)

    def _shutdown_executor(self) -> None:

        executor = self._executor
        self._executor = None

        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

    # ==========================================================
    # COM (worker thread only)
    # ==========================================================

    def _create_voice(self) -> Any:

        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()

        voice = win32com.client.Dispatch("SAPI.SpVoice")

        # Map the configured "+8%"-style rate onto SAPI's -10..10.
        voice.Rate = _sapi_rate(self._config.tts_rate)

        return voice

    def _release_voice(self) -> None:

        import pythoncom

        voice = self._voice

        if voice is not None:
            try:
                voice.Speak("", _SVSF_PURGE_BEFORE_SPEAK)

            except Exception:
                pass

        try:
            pythoncom.CoUninitialize()

        except Exception:
            pass

    def _render(self, text: str) -> str | None:
        """
        Synthesize `text` into a temporary WAV file.
        """

        import win32com.client

        voice = self._voice

        if voice is None:
            return None

        descriptor, path = tempfile.mkstemp(
            prefix="aetheros-tts-",
            suffix=".wav",
        )

        os.close(descriptor)

        stream = win32com.client.Dispatch("SAPI.SpFileStream")

        try:
            stream.Format.Type = _SAFT_22KHZ_16BIT_MONO
            stream.Open(path, _SSFM_CREATE_FOR_WRITE)

            voice.AudioOutputStream = stream
            voice.Speak(text)

        except Exception as exc:
            raise TextToSpeechError(
                code="023",
                message="Windows speech synthesis failed.",
                cause=exc,
            ) from exc

        finally:
            try:
                voice.AudioOutputStream = None

            except Exception:
                pass

            try:
                stream.Close()

            except Exception:
                pass

        return path


# ==============================================================
# Helpers
# ==============================================================


def _sapi_rate(rate: str) -> int:
    """
    Translate an edge-tts percentage offset into SAPI's -10..10 scale.
    """

    text = rate.strip().rstrip("%")

    try:
        percent = float(text)

    except ValueError:
        return 0

    # 100% faster is roughly SAPI's maximum.
    value = int(round(percent / 10.0))

    return max(-10, min(10, value))


__all__ = ["SapiTTS"]
