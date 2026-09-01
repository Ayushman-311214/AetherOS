from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..core.errors.voice_error import (
    AudioDeviceError,
    MicrophoneUnavailableError,
)
from ..core.logging.logging import get_logger
from .config import VoiceConfig

LevelCallback = Callable[[float], None]


# ==============================================================
# Device discovery
# ==============================================================


@dataclass(slots=True, frozen=True)
class AudioDevice:
    """
    A host audio device as reported by PortAudio.
    """

    index: int
    name: str
    inputs: int
    outputs: int
    default_sample_rate: float

    @property
    def is_input(self) -> bool:
        return self.inputs > 0

    @property
    def is_output(self) -> bool:
        return self.outputs > 0


def _sounddevice() -> Any:
    """
    Import sounddevice lazily.

    Keeps PortAudio out of the process until voice is actually used,
    and turns a missing/broken backend into a domain error.
    """

    try:
        import sounddevice

        return sounddevice

    except Exception as exc:
        raise AudioDeviceError(
            code="001",
            message="Audio backend unavailable.",
            hint=(
                "Install 'sounddevice' and verify that Windows "
                "audio services are running."
            ),
            cause=exc,
        ) from exc


def list_devices() -> list[AudioDevice]:
    """
    Enumerate every audio device PortAudio can see.
    """

    sd = _sounddevice()

    devices: list[AudioDevice] = []

    try:
        raw_devices = sd.query_devices()

    except Exception as exc:
        raise AudioDeviceError(
            code="002",
            message="Could not enumerate audio devices.",
            cause=exc,
        ) from exc

    for index, device in enumerate(raw_devices):
        devices.append(
            AudioDevice(
                index=index,
                name=str(device.get("name", f"device {index}")),
                inputs=int(device.get("max_input_channels", 0)),
                outputs=int(device.get("max_output_channels", 0)),
                default_sample_rate=float(
                    device.get("default_samplerate", 0.0)
                ),
            )
        )

    return devices


def microphone_available(
    device: int | None = None,
) -> bool:
    """
    Whether a usable capture device exists.

    Never raises: callers use this to decide whether to degrade to
    text input, and a probe failure means "no microphone".
    """

    try:
        devices = list_devices()

    except AudioDeviceError:
        return False

    if device is not None:
        return any(
            candidate.index == device and candidate.is_input
            for candidate in devices
        )

    return any(candidate.is_input for candidate in devices)


# ==============================================================
# Capture
# ==============================================================


@dataclass(slots=True, frozen=True)
class Recording:
    """
    Captured microphone audio.
    """

    samples: np.ndarray
    sample_rate: int
    duration: float
    reason: str
    peak: float

    @property
    def is_silent(self) -> bool:
        return self.samples.size == 0 or self.peak <= 0.0


