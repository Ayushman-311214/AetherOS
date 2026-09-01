from __future__ import annotations

from ..core.interfaces.speech_to_text import SpeechToText, Transcript
from ..core.interfaces.text_to_speech import TextToSpeech
from ..core.interfaces.voice_activator import VoiceActivator
from .activation import (
    NullActivator,
    PushToTalkActivator,
    WakeWordActivator,
    create_activator,
)
from .audio import (
    AudioCapture,
    AudioDevice,
    AudioPlayer,
    Recording,
    list_devices,
    microphone_available,
)
from .config import VoiceConfig
from .events import VOICE_EVENTS
from .pipeline import TurnResult, VoicePipeline, VoiceReasoner
from .reasoner import EchoReasoner, LLMLoopReasoner
from .service import VoiceService
from .state import VoiceState, VoiceStateMachine
from .stt import create_stt
from .tts import create_tts

__all__ = [
    "VOICE_EVENTS",
    "AudioCapture",
    "AudioDevice",
    "AudioPlayer",
    "EchoReasoner",
    "LLMLoopReasoner",
    "NullActivator",
    "PushToTalkActivator",
    "Recording",
    "SpeechToText",
    "TextToSpeech",
    "Transcript",
    "TurnResult",
    "VoiceActivator",
    "VoiceConfig",
    "VoicePipeline",
    "VoiceReasoner",
    "VoiceService",
    "VoiceState",
    "VoiceStateMachine",
    "WakeWordActivator",
    "create_activator",
    "create_stt",
    "create_tts",
    "list_devices",
    "microphone_available",
]
