from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)

    if raw is None:
        return default

    return raw.strip().lower() in ("1", "true", "yes", "on")


def _number(name: str, default: float) -> float:
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        return default

    try:
        return float(raw)

    except ValueError:
        return default


def _integer(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        return default

    try:
        return int(raw)

    except ValueError:
        return default


def _text(name: str, default: str) -> str:
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        return default

    return raw.strip()


@dataclass(slots=True)
class VoiceConfig:
    """
    Configuration for the AetherOS voice subsystem.

    Values may be supplied directly or loaded from the environment
    by from_env(). Directly supplied values always win.
    """

    # ----------------------------------------------------------
    # Feature flags
    # ----------------------------------------------------------

    # enabled: bool = False
    enabled: bool = True

    #: Hard kill switch for audio input.
    #
    # When true, no capture device is ever opened and recognition is
    # replaced by a null provider, whatever else is configured. This
    # is the unambiguous "disable the microphone completely" switch;
    # spoken output and the HUD keep working.
    microphone_disabled: bool = False

    # ----------------------------------------------------------
    # Audio capture
    # ----------------------------------------------------------

    sample_rate: int = 16_000
    channels: int = 1
    block_size: int = 512

    #: sounddevice device index, or None for the system default.
    input_device: int | None = None
    output_device: int | None = None

    #: Stop capturing after this much continuous silence.
    silence_threshold: float = 0.012
    silence_duration: float = 1.2

    #: Bounds on a single utterance.
    min_recording_duration: float = 0.4
    max_recording_duration: float = 20.0

    # ----------------------------------------------------------
    # Speech to text
    # ----------------------------------------------------------

    stt_provider: str = "faster-whisper"
    stt_model: str = "base"
    stt_device: str = "auto"
    stt_compute_type: str = "int8"
    stt_language: str | None = "en"
    stt_beam_size: int = 1

    # ----------------------------------------------------------
    # Text to speech
    # ----------------------------------------------------------

    tts_provider: str = "edge-tts"
    tts_voice: str = "en-US-AriaNeural"

    #: Percentage offsets understood by edge-tts, e.g. "+10%".
    tts_rate: str = "+8%"
    tts_volume: str = "+0%"
    tts_pitch: str = "+0Hz"

    # ----------------------------------------------------------
    # Activation
    # ----------------------------------------------------------

    activator: str = "push-to-talk"

    #: Global hotkey, or empty to disable OS-level activation.
    hotkey: str = "ctrl+alt+space"

    wake_word: str = "aether"

    # ----------------------------------------------------------
    # Reasoning
    # ----------------------------------------------------------

    system_prompt: str = (
        "You are AetherOS, a spoken assistant that operates this "
        "computer. Replies are read aloud, so answer in one or two "
        "short sentences of plain prose with no markdown, lists, or "
        "code. Use the available tools to carry out actions, then "
        "confirm briefly what you did."
    )

    max_iterations: int = 6

    #: Abort a turn that exceeds this many seconds.
    turn_timeout: float = 90.0

    #: Amplitude publish rate, in Hz, for HUD animation.
    level_publish_hz: float = 20.0

    metadata: dict[str, str] = field(default_factory=dict)

    # ==========================================================
    # Environment
    # ==========================================================

    @classmethod
    def from_env(cls) -> VoiceConfig:
        """
        Build a configuration from AETHEROS_* environment variables.
        """

        defaults = cls()

        return cls(
            enabled=_flag(
                "AETHEROS_VOICE_ENABLED",
                defaults.enabled,
            ),
            microphone_disabled=_flag(
                "AETHEROS_MICROPHONE_DISABLED",
                defaults.microphone_disabled,
            ),
            sample_rate=int(
                _number(
                    "AETHEROS_AUDIO_SAMPLE_RATE",
                    defaults.sample_rate,
                )
            ),
            input_device=_integer(
                "AETHEROS_AUDIO_DEVICE",
                defaults.input_device,
            ),
            output_device=_integer(
                "AETHEROS_AUDIO_OUTPUT_DEVICE",
                defaults.output_device,
            ),
            silence_threshold=_number(
                "AETHEROS_VOICE_SILENCE_THRESHOLD",
                defaults.silence_threshold,
            ),
            silence_duration=_number(
                "AETHEROS_VOICE_SILENCE_DURATION",
                defaults.silence_duration,
            ),
            max_recording_duration=_number(
                "AETHEROS_VOICE_MAX_DURATION",
                defaults.max_recording_duration,
            ),
            stt_provider=_text(
                "AETHEROS_STT_PROVIDER",
                defaults.stt_provider,
            ),
            stt_model=_text(
                "AETHEROS_STT_MODEL",
                defaults.stt_model,
            ),
            stt_device=_text(
                "AETHEROS_STT_DEVICE",
                defaults.stt_device,
            ),
            stt_compute_type=_text(
                "AETHEROS_STT_COMPUTE_TYPE",
                defaults.stt_compute_type,
            ),
            stt_language=(
                _text("AETHEROS_STT_LANGUAGE", "")
                or defaults.stt_language
            ),
            tts_provider=_text(
                "AETHEROS_TTS_PROVIDER",
                defaults.tts_provider,
            ),
            tts_voice=_text(
                "AETHEROS_TTS_VOICE",
                defaults.tts_voice,
            ),
            tts_rate=_text(
                "AETHEROS_TTS_RATE",
                defaults.tts_rate,
            ),
            tts_volume=_text(
                "AETHEROS_TTS_VOLUME",
                defaults.tts_volume,
            ),
            activator=_text(
                "AETHEROS_VOICE_ACTIVATOR",
                defaults.activator,
            ),
            hotkey=(
                os.getenv(
                    "AETHEROS_VOICE_HOTKEY",
                    defaults.hotkey,
                )
                or ""
            ).strip(),
            wake_word=_text(
                "AETHEROS_WAKE_WORD",
                defaults.wake_word,
            ),
            turn_timeout=_number(
                "AETHEROS_VOICE_TURN_TIMEOUT",
                defaults.turn_timeout,
            ),
        )

    # ==========================================================
    # Derived values
    # ==========================================================

    @property
    def level_interval(self) -> float:
        """
        Minimum seconds between amplitude publishes.
        """

        if self.level_publish_hz <= 0:
            return 0.0

        return 1.0 / self.level_publish_hz

    @property
    def resolved_stt_device(self) -> str:
        """
        Resolve "auto" to CUDA when a usable GPU is present.

        A CPU fallback must always work, so any failure to probe the
        GPU resolves to "cpu".
        """

        if self.stt_device != "auto":
            return self.stt_device

        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"

        except Exception:
            pass

        return "cpu"


__all__ = ["VoiceConfig"]
