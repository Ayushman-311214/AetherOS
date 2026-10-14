"""
Tests for the agent planner.

The planner's contract is narrow: goal in, one next action out. So the
properties under test are that every branch of its decision table produces the
action the loop expects, that a response the model got wrong comes back as a
correctable rejection rather than an exception, that a provider failure is
described rather than raised, and that none of it touches the registry, the
state, or the tools themselves.

``decide`` is pure, which is why most cases below need no provider at all.
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from aetheros.agents.context import AgentContext, ContextBuilder
from aetheros.agents.planner import (
    ERROR_INVALID_ARGUMENTS,
    ERROR_MALFORMED_CALL,
    ERROR_PROVIDER,
    ERROR_TERMINAL_STATE,
    ERROR_TOOL_DISABLED,
    ERROR_TOO_MANY_CALLS,
    ERROR_UNKNOWN_TOOL,
    TOOL_CALL_CEILING,
    ActionType,
    AgentPlanner,
    PlannedAction,
    PlannerConfig,
    PlanResult,
    RejectedToolCall,
)
from aetheros.agents.state import AgentState
from aetheros.core.errors.agent_error import AgentError
from aetheros.tools.registry import ToolDefinition, ToolRegistry


# ==============================================================
# Tool doubles
# ==============================================================

# Real signatures, because the validator reads them: an invalid-arguments test
# is only meaningful against a function that actually declares its parameters.


def move_mouse(x: int, y: int) -> str:
    """Move the cursor to a screen coordinate."""

    return f"moved to {x},{y}"


def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read a file from disk."""

    return f"read {path} as {encoding}"


def retired_tool(target: str) -> str:
    """A tool that is registered but switched off."""

    return target


# ==============================================================
# Helpers
# ==============================================================


def _state(goal: str = "Analyze RELIANCE", **kwargs: Any) -> AgentState:
    return AgentState(goal, **kwargs)


async def _started(goal: str = "Analyze RELIANCE", **kwargs: Any) -> AgentState:
    """A running, seeded state on its first iteration."""

    state = _state(goal, **kwargs)
    await state.start()
    await state.seed_conversation("Test system prompt.")
    await state.next_iteration()
    return state


def _calls(*calls: tuple[str, Any], content: str = "") -> dict[str, Any]:
    """A provider response requesting the given ``(name, arguments)`` calls.

    ``arguments`` is passed through untouched so a case can supply a dict, a
    JSON string, or deliberate garbage.
    """

    return {
        "content": content,
        "tool_calls": [
            {"id": f"call_{index}", "name": name, "arguments": arguments}
            for index, (name, arguments) in enumerate(calls)
        ],
    }


def _answer(content: str) -> dict[str, Any]:
    return {"content": content, "tool_calls": []}


