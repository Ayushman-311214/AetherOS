"""
End-to-end: the live trace of "What is my mouse position?" (PHASE 14).

This is the whole point of the trace layer proved in one run. The pipeline is
production -- the real ``mouse_position`` @tool copied out of the process-wide
registry, a real ``PolicyEngine``, the real ``ToolExecutor`` and ``AgentCore``,
the real planner emitting through the real emitter -- with fakes only at the two
legitimate seams: the LLM (scripted, so the turn is deterministic) and the mouse
backend (a controller returning a fixed position, so no real cursor is read).

A :class:`TraceCollector` subscribed to the shared bus is the honest witness:
a stage appears in its record only because a real component emitted it while
travelling the real chain. The brief's required order --

    INPUT_RECEIVED -> AGENT_STARTED -> LLM_REQUEST_STARTED
    -> LLM_RESPONSE_RECEIVED -> PLANNER_DECISION -> TOOL_SELECTED
    -> TOOL_EXECUTION_STARTED -> TOOL_EXECUTION_COMPLETED
    -> OBSERVATION_CREATED -> FINAL_RESPONSE_CREATED

is asserted as an *ordered subsequence* of the emitted stream, because the real
stream also carries the iteration and validation bookkeeping and a second LLM
turn -- the pipeline stages must appear, in order, among them.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from typing import Any

import pytest

from aetheros.agents.core import AgentCore
from aetheros.agents.policy import PolicyConfig, PolicyEngine
from aetheros.agents.state import STOP_FINAL_ANSWER
from aetheros.core.container import container
from aetheros.core.observability import TraceEventType
from aetheros.desktop.mouse import tools as _mouse_tools  # noqa: F401 - registers
from aetheros.desktop.mouse.controller import MouseService
from aetheros.tools import tool_registry
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry

# ``TraceCollector`` (the recording subscriber, injected via the ``collector``
# fixture) lives in this package's conftest. It is annotated ``Any`` at the call
# sites below because tests/ has no __init__.py -- the sibling conftest shares its
# fixtures, not its importable name.


# The stages PHASE 14 pins, in the order they must occur.
_EXPECTED_PIPELINE = [
    TraceEventType.INPUT_RECEIVED,
    TraceEventType.AGENT_STARTED,
    TraceEventType.LLM_REQUEST_STARTED,
    TraceEventType.LLM_RESPONSE_RECEIVED,
    TraceEventType.PLANNER_DECISION,
    TraceEventType.TOOL_SELECTED,
    TraceEventType.TOOL_EXECUTION_STARTED,
    TraceEventType.TOOL_EXECUTION_COMPLETED,
    TraceEventType.OBSERVATION_CREATED,
    TraceEventType.FINAL_RESPONSE_CREATED,
]


class _FakeMouseController:
    """The one seam below MouseService -- returns a fixed cursor position.

    Duck-typed rather than a MouseController subclass: MouseService only calls
    ``position()`` on this path, and a name reaches ``position_calls`` only if the
    tool actually ran, which is what makes it a witness of the full delegation.
    """

    def __init__(self, x: int = 500, y: int = 300) -> None:
        self._pos = (x, y)
        self.position_calls = 0

    def position(self) -> tuple[int, int]:
        self.position_calls += 1
        return self._pos


@contextlib.contextmanager
def _fake_mouse():
    """Bind the ``MouseService`` the tool resolves to a fixed-position backend."""

    controller = _FakeMouseController()
    container.register_singleton(MouseService, lambda: MouseService(controller))
    try:
        yield controller
    finally:
        container.remove(MouseService)


def _is_ordered_subsequence(expected: list[Any], actual: Iterable[Any]) -> bool:
    """True if every item of ``expected`` occurs in ``actual`` in order."""

    stream = iter(actual)
    return all(item in stream for item in expected)


class TestMousePositionPipelineE2E:
    @pytest.mark.asyncio
    async def test_the_full_pipeline_emits_every_stage_in_order(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        tool_calls: Any,
        answer: Any,
        collector: Any,
    ) -> None:
        # Real tool, real schema: copy the production definition into the
        # isolated registry so the planner is offered exactly what ships.
        registry.register(tool_registry.get("mouse_position"))

        provider = make_provider(
            [
                # Turn 1: the model asks for the position.
                tool_calls(("mouse_position", {})),
                # Turn 2: with the observation in hand, it answers.
                answer("Your mouse is at x=500, y=300."),
            ]
        )
        core = AgentCore.from_provider(
            provider,
            registry=registry,
            executor=ToolExecutor(registry=registry, timeout_seconds=None),
            policy=PolicyEngine(PolicyConfig()),
            system_prompt="Test system prompt.",
        )

        with _fake_mouse() as controller:
            result = await core.run("What is my mouse position?")

        # The run really executed the tool and answered from its result.
        assert result.stopped_reason == STOP_FINAL_ANSWER
        assert result.final_response == "Your mouse is at x=500, y=300."
        assert controller.position_calls == 1

        # Every PHASE 14 stage appears, in order, in the emitted stream.
        types = collector.types
        assert _is_ordered_subsequence(_EXPECTED_PIPELINE, types), (
            "expected the PHASE 14 stages in order; got "
            f"{[t.value for t in types]}"
        )

    @pytest.mark.asyncio
    async def test_the_run_id_correlates_the_whole_stream(
        self,
        make_provider: Any,
        registry: ToolRegistry,
        tool_calls: Any,
        answer: Any,
        collector: Any,
    ) -> None:
        # PHASE 13: one run id threads every stage, so a dashboard or a JSONL file
        # can group the pipeline back together.
        registry.register(tool_registry.get("mouse_position"))
        provider = make_provider(
            [
                tool_calls(("mouse_position", {})),
                answer("Your mouse is at x=500, y=300."),
            ]
        )
        core = AgentCore.from_provider(
            provider,
            registry=registry,
            executor=ToolExecutor(registry=registry, timeout_seconds=None),
            policy=PolicyEngine(PolicyConfig()),
            system_prompt="Test system prompt.",
        )

        with _fake_mouse():
            await core.run("What is my mouse position?")

        correlated = {e.run_id for e in collector.events if e.run_id}
        assert len(correlated) == 1
        run_id = correlated.pop()
        # The bookends both carry it.
        first = collector.of_type(TraceEventType.INPUT_RECEIVED)[0]
        last = collector.of_type(TraceEventType.FINAL_RESPONSE_CREATED)[-1]
        assert first.run_id == run_id
        assert last.run_id == run_id
