from __future__ import annotations

import asyncio
import time
from typing import Any

import numpy as np

from ...core.errors.voice_error import SpeechToTextError
from ...core.interfaces.speech_to_text import SpeechToText, Transcript
from ...core.logging.logging import get_logger
from ..config import VoiceConfig

#: Whisper's fixed input rate. Audio at any other rate is resampled.
WHISPER_SAMPLE_RATE = 16_000


class FasterWhisperSTT(SpeechToText):
    """
    Local speech recognition via faster-whisper (CTranslate2).

    Runs entirely offline with no API key. CPU is the guaranteed
    path (int8 quantization); CUDA is used only when the configured
    device resolves to it, and a GPU failure degrades to CPU rather
    than taking the voice subsystem down.

    Model loading and inference are both blocking C++ calls, so they
    are dispatched to worker threads.
    """

    def __init__(
        self,
        config: VoiceConfig,
    ) -> None:

        self._config = config
        self._logger = get_logger("voice.stt.whisper")

        self._model: Any = None
        self._device = "cpu"
        self._compute_type = config.stt_compute_type

        #: Serializes inference; the model is not re-entrant.
        self._lock = asyncio.Lock()

        #: Guards model loading against concurrent initialize() calls.
        self._init_lock = asyncio.Lock()

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return "faster-whisper"

    @property
    def sample_rate(self) -> int:
        return WHISPER_SAMPLE_RATE

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def device(self) -> str:
        return self._device

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def initialize(self) -> None:
        """
        Load the Whisper model.

        The first call downloads the model into the HuggingFace cache,
        which can take a while on a cold machine.
        """

        if self._model is not None:
            return

        async with self._init_lock:

            if self._model is not None:
                return

            await self._load()

    async def _load(self) -> None:
        """
        Load the model. Caller holds the init lock.
        """

        try:
            from faster_whisper import WhisperModel

        except Exception as exc:
            raise SpeechToTextError(
                code="001",
                message="faster-whisper is not installed.",
                hint="Install it with: pip install faster-whisper",
                cause=exc,
            ) from exc

        device = self._config.resolved_stt_device
        compute_type = self._config.stt_compute_type

        # int8 is a CPU quantization; on GPU it is the wrong choice.
        if device == "cuda" and compute_type == "int8":
            compute_type = "float16"

        self._logger.info(
            f"Loading Whisper model '{self._config.stt_model}' (device={device}, "
            f"compute={compute_type})..."
        )

        started = time.monotonic()

        try:
            self._model = await asyncio.to_thread(
                WhisperModel,
                self._config.stt_model,
                device=device,
                compute_type=compute_type,
            )

            self._device = device
            self._compute_type = compute_type

        except Exception as gpu_exc:

            if device == "cpu":
                raise SpeechToTextError(
                    code="002",
                    message=(
                        f"Could not load Whisper model "
                        f"'{self._config.stt_model}'."
                    ),
                    hint=(
                        "Check AETHEROS_STT_MODEL and that the model "
                        "can be downloaded or is already cached."
                    ),
                    cause=gpu_exc,
                ) from gpu_exc

            # A CPU fallback must always work.
            self._logger.warning(
                f"Whisper failed on {device} ({gpu_exc}); falling back to CPU."
            )

            try:
                self._model = await asyncio.to_thread(
                    WhisperModel,
                    self._config.stt_model,
                    device="cpu",
                    compute_type="int8",
                )

                self._device = "cpu"
                self._compute_type = "int8"

            except Exception as cpu_exc:
                raise SpeechToTextError(
                    code="002",
                    message=(
                        f"Could not load Whisper model "
                        f"'{self._config.stt_model}' on CPU."
                    ),
                    cause=cpu_exc,
                ) from cpu_exc

        self._logger.info(
            f"Whisper ready in {time.monotonic() - started:.1f}s "
            f"(device={self._device}, compute={self._compute_type})."
        )

    async def shutdown(self) -> None:
        """
        Release the model.
        """

        if self._model is None:
            return

        self._logger.debug("Releasing Whisper model.")

        self._model = None

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
        """
        Transcribe mono float32 PCM.
        """

        if self._model is None:
            await self.initialize()

        prepared = _prepare_audio(
            audio,
            sample_rate or self._config.sample_rate,
        )

        if prepared.size == 0:
            return Transcript(text="", language=language)

        started = time.monotonic()

        async with self._lock:
            try:
                text, detected, confidence = await asyncio.to_thread(
                    self._transcribe_blocking,
                    prepared,
                    language or self._config.stt_language,
                )

            except Exception as exc:
                raise SpeechToTextError(
                    code="003",
                    message="Transcription failed.",
                    cause=exc,
                ) from exc

        duration = time.monotonic() - started

        # Deliberately logs only the length, never the content.
        self._logger.debug(
            f"Transcribed {prepared.size / WHISPER_SAMPLE_RATE:.2f}s of audio in "
            f"{duration:.2f}s ({len(text)} chars)."
        )

        return Transcript(
            text=text,
            language=detected,
            confidence=confidence,
            duration=duration,
        )

    # ==========================================================
    # Internals
    # ==========================================================

    def _transcribe_blocking(
        self,
        audio: np.ndarray,
        language: str | None,
    ) -> tuple[str, str | None, float | None]:
        """
        Run inference. Executed on a worker thread.
        """

        segments, info = self._model.transcribe(
            audio,
            language=language,
            beam_size=self._config.stt_beam_size,
            vad_filter=False,
            condition_on_previous_text=False,
        )

        parts: list[str] = []
        probabilities: list[float] = []

        # faster-whisper returns a generator; consuming it is what
        # actually performs the work.
        for segment in segments:
            parts.append(segment.text)

            logprob = getattr(segment, "avg_logprob", None)

            if logprob is not None:
                probabilities.append(float(np.exp(logprob)))

        text = " ".join(part.strip() for part in parts).strip()

        detected = getattr(info, "language", None)

        confidence = (
            float(np.mean(probabilities)) if probabilities else None
        )

        return text, detected, confidence


# ==============================================================
# Helpers
# ==============================================================


def _prepare_audio(
    audio: np.ndarray,
    sample_rate: int,
) -> np.ndarray:
    """
    Coerce arbitrary PCM into the mono float32 16 kHz Whisper wants.
    """

    if audio.size == 0:
        return np.zeros(0, dtype=np.float32)

    samples = np.asarray(audio, dtype=np.float32)

    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    if sample_rate != WHISPER_SAMPLE_RATE:
        samples = _resample(samples, sample_rate, WHISPER_SAMPLE_RATE)

    return np.ascontiguousarray(samples)


def _resample(
    samples: np.ndarray,
    source_rate: int,
    target_rate: int,
) -> np.ndarray:
    """
    Linear resampling.

    Adequate here because capture is configured at 16 kHz already;
    this only guards against a device that refuses that rate.
    """

    if source_rate == target_rate or samples.size == 0:
        return samples

    count = int(round(samples.size * target_rate / source_rate))

    if count <= 0:
        return np.zeros(0, dtype=np.float32)

    source_positions = np.linspace(
        0.0,
        samples.size - 1,
        num=samples.size,
        dtype=np.float64,
    )

    target_positions = np.linspace(
        0.0,
        samples.size - 1,
        num=count,
        dtype=np.float64,
    )

    return np.interp(
        target_positions,
        source_positions,
        samples,
    ).astype(np.float32)


__all__ = [
    "WHISPER_SAMPLE_RATE",
    "FasterWhisperSTT",
]