class AudioCapture:
    """
    Microphone capture with energy-based silence detection.

    PortAudio delivers blocks on its own high-priority thread. Those
    blocks are marshalled onto the running event loop, so nothing in
    the asyncio world ever blocks on the audio device.

    Silence detection is deliberately a plain RMS threshold rather
    than a neural VAD: it is deterministic, unit-testable, and costs
    no model load time. `silero-vad` can be slotted in later behind
    the same interface.
    """

    def __init__(
        self,
        config: VoiceConfig,
    ) -> None:

        self._config = config
        self._logger = get_logger("voice.audio")

        self._recording = False

    # ==========================================================
    # State
    # ==========================================================

    @property
    def is_recording(self) -> bool:
        return self._recording

    # ==========================================================
    # Capture
    # ==========================================================

    async def record(
        self,
        *,
        on_level: LevelCallback | None = None,
        stop_event: asyncio.Event | None = None,
    ) -> Recording:
        """
        Record one utterance.

        Capture ends on whichever comes first: sustained silence
        after speech, `max_recording_duration`, or `stop_event`.

        Raises:
            MicrophoneUnavailableError: capture could not start.
        """

        if self._recording:
            raise MicrophoneUnavailableError(
                code="010",
                message="Microphone capture already in progress.",
            )

        sd = _sounddevice()

        config = self._config
        loop = asyncio.get_running_loop()

        queue: asyncio.Queue[np.ndarray] = asyncio.Queue()

        overflows = 0

        def callback(
            indata: np.ndarray,
            frames: int,
            time_info: Any,
            status: Any,
        ) -> None:
            nonlocal overflows

            if status:
                overflows += 1

            # indata is reused by PortAudio, so copy before handing
            # it to another thread.
            block = indata[:, 0].copy()

            try:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    block,
                )

            except RuntimeError:
                # Event loop already closed during shutdown.
                pass

        try:
            stream = sd.InputStream(
                samplerate=config.sample_rate,
                blocksize=config.block_size,
                device=config.input_device,
                channels=config.channels,
                dtype="float32",
                callback=callback,
            )

        except Exception as exc:
            raise MicrophoneUnavailableError(
                code="011",
                message="Could not open the microphone.",
                hint=(
                    "Check AETHEROS_AUDIO_DEVICE, Windows "
                    "microphone privacy settings, and that no other "
                    "application holds the device exclusively."
                ),
                cause=exc,
            ) from exc

        self._recording = True

        blocks: list[np.ndarray] = []

        peak = 0.0
        reason = "max_duration"

        speech_detected = False
        silence_started: float | None = None

        started = time.monotonic()
        last_level_publish = 0.0

        try:
            with stream:

                self._logger.debug(
                    f"Recording at {config.sample_rate} Hz "
                    f"(device={config.input_device})"
                )

                while True:

                    elapsed = time.monotonic() - started

                    if elapsed >= config.max_recording_duration:
                        reason = "max_duration"
                        break

                    if stop_event is not None and stop_event.is_set():
                        reason = "stopped"
                        break

                    try:
                        block = await asyncio.wait_for(
                            queue.get(),
                            timeout=0.1,
                        )

                    except asyncio.TimeoutError:
                        continue

                    blocks.append(block)

                    level = _rms(block)
                    peak = max(peak, float(np.abs(block).max()))

                    # Throttle HUD updates to the configured rate.
                    now = time.monotonic()

                    if (
                        on_level is not None
                        and now - last_level_publish
                        >= config.level_interval
                    ):
                        last_level_publish = now
                        on_level(_normalize_level(level))

                    # ------------------------------------------
                    # Silence tracking
                    # ------------------------------------------

                    if level >= config.silence_threshold:
                        speech_detected = True
                        silence_started = None
                        continue

                    if not speech_detected:
                        continue

                    if silence_started is None:
                        silence_started = now

                    elif (
                        now - silence_started
                        >= config.silence_duration
                    ):
                        reason = "silence"
                        break

        except asyncio.CancelledError:
            reason = "cancelled"
            raise

        finally:
            self._recording = False

            if on_level is not None:
                on_level(0.0)

        duration = time.monotonic() - started

        if overflows:
            self._logger.warning(f"Microphone reported {overflows} buffer problem(s).")

        samples = (
            np.concatenate(blocks)
            if blocks
            else np.zeros(0, dtype=np.float32)
        )

        # Trim the trailing silence that triggered the stop so the
        # STT provider is not handed dead air.
        if reason == "silence" and samples.size:
            keep = int(
                config.sample_rate
                * config.silence_duration
                * 0.5
            )

            trim = max(samples.size - keep, 0)

            if trim > 0:
                samples = samples[:trim]

        self._logger.debug(
            f"Recorded {duration:.2f}s ({samples.size} samples), reason={reason}, "
            f"peak={peak:.4f}"
        )

        return Recording(
            samples=samples.astype(np.float32, copy=False),
            sample_rate=config.sample_rate,
            duration=duration,
            reason=reason,
            peak=peak,
        )


# ==============================================================
# Playback
# ==============================================================


