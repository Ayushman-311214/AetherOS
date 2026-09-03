"""
Tests for the agent tool-execution coordinator.

The coordinator sits between a validated call and the authoritative
``ToolExecutor``, and it owns exactly three things the engine cannot: it refuses
before delegating, it records what happened into ``AgentState``, and it reports
one structured outcome. So the properties pinned below are that a refusal never
reaches a tool function, that a tool-level problem arrives as a result rather
than an exception, that the state gains exactly the records the round produced,
and that ``delegated`` tells a caller truthfully whether a side effect may have
occurred.

Two things are deliberately *not* under test here, because they are not this
layer's job. Argument validation belongs to the planner and the executor -- the
invalid-arguments case below asserts that the engine's verdict is captured, not
that the coordinator re-derived it. And result text is rendered once by
``ToolResultRecord``; the assertions read ``content`` rather than re-computing it.
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from aetheros.agents.execution import (
    AgentExecutionResult,
    ExecutionBatch,
    ExecutionConfig,
    ExecutionStatus,
    ToolExecutionCoordinator,
)
from aetheros.agents.planner import PlannedAction
from aetheros.agents.state import AgentState
from aetheros.core.errors.agent_error import AgentError
from aetheros.core.errors.tool_error import ToolError
from aetheros.llm.tool_calls import ToolCall
from aetheros.tools.executor import ToolExecutor
from aetheros.tools.registry import ToolRegistry


# ==============================================================
# Tool doubles
# ==============================================================

# Real signatures, because ToolValidator reads them: an invalid-arguments case
# is only meaningful against a function that actually declares its parameters.


def move_mouse(x: int, y: int) -> str:
    """Move the cursor to a screen coordinate."""

    return f"moved to {x},{y}"


def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read a file from disk."""

    return f"read {path} as {encoding}"


def retired_tool(target: str) -> str:
    """A tool that is registered but switched off."""

    return f"retired {target}"


def quote(symbol: str) -> dict[str, Any]:
    """Return a structured quote, so the rendered content is JSON."""

    return {"symbol": symbol, "last": 1420.5}


def explodes(reason: str) -> str:
    """A tool that raises an ordinary exception."""

    raise ValueError(f"boom: {reason}")


def refuses(reason: str) -> str:
    """A tool that raises the domain error."""

    raise ToolError(f"refused: {reason}")


async def add_async(a: int, b: int) -> int:
    """An async tool, to prove the coordinator does not care which it got."""

    await asyncio.sleep(0)
    return a + b


# ==============================================================
# Doubles that record
# ==============================================================


def _journalled(journal: list[str], name: str) -> Any:
    """An async tool that brackets its own run in ``journal``.

    Two entries rather than one, and a yield between them, because that is what
    separates *sequential* from *concurrent*: run one at a time the journal reads
    ``a:start, a:end, b:start, b:end``; gathered it reads
    ``a:start, b:start, ...``.
    """

    async def tool(target: str) -> str:
        journal.append(f"{name}:start")
        await asyncio.sleep(0)
        journal.append(f"{name}:end")
        return f"{name} touched {target}"

    tool.__name__ = name
    tool.__doc__ = f"Recording double for {name}."

    return tool


