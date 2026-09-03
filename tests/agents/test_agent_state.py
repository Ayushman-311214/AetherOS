"""
Tests for the agent execution state.

The state layer has no interesting arithmetic, so these tests are aimed almost
entirely at its *contract*: what it refuses. A record that accepts a fourth
iteration on a budget of three, or a second outcome on a finished run, still
returns plausible-looking data — it just describes a run that never happened,
and nothing downstream can detect that. So the guards get as much coverage as
the happy path.

Every async test carries an explicit ``@pytest.mark.asyncio`` because the
repository does not set ``asyncio_mode`` in pyproject.toml.
"""

from __future__ import annotations

import json

import pytest

from aetheros.agents.state import (
    DEFAULT_MAX_ITERATIONS,
    ITERATION_CEILING,
    STOP_CANCELLED,
    STOP_ERROR,
    STOP_FINAL_ANSWER,
    STOP_MAX_ITERATIONS,
    AgentState,
    AgentStatus,
    ErrorRecord,
    Message,
    Observation,
    ToolCallRecord,
    ToolResultRecord,
)
from aetheros.core.errors.agent_error import AgentError
from aetheros.llm.tool_calls import ToolCall
from aetheros.tools.executor import ToolExecutionResult

GOAL = "Analyze RELIANCE and estimate a one-day directional probability"


@pytest.fixture
def state() -> AgentState:
    return AgentState(GOAL, agent="market_analysis", max_iterations=3)


@pytest.fixture
def call() -> ToolCall:
    return ToolCall(
        id="call-1",
        name="get_quote",
        arguments={"symbol": "RELIANCE", "timeframe": "1d"},
        raw_arguments='{"symbol": "RELIANCE", "timeframe": "1d"}',
    )


@pytest.fixture
def ok_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        name="get_quote",
        ok=True,
        value={"symbol": "RELIANCE", "last": 2941.5},
        duration_ms=12.5,
    )


@pytest.fixture
def failed_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        name="get_quote",
        ok=False,
        error="upstream timeout",
        error_type="MarketDataError",
        duration_ms=5000.0,
    )


# ==============================================================
# Initial state
# ==============================================================


class TestInitialState:
    def test_starts_pending_and_empty(self, state: AgentState) -> None:
        assert state.goal == GOAL
        assert state.agent == "market_analysis"
        assert state.status is AgentStatus.PENDING
        assert state.iteration == 0
        assert state.max_iterations == 3
        assert state.final_response is None
        assert state.stopped_reason is None
        assert state.messages == ()
        assert state.tool_calls == ()
        assert state.tool_results == ()
        assert state.observations == ()
        assert state.errors == ()
        assert state.started_at is None
        assert state.completed_at is None
        assert not state.is_terminal
        assert not state.is_running
        assert state.has_iterations_left
        assert state.iterations_remaining == 3

    @pytest.mark.asyncio
    async def test_every_state_gets_its_own_identity(self) -> None:
        # No module singleton: two runs must not share a transcript.
        first, second = AgentState(GOAL), AgentState(GOAL)
        assert first.state_id != second.state_id

        await first.add_message(Message.user("only mine"))
        assert len(first.messages) == 1
        assert second.messages == ()

    def test_default_budget_matches_the_loop_layer(self) -> None:
        assert AgentState(GOAL).max_iterations == DEFAULT_MAX_ITERATIONS

    @pytest.mark.parametrize(
        ("requested", "expected"),
        [(0, 1), (-5, 1), (2, 2), (10_000, ITERATION_CEILING)],
    )
    def test_budget_is_clamped_not_rejected(
        self, requested: int, expected: int
    ) -> None:
        assert AgentState(GOAL, max_iterations=requested).max_iterations == expected

    @pytest.mark.parametrize("goal", ["", "   ", "\n\t"])
    def test_empty_goal_is_refused(self, goal: str) -> None:
        # A run with no objective has no completion condition.
        with pytest.raises(AgentError) as excinfo:
            AgentState(goal)
        assert excinfo.value.code == "AGENT_STATE_EMPTY_GOAL"

    def test_reads_cannot_mutate_the_transcript(self, state: AgentState) -> None:
        assert isinstance(state.messages, tuple)
        state.metadata["injected"] = True
        assert state.metadata == {}


