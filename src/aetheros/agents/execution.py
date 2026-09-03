"""
Agent-level tool execution.

One responsibility: *a planned tool call becomes a recorded outcome*. The
coordinator sits between a decision and a side effect, and it owns exactly the
three things neither of its neighbours does.

*Refusal before delegation.* A call naming a tool the registry does not hold, or
holds and has switched off, never reaches the execution engine.
:class:`~aetheros.tools.executor.ToolExecutor` refuses both cases itself, and its
wording is reused verbatim -- but it refuses them as a *result*, and a result
cannot be told apart from one a tool produced by running. The agent needs that
difference: :attr:`AgentExecutionResult.delegated` is what tells an orchestrator
whether a real side effect may have occurred, and no amount of reading an error
string afterwards recovers it.

*Recording.* Every attempt lands in :class:`~aetheros.agents.state.AgentState` --
the call, the result, and, when it failed, an error record. The engine keeps no
history at all, and ``LLMToolLoop`` keeps its history in local variables that die
with the call, so a run's tool history has nowhere else to live. CLAUDE.md 8
requires a prediction to be auditable, and an unrecorded side effect is not.

*One structured outcome.* :class:`AgentExecutionResult` says what the tool was
asked, what it answered, how long it took, and whether any of that reached the
state -- so a caller never has to reassemble one round from three places.

What this is not
----------------
``ToolExecutor`` is the execution engine, and the only one. It resolves the
function, applies the per-tool timeout, offloads blocking tools to a thread,
validates the arguments and turns every failure into a value. None of that is
reimplemented here.

Argument validation in particular is *not* re-run. The planner checks arguments
before it plans a call and the executor checks them again before it touches the
tool; a third pass in between would only add a third place for the three to
disagree. An ``InvalidArguments`` failure therefore arrives here exactly the way
a tool crash does -- as an outcome to capture and record.

Nor is the result text re-rendered or truncated.
:meth:`~aetheros.agents.state.ToolResultRecord.from_execution` renders it and
:class:`~aetheros.agents.context.ContextBuilder` truncates it to the prompt
budget, so a limit applied here would cut the same string twice and the model
would be told about a truncation the transcript does not show.

Ordering
--------
:meth:`ToolExecutionCoordinator.execute_many` runs its calls one at a time, in
the order the model asked for them. Concurrency would be wrong rather than merely
unnecessary: the desktop tools share one mouse, one keyboard and one clipboard, so
a ``click`` racing a ``type_text`` produces an interleaving neither call asked
for. It also never stops early -- a provider rejects an assistant turn whose tool
calls are not all answered, so abandoning the rest after one failure would make
the next request invalid.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.errors.agent_error import AgentError
from ..core.logging import get_logger
from ..llm.tool_calls import ToolCall
from ..tools.executor import ToolExecutionResult, ToolExecutor, tool_executor
from ..tools.registry import ToolDefinition, ToolRegistry, tool_registry

# Imported rather than restated. These are the executor's own error types, named
# once in the planner's action vocabulary; spelling the literals again here would
# give a future rename two places to miss.
from .planner.actions import (
    ERROR_TERMINAL_STATE,
    ERROR_TOOL_DISABLED,
    ERROR_UNKNOWN_TOOL,
    PlannedAction,
)
from .state import AgentState, ToolResultRecord


class ExecutionStatus(str, Enum):
    """How one attempt ended.

    ``str``-valued so a serialized result reads as ``{"status": "refused"}``
    rather than carrying an enum repr, matching
    :class:`~aetheros.agents.state.AgentStatus`.

    ``refused`` is not a kind of ``failed``: nothing ran, so nothing on the
    machine changed, and the only thing that can fix it is the model asking for a
    different tool.
    """

    OK = "ok"
    FAILED = "failed"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class AgentExecutionResult:
    """The outcome of one tool call, as the agent layer sees it.

    Frozen: what a tool did is a fact about the run, and a fact that can be
    edited afterwards is not an audit trail.

    Adapts :class:`~aetheros.tools.executor.ToolExecutionResult` rather than
    replacing it. The engine's result answers *what did the function do*; this one
    also answers the three questions the engine has no way to know -- which call
    it belonged to, whether the tool was reached at all, and whether the run's
    state now knows about it.
    """

    call_id: str
    tool_name: str
    ok: bool

    value: Any = None

    # The text the model will read, as ToolResultRecord rendered it. Carried here
    # so a caller building the tool message does not render it a second time and
    # risk showing the model something the transcript does not contain.
    content: str = ""

    error: str | None = None
    error_type: str | None = None

    arguments: dict[str, Any] = field(default_factory=dict)
    iteration: int = 0

    # The tool's own execution time, straight from the engine. Zero for a call
    # refused before it got there, which is why the two timings are kept apart.
    duration_ms: float = 0.0

    # This layer's whole span: the checks, the execution and the state writes. The
    # gap between it and duration_ms is overhead belonging here, and it is the
    # number to look at when every tool reports fast and the run still feels slow.
    total_ms: float = 0.0

    # Whether the call reached ToolExecutor. False means nothing ran and no side
    # effect is possible. True does not promise the function itself ran: the
    # engine still rejects invalid arguments before touching it.
    delegated: bool = False

    # Whether the outcome reached AgentState. False only when the run went
    # terminal underneath the call -- see ToolExecutionCoordinator._store.
    recorded: bool = False

    # -- shape ------------------------------------------------------------

    @property
    def status(self) -> ExecutionStatus:
        """``ok``, ``failed`` if the engine was asked, ``refused`` if it was not."""

        if self.ok:
            return ExecutionStatus.OK

        return (
            ExecutionStatus.FAILED if self.delegated else ExecutionStatus.REFUSED
        )

    @property
    def failed(self) -> bool:
        return not self.ok

    @property
    def refused(self) -> bool:
        """Turned away by this layer, without the engine being asked."""

        return not self.delegated

    @property
    def argument_names(self) -> tuple[str, ...]:
        """Sorted names, no values -- the log-safe half of the arguments.

        ``type_text`` and ``set_clipboard`` receive literal keystrokes, which may
        be a password the user was pasting, and the file sinks keep what they are
        given for weeks. Same rule ``ToolExecutor._log_outcome`` applies.
        """

        return tuple(sorted(self.arguments))

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Faithful, and therefore not safe for the log sinks.

        Holds the argument values and the tool's return value. :meth:`describe`
        is the projection for logging.
        """

        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "ok": self.ok,
            "value": self.value,
            "content": self.content,
            "error": self.error,
            "error_type": self.error_type,
            "arguments": deepcopy(self.arguments),
            "iteration": self.iteration,
            "duration_ms": self.duration_ms,
            "total_ms": self.total_ms,
            "delegated": self.delegated,
            "recorded": self.recorded,
        }

    def describe(self) -> dict[str, Any]:
        """Log-safe: names, outcomes and timings, never values.

        ``error`` is included because the engine and the validator write those
        sentences and both are careful to name parameters and types rather than
        payloads -- see ``ToolValidator``. ``content`` is the tool's own output and
        is reported as a length.
        """

        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "argument_names": list(self.argument_names),
            "iteration": self.iteration,
            "duration_ms": round(self.duration_ms, 2),
            "total_ms": round(self.total_ms, 2),
            "delegated": self.delegated,
            "recorded": self.recorded,
            "error_type": self.error_type,
            "error": self.error,
            "content_chars": len(self.content),
        }

    def __repr__(self) -> str:
        return (
            f"AgentExecutionResult(tool_name={self.tool_name!r}, "
            f"status={self.status.value!r}, "
            f"argument_names={list(self.argument_names)!r}, "
            f"duration_ms={round(self.duration_ms, 2)}, "
            f"content_chars={len(self.content)})"
        )


