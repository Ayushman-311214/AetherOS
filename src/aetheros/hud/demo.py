from __future__ import annotations

import math
from dataclasses import dataclass, field

from .state import HUDSnapshot, HUDState

#: The scripted walkthrough.
#
# Covers every state so the overlay can be inspected end to end with no
# microphone, no LLM and no network. The wording deliberately mirrors a
# real turn — a mouse-movement request — so the EXECUTING beat looks
# like what it will look like in use.
DEFAULT_STEPS: tuple[dict[str, object], ...] = (
    {
        "state": HUDState.IDLE,
        "seconds": 3.0,
    },
    {
        "state": HUDState.LISTENING,
        "seconds": 4.0,
        "transcript": "Move the mouse 300 pixels to the right",
    },
    {
        "state": HUDState.TRANSCRIBING,
        "seconds": 1.4,
        "transcript": "Move the mouse 300 pixels to the right",
    },
    {
        "state": HUDState.THINKING,
        "seconds": 3.2,
        "transcript": "Move the mouse 300 pixels to the right",
    },
    {
        "state": HUDState.EXECUTING,
        "seconds": 2.6,
        "action": "mouse.move_relative",
    },
    {
        "state": HUDState.SPEAKING,
        "seconds": 4.2,
        "response": "Done. The cursor moved 300 pixels right.",
    },
    {
        "state": HUDState.ERROR,
        "seconds": 2.8,
        "message": "Microphone unavailable",
    },
)


def synthetic_amplitude(elapsed: float) -> float:
    """
    A speech-like level, without any audio.

    Three unrelated periods multiplied together: a slow phrase
    envelope, a syllable rate, and fine detail. The result has the
    gaps and transients that make the visualizer look alive, and being
    a pure function of time it is identical on every run.
    """

    envelope = 0.5 + 0.5 * math.sin(elapsed * 2.1)

    syllable = 0.5 + 0.5 * math.sin(
        elapsed * 11.0 + math.sin(elapsed * 3.7)
    )

    detail = 0.5 + 0.5 * math.sin(elapsed * 27.0)

    level = 0.18 + 0.82 * envelope * syllable * (
        0.72 + 0.28 * detail
    )

    return max(0.0, min(1.0, level))


@dataclass(slots=True)
class DemoScript:
    """
    A time-driven state walkthrough.

    Deliberately free of Qt, asyncio and threads: it is a pure function
    from elapsed time to a snapshot, so the standalone window, the
    service and the tests can all drive it the same way.
    """

    steps: tuple[dict[str, object], ...] = DEFAULT_STEPS

    loop: bool = True

    #: Multiplies every step duration. Below 1.0 to skim, above to
    #: dwell on each state.
    speed: float = 1.0

    _sequence: int = field(default=0, init=False, repr=False)

    # ==========================================================
    # Timing
    # ==========================================================

    @property
    def duration(self) -> float:
        """
        Total length of one pass, in seconds.
        """

        rate = max(0.05, self.speed)

        return sum(
            max(0.1, float(step.get("seconds", 1.0))) / rate
            for step in self.steps
        )

    def index_at(self, elapsed: float) -> int:
        """
        Which step is current at `elapsed` seconds.
        """

        if not self.steps:
            return 0

        total = self.duration

        if self.loop and total > 0.0:
            elapsed = elapsed % total

        rate = max(0.05, self.speed)
        cursor = 0.0

        for index, step in enumerate(self.steps):

            cursor += max(0.1, float(step.get("seconds", 1.0))) / rate

            if elapsed < cursor:
                return index

        # Past the end of a non-looping script: hold the last state.
        return len(self.steps) - 1

    # ==========================================================
    # Output
    # ==========================================================

    def snapshot_at(self, elapsed: float) -> HUDSnapshot:
        """
        The snapshot that should be showing at `elapsed` seconds.
        """

        if not self.steps:
            return HUDSnapshot()

        step = self.steps[self.index_at(elapsed)]

        state = step.get("state", HUDState.IDLE)

        if not isinstance(state, HUDState):
            state = HUDState.parse(str(state))

        amplitude = (
            synthetic_amplitude(elapsed)
            if state in (HUDState.LISTENING, HUDState.SPEAKING)
            else 0.0
        )

        return HUDSnapshot(
            state=state,
            amplitude=amplitude,
            transcript=str(step.get("transcript", "") or ""),
            action=str(step.get("action", "") or ""),
            response=str(step.get("response", "") or ""),
            message=str(step.get("message", "") or ""),
            sequence=self._next_sequence(),
        )

    def _next_sequence(self) -> int:

        self._sequence += 1

        return self._sequence

    @property
    def states(self) -> tuple[HUDState, ...]:
        """
        Every state the script visits, in order.
        """

        result: list[HUDState] = []

        for step in self.steps:

            state = step.get("state", HUDState.IDLE)

            if not isinstance(state, HUDState):
                state = HUDState.parse(str(state))

            result.append(state)

        return tuple(result)


def single_state(name: str) -> HUDSnapshot:
    """
    Build a snapshot for one state, with plausible sample content.

    Used by `hud state <NAME>` so an individual state can be held
    still and inspected.
    """

    state = HUDState.parse(name)

    samples = {
        HUDState.LISTENING: {
            "transcript": "Hello Aether",
            "amplitude": 0.62,
        },
        HUDState.TRANSCRIBING: {
            "transcript": "Hello Aether",
        },
        HUDState.THINKING: {
            "transcript": "Hello Aether",
        },
        HUDState.EXECUTING: {
            "action": "mouse.move_relative",
        },
        HUDState.SPEAKING: {
            "response": "Hello. How can I help?",
            "amplitude": 0.58,
        },
        HUDState.ERROR: {
            "message": "Speech recognition unavailable",
        },
    }

    payload = samples.get(state, {})

    return HUDSnapshot(
        state=state,
        amplitude=float(payload.get("amplitude", 0.0)),
        transcript=str(payload.get("transcript", "")),
        action=str(payload.get("action", "")),
        response=str(payload.get("response", "")),
        message=str(payload.get("message", "")),
    )


__all__ = [
    "DEFAULT_STEPS",
    "DemoScript",
    "single_state",
    "synthetic_amplitude",
]