# ==============================================================
# Lifecycle and iteration budget
# ==============================================================


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_moves_to_running(self, state: AgentState) -> None:
        await state.start()
        assert state.status is AgentStatus.RUNNING
        assert state.is_running
        assert state.started_at is not None

    @pytest.mark.asyncio
    async def test_second_start_is_refused(self, state: AgentState) -> None:
        # Restarting would reset the clock on a run already in progress.
        await state.start()
        with pytest.raises(AgentError) as excinfo:
            await state.start()
        assert excinfo.value.code == "AGENT_STATE_ALREADY_STARTED"

    @pytest.mark.asyncio
    async def test_iterations_advance_and_then_refuse(self, state: AgentState) -> None:
        await state.start()
        assert [await state.next_iteration() for _ in range(3)] == [1, 2, 3]
        assert not state.has_iterations_left
        assert state.iterations_remaining == 0

        with pytest.raises(AgentError) as excinfo:
            await state.next_iteration()
        assert excinfo.value.code == "AGENT_STATE_ITERATIONS_EXHAUSTED"

    @pytest.mark.asyncio
    async def test_cannot_iterate_before_starting(self, state: AgentState) -> None:
        with pytest.raises(AgentError) as excinfo:
            await state.next_iteration()
        assert excinfo.value.code == "AGENT_STATE_NOT_RUNNING"

    @pytest.mark.asyncio
    async def test_concurrent_iterations_do_not_overspend(self) -> None:
        # The point of the lock: without it, tasks reading the same iteration
        # count would all pass the same budget check.
        import asyncio

        state = AgentState(GOAL, max_iterations=5)
        await state.start()

        claimed = await asyncio.gather(
            *(state.next_iteration() for _ in range(5)),
        )
        assert sorted(claimed) == [1, 2, 3, 4, 5]
        assert state.iteration == 5


# ==============================================================
# Messages
# ==============================================================


class TestMessages:
    @pytest.mark.asyncio
    async def test_seed_opens_with_system_then_goal(self, state: AgentState) -> None:
        await state.seed_conversation("You are a market analyst.")
        roles = [m.role for m in state.messages]
        assert roles == ["system", "user"]
        assert state.messages[1].content == GOAL

    @pytest.mark.asyncio
    async def test_seeding_twice_is_refused(self, state: AgentState) -> None:
        await state.seed_conversation()
        with pytest.raises(AgentError) as excinfo:
            await state.seed_conversation()
        assert excinfo.value.code == "AGENT_STATE_ALREADY_SEEDED"

    @pytest.mark.asyncio
    async def test_messages_append_in_order(self, state: AgentState) -> None:
        await state.add_message(Message.user("first"))
        await state.extend_messages(
            [Message.assistant("second"), Message.user("third")]
        )
        assert [m.content for m in state.messages] == ["first", "second", "third"]

    def test_unknown_role_is_refused(self) -> None:
        with pytest.raises(AgentError) as excinfo:
            Message(role="analyst", content="hello")
        assert excinfo.value.code == "AGENT_STATE_INVALID_ROLE"

    def test_role_is_normalized(self) -> None:
        assert Message(role="  ASSISTANT ").role == "assistant"

    def test_tool_message_without_a_call_id_is_refused(self) -> None:
        # The wire format rejects it; failing here beats spending an iteration
        # to find out.
        with pytest.raises(AgentError) as excinfo:
            Message(role="tool", content="{}")
        assert excinfo.value.code == "AGENT_STATE_ORPHAN_TOOL_MESSAGE"

    def test_wire_shapes_match_the_loop_layer(self, call: ToolCall) -> None:
        assert Message.user("hi").to_wire() == {"role": "user", "content": "hi"}

        assistant = Message.assistant(tool_calls=(call,)).to_wire()
        assert assistant["role"] == "assistant"
        # None, not "": a tool-calling turn often carries no prose.
        assert assistant["content"] is None
        assert assistant["tool_calls"] == [
            {
                "id": "call-1",
                "type": "function",
                # The raw string the model produced, replayed verbatim.
                "function": {
                    "name": "get_quote",
                    "arguments": call.raw_arguments,
                },
            }
        ]

        assert Message.tool(tool_call_id="call-1", content="{}").to_wire() == {
            "role": "tool",
            "tool_call_id": "call-1",
            "content": "{}",
        }

    @pytest.mark.asyncio
    async def test_conversation_renders_every_turn(self, state: AgentState) -> None:
        await state.seed_conversation("system")
        assert state.conversation() == (
            {"role": "system", "content": "system"},
            {"role": "user", "content": GOAL},
        )