@dataclass(frozen=True, slots=True)
class ExecutionBatch:
    """Every outcome from one round of tool calls, in the order they ran.

    Exists for the same reason :class:`~aetheros.agents.planner.PlanResult` does:
    a round is the unit a caller reasons about, and computing "did all of them
    work" at each call site is how two call sites end up disagreeing.
    """

    results: tuple[AgentExecutionResult, ...] = ()
    iteration: int = 0

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self) -> Iterator[AgentExecutionResult]:
        return iter(self.results)

    # -- shape ------------------------------------------------------------

    @property
    def succeeded(self) -> tuple[AgentExecutionResult, ...]:
        return tuple(r for r in self.results if r.ok)

    @property
    def failures(self) -> tuple[AgentExecutionResult, ...]:
        """Everything that did not succeed, refusals included."""

        return tuple(r for r in self.results if not r.ok)

    @property
    def refusals(self) -> tuple[AgentExecutionResult, ...]:
        """The calls this layer turned away before the engine was asked."""

        return tuple(r for r in self.results if r.refused)

    @property
    def all_ok(self) -> bool:
        """True for an empty batch: nothing was asked, so nothing went wrong."""

        return all(r.ok for r in self.results)

    @property
    def any_failed(self) -> bool:
        return any(not r.ok for r in self.results)

    @property
    def executed_count(self) -> int:
        """How many calls actually reached the engine."""

        return sum(1 for r in self.results if r.delegated)

    @property
    def total_ms(self) -> float:
        """Wall time for the round. Sequential execution makes the sum the span."""

        return sum(r.total_ms for r in self.results)

    def result_for(self, call_id: str) -> AgentExecutionResult | None:
        """The outcome answering one call, or ``None``."""

        for result in self.results:
            if result.call_id == call_id:
                return result

        return None

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Faithful, and therefore not safe for the log sinks."""

        return {
            "iteration": self.iteration,
            "results": [r.to_dict() for r in self.results],
        }

    def describe(self) -> dict[str, Any]:
        """Log-safe: one line's worth of what the round did."""

        return {
            "iteration": self.iteration,
            "calls": len(self.results),
            "succeeded": len(self.succeeded),
            "failed": len(self.failures),
            "refused": len(self.refusals),
            "executed": self.executed_count,
            "total_ms": round(self.total_ms, 2),
            "results": [r.describe() for r in self.results],
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionBatch(calls={len(self.results)}, "
            f"succeeded={len(self.succeeded)}, "
            f"failed={len(self.failures)}, "
            f"iteration={self.iteration})"
        )


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """What the coordinator records, and how loudly.

    Both defaults are the strict reading. Neither changes what runs -- only what
    the run leaves behind.
    """

    # A failed tool is already recorded as a result with ``ok=False``; this also
    # files it in ``AgentState.errors``. The two are not redundant: the result is
    # the answer the model reads, while the error list is the run's failure ledger,
    # and an orchestrator deciding whether a run is going badly reads the ledger.
    record_errors: bool = True

    # Argument *values* in the log lines. Off by default and intended to stay off
    # outside local debugging, for the reason documented on
    # ``AgentLoopConfig.log_tool_arguments``: type_text and set_clipboard receive
    # literal keystrokes and the file sinks retain for weeks.
    log_arguments: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_errors": self.record_errors,
            "log_arguments": self.log_arguments,
        }


