from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class HUDState(str, Enum):
    """
    What the overlay is currently depicting.

    Mirrors the voice state machine by name but is a separate type on
    purpose: the render process receives state as data over a queue and
    must not import the voice subsystem to interpret it. That is what
    keeps the dependency one-way.
    """

    #: Nothing is driving the HUD — standalone, or voice not started.
    OFFLINE = "OFFLINE"

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def parse(cls, value: object) -> HUDState:
        """
        Coerce a name into a state, defaulting to IDLE.

        Unknown names must not break the render loop, so this never
        raises.
        """

        if isinstance(value, cls):
            return value

        text = str(value or "").strip().upper()

        # Voice publishes state names like "VoiceState.LISTENING" via
        # str() in some paths; take the last component either way.
        if "." in text:
            text = text.rsplit(".", 1)[-1]

        try:
            return cls(text)

        except ValueError:
            return cls.IDLE


#: States during which live audio amplitude is meaningful. Outside
# these, the visualizer decays to zero rather than trusting a level
# that may have arrived late.
AUDIO_REACTIVE_STATES = frozenset(
    {
        HUDState.LISTENING,
        HUDState.SPEAKING,
    }
)


#: States that should return to IDLE by themselves. ERROR is a
# display state, not a resting state.
TRANSIENT_STATES = frozenset({HUDState.ERROR})


@dataclass(frozen=True, slots=True)
class HUDSnapshot:
    """
    Everything the renderer needs to draw one moment.

    Immutable and picklable: this is the payload that crosses the
    process boundary. Text fields stay short by contract — the HUD is
    an indicator, not a dashboard.
    """

    state: HUDState = HUDState.OFFLINE

    #: Normalized audio level, 0..1.
    amplitude: float = 0.0

    #: Last thing heard from the user.
    transcript: str = ""

    #: Tool currently executing, if any.
    action: str = ""

    #: Last thing AetherOS said.
    response: str = ""

    #: Error text, shown only in ERROR.
    message: str = ""

    #: Monotonic counter so the renderer can detect it fell behind.
    sequence: int = 0

    @property
    def is_audio_reactive(self) -> bool:
        return self.state in AUDIO_REACTIVE_STATES

    def with_state(
        self,
        state: HUDState,
        **changes: object,
    ) -> HUDSnapshot:
        """
        Copy with a new state, clearing fields the new state retires.
        """

        updates: dict[str, object] = dict(changes)
        updates["state"] = state
        updates["sequence"] = self.sequence + 1

        # An error message must not survive into the next turn.
        if state is not HUDState.ERROR and "message" not in updates:
            updates["message"] = ""

        # Nor should a stale tool name.
        if state is not HUDState.EXECUTING and "action" not in updates:
            updates["action"] = ""

        # Amplitude is only real while audio is flowing.
        if (
            state not in AUDIO_REACTIVE_STATES
            and "amplitude" not in updates
        ):
            updates["amplitude"] = 0.0

        return replace(self, **updates)  # type: ignore[arg-type]

    # ==========================================================
    # Serialization
    # ==========================================================

    def to_dict(self) -> dict[str, object]:

        return {
            "state": self.state.value,
            "amplitude": self.amplitude,
            "transcript": self.transcript,
            "action": self.action,
            "response": self.response,
            "message": self.message,
            "sequence": self.sequence,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> HUDSnapshot:
        """
        Rebuild from to_dict(), tolerating missing or malformed keys.
        """

        def number(key: str) -> float:
            try:
                return float(data.get(key, 0.0))  # type: ignore[arg-type]

            except (TypeError, ValueError):
                return 0.0

        def text(key: str) -> str:
            value = data.get(key, "")
            return "" if value is None else str(value)

        return cls(
            state=HUDState.parse(data.get("state")),
            amplitude=max(0.0, min(1.0, number("amplitude"))),
            transcript=text("transcript"),
            action=text("action"),
            response=text("response"),
            message=text("message"),
            sequence=int(number("sequence")),
        )


__all__ = [
    "AUDIO_REACTIVE_STATES",
    "TRANSIENT_STATES",
    "HUDSnapshot",
    "HUDState",
]
