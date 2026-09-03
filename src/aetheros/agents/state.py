"""
Agent execution state.

One :class:`AgentState` is the complete, explicit record of a single agent run:
the goal it was given, the conversation it built, every tool it called, every
result it got back, what it observed, what went wrong, and how it ended.

Three properties are deliberate.

*Explicit.* Nothing about a run is implied by control flow. The iteration count,
the stop reason and the final response are fields, not locals inside a loop, so
a run can be inspected, logged, persisted or replayed by something other than the
function that produced it. ``LLMToolLoop`` keeps exactly this information in
local variables today, which is why its history dies with the call.

*Owned, never global.* Every run constructs its own state. There is no module
singleton and no registry here: two concurrent agents sharing one mutable
transcript would interleave into a conversation neither of them said.

*Serializable.* ``to_dict``/``from_dict`` round-trip, so a run can cross a
process boundary or land in a ``MemoryProvider``.

Concurrency
-----------
State is owned by one event loop. Every mutation is a coroutine guarded by an
``asyncio.Lock``, because the transitions that matter are compound: advancing an
iteration means *checking* the budget and then incrementing it; finishing a run
means checking that no outcome was recorded and then recording one. With
concurrent tasks — an orchestrator fanning out to sub-agents that share a parent
state — an unguarded check-then-act lets two tasks both pass the same check. A
bare ``list.append`` would not need the lock; these do.

Reads are synchronous and hand back tuples or copies, so a caller walking the
transcript cannot see it change underneath and cannot mutate it in place to
bypass the lock.

Secret hygiene
--------------
``to_dict()`` is faithful: it holds the user's goal, the model's messages and the
tool arguments. Those arguments reach here from ``type_text`` and
``set_clipboard``, so they may contain a password the user was pasting. Treat a
serialized state like the conversation itself and keep it away from the log
sinks, which retain for weeks. :meth:`AgentState.describe` is the form for logs:
it emits argument *names* only, the same rule ``ToolExecutor._log_outcome`` and
``Step.to_dict`` already apply.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..core.errors.agent_error import AgentError
from ..core.logging import get_logger
from ..llm.tool_calls import ToolCall
from ..tools.executor import ToolExecutionResult

DEFAULT_MAX_ITERATIONS = 8
"""Same budget ``AgentLoopConfig.max_iterations`` uses, so a state handed to the
loop layer later does not silently change how long a run is allowed to think."""

ITERATION_CEILING = 50
"""Hard upper bound on the requested budget, mirroring ``workflow.MAX_STEPS``.
A caller asking for a million iterations gets 50, not a run that cannot end."""

MESSAGE_ROLES = frozenset({"system", "user", "assistant", "tool"})

# The loop's existing vocabulary, reused verbatim rather than re-invented.
STOP_FINAL_ANSWER = "final_answer"
STOP_MAX_ITERATIONS = "max_iterations"
STOP_LOOP_GUARD = "loop_guard"
# Outcomes a state can reach that the loop has no word for yet.
STOP_ERROR = "error"
STOP_CANCELLED = "cancelled"


def utc_now() -> str:
    """ISO-8601 timestamp in UTC.

    UTC, not local time: a DST transition in a local-time audit trail silently
    reorders events, and prediction history is only useful if ordered.
    """
    return datetime.now(timezone.utc).isoformat()


def new_state_id() -> str:
    """Short, collision-resistant identifier for one agent run."""
    return f"agent-{uuid.uuid4().hex[:12]}"


def _reject_unknown(
    payload: dict[str, Any],
    allowed: frozenset[str],
    label: str,
) -> None:
    """Fail on fields we do not recognise instead of dropping them.

    Ignoring an unknown key restores a run that is quietly missing part of
    itself — a misspelled ``ok`` would turn a failed tool call into a
    successful one. ``Step.from_dict`` rejects for the same reason.
    """
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise AgentError(
            code="STATE_UNKNOWN_FIELD",
            message=f"Unknown {label} field(s): {', '.join(unknown)}.",
            hint="Restoring state must be lossless; remove or migrate the field.",
        )


def _require(payload: dict[str, Any], key: str, label: str) -> Any:
    if key not in payload:
        raise AgentError(
            code="STATE_MISSING_FIELD",
            message=f"{label} payload is missing required field {key!r}.",
        )
    return payload[key]


class AgentStatus(str, Enum):
    """Lifecycle of one run.

    ``str`` subclass so the value serializes as itself and a stored run stays
    readable without importing this module.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_STATUSES


