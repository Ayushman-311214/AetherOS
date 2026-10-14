"""
The AetherOS heads-up display.

Importing this package deliberately does not import Qt. The overlay's
window, renderer and scene live behind `aetheros.hud.app` and
`aetheros.hud.window`, so configuration, state and the service can all
be used — and tested — on a machine with no Qt runtime and no display.
"""

from __future__ import annotations

from .config import QUALITY_LEVELS, HUDConfig
from .demo import DEFAULT_STEPS, DemoScript, single_state, synthetic_amplitude
from .pipe import PipeReader, PipeWriter, decode, encode
from .process import HUDProcess
from .protocol import (
    MSG_CLOSED,
    MSG_CONFIG,
    MSG_ERROR,
    MSG_QUIT,
    MSG_READY,
    MSG_SNAPSHOT,
    MSG_STATS,
    Message,
    MessageQueue,
)
from .service import HUDService
from .state import (
    AUDIO_REACTIVE_STATES,
    TRANSIENT_STATES,
    HUDSnapshot,
    HUDState,
)
from .theme import THEMES, Theme, get_theme

__all__ = [
    "AUDIO_REACTIVE_STATES",
    "DEFAULT_STEPS",
    "MSG_CLOSED",
    "MSG_CONFIG",
    "MSG_ERROR",
    "MSG_QUIT",
    "MSG_READY",
    "MSG_SNAPSHOT",
    "MSG_STATS",
    "QUALITY_LEVELS",
    "THEMES",
    "TRANSIENT_STATES",
    "DemoScript",
    "HUDConfig",
    "HUDProcess",
    "HUDService",
    "HUDSnapshot",
    "HUDState",
    "Message",
    "MessageQueue",
    "PipeReader",
    "PipeWriter",
    "Theme",
    "decode",
    "encode",
    "get_theme",
    "single_state",
    "synthetic_amplitude",
]
