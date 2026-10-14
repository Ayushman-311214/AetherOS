"""
End-to-end validation of the AetherOS *voice* path through the Agent Core.

The headline run exercises the entire spoken chain with a fake only at the two
legitimate boundaries -- the hardware (microphone/speaker + cursor) and the
model:

    fake capture -> ScriptedSTT -> text
        -> VoicePipeline -> AgentReasoner -> AgentCore
        -> planner (scripted LLM) -> Policy -> ToolExecutor
        -> the real ``move_mouse`` tool -> real ``MouseService``
        -> fake ``MouseController`` (records the move)
        -> final text -> RecordingTTS (records what was spoken)

Everything between the two seams is the production object: the real
``move_mouse`` ``@tool`` copied out of the process-wide ``tool_registry`` (so the
planner sees the production schema), a real ``PolicyEngine``, the real
``ToolExecutor`` (wrapped only to witness delegation), the real ``AgentCore``,
the *new* ``AgentReasoner`` adapter, and the real ``VoicePipeline``.

The point of the wiring under test: voice contributes only a transcript and a
spoken-style prompt. It never calls a tool or an LLM provider itself -- the
Agent Core is the single orchestration layer. The fakes are the honest
witnesses: a coordinate reaches ``mouse.moves`` only if it travelled the whole
chain, and ``tts.spoken`` holds the final answer only if it came back out.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import numpy as np
import pytest

from aetheros.agents.core import AgentCore
from aetheros.agents.policy import PolicyConfig, PolicyEngine
from aetheros.core.container import container
from aetheros.core.interfaces.mouse_controller import MouseController
from aetheros.desktop.mouse import tools as _mouse_tools  # noqa: F401 - registers tools
from aetheros.desktop.mouse.controller import MouseService
from aetheros.tools import tool_registry
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry
from aetheros.voice.audio import Recording
from aetheros.voice.config import VoiceConfig
from aetheros.voice.pipeline import VoicePipeline
from aetheros.voice.reasoner import AgentReasoner, EchoReasoner
from aetheros.voice.state import VoiceState
from aetheros.voice.stt.null_stt import ScriptedSTT
from aetheros.voice.tts.null_tts import RecordingTTS


# ==============================================================
# Fakes: the legitimate boundaries (hardware + model)
# ==============================================================


class _RecordingMouse(MouseController):
    """A ``MouseController`` sitting where PyAutoGUI would.

    Records every absolute move, so ``moves`` is proof a coordinate travelled
    the full chain and reached the seam. Nothing else is stubbed with behaviour,
    so the abstract interface is satisfied without touching a real cursor.
    """

    def __init__(self) -> None:
        self.moves: list[tuple[int, int, float]] = []

    def position(self) -> tuple[int, int]:
        return (7, 11)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        self.moves.append((x, y, duration))

    def move_relative(self, dx: int, dy: int, duration: float = 0.0) -> None: ...
    def click(
        self, button: str = "left", clicks: int = 1, interval: float = 0.0
    ) -> None: ...
    def double_click(self, button: str = "left") -> None: ...
    def right_click(self) -> None: ...
    def middle_click(self) -> None: ...
    def drag_to(
        self, x: int, y: int, duration: float = 0.5, button: str = "left"
    ) -> None: ...
    def drag_relative(
        self, dx: int, dy: int, duration: float = 0.5, button: str = "left"
    ) -> None: ...
    def mouse_down(self, button: str = "left") -> None: ...
    def mouse_up(self, button: str = "left") -> None: ...
    def scroll(self, clicks: int) -> None: ...
    def hscroll(self, clicks: int) -> None: ...
    def is_pressed(self, button: str) -> bool:
        return False


class _CountingExecutor(ToolExecutor):
    """The real executor, recording every tool it was actually asked to run.

    A name reaches ``asked`` only after the coordinator's policy gate returns
    ALLOW, so it witnesses that the call passed Policy and went *through*
    ``ToolExecutor`` rather than around it.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        super().__init__(registry=registry, timeout_seconds=None)
        self.asked: list[str] = []

    async def execute_safe(self, name: str, arguments: dict[str, Any]) -> Any:
        self.asked.append(name)
        return await super().execute_safe(name, arguments)


