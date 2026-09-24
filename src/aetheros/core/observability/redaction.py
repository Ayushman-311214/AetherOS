"""
Log-safe projections for trace payloads.

The trace persists to disk and renders to a terminal, so nothing that reaches a
:class:`~aetheros.core.observability.events.TraceEvent` may carry a secret. The
rules mirror the ones already enforced across the agent layer (see
``AgentExecutionResult.describe`` and ``PlannedAction.argument_names``): argument
*values* are never emitted -- only names -- because ``type_text`` and
``set_clipboard`` receive literal keystrokes that may be a password; API keys,
credentials, system prompts and chain-of-thought are never emitted at all; and
large text is truncated so a screen-full of page HTML cannot flood the trace.
"""

from __future__ import annotations

from typing import Any

# A response preview long enough to be useful, short enough not to bury the
# dashboard or blow up a JSONL line.
_PREVIEW_LIMIT = 500
_VALUE_LIMIT = 200

# Metadata keys whose values must never be stored, whatever a caller passes.
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "password",
        "passwd",
        "credential",
        "credentials",
        "system_prompt",
        "prompt",
        "messages",
        "reasoning",
        "chain_of_thought",
        "cot",
        "arguments",
        "argument_values",
    }
)


def safe_preview(text: Any, limit: int = _PREVIEW_LIMIT) -> str:
    """A truncated, single-block preview of model/tool text.

    Not a secret filter -- callers must only pass observable output (a model's
    visible answer, a tool's returned text), never a system prompt or hidden
    reasoning. Its job is purely to bound length.
    """

    if text is None:
        return ""
    rendered = text if isinstance(text, str) else str(text)
    if len(rendered) <= limit:
        return rendered
    return f"{rendered[:limit]}... ({len(rendered)} chars total)"


def truncate_value(value: Any, limit: int = _VALUE_LIMIT) -> Any:
    """Bound the size of an arbitrary value destined for a payload.

    Scalars pass through; strings are clipped; containers are summarised by size
    rather than expanded, so a huge tool result becomes ``{"list": 4096 items}``
    instead of thousands of lines.
    """

    if isinstance(value, str):
        return safe_preview(value, limit)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {"dict": f"{len(value)} keys"}
    if isinstance(value, (list, tuple, set)):
        return {"list": f"{len(value)} items"}
    return safe_preview(repr(value), limit)


def safe_metadata(data: dict[str, Any] | None) -> dict[str, Any]:
    """Strip forbidden keys and bound the rest.

    A defence in depth, not the primary guard: emit sites are expected to pass
    already-safe ``.describe()`` projections. This still refuses anything that
    looks like a credential or a raw prompt, and truncates oversized values, so a
    careless caller cannot leak a secret into the trace file.
    """

    if not data:
        return {}

    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if str(key).strip().lower() in _FORBIDDEN_KEYS:
            cleaned[key] = "[redacted]"
            continue
        cleaned[key] = truncate_value(value)
    return cleaned


def redact_keys(data: dict[str, Any] | None) -> dict[str, Any]:
    """Redact forbidden keys without shortening the surviving values.

    For the ``payload`` field, whose values are already bounded previews the
    caller built with :func:`safe_preview`; running the full :func:`safe_metadata`
    here would clip a 500-char preview down to the tighter value limit.
    """

    if not data:
        return {}

    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if str(key).strip().lower() in _FORBIDDEN_KEYS:
            cleaned[key] = "[redacted]"
            continue
        cleaned[key] = value
    return cleaned


__all__ = ["safe_preview", "truncate_value", "safe_metadata", "redact_keys"]
