"""
The LLM <-> tool execution loop, end to end.

Only the provider is faked. Schema generation, argument validation, tool
dispatch, result serialization and message construction are the real
implementations, so these tests exercise the whole path the CLI's `ask` runs:

    user message -> schemas -> provider -> tool calls -> executor
                 -> tool results -> provider -> final answer
"""

from __future__ import annotations

import json

import pytest

from aetheros.llm.agent_loop import AgentLoopConfig, AgentLoopResult, LLMToolLoop
from aetheros.llm.engine import LLMEngine
from aetheros.llm.tool_schema import get_llm_tools
from aetheros.tools.executor import ToolExecutor


# ==============================================================
# Sample tools
# ==============================================================


def add(a: int, b: int) -> int:
    """Add two integers."""

    return a + b


def scale(value: float, factor: float = 2.0) -> float:
    """Multiply a number."""

    return value * factor


def explodes() -> None:
    """A tool that fails."""

    raise ValueError("boom")


def long_output() -> str:
    """A tool that returns far more text than the model needs."""

    return "x" * 500


# ==============================================================
# Helpers
# ==============================================================


def _messages_of_role(
    result: AgentLoopResult,
    role: str,
) -> list[dict]:

    return [
        message
        for message in result.messages
        if message.get("role") == role
    ]


def _assert_every_tool_message_is_answerable(
    result: AgentLoopResult,
) -> None:
    """
    A ``role: "tool"`` message whose ``tool_call_id`` was never announced by an
    assistant turn is a provider 400 — the conversation becomes unusable from
    that point on. Every loop test runs this check.
    """

    announced: set[str] = set()

    for message in result.messages:

        role = message.get("role")

        if role == "assistant":

            for call in message.get("tool_calls") or []:
                announced.add(call["id"])

                # Both fields are mandatory in the wire format.
                assert call["function"]["name"]
                assert isinstance(call["function"]["arguments"], str)

        elif role == "tool":

            assert message["tool_call_id"] in announced, message


# ==============================================================
# Final answer
# ==============================================================


