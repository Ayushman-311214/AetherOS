from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from ..core.logging.logging import get_logger


class VoiceState(str, Enum):
    """
    Lifecycle state of a single voice interaction.

    A typical conversational turn:

        IDLE -> LISTENING -> TRANSCRIBING -> THINKING
            -> SPEAKING -> IDLE

    A turn that invokes a tool:

        IDLE -> LISTENING -> TRANSCRIBING -> THINKING
            -> EXECUTING -> SPEAKING -> IDLE

    EXECUTING is therefore optional: "Hello Aether" never enters it,
    "Open Chrome" does.
    """

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"

    def __str__(self) -> str:
        return self.value


#: States from which a new turn may begin.
_READY_STATES = frozenset({VoiceState.IDLE, VoiceState.ERROR})


#: Legal transitions.
#
# Every state may return to IDLE (cancellation) or fall to ERROR
# (failure), which is why those two targets appear everywhere.
_TRANSITIONS: dict[VoiceState, frozenset[VoiceState]] = {
    VoiceState.IDLE: frozenset(
        {
            VoiceState.LISTENING,
            VoiceState.TRANSCRIBING,
            VoiceState.THINKING,
            VoiceState.ERROR,
        }
    ),
    VoiceState.LISTENING: frozenset(
        {
            VoiceState.TRANSCRIBING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        }
    ),
    VoiceState.TRANSCRIBING: frozenset(
        {
            VoiceState.THINKING,
            VoiceState.SPEAKING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        }
    ),
    VoiceState.THINKING: frozenset(
        {
            VoiceState.EXECUTING,
            VoiceState.SPEAKING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        }
    ),
    VoiceState.EXECUTING: frozenset(
        {
            VoiceState.THINKING,
            VoiceState.SPEAKING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        }
    ),
    VoiceState.SPEAKING: frozenset(
        {
            VoiceState.IDLE,
            VoiceState.ERROR,
        }
    ),
    VoiceState.ERROR: frozenset(
        {
            VoiceState.IDLE,
            VoiceState.LISTENING,
        }
    ),
}


StateListener = Callable[[VoiceState, VoiceState], None]


class VoiceStateMachine:
    """
    Guards voice-state transitions and notifies listeners.

    The state machine is deliberately synchronous and side-effect
    free: it validates transitions and reports them. Publishing the
    corresponding EventBus events is the pipeline's job.
    """

    def __init__(
        self,
        *,
        initial: VoiceState = VoiceState.IDLE,
        strict: bool = False,
    ) -> None:

        self._state = initial
        self._strict = strict
        self._listeners: list[StateListener] = []

        self._logger = get_logger("voice.state")

    # ==========================================================
    # State
    # ==========================================================

    @property
    def state(self) -> VoiceState:
        return self._state

    @property
    def is_idle(self) -> bool:
        return self._state is VoiceState.IDLE

    @property
    def is_busy(self) -> bool:
        """
        Whether a turn is currently in flight.
        """
        return self._state not in _READY_STATES

    def can_start_turn(self) -> bool:
        """
        Whether a new voice turn may begin.
        """
        return self._state in _READY_STATES

    def can_transition(
        self,
        target: VoiceState,
    ) -> bool:
        """
        Whether moving to `target` is legal from the current state.
        """

        if target is self._state:
            return True

        return target in _TRANSITIONS[self._state]

    # ==========================================================
    # Transitions
    # ==========================================================

    def transition(
        self,
        target: VoiceState,
    ) -> bool:
        """
        Move to `target`.

        Returns True when the state actually changed.

        Illegal transitions are refused. In strict mode they raise;
        otherwise they are logged and ignored so that a confused
        pipeline cannot corrupt the HUD's view of the world.
        """

        if target is self._state:
            return False

        if target not in _TRANSITIONS[self._state]:

            message = (
                f"Illegal voice transition "
                f"{self._state} -> {target}"
            )

            if self._strict:
                raise ValueError(message)

            self._logger.warning(message)

            return False

        previous = self._state
        self._state = target

        self._logger.debug(f"Voice state: {previous} -> {target}")

        self._notify(previous, target)

        return True

    def reset(self) -> None:
        """
        Force the machine back to IDLE.

        Used by shutdown and cancellation paths, where the current
        state may be arbitrary.
        """

        if self._state is VoiceState.IDLE:
            return

        previous = self._state
        self._state = VoiceState.IDLE

        self._logger.debug(f"Voice state reset: {previous} -> IDLE")

        self._notify(previous, VoiceState.IDLE)

    # ==========================================================
    # Listeners
    # ==========================================================

    def add_listener(
        self,
        listener: StateListener,
    ) -> None:

        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(
        self,
        listener: StateListener,
    ) -> None:

        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify(
        self,
        previous: VoiceState,
        current: VoiceState,
    ) -> None:

        for listener in list(self._listeners):

            try:
                listener(previous, current)

            except Exception:
                self._logger.exception(
                    "Voice state listener failed."
                )


__all__ = [
    "StateListener",
    "VoiceState",
    "VoiceStateMachine",
]