# ==============================================================
# Tool calls
# ==============================================================


class TestToolCalls:
    @pytest.mark.asyncio
    async def test_recording_adapts_the_parse_layer_type(
        self, state: AgentState, call: ToolCall
    ) -> None:
        await state.start()
        await state.next_iteration()

        record = await state.record_tool_call(call)
        assert state.tool_calls == (record,)
        assert record.id == "call-1"
        assert record.name == "get_quote"
        assert record.arguments == {"symbol": "RELIANCE", "timeframe": "1d"}
        # Tagged with the iteration that asked for it.
        assert record.iteration == 1

    @pytest.mark.asyncio
    async def test_arguments_are_copied_not_aliased(
        self, state: AgentState, call: ToolCall
    ) -> None:
        record = await state.record_tool_call(call)
        call.arguments["symbol"] = "TCS"
        assert record.arguments["symbol"] == "RELIANCE"

    @pytest.mark.asyncio
    async def test_explicit_iteration_wins(
        self, state: AgentState, call: ToolCall
    ) -> None:
        record = await state.record_tool_call(call, iteration=7)
        assert record.iteration == 7

    def test_argument_names_exclude_values(self, call: ToolCall) -> None:
        # The projection that is safe for the log sinks.
        record = ToolCallRecord.from_tool_call(call, iteration=1)
        assert record.argument_names == ("symbol", "timeframe")


# ==============================================================
# Tool results
# ==============================================================


class TestToolResults:
    @pytest.mark.asyncio
    async def test_successful_result_is_rendered_for_the_model(
        self, state: AgentState, ok_result: ToolExecutionResult
    ) -> None:
        await state.start()
        await state.next_iteration()

        record = await state.record_tool_result(ok_result, call_id="call-1")
        assert state.tool_results == (record,)
        assert record.ok
        assert record.call_id == "call-1"
        assert record.iteration == 1
        assert record.duration_ms == 12.5
        assert json.loads(record.content) == {"symbol": "RELIANCE", "last": 2941.5}

    @pytest.mark.asyncio
    async def test_failure_is_data_not_an_exception(
        self, state: AgentState, failed_result: ToolExecutionResult
    ) -> None:
        # The model is expected to read this and try something else.
        record = await state.record_tool_result(failed_result, call_id="call-1")
        assert not record.ok
        assert record.error == "upstream timeout"
        assert record.error_type == "MarketDataError"
        assert "upstream timeout" in record.content
        assert state.status is AgentStatus.PENDING
        assert not state.is_terminal

    @pytest.mark.asyncio
    async def test_result_must_name_the_call_it_answers(
        self, state: AgentState, ok_result: ToolExecutionResult
    ) -> None:
        with pytest.raises(AgentError) as excinfo:
            await state.record_tool_result(ok_result)
        assert excinfo.value.code == "AGENT_STATE_MISSING_CALL_ID"

    @pytest.mark.asyncio
    async def test_caller_supplied_content_is_preserved(
        self, state: AgentState, ok_result: ToolExecutionResult
    ) -> None:
        record = await state.record_tool_result(
            ok_result, call_id="call-1", content="RELIANCE at 2941.5"
        )
        assert record.content == "RELIANCE at 2941.5"

    @pytest.mark.asyncio
    async def test_results_can_be_matched_to_their_call(
        self, state: AgentState, ok_result: ToolExecutionResult
    ) -> None:
        await state.record_tool_result(ok_result, call_id="call-1")
        await state.record_tool_result(ok_result, call_id="call-2")
        assert len(state.results_for("call-1")) == 1
        assert state.results_for("missing") == ()

    def test_unserializable_values_still_produce_a_turn(self) -> None:
        # default=str: a tool returning a Path must not break the conversation.
        from pathlib import Path

        record = ToolResultRecord.from_execution(
            ToolExecutionResult(name="save", ok=True, value={"path": Path("/tmp/a")}),
            call_id="call-1",
        )
        assert "tmp" in record.content