_TERMINAL_STATUSES = frozenset(
    {AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED}
)

_MESSAGE_FIELDS = frozenset(
    {"role", "content", "tool_call_id", "tool_calls", "timestamp"}
)


@dataclass(frozen=True, slots=True)
class Message:
    """One turn of the conversation, in the shape the providers expect.

    Frozen: a transcript that can be edited after the fact is not an audit
    trail. Validation happens at construction because an unusable message is
    cheaper to reject here than three iterations later, when the provider
    rejects the whole request and the run is already half spent.
    """

    role: str
    content: str = ""
    tool_call_id: str | None = None
    tool_calls: tuple[dict[str, Any], ...] = ()
    timestamp: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        normalized = self.role.strip().lower()
        if normalized not in MESSAGE_ROLES:
            raise AgentError(
                code="STATE_INVALID_ROLE",
                message=f"Unknown message role {self.role!r}.",
                hint=f"Expected one of: {', '.join(sorted(MESSAGE_ROLES))}.",
            )
        object.__setattr__(self, "role", normalized)

        if normalized == "tool" and not self.tool_call_id:
            raise AgentError(
                code="STATE_ORPHAN_TOOL_MESSAGE",
                message="A tool message must name the tool_call_id it answers.",
                hint="Pass the id from the ToolCall this result responds to.",
            )
        object.__setattr__(self, "tool_calls", tuple(self.tool_calls))

    @classmethod
    def system(cls, content: str) -> Message:
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        return cls(role="user", content=content)

    @classmethod
    def assistant(
        cls,
        content: str = "",
        *,
        tool_calls: tuple[ToolCall, ...] | list[ToolCall] = (),
    ) -> Message:
        """An assistant turn, optionally carrying the calls the model asked for.

        ``raw_arguments`` is replayed rather than re-serialized so the message
        sent back to the provider matches what the model actually said.
        """
        wire = tuple(
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.raw_arguments},
            }
            for call in tool_calls
        )
        return cls(role="assistant", content=content, tool_calls=wire)

    @classmethod
    def tool(cls, *, tool_call_id: str, content: str) -> Message:
        return cls(role="tool", content=content, tool_call_id=tool_call_id)

    def to_wire(self) -> dict[str, Any]:
        """The provider-facing shape, matching ``LLMToolLoop`` exactly."""
        if self.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": self.tool_call_id,
                "content": self.content,
            }
        if self.role == "assistant" and self.tool_calls:
            # content or None: a tool-calling turn often has no prose, and the
            # providers expect null there rather than an empty string.
            return {
                "role": "assistant",
                "content": self.content or None,
                "tool_calls": [deepcopy(c) for c in self.tool_calls],
            }
        return {"role": self.role, "content": self.content}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            payload["tool_calls"] = [deepcopy(c) for c in self.tool_calls]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Message:
        _reject_unknown(payload, _MESSAGE_FIELDS, "message")
        return cls(
            role=str(_require(payload, "role", "Message")),
            content=str(payload.get("content") or ""),
            tool_call_id=payload.get("tool_call_id"),
            tool_calls=tuple(payload.get("tool_calls") or ()),
            timestamp=str(payload.get("timestamp") or utc_now()),
        )