class _FakeCapture:
    """Stands in for the microphone.

    Returns one non-silent recording so the pipeline advances to
    transcription; the samples are never inspected downstream (ScriptedSTT
    ignores them), they only have to be non-empty and long enough to clear the
    ``min_recording_duration`` gate.
    """

    def __init__(self, *, duration: float = 1.0) -> None:
        self._duration = duration

    async def record(
        self,
        *,
        on_level: Any = None,
        stop_event: Any = None,
    ) -> Recording:
        return Recording(
            samples=np.ones(16_000, dtype=np.float32),
            sample_rate=16_000,
            duration=self._duration,
            reason="fake",
            peak=0.5,
        )


class _BlockingReasoner:
    """A reasoner that parks until released, to exercise cancellation."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def respond(
        self,
        text: str,
        *,
        on_tool_start: Any = None,
        on_tool_finished: Any = None,
    ) -> str:
        self.entered.set()
        await self.release.wait()
        return "Should never be spoken."


class _FailingTTS(RecordingTTS):
    """RecordingTTS whose ``speak`` raises, to exercise TTS error handling."""

    async def speak(self, text: str, *, on_amplitude: Any = None) -> None:
        self.spoken.append(text)
        raise RuntimeError("synthesizer exploded")


# ==============================================================
# Helpers
# ==============================================================


@contextlib.contextmanager
def _fake_mouse():
    """Bind the ``MouseService`` the tool resolves to a recording controller.

    ``move_mouse`` does ``container.resolve(MouseService)`` at call time, so the
    seam is swapped here and removed afterwards -- no global state leaks between
    tests.
    """

    mouse = _RecordingMouse()
    container.register_singleton(MouseService, lambda: MouseService(mouse))
    try:
        yield mouse
    finally:
        container.remove(MouseService)


def _agent_reasoner(
    provider: Any,
    registry: ToolRegistry,
    policy: PolicyEngine,
    config: VoiceConfig,
) -> tuple[AgentReasoner, _CountingExecutor]:
    """Wrap a real ``AgentCore`` in the production ``AgentReasoner`` adapter."""

    executor = _CountingExecutor(registry)
    core = AgentCore.from_provider(
        provider,
        registry=registry,
        executor=executor,
        policy=policy,
        system_prompt="Unused: the voice prompt is passed per-run.",
    )
    reasoner = AgentReasoner(config=config, agent=core)
    return reasoner, executor


def _pipeline(
    reasoner: Any,
    config: VoiceConfig,
    *,
    stt: Any = None,
    tts: Any = None,
    capture: Any = None,
) -> tuple[VoicePipeline, Any]:
    """A pipeline with no event bus, wired to the given collaborators."""

    tts = tts if tts is not None else RecordingTTS()

    pipeline = VoicePipeline(
        config=config,
        capture=capture or _FakeCapture(),
        stt=stt or ScriptedSTT([]),
        tts=tts,
        reasoner=reasoner,
    )
    return pipeline, tts


# ==============================================================
# 1. "Move the mouse to 500,300." -- the full spoken chain
# ==============================================================


class TestVoiceMouseMovementE2E:
    @pytest.mark.asyncio
    async def test_speech_moves_the_mouse_through_the_agent(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        config = VoiceConfig(system_prompt="Speak briefly.")
        policy = PolicyEngine(PolicyConfig())

        # The real production tool, copied into an isolated registry so this
        # test's tools are the only ones the planner is offered.
        registry.register(tool_registry.get("move_mouse"))

        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 500, "y": 300})),
                answer("Moved your mouse to 500, 300."),
            ]
        )

        reasoner, executor = _agent_reasoner(provider, registry, policy, config)

        stt = ScriptedSTT(["Move the mouse to 500,300."])
        pipeline, tts = _pipeline(reasoner, config, stt=stt)

        with _fake_mouse() as mouse:
            result = await pipeline.listen_once()

        # speech -> text: the microphone-driven turn produced the transcript.
        assert stt.calls == 1
        assert result.transcript == "Move the mouse to 500,300."

        # text -> Agent -> Policy -> ToolExecutor: the executor was asked, which
        # only happens after the gate returns ALLOW.
        assert executor.asked == ["move_mouse"]

        # ...-> real tool -> MouseService -> controller: the arguments survived
        # every hop and reached the hardware seam, exactly once.
        assert mouse.moves == [(500, 300, 0.0)]
        assert len([a for a in executor.asked if a == "move_mouse"]) == len(
            mouse.moves
        )

        # The pipeline saw the tool via the replayed progress hooks (the HUD's
        # EXECUTING producer), so its TurnResult names it.
        assert result.tools == ["move_mouse"]

        # final text -> TTS: the Agent's final response is what got spoken.
        assert result.ok
        assert result.response == "Moved your mouse to 500, 300."
        assert tts.spoken == ["Moved your mouse to 500, 300."]

        # The turn settled cleanly.
        assert pipeline.state is VoiceState.IDLE


# ==============================================================
# 2. Cancellation (requirement 6)
# ==============================================================


class TestVoiceCancellation:
    @pytest.mark.asyncio
    async def test_a_turn_in_flight_can_be_cancelled(self) -> None:
        config = VoiceConfig()
        reasoner = _BlockingReasoner()
        pipeline, tts = _pipeline(reasoner, config)

        turn = asyncio.ensure_future(pipeline.say("do something slow"))

        # Wait until the reasoner is parked mid-turn, then cancel.
        await asyncio.wait_for(reasoner.entered.wait(), timeout=1.0)
        await pipeline.cancel()

        result = await asyncio.wait_for(turn, timeout=1.0)

        assert result.error == "Cancelled."
        # Nothing was ever spoken, and the machine is back to a resting state.
        assert tts.spoken == []
        assert pipeline.state is VoiceState.IDLE


# ==============================================================
# 3. STT errors (requirement 7)
# ==============================================================


class TestVoiceSTTError:
    @pytest.mark.asyncio
    async def test_a_failing_stt_becomes_an_error_turn(self) -> None:
        config = VoiceConfig()

        class _BoomSTT(ScriptedSTT):
            async def transcribe(self, audio: Any, **kwargs: Any) -> Any:
                raise RuntimeError("recognizer offline")

        # A reasoner that must never run: STT failed before any text existed.
        reasoner = EchoReasoner(reply="unreachable")
        pipeline, tts = _pipeline(reasoner, config, stt=_BoomSTT([]))

        result = await pipeline.listen_once()

        assert not result.ok
        assert "recognizer offline" in result.error
        assert tts.spoken == []
        assert pipeline.state is VoiceState.IDLE


# ==============================================================
# 4. TTS errors (requirement 8)
# ==============================================================


class TestVoiceTTSError:
    @pytest.mark.asyncio
    async def test_a_failing_tts_preserves_the_answer(self) -> None:
        config = VoiceConfig()

        # The reasoning double stands in for the Agent here: the concern under
        # test is the pipeline's output stage, not orchestration.
        reasoner = EchoReasoner(reply="Here is your answer.")
        tts = _FailingTTS()
        pipeline, _ = _pipeline(reasoner, config, tts=tts)

        result = await pipeline.say("tell me something")

        # A failed synthesizer must not lose the answer: the turn still succeeds
        # and carries the response, and TTS was genuinely attempted.
        assert result.ok
        assert result.response == "Here is your answer."
        assert tts.spoken == ["Here is your answer."]
        assert pipeline.state is VoiceState.IDLE
