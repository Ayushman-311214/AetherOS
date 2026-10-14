"""
Planner actions and results.

The value types the planner returns. They exist so that deciding and acting can
be tested apart: the planner produces a description of the next step, and
something else -- the loop, once it exists -- carries it out. Nothing in this
module touches a tool, a provider or the registry.

Four action types cover every decision a single iteration can reach:

``final_response``
    The model answered in prose and asked for nothing. The run can stop.
``tool_call``
    The model asked for a tool, and the name and arguments survived validation,
    so the call is worth attempting. Whether it *succeeds* is the executor's
    business, not the planner's.
``continue``
    Nothing actionable this round -- an empty response, or every requested call
    was rejected. Feed the rejections back and plan again.
``fail``
    No next step can be produced: the provider errored, or the run has no
    iteration budget left to spend.

A rejected tool call is data, not an exception, for the same reason a failed
tool is: the model is the only thing that can fix a wrong argument, so it has to
be told. :class:`RejectedToolCall` is that telling, in a form the loop can turn
into a ``tool`` message.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ...core.errors.agent_error import AgentError
from ..state import ErrorRecord


class ActionType(str, Enum):
    """What the planner decided.

    ``str``-valued so a serialized action reads as ``{"type": "tool_call"}``
    rather than carrying an enum repr, and so equality against the wire string
    holds without a cast.
    """

    FINAL_RESPONSE = "final_response"
    TOOL_CALL = "tool_call"
    CONTINUE = "continue"
    FAIL = "fail"


# Rejection reasons, spelled exactly as ``ToolExecutor`` spells them. The two
# layers reject for the same reasons and a caller should not have to learn two
# vocabularies to tell which one spoke -- see ``tools/executor.py::_run``.
ERROR_MALFORMED_CALL = "MalformedCall"
ERROR_UNKNOWN_TOOL = "UnknownTool"
ERROR_TOOL_DISABLED = "ToolDisabled"
ERROR_INVALID_ARGUMENTS = "InvalidArguments"

# Refused by the planner rather than by the executor: more calls arrived in one
# response than an iteration is allowed to run.
ERROR_TOO_MANY_CALLS = "TooManyCalls"

# Not executor error types: nothing was executed. The provider itself failed, or
# the run was over before the planner was asked.
ERROR_PROVIDER = "ProviderError"
ERROR_TERMINAL_STATE = "RunAlreadyFinished"


@dataclass(frozen=True, slots=True)
class RejectedToolCall:
    """A call the planner refused to pass on, and why.

    Carries enough to answer the model in its own terms: ``call_id`` pairs the
    rejection with the assistant turn that asked for it, and ``reason`` is
    already phrased for the model to read -- ``ToolValidator`` writes those
    sentences, and they are reused verbatim rather than reworded.

    ``raw_arguments`` is the untouched payload text, kept because replaying the
    assistant turn needs it. It may contain argument *values*, so it is excluded
    from :meth:`describe` and from the repr; see the note on :meth:`to_dict`.
    """

    tool_name: str | None
    reason: str
    error_type: str
    call_id: str | None = None
    argument_names: tuple[str, ...] = ()
    raw_arguments: str = "{}"

    @property
    def is_addressable(self) -> bool:
        """Whether a ``tool`` message can carry this rejection back.

        A provider rejects a ``tool`` message whose ``tool_call_id`` is absent
        from the preceding assistant message, so a rejection without an id
        cannot be replayed as one -- it has to be folded into the next system or
        user turn instead.
        """

        return bool(self.call_id) and bool(self.tool_name)

    def to_dict(self) -> dict[str, Any]:
        """Faithful, and therefore not safe for the log sinks.

        Holds ``raw_arguments``, which may contain a password the model was
        asked to type. :meth:`describe` is the projection for logging.
        """

        return {
            "tool_name": self.tool_name,
            "reason": self.reason,
            "error_type": self.error_type,
            "call_id": self.call_id,
            "argument_names": list(self.argument_names),
            "raw_arguments": self.raw_arguments,
        }

    def describe(self) -> dict[str, Any]:
        """Log-safe: names and reasons, never argument values."""

        return {
            "tool_name": self.tool_name,
            "error_type": self.error_type,
            "reason": self.reason,
            "argument_names": list(self.argument_names),
        }

    def __repr__(self) -> str:
        return (
            f"RejectedToolCall(tool_name={self.tool_name!r}, "
            f"error_type={self.error_type!r}, "
            f"argument_names={list(self.argument_names)!r})"
        )


# Types whose whole purpose is to explain themselves. A ``fail`` nobody can
# read the cause of is worse than an exception; see ``__post_init__``.
_NEEDS_REASON = frozenset({ActionType.CONTINUE, ActionType.FAIL})


@dataclass(frozen=True, slots=True)
class PlannedAction:
    """One decision, described rather than performed.

    Frozen because an action that can be edited after it is decided is not a
    decision: the whole point of returning it as a value is that the step
    actually taken can be logged, diffed and replayed against the response that
    produced it.

    Construct through the classmethods -- :meth:`final_response`,
    :meth:`tool_call`, :meth:`continue_`, :meth:`fail` -- which set the fields
    each type needs. The invariants are checked either way, so a hand-built
    action that contradicts its own type is refused rather than passed on to a
    loop that would then have to guess what was meant.
    """

    type: ActionType

    # tool_call only.
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None
    raw_arguments: str = "{}"

    # final_response only.
    content: str = ""

    # continue / fail only.
    reason: str = ""
    error_type: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.arguments, dict):
            raise AgentError(
                code="PLANNER_ACTION_INVALID",
                message=(
                    "Action arguments must be a dict, got "
                    f"{type(self.arguments).__name__}."
                ),
                hint="Tool arguments are a JSON object; see parse_llm_response.",
            )

        if self.type is ActionType.TOOL_CALL and not self.tool_name:
            raise AgentError(
                code="PLANNER_ACTION_INVALID",
                message="A tool_call action needs a tool name.",
                hint="Reject the call instead of planning a nameless one.",
            )

        if self.type is ActionType.FINAL_RESPONSE and self.tool_name:
            raise AgentError(
                code="PLANNER_ACTION_INVALID",
                message=(
                    "A final_response action cannot name a tool "
                    f"(got {self.tool_name!r})."
                ),
                hint="Answering and calling a tool are different decisions.",
            )

        if self.type in _NEEDS_REASON and not self.reason:
            raise AgentError(
                code="PLANNER_ACTION_INVALID",
                message=f"A {self.type.value} action needs a reason.",
                hint="Whoever reads the log has to be able to tell why.",
            )

    # -- constructors -----------------------------------------------------

    @classmethod
    def final_response(cls, content: str) -> PlannedAction:
        """The model answered. ``content`` is the answer, verbatim."""

        return cls(type=ActionType.FINAL_RESPONSE, content=content)

    @classmethod
    def tool_call(
        cls,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        call_id: str | None = None,
        raw_arguments: str = "{}",
    ) -> PlannedAction:
        """A validated request to run ``tool_name``.

        The arguments are copied. The planner hands its actions to a caller that
        may keep them for the length of a run, and a dict shared with the parsed
        response would let one mutate the other.
        """

        return cls(
            type=ActionType.TOOL_CALL,
            tool_name=tool_name,
            arguments=deepcopy(dict(arguments or {})),
            call_id=call_id,
            raw_arguments=raw_arguments,
        )

    @classmethod
    def continue_(cls, reason: str) -> PlannedAction:
        """Another iteration is needed. Named with a trailing underscore
        because ``continue`` is a keyword; the wire value has neither."""

        return cls(type=ActionType.CONTINUE, reason=reason)

    @classmethod
    def fail(
        cls,
        reason: str,
        *,
        error_type: str | None = None,
    ) -> PlannedAction:
        """No next step exists. ``error_type`` names the kind of wall hit."""

        return cls(type=ActionType.FAIL, reason=reason, error_type=error_type)

    # -- shape ------------------------------------------------------------

    @property
    def is_final(self) -> bool:
        return self.type is ActionType.FINAL_RESPONSE

    @property
    def is_tool_call(self) -> bool:
        return self.type is ActionType.TOOL_CALL

    @property
    def is_continue(self) -> bool:
        return self.type is ActionType.CONTINUE

    @property
    def is_failure(self) -> bool:
        return self.type is ActionType.FAIL

    @property
    def argument_names(self) -> tuple[str, ...]:
        """Sorted argument names -- the log-safe half of the arguments.

        Values are withheld deliberately: ``type_text`` and ``set_clipboard``
        receive literal keystrokes, which may be a password the user was
        pasting, and the file sinks keep what they are given for weeks.
        """

        return tuple(sorted(self.arguments))

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """The action on the wire: ``type`` plus only the fields it uses.

        Faithful, and therefore not safe for the log sinks -- a tool_call holds
        argument values and a final_response holds the answer. :meth:`describe`
        is the projection for logging.
        """

        payload: dict[str, Any] = {"type": self.type.value}

        if self.type is ActionType.TOOL_CALL:
            payload["tool_name"] = self.tool_name
            payload["arguments"] = deepcopy(self.arguments)
            if self.call_id:
                payload["call_id"] = self.call_id
        elif self.type is ActionType.FINAL_RESPONSE:
            payload["content"] = self.content
        else:
            payload["reason"] = self.reason
            if self.error_type:
                payload["error_type"] = self.error_type

        return payload

    def describe(self) -> dict[str, Any]:
        """Log-safe: counts, names and planner-authored reasons only.

        ``reason`` is written by this layer, never by the model, so it is safe
        to log in full. ``content`` is the model's answer and is reported as a
        length.
        """

        payload: dict[str, Any] = {"type": self.type.value}

        if self.tool_name:
            payload["tool_name"] = self.tool_name
        if self.arguments:
            payload["argument_names"] = list(self.argument_names)
        if self.content:
            payload["content_chars"] = len(self.content)
        if self.reason:
            payload["reason"] = self.reason
        if self.error_type:
            payload["error_type"] = self.error_type

        return payload

    def __repr__(self) -> str:
        parts = [f"type={self.type.value!r}"]
        if self.tool_name:
            parts.append(f"tool_name={self.tool_name!r}")
            parts.append(f"argument_names={list(self.argument_names)!r}")
        if self.content:
            parts.append(f"content_chars={len(self.content)}")
        if self.reason:
            parts.append(f"reason={self.reason!r}")
        return f"PlannedAction({', '.join(parts)})"


@dataclass(frozen=True, slots=True)
class PlanResult:
    """What one planning round produced.

    The question the planner answers is singular -- what is the next action --
    and :attr:`action` is that answer. :attr:`actions` exists because a provider
    may return several tool calls in one turn, and dropping the rest would
    silently discard work the model asked for. For every other action type there
    is exactly one entry, so ``result.action`` is always the thing to look at
    first and ``result.tool_calls`` is what a loop iterates.

    :attr:`content` is any prose that arrived alongside tool calls. It is not
    the final answer -- the model has not finished -- but it is often the model
    explaining what it is about to do, which is worth keeping for the log.
    """

    actions: tuple[PlannedAction, ...]

    content: str = ""
    rejections: tuple[RejectedToolCall, ...] = ()

    # Provenance. Which provider and model produced the response this plan was
    # derived from, and which iteration asked. A plan that cannot be traced back
    # to a model version is not auditable, and CLAUDE.md 8 requires that it be.
    iteration: int = 0
    provider: str = ""
    model: str = ""

    # How many calls the provider asked for, before validation. The difference
    # between this and ``len(tool_calls)`` is how much the planner refused.
    requested_calls: int = 0

    # Set only when the provider itself failed; paired with a ``fail`` action.
    error: ErrorRecord | None = None

    def __post_init__(self) -> None:
        if not self.actions:
            raise AgentError(
                code="PLANNER_EMPTY_PLAN",
                message="A plan must contain at least one action.",
                hint="Return continue or fail rather than nothing at all.",
            )

    # -- shape ------------------------------------------------------------

    @property
    def action(self) -> PlannedAction:
        """The next action. Never absent -- see :meth:`__post_init__`."""

        return self.actions[0]

    @property
    def type(self) -> ActionType:
        return self.action.type

    @property
    def tool_calls(self) -> tuple[PlannedAction, ...]:
        return tuple(a for a in self.actions if a.is_tool_call)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    @property
    def has_rejections(self) -> bool:
        return bool(self.rejections)

    @property
    def is_final(self) -> bool:
        return self.action.is_final

    @property
    def is_failure(self) -> bool:
        return self.action.is_failure

    @property
    def needs_another_iteration(self) -> bool:
        """Whether the caller should plan again.

        True for ``continue`` and for tool calls -- both leave the goal
        unfinished. False for ``final_response`` and ``fail``, which are the two
        ways a run ends.
        """

        return self.action.is_continue or self.has_tool_calls

    # -- constructors -----------------------------------------------------

    @classmethod
    def single(cls, action: PlannedAction, **kwargs: Any) -> PlanResult:
        """One action, plus whatever provenance the caller has."""

        return cls(actions=(action,), **kwargs)

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Faithful, and therefore not safe for the log sinks."""

        return {
            "actions": [action.to_dict() for action in self.actions],
            "content": self.content,
            "rejections": [r.to_dict() for r in self.rejections],
            "iteration": self.iteration,
            "provider": self.provider,
            "model": self.model,
            "requested_calls": self.requested_calls,
            "error": self.error.to_dict() if self.error else None,
        }

    def describe(self) -> dict[str, Any]:
        """Log-safe: what was decided, not what was said."""

        return {
            "type": self.type.value,
            "actions": [action.describe() for action in self.actions],
            "content_chars": len(self.content),
            "rejections": [r.describe() for r in self.rejections],
            "iteration": self.iteration,
            "provider": self.provider,
            "model": self.model,
            "requested_calls": self.requested_calls,
            "error_type": self.error.error_type if self.error else None,
        }

    def __repr__(self) -> str:
        return (
            f"PlanResult(type={self.type.value!r}, "
            f"actions={len(self.actions)}, "
            f"rejections={len(self.rejections)}, "
            f"iteration={self.iteration}, "
            f"model={self.model!r})"
        )


__all__ = [
    "ERROR_INVALID_ARGUMENTS",
    "ERROR_MALFORMED_CALL",
    "ERROR_PROVIDER",
    "ERROR_TERMINAL_STATE",
    "ERROR_TOOL_DISABLED",
    "ERROR_TOO_MANY_CALLS",
    "ERROR_UNKNOWN_TOOL",
    "ActionType",
    "PlanResult",
    "PlannedAction",
    "RejectedToolCall",
]