# ==============================================================
# Observations
# ==============================================================


class TestObservations:
    @pytest.mark.asyncio
    async def test_observation_records_text_source_and_iteration(
        self, state: AgentState
    ) -> None:
        await state.start()
        await state.next_iteration()

        observation = await state.record_observation(
            "Price is above the 50-day moving average",
            source="market_analysis",
            metadata={"indicator": "sma_50"},
        )
        assert state.observations == (observation,)
        assert observation.source == "market_analysis"
        assert observation.iteration == 1
        assert observation.metadata == {"indicator": "sma_50"}
        assert observation.timestamp

    @pytest.mark.asyncio
    async def test_source_defaults_to_the_agent(self, state: AgentState) -> None:
        # Provenance matters: a vision reading and a market-data number are not
        # equally authoritative, and a critic has to be able to tell them apart.
        assert (await state.record_observation("noted")).source == "agent"


# ==============================================================
# Errors
# ==============================================================


class TestErrors:
    @pytest.mark.asyncio
    async def test_recording_an_error_does_not_end_the_run(
        self, state: AgentState
    ) -> None:
        await state.start()
        record = await state.record_error("indicator window too short")
        assert state.errors == (record,)
        assert record.recoverable
        assert record.error_type == "AgentError"
        assert state.status is AgentStatus.RUNNING
        assert not state.is_terminal

    @pytest.mark.asyncio
    async def test_exceptions_keep_their_type(self, state: AgentState) -> None:
        record = await state.record_error(ValueError("bad window"))
        assert record.error_type == "ValueError"
        assert record.message == "bad window"

    @pytest.mark.asyncio
    async def test_fail_marks_the_run_and_the_error_unrecoverable(
        self, state: AgentState
    ) -> None:
        await state.start()
        await state.fail(RuntimeError("provider unreachable"))

        assert state.status is AgentStatus.FAILED
        assert state.is_terminal
        assert state.stopped_reason == STOP_ERROR
        assert state.completed_at is not None
        assert state.final_response is None

        assert state.last_error is not None
        assert state.last_error.error_type == "RuntimeError"
        assert not state.last_error.recoverable

    @pytest.mark.asyncio
    async def test_last_error_is_the_most_recent(self, state: AgentState) -> None:
        await state.record_error("first")
        await state.record_error("second")
        assert state.last_error is not None
        assert state.last_error.message == "second"


# ==============================================================
# Completion
# ==============================================================


