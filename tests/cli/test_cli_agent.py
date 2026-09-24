"""
Integration tests for the CLI ``ask`` command on the agent core.

``ask`` used to call the LLM tool loop directly; after the migration it submits
the user's message to an :class:`AgentCore` and only renders the result. These
tests drive the *real* command handler over a *real* ``AgentCore`` -- real
planner, real policy-gated coordinator, real ``ToolExecutor`` -- with just two
doubles: a scripted provider, so each turn is deterministic and no model is
called, and a counting executor that witnesses every delegation.

The three cases the task named -- ``ask hello`` (no tools), ``ask what is my
mouse position?`` (a read-only tool), and ``ask move my mouse to 500,300`` (a
tool with arguments) -- each assert the whole chain the migration must keep
intact: Agent -> Policy -> ToolExecutor -> the actual tool body.
"""

from __future__ import annotations

from typing import Any

import pytest

from aetheros.agents.core import AgentCore
from aetheros.agents.policy import PolicyConfig, PolicyEngine
from aetheros.cli.commands import CommandRegistry
from aetheros.cli.parser import CommandParser
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry


# ==============================================================
# Tool doubles that witness their own execution
# ==============================================================

# The independent proof that a call reached the *actual tool body* -- not just
# the executor -- and with which arguments. Reset by the ``invoked`` fixture
# before each test.
_INVOKED: list[tuple[str, dict[str, Any]]] = []


def mouse_position() -> str:
    """A read-only tool: report a fixed cursor position."""

    _INVOKED.append(("mouse_position", {}))
    return "position: x=7, y=11"


def move_mouse(x: int, y: int) -> str:
    """A tool with arguments: 'move' the cursor and report where."""

    _INVOKED.append(("move_mouse", {"x": x, "y": y}))
    return f"moved to {x},{y}"


class _CountingExecutor(ToolExecutor):
    """The real engine, recording every tool it was actually asked to run.

    ``asked`` is the honest witness that a call reached ``ToolExecutor``: the
    coordinator delegates here only *after* the policy returns ALLOW, so a name
    in ``asked`` is proof the call passed the gate rather than bypassing it.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        super().__init__(registry=registry, timeout_seconds=None)
        self.asked: list[str] = []

    async def execute_safe(self, name: str, arguments: dict[str, Any]) -> Any:
        self.asked.append(name)
        return await super().execute_safe(name, arguments)


# ==============================================================
# Fixtures and helpers
# ==============================================================


@pytest.fixture
def invoked() -> list[tuple[str, dict[str, Any]]]:
    """The shared invocation record, cleared before each test."""

    _INVOKED.clear()
    return _INVOKED


def _with_tools(registry: ToolRegistry, define: Any) -> ToolRegistry:
    registry.register(define(mouse_position, category="desktop"))
    registry.register(define(move_mouse, category="desktop"))
    return registry


def _build(
    provider: Any,
    registry: ToolRegistry,
    *,
    policy: PolicyEngine | None = None,
) -> tuple[CommandRegistry, AgentCore, _CountingExecutor]:
    """A command registry whose ``ask`` runs through a real agent core."""

    executor = _CountingExecutor(registry)
    core = AgentCore.from_provider(
        provider,
        registry=registry,
        executor=executor,
        policy=policy,
        system_prompt="Test system prompt.",
    )
    # First positional is the tool service (unused here); the provider is
    # handed in as the llm_service only so `llm` status has something to read.
    commands = CommandRegistry(None, provider, agent=core)
    return commands, core, executor


async def _ask(commands: CommandRegistry, line: str) -> str:
    """Parse and execute one raw CLI line, exactly as the input loop would."""

    command = CommandParser().parse(line)
    assert command is not None
    return await commands.execute(command)


# ==============================================================
# 1. ask hello -- a plain answer, no tools
# ==============================================================


class TestAskHello:
    @pytest.mark.asyncio
    async def test_a_plain_question_is_answered_and_runs_no_tool(
        self, make_provider: Any, registry: ToolRegistry, invoked: Any
    ) -> None:
        # Empty registry: the agent advertises no tools, so the turn is prose
        # and the first answer ends the run.
        provider = make_provider(generate_result="Hello there.")
        commands, _core, executor = _build(provider, registry)

        output = await _ask(commands, "ask hello")

        assert output == "Hello there."
        assert executor.asked == []
        assert invoked == []


# ==============================================================
# 2. ask what is my mouse position? -- a read-only tool
# ==============================================================


class TestAskMousePosition:
    @pytest.mark.asyncio
    async def test_the_read_only_tool_passes_through_the_whole_chain(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        define: Any,
        tool_calls: Any,
        answer: Any,
        invoked: Any,
    ) -> None:
        policy = PolicyEngine(PolicyConfig())
        _with_tools(registry, define)
        provider = make_provider(
            [
                tool_calls(("mouse_position", {})),
                answer("The cursor is at 7, 11."),
            ]
        )
        commands, core, executor = _build(provider, registry, policy=policy)

        output = await _ask(commands, "ask what is my mouse position?")

        # The answer is shown, with the tool that produced it (and no "(failed)"
        # marker -- the recorded result was ok).
        assert "The cursor is at 7, 11." in output
        assert "Tools used: mouse_position" in output
        assert "(failed)" not in output
        # Agent -> Policy: a real gate is in the path...
        assert core.policy is policy
        # ...-> ToolExecutor: the executor was asked, which happens only after
        # the gate returns ALLOW...
        assert executor.asked == ["mouse_position"]
        # ...-> actual tool: the tool body itself ran.
        assert ("mouse_position", {}) in invoked


# ==============================================================
# 3. ask move my mouse to 500,300 -- a tool with arguments
# ==============================================================


class TestAskMoveMouse:
    @pytest.mark.asyncio
    async def test_a_tool_with_arguments_reaches_the_tool_body_with_them(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        define: Any,
        tool_calls: Any,
        answer: Any,
        invoked: Any,
    ) -> None:
        policy = PolicyEngine(PolicyConfig())
        _with_tools(registry, define)
        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 500, "y": 300})),
                answer("Moved the mouse to 500, 300."),
            ]
        )
        commands, core, executor = _build(provider, registry, policy=policy)

        output = await _ask(commands, "ask move my mouse to 500,300")

        assert "Moved the mouse to 500, 300." in output
        assert "Tools used: move_mouse" in output
        assert "(failed)" not in output
        assert core.policy is policy
        assert executor.asked == ["move_mouse"]
        # The arguments survived the whole chain and reached the tool body.
        assert ("move_mouse", {"x": 500, "y": 300}) in invoked
