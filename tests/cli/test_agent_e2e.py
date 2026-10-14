"""
End-to-end validation of the AetherOS agent through the CLI.

These two runs exercise the *entire* production chain for the mouse tools, with
a fake only at the hardware seam:

    CLI -> AgentCore -> planner (LLM) -> Policy -> ToolExecutor
        -> the real ``mouse_position`` / ``move_mouse`` tool
        -> the real ``MouseService`` -> MouseController (fake PyAutoGUI)
        -> result -> AgentCore -> LLM -> final response

Everything above the controller is the real object: the real ``@tool``
definitions copied out of the process-wide ``tool_registry`` (so the schema the
planner sees is the production schema), a real ``PolicyEngine``, the real
``ToolExecutor`` (wrapped only to witness delegation), the real
``ToolExecutionCoordinator`` and ``AgentPlanner`` inside ``AgentCore``, and the
real CLI ``ask`` handler reached through ``CommandParser``.

Only two things are doubled, and both are legitimate boundaries: the LLM (a
scripted provider, so the turn is deterministic and no model is called) and the
``MouseController`` (a recording fake, so no real cursor is touched). The fake
controller is the honest witness for the bottom of the chain -- a coordinate
appears in ``moves`` only if it travelled the whole path and reached the seam.
"""

from __future__ import annotations

import contextlib
from typing import Any

import pytest

from aetheros.agents.core import AgentCore
from aetheros.agents.policy import PolicyConfig, PolicyEngine
from aetheros.cli.commands import CommandRegistry
from aetheros.cli.parser import CommandParser
from aetheros.core.container import container
from aetheros.core.interfaces.mouse_controller import MouseController
from aetheros.desktop.mouse import tools as _mouse_tools  # noqa: F401 - registers tools
from aetheros.desktop.mouse.controller import MouseService
from aetheros.tools import tool_registry
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry
from aetheros.tools.schema import ToolSchemaGenerator


# ==============================================================
# Fakes: the two legitimate boundaries (hardware + model)
# ==============================================================


class _RecordingMouse(MouseController):
    """A ``MouseController`` sitting where PyAutoGUI would.

    Reports a fixed position for the read-only tool and records every absolute
    move, so ``moves`` is proof that a coordinate travelled the full chain and
    arrived at the seam -- and nothing else stubbed, so the abstract interface
    is satisfied without touching a real cursor.
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
    ALLOW, so it is the witness that the call passed Policy and went through
    ``ToolExecutor`` rather than around it.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        super().__init__(registry=registry, timeout_seconds=None)
        self.asked: list[str] = []

    async def execute_safe(self, name: str, arguments: dict[str, Any]) -> Any:
        self.asked.append(name)
        return await super().execute_safe(name, arguments)


# ==============================================================
# Helpers
# ==============================================================


@contextlib.contextmanager
def _fake_mouse():
    """Bind the ``MouseService`` the tools resolve to a recording controller.

    The real tool does ``container.resolve(MouseService)`` at call time, so the
    seam is swapped here and removed afterwards -- no global state leaks between
    tests.
    """

    mouse = _RecordingMouse()
    container.register_singleton(MouseService, lambda: MouseService(mouse))
    try:
        yield mouse
    finally:
        container.remove(MouseService)


def _with_real_tool(registry: ToolRegistry, name: str) -> ToolRegistry:
    """Copy one *production* tool definition into an isolated registry."""

    registry.register(tool_registry.get(name))
    return registry


def _build(
    provider: Any,
    registry: ToolRegistry,
    policy: PolicyEngine,
) -> tuple[CommandRegistry, AgentCore, _CountingExecutor]:
    """A CLI command registry whose ``ask`` runs the real agent core."""

    executor = _CountingExecutor(registry)
    core = AgentCore.from_provider(
        provider,
        registry=registry,
        executor=executor,
        policy=policy,
        system_prompt="Test system prompt.",
    )
    commands = CommandRegistry(None, provider, agent=core)
    return commands, core, executor


async def _ask(commands: CommandRegistry, line: str) -> str:
    command = CommandParser().parse(line)
    assert command is not None
    return await commands.execute(command)


# ==============================================================
# 0. Tool schema -- what the planner (LLM) is offered
# ==============================================================


class TestToolSchema:
    def test_the_production_mouse_tool_schemas_are_correct(self) -> None:
        gen = ToolSchemaGenerator()

        position = gen.generate(tool_registry.get("mouse_position"))
        assert position["function"]["name"] == "mouse_position"
        assert position["function"]["parameters"]["required"] == []

        move = gen.generate(tool_registry.get("move_mouse"))
        assert move["function"]["name"] == "move_mouse"
        params = move["function"]["parameters"]
        # x and y are integers and required; the optional duration is not.
        assert params["properties"]["x"] == {"type": "integer"}
        assert params["properties"]["y"] == {"type": "integer"}
        assert set(params["required"]) == {"x", "y"}
        assert "duration" not in params["required"]


# ==============================================================
# 1. "What is my current mouse position?"
# ==============================================================


class TestMousePositionE2E:
    @pytest.mark.asyncio
    async def test_position_flows_through_the_full_chain(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        policy = PolicyEngine(PolicyConfig())
        _with_real_tool(registry, "mouse_position")
        provider = make_provider(
            [
                tool_calls(("mouse_position", {})),
                answer("Your cursor is at x=7, y=11."),
            ]
        )
        commands, core, executor = _build(provider, registry, policy)

        with _fake_mouse():
            output = await _ask(commands, "ask What is my current mouse position?")

        # LLM chose the tool, it passed Policy, ToolExecutor ran it...
        assert core.policy is policy
        assert executor.asked == ["mouse_position"]
        # ...the real tool -> MouseService -> controller returned coordinates,
        # recorded ok, and the final response was generated from them.
        assert "Your cursor is at x=7, y=11." in output
        assert "Tools used: mouse_position" in output
        assert "(failed)" not in output


# ==============================================================
# 2. "Move my mouse to 500,300."
# ==============================================================


class TestMouseMovementE2E:
    @pytest.mark.asyncio
    async def test_move_flows_through_the_full_chain_with_arguments(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        tool_calls: Any,
        answer: Any,
    ) -> None:
        policy = PolicyEngine(PolicyConfig())
        _with_real_tool(registry, "move_mouse")
        provider = make_provider(
            [
                tool_calls(("move_mouse", {"x": 500, "y": 300})),
                answer("Moved your mouse to 500, 300."),
            ]
        )
        commands, core, executor = _build(provider, registry, policy)

        with _fake_mouse() as mouse:
            output = await _ask(commands, "ask Move my mouse to 500,300.")

        assert core.policy is policy
        assert executor.asked == ["move_mouse"]
        assert "Moved your mouse to 500, 300." in output
        assert "Tools used: move_mouse" in output
        assert "(failed)" not in output
        # The arguments survived every hop and reached the hardware seam...
        assert mouse.moves == [(500, 300, 0.0)]
        # ...exactly once, via the executor: no direct invocation bypassed it.
        assert len([a for a in executor.asked if a == "move_mouse"]) == len(
            mouse.moves
        )