_TOOL_CALL_FIELDS = frozenset({"id", "name", "iteration", "arguments", "timestamp"})


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """A tool the model asked for, tagged with the iteration that asked.

    Adapts :class:`~aetheros.llm.tool_calls.ToolCall` rather than replacing it:
    the parse layer owns the shape of a call, this layer owns *when* it happened.
    """

    id: str
    name: str
    iteration: int = 0
    arguments: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    @property
    def argument_names(self) -> tuple[str, ...]:
        """Names only. The safe projection for logs — see module docstring."""
        return tuple(sorted(self.arguments))

    @classmethod
    def from_tool_call(cls, call: ToolCall, *, iteration: int = 0) -> ToolCallRecord:
        return cls(
            id=call.id,
            name=call.name,
            iteration=iteration,
            arguments=deepcopy(call.arguments),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "iteration": self.iteration,
            "arguments": deepcopy(self.arguments),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ToolCallRecord:
        _reject_unknown(payload, _TOOL_CALL_FIELDS, "tool call")
        return cls(
            id=str(_require(payload, "id", "ToolCallRecord")),
            name=str(_require(payload, "name", "ToolCallRecord")),
            iteration=int(payload.get("iteration") or 0),
            arguments=dict(payload.get("arguments") or {}),
            timestamp=str(payload.get("timestamp") or utc_now()),
        )


_TOOL_RESULT_FIELDS = frozenset(
    {
        "call_id",
        "name",
        "ok",
        "iteration",
        "content",
        "error",
        "error_type",
        "duration_ms",
        "timestamp",
    }
)


@dataclass(frozen=True, slots=True)
class ToolResultRecord:
    """What came back from one tool call.

    A failed tool is data, not an exception: the model is expected to read
    ``error`` and try something else, which is why ``ToolExecutor`` reports
    failure as a result and why nothing here raises on ``ok=False``.
    """

    call_id: str
    name: str
    ok: bool
    iteration: int = 0
    content: str = ""
    error: str | None = None
    error_type: str | None = None
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=utc_now)

    @classmethod
    def from_execution(
        cls,
        result: ToolExecutionResult,
        *,
        call_id: str,
        iteration: int = 0,
        content: str | None = None,
    ) -> ToolResultRecord:
        """Adapt a :class:`ToolExecutionResult` without re-implementing it.

        ``content`` is what the model will read. When the caller does not supply
        it we render the value ourselves with ``default=str``, so a tool that
        returns a ``Path`` or a numpy scalar still produces a usable turn
        instead of raising mid-conversation.
        """
        return cls(
            call_id=call_id,
            name=result.name,
            ok=result.ok,
            iteration=iteration,
            content=content if content is not None else _render(result),
            error=result.error,
            error_type=result.error_type,
            duration_ms=result.duration_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "name": self.name,
            "ok": self.ok,
            "iteration": self.iteration,
            "content": self.content,
            "error": self.error,
            "error_type": self.error_type,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ToolResultRecord:
        _reject_unknown(payload, _TOOL_RESULT_FIELDS, "tool result")
        return cls(
            call_id=str(_require(payload, "call_id", "ToolResultRecord")),
            name=str(_require(payload, "name", "ToolResultRecord")),
            ok=bool(_require(payload, "ok", "ToolResultRecord")),
            iteration=int(payload.get("iteration") or 0),
            content=str(payload.get("content") or ""),
            error=payload.get("error"),
            error_type=payload.get("error_type"),
            duration_ms=float(payload.get("duration_ms") or 0.0),
            timestamp=str(payload.get("timestamp") or utc_now()),
        )


def _render(result: ToolExecutionResult) -> str:
    if not result.ok:
        return f"Error: {result.error}" if result.error else "Error"
    if isinstance(result.value, str):
        return result.value
    try:
        return json.dumps(result.value, default=str)
    except (TypeError, ValueError):
        return str(result.value)


_OBSERVATION_FIELDS = frozenset(
    {"text", "iteration", "source", "metadata", "timestamp"}
)


@dataclass(frozen=True, slots=True)
class Observation:
    """Something the agent noticed that is not itself a tool result.

    Kept separate from tool results because provenance matters: a screen reading
    from the vision layer and a number from a market-data API are not equally
    authoritative, and a later critic has to be able to tell them apart.
    """

    text: str
    iteration: int = 0
    source: str = "agent"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "iteration": self.iteration,
            "source": self.source,
            "metadata": deepcopy(self.metadata),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Observation:
        _reject_unknown(payload, _OBSERVATION_FIELDS, "observation")
        return cls(
            text=str(_require(payload, "text", "Observation")),
            iteration=int(payload.get("iteration") or 0),
            source=str(payload.get("source") or "agent"),
            metadata=dict(payload.get("metadata") or {}),
            timestamp=str(payload.get("timestamp") or utc_now()),
        )


_ERROR_FIELDS = frozenset(
    {"message", "error_type", "iteration", "recoverable", "timestamp"}
)


@dataclass(frozen=True, slots=True)
class ErrorRecord:
    """Something that went wrong during the run.

    ``recoverable`` is the important field. Most errors an agent meets are
    recoverable — a tool failed, the model can pick another one — and recording
    them must not end the run. An unrecoverable error is one the run cannot
    continue past, and only that kind is paired with :meth:`AgentState.fail`.
    """

    message: str
    error_type: str = "AgentError"
    iteration: int = 0
    recoverable: bool = True
    timestamp: str = field(default_factory=utc_now)

    @classmethod
    def from_exception(
        cls,
        exc: BaseException,
        *,
        iteration: int = 0,
        recoverable: bool = True,
    ) -> ErrorRecord:
        return cls(
            message=str(exc),
            error_type=type(exc).__name__,
            iteration=iteration,
            recoverable=recoverable,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "error_type": self.error_type,
            "iteration": self.iteration,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ErrorRecord:
        _reject_unknown(payload, _ERROR_FIELDS, "error")
        return cls(
            message=str(_require(payload, "message", "ErrorRecord")),
            error_type=str(payload.get("error_type") or "AgentError"),
            iteration=int(payload.get("iteration") or 0),
            recoverable=bool(payload.get("recoverable", True)),
            timestamp=str(payload.get("timestamp") or utc_now()),
        )


class AgentState:
    """The mutable record of one agent run.

    Not a dataclass, deliberately. The transcript lists are private, so no
    caller can ``state.messages.append(...)`` behind the lock's back; the public
    reads hand out tuples. This also follows the repository's existing split —
    frozen dataclasses for values, plain ``__slots__`` classes for objects with
    behaviour, as in ``ToolExecutor`` and ``AutomationEngine``.
    """

    __slots__ = (
        "_agent",
        "_completed_at",
        "_created_at",
        "_errors",
        "_final_response",
        "_goal",
        "_iteration",
        "_lock",
        "_logger",
        "_max_iterations",
        "_messages",
        "_metadata",
        "_observations",
        "_session_id",
        "_started_at",
        "_state_id",
        "_status",
        "_stopped_reason",
        "_tool_calls",
        "_tool_results",
        "_updated_at",
    )

    def __init__(
        self,
        goal: str,
        *,
        agent: str = "agent",
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        state_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not goal or not goal.strip():
            raise AgentError(
                code="STATE_EMPTY_GOAL",
                message="An agent run requires a goal.",
                hint="A run with no objective has no completion condition.",
            )

        self._goal = goal.strip()
        self._agent = agent
        self._state_id = state_id or new_state_id()
        self._session_id = session_id
        # Clamped, not validated: bounding by construction is the same rule
        # AgentLoopConfig and the workflow attempt budget already follow.
        self._max_iterations = max(1, min(int(max_iterations), ITERATION_CEILING))

        self._status = AgentStatus.PENDING
        self._iteration = 0
        self._stopped_reason: str | None = None
        self._final_response: str | None = None

        self._messages: list[Message] = []
        self._tool_calls: list[ToolCallRecord] = []
        self._tool_results: list[ToolResultRecord] = []
        self._observations: list[Observation] = []
        self._errors: list[ErrorRecord] = []
        self._metadata: dict[str, Any] = dict(metadata or {})

        self._created_at = utc_now()
        self._updated_at = self._created_at
        self._started_at: str | None = None
        self._completed_at: str | None = None

        self._lock = asyncio.Lock()
        self._logger = get_logger("agent_state")

    # -- identity ---------------------------------------------------------

    @property
    def goal(self) -> str:
        return self._goal

    @property
    def agent(self) -> str:
        return self._agent

    @property
    def state_id(self) -> str:
        return self._state_id

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def updated_at(self) -> str:
        return self._updated_at

    @property
    def started_at(self) -> str | None:
        return self._started_at

    @property
    def completed_at(self) -> str | None:
        return self._completed_at

    # -- progress ---------------------------------------------------------

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def stopped_reason(self) -> str | None:
        return self._stopped_reason

    @property
    def final_response(self) -> str | None:
        return self._final_response


    @property
    def iteration(self) -> int:
        return self._iteration

    @property
    def max_iterations(self) -> int:
        return self._max_iterations

    @property
    def iterations_remaining(self) -> int:
        return max(0, self._max_iterations - self._iteration)

    @property
    def has_iterations_left(self) -> bool:
        return self._iteration < self._max_iterations

    @property
    def is_running(self) -> bool:
        return self._status is AgentStatus.RUNNING

    @property
    def is_terminal(self) -> bool:
        return self._status.is_terminal

    # -- transcript -------------------------------------------------------
    #
    # Tuples, not the live lists: a caller walking the transcript must not see
    # it change underneath, and must not be able to append past the lock.

    @property
    def messages(self) -> tuple[Message, ...]:
        return tuple(self._messages)

    @property
    def tool_calls(self) -> tuple[ToolCallRecord, ...]:
        return tuple(self._tool_calls)

    @property
    def tool_results(self) -> tuple[ToolResultRecord, ...]:
        return tuple(self._tool_results)

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._observations)

    @property
    def errors(self) -> tuple[ErrorRecord, ...]:
        return tuple(self._errors)

    @property
    def metadata(self) -> dict[str, Any]:
        return deepcopy(self._metadata)


    @property
    def last_error(self) -> ErrorRecord | None:
        return self._errors[-1] if self._errors else None

    def conversation(self) -> tuple[dict[str, Any], ...]:
        """The transcript in provider wire format, ready to send."""
        return tuple(m.to_wire() for m in self._messages)

    def results_for(self, call_id: str) -> tuple[ToolResultRecord, ...]:
        """Every result recorded against one call id."""
        return tuple(r for r in self._tool_results if r.call_id == call_id)

    # -- internal ---------------------------------------------------------

    def _touch(self) -> None:
        self._updated_at = utc_now()

    def _reject_if_terminal(self, operation: str) -> None:
        """A finished run is immutable.

        This is what makes the record auditable: a state that recorded both a
        completion and a later failure describes a run that never happened.
        """
        if self._status.is_terminal:
            raise AgentError(
                code="STATE_ALREADY_FINISHED",
                message=(
                    f"Cannot {operation}: run {self._state_id} already finished "
                    f"as {self._status.value}."
                ),
                hint="Start a new AgentState instead of reopening a finished one.",
            )

    def _require_running(self, operation: str) -> None:
        self._reject_if_terminal(operation)
        if self._status is not AgentStatus.RUNNING:
            raise AgentError(
                code="STATE_NOT_RUNNING",
                message=f"Cannot {operation} before the run has started.",
                hint="Await state.start() first.",
            )

    # -- lifecycle --------------------------------------------------------

    async def start(self) -> None:
        """PENDING -> RUNNING. Idempotence is not offered on purpose: a second
        start would reset the clock on a run already in progress."""
        async with self._lock:
            if self._status is not AgentStatus.PENDING:
                raise AgentError(
                    code="STATE_ALREADY_STARTED",
                    message=(
                        f"Run {self._state_id} is {self._status.value}, "
                        "not pending."
                    ),
                )
            self._status = AgentStatus.RUNNING
            self._started_at = utc_now()
            self._touch()

        self._logger.bind(
            agent=self._agent,
            state_id=self._state_id,
            max_iterations=self._max_iterations,
        ).info("Agent run started")


    async def seed_conversation(self, system_prompt: str | None = None) -> None:
        """Open the transcript with the system prompt and the goal."""
        async with self._lock:
            self._reject_if_terminal("seed the conversation")
            if self._messages:
                raise AgentError(
                    code="STATE_ALREADY_SEEDED",
                    message="The conversation already has messages.",
                    hint="Seed once, before the first iteration.",
                )
            if system_prompt:
                self._messages.append(Message.system(system_prompt))
            self._messages.append(Message.user(self._goal))
            self._touch()

    async def next_iteration(self) -> int:
        """Claim the next iteration, or refuse.

        Check-then-increment is exactly why the lock exists: two tasks reading
        ``iteration == 7`` against a budget of 8 would both proceed and the run
        would overspend its budget by one.
        """
        async with self._lock:
            self._require_running("advance the iteration")
            if self._iteration >= self._max_iterations:
                raise AgentError(
                    code="STATE_ITERATIONS_EXHAUSTED",
                    message=(
                        f"Iteration budget of {self._max_iterations} is spent."
                    ),
                    hint=(
                        "Finish with complete(..., stopped_reason="
                        f"{STOP_MAX_ITERATIONS!r}) instead of advancing."
                    ),
                )
            self._iteration += 1
            self._touch()
            return self._iteration

    # -- recording --------------------------------------------------------

    async def add_message(self, message: Message) -> Message:
        async with self._lock:
            self._reject_if_terminal("add a message")
            self._messages.append(message)
            self._touch()
            return message

    async def extend_messages(self, messages: list[Message]) -> None:
        """Append several turns atomically.

        One lock acquisition, not one per message: an assistant turn and the
        tool turns answering it must never be split by another task's append,
        because a tool message that precedes its own call is an invalid request.
        """
        async with self._lock:
            self._reject_if_terminal("add messages")
            self._messages.extend(messages)
            self._touch()


    async def record_tool_call(
        self,
        call: ToolCall | ToolCallRecord,
        *,
        iteration: int | None = None,
    ) -> ToolCallRecord:
        """Record a call the model asked for.

        Accepts the parse layer's :class:`ToolCall` directly so callers never
        have to hand-copy fields between the two shapes.
        """
        async with self._lock:
            self._reject_if_terminal("record a tool call")
            record = (
                call
                if isinstance(call, ToolCallRecord)
                else ToolCallRecord.from_tool_call(
                    call,
                    iteration=self._iteration if iteration is None else iteration,
                )
            )
            self._tool_calls.append(record)
            self._touch()

        # Argument *names* only. Values reach here from type_text and
        # set_clipboard, so they may hold a password the user was pasting, and
        # the file sinks retain for weeks. Same rule the tool executor applies.
        self._logger.bind(
            agent=self._agent,
            state_id=self._state_id,
            iteration=record.iteration,
            tool=record.name,
            argument_names=list(record.argument_names),
        ).debug("Tool call recorded")
        return record

    async def record_tool_result(
        self,
        result: ToolExecutionResult | ToolResultRecord,
        *,
        call_id: str | None = None,
        iteration: int | None = None,
        content: str | None = None,
    ) -> ToolResultRecord:
        """Record what a tool returned. ``ok=False`` is data, not an error."""
        async with self._lock:
            self._reject_if_terminal("record a tool result")
            if isinstance(result, ToolResultRecord):
                record = result
            else:
                if call_id is None:
                    raise AgentError(
                        code="STATE_MISSING_CALL_ID",
                        message="A tool result must name the call it answers.",
                        hint="Pass call_id from the ToolCall that produced it.",
                    )
                record = ToolResultRecord.from_execution(
                    result,
                    call_id=call_id,
                    iteration=self._iteration if iteration is None else iteration,
                    content=content,
                )
            self._tool_results.append(record)
            self._touch()

        self._logger.bind(
            agent=self._agent,
            state_id=self._state_id,
            iteration=record.iteration,
            tool=record.name,
            ok=record.ok,
            duration_ms=record.duration_ms,
        ).debug("Tool result recorded")
        return record


    async def record_observation(
        self,
        text: str,
        *,
        source: str = "agent",
        iteration: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Observation:
        async with self._lock:
            self._reject_if_terminal("record an observation")
            observation = Observation(
                text=text,
                iteration=self._iteration if iteration is None else iteration,
                source=source,
                metadata=dict(metadata or {}),
            )
            self._observations.append(observation)
            self._touch()
            return observation

    async def record_error(
        self,
        error: str | BaseException,
        *,
        error_type: str | None = None,
        iteration: int | None = None,
        recoverable: bool = True,
    ) -> ErrorRecord:
        """Record a failure without ending the run.

        Recording is not failing. Most errors an agent meets are recoverable,
        and a state that ended itself on the first tool error would make the
        model's retry impossible.
        """
        async with self._lock:
            self._reject_if_terminal("record an error")
            at = self._iteration if iteration is None else iteration
            if isinstance(error, BaseException):
                record = ErrorRecord.from_exception(
                    error, iteration=at, recoverable=recoverable
                )
            else:
                record = ErrorRecord(
                    message=error,
                    error_type=error_type or "AgentError",
                    iteration=at,
                    recoverable=recoverable,
                )
            self._errors.append(record)
            self._touch()

        self._logger.bind(
            agent=self._agent,
            state_id=self._state_id,
            iteration=record.iteration,
            error_type=record.error_type,
            recoverable=record.recoverable,
        ).warning("Agent error recorded")
        return record


    # -- outcomes ---------------------------------------------------------

    async def complete(
        self,
        final_response: str,
        *,
        stopped_reason: str = STOP_FINAL_ANSWER,
    ) -> None:
        """Finish the run successfully.

        Running out of iterations is a completion, not a failure: it is reported
        as ``stopped_reason=max_iterations`` with whatever content exists, which
        is exactly how ``LLMToolLoop`` already ends an over-long run.
        """
        async with self._lock:
            self._reject_if_terminal("complete the run")
            self._status = AgentStatus.COMPLETED
            self._final_response = final_response
            self._stopped_reason = stopped_reason
            self._completed_at = utc_now()
            self._touch()

        self._logger.bind(
            agent=self._agent,
            state_id=self._state_id,
            iterations=self._iteration,
            stopped_reason=stopped_reason,
            tool_calls=len(self._tool_calls),
        ).info("Agent run completed")

    async def fail(
        self,
        error: str | BaseException,
        *,
        error_type: str | None = None,
        stopped_reason: str = STOP_ERROR,
    ) -> None:
        """Finish the run unsuccessfully, recording the unrecoverable error."""
        async with self._lock:
            self._reject_if_terminal("fail the run")
            if isinstance(error, BaseException):
                record = ErrorRecord.from_exception(
                    error, iteration=self._iteration, recoverable=False
                )
            else:
                record = ErrorRecord(
                    message=error,
                    error_type=error_type or "AgentError",
                    iteration=self._iteration,
                    recoverable=False,
                )
            self._errors.append(record)
            self._status = AgentStatus.FAILED
            self._stopped_reason = stopped_reason
            self._completed_at = utc_now()
            self._touch()

        self._logger.bind(
            agent=self._agent,
            state_id=self._state_id,
            iterations=self._iteration,
            error_type=record.error_type,
        ).error("Agent run failed")

    async def cancel(self, reason: str = STOP_CANCELLED) -> None:
        """Stop the run on request. Distinct from failure: nothing went wrong."""
        async with self._lock:
            self._reject_if_terminal("cancel the run")
            self._status = AgentStatus.CANCELLED
            self._stopped_reason = reason
            self._completed_at = utc_now()
            self._touch()

        self._logger.bind(
            agent=self._agent,
            state_id=self._state_id,
            iterations=self._iteration,
            reason=reason,
        ).info("Agent run cancelled")


    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """A faithful, round-trippable snapshot of the whole run.

        Contains the goal, the messages and the tool argument *values*. Treat it
        like the conversation itself: persist it, ship it across a process
        boundary, hand it to memory — but never to the log sinks. Use
        :meth:`describe` for that.
        """
        return {
            "state_id": self._state_id,
            "agent": self._agent,
            "goal": self._goal,
            "session_id": self._session_id,
            "status": self._status.value,
            "stopped_reason": self._stopped_reason,
            "final_response": self._final_response,
            "iteration": self._iteration,
            "max_iterations": self._max_iterations,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "started_at": self._started_at,
            "completed_at": self._completed_at,
            "messages": [m.to_dict() for m in self._messages],
            "tool_calls": [c.to_dict() for c in self._tool_calls],
            "tool_results": [r.to_dict() for r in self._tool_results],
            "observations": [o.to_dict() for o in self._observations],
            "errors": [e.to_dict() for e in self._errors],
            "metadata": deepcopy(self._metadata),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, raw: str) -> AgentState:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AgentError(
                code="STATE_INVALID_JSON",
                message="Agent state payload is not valid JSON.",
                cause=exc,
            ) from exc
        if not isinstance(payload, dict):
            raise AgentError(
                code="STATE_INVALID_PAYLOAD",
                message="Agent state payload must be a JSON object.",
            )
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentState:
        """Rebuild a run from a snapshot, rejecting anything we cannot restore.

        Private attributes are set directly rather than through the mutators:
        replaying a finished run through ``complete()`` would be rejected by the
        terminal-state guard, and nothing else holds a reference yet, so there
        is nothing for the lock to protect.
        """
        _reject_unknown(payload, _STATE_FIELDS, "agent state")

        state = cls(
            goal=str(_require(payload, "goal", "AgentState")),
            agent=str(payload.get("agent") or "agent"),
            max_iterations=int(
                payload.get("max_iterations") or DEFAULT_MAX_ITERATIONS
            ),
            state_id=payload.get("state_id"),
            session_id=payload.get("session_id"),
            metadata=dict(payload.get("metadata") or {}),
        )

        raw_status = str(payload.get("status") or AgentStatus.PENDING.value)
        try:
            state._status = AgentStatus(raw_status)
        except ValueError as exc:
            raise AgentError(
                code="STATE_INVALID_STATUS",
                message=f"Unknown agent status {raw_status!r}.",
                hint=f"Expected one of: {', '.join(s.value for s in AgentStatus)}.",
                cause=exc,
            ) from exc

        state._iteration = int(payload.get("iteration") or 0)
        state._stopped_reason = payload.get("stopped_reason")
        state._final_response = payload.get("final_response")
        state._created_at = str(payload.get("created_at") or state._created_at)
        state._updated_at = str(payload.get("updated_at") or state._updated_at)
        state._started_at = payload.get("started_at")
        state._completed_at = payload.get("completed_at")

        state._messages = [
            Message.from_dict(m) for m in payload.get("messages") or ()
        ]
        state._tool_calls = [
            ToolCallRecord.from_dict(c) for c in payload.get("tool_calls") or ()
        ]
        state._tool_results = [
            ToolResultRecord.from_dict(r) for r in payload.get("tool_results") or ()
        ]
        state._observations = [
            Observation.from_dict(o) for o in payload.get("observations") or ()
        ]
        state._errors = [
            ErrorRecord.from_dict(e) for e in payload.get("errors") or ()
        ]
        return state

    # -- logging ----------------------------------------------------------

    def describe(self) -> dict[str, Any]:
        """The redacted view, safe for the log sinks.

        Counts and tool *names* only — no goal text, no message content, no
        argument values. This is the projection ``ToolExecutor._log_outcome``
        and ``Step.to_dict`` already use, and the reason is the same: the file
        sinks retain for weeks, and tool arguments can hold a password.
        """
        return {
            "state_id": self._state_id,
            "agent": self._agent,
            "status": self._status.value,
            "stopped_reason": self._stopped_reason,
            "iteration": self._iteration,
            "max_iterations": self._max_iterations,
            "messages": len(self._messages),
            "tool_calls": len(self._tool_calls),
            "tools_used": sorted({c.name for c in self._tool_calls}),
            "tool_results": len(self._tool_results),
            "tool_failures": sum(1 for r in self._tool_results if not r.ok),
            "observations": len(self._observations),
            "errors": len(self._errors),
            "has_final_response": self._final_response is not None,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    def __repr__(self) -> str:
        # No goal text: reprs land in tracebacks, and tracebacks land in logs.
        return (
            f"AgentState(state_id={self._state_id!r}, agent={self._agent!r}, "
            f"status={self._status.value!r}, "
            f"iteration={self._iteration}/{self._max_iterations}, "
            f"messages={len(self._messages)})"
        )


_STATE_FIELDS = frozenset(
    {
        "state_id",
        "agent",
        "goal",
        "session_id",
        "status",
        "stopped_reason",
        "final_response",
        "iteration",
        "max_iterations",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "messages",
        "tool_calls",
        "tool_results",
        "observations",
        "errors",
        "metadata",
    }
)


__all__ = [
    "DEFAULT_MAX_ITERATIONS",
    "ITERATION_CEILING",
    "MESSAGE_ROLES",
    "STOP_CANCELLED",
    "STOP_ERROR",
    "STOP_FINAL_ANSWER",
    "STOP_LOOP_GUARD",
    "STOP_MAX_ITERATIONS",
    "AgentState",
    "AgentStatus",
    "ErrorRecord",
    "Message",
    "Observation",
    "ToolCallRecord",
    "ToolResultRecord",
    "new_state_id",
    "utc_now",
]