class ToolExecutionCoordinator:
    """Runs one planned tool call through the engine and records what happened.

    Holds no per-run state: the run lives in the :class:`AgentState` passed to
    each call, so one coordinator serves every concurrent agent in the process.
    That is deliberate -- a coordinator that accumulated a run's history would be
    a second, quieter copy of the state, free to disagree with it.

    The registry and the executor are injected, defaulting to the process-wide
    singletons. They must be built over the *same* registry: the existence and
    enabled checks answer for the registry this object was given, and an executor
    reading a different one would then contradict its own coordinator.
    """

    __slots__ = ("_config", "_executor", "_logger", "_registry")

    def __init__(
        self,
        executor: ToolExecutor | None = None,
        *,
        registry: ToolRegistry | None = None,
        config: ExecutionConfig | None = None,
    ) -> None:
        self._executor = executor or tool_executor
        self._registry = registry or tool_registry
        self._config = config or ExecutionConfig()

        # Built here, not at import time: loguru is a process-wide singleton and
        # get_logger installs the file sinks on first use.
        self._logger = get_logger("agents.execution")

    @property
    def config(self) -> ExecutionConfig:
        return self._config

    # -- execution --------------------------------------------------------

    async def execute(
        self,
        state: AgentState,
        call: ToolCall | PlannedAction,
        *,
        iteration: int | None = None,
    ) -> AgentExecutionResult:
        """Run one validated call and record the round it produced.

        Accepts either shape a validated call arrives in: the parse layer's
        :class:`~aetheros.llm.tool_calls.ToolCall`, or the
        :class:`~aetheros.agents.planner.PlannedAction` the planner emits for one
        -- which is the same call wearing the planner's vocabulary, and converting
        it at every call site would be busywork.

        Never raises for a tool-level problem; every one of them comes back as a
        result, because a model that asked for the wrong thing is the only thing
        that can fix it and it has to be told. ``asyncio.CancelledError`` does
        propagate, from ``ToolExecutor`` through untouched: the run is being torn
        down and swallowing it would hide that from the task that asked. The call
        record already written then stays in the state without a result, which is
        the honest description of a tool that was in flight when the run stopped.
        """

        started = time.perf_counter()
        resolved = _as_tool_call(call)
        at = state.iteration if iteration is None else iteration

        if state.is_terminal:
            # Nothing is written: AgentState refuses every recording once a run
            # has ended, and it is right to -- a finished run whose transcript
            # keeps growing is not a record of anything.
            return self._unrecorded(
                resolved,
                at,
                started,
                reason=(
                    f"The run already finished ({state.status.value}); "
                    f"'{resolved.name}' was not executed."
                ),
                error_type=ERROR_TERMINAL_STATE,
            )

        if not await self._store_call(state, resolved, at):
            return self._unrecorded(
                resolved,
                at,
                started,
                reason=(
                    f"The run finished before '{resolved.name}' could be "
                    "recorded; it was not executed."
                ),
                error_type=ERROR_TERMINAL_STATE,
            )

        tool = self._resolve(resolved.name)

        if tool is None:
            return await self._refuse(
                state,
                resolved,
                at,
                started,
                reason=(
                    f"Unknown tool '{resolved.name}'. "
                    f"Available tools: {self._available() or 'none'}."
                ),
                error_type=ERROR_UNKNOWN_TOOL,
            )

        if not tool.enabled:
            return await self._refuse(
                state,
                resolved,
                at,
                started,
                reason=f"Tool '{resolved.name}' is disabled.",
                error_type=ERROR_TOOL_DISABLED,
            )

        outcome = await self._executor.execute_safe(
            resolved.name,
            resolved.arguments,
        )

        return await self._capture(
            state,
            resolved,
            outcome,
            at,
            started,
            delegated=True,
        )

    async def execute_many(
        self,
        state: AgentState,
        calls: Sequence[ToolCall | PlannedAction],
        *,
        iteration: int | None = None,
    ) -> ExecutionBatch:
        """Run several calls in order, one at a time, answering all of them.

        The iteration is resolved once so every result in a round carries the same
        number, even if another task advances the state while the round runs.

        See the module docstring for why this is sequential and why it does not
        stop at the first failure.
        """

        at = state.iteration if iteration is None else iteration

        results = [
            await self.execute(state, call, iteration=at) for call in calls
        ]

        batch = ExecutionBatch(results=tuple(results), iteration=at)

        self._logger.bind(**batch.describe()).debug(
            "Executed {calls} tool call(s) for iteration {iteration}",
            calls=len(batch),
            iteration=at,
        )

        return batch

    # -- refusals ---------------------------------------------------------

    def _resolve(self, name: str) -> ToolDefinition | None:
        """``exists`` before ``get``, because ``get`` raises ``KeyError``.

        An invented tool name is the single most common thing a model gets wrong,
        and it has to come back as a sentence the model can act on rather than a
        traceback out of a dict lookup.
        """

        return self._registry.get(name) if self._registry.exists(name) else None

    def _available(self) -> str:
        """Enabled tool names, sorted, for a message the model has to read.

        Enabled only -- matching the planner rather than
        ``ToolExecutor``, which lists everything registered. A disabled tool is
        not available, whatever the registry still holds, and naming it in the
        list only invites the model to try it again.
        """

        return ", ".join(
            sorted(tool.name for tool in self._registry.enabled_tools())
        )

    async def _refuse(
        self,
        state: AgentState,
        call: ToolCall,
        at: int,
        started: float,
        *,
        reason: str,
        error_type: str,
    ) -> AgentExecutionResult:
        """Record a call that was turned away, without the engine being asked.

        The refusal is still a full round in the transcript: the model asked, and
        it gets an answer it can read. Only ``delegated`` distinguishes it from a
        tool that ran and failed.
        """

        return await self._capture(
            state,
            call,
            _failure(call.name, reason, error_type),
            at,
            started,
            delegated=False,
        )

    def _unrecorded(
        self,
        call: ToolCall,
        at: int,
        started: float,
        *,
        reason: str,
        error_type: str,
    ) -> AgentExecutionResult:
        """Report a refusal that could not be written down.

        Reached only when the run is already terminal, so there is no state left
        to record into. The result is still rendered the way a recorded one would
        be, so a caller that builds tool messages from ``content`` does not have to
        special-case it.
        """

        outcome = _failure(call.name, reason, error_type)

        return self._log(
            self._assemble(
                call,
                outcome,
                ToolResultRecord.from_execution(
                    outcome,
                    call_id=call.id,
                    iteration=at,
                ).content,
                at,
                started,
                delegated=False,
                recorded=False,
            )
        )

    # -- recording --------------------------------------------------------

    async def _capture(
        self,
        state: AgentState,
        call: ToolCall,
        outcome: ToolExecutionResult,
        at: int,
        started: float,
        *,
        delegated: bool,
    ) -> AgentExecutionResult:
        """Write the outcome into the run, then describe it.

        The record is built before it is stored so its rendered ``content`` is
        available whether or not the write lands -- and so it is rendered once,
        by the layer that owns the rendering.
        """

        record = ToolResultRecord.from_execution(
            outcome,
            call_id=call.id,
            iteration=at,
        )

        recorded = await self._store(state, record)

        if not outcome.ok and self._config.record_errors:
            await self._store_error(state, outcome, at)

        return self._log(
            self._assemble(
                call,
                outcome,
                record.content,
                at,
                started,
                delegated=delegated,
                recorded=recorded,
            )
        )

    async def _store_call(
        self,
        state: AgentState,
        call: ToolCall,
        at: int,
    ) -> bool:
        """Record the request, before anything is checked or run.

        Ordered first on purpose: the model asked for this call, and a transcript
        that shows the refusal but not the request cannot explain itself.
        """

        try:
            await state.record_tool_call(call, iteration=at)

        except AgentError as exc:
            self._logger.bind(
                tool=call.name,
                iteration=at,
                reason=exc.message,
            ).warning("Could not record the tool call; the run has ended.")

            return False

        return True

    async def _store(
        self,
        state: AgentState,
        record: ToolResultRecord,
    ) -> bool:
        """Record the outcome, tolerating a run that ended underneath it.

        The only way this fails is a concurrent terminal transition -- another task
        cancelling the run between the check at the top of :meth:`execute` and this
        write. Letting that raise would turn a completed side effect into an
        exception and lose the only evidence the tool ran, so it comes back as
        ``recorded=False`` on a result that still reports what happened.
        """

        try:
            await state.record_tool_result(record)

        except AgentError as exc:
            self._logger.bind(
                tool=record.name,
                ok=record.ok,
                iteration=record.iteration,
                reason=exc.message,
            ).warning("Could not record the tool result; the run has ended.")

            return False

        return True

    async def _store_error(
        self,
        state: AgentState,
        outcome: ToolExecutionResult,
        at: int,
    ) -> bool:
        """File a failure in the run's error ledger.

        Field by field rather than by handing over a record:
        :meth:`AgentState.record_error` takes a message plus its metadata, and
        stamps its own timestamp. Marked recoverable because a failed tool is data
        -- the model reads the error and tries something else, which is the whole
        reason ``ToolExecutor`` reports failure as a value.
        """

        try:
            await state.record_error(
                outcome.error or f"Tool '{outcome.name}' failed.",
                error_type=outcome.error_type,
                iteration=at,
                recoverable=True,
            )

        except AgentError as exc:
            self._logger.bind(
                tool=outcome.name,
                iteration=at,
                reason=exc.message,
            ).warning("Could not record the tool failure; the run has ended.")

            return False

        return True

    # -- assembly ---------------------------------------------------------

    @staticmethod
    def _assemble(
        call: ToolCall,
        outcome: ToolExecutionResult,
        content: str,
        at: int,
        started: float,
        *,
        delegated: bool,
        recorded: bool,
    ) -> AgentExecutionResult:
        """Build the result. Pure -- no state, no clock beyond the elapsed span.

        The arguments are copied. A caller may keep a result for the length of a
        run, and a dict shared with the call it describes would let one edit the
        other's history.
        """

        return AgentExecutionResult(
            call_id=call.id,
            tool_name=call.name,
            ok=outcome.ok,
            value=outcome.value,
            content=content,
            error=outcome.error,
            error_type=outcome.error_type,
            arguments=deepcopy(call.arguments),
            iteration=at,
            duration_ms=outcome.duration_ms,
            total_ms=(time.perf_counter() - started) * 1000.0,
            delegated=delegated,
            recorded=recorded,
        )

    def _log(self, result: AgentExecutionResult) -> AgentExecutionResult:
        """One line per attempt, returning the result unchanged.

        :meth:`AgentExecutionResult.describe` withholds argument values and the
        tool's output; ``log_arguments`` adds the values back for a local debugging
        session and is off everywhere else.
        """

        bound = self._logger.bind(**result.describe())

        if self._config.log_arguments:
            bound = bound.bind(arguments=result.arguments)

        message = "Tool {tool} {status} in iteration {iteration}"

        if result.ok:
            bound.info(
                message,
                tool=result.tool_name,
                status=result.status.value,
                iteration=result.iteration,
            )
        else:
            bound.warning(
                message,
                tool=result.tool_name,
                status=result.status.value,
                iteration=result.iteration,
            )

        return result


