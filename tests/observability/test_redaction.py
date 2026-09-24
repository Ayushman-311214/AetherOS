"""
Log-safe projections for trace payloads (PHASES 3, 5, 11).

The redaction rules are a hard safety boundary: argument *values* and anything
that looks like a credential, a system prompt or hidden reasoning must never
reach a trace, whatever a caller passes. Large text is bounded so a screenful of
page HTML cannot flood the dashboard or a JSONL line.
"""

from __future__ import annotations

from aetheros.core.observability import (
    redact_keys,
    safe_metadata,
    safe_preview,
    truncate_value,
)


class TestSafePreview:
    def test_short_text_passes_through(self) -> None:
        assert safe_preview("hello") == "hello"

    def test_none_becomes_empty(self) -> None:
        assert safe_preview(None) == ""

    def test_long_text_is_truncated_with_a_total(self) -> None:
        rendered = safe_preview("x" * 600, limit=500)
        assert rendered.startswith("x" * 500)
        assert "600 chars total" in rendered

    def test_non_strings_are_stringified(self) -> None:
        assert safe_preview({"x": 500}) == "{'x': 500}"


class TestTruncateValue:
    def test_scalars_pass_through(self) -> None:
        assert truncate_value(500) == 500
        assert truncate_value(True) is True
        assert truncate_value(None) is None

    def test_a_long_string_is_clipped(self) -> None:
        assert "chars total" in truncate_value("y" * 400, limit=200)

    def test_containers_are_summarised_by_size(self) -> None:
        # A huge tool result becomes a size summary, never thousands of lines.
        assert truncate_value([1, 2, 3]) == {"list": "3 items"}
        assert truncate_value({"a": 1, "b": 2}) == {"dict": "2 keys"}


class TestSafeMetadata:
    def test_empty_input_is_empty(self) -> None:
        assert safe_metadata(None) == {}

    def test_forbidden_keys_are_redacted(self) -> None:
        # A careless caller cannot leak a credential or a raw prompt into the
        # trace file.
        cleaned = safe_metadata(
            {
                "api_key": "sk-secret",
                "authorization": "Bearer xyz",
                "system_prompt": "you are...",
                "messages": [{"role": "user"}],
                "tool_name": "mouse_position",
            }
        )
        assert cleaned["api_key"] == "[redacted]"
        assert cleaned["authorization"] == "[redacted]"
        assert cleaned["system_prompt"] == "[redacted]"
        assert cleaned["messages"] == "[redacted]"
        # A safe key survives untouched.
        assert cleaned["tool_name"] == "mouse_position"

    def test_forbidden_keys_are_case_insensitive(self) -> None:
        assert safe_metadata({"API_KEY": "x"})["API_KEY"] == "[redacted]"

    def test_argument_values_are_never_stored(self) -> None:
        # The single most important rule: a password typed via type_text must not
        # travel as an argument value.
        assert safe_metadata({"arguments": {"text": "hunter2"}})[
            "arguments"
        ] == "[redacted]"

    def test_surviving_values_are_bounded(self) -> None:
        cleaned = safe_metadata({"note": "z" * 400})
        assert "chars total" in cleaned["note"]


class TestRedactKeys:
    def test_forbidden_keys_are_redacted_without_shortening_the_rest(self) -> None:
        # The payload path keeps the caller's already-bounded 500-char preview
        # rather than clipping it to the tighter value limit.
        long_preview = "p" * 400
        cleaned = redact_keys({"password": "x", "result_preview": long_preview})
        assert cleaned["password"] == "[redacted]"
        assert cleaned["result_preview"] == long_preview

    def test_empty_input_is_empty(self) -> None:
        assert redact_keys(None) == {}