class _CountingExecutor(ToolExecutor):
    """The real engine, counting how often it was asked.

    A subclass rather than a stub: the point of several cases below is that the
    coordinator's verdict agrees with the engine's, which is only meaningful if
    the engine is the real one. ``delegated`` claims the engine was reached, and
    ``asked`` is the independent witness.
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


async def _started(goal: str = "Analyze RELIANCE", **kwargs: Any) -> AgentState:
    """A running, seeded state on its first iteration."""

    state = AgentState(goal, **kwargs)
    await state.start()
    await state.seed_conversation("Test system prompt.")
    await state.next_iteration()
    return state


def _call(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    call_id: str = "call_0",
) -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments or {})


# ==============================================================
# Fixtures
# ==============================================================


@pytest.fixture
def journal() -> list[str]:
    """Where the recording doubles write. Empty means nothing ran."""

    return []


@pytest.fixture
def tools(registry: ToolRegistry, define: Any, journal: list[str]) -> ToolRegistry:
    """An isolated registry: live tools, one disabled, one that records."""

    registry.register(define(move_mouse, category="desktop"))
    registry.register(define(read_file, category="files"))
    registry.register(define(quote, category="market"))
    registry.register(define(add_async, category="math"))
    registry.register(define(explodes, category="test"))
    registry.register(define(refuses, category="test"))
    registry.register(define(retired_tool, category="files", enabled=False))
    registry.register(define(_journalled(journal, "watched"), category="test"))

    return registry


@pytest.fixture
def executor(tools: ToolRegistry) -> _CountingExecutor:
    """The real engine over the isolated registry, with no time budget.

    ``timeout_seconds=None`` is deliberate and matches the tool-executor suite:
    an unbounded budget keeps the tests from depending on machine speed.
    """

    return _CountingExecutor(tools)


@pytest.fixture
def coordinator(
    executor: _CountingExecutor,
    tools: ToolRegistry,
) -> ToolExecutionCoordinator:
    """Engine and coordinator over the *same* registry.

    The class docstring makes this an invariant rather than a convenience: the
    existence and enabled checks answer for the registry the coordinator holds,
    so an engine reading a different one would contradict its own coordinator.
    """

    return ToolExecutionCoordinator(executor, registry=tools)


# ==============================================================
# Successful execution
# ==============================================================


class TestSuccessfulExecution:
    """A live tool with good arguments: run it, record it, report it."""

    @pytest.mark.asyncio
    async def test_a_successful_call_reports_ok(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 4, "y": 9}))

        assert result.ok
        assert result.status is ExecutionStatus.OK
        assert not result.failed
        assert result.error is None
        assert result.error_type is None

    @pytest.mark.asyncio
    async def test_a_success_reached_the_engine_and_the_state(
        self,
        coordinator: ToolExecutionCoordinator,
        executor: _CountingExecutor,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 2}))

        assert result.delegated
        assert not result.refused
        assert result.recorded
        assert executor.asked == ["move_mouse"]

    @pytest.mark.asyncio
    async def test_the_result_carries_the_text_the_model_will_read(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 7, "y": 8}))

        assert result.value == "moved to 7,8"
        assert result.content == "moved to 7,8"
        # The same string the transcript holds, rendered once by the state layer.
        assert state.tool_results[-1].content == result.content

    @pytest.mark.asyncio
    async def test_a_structured_value_is_rendered_as_json(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("quote", {"symbol": "RELIANCE"}),
        )

        assert result.value == {"symbol": "RELIANCE", "last": 1420.5}
        assert '"symbol": "RELIANCE"' in result.content

    @pytest.mark.asyncio
    async def test_the_state_gains_one_call_and_one_result(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        await coordinator.execute(state, _call("read_file", {"path": "notes.md"}))

        assert len(state.tool_calls) == 1
        assert len(state.tool_results) == 1
        assert state.tool_calls[0].name == "read_file"
        assert state.tool_results[0].ok
        # A success is not a failure, so the ledger stays empty.
        assert state.errors == ()

    @pytest.mark.asyncio
    async def test_the_result_names_the_call_it_answers(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("read_file", {"path": "a.txt"}, call_id="call_xyz"),
        )

        assert result.call_id == "call_xyz"
        assert result.tool_name == "read_file"
        assert state.tool_calls[0].id == "call_xyz"
        assert state.tool_results[0].call_id == "call_xyz"

    @pytest.mark.asyncio
    async def test_an_async_tool_executes_the_same_way(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("add_async", {"a": 2, "b": 3}))

        assert result.ok
        assert result.value == 5
        assert result.content == "5"

    @pytest.mark.asyncio
    async def test_a_planned_action_is_accepted_as_well_as_a_tool_call(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # The planner emits PlannedAction; the parse layer emits ToolCall. Both
        # describe the same validated call, so both are accepted directly rather
        # than converted at every call site.
        state = await _started()

        action = PlannedAction.tool_call(
            "move_mouse",
            {"x": 3, "y": 4},
            call_id="call_from_plan",
        )
        result = await coordinator.execute(state, action)

        assert result.ok
        assert result.call_id == "call_from_plan"
        assert result.value == "moved to 3,4"

    @pytest.mark.asyncio
    async def test_the_result_reports_both_timings(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 0, "y": 0}))

        # duration_ms is the tool's own time; total_ms is this layer's whole span,
        # so it also covers the checks and the two state writes.
        assert result.duration_ms >= 0.0
        assert result.total_ms >= result.duration_ms

    @pytest.mark.asyncio
    async def test_the_arguments_are_copied_not_shared(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        arguments = {"path": "notes.md"}
        result = await coordinator.execute(state, _call("read_file", arguments))

        result.arguments["path"] = "mutated.md"

        assert arguments == {"path": "notes.md"}

    @pytest.mark.asyncio
    async def test_the_result_is_frozen(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # What a tool did is a fact about the run; an editable fact is not an
        # audit trail.
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 1}))

        with pytest.raises(FrozenInstanceError):
            result.ok = False  # type: ignore[misc]


# ==============================================================
# Unknown tool
# ==============================================================


class TestUnknownTool:
    """A name the registry has never heard of is refused before delegation."""

    @pytest.mark.asyncio
    async def test_an_unknown_tool_is_refused(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("teleport", {"x": 1}))

        assert not result.ok
        assert result.refused
        assert result.status is ExecutionStatus.REFUSED
        assert result.error_type == "UnknownTool"

    @pytest.mark.asyncio
    async def test_a_refusal_never_reaches_the_engine(
        self,
        coordinator: ToolExecutionCoordinator,
        executor: _CountingExecutor,
    ) -> None:
        # The distinction the engine cannot express: its own UnknownTool result is
        # shaped exactly like a result from a tool that ran.
        state = await _started()

        result = await coordinator.execute(state, _call("teleport"))

        assert not result.delegated
        assert executor.asked == []

    @pytest.mark.asyncio
    async def test_the_refusal_lists_the_tools_that_do_exist(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("teleport"))

        assert result.error is not None
        assert "Unknown tool 'teleport'" in result.error
        assert "move_mouse" in result.error
        # Enabled only, matching the planner: a disabled tool is not available,
        # whatever the registry still holds.
        assert "retired_tool" not in result.error

    @pytest.mark.asyncio
    async def test_a_refusal_reports_no_execution_time(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # A non-zero duration for a tool that was never reached would be a small
        # lie in every latency figure derived from the logs.
        state = await _started()

        result = await coordinator.execute(state, _call("teleport"))

        assert result.duration_ms == 0.0

    @pytest.mark.asyncio
    async def test_a_refusal_is_still_recorded_for_the_model_to_read(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # A provider rejects an assistant turn whose tool calls are not all
        # answered, so a refused call still needs a call record and a result.
        state = await _started()

        result = await coordinator.execute(state, _call("teleport"))

        assert result.recorded
        assert len(state.tool_calls) == 1
        assert len(state.tool_results) == 1
        assert state.tool_results[0].ok is False
        assert result.content.startswith("Error:")


# ==============================================================
# Disabled tool
# ==============================================================


class TestDisabledTool:
    """Registered but switched off is refused too, and named differently."""

    @pytest.mark.asyncio
    async def test_a_disabled_tool_is_refused(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("retired_tool", {"target": "anything"}),
        )

        assert not result.ok
        assert result.refused
        assert result.status is ExecutionStatus.REFUSED
        assert result.error_type == "ToolDisabled"
        assert result.error == "Tool 'retired_tool' is disabled."

    @pytest.mark.asyncio
    async def test_a_disabled_tool_does_not_run(
        self,
        coordinator: ToolExecutionCoordinator,
        executor: _CountingExecutor,
    ) -> None:
        state = await _started()

        await coordinator.execute(state, _call("retired_tool", {"target": "x"}))

        assert executor.asked == []

    @pytest.mark.asyncio
    async def test_disabling_a_tool_mid_run_takes_effect(
        self,
        coordinator: ToolExecutionCoordinator,
        tools: ToolRegistry,
        journal: list[str],
    ) -> None:
        # The coordinator reads the registry per call rather than caching it, so a
        # tool switched off between iterations stops being executed.
        state = await _started()

        first = await coordinator.execute(state, _call("watched", {"target": "a"}))
        tools.disable("watched")
        second = await coordinator.execute(
            state,
            _call("watched", {"target": "b"}, call_id="call_1"),
        )

        assert first.ok
        assert second.refused
        assert second.error_type == "ToolDisabled"
        assert journal == ["watched:start", "watched:end"]


# ==============================================================
# Invalid arguments
# ==============================================================


class TestInvalidArguments:
    """The engine's verdict is captured, not re-derived.

    The planner checks arguments before it plans a call and the executor checks
    them again before it touches the tool. A third pass here would only add a
    third place for the three to disagree, so an ``InvalidArguments`` failure
    arrives exactly the way a tool crash does -- as an outcome to record.
    """

    @pytest.mark.asyncio
    async def test_a_missing_argument_fails(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 5}))

        assert not result.ok
        assert result.error_type == "InvalidArguments"
        assert result.error is not None
        assert "'y'" in result.error

    @pytest.mark.asyncio
    async def test_invalid_arguments_reach_the_engine_and_stop_there(
        self,
        coordinator: ToolExecutionCoordinator,
        executor: _CountingExecutor,
        journal: list[str],
    ) -> None:
        # Delegated, because the argument check is the engine's; failed rather
        # than refused, because the engine was asked. The function still never
        # runs -- the validator sits in front of it.
        state = await _started()

        result = await coordinator.execute(state, _call("watched", {"wrong": "x"}))

        assert result.delegated
        assert not result.refused
        assert result.status is ExecutionStatus.FAILED
        assert executor.asked == ["watched"]
        assert journal == []

    @pytest.mark.asyncio
    async def test_an_unknown_argument_is_rejected(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("read_file", {"path": "a.txt", "mode": "rb"}),
        )

        assert result.error_type == "InvalidArguments"
        assert result.error is not None
        assert "'mode'" in result.error

    @pytest.mark.asyncio
    async def test_a_wrong_type_is_rejected(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("move_mouse", {"x": "left", "y": 3}),
        )

        assert result.error_type == "InvalidArguments"

    @pytest.mark.asyncio
    async def test_an_argument_failure_is_recorded(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 5}))

        assert result.recorded
        assert state.tool_results[0].error_type == "InvalidArguments"
        assert len(state.errors) == 1


# ==============================================================
# Tool failure
# ==============================================================


class TestToolFailure:
    """A tool that ran and raised is data, not an exception."""

    @pytest.mark.asyncio
    async def test_a_raising_tool_reports_its_exception_type(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("explodes", {"reason": "disk"}))

        assert not result.ok
        assert result.status is ExecutionStatus.FAILED
        assert result.delegated
        assert result.error_type == "ValueError"
        assert result.error == "Tool 'explodes' failed: ValueError: boom: disk"

    @pytest.mark.asyncio
    async def test_a_tool_error_is_reported_as_a_tool_error(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("refuses", {"reason": "policy"}),
        )

        assert result.error_type == "ToolError"
        assert result.error is not None
        assert "refused: policy" in result.error

    @pytest.mark.asyncio
    async def test_a_failure_still_produces_a_turn_the_model_can_read(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("explodes", {"reason": "disk"}))

        assert result.content == (
            "Error: Tool 'explodes' failed: ValueError: boom: disk"
        )
        assert state.tool_results[0].content == result.content

    @pytest.mark.asyncio
    async def test_a_failure_is_filed_in_the_error_ledger(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # Not redundant with the result: the result is the answer the model reads,
        # the ledger is what an orchestrator reads to tell a run is going badly.
        state = await _started()

        await coordinator.execute(state, _call("explodes", {"reason": "disk"}))

        assert len(state.errors) == 1
        recorded = state.errors[0]
        assert recorded.message == (
            "Tool 'explodes' failed: ValueError: boom: disk"
        )
        assert recorded.error_type == "ValueError"
        assert recorded.iteration == state.iteration
        # Recoverable: the model can pick another tool, so the run continues.
        assert recorded.recoverable
        assert not state.is_terminal

    @pytest.mark.asyncio
    async def test_record_errors_off_keeps_the_ledger_empty(
        self,
        executor: _CountingExecutor,
        tools: ToolRegistry,
    ) -> None:
        state = await _started()
        quiet = ToolExecutionCoordinator(
            executor,
            registry=tools,
            config=ExecutionConfig(record_errors=False),
        )

        result = await quiet.execute(state, _call("explodes", {"reason": "disk"}))

        assert not result.ok
        # Still recorded as a result -- the model has to be told -- but not filed.
        assert result.recorded
        assert len(state.tool_results) == 1
        assert state.errors == ()


# ==============================================================
# Multiple tool calls
# ==============================================================


class TestMultipleToolCalls:
    """One round, several calls: all answered, in order, one at a time."""

    @pytest.mark.asyncio
    async def test_every_call_is_answered(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        calls = [
            _call("move_mouse", {"x": 1, "y": 2}, call_id="call_0"),
            _call("read_file", {"path": "a.txt"}, call_id="call_1"),
            _call("add_async", {"a": 1, "b": 1}, call_id="call_2"),
        ]
        batch = await coordinator.execute_many(state, calls)

        assert isinstance(batch, ExecutionBatch)
        assert len(batch) == 3
        assert batch.all_ok
        assert not batch.any_failed
        assert len(state.tool_results) == 3

    @pytest.mark.asyncio
    async def test_results_come_back_in_model_order(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        calls = [
            _call("read_file", {"path": "a.txt"}, call_id="call_0"),
            _call("move_mouse", {"x": 9, "y": 9}, call_id="call_1"),
        ]
        batch = await coordinator.execute_many(state, calls)

        assert [r.tool_name for r in batch] == ["read_file", "move_mouse"]
        assert [r.call_id for r in batch] == ["call_0", "call_1"]

    @pytest.mark.asyncio
    async def test_a_failure_does_not_stop_the_round(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # A provider rejects an assistant turn whose tool calls are not all
        # answered, so stopping early would make the next request unsendable.
        state = await _started()

        calls = [
            _call("explodes", {"reason": "disk"}, call_id="call_0"),
            _call("teleport", {}, call_id="call_1"),
            _call("move_mouse", {"x": 2, "y": 2}, call_id="call_2"),
        ]
        batch = await coordinator.execute_many(state, calls)

        assert len(batch) == 3
        assert [r.status for r in batch] == [
            ExecutionStatus.FAILED,
            ExecutionStatus.REFUSED,
            ExecutionStatus.OK,
        ]
        assert len(batch.succeeded) == 1
        assert len(batch.failures) == 2
        assert len(batch.refusals) == 1
        assert batch.executed_count == 2
        assert batch.any_failed
        assert not batch.all_ok

    @pytest.mark.asyncio
    async def test_calls_run_one_at_a_time(
        self,
        coordinator: ToolExecutionCoordinator,
        tools: ToolRegistry,
        define: Any,
        journal: list[str],
    ) -> None:
        # The desktop tools share one mouse, one keyboard and one clipboard, so a
        # click racing a type_text produces an interleaving neither call asked for.
        state = await _started()
        tools.register(define(_journalled(journal, "second"), category="test"))

        calls = [
            _call("watched", {"target": "a"}, call_id="call_0"),
            _call("second", {"target": "b"}, call_id="call_1"),
        ]
        await coordinator.execute_many(state, calls)

        assert journal == [
            "watched:start",
            "watched:end",
            "second:start",
            "second:end",
        ]

    @pytest.mark.asyncio
    async def test_every_result_carries_the_same_iteration(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # Resolved once for the round, so another task advancing the state
        # mid-round cannot split one iteration's results across two numbers.
        state = await _started()
        await state.next_iteration()

        calls = [
            _call("move_mouse", {"x": 1, "y": 1}, call_id="call_0"),
            _call("read_file", {"path": "a.txt"}, call_id="call_1"),
        ]
        batch = await coordinator.execute_many(state, calls)

        assert batch.iteration == 2
        assert {r.iteration for r in batch} == {2}

    @pytest.mark.asyncio
    async def test_an_explicit_iteration_overrides_the_state(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("move_mouse", {"x": 1, "y": 1}),
            iteration=7,
        )

        assert result.iteration == 7
        assert state.tool_results[0].iteration == 7

    @pytest.mark.asyncio
    async def test_result_for_resolves_by_call_id(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        calls = [
            _call("move_mouse", {"x": 1, "y": 1}, call_id="call_a"),
            _call("read_file", {"path": "a.txt"}, call_id="call_b"),
        ]
        batch = await coordinator.execute_many(state, calls)

        found = batch.result_for("call_b")
        assert found is not None
        assert found.tool_name == "read_file"
        assert batch.result_for("call_missing") is None

    @pytest.mark.asyncio
    async def test_an_empty_round_is_all_ok(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # Nothing was asked, so nothing went wrong.
        state = await _started()

        batch = await coordinator.execute_many(state, [])

        assert len(batch) == 0
        assert batch.all_ok
        assert not batch.any_failed
        assert batch.executed_count == 0
        assert batch.total_ms == 0.0
        assert state.tool_calls == ()

    @pytest.mark.asyncio
    async def test_the_batch_summarises_the_round(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        calls = [
            _call("move_mouse", {"x": 1, "y": 1}, call_id="call_0"),
            _call("teleport", {}, call_id="call_1"),
        ]
        batch = await coordinator.execute_many(state, calls)
        summary = batch.describe()

        assert summary["calls"] == 2
        assert summary["succeeded"] == 1
        assert summary["failed"] == 1
        assert summary["refused"] == 1
        assert summary["executed"] == 1
        assert summary["iteration"] == batch.iteration
        assert len(summary["results"]) == 2

# ==============================================================
# A finished run
# ==============================================================


class TestTerminalRun:
    """Once a run has ended, nothing executes and nothing is written."""

    @pytest.mark.asyncio
    async def test_a_finished_run_executes_nothing(
        self,
        coordinator: ToolExecutionCoordinator,
        executor: _CountingExecutor,
    ) -> None:
        state = await _started()
        await state.complete("Done.")

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 1}))

        assert not result.ok
        assert result.refused
        assert result.error_type == "RunAlreadyFinished"
        assert executor.asked == []

    @pytest.mark.asyncio
    async def test_a_finished_run_is_not_written_to(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # AgentState refuses every recording once a run has ended, and it is right
        # to: a finished run whose transcript keeps growing is not a record of
        # anything. The refusal surfaces as recorded=False rather than as a raise.
        state = await _started()
        await state.cancel()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 1}))

        assert not result.recorded
        assert state.tool_calls == ()
        assert state.tool_results == ()
        assert state.errors == ()
        # The model still gets a turn for the call it asked for.
        assert result.content.startswith("Error:")


# ==============================================================
# Accepting a call
# ==============================================================


class TestCallShapes:
    """What counts as a validated call, and what is a programming error.

    These raise rather than returning a result, because they are not something a
    model can fix by trying again -- they mean a caller handed this layer
    something that was never a tool call.
    """

    @pytest.mark.asyncio
    async def test_a_final_response_action_is_not_a_call(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        with pytest.raises(AgentError) as caught:
            await coordinator.execute(state, PlannedAction.final_response("Done."))

        assert caught.value.code == "AGENT_EXECUTION_NOT_A_CALL"

    @pytest.mark.asyncio
    async def test_a_call_without_an_id_is_refused(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # parse_llm_response always synthesises call_<index>, and AgentState
        # refuses a result that does not name its call. Inventing an id here would
        # make the transcript claim the model said something it did not.
        state = await _started()

        action = PlannedAction.tool_call("move_mouse", {"x": 1, "y": 1})

        with pytest.raises(AgentError) as caught:
            await coordinator.execute(state, action)

        assert caught.value.code == "AGENT_EXECUTION_MISSING_CALL_ID"

    @pytest.mark.asyncio
    async def test_something_that_is_not_a_call_at_all_is_refused(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        with pytest.raises(AgentError):
            await coordinator.execute(state, "move_mouse")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_nothing_is_written_when_the_call_is_rejected(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        with pytest.raises(AgentError):
            await coordinator.execute(state, PlannedAction.final_response("Done."))

        assert state.tool_calls == ()
        assert state.tool_results == ()


# ==============================================================
# Log safety
# ==============================================================


class TestLogSafety:
    """Argument names may be logged. Argument values may not.

    ``type_text`` and ``set_clipboard`` receive literal keystrokes, which may be a
    password the user was pasting, and the file sinks keep what they are given for
    weeks. Same rule ``ToolExecutor._log_outcome`` applies.
    """

    @pytest.mark.asyncio
    async def test_describe_reports_names_without_values(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("read_file", {"path": "hunter2-secret.txt"}),
        )
        described = result.describe()

        assert described["argument_names"] == ["path"]
        assert "arguments" not in described
        assert "hunter2-secret.txt" not in repr(described)

    @pytest.mark.asyncio
    async def test_repr_withholds_values_and_content(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(
            state,
            _call("read_file", {"path": "hunter2-secret.txt"}),
        )
        text = repr(result)

        assert "hunter2-secret.txt" not in text
        assert "'path'" in text
        assert "content_chars=" in text

    @pytest.mark.asyncio
    async def test_describe_reports_content_as_a_length(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 1, "y": 2}))
        described = result.describe()

        assert described["content_chars"] == len(result.content)
        assert "content" not in described

    @pytest.mark.asyncio
    async def test_to_dict_is_faithful(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # The faithful view exists for persistence and replay, and is documented as
        # unsafe for the sinks precisely because it holds what describe() withholds.
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 3, "y": 4}))
        payload = result.to_dict()

        assert payload["arguments"] == {"x": 3, "y": 4}
        assert payload["value"] == "moved to 3,4"
        assert payload["content"] == "moved to 3,4"
        assert payload["status"] == "ok"
        assert payload["delegated"] is True
        assert payload["recorded"] is True

    @pytest.mark.asyncio
    async def test_to_dict_hands_out_a_copy_of_the_arguments(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        state = await _started()

        result = await coordinator.execute(state, _call("move_mouse", {"x": 3, "y": 4}))
        payload = result.to_dict()
        payload["arguments"]["x"] = 999

        assert result.arguments["x"] == 3


# ==============================================================
# Construction
# ==============================================================


class TestConstruction:
    """Defaults, and the invariant the class docstring states."""

    def test_the_default_config_is_the_strict_reading(self) -> None:
        config = ExecutionConfig()

        assert config.record_errors
        assert not config.log_arguments
        assert config.to_dict() == {
            "record_errors": True,
            "log_arguments": False,
        }

    def test_a_coordinator_exposes_its_config(
        self,
        executor: _CountingExecutor,
        tools: ToolRegistry,
    ) -> None:
        config = ExecutionConfig(record_errors=False, log_arguments=True)

        coordinator = ToolExecutionCoordinator(
            executor,
            registry=tools,
            config=config,
        )

        assert coordinator.config is config

    @pytest.mark.asyncio
    async def test_a_coordinator_holds_no_per_run_state(
        self,
        coordinator: ToolExecutionCoordinator,
    ) -> None:
        # One coordinator serves every concurrent agent, so two runs sharing it
        # must not see each other's records.
        first = await _started("Analyze RELIANCE")
        second = await _started("Analyze TCS")

        await coordinator.execute(first, _call("move_mouse", {"x": 1, "y": 1}))
        await coordinator.execute(second, _call("read_file", {"path": "a.txt"}))

        assert [r.name for r in first.tool_results] == ["move_mouse"]
        assert [r.name for r in second.tool_results] == ["read_file"]

    def test_the_result_type_is_importable_from_the_package(self) -> None:
        # The loop above this layer imports from aetheros.agents, not from the
        # module path.
        from aetheros import agents

        assert agents.AgentExecutionResult is AgentExecutionResult
        assert agents.ToolExecutionCoordinator is ToolExecutionCoordinator