# ==============================================================
# Module helpers
# ==============================================================


def _as_tool_call(source: ToolCall | PlannedAction) -> ToolCall:
    """Normalise what the caller handed over into a :class:`ToolCall`.

    A ``tool_call`` :class:`PlannedAction` is a validated call in the planner's
    vocabulary and converts exactly. Anything else is a caller mistake, not a
    model mistake: an :class:`AgentError` is right here for the same reason
    ``AgentState`` raises one on a fourth iteration of a three-iteration budget --
    nothing downstream can recover from a coordinator asked to execute something
    that is not a call.
    """

    if isinstance(source, ToolCall):
        return source

    if not isinstance(source, PlannedAction):
        raise AgentError(
            code="EXECUTION_NOT_A_CALL",
            message=(
                "Expected a ToolCall or a tool_call PlannedAction, got "
                f"{type(source).__name__}."
            ),
            hint="Pass plan.tool_calls, or the parsed ToolCall itself.",
        )

    if not source.is_tool_call:
        raise AgentError(
            code="EXECUTION_NOT_A_CALL",
            message=(
                f"A {source.type.value} action names no tool to execute."
            ),
            hint="Only tool_call actions are executable; the rest end a round.",
        )

    if not source.call_id:
        # Every call that reached here through the planner has one:
        # parse_llm_response synthesises ``call_<index>`` when the provider omits
        # it. A hand-built action without one cannot be recorded -- AgentState
        # refuses a result that does not name the call it answers -- and inventing
        # an id would make the transcript claim the model said something it did not.
        raise AgentError(
            code="EXECUTION_MISSING_CALL_ID",
            message=(
                f"The planned call to '{source.tool_name}' has no call_id."
            ),
            hint="Carry the id from the ToolCall the planner accepted.",
        )

    return ToolCall(
        id=source.call_id,
        name=source.tool_name or "",
        arguments=deepcopy(source.arguments),
        raw_arguments=source.raw_arguments,
    )


def _failure(
    name: str,
    reason: str,
    error_type: str,
) -> ToolExecutionResult:
    """A failure in the engine's own currency, for a call the engine never saw.

    ``duration_ms`` stays at zero: nothing ran, and a non-zero execution time for
    a tool that was never reached would be a small lie in every log line and
    latency figure derived from it.
    """

    return ToolExecutionResult(
        name=name,
        ok=False,
        error=reason,
        error_type=error_type,
        duration_ms=0.0,
    )


__all__ = [
    "AgentExecutionResult",
    "ExecutionBatch",
    "ExecutionConfig",
    "ExecutionStatus",
    "ToolExecutionCoordinator",
]
