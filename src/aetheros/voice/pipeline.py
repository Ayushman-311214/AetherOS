from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

from ..core.errors.voice_error import VoiceError as VoiceErrorException
from ..core.interfaces.speech_to_text import SpeechToText
from ..core.interfaces.text_to_speech import TextToSpeech
from ..core.logging.logging import get_logger
from ..runtime.events.event_bus import EventBus
from ..runtime.events.events import Event
from .audio import AudioCapture
from .config import VoiceConfig
from .events import (
    LLMThinkingFinished,
    LLMThinkingStarted,
    SpeechFinished,
    SpeechStarted,
    SpeechTranscribed,
    SpeechTranscriptionStarted,
    ToolExecutionFinished,
    ToolExecutionStarted,
    VoiceAudioLevel,
    VoiceError,
    VoiceListeningStarted,
    VoiceListeningStopped,
    VoiceStateChanged,
)
from .state import VoiceState, VoiceStateMachine


class VoiceReasoner(Protocol):
    """
    Anything that can turn an utterance into a spoken reply.

    The pipeline depends on this rather than on the LLM stack directly,
    which keeps the voice layer testable and leaves model and tool
    behaviour entirely to the existing LLM architecture.
    """

    async def respond(
        self,
        text: str,
        *,
        on_tool_start: Any = None,
        on_tool_finished: Any = None,
    ) -> str: ...


class TurnResult:
    """
    Outcome of one voice interaction.
    """

    __slots__ = ("transcript", "response", "tools", "error", "duration")

    def __init__(
        self,
        *,
        transcript: str = "",
        response: str = "",
        tools: list[str] | None = None,
        error: str | None = None,
        duration: float = 0.0,
    ) -> None:

        self.transcript = transcript
        self.response = response
        self.tools = tools or []
        self.error = error
        self.duration = duration

    @property
    def ok(self) -> bool:
        return self.error is None

    def __repr__(self) -> str:
        return (
            f"TurnResult(transcript={self.transcript!r}, "
            f"response={self.response!r}, tools={self.tools!r}, "
            f"error={self.error!r})"
        )