class TestCompletion:
    @pytest.mark.asyncio
    async def test_complete_records_the_answer(self, state: AgentState) -> None:
        await state.start()
        await state.next_iteration()
        await state.complete("P(UP) = 0.62 over one trading day")

        assert state.status is AgentStatus.COMPLETED
        assert state.is_terminal
        assert state.stopped_reason == STOP_FINAL_ANSWER
        assert state.final_response == "P(UP) = 0.62 over one trading day"
        assert state.completed_at is not None

    @pytest.mark.asyncio
    async def test_exhausted_budget_is_a_completion_not_a_failure(self) -> None:
        # Exactly how LLMToolLoop ends an over-long run: it returns the content
        # it has with stopped_reason="max_iterations" rather than raising.
        state = AgentState(GOAL, max_iterations=1)
        await state.start()
        await state.next_iteration()
        await state.complete("partial analysis", stopped_reason=STOP_MAX_ITERATIONS)

        assert state.status is AgentStatus.COMPLETED
        assert state.stopped_reason == STOP_MAX_ITERATIONS

    @pytest.mark.asyncio
    async def test_cancel_is_distinct_from_failure(self, state: AgentState) -> None:
        await state.start()
        await state.cancel()
        assert state.status is AgentStatus.CANCELLED
        assert state.stopped_reason == STOP_CANCELLED
        assert state.errors == ()

    @pytest.mark.asyncio
    async def test_a_finished_run_is_immutable(self, state: AgentState) -> None:
        # A state holding both a completion and a later failure describes a run
        # that never happened, and that is not auditable.
        await state.start()
        await state.complete("done")

        for operation in (
            state.complete("again"),
            state.fail("too late"),
            state.cancel(),
            state.add_message(Message.user("more")),
            state.record_observation("more"),
            state.record_error("more"),
            state.next_iteration(),
            state.seed_conversation(),
        ):
            with pytest.raises(AgentError) as excinfo:
                await operation
            assert excinfo.value.code == "AGENT_STATE_ALREADY_FINISHED"

    @pytest.mark.asyncio
    async def test_failed_run_also_refuses_further_mutation(
        self, state: AgentState
    ) -> None:
        await state.start()
        await state.fail("provider unreachable")
        with pytest.raises(AgentError):
            await state.complete("recovered")


# ==============================================================
# Serialization
# ==============================================================


async def _populated_state() -> AgentState:
    state = AgentState(
        GOAL,
        agent="market_analysis",
        max_iterations=4,
        session_id="session-9",
        metadata={"symbol": "RELIANCE"},
    )
    await state.start()
    await state.seed_conversation("You are a market analyst.")
    await state.next_iteration()

    call = ToolCall(
        id="call-1",
        name="get_quote",
        arguments={"symbol": "RELIANCE"},
        raw_arguments='{"symbol": "RELIANCE"}',
    )
    await state.add_message(Message.assistant(tool_calls=(call,)))
    await state.record_tool_call(call)
    await state.record_tool_result(
        ToolExecutionResult(name="get_quote", ok=True, value={"last": 2941.5}),
        call_id="call-1",
    )
    await state.add_message(Message.tool(tool_call_id="call-1", content='{"last": 1}'))
    await state.record_observation("Momentum is positive", source="market_analysis")
    await state.record_error("news feed returned no items")
    await state.complete("P(UP) = 0.62")
    return state