class _FailingProvider:
    """A provider that raises instead of answering.

    Not a :class:`FakeLLMProvider` subclass: the point is that ``plan`` catches
    whatever the provider raises, so the double only needs the three members the
    planner touches.
    """

    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error or TimeoutError("upstream timed out")
        self.calls = 0

    @property
    def name(self) -> str:
        return "flaky"

    @property
    def model(self) -> str:
        return "flaky-model"

    async def tool_call(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls += 1
        raise self.error

    async def generate(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        self.calls += 1
        raise self.error


# ==============================================================
# Fixtures
# ==============================================================


@pytest.fixture
def tools(registry: ToolRegistry, define: Any) -> ToolRegistry:
    """An isolated registry holding two live tools and one disabled one."""

    registry.register(define(move_mouse, category="desktop"))
    registry.register(define(read_file, category="files"))
    registry.register(define(retired_tool, category="files", enabled=False))

    return registry


@pytest.fixture
def builder(tools: ToolRegistry) -> ContextBuilder:
    """A builder over the isolated registry, never the process-wide one."""

    return ContextBuilder(registry=tools)


@pytest.fixture
def provider(make_provider: type) -> Any:
    """The scripted provider, answering with a plain final response."""

    return make_provider([_answer("Done.")])


@pytest.fixture
def planner(provider: Any, tools: ToolRegistry) -> AgentPlanner:
    return AgentPlanner(provider, registry=tools)


@pytest.fixture
def context(builder: ContextBuilder) -> AgentContext:
    """A context for a fresh state -- enough for every ``decide`` case."""

    return builder.build(_state())


# ==============================================================
# Final response
# ==============================================================


class TestFinalResponse:
    """A response with prose and no tool calls ends the run."""

    def test_content_becomes_a_final_response(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _answer("RELIANCE looks bullish."))

        assert result.type is ActionType.FINAL_RESPONSE
        assert result.is_final
        assert result.action.content == "RELIANCE looks bullish."
        assert result.action.tool_name is None

    def test_final_response_matches_the_specified_shape(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _answer("Done."))

        assert result.action.to_dict() == {
            "type": "final_response",
            "content": "Done.",
        }

    def test_a_final_response_does_not_ask_for_another_iteration(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _answer("Done."))

        assert not result.needs_another_iteration
        assert not result.has_tool_calls
        assert result.tool_calls == ()

    def test_empty_content_and_no_calls_becomes_continue(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        # A provider that answered with nothing at all has not finished; the
        # loop needs a turn it can retry, not an empty final answer.
        result = planner.decide(context, _answer("   "))

        assert result.type is ActionType.CONTINUE
        assert result.needs_another_iteration
        assert result.action.reason

    def test_a_bare_string_response_is_still_a_final_answer(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, "Straight from the model.")

        assert result.type is ActionType.FINAL_RESPONSE
        assert result.action.content == "Straight from the model."

    def test_every_plan_records_the_model_that_produced_it(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        # CLAUDE.md 8: a prediction has to name its model.
        result = planner.decide(context, _answer("Done."))

        assert result.provider == "fake"
        assert result.model == "fake-model"
        assert result.iteration == context.iteration

    @pytest.mark.asyncio
    async def test_plan_returns_the_scripted_final_response(
        self,
        planner: AgentPlanner,
        builder: ContextBuilder,
        provider: Any,
    ) -> None:
        state = await _started()
        result = await planner.plan(state, builder.build(state))

        assert result.type is ActionType.FINAL_RESPONSE
        assert result.action.content == "Done."
        assert provider.tool_call_count == 1

    @pytest.mark.asyncio
    async def test_no_registered_tools_falls_back_to_generate(
        self,
        registry: ToolRegistry,
        make_provider: type,
    ) -> None:
        # OpenAI-compatible endpoints reject an empty `tools` array, so an empty
        # registry must not produce a tool_call request.
        provider = make_provider([], generate_result="Nothing to use.")
        planner = AgentPlanner(provider, registry=registry)
        builder = ContextBuilder(registry=registry)

        state = await _started()
        result = await planner.plan(state, builder.build(state))

        assert provider.tool_call_count == 0
        assert provider.generate_count == 1
        assert result.type is ActionType.FINAL_RESPONSE
        assert result.action.content == "Nothing to use."


# ==============================================================
# Single tool call
# ==============================================================


class TestSingleToolCall:
    """One well-formed call for a known tool is planned, not executed."""

    def test_a_known_call_becomes_a_tool_call_action(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(("move_mouse", {"x": 500, "y": 300})),
        )

        assert result.type is ActionType.TOOL_CALL
        assert result.action.tool_name == "move_mouse"
        assert result.action.arguments == {"x": 500, "y": 300}
        assert result.action.call_id == "call_0"
        assert result.rejections == ()

    def test_tool_call_matches_the_specified_shape(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(("move_mouse", {"x": 500, "y": 300})),
        )

        assert result.action.to_dict() == {
            "type": "tool_call",
            "tool_name": "move_mouse",
            "arguments": {"x": 500, "y": 300},
            "call_id": "call_0",
        }

    def test_a_tool_call_asks_for_another_iteration(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("read_file", {"path": "/tmp/x"})))

        assert result.needs_another_iteration
        assert result.has_tool_calls
        assert len(result.tool_calls) == 1
        assert not result.is_final

    def test_json_string_arguments_are_parsed(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        # Most providers send arguments as a JSON string, not a dict.
        result = planner.decide(
            context,
            _calls(("move_mouse", '{"x": 12, "y": 34}')),
        )

        assert result.type is ActionType.TOOL_CALL
        assert result.action.arguments == {"x": 12, "y": 34}

    def test_planned_arguments_are_insulated_from_the_response(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        arguments = {"x": 1, "y": 2}
        response = _calls(("move_mouse", arguments))

        result = planner.decide(context, response)
        arguments["x"] = 999

        assert result.action.arguments == {"x": 1, "y": 2}

    def test_the_planner_does_not_execute_the_tool(
        self,
        tools: ToolRegistry,
        provider: Any,
        builder: ContextBuilder,
    ) -> None:
        # The strongest form of "do not execute tools inside Planner": register a
        # tool that records every invocation, plan a call to it, and assert the
        # recorder stayed empty.
        invocations: list[tuple[int, int]] = []

        def recording_mouse(x: int, y: int) -> str:
            """Record a move instead of performing one."""

            invocations.append((x, y))
            return "moved"

        tools.register(
            ToolDefinition(
                name="recording_mouse",
                description="Records instead of moving.",
                function=recording_mouse,
                category="desktop",
            )
        )

        planner = AgentPlanner(provider, registry=tools)
        result = planner.decide(
            builder.build(_state()),
            _calls(("recording_mouse", {"x": 5, "y": 6})),
        )

        assert result.type is ActionType.TOOL_CALL
        assert invocations == []


# ==============================================================
# Multiple tool calls
# ==============================================================


class TestMultipleToolCalls:
    """A provider that supports parallel calls gets one action per call."""

    def test_two_calls_become_two_actions_in_order(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(
                ("move_mouse", {"x": 1, "y": 2}),
                ("read_file", {"path": "/tmp/x"}),
            ),
        )

        assert len(result.actions) == 2
        assert [action.tool_name for action in result.actions] == [
            "move_mouse",
            "read_file",
        ]
        assert [action.call_id for action in result.actions] == ["call_0", "call_1"]
        assert result.requested_calls == 2
        assert result.rejections == ()

    def test_the_first_action_is_the_one_reported_as_the_plan(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(("move_mouse", {"x": 1, "y": 2}), ("read_file", {"path": "/x"})),
        )

        assert result.action is result.actions[0]
        assert result.type is ActionType.TOOL_CALL
        assert len(result.tool_calls) == 2

    def test_parallelism_off_keeps_the_first_call_and_rejects_the_rest(
        self,
        provider: Any,
        tools: ToolRegistry,
        context: AgentContext,
    ) -> None:
        planner = AgentPlanner(
            provider,
            registry=tools,
            config=PlannerConfig(allow_parallel_tool_calls=False),
        )

        result = planner.decide(
            context,
            _calls(("move_mouse", {"x": 1, "y": 2}), ("read_file", {"path": "/x"})),
        )

        assert len(result.actions) == 1
        assert result.action.tool_name == "move_mouse"
        assert len(result.rejections) == 1
        assert result.rejections[0].error_type == ERROR_TOO_MANY_CALLS
        assert result.rejections[0].tool_name == "read_file"

    def test_calls_beyond_the_limit_are_rejected_not_dropped(
        self,
        provider: Any,
        tools: ToolRegistry,
        context: AgentContext,
    ) -> None:
        # Silently discarding a call would leave the model waiting for a result
        # that never arrives.
        planner = AgentPlanner(
            provider,
            registry=tools,
            config=PlannerConfig(max_tool_calls=2),
        )

        result = planner.decide(
            context,
            _calls(
                ("move_mouse", {"x": 1, "y": 1}),
                ("move_mouse", {"x": 2, "y": 2}),
                ("move_mouse", {"x": 3, "y": 3}),
            ),
        )

        assert len(result.actions) == 2
        assert len(result.rejections) == 1
        assert result.requested_calls == 3
        assert result.rejections[0].call_id == "call_2"

    def test_a_partly_valid_batch_keeps_the_valid_calls(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(
                ("move_mouse", {"x": 1, "y": 2}),
                ("teleport_mouse", {"x": 9}),
            ),
        )

        assert len(result.actions) == 1
        assert result.action.tool_name == "move_mouse"
        assert result.has_rejections
        assert result.rejections[0].error_type == ERROR_UNKNOWN_TOOL


# ==============================================================
# Malformed response
# ==============================================================


class TestMalformedResponse:
    """Anything the parser cannot turn into a call comes back as a rejection."""

    def test_unparseable_arguments_are_rejected(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("move_mouse", "{not json at all")))

        assert result.type is ActionType.CONTINUE
        assert len(result.rejections) == 1
        assert result.rejections[0].error_type == ERROR_MALFORMED_CALL
        assert result.rejections[0].tool_name == "move_mouse"

    def test_a_wholly_rejected_batch_continues_rather_than_fails(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        # The model asked for work and can be told what was wrong with the
        # request, so this is correctable, not terminal.
        result = planner.decide(context, _calls(("move_mouse", "[]")))

        assert result.type is ActionType.CONTINUE
        assert not result.is_failure
        assert result.needs_another_iteration
        assert "rejected" in result.action.reason

    def test_a_call_with_no_name_is_not_addressable(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        # Without a name the correction cannot be delivered as a `tool` message.
        result = planner.decide(
            context,
            {"content": "", "tool_calls": [{"id": "call_0", "arguments": {}}]},
        )

        assert result.type is ActionType.CONTINUE
        assert result.rejections[0].tool_name is None
        assert not result.rejections[0].is_addressable

    def test_a_named_rejection_is_addressable(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("move_mouse", "nonsense")))

        assert result.rejections[0].is_addressable

    def test_garbage_in_place_of_tool_calls_is_ignored(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            {"content": "Thinking out loud.", "tool_calls": "not-a-list"},
        )

        assert result.type is ActionType.FINAL_RESPONSE
        assert result.rejections == ()

    def test_malformed_rejections_are_reported_before_validated_ones(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(("teleport_mouse", {"x": 1}), ("move_mouse", "{{{")),
        )

        assert [r.error_type for r in result.rejections] == [
            ERROR_MALFORMED_CALL,
            ERROR_UNKNOWN_TOOL,
        ]

    def test_content_alongside_rejected_calls_is_preserved(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(("move_mouse", "{{{"), content="Let me move the cursor."),
        )

        assert result.content == "Let me move the cursor."
        assert result.type is ActionType.CONTINUE


# ==============================================================
# Invalid tool name
# ==============================================================


class TestInvalidToolName:
    """An invented tool name is the commonest model error; it must not raise."""

    def test_an_unknown_tool_is_rejected(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("teleport_mouse", {"x": 1})))

        assert result.type is ActionType.CONTINUE
        assert result.rejections[0].error_type == ERROR_UNKNOWN_TOOL
        assert result.rejections[0].tool_name == "teleport_mouse"

    def test_the_rejection_lists_what_the_model_could_have_used(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("teleport_mouse", {"x": 1})))

        reason = result.rejections[0].reason

        assert "teleport_mouse" in reason
        assert "move_mouse" in reason
        assert "read_file" in reason
        # Disabled tools are not on offer, so naming one would be misleading.
        assert "retired_tool" not in reason

    def test_an_unknown_tool_does_not_raise(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        # ToolRegistry.get raises KeyError, so the lookup has to be guarded.
        assert planner.decide(context, _calls(("nope", {}))).is_failure is False

    def test_a_disabled_tool_is_rejected_separately(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("retired_tool", {"target": "x"})))

        assert result.rejections[0].error_type == ERROR_TOOL_DISABLED
        assert "disabled" in result.rejections[0].reason

    def test_name_checking_can_be_switched_off(
        self,
        provider: Any,
        tools: ToolRegistry,
        context: AgentContext,
    ) -> None:
        # With checking off there is nothing to validate against, so the call
        # goes downstream for the executor to refuse.
        planner = AgentPlanner(
            provider,
            registry=tools,
            config=PlannerConfig(require_known_tools=False),
        )

        result = planner.decide(context, _calls(("teleport_mouse", {"x": 1})))

        assert result.type is ActionType.TOOL_CALL
        assert result.action.tool_name == "teleport_mouse"
        assert result.rejections == ()

    def test_an_empty_registry_says_so(
        self,
        provider: Any,
        registry: ToolRegistry,
    ) -> None:
        planner = AgentPlanner(provider, registry=registry)
        context = ContextBuilder(registry=registry).build(_state())

        result = planner.decide(context, _calls(("move_mouse", {"x": 1, "y": 2})))

        assert "none" in result.rejections[0].reason


# ==============================================================
# Invalid arguments
# ==============================================================


class TestInvalidArguments:
    """Arguments are checked against the real signature before planning."""

    def test_a_missing_required_argument_is_rejected(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("move_mouse", {"x": 500})))

        assert result.type is ActionType.CONTINUE
        assert result.rejections[0].error_type == ERROR_INVALID_ARGUMENTS
        assert "y" in result.rejections[0].reason

    def test_a_wrongly_typed_argument_is_rejected(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(("move_mouse", {"x": "left", "y": 300})),
        )

        assert result.rejections[0].error_type == ERROR_INVALID_ARGUMENTS
        assert "int" in result.rejections[0].reason

    def test_an_invented_argument_is_rejected(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(("move_mouse", {"x": 1, "y": 2, "speed": "fast"})),
        )

        assert result.rejections[0].error_type == ERROR_INVALID_ARGUMENTS
        assert "speed" in result.rejections[0].reason

    def test_an_omitted_optional_argument_is_fine(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("read_file", {"path": "/tmp/x"})))

        assert result.type is ActionType.TOOL_CALL
        assert result.rejections == ()

    def test_argument_validation_can_be_switched_off(
        self,
        provider: Any,
        tools: ToolRegistry,
        context: AgentContext,
    ) -> None:
        planner = AgentPlanner(
            provider,
            registry=tools,
            config=PlannerConfig(validate_arguments=False),
        )

        result = planner.decide(context, _calls(("move_mouse", {"x": 500})))

        assert result.type is ActionType.TOOL_CALL
        assert result.rejections == ()

    def test_the_rejection_names_the_argument_but_not_its_value(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        # The reason reaches the log; a value like a pasted password must not.
        result = planner.decide(
            context,
            _calls(("move_mouse", {"x": 1, "y": 2, "secret": "hunter2"})),
        )

        rejection = result.rejections[0]

        assert "secret" in rejection.reason
        assert "hunter2" not in rejection.reason
        assert "hunter2" not in str(rejection.describe())


# ==============================================================
# Provider failure
# ==============================================================


class TestProviderFailure:
    """A provider that cannot answer becomes a described failure, not a raise."""

    @pytest.mark.asyncio
    async def test_a_provider_exception_becomes_a_fail_action(
        self,
        tools: ToolRegistry,
        builder: ContextBuilder,
    ) -> None:
        planner = AgentPlanner(_FailingProvider(), registry=tools)
        state = await _started()

        result = await planner.plan(state, builder.build(state))

        assert result.type is ActionType.FAIL
        assert result.is_failure
        assert result.action.error_type == ERROR_PROVIDER
        assert "flaky" in result.action.reason

    @pytest.mark.asyncio
    async def test_the_cause_is_kept_as_an_error_record(
        self,
        tools: ToolRegistry,
        builder: ContextBuilder,
    ) -> None:
        # Shaped so it can go straight into AgentState.record_error.
        planner = AgentPlanner(
            _FailingProvider(TimeoutError("upstream timed out")),
            registry=tools,
        )
        state = await _started()
        context = builder.build(state)

        result = await planner.plan(state, context)

        assert result.error is not None
        assert result.error.error_type == "TimeoutError"
        assert result.error.message == "upstream timed out"
        assert result.error.iteration == context.iteration
        assert result.error.recoverable is True

    @pytest.mark.asyncio
    async def test_a_failed_plan_is_recorded_by_the_state_unchanged(
        self,
        tools: ToolRegistry,
        builder: ContextBuilder,
    ) -> None:
        planner = AgentPlanner(_FailingProvider(), registry=tools)
        state = await _started()

        result = await planner.plan(state, builder.build(state))
        assert result.error is not None

        # Every field record_error asks for is already on the record.
        recorded = await state.record_error(
            result.error.message,
            error_type=result.error.error_type,
            iteration=result.error.iteration,
            recoverable=result.error.recoverable,
        )

        # Not compared whole: record_error stamps its own timestamp.
        assert recorded.message == result.error.message
        assert recorded.error_type == "TimeoutError"
        assert recorded.iteration == result.error.iteration
        assert recorded.recoverable is True
        assert len(state.errors) == 1
        assert not state.is_terminal

    @pytest.mark.asyncio
    async def test_the_failure_does_not_ask_for_another_iteration(
        self,
        tools: ToolRegistry,
        builder: ContextBuilder,
    ) -> None:
        planner = AgentPlanner(_FailingProvider(), registry=tools)
        state = await _started()

        result = await planner.plan(state, builder.build(state))

        assert not result.needs_another_iteration
        assert not result.has_tool_calls

    @pytest.mark.asyncio
    async def test_cancellation_is_not_treated_as_a_provider_failure(
        self,
        tools: ToolRegistry,
        builder: ContextBuilder,
    ) -> None:
        # The run is being torn down; swallowing it would hide that from the
        # task that asked for the cancellation.
        planner = AgentPlanner(
            _FailingProvider(asyncio.CancelledError()),
            registry=tools,
        )
        state = await _started()

        with pytest.raises(asyncio.CancelledError):
            await planner.plan(state, builder.build(state))

    @pytest.mark.asyncio
    async def test_an_empty_registry_failure_comes_from_generate(
        self,
        registry: ToolRegistry,
    ) -> None:
        provider = _FailingProvider(ConnectionError("no route to host"))
        planner = AgentPlanner(provider, registry=registry)
        state = await _started()

        context = ContextBuilder(registry=registry).build(state)

        result = await planner.plan(state, context)

        assert provider.calls == 1
        assert result.type is ActionType.FAIL
        assert result.error is not None
        assert result.error.error_type == "ConnectionError"


# ==============================================================
# Terminal state
# ==============================================================


class TestTerminalState:
    """A finished run has no next action, and costs no tokens to say so."""

    @pytest.mark.asyncio
    async def test_a_completed_run_is_refused(
        self,
        planner: AgentPlanner,
        builder: ContextBuilder,
        provider: Any,
    ) -> None:
        state = await _started()
        await state.complete("Already answered.")

        result = await planner.plan(state, builder.build(state))

        assert result.type is ActionType.FAIL
        assert result.action.error_type == ERROR_TERMINAL_STATE
        assert provider.tool_call_count == 0
        assert provider.generate_count == 0

    @pytest.mark.asyncio
    async def test_a_failed_run_is_refused_too(
        self,
        planner: AgentPlanner,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await state.fail("Data provider unreachable.")

        result = await planner.plan(state, builder.build(state))

        assert result.type is ActionType.FAIL
        assert "failed" in result.action.reason

    @pytest.mark.asyncio
    async def test_the_last_allowed_iteration_is_still_planned(
        self,
        planner: AgentPlanner,
        builder: ContextBuilder,
    ) -> None:
        # has_iterations_left is False *during* the final turn, because
        # next_iteration refuses to overrun. Guarding on it would refuse the
        # final iteration of every run.
        state = _state(max_iterations=1)
        await state.start()
        await state.seed_conversation("Test system prompt.")
        await state.next_iteration()

        assert not state.has_iterations_left

        result = await planner.plan(state, builder.build(state))

        assert result.type is ActionType.FINAL_RESPONSE


# ==============================================================
# Determinism and isolation
# ==============================================================


class TestDeterminism:
    """Everything around the provider response is deterministic."""

    def test_the_same_response_plans_the_same_action(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        response = _calls(("move_mouse", {"x": 500, "y": 300}))

        first = planner.decide(context, response)
        second = planner.decide(context, response)

        assert first.actions == second.actions
        assert first.to_dict() == second.to_dict()

    def test_two_planners_over_one_registry_agree(
        self,
        provider: Any,
        tools: ToolRegistry,
        context: AgentContext,
    ) -> None:
        response = _calls(("move_mouse", {"x": 1, "y": 2}), ("nope", {}))

        left = AgentPlanner(provider, registry=tools).decide(context, response)
        right = AgentPlanner(provider, registry=tools).decide(context, response)

        assert left.actions == right.actions
        assert left.describe() == right.describe()

    @pytest.mark.asyncio
    async def test_planning_does_not_mutate_the_state(
        self,
        planner: AgentPlanner,
        builder: ContextBuilder,
    ) -> None:
        # Recording the decision is the loop's job, not the planner's.
        state = await _started()
        before = state.to_dict()

        await planner.plan(state, builder.build(state))

        assert state.to_dict() == before

    @pytest.mark.asyncio
    async def test_planning_does_not_mutate_the_registry(
        self,
        planner: AgentPlanner,
        builder: ContextBuilder,
        tools: ToolRegistry,
    ) -> None:
        before: list[ToolDefinition] = list(tools.enabled_tools())
        state = await _started()

        await planner.plan(state, builder.build(state))
        planner.decide(builder.build(state), _calls(("nope", {}), ("move_mouse", "{{")))

        assert list(tools.enabled_tools()) == before
        assert tools.names() == ["move_mouse", "read_file", "retired_tool"]

    @pytest.mark.asyncio
    async def test_the_provider_receives_the_context_payload_unchanged(
        self,
        planner: AgentPlanner,
        builder: ContextBuilder,
        provider: Any,
    ) -> None:
        state = await _started()
        context = builder.build(state)

        await planner.plan(state, context)

        assert provider.received_messages[-1] == context.messages()
        assert provider.received_tools[-1] == context.tool_schemas()

    @pytest.mark.asyncio
    async def test_generation_settings_reach_the_provider(
        self,
        tools: ToolRegistry,
        builder: ContextBuilder,
        make_provider: type,
    ) -> None:
        seen: dict[str, Any] = {}

        class RecordingProvider(make_provider):  # type: ignore[misc, valid-type]
            async def tool_call(
                self,
                messages: list[dict[str, Any]],
                tools: list[dict[str, Any]],
                **kwargs: Any,
            ) -> dict[str, Any]:
                seen.update(kwargs)
                return await super().tool_call(messages, tools)

        planner = AgentPlanner(
            RecordingProvider([_answer("Done.")]),
            registry=tools,
        )
        state = await _started()

        await planner.plan(state, builder.build(state), temperature=0.0)

        assert seen == {"temperature": 0.0}


# ==============================================================
# Log safety
# ==============================================================


class TestLogSafety:
    """Argument names may be logged; argument values may not."""

    def test_describe_withholds_argument_values(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(
            context,
            _calls(("read_file", {"path": "/home/ayush/.ssh/id_rsa"})),
        )

        rendered = str(result.describe())

        assert "path" in rendered
        assert "id_rsa" not in rendered

    def test_repr_withholds_argument_values(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _calls(("read_file", {"path": "hunter2"})))

        assert "hunter2" not in repr(result)
        assert "hunter2" not in repr(result.action)

    def test_describe_reports_content_as_a_length(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        result = planner.decide(context, _answer("A long private answer."))

        described = result.describe()

        assert described["content_chars"] == len("A long private answer.")
        assert "A long private answer." not in str(described)

    def test_to_dict_is_faithful_where_describe_is_safe(
        self,
        planner: AgentPlanner,
        context: AgentContext,
    ) -> None:
        # The two views differ on purpose: to_dict is for persistence.
        result = planner.decide(context, _calls(("read_file", {"path": "/tmp/x"})))

        assert result.to_dict()["actions"][0]["arguments"] == {"path": "/tmp/x"}
        assert "arguments" not in result.describe()["actions"][0]


# ==============================================================
# Action and result invariants
# ==============================================================


class TestActionInvariants:
    """An action that cannot be acted on must not be constructible."""

    def test_a_tool_call_without_a_tool_name_is_refused(self) -> None:
        with pytest.raises(AgentError) as excinfo:
            PlannedAction(type=ActionType.TOOL_CALL)

        assert excinfo.value.code == "AGENT_PLANNER_ACTION_INVALID"

    def test_a_final_response_may_not_name_a_tool(self) -> None:
        with pytest.raises(AgentError):
            PlannedAction(type=ActionType.FINAL_RESPONSE, tool_name="move_mouse")

    @pytest.mark.parametrize("kind", [ActionType.CONTINUE, ActionType.FAIL])
    def test_continue_and_fail_must_explain_themselves(
        self,
        kind: ActionType,
    ) -> None:
        # A fail nobody can read the cause of is worse than an exception.
        with pytest.raises(AgentError):
            PlannedAction(type=kind)

    def test_non_dict_arguments_are_refused(self) -> None:
        with pytest.raises(AgentError):
            PlannedAction(
                type=ActionType.TOOL_CALL,
                tool_name="move_mouse",
                arguments=[1, 2],  # type: ignore[arg-type]
            )

    def test_an_action_cannot_be_edited_after_it_is_decided(self) -> None:
        action = PlannedAction.final_response("Done.")

        with pytest.raises(FrozenInstanceError):
            action.content = "Something else"  # type: ignore[misc]

    def test_a_plan_must_carry_at_least_one_action(self) -> None:
        # This is what makes PlanResult.action safe to read unconditionally.
        with pytest.raises(AgentError) as excinfo:
            PlanResult(actions=())

        assert excinfo.value.code == "AGENT_PLANNER_EMPTY_PLAN"

    def test_argument_names_are_sorted_and_valueless(self) -> None:
        action = PlannedAction.tool_call("move_mouse", {"y": 2, "x": 1})

        assert action.argument_names == ("x", "y")

    def test_the_constructors_agree_with_the_predicates(self) -> None:
        assert PlannedAction.final_response("Done.").is_final
        assert PlannedAction.tool_call("move_mouse", {"x": 1}).is_tool_call
        assert PlannedAction.continue_("More work to do.").is_continue
        assert PlannedAction.fail("Provider down.").is_failure

    def test_tool_call_arguments_are_copied_at_construction(self) -> None:
        arguments = {"target": {"x": 1}}
        action = PlannedAction.tool_call("move_mouse", arguments)

        arguments["target"]["x"] = 999

        assert action.arguments == {"target": {"x": 1}}

    def test_a_rejection_describes_itself_without_its_payload(self) -> None:
        rejection = RejectedToolCall(
            tool_name="read_file",
            reason="Missing required argument 'path'.",
            error_type=ERROR_INVALID_ARGUMENTS,
            call_id="call_0",
            argument_names=("token",),
            raw_arguments='{"token": "hunter2"}',
        )

        assert rejection.is_addressable
        assert "hunter2" not in str(rejection.describe())
        assert "hunter2" not in repr(rejection)
        assert rejection.to_dict()["raw_arguments"] == '{"token": "hunter2"}'

    def test_single_wraps_one_action_with_provenance(self) -> None:
        result = PlanResult.single(
            PlannedAction.final_response("Done."),
            provider="fake",
            model="fake-model",
            iteration=3,
        )

        assert result.actions == (PlannedAction.final_response("Done."),)
        assert result.iteration == 3
        assert result.model == "fake-model"


# ==============================================================
# Configuration
# ==============================================================


class TestPlannerConfig:
    """The one bounded number is clamped rather than trusted."""

    def test_defaults_allow_parallel_calls(self) -> None:
        config = PlannerConfig()

        assert config.allow_parallel_tool_calls
        assert config.effective_max_tool_calls == config.max_tool_calls

    def test_parallelism_off_pins_the_limit_to_one(self) -> None:
        config = PlannerConfig(allow_parallel_tool_calls=False)

        assert config.effective_max_tool_calls == 1

    @pytest.mark.parametrize(
        ("given", "expected"),
        [(0, 1), (-5, 1), (TOOL_CALL_CEILING + 100, TOOL_CALL_CEILING)],
    )
    def test_the_limit_is_clamped(self, given: int, expected: int) -> None:
        assert PlannerConfig(max_tool_calls=given).max_tool_calls == expected

    def test_a_non_numeric_limit_is_refused(self) -> None:
        with pytest.raises(AgentError) as excinfo:
            PlannerConfig(max_tool_calls="eight")  # type: ignore[arg-type]

        assert excinfo.value.code == "AGENT_PLANNER_INVALID_LIMIT"

    def test_the_planner_exposes_what_it_was_given(
        self,
        provider: Any,
        tools: ToolRegistry,
    ) -> None:
        config = PlannerConfig(max_tool_calls=3)
        planner = AgentPlanner(provider, registry=tools, config=config)

        assert planner.provider is provider
        assert planner.config is config
        assert config.to_dict()["max_tool_calls"] == 3
