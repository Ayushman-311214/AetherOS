from __future__ import annotations

import json

import pytest

from aetheros.agents.execution import (
    AgentExecutionResult,
    ToolExecutionCoordinator,
)
from aetheros.llm.agent_loop import LLMToolLoop
from aetheros.llm.engine import LLMEngine
from aetheros.llm.tool_calls import ToolCall
from aetheros.llm.tool_schema import get_llm_tools
from aetheros.tools.executor import ToolExecutor


class RecordingCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ToolCall, int | None]] = []

    async def execute(self, state, call, *, iteration=None):
        self.calls.append((state, call, iteration))
        return AgentExecutionResult(
            call_id=call.id,
            tool_name=call.name,
            ok=True,
            value=5,
            content=json.dumps({"ok": True, "result": 5}),
            arguments=call.arguments,
            iteration=iteration or 0,
            recorded=True,
        )


def add(a: int, b: int) -> int:
    return a + b


@pytest.mark.asyncio
async def test_legacy_loop_delegates_tool_execution_to_coordinator(
    registry,
    define,
    make_provider,
    tool_calls,
    answer,
) -> None:
    registry.register(define(add))
    provider = make_provider(
        [
            tool_calls(("add", {"a": 2, "b": 3})),
            answer("done"),
        ]
    )
    coordinator = RecordingCoordinator()
    loop = LLMToolLoop(
        LLMEngine(
            provider,
            tool_provider=lambda: get_llm_tools(registry),
        ),
        ToolExecutor(registry),
        coordinator=coordinator,
    )

    result = await loop.run_detailed("calculate")

    assert result.content == "done"
    assert len(coordinator.calls) == 1
    state, call, iteration = coordinator.calls[0]
    assert call.name == "add"
    assert call.arguments == {"a": 2, "b": 3}
    assert iteration == 1
    assert state.goal == "calculate"
    assert state.is_terminal is True
    assert state.conversation()[:-1] == result.messages
    assert state.conversation()[-1] == {
        "role": "assistant",
        "content": "done",
    }


def test_loop_builds_default_coordinator_from_executor(registry) -> None:
    executor = ToolExecutor(registry)
    loop = LLMToolLoop(
        LLMEngine(object(), tool_provider=lambda: []),
        executor,
    )

    assert isinstance(loop.coordinator, ToolExecutionCoordinator)
    assert loop.coordinator.executor is executor
