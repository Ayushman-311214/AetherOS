"""
Parsing of provider tool-call responses.

Everything the model emits is untrusted input, and ``parse_llm_response`` is the
only place that decides what a malformed payload means — the provider no longer
does any JSON decoding of its own. The contract asserted throughout this module
is that it never raises: a broken payload becomes a ``MalformedToolCall`` the
loop can report back, never an exception that ends the conversation.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from aetheros.llm.tool_calls import (
    MalformedToolCall,
    ParsedResponse,
    ToolCall,
    parse_llm_response,
)


def _one(raw: dict) -> ToolCall | MalformedToolCall:
    """
    Parse a response expected to hold exactly one call, and return it.
    """

    parsed = parse_llm_response(raw)

    calls = [*parsed.tool_calls, *parsed.malformed]

    assert len(calls) == 1, calls

    return calls[0]


# ==============================================================
# Well-formed calls
# ==============================================================


class TestWellFormedCalls:

    def test_dict_arguments_are_used_directly(self) -> None:

        call = _one(
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "name": "move_mouse",
                        "arguments": {"dx": 10, "dy": -5},
                    }
                ],
            }
        )

        assert isinstance(call, ToolCall)
        assert call.id == "call_abc"
        assert call.name == "move_mouse"
        assert call.arguments == {"dx": 10, "dy": -5}

    def test_json_string_arguments_are_decoded(self) -> None:
        """
        The OpenAI wire format sends arguments as a JSON *string*.
        """

        call = _one(
            {
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "name": "move_mouse",
                        "arguments": '{"dx": 10, "dy": -5}',
                    }
                ],
            }
        )

        assert isinstance(call, ToolCall)
        assert call.arguments == {"dx": 10, "dy": -5}

    def test_nested_function_shape_is_understood(self) -> None:
        """
        A provider that passes the wire shape through verbatim keeps the name
        and arguments under `function`.
        """

        call = _one(
            {
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "add",
                            "arguments": '{"a": 1, "b": 2}',
                        },
                    }
                ],
            }
        )

        assert isinstance(call, ToolCall)
        assert call.name == "add"
        assert call.arguments == {"a": 1, "b": 2}

    def test_object_entries_are_understood(self) -> None:
        """
        SDK responses arrive as objects with attributes, not dicts.
        """

        entry = SimpleNamespace(
            id="call_sdk",
            type="function",
            function=SimpleNamespace(
                name="press_key",
                arguments='{"key": "enter"}',
            ),
        )

        call = _one({"tool_calls": [entry]})

        assert isinstance(call, ToolCall)
        assert call.id == "call_sdk"
        assert call.name == "press_key"
        assert call.arguments == {"key": "enter"}

    def test_absent_arguments_become_an_empty_dict(self) -> None:

        call = _one(
            {"tool_calls": [{"id": "c", "name": "screen_size"}]}
        )

        assert isinstance(call, ToolCall)
        assert call.arguments == {}

    def test_empty_string_arguments_become_an_empty_dict(self) -> None:
        """
        A no-argument tool is commonly called with "" or "  ".
        """

        for value in ("", "   ", "{}"):

            call = _one(
                {
                    "tool_calls": [
                        {
                            "id": "c",
                            "name": "screen_size",
                            "arguments": value,
                        }
                    ]
                }
            )

            assert isinstance(call, ToolCall), value
            assert call.arguments == {}

    def test_name_is_stripped(self) -> None:

        call = _one(
            {
                "tool_calls": [
                    {"id": "c", "name": "  add  ", "arguments": {}}
                ]
            }
        )

        assert isinstance(call, ToolCall)
        assert call.name == "add"

    def test_multiple_calls_are_all_parsed(self) -> None:

        parsed = parse_llm_response(
            {
                "tool_calls": [
                    {"id": "a", "name": "one", "arguments": {}},
                    {"id": "b", "name": "two", "arguments": {"x": 1}},
                    {"id": "c", "name": "three", "arguments": "{}"},
                ]
            }
        )

        assert [call.name for call in parsed.tool_calls] == [
            "one",
            "two",
            "three",
        ]

        assert parsed.malformed == ()
        assert parsed.has_calls is True


# ==============================================================
# raw_arguments
# ==============================================================


class TestRawArguments:

    def test_original_string_is_preserved_verbatim(self) -> None:
        """
        The assistant turn replayed to the provider must match what the model
        actually said, character for character.
        """

        original = '{"dx":10,   "dy":-5}'

        call = _one(
            {
                "tool_calls": [
                    {
                        "id": "c",
                        "name": "move_mouse",
                        "arguments": original,
                    }
                ]
            }
        )

        assert isinstance(call, ToolCall)
        assert call.raw_arguments == original

    def test_dict_arguments_are_serialized(self) -> None:

        call = _one(
            {
                "tool_calls": [
                    {
                        "id": "c",
                        "name": "move_mouse",
                        "arguments": {"dx": 10},
                    }
                ]
            }
        )

        assert isinstance(call, ToolCall)
        assert json.loads(call.raw_arguments) == {"dx": 10}

    def test_raw_arguments_defaults_to_an_empty_object(self) -> None:

        call = _one({"tool_calls": [{"id": "c", "name": "noop"}]})

        assert isinstance(call, ToolCall)
        assert json.loads(call.raw_arguments) == {}

    def test_unserializable_arguments_still_produce_a_string(self) -> None:
        """
        default=str covers most oddities; the result must be valid JSON either
        way, since it is replayed into the conversation.
        """

        call = _one(
            {
                "tool_calls": [
                    {
                        "id": "c",
                        "name": "noop",
                        "arguments": {"when": object()},
                    }
                ]
            }
        )

        assert isinstance(call, ToolCall)
        assert isinstance(json.loads(call.raw_arguments), dict)


# ==============================================================
# Malformed calls
# ==============================================================


class TestMalformedCalls:

    def test_invalid_json_arguments_are_reported(self) -> None:

        call = _one(
            {
                "tool_calls": [
                    {
                        "id": "call_bad",
                        "name": "move_mouse",
                        "arguments": '{"dx": 10, "dy":',
                    }
                ]
            }
        )

        assert isinstance(call, MalformedToolCall)
        assert call.id == "call_bad"
        assert call.name == "move_mouse"
        assert "not valid JSON" in call.reason

        # Named and identified, so the model can be corrected with a proper
        # tool message rather than a loose user note.
        assert call.is_addressable is True

    def test_the_offending_payload_is_kept(self) -> None:

        call = _one(
            {
                "tool_calls": [
                    {
                        "id": "c",
                        "name": "move_mouse",
                        "arguments": "not json at all",
                    }
                ]
            }
        )

        assert isinstance(call, MalformedToolCall)
        assert call.raw == "not json at all"

    def test_json_array_arguments_are_rejected(self) -> None:
        """
        Valid JSON, but not an object: it cannot be splatted into a signature.
        """

        call = _one(
            {
                "tool_calls": [
                    {
                        "id": "c",
                        "name": "move_mouse",
                        "arguments": "[10, -5]",
                    }
                ]
            }
        )

        assert isinstance(call, MalformedToolCall)
        assert "JSON object" in call.reason
        assert "list" in call.reason

    def test_non_string_non_dict_arguments_are_rejected(self) -> None:

        call = _one(
            {
                "tool_calls": [
                    {"id": "c", "name": "move_mouse", "arguments": 42}
                ]
            }
        )

        assert isinstance(call, MalformedToolCall)
        assert "int" in call.reason

    def test_missing_name_is_not_addressable(self) -> None:
        """
        A tool message must carry a name, so a nameless call cannot be answered
        inside the assistant/tool exchange at all.
        """

        call = _one(
            {"tool_calls": [{"id": "c", "arguments": {"dx": 1}}]}
        )

        assert isinstance(call, MalformedToolCall)
        assert call.name is None
        assert call.is_addressable is False
        assert "function name" in call.reason

    def test_blank_name_is_treated_as_missing(self) -> None:

        for value in ("", "   ", None, 7):

            call = _one(
                {"tool_calls": [{"id": "c", "name": value}]}
            )

            assert isinstance(call, MalformedToolCall), value
            assert call.name is None

    def test_a_garbage_entry_is_reported_not_dropped(self) -> None:
        """
        Dropping it silently would leave the model repeating the same broken
        call until the loop gave up.
        """

        parsed = parse_llm_response(
            {"tool_calls": ["hello", 42, None]}
        )

        assert parsed.tool_calls == ()
        assert len(parsed.malformed) == 3
        assert all(
            call.is_addressable is False for call in parsed.malformed
        )

    def test_well_formed_and_malformed_calls_coexist(self) -> None:

        parsed = parse_llm_response(
            {
                "tool_calls": [
                    {"id": "a", "name": "good", "arguments": {"x": 1}},
                    {"id": "b", "name": "bad", "arguments": "{oops"},
                ]
            }
        )

        assert [call.name for call in parsed.tool_calls] == ["good"]
        assert [call.name for call in parsed.malformed] == ["bad"]
        assert parsed.has_calls is True


# ==============================================================
# Identifiers
# ==============================================================


class TestCallIdentifiers:

    def test_missing_id_is_synthesized_from_the_index(self) -> None:
        """
        A tool message whose tool_call_id matches nothing in the assistant turn
        is a provider 400, so an id has to exist even when the model omits one.
        """

        parsed = parse_llm_response(
            {
                "tool_calls": [
                    {"name": "one", "arguments": {}},
                    {"name": "two", "arguments": {}},
                ]
            }
        )

        assert [call.id for call in parsed.tool_calls] == [
            "call_0",
            "call_1",
        ]

    def test_synthesized_ids_are_unique_per_response(self) -> None:

        parsed = parse_llm_response(
            {
                "tool_calls": [
                    {"name": "one"},
                    {"name": "two"},
                    {"name": "three"},
                ]
            }
        )

        ids = [call.id for call in parsed.tool_calls]

        assert len(set(ids)) == len(ids)

    def test_blank_id_is_replaced(self) -> None:

        call = _one({"tool_calls": [{"id": "", "name": "one"}]})

        assert isinstance(call, ToolCall)
        assert call.id == "call_0"

    def test_non_string_id_is_replaced(self) -> None:

        call = _one({"tool_calls": [{"id": 99, "name": "one"}]})

        assert isinstance(call, ToolCall)
        assert call.id == "call_0"


# ==============================================================
# Content and degenerate responses
# ==============================================================


class TestContent:

    def test_content_is_returned_with_no_calls(self) -> None:

        parsed = parse_llm_response(
            {"content": "The answer is 4.", "tool_calls": []}
        )

        assert parsed.content == "The answer is 4."
        assert parsed.has_calls is False

    def test_absent_tool_calls_field_means_no_calls(self) -> None:

        parsed = parse_llm_response({"content": "done"})

        assert parsed.content == "done"
        assert parsed.tool_calls == ()
        assert parsed.malformed == ()
        assert parsed.has_calls is False

    def test_tool_calls_of_the_wrong_type_is_ignored(self) -> None:

        for value in ("not-a-list", 42, {"a": 1}, None):

            parsed = parse_llm_response(
                {"content": "hi", "tool_calls": value}
            )

            assert parsed.content == "hi", value
            assert parsed.has_calls is False, value

    def test_content_and_calls_together(self) -> None:
        """
        Models often narrate before calling a tool.
        """

        parsed = parse_llm_response(
            {
                "content": "Let me check that.",
                "tool_calls": [{"id": "c", "name": "check"}],
            }
        )

        assert parsed.content == "Let me check that."
        assert len(parsed.tool_calls) == 1

    def test_missing_content_becomes_empty_string(self) -> None:

        parsed = parse_llm_response({"tool_calls": []})

        assert parsed.content == ""

    def test_null_content_becomes_empty_string(self) -> None:
        """
        The wire format sets content to null on a pure tool-call turn.
        """

        parsed = parse_llm_response(
            {"content": None, "tool_calls": []}
        )

        assert parsed.content == ""

    def test_non_string_content_is_stringified(self) -> None:

        parsed = parse_llm_response({"content": 42})

        assert parsed.content == "42"


class TestDegenerateInput:

    @pytest.mark.parametrize(
        "raw",
        [
            None,
            "",
            "a bare string answer",
            42,
            [],
            ["nope"],
            object(),
            {},
        ],
    )
    def test_never_raises(self, raw) -> None:

        parsed = parse_llm_response(raw)

        assert isinstance(parsed, ParsedResponse)

    def test_a_bare_string_is_treated_as_the_answer(self) -> None:
        """
        A provider that returned plain text still yields a usable answer.
        """

        parsed = parse_llm_response("just text")

        assert parsed.content == "just text"
        assert parsed.has_calls is False

    def test_non_string_non_dict_yields_empty_content(self) -> None:

        parsed = parse_llm_response(42)

        assert parsed.content == ""
        assert parsed.has_calls is False
