"""
The voice reasoner — the seam between a spoken turn and the LLM tool loop.

Three things are worth pinning down, and all three were live defects before the
wiring: that `from_container` picks up the *tool-enabled* engine bootstrap
registered rather than quietly building a tool-less one, that a turn which runs
out of iterations still says something out loud instead of raising, and that the
progress hooks reach the loop so the HUD's EXECUTING state has a producer.

No provider, no microphone, no model: the scripted `FakeLLMProvider` from the
root conftest drives the whole path.
"""

from __future__ import annotations

from typing import Any

import pytest

from aetheros.core.container.container import ServiceContainer
from aetheros.llm.engine import LLMEngine
from aetheros.llm.tool_schema import get_llm_tools
from aetheros.tools.executor import ToolExecutor
from aetheros.voice.config import VoiceConfig
from aetheros.voice.reasoner import EchoReasoner, LLMLoopReasoner


# ==============================================================
# Sample tool
# ==============================================================


def add(a: int, b: int) -> int:
    """Add two integers."""

    return a + b


# ==============================================================
# Helpers
# ==============================================================


class HookRecorder:
    """
    Stands in for the pipeline's HUD-facing progress callbacks.
    """

    def __init__(self) -> None:
        self.started: list[tuple[str, dict[str, Any]]] = []
        self.finished: list[tuple[str, bool, str | None]] = []

    async def on_start(self, name: str, arguments: dict[str, Any]) -> None:
        self.started.append((name, arguments))

    async def on_finished(
        self,
        name: str,
        success: bool,
        error: str | None,
    ) -> None:
        self.finished.append((name, success, error))


@pytest.fixture
def make_reasoner(registry, make_provider):
    """
    Build a ``(provider, reasoner)`` pair over the isolated registry.

    The executor is built from the same registry rather than the process-wide
    singleton, so a test's tools are the only ones that exist.
    """

    def build(
        responses: list[dict[str, Any]],
        *,
        config: VoiceConfig | None = None,
    ) -> tuple[Any, LLMLoopReasoner]:

        provider = make_provider(responses)

        engine = LLMEngine(
            provider,
            tool_provider=lambda: get_llm_tools(registry),
        )

        reasoner = LLMLoopReasoner(
            config=config or VoiceConfig(max_iterations=2),
            engine=engine,
            executor=ToolExecutor(registry),
        )

        return provider, reasoner

    return build


# ==============================================================
# Construction
# ==============================================================


class TestFromContainer:

    @pytest.mark.asyncio
    async def test_the_registered_engine_is_preferred(
        self,
        registry,
        define,
        make_provider,
        answer,
    ) -> None:
        """
        Bootstrap registers an LLMEngine whose tool_provider is bound to the
        live ToolRegistry. Building a fresh `LLMEngine(provider)` from the raw
        provider instead offers the model nothing to call — voice would be able
        to talk but not to act, which is the failure this guards.
        """

        registry.register(define(add))

        container = ServiceContainer()

        engine_provider = make_provider([answer("ok")])

        container.register_singleton(
            LLMEngine,
            lambda: LLMEngine(
                engine_provider,
                tool_provider=lambda: get_llm_tools(registry),
            ),
        )

        # Registered too, so preferring the engine is the only thing that can
        # produce a tool-enabled reasoner here.
        container.register_singleton(
            "llm_provider",
            lambda: make_provider([answer("ok")]),
        )

        reasoner = LLMLoopReasoner.from_container(
            VoiceConfig(),
            container,
        )

        await reasoner.respond("hello")

        offered = {
            schema["function"]["name"]
            for schema in engine_provider.received_tools[0]
        }

        assert "add" in offered

    @pytest.mark.asyncio
    async def test_the_provider_is_the_fallback(
        self,
        make_provider,
    ) -> None:
        """
        A caller that built only a provider still gets a working reasoner — it
        just has no tools, which is honest rather than broken.

        With nothing to offer, the engine takes its documented empty-tools path
        and calls `generate` rather than sending `tools: []`, which
        OpenAI-compatible endpoints reject. So the reply is scripted there.
        """

        container = ServiceContainer()

        provider = make_provider(generate_result="ok")

        container.register_singleton("llm_provider", lambda: provider)

        reasoner = LLMLoopReasoner.from_container(
            VoiceConfig(),
            container,
        )

        assert await reasoner.respond("hello") == "ok"

        assert provider.generate_count == 1
        assert provider.received_tools == []

    def test_an_empty_container_raises(self) -> None:
        """
        Better to fail loudly at startup than to answer every spoken turn with
        an error.
        """

        with pytest.raises(KeyError):
            LLMLoopReasoner.from_container(
                VoiceConfig(),
                ServiceContainer(),
            )