class AudioPlayer:
    """
    Non-blocking playback of mono float32 PCM.

    Amplitude is measured inside the PortAudio callback and forwarded
    to the event loop, which is what lets the HUD pulse in time with
    AetherOS's own voice.
    """

    def __init__(
        self,
        config: VoiceConfig,
    ) -> None:

        self._config = config
        self._logger = get_logger("voice.playback")

        self._stream: Any = None
        self._playing = False

    # ==========================================================
    # State
    # ==========================================================

    @property
    def is_playing(self) -> bool:
        return self._playing

    # ==========================================================
    # Playback
    # ==========================================================

    async def play(
        self,
        samples: np.ndarray,
        sample_rate: int,
        *,
        on_level: LevelCallback | None = None,
    ) -> None:
        """
        Play `samples`, returning when playback finishes.

        Cancellation stops the device immediately.
        """

        if samples.size == 0:
            return

        sd = _sounddevice()

        loop = asyncio.get_running_loop()
        finished: asyncio.Future[None] = loop.create_future()

        audio = np.ascontiguousarray(
            samples.astype(np.float32, copy=False)
        )

        cursor = 0
        last_publish = 0.0
        interval = self._config.level_interval

        def callback(
            outdata: np.ndarray,
            frames: int,
            time_info: Any,
            status: Any,
        ) -> None:
            nonlocal cursor, last_publish

            remaining = audio.size - cursor

            if remaining <= 0:
                outdata.fill(0)
                raise sd.CallbackStop

            count = min(frames, remaining)

            chunk = audio[cursor : cursor + count]

            outdata[:count, 0] = chunk

            if count < frames:
                outdata[count:, 0] = 0.0

            cursor += count

            if on_level is not None:
                now = time.monotonic()

                if now - last_publish >= interval:
                    last_publish = now
                    level = _normalize_level(_rms(chunk))

                    try:
                        loop.call_soon_threadsafe(on_level, level)

                    except RuntimeError:
                        pass

            if cursor >= audio.size:
                raise sd.CallbackStop

        def finished_callback() -> None:
            try:
                loop.call_soon_threadsafe(
                    _resolve,
                    finished,
                )

            except RuntimeError:
                pass

        try:
            stream = sd.OutputStream(
                samplerate=sample_rate,
                blocksize=self._config.block_size,
                device=self._config.output_device,
                channels=1,
                dtype="float32",
                callback=callback,
                finished_callback=finished_callback,
            )

        except Exception as exc:
            raise AudioDeviceError(
                code="020",
                message="Could not open the audio output device.",
                hint="Check AETHEROS_AUDIO_OUTPUT_DEVICE.",
                cause=exc,
            ) from exc

        self._stream = stream
        self._playing = True

        try:
            stream.start()

            await finished

        except asyncio.CancelledError:
            self._logger.debug("Playback cancelled.")
            raise

        finally:
            self._playing = False
            self._stream = None

            try:
                stream.abort(ignore_errors=True)
                stream.close(ignore_errors=True)

            except Exception:
                self._logger.opt(exception=True).debug(
                    "Ignoring error while closing output stream."
                )

            if on_level is not None:
                on_level(0.0)

    async def stop(self) -> None:
        """
        Abort playback immediately.
        """

        stream = self._stream

        if stream is None:
            return

        try:
            stream.abort(ignore_errors=True)

        except Exception:
            self._logger.opt(exception=True).debug(
                "Ignoring error while aborting playback."
            )


# ==============================================================
# Helpers
# ==============================================================


def _resolve(future: asyncio.Future[None]) -> None:
    if not future.done():
        future.set_result(None)


def _rms(block: np.ndarray) -> float:
    """
    Root-mean-square amplitude of a PCM block.
    """

    if block.size == 0:
        return 0.0

    return float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))


def _normalize_level(rms: float) -> float:
    """
    Map an RMS value onto a perceptually useful [0, 1] range.

    Speech RMS typically lands around 0.02-0.2, which would barely
    register on a linear scale, so the value is compressed with a
    square root and clipped.
    """

    if rms <= 0.0:
        return 0.0

    level = float(np.sqrt(rms / 0.25))

    return max(0.0, min(1.0, level))


__all__ = [
    "AudioCapture",
    "AudioDevice",
    "AudioPlayer",
    "LevelCallback",
    "Recording",
    "list_devices",
    "microphone_available",
]
