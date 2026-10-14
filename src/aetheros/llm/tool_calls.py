"""
Safe parsing of a provider's tool-calling response.

Everything a model emits is untrusted input: arguments may be a JSON string, a
dict, or malformed JSON; a call may be missing its ``id`` or its ``name``; the
whole ``tool_calls`` field may be absent or the wrong type. Parsing lives here,
apart from the loop, so it is directly testable and so no failure in it can
take down a conversation.

:func:`parse_llm_response` never raises.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolCall:
    """
    A tool call the model requested, with usable arguments.
    """

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    # The exact JSON string the model produced, preserved so the assistant
    # message replayed to the provider matches what the model actually said.
    raw_arguments: str = "{}"


@dataclass(frozen=True, slots=True)
class MalformedToolCall:
    """
    A tool call that could not be turned into something executable.

    Surfaced rather than dropped: a model emitting invalid JSON needs to be
    told so, or it will repeat the same broken call until the loop gives up.
    """

    id: str | None
    name: str | None
    raw: str
    reason: str

    @property
    def is_addressable(self) -> bool:
        """
        Whether this call can be answered with a ``role: "tool"`` message.

        The OpenAI wire format requires every tool message's ``tool_call_id``
        to match a call in the preceding assistant message, and every replayed
        call to carry a string ``name``. A call missing either cannot be
        represented in that exchange, so its correction has to be delivered as
        a plain user-role note instead.
        """

        return bool(self.id) and bool(self.name)


@dataclass(frozen=True, slots=True)
class ParsedResponse:
    """
    Normalised view of one provider response.
    """

    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    malformed: tuple[MalformedToolCall, ...] = ()

    @property
    def has_calls(self) -> bool:
        return bool(self.tool_calls) or bool(self.malformed)


def parse_llm_response(
    raw: Any,
) -> ParsedResponse:
    """
    Normalise a provider tool-call response. Never raises.

    Accepts the shape returned by ``LLMProvider.tool_call`` — a mapping with
    ``content`` and ``tool_calls`` — and tolerates entries expressed either as
    dicts or as objects with attributes.
    """

    if not isinstance(raw, dict):
        # A provider that returned a bare string (or nothing) still yields a
        # usable final answer rather than an error.
        return ParsedResponse(
            content=raw if isinstance(raw, str) else ""
        )

    content = raw.get("content")

    if not isinstance(content, str):
        content = "" if content is None else str(content)

    entries = raw.get("tool_calls")

    if not isinstance(entries, (list, tuple)):
        return ParsedResponse(content=content)

    calls: list[ToolCall] = []
    malformed: list[MalformedToolCall] = []

    for index, entry in enumerate(entries):

        parsed = _parse_entry(entry, index)

        if isinstance(parsed, ToolCall):
            calls.append(parsed)
        else:
            malformed.append(parsed)

    return ParsedResponse(
        content=content,
        tool_calls=tuple(calls),
        malformed=tuple(malformed),
    )


# ==============================================================
# Internal
# ==============================================================


def _parse_entry(
    entry: Any,
    index: int,
) -> ToolCall | MalformedToolCall:

    call_id = _read(entry, "id")
    name = _read(entry, "name")
    arguments = _read(entry, "arguments")

    # Providers that hand back the nested OpenAI wire shape verbatim keep the
    # name and arguments under `function`.
    function = _read(entry, "function")

    if function is not None:
        name = name or _read(function, "name")

        if arguments is None:
            arguments = _read(function, "arguments")

    # An absent id is recoverable: synthesise a deterministic one so the
    # assistant/tool message pair stays internally consistent.
    if not isinstance(call_id, str) or not call_id:
        call_id = f"call_{index}"

    if not isinstance(name, str) or not name.strip():
        return MalformedToolCall(
            id=call_id,
            name=None,
            raw=_stringify(entry),
            reason=(
                "Tool call is missing a function name."
            ),
        )

    name = name.strip()

    resolved, error = _parse_arguments(arguments)

    if error is not None:
        return MalformedToolCall(
            id=call_id,
            name=name,
            raw=_stringify(arguments),
            reason=error,
        )

    return ToolCall(
        id=call_id,
        name=name,
        arguments=resolved,
        raw_arguments=_raw_arguments(arguments, resolved),
    )


def _parse_arguments(
    arguments: Any,
) -> tuple[dict[str, Any], str | None]:
    """
    Return ``(arguments, error)``; exactly one is meaningful.
    """

    if arguments is None:
        return {}, None

    if isinstance(arguments, dict):
        return dict(arguments), None

    if isinstance(arguments, str):

        text = arguments.strip()

        if not text:
            return {}, None

        try:
            decoded = json.loads(text)

        except (json.JSONDecodeError, ValueError) as exc:
            return {}, (
                f"Arguments are not valid JSON: {exc}. "
                f"Send a JSON object."
            )

        if not isinstance(decoded, dict):
            return {}, (
                f"Arguments must be a JSON object, got "
                f"{type(decoded).__name__}."
            )

        return decoded, None

    return {}, (
        f"Arguments must be a JSON object, got "
        f"{type(arguments).__name__}."
    )


def _raw_arguments(
    arguments: Any,
    resolved: dict[str, Any],
) -> str:
    """
    The argument string to replay in the assistant message.
    """

    if isinstance(arguments, str) and arguments.strip():
        return arguments

    try:
        return json.dumps(resolved, default=str)

    except (TypeError, ValueError):
        return "{}"


def _read(
    source: Any,
    key: str,
) -> Any:
    """
    Read ``key`` from a mapping or an attribute of an object.
    """

    if isinstance(source, dict):
        return source.get(key)

    return getattr(source, key, None)


def _stringify(
    value: Any,
) -> str:
    """
    Best-effort text form of a malformed payload, for the error report.
    """

    if isinstance(value, str):
        return value

    try:
        return json.dumps(value, default=str)

    except (TypeError, ValueError):
        return repr(value)