# ==============================================================
# Responding
# ==============================================================


class TestRespond:

    @pytest.mark.asyncio
    async def test_a_plain_answer_is_returned(
        self,
        registry,
        define,
        make_reasoner,
        answer,
    ) -> None:
        """
        A tool is registered so the loop takes its tool-calling path; with an
        empty registry the engine would fall back to plain generation and the
        scripted answer would never be reached.
        """

        registry.register(define(add))

        _, reasoner = make_reasoner([answer("  Done.  ")])

        assert await reasoner.respond("do the thing") == "Done."

    @pytest.mark.asyncio
    async def test_the_voice_system_prompt_is_used(
        self,
        make_reasoner,
        answer,
    ) -> None:
        """
        The spoken prompt is the reasoner's only real contribution; the loop's
        own default is written for a text CLI.
        """

        provider, reasoner = make_reasoner(
            [answer("Aye.")],
            config=VoiceConfig(system_prompt="Speak like a pirate."),
        )

        await reasoner.respond("hello")

        assert provider.received_messages[0][0] == {
            "role": "system",
            "content": "Speak like a pirate.",
        }

    @pytest.mark.asyncio
    async def test_the_hooks_reach_the_loop(
        self,
        registry,
        define,
        make_reasoner,
        tool_calls,
        answer,
    ) -> None:
        """
        This is the entire producer side of the HUD's EXECUTING state. Before
        the loop accepted these keywords, passing them raised TypeError on the
        first spoken turn.
        """

        registry.register(define(add))

        _, reasoner = make_reasoner(
            [
                tool_calls(("add", {"a": 1, "b": 2})),
                answer("Three."),
            ]
        )

        hooks = HookRecorder()

        result = await reasoner.respond(
            "add one and two",
            on_tool_start=hooks.on_start,
            on_tool_finished=hooks.on_finished,
        )

        assert result == "Three."
        assert hooks.started == [("add", {"a": 1, "b": 2})]
        assert hooks.finished == [("add", True, None)]

    @pytest.mark.asyncio
    async def test_a_bounded_stop_still_produces_speech(
        self,
        registry,
        define,
        make_reasoner,
        tool_calls,
    ) -> None:
        """
        Running out of iterations used to be handled by catching
        IterationLimitExceeded — a name that does not exist in the LLM layer,
        so importing the reasoner failed outright. The loop returns a partial
        answer instead, and saying that is better than saying nothing.
        """

        registry.register(define(add))

        # One scripted response repeats, so no final answer ever arrives.
        _, reasoner = make_reasoner(
            [
                tool_calls(
                    ("add", {"a": 1, "b": 1}),
                    content="Working on it.",
                )
            ]
        )

        assert await reasoner.respond("add one and one") == "Working on it."

    @pytest.mark.asyncio
    async def test_an_empty_answer_is_replaced(
        self,
        make_reasoner,
        answer,
    ) -> None:
        """
        TTS handed "" plays nothing, which is indistinguishable from a hang.
        """

        _, reasoner = make_reasoner([answer("   ")])

        assert (await reasoner.respond("say nothing")).strip()


# ==============================================================
# The double
# ==============================================================


class TestEchoReasoner:
    """
    EchoReasoner is what the pipeline tests run against, so its contract has to
    match LLMLoopReasoner's.
    """

    @pytest.mark.asyncio
    async def test_it_reports_the_tools_it_claims(self) -> None:

        reasoner = EchoReasoner(reply="Done.", tools=["click", "type_text"])

        hooks = HookRecorder()

        assert (
            await reasoner.respond(
                "do it",
                on_tool_start=hooks.on_start,
                on_tool_finished=hooks.on_finished,
            )
            == "Done."
        )

        assert [name for name, _ in hooks.started] == ["click", "type_text"]
        assert [name for name, _, _ in hooks.finished] == [
            "click",
            "type_text",
        ]

    @pytest.mark.asyncio
    async def test_the_hooks_are_optional(self) -> None:

        assert await EchoReasoner().respond("hello") == "Acknowledged."