class VoicePipeline:
    """
    Orchestrates a single voice turn.

    The sequence is:

        LISTENING -> TRANSCRIBING -> THINKING
                  -> [EXECUTING] -> SPEAKING -> IDLE

    Every stage publishes a typed event, and every state change
    publishes VoiceStateChanged. The HUD subscribes to those events;
    it is never called directly from here, so voice and HUD stay
    decoupled even though they move in lockstep.

    The pipeline owns no hardware of its own: capture, recognition and
    synthesis are injected, which is what lets the whole flow run in
    tests with no microphone and no speaker.
    """

    def __init__(
        self,
        *,
        config: VoiceConfig,
        capture: AudioCapture,
        stt: SpeechToText,
        tts: TextToSpeech,
        reasoner: VoiceReasoner,
        event_bus: EventBus | None = None,
        machine: VoiceStateMachine | None = None,
    ) -> None:

        self._config = config
        self._capture = capture
        self._stt = stt
        self._tts = tts
        self._reasoner = reasoner
        self._bus = event_bus

        self._machine = machine or VoiceStateMachine()
        self._machine.add_listener(self._on_state_changed)

        self._logger = get_logger("voice.pipeline")

        self._turn: asyncio.Task[TurnResult] | None = None
        self._stop_listening = asyncio.Event()

        #: Queued state events, drained on the event loop.
        self._pending: list[Event] = []

    # ==========================================================
    # State
    # ==========================================================

    @property
    def state(self) -> VoiceState:
        return self._machine.state

    @property
    def machine(self) -> VoiceStateMachine:
        return self._machine

    @property
    def is_busy(self) -> bool:
        return self._turn is not None and not self._turn.done()

    # ==========================================================
    # Turns
    # ==========================================================

    async def listen_once(self) -> TurnResult:
        """
        Run one microphone-driven turn, start to finish.
        """

        return await self._guarded(self._listen_turn())

    async def say(self, text: str) -> TurnResult:
        """
        Run one turn from typed text, skipping capture and recognition.

        This is how the CLI drives the pipeline, and how the whole
        Voice -> LLM -> Tool -> TTS path is exercised without hardware.
        """

        return await self._guarded(self._text_turn(text))

    async def speak(self, text: str) -> None:
        """
        Speak `text` without reasoning about it.
        """

        await self._guarded(self._speak_turn(text))

    # ==========================================================
    # Cancellation
    # ==========================================================

    def request_stop_listening(self) -> None:
        """
        Stop capturing but let the rest of the turn proceed.

        This is what a second hotkey press does: it ends the recording
        early rather than throwing the utterance away.
        """

        self._stop_listening.set()

    async def cancel(self) -> None:
        """
        Abandon the current turn and return to IDLE.
        """

        self._stop_listening.set()

        turn = self._turn

        if turn is not None and not turn.done():

            turn.cancel()

            try:
                await turn

            except (asyncio.CancelledError, Exception):
                pass

        await self._tts.stop()

        self._machine.reset()

        await self._flush()

    # ==========================================================
    # Turn Implementations
    # ==========================================================

    async def _listen_turn(self) -> TurnResult:

        started = time.monotonic()

        # ------------------------------------------------------
        # Listen
        # ------------------------------------------------------

        self._stop_listening = asyncio.Event()

        self._transition(VoiceState.LISTENING)

        await self._publish(VoiceListeningStarted(trigger="manual"))

        recording = await self._capture.record(
            on_level=self._level_reporter("microphone"),
            stop_event=self._stop_listening,
        )

        await self._publish(
            VoiceListeningStopped(
                duration=recording.duration,
                reason=recording.reason,
            )
        )

        if (
            recording.samples.size == 0
            or recording.duration < self._config.min_recording_duration
        ):
            self._logger.info("Nothing captured; returning to idle.")

            self._transition(VoiceState.IDLE)

            return TurnResult(
                duration=time.monotonic() - started,
            )

        # ------------------------------------------------------
        # Transcribe
        # ------------------------------------------------------

        self._transition(VoiceState.TRANSCRIBING)

        await self._publish(
            SpeechTranscriptionStarted(
                samples=int(recording.samples.size),
                duration=recording.duration,
            )
        )

        transcript = await self._stt.transcribe(
            recording.samples,
            sample_rate=recording.sample_rate,
        )

        if transcript.is_empty:
            self._logger.info("No speech recognized; returning to idle.")

            self._transition(VoiceState.IDLE)

            return TurnResult(
                duration=time.monotonic() - started,
            )

        await self._publish(
            SpeechTranscribed(
                text=transcript.text,
                language=transcript.language,
                duration=transcript.duration,
            )
        )

        result = await self._reason_and_speak(transcript.text)

        result.duration = time.monotonic() - started

        return result

    async def _text_turn(self, text: str) -> TurnResult:

        started = time.monotonic()

        spoken = text.strip()

        if not spoken:
            return TurnResult()

        await self._publish(
            SpeechTranscribed(
                text=spoken,
                language=self._config.stt_language,
            )
        )

        result = await self._reason_and_speak(spoken)

        result.duration = time.monotonic() - started

        return result

    async def _speak_turn(self, text: str) -> TurnResult:

        started = time.monotonic()

        spoken = text.strip()

        if not spoken:
            return TurnResult()

        await self._say(spoken)

        return TurnResult(
            response=spoken,
            duration=time.monotonic() - started,
        )

    # ==========================================================
    # Reasoning
    # ==========================================================

    async def _reason_and_speak(self, text: str) -> TurnResult:

        tools: list[str] = []

        self._transition(VoiceState.THINKING)

        await self._publish(LLMThinkingStarted(prompt=text))

        thinking_started = time.monotonic()

        #: Single-element holder so the two hooks can share a clock.
        tool_clock = [0.0]

        async def on_tool_start(
            name: str,
            arguments: dict[str, Any],
        ) -> None:

            tools.append(name)
            tool_clock[0] = time.monotonic()

            self._transition(VoiceState.EXECUTING)

            await self._publish(
                ToolExecutionStarted(
                    tool=name,
                    arguments=dict(arguments),
                )
            )

        async def on_tool_finished(
            name: str,
            success: bool,
            error: str | None,
        ) -> None:

            await self._publish(
                ToolExecutionFinished(
                    tool=name,
                    success=success,
                    duration=max(
                        0.0,
                        time.monotonic() - tool_clock[0],
                    ),
                    error=error,
                )
            )

            # Back to THINKING: the model still has to decide what to
            # say about what just happened.
            self._transition(VoiceState.THINKING)

        response = await self._reasoner.respond(
            text,
            on_tool_start=on_tool_start,
            on_tool_finished=on_tool_finished,
        )

        await self._publish(
            LLMThinkingFinished(
                response=response,
                duration=time.monotonic() - thinking_started,
            )
        )

        await self._say(response)

        return TurnResult(
            transcript=text,
            response=response,
            tools=tools,
        )

    # ==========================================================
    # Speech Output
    # ==========================================================

    async def _say(self, text: str) -> None:

        spoken = text.strip()

        if not spoken:
            self._transition(VoiceState.IDLE)
            return

        self._transition(VoiceState.SPEAKING)

        await self._publish(SpeechStarted(text=spoken))

        started = time.monotonic()
        cancelled = False

        try:
            await self._tts.speak(
                spoken,
                on_amplitude=self._level_reporter("speech"),
            )

        except asyncio.CancelledError:
            cancelled = True
            raise

        except Exception as exc:
            # A failed voice must not lose the answer: the text has
            # already been published, so downgrade to a warning.
            cancelled = True

            self._logger.warning(f"Speech synthesis failed: {exc}")

            await self._publish(
                VoiceError(
                    message=str(exc),
                    stage="speaking",
                    recoverable=True,
                )
            )

        finally:
            await self._publish(
                SpeechFinished(
                    duration=time.monotonic() - started,
                    cancelled=cancelled,
                )
            )

            self._transition(VoiceState.IDLE)

    # ==========================================================
    # Turn Supervision
    # ==========================================================

    async def _guarded(self, coroutine: Any) -> TurnResult:
        """
        Run one turn under a timeout, mapping failures onto ERROR.
        """

        if not self._machine.can_start_turn():

            self._logger.debug(f"Ignoring voice request while {self._machine.state}.")

            return TurnResult(
                error=f"Voice is busy ({self._machine.state}).",
            )

        task: asyncio.Task[TurnResult] = asyncio.ensure_future(
            asyncio.wait_for(
                coroutine,
                timeout=self._config.turn_timeout,
            )
        )

        self._turn = task

        try:
            return await task

        except asyncio.CancelledError:

            self._logger.info("Voice turn cancelled.")

            self._machine.reset()

            return TurnResult(error="Cancelled.")

        except asyncio.TimeoutError:

            await self._fail(
                f"Voice turn exceeded "
                f"{self._config.turn_timeout:.0f}s.",
                stage=str(self._machine.state).lower(),
            )

            return TurnResult(error="Timed out.")

        except VoiceErrorException as exc:

            await self._fail(
                exc.message,
                stage=str(self._machine.state).lower(),
                hint=exc.hint,
            )

            return TurnResult(error=exc.message)

        except Exception as exc:

            await self._fail(
                str(exc) or exc.__class__.__name__,
                stage=str(self._machine.state).lower(),
            )

            return TurnResult(error=str(exc))

        finally:
            self._turn = None

            await self._flush()

    async def _fail(
        self,
        message: str,
        *,
        stage: str,
        hint: str | None = None,
    ) -> None:
        """
        Record a turn failure and settle back to IDLE.
        """

        self._logger.error(f"Voice turn failed ({stage}): {message}")

        if hint:
            self._logger.info(f"Hint: {hint}")

        self._transition(VoiceState.ERROR)

        await self._publish(
            VoiceError(
                message=message,
                stage=stage,
                recoverable=True,
            )
        )

        # ERROR is a display state, not a resting state: the HUD shows
        # it, then the machine settles so the next turn can start.
        self._machine.reset()

        await self._flush()

    # ==========================================================
    # Events
    # ==========================================================

    def _transition(self, target: VoiceState) -> None:
        self._machine.transition(target)

    def _on_state_changed(
        self,
        previous: VoiceState,
        current: VoiceState,
    ) -> None:
        """
        Queue a state event.

        The state machine is synchronous, so publishing is deferred to
        the next await rather than spawning a task per transition.
        """

        self._pending.append(
            VoiceStateChanged(
                previous=previous,
                current=current,
            )
        )

    def _level_reporter(self, source: str) -> Any:
        """
        Build an amplitude callback that publishes VoiceAudioLevel.

        Called from the event loop (capture and playback both marshal
        back onto it), so publishing is scheduled rather than awaited.
        """

        bus = self._bus

        if bus is None:
            return None

        def report(level: float) -> None:
            try:
                loop = asyncio.get_running_loop()

            except RuntimeError:
                return

            loop.create_task(
                bus.publish(
                    VoiceAudioLevel(
                        level=level,
                        source=source,
                    )
                )
            )

        return report

    async def _publish(self, event: Event) -> None:
        """
        Publish `event`, after any queued state changes.
        """

        await self._flush()

        if self._bus is None:
            return

        await self._bus.publish(event)

    async def _flush(self) -> None:
        """
        Drain queued state-change events in order.
        """

        if not self._pending:
            return

        pending = self._pending
        self._pending = []

        if self._bus is None:
            return

        for event in pending:
            await self._bus.publish(event)


__all__ = [
    "TurnResult",
    "VoicePipeline",
    "VoiceReasoner",
]