class TestSerialization:
    @pytest.mark.asyncio
    async def test_round_trip_preserves_the_whole_run(self) -> None:
        original = await _populated_state()
        restored = AgentState.from_dict(original.to_dict())

        assert restored.to_dict() == original.to_dict()
        assert restored.state_id == original.state_id
        assert restored.session_id == "session-9"
        assert restored.goal == original.goal
        assert restored.agent == original.agent
        assert restored.status is AgentStatus.COMPLETED
        assert restored.stopped_reason == STOP_FINAL_ANSWER
        assert restored.final_response == "P(UP) = 0.62"
        assert restored.iteration == original.iteration
        assert restored.max_iterations == 4
        assert restored.metadata == {"symbol": "RELIANCE"}
        assert restored.created_at == original.created_at
        assert restored.started_at == original.started_at
        assert restored.completed_at == original.completed_at

    @pytest.mark.asyncio
    async def test_round_trip_preserves_every_transcript_entry(self) -> None:
        original = await _populated_state()
        restored = AgentState.from_dict(original.to_dict())

        assert restored.messages == original.messages
        assert restored.tool_calls == original.tool_calls
        assert restored.tool_results == original.tool_results
        assert restored.observations == original.observations
        assert restored.errors == original.errors
        assert restored.conversation() == original.conversation()

    @pytest.mark.asyncio
    async def test_json_round_trip(self) -> None:
        original = await _populated_state()
        restored = AgentState.from_json(original.to_json())
        assert restored.to_dict() == original.to_dict()

    @pytest.mark.asyncio
    async def test_restored_state_is_independent(self) -> None:
        original = await _populated_state()
        payload = original.to_dict()
        payload["messages"].clear()
        assert len(original.messages) == 4

    def test_missing_goal_is_refused(self) -> None:
        with pytest.raises(AgentError) as excinfo:
            AgentState.from_dict({"agent": "market_analysis"})
        assert excinfo.value.code == "AGENT_STATE_MISSING_FIELD"

    def test_unknown_field_is_refused_not_dropped(self) -> None:
        # Silently ignoring it restores a run quietly missing part of itself.
        with pytest.raises(AgentError) as excinfo:
            AgentState.from_dict({"goal": GOAL, "iterations": 3})
        assert excinfo.value.code == "AGENT_STATE_UNKNOWN_FIELD"

    def test_unknown_status_is_refused(self) -> None:
        with pytest.raises(AgentError) as excinfo:
            AgentState.from_dict({"goal": GOAL, "status": "thinking"})
        assert excinfo.value.code == "AGENT_STATE_INVALID_STATUS"

    def test_malformed_json_is_refused(self) -> None:
        with pytest.raises(AgentError) as excinfo:
            AgentState.from_json("{not json")
        assert excinfo.value.code == "AGENT_STATE_INVALID_JSON"

    def test_non_object_json_is_refused(self) -> None:
        with pytest.raises(AgentError) as excinfo:
            AgentState.from_json("[]")
        assert excinfo.value.code == "AGENT_STATE_INVALID_PAYLOAD"

    @pytest.mark.parametrize(
        ("record", "payload"),
        [
            (Message, {"role": "user", "contents": "typo"}),
            (ToolCallRecord, {"id": "c", "name": "n", "arg": {}}),
            (ToolResultRecord, {"call_id": "c", "name": "n", "ok": True, "x": 1}),
            (Observation, {"text": "t", "sources": "vision"}),
            (ErrorRecord, {"message": "m", "recoverible": True}),
        ],
    )
    def test_records_reject_unknown_fields(self, record, payload) -> None:
        # A misspelled `ok` would turn a failed tool call into a successful one.
        with pytest.raises(AgentError) as excinfo:
            record.from_dict(payload)
        assert excinfo.value.code == "AGENT_STATE_UNKNOWN_FIELD"


# ==============================================================
# Redacted view for logs
# ==============================================================


class TestDescribe:
    @pytest.mark.asyncio
    async def test_describe_carries_counts_and_names_only(self) -> None:
        state = await _populated_state()
        described = state.describe()

        assert described["status"] == "completed"
        assert described["messages"] == 4
        assert described["tool_calls"] == 1
        assert described["tools_used"] == ["get_quote"]
        assert described["tool_failures"] == 0
        assert described["observations"] == 1
        assert described["errors"] == 1
        assert described["has_final_response"] is True

        # Nothing that could leak the conversation or an argument value.
        rendered = json.dumps(described)
        assert GOAL not in rendered
        assert "RELIANCE" not in rendered
        assert "P(UP)" not in rendered

    @pytest.mark.asyncio
    async def test_repr_does_not_leak_the_goal(self) -> None:
        # reprs land in tracebacks, and tracebacks land in logs.
        state = await _populated_state()
        assert GOAL not in repr(state)
        assert state.state_id in repr(state)
