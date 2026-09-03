"""
The tool-progress hooks on the agent loop.

These exist for a presentation layer: the voice pipeline passes them so the
HUD can show EXECUTING and name the tool that is running. What matters here is
that they fire around the calls that *actually* execute, that they carry the
real outcome, and that a broken hook cannot take down a conversation.

Only the provider is faked. Schema generation, validation and dispatch are the
real implementations.
"""

from __future__ import annotations

from typing import Any

import pytest


# ==============================================================
# Sample tools
# ==============================================================


def add(a: int, b: int) -> int:
    """Add two integers."""

    return a + b


def explodes() -> None:
    """A tool that fails."""

    raise ValueError("boom")


# ==============================================================
# Recorder
# ==============================================================


class HookRecorder:
    """
    Stands in for the voice pipeline's progress callbacks.
    """

    def __init__(self, *, fail: bool = False) -> None:

        self.started: list[tuple[str, dict[str, Any]]] = []
        self.finished: list[tuple[str, bool, str | None]] = []

        self._fail = fail

    async def on_start(self, name: str, arguments: dict[str, Any]) -> None:

        self.started.append((name, arguments))

        if self._fail:
            raise RuntimeError("the overlay went away")

    async def on_finished(
        self,
        name: str,
        success: bool,
        error: str | None,
    ) -> None:

        self.finished.append((name, success, error))

        if self._fail:
            raise RuntimeError("the overlay went away")


# ==============================================================
# Tests
# ==============================================================


class TestToolProgressHooks:

    @pytest.mark.asyncio
    async def test_hooks_fire_around_a_successful_call(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:

        registry.register(define(add))

        _, loop = make_loop(
            [
                tool_calls(("add", {"a": 2, "b": 3})),
                answer("It is 5."),
            ]
        )

        hooks = HookRecorder()

        result = await loop.run_detailed(
            "add two and three",
            on_tool_start=hooks.on_start,
            on_tool_finished=hooks.on_finished,
        )

        assert result.content == "It is 5."

        assert hooks.started == [("add", {"a": 2, "b": 3})]
        assert hooks.finished == [("add", True, None)]

    @pytest.mark.asyncio
    async def test_a_failing_tool_is_reported_as_failed(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:

        registry.register(define(explodes))

        _, loop = make_loop(
            [
                tool_calls(("explodes", {})),
                answer("That did not work."),
            ]
        )

        hooks = HookRecorder()

        await loop.run_detailed(
            "break something",
            on_tool_start=hooks.on_start,
            on_tool_finished=hooks.on_finished,
        )

        assert len(hooks.finished) == 1

        name, success, error = hooks.finished[0]

        assert name == "explodes"
        assert success is False
        assert error

    @pytest.mark.asyncio
    async def test_run_forwards_the_hooks(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        `run` is the entry point the reasoner used to call; the hooks must not
        be silently dropped on the way through to `run_detailed`.
        """

        registry.register(define(add))

        _, loop = make_loop(
            [
                tool_calls(("add", {"a": 1, "b": 1})),
                answer("Two."),
            ]
        )

        hooks = HookRecorder()

        assert (
            await loop.run(
                "add one and one",
                on_tool_start=hooks.on_start,
                on_tool_finished=hooks.on_finished,
            )
            == "Two."
        )

        assert [name for name, _ in hooks.started] == ["add"]

    @pytest.mark.asyncio
    async def test_a_blocked_repeat_does_not_fire_the_hooks(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
    ) -> None:
        """
        The repeat guard refuses to run the call at all, so a display that
        showed EXECUTING for it would be describing something that never
        happened.
        """

        from aetheros.llm.agent_loop import AgentLoopConfig

        registry.register(define(add))

        # A single scripted response repeats forever, so the same call is
        # requested on every iteration.
        _, loop = make_loop(
            [tool_calls(("add", {"a": 2, "b": 2}))],
            config=AgentLoopConfig(
                max_iterations=4,
                max_repeated_calls=1,
            ),
        )

        hooks = HookRecorder()

        await loop.run_detailed(
            "add two and two",
            on_tool_start=hooks.on_start,
            on_tool_finished=hooks.on_finished,
        )

        # Executed exactly once despite being requested repeatedly.
        assert len(hooks.started) == 1
        assert len(hooks.finished) == 1

    @pytest.mark.asyncio
    async def test_a_hook_that_raises_does_not_break_the_run(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        The HUD is a child process that can die at any moment. Losing it must
        cost the overlay, not the answer.
        """

        registry.register(define(add))

        _, loop = make_loop(
            [
                tool_calls(("add", {"a": 4, "b": 4})),
                answer("Eight."),
            ]
        )

        hooks = HookRecorder(fail=True)

        result = await loop.run_detailed(
            "add four and four",
            on_tool_start=hooks.on_start,
            on_tool_finished=hooks.on_finished,
        )

        assert result.content == "Eight."
        assert result.stopped_reason == "final_answer"

        # The tool still ran and its result still reached the model.
        assert len(result.tool_results) == 1
        assert result.tool_results[0].ok is True

    @pytest.mark.asyncio
    async def test_the_hooks_are_optional(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        Every existing caller omits them.
        """

        registry.register(define(add))

        _, loop = make_loop(
            [
                tool_calls(("add", {"a": 1, "b": 2})),
                answer("Three."),
            ]
        )

        assert await loop.run("add one and two") == "Three."
