from __future__ import annotations

import io
import wave
from typing import Any

import numpy as np

from ...core.errors.voice_error import TextToSpeechError

#: Cached PyAV module, or False once an import attempt has failed.
_av: Any = None


def pyav_available() -> bool:
    """
    Whether compressed audio (MP3) can be decoded.

    PyAV ships as a faster-whisper dependency, so this is normally
    true without any extra installation.
    """

    return _load_av() is not None


def _load_av() -> Any:
    global _av

    if _av is False:
        return None

    if _av is not None:
        return _av

    try:
        import av

        _av = av

    except Exception:
        _av = False

        return None

    return _av


def decode_mp3(data: bytes) -> tuple[np.ndarray, int]:
    """
    Decode MP3 bytes into mono float32 PCM.

    Returns:
        (samples, sample_rate)
    """

    av = _load_av()

    if av is None:
        raise TextToSpeechError(
            code="010",
            message="No MP3 decoder available.",
            hint=(
                "Install PyAV (pip install av) or select an "
                "uncompressed TTS provider such as 'sapi'."
            ),
        )

    try:
        with av.open(io.BytesIO(data)) as container:

            if not container.streams.audio:
                raise TextToSpeechError(
                    code="011",
                    message="Synthesized audio contained no audio stream.",
                )

            stream = container.streams.audio[0]
            rate = int(stream.rate or 24_000)

            resampler = av.AudioResampler(
                format="fltp",
                layout="mono",
                rate=rate,
            )

            chunks: list[np.ndarray] = []

            for frame in container.decode(stream):
                for resampled in resampler.resample(frame):
                    chunks.append(_frame_to_mono(resampled))

            # Flush whatever the resampler is still holding.
            for resampled in resampler.resample(None):
                chunks.append(_frame_to_mono(resampled))

    except TextToSpeechError:
        raise

    except Exception as exc:
        raise TextToSpeechError(
            code="012",
            message="Could not decode synthesized audio.",
            cause=exc,
        ) from exc

    if not chunks:
        return np.zeros(0, dtype=np.float32), rate

    return np.concatenate(chunks).astype(np.float32), rate


def decode_wav(data: bytes) -> tuple[np.ndarray, int]:
    """
    Decode RIFF/WAVE bytes into mono float32 PCM.

    Uses the standard library, so it works with no audio codecs
    installed at all.
    """

    try:
        with wave.open(io.BytesIO(data), "rb") as handle:

            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()

            frames = handle.readframes(handle.getnframes())

    except Exception as exc:
        raise TextToSpeechError(
            code="013",
            message="Could not decode WAV audio.",
            cause=exc,
        ) from exc

    dtypes: dict[int, str] = {1: "u1", 2: "<i2", 4: "<i4"}

    dtype = dtypes.get(width)

    if dtype is None:
        raise TextToSpeechError(
            code="014",
            message=f"Unsupported WAV sample width: {width} bytes.",
        )

    raw = np.frombuffer(frames, dtype=dtype)

    if raw.size == 0:
        return np.zeros(0, dtype=np.float32), rate

    if width == 1:
        # 8-bit WAV is unsigned, centred on 128.
        samples = (raw.astype(np.float32) - 128.0) / 128.0

    else:
        scale = float(1 << (8 * width - 1))
        samples = raw.astype(np.float32) / scale

    if channels > 1:
        usable = samples.size - (samples.size % channels)
        samples = samples[:usable].reshape(-1, channels).mean(axis=1)

    return np.ascontiguousarray(samples, dtype=np.float32), rate


def _frame_to_mono(frame: Any) -> np.ndarray:
    """
    Flatten a decoded PyAV audio frame to 1-D float32.
    """

    array = frame.to_ndarray()

    if array.ndim > 1:
        array = array.reshape(-1)

    return array.astype(np.float32, copy=False)


__all__ = [
    "decode_mp3",
    "decode_wav",
    "pyav_available",
]