class TestFinalResponse:

    @pytest.mark.asyncio
    async def test_a_response_without_tool_calls_is_the_answer(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:

        registry.register(define(add))

        _, loop = make_loop([answer("The answer is 4.")])

        result = await loop.run_detailed("what is 2+2")

        assert result.content == "The answer is 4."
        assert result.stopped_reason == "final_answer"
        assert result.iterations == 1
        assert result.tool_results == ()
        assert result.used_tools is False

    @pytest.mark.asyncio
    async def test_run_returns_just_the_text(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:

        registry.register(define(add))

        _, loop = make_loop([answer("hello")])

        assert await loop.run("hi") == "hello"

    @pytest.mark.asyncio
    async def test_the_conversation_starts_with_system_then_user(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:

        registry.register(define(add))

        _, loop = make_loop([answer("ok")])

        result = await loop.run_detailed("what is 2+2")

        assert result.messages[0]["role"] == "system"
        assert result.messages[1] == {
            "role": "user",
            "content": "what is 2+2",
        }

    @pytest.mark.asyncio
    async def test_the_system_prompt_can_be_overridden(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:

        registry.register(define(add))

        _, loop = make_loop([answer("ok")])

        result = await loop.run_detailed(
            "hi",
            system_prompt="You are a calculator.",
        )

        assert result.messages[0]["content"] == "You are a calculator."


# ==============================================================
# Schemas reaching the provider
# ==============================================================


class TestSchemaDelivery:

    @pytest.mark.asyncio
    async def test_enabled_tool_schemas_reach_the_provider(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:
        """
        The original defect: `ask` passed tools inside the *message* dict, so
        the model was never offered a single tool.
        """

        registry.register(define(add))
        registry.register(define(scale))

        provider, loop = make_loop([answer("ok")])

        await loop.run_detailed("hi")

        assert provider.tool_call_count == 1

        offered = provider.received_tools[0]

        assert {schema["function"]["name"] for schema in offered} == {
            "add",
            "scale",
        }

    @pytest.mark.asyncio
    async def test_offered_schemas_carry_resolved_types(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:
        """
        Ties the PEP 563 fix to the wire: what the model actually receives must
        say "integer", not "string".
        """

        registry.register(define(add))

        provider, loop = make_loop([answer("ok")])

        await loop.run_detailed("hi")

        properties = provider.received_tools[0][0]["function"][
            "parameters"
        ]["properties"]

        assert properties["a"] == {"type": "integer"}
        assert properties["b"] == {"type": "integer"}

    @pytest.mark.asyncio
    async def test_disabled_tools_are_not_offered(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:

        registry.register(define(add))
        registry.register(define(scale, enabled=False))

        provider, loop = make_loop([answer("ok")])

        await loop.run_detailed("hi")

        assert [
            schema["function"]["name"]
            for schema in provider.received_tools[0]
        ] == ["add"]

    @pytest.mark.asyncio
    async def test_schemas_are_generated_once_per_run(
        self,
        registry,
        define,
        make_provider,
        tool_calls,
        answer,
    ) -> None:
        """
        Regenerating every schema on each round-trip is pure waste, and a tool
        set that changed mid-conversation would invalidate tool_call ids already
        in flight.
        """

        registry.register(define(add))

        generated = {"count": 0}

        def tool_provider() -> list[dict]:
            generated["count"] += 1
            return get_llm_tools(registry)

        provider = make_provider(
            [
                tool_calls(("add", {"a": 1, "b": 1})),
                tool_calls(("add", {"a": 2, "b": 2})),
                answer("done"),
            ]
        )

        loop = LLMToolLoop(
            LLMEngine(provider, tool_provider=tool_provider),
            ToolExecutor(registry),
        )

        result = await loop.run_detailed("hi")

        assert result.iterations == 3
        assert provider.tool_call_count == 3
        assert generated["count"] == 1


# ==============================================================
# Single-iteration tool use
# ==============================================================


class TestToolExecution:

    @pytest.mark.asyncio
    async def test_a_tool_call_runs_and_the_result_reaches_the_model(
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

        result = await loop.run_detailed("what is 2+3")

        assert result.stopped_reason == "final_answer"
        assert result.content == "It is 5."
        assert result.iterations == 2

        assert len(result.tool_results) == 1

        invocation = result.tool_results[0]

        assert invocation.name == "add"
        assert invocation.ok is True
        assert invocation.iteration == 1

        # The value the tool returned is what the model was shown.
        assert json.loads(invocation.content) == {"ok": True, "result": 5}

        _assert_every_tool_message_is_answerable(result)

    @pytest.mark.asyncio
    async def test_the_assistant_turn_is_replayed_in_wire_format(
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

        result = await loop.run_detailed("what is 2+3")

        assistant = _messages_of_role(result, "assistant")

        assert len(assistant) == 1

        call = assistant[0]["tool_calls"][0]

        assert call["type"] == "function"
        assert call["function"]["name"] == "add"

        # Arguments travel as a JSON string, never as a dict.
        assert json.loads(call["function"]["arguments"]) == {
            "a": 2,
            "b": 3,
        }

    @pytest.mark.asyncio
    async def test_the_tool_reply_is_addressed_to_the_call(
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

        result = await loop.run_detailed("what is 2+3")

        assistant = _messages_of_role(result, "assistant")[0]
        tool_messages = _messages_of_role(result, "tool")

        assert len(tool_messages) == 1
        assert (
            tool_messages[0]["tool_call_id"]
            == assistant["tool_calls"][0]["id"]
        )

    @pytest.mark.asyncio
    async def test_json_string_arguments_from_the_model_work(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        Real providers send arguments as a JSON string, not a dict.
        """

        registry.register(define(add))

        _, loop = make_loop(
            [
                tool_calls(("add", '{"a": 20, "b": 22}')),
                answer("42."),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.tool_results[0].ok is True
        assert json.loads(result.tool_results[0].content)["result"] == 42


class TestMultipleToolCalls:

    @pytest.mark.asyncio
    async def test_several_calls_in_one_iteration_all_run(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:

        registry.register(define(add))
        registry.register(define(scale))

        _, loop = make_loop(
            [
                tool_calls(
                    ("add", {"a": 1, "b": 2}),
                    ("scale", {"value": 4}),
                ),
                answer("done"),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.iterations == 2
        assert len(result.tool_results) == 2

        assert [
            invocation.name for invocation in result.tool_results
        ] == ["add", "scale"]

        assert all(
            invocation.ok for invocation in result.tool_results
        )
        assert all(
            invocation.iteration == 1 for invocation in result.tool_results
        )

    @pytest.mark.asyncio
    async def test_one_assistant_turn_announces_every_call(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:

        registry.register(define(add))
        registry.register(define(scale))

        _, loop = make_loop(
            [
                tool_calls(
                    ("add", {"a": 1, "b": 2}),
                    ("scale", {"value": 4}),
                ),
                answer("done"),
            ]
        )

        result = await loop.run_detailed("hi")

        assistant = _messages_of_role(result, "assistant")

        assert len(assistant) == 1
        assert len(assistant[0]["tool_calls"]) == 2

        assert len(_messages_of_role(result, "tool")) == 2

        _assert_every_tool_message_is_answerable(result)

    @pytest.mark.asyncio
    async def test_one_failing_call_does_not_stop_its_siblings(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:

        registry.register(define(add))
        registry.register(define(explodes))

        _, loop = make_loop(
            [
                tool_calls(
                    ("explodes", {}),
                    ("add", {"a": 1, "b": 2}),
                ),
                answer("done"),
            ]
        )

        result = await loop.run_detailed("hi")

        outcomes = {
            invocation.name: invocation.ok
            for invocation in result.tool_results
        }

        assert outcomes == {"explodes": False, "add": True}


# ==============================================================
# Multiple iterations
# ==============================================================


class TestMultipleIterations:

    @pytest.mark.asyncio
    async def test_the_loop_keeps_going_until_the_model_answers(
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
                tool_calls(("add", {"a": 1, "b": 1})),
                tool_calls(("add", {"a": 2, "b": 2})),
                tool_calls(("add", {"a": 3, "b": 3})),
                answer("All three done."),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "final_answer"
        assert result.iterations == 4
        assert len(result.tool_results) == 3

        assert [
            invocation.iteration for invocation in result.tool_results
        ] == [1, 2, 3]

        _assert_every_tool_message_is_answerable(result)

    @pytest.mark.asyncio
    async def test_earlier_results_stay_in_the_conversation(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        Each round-trip has to carry the whole history, or the model re-asks for
        what it already learned.
        """

        registry.register(define(add))

        provider, loop = make_loop(
            [
                tool_calls(("add", {"a": 1, "b": 1})),
                tool_calls(("add", {"a": 2, "b": 2})),
                answer("done"),
            ]
        )

        await loop.run_detailed("hi")

        first, second, third = provider.received_messages

        assert len(first) == 2
        assert len(second) == 4
        assert len(third) == 6

        assert second[2]["role"] == "assistant"
        assert second[3]["role"] == "tool"

    @pytest.mark.asyncio
    async def test_narration_before_a_tool_call_is_preserved(
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
                tool_calls(
                    ("add", {"a": 1, "b": 1}),
                    content="Let me add those.",
                ),
                answer("It is 2."),
            ]
        )

        result = await loop.run_detailed("hi")

        assistant = _messages_of_role(result, "assistant")[0]

        assert assistant["content"] == "Let me add those."

        # The final answer still wins as the returned content.
        assert result.content == "It is 2."


# ==============================================================
# Bounds
# ==============================================================


class TestMaxIterations:

    @pytest.mark.asyncio
    async def test_the_ceiling_returns_instead_of_raising(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
    ) -> None:
        """
        This used to raise RuntimeError, so a bounded and entirely expected
        outcome showed the user a traceback.
        """

        registry.register(define(add))

        _, loop = make_loop(
            [
                tool_calls(("add", {"a": 1, "b": 1})),
                tool_calls(("add", {"a": 2, "b": 2})),
                tool_calls(("add", {"a": 3, "b": 3})),
            ],
            config=AgentLoopConfig(max_iterations=2),
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "max_iterations"
        assert result.iterations == 2
        assert "Stopped after 2 iterations" in result.content

    @pytest.mark.asyncio
    async def test_the_provider_is_not_called_beyond_the_ceiling(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
    ) -> None:

        registry.register(define(add))

        provider, loop = make_loop(
            [
                tool_calls(("add", {"a": 1, "b": 1})),
                tool_calls(("add", {"a": 2, "b": 2})),
                tool_calls(("add", {"a": 3, "b": 3})),
                tool_calls(("add", {"a": 4, "b": 4})),
            ],
            config=AgentLoopConfig(max_iterations=3),
        )

        await loop.run_detailed("hi")

        assert provider.tool_call_count == 3

    @pytest.mark.asyncio
    async def test_results_gathered_so_far_are_still_returned(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
    ) -> None:

        registry.register(define(add))

        _, loop = make_loop(
            [
                tool_calls(("add", {"a": 1, "b": 1})),
                tool_calls(("add", {"a": 2, "b": 2})),
                tool_calls(("add", {"a": 3, "b": 3})),
            ],
            config=AgentLoopConfig(max_iterations=2),
        )

        result = await loop.run_detailed("hi")

        assert len(result.tool_results) == 2
        assert all(
            invocation.ok for invocation in result.tool_results
        )

    @pytest.mark.asyncio
    async def test_the_ceiling_can_be_overridden_per_run(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
    ) -> None:

        registry.register(define(add))

        provider, loop = make_loop(
            [
                tool_calls(("add", {"a": 1, "b": 1})),
                tool_calls(("add", {"a": 2, "b": 2})),
                tool_calls(("add", {"a": 3, "b": 3})),
            ],
            config=AgentLoopConfig(max_iterations=8),
        )

        result = await loop.run_detailed("hi", max_iterations=1)

        assert result.iterations == 1
        assert provider.tool_call_count == 1

    @pytest.mark.asyncio
    async def test_a_non_positive_ceiling_still_asks_the_model_once(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:
        """
        A limit of 0 would otherwise skip the provider entirely and return an
        empty answer with no explanation.
        """

        registry.register(define(add))

        provider, loop = make_loop([answer("ok")])

        result = await loop.run_detailed("hi", max_iterations=0)

        assert provider.tool_call_count == 1
        assert result.content == "ok"


class TestRepeatGuard:

    @pytest.mark.asyncio
    async def test_the_same_call_twice_in_a_row_ends_the_run(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
    ) -> None:
        """
        A model looping on one call would otherwise burn every iteration.
        """

        registry.register(define(add))

        # A single scripted response repeats forever.
        _, loop = make_loop(
            [tool_calls(("add", {"a": 1, "b": 1}))],
            config=AgentLoopConfig(max_iterations=8),
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "loop_guard"
        assert result.iterations == 2
        assert "same tool call" in result.content

    @pytest.mark.asyncio
    async def test_a_repeated_call_is_refused_rather_than_re_run(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        Re-running is not just wasted work: for a side-effecting tool such as
        `click` or `type_text` it would repeat a real action.
        """

        executions: list[tuple[int, int]] = []

        def counted_add(a: int, b: int) -> int:
            """Adds, and records that it really ran."""

            executions.append((a, b))

            return a + b

        registry.register(define(counted_add))

        _, loop = make_loop(
            [
                tool_calls(("counted_add", {"a": 1, "b": 1})),
                tool_calls(("counted_add", {"a": 2, "b": 2})),
                tool_calls(("counted_add", {"a": 1, "b": 1})),
                answer("done"),
            ],
            config=AgentLoopConfig(max_repeated_calls=1),
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "final_answer"

        # The third request repeated the first, so it never reached the tool.
        assert executions == [(1, 1), (2, 2)]

        refusals = [
            invocation
            for invocation in result.tool_results
            if not invocation.ok
        ]

        assert len(refusals) == 1
        assert "already been made" in (refusals[0].error or "")

    @pytest.mark.asyncio
    async def test_non_consecutive_repetition_is_allowed(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        Re-reading the screen before and after an action is legitimate; only
        back-to-back identical rounds are a loop.
        """

        registry.register(define(add))
        registry.register(define(scale))

        _, loop = make_loop(
            [
                tool_calls(("add", {"a": 1, "b": 1})),
                tool_calls(("scale", {"value": 2})),
                tool_calls(("add", {"a": 1, "b": 1})),
                answer("done"),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "final_answer"
        assert len(result.tool_results) == 3
        assert all(
            invocation.ok for invocation in result.tool_results
        )


# ==============================================================
# Failures fed back to the model
# ==============================================================


class TestFailureFeedback:

    @pytest.mark.asyncio
    async def test_a_failing_tool_does_not_end_the_run(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        The loop used to let the executor's exception escape, so one bad tool
        call aborted the whole conversation.
        """

        registry.register(define(explodes))

        _, loop = make_loop(
            [
                tool_calls(("explodes", {})),
                answer("That tool is broken."),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "final_answer"
        assert result.content == "That tool is broken."

        assert len(result.tool_results) == 1
        assert result.tool_results[0].ok is False

    @pytest.mark.asyncio
    async def test_the_failure_reason_is_shown_to_the_model(
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
                answer("ok"),
            ]
        )

        result = await loop.run_detailed("hi")

        payload = json.loads(
            _messages_of_role(result, "tool")[0]["content"]
        )

        assert payload["ok"] is False
        assert "boom" in payload["error"]
        assert payload["error_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_an_unknown_tool_is_reported_and_the_run_continues(
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
                tool_calls(("teleport", {})),
                answer("No such tool."),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "final_answer"

        payload = json.loads(result.tool_results[0].content)

        assert payload["error_type"] == "UnknownTool"
        assert "add" in payload["error"]

    @pytest.mark.asyncio
    async def test_invalid_arguments_are_reported_and_the_run_continues(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        The model sending the wrong type must be corrected, not allowed to
        trigger a TypeError inside a desktop backend.
        """

        registry.register(define(add))

        _, loop = make_loop(
            [
                tool_calls(("add", {"a": "two", "b": 3})),
                answer("Corrected."),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "final_answer"

        payload = json.loads(result.tool_results[0].content)

        assert payload["error_type"] == "InvalidArguments"


class TestMalformedToolCalls:

    @pytest.mark.asyncio
    async def test_unparseable_arguments_are_reported_not_executed(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:

        executions: list[object] = []

        def watched(a: int, b: int) -> int:
            """Records that it ran."""

            executions.append((a, b))

            return a + b

        registry.register(define(watched))

        _, loop = make_loop(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_bad",
                            "name": "watched",
                            "arguments": '{"a": 1, "b":',
                        }
                    ],
                },
                answer("I will retry."),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "final_answer"
        assert executions == []

        assert len(result.tool_results) == 1
        assert result.tool_results[0].ok is False
        assert "not valid JSON" in (result.tool_results[0].error or "")

    @pytest.mark.asyncio
    async def test_an_addressable_malformed_call_gets_a_tool_reply(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:
        """
        It has an id and a name, so the correction belongs in the assistant/tool
        exchange where the model expects it.
        """

        registry.register(define(add))

        _, loop = make_loop(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_bad",
                            "name": "add",
                            "arguments": "{oops",
                        }
                    ],
                },
                answer("ok"),
            ]
        )

        result = await loop.run_detailed("hi")

        tool_messages = _messages_of_role(result, "tool")

        assert len(tool_messages) == 1
        assert tool_messages[0]["tool_call_id"] == "call_bad"

        # The assistant turn replays exactly what the model said, so the ids
        # line up.
        assistant = _messages_of_role(result, "assistant")[0]

        assert assistant["tool_calls"][0]["function"]["arguments"] == (
            "{oops"
        )

        _assert_every_tool_message_is_answerable(result)

    @pytest.mark.asyncio
    async def test_a_nameless_call_is_corrected_with_a_user_note(
        self,
        registry,
        define,
        make_loop,
        answer,
    ) -> None:
        """
        A tool message needs a name to be valid, so a nameless call cannot be
        answered inside the tool exchange at all — the provider would reject the
        whole request.
        """

        registry.register(define(add))

        _, loop = make_loop(
            [
                {
                    "content": "",
                    "tool_calls": [
                        {"id": "call_x", "arguments": {"a": 1}}
                    ],
                },
                answer("Sorry about that."),
            ]
        )

        result = await loop.run_detailed("hi")

        assert result.stopped_reason == "final_answer"

        # No assistant turn, because there was nothing valid to replay.
        assert _messages_of_role(result, "assistant") == []
        assert _messages_of_role(result, "tool") == []

        notes = [
            message
            for message in _messages_of_role(result, "user")
            if "no function name" in message["content"]
        ]

        assert len(notes) == 1

        assert result.tool_results[0].name == "<unnamed>"
        assert result.tool_results[0].ok is False


# ==============================================================
# Oversized results
# ==============================================================


class TestResultTruncation:

    @pytest.mark.asyncio
    async def test_long_results_are_truncated_with_a_marker(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        The model must know it did not see everything, rather than silently
        reasoning over a cut-off value.
        """

        registry.register(define(long_output))

        _, loop = make_loop(
            [
                tool_calls(("long_output", {})),
                answer("done"),
            ],
            config=AgentLoopConfig(tool_result_max_chars=50),
        )

        result = await loop.run_detailed("hi")

        content = _messages_of_role(result, "tool")[0]["content"]

        assert content.startswith('{"ok": true')
        assert "[truncated" in content
        assert content.endswith("chars]")

    @pytest.mark.asyncio
    async def test_the_recorded_invocation_holds_the_truncated_text(
        self,
        registry,
        define,
        make_loop,
        tool_calls,
        answer,
    ) -> None:
        """
        Storing the raw return value instead would let a run's history pin a
        captured frame or an OCR buffer in memory.
        """

        registry.register(define(long_output))

        _, loop = make_loop(
            [
                tool_calls(("long_output", {})),
                answer("done"),
            ],
            config=AgentLoopConfig(tool_result_max_chars=50),
        )

        result = await loop.run_detailed("hi")

        assert (
            result.tool_results[0].content
            == _messages_of_role(result, "tool")[0]["content"]
        )

    @pytest.mark.asyncio
    async def test_short_results_are_left_alone(
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
                tool_calls(("add", {"a": 1, "b": 1})),
                answer("done"),
            ],
            config=AgentLoopConfig(tool_result_max_chars=4000),
        )

        result = await loop.run_detailed("hi")

        content = _messages_of_role(result, "tool")[0]["content"]

        assert "truncated" not in content
        assert json.loads(content) == {"ok": True, "result": 2}


# ==============================================================
# No tools available
# ==============================================================


class TestNoToolsAvailable:

    @pytest.mark.asyncio
    async def test_an_empty_registry_falls_back_to_plain_generation(
        self,
        registry,
        make_loop,
    ) -> None:
        """
        OpenAI-compatible endpoints reject an empty `tools` array, and
        LLMProvider.tool_call takes `tools` as required — so with nothing to
        offer, the engine must generate instead.
        """

        provider, loop = make_loop(
            generate_result="No tools, but here is an answer.",
        )

        result = await loop.run_detailed("hi")

        assert provider.tool_call_count == 0
        assert provider.generate_count == 1

        assert result.content == "No tools, but here is an answer."
        assert result.stopped_reason == "final_answer"
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_no_tool_provider_at_all_falls_back_too(
        self,
        registry,
        define,
        make_loop,
    ) -> None:

        registry.register(define(add))

        provider, loop = make_loop(
            offer_tools=False,
            generate_result="plain answer",
        )

        result = await loop.run_detailed("hi")

        assert provider.tool_call_count == 0
        assert provider.generate_count == 1
        assert result.content == "plain answer"

    @pytest.mark.asyncio
    async def test_all_tools_disabled_falls_back_too(
        self,
        registry,
        define,
        make_loop,
    ) -> None:

        registry.register(define(add, enabled=False))
        registry.register(define(scale, enabled=False))

        provider, loop = make_loop(generate_result="plain answer")

        result = await loop.run_detailed("hi")

        assert provider.tool_call_count == 0
        assert provider.generate_count == 1
        assert result.content == "plain answer"


# ==============================================================
# Engine
# ==============================================================


class TestEngine:

    def test_provider_details_are_exposed_read_only(
        self,
        make_provider,
    ) -> None:
        """
        Used for logging and for the CLI's `llm` command. The engine must not
        hardcode either value.
        """

        engine = LLMEngine(
            make_provider(name="acme", model="acme-large")
        )

        assert engine.provider_name == "acme"
        assert engine.model == "acme-large"

    def test_no_tool_provider_means_no_tools(
        self,
        make_provider,
    ) -> None:

        assert LLMEngine(make_provider()).available_tools() == []

    def test_available_tools_reflects_later_registration(
        self,
        registry,
        define,
        make_provider,
    ) -> None:
        """
        The provider callable is invoked per run, not captured at construction,
        so a tool registered after bootstrap is still offered.
        """

        engine = LLMEngine(
            make_provider(),
            tool_provider=lambda: get_llm_tools(registry),
        )

        assert engine.available_tools() == []

        registry.register(define(add))

        assert len(engine.available_tools()) == 1

    @pytest.mark.asyncio
    async def test_explicit_tools_override_the_provider(
        self,
        registry,
        define,
        make_provider,
        answer,
    ) -> None:

        registry.register(define(add))

        provider = make_provider([answer("ok")])

        engine = LLMEngine(
            provider,
            tool_provider=lambda: get_llm_tools(registry),
        )

        explicit = [
            {
                "type": "function",
                "function": {
                    "name": "only_this",
                    "description": "",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        await engine.tool_call(
            messages=[{"role": "user", "content": "hi"}],
            tools=explicit,
        )

        assert provider.received_tools[0] == explicit
