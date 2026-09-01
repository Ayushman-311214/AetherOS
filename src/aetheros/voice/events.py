from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..runtime.events.events import Event
from .state import VoiceState

# ==============================================================
# State
# ==============================================================


@dataclass(frozen=True, slots=True)
class VoiceStateChanged(Event):
    """
    The voice state machine moved between states.

    This is the single event the HUD needs in order to stay in sync;
    the finer-grained events below carry the extra detail (transcript
    text, tool names) that the HUD optionally displays.
    """

    previous: VoiceState = VoiceState.IDLE
    current: VoiceState = VoiceState.IDLE


# ==============================================================
# Listening
# ==============================================================


@dataclass(frozen=True, slots=True)
class VoiceListeningStarted(Event):
    """
    Microphone capture began.
    """

    trigger: str = "manual"


@dataclass(frozen=True, slots=True)
class VoiceListeningStopped(Event):
    """
    Microphone capture ended.
    """

    duration: float = 0.0
    reason: str = "silence"


@dataclass(frozen=True, slots=True)
class VoiceAudioLevel(Event):
    """
    Normalized audio amplitude in [0, 1].

    Published at roughly 20 Hz from both microphone capture and TTS
    playback to drive the HUD waveform. Marked quiet so the EventBus
    does not log one line per sample.
    """

    quiet: ClassVar[bool] = True

    level: float = 0.0
    source: str = "microphone"


# ==============================================================
# Transcription
# ==============================================================


@dataclass(frozen=True, slots=True)
class SpeechTranscriptionStarted(Event):
    """
    Captured audio was handed to the STT provider.
    """

    samples: int = 0
    duration: float = 0.0


@dataclass(frozen=True, slots=True)
class SpeechTranscribed(Event):
    """
    Speech was converted to text.
    """

    text: str = ""
    language: str | None = None
    duration: float = 0.0


# ==============================================================
# Reasoning
# ==============================================================


@dataclass(frozen=True, slots=True)
class LLMThinkingStarted(Event):
    """
    A reasoning request was sent to the LLM.
    """

    prompt: str = ""


@dataclass(frozen=True, slots=True)
class LLMThinkingFinished(Event):
    """
    The LLM produced a response.
    """

    response: str = ""
    duration: float = 0.0


# ==============================================================
# Tool Execution
# ==============================================================


@dataclass(frozen=True, slots=True)
class ToolExecutionStarted(Event):
    """
    The LLM requested a tool from the existing ToolRegistry.
    """

    tool: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolExecutionFinished(Event):
    """
    A tool finished, successfully or otherwise.
    """

    tool: str = ""
    success: bool = True
    duration: float = 0.0
    error: str | None = None


# ==============================================================
# Speech Output
# ==============================================================


@dataclass(frozen=True, slots=True)
class SpeechStarted(Event):
    """
    Speech synthesis playback began.
    """

    text: str = ""


@dataclass(frozen=True, slots=True)
class SpeechFinished(Event):
    """
    Speech synthesis playback ended.
    """

    duration: float = 0.0
    cancelled: bool = False


# ==============================================================
# Errors and Lifecycle
# ==============================================================


@dataclass(frozen=True, slots=True)
class VoiceError(Event):
    """
    A recoverable voice-subsystem failure.

    Named for the HUD's benefit; the exception hierarchy lives in
    core.errors.voice_error.
    """

    message: str = ""
    stage: str = "unknown"
    recoverable: bool = True


@dataclass(frozen=True, slots=True)
class VoiceServiceStarted(Event):
    """
    The voice service finished initializing.
    """

    stt_provider: str = ""
    tts_provider: str = ""
    activator: str = ""


@dataclass(frozen=True, slots=True)
class VoiceServiceStopped(Event):
    """
    The voice service released all audio resources.
    """


#: Every event the HUD may subscribe to.
VOICE_EVENTS: tuple[type[Event], ...] = (
    VoiceStateChanged,
    VoiceListeningStarted,
    VoiceListeningStopped,
    VoiceAudioLevel,
    SpeechTranscriptionStarted,
    SpeechTranscribed,
    LLMThinkingStarted,
    LLMThinkingFinished,
    ToolExecutionStarted,
    ToolExecutionFinished,
    SpeechStarted,
    SpeechFinished,
    VoiceError,
    VoiceServiceStarted,
    VoiceServiceStopped,
)


__all__ = [
    "VOICE_EVENTS",
    "LLMThinkingFinished",
    "LLMThinkingStarted",
    "SpeechFinished",
    "SpeechStarted",
    "SpeechTranscribed",
    "SpeechTranscriptionStarted",
    "ToolExecutionFinished",
    "ToolExecutionStarted",
    "VoiceAudioLevel",
    "VoiceError",
    "VoiceListeningStarted",
    "VoiceListeningStopped",
    "VoiceServiceStarted",
    "VoiceServiceStopped",
    "VoiceStateChanged",
]
