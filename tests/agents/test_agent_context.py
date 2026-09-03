"""
Tests for the agent context layer.

The properties under test are the ones the layer promises: that the payload is
deterministic, that it is bounded no matter how long the run got, that it stays
in the shape the existing provider layer accepts, and that it offers the model
exactly the enabled tools from the one registry it was given.
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from aetheros.agents.context import (
    CHARS_CEILING,
    HISTORY_CEILING,
    AgentContext,
    ContextBuilder,
    ContextConfig,
    IterationInfo,
    context_builder,
    truncate,
)
from aetheros.agents.state import AgentState, Message
from aetheros.core.errors.agent_error import AgentError
from aetheros.llm.tool_calls import ToolCall
from aetheros.tools.executor import ToolExecutionResult
from aetheros.tools.registry import ToolRegistry, tool_registry
from aetheros.tools.schema import schema_generator


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


def _call(name: str = "read_file", *, id: str = "call_0", **arguments: Any) -> ToolCall:
    return ToolCall(id=id, name=name, arguments=arguments, raw_arguments="{}")


def _result(name: str = "read_file", *, ok: bool = True, **kwargs: Any):
    return ToolExecutionResult(name=name, ok=ok, **kwargs)


async def _with_tool_round(
    state: AgentState,
    *,
    name: str = "read_file",
    call_id: str = "call_0",
    content: str = '{"ok": true, "value": "data"}',
) -> None:
    """Record one full call/result round, transcript and records together."""

    call = _call(name, id=call_id, path="/tmp/x")
    await state.record_tool_call(call)
    await state.add_message(Message.assistant(tool_calls=(call,)))
    await state.record_tool_result(
        _result(name, value="data"),
        call_id=call_id,
        content=content,
    )
    await state.add_message(Message.tool(tool_call_id=call_id, content=content))


@pytest.fixture
def builder(registry: ToolRegistry) -> ContextBuilder:
    """A builder over an isolated registry, never the process-wide one."""

    return ContextBuilder(registry=registry)


# ==============================================================
# Empty context
# ==============================================================


class TestEmptyContext:
    """A state that has not run yet still produces a usable payload."""

    def test_fresh_state_has_no_history(self, builder: ContextBuilder) -> None:
        context = builder.build(_state())

        assert context.history == ()
        assert context.recent_tool_calls == ()
        assert context.recent_tool_results == ()
        assert context.observations == ()

    def test_fresh_state_still_carries_the_goal(self, builder: ContextBuilder) -> None:
        context = builder.build(_state("Analyze RELIANCE"))

        assert context.goal == "Analyze RELIANCE"
        assert "Analyze RELIANCE" in context.system_instructions

    def test_messages_always_open_with_one_system_turn(
        self,
        builder: ContextBuilder,
    ) -> None:
        messages = builder.build(_state()).messages()

        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert sum(1 for m in messages if m["role"] == "system") == 1

    def test_iteration_zero_is_reported_as_zero(
        self,
        builder: ContextBuilder,
    ) -> None:
        context = builder.build(_state())

        assert context.iteration == 0
        assert context.max_iterations == 8
        assert context.iterations_remaining == 8
        assert not context.is_final_iteration

    def test_no_tools_registered_means_no_schemas(
        self,
        builder: ContextBuilder,
    ) -> None:
        context = builder.build(_state())

        assert context.tools == ()
        assert not context.has_tools
        # An empty tools list is what LLMEngine.tool_call falls back on, so the
        # caller does not need a special case for a registry with nothing in it.
        assert context.tool_schemas() == []

    def test_empty_context_is_not_reported_as_trimmed(
        self,
        builder: ContextBuilder,
    ) -> None:
        context = builder.build(_state())

        assert not context.is_trimmed
        assert context.dropped_messages == 0
        assert context.dropped_orphans == 0


# ==============================================================
# Normal conversation
# ==============================================================


class TestNormalConversation:
    """A plain back-and-forth reaches the provider unchanged."""

    @pytest.mark.asyncio
    async def test_history_replays_the_transcript_in_order(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await state.add_message(Message.assistant("Working on it."))
        await state.add_message(Message.user("Any update?"))

        context = builder.build(state)

        assert [m["role"] for m in context.history] == [
            "user",
            "assistant",
            "user",
        ]
        assert context.history[1]["content"] == "Working on it."

    @pytest.mark.asyncio
    async def test_seeded_system_turn_is_not_replayed_twice(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()

        context = builder.build(state)
        messages = context.messages()

        # AgentState.seed_conversation recorded one; the context owns the system
        # message, so the transcript's copy is superseded rather than duplicated.
        assert context.superseded_system_messages == 1
        assert [m["role"] for m in messages].count("system") == 1

    @pytest.mark.asyncio
    async def test_configured_prompt_wins_over_the_seeded_one(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started()
        builder = ContextBuilder(
            ContextConfig(system_prompt="You are a quant analyst."),
            registry=registry,
        )

        instructions = builder.build(state).system_instructions

        assert instructions.startswith("You are a quant analyst.")
        assert "Test system prompt." not in instructions

    @pytest.mark.asyncio
    async def test_goal_survives_even_when_its_turn_is_trimmed_away(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started("Analyze RELIANCE")
        for index in range(10):
            await state.add_message(Message.assistant(f"turn {index}"))

        builder = ContextBuilder(
            ContextConfig(max_history_messages=3),
            registry=registry,
        )
        context = builder.build(state)

        assert all(m["role"] != "user" for m in context.history)
        assert "Analyze RELIANCE" in context.system_instructions

    @pytest.mark.asyncio
    async def test_build_does_not_mutate_the_state(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        before = state.to_dict()

        builder.build(state)

        assert state.to_dict() == before

    @pytest.mark.asyncio
    async def test_returned_payload_is_a_copy(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        context = builder.build(state)

        messages = context.messages()
        messages[0]["content"] = "tampered"
        messages.append({"role": "user", "content": "injected"})

        assert context.messages()[0]["content"] != "tampered"
        assert len(context.messages()) == len(messages) - 1


# ==============================================================
# Tool-call context
# ==============================================================


class TestToolCallContext:
    """Tool rounds keep the shape the provider layer already accepts."""

    @pytest.mark.asyncio
    async def test_recent_calls_and_results_are_exposed(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await _with_tool_round(state)

        context = builder.build(state)

        assert [c.name for c in context.recent_tool_calls] == ["read_file"]
        assert [r.name for r in context.recent_tool_results] == ["read_file"]
        assert context.recent_tool_results[0].ok

    @pytest.mark.asyncio
    async def test_assistant_turn_replays_tool_calls_in_wire_shape(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await _with_tool_round(state)

        assistant = next(
            m for m in builder.build(state).history if m["role"] == "assistant"
        )

        # The shape LLMToolLoop builds by hand and the provider validates.
        assert assistant["content"] is None
        assert assistant["tool_calls"][0]["type"] == "function"
        assert assistant["tool_calls"][0]["id"] == "call_0"
        assert assistant["tool_calls"][0]["function"]["name"] == "read_file"

    @pytest.mark.asyncio
    async def test_tool_turn_answers_the_call_it_belongs_to(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await _with_tool_round(state)

        history = builder.build(state).history
        assistant_index = next(
            i for i, m in enumerate(history) if m["role"] == "assistant"
        )
        tool_message = history[assistant_index + 1]

        assert tool_message["role"] == "tool"
        assert tool_message["tool_call_id"] == "call_0"

    @pytest.mark.asyncio
    async def test_orphaned_tool_turn_is_dropped_not_sent(
        self,
        registry: ToolRegistry,
    ) -> None:
        """A tool message whose assistant turn was trimmed fails the request.

        The provider rejects the whole call, so the context drops the orphan
        rather than shipping a payload it knows to be invalid.
        """

        state = await _started()
        await _with_tool_round(state)

        builder = ContextBuilder(
            ContextConfig(max_history_messages=1),
            registry=registry,
        )
        context = builder.build(state)

        assert context.dropped_orphans == 1
        assert all(m["role"] != "tool" for m in context.history)

    @pytest.mark.asyncio
    async def test_digest_lists_argument_names_but_never_values(
        self,
        builder: ContextBuilder,
    ) -> None:
        """The digest must stay safe to log; the history carries the values."""

        state = await _started()
        await state.record_tool_call(_call("type_text", text="hunter2"))

        instructions = builder.build(state).system_instructions

        assert "type_text(text)" in instructions
        assert "hunter2" not in instructions

    @pytest.mark.asyncio
    async def test_failed_result_says_why_in_the_digest(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await state.record_tool_result(
            _result("read_file", ok=False, error="No such file", error_type="OSError"),
            call_id="call_0",
        )

        instructions = builder.build(state).system_instructions

        assert "failed (OSError): No such file" in instructions


# ==============================================================
# Observation context
# ==============================================================


class TestObservationContext:
    """Observations are not transcript turns, so the context has to carry them."""

    @pytest.mark.asyncio
    async def test_observations_reach_the_system_block(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await state.record_observation("Price is above the 200-day average.")

        context = builder.build(state)

        assert len(context.observations) == 1
        assert "Price is above the 200-day average." in context.system_instructions

    @pytest.mark.asyncio
    async def test_observations_are_tagged_with_their_iteration(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await state.record_observation("first")
        await state.next_iteration()
        await state.record_observation("second")

        instructions = builder.build(state).system_instructions

        assert "[iteration 1] first" in instructions
        assert "[iteration 2] second" in instructions

    @pytest.mark.asyncio
    async def test_observations_stay_out_of_the_transcript(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        await state.record_observation("Volume is thin.")

        context = builder.build(state)

        assert all(
            "Volume is thin." not in str(m.get("content") or "")
            for m in context.history
        )

    @pytest.mark.asyncio
    async def test_observations_can_be_switched_off(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started()
        await state.record_observation("Volume is thin.")

        builder = ContextBuilder(
            ContextConfig(include_observations=False),
            registry=registry,
        )
        context = builder.build(state)

        assert context.observations == ()
        assert "Volume is thin." not in context.system_instructions

    @pytest.mark.asyncio
    async def test_long_observation_is_truncated_with_a_marker(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started()
        await state.record_observation("x" * 900)

        builder = ContextBuilder(
            ContextConfig(observation_max_chars=100),
            registry=registry,
        )
        instructions = builder.build(state).system_instructions

        assert "truncated 800 chars" in instructions
        assert "x" * 200 not in instructions


# ==============================================================
# Multiple iterations
# ==============================================================


class TestMultipleIterations:
    """The context tracks where the run is in its budget."""

    @pytest.mark.asyncio
    async def test_iteration_advances_with_the_state(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()

        assert builder.build(state).iteration == 1

        await state.next_iteration()
        await state.next_iteration()

        context = builder.build(state)
        assert context.iteration == 3
        assert context.iterations_remaining == 5

    @pytest.mark.asyncio
    async def test_final_iteration_is_announced_to_the_model(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = _state(max_iterations=2)
        await state.start()
        await state.seed_conversation()
        await state.next_iteration()
        await state.next_iteration()

        context = builder.build(state)

        assert context.is_final_iteration
        assert context.iterations_remaining == 0
        assert "last iteration" in context.system_instructions

    @pytest.mark.asyncio
    async def test_earlier_iterations_do_not_announce_the_end(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = _state(max_iterations=2)
        await state.start()
        await state.next_iteration()

        assert "last iteration" not in builder.build(state).system_instructions

    @pytest.mark.asyncio
    async def test_history_grows_across_iterations(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started()
        sizes: list[int] = []

        for index in range(3):
            await _with_tool_round(state, call_id=f"call_{index}")
            sizes.append(len(builder.build(state).history))
            await state.next_iteration()

        assert sizes == [3, 5, 7]

    @pytest.mark.asyncio
    async def test_digest_keeps_the_newest_rounds(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started()
        for index in range(5):
            await state.record_tool_call(_call(f"tool_{index}", id=f"call_{index}"))
            await state.next_iteration()

        builder = ContextBuilder(
            ContextConfig(max_tool_calls=2),
            registry=registry,
        )
        context = builder.build(state)

        assert [c.name for c in context.recent_tool_calls] == ["tool_3", "tool_4"]
        assert "tool_0" not in context.system_instructions

    @pytest.mark.asyncio
    async def test_same_state_builds_the_same_context_twice(
        self,
        builder: ContextBuilder,
    ) -> None:
        """Determinism: no clock, no registry order, no set iteration."""

        state = await _started()
        await _with_tool_round(state)
        await state.record_observation("Volume is thin.")

        first = builder.build(state)
        second = builder.build(state)

        assert first.to_dict() == second.to_dict()
        assert first.messages() == second.messages()


# ==============================================================
# Enabled / disabled tools
# ==============================================================


def _sample_tools(registry: ToolRegistry, define: Any) -> None:
    """Three tools, registered out of alphabetical order on purpose."""

    def zoom(level: int) -> str:
        """Zoom the chart."""
        return "zoomed"

    def annotate(text: str, color: str = "red") -> str:
        """Annotate the chart."""
        return "annotated"

    def measure(a: int, b: int) -> int:
        """Measure a span."""
        return a + b

    for function in (zoom, annotate, measure):
        registry.register(define(function, category="chart"))


class TestToolExposure:
    """Only enabled tools, from the injected registry, in a stable order."""

    def test_enabled_tools_become_schemas(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        _sample_tools(registry, define)

        context = builder.build(_state())

        assert context.has_tools
        assert set(context.tool_names) == {"annotate", "measure", "zoom"}

    def test_disabled_tools_are_not_offered(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        _sample_tools(registry, define)
        registry.disable("measure")

        context = builder.build(_state())

        assert "measure" not in context.tool_names
        assert set(context.tool_names) == {"annotate", "zoom"}

    def test_re_enabling_brings_a_tool_back(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        """Schemas are resolved per build, so a late registration is visible."""

        _sample_tools(registry, define)
        registry.disable("zoom")

        assert "zoom" not in builder.build(_state()).tool_names

        registry.enable("zoom")

        assert "zoom" in builder.build(_state()).tool_names

    def test_schema_order_is_alphabetical_not_registration_order(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        _sample_tools(registry, define)

        assert builder.build(_state()).tool_names == ("annotate", "measure", "zoom")

    def test_schemas_come_from_the_existing_generator(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        """Not a second schema format: byte-identical to ToolSchemaGenerator."""

        _sample_tools(registry, define)

        expected = schema_generator.generate(registry.get("annotate"))
        actual = next(
            schema
            for schema in builder.build(_state()).tools
            if schema["function"]["name"] == "annotate"
        )

        assert actual == expected
        assert actual["function"]["parameters"]["required"] == ["text"]

    def test_the_injected_registry_is_the_only_one_consulted(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        """No second registry: an isolated one must not see the singleton's tools."""

        _sample_tools(registry, define)

        names = set(builder.build(_state()).tool_names)

        assert names == {"annotate", "measure", "zoom"}
        assert names.isdisjoint(set(tool_registry.names()))

    def test_schemas_can_be_switched_off_entirely(
        self,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        _sample_tools(registry, define)
        builder = ContextBuilder(
            ContextConfig(include_tool_schemas=False),
            registry=registry,
        )

        assert builder.build(_state()).tools == ()

    def test_tool_schemas_are_handed_out_as_copies(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        _sample_tools(registry, define)
        context = builder.build(_state())

        schemas = context.tool_schemas()
        schemas[0]["function"]["name"] = "tampered"

        assert context.tool_names[0] == "annotate"


# ==============================================================
# Size limits
# ==============================================================


class TestSizeLimits:
    """A long run must not produce an unbounded prompt."""

    @pytest.mark.asyncio
    async def test_history_is_capped_at_the_configured_limit(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started()
        for index in range(30):
            await state.add_message(Message.assistant(f"turn {index}"))

        builder = ContextBuilder(
            ContextConfig(max_history_messages=5),
            registry=registry,
        )
        context = builder.build(state)

        assert len(context.history) == 5
        assert context.dropped_messages == 26
        assert context.is_trimmed

    @pytest.mark.asyncio
    async def test_the_newest_turns_are_the_ones_kept(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started()
        for index in range(10):
            await state.add_message(Message.assistant(f"turn {index}"))

        builder = ContextBuilder(
            ContextConfig(max_history_messages=3),
            registry=registry,
        )
        contents = [m["content"] for m in builder.build(state).history]

        assert contents == ["turn 7", "turn 8", "turn 9"]

    @pytest.mark.asyncio
    async def test_zero_history_drops_every_turn(
        self,
        registry: ToolRegistry,
    ) -> None:
        """`[-0:]` is the whole list, so zero has to be handled explicitly."""

        state = await _started()
        await state.add_message(Message.assistant("turn"))

        builder = ContextBuilder(
            ContextConfig(max_history_messages=0),
            registry=registry,
        )
        context = builder.build(state)

        assert context.history == ()
        assert context.dropped_messages == 2
        assert len(context.messages()) == 1

    @pytest.mark.asyncio
    async def test_tool_turn_with_no_call_anywhere_is_dropped(
        self,
        registry: ToolRegistry,
    ) -> None:
        """Nothing in the window announced this id, so the provider would reject it."""

        state = await _started()
        await state.add_message(
            Message.tool(tool_call_id="call_0", content="y" * 5000)
        )

        builder = ContextBuilder(
            ContextConfig(max_history_messages=10),
            registry=registry,
        )
        context = builder.build(state)

        assert context.dropped_orphans == 1
        assert all(m["role"] != "tool" for m in context.history)

    @pytest.mark.asyncio
    async def test_tool_body_truncation_applies_to_a_valid_round(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started()
        await _with_tool_round(state, content="y" * 5000)

        builder = ContextBuilder(
            ContextConfig(tool_result_max_chars=100),
            registry=registry,
        )
        tool_message = next(
            m for m in builder.build(state).history if m["role"] == "tool"
        )

        assert len(tool_message["content"]) < 200
        assert "truncated 4900 chars" in tool_message["content"]

    @pytest.mark.asyncio
    async def test_goal_is_truncated_too(self, registry: ToolRegistry) -> None:
        state = _state("g" * 3000)
        builder = ContextBuilder(
            ContextConfig(goal_max_chars=50),
            registry=registry,
        )

        context = builder.build(state)

        assert "truncated 2950 chars" in context.goal
        assert len(context.goal) < 200

    @pytest.mark.asyncio
    async def test_digests_are_capped_independently(
        self,
        registry: ToolRegistry,
    ) -> None:
        state = await _started()
        for index in range(12):
            await state.record_tool_call(_call(f"tool_{index}", id=f"c{index}"))
            await state.record_tool_result(
                _result(f"tool_{index}"),
                call_id=f"c{index}",
            )
            await state.record_observation(f"observation {index}")

        builder = ContextBuilder(
            ContextConfig(
                max_tool_calls=2,
                max_tool_results=3,
                max_observations=4,
            ),
            registry=registry,
        )
        context = builder.build(state)

        assert len(context.recent_tool_calls) == 2
        assert len(context.recent_tool_results) == 3
        assert len(context.observations) == 4

    @pytest.mark.asyncio
    async def test_prompt_size_stops_growing_once_the_limits_bite(
        self,
        registry: ToolRegistry,
    ) -> None:
        """The property that matters: a longer run is not a bigger prompt."""

        builder = ContextBuilder(
            ContextConfig(
                max_history_messages=4,
                max_tool_calls=2,
                max_tool_results=2,
                max_observations=2,
                tool_result_max_chars=200,
            ),
            registry=registry,
        )

        state = await _started()
        sizes: list[int] = []

        for index in range(12):
            await _with_tool_round(state, call_id=f"c{index}", content="z" * 4000)
            await state.record_observation(f"observation {index}")
            sizes.append(len(str(builder.build(state).messages())))

        # Not byte-identical -- the record labels carry growing indices -- but
        # flat: the 12th round costs the same as the 9th, which is the point.
        plateau = sizes[-4:]
        assert max(plateau) - min(plateau) < 20
        assert max(sizes) < 4000


# ==============================================================
# Configuration
# ==============================================================


class TestConfiguration:
    """Limits are clamped, not trusted."""

    def test_defaults_match_the_loop_they_feed(self) -> None:
        config = ContextConfig()

        # Restating either of these would let the two layers disagree about how
        # much of a tool result the model may see, or about what AetherOS is.
        assert config.tool_result_max_chars == 4000
        assert "AetherOS" in config.system_prompt

    def test_oversized_limits_are_clamped_to_the_ceiling(self) -> None:
        config = ContextConfig(
            max_history_messages=100_000,
            tool_result_max_chars=10**9,
        )

        assert config.max_history_messages == HISTORY_CEILING
        assert config.tool_result_max_chars == CHARS_CEILING

    def test_negative_limits_are_clamped_to_zero(self) -> None:
        config = ContextConfig(max_history_messages=-5, max_observations=-1)

        assert config.max_history_messages == 0
        assert config.max_observations == 0

    def test_a_non_numeric_limit_is_refused(self) -> None:
        with pytest.raises(AgentError) as info:
            ContextConfig(max_history_messages="lots")  # type: ignore[arg-type]

        assert info.value.code == "AGENT_CONTEXT_INVALID_LIMIT"

    def test_with_config_keeps_the_collaborators(
        self,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        _sample_tools(registry, define)
        builder = ContextBuilder(registry=registry)

        narrowed = builder.with_config(ContextConfig(max_history_messages=1))

        assert narrowed.config.max_history_messages == 1
        assert narrowed.build(_state()).tool_names == ("annotate", "measure", "zoom")

    def test_module_builder_defaults_to_the_shared_registry(self) -> None:
        """The singleton exists for parity with schema_generator/tool_executor."""

        assert isinstance(context_builder, ContextBuilder)
        assert context_builder.config.max_history_messages == 40

    def test_truncate_leaves_short_text_alone(self) -> None:
        assert truncate("short", 100) == "short"
        assert truncate("short", 0) == "short"

    def test_truncate_reports_what_it_dropped(self) -> None:
        assert truncate("abcdef", 2) == "ab…[truncated 4 chars]"


# ==============================================================
# Serialization and logging
# ==============================================================


class TestSerializationAndLogging:
    """One faithful view for auditing, one redacted view for the sinks."""

    @pytest.mark.asyncio
    async def test_to_dict_covers_the_eight_context_elements(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        _sample_tools(registry, define)
        state = await _started()
        await _with_tool_round(state)
        await state.record_observation("Volume is thin.")

        payload = builder.build(state).to_dict()

        for key in (
            "system_instructions",
            "history",
            "goal",
            "recent_tool_calls",
            "recent_tool_results",
            "observations",
            "tools",
            "iteration",
        ):
            assert key in payload, key

        assert payload["iteration"]["max_iterations"] == 8

    @pytest.mark.asyncio
    async def test_describe_hides_the_goal_and_the_conversation(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started("Analyze RELIANCE")
        await state.record_tool_call(_call("type_text", text="hunter2"))
        await state.add_message(Message.assistant("secret plan"))

        rendered = str(builder.build(state).describe())

        assert "RELIANCE" not in rendered
        assert "hunter2" not in rendered
        assert "secret plan" not in rendered

    @pytest.mark.asyncio
    async def test_describe_still_reports_the_shape(
        self,
        builder: ContextBuilder,
        registry: ToolRegistry,
        define: Any,
    ) -> None:
        _sample_tools(registry, define)
        state = await _started()
        await _with_tool_round(state)

        described = builder.build(state).describe()

        assert described["history_messages"] == 3
        assert described["tool_calls"] == 1
        assert described["tool_names"] == ["annotate", "measure", "zoom"]
        assert described["iteration"] == 1

    @pytest.mark.asyncio
    async def test_repr_leaks_neither_goal_nor_instructions(
        self,
        builder: ContextBuilder,
    ) -> None:
        state = await _started("Analyze RELIANCE")

        rendered = repr(builder.build(state))

        assert "RELIANCE" not in rendered
        assert "AgentContext(state_id=" in rendered

    @pytest.mark.asyncio
    async def test_context_is_frozen(self, builder: ContextBuilder) -> None:
        """A snapshot that can be edited after assembly is not a snapshot."""

        context = builder.build(_state())

        assert isinstance(context, AgentContext)
        with pytest.raises(FrozenInstanceError):
            context.goal = "something else"  # type: ignore[misc]

    def test_iteration_info_reports_its_position(self) -> None:
        assert IterationInfo(0, 8).is_first
        assert IterationInfo(1, 8).is_first
        assert not IterationInfo(2, 8).is_first
        assert IterationInfo(8, 8).is_final
        assert IterationInfo(9, 8).remaining == 0


# ==============================================================
# Provider compatibility
# ==============================================================


class TestProviderCompatibility:
    """The payload has to be accepted by the engine that already exists."""

    @pytest.mark.asyncio
    async def test_payload_drives_a_real_tool_call_round_trip(
        self,
        registry: ToolRegistry,
        define: Any,
        make_provider: Any,
        answer: Any,
    ) -> None:
        from aetheros.llm.engine import LLMEngine

        _sample_tools(registry, define)
        builder = ContextBuilder(registry=registry)

        state = await _started()
        await _with_tool_round(state)

        context = builder.build(state)
        provider = make_provider([answer("done")])
        engine = LLMEngine(provider, tool_provider=context.tool_schemas)

        response = await engine.tool_call(
            messages=context.messages(),
            tools=context.tool_schemas(),
        )

        assert response["content"] == "done"
        sent = provider.received_messages[-1]
        assert sent[0]["role"] == "system"
        assert [m["role"] for m in sent] == ["system", "user", "assistant", "tool"]
        assert provider.received_tools[-1][0]["function"]["name"] == "annotate"

    @pytest.mark.asyncio
    async def test_every_tool_turn_answers_a_call_in_the_payload(
        self,
        builder: ContextBuilder,
    ) -> None:
        """The invariant the provider enforces, asserted over the whole payload."""

        state = await _started()
        for index in range(4):
            await _with_tool_round(state, call_id=f"c{index}")
            await state.next_iteration()

        messages = builder.build(state).messages()

        announced: set[str] = set()
        for message in messages:
            for call in message.get("tool_calls") or ():
                announced.add(call["id"])
            if message["role"] == "tool":
                assert message["tool_call_id"] in announced

    @pytest.mark.asyncio
    async def test_concurrent_builds_see_a_consistent_snapshot(
        self,
        builder: ContextBuilder,
    ) -> None:
        """Reads are lock-free because state hands back immutable snapshots."""

        state = await _started()

        async def mutate() -> None:
            for index in range(20):
                await state.add_message(Message.assistant(f"turn {index}"))

        async def observe() -> list[int]:
            return [len(builder.build(state).history) for _ in range(20)]

        _, sizes = await asyncio.gather(mutate(), observe())

        assert sizes == sorted(sizes)
        assert len(builder.build(state).history) == 21
